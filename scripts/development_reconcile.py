"""Narrow, audited cancellation of an intent proven blocked BEFORE any HTTP.

This never retries a provider request, releases a timeout/HTTP error, or edits a
charged receipt. It preserves the blocked intent under an archive routing key,
retains its raw receipt/trace, and makes the original unsubmitted slot available.
"""
import argparse
from contextlib import closing
import datetime as dt
import json
from pathlib import Path
import sqlite3

from development_contracts import digest, file_digest, load, sources
from provider_connectivity_v1 import write_new


def assert_pre_dispatch(requests,tools,outcome):
    if len(requests)!=1 or tools or outcome.get('valid') is not False or outcome.get('status')!='infra_error':
        raise ValueError('NOT_A_SINGLE_PRE_DISPATCH_INTENT')
    request=requests[0]; receipt=json.loads(request['receipt'])
    expected={'error':{'error':'DISPATCH_BLOCKED','exception_type':'CredentialError'}}
    loop=outcome.get('raw_loop') or {}
    if (receipt!=expected or request['phase']!='uncertain' or request['slot']!=1 or request['estimate_i'] is not None
            or loop.get('tool_calls')!=0 or loop.get('model_requests')!=1 or loop.get('stop_reason')!='provider_uncertain'):
        raise ValueError('PRE_NETWORK_PROOF_REQUIRED')
    return receipt


def cancelled_keys(trial,rid):
    return trial+'--blocked-intent-001',rid+'-blocked-intent-001'


