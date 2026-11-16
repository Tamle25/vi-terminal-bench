import copy
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aggregate_results import aggregate
from dev_registry import hooks
from import_harbor_results import normalize, normalized_reward, import_results
from preflight import filesystem_probe
from statistics_family import interval
from materialize_variants import payload_hash
from test_aggregate_results import manifest, row


def planned(trial):
    return {**trial,'payload_sha256':'payload','instruction_sha256':'instruction','configuration_sha256':'configuration','harbor_task_checksum':'checksum','task_package':'vi-terminal/'+trial['task_id'],'attempts':[{'attempt':1,'job_name':'job','task_package':'vi-terminal/'+trial['task_id']}]}


def raw(trial,exception=None):
    return {'task_name':trial['task_package'],'task_checksum':'checksum','trial_name':'raw-name','started_at':'2026-11-12T00:00:00Z','finished_at':'2026-11-12T00:00:01Z','verifier_result':{'rewards':{'reward':1.0}},'exception_info':exception,'agent_result':{'cost_usd':None},'config':{'agent':{'name':'oracle','model_name':None}}}


class AdapterAndCoverageTests(unittest.TestCase):
    def test_payload_hash_has_portable_path_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'Z.txt').write_bytes(b'upper')
            (root/'a.txt').write_bytes(b'lower')
            (root/'instruction.md').write_bytes(b'ignored')
            expected=hashlib.sha256()
            for name,content in [('Z.txt',b'upper'),('a.txt',b'lower')]:
                expected.update(name.encode()+b'\0');expected.update(hashlib.sha256(content).digest())
            self.assertEqual(payload_hash(root),expected.hexdigest())

    def test_float_reward_validation(self):
        self.assertEqual(normalized_reward(1.0),1)
        for value in [True,None,.5,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):normalized_reward(value)

    def test_unknown_error_is_not_model_failure(self):
        trial=planned(row())
        data=raw(trial,{'exception_type':'NewProviderError'})
        with self.assertRaises(ValueError):normalize(data,trial,trial['attempts'][0],'raw')
        result=normalize(data,trial,trial['attempts'][0],'raw',{'NewProviderError':'infra_error'})
        self.assertEqual(result['status'],'infra_error');self.assertIsNone(result['reward'])

    def test_known_timeout_and_verifier_error(self):
        trial=planned(row())
        for error,status,reward in [('AgentTimeoutError','agent_timeout',0),('VerifierTimeoutError','verifier_error',None)]:
            result=normalize(raw(trial,{'exception_type':error}),trial,trial['attempts'][0],'raw')
            self.assertEqual((result['status'],result['reward']),(status,reward))

    def test_checksum_drift_rejected(self):
        trial=planned(row());data=raw(trial);data['task_checksum']='other'
        with self.assertRaises(ValueError):normalize(data,trial,trial['attempts'][0],'raw')

    def test_whole_configuration_missing(self):
        first=planned(row());second=planned(row(configuration='absent',trial_id='absent'))
        result=aggregate([first],[manifest()],run_plan={'planned_trials':[first,second]})
        missing=next(group for group in result['groups'] if group['configuration']=='absent')
        self.assertEqual(missing['observed_trials'],0);self.assertTrue(missing['provisional'])

    def test_empty_observations_with_plan(self):
        result=aggregate([],[manifest()],run_plan={'planned_trials':[planned(row())]})
        self.assertEqual(result['groups'][0]['valid_trials'],0)
        self.assertIsNone(result['groups'][0]['score'])

    def test_mixed_snapshot_is_rejected(self):
        first=row(repeat=1,payload_sha256='one');second=row(repeat=2,payload_sha256='two')
        with self.assertRaises(ValueError):aggregate([first,second],[manifest()])

    def test_planned_provenance_must_match(self):
        expected=planned(row());observed=copy.deepcopy(expected);observed['configuration_sha256']='changed'
        with self.assertRaises(ValueError):aggregate([observed],[manifest()],run_plan={'planned_trials':[expected]})

    def test_bound_raw_import_and_configuration_drift(self):
        trial=planned(row())
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'result.json';source.write_text(json.dumps(raw(trial)))
            plan={'schema':'vi-terminal-run/0.1','harbor_version':'0.25.0','jobs_root':tmp,'configuration_spec':{'agent':'oracle','model':None},'planned_trials':[trial]}
            bindings={trial['trial_id']+':1':str(source)}
            rows,missing=import_results(plan,bindings=bindings)
            self.assertEqual((len(rows),missing),(1,[]))
            data=raw(trial);data['config']['agent']['kwargs']={'something':'different'};source.write_text(json.dumps(data))
            with self.assertRaises(ValueError):import_results(plan,bindings=bindings)

    def test_unregistered_task_has_no_fallback(self):
        with self.assertRaises(ValueError):hooks('b999-unknown')


