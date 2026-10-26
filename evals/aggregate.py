"""Aggregate one measured eval study, refusing any study that is incomplete, inconsistent or altered.

Usage:
    python3 evals/aggregate.py STUDY_DIR [--json OUT] [--summary OUT]
    python3 evals/aggregate.py --rescore STUDY_DIR [--json OUT] [--summary OUT]
    python3 evals/aggregate.py --verify-identity STUDY_DIR

Exit codes: 0 when the study is valid (or the identity matches), 1 otherwise.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys

EVALS_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, EVALS_DIR)
import run as eval_run  # noqa: E402
import score  # noqa: E402

RESULTS_GLOBS = ("samples/*/results.json", "controls/*/results.json", "retries/*/*/results.json")
PROVENANCE_KEYS = ("provenance", "provenance_after")
IDENTITY_SKIP = ("commit", "dirty")
OBSERVATION_KEYS = ("intent_line", "spec_cited", "history_cited")
MANIFEST = "manifest-sha256.txt"
# A rescore recomputes every scored field from the raw reports; only these may change.
RESCORE_ALGORITHM = "completeness-v2"
RESCORABLE_FIELDS = ("complete", "passed", "checks.complete")
# The study whose aggregate is the canonical baseline.json.
CURRENT_STUDY = os.path.join(EVALS_DIR, "baseline", "expanded-r2")


class StudyError(Exception):
    """A study that cannot be aggregated: missing, incomplete, inconsistent or altered."""


def _read_study_file(study_dir: str, name: str) -> bytes:
    path = os.path.join(study_dir, name)
    if not os.path.isfile(path):
        raise StudyError(f"missing {name}")
    with open(path, "rb") as handle:
        return handle.read()


def _sha256_file(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _load_records(study_dir: str, freeze: dict, path: str) -> list[dict]:
    """Return one results file's records, checking its schema, provenance and report hashes."""
    rel = os.path.relpath(path, study_dir).replace(os.sep, "/")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema_version") != 2:
        raise StudyError(f"{rel}: schema_version must be 2")
    for key in PROVENANCE_KEYS:
        if data.get(key) != freeze:
            raise StudyError(f"{rel}: {key} differs from freeze.json")

    results_dir = os.path.dirname(path)
    records = []
    for record in data.get("cases", []):
        record = dict(record)
        if record.get("report"):
            report_path = os.path.join(results_dir, record["report"])
            if not os.path.isfile(report_path):
                raise StudyError(f"{rel}: missing report {record['report']}")
            if _sha256_file(report_path) != record.get("report_sha256"):
                raise StudyError(f"{rel}: report hash differs for {record['trial_id']}")
            record["report"] = os.path.relpath(os.path.abspath(report_path),
                                               os.path.abspath(study_dir)).replace(os.sep, "/")
        records.append(record)
    return records


def _verify_manifest(study_dir: str) -> str:
    """Check every file of the study against its manifest, with none missing or extra; return the manifest's sha256."""
    manifest = _read_study_file(study_dir, MANIFEST)
    listed = {line[68:]: line[:64] for line in manifest.decode("utf-8").splitlines()}
    present = sorted(
        os.path.relpath(os.path.join(directory, name), study_dir).replace(os.sep, "/")
        for directory, _dirs, names in os.walk(study_dir) for name in names
        if name not in eval_run._SKIPPED_NAMES
    )
    present.remove(MANIFEST)
    if present != sorted(listed):
        raise StudyError("the files of the study differ from its manifest")
    for path in present:
        if _sha256_file(os.path.join(study_dir, path)) != listed[path]:
            raise StudyError(f"manifest hash differs for {path}")
    return hashlib.sha256(manifest).hexdigest()


def _report_text(study_dir: str, record: dict) -> str:
    if not record.get("report"):
        return ""
    with open(os.path.join(study_dir, record["report"]), "rb") as handle:
        return handle.read().decode("utf-8")


