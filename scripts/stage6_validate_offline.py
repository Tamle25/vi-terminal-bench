"""Bounded shared-budget integration; fixture scopes, not a real smoke/pilot."""
import json
import argparse
import re
import platform
import sys
import tarfile
import tempfile
from pathlib import Path
from billing_executor import BillingExecutor, BillingFixtureAdapter, BillingCrash, billing_sources, open_local_bridge
from billing_fixtures import billing_fixture
from billing_ledger import BillingLedger, pool_spec, receipt_evidence, hashlib_sha
from model_executor import Executor, FixtureAdapter
from pilot_runner import FakeProvider
from runtime_process import run_bounded
from reconcile_billing import status


def validate(repo, prefix='stage6'):
    if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', prefix): raise ValueError('Invalid evidence prefix')
    output = repo / 'reports' / (prefix + '-offline-summary.json')
    archive = repo / 'jobs' / (prefix + '-shared-billing.tar.gz')
    if output.exists() or archive.exists(): raise ValueError('Do not overwrite billing integration evidence')
    with tempfile.TemporaryDirectory(prefix='stage6-billing-', dir=repo / 'build') as temporary:
        root = Path(temporary)
        ledger = BillingLedger(root / 'shared.sqlite3')
        spec = pool_spec(caps={'inference': 1500, 'compute': 200})
        handles = []
        def executor(run, scope, unknown=False):
            folder = root / run
            context, manifest = billing_fixture(repo, folder, run, scope)
            probe = Executor(repo, lambda: context, manifest, FixtureAdapter(None, folder / 'effective-settings.json'), folder / 'state')
            scenarios = {probe.ids()[0] + '@request-1:1': {'status': 'completed', 'reward': 1, 'inference_micros': None, 'compute_micros': None}} if unknown else {}
            provider = FakeProvider(folder / 'state/provider.sqlite3', scenarios)
            adapter = BillingFixtureAdapter(provider, folder / 'effective-settings.json', ledger, spec['billing_scope_id'], run)
            runner = BillingExecutor(repo, lambda: context, manifest, adapter, folder / 'state', spec)
            handles.append((runner, provider))
            return runner, provider, folder, scenarios
        try:
            smoke, sp, sf, scenarios = executor('fixture-smoke', 'model-smoke', True)
            pilot, pp, pf, _ = executor('fixture-pilot', 'native-pilot')
            smoke.adapter.fault = 'after_global_receipt'
            try: smoke.run_one(smoke.ids()[0])
            except BillingCrash: pass
            else: raise ValueError('Expected cross-database crash injection')
            if pilot.run_one(pilot.ids()[0]) != 'gate-blocked' or pp.call_count():
                raise ValueError('Unknown smoke cost did not block pilot')
            row = dict(ledger.db.execute('SELECT * FROM requests').fetchone())
            env2, raw2 = receipt_evidence(json.loads(row['identity_json']), {'status': 'completed', 'reward': 1, 'inference_micros': 800, 'compute_micros': 80}, 2, row['receipt_sha256'])
            (root / 'receipt-v2.json').write_text(json.dumps(env2), encoding='utf-8')
            (root / 'raw-v2.json').write_bytes(raw2)
            command = [sys.executable, str(repo / 'scripts/reconcile_billing.py'), 'import-receipt', '--ledger', str(ledger.path), '--local-state', str(sf / 'state/ledger.sqlite3'), '--receipt', str(root / 'receipt-v2.json'), '--raw-evidence', str(root / 'raw-v2.json')]
            failed = run_bounded([*command, '--fault-after-global'], timeout=30)
            if failed['returncode'] == 0 or 'BillingCrash' not in failed['stderr']:
                raise ValueError('Expected receipt import crash after global commit')
            resumed = run_bounded(command, timeout=30)
            if resumed['returncode'] != 0 or resumed['timed_out']: raise ValueError('Receipt replay failed: ' + resumed['stderr'])
            if smoke.store.latest(smoke.ids()[0])['phase'] != 'completed' or sp.call_count() != 1:
                raise ValueError('Receipt recovery changed result or dispatched again')
            if pilot.run_one(pilot.ids()[0]) != 'gate-blocked' or pp.call_count():
                raise ValueError('Remaining pool budget is insufficient but pilot dispatched')
            row = ledger.request(row['id'])
            env3, raw3 = receipt_evidence(json.loads(row['identity_json']), {'status': 'completed', 'reward': 1, 'inference_micros': 400, 'compute_micros': 80}, 3, row['receipt_sha256'], 'provider-billing-adjustment')
            (root / 'receipt-v3.json').write_text(json.dumps(env3), encoding='utf-8')
            (root / 'raw-v3.json').write_bytes(raw3)
            adjusted = run_bounded([sys.executable, str(repo / 'scripts/reconcile_billing.py'), 'import-receipt', '--ledger', str(ledger.path), '--local-state', str(sf / 'state/ledger.sqlite3'), '--receipt', str(root / 'receipt-v3.json'), '--raw-evidence', str(root / 'raw-v3.json')], timeout=30)
            if adjusted['returncode'] != 0: raise ValueError('Billing adjustment failed: ' + adjusted['stderr'])
            if pilot.run_one(pilot.ids()[0]) != 'dispatched' or pp.call_count() != 1:
                raise ValueError('Pilot fixture did not use legitimately available balance')
            if ledger.exposure('fixture-shared') != {'inference': 1400, 'compute': 180}:
                raise ValueError('Shared ledger fees mismatch')
            if smoke.store.latest(smoke.ids()[0])['actual_i'] != 800 or smoke.store.db.execute('SELECT actual_i FROM billing_overlay').fetchone()[0] != 400:
                raise ValueError('Original task raw or correction overlay lost')
            event_count = ledger.db.execute('SELECT count(*) FROM events').fetchone()[0]
            inspected = run_bounded([sys.executable, str(repo / 'scripts/reconcile_billing.py'), 'status', '--ledger', str(ledger.path), '--local-state', str(sf / 'state/ledger.sqlite3'), '--output', str(root / 'read-only-status.json')], timeout=30)
            if inspected['returncode'] != 0 or ledger.db.execute('SELECT count(*) FROM events').fetchone()[0] != event_count:
                raise ValueError('Read-only status mutated ledger')
            smoke.write_export(); pilot.write_export()
            proof = {'schema': 'vi-stage6-offline/0.1', 'origin': 'offline-fixture',
                     'kind': 'shared-billing-reconciliation-not-model-evaluation',
                     'platform': platform.platform(), 'python': platform.python_version(),
                     'logical_fixture_requests': 2, 'fake_dispatch_calls': sp.call_count() + pp.call_count(),
                     'receipt_revisions': ledger.db.execute('SELECT count(*) FROM receipts').fetchone()[0],
                     'unknown_smoke_blocked_pilot': True, 'insufficient_pool_budget_blocked_pilot': True,
                     'receipt_import_replay_no_double_charge': True, 'read_only_status_no_mutation': True,
                     'currency': 'SIM_USD', 'pool_caps_micro_units': spec['caps'],
                     'authoritative_shared_charges_micro_units': {'inference': 1400, 'compute': 180},
                     'legacy_task_charges_micro_units': {'inference': 1800, 'compute': 180},
                     'billing_adjustment_delta_micro_units': {'inference': -400, 'compute': 0},
                     'real_cost_usd': None, 'model_calls': 0, 'secrets_read': False,
                     'source_files_sha256': billing_sources(),
                     'scope_note': 'One request selected in each fixture scope. Not a completed smoke or 72-trial model pilot.'}
        finally:
            for runner, provider in handles: runner.close(); provider.db.close()
            ledger.close()
        with tarfile.open(archive, 'w:gz') as handle:
            handle.add(root, arcname='state')
            for name in billing_sources(): handle.add(repo / 'scripts' / name, arcname='source/' + name)
        with tempfile.TemporaryDirectory(prefix='vi-stage6-restore-') as restored:
            with tarfile.open(archive, 'r:gz') as handle: handle.extractall(restored, filter='data')
            restored = Path(restored) / 'state'
            global_db = BillingLedger(restored / 'shared.sqlite3')
            try:
                if global_db.exposure('fixture-shared') != proof['authoritative_shared_charges_micro_units']:
                    raise ValueError('Restored pool fees mismatch')
                for run, expected, scenario in [('fixture-smoke', 800, scenarios), ('fixture-pilot', 1000, {})]:
                    store, bridge = open_local_bridge(restored / run / 'state/ledger.sqlite3', global_db)
                    provider = FakeProvider(restored / run / 'state/provider.sqlite3', scenario)
                    try:
                        if provider.call_count() != 1 or store.summary()['known_charges_micro_units']['inference'] != expected:
                            raise ValueError('Restored local/provider mismatch')
                    finally: store.db.close(); provider.db.close()
            finally: global_db.close()
        proof.update(restored_all_databases_verified=True, archive='jobs/' + archive.name,
                     archive_sha256=hashlib_sha(archive.read_bytes()))
        with output.open('x', encoding='utf-8') as handle: handle.write(json.dumps(proof, indent=2) + '\n')
        print('Shared billing integration passed: 2 fake requests, 4 receipt revisions, 0 model calls')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--prefix', default='stage6')
    validate(Path(__file__).resolve().parents[1], parser.parse_args().prefix)
