"""Fixture executor binding to a shared ledger with a durable local outbox."""
import hashlib
import json
import uuid
from pathlib import Path
from billing_ledger import BillingLedger, receipt_evidence
from model_executor import Executor, FixtureAdapter, RequestLedger, load_json, source_hashes
from pilot_contracts import digest
from pilot_runner import Store


class BillingBlocked(RuntimeError): pass
class BillingCrash(BaseException): pass


def billing_sources():
    folder = Path(__file__).resolve().parent
    return {**source_hashes(), **{name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
            for name in ['billing_ledger.py', 'billing_executor.py', 'reconcile_billing.py']}}


class Bridge:
    def __init__(self, store, ledger, pool, run):
        self.store = store; self.ledger = ledger; self.pool = pool; self.run = run
        binding = store.plan.get('billing_binding', {})
        pool_row = ledger.db.execute('SELECT spec FROM pools WHERE id=?', (pool,)).fetchone()
        run_row = ledger.db.execute('SELECT spec FROM runs WHERE pool_id=? AND run_id=?', (pool, run)).fetchone()
        if not pool_row or not run_row or binding.get('pool_id') != pool or binding.get('run_id') != run or digest(json.loads(pool_row['spec'])) != binding.get('pool_spec_sha256'):
            raise ValueError('Wrong shared ledger/pool for this frozen local binding')
        run_spec = json.loads(run_row['spec'])
        if run_spec['manifest_sha256'] != binding.get('manifest_sha256') or run_spec['caps'] != store.plan['caps'] or run_spec['scope'] != store.plan['scope']:
            raise ValueError('Global run manifest/caps/scope differ from local binding')
        store.db.executescript('''
        CREATE TABLE IF NOT EXISTS billing_outbox(request_id TEXT PRIMARY KEY,identity_json TEXT NOT NULL,phase TEXT NOT NULL,revision_seen INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS billing_overlay(request_id TEXT PRIMARY KEY,revision INTEGER NOT NULL,actual_i INTEGER,actual_c INTEGER,receipt_sha256 TEXT NOT NULL);
        ''')

    def prepare(self, request_id, tid, number, slot):
        row = self.store.db.execute('SELECT * FROM execution_requests WHERE request_id=?', (request_id,)).fetchone()
        if row is None or (row['trial_id'], row['attempt'], row['slot']) != (tid, number, slot) or row['phase'] != 'submitted':
            raise ValueError('Submitted local intent must exist before global reservation')
        identity = {'pool_id': self.pool, 'run_id': self.run, 'request_id': request_id,
                    'trial_id': tid, 'attempt': number, 'slot': slot,
                    'bound': {'inference': row['reserve_i'], 'compute': row['reserve_c']}}
        encoded = json.dumps(identity, sort_keys=True)
        with self.store.transaction():
            old = self.store.db.execute('SELECT * FROM billing_outbox WHERE request_id=?', (request_id,)).fetchone()
            if old and old['identity_json'] != encoded: raise ValueError('Outbox identity drift')
            if not old:
                self.store.db.execute("INSERT INTO billing_outbox(request_id,identity_json,phase) VALUES(?,?,'intent')", (request_id, encoded))
                self.store.event(tid, number, 'billing_intent', {'request_id': request_id})
        return identity

    def phase(self, request_id, value):
        with self.store.transaction():
            self.store.db.execute('UPDATE billing_outbox SET phase=? WHERE request_id=?', (value, request_id))

    def accept_provider_receipt(self, request_id, result):
        row = self.ledger.request(request_id)
        if not row: raise ValueError('Missing global request intent')
        if row['revision']:
            prior = self.ledger.db.execute('SELECT envelope FROM receipts WHERE request_id=? AND revision=?', (request_id, row['revision'])).fetchone()
            if json.loads(prior['envelope'])['result'] == result:
                return
        envelope, raw = receipt_evidence(json.loads(row['identity_json']), result, row['revision'] + 1, row['receipt_sha256'])
        self.ledger.apply_receipt(envelope, raw)

    def sync_one(self, request_id):
        old = self.store.db.execute('SELECT * FROM billing_outbox WHERE request_id=?', (request_id,)).fetchone()
        row = self.ledger.request(request_id)
        if not old or not row or old['identity_json'] != row['identity_json']:
            raise ValueError('Global/local outbox identity mismatch')
        if not row['revision']:
            # Never refund or infer absence from an expired lease or missing receipt.
            if row['phase'] == 'submitted':
                self.ledger.uncertain(request_id, 'No complete receipt during explicit reconciliation')
            return 'needs_receipt_or_checkpoint'
        receipt = json.loads(self.ledger.db.execute('SELECT envelope FROM receipts WHERE request_id=? AND revision=?', (request_id, row['revision'])).fetchone()['envelope'])
        result = receipt['result']
        local = self.store.db.execute('SELECT * FROM execution_requests WHERE request_id=?', (request_id,)).fetchone()
        if not local: raise ValueError('Local request intent missing')
        # A settled task result is immutable; later billing deltas live in an overlay.
        if local['phase'] != 'received':
            RequestLedger(self.store).receive(dict(local), result)
        else:
            known = json.loads(local['receipt'])
            if (known['status'], known['reward']) != (result['status'], result['reward']):
                raise ValueError('Billing receipt changed a known local task result')
        with self.store.transaction():
            self.store.db.execute('INSERT INTO billing_overlay VALUES(?,?,?,?,?) ON CONFLICT(request_id) DO UPDATE SET revision=excluded.revision,actual_i=excluded.actual_i,actual_c=excluded.actual_c,receipt_sha256=excluded.receipt_sha256', (request_id, row['revision'], row['actual_i'], row['actual_c'], row['receipt_sha256']))
            if old['revision_seen'] != row['revision']:
                self.store.event(local['trial_id'], local['attempt'], 'billing_receipt_synced', {'request_id': request_id, 'revision': row['revision'], 'sha256': row['receipt_sha256']})
            self.store.db.execute("UPDATE billing_outbox SET phase='receipt_applied',revision_seen=? WHERE request_id=?", (row['revision'], request_id))
        return 'billing_synced'

    def sync_all(self):
        results = {}
        for row in self.store.db.execute('SELECT request_id FROM billing_outbox').fetchall():
            results[row['request_id']] = self.sync_one(row['request_id'])
        # Only settle complete receipts; do not synthesize a checkpoint for partial trials.
        for parent in self.store.db.execute("SELECT * FROM attempts WHERE phase IN ('submitted','uncertain')").fetchall():
            requests = RequestLedger(self.store).rows(parent['trial_id'], parent['number'])
            receipts = [json.loads(row['receipt']) if row['receipt'] else None for row in requests]
            last = receipts[-1] if receipts else None
            complete = bool(last) and all(receipts) and (len(requests) == self.store.plan['execution_policy']['max_requests_per_attempt'] or last['status'] != 'completed')
            if complete:
                amounts = {key: sum(r[key] for r in receipts) if all(r[key] is not None for r in receipts) else None for key in ['inference_micros', 'compute_micros']}
                self.store.settle(parent['trial_id'], parent['number'], {**last, **amounts})
        return results


