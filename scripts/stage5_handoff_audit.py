"""Audit stage5 handoff against immutable history, executed sources and raw receipts."""
import ast
import datetime as dt
import hashlib
import json
import re
import tarfile
from pathlib import Path
from model_executor import source_hashes
from pilot_contracts import snapshot
from review_records import validate_reviews
from stage4_handoff_audit import audit as audit_stage4


def audit(repo):
    def read(name):
        return json.loads((repo / name).read_text(encoding='utf-8'))

    historical = audit_stage4(repo)
    initial = read('reports/stage5-input-state.json')
    snap = snapshot(repo)
    if snap != initial['snapshot']:
        raise ValueError('Native task/prompt snapshot drift')
    for relative, wanted in initial['stage4_evidence_sha256'].items():
        if hashlib.sha256((repo / relative).read_bytes()).hexdigest() != wanted:
            raise ValueError('Stage4 evidence changed: ' + relative)
    tests = read('reports/stage5-unit-tests.json')
    if not tests['all_passed'] or tests['tests_run'] != 102 or tests['failures'] or tests['errors'] or tests['skipped'] or not tests['platform'].startswith('Linux-') or tests['execution_workspace'] != 'native-linux-byte-verified-copy':
        raise ValueError('Complete clean native Linux test evidence required')
    for relative, wanted in tests['input_sha256'].items():
        path = (repo / relative).resolve()
        if not path.is_relative_to(repo.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != wanted:
            raise ValueError('Tested source/input changed: ' + relative)
    simulation = read('reports/stage5-offline-summary.json')
    if simulation['source_files_sha256'] != source_hashes() or simulation['snapshot_id'] != snap['id']:
        raise ValueError('Integration source/snapshot drift')
    archive = repo / simulation['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest() != simulation['archive_sha256']:
        raise ValueError('Integration archive checksum mismatch')
    rows = [json.loads(line) for line in (repo / 'reports/stage5-fixture-trials.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(rows) != 3 or len({row['trial_id'] for row in rows}) != 2:
        raise ValueError('Unexpected scoped fixture coverage')
    charges = {'inference': 0, 'compute': 0}
    by_attempt = {}
    with tarfile.open(archive, 'r:gz') as handle:
        requests = [json.loads(line) for line in handle.extractfile('state/export/requests.jsonl').read().decode('utf-8').splitlines()]
        if len(requests) != 5 or len({r['request_id'] for r in requests}) != 5:
            raise ValueError('Request identities lost/duplicated')
        for row in requests:
            if row['phase'] != 'received' or row['actual_i'] is None or row['actual_c'] is None:
                raise ValueError('Expected settled fixture request receipts')
            key = (row['trial_id'], row['attempt'])
            pair = by_attempt.setdefault(key, [0, 0])
            pair[0] += row['actual_i']; pair[1] += row['actual_c']
        for row in rows:
            if row['data_origin'] != 'simulation' or row['cost_usd'] is not None:
                raise ValueError('Fixture escaped simulation namespace')
            name, member = row['raw_reference'].split('::', 1)
            if name != simulation['archive']:
                raise ValueError('Unexpected raw archive reference')
            raw = json.load(handle.extractfile(member))
            key = (row['trial_id'], row['attempt'])
            if key != (raw['trial_id'], raw['number']) or by_attempt[key] != [raw['actual_i'], raw['actual_c']]:
                raise ValueError('Request/raw attempt identity or charges mismatch')
            for label, actual in [('inference', 'actual_i'), ('compute', 'actual_c')]:
                if row['simulation_cost_micro_units'][label] != raw[actual]:
                    raise ValueError('Normalized charges mismatch')
                charges[label] += raw[actual]
        if charges != simulation['known_attempt_and_request_charges_micro_units']:
            raise ValueError('Retry/request costs lost')
        for name, wanted in simulation['source_files_sha256'].items():
            if hashlib.sha256(handle.extractfile('source/' + name).read()).hexdigest() != wanted:
                raise ValueError('Archived execution source differs')
        proof = json.load(handle.extractfile('state/export/executor-provenance.json'))
        if proof['source_files_sha256'] != source_hashes() or proof['known_request_charges_micro_units'] != charges:
            raise ValueError('Archived provenance mismatch')
    roster = [json.loads(line) for line in (repo / 'manifest.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    if any(row['review_status'] != 'pending' for row in roster):
        raise ValueError('Unexpected human review mutation')
    template = read('configs/review-records.stage5.template.json')
    try:
        validate_reviews(snap, template['records'])
    except ValueError:
        pass
    else:
        raise ValueError('Incomplete review template unexpectedly accepted')
    ready = read('reports/stage5-model-readiness-current.json')
    if ready['ready_for_dispatch'] or ready['ready_for_model_dispatch'] or ready['model_calls'] or ready['manifest_source'] != 'generated-preview-not-executable':
        raise ValueError('Unwarranted real model readiness')
    documents = ['README.md', 'Plan/plan.md', 'Plan/plan-giai-doan-5.md',
                 'docs/model-executor.md', 'docs/model-executor-contract.md',
                 'reports/model-executor-offline-validation.md', 'reports/stage5-readiness.md']
    for relative in documents:
        path = repo / relative
        content = path.read_text(encoding='utf-8')
        if '\ufffd' in content or sum(line.startswith('```') for line in content.splitlines()) % 2:
            raise ValueError('Invalid UTF-8/fence in handoff document')
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', content):
            if '://' not in target and not target.startswith('#') and not (path.parent / target.split('#')[0]).exists():
                raise ValueError('Broken link: ' + relative + ' -> ' + target)
    for path in (repo / 'scripts').rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    for path in (repo / 'reports').rglob('*.json'):
        json.loads(path.read_text(encoding='utf-8'))
    return {'schema': 'vi-stage5-summary/0.1',
            'recorded_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'run_id': 'stage5-offline-engineering', 'scope': 'offline-engineering',
            'kind': 'offline-executor-not-model-evaluation',
            'milestones': {'G5.1': 'offline_contracts_validated', 'G5.2': 'offline_orchestration_validated',
                           'G5.3': 'missing_input_and_unverified', 'G5.4': 'not_run', 'G5.5': 'not_run'},
            'snapshot_id': snap['id'], 'historical_evidence_unchanged': True,
            'stage4_report_and_archive_hashes_preserved': True, 'task_payloads_and_prompts_unchanged': True,
            'unit_tests': {key: tests[key] for key in ['platform', 'tests_run', 'failures', 'errors', 'skipped', 'all_passed', 'execution_workspace']},
            'verified_test_input_files': len(tests['input_sha256']),
            'offline_integration': simulation,
            'review_accepted': 0, 'review_total': len(roster),
            'ready_for_model_dispatch': False, 'real_provider_binding': False,
            'real_runtime_or_isolation_validated': False,
            'shared_real_provider_account_ledger': 'not_implemented',
            'partial_multi_request_recovery': 'conservative_uncertain_no_automatic_continuation',
            'model_calls': 0, 'secrets_read': False,
            'readiness_checks': ready['checks'], 'missing_profile_fields': initial['missing_profile_fields'],
            'part_A': 'missing_eval_snapshot_and_configuration', 'publication': 'not_performed',
            'handoff_checks': 'Passed historical hashes, 172 executed input hashes, raw/request/normalized charges, archive source, review pending, JSON/AST/UTF-8 and local links',
            'stage4_archive_count': len(historical['archive_inventory'])}


if __name__ == '__main__':
    repo = Path(__file__).resolve().parents[1]
    output = repo / 'reports/stage5-summary.json'
    if output.exists():
        raise ValueError('Do not overwrite final handoff evidence')
    result = audit(repo)
    with output.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('Stage5 handoff passed: 102 Linux tests, 2 fixture trials/3 attempts/5 requests, 0 model calls')
