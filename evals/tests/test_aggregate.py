import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
EVALS = os.path.dirname(HERE)
AGGREGATE = os.path.join(EVALS, "aggregate.py")
BASELINE = os.path.join(EVALS, "baseline.json")
BASELINE_SHA256 = "ca33dc8c7c74757a642bf2ddd584ea37a7f579f412364c00f834cb337f84918a"

sys.path.insert(0, EVALS)
import aggregate  # noqa: E402
import run as eval_run  # noqa: E402

PROTOCOL = {
    "study": "t",
    "samples": ["s1", "s2"],
    "pairs": ["p1", "p2"],
    "legacy_pairs": ["p1"],
    "controls": ["c1"],
    "planned_trials": {"primary": 8, "controls": 2, "total": 10},
    "max_retries": 1,
    "retryable_error_classes": ["infrastructure"],
}
FREEZE = {"commit": "abc", "model": "m"}


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pair_record(tid, pair, kind, **over):
    """A bug or clean trial record shaped like the records run.py writes."""
    record = {
        "trial_id": tid,
        "pair": pair,
        "kind": kind,
        "status": "ok",
        "error_class": None,
        "attempt": 1,
        "complete": True,
        "report_valid": True,
        "worktree_unchanged": True,
        "exit_code": 0,
        "duration_s": 1.0,
        "observations": {"intent_line": True, "spec_cited": None, "history_cited": None},
        "report": f"reports/{pair}__{kind}.md",
        "report_sha256": sha256_text(f"report {tid}"),
    }
    if kind == "bug":
        record.update(detected=over.pop("detected"), false_positives=None)
        record["passed"] = record["detected"]
    else:
        record.update(detected=None, false_positives=over.pop("false_positives"))
        record["passed"] = record["false_positives"] == 0
    record.update(over)
    return record


def control_record(tid, passed):
    """A behavior control record: one check, named after the control."""
    name = tid.rsplit("/", 1)[-1]
    return {
        "trial_id": tid,
        "id": "control/" + name,
        "control": name,
        "status": "ok",
        "error_class": None,
        "attempt": 1,
        "passed": passed,
        "checks": {"a": passed},
        "worktree_unchanged": True,
        "exit_code": 0,
        "duration_s": 1.0,
    }


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def write_results(directory, kind, records):
    """Write one results.json and the report file of each record, relative to it."""
    for record in records:
        if record.get("report"):
            path = os.path.join(directory, record["report"])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(f"report {record['trial_id']}")
    write_json(os.path.join(directory, "results.json"), {
        "schema_version": 2,
        "kind": kind,
        "provenance": FREEZE,
        "provenance_after": FREEZE,
        "cases": records,
    })


def base_records():
    return [
        pair_record("s1/p1/bug", "p1", "bug", detected=True),
        pair_record("s1/p1/clean", "p1", "clean", false_positives=0),
        pair_record("s1/p2/bug", "p2", "bug", detected=True),
        pair_record("s1/p2/clean", "p2", "clean", false_positives=0),
        control_record("s1/control/c1", True),
        pair_record("s2/p1/bug", "p1", "bug", detected=False),
        pair_record("s2/p1/clean", "p1", "clean", false_positives=1),
        pair_record("s2/p2/bug", "p2", "bug", detected=True),
        pair_record("s2/p2/clean", "p2", "clean", false_positives=0),
        control_record("s2/control/c1", False),
    ]


def write_study(root, records, retries=()):
    """Write a study: protocol, freeze, per-sample results, controls and retries."""
    write_json(os.path.join(root, "protocol.json"), PROTOCOL)
    write_json(os.path.join(root, "freeze.json"), FREEZE)
    groups = {}
    for record in records:
        sample = record["trial_id"].split("/", 1)[0]
        kind = "controls" if "control" in record else "samples"
        groups.setdefault((kind, sample), []).append(record)
    for (kind, sample), group in groups.items():
        write_results(os.path.join(root, kind, sample), "study", group)
    for record in retries:
        sample, rest = record["trial_id"].split("/", 1)
        slug = rest.replace("/", "__")
        write_results(os.path.join(root, "retries", sample, slug), "retry", [record])


class StudyTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.study = os.path.join(self.root, "study")
        write_study(self.study, base_records())

    def retried_study(self, error_class):
        """The base study with s1/p1/bug failing once, then retried to a detection."""
        records = base_records()
        records[0] = pair_record("s1/p1/bug", "p1", "bug", detected=False, status="error",
                                 error_class=error_class)
        retry = pair_record("s1/p1/bug", "p1", "bug", detected=True, attempt=2)
        study = os.path.join(self.root, "retried")
        write_study(study, records, retries=[retry])
        return study


class MetricsTest(StudyTest):
    def test_metrics_of_a_complete_study(self):
        result = aggregate.build(self.study)
        self.assertEqual(result["primary"]["overall"], {
            "bug_trials": 4, "detected": 3, "recall": 0.75, "clean_trials": 4, "complete_clean_no_fp": 3,
            "false_positive_trials": 1, "false_positive_findings": 1, "incomplete": 0, "errors": 0,
            "worktree_changed": 0,
        })
        self.assertEqual(result["primary"]["legacy"]["detected"], 1)
        self.assertEqual(result["primary"]["new"]["detected"], 2)
        self.assertEqual(result["controls"]["by_control"]["c1"],
                         {"trials": 2, "passed": 1, "errors": 0, "checks": {"a": 1}})
        self.assertEqual(result["trials"], {
            "planned": PROTOCOL["planned_trials"], "effective": 10, "attempts": 10, "retried": [],
        })
        case = next(entry for entry in result["cases"] if entry["id"] == "p1/clean")
        self.assertEqual(case["false_positive_findings"], [0, 1])

    def test_missing_trial_is_invalid(self):
        records = [record for record in base_records() if record["trial_id"] != "s2/p2/clean"]
        study = os.path.join(self.root, "partial")
        write_study(study, records)
        with self.assertRaises(aggregate.StudyError) as context:
            aggregate.build(study)
        self.assertEqual(str(context.exception), "missing trials: s2/p2/clean")

    def test_changed_report_is_invalid(self):
        with open(os.path.join(self.study, "samples", "s1", "reports", "p1__bug.md"), "a",
                  encoding="utf-8") as handle:
            handle.write("\nedited after the run\n")
        with self.assertRaisesRegex(aggregate.StudyError, "report hash differs"):
            aggregate.build(self.study)

    def test_infrastructure_retry_replaces_the_first_attempt(self):
        result = aggregate.build(self.retried_study("infrastructure"))
        self.assertEqual(result["primary"]["overall"]["detected"], 3)
        self.assertEqual(result["trials"]["retried"], ["s1/p1/bug"])
        self.assertEqual(result["trials"]["attempts"], 11)
        entry = next(item for item in result["trial_results"] if item["trial_id"] == "s1/p1/bug")
        self.assertEqual((entry["attempt"], entry["attempts"], entry["status"]), (2, 2, "ok"))

    def test_retry_of_a_measured_failure_is_invalid(self):
        with self.assertRaisesRegex(aggregate.StudyError, "is not retryable"):
            aggregate.build(self.retried_study("format"))

    def test_provenance_change_is_invalid(self):
        path = os.path.join(self.study, "samples", "s1", "results.json")
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        data["provenance_after"] = {"commit": "abc", "model": "x"}
        write_json(path, data)
        with self.assertRaisesRegex(aggregate.StudyError, "provenance_after differs from freeze.json"):
            aggregate.build(self.study)

    def test_cli_writes_json_and_summary(self):
        json_out = os.path.join(self.root, "out.json")
        summary_out = os.path.join(self.root, "summary.md")
        proc = subprocess.run(
            [sys.executable, AGGREGATE, self.study, "--json", json_out, "--summary", summary_out],
            cwd=self.root, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(summary_out, encoding="utf-8") as handle:
            summary = handle.read()
        self.assertIn("- Recall: 3/4 overall; legacy 1/2; new 2/2", summary)
        self.assertIn("- Controls: 1/2 passed", summary)
        with open(json_out, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), aggregate.build(self.study))

        os.remove(os.path.join(self.study, "freeze.json"))
        proc = subprocess.run([sys.executable, AGGREGATE, self.study], cwd=self.root,
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 1)
        self.assertTrue(proc.stdout.startswith("study invalid:"), proc.stdout)


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.study = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.study, True)

    def test_verify_identity_matches_current_source(self):
        freeze = eval_run.provenance(eval_run.resolve_args([]))
        write_json(os.path.join(self.study, "freeze.json"), freeze)
        self.assertEqual(aggregate.verify_identity(self.study), [])

        freeze["runner_sha256"] = "0"
        write_json(os.path.join(self.study, "freeze.json"), freeze)
        differences = aggregate.verify_identity(self.study)
        self.assertEqual(len(differences), 1)
        self.assertTrue(differences[0].startswith("runner_sha256:"), differences[0])