class BillingFixtureAdapter(FixtureAdapter):
    def __init__(self, provider, settings_path, ledger, pool, run):
        super().__init__(provider, settings_path)
        self.ledger = ledger; self.pool = pool; self.run = run
        self.bridge = None; self.fault = None; self.owner = uuid.uuid4().hex

    def inspect(self, repo, manifest):
        result = super().inspect(repo, manifest)
        result['billing_source_sha256'] = digest(billing_sources())
        result['billing_scope_id'] = self.pool
        return result

    def send_request(self, key, tid, number, slot):
        if self.bridge is None: raise ValueError('Durable bridge must be attached')
        identity = self.bridge.prepare(key, tid, number, slot)
        reservation = self.ledger.reserve(identity)
        if self.fault == 'after_global_reserve': raise BillingCrash(self.fault)
        if reservation is None: raise BillingBlocked('Shared scope reservation denied; no provider request sent')
        self.bridge.phase(key, 'reserved')
        if not self.ledger.claim(key, self.owner): raise BillingBlocked('Global request not claimable; never resend')
        if self.fault == 'after_global_claim': raise BillingCrash(self.fault)
        self.bridge.phase(key, 'submitted')
        try:
            result = super().send_request(key, tid, number, slot)
        except Exception:
            self.ledger.uncertain(key, 'Provider response interrupted')
            raise
        if self.fault == 'after_provider': raise BillingCrash(self.fault)
        self.bridge.accept_provider_receipt(key, result)
        if self.fault == 'after_global_receipt': raise BillingCrash(self.fault)
        self.bridge.sync_one(key)
        return result

    def lookup(self, key):
        # Local fixture lookup only. No negative lookup is an absence proof.
        result = super().lookup(key)
        if result is not None and self.bridge:
            self.bridge.accept_provider_receipt(key, result)
            self.bridge.sync_one(key)
        return result


