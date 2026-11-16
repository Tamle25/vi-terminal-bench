"""Scoped orchestration seam with a durable OFFLINE fixture adapter only.

No real provider registry, API client, secret loader or dynamic plugin imports.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import time
import uuid
from pathlib import Path
from execution_contracts import DEFAULT_POLICY, assess, build_manifest, configuration_hashes, validate_manifest
from pilot_contracts import digest, snapshot
from pilot_runner import Store, FakeProvider, SimulatedCrash, simulation_plan, export, money


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def source_hashes():
    folder = Path(__file__).resolve().parent
    return {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in
            ['model_executor.py', 'execution_contracts.py', 'pilot_runner.py',
             'model_dry_run.py', 'pilot_contracts.py', 'review_records.py', 'materialize_variants.py']}


def source_hash():
    return digest(source_hashes())


def checked_receipt(receipt):
    if set(receipt) != {'status', 'reward', 'inference_micros', 'compute_micros'}:
        raise ValueError('Receipt schema mismatch')
    status = receipt['status']
    if status not in {'completed', 'agent_failure', 'retryable_infra_error', 'verifier_error', 'unknown'}:
        raise ValueError('Unclassified provider response')
    reward = receipt['reward']
    if status == 'completed' and (type(reward) is not int or reward not in (0, 1)):
        raise ValueError('Invalid completed reward')
    if status == 'agent_failure' and (type(reward) is not int or reward != 0):
        raise ValueError('Invalid agent failure reward')
    if status not in {'completed', 'agent_failure'} and reward is not None:
        raise ValueError('Infrastructure/unknown reward must be null')
    for key in ['inference_micros', 'compute_micros']:
        if receipt[key] is not None:
            money(receipt[key])
    return receipt


class FixtureAdapter:
    """Observed settings are read independently of expected context on every gate."""
    origin = 'offline-fixture'

    def __init__(self, provider, settings_path):
        self.provider = provider
        self.settings_path = Path(settings_path)

    def inspect(self, repo, manifest):
        settings = load_json(self.settings_path)
        if settings.get('origin') != self.origin:
            raise ValueError('Fixture adapter requires explicit fixture settings')
        hashes = configuration_hashes(repo, settings['profile'], settings['runtime_catalog'], settings['policy'])
        return {'origin': self.origin, 'adapter_id': 'durable-offline-fixture',
                'adapter_version': '0.1', 'source_sha256': source_hash(),
                'run_id': settings['profile']['run_id'], 'snapshot_id': snapshot(repo)['id'],
                'configuration_fingerprints': {key: hashes[key] for key in manifest['expected_configurations']},
                'policy_sha256': digest(settings['policy']),
                'capabilities': {'request_accounting': True,
                    'max_requests_per_attempt': settings['policy']['max_requests_per_attempt'],
                    'lookup': 'durable-fixture-receipts-only', 'idempotency': 'not-assumed',
                    'cancellation': False, 'real_pricing': False}}

    def send_request(self, key, tid, number, slot):
        return self.provider.dispatch(key, f'{tid}@request-{slot}', number)

    def lookup(self, key):
        return self.provider.lookup(key)


class RequestLedger:
    """Per-request intent, CAS claim and exposure within a reserved attempt."""
    def __init__(self, store):
        self.store = store
        store.db.execute('''CREATE TABLE IF NOT EXISTS execution_requests(
          trial_id TEXT NOT NULL, attempt INTEGER NOT NULL, slot INTEGER NOT NULL,
          request_id TEXT NOT NULL UNIQUE, phase TEXT NOT NULL,
          reserve_i INTEGER NOT NULL, reserve_c INTEGER NOT NULL,
          actual_i INTEGER, actual_c INTEGER, receipt TEXT, owner TEXT, lease_until REAL,
          PRIMARY KEY(trial_id,attempt,slot),
          FOREIGN KEY(trial_id,attempt) REFERENCES attempts(trial_id,number))''')

    def rows(self, tid, number):
        return [dict(row) for row in self.store.db.execute(
            'SELECT * FROM execution_requests WHERE trial_id=? AND attempt=? ORDER BY slot', (tid, number))]

    def claim_attempt(self, tid, number, owner):
        s = self.store
        with s.transaction():
            # This executor is C1 across controllers, not only within one process.
            if s.db.execute("SELECT 1 FROM attempts WHERE phase IN ('submitted','uncertain') LIMIT 1").fetchone():
                return False
            if any(s.exposure()[key] > s.plan['caps'][key] for key in s.plan['caps']):
                return False
            changed = s.db.execute("UPDATE attempts SET phase='submitted',owner=?,lease_until=? WHERE trial_id=? AND number=? AND phase='reserved'", (owner, s.clock() + 30, tid, number)).rowcount
            if changed:
                s.event(tid, number, 'submitted', {'owner': owner, 'executor': 'scoped-offline-C1'})
            return bool(changed)

    def reserve(self, tid, number, slot, bound):
        s = self.store
        with s.transaction():
            parent = s.latest(tid)
            if parent is None or parent['number'] != number or parent['phase'] != 'submitted':
                return None
            rows = self.rows(tid, number)
            existing = next((row for row in rows if row['slot'] == slot), None)
            if existing:
                return existing if existing['phase'] == 'reserved' else None
            if slot != len(rows) + 1 or any(row['phase'] != 'received' for row in rows):
                return None
            spent = {key: sum(row[actual] if row[actual] is not None else row[reserved] for row in rows)
                     for key, actual, reserved in [('inference', 'actual_i', 'reserve_i'), ('compute', 'actual_c', 'reserve_c')]}
            if spent['inference'] + bound['inference'] > parent['reserve_i'] or spent['compute'] + bound['compute'] > parent['reserve_c']:
                s.event(tid, number, 'request_budget_blocked', {'slot': slot, 'spent': spent})
                return None
            request_id = digest({'attempt_request': parent['request_id'], 'slot': slot})
            s.db.execute("INSERT INTO execution_requests(trial_id,attempt,slot,request_id,phase,reserve_i,reserve_c) VALUES(?,?,?,?,'reserved',?,?)", (tid, number, slot, request_id, bound['inference'], bound['compute']))
            s.event(tid, number, 'request_reserved', {'slot': slot, 'request_id': request_id})
            return self.rows(tid, number)[-1]

    def claim(self, row, owner):
        s = self.store
        with s.transaction():
            changed = s.db.execute("UPDATE execution_requests SET phase='submitted',owner=?,lease_until=? WHERE request_id=? AND phase='reserved'", (owner, s.clock() + 30, row['request_id'])).rowcount
            if changed:
                s.event(row['trial_id'], row['attempt'], 'request_submitted', {'slot': row['slot'], 'request_id': row['request_id']})
            return bool(changed)

    def receive(self, row, receipt):
        checked_receipt(receipt)
        s = self.store
        encoded = json.dumps(receipt, sort_keys=True, allow_nan=False)
        with s.transaction():
            old = s.db.execute('SELECT * FROM execution_requests WHERE request_id=?', (row['request_id'],)).fetchone()
            if old is None or old['phase'] == 'reserved':
                raise ValueError('Cannot receive an unsubmitted request')
            if old['phase'] == 'received':
                if old['receipt'] != encoded:
                    raise ValueError('Conflicting terminal request receipt')
                return
            if old['receipt']:
                previous = json.loads(old['receipt'])
                if previous['status'] != 'unknown' and (previous['status'], previous['reward']) != (receipt['status'], receipt['reward']):
                    raise ValueError('Reconciliation changed a known task result')
            phase = 'uncertain' if receipt['status'] == 'unknown' or receipt['inference_micros'] is None or receipt['compute_micros'] is None else 'received'
            s.db.execute('UPDATE execution_requests SET phase=?,actual_i=?,actual_c=?,receipt=? WHERE request_id=?', (phase, receipt['inference_micros'], receipt['compute_micros'], encoded, row['request_id']))
            s.event(row['trial_id'], row['attempt'], 'request_receipt', {'slot': row['slot'], **receipt})


class Executor:
    """Actual orchestration seam exercised offline. Real adapter binding remains absent."""
    def __init__(self, repo, context_loader, manifest, adapter, state_dir, clock=time.time):
        if not isinstance(adapter, FixtureAdapter) or adapter.origin != 'offline-fixture':
            raise ValueError('Only the explicit fixture adapter is installed')
        self.repo = Path(repo)
        self.load_context = context_loader
        self.manifest = copy.deepcopy(manifest)
        self.adapter = adapter
        self.state_dir = Path(state_dir)
        self.clock = clock
        self.owner = uuid.uuid4().hex
        self.store = None
        self.requests = None
        self.last_gate = None

    def gate(self, tid=None):
        context = self.load_context()
        context = copy.deepcopy(context)
        if self.store:
            budget = context.get('budget_evidence')
            if budget:
                exposure = self.store.exposure()
                own = self.store.latest(tid) if tid else None
                for key, reserved in [('inference', 'reserve_i'), ('compute', 'reserve_c')]:
                    available = self.store.plan['caps'][key] - exposure[key] + (own[reserved] if own and own['phase'] in {'reserved', 'submitted'} else 0)
                    budget['remaining'][key] = min(budget['remaining'][key], max(0, available))
                budget['cost_uncertain'] = budget.get('cost_uncertain') is not False or bool(self.store.db.execute("SELECT 1 FROM attempts WHERE phase='uncertain' LIMIT 1").fetchone())
        try:
            observation = self.adapter.inspect(self.repo, self.manifest)
            self.last_gate = assess(self.repo, context, self.manifest, observation, 'offline-fixture', dt.datetime.fromtimestamp(self.clock(), dt.timezone.utc))
        except (ValueError, KeyError, TypeError, OSError):
            self.last_gate = {'ready_for_dispatch': False, 'ready_for_model_dispatch': False,
                              'checks': [{'name': 'context_or_adapter', 'status': 'fail', 'reason': 'Invalid or changed execution evidence'}], 'model_calls': 0}
        return context, self.last_gate

    def ledger_plan(self, context):
        roster = [json.loads(line) for line in (self.repo / 'manifest.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        plan = simulation_plan({'kind': 'offline-dry-run-not-executable', 'planned_trials': self.manifest['planned_trials']}, roster, self.manifest['snapshot_id'], run_id='stage5-' + self.manifest['run_id'] + '-' + self.manifest['scope'])
        plan.update(caps=context['budget_evidence']['caps'], reservation=context['budget_evidence']['reservation'],
                    execution_manifest_sha256=self.manifest['manifest_sha256'],
                    execution_policy=context['policy'], executor_source_sha256=source_hash(),
                    scope=self.manifest['scope'])
        return plan

    def open(self, context):
        plan = self.ledger_plan(context)
        if self.store:
            if digest(self.store.plan) != digest(plan):
                raise ValueError('Resume drift in budget, executor source or policy')
            return
        self.store = Store(self.state_dir / 'ledger.sqlite3', plan, self.clock)
        self.requests = RequestLedger(self.store)

    def ids(self):
        prefix = 'simulation-stage5-' + self.manifest['run_id'] + '-' + self.manifest['scope'] + '--'
        return [prefix + row['trial_id'] for row in self.manifest['planned_trials']]

    def combined_receipt(self, tid, number, force_unknown=False):
        rows = self.requests.rows(tid, number)
        receipts = [json.loads(row['receipt']) if row['receipt'] else None for row in rows]
        last = receipts[-1] if receipts else None
        complete = bool(last) and all(receipts) and (len(rows) == self.store.plan['execution_policy']['max_requests_per_attempt'] or last['status'] != 'completed')
        status = last['status'] if complete and not force_unknown else 'unknown'
        amounts = {}
        for key in ['inference_micros', 'compute_micros']:
            amounts[key] = sum(receipt[key] for receipt in receipts) if receipts and all(receipt is not None and receipt[key] is not None for receipt in receipts) else None
        return {'status': status, 'reward': last['reward'] if status in {'completed', 'agent_failure'} else None, **amounts}

    def reconcile(self, tid):
        s = self.store
        parent = s.latest(tid)
        if parent['phase'] == 'submitted' and parent['lease_until'] > self.clock():
            return 'active-lease'
        s.mark_uncertain(tid, parent['number'], 'Expired attempt; receipt lookup only, never blind resend')
        rows = self.requests.rows(tid, parent['number'])
        for row in rows:
            if row['phase'] == 'received':
                continue
            if row['phase'] == 'reserved':
                continue
            receipt = self.adapter.lookup(row['request_id'])
            if receipt is not None:
                try:
                    self.requests.receive(row, receipt)
                except (ValueError, KeyError, TypeError):
                    return 'uncertain-invalid-receipt'
        combined = self.combined_receipt(tid, parent['number'])
        s.settle(tid, parent['number'], combined)
        return 'reconciled' if s.latest(tid)['phase'] != 'uncertain' else 'uncertain-no-resend'

    def run_one(self, tid, crash=None):
        if tid not in self.ids():
            raise ValueError('Unplanned trial')
        # Reconciliation only reads local durable fixture receipts; no model call.
        if self.store:
            old = self.store.latest(tid)
            if old and old['phase'] in {'submitted', 'uncertain'}:
                return self.reconcile(tid)
        context, gate = self.gate(tid)
        if not gate['ready_for_dispatch']:
            return 'gate-blocked'
        self.open(context)
        old = self.store.latest(tid)
        if old and old['phase'] in {'submitted', 'uncertain'}:
            return self.reconcile(tid)
        attempt = self.store.reserve(tid)
        if attempt is None:
            return 'budget-blocked-or-terminal'
        if crash == 'after_reserve':
            raise SimulatedCrash(crash)
        _, gate = self.gate(tid)
        if not gate['ready_for_dispatch']:
            return 'gate-blocked'
        if not self.requests.claim_attempt(tid, attempt['number'], self.owner):
            return 'claim-lost'
        if crash == 'after_submit':
            raise SimulatedCrash(crash)
        policy = context['policy']
        for slot in range(1, policy['max_requests_per_attempt'] + 1):
            _, gate = self.gate(tid)
            if not gate['ready_for_dispatch']:
                self.store.settle(tid, attempt['number'], self.combined_receipt(tid, attempt['number'], True))
                return 'gate-blocked-between-requests'
            request = self.requests.reserve(tid, attempt['number'], slot, policy['request_reservation'])
            if request is None:
                self.store.settle(tid, attempt['number'], self.combined_receipt(tid, attempt['number'], True))
                return 'request-budget-blocked'
            if not self.requests.claim(request, self.owner):
                return 'request-claim-lost'
            try:
                receipt = self.adapter.send_request(request['request_id'], tid, attempt['number'], slot)
            except Exception:
                self.store.mark_uncertain(tid, attempt['number'], 'Adapter request interrupted; reconcile required')
                return 'uncertain-provider-error'
            if crash == 'after_provider':
                raise SimulatedCrash(crash)
            try:
                self.requests.receive(request, receipt)
            except (ValueError, TypeError, KeyError):
                self.store.mark_uncertain(tid, attempt['number'], 'Invalid receipt; not a model failure')
                return 'uncertain-invalid-receipt'
            if receipt['status'] != 'completed' or receipt['inference_micros'] is None or receipt['compute_micros'] is None:
                break
        self.store.settle(tid, attempt['number'], self.combined_receipt(tid, attempt['number']))
        return 'dispatched'

    def write_export(self):
        if not self.store:
            return {'kind': 'offline-executor-not-model-evaluation', 'model_calls': 0, 'gate': self.last_gate, 'state_created': False}
        rows, summary = export(self.store, self.adapter.provider, self.state_dir / 'export')
        destination = self.state_dir / 'export'
        requests = [dict(row) for row in self.store.db.execute('SELECT * FROM execution_requests ORDER BY trial_id,attempt,slot')]
        (destination / 'requests.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in requests), encoding='utf-8')
        try:
            observation = self.adapter.inspect(self.repo, self.manifest)
        except (ValueError, KeyError, TypeError, OSError):
            observation = {'origin': 'offline-fixture', 'status': 'unverified', 'reason': 'Settings changed or unavailable; preserved ledger export'}
        proof = {'kind': 'offline-executor-not-model-evaluation',
                 'manifest_sha256': self.manifest['manifest_sha256'],
                 'executor_source_sha256': source_hash(), 'scope': self.manifest['scope'],
                 'source_files_sha256': source_hashes(),
                 'adapter': observation,
                 'request_count': len(requests), 'gate': self.last_gate,
                 'known_request_charges_micro_units': {
                     'inference': sum(row['actual_i'] or 0 for row in requests),
                     'compute': sum(row['actual_c'] or 0 for row in requests)},
                 'requests_with_unknown_cost': sum(row['actual_i'] is None or row['actual_c'] is None for row in requests),
                 'model_calls': 0, 'secrets_read': False, 'summary': summary}
        (destination / 'executor-provenance.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
        return proof

    def close(self):
        if self.store:
            self.store.db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['validate', 'offline-fixture', 'model'], default='validate')
    parser.add_argument('--scope', choices=['model-smoke', 'native-pilot'], default='native-pilot')
    parser.add_argument('--context', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--settings', type=Path)
    parser.add_argument('--state-dir', type=Path)
    parser.add_argument('--scenarios', type=Path)
    parser.add_argument('--max-attempts', type=int)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new report path; historical reports are immutable')
    repo = Path(__file__).resolve().parents[1]
    context = load_json(args.context) if args.context else {
        'origin': 'real', 'profile': load_json(repo / 'configs/model-pilot.template.json'),
        'runtime_catalog': load_json(repo / 'configs/runtime-profiles.json'),
        'policy': copy.deepcopy(DEFAULT_POLICY),
        'reviews': [], 'runtime_evidence': None, 'budget_evidence': None}
    manifest = load_json(args.manifest) if args.manifest else build_manifest(repo, context, args.scope)
    if args.mode != 'offline-fixture':
        report = assess(repo, context, manifest, mode='model')
        if not args.manifest:
            report['manifest_source'] = 'generated-preview-not-executable'
            for check in report['checks']:
                if check['name'] == 'manifest':
                    check.update(status='unverified', reason='Generated preview only; actual frozen execution manifest not supplied')
        code = 2  # Real provider binding absent; --mode model never enables dispatch.
    else:
        if not args.context or not args.manifest or not args.settings or not args.state_dir:
            raise ValueError('Offline fixture requires context, manifest, settings and state-dir')
        # Validate before even creating a provider database.
        manifest = validate_manifest(repo, context, manifest)
        if context.get('origin') != 'offline-fixture' or manifest['kind'] != 'simulation':
            raise ValueError('Offline fixture cannot consume a model plan')
        if args.max_attempts is not None and args.max_attempts < 1:
            raise ValueError('max-attempts must be positive')
        observation = FixtureAdapter(None, args.settings).inspect(repo, manifest)
        initial_gate = assess(repo, context, manifest, observation, 'offline-fixture')
        if not initial_gate['ready_for_dispatch']:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x', encoding='utf-8') as handle:
                handle.write(json.dumps(initial_gate, indent=2) + '\n')
            print('Offline gate blocked before state creation; model calls=0')
            return 2
        provider = FakeProvider(args.state_dir / 'fake-provider.sqlite3', load_json(args.scenarios) if args.scenarios else {})
        executor = Executor(repo, lambda: load_json(args.context), manifest, FixtureAdapter(provider, args.settings), args.state_dir)
        try:
            dispatched = 0
            for _ in range(4):
                for tid in executor.ids():
                    if args.max_attempts is not None and dispatched >= args.max_attempts:
                        break
                    before = provider.call_count()
                    executor.run_one(tid)
                    dispatched += provider.call_count() > before
            report = executor.write_export()
            code = 0 if executor.store and executor.store.summary()['unfinished_trials'] == 0 else 2
        finally:
            executor.close()
            provider.db.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Scoped executor report written; model calls=0; real provider binding absent')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
