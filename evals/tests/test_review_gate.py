"""Offline checks of the --format json contract (references/json-output.md) and its optional consumer, scripts/review_gate.py, against handwritten documents; they do not measure what an agent writes."""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(ROOT, "scripts", "review_gate.py")
FIXTURES = os.path.join(HERE, "fixtures", "json")
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import review_gate  # noqa: E402

NAMES = ("pass", "critical", "incomplete", "error", "nothing-to-review")


def fixture_bytes(name):
    with open(os.path.join(FIXTURES, name + ".json"), "rb") as f:
        return f.read()


def fixture(name):
    return json.loads(fixture_bytes(name))


def run_gate(*args, stdin=b""):
    proc = subprocess.run([sys.executable, SCRIPT, *args], input=stdin, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("utf-8")


class LoadTest(unittest.TestCase):
    def assert_invalid(self, data, message):
        with self.assertRaises(review_gate.GateInputError) as ctx:
            review_gate.load(data)
        self.assertIn(message, str(ctx.exception))

    def test_empty_input_is_never_zero_findings(self):
        self.assert_invalid(b"  \n", "empty input")

    def test_fenced_document_is_invalid(self):
        self.assert_invalid(b"```json\n" + fixture_bytes("pass") + b"```\n", "not a single JSON document")

    def test_prose_after_the_document_is_invalid(self):
        self.assert_invalid(fixture_bytes("pass") + b"\nThe review is done.\n", "not a single JSON document")

    def test_cut_off_document_is_invalid(self):
        data = fixture_bytes("critical")
        self.assert_invalid(data[:len(data) // 2], "not a single JSON document")

    def test_duplicate_key_is_invalid(self):
        self.assert_invalid(b'{"status": "complete", "status": "error"}', 'duplicate key "status"')

    def test_nan_is_invalid(self):
        self.assert_invalid(b'{"version": NaN}', "NaN is not valid JSON")

    def test_array_is_invalid(self):
        self.assert_invalid(b"[]", "the document is not a JSON object")

    def test_non_utf8_is_invalid(self):
        self.assert_invalid(b'{"scope": "\xff"}', "not UTF-8 text")


class ContractTest(unittest.TestCase):
    def assert_error(self, doc, message):
        errors = review_gate.contract_errors(doc)
        self.assertTrue(any(message in e for e in errors), f"{message!r} not in {errors}")

    def test_fixtures_keep_the_contract(self):
        for name in NAMES:
            with self.subTest(name=name):
                self.assertEqual(review_gate.contract_errors(review_gate.load(fixture_bytes(name))), [])

    def test_another_version_is_incompatible(self):
        doc = fixture("pass")
        doc["version"] = 2
        self.assertEqual(review_gate.contract_errors(doc), ["version must be 1; this gate reads only version 1"])

    def test_another_schema_is_incompatible(self):
        doc = fixture("pass")
        doc["schema"] = "other/review"
        self.assertEqual(review_gate.contract_errors(doc), ['schema must be "code-review-skill/review"'])

    def test_missing_key_fails(self):
        doc = fixture("pass")
        del doc["review"]["audit"]
        self.assert_error(doc, "review keys: missing ['audit']")

    def test_critical_hidden_by_a_filter_still_fails_the_gate(self):
        doc = fixture("critical")
        doc["review"]["findings"][0]["omitted_by"] = "disabled_categories"
        self.assert_error(doc, "a Critical finding is never omitted by a filter")
        self.assertEqual(review_gate.expected_gate(doc), "fail")

    def test_omitted_warning_still_counts_for_the_verdict(self):
        doc = fixture("critical")
        del doc["review"]["findings"][0]
        doc["review"]["verification"] = {"checked": 1, "refuted": 0}
        self.assertEqual(review_gate.expected_row(doc["review"]), 4)

    def test_dropping_the_critical_finding_never_passes(self):
        doc = fixture("critical")
        del doc["review"]["findings"][0]
        self.assert_error(doc, "review.verdict row 2 does not match the facts (row 4)")
        self.assertNotEqual(run_gate("-", stdin=json.dumps(doc).encode())[0], 0)

    def test_omitted_finding_needs_the_omitted_line(self):
        doc = fixture("critical")
        doc["review"]["omitted_by_configuration"] = None
        self.assert_error(doc, "review.omitted_by_configuration is null, but a finding is omitted by a filter")

    def test_location_must_match_its_parts(self):
        doc = fixture("critical")
        doc["review"]["findings"][0]["location"] = "src/orders.js:42"
        self.assert_error(doc, "review.findings[0].location must be src/orders.js:42-44")

    def test_grouped_place_is_never_repeated(self):
        doc = fixture("critical")
        doc["review"]["findings"][0]["also_at"] = ["src/orders.js:42-44"]
        self.assert_error(doc, "review.findings[0].also_at repeats a place")

    def test_confidence_follows_the_section(self):
        doc = fixture("pass")
        doc["review"]["needs_verification"] = [copy.deepcopy(doc["review"]["findings"][0])]
        self.assert_error(doc, 'review.needs_verification[0].confidence must be "Medium"')

    def test_unrefuted_candidates_cover_the_findings(self):
        doc = fixture("critical")
        doc["review"]["verification"] = {"checked": 1, "refuted": 1}
        self.assert_error(doc, "review.verification leaves 0 unrefuted candidates, but 2 Critical or Warning "
                               "findings are reported")

    def test_gate_claim_must_match_the_facts(self):
        doc = fixture("pass")
        doc["gate"]["status"] = "fail"
        self.assert_error(doc, 'gate status "fail" does not match the facts ("pass")')

    def test_json_output_guide_is_read_for_context(self):
        doc = fixture("pass")
        doc["review"]["audit"]["read_for_context"].remove("skill:references/json-output.md")
        self.assert_error(doc, "review.audit.read_for_context must list skill:references/json-output.md")

    def test_material_limit_makes_the_review_incomplete(self):
        doc = fixture("incomplete")
        doc["review"]["audit"]["not_verified"][0]["material"] = False
        self.assert_error(doc, "review.verdict row 3 does not match the facts (row 7)")

    def test_unverified_critical_never_fails_the_gate(self):
        doc = fixture("pass")
        unverified = copy.deepcopy(doc["review"]["findings"][0])
        unverified.update(severity="Critical", confidence="Medium", category="Security")
        doc["review"]["needs_verification"] = [unverified]
        doc["review"]["verification"] = {"checked": 2, "refuted": 1}
        doc["review"]["verdict"] = {"ready_to_merge": "With fixes", "row": 5}
        doc["review"]["triage"]["ready_to_merge"] = ("With fixes — a person must check 1 finding under Needs human "
                                                     "verification before merging.")
        self.assertEqual(review_gate.contract_errors(doc), [])
        self.assertEqual(review_gate.expected_gate(doc), "pass")

    def test_unverified_critical_with_a_material_limit_is_incomplete(self):
        doc = fixture("pass")
        unverified = copy.deepcopy(doc["review"]["findings"][0])
        unverified.update(severity="Critical", confidence="Medium", category="Security")
        doc["review"]["needs_verification"] = [unverified]
        doc["review"]["verification"] = {"checked": 2, "refuted": 1}
        doc["review"]["audit"]["not_verified"] = [
            {"what": "the authorization check of `/cart/export`", "tag": "context not read", "material": True,
             "detail": "the head commit is not in this repository, so the middleware that guards the route was not "
                       "read."}]
        doc["review"]["verdict"] = {"ready_to_merge": "No", "row": 3}
        doc["review"]["triage"]["ready_to_merge"] = ("No — not fully reviewed (context not read): the authorization "
                                                     "check of `/cart/export`.")
        doc["gate"] = {"fail_on": "critical", "status": "incomplete",
                       "reason": "not fully reviewed (context not read): the authorization check of `/cart/export`."}
        self.assertEqual(review_gate.contract_errors(doc), [])
        self.assertEqual(run_gate("-", stdin=json.dumps(doc).encode())[0], 2)

    def test_error_document_has_no_review(self):
        doc = fixture("error")
        doc["review"] = fixture("pass")["review"]
        self.assert_error(doc, "review must be null when status is error")

    def test_error_message_is_the_cannot_review_line(self):
        doc = fixture("error")
        doc["message"] = "Something went wrong."
        self.assert_error(doc, "message must be the Cannot review line when status is error")


class ExitStatusTest(unittest.TestCase):
    """Runs the consumer as a CI job would and checks the exit status it really returns."""

    def test_documented_exit_statuses(self):
        expected = {"pass": (0, "review-gate: pass: complete review with no verified Critical finding"),
                    "critical": (1, "review-gate: fail: 1 verified Critical finding"),
                    "incomplete": (2, "review-gate: incomplete: not fully reviewed (not read): "),
                    "error": (2, "review-gate: error: Cannot review: --comment cannot be combined with --format json"),
                    "nothing-to-review": (0, "review-gate: pass: nothing to review")}
        for name, (status, line) in expected.items():
            with self.subTest(name=name):
                code, out = run_gate(os.path.join(FIXTURES, name + ".json"))
                self.assertEqual(code, status, out)
                self.assertTrue(out.startswith(line), out)

    def test_stdin_is_read_with_a_dash(self):
        self.assertEqual(run_gate("-", stdin=fixture_bytes("critical"))[0], 1)

    def test_empty_input_exits_3(self):
        code, out = run_gate("-", stdin=b"")
        self.assertEqual((code, out), (3, "review-gate: invalid: empty input: no JSON document\n"))

    def test_missing_file_exits_3(self):
        code, out = run_gate(os.path.join(FIXTURES, "missing.json"))
        self.assertEqual(code, 3)
        self.assertTrue(out.startswith("review-gate: invalid: cannot read "), out)

    def test_contract_violation_exits_3(self):
        doc = fixture("critical")
        doc["review"]["findings"][0]["omitted_by"] = "disabled_categories"
        code, out = run_gate("-", stdin=json.dumps(doc).encode())
        self.assertEqual(code, 3)
        self.assertIn("a Critical finding is never omitted by a filter", out)

    def test_review_without_a_gate_exits_3(self):
        doc = fixture("pass")
        doc["gate"] = {"fail_on": None, "status": "not_requested", "reason": "no gate was requested"}
        self.assertEqual(run_gate("-", stdin=json.dumps(doc).encode()),
                         (3, "review-gate: invalid: the review was not run with --fail-on critical\n"))

    def test_error_without_a_gate_still_exits_2(self):
        doc = fixture("error")
        doc["gate"] = {"fail_on": None, "status": "error", "reason": doc["message"]}
        self.assertEqual(run_gate("-", stdin=json.dumps(doc).encode())[0], 2)

    def test_two_arguments_exit_3(self):
        self.assertEqual(run_gate("a.json", "b.json")[0], 3)


class FileAccountingTest(unittest.TestCase):
    """SKILL.md Audit: the reviewed, excluded, binary and whole-file unread files add up to the changed files."""

    def assert_only_error(self, doc, message):
        self.assertEqual(review_gate.contract_errors(doc), [message])
        self.assertEqual(run_gate("-", stdin=json.dumps(doc).encode()), (3, f"review-gate: invalid: {message}\n"))

    def assert_gate(self, doc, status, code):
        self.assertEqual(review_gate.contract_errors(doc), [])
        self.assertEqual(review_gate.expected_gate(doc), status)
        self.assertEqual(run_gate("-", stdin=json.dumps(doc).encode())[0], code)

    def test_unaccounted_changed_file_is_invalid(self):
        doc = fixture("pass")
        doc["review"]["audit"]["files_reviewed"]["changed"] = 2
        self.assert_only_error(doc, "review.audit.files_reviewed: 1 reviewed + 0 excluded by configuration + 0 binary "
                                    "+ 0 not read as a whole make 1, not the 2 changed files")

    def test_files_excluded_by_configuration_pass(self):
        doc = fixture("pass")
        review = doc["review"]
        review["context_lines"] = [
            "**Configuration:** `.code-review/config.yml`.",
            "**Excluded by configuration:** 2 changed files match ignore_paths and were not reviewed: "
            "`docs/setup.md`, `src/generated/client.ts`."]
        review["audit"]["files_reviewed"]["changed"] = 3
        review["audit"]["read_for_context"] = [".code-review/config.yml", "skill:references/configuration.md",
                                               "skill:references/intent.md", "skill:references/json-output.md",
                                               "tests/cart.test.js"]
        review["triage"]["ready_to_merge"] += " 2 changed files excluded by configuration were not reviewed."
        self.assert_gate(doc, "pass", 0)

    def test_nonmaterial_whole_file_omission_passes(self):
        doc = fixture("pass")
        doc["review"]["audit"]["files_reviewed"]["changed"] = 2
        doc["review"]["audit"]["not_verified"] = [
            {"what": "`CHANGELOG.md` (whole file)", "tag": "not read", "material": False,
             "detail": "the file could not be opened; it is the changelog, which holds no behavior."}]
        self.assert_gate(doc, "pass", 0)

    def test_nonmaterial_binary_file_passes(self):
        doc = fixture("pass")
        doc["review"]["audit"]["files_reviewed"]["changed"] = 2
        doc["review"]["audit"]["not_verified"] = [
            {"what": "`assets/cart.png`", "tag": "binary", "material": False,
             "detail": "a changed image; no changed behavior depends on it."}]
        self.assert_gate(doc, "pass", 0)

    def test_material_unread_file_is_incomplete(self):
        doc = fixture("pass")
        review = doc["review"]
        review["audit"]["files_reviewed"]["changed"] = 2
        review["audit"]["not_verified"] = [
            {"what": "`src/checkout.js` (whole file)", "tag": "not read", "material": True,
             "detail": "the file could not be opened, and `src/cart.js` calls its changed `checkout()`."}]
        review["verdict"] = {"ready_to_merge": "No", "row": 3}
        review["triage"]["ready_to_merge"] = "No — not fully reviewed (not read): `src/checkout.js` (whole file)."
        doc["gate"] = {"fail_on": "critical", "status": "incomplete",
                       "reason": "not fully reviewed (not read): `src/checkout.js` (whole file)."}
        self.assert_gate(doc, "incomplete", 2)

    def test_partly_read_file_is_counted_once(self):
        self.assert_gate(fixture("incomplete"), "incomplete", 2)
        doc = fixture("incomplete")
        doc["review"]["audit"]["not_verified"][0]["what"] = "`src/routes.js` (whole file)"
        self.assert_only_error(doc, "review.audit counts src/routes.js more than once among the reviewed, excluded, "
                                    "binary and whole-file unread files")

    def test_unread_lines_belong_to_a_reviewed_file(self):
        doc = fixture("incomplete")
        doc["review"]["audit"]["not_verified"][0]["what"] = "`src/other.js` lines 40-90"
        self.assert_only_error(doc, "review.audit.not_verified[0]: `src/other.js` lines 40-90 are unread lines of a "
                                    "file that is not reviewed")

    def test_not_read_item_names_its_file(self):
        doc = fixture("incomplete")
        doc["review"]["audit"]["not_verified"][0]["what"] = "the end of the diff"
        self.assert_only_error(doc, "review.audit.not_verified[0].what of a not read item must be `<path>` (whole "
                                    "file) or `<path>` lines <a>-<b>")

    def test_excluded_line_counts_what_it_lists(self):
        doc = fixture("pass")
        doc["review"]["context_lines"] = [
            "**Excluded by configuration:** 2 changed files match ignore_paths and were not reviewed: `docs/setup.md`."]
        doc["review"]["audit"]["files_reviewed"]["changed"] = 3
        self.assert_only_error(doc, "review.context_lines: the **Excluded by configuration:** line counts 2 files and "
                                    "lists 1")

    def test_changed_file_read_for_context_is_invalid(self):
        doc = fixture("pass")
        doc["review"]["audit"]["read_for_context"] = ["skill:references/intent.md", "skill:references/json-output.md",
                                                      "src/cart.js", "tests/cart.test.js"]
        self.assert_only_error(doc, "review.audit.read_for_context lists a changed file: src/cart.js")


def json_paths(value, path=()):
    yield path
    if isinstance(value, dict):
        for key, item in value.items():
            yield from json_paths(item, path + (key,))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from json_paths(item, path + (i,))


class MalformedInputTest(unittest.TestCase):
    """A value of the wrong type is invalid input (exit 3), never a crash of the consumer."""

    def test_object_in_read_for_context_exits_3(self):
        doc = fixture("pass")
        doc["review"]["audit"]["read_for_context"] = [{}]
        self.assertEqual(run_gate("-", stdin=json.dumps(doc).encode()),
                         (3, "review-gate: invalid: review.audit.read_for_context must be a list of non-empty strings\n"))

    def test_object_in_reviewed_paths_exits_3(self):
        doc = fixture("pass")
        doc["review"]["audit"]["files_reviewed"]["paths"] = [{}]
        self.assertEqual(run_gate("-", stdin=json.dumps(doc).encode()),
                         (3, "review-gate: invalid: review.audit.files_reviewed.paths must list each reviewed path once\n"))

    def test_well_typed_control_exits_0(self):
        self.assertEqual(run_gate("-", stdin=json.dumps(fixture("pass")).encode()),
                         (0, "review-gate: pass: complete review with no verified Critical finding\n"))

    def test_deep_nesting_exits_3(self):
        code, out = run_gate("-", stdin=b'{"review": ' + b"[" * 100000 + b"]" * 100000 + b"}")
        self.assertEqual(code, 3)
        self.assertTrue(out.startswith("review-gate: invalid: "), out)

    def test_long_number_exits_3(self):
        code, out = run_gate("-", stdin=b'{"version": ' + b"1" * 5000 + b"}")
        self.assertEqual(code, 3)
        self.assertTrue(out.startswith("review-gate: invalid: "), out)

    def test_a_wrong_type_anywhere_is_reported_never_raised(self):
        for name in NAMES:
            base = fixture(name)
            for path in list(json_paths(base))[1:]:
                for wrong in ({}, [], [{}], None, 0, "x"):
                    doc = copy.deepcopy(base)
                    parent = doc
                    for key in path[:-1]:
                        parent = parent[key]
                    parent[path[-1]] = copy.deepcopy(wrong)
                    with self.subTest(name=name, path=path, wrong=wrong):
                        if not review_gate.contract_errors(doc):
                            review_gate.expected_gate(doc)


if __name__ == "__main__":
    unittest.main()
