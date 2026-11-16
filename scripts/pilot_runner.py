"""Durable SIMULATION ONLY scheduler/ledger. No real provider or credentials loader."""
import argparse
import contextlib
import hashlib
import json
import random
import sqlite3
import time
import uuid
from pathlib import Path
from pilot_contracts import digest

TERMINAL={'completed','agent_failure','retryable_infra_error','verifier_error','cancelled'}
RETRYABLE={'retryable_infra_error','verifier_error'}


class SimulatedCrash(RuntimeError):pass


def money(value):
    if type(value) is not int or value<0:raise ValueError('Simulation cost must be nonnegative integer micro-units')
    return value


def simulation_plan(preview,roster,snapshot_id,run_id='stage4-offline',seed=20261112):
    if preview.get('kind')!='offline-dry-run-not-executable':raise ValueError('Expected offline preview')
    trials=[]
    for original in preview['planned_trials']:
        row=dict(original);row.update(trial_id='simulation-'+run_id+'--'+original['trial_id'],configuration='simulation-'+original['configuration'],configuration_sha256=digest({'origin':'simulation','source':original['configuration_sha256']}),harbor_task_checksum='simulation-not-harbor:'+original['payload_sha256'])
        row['attempts']=[{'attempt':n,'job_name':f'simulation-{run_id}-a{n}'} for n in range(1,4)]
        trials.append(row)
    return {'schema':'vi-pilot-simulation/0.1','kind':'simulation','run_id':run_id,'snapshot_id':snapshot_id,'task_manifest':roster,'planned_trials':trials,'currency':'SIM_USD','price_source':'synthetic-fixture-v1-not-provider-pricing','seed':seed,'caps':{'inference':200000,'compute':20000},'reservation':{'inference':2000,'compute':200},'max_attempts':3,'model_calls':0}


def connect(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=5,isolation_level=None);db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA foreign_keys=ON')
    return db


