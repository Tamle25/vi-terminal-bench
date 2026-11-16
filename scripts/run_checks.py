"""Run meaningful tooling tests and retain machine-readable outcomes."""
import argparse
import io
import json
import platform
import unittest
from pathlib import Path


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    folder=Path(__file__).resolve().parent/'tests'
    suite=unittest.defaultTestLoader.discover(str(folder))
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report={'platform':platform.platform(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'all_passed':result.wasSuccessful(),'log':stream.getvalue()}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"{report['tests_run']} tests; failures={report['failures']}; errors={report['errors']}; skipped={report['skipped']}")
    raise SystemExit(0 if result.wasSuccessful() else 1)
