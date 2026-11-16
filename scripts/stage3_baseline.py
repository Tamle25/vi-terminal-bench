"""Preserve evidence identities before runtime changes; do not rerun task trials."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
from materialize_variants import payload_hash


def baseline(repo):
    summary=json.loads((repo/'reports/native-six-summary.json').read_text(encoding='utf-8'))
    audit=json.loads((repo/'reports/m1-archive-audit.json').read_text(encoding='utf-8'))
    archives={}
    for name,expected in [('m1-linux-validation.tar.gz',audit['archive_sha256']),('native-six-validation.tar.gz',summary['archive_sha256'])]:
        path=repo/'jobs'/name;actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=expected:raise ValueError('Archive drift: '+name)
        archives[name]={'sha256':actual,'bytes':path.stat().st_size,'matched':True}
    files=['reports/native-six-oracle-run.json','reports/native-six-nop-run.json','reports/native-six-task-snapshot.json','reports/native-six-preflight-final.json','uv.lock']
    identities={name:hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in files}
    plan=json.loads((repo/files[0]).read_text(encoding='utf-8'));tasks={}
    for row in plan['planned_trials']:
        task_id=row['task_id'];actual=payload_hash(repo/'tasks'/task_id)
        if actual!=row['payload_sha256']:raise ValueError('Task drift: '+task_id)
        tasks[task_id]=actual
    return {'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'stage3-baseline-evidence-not-new-runtime-probe','archives':archives,'file_sha256':identities,'canonical_task_payloads':tasks,'task_content_changed':False,'historical_readiness':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise ValueError('Do not overwrite baseline evidence')
    report=baseline(Path(__file__).resolve().parents[1]);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print('Two archives and six canonical snapshots verified; historical reports unchanged')
