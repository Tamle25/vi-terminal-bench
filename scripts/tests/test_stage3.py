import copy
import json
import os
import platform
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime_process import run_bounded
from preflight import inspect
from model_dry_run import dry_run,check_effective

REPO=Path(__file__).resolve().parents[2]


class ProcessTests(unittest.TestCase):
    def test_timeout_is_bounded(self):
        result=run_bounded([sys.executable,'-c','import time;time.sleep(60)'],timeout=.1)
        self.assertTrue(result['timed_out']);self.assertLess(result['elapsed_sec'],3)

    def test_nonzero_and_output(self):
        result=run_bounded([sys.executable,'-c','import sys;print("data");sys.exit(7)'])
        self.assertEqual(result['returncode'],7);self.assertIn('data',result['stdout'])

    def test_missing_executable(self):
        self.assertEqual(run_bounded(['no-such-benchmark-program'])['error_type'],'FileNotFoundError')

    @unittest.skipUnless(os.name=='posix','Owned Unix process groups')
    def test_inherited_capture_child_does_not_hold_parent(self):
        code='import subprocess,sys;subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]);print("parent finished")'
        result=run_bounded([sys.executable,'-c',code],timeout=2)
        self.assertFalse(result['timed_out']);self.assertIn('parent finished',result['stdout']);self.assertLess(result['elapsed_sec'],3)


@unittest.skipUnless(platform.system()=='Linux','Native filesystem semantics')
class PreflightTests(unittest.TestCase):
    def fake(self,args,**kwargs):
        return {'returncode':0,'timed_out':False,'stdout':'ext4\n' if args[0]=='stat' else '{"Os":"linux","Version":"test"}','stderr':''}
    def test_health_passes_without_model(self):
        with tempfile.TemporaryDirectory() as tmp:self.assertTrue(inspect(Path(tmp),REPO,runner=self.fake)['ready'])
    def test_cli_timeout_is_not_reward(self):
        def bad(args,**kw):
            if args[0]=='stat':return self.fake(args,**kw)
            return {'returncode':-15,'timed_out':True,'stdout':'','stderr':''}
        with tempfile.TemporaryDirectory() as tmp:
            result=inspect(Path(tmp),REPO,runner=bad)
            self.assertFalse(result['ready']);self.assertEqual(result['steps'][-1]['name'],'docker-cli-engine');self.assertNotIn('reward',result)
    def test_invalid_cli_output(self):
        def bad(args,**kw):return {**self.fake(args,**kw),'stdout':'not json'}
        with tempfile.TemporaryDirectory() as tmp:self.assertFalse(inspect(Path(tmp),REPO,runner=bad)['ready'])
    def test_wrong_engine(self):
        def bad(args,**kw):return {**self.fake(args,**kw),'stdout':'ext4' if args[0]=='stat' else '{"Os":"windows","Version":"test"}'}
        with tempfile.TemporaryDirectory() as tmp:self.assertFalse(inspect(Path(tmp),REPO,runner=bad)['ready'])
    def test_deadline_exhausted(self):
        with tempfile.TemporaryDirectory() as tmp:self.assertFalse(inspect(Path(tmp),REPO,deadline_sec=0,runner=self.fake)['ready'])


class DryRunTests(unittest.TestCase):
    def profile(self):return json.loads((REPO/'configs/model-pilot.template.json').read_text())
    def test_missing_inputs_preview_72_without_calls(self):
        with patch('subprocess.Popen',side_effect=AssertionError('No processes in dry run')):
            result=dry_run(self.profile(),REPO)
        self.assertEqual(result['trial_count'],72);self.assertEqual(len({t['trial_id'] for t in result['planned_trials']}),72)
        self.assertFalse(result['ready_for_model_calls']);self.assertFalse(result['profile_complete']);self.assertEqual(result['model_calls'],0)
    def test_secret_values_are_rejected_without_echo(self):
        value=self.profile();value['configurations'][0]['api_key']='do-not-print-this'
        with self.assertRaises(ValueError) as error:dry_run(value,REPO)
        self.assertNotIn('do-not-print-this',str(error.exception))
    def test_effective_profile_field_drift(self):
        expected=self.profile()['configurations'][0]
        for field in ['model','endpoint','timeout_sec','reasoning_effort','agent_version']:
            observed=copy.deepcopy(expected);observed[field]='different'
            with self.assertRaises(ValueError):check_effective(expected,observed)
    def test_invalid_budget_and_endpoint(self):
        for field in ['budget','endpoint']:
            value=self.profile()
            if field=='budget':value['budget']['max_inference_usd']=True
            else:value['configurations'][0]['endpoint']='https://user:secret@example.com'
            with self.assertRaises(ValueError):dry_run(value,REPO)

    def test_system_prompt_content_changes_fingerprint(self):
        with tempfile.TemporaryDirectory(dir=REPO/'build') as tmp:
            path=Path(tmp)/'prompt.md';path.write_text('first',encoding='utf-8')
            value=self.profile();value['configurations'][0]['system_prompt_path']=str(path.relative_to(REPO))
            first=dry_run(value,REPO)['planned_trials'][0]['configuration_sha256']
            path.write_text('second',encoding='utf-8')
            second=dry_run(value,REPO)['planned_trials'][0]['configuration_sha256']
            self.assertNotEqual(first,second)


if __name__=='__main__':unittest.main()
