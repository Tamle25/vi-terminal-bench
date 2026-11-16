import copy
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from billing_ledger import BillingLedger, pool_spec, receipt_evidence
from billing_executor import BillingExecutor, BillingFixtureAdapter, BillingCrash, open_local_bridge
from billing_fixtures import billing_fixture
from reconcile_billing import status, import_receipt
from pilot_contracts import digest
from pilot_runner import FakeProvider

REPO = Path(__file__).resolve().parents[2]


def result(i=1000, c=100, state='completed', reward=1):
    return {'status': state, 'reward': reward, 'inference_micros': i, 'compute_micros': c}


def identity(number=1, pool='fixture-shared', run='smoke', bound=None):
    return {'pool_id': pool, 'run_id': run, 'request_id': digest([pool, run, number]),
            'trial_id': 'fixture-trial-' + str(number), 'attempt': 1, 'slot': 1,
            'bound': bound or {'inference': 1000, 'compute': 100}}


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name); self.path = self.root / 'shared.sqlite3'
        self.ledger = BillingLedger(self.path)
        self.spec = pool_spec()
        self.ledger.register_pool(self.spec)
        for run, scope in [('smoke', 'model-smoke'), ('pilot', 'native-pilot')]:
            self.ledger.register_run('fixture-shared', run, scope, digest(run), {'inference': 10000, 'compute': 1000})

    def tearDown(self):
        self.ledger.close(); self.temp.cleanup()

    def submitted(self, ident=None):
        ident = ident or identity()
        self.ledger.reserve(ident); self.assertTrue(self.ledger.claim(ident['request_id'], 'worker'))
        return ident

    def test_real_currency_and_changed_caps_rejected(self):
        spec = copy.deepcopy(self.spec); spec['currency'] = 'USD'
        with self.assertRaises(ValueError): self.ledger.register_pool(spec)
        with self.assertRaises(ValueError): self.ledger.reserve(identity(bound={'inference': 0, 'compute': 0}))
        spec = copy.deepcopy(self.spec); spec['caps']['inference'] += 1
        with self.assertRaises(ValueError): self.ledger.register_pool(spec)

    def test_idempotent_reservation_and_run_identity_frozen(self):
        ident = identity(); self.ledger.reserve(ident); self.ledger.reserve(ident)
        self.assertEqual(self.ledger.exposure('fixture-shared'), ident['bound'])
        changed = copy.deepcopy(ident); changed['bound']['compute'] += 1
        with self.assertRaises(ValueError): self.ledger.reserve(changed)
        with self.assertRaises(ValueError): self.ledger.register_run('fixture-shared', 'smoke', 'native-pilot', digest('smoke'), self.spec['caps'])

    def test_two_runs_race_near_pool_cap(self):
        barrier = threading.Barrier(2); accepted = []; errors = []
        def reserve(run):
            local = None
            try:
                local = BillingLedger(self.path); barrier.wait(timeout=5)
                accepted.append(local.reserve(identity(run=run, bound={'inference': 7000, 'compute': 700})) is not None)
            except Exception as exc: errors.append(type(exc).__name__)
            finally:
                if local: local.close()
        threads = [threading.Thread(target=reserve, args=(run,)) for run in ['smoke', 'pilot']]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=15)
        self.assertFalse(any(t.is_alive() for t in threads)); self.assertEqual(errors, [])
        self.assertEqual(sorted(accepted), [False, True])
        self.assertEqual(self.ledger.exposure('fixture-shared')['inference'], 7000)

    def test_run_cap_is_checked_independently(self):
        self.ledger.register_run('fixture-shared', 'small', 'model-smoke', digest('small'), {'inference': 500, 'compute': 100})
        self.assertIsNone(self.ledger.reserve(identity(run='small')))

    def test_independent_pool_not_blocked_by_uncertain_other_pool(self):
        ident = self.submitted(); self.ledger.uncertain(ident['request_id'], 'fixture interruption')
        self.assertIsNone(self.ledger.reserve(identity(2, run='pilot')))
        self.ledger.register_pool(pool_spec('other', 'other-account'))
        self.ledger.register_run('other', 'other-run', 'native-pilot', digest('other'), self.spec['caps'])
        self.assertIsNotNone(self.ledger.reserve(identity(pool='other', run='other-run')))

    def test_external_hold_preserved_until_explicit_source_release(self):
        self.ledger.hold('fixture-shared', 'external-uncertainty', 'fixture evidence')
        self.assertIsNone(self.ledger.reserve(identity()))
        self.ledger.hold('fixture-shared', 'external-uncertainty', 'fixture reconciliation evidence', False)
        self.assertIsNotNone(self.ledger.reserve(identity()))

    def test_submitted_and_unknown_cost_hold_exposure(self):
        ident = self.submitted()
        self.assertFalse(self.ledger.ready('fixture-shared', 'pilot', ident['bound']))
        envelope, raw = receipt_evidence(ident, result(i=None, c=None))
        self.ledger.apply_receipt(envelope, raw)
        self.assertEqual(self.ledger.exposure('fixture-shared'), ident['bound'])
        self.assertEqual(self.ledger.request(ident['request_id'])['phase'], 'uncertain')

    def test_zero_charge_distinct_from_unknown_and_receipt_repeat_idempotent(self):
        ident = self.submitted(); envelope, raw = receipt_evidence(ident, result(0, 0))
        self.assertTrue(self.ledger.apply_receipt(envelope, raw))
        count = self.ledger.db.execute('SELECT count(*) FROM events').fetchone()[0]
        self.assertFalse(self.ledger.apply_receipt(envelope, raw))
        self.assertEqual(self.ledger.db.execute('SELECT count(*) FROM events').fetchone()[0], count)
        self.assertEqual(self.ledger.exposure('fixture-shared'), {'inference': 0, 'compute': 0})

    def test_wrong_identity_raw_hash_and_conflicting_revision_rejected(self):
        ident = self.submitted(); envelope, raw = receipt_evidence(ident, result())
        with self.assertRaises(ValueError): self.ledger.apply_receipt(envelope, raw + b' ')
        wrong, wrong_raw = receipt_evidence(identity(2), result())
        with self.assertRaises(ValueError): self.ledger.apply_receipt(wrong, wrong_raw)
        self.ledger.apply_receipt(envelope, raw)
        conflict, raw2 = receipt_evidence(ident, result(1500))
        with self.assertRaises(ValueError): self.ledger.apply_receipt(conflict, raw2)

    def test_billing_adjustment_chain_preserves_task_result_and_not_double_charged(self):
        ident = self.submitted(); envelope, raw = receipt_evidence(ident, result())
        self.ledger.apply_receipt(envelope, raw)
        next_env, next_raw = receipt_evidence(ident, result(1200), 2, digest(envelope), 'provider-billing-adjustment')
        self.ledger.apply_receipt(next_env, next_raw); self.ledger.apply_receipt(next_env, next_raw)
        self.assertEqual(self.ledger.exposure('fixture-shared')['inference'], 1200)
        self.assertEqual(self.ledger.db.execute('SELECT count(*) FROM receipts').fetchone()[0], 2)
        missing, missing_raw = receipt_evidence(ident, result(None), 3, digest(next_env), 'provider-billing-adjustment')
        with self.assertRaises(ValueError): self.ledger.apply_receipt(missing, missing_raw)
        bad, bad_raw = receipt_evidence(ident, result(1200, state='agent_failure', reward=0), 3, digest(next_env), 'provider-billing-adjustment')
        with self.assertRaises(ValueError): self.ledger.apply_receipt(bad, bad_raw)

    def test_overrun_keeps_observed_charge_and_stops_future_reservation(self):
        ident = self.submitted(); envelope, raw = receipt_evidence(ident, result(12000))
        self.ledger.apply_receipt(envelope, raw)
        self.assertEqual(self.ledger.exposure('fixture-shared')['inference'], 12000)
        self.assertIsNone(self.ledger.reserve(identity(2, run='pilot')))

    def test_cancel_only_never_claimed_and_readonly_missing_never_creates(self):
        ident = identity(); self.ledger.reserve(ident); self.ledger.cancel_reserved(ident['request_id'])
        ident2 = self.submitted(identity(2))
        with self.assertRaises(ValueError): self.ledger.cancel_reserved(ident2['request_id'])
        missing = self.root / 'missing.db'
        with self.assertRaises(ValueError): status(missing)
        self.assertFalse(missing.exists())

    def test_closed_backup_restore_and_readonly_status_no_row_mutation(self):
        ident = self.submitted(); envelope, raw = receipt_evidence(ident, result())
        self.ledger.apply_receipt(envelope, raw); self.ledger.close()
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        report = status(self.path)
        self.assertEqual(len(report['receipt_revisions']), 1)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)
        restored = self.root / 'restored.db'; shutil.copyfile(self.path, restored)
        other = BillingLedger(restored)
        try: self.assertEqual(other.exposure('fixture-shared')['inference'], 1000)
        finally: other.close()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        (REPO / 'build').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=REPO / 'build'); self.root = Path(self.temp.name)
        self.clock_value = time.time(); self.handles = []
        self.ledger = BillingLedger(self.root / 'shared.db'); self.spec = pool_spec()

    def tearDown(self):
        for item in reversed(self.handles):
            if isinstance(item, BillingExecutor): item.close()
            else: item.db.close()
        self.ledger.close(); self.temp.cleanup()

    def executor(self, run='fixture-smoke', scope='model-smoke', requests=1):
        root = self.root / run
        context, manifest = billing_fixture(REPO, root, run, scope, requests, dt.datetime.fromtimestamp(self.clock_value, dt.timezone.utc))
        provider = FakeProvider(root / 'state/provider.db')
        adapter = BillingFixtureAdapter(provider, root / 'effective-settings.json', self.ledger, self.spec['billing_scope_id'], run)
        executor = BillingExecutor(REPO, lambda: json.loads((root / 'context.json').read_text(encoding='utf-8')), manifest, adapter, root / 'state', self.spec, lambda: self.clock_value)
        self.handles.extend([provider, executor])
        return executor, provider, root

    def test_smoke_charge_blocks_pilot_in_same_pool(self):
        self.spec = pool_spec(caps={'inference': 1000, 'compute': 100})
        smoke, p, _ = self.executor(); pilot, p2, _ = self.executor('fixture-pilot', 'native-pilot')
        smoke.run_one(smoke.ids()[0])
        self.assertEqual(pilot.run_one(pilot.ids()[0]), 'gate-blocked')
        self.assertEqual((p.call_count(), p2.call_count()), (1, 0))

    def test_crash_between_global_reserve_and_local_ack_keeps_exposure(self):
        e, p, root = self.executor(); e.adapter.fault = 'after_global_reserve'
        with self.assertRaises(BillingCrash): e.run_one(e.ids()[0])
        row = self.ledger.db.execute('SELECT * FROM requests').fetchone()
        self.assertEqual(row['phase'], 'reserved'); self.assertEqual(p.call_count(), 0)
        self.assertEqual(self.ledger.exposure('fixture-shared')['inference'], 1000)
        self.ledger.cancel_reserved(row['id'])
        self.assertEqual(self.ledger.exposure('fixture-shared')['inference'], 0)
        self.assertEqual(e.store.latest(e.ids()[0])['phase'], 'submitted')

    def test_crash_after_claim_without_receipt_never_resends(self):
        e, p, _ = self.executor(); e.adapter.fault = 'after_global_claim'
        with self.assertRaises(BillingCrash): e.run_one(e.ids()[0])
        self.clock_value += 31; e.adapter.fault = None
        e.run_one(e.ids()[0]); e.run_one(e.ids()[0])
        self.assertEqual(p.call_count(), 0)
        self.assertFalse(self.ledger.ready('fixture-shared', 'fixture-smoke', {'inference': 1000, 'compute': 100}))

    def test_crash_after_provider_reconciles_without_duplicate_reservation(self):
        e, p, _ = self.executor(); e.adapter.fault = 'after_provider'
        with self.assertRaises(BillingCrash): e.run_one(e.ids()[0])
        self.clock_value += 31; e.adapter.fault = None
        self.assertEqual(e.run_one(e.ids()[0]), 'reconciled')
        self.assertEqual(p.call_count(), 1)
        self.assertEqual(self.ledger.db.execute('SELECT count(*) FROM requests').fetchone()[0], 1)
        self.assertEqual(self.ledger.exposure('fixture-shared')['inference'], 1000)

    def test_cli_receipt_replay_after_global_commit_syncs_local_without_double_cost(self):
        e, p, root = self.executor(); e.adapter.fault = 'after_global_receipt'
        with self.assertRaises(BillingCrash): e.run_one(e.ids()[0])
        row = self.ledger.db.execute('SELECT * FROM receipts').fetchone()
        receipt = root / 'receipt.json'; raw = root / 'raw.json'
        receipt.write_text(row['envelope'], encoding='utf-8'); raw.write_bytes(row['raw_evidence'].encode('utf-8'))
        command = [sys.executable, str(REPO / 'scripts/reconcile_billing.py'), 'import-receipt', '--ledger', str(self.ledger.path), '--local-state', str(root / 'state/ledger.sqlite3'), '--receipt', str(receipt), '--raw-evidence', str(raw)]
        first = subprocess.run([*command, '--fault-after-global'], capture_output=True, text=True, timeout=20)
        self.assertNotEqual(first.returncode, 0); self.assertIn('BillingCrash', first.stderr)
        second = subprocess.run(command, capture_output=True, text=True, timeout=20)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(p.call_count(), 1)
        self.assertEqual(e.store.latest(e.ids()[0])['phase'], 'completed')
        self.assertEqual(self.ledger.db.execute('SELECT count(*) FROM receipts').fetchone()[0], 1)

    def test_cost_adjustment_overlay_keeps_original_raw_task_result(self):
        e, p, root = self.executor(); e.run_one(e.ids()[0])
        row = dict(self.ledger.db.execute('SELECT * FROM requests').fetchone())
        old = json.loads(self.ledger.db.execute('SELECT envelope FROM receipts WHERE request_id=?', (row['id'],)).fetchone()[0])['result']
        env, raw = receipt_evidence(json.loads(row['identity_json']), {**old, 'inference_micros': 1200}, 2, row['receipt_sha256'], 'provider-billing-adjustment')
        import_receipt(self.ledger.path, env, raw, root / 'state/ledger.sqlite3')
        self.assertEqual(e.store.latest(e.ids()[0])['actual_i'], 1000)
        self.assertEqual(e.store.db.execute('SELECT actual_i FROM billing_overlay').fetchone()[0], 1200)
        self.assertEqual(self.ledger.exposure('fixture-shared')['inference'], 1200)
        self.assertEqual(p.call_count(), 1)

    def test_partial_multi_request_without_checkpoint_stays_uncertain(self):
        e, p, _ = self.executor(requests=2); e.adapter.fault = 'after_provider'
        with self.assertRaises(BillingCrash): e.run_one(e.ids()[0])
        self.clock_value += 31; e.adapter.fault = None
        self.assertEqual(e.run_one(e.ids()[0]), 'uncertain-no-resend')
        e.run_one(e.ids()[0]); self.assertEqual(p.call_count(), 1)

    def test_external_pool_hold_blocks_executor_before_provider(self):
        e, p, _ = self.executor()
        self.ledger.hold('fixture-shared', 'outside', 'fixture external evidence')
        self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked')
        self.assertEqual(p.call_count(), 0)

    def test_cli_status_reads_pending_outbox_without_mutation(self):
        e, p, root = self.executor(); e.adapter.fault = 'after_global_claim'
        with self.assertRaises(BillingCrash): e.run_one(e.ids()[0])
        count = self.ledger.db.execute('SELECT count(*) FROM events').fetchone()[0]
        completed = subprocess.run([sys.executable, str(REPO / 'scripts/reconcile_billing.py'), 'status', '--ledger', str(self.ledger.path), '--local-state', str(root / 'state/ledger.sqlite3')], capture_output=True, text=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        observed = json.loads(completed.stdout)
        self.assertEqual(observed['requests'][0]['phase'], 'submitted')
        self.assertEqual(len(observed['local_outbox']), 1)
        self.assertEqual(self.ledger.db.execute('SELECT count(*) FROM events').fetchone()[0], count)
        self.assertEqual(p.call_count(), 0)

    def test_unknown_cost_reconciles_result_but_does_not_bypass_expired_gate(self):
        e, p, root = self.executor(); tid = e.ids()[0]
        p.scenarios = {tid + '@request-1:1': result(None, None)}
        e.run_one(tid)
        self.assertEqual(e.store.latest(tid)['phase'], 'uncertain')
        self.assertFalse(self.ledger.ready('fixture-shared', 'fixture-smoke', {'inference': 1000, 'compute': 100}))
        row = dict(self.ledger.db.execute('SELECT * FROM requests').fetchone())
        env, raw = receipt_evidence(json.loads(row['identity_json']), result(), 2, row['receipt_sha256'])
        import_receipt(self.ledger.path, env, raw, root / 'state/ledger.sqlite3')
        self.assertEqual(e.store.latest(tid)['phase'], 'completed')
        self.clock_value += 301
        self.assertEqual(e.run_one(e.ids()[1]), 'gate-blocked')
        self.assertEqual(p.call_count(), 1)

    def test_wrong_shared_database_with_same_reference_ids_is_rejected(self):
        e, p, root = self.executor(); e.run_one(e.ids()[0])
        for index, different_pool in enumerate([True, False]):
            wrong = BillingLedger(self.root / f'wrong-{index}.db')
            try:
                spec = pool_spec(caps={'inference': 20000, 'compute': 2000}) if different_pool else self.spec
                wrong.register_pool(spec)
                manifest = e.binding['manifest_sha256'] if different_pool else digest('different-manifest')
                wrong.register_run('fixture-shared', 'fixture-smoke', 'model-smoke', manifest, e.store.plan['caps'])
                with self.assertRaises(ValueError): open_local_bridge(root / 'state/ledger.sqlite3', wrong)
            finally: wrong.close()


if __name__ == '__main__': unittest.main()