def _rescored(study_dir: str, record: dict, cases: dict, controls: dict) -> tuple[dict, list[dict]]:
    """Return ``record`` scored again from its raw report by the current scorer, and the fields that changed.

    Status, error class and exit code are measured, never rescored. Only completeness and what follows from it
    may change: any other scored field that differs (report validity, a finding, a label) refuses the rescore.
    """
    stdout = _report_text(study_dir, record)
    rescored = dict(record)
    if "control" in record:
        checked = eval_run.check_control(controls[record["control"]], stdout, record.get("gate_exit"))
        checks = dict(checked["checks"], worktree_unchanged=record.get("worktree_unchanged"))
        rescored.update(report_valid=checked["report_valid"], complete=checked["complete"], checks=checks,
                        passed=record["status"] == "ok" and all(checks.values()))
    else:
        rescored["report_valid"] = score.looks_like_report(stdout)
        if record["status"] == "ok":
            rescored.update(eval_run.score_case(cases[record["id"]], stdout))

    changes = []
    for field in sorted(set(record) | set(rescored)):
        old, new = record.get(field), rescored.get(field)
        if field == "checks":
            old, new = old or {}, new or {}
            changes += [{"trial_id": record["trial_id"], "attempt": record["attempt"], "field": "checks." + name,
                         "original": old.get(name), "rescored": new.get(name)}
                        for name in sorted(set(old) | set(new)) if old.get(name) != new.get(name)]
        elif old != new:
            changes.append({"trial_id": record["trial_id"], "attempt": record["attempt"], "field": field,
                            "original": old, "rescored": new})
    refused = [change["field"] for change in changes if change["field"] not in RESCORABLE_FIELDS]
    if refused:
        raise StudyError(f"{record['trial_id']}: rescoring changed {', '.join(refused)}; only completeness may change")
    return rescored, changes


def _results_files(study_dir: str) -> list[str]:
    paths = []
    for pattern in RESULTS_GLOBS:
        paths.extend(sorted(glob.glob(os.path.join(study_dir, pattern))))
    return paths


def expected_trials(protocol: dict) -> list[str]:
    """List every trial the protocol plans, in protocol order."""
    trials = []
    for sample in protocol["samples"]:
        for pair in protocol["pairs"]:
            trials.append(f"{sample}/{pair}/bug")
            trials.append(f"{sample}/{pair}/clean")
        for control in protocol["controls"]:
            trials.append(f"{sample}/control/{control}")
    return trials


def _ratio(count: int, total: int) -> str:
    return f"{count}/{total}"


def _pair_metrics(records: list[dict]) -> dict:
    bugs = [record for record in records if record["kind"] == "bug"]
    cleans = [record for record in records if record["kind"] == "clean"]
    detected = sum(1 for record in bugs if record.get("detected") is True)
    false_positive = [
        record for record in cleans
        if record["status"] == "ok" and (record.get("false_positives") or 0) > 0
    ]
    return {
        "bug_trials": len(bugs),
        "detected": detected,
        "recall": round(detected / len(bugs), 3) if bugs else None,
        "clean_trials": len(cleans),
        "complete_clean_no_fp": sum(1 for record in cleans if record.get("passed") is True),
        "false_positive_trials": len(false_positive),
        "false_positive_findings": sum(record["false_positives"] for record in false_positive),
        "incomplete": sum(1 for record in records if record["status"] == "ok" and not record.get("complete")),
        "errors": sum(1 for record in records if record["status"] == "error"),
        "worktree_changed": sum(1 for record in records if record.get("worktree_unchanged") is False),
    }


def _cases(protocol: dict, effective: dict) -> list[dict]:
    cases = []
    for pair in protocol["pairs"]:
        for kind in ("bug", "clean"):
            trials = [effective[f"{sample}/{pair}/{kind}"] for sample in protocol["samples"]]
            observations = [record.get("observations") or {} for record in trials]
            cases.append({
                "id": f"{pair}/{kind}",
                "pair": pair,
                "kind": kind,
                "legacy": pair in protocol["legacy_pairs"],
                "trials": len(trials),
                "errors": sum(1 for record in trials if record["status"] == "error"),
                "complete": sum(1 for record in trials if record.get("complete") is True),
                "passed": sum(1 for record in trials if record.get("passed") is True),
                "detected": sum(1 for record in trials if record.get("detected") is True) if kind == "bug" else None,
                "false_positive_findings": None if kind == "bug" else [
                    record.get("false_positives") for record in trials
                ],
                "observations": {
                    key: sum(1 for entry in observations if entry.get(key) is True)
                    for key in OBSERVATION_KEYS
                },
            })
    return cases


