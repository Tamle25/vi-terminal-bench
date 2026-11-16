"""Inventory immutable evidence and missing decisions, without probing Docker or APIs."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from pilot_contracts import snapshot


def inventory(repo):
    prior=json.loads((repo/'reports/stage3-summary.json').read_text())
    baseline=json.loads((repo/'reports/stage3-baseline-state.json').read_text())
    archives={name:item['sha256'] for name,item in baseline['archives'].items()}
    archives.update({'stage3-targeted-smoke.tar.gz':prior['smoke_archive_sha256']})
    archives.update({Path(item['path']).name:item['sha256'] for item in prior['review_bundles'].values()})
    checked=[]
    for name,wanted in archives.items():
        actual=hashlib.sha256((repo/'jobs'/name).read_bytes()).hexdigest()
        if actual!=wanted:raise ValueError('Archive drift')
        checked.append({'path':'jobs/'+name,'sha256':actual,'status':'pass'})
    snap=snapshot(repo)
    for task,wanted in baseline['canonical_task_payloads'].items():
        if snap['tasks'][task]['payload_sha256']!=wanted:raise ValueError('Task payload drift')
    for path,wanted in baseline['file_sha256'].items():
        if hashlib.sha256((repo/path).read_bytes()).hexdigest()!=wanted:raise ValueError('Historical metadata changed')
    return {'schema':'vi-stage4-state/0.1','recorded_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'offline-engineering-not-model-evaluation','snapshot':snap,'archive_inventory':checked,'states':[{'name':'historical_evidence','status':'pass','evidence':'stage3-summary.json and checked archive hashes','next_action':None},{'name':'independent_review','status':'missing_input','evidence':'review records remain pending','next_action':'Supply actual human review records for these hashes'},{'name':'model_profile_and_budget','status':'missing_input','evidence':'model-pilot.template.json contains null decisions','next_action':'Choose two concrete profiles and budgets'},{'name':'runtime_for_model','status':'unverified','evidence':'stage3 default path failed and scoped relay passed development only','next_action':'Explicit profile choice and fresh run-scoped capture; no automatic probe or root fallback'},{'name':'real_adapter','status':'unverified','evidence':'no actual agent selected','next_action':'Verify actual profile mapping when supplied'},{'name':'part_A','status':'missing_input','evidence':'Eval snapshot/config unavailable','next_action':'Follow Eval input checklist'},{'name':'release','status':'not_applicable','evidence':'offline stage does not publish','next_action':'License/hosting decisions remain with owner'}],'model_calls':0}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Use a new evidence output path')
    report=inventory(Path(__file__).resolve().parents[1]);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Historical archives, metadata and six task payloads match; runtime/model decisions not inferred')
