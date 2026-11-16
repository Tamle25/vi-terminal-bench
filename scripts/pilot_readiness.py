"""Explain readiness from current scoped evidence. Never dispatch a provider."""
import argparse
import datetime as dt
import json
import math
from pathlib import Path
from model_dry_run import dry_run
from pilot_contracts import snapshot,validate_attestation,runtime_fingerprint,STATUSES
from review_records import coverage


def evaluate(repo,profile,runtime_catalog,*,runtime_evidence=None,reviews=None,adapter_evidence=None,budget_evidence=None,run_manifest=None,now=None):
    snap=snapshot(repo);preview=dry_run(profile,repo);checks=[]
    def record(name,status,reason,evidence=None,action=None):
        if status not in STATUSES:raise ValueError('Invalid readiness status')
        checks.append({'name':name,'status':status,'reason':reason,'evidence':evidence,'next_action':action if status!='pass' else None})
    record('model_profile','pass' if preview['profile_complete'] else 'missing_input','Profile complete' if preview['profile_complete'] else 'Model/agent/budget fields missing',preview['missing_inputs'],'Fill only decisions actually supplied by owner')
    review=coverage(repo,reviews)
    record('independent_review','pass' if not review['pending_tasks'] else 'missing_input','Snapshot-bound independent review coverage',review,'Obtain actual human review records; do not auto-accept')
    selected=runtime_catalog.get('selected_runtime_profile');runtime=None
    for option in runtime_catalog['profiles']:
        runtime_fingerprint(option)
        if option['id']==selected:runtime=option
    if runtime is None:
        record('runtime','missing_input','No explicit runtime profile selected',None,'Choose an operating profile, then capture fresh run-scoped evidence; no fallback')
    else:
        status,reason=validate_attestation(runtime,runtime_evidence,profile['run_id'],snap['id'],now,profile['concurrency'])
        record('runtime',status,reason,{'profile_id':runtime['id']},'Capture evidence for the selected runtime and exact run')
    expected={row['configuration']:row['configuration_sha256'] for row in preview['planned_trials']}
    adapter_ok=adapter_evidence is not None and adapter_evidence.get('kind')=='agent-verified' and adapter_evidence.get('configuration_fingerprints')==expected and runtime is not None and adapter_evidence.get('runtime_profile_sha256')==runtime_fingerprint(runtime)
    record('effective_adapter','pass' if adapter_ok else 'unverified','Real agent mapping must match both profiles and runtime',None,'Verify the concrete selected adapter; simulated mapping is insufficient')
    budget_ok=False
    if budget_evidence is not None:
        amounts=[budget_evidence.get(key) for key in ['remaining_inference_usd','remaining_compute_usd','reserve_inference_usd','reserve_compute_usd']]
        finite=all(type(value) in (int,float) and math.isfinite(value) and value>=0 for value in amounts)
        caps=profile['budget'];cap_values=[caps.get('max_inference_usd'),caps.get('max_compute_usd')]
        budget_ok=finite and all(type(value) in (int,float) and math.isfinite(value) and value>0 for value in cap_values) and budget_evidence.get('origin')=='provider-estimate-and-ledger' and budget_evidence.get('currency')=='USD' and budget_evidence.get('pricing_state')=='verified-current' and budget_evidence.get('cost_uncertain') is False and bool(budget_evidence.get('price_source')) and budget_evidence.get('run_id')==profile['run_id'] and budget_evidence.get('scope')=='native-pilot' and budget_evidence.get('configuration_fingerprints')==expected and amounts[0]>=amounts[2] and amounts[1]>=amounts[3] and amounts[0]<=cap_values[0] and amounts[1]<=cap_values[1]
    record('budget','pass' if budget_ok else 'missing_input','Real estimates, caps and available reservation required',None,'Supply current pricing/ledger evidence; simulation currency never pays a real run')
    planned=run_manifest.get('planned_trials',[]) if run_manifest else []
    wanted={row['trial_id']:row for row in preview['planned_trials']}
    manifest_ok=bool(run_manifest) and run_manifest.get('kind')=='model-pilot' and run_manifest.get('run_id')==profile['run_id'] and run_manifest.get('snapshot_id')==snap['id'] and len(planned)==len(wanted) and len({r['trial_id'] for r in planned})==len(wanted) and run_manifest.get('expected_configurations')==preview['expected_configurations']
    if manifest_ok:
        for row in planned:
            original=wanted.get(row['trial_id'])
            if original is None or any(row.get(key)!=original[key] for key in ['task_id','language','configuration','repeat','payload_sha256','instruction_sha256','configuration_sha256','attempts']):manifest_ok=False;break
    record('execution_manifest','pass' if manifest_ok else 'unverified','Frozen model manifest must match current snapshot and planned scope; preview is not executable',None,'Prepare concrete execution manifest after profile/review/runtime choices')
    ready=all(row['status']=='pass' for row in checks)
    return {'schema':'vi-pilot-readiness/0.1','recorded_at_utc':(now or dt.datetime.now(dt.timezone.utc)).isoformat(),'scope':'native-pilot','run_id':profile['run_id'],'snapshot_id':snap['id'],'ready_for_dispatch':ready,'authorization_token':False,'checks':checks,'model_calls':0,'preview_trial_count':preview['trial_count'],'note':'Evidence coherence gate only; real provider executor is not implemented/enabled by this command'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',type=Path,required=True);p.add_argument('--runtime-profiles',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    for name in ['runtime-evidence','reviews','adapter-evidence','budget-evidence','run-manifest']:p.add_argument('--'+name,type=Path)
    args=p.parse_args();load=lambda path:json.loads(path.read_text(encoding='utf-8')) if path else None
    report=evaluate(Path(__file__).resolve().parents[1],load(args.profile),load(args.runtime_profiles),runtime_evidence=load(args.runtime_evidence),reviews=load(args.reviews),adapter_evidence=load(args.adapter_evidence),budget_evidence=load(args.budget_evidence),run_manifest=load(args.run_manifest))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Readiness ready={report['ready_for_dispatch']}; model calls=0; reasons={[c['name'] for c in report['checks'] if c['status']!='pass']}")
    raise SystemExit(0 if report['ready_for_dispatch'] else 2)
