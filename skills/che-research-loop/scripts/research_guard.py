#!/usr/bin/env python3
"""Structural safeguards only; never a substitute for source verification."""
import argparse
import json
import os
from pathlib import Path
import tempfile


def require_fields(obj, fields):
    for field in fields.split():
        if field not in obj:
            raise ValueError('Missing field: ' + field)


def validate_checkpoint(c):
    require_fields(c, 'workflow version client_id iteration status sources_checked known_facts gaps conflicts client_state reactivation_eligibility next_step retry_count updated_at')
    if c['workflow'] != 'RESEARCH-LOOP-001' or c['version'] != '1.0':
        raise ValueError('Wrong workflow/version')
    if c['status'] != 'RUNNING' or type(c['iteration']) is not int or not 1 <= c['iteration'] <= 8:
        raise ValueError('Invalid checkpoint status/iteration')
    require_fields(c['next_step'], 'uncertainty source purpose')
    if not isinstance(c['retry_count'], dict) or any(type(n) is not int or not 0 <= n <= 2 for n in c['retry_count'].values()):
        raise ValueError('Retry limit exceeded or invalid counters')
    if not c['client_id'] or not c['updated_at']:
        raise ValueError('Client key and actual timestamp required')


def validate_result(doc):
    require_fields(doc, 'research_result')
    r = doc['research_result']
    require_fields(r, 'workflow client relationship stop_reason current_context client_state reactivation_eligibility facts conflicts gaps sources_checked research_quality routing result evidence_registry source_selection_log verify')
    if r['workflow'] != {'name': 'RESEARCH-LOOP-001', 'version': '1.0'}:
        raise ValueError('Wrong workflow/version')
    require_fields(r['client'], 'company legal_entity contacts website crm_ids')
    require_fields(r['relationship'], 'first_known_contact projects purchases key_events last_meaningful_interaction')
    require_fields(r['current_context'], 'active_projects recent_changes open_commitments')
    require_fields(r['client_state'], 'status confidence evidence')
    require_fields(r['reactivation_eligibility'], 'status reason evidence')
    require_fields(r['routing'], 'next_process reason')
    require_fields(r['research_quality'], 'iterations evidence_coverage unresolved_high_priority_gaps loop_stop_reason')
    require_fields(r['stop_reason'], 'status reason evidence')
    s, e, route, result = r['client_state']['status'], r['reactivation_eligibility']['status'], r['routing']['next_process'], r['result']
    if result not in {'PASS', 'PASS_WITH_GAPS', 'HUMAN_REVIEW', 'FAIL'}:
        raise ValueError('Invalid result')
    if type(r['research_quality']['iterations']) is not int or not 0 <= r['research_quality']['iterations'] <= 8:
        raise ValueError('Iteration limit exceeded')
    allowed = {'ACTIVE': {'NO': {'ACTIVE_CLIENT'}}, 'PROSPECT_ONLY': {'NO': {'PROSPECT_SALES', 'CLOSE'}}, 'UNKNOWN': {'HUMAN_REVIEW': {'HUMAN_REVIEW'}}, 'CONFLICT': {'HUMAN_REVIEW': {'HUMAN_REVIEW'}}}
    for state in ('DORMANT', 'LOST', 'COMPLETED'):
        allowed[state] = {'YES': {'OPPORTUNITY', 'REACTIVATION'}, 'NO': {'CLOSE'}, 'HUMAN_REVIEW': {'HUMAN_REVIEW'}}
    human_override = result == 'HUMAN_REVIEW' and e == 'HUMAN_REVIEW' and route == 'HUMAN_REVIEW'
    if s not in allowed or (not human_override and route not in allowed[s].get(e, set())):
        raise ValueError('State/eligibility/route mismatch')
    if result in {'HUMAN_REVIEW', 'FAIL'} and route != 'HUMAN_REVIEW':
        raise ValueError('Human Review/FAIL cannot route automatically')
    if result in {'PASS', 'PASS_WITH_GAPS'} and (s in {'UNKNOWN', 'CONFLICT'} or e == 'HUMAN_REVIEW' or any(g.get('affects_decision') for g in r['gaps']) or any(c.get('affects_decision') and c.get('status') != 'RESOLVED' for c in r['conflicts'])):
        raise ValueError('Decision-critical uncertainty cannot pass')
    if e == 'YES' and r['current_context'].get('human_restrictions'):
        raise ValueError('Human restrictions require explicit review, not automatic YES')
    if r['stop_reason']['status'] not in {'CONFIRMED', 'UNKNOWN', 'CONFLICT', 'NOT_APPLICABLE'}:
        raise ValueError('Invalid stop_reason')
    if r['stop_reason']['status'] == 'CONFIRMED' and not r['stop_reason']['evidence']:
        raise ValueError('Confirmed reason needs evidence')
    registry = {}
    for evidence in r['evidence_registry']:
        require_fields(evidence, 'id source reference date fact')
        if evidence['id'] in registry:
            raise ValueError('Duplicate evidence ID')
        registry[evidence['id']] = evidence
    for claim in r['facts']:
        require_fields(claim, 'claim confidence evidence')
        if not 0 <= claim['confidence'] <= 1 or not claim['evidence']:
            raise ValueError('Claim needs confidence and evidence')
        for evidence in claim['evidence']:
            if isinstance(evidence, str):
                if evidence not in registry:
                    raise ValueError('Unknown evidence reference')
            else:
                require_fields(evidence, 'source reference date fact')


def atomic_checkpoint(c, destination):
    validate_checkpoint(c)
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = json.loads(path.read_text())
        if old['client_id'] != c['client_id'] or old['iteration'] > c['iteration']:
            raise ValueError('Cannot replace another client or move backwards')
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.checkpoint-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(c, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if json.loads(path.read_text()) != c:
            raise ValueError('Checkpoint read-back failed')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['result', 'checkpoint'])
    parser.add_argument('input')
    parser.add_argument('destination', nargs='?')
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.input).read_text())
        if args.mode == 'result':
            validate_result(data)
        else:
            if not args.destination:
                parser.error('checkpoint requires destination')
            atomic_checkpoint(data, args.destination)
        print('Structural checks passed; verify evidence and workflow separately.')
    except (ValueError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
