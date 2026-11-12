"""JSON v2 behavior tests; v1 fixtures remain unchanged historical contracts."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import review_gate


def document(severity='Warning', blocking=True, confidence='High'):
    doc = json.loads((ROOT / 'evals/tests/fixtures/json/critical.json').read_text())
    doc['version'] = 2
    finding = copy.deepcopy(doc['review']['findings'][1])
    finding.update(severity=severity, confidence=confidence, blocking=blocking, omitted_by=None)
    review = doc['review']
    review['findings'] = [finding] if confidence == 'High' else []
    review['needs_verification'] = [finding] if confidence == 'Medium' else []
    review['verification'] = {'checked': 1, 'refuted': 0}
    review['omitted_by_configuration'] = None
    row = 5 if confidence == 'Medium' else 2 if severity == 'Critical' else 8 if blocking else 4
    review['verdict'] = {'row': row, 'ready_to_merge': 'No' if row in (2, 8) else 'With fixes'}
    review['triage']['ready_to_merge'] = review['verdict']['ready_to_merge'] + ' — the verified impact decides readiness.'
    doc['gate'] = {'fail_on': 'blocking', 'status': 'incomplete' if row == 5 else 'fail' if blocking else 'pass', 'reason': 'test'}
    return doc


class BlockingGateTest(unittest.TestCase):
    def errors(self, doc):
        return review_gate.contract_errors(doc)

    def test_warning_can_block_without_becoming_critical(self):
        doc = document()
        self.assertEqual(self.errors(doc), [])
        self.assertEqual(review_gate.expected_gate(doc), 'fail')

    def test_nonblocking_warning_passes_blocking_threshold(self):
        self.assertEqual(self.errors(document(blocking=False)), [])

    def test_critical_threshold_keeps_its_explicit_meaning(self):
        doc = document()
        doc['gate'].update(fail_on='critical', status='pass')
        self.assertEqual(self.errors(doc), [])

    def test_pending_warning_never_passes_blocking_gate(self):
        self.assertEqual(self.errors(document(blocking=False, confidence='Medium')), [])

    def test_critical_cannot_be_marked_nonblocking(self):
        self.assertTrue(any('Critical finding must block' in x for x in self.errors(document('Critical', False))))

    def test_suggestion_cannot_block(self):
        self.assertTrue(any('Suggestion cannot block' in x for x in self.errors(document('Suggestion', True))))

    def test_medium_confidence_cannot_claim_confirmed_blocker(self):
        self.assertTrue(any('Medium-confidence finding cannot block' in x for x in self.errors(document(confidence='Medium'))))

    def test_blocking_is_boolean_not_truthy_string(self):
        doc = document()
        doc['review']['findings'][0]['blocking'] = 'false'
        self.assertTrue(any('blocking must be a boolean' in x for x in self.errors(doc)))

    def test_missing_blocking_is_invalid_in_v2(self):
        doc = document()
        del doc['review']['findings'][0]['blocking']
        self.assertTrue(any("missing ['blocking']" in x for x in self.errors(doc)))

    def test_blocker_cannot_be_hidden_by_filter(self):
        for field in review_gate.FILTERS:
            doc = document()
            doc['review']['findings'][0]['omitted_by'] = field
            doc['review']['omitted_by_configuration'] = 'one omitted'
            self.assertTrue(any('blocking finding is never omitted' in x for x in self.errors(doc)))

    def test_claiming_ready_with_blocker_is_rejected(self):
        doc = document()
        doc['review']['verdict'] = {'row': 4, 'ready_to_merge': 'With fixes'}
        doc['review']['triage']['ready_to_merge'] = 'With fixes — none blocks.'
        self.assertTrue(any('does not match the facts (row 8)' in x for x in self.errors(doc)))

    def test_unavailable_execution_only_blocks_when_material(self):
        doc = document(blocking=False)
        doc['review']['audit']['not_verified'] = [{'what': 'integration not run', 'tag': 'tests not verified', 'material': True, 'detail': 'required runtime absent'}]
        doc['review']['verdict'] = {'row': 3, 'ready_to_merge': 'No'}
        doc['review']['triage']['ready_to_merge'] = 'No — not fully reviewed.'
        doc['gate']['status'] = 'incomplete'
        self.assertEqual(self.errors(doc), [])

    def test_v1_rejects_new_threshold_instead_of_silently_passing(self):
        doc = document(blocking=False)
        doc['version'] = 1
        del doc['review']['findings'][0]['blocking']
        self.assertTrue(self.errors(doc))

    def test_known_blocker_still_fails_when_another_area_is_unverified(self):
        doc = document()
        doc['review']['audit']['not_verified'] = [{'what': 'integration', 'tag': 'tests not verified', 'material': True, 'detail': 'dependency unavailable'}]
        doc['review']['verdict'] = {'row': 3, 'ready_to_merge': 'No'}
        doc['gate']['status'] = 'fail'
        self.assertEqual(review_gate.expected_gate(doc), 'fail')
        self.assertEqual(self.errors(doc), [])

    def test_nonblocking_warning_cannot_mask_pending_candidate(self):
        doc = document(blocking=False)
        pending = copy.deepcopy(doc['review']['findings'][0])
        pending['confidence'] = 'Medium'
        doc['review']['needs_verification'] = [pending]
        doc['review']['verification']['checked'] = 2
        doc['gate']['status'] = 'incomplete'
        self.assertEqual(review_gate.expected_gate(doc), 'incomplete')
        self.assertEqual(self.errors(doc), [])

    def test_nonblocking_warning_cannot_mask_open_candidate(self):
        doc = document(blocking=False)
        doc['review']['audit']['already_raised_not_verified'] = [{'location': 'src/report.js:17', 'category': 'Potential Bugs'}]
        doc['gate']['status'] = 'incomplete'
        self.assertEqual(review_gate.expected_gate(doc), 'incomplete')
        self.assertEqual(self.errors(doc), [])

    def test_cli_returns_failure_for_blocking_warning(self):
        import subprocess
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/review_gate.py'), '-'], input=json.dumps(document()), text=True, capture_output=True)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('review-gate: fail:', result.stdout)
