import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dashboard import server
from dashboard.runtime_clock import RuntimeClock, stable_runtime_clock
from dashboard.recovery import archive_preloop_failure, eligible
import pilot_contracts
from development_contracts import planned, sources
from development_ledger import DevelopmentLedger
from usd_ledger_v1 import nano


class RuntimeClockTests(unittest.TestCase):
    def setUp(self):
        self.wall = dt.datetime(2026,11,13,7,0,tzinfo=dt.timezone.utc)
        self.boot = 1000000000
        self.clock = RuntimeClock(wall=lambda:self.wall, elapsed=lambda:self.boot)
        self.profile = server.load(server.ROOT/'configs/development-runtime-profiles.json')['profiles'][0]
        self.dev = SimpleNamespace(capture=lambda *args,**kwargs:{'kind':'fixture'})

    def evidence(self):
        now = pilot_contracts.dt.datetime.now(dt.timezone.utc)
        return {'kind':'runtime-capture','run_id':'fixture','snapshot_id':'snapshot',
                'runtime_profile_id':self.profile['id'],'runtime_profile_sha256':pilot_contracts.runtime_fingerprint(self.profile),
                'issued_at_utc':now.isoformat(),'expires_at_utc':(now+dt.timedelta(seconds=900)).isoformat(),
                'preflight':{'ready':True},'observation':{'user':'tamle','endpoint_class':self.profile['endpoint_class'],
                    'docker_os':'linux','filesystem_capabilities_ok':True,'verifier_network':'none',
                    'control_socket_in_sandbox':False,'socket_mode':'0600','lifecycle':'command-only',
                    'endpoint':'unix:///tmp/vi-bench-proxy-fixture/docker.sock'}}

    def test_backwards_wall_step_no_longer_rejects_fresh_capture(self):
        with stable_runtime_clock(self.dev,self.clock):
            e=self.evidence(); self.boot+=2000000000; self.wall-=dt.timedelta(seconds=3)
            self.assertEqual(pilot_contracts.validate_attestation(self.profile,e,'fixture','snapshot')[0],'pass')
            # Exactly the legacy failure when wall time is used explicitly.
            self.assertEqual(pilot_contracts.validate_attestation(self.profile,e,'fixture','snapshot',now=self.wall)[0],'fail')
            self.assertEqual(self.dev.capture()['runtime_clock']['policy'],'dashboard-boottime-utc-v1')

    def test_forward_wall_step_does_not_change_elapsed_ttl(self):
        with stable_runtime_clock(self.dev,self.clock):
            e=self.evidence();self.wall+=dt.timedelta(days=1);self.boot+=899000000000
            self.assertEqual(pilot_contracts.validate_attestation(self.profile,e,'fixture','snapshot')[0],'pass')
            self.boot+=1000000000
            self.assertEqual(pilot_contracts.validate_attestation(self.profile,e,'fixture','snapshot')[0],'fail')

    def test_suspend_time_expires_and_identity_is_still_enforced(self):
        with stable_runtime_clock(self.dev,self.clock):
            e=self.evidence()
            self.assertEqual(pilot_contracts.validate_attestation(self.profile,e,'other-run','snapshot')[0],'fail')
            bad=copy.deepcopy(e);bad['observation']['verifier_network']='host'
            self.assertEqual(pilot_contracts.validate_attestation(self.profile,bad,'fixture','snapshot')[0],'fail')
            self.boot+=901000000000
            self.assertEqual(pilot_contracts.validate_attestation(self.profile,e,'fixture','snapshot')[0],'fail')

    def test_clock_regression_process_change_and_scope_restore(self):
        original=pilot_contracts.dt;capture=self.dev.capture
        with self.assertRaisesRegex(ValueError,'REGRESSED_OR_PROCESS_CHANGED'):
            with stable_runtime_clock(self.dev,self.clock):
                self.boot-=1;pilot_contracts.dt.datetime.now(dt.timezone.utc)
        self.assertIs(pilot_contracts.dt,original);self.assertIs(self.dev.capture,capture)
        self.boot+=1
        with patch('dashboard.runtime_clock.os.getpid',return_value=self.clock.owner+1):
            with self.assertRaises(ValueError):self.clock.now(dt.timezone.utc)


class PreloopRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        cfg=server.load(server.ROOT/'configs/development-benchmark.json');cfg.update(state_root=str(self.root),account_reference='recovery-test')
        self.plan=planned(server.ROOT,cfg,'development-batch','dashboard-batch-123456789abc')
        self.path=self.root/'plan.json';server.atomic_json(self.path,self.plan)
        self.run=self.plan['run_id'];self.tid=self.plan['planned_trials'][0]['trial_id']
        self.folder=self.root/'runs'/self.run/self.tid;self.folder.mkdir(parents=True)
        self.row={**self.plan['planned_trials'][0],'run_id':self.run,'data_origin':'real-model','status':'infra_error',
                  'valid':False,'reward':None,'error_code':'GATE_DENIED_ATTESTATION_EXPIRED_OR_INVALID',
                  'raw_loop':None,'raw_verifier':None,'request_ids':[],'input_tokens':0,'output_tokens':0,
                  'cost_usd':None,'cleanup':'removed_owned_container'}
        server.atomic_json(self.folder/'outcome.json',self.row);server.atomic_json(self.folder/'runtime-attestation.json',{'kind':'fixture-preserved'})
        self.ledger=DevelopmentLedger(self.root/'ledger.sqlite3',account='recovery-test',pool_cap=nano('2'),origin='real')
        self.ledger.create_run(self.run,self.plan,nano('2'),0)
        self.ledger.claim_trial(self.run,self.tid,0);self.ledger.finish(self.run,self.tid,{})
        self.ledger.complete_outcome(self.run,self.tid,self.row)
        retained=self.plan['planned_trials'][1]['trial_id'];self.retained=retained
        self.ledger.claim_trial(self.run,retained,0);self.ledger.finish(self.run,retained,{})
        self.ledger.complete_outcome(self.run,retained,{'run_id':self.run,'trial_id':retained,'data_origin':'real-model','valid':True,'reward':0})
        self.addCleanup(self.ledger.close)

    def test_archive_rearms_only_zero_dispatch_slot_preserving_zero_reward_and_contract(self):
        before=self.ledger.outcomes(self.run)[self.retained]
        contract=self.ledger.db.execute('SELECT contract FROM runs WHERE id=?',(self.run,)).fetchone()[0]
        outcome_bytes=(self.folder/'outcome.json').read_bytes()
        result=archive_preloop_failure(server.ROOT,self.path,self.tid)
        self.assertFalse(self.folder.exists())
        archived=Path(result['audit']['archived_folder']);self.assertEqual((archived/'outcome.json').read_bytes(),outcome_bytes)
        self.assertEqual(self.ledger.outcomes(self.run)[self.retained],before)
        self.assertEqual(self.ledger.db.execute('SELECT contract FROM runs WHERE id=?',(self.run,)).fetchone()[0],contract)
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM requests').fetchone()[0],0)
        self.assertFalse(self.ledger.db.execute('PRAGMA foreign_key_check').fetchall())
        self.ledger.claim_trial(self.run,self.tid,0)

    def test_any_request_tool_trace_or_partial_loop_denies_recovery(self):
        for requests,tools in [([{'id':'request'}],[]),([],[{'call_id':'tool'}])]:
            with self.assertRaises(ValueError):eligible(requests,tools,self.row,self.folder)
        altered={**self.row,'raw_loop':{'model_requests':0}}
        with self.assertRaises(ValueError):eligible([],[],altered,self.folder)
        (self.folder/'trajectory.jsonl').write_text('',encoding='utf-8')
        with self.assertRaises(ValueError):eligible([],[],self.row,self.folder)

    def test_real_request_row_even_without_receipt_is_never_rearmed(self):
        with self.ledger.atomic():
            self.ledger.db.execute('INSERT INTO requests(id,run,trial,slot,payload,reserve_i,phase) VALUES (?,?,?,?,?,?,?)',
                ('must-retain',self.run,self.tid,1,'payload',213216000,'submitted'))
        with self.assertRaises(ValueError):archive_preloop_failure(server.ROOT,self.path,self.tid)
        self.assertTrue(self.folder.is_dir())
        self.assertEqual(self.ledger.db.execute('SELECT phase FROM requests WHERE id=?',('must-retain',)).fetchone()[0],'submitted')


class WorkerStartupTests(unittest.TestCase):
    def test_runtime_revision_does_not_precreate_new_run_directory(self):
        from dashboard import worker
        from provider_connectivity_v1 import write_new
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);run='dashboard-smoke-123456789abc'
            cfg={'state_root':str(root)}
            plan={'run_id':run,'source_sha256':{},'planned_trials':[{'trial_id':'first'}]}
            def freeze(cfg,scope,run_id,proof,output,smoke):write_new(output,plan)
            def execute(*args,**kwargs):
                self.assertFalse((root/'runs'/run).exists())
                self.assertTrue(list((root/'runtime-revisions'/run).glob('*.json')))
                raise RuntimeError('PROVIDER_NOT_CALLED_TEST_BOUNDARY')
            dev=SimpleNamespace(load=server.load,freeze_plan=freeze,execute=execute,write_new=write_new,
                                file_digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest())
            args=SimpleNamespace(action='smoke',run_id=run,target_run_id=None)
            with patch.object(worker,'pick_validation',return_value=root/'validation.json'),patch.object(worker,'readonly_ledger',return_value={}),patch.object(worker,'event'):
                with self.assertRaisesRegex(RuntimeError,'PROVIDER_NOT_CALLED_TEST_BOUNDARY'):
                    worker.execute_action(args,dev,root/'config.json',cfg,SimpleNamespace(receipt=lambda:{'policy':'fixture'}))


if __name__=='__main__':unittest.main()
