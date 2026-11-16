"""Development-only real gate and model/terminal loop; old review gates unchanged."""
from contextlib import closing
import copy
import json
import os
from pathlib import Path
import re
import sqlite3
import time

from development_contracts import (SCOPES, MODEL, SYSTEM, TOOL, backend_config, digest, file_digest, load,
                                   registry, request_reserve, snapshot, sources, validate_config)
from pilot_contracts import validate_attestation
from scoped_credentials import sanitize, sanitized_error
from terminal_agent_v1 import RealGate, OpenAIResponses
from terminal_sandbox_v1 import DockerSandbox
from usd_ledger_v1 import nano


class DevelopmentGate(RealGate):
    def __init__(self,repo,config_path,plan_path,plan,trial,profile,attestation,sandbox,ledger):
        self.repo,self.config_path,self.plan_path=Path(repo),Path(config_path),Path(plan_path)
        self.plan,self.trial,self.profile,self.attestation=plan,trial,profile,attestation
        self.sandbox,self.ledger=sandbox,ledger
        self.active_request=None; self.reason='not_checked'

    def check(self):
        cfg=load(self.config_path); validate_config(cfg)
        if self.plan['scope'] not in SCOPES or not self.plan['development_only']: raise ValueError('DEVELOPMENT_SCOPE_REQUIRED')
        if file_digest(self.repo/'manifest.jsonl')!=self.plan['manifest_sha256']: raise ValueError('MANIFEST_DRIFT')
        if cfg!=self.plan['config'] or load(self.plan_path)!=self.plan: raise ValueError('PLAN_CONFIG_DRIFT')
        if sources(self.repo)!=self.plan['source_sha256'] or snapshot(self.repo)!=self.plan['snapshot']: raise ValueError('SOURCE_SNAPSHOT_DRIFT')
        if digest([SYSTEM,TOOL])!=self.plan['prompt_tools_hash'] or self.trial not in self.plan['planned_trials']: raise ValueError('TRIAL_CONTRACT_DRIFT')
        if validate_attestation(self.profile,self.attestation,self.plan['run_id'],self.plan['snapshot']['id'])[0]!='pass': raise ValueError('ATTESTATION_EXPIRED_OR_INVALID')
        observed_endpoint=os.environ.get('DOCKER_HOST') if not os.environ.get('DOCKER_CONTEXT') else None
        if observed_endpoint and observed_endpoint!=self.attestation['observation']['endpoint']: raise ValueError('DOCKER_ENDPOINT_DRIFT')
        task=registry(self.repo)[self.trial['task_id']]
        if self.sandbox.config!=backend_config(cfg,task): raise ValueError('BACKEND_CONFIG_DRIFT')
        identity=self.ledger.db.execute('SELECT * FROM identity').fetchone()
        if identity['origin']!='real' or identity['cap']!=nano(cfg['pool_cap_usd']) or identity['account']!=cfg['account_reference']:
            raise ValueError('REAL_LEDGER_REQUIRED')
        if self.ledger.path!=(Path(cfg['state_root'])/'ledger.sqlite3').resolve(): raise ValueError('LEDGER_PATH_DRIFT')
        run=self.ledger.db.execute('SELECT contract FROM runs WHERE id=?',(self.plan['run_id'],)).fetchone()
        if not run or run['contract']!=digest(self.plan): raise ValueError('LEDGER_CONTRACT_DRIFT')
        uncertain=self.ledger.db.execute("SELECT id FROM requests WHERE phase IN ('submitted','uncertain')").fetchall()
        if uncertain and (len(uncertain)!=1 or uncertain[0]['id']!=self.active_request): raise ValueError('OTHER_REQUEST_UNCERTAIN')
        if self.ledger.inspect()['available_nano']<0: raise ValueError('BUDGET_DENIED')
        old=load(self.repo/'reports/provider-connectivity-stage9.json')
        external=self.ledger.db.execute('SELECT sha,held FROM external WHERE id=?',(old['run_id'],)).fetchone()
        if not external or tuple(external)!=(digest(old),nano(old['exposure_held_usd'])): raise ValueError('EXTERNAL_HOLD_DRIFT')
        with closing(sqlite3.connect((self.repo/'jobs/stage9-connectivity/ledger.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)) as db:
            previous=db.execute('SELECT state,result FROM runs WHERE id=?',(old['run_id'],)).fetchone()
        if not previous or previous[0]!='observed' or json.loads(previous[1])!=old: raise ValueError('CONNECTIVITY_LEDGER_DRIFT')
        image=self.plan['images'][self.trial['task_id']]['agent']
        if self.sandbox.image_id!=image: raise ValueError('TASK_IMAGE_DRIFT')
        self.sandbox.inspect()

    def __call__(self):
        try:
            self.check(); self.reason='pass'; return True
        except Exception as exc:
            value=exc.args[0] if isinstance(exc,ValueError) and exc.args else 'DEVELOPMENT_GATE_REJECTED'
            self.reason=value if isinstance(value,str) and re.fullmatch('[A-Z_]{1,100}',value) else 'DEVELOPMENT_GATE_REJECTED'
            return False


def request_payload(cfg,history):
    request={'model':MODEL,'instructions':SYSTEM,'input':copy.deepcopy(history),'tools':[copy.deepcopy(TOOL)],
             'parallel_tool_calls':False,'max_output_tokens':cfg['max_output_tokens'],'reasoning':{'effort':'none'},
             'service_tier':'default','store':False,'stream':False}
    if len(json.dumps(request,ensure_ascii=False).encode('utf-8'))>cfg['max_payload_bytes']: raise ValueError('CONTEXT_LIMIT')
    return request


def unique_object(pairs):
    result={}
    for k,v in pairs:
        if k in result: raise ValueError('DUPLICATE_TOOL_ARGUMENT')
        result[k]=v
    return result


def run_loop(cfg,plan,trial,instruction,ledger,api,backend,gate,trace,owner):
    validate_config(cfg)
    if plan['scope'] not in SCOPES or trial not in plan['planned_trials']: raise ValueError('DEVELOPMENT_SCOPE_REQUIRED')
    if api.origin=='real':
        if not isinstance(api,OpenAIResponses) or not isinstance(gate,DevelopmentGate) or not isinstance(backend,DockerSandbox) or api.gate is not gate:
            raise ValueError('REAL_BINDING_MISMATCH')
        if instruction!=(gate.repo/'prompts'/trial['task_id']/(trial['language']+'.md')).read_text(encoding='utf-8'):
            raise ValueError('INSTRUCTION_DRIFT')
    elif api.origin!='offline-fixture' or backend.origin!='offline-fixture' or ledger.inspect()['origin']!='offline-fixture':
        raise ValueError('FIXTURE_ORIGIN_REQUIRED')
    run=plan['run_id']; tid=trial['trial_id']; ledger.check_trial_owner(run,tid,owner)
    if gate() is not True: raise ValueError('GATE_DENIED_'+getattr(gate,'reason','UNKNOWN'))
    history=[{'role':'user','content':instruction}]; started=time.monotonic(); fingerprint=digest(cfg)
    count=0; calls=0; stop='request_limit'; failure='agent'
    with Path(trace).open('x',encoding='utf-8',newline='\n') as stream:
        def event(kind,data):
            stream.write(json.dumps(sanitize({'kind':kind,'trial_id':tid,'elapsed_sec':time.monotonic()-started,'data':data}),ensure_ascii=False)+'\n'); stream.flush()
        event('start',{'origin':api.origin,'scope':plan['scope'],'trial':trial,'config_sha256':fingerprint})
        for slot in range(1,cfg['max_requests_per_trial']+1):
            remaining=cfg['trial_timeout_sec']-(time.monotonic()-started)
            if remaining<=0: stop='trial_timeout'; break
            if digest(cfg)!=fingerprint or gate() is not True: stop='gate_changed'; failure='infrastructure'; break
            try: payload=request_payload(cfg,history)
            except ValueError: stop='context_limit'; break
            try: rid=ledger.claim_request(run,tid,slot,digest(payload),request_reserve(cfg),cfg['max_requests_per_trial'])
            except ValueError:
                stop='accounting_stop'; failure='accounting'; break
            count+=1
            if isinstance(gate,DevelopmentGate): gate.active_request=rid
            event('request_intent',{'request_id':rid,'slot':slot,'payload_sha256':digest(payload),'reservation_nano':request_reserve(cfg)})
            try: receipt=api.send(payload,rid,max(.001,cfg['trial_timeout_sec']-(time.monotonic()-started)))
            except Exception as exc: receipt={'error':sanitized_error(exc)}
            amount=ledger.record_provider(rid,receipt,cfg)
            if isinstance(gate,DevelopmentGate): gate.active_request=None
            event('response',{'request_id':rid,'receipt':receipt,'conservative_cost_nano':amount})
            if amount is None: stop='provider_uncertain'; failure='provider'; break
            body=receipt['response']
            if body['status']!='completed': stop='model_incomplete'; break
            output=body.get('output')
            if not isinstance(output,list) or not all(isinstance(item,dict) for item in output): stop='invalid_model_output'; break
            tools=[item for item in output if item.get('type')=='function_call']
            if not tools:
                stop='model_final' if any(item.get('type')=='message' for item in output) else 'invalid_model_output'
                failure=None if stop=='model_final' else 'agent'; break
            history.extend(copy.deepcopy(output)); valid=True
            for item in tools:
                phase='schema'
                try:
                    if item.get('name')!='terminal' or not re.fullmatch('[A-Za-z0-9_-]{1,200}',item.get('call_id','')): raise ValueError('TOOL_SCHEMA')
                    args=json.loads(item['arguments'],object_pairs_hook=unique_object)
                    if not isinstance(args,dict) or set(args)!={'command'} or not isinstance(args['command'],str) or not args['command'] or '\0' in args['command'] or len(args['command'].encode('utf-8'))>cfg['max_command_bytes']: raise ValueError('TOOL_SCHEMA')
                    phase='gate'
                    if gate() is not True or digest(cfg)!=fingerprint: raise ValueError('TOOL_GATE')
                    remaining=cfg['trial_timeout_sec']-(time.monotonic()-started)
                    if remaining<=0: stop='trial_timeout'; failure='agent'; valid=False; break
                    ledger.tool_intent(run,tid,item['call_id'],digest(args['command']))
                    event('tool_intent',item); phase='execute'
                    result=sanitize(backend.command(args['command'],min(cfg['command_timeout_sec'],remaining)))
                    ledger.tool_result(run,tid,item['call_id'],result); calls+=1
                    history.append({'type':'function_call_output','call_id':item['call_id'],'output':json.dumps(result,ensure_ascii=False)})
                    event('tool_result',{'call_id':item['call_id'],'result':result})
                except Exception as exc:
                    stop='invalid_tool_call' if phase=='schema' else 'tool_infrastructure_failure'
                    failure='agent' if phase=='schema' else 'infrastructure'; valid=False
                    event('tool_failure',sanitized_error(exc)); break
            if not valid: break
        result={'origin':api.origin,'scope':plan['scope'],'development_only':True,'review_status':trial['review_status'],
                'trial_id':tid,'stop_reason':stop,'failure_class':failure,'tool_calls':calls,'model_requests':count,
                'elapsed_sec':time.monotonic()-started,'trajectory':str(trace),'reward':None}
        event('stop',result)
    ledger.finish(run,tid,result)
    return result
