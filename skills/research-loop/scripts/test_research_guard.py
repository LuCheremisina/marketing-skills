"""Synthetic regression scenarios; no real client data."""
import copy
import tempfile
import unittest
from pathlib import Path
from research_guard import validate_result, atomic_checkpoint


def fixture(state='ACTIVE', eligibility='NO', route='ACTIVE_CLIENT'):
    return {'research_result': {'workflow': {'name': 'RESEARCH-LOOP-001', 'version': '1.0'}, 'client': dict(company='Synthetic', legal_entity='UNKNOWN', contacts=[], website='UNKNOWN', crm_ids={}), 'relationship': dict(first_known_contact='UNKNOWN', projects=[], purchases=[], key_events=[], last_meaningful_interaction='UNKNOWN'), 'stop_reason': dict(status='UNKNOWN', reason='UNKNOWN', evidence=[]), 'current_context': dict(active_projects=[], recent_changes=[], open_commitments=[]), 'client_state': dict(status=state, confidence=.95, evidence=['E1']), 'reactivation_eligibility': dict(status=eligibility, reason='Synthetic scenario', evidence=['E1']), 'facts': [dict(claim='Synthetic fact', confidence=.95, evidence=['E1'])], 'evidence_registry': [dict(id='E1', source='fixture', reference='record-1', date='2026-01-01', fact='Synthetic fact')], 'conflicts': [], 'gaps': [], 'sources_checked': [], 'source_selection_log': [], 'verify': {}, 'research_quality': dict(iterations=1, evidence_coverage=1, unresolved_high_priority_gaps=[], loop_stop_reason='DATA_SUFFICIENT'), 'routing': dict(next_process=route, reason='Synthetic'), 'result': 'PASS'}}


class GuardTests(unittest.TestCase):
    def test_valid_routes(self):
        for args in [('ACTIVE','NO','ACTIVE_CLIENT'), ('DORMANT','YES','OPPORTUNITY'), ('LOST','YES','OPPORTUNITY'), ('COMPLETED','YES','OPPORTUNITY'), ('PROSPECT_ONLY','NO','PROSPECT_SALES')]:
            validate_result(fixture(*args))
        for state in ['UNKNOWN', 'CONFLICT']:
            doc = fixture(state, 'HUMAN_REVIEW', 'HUMAN_REVIEW')
            doc['research_result']['result'] = 'HUMAN_REVIEW'
            validate_result(doc)

    def test_invalid_routes(self):
        for args in [('ACTIVE','YES','OPPORTUNITY'), ('UNKNOWN','YES','OPPORTUNITY'), ('PROSPECT_ONLY','YES','OPPORTUNITY')]:
            with self.assertRaises(ValueError):
                validate_result(fixture(*args))

    def test_critical_gaps_and_ban(self):
        doc = fixture('DORMANT','YES','OPPORTUNITY')
        doc['research_result']['gaps'] = [dict(fact='Unknown active process', affects_decision=True)]
        with self.assertRaises(ValueError):
            validate_result(doc)
        doc['research_result']['gaps'] = []
        doc['research_result']['current_context']['human_restrictions'] = ['Do not contact']
        with self.assertRaises(ValueError):
            validate_result(doc)

    def test_broken_evidence(self):
        doc = fixture()
        doc['research_result']['facts'][0]['evidence'] = ['missing']
        with self.assertRaises(ValueError):
            validate_result(doc)

    def test_atomic_checkpoint_and_limits(self):
        c = dict(workflow='RESEARCH-LOOP-001', version='1.0', client_id='synthetic', iteration=1, status='RUNNING', sources_checked=[], known_facts=[], gaps=[], conflicts=[], client_state={}, reactivation_eligibility={}, next_step=dict(uncertainty='payment', source='finance', purpose='confirm'), retry_count={}, updated_at='2026-01-01T00:00:00Z')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'checkpoint.json'
            atomic_checkpoint(c, target)
            old = target.read_text()
            for field, value in [('iteration',9), ('retry_count',{'crm':3}), ('client_id','other')]:
                bad = copy.deepcopy(c)
                bad[field] = value
                with self.assertRaises(ValueError):
                    atomic_checkpoint(bad,target)
                self.assertEqual(old,target.read_text())


if __name__ == '__main__':
    unittest.main()
