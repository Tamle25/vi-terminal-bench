"""Versioned provisional settlement overlay, restricted to development DBs.

Old fixture/real DBs are rejected before DDL. Known, fully mapped provider usage
can release unused reservation; unknown retains the full hold and blocks dispatch.
"""
from pathlib import Path
import sqlite3

from development_contracts import conservative_cost
from pilot_contracts import digest
from usd_ledger_v1 import Ledger, nano

POLICY='observed-usage-conservative-input-v1'


class DevelopmentLedger(Ledger):
    def __init__(self,path,*,account,pool_cap,origin):
        path=Path(path)
        if path.exists():
            from contextlib import closing
            with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as check:
                found=check.execute("SELECT 1 FROM sqlite_master WHERE name='development_policy'").fetchone()
                if not found: raise ValueError('DEVELOPMENT_NAMESPACE_REQUIRED')
                row=check.execute('SELECT policy FROM development_policy WHERE id=1').fetchone()
                if row!=(POLICY,): raise ValueError('SETTLEMENT_POLICY_DRIFT')
        super().__init__(path,account=account,pool_cap=pool_cap,origin=origin)
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS development_policy(id INTEGER PRIMARY KEY CHECK(id=1),policy TEXT);
          CREATE TABLE IF NOT EXISTS settlements(request TEXT PRIMARY KEY REFERENCES requests(id),amount INTEGER,receipt_sha TEXT,policy TEXT);
          CREATE TABLE IF NOT EXISTS development_outcomes(run TEXT,trial TEXT,record TEXT,sha TEXT,PRIMARY KEY(run,trial),FOREIGN KEY(run,trial) REFERENCES trials(run,id));
          INSERT OR IGNORE INTO development_policy VALUES (1,'observed-usage-conservative-input-v1');
        ''')

    def _charges(self,run=None):
        i,c,e=super()._charges(run)
        # _charges can be called during initialization before overlay DDL exists.
        if not self.db.execute("SELECT 1 FROM sqlite_master WHERE name='settlements'").fetchone(): return i,c,e
        query='SELECT r.*,s.amount FROM requests r JOIN settlements s ON r.id=s.request WHERE r.phase="observed"'
        if run is not None: query+=' AND r.run=?'
        for row in self.db.execute(query,(run,) if run else ()):
            if self.db.execute('SELECT 1 FROM corrections WHERE request=?',(row['id'],)).fetchone(): continue
            i-=max(row['reserve_i'],row['estimate_i'] or 0)
            i+=row['amount']
        return i,c,e

    def record_provider(self,rid,receipt,cfg):
        amount=conservative_cost(receipt,cfg)
        super().record(rid,receipt,amount,amount is not None)
        if amount is not None:
            with self.atomic():
                self.db.execute('INSERT INTO settlements VALUES (?,?,?,?)',(rid,amount,digest(receipt),POLICY))
        return amount

    def add_margin(self):
        self.import_external('stage11-correction-margin',{'kind':'development-correction-reserve','policy':POLICY},nano('.10'))

    def complete_outcome(self,run,trial,record):
        import json
        from scoped_credentials import sanitize
        record=sanitize(record)
        origin=self.db.execute('SELECT origin FROM identity').fetchone()[0]
        if record.get('data_origin')!=('real-model' if origin=='real' else 'offline-fixture') or record.get('run_id')!=run or record.get('trial_id')!=trial:
            raise ValueError('OUTCOME_ORIGIN_OR_IDENTITY')
        with self.atomic():
            row=self.db.execute('SELECT state FROM trials WHERE run=? AND id=?',(run,trial)).fetchone()
            if not row or row['state']!='finished': raise ValueError('TRIAL_NOT_FINISHED')
            self.db.execute('INSERT INTO development_outcomes VALUES (?,?,?,?)',(run,trial,json.dumps(record,ensure_ascii=False),digest(record)))

    def outcomes(self,run):
        import json
        result={}
        for row in self.db.execute('SELECT trial,record,sha FROM development_outcomes WHERE run=?',(run,)):
            value=json.loads(row['record'])
            if digest(value)!=row['sha']: raise ValueError('OUTCOME_LEDGER_DRIFT')
            result[row['trial']]=value
        return result