class BillingExecutor(Executor):
    def __init__(self, repo, context_loader, manifest, adapter, state_dir, pool_spec, clock=None):
        if not isinstance(adapter, BillingFixtureAdapter): raise ValueError('Explicit billing fixture binding required')
        args = {} if clock is None else {'clock': clock}
        super().__init__(repo, context_loader, manifest, adapter, state_dir, **args)
        context = context_loader()
        adapter.ledger.register_pool(pool_spec)
        adapter.ledger.register_run(adapter.pool, adapter.run, manifest['scope'], manifest['manifest_sha256'], context['budget_evidence']['caps'])
        self.binding = {'schema': 'vi-local-billing-binding/0.1', 'origin': 'offline-fixture',
                        'pool_spec_sha256': digest(pool_spec), 'pool_id': adapter.pool, 'run_id': adapter.run,
                        'manifest_sha256': manifest['manifest_sha256'], 'source_sha256': digest(billing_sources())}

    def ledger_plan(self, context):
        plan = super().ledger_plan(context)
        plan['billing_binding'] = self.binding
        return plan

    def open(self, context):
        super().open(context)
        self.adapter.bridge = Bridge(self.store, self.adapter.ledger, self.adapter.pool, self.adapter.run)
        self.store.db.execute('CREATE TABLE IF NOT EXISTS billing_context(plan_json TEXT NOT NULL,binding_json TEXT NOT NULL)')
        old = self.store.db.execute('SELECT * FROM billing_context').fetchone()
        if old and (digest(json.loads(old['plan_json'])) != digest(self.store.plan) or json.loads(old['binding_json']) != self.binding):
            raise ValueError('Frozen local billing context mismatch')
        if not old:
            self.store.db.execute('INSERT INTO billing_context VALUES(?,?)', (json.dumps(self.store.plan, sort_keys=True), json.dumps(self.binding, sort_keys=True)))

    def gate(self, tid=None):
        context, report = super().gate(tid)
        ok = self.adapter.ledger.ready(self.adapter.pool, self.adapter.run, context['policy']['request_reservation'])
        report['checks'].append({'name': 'shared_billing_scope', 'status': 'pass' if ok else 'fail', 'reason': 'Run/pool caps, open submissions and external holds checked; reservation rechecked atomically at dispatch'})
        report['ready_for_dispatch'] = report['ready_for_dispatch'] and ok
        self.last_gate = report
        return context, report

    def write_export(self):
        proof = super().write_export()
        if self.store:
            folder = self.state_dir / 'export'
            outbox = [dict(row) for row in self.store.db.execute('SELECT * FROM billing_outbox ORDER BY request_id')]
            overlay = [dict(row) for row in self.store.db.execute('SELECT * FROM billing_overlay ORDER BY request_id')]
            latest = [self.adapter.ledger.request(row['request_id']) for row in outbox]
            latest = [row for row in latest if row is not None]
            report = {'origin': 'offline-fixture', 'currency': 'SIM_USD', 'binding': self.binding,
                      'source_files_sha256': billing_sources(), 'outbox': outbox, 'billing_overlay': overlay,
                      'pool_exposure': self.adapter.ledger.exposure(self.adapter.pool),
                      'run_exposure': self.adapter.ledger.exposure(self.adapter.pool, self.adapter.run),
                      'known_run_charges_micro_units': {
                          'inference': sum(row['actual_i'] or 0 for row in latest),
                          'compute': sum(row['actual_c'] or 0 for row in latest)},
                      'requests_with_unknown_cost': sum(row['actual_i'] is None or row['actual_c'] is None for row in latest),
                      'note': 'Billing ledger/overlay are authoritative for later fee revisions; legacy task raw remains immutable', 'model_calls': 0}
            (folder / 'shared-billing.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            proof['shared_billing'] = report
        return proof


def open_local_bridge(local_path, ledger):
    from billing_ledger import readonly
    db = readonly(local_path)
    try:
        row = db.execute('SELECT * FROM billing_context').fetchone()
        if not row: raise ValueError('Missing local billing context')
        plan, binding = json.loads(row['plan_json']), json.loads(row['binding_json'])
    finally: db.close()
    if binding['source_sha256'] != digest(billing_sources()): raise ValueError('Recovery source differs from frozen binding')
    store = Store(Path(local_path), plan)
    try:
        return store, Bridge(store, ledger, binding['pool_id'], binding['run_id'])
    except BaseException:
        store.db.close(); raise
