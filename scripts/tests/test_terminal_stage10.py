from contextlib import closing
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
import terminal_agent_v1 as agent
import terminal_sandbox_v1 as sandbox
import terminal_smoke_v1 as controller
from terminal_verifier_v1 import result_from_process, normalized
from usd_ledger_v1 import Ledger, nano


def config():
    return json.loads((Path(__file__).resolve().parents[2]/'configs/stage10-smoke.draft.json').read_text(encoding='utf-8'))


def response(output, tokens=50):
    return {'http_status':200,'provider_request_id':'req_fixture','response':{
        'id':'resp_fixture','model':agent.MODEL,'status':'completed','service_tier':'default','output':output,
        'usage':{'input_tokens':tokens,'output_tokens':20,'input_tokens_details':{'cached_tokens':0}}}}


def call(command='fixture-probe', call_id='call_fixture'):
    return {'type':'function_call','name':'terminal','call_id':call_id,'arguments':json.dumps({'command':command})}


class FixtureAPI:
    origin='offline-fixture'
    def __init__(self, outputs): self.outputs=outputs; self.inputs=[]
    def send(self,payload,rid,timeout):
        self.inputs.append(copy.deepcopy(payload))
        value=self.outputs[len(self.inputs)-1]
        if isinstance(value,Exception): raise value
        return value


class FixtureSandbox:
    origin='offline-fixture'
    def __init__(self): self.commands=[]
    def command(self,command,timeout):
        self.commands.append(command)
        return {'exit_code':0,'timed_out':False,'stdout':'Tiếng Việt NFC: Đặng; NFD: Đa\u0323ng',
                'stderr':'','stdout_truncated':False,'stderr_truncated':False}


