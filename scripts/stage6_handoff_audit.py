"""Verify history, final executed code, receipt chains, overlays and read-only CLI."""
import ast
import datetime as dt
import hashlib
import json
import re
import sys
import tarfile
import tempfile
from pathlib import Path
from billing_executor import billing_sources
from billing_ledger import readonly
from pilot_contracts import digest, snapshot
from runtime_process import run_bounded
from stage5_handoff_audit import audit as audit_stage5


def audit(repo):
    def read(name): return json.loads((repo / name).read_text(encoding='utf-8'))
    historical = audit_stage5(repo)
    initial = read('reports/stage6-input-state.json')
    if initial['snapshot_id'] != snapshot(repo)['id']:
        raise ValueError('Task/prompt snapshot drift')
    for name, wanted in initial['stage5_evidence_sha256'].items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != wanted:
            raise ValueError('Historical stage5 evidence changed: ' + name)
    tests = read('reports/stage6-final-unit-tests.json')
    if tests['tests_run'] != 126 or not tests['all_passed'] or tests['failures'] or tests['errors'] or tests['skipped'] or tests['execution_workspace'] != 'native-linux-byte-verified-copy':
        raise ValueError('Clean final native Linux regression required')
    for name, wanted in tests['input_sha256'].items():
        path = (repo / name).resolve()
        if not path.is_relative_to(repo.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != wanted:
            raise ValueError('Executed input/source differs: ' + name)
    proof = read('reports/stage6-final-offline-summary.json')
    if proof['source_files_sha256'] != billing_sources(): raise ValueError('Billing source differs from final integration')
    archive = repo / proof['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest() != proof['archive_sha256']:
        raise ValueError('Archive checksum drift')
    with tempfile.TemporaryDirectory(prefix='vi-stage6-audit-') as folder:
        folder = Path(folder)
        with tarfile.open(archive, 'r:gz') as handle:
            handle.extractall(folder, filter='data')
        for name, wanted in proof['source_files_sha256'].items():
            if hashlib.sha256((folder / 'source' / name).read_bytes()).hexdigest() != wanted:
                raise ValueError('Archived execution source differs')
        state = folder / 'state'
        global_path = state / 'shared.sqlite3'
        db = readonly(global_path)
        try:
            requests = [dict(row) for row in db.execute('SELECT * FROM requests ORDER BY id')]
            receipts = [dict(row) for row in db.execute('SELECT * FROM receipts ORDER BY request_id,revision')]
            if len(requests) != 2 or len(receipts) != 4: raise ValueError('Request/revision coverage mismatch')
            for request in requests:
                prior = None
                chain = [row for row in receipts if row['request_id'] == request['id']]
                for index, row in enumerate(chain, 1):
                    envelope = json.loads(row['envelope'])
                    if row['revision'] != index or envelope['previous_sha256'] != prior or digest(envelope) != row['sha256'] or hashlib.sha256(row['raw_evidence'].encode('utf-8')).hexdigest() != envelope['raw_sha256']:
                        raise ValueError('Receipt chain/raw evidence mismatch')
                    if envelope['identity'] != json.loads(request['identity_json']): raise ValueError('Receipt request identity drift')
                    prior = row['sha256']
                latest = json.loads(chain[-1]['envelope'])['result']
                if request['phase'] != 'settled' or (request['actual_i'], request['actual_c']) != (latest['inference_micros'], latest['compute_micros']):
                    raise ValueError('Latest fee revision not reflected in request')
            charges = {'inference': sum(r['actual_i'] for r in requests), 'compute': sum(r['actual_c'] for r in requests)}
            if charges != proof['authoritative_shared_charges_micro_units']: raise ValueError('Shared charges mismatch')
        finally: db.close()
        legacy = {'inference': 0, 'compute': 0}; overlay = {'inference': 0, 'compute': 0}
        for run in ['fixture-smoke', 'fixture-pilot']:
            local_path = state / run / 'state/ledger.sqlite3'
            local = readonly(local_path)
            provider = readonly(state / run / 'state/provider.sqlite3')
            try:
                if provider.execute('SELECT count(*) FROM calls').fetchone()[0] != 1: raise ValueError('Unexpected provider redispatch')
                parent = local.execute('SELECT * FROM attempts').fetchone()
                bill = local.execute('SELECT * FROM billing_overlay').fetchone()
                legacy['inference'] += parent['actual_i']; legacy['compute'] += parent['actual_c']
                overlay['inference'] += bill['actual_i']; overlay['compute'] += bill['actual_c']
                raw = json.loads(next((state / run / 'state/export/raw').glob('*.json')).read_text(encoding='utf-8'))
                normalized = json.loads((state / run / 'state/export/trials.jsonl').read_text(encoding='utf-8').splitlines()[0])
                if (parent['trial_id'], parent['number']) != (raw['trial_id'], raw['number']) or normalized['trial_id'] != parent['trial_id'] or normalized['data_origin'] != 'simulation' or normalized['cost_usd'] is not None:
                    raise ValueError('Raw/normalized task identity or origin mismatch')
                if normalized['simulation_cost_micro_units'] != {'inference': parent['actual_i'], 'compute': parent['actual_c']}:
                    raise ValueError('Legacy task fee was rewritten')
            finally: local.close(); provider.close()
        if legacy != proof['legacy_task_charges_micro_units'] or overlay != charges:
            raise ValueError('Legacy/overlay financial mapping mismatch')
        dbs = list(state.rglob('*.sqlite3'))
        before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in dbs}
        output = folder / 'inspection.json'
        inspected = run_bounded([sys.executable, str(repo / 'scripts/inspect_billing_state.py'), '--ledger', str(global_path), '--local-state', str(state / 'fixture-smoke/state/ledger.sqlite3'), '--output', str(output)], timeout=20)
        if inspected['returncode'] != 0: raise ValueError('Read-only recovery view failed: ' + inspected['stderr'])
        view = json.loads(output.read_text(encoding='utf-8'))
        if not view['observed_at_utc'] or len(view['local_execution_leases']) != 1 or len(view['local_request_leases']) != 1:
            raise ValueError('Missing owner/lease/observation metadata')
        if before != {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in dbs}:
            raise ValueError('Read-only CLI changed a database')
    roster = [json.loads(line) for line in (repo / 'manifest.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    if any(row['review_status'] != 'pending' for row in roster): raise ValueError('Unexpected review acceptance')
    ready = read('reports/stage6-model-readiness.json')
    if ready['ready_for_dispatch'] or ready['ready_for_model_dispatch'] or ready['model_calls']:
        raise ValueError('Unexpected real model readiness')
    documents = ['README.md', 'Plan/plan.md', 'Plan/plan-giai-doan-6.md',
                 'docs/shared-billing-ledger.md', 'docs/reconciliation-runbook.md',
                 'reports/shared-billing-offline-validation.md', 'reports/stage6-readiness.md']
    for name in documents:
        path = repo / name; content = path.read_text(encoding='utf-8')
        if '\ufffd' in content or sum(line.startswith('```') for line in content.splitlines()) % 2:
            raise ValueError('Invalid handoff UTF-8/fence')
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', content):
            if '://' not in target and not target.startswith('#') and not (path.parent / target.split('#')[0]).exists():
                raise ValueError('Broken local link: ' + target)
    for path in (repo / 'scripts').rglob('*.py'): ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    for path in (repo / 'reports').rglob('*.json'): json.loads(path.read_text(encoding='utf-8'))
    return {'schema': 'vi-stage6-summary/0.1', 'run_id': 'stage6-offline-engineering',
            'scope': 'offline-engineering', 'recorded_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'kind': 'shared-billing-reconciliation-not-model-evaluation',
            'milestones': {'G6.1': 'offline_shared_billing_validated', 'G6.2': 'offline_reconciliation_validated',
                           'G6.3': 'missing_input_and_unverified', 'G6.4': 'not_run'},
            'snapshot_id': initial['snapshot_id'], 'historical_evidence_unchanged': True,
            'stage5_sources_reports_and_archives_preserved': True,
            'unit_tests': {key: tests[key] for key in ['platform', 'tests_run', 'failures', 'errors', 'skipped', 'all_passed', 'execution_workspace']},
            'verified_test_input_files': len(tests['input_sha256']), 'offline_integration': proof,
            'additional_readonly_cli': {'path': 'scripts/inspect_billing_state.py',
                'sha256': hashlib.sha256((repo / 'scripts/inspect_billing_state.py').read_bytes()).hexdigest(),
                'verified_against_restored_archive': True, 'owner_lease_metadata_present': True,
                'five_database_hashes_unchanged': len(dbs) == 5},
            'review_accepted': 0, 'review_total': len(roster), 'model_calls': 0, 'secrets_read': False,
            'ready_for_model_dispatch': False, 'real_provider_account_binding': False,
            'real_runtime_or_isolation_validated': False, 'currency_supported': 'SIM_USD fixture only',
            'provider_specific_checkpoint_lookup_cancel': 'unverified',
            'part_A': 'missing_eval_snapshot_and_configuration', 'publication': 'not_performed',
            'missing_profile_fields': initial['missing_profile_fields'],
            'handoff_checks': 'Historical and executed hashes, receipt chains, legacy/overlay fees, five DB restore, readonly CLI, review pending, AST/JSON/UTF-8/local links passed'}


if __name__ == '__main__':
    repo = Path(__file__).resolve().parents[1]
    target = repo / 'reports/stage6-summary.json'
    if target.exists(): raise ValueError('Do not overwrite final handoff evidence')
    report = audit(repo)
    with target.open('x', encoding='utf-8') as handle: handle.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Stage6 handoff passed: 126 Linux tests, 2 fake requests/4 revisions, 0 model calls')
