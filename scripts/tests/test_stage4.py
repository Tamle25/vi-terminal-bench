import copy
import datetime as dt
import json
import sys
import subprocess
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pilot_contracts import snapshot,runtime_fingerprint,validate_attestation,configuration_contract,compare_effective,digest
from pilot_readiness import evaluate
from review_records import validate_reviews,coverage
from model_dry_run import dry_run
from pilot_runner import Store,FakeProvider,Runner,SimulatedCrash,simulation_plan,export
from aggregate_results import aggregate

REPO=Path(__file__).resolve().parents[2]


def tiny_plan(count=2):
    rows=[{'trial_id':f'trial-{i}','task_id':'t','family_id':'family','track':'B','skill':'s','language':'vi','configuration':'cfg','repeat':i+1,'payload_sha256':'p','instruction_sha256':'i','configuration_sha256':'c'} for i in range(count)]
    return simulation_plan({'kind':'offline-dry-run-not-executable','planned_trials':rows},[{'task_id':'t','family_id':'family','track':'B','primary_skill':'s','languages':['vi']}],'snapshot')


def receipt(status='completed',reward=1,i=1000,c=100):return {'status':status,'reward':reward,'inference_micros':i,'compute_micros':c}


class Clock:
    def __init__(self):self.value=1000.
    def __call__(self):return self.value
    def advance(self,value=31):self.value+=value


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.plan=tiny_plan();self.clock=Clock();self.handles=[]
    def tearDown(self):
        for db in self.handles:db.close()
        self.temp.cleanup()
    def setup_store(self,scenarios=None):
        s=Store(self.root/'state.db',self.plan,self.clock);p=FakeProvider(self.root/'provider.db',scenarios);self.handles.extend([s.db,p.db]);return s,p
    def first_id(self):return self.plan['planned_trials'][0]['trial_id']
    def test_resume_completed_does_not_dispatch_twice(self):
        s,p=self.setup_store();Runner(s,p).run();count=p.call_count();Runner(s,p).run()
        self.assertEqual(count,2);self.assertEqual(p.call_count(),2);self.assertEqual(s.summary()['unfinished_trials'],0)
    def test_model_mode_never_reads_plan_or_creates_state(self):
        target=self.root/'must-not-create'
        result=subprocess.run([sys.executable,str(REPO/'scripts/pilot_runner.py'),'--mode','model','--plan',str(self.root/'missing.json'),'--state-dir',str(target)],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0);self.assertIn('Real model dispatch is not implemented',result.stderr);self.assertFalse(target.exists())
    def test_crash_after_reserve_safe_resume(self):
        s,p=self.setup_store();tid=self.first_id()
        with self.assertRaises(SimulatedCrash):Runner(s,p).run_one(tid,'after_reserve')
        self.assertEqual(p.call_count(),0);Runner(s,p).run_one(tid);self.assertEqual(p.call_count(),1)
    def test_crash_after_submission_requires_authoritative_absence(self):
        s,p=self.setup_store();tid=self.first_id()
        with self.assertRaises(SimulatedCrash):Runner(s,p).run_one(tid,'after_submit')
        self.assertEqual(Runner(s,p).run_one(tid),'active-lease');self.clock.advance()
        self.assertEqual(Runner(s,p).run_one(tid),'uncertain-no-receipt');self.assertEqual(p.call_count(),0)
        row=s.latest(tid)
        with self.assertRaises(ValueError):s.confirm_not_submitted(tid,{},p)
        s.confirm_not_submitted(tid,{'kind':'simulation-authoritative-not-received','request_id':row['request_id']},p)
        Runner(s,p).run_one(tid);self.assertEqual(p.call_count(),1)
    def test_crash_after_provider_reconciles_without_resend(self):
        s,p=self.setup_store();tid=self.first_id()
        with self.assertRaises(SimulatedCrash):Runner(s,p).run_one(tid,'after_provider')
        self.clock.advance();Runner(s,p).run_one(tid)
        self.assertEqual(p.call_count(),1);self.assertEqual(s.latest(tid)['phase'],'completed')
    def test_actual_subprocess_crash_after_provider_receipt(self):
        s,p=self.setup_store();tid=self.first_id();path=self.root/'plan.json';path.write_text(json.dumps(self.plan))
        code='import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from pilot_runner import Store,FakeProvider,Runner;s=Store(Path(sys.argv[2])/"state.db",json.loads(Path(sys.argv[3]).read_text()),lambda:1000.);p=FakeProvider(Path(sys.argv[2])/"provider.db");Runner(s,p).run_one(sys.argv[4],"after_provider")'
        result=subprocess.run([sys.executable,'-c',code,str(REPO/'scripts'),str(self.root),str(path),tid],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0);self.assertIn('SimulatedCrash',result.stderr)
        self.clock.advance();Runner(s,p).run_one(tid);self.assertEqual(p.call_count(),1);self.assertEqual(s.latest(tid)['phase'],'completed')
    def test_retry_charges_both_attempts(self):
        tid=self.first_id();s,p=self.setup_store({tid+':1':receipt('retryable_infra_error',None,250,50)})
        Runner(s,p).run();rows=list(s.db.execute('SELECT * FROM attempts WHERE trial_id=?',(tid,)))
        self.assertEqual(len(rows),2);self.assertEqual(sum(row['actual_i'] for row in rows),1250);self.assertEqual(s.summary()['unfinished_trials'],0)
    def test_verifier_retry_and_two_retry_limit(self):
        tid=self.first_id();scenario={tid+f':{n}':receipt('verifier_error',None,200,50) for n in range(1,4)}
        s,p=self.setup_store(scenario);Runner(s,p).run()
        self.assertEqual(s.latest(tid)['number'],3);self.assertEqual(p.call_count(),4)
    def test_agent_failure_never_retried(self):
        tid=self.first_id();s,p=self.setup_store({tid+':1':receipt('agent_failure',0)})
        Runner(s,p).run();self.assertEqual(s.latest(tid)['number'],1);self.assertEqual(s.latest(tid)['phase'],'agent_failure')
    def test_unknown_cost_holds_reservation_and_preserves_known_reward(self):
        tid=self.first_id();s,p=self.setup_store({tid+':1':receipt(i=None,c=None)})
        Runner(s,p).run_one(tid);self.assertEqual(s.summary()['exposure_micro_units'],self.plan['reservation'])
        self.assertIsNone(s.reserve(self.plan['planned_trials'][1]['trial_id']))
        rows,summary=export(s,p,self.root/'export');self.assertEqual(rows[0]['reward'],1);self.assertIsNone(rows[0]['cost_usd']);self.assertEqual(summary['uncertain_attempts'],1)
        p.resolve(s.latest(tid)['request_id'],receipt());Runner(s,p).run_one(tid)
        self.assertEqual(s.latest(tid)['phase'],'completed');self.assertEqual(p.call_count(),1)
    def test_unknown_provider_no_auto_retry(self):
        tid=self.first_id();s,p=self.setup_store({tid+':1':receipt('unknown',None,None,None)})
        Runner(s,p).run_one(tid);Runner(s,p).run_one(tid);self.assertEqual(p.call_count(),1);self.assertEqual(s.latest(tid)['phase'],'uncertain')
    def test_null_reward_rejected_not_coerced(self):
        tid=self.first_id();s,p=self.setup_store({tid+':1':receipt(reward=None)})
        with self.assertRaises(ValueError):Runner(s,p).run_one(tid)
        self.assertEqual(s.latest(tid)['phase'],'submitted')
    def test_budget_exhaustion_never_dispatches(self):
        self.plan['caps']={'inference':100,'compute':10};s,p=self.setup_store();Runner(s,p).run()
        self.assertEqual(p.call_count(),0);self.assertEqual(s.summary()['unfinished_trials'],2)
    def test_observed_overrun_stops_future_dispatches(self):
        self.plan['caps']={'inference':2000,'compute':200};tid=self.first_id();s,p=self.setup_store({tid+':1':receipt(i=2500,c=250)})
        Runner(s,p).run_one(tid);Runner(s,p).run()
        self.assertEqual(p.call_count(),1);self.assertEqual(s.summary()['exposure_micro_units']['inference'],2500)
        self.assertTrue(s.db.execute("SELECT 1 FROM events WHERE event='reservation_overrun'").fetchone())
    def test_cancel_only_before_submit(self):
        s,p=self.setup_store();tid=self.first_id();s.reserve(tid);s.cancel_reserved(tid);self.assertEqual(s.exposure(),{'inference':0,'compute':0})
        with self.assertRaises(ValueError):s.cancel_reserved(tid)
    def test_changed_snapshot_budget_or_profile_refuses_resume(self):
        s,p=self.setup_store()
        for field,value in [('snapshot_id','changed'),('caps',{'inference':999,'compute':999})]:
            altered=copy.deepcopy(self.plan);altered[field]=value
            with self.assertRaises(ValueError):Store(self.root/'state.db',altered,self.clock)
    def test_compare_and_swap_double_start(self):
        s,p=self.setup_store();tid=self.first_id();first=s.reserve(tid);second=s.reserve(tid)
        self.assertEqual(first['request_id'],second['request_id']);self.assertTrue(s.submit(tid,1,'worker1'));self.assertFalse(s.submit(tid,1,'worker2'))
        self.assertEqual(Runner(s,p).run_one(tid),'active-lease');self.assertEqual(p.call_count(),0)
    def test_two_workers_do_not_double_dispatch(self):
        s,p=self.setup_store();tid=self.first_id();barrier=threading.Barrier(2);errors=[]
        def worker():
            local=None;provider=None
            try:
                local=Store(self.root/'state.db',self.plan,self.clock);provider=FakeProvider(self.root/'provider.db');barrier.wait(timeout=5);Runner(local,provider).run_one(tid)
            except Exception as exc:errors.append(exc)
            finally:
                if local:local.db.close()
                if provider:provider.db.close()
        threads=[threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads));self.assertEqual(errors,[]);self.assertEqual(p.call_count(),1)
    def test_simulation_cannot_be_scored_as_model(self):
        s,p=self.setup_store();Runner(s,p).run();rows,_=export(s,p,self.root/'export')
        with self.assertRaises(ValueError):aggregate(rows,self.plan['task_manifest'])
        result=aggregate(rows,self.plan['task_manifest'],run_plan=self.plan)
        self.assertEqual(result['result_kind'],'simulation-not-model-evaluation')
        mixed=copy.deepcopy(rows);mixed[0].pop('data_origin')
        with self.assertRaises(ValueError):aggregate(mixed,self.plan['task_manifest'],run_plan=self.plan)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=REPO/'build');self.prompt=Path(self.temp.name)/'fixture.md';self.prompt.write_text('Synthetic unit-test prompt, no model called',encoding='utf-8')
        self.now=dt.datetime(2026,11,12,tzinfo=dt.timezone.utc);self.profile=json.loads((REPO/'configs/model-pilot.template.json').read_text())
        self.profile['budget']={k:10 for k in self.profile['budget']}
        for config in self.profile['configurations']:
            config.update(agent='fixture-agent',agent_version='fixture-v1',model='fixture-model',provider='fixture-provider',endpoint='https://provider.invalid',reasoning_effort='not-applicable',system_prompt_path=str(self.prompt.relative_to(REPO)),max_tokens=100,max_turns=5,timeout_sec=300,architecture='host-agent-offline-sandbox',credential_env_name='FIXTURE_KEY_NAME')
        self.catalog=json.loads((REPO/'configs/runtime-profiles.json').read_text());self.catalog['selected_runtime_profile']='native-wsl-v1';self.runtime=self.catalog['profiles'][0];self.snap=snapshot(REPO)
        self.attest={'kind':'runtime-capture','run_id':self.profile['run_id'],'snapshot_id':self.snap['id'],'runtime_profile_id':self.runtime['id'],'runtime_profile_sha256':runtime_fingerprint(self.runtime),'issued_at_utc':self.now.isoformat(),'expires_at_utc':(self.now+dt.timedelta(minutes=5)).isoformat(),'preflight':{'ready':True},'observation':{'user':'tamle','endpoint_class':self.runtime['endpoint_class'],'docker_os':'linux','filesystem_capabilities_ok':True,'verifier_network':'none','control_socket_in_sandbox':False,'endpoint':'unix:///var/run/docker.sock'}}
        self.reviews=[{'task_id':tid,'task_version':row['version'],'payload_sha256':row['payload_sha256'],'prompt_hashes':row['prompts'],'author':row['author'],'reviewer':'Synthetic Unit Fixture Reviewer','reviewer_kind':'human','reviewed_at':'2026-11-12','expert_time_sec':60,'decision':'accepted','notes':'Synthetic in-memory test record, not an actual review'} for tid,row in self.snap['tasks'].items()]
        preview=dry_run(self.profile,REPO);expected={r['configuration']:r['configuration_sha256'] for r in preview['planned_trials']}
        self.adapter={'kind':'agent-verified','configuration_fingerprints':expected,'runtime_profile_sha256':runtime_fingerprint(self.runtime)}
        self.budget={'origin':'provider-estimate-and-ledger','currency':'USD','pricing_state':'verified-current','cost_uncertain':False,'price_source':'synthetic unit-test data, never a real price quote','run_id':self.profile['run_id'],'scope':'native-pilot','configuration_fingerprints':expected,'remaining_inference_usd':5,'remaining_compute_usd':5,'reserve_inference_usd':1,'reserve_compute_usd':1}
        self.manifest={'kind':'model-pilot','run_id':self.profile['run_id'],'snapshot_id':self.snap['id'],'expected_configurations':preview['expected_configurations'],'planned_trials':preview['planned_trials']}
    def tearDown(self):self.temp.cleanup()
    def evaluate(self,**changes):
        kwargs={'runtime_evidence':self.attest,'reviews':self.reviews,'adapter_evidence':self.adapter,'budget_evidence':self.budget,'run_manifest':self.manifest,'now':self.now};kwargs.update(changes)
        return evaluate(REPO,self.profile,self.catalog,**kwargs)
    def test_all_evidence_coherent_is_not_an_authorization_token(self):
        report=self.evaluate();self.assertTrue(report['ready_for_dispatch']);self.assertFalse(report['authorization_token']);self.assertEqual(report['model_calls'],0)
    def test_each_gate_failure_means_no_dispatch(self):
        for field,value in [('runtime_evidence',None),('reviews',[]),('adapter_evidence',None),('budget_evidence',None),('run_manifest',None)]:
            report=self.evaluate(**{field:value});calls=[]
            if report['ready_for_dispatch']:calls.append('fake-dispatch')
            self.assertEqual(calls,[],field)
        self.profile['configurations'][0]['model']=None;self.assertFalse(self.evaluate()['ready_for_dispatch'])
    def test_unselected_runtime_no_silent_relay(self):
        self.catalog['selected_runtime_profile']=None;self.assertFalse(self.evaluate()['ready_for_dispatch'])
    def test_expired_other_run_endpoint_and_snapshot(self):
        for key,value in [('run_id','other'),('snapshot_id','changed'),('expires_at_utc',(self.now-dt.timedelta(seconds=1)).isoformat())]:
            data=copy.deepcopy(self.attest);data[key]=value;self.assertNotEqual(validate_attestation(self.runtime,data,self.profile['run_id'],self.snap['id'],self.now)[0],'pass')
        data=copy.deepcopy(self.attest);data['observation']['endpoint']='tcp://wrong:1234';self.assertEqual(validate_attestation(self.runtime,data,self.profile['run_id'],self.snap['id'],self.now)[0],'fail')
    def test_simulated_attestation_or_budget_never_real_evidence(self):
        self.attest['kind']='simulation-attestation';self.assertFalse(self.evaluate()['ready_for_dispatch'])
        self.attest['kind']='runtime-capture';self.budget['currency']='SIM_USD';self.assertFalse(self.evaluate()['ready_for_dispatch'])
    def test_review_changed_prompt_or_author_rejected(self):
        for field,value in [('payload_sha256','old'),('author','false-author'),('reviewer','Codex-assisted')]:
            reviews=copy.deepcopy(self.reviews);reviews[0][field]=value
            with self.assertRaises(ValueError):validate_reviews(self.snap,reviews)
    def test_missing_configuration_and_preview_not_executable(self):
        self.manifest['planned_trials']=self.manifest['planned_trials'][:36];self.assertFalse(self.evaluate()['ready_for_dispatch'])
        self.manifest['kind']='offline-dry-run-not-executable';self.assertFalse(self.evaluate()['ready_for_dispatch'])
    def test_effective_contract_and_ephemeral_endpoint(self):
        contract=configuration_contract(self.profile['configurations'][0],'prompt-hash',self.runtime,1,['terminal'],{'source':'task.toml'})
        observed=copy.deepcopy(contract);compare_effective(contract,observed)
        observed['tool_access']=['extra-tool']
        with self.assertRaises(ValueError):compare_effective(contract,observed)
        runtime=copy.deepcopy(self.catalog['profiles'][1]);first=copy.deepcopy(self.attest)
        first.update(runtime_profile_id=runtime['id'],runtime_profile_sha256=runtime_fingerprint(runtime));first['observation'].update(endpoint_class=runtime['endpoint_class'],endpoint='unix:///tmp/vi-bench-proxy-one/docker.sock',socket_mode='0600',lifecycle='command-only')
        second=copy.deepcopy(first);second['observation']['endpoint']='unix:///tmp/vi-bench-proxy-two/docker.sock'
        self.assertEqual(validate_attestation(runtime,first,self.profile['run_id'],self.snap['id'],self.now)[0],'pass')
        self.assertEqual(validate_attestation(runtime,second,self.profile['run_id'],self.snap['id'],self.now)[0],'pass');self.assertEqual(first['runtime_profile_sha256'],second['runtime_profile_sha256'])


