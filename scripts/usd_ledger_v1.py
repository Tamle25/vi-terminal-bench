"""Atomic nano-USD pool/run/trial/request accounting. Estimates never release holds.

Origin is immutable: fixture DBs cannot be promoted to real USD runs. Local
invoice revisions are operator evidence, not provider-authenticated invoices.
"""
from contextlib import contextmanager
from decimal import Decimal, DecimalException
import json
from pathlib import Path
import sqlite3
import uuid

from pilot_contracts import digest
from scoped_credentials import sanitize


def nano(value):
    if type(value) is bool: raise ValueError('INVALID_USD_AMOUNT')
    try: amount = Decimal(str(value)) * 1000000000
    except DecimalException: raise ValueError('INVALID_USD_AMOUNT') from None
    if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value():
        raise ValueError('INVALID_USD_AMOUNT')
    return int(amount)


def checked_int(value):
    if type(value) is not int or not 0 <= value < 10**15:
        raise ValueError('INVALID_NANO_USD')
    return value


class Ledger:
    def __init__(self, path, *, account, pool_cap, origin):
        checked_int(pool_cap)
        if origin not in {'real', 'offline-fixture'} or not account or pool_cap <= 0:
            raise ValueError('POOL_IDENTITY_REQUIRED')
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path=Path(path).resolve()
        self.db = sqlite3.connect(path, timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='identity'").fetchone():
            existing=self.db.execute('SELECT schema,account,cap,origin FROM identity WHERE id=1').fetchone()
            if not existing or tuple(existing)!=('vi-usd-ledger/1.1',account,pool_cap,origin):
                self.db.close(); raise ValueError('POOL_IDENTITY_DRIFT')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS identity(id INTEGER PRIMARY KEY CHECK(id=1), schema TEXT, account TEXT, cap INTEGER, origin TEXT);
          CREATE TABLE IF NOT EXISTS external(id TEXT PRIMARY KEY, sha TEXT, held INTEGER, estimate INTEGER);
          CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, contract TEXT, cap_i INTEGER, cap_c INTEGER);
          CREATE TABLE IF NOT EXISTS trials(run TEXT REFERENCES runs(id), id TEXT, reserve_c INTEGER, invoice_c INTEGER, state TEXT, result TEXT, owner TEXT NOT NULL, estimate_c INTEGER, PRIMARY KEY(run,id));
          CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, run TEXT, trial TEXT, slot INTEGER, payload TEXT, reserve_i INTEGER, estimate_i INTEGER, phase TEXT, receipt TEXT, UNIQUE(run,trial,slot), FOREIGN KEY(run,trial) REFERENCES trials(run,id));
          CREATE TABLE IF NOT EXISTS corrections(request TEXT REFERENCES requests(id), revision INTEGER, amount INTEGER, evidence TEXT, PRIMARY KEY(request,revision));
          CREATE TABLE IF NOT EXISTS compute_corrections(run TEXT, trial TEXT, revision INTEGER, amount INTEGER, evidence TEXT, PRIMARY KEY(run,trial,revision), FOREIGN KEY(run,trial) REFERENCES trials(run,id));
          CREATE TABLE IF NOT EXISTS tools(run TEXT, trial TEXT, call_id TEXT, command_hash TEXT, phase TEXT, result TEXT, PRIMARY KEY(run,trial,call_id), FOREIGN KEY(run,trial) REFERENCES trials(run,id));
        ''')
        try:
            with self.atomic():
                self.db.execute('INSERT OR IGNORE INTO identity VALUES (1,?,?,?,?)', ('vi-usd-ledger/1.1', account, pool_cap, origin))
                row = self.db.execute('SELECT * FROM identity').fetchone()
                if tuple(row)[1:] != ('vi-usd-ledger/1.1', account, pool_cap, origin):
                    raise ValueError('POOL_IDENTITY_DRIFT')
        except BaseException:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    @contextmanager
    def atomic(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def import_external(self, identity, evidence, held, estimate=None):
        checked_int(held)
        if estimate is not None: checked_int(estimate)
        fingerprint = digest(evidence)
        with self.atomic():
            old = self.db.execute('SELECT sha,held,estimate FROM external WHERE id=?', (identity,)).fetchone()
            values = (fingerprint, held, estimate)
            if old and tuple(old) != values: raise ValueError('EXTERNAL_EVIDENCE_DRIFT')
            self.db.execute('INSERT OR IGNORE INTO external VALUES (?,?,?,?)', (identity, *values))

    def _charges(self, run=None):
        query = 'SELECT * FROM requests' + (' WHERE run=?' if run else '')
        requests = self.db.execute(query, (run,) if run else ()).fetchall()
        inference = 0
        for req in requests:
            invoice = self.db.execute('SELECT amount FROM corrections WHERE request=? ORDER BY revision DESC LIMIT 1', (req['id'],)).fetchone()
            inference += invoice[0] if invoice else max(req['reserve_i'], req['estimate_i'] or 0)
        trials = self.db.execute('SELECT * FROM trials' + (' WHERE run=?' if run else ''), (run,) if run else ()).fetchall()
        compute=0
        for trial in trials:
            invoice=self.db.execute('SELECT amount FROM compute_corrections WHERE run=? AND trial=? ORDER BY revision DESC LIMIT 1',(trial['run'],trial['id'])).fetchone()
            compute+=invoice[0] if invoice else max(trial['reserve_c'],trial['estimate_c'] or 0)
        external = sum(max(r['held'], r['estimate'] or 0) for r in self.db.execute('SELECT held,estimate FROM external')) if run is None else 0
        return inference, compute, external

    def inspect(self):
        i, c, e = self._charges()
        cap = self.db.execute('SELECT cap FROM identity').fetchone()[0]
        return {'currency': 'USD', 'origin': self.db.execute('SELECT origin FROM identity').fetchone()[0],
                'inference_exposure_nano': i, 'compute_exposure_nano': c, 'external_exposure_nano': e,
                'total_exposure_nano': i+c+e, 'available_nano': cap-i-c-e,
                'uncertain_requests': self.db.execute("SELECT COUNT(*) FROM requests WHERE phase IN ('submitted','uncertain')").fetchone()[0]}

    def create_run(self, run, contract, cap_i, cap_c):
        checked_int(cap_i); checked_int(cap_c)
        identity = digest(contract)
        with self.atomic():
            old = self.db.execute('SELECT contract,cap_i,cap_c FROM runs WHERE id=?', (run,)).fetchone()
            if old and tuple(old) != (identity, cap_i, cap_c): raise ValueError('RUN_DRIFT')
            self.db.execute('INSERT OR IGNORE INTO runs VALUES (?,?,?,?)', (run, identity, cap_i, cap_c))

    def _check(self, run, add_i=0, add_c=0):
        if self.inspect()['uncertain_requests']: raise ValueError('UNRECONCILED_REQUEST')
        if self.db.execute("SELECT 1 FROM tools WHERE phase='submitted'").fetchone(): raise ValueError('UNRECONCILED_TOOL')
        i, c, _ = self._charges(run)
        caps = self.db.execute('SELECT cap_i,cap_c FROM runs WHERE id=?', (run,)).fetchone()
        if not caps or i+add_i > caps['cap_i'] or c+add_c > caps['cap_c'] or add_i+add_c > self.inspect()['available_nano']:
            raise ValueError('BUDGET_DENIED')

    def claim_trial(self, run, trial, reserve_c):
        checked_int(reserve_c)
        with self.atomic():
            if self.db.execute("SELECT 1 FROM trials WHERE state='active'").fetchone(): raise ValueError('CONCURRENCY_DENIED')
            self._check(run, add_c=reserve_c)
            owner=uuid.uuid4().hex
            self.db.execute('INSERT INTO trials VALUES (?,?,?,?,?,NULL,?,NULL)', (run, trial, reserve_c, None, 'active',owner))
        return owner

    def check_trial_owner(self,run,trial,owner):
        row=self.db.execute('SELECT state,owner FROM trials WHERE run=? AND id=?',(run,trial)).fetchone()
        if not row or row['state']!='active' or row['owner']!=owner: raise ValueError('TRIAL_OWNER_MISMATCH')

    def record_compute_estimate(self,run,trial,amount):
        checked_int(amount)
        with self.atomic():
            changed=self.db.execute('UPDATE trials SET estimate_c=? WHERE run=? AND id=? AND estimate_c IS NULL',(amount,run,trial)).rowcount
            if changed!=1: raise ValueError('COMPUTE_ESTIMATE_REPLAY')

    def compute_invoice_revision(self,run,trial,revision,amount,evidence):
        checked_int(amount)
        if type(revision) is not int or revision<1 or not evidence: raise ValueError('INVOICE_EVIDENCE_REQUIRED')
        with self.atomic():
            old=self.db.execute('SELECT MAX(revision) FROM compute_corrections WHERE run=? AND trial=?',(run,trial)).fetchone()[0]
            if revision!=(old or 0)+1: raise ValueError('REVISION_ORDER')
            self.db.execute('INSERT INTO compute_corrections VALUES (?,?,?,?,?)',(run,trial,revision,amount,json.dumps(sanitize(evidence))))

    def claim_request(self, run, trial, slot, payload_hash, reserve_i, max_requests):
        checked_int(reserve_i)
        if type(slot) is not int or type(max_requests) is not int or not 1 <= slot <= max_requests:
            raise ValueError('REQUEST_LIMIT')
        rid = digest([run, trial, slot])
        with self.atomic():
            row = self.db.execute('SELECT state FROM trials WHERE run=? AND id=?', (run, trial)).fetchone()
            if not row or row['state'] != 'active': raise ValueError('TRIAL_NOT_ACTIVE')
            count = self.db.execute('SELECT COUNT(*) FROM requests WHERE run=? AND trial=?', (run, trial)).fetchone()[0]
            if slot != count+1: raise ValueError('REQUEST_REPLAY_OR_GAP')
            self._check(run, add_i=reserve_i)
            self.db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,NULL,?,NULL)', (rid, run, trial, slot, payload_hash, reserve_i, 'submitted'))
        return rid

    def record(self, rid, receipt, estimate, known_outcome):
        if estimate is not None: checked_int(estimate)
        with self.atomic():
            # Unknown usage or outcome cannot unlock another request.
            phase = 'observed' if known_outcome and estimate is not None else 'uncertain'
            changed = self.db.execute("UPDATE requests SET phase=?,receipt=?,estimate_i=? WHERE id=? AND phase='submitted'",
                                      (phase, json.dumps(sanitize(receipt), ensure_ascii=False), estimate, rid)).rowcount
            if changed != 1: raise ValueError('RECEIPT_REPLAY_OR_UNKNOWN_REQUEST')

    def invoice_revision(self, rid, revision, amount, evidence):
        checked_int(amount)
        if type(revision) is not int or revision < 1 or not evidence: raise ValueError('INVOICE_EVIDENCE_REQUIRED')
        with self.atomic():
            row = self.db.execute('SELECT MAX(revision) FROM corrections WHERE request=?', (rid,)).fetchone()
            if revision != (row[0] or 0)+1: raise ValueError('REVISION_ORDER')
            self.db.execute('INSERT INTO corrections VALUES (?,?,?,?)', (rid, revision, amount, json.dumps(sanitize(evidence))))
        # Billing correction alone never proves an uncertain provider outcome.

    def tool_intent(self, run, trial, call_id, command_hash):
        with self.atomic():
            self.db.execute('INSERT INTO tools VALUES (?,?,?,?,?,NULL)', (run, trial, call_id, command_hash, 'submitted'))

    def tool_result(self, run, trial, call_id, result):
        with self.atomic():
            count = self.db.execute("UPDATE tools SET phase='observed',result=? WHERE run=? AND trial=? AND call_id=? AND phase='submitted'",
                                    (json.dumps(sanitize(result), ensure_ascii=False), run, trial, call_id)).rowcount
            if count != 1: raise ValueError('TOOL_RESULT_REPLAY')

    def finish(self, run, trial, result):
        with self.atomic():
            changed = self.db.execute("UPDATE trials SET state='finished',result=? WHERE run=? AND id=? AND state='active'",
                                      (json.dumps(sanitize(result), ensure_ascii=False), run, trial)).rowcount
            if changed != 1: raise ValueError('TRIAL_REPLAY')