class FamilyStatisticsTests(unittest.TestCase):
    def test_seed_reproducible_and_bounds(self):
        values=[{'family_id':'a','skill':'s','score':0},{'family_id':'b','skill':'s','score':1}]
        first=interval(values,'A',100,seed=11);second=interval(values,'A',100,seed=11)
        self.assertEqual(first,second);self.assertEqual(first['ci95'],[0,1])

    def test_native_single_family_per_skill_not_estimable(self):
        values=[{'family_id':'a','skill':'encoding','score':0},{'family_id':'b','skill':'search','score':1}]
        self.assertIsNone(interval(values,'B',100)['ci95'])

    def test_cross_skill_family_not_resampled_independently(self):
        values=[{'family_id':'a','skill':'encoding','score':0},{'family_id':'a','skill':'search','score':1}]
        self.assertEqual(interval(values,'B',100)['reason'],'family-crosses-skill-strata-unsupported')

    def test_paired_resampling_preserves_zero_delta(self):
        roster=[manifest('t1',track='A'),manifest('t2',track='A')]
        rows=[row(task=task,track='A',language=language,reward=reward) for task,reward in [('t1',1),('t2',0)] for language in ['en','vi']]
        result=aggregate(rows,roster,expected_repeats=1,bootstrap_draws=100)
        delta=result['language_deltas'][0]
        self.assertEqual(delta['uncertainty_pp']['ci95'],[0,0])

    def test_full_fail_and_full_pass(self):
        for score in [0,1]:
            tasks=[{'family_id':'a','skill':'s','score':score},{'family_id':'b','skill':'s','score':score}]
            self.assertEqual(interval(tasks,'B',100)['ci95'],[score,score])


@unittest.skipUnless(platform.system()=='Linux','Needs native Linux semantics and bash')
class LinuxPreflightTests(unittest.TestCase):
    def test_native_unicode_and_case_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(filesystem_probe(Path(tmp)),str(Path(tmp).resolve()))
        with self.assertRaises(ValueError):filesystem_probe(Path('/mnt/d/never-create'))

    def test_wrapper_default_native_and_windows_paths(self):
        wrapper=Path(__file__).resolve().parents[1]/'harbor-wsl.sh'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);binary=root/'vi-terminal-bench-runtime/venv/bin/harbor';binary.parent.mkdir(parents=True)
            binary.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n');binary.chmod(0o755)
            env={**os.environ,'TMPDIR':temporary}
            def run(*arguments):return subprocess.run(['bash',str(wrapper),'run',*arguments],capture_output=True,text=True,env=env)
            default=run('--print-config');self.assertEqual(default.returncode,0);self.assertIn(str(root/'vi-terminal-bench-runtime/jobs'),default.stdout)
            native=root/'jobs có dấu'
            explicit=run('--jobs-dir',str(native));self.assertEqual(explicit.returncode,0);self.assertIn(str(native),explicit.stdout)
            rejected=run('--jobs-dir','/mnt/d/jobs');self.assertNotEqual(rejected.returncode,0)


if __name__=='__main__':unittest.main()
