"""Smoke controller. Preview by default; execute requires reviewed frozen evidence.

Prebuilt images must come from --prepare-images, whose public source snapshot is
bound to the freeze contract. No automatic model fallback, retry or partial resume.
"""
import argparse
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import re
import sys
import time
import uuid

from pilot_contracts import digest, snapshot, validate_attestation
from preflight import filesystem_probe
from provider_connectivity_v1 import digest as file_digest, write_new
from review_records import validate_reviews
from scoped_credentials import sanitized_error
from terminal_agent_v1 import (SYSTEM, TOOL, RealGate, OpenAIResponses, run_trial,
                               source_hashes, validate_config, request_reserve)
from terminal_sandbox_v1 import DockerSandbox, bounded
from terminal_verifier_v1 import verify, normalized
from usd_ledger_v1 import Ledger, nano
from credential_artifacts import validate_native_inputs


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def approved(cfg):
    validate_config(cfg)
    if cfg.get('kind')!='approved-model-smoke' or not cfg.get('authorization_reference'):
        raise ValueError('SMOKE_NOT_AUTHORIZED')
    if any(cfg.get(k) is None for k in ['pool_cap_usd','ledger_path','inference_cap_usd','compute_cap_usd','compute_reservation_usd_per_trial','runtime_profile','compute_nano_usd_per_second','compute_quote_reference']):
        raise ValueError('SMOKE_INPUTS_MISSING')
    storage=Path(cfg['ledger_path'])
    if not storage.is_absolute() or '..' in storage.parts or str(storage.resolve()).startswith(('/tmp/','/mnt/','/var/tmp/')):
        raise ValueError('PERSISTENT_NATIVE_LEDGER_REQUIRED')
    rate=cfg['compute_nano_usd_per_second']
    if type(rate) is not int or rate<0 or not cfg['compute_quote_reference']: raise ValueError('COMPUTE_QUOTE_REQUIRED')
    reserve=nano(cfg['compute_reservation_usd_per_trial'])
    if reserve<420*rate: raise ValueError('COMPUTE_RESERVATION_TOO_SMALL')
    if nano(cfg['inference_cap_usd'])<8*request_reserve(cfg) or nano(cfg['compute_cap_usd'])<2*reserve:
        raise ValueError('SMOKE_CAP_TOO_SMALL')
    if not 0<nano(cfg['pool_cap_usd'])<=nano('2') or nano(cfg['pool_cap_usd'])<nano(cfg['inference_cap_usd'])+nano(cfg['compute_cap_usd'])+nano('0.01'):
        raise ValueError('POOL_CAP_DENIED')


def profile_for(repo,cfg):
    profiles=read(repo/'configs/runtime-profiles.json')['profiles']
    matches=[p for p in profiles if p['id']==cfg['runtime_profile']]
    if len(matches)!=1: raise ValueError('RUNTIME_PROFILE_REQUIRED')
    return matches[0]


def build_images(repo,directory):
    validate_native_inputs(repo)
    directory=Path(directory); filesystem_probe(directory.parent)
    if directory.exists(): raise ValueError('IMAGE_PREPARATION_EXISTS')
    directory.mkdir(); snap=snapshot(repo); payload=snap['tasks']['b001-vn-invoice']['payload_sha256']; images={}
    for role,folder in [('agent','environment'),('verifier','tests')]:
        iid=directory/(role+'.iid')
        result=bounded(['docker','build','--iidfile',str(iid),'--label','vi-bench.payload='+payload,
                        '--label','vi-bench.role='+role,str(repo/'tasks/b001-vn-invoice'/folder)],300)
        if result['exit_code']!=0 or result['timed_out'] or not iid.is_file(): raise ValueError('IMAGE_BUILD_FAILED')
        image=iid.read_text().strip()
        if not re.fullmatch('sha256:[0-9a-f]{64}',image): raise ValueError('IMAGE_ID_REQUIRED')
        images[role]=image
    if snapshot(repo)!=snap: raise ValueError('SOURCE_DRIFT_DURING_BUILD')
    result={'schema':'vi-smoke-images/1','snapshot_id':snap['id'],'task_payload_sha256':payload,'images':images}
    write_new(directory/'images.json',result)
    return result


def check_images(repo,images):
    snap=snapshot(repo)
    if images['schema']!='vi-smoke-images/1' or images['snapshot_id']!=snap['id'] or images['task_payload_sha256']!=snap['tasks']['b001-vn-invoice']['payload_sha256']:
        raise ValueError('IMAGE_SOURCE_DRIFT')
    if set(images['images'])!={'agent','verifier'}: raise ValueError('IMAGE_ROLES')
    for role,image in images['images'].items():
        if not re.fullmatch('sha256:[0-9a-f]{64}',image): raise ValueError('IMAGE_ID_REQUIRED')
        result=bounded(['docker','image','inspect',image],5)
        if result['exit_code']!=0 or result['timed_out']: raise ValueError('IMAGE_UNAVAILABLE')
        rows=json.loads(result['stdout_bytes'])
        if len(rows)!=1 or rows[0]['Id']!=image: raise ValueError('IMAGE_IDENTITY')
        labels=rows[0]['Config'].get('Labels',{})
        if labels.get('vi-bench.payload')!=images['task_payload_sha256'] or labels.get('vi-bench.role')!=role:
            raise ValueError('IMAGE_PROVENANCE')


