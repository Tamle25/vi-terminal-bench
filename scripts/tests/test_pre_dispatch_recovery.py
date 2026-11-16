import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from development_reconcile import assert_pre_dispatch
from terminal_agent_v1 import RealGate,OpenAIResponses


class RecoveryTests(unittest.TestCase):
    def values(self):
        request={'receipt':json.dumps({'error':{'error':'DISPATCH_BLOCKED','exception_type':'CredentialError'}}),
                 'phase':'uncertain','slot':1,'estimate_i':None}
        outcome={'valid':False,'status':'infra_error','raw_loop':{'tool_calls':0,'model_requests':1,'stop_reason':'provider_uncertain'}}
        return request,outcome

    def test_only_proven_no_network_no_tool_is_eligible(self):
        request,outcome=self.values()
        self.assertEqual(assert_pre_dispatch([request],[],outcome)['error']['error'],'DISPATCH_BLOCKED')
        changed=copy.deepcopy(outcome); changed['raw_loop']['tool_calls']=1
        with self.assertRaises(ValueError): assert_pre_dispatch([request],[],changed)
        with self.assertRaises(ValueError): assert_pre_dispatch([request],[{'phase':'submitted'}],outcome)

    def test_timeout_http_error_or_unknown_is_never_released(self):
        request,outcome=self.values()
        for value in [{'error':{'error':'EXECUTION_ERROR','exception_type':'Exception'}},{'http_status':429},{'http_status':200,'response':{'usage':None}}]:
            changed=dict(request,receipt=json.dumps(value))
            with self.assertRaises(ValueError): assert_pre_dispatch([changed],[],outcome)

    def test_frozen_client_gate_denial_precedes_worker_and_dotenv(self):
        class Denied(RealGate):
            def __init__(self): pass
            def __call__(self): return False
        api=OpenAIResponses(Path(__file__).resolve().parents[2],Denied())
        with patch('terminal_agent_v1.subprocess.Popen') as worker,patch('scoped_credentials._dotenv',side_effect=AssertionError('no key read')):
            with self.assertRaises(ValueError) as caught: api.send({},'fixture',1)
            self.assertEqual(caught.exception.code,'DISPATCH_BLOCKED'); worker.assert_not_called()


if __name__=='__main__': unittest.main()
