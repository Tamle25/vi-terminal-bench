"""Internal six-task benchmark CLI: validate, plan, run, resume-unstarted, report.

Only new development scopes admit pending human review. Every provider request
uses the real gate, persistent shared cap and a durable request claim.
"""
import argparse
import csv
from contextlib import closing
import io
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import statistics
import sys
import time
import uuid
import zipfile

from capture_runtime_development import capture
from development_agent import DevelopmentGate, run_loop
from development_contracts import (TASKS, SCOPES, backend_config, digest, file_digest, load, planned,
                                   public_inputs, registry, request_reserve, sources, validate_config)
from development_ledger import DevelopmentLedger
from pilot_contracts import snapshot
from preflight import filesystem_probe
from provider_connectivity_v1 import write_new
from scoped_credentials import sanitize, sanitized_error
from terminal_agent_v1 import OpenAIResponses
from development_sandbox import DevelopmentSandbox as DockerSandbox
from terminal_sandbox_v1 import bounded
from development_verifier import verify
from usd_ledger_v1 import nano

REPO=Path(__file__).resolve().parents[1]


def safe_error(exc):
    value=exc.args[0] if isinstance(exc,ValueError) and exc.args else ''
    return value if isinstance(value,str) and re.fullmatch('[A-Z_]{1,150}',value) else sanitized_error(exc)['error']


def profile_for(cfg):
    matches=[p for p in load(REPO/'configs/development-runtime-profiles.json')['profiles'] if p['id']==cfg['runtime_profile']]
    if len(matches)!=1: raise ValueError('RUNTIME_PROFILE_REQUIRED')
    return matches[0]


def native_root(cfg):
    root=Path(cfg['state_root'])
    if not root.is_absolute() or '..' in root.parts or str(root.resolve()).startswith(('/mnt/','/tmp/','/var/tmp/')):
        raise ValueError('PERSISTENT_NATIVE_STATE_REQUIRED')
    filesystem_probe(root)
    if any(p.is_symlink() for p in [root,*root.parents]): raise ValueError('STATE_SYMLINK')
    return root


def image_check(images):
    snap=snapshot(REPO)
    if set(images)!=set(TASKS): raise ValueError('SIX_TASK_IMAGES_REQUIRED')
    for tid,pair in images.items():
        if set(pair)!={'agent','verifier'}: raise ValueError('IMAGE_ROLES')
        for role,image in pair.items():
            if not re.fullmatch('sha256:[0-9a-f]{64}',image): raise ValueError('IMAGE_ID_REQUIRED')
            proc=bounded(['docker','image','inspect',image],5)
            if proc['exit_code'] or proc['timed_out']: raise ValueError('IMAGE_NOT_AVAILABLE')
            rows=json.loads(proc['stdout_bytes']); labels=rows[0]['Config'].get('Labels',{})
            if len(rows)!=1 or rows[0]['Id']!=image or labels.get('vi-bench.role')!=role or labels.get('vi-bench.payload')!=snap['tasks'][tid]['payload_sha256']:
                raise ValueError('IMAGE_PROVENANCE_DRIFT')


def create_backend(cfg,tid,images,run):
    params=backend_config(cfg,registry(REPO)[tid]); image=images[tid]['agent']
    args=DockerSandbox.create_args(image,run,params); name='vi-stage11-'+uuid.uuid4().hex
    args[2:2]=['--name',name]
    proc=bounded(args,10); cid=proc['stdout_bytes'].decode('ascii',errors='ignore').strip()
    if proc['exit_code'] or proc['timed_out'] or not re.fullmatch('[0-9a-f]{64}',cid):
        # Recover ownership after a create response loss, without sending anything twice.
        check=bounded(['docker','inspect',name],5)
        if check['exit_code']==0 and not check['timed_out']:
            rows=json.loads(check['stdout_bytes'])
            if len(rows)==1 and rows[0]['Config'].get('Labels',{}).get('vi-bench.run')==run:
                DockerSandbox(rows[0]['Id'],run,image,params).destroy()
        raise ValueError('CONTAINER_CREATE_FAILED')
    backend=DockerSandbox(cid,run,image,params)
    try:
        proc=bounded(['docker','start',cid],10)
        if proc['exit_code'] or proc['timed_out']: raise ValueError('CONTAINER_START_FAILED')
        backend.inspect(); return backend
    except BaseException:
        backend.destroy(); raise