class CommittedBaselineTest(unittest.TestCase):
    def test_committed_baseline_matches_its_study(self):
        study = os.path.join(EVALS, "baseline", "expanded")
        if not os.path.exists(os.path.join(study, "freeze.json")):
            with open(BASELINE, "rb") as handle:
                self.assertEqual(hashlib.sha256(handle.read()).hexdigest(), BASELINE_SHA256)
            return
        with open(BASELINE, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), aggregate.build(study))


ORIGINAL_STUDY = os.path.join(EVALS, "baseline", "expanded")
ORIGINAL_MANIFEST_SHA256 = "8804c7567dace5b2a16c0826eadf5de007120d97b0deb8a9b4fc89e12df86557"
I1_TRIALS = ["s2/elapsed-timer-react/clean", "s3/elapsed-timer-react/clean", "s3/sqli-laravel/clean"]


class RescoreTest(unittest.TestCase):
    def copy_original(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        study = os.path.join(root, "expanded")
        shutil.copytree(ORIGINAL_STUDY, study)
        return study

    def test_rescore_of_the_original_study_changes_only_completeness(self):
        result = aggregate.build(ORIGINAL_STUDY, rescore=True)
        self.assertEqual(result["kind"], "rescored-aggregate")
        self.assertEqual(result["original"]["manifest_sha256"], ORIGINAL_MANIFEST_SHA256)
        with open(os.path.join(ORIGINAL_STUDY, "freeze.json"), encoding="utf-8") as handle:
            self.assertEqual(result["provenance"], json.load(handle))
        self.assertEqual(result["rescoring"]["algorithm"], "completeness-v2")
        self.assertEqual(result["rescoring"]["scorer_sha256"], eval_run.file_sha256("evals/score.py"))
        changes = result["changes"]
        self.assertTrue(changes)
        for change in changes:
            with self.subTest(change=change):
                self.assertIn(change["field"], aggregate.RESCORABLE_FIELDS)
                self.assertEqual((change["original"], change["rescored"]), (True, False))
        changed = {(change["trial_id"], change["field"]) for change in changes}
        for trial in I1_TRIALS:
            self.assertIn((trial, "complete"), changed)
            self.assertIn((trial, "passed"), changed)

    def test_rescore_refuses_a_study_without_a_manifest(self):
        study = self.copy_original()
        os.remove(os.path.join(study, "manifest-sha256.txt"))
        with self.assertRaisesRegex(aggregate.StudyError, "missing manifest-sha256.txt"):
            aggregate.build(study, rescore=True)

    def test_rescore_refuses_a_file_changed_after_its_manifest(self):
        study = self.copy_original()
        with open(os.path.join(study, "env.txt"), "a", encoding="utf-8") as handle:
            handle.write("edited after the manifest\n")
        with self.assertRaisesRegex(aggregate.StudyError, "manifest hash differs for env.txt"):
            aggregate.build(study, rescore=True)

    def test_rescore_refuses_a_change_outside_completeness(self):
        real = eval_run.score_case

        def drifted(case, stdout):
            fields = real(case, stdout)
            if case["kind"] == "clean":
                fields["false_positives"] = 7
            return fields

        with mock.patch.object(eval_run, "score_case", side_effect=drifted):
            with self.assertRaisesRegex(aggregate.StudyError, "rescoring changed false_positives"):
                aggregate.build(ORIGINAL_STUDY, rescore=True)

    def test_cli_rescore_writes_json_and_summary(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        json_out = os.path.join(root, "aggregate.json")
        summary_out = os.path.join(root, "summary.md")
        proc = subprocess.run(
            [sys.executable, AGGREGATE, "--rescore", ORIGINAL_STUDY, "--json", json_out, "--summary", summary_out],
            cwd=root, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(json_out, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), aggregate.build(ORIGINAL_STUDY, rescore=True))
        with open(summary_out, encoding="utf-8") as handle:
            summary = handle.read()
        self.assertTrue(summary.startswith("# Expanded eval baseline, rescored\n"), summary)
        self.assertIn("- Rescored without a model call from the raw reports of study expanded (manifest sha256 "
                      + ORIGINAL_MANIFEST_SHA256[:12], summary)


if __name__ == "__main__":
    unittest.main()
