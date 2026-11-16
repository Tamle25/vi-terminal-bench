"""Read-only handoff checks; write a new summary, never rewrite historical evidence."""
import ast
import datetime as dt
import hashlib
import json
import re
import tarfile
from pathlib import Path
from pilot_contracts import snapshot
from review_records import coverage
from stage4_input_state import inventory


def audit(repo):
    def read(name):
        return json.loads((repo / name).read_text(encoding='utf-8'))

    current = inventory(repo)
    initial = read('reports/stage4-input-state.json')
    if current['snapshot'] != initial['snapshot'] or current['archive_inventory'] != initial['archive_inventory']:
        raise ValueError('Historical evidence or native snapshot changed')
    snap = snapshot(repo)
    tests = read('reports/stage4-unit-tests.json')
    if not tests['all_passed'] or tests['tests_run'] != 70 or tests['skipped'] or not tests['platform'].startswith('Linux-'):
        raise ValueError('Expected clean complete Linux checks')
    simulation = read('reports/stage4-offline-summary.json')
    archive = repo / simulation['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest() != simulation['archive_sha256']:
        raise ValueError('Simulation archive drift')
    plan = read('reports/stage4-simulation-run.json')
    if plan['snapshot_id'] != snap['id'] or plan['kind'] != 'simulation':
        raise ValueError('Simulation plan scope mismatch')
    rows = [json.loads(line) for line in (repo / 'reports/stage4-simulation-trials.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(rows) != 74 or len({row['trial_id'] for row in rows}) != 72:
        raise ValueError('Attempt/trial count mismatch')
    charges = {'inference': 0, 'compute': 0}
    with tarfile.open(archive, 'r:gz') as handle:
        requests = set()
        for row in rows:
            if row['data_origin'] != 'simulation' or row['cost_usd'] is not None:
                raise ValueError('Synthetic cost/origin escaped namespace')
            archive_name, member = row['raw_reference'].split('::', 1)
            if archive_name != simulation['archive']:
                raise ValueError('Raw reference archive mismatch')
            raw = json.load(handle.extractfile(member))
            if (raw['trial_id'], raw['number']) != (row['trial_id'], row['attempt']):
                raise ValueError('Raw/normalized attempt mismatch')
            requests.add(raw['request_id'])
            for key, actual in [('inference', 'actual_i'), ('compute', 'actual_c')]:
                if raw[actual] != row['simulation_cost_micro_units'][key]:
                    raise ValueError('Raw/normalized cost mismatch')
                charges[key] += raw[actual]
        if len(requests) != 74:
            raise ValueError('Duplicated archived request identity')
    if charges != simulation['synthetic_micro_unit_charges']:
        raise ValueError('Retry costs lost')
    results = read('reports/stage4-simulation-results.json')
    if results['result_kind'] != 'simulation-not-model-evaluation' or len(results['final_trials']) != 72:
        raise ValueError('Simulation aggregate scope mismatch')
    review = coverage(repo)
    manifest = [json.loads(line) for line in (repo / 'manifest.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    if review['accepted_count'] or any(row['review_status'] != 'pending' for row in manifest):
        raise ValueError('Unexpected review mutation')
    ready = read('reports/stage4-model-readiness.json')
    if ready['snapshot_id'] != snap['id'] or ready['ready_for_dispatch'] or ready['model_calls'] != 0:
        raise ValueError('Readiness scope drift')
    for path in (repo / 'scripts').rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    for path in (repo / 'reports').rglob('*.json'):
        json.loads(path.read_text(encoding='utf-8'))
    documents = [repo / name for name in [
        'README.md', 'Plan/plan.md', 'Plan/plan-giai-doan-4.md',
        'docs/pilot-state-schema.md', 'docs/model-profile-mapping.md', 'docs/pilot-runner.md',
        'reports/pilot-runner-offline-validation.md', 'reports/stage4-readiness.md',
    ]]
    for path in documents:
        content = path.read_text(encoding='utf-8')
        if '\ufffd' in content or sum(line.startswith('```') for line in content.splitlines()) % 2:
            raise ValueError('Invalid text/fence: ' + str(path))
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', content):
            if '://' not in target and not target.startswith('#') and not (path.parent / target.split('#')[0]).exists():
                raise ValueError('Broken local link: ' + str(path) + ' -> ' + target)
    return {
        'schema': 'vi-stage4-summary/0.1',
        'recorded_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'kind': 'offline-engineering-not-model-evaluation',
        'milestones': {'G4.1': 'offline_contracts_validated', 'G4.2': 'simulation_validated', 'G4.3': 'missing_input', 'G4.4': 'not_run', 'G4.5': 'not_run'},
        'snapshot_id': snap['id'], 'six_task_payloads_and_prompts_unchanged': True,
        'historical_archives_unchanged': True, 'historical_metadata_unchanged': True,
        'archive_inventory': current['archive_inventory'],
        'unit_tests': {key: tests[key] for key in ['platform', 'tests_run', 'failures', 'errors', 'skipped', 'all_passed']},
        'simulation': simulation,
        'review_accepted': review['accepted_count'], 'review_total': review['total_tasks'],
        'ready_for_model_dispatch': False,
        'readiness_checks': [{key: row[key] for key in ['name', 'status', 'next_action']} for row in ready['checks']],
        'new_real_runtime_attestation': False, 'real_adapter_verified': False,
        'real_provider_executor_implemented': False, 'model_calls': 0,
        'part_A': 'missing_eval_snapshot_and_config', 'release': 'not_performed',
        'handoff_checks': 'historical hashes, raw references and synthetic charges, namespace, UTF-8, AST, JSON, local links passed',
    }


if __name__ == '__main__':
    repo = Path(__file__).resolve().parents[1]
    output = repo / 'reports/stage4-summary.json'
    if output.exists():
        raise ValueError('Do not overwrite handoff evidence')
    result = audit(repo)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Handoff checks passed; 70 Linux tests, 72 simulated finals, 74 fake calls, 0 model calls')