def validate_containers(cfg,output):
    validate_config(cfg); native_root(cfg); filesystem_probe(output.parent)
    if output.exists(): raise ValueError('VALIDATION_OUTPUT_EXISTS')
    output.mkdir(); initial=snapshot(REPO); images={}; cases=[]
    attest=capture(REPO,profile_for(cfg),'stage11-container-validation',ttl_sec=900)
    if not attest.get('ready'): raise ValueError('RUNTIME_PREFLIGHT_FAILED')
    public_inputs(REPO)
    for tid in TASKS:
        images[tid]={}; folder=output/tid; folder.mkdir()
        for role,context in [('agent','environment'),('verifier','tests')]:
            print('Building '+tid+' '+role,flush=True)
            iid=folder/(role+'.iid')
            proc=bounded(['docker','build','--iidfile',str(iid),'--label','vi-bench.payload='+initial['tasks'][tid]['payload_sha256'],
                          '--label','vi-bench.role='+role,str(REPO/'tasks'/tid/context)],300)
            if proc['exit_code'] or proc['timed_out'] or not iid.exists():
                write_new(folder/(role+'-build-error.json'),{'exit_code':proc['exit_code'],'timed_out':proc['timed_out'],
                            'stdout':proc['stdout_bytes'].decode('utf-8',errors='replace'),'stderr':proc['stderr_bytes'].decode('utf-8',errors='replace')})
                raise ValueError('IMAGE_BUILD_FAILED')
            images[tid][role]=iid.read_text().strip()
        for mode in ['oracle','nop']:
            case=folder/mode; case.mkdir(); backend=create_backend(cfg,tid,images,'stage11-validation-'+tid+'-'+mode)
            try:
                observation=backend.inspect()
                if mode=='oracle':
                    code=(REPO/'tasks'/tid/'solution/solve.py').read_text(encoding='utf-8')
                    command='python -I -c '+shlex.quote(code)+' --root /app'
                    result=backend.command(command,cfg['command_timeout_sec'])
                    if result['exit_code'] or result['timed_out']: raise ValueError('ORACLE_EXECUTION_FAILED')
                else: result=backend.command('true',cfg['command_timeout_sec'])
                if tid=='b005-vietnamese-collation':
                    observed=backend.command("node -e 'console.log(JSON.stringify({node:process.versions.node,icu:process.versions.icu,cldr:process.versions.cldr}))'",10)
                    node=json.loads(observed['stdout'])
                    if node!={'node':'22.14.0','icu':'76.1','cldr':'46.0'}: raise ValueError('COLLATION_RUNTIME_DRIFT')
                backend.collect(case/'artifacts')
                grade=verify(case/'artifacts',output,images[tid]['verifier'],'stage11-validation-'+tid)
                expected=1 if mode=='oracle' else 0
                row={'task_id':tid,'mode':mode,'expected_reward':expected,'observed':grade,'backend':observation,
                     'artifact_sha256':{p.relative_to(case/'artifacts').as_posix():file_digest(p) for p in (case/'artifacts').rglob('*') if p.is_file()}}
                write_new(case/'result.json',row); cases.append(row)
                if grade['status']!='verified' or grade['reward']!=expected: raise ValueError('VERIFIER_BACKEND_MISMATCH')
            finally: backend.destroy()
            print(tid+' '+mode+' reward='+str(grade['reward']),flush=True)
    if snapshot(REPO)!=initial: raise ValueError('TASK_SOURCE_CHANGED_DURING_VALIDATION')
    report={'schema':'vi-development-container-validation/1','origin':'real-docker-no-model','passed':True,
            'snapshot':initial,'source_sha256':sources(REPO),'config_sha256':digest(cfg),'images':images,'cases':cases,
            'runtime_attestation':attest,'provider_requests':0,'credential_read':False,'compute_cost_status':'not_metered'}
    write_new(output/'validation.json',report)
    return report