@unittest.skipUnless(os.name=='posix','Linux runtime capture')
class CaptureTests(unittest.TestCase):
    def profile(self):
        import pwd
        result=json.loads((REPO/'configs/runtime-profiles.json').read_text())['profiles'][0]
        result['user']=pwd.getpwuid(os.getuid()).pw_name
        return result
    def test_capture_uses_exact_run_and_scope(self):
        from capture_runtime_attestation import capture
        with patch.dict(os.environ,{'DOCKER_HOST':'unix:///var/run/docker.sock','DOCKER_CONTEXT':''}),patch('capture_runtime_attestation.inspect',return_value={'ready':True,'docker_os':'linux'}):
            report=capture(REPO,self.profile(),'fixture-run',60)
        self.assertTrue(report['ready']);self.assertEqual(report['run_id'],'fixture-run');self.assertFalse(report['authorization_token'])
    def test_remote_or_mismatched_endpoint_rejected_before_probe(self):
        from capture_runtime_attestation import capture
        for endpoint in ['tcp://remote:2375','unix:///tmp/unselected.sock']:
            with patch.dict(os.environ,{'DOCKER_HOST':endpoint,'DOCKER_CONTEXT':''}),patch('capture_runtime_attestation.inspect',side_effect=AssertionError('Do not probe unselected endpoint')):
                with self.assertRaises(ValueError):capture(REPO,self.profile(),'fixture-run',60)


if __name__=='__main__':unittest.main()