def precheck(repo,cfg,review_path,attestation_path,images):
    approved(cfg); snap=snapshot(repo)
    if cfg['task'] not in validate_reviews(snap,read(review_path)): raise ValueError('TASK_REVIEW_REQUIRED')
    profile=profile_for(repo,cfg)
    if validate_attestation(profile,read(attestation_path),cfg['run_id'],snap['id'])[0]!='pass':
        raise ValueError('RUNTIME_ATTESTATION_REQUIRED')
    check_images(repo,images)
    return profile


def contract_for(repo,cfg,images):
    return {'schema':'vi-smoke-contract/1','config':cfg,'source_sha256':source_hashes(repo),
            'snapshot_id':snapshot(repo)['id'],'prompt_tools_hash':digest([SYSTEM,TOOL]),'images':images,
            'planned_trials':[cfg['task']+'-en',cfg['task']+'-vi']}


def execute_one(repo,cfg,contract,profile,config_path,reviews,attestation,ledger,state,language):
    trial=cfg['task']+'-'+language; folder=state/language; folder.mkdir()
    token=ledger.claim_trial(cfg['run_id'],trial,nano(cfg['compute_reservation_usd_per_trial']))
    started=time.monotonic(); backend=None; loop=None; cleanup='not_created'
    try:
        image=contract['images']['images']['agent']
        args=DockerSandbox.create_args(image,cfg['run_id'],cfg)
        # Deterministic ownership recovery for a lost create response, never by broad label deletion.
        name='vi-stage10-'+uuid.uuid4().hex
        args[2:2]=['--name',name]
        created=bounded(args,10)
        cid=created['stdout_bytes'].decode('ascii',errors='ignore').strip()
        if created['exit_code']!=0 or created['timed_out'] or not re.fullmatch('[0-9a-f]{64}',cid):
            recovered=bounded(['docker','inspect',name],5)
            if recovered['exit_code']==0 and not recovered['timed_out']:
                rows=json.loads(recovered['stdout_bytes'])
                if len(rows)==1 and rows[0]['Config'].get('Labels',{}).get('vi-bench.run')==cfg['run_id'] and re.fullmatch('[0-9a-f]{64}',rows[0]['Id']):
                    backend=DockerSandbox(rows[0]['Id'],cfg['run_id'],image,cfg)
            raise ValueError('CONTAINER_CREATE_UNCERTAIN')
        backend=DockerSandbox(cid,cfg['run_id'],image,cfg)
        running=bounded(['docker','start',cid],10)
        if running['exit_code']!=0 or running['timed_out']: raise ValueError('CONTAINER_START_FAILED')
        backend.inspect()
        gate=RealGate(repo,config_path,contract,reviews,profile,attestation,backend,ledger)
        api=OpenAIResponses(repo,gate)
        instruction=(repo/'prompts'/cfg['task']/(language+'.md')).read_text(encoding='utf-8')
        loop=run_trial(cfg,instruction,language,ledger,api,backend,gate,folder/'trajectory.jsonl',
                       nano(cfg['compute_reservation_usd_per_trial']),claim_token=token)
        if loop['failure_class'] not in {None,'agent'}: raise ValueError('TRIAL_REQUIRES_RECONCILIATION')
        if gate() is not True: raise ValueError('POST_LOOP_GATE_DENIED')
        backend.collect(folder/'artifacts')
        verification=verify(folder/'artifacts',state,contract['images']['images']['verifier'],cfg['run_id'])
        hashes={p.relative_to(folder/'artifacts').as_posix():file_digest(p) for p in (folder/'artifacts').rglob('*') if p.is_file()}
        result=normalized(loop,verification,snapshot_id=contract['snapshot_id'],artifact_sha256=hashes)
    except Exception as exc:
        result={'schema':'vi-terminal-controller-failure/1','origin':'real','scope':'model-smoke','trial_id':trial,
                'reward':None,'benchmark_result':False,'error':sanitized_error(exc),'raw_loop':loop}
        write_new(folder/'controller-failure.json',result)
        row=ledger.db.execute('SELECT state FROM trials WHERE run=? AND id=?',(cfg['run_id'],trial)).fetchone()
        if row and row['state']=='active': ledger.finish(cfg['run_id'],trial,result)
    finally:
        if backend:
            try: backend.destroy(); cleanup='removed_owned_container'
            except Exception: cleanup='failed_manual_cleanup_required'
        elapsed=time.monotonic()-started
        estimate=int((Decimal(str(elapsed))*cfg['compute_nano_usd_per_second']).to_integral_value(rounding=ROUND_CEILING))
        ledger.record_compute_estimate(cfg['run_id'],trial,estimate)
        write_new(folder/'lifecycle.json',{'elapsed_sec':elapsed,'cleanup':cleanup,'compute_estimate_nano':estimate,
                                          'compute_invoice':None,'compute_quote_reference':cfg['compute_quote_reference']})
    if cleanup=='failed_manual_cleanup_required': result['benchmark_result']=False
    result['cleanup']=cleanup
    write_new(folder/'controller-outcome.json',result)
    if result.get('schema')=='vi-terminal-trial/1': write_new(folder/'normalized.json',result)
    return result,cleanup


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,default=Path('configs/stage10-smoke.draft.json'))
    parser.add_argument('--prepare-images',type=Path)
    parser.add_argument('--images',type=Path); parser.add_argument('--reviews',type=Path); parser.add_argument('--attestation',type=Path)
    parser.add_argument('--contract',type=Path); parser.add_argument('--freeze',action='store_true')
    parser.add_argument('--execute',action='store_true'); parser.add_argument('--state',type=Path)
    args=parser.parse_args(); repo=Path(__file__).resolve().parents[1]
    if args.prepare_images:
        if args.execute or args.freeze: raise ValueError('ONE_ACTION_REQUIRED')
        build_images(repo,args.prepare_images); print('Images prepared; API calls 0'); return
    cfg=read(args.config); validate_config(cfg)
    if not args.execute and not args.freeze:
        print(json.dumps({'ready_for_dispatch':False,'kind':cfg['kind'],'scope':cfg['scope'],
                          'real_cli':'implemented_requires_precheck','api_calls':0,'credential_read':False})); return
    if args.execute and args.freeze: raise ValueError('ONE_ACTION_REQUIRED')
    # Draft rejection precedes ledger/container/key operations.
    approved(cfg)
    if any(p is None for p in [args.images,args.reviews,args.attestation,args.contract]): raise ValueError('EVIDENCE_PATHS_REQUIRED')
    images=read(args.images); profile=precheck(repo,cfg,args.reviews,args.attestation,images)
    contract=contract_for(repo,cfg,images)
    if args.freeze:
        write_new(args.contract,contract); print('Contract frozen; API calls 0; recheck before execute'); return
    if read(args.contract)!=contract: raise ValueError('FROZEN_CONTRACT_DRIFT')
    if args.state is None: raise ValueError('NATIVE_STATE_REQUIRED')
    state=args.state.resolve(); filesystem_probe(state.parent)
    if state.exists(): raise ValueError('EXISTING_RUN_NO_AUTOMATIC_RESUME')
    state.mkdir()
    filesystem_probe(Path(cfg['ledger_path']).parent)
    ledger=Ledger(cfg['ledger_path'],account=cfg['account_reference'],pool_cap=nano(cfg['pool_cap_usd']),origin='real')
    try:
        receipt=read(repo/'reports/provider-connectivity-stage9.json')
        ledger.import_external(receipt['run_id'],receipt,nano(receipt['exposure_held_usd']),nano(receipt['token_price_estimate_usd']))
        ledger.create_run(cfg['run_id'],contract,nano(cfg['inference_cap_usd']),nano(cfg['compute_cap_usd']))
        results=[]
        for language in ['en','vi']:
            precheck(repo,cfg,args.reviews,args.attestation,images)
            if read(args.contract)!=contract or read(args.config)!=cfg: raise ValueError('LIVE_CONTRACT_DRIFT')
            result,cleanup=execute_one(repo,cfg,contract,profile,args.config,args.reviews,args.attestation,ledger,state,language)
            results.append(result)
            if not result.get('benchmark_result') or cleanup=='failed_manual_cleanup_required' or ledger.inspect()['uncertain_requests']:
                break
        coverage=len(results)==2 and all(r.get('benchmark_result') for r in results)
        terminal=bool(results) and all(r.get('terminal_path_observed') for r in results)
        technical=coverage and terminal
        write_new(state/'summary.json',{'kind':'real-model-smoke','scope':'model-smoke','results':results,'billing':ledger.inspect(),
                                       'full_planned_coverage':coverage,'terminal_path_observed':terminal,
                                       'technical_smoke_passed':technical,'reward_successes':sum(r.get('reward')==1 for r in results)})
        print('Smoke artifacts retained; inspect coverage/reward/billing separately')
        if not technical: raise SystemExit(3)
    finally: ledger.close()


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps(sanitized_error(exc))); raise SystemExit(2) from None