def validation_for(cfg,path):
    proof=load(path)
    if proof.get('origin')!='real-docker-no-model' or not proof.get('passed') or len(proof.get('cases',[]))!=12:
        raise ValueError('REAL_CONTAINER_VALIDATION_REQUIRED')
    if proof['snapshot']!=snapshot(REPO) or proof['source_sha256']!=sources(REPO) or proof['config_sha256']!=digest(cfg):
        raise ValueError('CONTAINER_VALIDATION_DRIFT')
    expected={(tid,mode) for tid in TASKS for mode in ['oracle','nop']}
    observed={(row['task_id'],row['mode']) for row in proof['cases'] if row['observed']['status']=='verified' and row['observed']['reward']==row['expected_reward']}
    if observed!=expected: raise ValueError('VALIDATION_COVERAGE')
    return proof


def smoke_for(cfg,path):
    evidence=load(path)
    location=Path(path).parent
    plan_path=location/'plan.json'
    if not plan_path.exists(): plan_path=location.parent/'plan.json'
    smoke_plan=load(plan_path)
    if not evidence.get('technical_smoke_passed') or smoke_plan['scope']!='development-smoke' or smoke_plan['config']!=cfg or smoke_plan['source_sha256']!=sources(REPO):
        raise ValueError('MATCHING_MODEL_SMOKE_REQUIRED')
    with closing(sqlite3.connect((Path(cfg['state_root'])/'ledger.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)) as db:
        stored=db.execute('SELECT contract FROM runs WHERE id=?',(smoke_plan['run_id'],)).fetchone()
        identity=db.execute('SELECT origin FROM identity').fetchone()
        rows=db.execute('SELECT trial,record,sha FROM development_outcomes WHERE run=?',(smoke_plan['run_id'],)).fetchall()
    if not stored or stored[0]!=digest(smoke_plan) or identity!=('real',): raise ValueError('SMOKE_LEDGER_IDENTITY')
    outcomes={tid:json.loads(record) for tid,record,sha in rows if digest(json.loads(record))==sha}
    if set(outcomes)!={t['trial_id'] for t in smoke_plan['planned_trials']} or not all(r.get('valid') and r.get('tool_calls',0)>0 and r.get('data_origin')=='real-model' for r in outcomes.values()):
        raise ValueError('SMOKE_OUTCOME_EVIDENCE_REQUIRED')
    return {'path':str(Path(path).resolve()),'sha256':file_digest(path),'run_id':smoke_plan['run_id']}


def freeze_plan(cfg,scope,run_id,validation,output,smoke=None):
    plan=planned(REPO,cfg,scope,run_id)
    proof=validation_for(cfg,validation); image_check(proof['images'])
    plan.update(images=proof['images'],validation={'path':str(Path(validation).resolve()),'sha256':file_digest(validation)})
    if scope=='development-batch':
        if smoke is None: raise ValueError('MODEL_SMOKE_EVIDENCE_REQUIRED')
        plan['smoke_evidence']=smoke_for(cfg,smoke)
    write_new(output,plan)
    inputs=public_inputs(REPO)
    with zipfile.ZipFile(Path(output).with_suffix('.source.zip'),'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,expected in inputs.items():
            if file_digest(REPO/name)!=expected: raise ValueError('FREEZE_SOURCE_DRIFT')
            archive.write(REPO/name,name)
    return plan


def check_plan(cfg,path,plan):
    wanted=planned(REPO,cfg,plan['scope'],plan['run_id'])
    for key in wanted:
        if wanted[key]!=plan.get(key): raise ValueError('FROZEN_PLAN_DRIFT')
    if load(path)!=plan: raise ValueError('PLAN_FILE_DRIFT')
    proof=validation_for(cfg,plan['validation']['path'])
    if file_digest(plan['validation']['path'])!=plan['validation']['sha256'] or proof['images']!=plan['images']: raise ValueError('VALIDATION_PROOF_DRIFT')
    if plan['scope']=='development-batch':
        expected=plan.get('smoke_evidence')
        if not expected or smoke_for(cfg,expected['path'])!=expected: raise ValueError('SMOKE_EVIDENCE_DRIFT')


def open_ledger(cfg):
    root=native_root(cfg)
    ledger=DevelopmentLedger(root/'ledger.sqlite3',account=cfg['account_reference'],pool_cap=nano(cfg['pool_cap_usd']),origin='real')
    old=load(REPO/'reports/provider-connectivity-stage9.json')
    ledger.import_external(old['run_id'],old,nano(old['exposure_held_usd']),nano(old['token_price_estimate_usd']))
    ledger.add_margin(); return ledger


def execute_trial(cfg,config_path,plan_path,plan,trial,ledger,runroot):
    tid=trial['trial_id']; folder=runroot/tid
    folder.mkdir(); owner=ledger.claim_trial(plan['run_id'],tid,0)
    started=time.monotonic(); backend=None; loop=None; cleanup='not_created'; grade=None
    try:
        attest=capture(REPO,profile_for(cfg),plan['run_id'],ttl_sec=900)
        write_new(folder/'runtime-attestation.json',attest)
        if not attest.get('ready'): raise ValueError('RUNTIME_ATTESTATION_FAILED')
        backend=create_backend(cfg,trial['task_id'],plan['images'],plan['run_id'])
        gate=DevelopmentGate(REPO,config_path,plan_path,plan,trial,profile_for(cfg),attest,backend,ledger)
        instruction=(REPO/'prompts'/trial['task_id']/(trial['language']+'.md')).read_text(encoding='utf-8')
        loop=run_loop(cfg,plan,trial,instruction,ledger,OpenAIResponses(REPO,gate),backend,gate,folder/'trajectory.jsonl',owner)
        if loop['failure_class'] not in {None,'agent'}: raise ValueError('TRIAL_REQUIRES_RECONCILIATION')
        if gate() is not True: raise ValueError('POST_LOOP_GATE_DENIED')
        backend.collect(folder/'artifacts')
        grade=verify(folder/'artifacts',runroot,plan['images'][trial['task_id']]['verifier'],plan['run_id'])
        if grade['status']!='verified': raise ValueError('VERIFIER_INFRA_FAILURE')
        reward=0 if loop['stop_reason']=='trial_timeout' else grade['reward']
        result={**trial,'schema':'vi-development-trial/1','run_id':plan['run_id'],'execution_scope':plan['scope'],
                'development_only':True,'data_origin':'real-model','status':'agent_timeout' if loop['stop_reason']=='trial_timeout' else 'completed',
                'reward':reward,'verifier_reward':grade['reward'],'valid':True,'stop_reason':loop['stop_reason'],
                'tool_calls':loop['tool_calls'],'model_requests':loop['model_requests'],
                'duration_sec':time.monotonic()-started,'compute_cost_status':'not_metered','compute_cost_usd':None,
                'snapshot_id':plan['snapshot']['id'],'trajectory':str(folder/'trajectory.jsonl'),
                'artifact_sha256':{p.relative_to(folder/'artifacts').as_posix():file_digest(p) for p in (folder/'artifacts').rglob('*') if p.is_file()}}
    except Exception as exc:
        result={**trial,'schema':'vi-development-trial/1','run_id':plan['run_id'],'execution_scope':plan['scope'],
                'development_only':True,'data_origin':'real-model','status':'infra_error','reward':None,'valid':False,
                'error_code':safe_error(exc),'raw_loop':loop,'raw_verifier':grade,'duration_sec':time.monotonic()-started,
                'compute_cost_status':'not_metered','compute_cost_usd':None,'snapshot_id':plan['snapshot']['id']}
        state=ledger.db.execute('SELECT state FROM trials WHERE run=? AND id=?',(plan['run_id'],tid)).fetchone()
        if state and state['state']=='active': ledger.finish(plan['run_id'],tid,result)
    finally:
        if backend:
            try: backend.destroy(); cleanup='removed_owned_container'
            except Exception: cleanup='manual_cleanup_required'
    result['cleanup']=cleanup
    if cleanup=='manual_cleanup_required': result.update(valid=False,status='infra_error',error_code='CLEANUP_FAILED')
    requests=ledger.db.execute('SELECT id,estimate_i,receipt,phase FROM requests WHERE run=? AND trial=? ORDER BY slot',(plan['run_id'],tid)).fetchall()
    estimates=[r['estimate_i'] for r in requests]
    result['cost_usd']=sum(estimates)/1000000000 if estimates and all(n is not None for n in estimates) else None
    result['cost_status']='conservative-token-estimate-not-invoice' if result['cost_usd'] is not None else 'unknown'
    result['request_ids']=[r['id'] for r in requests]
    usages=[json.loads(r['receipt']).get('response',{}).get('usage',{}) for r in requests if r['receipt']]
    result['input_tokens']=sum(u.get('input_tokens',0) for u in usages)
    result['output_tokens']=sum(u.get('output_tokens',0) for u in usages)
    ledger.complete_outcome(plan['run_id'],tid,result)
    write_new(folder/'outcome.json',sanitize(result))
    return result


def report(plan,runroot,output,ledger_state=None,authoritative=None):
    output=Path(output)
    if output.exists(): raise ValueError('REPORT_OUTPUT_EXISTS')
    output.mkdir(parents=True)
    rows=[]; missing=[]
    for trial in plan['planned_trials']:
        path=runroot/trial['trial_id']/'outcome.json'
        if not path.exists(): missing.append(trial['trial_id']); continue
        row=load(path)
        if authoritative is None or authoritative.get(trial['trial_id'])!=row: raise ValueError('OUTCOME_FILE_LEDGER_DRIFT')
        for key in trial:
            if row.get(key)!=trial[key]: raise ValueError('NORMALIZED_IDENTITY_DRIFT')
        if row.get('run_id')!=plan['run_id'] or row.get('execution_scope')!=plan['scope'] or row.get('data_origin')!=plan['origin'] or row.get('snapshot_id')!=plan['snapshot']['id']:
            raise ValueError('NORMALIZED_PROVENANCE_DRIFT')
        rows.append(row)
    valid=[r for r in rows if r.get('valid') and type(r.get('reward')) is int and r['reward'] in (0,1) and r.get('status') in {'completed','agent_error','agent_timeout'}]
    complete=len(valid)==len(plan['planned_trials']) and not missing
    scores={}
    for lang in ['en','vi']:
        group={}
        for tid in sorted({p['task_id'] for p in plan['planned_trials']}):
            expected=[p for p in plan['planned_trials'] if p['language']==lang and p['task_id']==tid]
            observed=[r['reward'] for r in valid if r['language']==lang and r['task_id']==tid]
            group[tid]=statistics.mean(observed) if len(observed)==len(expected) and expected else None
        scores[lang]={'tasks':group,'macro':statistics.mean(group.values()) if group and all(v is not None for v in group.values()) else None}
    delta=100*(scores['vi']['macro']-scores['en']['macro']) if all(scores[l]['macro'] is not None for l in ['en','vi']) else None
    known_cost=sum(r['cost_usd'] for r in rows if r.get('cost_usd') is not None)
    result={'schema':'vi-development-report/1','scope':plan['scope'],'run_id':plan['run_id'],'development_only':True,
            'data_origin':plan['origin'],
            'independently_reviewed':False,'planned_trials':len(plan['planned_trials']),'valid_trials':len(valid),
            'missing_trials':missing,'infra_trials':[r['trial_id'] for r in rows if not r.get('valid')],
            'complete':complete,'scores':scores,'delta_vi_pp':delta,'ci95':None,'ci_reason':'one family per skill; insufficient independent replication',
            'conservative_token_estimate_usd':known_cost,'cost_unknown_trials':[r['trial_id'] for r in rows if r.get('cost_usd') is None],
            'invoice_usd':None,'compute_cost_status':'not_metered','compute_cost_usd':None,'ledger':ledger_state,
            'technical_smoke_passed':plan['scope']=='development-smoke' and complete and all(r.get('tool_calls',0)>0 for r in rows),
            'configuration':plan['config']['configuration'],'snapshot_id':plan['snapshot']['id']}
    write_new(output/'summary.json',result)
    write_new(output/'plan.json',plan)
    with (output/'normalized.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
        for row in rows: stream.write(json.dumps(row,ensure_ascii=False)+'\n')
    fields=['trial_id','task_id','language','configuration','repeat','attempt','status','reward','duration_sec','input_tokens','output_tokens','cost_usd','cost_status','review_status']
    with (output/'trials.csv').open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)
    lines=['# Development benchmark results','', '**Internal / pending independent review.**','',
           f"Coverage: {len(valid)}/{len(plan['planned_trials'])} valid trials. Complete: {complete}.",'',
           '| Task | EN | VI |','|---|---:|---:|']
    for tid in scores['en']['tasks']: lines.append(f"| {tid} | {scores['en']['tasks'][tid]} | {scores['vi']['tasks'][tid]} |")
    lines+=['',f"EN macro: {scores['en']['macro']}; VI macro: {scores['vi']['macro']}; delta VI-EN: {delta} pp.",'',
            f"Conservative token estimate: USD {known_cost:.9f}; invoice unavailable; local compute not metered.",'',
            'Infrastructure failures and missing trials remain explicit. CI unavailable: one family per skill. Smoke and batch coverage are separate.']
    with (output/'results.md').open('x',encoding='utf-8') as stream: stream.write('\n'.join(lines)+'\n')
    return result


def execute(cfg,config_path,plan_path,resume=False):
    plan=load(plan_path); check_plan(cfg,plan_path,plan); image_check(plan['images']); root=native_root(cfg)
    runroot=root/'runs'/plan['run_id']
    if runroot.exists() and not resume: raise ValueError('RUN_EXISTS_USE_RESUME_UNSTARTED')
    if not runroot.exists() and resume: raise ValueError('RUN_NOT_STARTED')
    runroot.mkdir(parents=True,exist_ok=True)
    ledger=open_ledger(cfg)
    try:
        ledger.create_run(plan['run_id'],plan,nano(cfg['pool_cap_usd']),0)
        copy=runroot/'plan.json'
        if copy.exists():
            if load(copy)!=plan: raise ValueError('RUN_CONTRACT_DRIFT')
        else: write_new(copy,plan)
        if ledger.inspect()['uncertain_requests'] or ledger.db.execute("SELECT 1 FROM tools WHERE phase='submitted'").fetchone(): raise ValueError('UNRECONCILED_PARTIAL_STATE')
        for index,trial in enumerate(plan['planned_trials'],1):
            check_plan(cfg,plan_path,plan)
            existing=ledger.db.execute('SELECT state FROM trials WHERE run=? AND id=?',(plan['run_id'],trial['trial_id'])).fetchone()
            if existing:
                path=runroot/trial['trial_id']/'outcome.json'
                completed=ledger.outcomes(plan['run_id']).get(trial['trial_id'])
                if not path.exists() and completed is not None: write_new(path,completed)
                if existing['state']!='finished' or not path.exists() or not load(path).get('valid'): raise ValueError('PARTIAL_TRIAL_NO_AUTOMATIC_REPLAY')
                if completed!=load(path): raise ValueError('OUTCOME_FILE_LEDGER_DRIFT')
                print('Retained completed '+trial['trial_id'],flush=True); continue
            if ledger.inspect()['available_nano']<request_reserve(cfg):
                print('Budget cannot reserve another request; stopping before dispatch',flush=True); break
            row=execute_trial(cfg,config_path,plan_path,plan,trial,ledger,runroot)
            print(json.dumps({'progress':f'{index}/{len(plan["planned_trials"])}','trial_id':trial['trial_id'],'valid':row['valid'],
                              'reward':row['reward'],'cost_usd':row['cost_usd'],'error_code':row.get('error_code')}),flush=True)
            if not row['valid']: break
        out=runroot/('report-'+uuid.uuid4().hex[:8]); result=report(plan,runroot,out,ledger.inspect(),ledger.outcomes(plan['run_id']))
        print('Report: '+str(out),flush=True)
        write_new(runroot/('run-summary-'+uuid.uuid4().hex[:8]+'.json'),{'report':str(out),'complete':result['complete'],'technical_smoke_passed':result['technical_smoke_passed']})
        return result
    finally: ledger.close()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['validate','plan','run','resume-unstarted','report'])
    parser.add_argument('--config',type=Path,default=REPO/'configs/development-benchmark.json')
    parser.add_argument('--scope',choices=sorted(SCOPES),default='development-batch')
    parser.add_argument('--run-id',default='stage11-development-001'); parser.add_argument('--validation',type=Path)
    parser.add_argument('--plan',type=Path); parser.add_argument('--output',type=Path); parser.add_argument('--smoke',type=Path)
    args=parser.parse_args(); cfg=load(args.config); validate_config(cfg)
    if args.action=='validate':
        output=args.output or Path(cfg['state_root'])/'validation-001'
        result=validate_containers(cfg,output); print('Container validation passed: '+str(output/'validation.json')); return
    if args.action=='plan':
        if args.output:
            if args.validation is None: raise ValueError('VALIDATION_PATH_REQUIRED')
            result=freeze_plan(cfg,args.scope,args.run_id,args.validation,args.output,args.smoke)
        else: result=planned(REPO,cfg,args.scope,args.run_id)
        print(json.dumps({'scope':result['scope'],'run_id':result['run_id'],'planned_trials':len(result['planned_trials']),
                          'review_required':False,'development_only':True,'credential_read':False,'provider_calls':0})); return
    if args.plan is None: raise ValueError('PLAN_PATH_REQUIRED')
    if args.action in {'run','resume-unstarted'}:
        result=execute(cfg,args.config,args.plan,resume=args.action=='resume-unstarted')
        if not result['complete'] or (result['scope']=='development-smoke' and not result['technical_smoke_passed']): raise SystemExit(3)
    else:
        plan=load(args.plan); root=Path(cfg['state_root'])/'runs'/plan['run_id']
        if args.output is None: raise ValueError('REPORT_OUTPUT_REQUIRED')
        with closing(sqlite3.connect((Path(cfg['state_root'])/'ledger.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)) as db:
            run=db.execute('SELECT contract FROM runs WHERE id=?',(plan['run_id'],)).fetchone()
            if not run or run[0]!=digest(plan): raise ValueError('REPORT_RUN_CONTRACT_DRIFT')
            authoritative={tid:json.loads(record) for tid,record,sha in db.execute('SELECT trial,record,sha FROM development_outcomes WHERE run=?',(plan['run_id'],)) if digest(json.loads(record))==sha}
        result=report(plan,root,args.output,authoritative=authoritative); print(json.dumps({'complete':result['complete'],'valid_trials':result['valid_trials']}))


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'error':safe_error(exc)}),flush=True); raise SystemExit(2) from None