def cancel(repo,plan_path,trial):
    repo=Path(repo); plan=load(plan_path); cfg=plan['config']; root=Path(cfg['state_root']).resolve()
    if plan['scope']!='development-batch' or trial not in {t['trial_id'] for t in plan['planned_trials']}:
        raise ValueError('FROZEN_DEVELOPMENT_TRIAL_REQUIRED')
    if sources(repo)!=plan['source_sha256']: raise ValueError('FROZEN_EXECUTION_SOURCE_DRIFT')
    # Frozen client has credential_scope/sdk_key checks before Popen, and no
    # CredentialError-producing operation after HTTP worker creation. Worker has
    # no credential scope. Existing gate-denial tests verify no socket/process.
    proof_sources={name:file_digest(repo/name) for name in [
        'scripts/terminal_agent_v1.py','scripts/scoped_credentials.py','scripts/terminal_provider_worker_v1.py']}
    if any(value!=plan['source_sha256'][name] for name,value in proof_sources.items()): raise ValueError('CLIENT_SOURCE_PROOF_DRIFT')
    database=root/'ledger.sqlite3'; run=plan['run_id']; folder=root/'runs'/run/trial
    destination=root/'runs'/run/'blocked-intents'/(trial+'--intent-001')
    if not folder.resolve().is_relative_to(root/'runs'/run) or not destination.resolve().is_relative_to(root/'runs'/run): raise ValueError('RECOVERY_PATH_ESCAPE')
    if any(p.is_symlink() for p in [folder,*folder.parents]) or destination.exists(): raise ValueError('RECOVERY_PATH_POLICY')
    backup=root/'recovery-checkpoints'/('before-'+run+'-'+trial)
    if backup.exists(): raise ValueError('RECOVERY_CHECKPOINT_EXISTS')
    backup.mkdir(parents=True)
    with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        identity=db.execute('SELECT * FROM identity').fetchone()
        stored=db.execute('SELECT contract FROM runs WHERE id=?',(run,)).fetchone()
        if not identity or identity['origin']!='real' or not stored or stored['contract']!=digest(plan): raise ValueError('REAL_RUN_IDENTITY_REQUIRED')
        requests=[dict(r) for r in db.execute('SELECT * FROM requests WHERE run=? AND trial=?',(run,trial))]
        tools=[dict(r) for r in db.execute('SELECT * FROM tools WHERE run=? AND trial=?',(run,trial))]
        outcome_row=db.execute('SELECT record,sha FROM development_outcomes WHERE run=? AND trial=?',(run,trial)).fetchone()
        if not outcome_row: raise ValueError('RAW_OUTCOME_REQUIRED')
        outcome=json.loads(outcome_row['record'])
        if digest(outcome)!=outcome_row['sha'] or load(folder/'outcome.json')!=outcome: raise ValueError('OUTCOME_LEDGER_DRIFT')
        receipt=assert_pre_dispatch(requests,tools,outcome); request=requests[0]
        if db.execute('SELECT 1 FROM corrections WHERE request=?',(request['id'],)).fetchone() or db.execute('SELECT 1 FROM settlements WHERE request=?',(request['id'],)).fetchone():
            raise ValueError('ALREADY_ACCOUNTED_REQUEST_NOT_ELIGIBLE')
        charged_before=[dict(r) for r in db.execute('SELECT * FROM requests WHERE id!=? ORDER BY id',(request['id'],))]
        with closing(sqlite3.connect(backup/'ledger.sqlite3')) as target: db.backup(target)
    archived_trial,archived_request=cancelled_keys(trial,request['id'])
    audit={'schema':'vi-pre-dispatch-cancellation/1','run_id':run,'trial_id':trial,'original_request_id':request['id'],
           'archived_trial_key':archived_trial,'archived_request_key':archived_request,
           'reason':'CredentialError DISPATCH_BLOCKED in frozen client before HTTP worker creation',
           'underlying_gate_reason':'not_retained_by_previous_error_mapping','provider_dispatches':0,'tool_executions':0,
           'api_charge_nano':0,'invoice':None,'reservation_released_nano':request['reserve_i'],
           'proof_source_sha256':proof_sources,'recovery_tool_sha256':file_digest(Path(__file__)),
           'backup_sha256':file_digest(backup/'ledger.sqlite3'),'original_request':request,'original_outcome':outcome,
           'raw_trace_sha256':file_digest(folder/'trajectory.jsonl'),'archived_folder':str(destination),
           'recorded_at_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    write_new(backup/'audit-before.json',audit)
    moved=False
    with closing(sqlite3.connect(database,isolation_level=None)) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('CREATE TABLE IF NOT EXISTS pre_dispatch_cancellations(id TEXT PRIMARY KEY, record TEXT NOT NULL)')
        db.execute('BEGIN IMMEDIATE'); db.execute('PRAGMA defer_foreign_keys=ON')
        try:
            current=db.execute('SELECT phase,receipt FROM requests WHERE id=?',(request['id'],)).fetchone()
            if current!=('uncertain',request['receipt']): raise ValueError('REQUEST_CHANGED_DURING_RECOVERY')
            db.execute('UPDATE trials SET id=?,state=? WHERE run=? AND id=?',(archived_trial,'pre_dispatch_blocked',run,trial))
            db.execute('UPDATE requests SET id=?,trial=?,phase=?,estimate_i=0 WHERE id=?',
                       (archived_request,archived_trial,'observed',request['id']))
            db.execute('UPDATE development_outcomes SET trial=? WHERE run=? AND trial=?',(archived_trial,run,trial))
            db.execute('INSERT INTO settlements VALUES (?,?,?,?)',(archived_request,0,digest(receipt),'proven-pre-network-cancellation-v1'))
            db.execute('INSERT INTO pre_dispatch_cancellations VALUES (?,?)',(request['id'],json.dumps(audit,ensure_ascii=False)))
            if db.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('RECOVERY_FOREIGN_KEY_FAILURE')
            destination.parent.mkdir(exist_ok=True); folder.rename(destination); moved=True
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK')
            if moved: destination.rename(folder)
            raise
        db.row_factory=sqlite3.Row
        charged_after=[dict(r) for r in db.execute('SELECT * FROM requests WHERE id!=? ORDER BY id',(archived_request,))]
        if charged_after!=charged_before: raise ValueError('UNRELATED_REQUEST_CHANGED')
    write_new(backup/'completed.json',{'audit':audit,'unrelated_requests_unchanged':True,'raw_receipt_preserved':True,
                                      'raw_outcome_preserved':True,'slot_rearmed_before_first_provider_dispatch':True})
    print('Pre-dispatch intent cancelled with checkpoint/audit; no provider request or model answer retried')
    return backup/'completed.json'


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--plan',type=Path,required=True); parser.add_argument('--trial',required=True)
    args=parser.parse_args(); cancel(Path(__file__).resolve().parents[1],args.plan,args.trial)