class Store:
    def __init__(self,path,plan,clock=time.time):
        if plan.get('kind')!='simulation' or plan.get('schema')!='vi-pilot-simulation/0.1' or plan.get('currency')!='SIM_USD' or plan.get('max_attempts')!=3:raise ValueError('Only isolated simulation plans are supported')
        ids=[row['trial_id'] for row in plan['planned_trials']]
        if not ids or len(ids)!=len(set(ids)):raise ValueError('Invalid planned identities')
        for value in [*plan['caps'].values(),*plan['reservation'].values()]:money(value)
        self.db=connect(path);self.plan=plan;self.clock=clock
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS trials(id TEXT PRIMARY KEY,position INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(trial_id TEXT NOT NULL REFERENCES trials(id),number INTEGER NOT NULL,phase TEXT NOT NULL,request_id TEXT NOT NULL UNIQUE,reserve_i INTEGER NOT NULL,reserve_c INTEGER NOT NULL,actual_i INTEGER,actual_c INTEGER,owner TEXT,lease_until REAL,response TEXT,PRIMARY KEY(trial_id,number));
        CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,at REAL NOT NULL,trial_id TEXT,attempt INTEGER,event TEXT NOT NULL,details TEXT NOT NULL);
        ''')
        try:
            with self.transaction():
                old=self.db.execute("SELECT value FROM meta WHERE key='plan_hash'").fetchone()
                if old and old['value']!=digest(plan):raise ValueError('Resume refused: plan/snapshot/profile/budget changed')
                if not old:
                    self.db.execute("INSERT INTO meta VALUES('plan_hash',?)",(digest(plan),))
                    order=list(ids);random.Random(plan['seed']).shuffle(order)
                    self.db.executemany('INSERT INTO trials VALUES(?,?)',[(tid,index) for index,tid in enumerate(order)])
                    self.event(None,None,'run_created',{'kind':'simulation','currency':'SIM_USD'})
        except BaseException:
            self.db.close();raise

    @contextlib.contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:yield;self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise

    def event(self,tid,number,name,details=None):
        self.db.execute('INSERT INTO events(at,trial_id,attempt,event,details) VALUES(?,?,?,?,?)',(self.clock(),tid,number,name,json.dumps(details or {},sort_keys=True,allow_nan=False)))

    def latest(self,tid):return self.db.execute('SELECT * FROM attempts WHERE trial_id=? ORDER BY number DESC LIMIT 1',(tid,)).fetchone()

    def exposure(self):
        row=self.db.execute('SELECT coalesce(sum(coalesce(actual_i,reserve_i)),0) i,coalesce(sum(coalesce(actual_c,reserve_c)),0) c FROM attempts').fetchone()
        return {'inference':row['i'],'compute':row['c']}

    def reserve(self,tid):
        with self.transaction():
            if not self.db.execute('SELECT 1 FROM trials WHERE id=?',(tid,)).fetchone():raise ValueError('Unplanned trial')
            last=self.latest(tid)
            if self.db.execute("SELECT 1 FROM attempts WHERE phase='uncertain' LIMIT 1").fetchone():return None
            if last and last['phase']=='reserved':return dict(last)
            if last and (last['phase'] not in RETRYABLE or last['number']>=3):return None
            if self.db.execute("SELECT 1 FROM attempts WHERE phase='uncertain' LIMIT 1").fetchone():return None
            used=self.exposure();reserve=self.plan['reservation']
            if any(used[key]+reserve[key]>self.plan['caps'][key] for key in used):return None
            number=last['number']+1 if last else 1
            request=digest({'run':self.plan['run_id'],'trial':tid,'attempt':number})
            self.db.execute("INSERT INTO attempts(trial_id,number,phase,request_id,reserve_i,reserve_c) VALUES(?,?,'reserved',?,?,?)",(tid,number,request,reserve['inference'],reserve['compute']))
            self.event(tid,number,'reserved',reserve)
            return dict(self.latest(tid))

    def submit(self,tid,number,owner,lease_sec=30):
        with self.transaction():
            if self.db.execute("SELECT 1 FROM attempts WHERE phase='uncertain' LIMIT 1").fetchone() or any(self.exposure()[key]>self.plan['caps'][key] for key in self.plan['caps']):return False
            changed=self.db.execute("UPDATE attempts SET phase='submitted',owner=?,lease_until=? WHERE trial_id=? AND number=? AND phase='reserved'",(owner,self.clock()+lease_sec,tid,number)).rowcount
            if changed:self.event(tid,number,'submitted',{'owner':owner})
            return bool(changed)

    def mark_uncertain(self,tid,number,reason):
        with self.transaction():
            row=self.latest(tid)
            if row['number']==number and row['phase']=='submitted':
                self.db.execute("UPDATE attempts SET phase='uncertain' WHERE trial_id=? AND number=?",(tid,number));self.event(tid,number,'uncertain',{'reason':reason})

    def settle(self,tid,number,response):
        allowed={'status','reward','inference_micros','compute_micros'}
        if set(response)!=allowed:raise ValueError('Fake receipt schema mismatch')
        status=response['status']
        if status not in {'completed','agent_failure','retryable_infra_error','verifier_error','unknown'}:raise ValueError('Unclassified receipt')
        if status=='completed' and (type(response['reward']) is not int or response['reward'] not in (0,1)):raise ValueError('Completed receipt needs integer reward')
        if status=='agent_failure' and (type(response['reward']) is not int or response['reward']!=0):raise ValueError('Agent failure reward must be integer zero')
        if status not in {'completed','agent_failure'} and response['reward'] is not None:raise ValueError('Infrastructure/unknown result must have null reward')
        i,c=response['inference_micros'],response['compute_micros']
        if i is not None:money(i)
        if c is not None:money(c)
        with self.transaction():
            row=self.db.execute('SELECT * FROM attempts WHERE trial_id=? AND number=?',(tid,number)).fetchone()
            if row is None or row['phase']=='reserved':raise ValueError('Cannot settle an unsubmitted attempt')
            encoded=json.dumps(response,sort_keys=True,allow_nan=False)
            if row['phase'] in TERMINAL:
                if row['response']!=encoded:raise ValueError('Conflicting terminal receipt')
                return
            if row['response']==encoded and row['phase']=='uncertain':return
            if i is not None and i>row['reserve_i'] or c is not None and c>row['reserve_c']:
                self.event(tid,number,'reservation_overrun',response)
            phase='uncertain' if status=='unknown' or i is None or c is None else status
            self.db.execute('UPDATE attempts SET phase=?,actual_i=?,actual_c=?,response=? WHERE trial_id=? AND number=?',(phase,i,c,encoded,tid,number))
            self.event(tid,number,'settled' if phase!='uncertain' else 'uncertain_receipt',response)
            if any(self.exposure()[key]>self.plan['caps'][key] for key in self.plan['caps']):self.event(tid,number,'budget_overrun_observed',response)

    def confirm_not_submitted(self,tid,receipt,provider):
        # Only the fake adapter has authoritative absence; never infer this from real provider eventual consistency.
        with self.transaction():
            row=self.latest(tid)
            if row is None or row['phase']!='uncertain' or receipt!={'kind':'simulation-authoritative-not-received','request_id':row['request_id']} or provider.lookup(row['request_id']) is not None:raise ValueError('Explicit authoritative fake absence receipt required')
            self.db.execute("UPDATE attempts SET phase='reserved',owner=NULL,lease_until=NULL WHERE trial_id=? AND number=?",(tid,row['number']))
            self.event(tid,row['number'],'reconciled_not_received',receipt)

    def cancel_reserved(self,tid):
        with self.transaction():
            row=self.latest(tid)
            if not row or row['phase']!='reserved':raise ValueError('Only never-submitted reservation can be cancelled/refunded')
            self.db.execute("UPDATE attempts SET phase='cancelled',actual_i=0,actual_c=0 WHERE trial_id=? AND number=?",(tid,row['number']))
            self.event(tid,row['number'],'cancelled_before_submission')

    def summary(self):
        attempts=[dict(row) for row in self.db.execute('SELECT * FROM attempts ORDER BY trial_id,number')]
        finals=[self.latest(row['id']) for row in self.db.execute('SELECT id FROM trials ORDER BY position')]
        unfinished=sum(row is None or row['phase'] not in {'completed','agent_failure','cancelled'} and not(row['phase'] in RETRYABLE and row['number']==3) for row in finals)
        return {'kind':'simulation-not-model-evaluation','currency':'SIM_USD','price_source':self.plan['price_source'],'planned_trials':len(finals),'attempts':len(attempts),'unfinished_trials':unfinished,'valid_final_trials':sum(row is not None and row['phase'] in {'completed','agent_failure'} for row in finals),'exhausted_infrastructure_trials':sum(row is not None and row['phase'] in RETRYABLE and row['number']==3 for row in finals),'uncertain_attempts':sum(row['phase']=='uncertain' for row in attempts),'exposure_micro_units':self.exposure(),'known_charges_micro_units':{'inference':sum(row['actual_i'] or 0 for row in attempts),'compute':sum(row['actual_c'] or 0 for row in attempts)},'unknown_cost_attempts':sum(row['actual_i'] is None or row['actual_c'] is None for row in attempts),'caps_micro_units':self.plan['caps'],'model_calls':0}


class FakeProvider:
    """Durable deterministic fixture provider, including explicit reconciliation receipts."""
    def __init__(self,path,scenarios=None):
        self.db=connect(path);self.scenarios=scenarios or {}
        self.db.executescript('CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,response TEXT NOT NULL); CREATE TABLE IF NOT EXISTS calls(sequence INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL); CREATE TABLE IF NOT EXISTS receipts(sequence INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL,response TEXT NOT NULL); CREATE TABLE IF NOT EXISTS meta(value TEXT NOT NULL);')
        old=self.db.execute('SELECT value FROM meta').fetchone()
        if old and old['value']!=digest(self.scenarios):self.db.close();raise ValueError('Fake provider fixture changed')
        if not old:self.db.execute('INSERT INTO meta VALUES(?)',(digest(self.scenarios),))
    def lookup(self,key):
        row=self.db.execute('SELECT response FROM receipts WHERE id=? ORDER BY sequence DESC LIMIT 1',(key,)).fetchone() or self.db.execute('SELECT response FROM requests WHERE id=?',(key,)).fetchone()
        return json.loads(row['response']) if row else None
    def dispatch(self,key,tid,number):
        self.db.execute('INSERT INTO calls(id) VALUES(?)',(key,))
        response=self.scenarios.get(f'{tid}:{number}',{'status':'completed','reward':hashlib.sha256(tid.encode()).digest()[0]%2,'inference_micros':1000,'compute_micros':100})
        self.db.execute('INSERT OR IGNORE INTO requests VALUES(?,?)',(key,json.dumps(response,sort_keys=True,allow_nan=False)))
        return self.lookup(key)
    def resolve(self,key,response):
        if not self.db.execute('SELECT 1 FROM requests WHERE id=?',(key,)).fetchone():raise ValueError('No provider request to reconcile')
        self.db.execute('INSERT INTO receipts(id,response) VALUES(?,?)',(key,json.dumps(response,sort_keys=True,allow_nan=False)))
    def call_count(self):return self.db.execute('SELECT count(*) n FROM calls').fetchone()['n']


class Runner:
    def __init__(self,store,provider):self.store=store;self.provider=provider;self.owner=uuid.uuid4().hex
    def run_one(self,tid,crash=None):
        s=self.store;row=s.latest(tid)
        if row and row['phase'] in {'submitted','uncertain'}:
            if row['phase']=='submitted' and row['lease_until']>s.clock():return 'active-lease'
            s.mark_uncertain(tid,row['number'],'expired submission; reconcile before any resend')
            receipt=self.provider.lookup(row['request_id'])
            if receipt is None:return 'uncertain-no-receipt'
            s.settle(tid,row['number'],receipt);return 'reconciled'
        row=s.reserve(tid)
        if row is None:return 'blocked-or-terminal'
        if crash=='after_reserve':raise SimulatedCrash(crash)
        if not s.submit(tid,row['number'],self.owner):return 'claim-lost'
        if crash=='after_submit':raise SimulatedCrash(crash)
        receipt=self.provider.dispatch(row['request_id'],tid,row['number'])
        if crash=='after_provider':raise SimulatedCrash(crash)
        s.settle(tid,row['number'],receipt)
        return 'dispatched'
    def run(self,max_dispatches=None):
        before=self.provider.call_count()
        for _ in range(4):
            changed=False
            for item in self.store.db.execute('SELECT id FROM trials ORDER BY position').fetchall():
                if max_dispatches is not None and self.provider.call_count()-before>=max_dispatches:return
                old=self.store.latest(item['id']);old_signature=(old['phase'],old['number']) if old else None
                self.run_one(item['id'])
                new=self.store.latest(item['id']);changed|=((new['phase'],new['number']) if new else None)!=old_signature
            if not changed:break


def export(store,provider,destination):
    destination.mkdir(parents=True,exist_ok=True);by_id={r['trial_id']:r for r in store.plan['planned_trials']};normalized=[];unresolved=[]
    raw_folder=destination/'raw';raw_folder.mkdir(exist_ok=True)
    for index,row in enumerate(store.db.execute('SELECT * FROM attempts ORDER BY trial_id,number'),1):
        raw=dict(row);path=raw_folder/f'attempt-{index:04d}.json';path.write_text(json.dumps(raw,indent=2)+'\n',encoding='utf-8')
        response=json.loads(row['response']) if row['response'] else None
        if not response or response['status']=='unknown' or row['phase']=='cancelled':unresolved.append({'trial_id':row['trial_id'],'attempt':row['number'],'phase':row['phase']});continue
        original=by_id[row['trial_id']];status={'completed':'completed','agent_failure':'agent_error','retryable_infra_error':'infra_error','verifier_error':'verifier_error'}[response['status']]
        keys=['trial_id','task_id','family_id','track','skill','language','configuration','repeat','payload_sha256','instruction_sha256','configuration_sha256','harbor_task_checksum']
        normalized.append({**{key:original[key] for key in keys},'attempt':row['number'],'status':status,'reward':response['reward'],'duration_sec':0,'cost_usd':None,'raw_reference':str(path),'data_origin':'simulation','simulation_cost_micro_units':{'inference':row['actual_i'],'compute':row['actual_c']}})
    (destination/'trials.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in normalized),encoding='utf-8')
    (destination/'events.jsonl').write_text(''.join(json.dumps(dict(row))+'\n' for row in store.db.execute('SELECT * FROM events ORDER BY sequence')),encoding='utf-8')
    report={**store.summary(),'fake_dispatch_calls':provider.call_count(),'unique_fake_requests':provider.db.execute('SELECT count(*) n FROM requests').fetchone()['n'],'unresolved':unresolved}
    (destination/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return normalized,report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['simulation','model'],default='simulation');p.add_argument('--plan',type=Path,required=True);p.add_argument('--state-dir',type=Path,required=True);p.add_argument('--scenarios',type=Path);p.add_argument('--max-dispatches',type=int);a=p.parse_args()
    if a.mode!='simulation':raise ValueError('Real model dispatch is not implemented/enabled; no API call made')
    plan=json.loads(a.plan.read_text(encoding='utf-8'));scenarios=json.loads(a.scenarios.read_text()) if a.scenarios else {}
    s=Store(a.state_dir/'ledger.sqlite3',plan);provider=FakeProvider(a.state_dir/'fake-provider.sqlite3',scenarios);Runner(s,provider).run(a.max_dispatches)
    _,report=export(s,provider,a.state_dir/'export');print(json.dumps(report));s.db.close();provider.db.close()