def _controls(records: list[dict]) -> dict:
    by_control = {}
    for name in sorted({record["control"] for record in records}):
        group = [record for record in records if record["control"] == name]
        check_names = sorted({key for record in group for key in record.get("checks") or {}})
        by_control[name] = {
            "trials": len(group),
            "passed": sum(1 for record in group if record.get("passed") is True),
            "errors": sum(1 for record in group if record["status"] == "error"),
            "checks": {
                check: sum(1 for record in group if (record.get("checks") or {}).get(check) is True)
                for check in check_names
            },
        }
    return {
        "trials": len(records),
        "passed": sum(1 for record in records if record.get("passed") is True),
        "errors": sum(1 for record in records if record["status"] == "error"),
        "by_control": by_control,
    }


def build(study_dir: str, rescore: bool = False) -> dict:
    """Validate one study directory and return its aggregate; the result carries no timestamp.

    With ``rescore``, the study must match its manifest and its own ``aggregate.json``; every trial is then
    scored again from its raw report (see ``_rescored``), and the result names the original study, the
    rescoring source and every changed field. The original provenance is kept as it was frozen.
    """
    protocol_bytes = _read_study_file(study_dir, "protocol.json")
    protocol = json.loads(protocol_bytes)
    freeze = json.loads(_read_study_file(study_dir, "freeze.json"))
    if rescore:
        manifest_sha256 = _verify_manifest(study_dir)
        aggregate_bytes = _read_study_file(study_dir, "aggregate.json")
        if json.loads(aggregate_bytes) != build(study_dir):
            raise StudyError("aggregate.json is not the aggregate of the recorded trials")
        cases = {case["id"]: case for case in eval_run.select_cases(
            [pair for pair in eval_run.load_pairs(eval_run.DEFAULT_CASES_DIR) if not pair["errors"]], None)}
        controls = {entry["name"]: entry["control"] for entry in eval_run.load_controls(eval_run.DEFAULT_CONTROLS_DIR)}
    changes = []

    by_id: dict[str, list[dict]] = {}
    for path in _results_files(study_dir):
        for record in _load_records(study_dir, freeze, path):
            if rescore:
                record, changed = _rescored(study_dir, record, cases, controls)
                changes += changed
            by_id.setdefault(record["trial_id"], []).append(record)

    expected = expected_trials(protocol)
    if len(expected) != protocol["planned_trials"]["total"]:
        raise StudyError("planned_trials does not match the inventory")
    unexpected = sorted(set(by_id) - set(expected))
    if unexpected:
        raise StudyError("unexpected trials: " + ", ".join(unexpected))
    missing = [trial for trial in expected if trial not in by_id]
    if missing:
        raise StudyError("missing trials: " + ", ".join(missing))

    max_retries = protocol["max_retries"]
    retryable = protocol["retryable_error_classes"]
    effective = {}
    attempts_total = 0
    retried = []
    for trial in expected:
        records = sorted(by_id[trial], key=lambda record: record["attempt"])
        numbers = [record["attempt"] for record in records]
        if numbers != list(range(1, len(records) + 1)):
            raise StudyError(f"{trial}: attempts must be 1..n once each, found {numbers}")
        if len(records) > 1 + max_retries:
            raise StudyError(f"{trial}: more than {max_retries} retry")
        for number, record in enumerate(records[:-1], start=1):
            if record.get("error_class") not in retryable:
                raise StudyError(
                    f"{trial}: attempt {number} was retried, but its error class "
                    f"{record.get('error_class')!r} is not retryable"
                )
        effective[trial] = records[-1]
        attempts_total += len(records)
        if len(records) > 1:
            retried.append(trial)

    primary_records = [effective[trial] for trial in expected if "control" not in effective[trial]]
    control_records = [effective[trial] for trial in expected if "control" in effective[trial]]
    legacy = set(protocol["legacy_pairs"])
    primary = {
        "overall": _pair_metrics(primary_records),
        "legacy": _pair_metrics([record for record in primary_records if record["pair"] in legacy]),
        "new": _pair_metrics([record for record in primary_records if record["pair"] not in legacy]),
    }

    trial_results = []
    for trial in expected:
        record = effective[trial]
        trial_results.append({
            "trial_id": trial,
            "attempt": record["attempt"],
            "attempts": len(by_id[trial]),
            "status": record.get("status"),
            "error_class": record.get("error_class"),
            "exit_code": record.get("exit_code"),
            "report_valid": record.get("report_valid"),
            "complete": record.get("complete"),
            "detected": record.get("detected"),
            "false_positives": record.get("false_positives"),
            "passed": record.get("passed"),
            "worktree_unchanged": record.get("worktree_unchanged"),
            "duration_s": record.get("duration_s"),
            "report": record.get("report"),
            "report_sha256": record.get("report_sha256"),
        })

    result = {
        "schema_version": 2,
        "kind": "aggregate",
        "study": protocol["study"],
        "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "provenance": freeze,
        "trials": {
            "planned": protocol["planned_trials"],
            "effective": len(effective),
            "attempts": attempts_total,
            "retried": retried,
        },
        "primary": primary,
        "controls": _controls(control_records),
        "cases": _cases(protocol, effective),
        "trial_results": trial_results,
    }
    if rescore:
        result["kind"] = "rescored-aggregate"
        result["original"] = {
            "manifest_sha256": manifest_sha256,
            "aggregate_sha256": hashlib.sha256(aggregate_bytes).hexdigest(),
        }
        result["rescoring"] = {
            "algorithm": RESCORE_ALGORITHM,
            "scorer_sha256": eval_run.file_sha256("evals/score.py"),
            "runner_sha256": eval_run.file_sha256("evals/run.py"),
            "aggregate_sha256": eval_run.file_sha256("evals/aggregate.py"),
        }
        result["changes"] = changes
    return result


