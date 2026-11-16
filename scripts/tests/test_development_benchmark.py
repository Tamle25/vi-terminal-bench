import copy
import io
import json
from pathlib import Path
import sqlite3
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from development_contracts import planned,load,request_reserve,conservative_cost
from development_agent import DevelopmentGate,run_loop
from development_ledger import DevelopmentLedger
from development_sandbox import DevelopmentSandbox
from dev_benchmark import report
from development_verifier import pack,verify
from pilot_contracts import digest
from terminal_agent_v1 import OpenAIResponses,validate_config as old_validate
from usd_ledger_v1 import Ledger,nano
from test_terminal_stage10 import FixtureAPI,FixtureSandbox,call

ROOT=Path(__file__).resolve().parents[2]


def receipt(output=None):
    return {'http_status':200,'provider_request_id':'req_fixture','response':{'id':'resp_fixture',
        'model':'gpt-5.4-mini-2026-03-17','status':'completed','service_tier':'default',
        'output':output if output is not None else [{'type':'message','content':[]}],
        'usage':{'input_tokens':100,'output_tokens':20,'total_tokens':120,
                 'input_tokens_details':{'cached_tokens':20,'cache_write_tokens':0},
                 'output_tokens_details':{'reasoning_tokens':0}}}}


class DevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)
        self.cfg=load(ROOT/'configs/development-benchmark.json')
        self.plan=planned(ROOT,self.cfg,'development-smoke','fixture-development')
        self.plan['origin']='offline-fixture'
        self.ledger=DevelopmentLedger(self.root/'dev.sqlite3',account='fixture',pool_cap=nano('2'),origin='offline-fixture')
        self.addCleanup(self.ledger.close)
        self.ledger.create_run(self.plan['run_id'],self.plan,nano('2'),0)
        self.ledger.add_margin()
        self.ledger.import_external('old',{'kind':'fixture-old'},nano('.01'))

    def claim(self):
        trial=self.plan['planned_trials'][0]
        owner=self.ledger.claim_trial(self.plan['run_id'],trial['trial_id'],0)
        return trial,owner

    def test_plan_exact_36_and_pending_review_allowed(self):
        plan=planned(ROOT,self.cfg,'development-batch','batch-fixture')
        self.assertEqual(len(plan['planned_trials']),36)
        identities={(t['task_id'],t['language'],t['repeat']) for t in plan['planned_trials']}
        self.assertEqual(len(identities),36); self.assertEqual(len({t['configuration'] for t in plan['planned_trials']}),1)
        self.assertTrue(all(t['review_status']=='pending' for t in plan['planned_trials']))
        self.assertEqual(plan,planned(ROOT,self.cfg,'development-batch','batch-fixture'))

    def test_new_scope_does_not_open_old_reviewed_gate(self):
        with self.assertRaises(ValueError): old_validate(self.cfg)
        for scope in ['native-pilot','model-smoke','simulation']:
            with self.assertRaises(ValueError): planned(ROOT,self.cfg,scope,'fixture')

    def test_provisional_known_usage_releases_only_mapped_reservation(self):
        trial,_=self.claim()
        rid=self.ledger.claim_request(self.plan['run_id'],trial['trial_id'],1,'payload',request_reserve(self.cfg),6)
        held=self.ledger.inspect()['total_exposure_nano']
        self.assertEqual(held,nano('.11')+213216000)
        amount=self.ledger.record_provider(rid,receipt(),self.cfg)
        self.assertEqual(amount,165000)  # Cached tokens conservatively priced as uncached.
        self.assertEqual(self.ledger.inspect()['total_exposure_nano'],nano('.11')+165000)
        self.assertEqual(self.ledger.db.execute('SELECT reserve_i FROM requests').fetchone()[0],213216000)

    def test_unknown_usage_retains_hold_and_blocks_next_request(self):
        trial,_=self.claim(); tid=trial['trial_id']; run=self.plan['run_id']
        rid=self.ledger.claim_request(run,tid,1,'payload',request_reserve(self.cfg),6)
        bad=receipt(); bad['response']['usage'].pop('output_tokens_details')
        self.assertIsNone(self.ledger.record_provider(rid,bad,self.cfg))
        self.assertEqual(self.ledger.inspect()['inference_exposure_nano'],213216000)
        with self.assertRaisesRegex(ValueError,'UNRECONCILED_REQUEST'):
            self.ledger.claim_request(run,tid,2,'payload',213216000,6)

    def test_model_tier_usage_or_cache_fee_drift_stays_unknown(self):
        for field,value in [('model','other'),('service_tier','priority')]:
            bad=receipt(); bad['response'][field]=value; self.assertIsNone(conservative_cost(bad,self.cfg))
        for field,value in [('total_tokens',121),('input_tokens',True),('output_tokens',2049)]:
            bad=receipt(); bad['response']['usage'][field]=value; self.assertIsNone(conservative_cost(bad,self.cfg))
        bad=receipt(); bad['response']['usage']['input_tokens_details']['cache_write_tokens']=1
        self.assertIsNone(conservative_cost(bad,self.cfg))

    def test_namespace_rejects_old_db_without_modifying_it(self):
        path=self.root/'old.sqlite3'
        old=Ledger(path,account='fixture',pool_cap=nano('2'),origin='offline-fixture'); old.close()
        before=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'DEVELOPMENT_NAMESPACE_REQUIRED'):
            DevelopmentLedger(path,account='fixture',pool_cap=nano('2'),origin='offline-fixture')
        self.assertEqual(before,path.read_bytes())

    def test_invoice_overlay_not_added_to_provisional_settlement(self):
        trial,_=self.claim(); run=self.plan['run_id']; tid=trial['trial_id']
        rid=self.ledger.claim_request(run,tid,1,'payload',213216000,6)
        self.ledger.record_provider(rid,receipt(),self.cfg)
        self.ledger.invoice_revision(rid,1,120000,{'kind':'fixture-invoice'})
        self.assertEqual(self.ledger.inspect()['inference_exposure_nano'],120000)

    def test_crash_before_settlement_keeps_full_reservation(self):
        trial,_=self.claim(); rid=self.ledger.claim_request(self.plan['run_id'],trial['trial_id'],1,'payload',213216000,6)
        Ledger.record(self.ledger,rid,receipt(),165000,True)
        self.assertEqual(self.ledger.inspect()['inference_exposure_nano'],213216000)

    def test_loop_fixture_uses_tool_and_never_claims_real_benchmark(self):
        trial,owner=self.claim(); api=FixtureAPI([receipt([call()]),receipt()]); backend=FixtureSandbox()
        result=run_loop(self.cfg,self.plan,trial,'fixture instruction',self.ledger,api,backend,lambda:True,self.root/'trace.jsonl',owner)
        self.assertEqual(result['origin'],'offline-fixture'); self.assertEqual(result['tool_calls'],1)
        self.assertEqual(result['stop_reason'],'model_final'); self.assertEqual(len(api.inputs),2)
        self.assertEqual(api.inputs[1]['input'][-1]['type'],'function_call_output')
        self.assertIn('Đặng',api.inputs[1]['input'][-1]['output'])

    def test_development_gate_denies_other_scope_before_reading_key(self):
        cfgpath=self.root/'config.json'; cfgpath.write_text(json.dumps(self.cfg),encoding='utf-8')
        bad=copy.deepcopy(self.plan); bad['scope']='native-pilot'
        gate=DevelopmentGate(ROOT,cfgpath,self.root/'missing',bad,bad['planned_trials'][0],{}, {},FixtureSandbox(),self.ledger)
        api=OpenAIResponses(ROOT,gate)
        with patch('scoped_credentials._dotenv',side_effect=AssertionError('no key')),patch('terminal_agent_v1.subprocess.Popen') as process:
            with self.assertRaises(ValueError): api.send({},'fixture',1)
            process.assert_not_called()

    def test_outcome_commit_is_once_and_source_linked(self):
        trial,_=self.claim(); run=self.plan['run_id']; tid=trial['trial_id']
        self.ledger.finish(run,tid,{})
        row={'run_id':run,'trial_id':tid,'data_origin':'offline-fixture','reward':0}
        self.ledger.complete_outcome(run,tid,row)
        self.assertEqual(self.ledger.outcomes(run)[tid],row)
        with self.assertRaises(sqlite3.IntegrityError): self.ledger.complete_outcome(run,tid,row)

    def report_fixture(self):
        plan=planned(ROOT,self.cfg,'development-batch','report-fixture'); plan['origin']='offline-fixture'
        authoritative={}; root=self.root/'run'; root.mkdir()
        for trial in plan['planned_trials']:
            row={**trial,'run_id':plan['run_id'],'execution_scope':plan['scope'],'data_origin':plan['origin'],
                 'snapshot_id':plan['snapshot']['id'],'valid':True,'status':'completed','reward':1 if trial['language']=='en' else 0,
                 'cost_usd':0.0,'duration_sec':1,'tool_calls':1}
            path=root/trial['trial_id']; path.mkdir(); (path/'outcome.json').write_text(json.dumps(row),encoding='utf-8')
            authoritative[trial['trial_id']]=row
        return plan,root,authoritative

    def test_report_36_coverage_macro_and_paired_delta(self):
        plan,root,auth=self.report_fixture(); result=report(plan,root,self.root/'report',authoritative=auth)
        self.assertTrue(result['complete']); self.assertEqual(result['valid_trials'],36)
        self.assertEqual(result['scores']['en']['macro'],1); self.assertEqual(result['scores']['vi']['macro'],0)
        self.assertEqual(result['delta_vi_pp'],-100); self.assertIsNone(result['ci95'])
        self.assertEqual(result['data_origin'],'offline-fixture')
        self.assertEqual(load(self.root/'report/plan.json'),plan)

    def test_missing_trial_never_claims_full_coverage(self):
        plan,root,auth=self.report_fixture(); first=plan['planned_trials'][0]
        (root/first['trial_id']/'outcome.json').unlink()
        result=report(plan,root,self.root/'partial-report',authoritative=auth)
        self.assertFalse(result['complete']); self.assertEqual(len(result['missing_trials']),1)

    def test_tampered_reward_cannot_override_ledger(self):
        plan,root,auth=self.report_fixture(); tid=plan['planned_trials'][0]['trial_id']
        row=copy.deepcopy(auth[tid]); row['reward']=1-row['reward']
        (root/tid/'outcome.json').write_text(json.dumps(row),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'OUTCOME_FILE_LEDGER_DRIFT'):
            report(plan,root,self.root/'tampered-report',authoritative=auth)

    def test_tmpfs_collector_reads_inside_namespace_before_pause(self):
        data=io.BytesIO()
        with tarfile.open(fileobj=data,mode='w') as tar:
            item=tarfile.TarInfo('output/Đặng.txt'); item.size=2; tar.addfile(item,io.BytesIO(b'OK'))
        backend=DevelopmentSandbox('a'*64,'fixture','sha256:'+'b'*64,self.cfg)
        results=[{'exit_code':0,'timed_out':False,'truncated':[False,False],'stdout_bytes':data.getvalue()},
                 {'exit_code':0,'timed_out':False,'stdout_bytes':b''}]
        with patch.object(backend,'inspect',return_value={}),patch('development_sandbox.bounded',side_effect=results) as command:
            backend.collect(self.root/'collected')
            self.assertEqual(command.call_args_list[0].args[0][1],'exec')
            self.assertEqual(command.call_args_list[1].args[0][1],'pause')
        self.assertEqual((self.root/'collected/output/Đặng.txt').read_bytes(),b'OK')

    def test_verifier_stdin_has_no_host_bind_and_keeps_unicode_bytes(self):
        artifact=self.root/'artifacts'; artifact.mkdir(); (artifact/'Đặng.txt').write_bytes(b'\x00\xffbinary')
        with tarfile.open(fileobj=io.BytesIO(pack(artifact)),mode='r:') as archive:
            self.assertEqual(archive.extractfile('Đặng.txt').read(),b'\x00\xffbinary')
        with patch('development_verifier.subprocess.Popen') as process:
            child=process.return_value; child.returncode=1; child.communicate.return_value=(b'{"passed":false}',b'')
            value=verify(artifact,self.root,'sha256:'+'b'*64,'fixture')
            args,kw=process.call_args
            self.assertNotIn('--mount',args[0]); self.assertIn('-i',args[0]); self.assertIn('--read-only',args[0])
            self.assertNotIn('OPENAI_API_KEY',kw['env']); self.assertIsInstance(child.communicate.call_args.kwargs['input'],bytes)
            self.assertEqual(value['reward'],0)

    def test_runtime_selection_is_explicit_shared_relay(self):
        from dev_benchmark import profile_for
        profile=profile_for(self.cfg)
        self.assertEqual(profile['id'],'desktop-shared-relay-v2')
        self.assertEqual(profile['mode'],'scoped-relay'); self.assertEqual(profile['user'],'tamle')


if __name__=='__main__': unittest.main()
