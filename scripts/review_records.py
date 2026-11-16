"""Validate supplied human review records against snapshots; never invent acceptance."""
import argparse
import json
from pathlib import Path
from pilot_contracts import snapshot


def validate_reviews(snap,records):
    accepted={};seen=set()
    for row in records:
        required={'task_id','task_version','payload_sha256','prompt_hashes','reviewer','author','reviewer_kind','reviewed_at','expert_time_sec','decision','notes'}
        if set(row)!=required:raise ValueError('Review record schema mismatch')
        task=row['task_id']
        if task in seen or task not in snap['tasks']:raise ValueError('Unknown/duplicate review task')
        seen.add(task);actual=snap['tasks'][task]
        if (row['task_version'],row['payload_sha256'],row['prompt_hashes'])!=(actual['version'],actual['payload_sha256'],actual['prompts']):raise ValueError('Review belongs to another snapshot')
        if row['author']!=actual['author']:raise ValueError('Review author attribution mismatch')
        if row['reviewer_kind']!='human' or not row['reviewer'] or row['reviewer']==row['author'] or row['reviewer'] in {'Codex','Codex-assisted'}:raise ValueError('Independent human reviewer required')
        import datetime
        datetime.date.fromisoformat(row['reviewed_at'])
        if type(row['expert_time_sec']) not in (int,float) or not 0<row['expert_time_sec']<864000:raise ValueError('Measured review time required')
        if row['decision'] not in {'accepted','changes_requested'} or not isinstance(row['notes'],str) or not row['notes'].strip():raise ValueError('Review decision/notes required')
        if row['decision']=='accepted':accepted[task]=row
    return accepted


def coverage(repo,records=None):
    snap=snapshot(repo);accepted=validate_reviews(snap,records or [])
    return {'schema':'vi-review-coverage/0.1','snapshot_id':snap['id'],'accepted_count':len(accepted),'total_tasks':len(snap['tasks']),'accepted_tasks':sorted(accepted),'pending_tasks':sorted(set(snap['tasks'])-set(accepted)),'identity_note':'Record consistency check; does not authenticate a human identity or create authorization'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--records',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    repo=Path(__file__).resolve().parents[1];records=json.loads(a.records.read_text(encoding='utf-8')) if a.records else []
    report=coverage(repo,records)
    if a.apply:
        accepted=validate_reviews(snapshot(repo),records)
        if not accepted:raise ValueError('No supplied accepted reviews to import')
        manifest=repo/'manifest.jsonl';rows=[json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
        backup=a.output.with_suffix('.manifest-before.jsonl')
        if backup.exists():raise ValueError('Backup already exists')
        backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(manifest.read_bytes())
        for row in rows:
            if row['task_id'] in accepted:row.update(reviewer=accepted[row['task_id']]['reviewer'],review_status='accepted',review_evidence=str(a.records))
        temporary=manifest.with_suffix('.jsonl.review-tmp')
        with temporary.open('x',encoding='utf-8',newline='\n') as handle:handle.write(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows))
        temporary.replace(manifest)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(f"Review coverage {report['accepted_count']}/{report['total_tasks']}; no acceptance invented")
