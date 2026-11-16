"""Transactional shared billing ledger, OFFLINE SIM_USD only. No provider client."""
import contextlib
import json
import re
import sqlite3
import time
from pathlib import Path
from model_executor import checked_receipt
from pilot_contracts import digest

KEYS = ('inference', 'compute')
MAX_AMOUNT = 10**12


def amounts(value):
    if not isinstance(value, dict) or set(value) != set(KEYS) or any(type(v) is not int or not 0 <= v <= MAX_AMOUNT for v in value.values()):
        raise ValueError('Expected nonnegative integer micro-units, never null/bool/float')
    return value


def label(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,159}', value):
        raise ValueError('Use a nonsecret reference identifier')
    return value


def readonly(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('Existing ledger required; read-only commands never create state')
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db


def pool_spec(pool='fixture-shared', account='fixture-account', caps=None):
    return {'schema': 'vi-billing-pool/0.1', 'origin': 'offline-fixture',
            'billing_scope_id': pool, 'account_ref': account, 'currency': 'SIM_USD',
            'unit': 'micro', 'caps': caps or {'inference': 10000, 'compute': 1000},
            'uncertainty_policy': 'block-pool'}


class BillingLedger:
    def __init__(self, path, clock=time.time):
        self.path = Path(path); self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS pools(id TEXT PRIMARY KEY,spec TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS runs(pool_id TEXT NOT NULL REFERENCES pools(id),run_id TEXT NOT NULL,spec TEXT NOT NULL,PRIMARY KEY(pool_id,run_id));
        CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,pool_id TEXT NOT NULL,run_id TEXT NOT NULL,identity_json TEXT NOT NULL,phase TEXT NOT NULL,reserve_i INTEGER NOT NULL,reserve_c INTEGER NOT NULL,actual_i INTEGER,actual_c INTEGER,revision INTEGER NOT NULL DEFAULT 0,receipt_sha256 TEXT,owner TEXT,FOREIGN KEY(pool_id,run_id) REFERENCES runs(pool_id,run_id));
        CREATE TABLE IF NOT EXISTS receipts(request_id TEXT NOT NULL REFERENCES requests(id),revision INTEGER NOT NULL,envelope TEXT NOT NULL,raw_evidence TEXT NOT NULL,sha256 TEXT NOT NULL,PRIMARY KEY(request_id,revision));
        CREATE TABLE IF NOT EXISTS holds(pool_id TEXT NOT NULL REFERENCES pools(id),id TEXT NOT NULL,active INTEGER NOT NULL,source TEXT NOT NULL,PRIMARY KEY(pool_id,id));
        CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,at REAL NOT NULL,pool_id TEXT,request_id TEXT,event TEXT NOT NULL,details TEXT NOT NULL);
        ''')

    @contextlib.contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK'); raise

    def event(self, pool, request, name, details):
        self.db.execute('INSERT INTO events(at,pool_id,request_id,event,details) VALUES(?,?,?,?,?)',
                        (self.clock(), pool, request, name, json.dumps(details, sort_keys=True, allow_nan=False)))

    def register_pool(self, spec):
        if set(spec) != set(pool_spec()) or spec['schema'] != 'vi-billing-pool/0.1' or spec['origin'] != 'offline-fixture' or spec['currency'] != 'SIM_USD' or spec['unit'] != 'micro' or spec['uncertainty_policy'] != 'block-pool':
            raise ValueError('Only explicitly isolated fixture pools are implemented')
        label(spec['billing_scope_id']); label(spec['account_ref']); amounts(spec['caps'])
        encoded = json.dumps(spec, sort_keys=True)
        with self.transaction():
            old = self.db.execute('SELECT spec FROM pools WHERE id=?', (spec['billing_scope_id'],)).fetchone()
            if old and old['spec'] != encoded:
                raise ValueError('Pool identity/caps/currency are frozen')
            if not old:
                self.db.execute('INSERT INTO pools VALUES(?,?)', (spec['billing_scope_id'], encoded))
                self.event(spec['billing_scope_id'], None, 'pool_created', {'spec_sha256': digest(spec)})

    def register_run(self, pool, run, scope, manifest_sha256, caps):
        label(run); amounts(caps)
        if scope not in {'model-smoke', 'native-pilot'} or not re.fullmatch('[a-f0-9]{64}', manifest_sha256):
            raise ValueError('Run scope/manifest required')
        spec = {'scope': scope, 'manifest_sha256': manifest_sha256, 'caps': caps}
        encoded = json.dumps(spec, sort_keys=True)
        with self.transaction():
            if not self.db.execute('SELECT 1 FROM pools WHERE id=?', (pool,)).fetchone():
                raise ValueError('Pool must be registered explicitly')
            old = self.db.execute('SELECT spec FROM runs WHERE pool_id=? AND run_id=?', (pool, run)).fetchone()
            if old and old['spec'] != encoded:
                raise ValueError('Run scope/manifest/caps are frozen')
            if not old:
                self.db.execute('INSERT INTO runs VALUES(?,?,?)', (pool, run, encoded))
                self.event(pool, None, 'run_registered', {'run_id': run, 'spec_sha256': digest(spec)})

    def request(self, request_id):
        row = self.db.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
        return dict(row) if row else None

    def exposure(self, pool, run=None):
        sql = 'SELECT * FROM requests WHERE pool_id=?'
        params = [pool]
        if run is not None:
            sql += ' AND run_id=?'; params.append(run)
        values = {key: 0 for key in KEYS}
        for row in self.db.execute(sql, params):
            for key, actual, reserve in [('inference', 'actual_i', 'reserve_i'), ('compute', 'actual_c', 'reserve_c')]:
                value = row[reserve] if row[actual] is None else row[actual]
                if row['phase'] == 'uncertain': value = max(value, row[reserve])
                values[key] += value
        return values

    def ready(self, pool, run, bound):
        amounts(bound)
        p = self.db.execute('SELECT spec FROM pools WHERE id=?', (pool,)).fetchone()
        r = self.db.execute('SELECT spec FROM runs WHERE pool_id=? AND run_id=?', (pool, run)).fetchone()
        if not p or not r: return False
        if self.db.execute("SELECT 1 FROM requests WHERE pool_id=? AND phase IN ('submitted','uncertain') LIMIT 1", (pool,)).fetchone(): return False
        if self.db.execute('SELECT 1 FROM holds WHERE pool_id=? AND active=1 LIMIT 1', (pool,)).fetchone(): return False
        for used, spec in [(self.exposure(pool), json.loads(p['spec'])), (self.exposure(pool, run), json.loads(r['spec']))]:
            if any(used[key] + bound[key] > spec['caps'][key] for key in KEYS): return False
        return True

    def reserve(self, identity):
        if set(identity) != {'pool_id', 'run_id', 'request_id', 'trial_id', 'attempt', 'slot', 'bound'}:
            raise ValueError('Request identity schema mismatch')
        for key in ['pool_id', 'run_id']: label(identity[key])
        if not re.fullmatch('[a-f0-9]{64}', identity['request_id']) or not isinstance(identity['trial_id'], str) or not identity['trial_id']:
            raise ValueError('Request/trial identity invalid')
        if any(type(identity[key]) is not int or identity[key] < 1 for key in ['attempt', 'slot']):
            raise ValueError('Invalid request attempt/slot')
        amounts(identity['bound'])
        if not sum(identity['bound'].values()):
            raise ValueError('A request needs a nonzero reservation; observed zero charge is a separate result')
        encoded = json.dumps(identity, sort_keys=True)
        with self.transaction():
            old = self.request(identity['request_id'])
            if old:
                if old['identity_json'] != encoded: raise ValueError('Request identity/reservation drift')
                return old
            if not self.ready(identity['pool_id'], identity['run_id'], identity['bound']): return None
            self.db.execute("INSERT INTO requests(id,pool_id,run_id,identity_json,phase,reserve_i,reserve_c) VALUES(?,?,?,?,'reserved',?,?)", (identity['request_id'], identity['pool_id'], identity['run_id'], encoded, identity['bound']['inference'], identity['bound']['compute']))
            self.event(identity['pool_id'], identity['request_id'], 'reserved', identity)
            return self.request(identity['request_id'])

    def claim(self, request_id, owner):
        label(owner)
        with self.transaction():
            row = self.request(request_id)
            if not row or row['phase'] != 'reserved': return False
            # C1 at pool level; reserved exposure is already counted in both caps.
            if self.db.execute("SELECT 1 FROM requests WHERE pool_id=? AND phase IN ('submitted','uncertain') LIMIT 1", (row['pool_id'],)).fetchone(): return False
            if self.db.execute('SELECT 1 FROM holds WHERE pool_id=? AND active=1', (row['pool_id'],)).fetchone(): return False
            for used, spec in [(self.exposure(row['pool_id']), json.loads(self.db.execute('SELECT spec FROM pools WHERE id=?', (row['pool_id'],)).fetchone()['spec'])), (self.exposure(row['pool_id'], row['run_id']), json.loads(self.db.execute('SELECT spec FROM runs WHERE pool_id=? AND run_id=?', (row['pool_id'], row['run_id'])).fetchone()['spec']))]:
                if any(used[key] > spec['caps'][key] for key in KEYS): return False
            changed = self.db.execute("UPDATE requests SET phase='submitted',owner=? WHERE id=? AND phase='reserved'", (owner, request_id)).rowcount
            if changed: self.event(row['pool_id'], request_id, 'submitted', {'owner': owner})
            return bool(changed)

    def uncertain(self, request_id, reason):
        with self.transaction():
            row = self.request(request_id)
            if row and row['phase'] == 'submitted':
                self.db.execute("UPDATE requests SET phase='uncertain' WHERE id=?", (request_id,))
                self.event(row['pool_id'], request_id, 'uncertain', {'reason': reason})

    def hold(self, pool, hold_id, source, active=True):
        label(hold_id)
        if not isinstance(source, str) or not source.strip(): raise ValueError('Hold/release source required')
        with self.transaction():
            self.db.execute('INSERT INTO holds VALUES(?,?,?,?) ON CONFLICT(pool_id,id) DO UPDATE SET active=excluded.active,source=excluded.source', (pool, hold_id, int(active), source))
            self.event(pool, None, 'external_hold' if active else 'external_hold_released', {'id': hold_id, 'source': source})

    def cancel_reserved(self, request_id):
        with self.transaction():
            row = self.request(request_id)
            if not row or row['phase'] != 'reserved': raise ValueError('Only a never-claimed reservation can be cancelled')
            self.db.execute("UPDATE requests SET phase='cancelled',actual_i=0,actual_c=0 WHERE id=?", (request_id,))
            self.event(row['pool_id'], request_id, 'cancelled_before_submit', {})

    def apply_receipt(self, envelope, raw_bytes):
        fields = {'schema', 'origin', 'identity', 'revision', 'previous_sha256', 'reason', 'source', 'provider_request_id', 'result', 'raw_sha256'}
        if set(envelope) != fields or envelope['schema'] != 'vi-billing-receipt/0.1' or envelope['origin'] != 'offline-fixture':
            raise ValueError('Only explicit fixture receipt evidence is supported')
        if hashlib_sha(raw_bytes) != envelope['raw_sha256']: raise ValueError('Raw evidence checksum mismatch')
        raw = json.loads(raw_bytes.decode('utf-8'))
        if raw != {'request_id': envelope['identity']['request_id'], 'provider_request_id': envelope['provider_request_id'], 'result': envelope['result']}:
            raise ValueError('Raw evidence identity/result mismatch')
        checked_receipt(envelope['result'])
        for key in ['inference_micros', 'compute_micros']:
            value = envelope['result'][key]
            if value is not None and value > MAX_AMOUNT: raise ValueError('Receipt amount out of range')
        if type(envelope['revision']) is not int or envelope['revision'] < 1 or not all(isinstance(envelope[k], str) and envelope[k].strip() for k in ['reason', 'source', 'provider_request_id']):
            raise ValueError('Receipt revision/source/reason required')
        encoded = json.dumps(envelope, sort_keys=True, allow_nan=False)
        sha = digest(envelope)
        with self.transaction():
            row = self.request(envelope['identity']['request_id'])
            if not row or json.loads(row['identity_json']) != envelope['identity']: raise ValueError('Receipt belongs to another request/run/pool')
            prior = self.db.execute('SELECT * FROM receipts WHERE request_id=? AND revision=?', (row['id'], envelope['revision'])).fetchone()
            if prior:
                if prior['sha256'] != sha or prior['raw_evidence'].encode('utf-8') != raw_bytes: raise ValueError('Conflicting receipt revision')
                return False
            if row['phase'] not in {'submitted', 'uncertain', 'settled'}: raise ValueError('No receipt for an unsubmitted/cancelled reservation')
            if envelope['revision'] != row['revision'] + 1 or envelope['previous_sha256'] != row['receipt_sha256']:
                raise ValueError('Receipt chain is stale or gapped')
            if row['revision']:
                old = json.loads(self.db.execute('SELECT envelope FROM receipts WHERE request_id=? AND revision=?', (row['id'], row['revision'])).fetchone()[0])
                if old['provider_request_id'] != envelope['provider_request_id']: raise ValueError('Provider request identity changed across revisions')
                before, after = old['result'], envelope['result']
                if before['status'] != 'unknown' and (before['status'], before['reward']) != (after['status'], after['reward']): raise ValueError('Known task result cannot change during billing correction')
                if any(before[k] is not None and after[k] is None for k in ['inference_micros', 'compute_micros']): raise ValueError('Known charges cannot be erased by a null revision')
                changed_cost = any(before[k] is not None and before[k] != after[k] for k in ['inference_micros', 'compute_micros'])
                if changed_cost and envelope['reason'] != 'provider-billing-adjustment': raise ValueError('Known cost change requires explicit billing adjustment')
            result = envelope['result']
            phase = 'uncertain' if result['status'] == 'unknown' or result['inference_micros'] is None or result['compute_micros'] is None else 'settled'
            self.db.execute('INSERT INTO receipts VALUES(?,?,?,?,?)', (row['id'], envelope['revision'], encoded, raw_bytes.decode('utf-8'), sha))
            self.db.execute('UPDATE requests SET phase=?,actual_i=?,actual_c=?,revision=?,receipt_sha256=? WHERE id=?', (phase, result['inference_micros'], result['compute_micros'], envelope['revision'], sha, row['id']))
            self.event(row['pool_id'], row['id'], 'receipt_revision', {'revision': envelope['revision'], 'sha256': sha, 'reason': envelope['reason']})
            spec = json.loads(self.db.execute('SELECT spec FROM pools WHERE id=?', (row['pool_id'],)).fetchone()['spec'])
            if any(self.exposure(row['pool_id'])[key] > spec['caps'][key] for key in KEYS):
                self.event(row['pool_id'], row['id'], 'observed_pool_overrun', {'actual': result})
            return True

    def close(self): self.db.close()


def hashlib_sha(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def receipt_evidence(identity, result, revision=1, previous=None, reason='receipt-reconciliation'):
    raw = json.dumps({'request_id': identity['request_id'], 'provider_request_id': 'fixture:' + identity['request_id'], 'result': result}, sort_keys=True).encode('utf-8')
    envelope = {'schema': 'vi-billing-receipt/0.1', 'origin': 'offline-fixture',
                'identity': identity, 'revision': revision, 'previous_sha256': previous,
                'reason': reason, 'source': 'durable-offline-fixture-receipt',
                'provider_request_id': 'fixture:' + identity['request_id'],
                'result': result, 'raw_sha256': hashlib_sha(raw)}
    return envelope, raw
