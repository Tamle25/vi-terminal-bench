"""Native Linux fixture integration. Never uses Docker/model/key or human signoff.

The fixture terminal runs one fixed trusted Python probe, not model command text.
This proves loop/data/verifier plumbing, not container isolation or model skill.
"""
import argparse
from contextlib import closing
import importlib.util
import io
import json
import platform
from pathlib import Path
import shutil
import sqlite3
import sys
import tarfile
import tempfile

from credential_artifacts import validate_native_inputs
from pilot_contracts import snapshot
from provider_connectivity_v1 import digest, write_new
from run_native_offline import inputs
from runtime_process import run_bounded
from terminal_agent_v1 import run_trial
from terminal_sandbox_v1 import bounded, extract_data
from terminal_verifier_v1 import normalized, result_from_process
from usd_ledger_v1 import Ledger, nano


def worker(repo, state):
    sys.path.insert(0,str(repo/'scripts/tests'))
    from test_terminal_stage10 import FixtureAPI, FixtureSandbox, response, call
    cfg=json.loads((repo/'configs/stage10-smoke.draft.json').read_text(encoding='utf-8'))
    spec=importlib.util.spec_from_file_location('b001_fixture',repo/'tasks/b001-vn-invoice/environment/generate_fixture.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    state.mkdir(); rows=[]; requests=0
    db_path=state/'fixture-usd.sqlite3'
    ledger=Ledger(db_path,account='stage10-offline-fixture',pool_cap=nano('10'),origin='offline-fixture')
    try:
        ledger.create_run(cfg['run_id'],cfg,nano('8'),nano('1'))
        ledger.import_external('fixture-connectivity',{'kind':'synthetic-exposure-not-stage9-real-import'},nano('0.01'),nano('0.0000705'))
        for language in ['en','vi']:
            root=state/language; root.mkdir(); module.generate(root)
            class Probe(FixtureSandbox):
                def command(self,command,timeout):
                    if command!='fixture-probe': raise ValueError('FIXED_FIXTURE_PROBE_ONLY')
                    self.commands.append(command)
                    # Fixed trusted process; never execute command supplied by a model.
                    observed=bounded([sys.executable,'-I','-c',"print('Kiểm tra tiếng Việt: Đặng')"],timeout)
                    output=root/'output'; output.mkdir()
                    (output/'hoa_don.jsonl').write_bytes(b'')
                    (output/'errors.jsonl').write_bytes(b'')
                    (output/'Đặng probe.txt').write_bytes(observed['stdout_bytes'])
                    return {'exit_code':observed['exit_code'],'timed_out':observed['timed_out'],
                            'stdout':observed['stdout_bytes'].decode('utf-8'),'stderr':'',
                            'stdout_truncated':False,'stderr_truncated':False}
            backend=Probe(); api=FixtureAPI([response([call()]),response([{'type':'message','content':[]}])])
            instruction=(repo/'prompts'/cfg['task']/(language+'.md')).read_text(encoding='utf-8')
            loop=run_trial(cfg,instruction,language,ledger,api,backend,lambda:True,state/(language+'-trajectory.jsonl'),nano('0.01'))
            requests+=len(api.inputs)
            raw=io.BytesIO()
            with tarfile.open(fileobj=raw,mode='w') as tar:
                for path in sorted(root.rglob('*')):
                    if path.is_file(): tar.add(path,arcname=path.relative_to(root).as_posix(),recursive=False)
            artifact=state/(language+'-collected'); extract_data(raw.getvalue(),artifact)
            process=bounded([sys.executable,'-I',str(repo/'tasks/b001-vn-invoice/tests/grader.py'),'--root',str(artifact)],10)
            verification=result_from_process(process)
            assert verification['status']=='verified' and verification['reward']==0
            assert (artifact/'output/Đặng probe.txt').read_text(encoding='utf-8').startswith('Kiểm tra')
            artifact_hashes={p.relative_to(artifact).as_posix():digest(p) for p in artifact.rglob('*') if p.is_file()}
            record=normalized(loop,verification,snapshot_id=snapshot(repo)['id'],artifact_sha256=artifact_hashes)
            assert not record['benchmark_result'] and loop['tool_calls']==1
            assert len(api.inputs)==2 and api.inputs[1]['input'][-1]['type']=='function_call_output'
            rows.append(record)
        # Invoice overlays are explicitly synthetic; raw request estimates remain.
        rid=ledger.db.execute('SELECT id FROM requests ORDER BY rowid LIMIT 1').fetchone()[0]
        ledger.invoice_revision(rid,1,nano('0.0001'),{'kind':'fixture-invoice','revision':1})
        ledger.invoice_revision(rid,2,nano('0.0002'),{'kind':'fixture-invoice','revision':2})
        accounting=ledger.inspect()
        assert accounting['inference_exposure_nano']==3*208608000+200000
        assert accounting['external_exposure_nano']==10000000
        backup=state/'fixture-usd-backup.sqlite3'
        with closing(sqlite3.connect(backup)) as copied: ledger.db.backup(copied)
    finally: ledger.close()
    with closing(sqlite3.connect(backup)) as restored:
        assert restored.execute('SELECT COUNT(*) FROM requests').fetchone()[0]==4
        assert restored.execute('SELECT COUNT(*) FROM tools').fetchone()[0]==2
        assert restored.execute('SELECT COUNT(*) FROM corrections').fetchone()[0]==2
    write_new(state/'normalized.json',rows)
    return {'kind':'offline-host-fixture-not-model-evaluation','fixture_trials':2,'fixture_requests':requests,
            'fixture_tool_executions':2,'trusted_data_verifier_rewards':[r['reward'] for r in rows],
            'normalization_keeps_fixture_origin':True,'invoice_revision_overlay_verified':True,
            'ledger_backup_restore_verified':True,'accounting':accounting,
            'container_integration':'not_run_default_wsl_docker_unavailable',
            'real_api_calls':0,'benchmark_trials':0,'credential_value_read':False}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--worker',type=Path)
    parser.add_argument('--output',type=Path,default=Path('reports/stage10-offline-validation.json'))
    parser.add_argument('--archive',type=Path,default=Path('reports/stage10-offline-evidence.tar.gz'))
    args=parser.parse_args()
    repo=Path(__file__).resolve().parents[1]
    if args.worker:
        write_new(args.worker.parent/'proof.json',worker(repo,args.worker)); return
    if not sys.platform.startswith('linux'): raise ValueError('NATIVE_LINUX_REQUIRED')
    output=repo/args.output; archive=repo/args.archive
    if output.exists() or archive.exists(): raise ValueError('EVIDENCE_ALREADY_EXISTS')
    validate_native_inputs(repo); before=inputs(repo)
    with tempfile.TemporaryDirectory(prefix='vi-stage10-native-') as temp:
        native=Path(temp)
        if str(native.resolve()).startswith('/mnt/'): raise ValueError('NATIVE_LINUX_REQUIRED')
        for name in before:
            target=native/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(repo/name,target)
        if inputs(native)!=before: raise ValueError('SOURCE_COPY_DRIFT')
        result=run_bounded([sys.executable,str(native/'scripts/stage10_validate_offline.py'),'--worker',str(native/'run')],timeout=60,cwd=str(native))
        if result['timed_out'] or result['returncode']!=0: raise ValueError('FIXTURE_INTEGRATION_FAILED: '+result['stderr'])
        if inputs(repo)!=before: raise ValueError('SOURCE_DRIFT_DURING_VALIDATION')
        proof=json.loads((native/'proof.json').read_text(encoding='utf-8'))
        with tarfile.open(archive,'x:gz') as tar: tar.add(native/'run',arcname='run')
        with tarfile.open(archive,'r:gz') as tar:
            assert json.loads(tar.extractfile('run/normalized.json').read())[0]['origin']=='offline-fixture'
            data=tar.extractfile('run/fixture-usd-backup.sqlite3').read()
            restore=native/'archive-restored.sqlite3'; restore.write_bytes(data)
        with closing(sqlite3.connect(restore)) as db: assert db.execute('SELECT COUNT(*) FROM requests').fetchone()[0]==4
        proof.update(schema='vi-stage10-offline/1',platform=platform.platform(),python=sys.version,
                     input_sha256=before,archive_sha256=digest(archive),archive_path=archive.relative_to(repo).as_posix(),
                     archive_restore_verified=True,execution_workspace='native-linux-byte-verified-copy')
        write_new(output,proof)
    print('Stage10 native fixture: 2 trials, 4 fixture requests, 2 fixed probes, real grader reward 0/0; no model or Docker calls')


if __name__=='__main__': main()
