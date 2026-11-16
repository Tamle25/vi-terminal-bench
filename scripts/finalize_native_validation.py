"""Archive/restore native-six validation evidence and write a non-model audit."""
import argparse
import hashlib
import json
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from import_harbor_results import import_results
from report_harbor_validation import summarize


def finalize(repo,archive):
    plans=[json.loads((repo/'reports'/f'native-six-{agent}-run.json').read_text(encoding='utf-8')) for agent in ['oracle','nop']]
    archive.parent.mkdir(parents=True,exist_ok=True)
    if archive.exists():raise ValueError('Refusing to overwrite validation archive')
    summaries=[]
    with tarfile.open(archive,'w:gz') as handle:
        for plan in plans:
            agent=plan['configuration_spec']['agent']
            expected=1 if agent=='oracle' else 0
            rows,missing=import_results(plan)
            if missing or any(row['status']!='completed' or row['reward']!=expected for row in rows):
                raise ValueError('Native validation incomplete or unexpected reward')
            summaries.append({'agent':agent,'trials':len(rows),'expected_reward':expected,'matched':True,'per_task':dict(Counter(row['task_id'] for row in rows)),'summed_trial_duration_sec':sum(row['duration_sec'] for row in rows),'inference_cost':'not-applicable-no-model','compute_cost_usd':None})
            for job in sorted({attempt['job_name'] for trial in plan['planned_trials'] for attempt in trial['attempts']}):
                folder=Path(plan['jobs_root'])/job
                handle.add(folder,arcname=job)
                console=folder.with_suffix('.console.log')
                if console.exists():handle.add(console,arcname=console.name)
    restored=[]
    with tempfile.TemporaryDirectory(prefix='vi-native-six-restore-') as tmp:
        root=Path(tmp)
        with tarfile.open(archive,'r:gz') as handle:handle.extractall(root,filter='data')
        for plan in plans:
            agent=plan['configuration_spec']['agent']
            for job in sorted({attempt['job_name'] for trial in plan['planned_trials'] for attempt in trial['attempts']}):
                count=sum(any(attempt['job_name']==job for attempt in trial['attempts']) for trial in plan['planned_trials'])
                result=summarize(root/job,agent,count)
                if not result['all_matched']:raise ValueError('Restored archive failed verification')
                restored.append({'job':job,'trials':count,'matched':True})
    controls=json.loads((repo/'reports/native-six-controls.json').read_text(encoding='utf-8'))
    image=json.loads((repo/'reports/native-six-agent-images.json').read_text(encoding='utf-8'))
    cases=controls['controls']
    if not controls['all_matched'] or not image['all_matched']:raise ValueError('Controls/image checks incomplete')
    return {'kind':'native-six-technical-validation-not-model-evaluation','all_matched':True,'runs':summaries,'controls':{'total':len(cases),'positive':sum(row['expected_pass'] for row in cases),'negative':sum(not row['expected_pass'] for row in cases),'all_matched':True},'agent_images_checked':len(image['images']),'archive':str(archive),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'restored_jobs':restored,'independent_review':'pending','model_pilot':'not-run'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=finalize(Path(__file__).resolve().parents[1],args.archive)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Archived and restored all 24 trials; technical validation matched')