def _digest(provenance: dict, key: str) -> str:
    value = provenance.get(key)
    return value[:12] if value else "none"


def _text(provenance: dict, key: str) -> str:
    value = provenance.get(key)
    return str(value) if value is not None else "none"


def summary_markdown(result: dict) -> str:
    """Render the aggregate as the baseline summary page."""
    freeze = result["provenance"]
    trials = result["trials"]
    overall = result["primary"]["overall"]
    legacy = result["primary"]["legacy"]
    new = result["primary"]["new"]
    controls = result["controls"]
    title, rescoring = "# Expanded eval baseline", []
    if result["kind"] == "rescored-aggregate":
        title += ", rescored"
        source = result["rescoring"]
        changed_trials = len({change["trial_id"] for change in result["changes"]})
        rescoring = [
            f"- Rescored without a model call from the raw reports of study {result['study']} (manifest sha256 "
            f"{result['original']['manifest_sha256'][:12]}, original aggregate sha256 "
            f"{result['original']['aggregate_sha256'][:12]})",
            f"- Rescoring {source['algorithm']}: scorer {source['scorer_sha256'][:12]}; runner "
            f"{source['runner_sha256'][:12]}; aggregator {source['aggregate_sha256'][:12]}; "
            f"{len(result['changes'])} field change(s) in {changed_trials} trial(s)",
        ]
    lines = [
        title,
        "",
        *rescoring,
        f"- Study: {result['study']}; protocol sha256 {result['protocol_sha256'][:12]}",
        f"- Skill tree {_digest(freeze, 'skill_tree_sha256')}; runner {_digest(freeze, 'runner_sha256')}; "
        f"scorer {_digest(freeze, 'scorer_sha256')}; cases {_digest(freeze, 'cases_tree_sha256')}; "
        f"controls {_digest(freeze, 'controls_tree_sha256')}; profile {_digest(freeze, 'profile_sha256')}",
        f"- Model: {_text(freeze, 'model')} ({_text(freeze, 'agent_name')}); trials: "
        f"{trials['effective']} effective of {trials['planned']['total']} planned, {trials['attempts']} attempts",
        f"- Recall: {_ratio(overall['detected'], overall['bug_trials'])} overall; "
        f"legacy {_ratio(legacy['detected'], legacy['bug_trials'])}; "
        f"new {_ratio(new['detected'], new['bug_trials'])}",
        "- Clean reviews complete with no Critical/Warning finding: "
        f"{_ratio(overall['complete_clean_no_fp'], overall['clean_trials'])} overall; "
        f"legacy {_ratio(legacy['complete_clean_no_fp'], legacy['clean_trials'])}; "
        f"new {_ratio(new['complete_clean_no_fp'], new['clean_trials'])}",
        f"- False positives: {overall['false_positive_findings']} Critical/Warning finding(s) in "
        f"{_ratio(overall['false_positive_trials'], overall['clean_trials'])} clean trial(s)",
        f"- Incomplete reports: {overall['incomplete']}; errors: {overall['errors']}; "
        f"worktree changes: {overall['worktree_changed']}",
        f"- Controls: {_ratio(controls['passed'], controls['trials'])} passed",
        "",
        "| Case | Legacy | Detected | Clean, no FP | FP findings per sample | Complete | Errors |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in result["cases"]:
        is_bug = case["kind"] == "bug"
        detected = _ratio(case["detected"], case["trials"]) if is_bug else "—"
        clean = "—" if is_bug else _ratio(case["passed"], case["trials"])
        findings = "—" if is_bug else ", ".join(
            "—" if value is None else str(value) for value in case["false_positive_findings"]
        )
        lines.append(
            f"| {case['id']} | {'yes' if case['legacy'] else 'no'} | {detected} | {clean} | {findings} | "
            f"{_ratio(case['complete'], case['trials'])} | {case['errors']} |"
        )
    lines += [
        "",
        "| Control | Passed | Errors | Checks |",
        "| --- | --- | --- | --- |",
    ]
    for name, entry in controls["by_control"].items():
        checks = ", ".join(
            f"{check} {_ratio(count, entry['trials'])}" for check, count in entry["checks"].items()
        ) or "none"
        lines.append(f"| {name} | {_ratio(entry['passed'], entry['trials'])} | {entry['errors']} | {checks} |")
    return "\n".join(lines) + "\n"


def verify_identity(study_dir: str) -> list[str]:
    """Compare the study's frozen provenance with the current source; return one line per difference."""
    freeze = json.loads(_read_study_file(study_dir, "freeze.json"))
    argv = ["--profile", os.path.join(eval_run.REPO_ROOT, freeze["profile"])] if freeze.get("profile") else []
    current = eval_run.provenance(eval_run.resolve_args(argv))
    differences = []
    for key in sorted(set(freeze) | set(current)):
        if key in IDENTITY_SKIP:
            continue
        if freeze.get(key) != current.get(key):
            differences.append(f"{key}: frozen {freeze.get(key)!r}, now {current.get(key)!r}")
    return differences


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate one measured eval study.")
    parser.add_argument("study_dir", metavar="STUDY_DIR")
    parser.add_argument("--json", default=None, metavar="OUT", help="write the aggregate as JSON")
    parser.add_argument("--summary", default=None, metavar="OUT", help="write the summary as Markdown")
    parser.add_argument("--rescore", action="store_true",
                        help="score every trial again from its raw report with the current scorer")
    parser.add_argument("--verify-identity", action="store_true",
                        help="compare the study's freeze.json with the current source and exit")
    args = parser.parse_args(argv)

    if args.verify_identity:
        try:
            differences = verify_identity(args.study_dir)
        except StudyError as exc:
            print(f"study invalid: {exc}")
            return 1
        if not differences:
            print("identity: source, runtime, cases, controls, profile and prompt match freeze.json")
            return 0
        for line in differences:
            print(line)
        return 1

    try:
        result = build(args.study_dir, rescore=args.rescore)
    except StudyError as exc:
        print(f"study invalid: {exc}")
        return 1
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    summary = summary_markdown(result)
    if args.summary:
        with open(args.summary, "w", encoding="utf-8") as handle:
            handle.write(summary)
    sys.stdout.write(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
