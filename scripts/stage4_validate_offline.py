"""Run 72 synthetic trials across stopped/restarted processes; no Docker/model API."""
import hashlib
import json
import sys
import tarfile
import tempfile
from pathlib import Path
from aggregate_results import aggregate
from model_dry_run import dry_run
from pilot_contracts import snapshot
from pilot_runner import simulation_plan,Store,FakeProvider
from runtime_process import run_bounded


def validate(repo):
    prefix=repo/'reports';summary_path=prefix/'stage4-offline-summary.json'
    if summary_path.exists():raise ValueError('Do not overwrite validation evidence')
    profile=json.loads((repo/'configs/model-pilot.template.json').read_text());preview=dry_run(profile,repo)
    roster=[json.loads(line) for line in (repo/'manifest.jsonl').read_text().splitlines() if line.strip()]
    plan=simulation_plan(preview,roster,snapshot(repo)['id'])
    ids=[row['trial_id'] for row in plan['planned_trials']]
    scenarios={ids[0]+':1':{'status':'retryable_infra_error','reward':None,'inference_micros':250,'compute_micros':50},ids[1]+':1':{'status':'verifier_error','reward':None,'inference_micros':700,'compute_micros':100},ids[2]+':1':{'status':'agent_failure','reward':0,'inference_micros':1000,'compute_micros':100}}
    plan_path=prefix/'stage4-simulation-run.json';scenario_path=prefix/'stage4-simulation-scenarios.json'
    plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');scenario_path.write_text(json.dumps(scenarios,indent=2)+'\n',encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='vi-stage4-ledger-') as temporary:
        root=Path(temporary)
        command=[sys.executable,str(repo/'scripts/pilot_runner.py'),'--plan',str(plan_path),'--state-dir',str(root),'--scenarios',str(scenario_path)]
        first=run_bounded([*command,'--max-dispatches','11'],timeout=90)
        if first['returncode']!=0 or first['timed_out']:raise ValueError('Partial simulation process failed: '+first['stderr'])
        partial=json.loads((root/'export/summary.json').read_text())
        if partial['fake_dispatch_calls']!=11 or partial['unfinished_trials']<=0:raise ValueError('Expected durable partial run')
        second=run_bounded(command,timeout=90)
        if second['returncode']!=0 or second['timed_out']:raise ValueError('Resumed simulation failed: '+second['stderr'])
        resumed=json.loads((root/'export/summary.json').read_text())
        third=run_bounded(command,timeout=90)
        if third['returncode']!=0 or third['timed_out']:raise ValueError('Idempotent resume failed')
        final=json.loads((root/'export/summary.json').read_text())
        if final['fake_dispatch_calls']!=resumed['fake_dispatch_calls'] or final['fake_dispatch_calls']!=74 or final['unique_fake_requests']!=74 or final['valid_final_trials']!=72 or final['unfinished_trials'] or final['unknown_cost_attempts']:raise ValueError('Duplicate/lost attempts or coverage/cost mismatch')
        if final['known_charges_micro_units']!={'inference':72950,'compute':7350}:raise ValueError('Retry charges lost')
        rows=[json.loads(line) for line in (root/'export/trials.jsonl').read_text(encoding='utf-8').splitlines()]
        # Rewrite raw references to the archive location, not an ephemeral directory.
        for row in rows:row['raw_reference']='jobs/stage4-offline-simulation.tar.gz::export/raw/'+Path(row['raw_reference']).name
        result=aggregate(rows,roster,run_plan=plan,bootstrap_draws=100)
        if result['result_kind']!='simulation-not-model-evaluation' or any(group['provisional'] for group in result['groups']) or len(result['final_trials'])!=72:raise ValueError('Simulation aggregate mismatch')
        (prefix/'stage4-simulation-trials.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')
        (prefix/'stage4-simulation-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        archive=repo/'jobs/stage4-offline-simulation.tar.gz'
        if archive.exists():raise ValueError('Simulation archive already exists')
        with tarfile.open(archive,'w:gz') as handle:
            for path in sorted(root.iterdir()):handle.add(path,arcname=path.name)
        with tempfile.TemporaryDirectory(prefix='vi-stage4-restore-') as restored:
            with tarfile.open(archive,'r:gz') as handle:handle.extractall(restored,filter='data')
            restored=Path(restored);store=Store(restored/'ledger.sqlite3',plan);provider=FakeProvider(restored/'fake-provider.sqlite3',scenarios)
            if store.summary()['valid_final_trials']!=72 or provider.call_count()!=74:raise ValueError('Restored ledger mismatch')
            # Reopening the archived databases verifies the restored durable state.
            store.db.close();provider.db.close()
        report={'kind':'offline-simulation-not-model-evaluation','all_matched':True,'planned_trials':72,'partial_process_dispatches':11,'final_fake_dispatches':74,'unique_fake_requests':74,'final_valid_trials':72,'resume_did_not_redispatch':True,'currency':'SIM_USD','synthetic_micro_unit_charges':final['known_charges_micro_units'],'unknown_cost_attempts':0,'real_cost_usd':None,'model_calls':0,'secrets_read':False,'archive':'jobs/'+archive.name,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'restored_ledger_verified':True,'point_scores':'synthetic values only, never model capability','runtime':'offline local SQLite; no attestation of Docker/model API'}
        summary_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':validate(Path(__file__).resolve().parents[1])