class Stage10Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.cfg=config()
        self.ledger=Ledger(self.root/'pool.sqlite3',account='fixture',pool_cap=nano('10'),origin='offline-fixture')
        self.addCleanup(self.ledger.close)
        self.ledger.create_run(self.cfg['run_id'],self.cfg,nano('8'),nano('1'))
        self.backend=FixtureSandbox()

    def loop(self, api, gate=lambda:True, instruction='Instruction VI', lang='vi'):
        return agent.run_trial(self.cfg,instruction,lang,self.ledger,api,self.backend,gate,self.root/(lang+'.jsonl'),nano('0.01'))

    def test_tool_history_and_unicode_preserved(self):
        api=FixtureAPI([response([{'type':'reasoning','summary':[]},call()]),response([{'type':'message','content':[]}])])
        result=self.loop(api)
        self.assertEqual(result['tool_calls'],1); self.assertEqual(result['stop_reason'],'model_final')
        self.assertEqual(api.inputs[1]['input'][1]['type'],'reasoning')
        last=api.inputs[1]['input'][-1]
        self.assertEqual(last['type'],'function_call_output'); self.assertEqual(last['call_id'],'call_fixture')
        self.assertIn('Đặng',last['output']); self.assertIn('Đa\u0323ng',last['output'])
        self.assertIsNone(result['reward']); self.assertFalse(result['benchmark_result'])

    def test_gate_denied_before_claim_or_key(self):
        api=FixtureAPI([])
        with patch.object(agent,'credential_scope',side_effect=AssertionError('no key')):
            with self.assertRaisesRegex(ValueError,'GATE_DENIED'): self.loop(api,lambda:False)
        self.assertFalse(api.inputs)
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM trials').fetchone()[0],0)

    def test_gate_change_stops_before_next_request(self):
        checks=iter([True,True,True,False])
        api=FixtureAPI([response([call()])])
        result=self.loop(api,lambda:next(checks))
        self.assertEqual(len(api.inputs),1); self.assertEqual(result['stop_reason'],'gate_or_config_changed')

    def test_unknown_tool_or_duplicate_argument_never_executes(self):
        for index,item in enumerate([dict(call(),name='host_shell'),dict(call(),arguments='{"command":"x","command":"y"}'),dict(call(),arguments='{"command":"x","extra":1}')]):
            cfg=copy.deepcopy(self.cfg); cfg['run_id']+='-'+str(index)
            self.ledger.create_run(cfg['run_id'],cfg,nano('1'),nano('1'))
            api=FixtureAPI([response([item])])
            result=agent.run_trial(cfg,'test','en',self.ledger,api,self.backend,lambda:True,self.root/(str(index)+'.jsonl'),0)
            self.assertEqual(result['stop_reason'],'tool_or_gate_failure')
        self.assertEqual(self.backend.commands,[])

    def test_missing_usage_retains_unknown_and_stops(self):
        bad=response([call()]); bad['response'].pop('usage')
        result=self.loop(FixtureAPI([bad]))
        self.assertEqual(result['stop_reason'],'provider_uncertain')
        self.assertEqual(self.ledger.inspect()['uncertain_requests'],1)
        self.assertEqual(self.ledger.inspect()['inference_exposure_nano'],agent.request_reserve(self.cfg))
        self.assertFalse(self.backend.commands)

    def test_timeout_no_retry_and_no_exception_secret(self):
        api=FixtureAPI([TimeoutError('Bearer sk-fixture-do-not-log')])
        result=self.loop(api)
        self.assertEqual(result['stop_reason'],'provider_uncertain'); self.assertEqual(len(api.inputs),1)
        self.assertNotIn('sk-fixture',(self.root/'vi.jsonl').read_text(encoding='utf-8'))

    def test_repeated_trial_cannot_resubmit(self):
        self.loop(FixtureAPI([response([{'type':'message'}])]))
        api=FixtureAPI([])
        with self.assertRaises(sqlite3.IntegrityError): self.loop(api)
        self.assertFalse(api.inputs)

    def test_context_limit_before_network(self):
        api=FixtureAPI([]); result=self.loop(api,instruction='x'*20000)
        self.assertEqual(result['stop_reason'],'context_limit'); self.assertFalse(api.inputs)

    def test_request_bound_and_repeated_tool_id(self):
        api=FixtureAPI([response([call(call_id='call_'+str(i))]) for i in range(4)])
        result=self.loop(api)
        self.assertEqual(len(api.inputs),4); self.assertEqual(result['stop_reason'],'request_limit')

    def test_repeated_call_id_is_not_executed_twice(self):
        result=self.loop(FixtureAPI([response([call()]),response([call()])]))
        self.assertEqual(result['stop_reason'],'tool_or_gate_failure'); self.assertEqual(len(self.backend.commands),1)

    def test_real_origin_cannot_bypass_real_binding(self):
        api=FixtureAPI([]); api.origin='real'
        with self.assertRaisesRegex(ValueError,'REAL_BINDING_MISMATCH'): self.loop(api)
        with self.assertRaisesRegex(ValueError,'REAL_GATE_REQUIRED'): agent.OpenAIResponses(self.root,lambda:True)

    def test_config_drift_after_response_stops_tool(self):
        api=FixtureAPI([response([call()])]); original=api.send
        def changed(*args):
            result=original(*args); self.cfg['max_payload_bytes']=20000; return result
        api.send=changed
        result=self.loop(api)
        self.assertEqual(result['stop_reason'],'tool_or_gate_failure'); self.assertFalse(self.backend.commands)

    def test_pool_external_import_is_idempotent_and_not_double_counted(self):
        self.ledger.import_external('connectivity',{'receipt':'fixture'},nano('0.01'),nano('0.0000705'))
        self.ledger.import_external('connectivity',{'receipt':'fixture'},nano('0.01'),nano('0.0000705'))
        self.assertEqual(self.ledger.inspect()['external_exposure_nano'],nano('0.01'))
        with self.assertRaisesRegex(ValueError,'EXTERNAL_EVIDENCE_DRIFT'):
            self.ledger.import_external('connectivity',{'receipt':'different'},nano('0.01'))

    def test_cap_shared_across_runs(self):
        self.ledger.import_external('other',{'id':'other'},nano('9.8'))
        result=self.loop(FixtureAPI([]))
        self.assertEqual(result['stop_reason'],'accounting_stop')
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM requests').fetchone()[0],0)

    def test_claim_is_durable_before_send(self):
        api=FixtureAPI([response([{'type':'message'}])]); original=api.send
        def observe(request,rid,timeout):
            with closing(sqlite3.connect(self.root/'pool.sqlite3')) as db:
                self.assertEqual(db.execute('SELECT phase FROM requests WHERE id=?',(rid,)).fetchone()[0],'submitted')
            return original(request,rid,timeout)
        api.send=observe; self.loop(api)

    def test_crash_after_submit_keeps_claim_and_blocks_new_run(self):
        self.ledger.claim_trial(self.cfg['run_id'],'old',0)
        self.ledger.claim_request(self.cfg['run_id'],'old',1,'hash',100,4)
        self.ledger.finish(self.cfg['run_id'],'old',{})
        with self.assertRaisesRegex(ValueError,'UNRECONCILED_REQUEST'): self.loop(FixtureAPI([]))

    def test_unknown_tool_execution_blocks_new_trial(self):
        self.ledger.claim_trial(self.cfg['run_id'],'old',0)
        self.ledger.tool_intent(self.cfg['run_id'],'old','call_x','hash')
        self.ledger.finish(self.cfg['run_id'],'old',{})
        with self.assertRaisesRegex(ValueError,'UNRECONCILED_TOOL'): self.loop(FixtureAPI([]))

    def test_invoice_revision_is_overlay_not_sum(self):
        self.ledger.claim_trial(self.cfg['run_id'],'old',0)
        rid=self.ledger.claim_request(self.cfg['run_id'],'old',1,'hash',100,4)
        self.ledger.record(rid,{'usage':'fixture'},50,True)
        self.assertEqual(self.ledger.inspect()['inference_exposure_nano'],100)
        self.ledger.invoice_revision(rid,1,40,{'invoice':'fixture-rev1'})
        self.ledger.invoice_revision(rid,2,70,{'invoice':'fixture-rev2'})
        self.assertEqual(self.ledger.inspect()['inference_exposure_nano'],70)
        self.assertEqual(self.ledger.db.execute('SELECT estimate_i FROM requests').fetchone()[0],50)
        with self.assertRaisesRegex(ValueError,'REVISION_ORDER'): self.ledger.invoice_revision(rid,2,0,{'bad':True})

    def test_overrun_preserved_and_blocks_future_request(self):
        self.ledger.claim_trial(self.cfg['run_id'],'old',0)
        rid=self.ledger.claim_request(self.cfg['run_id'],'old',1,'hash',100,4)
        self.ledger.record(rid,{},nano('11'),True)
        self.assertLess(self.ledger.inspect()['available_nano'],0)
        with self.assertRaisesRegex(ValueError,'BUDGET_DENIED'):
            self.ledger.claim_request(self.cfg['run_id'],'old',2,'hash',100,4)

    def test_pool_identity_origin_and_contract_cannot_drift(self):
        with self.assertRaisesRegex(ValueError,'POOL_IDENTITY_DRIFT'):
            Ledger(self.root/'pool.sqlite3',account='fixture',pool_cap=nano('10'),origin='real')
        with self.assertRaisesRegex(ValueError,'RUN_DRIFT'):
            self.ledger.create_run(self.cfg['run_id'],{'changed':True},nano('8'),nano('1'))

    def test_simultaneous_controllers_cannot_claim_two_trials(self):
        other=Ledger(self.root/'pool.sqlite3',account='fixture',pool_cap=nano('10'),origin='offline-fixture')
        self.addCleanup(other.close)
        self.ledger.claim_trial(self.cfg['run_id'],'en',0)
        with self.assertRaisesRegex(ValueError,'CONCURRENCY_DENIED'): other.claim_trial(self.cfg['run_id'],'vi',0)

    def test_nano_exact_and_bool_rejected(self):
        self.assertEqual(nano('0.0000705'),70500)
        for value in ['NaN','-1','0.0000000001',True,'invalid']:
            with self.assertRaises(ValueError): nano(value)

    def test_verifier_zero_is_valid_and_fixture_cannot_become_benchmark(self):
        result=result_from_process({'timed_out':False,'exit_code':1,'stdout_bytes':b'{"passed":false}', 'truncated':[False,False]})
        self.assertEqual(result['reward'],0)
        trial={'origin':'offline-fixture','trial_id':'x','language':'vi','stop_reason':'model_final','tool_calls':1,'trajectory':'fixture'}
        value=normalized(trial,result,snapshot_id='fixture',artifact_sha256='hash')
        self.assertFalse(value['benchmark_result'])
        self.assertEqual(value['reward'],0)

    def test_verifier_error_is_not_reward_zero(self):
        for code, data in [(2,b'{}'),(1,b'{"passed":true}'),(0,b'not json'),(0,b'[]')]:
            self.assertIsNone(result_from_process({'timed_out':False,'exit_code':code,'stdout_bytes':data,'truncated':[False,False]})['reward'])

    def archive(self,name,kind=None,size=1):
        raw=io.BytesIO()
        with tarfile.open(fileobj=raw,mode='w') as tar:
            item=tarfile.TarInfo(name)
            if kind: item.type=kind; item.linkname='/etc/passwd'
            else: item.size=size
            tar.addfile(item,None if kind else io.BytesIO(b'x'*size))
        return raw.getvalue()

    def test_artifact_archive_rejects_traversal_links_and_size(self):
        for index,(name,kind,size) in enumerate([('../escape',None,1),('/escape',None,1),('link',tarfile.SYMTYPE,1),('hard',tarfile.LNKTYPE,1),('a\\b',None,1),('big',None,20)]):
            target=self.root/('bad'+str(index))
            with self.assertRaises(ValueError): sandbox.extract_data(self.archive(name,kind,size),target,10)
            self.assertFalse(target.exists())

    def test_artifact_unicode_bytes_and_existing_path(self):
        target=self.root/'artifacts'; sandbox.extract_data(self.archive('output/Đặng.txt'),target)
        self.assertEqual((target/'output/Đặng.txt').read_bytes(),b'x')
        with self.assertRaisesRegex(ValueError,'DESTINATION_EXISTS'): sandbox.extract_data(self.archive('x'),target)

    def test_container_identity_and_command_are_not_host_shell(self):
        cid='a'*64; image='sha256:'+'b'*64
        backend=sandbox.DockerSandbox(cid,'run',image,self.cfg)
        with patch.object(backend,'inspect',return_value={}),patch.object(sandbox,'bounded') as run:
            run.return_value={'exit_code':0,'timed_out':False,'truncated':[False,False],'stdout_bytes':b'{"exit_code":0}'}
            hostile='echo $(touch /host/escape); unicode Đặng'
            backend.command(hostile,3)
            command=run.call_args.args[0]
            self.assertEqual(command[:5],['docker','exec','-w','/app',cid]); self.assertIn(hostile,command)
            self.assertNotIn('shell',run.call_args.kwargs)
        with self.assertRaises(ValueError): sandbox.DockerSandbox('--privileged','run',image,self.cfg)

    def test_container_creation_has_network_resource_and_storage_limits(self):
        args=sandbox.DockerSandbox.create_args('sha256:'+'b'*64,'run',self.cfg)
        for value in ['--read-only','--network','none','--cap-drop','ALL','--pids-limit','128','/app/output:rw,nosuid,nodev,size=16m']:
            self.assertIn(value,args)
        self.assertNotIn('--privileged',args)

    def test_unknown_real_config_cannot_make_api_call(self):
        api=FixtureAPI([]); self.cfg['model']='other'
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_EFFECTIVE_CONFIG'): self.loop(api)
        self.assertFalse(api.inputs)

    def test_full_model_input_reserve_is_exact(self):
        self.assertEqual(agent.request_reserve(self.cfg),208608000)
        self.assertEqual(agent.request_reserve(self.cfg)*8,nano('1.668864'))

    def test_process_capture_is_bounded_and_excludes_host_api_key(self):
        with patch.dict(sandbox.os.environ,{'OPENAI_API_KEY':'fixture-never-real'}):
            result=sandbox.bounded([sys.executable,'-c',"import os,sys; print('OPENAI_API_KEY' in os.environ); sys.stdout.write('x'*1000000)"],5,32)
        self.assertEqual(result['exit_code'],0)
        self.assertTrue(result['stdout_bytes'].startswith(b'False'))
        self.assertEqual(len(result['stdout_bytes']),32); self.assertTrue(result['truncated'][0])

    def test_container_inspection_checks_actual_policy(self):
        cid='a'*64; image='sha256:'+'b'*64
        backend=sandbox.DockerSandbox(cid,'run',image,self.cfg)
        row={'Id':cid,'Image':image,'State':{'Running':True},'Mounts':[],
             'Config':{'Labels':{'vi-bench.run':'run'},'Env':['LANG=C.UTF-8'],'Cmd':['sleep','360']},
             'HostConfig':{'NetworkMode':'none','CapDrop':['ALL'],'ReadonlyRootfs':True,
                           'NanoCpus':1000000000,'Memory':1073741824,'PidsLimit':128,
                           'SecurityOpt':['no-new-privileges'],
                           'Tmpfs':{'/tmp':'rw,nosuid,nodev,size=16m','/app/output':'rw,nosuid,nodev,size=16m'}}}
        def observed(value):
            return {'exit_code':0,'timed_out':False,'stdout_bytes':json.dumps([value]).encode('utf-8')}
        with patch.object(sandbox,'bounded',return_value=observed(row)):
            self.assertEqual(backend.inspect()['container_id'],cid)
        for field,value in [('NetworkMode','host'),('Privileged',True),('Binds',['/var/run/docker.sock:/var/run/docker.sock']),('Memory',0)]:
            changed=copy.deepcopy(row); changed['HostConfig'][field]=value
            with patch.object(sandbox,'bounded',return_value=observed(changed)):
                with self.assertRaisesRegex(ValueError,'SANDBOX_POLICY_MISMATCH'): backend.inspect()
        changed=copy.deepcopy(row); changed['Config']['Env'].append('OPENAI_API_KEY=fixture')
        with patch.object(sandbox,'bounded',return_value=observed(changed)):
            with self.assertRaisesRegex(ValueError,'SANDBOX_POLICY_MISMATCH'): backend.inspect()

    def test_real_client_gate_denial_does_not_read_dotenv_or_open_socket(self):
        gate=agent.RealGate(self.root,self.root/'missing.json',{},self.root/'missing-review.json',{},self.root/'missing-attestation.json',self.backend,self.ledger)
        api=agent.OpenAIResponses(self.root,gate)
        with patch('scoped_credentials._dotenv',side_effect=AssertionError('no key read')),patch.object(agent.subprocess,'Popen') as factory:
            with self.assertRaises(ValueError): api.send({},'request-fixture',1)
            factory.assert_not_called()

    def test_controller_draft_denied_before_docker_or_key(self):
        with patch.object(controller,'bounded',side_effect=AssertionError('no Docker')):
            with self.assertRaisesRegex(ValueError,'SMOKE_NOT_AUTHORIZED'): controller.approved(self.cfg)

    def test_compute_estimate_and_invoice_revision_keep_raw_and_latest(self):
        self.ledger.claim_trial(self.cfg['run_id'],'compute',100)
        self.ledger.record_compute_estimate(self.cfg['run_id'],'compute',50)
        self.assertEqual(self.ledger.inspect()['compute_exposure_nano'],100)
        self.ledger.compute_invoice_revision(self.cfg['run_id'],'compute',1,40,{'kind':'fixture'})
        self.ledger.compute_invoice_revision(self.cfg['run_id'],'compute',2,70,{'kind':'fixture'})
        self.assertEqual(self.ledger.inspect()['compute_exposure_nano'],70)
        self.assertEqual(self.ledger.db.execute('SELECT estimate_c FROM trials').fetchone()[0],50)

    def test_controller_owner_token_cannot_resume_another_claim(self):
        token=self.ledger.claim_trial(self.cfg['run_id'],'own',0)
        self.ledger.check_trial_owner(self.cfg['run_id'],'own',token)
        with self.assertRaisesRegex(ValueError,'TRIAL_OWNER_MISMATCH'):
            self.ledger.check_trial_owner(self.cfg['run_id'],'own','different')

    def test_http_worker_has_hard_timeout_and_private_credential_pipe(self):
        from contextlib import contextmanager
        gate=agent.RealGate(self.root,self.root/'missing',{},self.root/'missing',{},self.root/'missing',self.backend,self.ledger)
        api=agent.OpenAIResponses(self.root,gate)
        @contextmanager
        def lease_scope(**kwargs):
            class Lease:
                def sdk_key(self): return 'fixture-private-key'
                def sanitize(self,obj): return obj
            yield Lease()
        with patch.object(agent,'credential_scope',lease_scope),patch.object(agent.subprocess,'Popen') as factory,patch.object(agent.os,'killpg',create=True) as kill_group:
            process=factory.return_value; process.poll.return_value=None; process.pid=123456789
            process.communicate.side_effect=[agent.subprocess.TimeoutExpired('worker',1),(b'',None)]
            result=api.send({'model':'fixture'},'rid',1)
            self.assertIn('error',result)
            args,kw=factory.call_args
            self.assertNotIn('fixture-private-key',str(args)); self.assertNotIn('OPENAI_API_KEY',kw['env'])
            self.assertIn(b'fixture-private-key',process.communicate.call_args_list[0].kwargs['input'])
            self.assertGreater(process.communicate.call_args_list[0].kwargs['timeout'],0)
            self.assertLessEqual(process.communicate.call_args_list[0].kwargs['timeout'],1)
            if agent.os.name=='posix': kill_group.assert_called_once_with(123456789,agent.signal.SIGKILL)
            else: process.kill.assert_called_once()

    def test_persistent_ledger_prevents_new_folder_from_resetting_claims(self):
        self.loop(FixtureAPI([response([{'type':'message'}])]))
        other=Ledger(self.root/'pool.sqlite3',account='fixture',pool_cap=nano('10'),origin='offline-fixture')
        self.addCleanup(other.close)
        with self.assertRaises(sqlite3.IntegrityError): other.claim_trial(self.cfg['run_id'],self.cfg['task']+'-vi',0)

    def test_controller_lifecycle_reserves_before_create_and_cleans_after_verifier(self):
        events=[]; cfg=copy.deepcopy(self.cfg)
        cfg.update(compute_reservation_usd_per_trial='0.01',compute_nano_usd_per_second=100,compute_quote_reference='fixture-quote')
        state=self.root/'controller'; state.mkdir()
        image='sha256:'+'b'*64; cid='a'*64
        contract={'images':{'images':{'agent':image,'verifier':image}},'snapshot_id':'fixture'}
        def command(args,*a,**kw):
            events.append(args[1])
            if args[1]=='create':
                row=self.ledger.db.execute('SELECT state,reserve_c FROM trials').fetchone()
                self.assertEqual(tuple(row),('active',nano('0.01')))
            return {'exit_code':0,'timed_out':False,'stdout_bytes':cid.encode()}
        backend=unittest.mock.Mock()
        backend.inspect.side_effect=lambda:events.append('inspect')
        def collect(target):
            events.append('collect'); target.mkdir(); (target/'fixture.txt').write_bytes(b'fixture')
        backend.collect.side_effect=collect
        backend.destroy.side_effect=lambda:events.append('destroy')
        def loop(cfg,instruction,language,ledger,api,backend,gate,trace,reserve,*,claim_token):
            events.append('loop'); ledger.check_trial_owner(cfg['run_id'],cfg['task']+'-'+language,claim_token)
            value={'origin':'offline-fixture','trial_id':cfg['task']+'-'+language,'language':language,'stop_reason':'model_final','tool_calls':1,'failure_class':None,'trajectory':str(trace)}
            ledger.finish(cfg['run_id'],value['trial_id'],value); return value
        def verifier(*args): events.append('verify'); return {'status':'verified','reward':0}
        with patch.object(controller,'bounded',side_effect=command),patch.object(controller,'DockerSandbox') as cls,patch.object(controller,'RealGate',return_value=lambda:True),patch.object(controller,'OpenAIResponses'),patch.object(controller,'run_trial',side_effect=loop),patch.object(controller,'verify',side_effect=verifier):
            cls.create_args.return_value=['docker','create',image]; cls.return_value=backend
            result,cleanup=controller.execute_one(Path(__file__).resolve().parents[2],cfg,contract,{},'fixture','fixture','fixture',self.ledger,state,'en')
        self.assertEqual(events,['create','start','inspect','loop','collect','verify','destroy'])
        self.assertEqual(cleanup,'removed_owned_container'); self.assertEqual(result['reward'],0)
        self.assertFalse(result['benchmark_result'])
        self.assertTrue((state/'en/lifecycle.json').exists())


if __name__=='__main__': unittest.main()
