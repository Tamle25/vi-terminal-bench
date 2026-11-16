"""Read-only inherited evidence audit and creation of a pending human review kit."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

from credential_artifacts import validate_native_inputs
from pilot_contracts import snapshot
from provider_connectivity_v1 import digest, write_new
from terminal_agent_v1 import source_hashes, request_reserve, validate_config


def prepare(repo):
    read = lambda name: json.loads((repo/name).read_text(encoding='utf-8'))
    old = read('reports/stage9-summary.json'); frozen = read('reports/stage9-frozen-inputs.json')
    archive = repo/old['evidence_archive']
    if digest(archive) != old['evidence_archive_sha256']: raise ValueError('STAGE9_ARCHIVE_DRIFT')
    checked = {}; living_drift = []
    living = {'README.md','Plan/plan.md','Plan/plan-giai-doan-9.md'}
    with zipfile.ZipFile(archive) as bundle:
        for group in [old['source_sha256'],old['artifact_sha256']]:
            for name,expected in group.items():
                if name in bundle.namelist() and hashlib.sha256(bundle.read(name)).hexdigest()!=expected:
                    raise ValueError('ARCHIVED_EVIDENCE_DRIFT')
                if digest(repo/name)!=expected:
                    if name not in living: raise ValueError('IMMUTABLE_EVIDENCE_DRIFT: '+name)
                    living_drift.append(name)
                checked[name] = expected
    for name,expected in frozen['historical_sha256'].items():
        if digest(repo/name)!=expected: raise ValueError('HISTORICAL_SOURCE_DRIFT: '+name)
        checked[name] = expected
    snap = snapshot(repo)
    if snap['id']!=old['snapshot_id']: raise ValueError('TASK_SNAPSHOT_DRIFT')
    receipt = read('reports/provider-connectivity-stage9.json')
    ledger = repo/'jobs/stage9-connectivity/ledger.sqlite3'; before = digest(ledger)
    with closing(sqlite3.connect(ledger.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        rows = db.execute('SELECT id,state,reserve,result FROM runs').fetchall()
    if len(rows)!=1 or rows[0][0]!=receipt['run_id'] or rows[0][1]!='observed' or json.loads(rows[0][3])!=receipt:
        raise ValueError('CONNECTIVITY_STATE_DRIFT')
    if digest(ledger)!=before: raise ValueError('READONLY_LEDGER_CHANGED')
    cfg = read('configs/stage10-smoke.draft.json'); validate_config(cfg)
    members = validate_native_inputs(repo)
    row = next(row for row in read('configs/review-records.stage5.template.json')['records'] if row['task_id']==cfg['task'])
    folder = repo/'reports/reviews/stage10-b001'; folder.mkdir(parents=True,exist_ok=True)
    # Opening kit intentionally contains only instructions and snapshot metadata.
    for lang in ['en','vi']:
        target = folder/('instruction-'+lang+'.md')
        with target.open('xb') as stream: stream.write((repo/'prompts'/cfg['task']/(lang+'.md')).read_bytes())
    write_new(folder/'pending-record.json', {'kind':'incomplete-review-template-not-evidence','snapshot_id':snap['id'],'records':[row]})
    result = {'schema':'vi-stage10-input-state/1','client_date':'2026-11-13','snapshot_id':snap['id'],
              'historical_verified_files':len(checked),'living_documents_verified_in_archive':sorted(living),
              'living_document_current_changes':living_drift,'stage9_archive_sha256':digest(archive),
              'stage9_ledger_sha256':before,'stage9_ledger_readonly_unchanged':True,
              'connectivity':{'run_id':receipt['run_id'],'state':rows[0][1],'held_usd':receipt['exposure_held_usd'],
                              'token_price_estimate_usd':receipt['token_price_estimate_usd'],'invoice_usd':None},
              'draft_config_sha256':digest(repo/'configs/stage10-smoke.draft.json'),'agent_source_sha256':source_hashes(repo),
              'credential_value_read':False,'public_source_policy':'pass','public_source_inputs':len(members),
              'request_reservation_nano':request_reserve(cfg),'max_smoke_inference_nano':8*request_reserve(cfg),
              'review_accepted':0,'review_total':6,'reviewer_answer':'No reviewer yet; prepare pending kit',
              'states':{'model_snapshot':'previously_connected','agent':'implemented_pending_validation',
                        'runtime':'failed_default_wsl_docker_probe','review':'missing_input',
                        'smoke_budget_authorization':'missing_input','compute_pricing':'missing_input',
                        'terminal_container_integration':'unverified','real_smoke_dispatch':'disabled'},
              'new_api_calls':0,'benchmark_trials':0,'native_pilot_ready':False}
    write_new(repo/'reports/stage10-input-state.json',result)
    print('Stage10 input audit passed; historical files:',len(checked),'; review pending; no credential read or API call')


if __name__=='__main__':
    prepare(Path(__file__).resolve().parents[1])
