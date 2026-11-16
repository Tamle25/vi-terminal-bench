"""Verify stage10 history without reading credentials or changing old ledgers."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

from credential_artifacts import validate_native_inputs
from pilot_contracts import snapshot
from provider_connectivity_v1 import digest, write_new


def prepare(repo):
    read=lambda p:json.loads((repo/p).read_text(encoding='utf-8'))
    summary=read('reports/stage10-summary.json')
    archive=repo/summary['evidence_archive']
    if digest(archive)!=summary['evidence_archive_sha256']: raise ValueError('STAGE10_ARCHIVE_DRIFT')
    living={'README.md','Plan/plan.md','Plan/plan-giai-doan-10.md'}
    verified={}
    with zipfile.ZipFile(archive) as package:
        for group in [summary['public_input_sha256'],summary['artifact_sha256']]:
            for name,expected in group.items():
                if hashlib.sha256(package.read(name)).hexdigest()!=expected: raise ValueError('ARCHIVE_MEMBER_DRIFT')
                if name not in living and digest(repo/name)!=expected: raise ValueError('IMMUTABLE_HISTORY_DRIFT: '+name)
                verified[name]=expected
    snap=snapshot(repo)
    if snap['id']!=summary['snapshot_id']: raise ValueError('TASK_SNAPSHOT_DRIFT')
    old=repo/'jobs/stage9-connectivity/ledger.sqlite3'; before=digest(old)
    with closing(sqlite3.connect(old.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        rows=db.execute('SELECT id,state,result FROM runs').fetchall()
    receipt=read('reports/provider-connectivity-stage9.json')
    if len(rows)!=1 or rows[0][1]!='observed' or json.loads(rows[0][2])!=receipt or digest(old)!=before: raise ValueError('CONNECTIVITY_HISTORY_DRIFT')
    validate_native_inputs(repo)
    result={'schema':'vi-stage11-input-state/1','client_date':'2026-11-13','snapshot_id':snap['id'],
            'historical_verified_files':len(verified),'stage10_archive_sha256':digest(archive),
            'stage9_ledger_sha256':before,'stage9_ledger_readonly_unchanged':True,
            'credential_value_read':False,'review_accepted':0,'review_total':6,
            'user_objective':'internal small usable benchmark; pending review allowed',
            'planned_batch_trials':36,'configurations':1,'scope_budget_usd':'2.00',
            'connectivity_hold_usd':receipt['exposure_held_usd'],'connectivity_token_estimate_usd':receipt['token_price_estimate_usd'],
            'new_provider_calls':0,'history_verified_sha256':verified}
    write_new(repo/'reports/stage11-input-state.json',result)
    print('Stage11 inherited history verified; no credential read or provider call')


if __name__=='__main__': prepare(Path(__file__).resolve().parents[1])
