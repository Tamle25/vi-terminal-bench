"""Restore our M1 archive to fresh Linux storage and verify recorded outcomes."""
import argparse
import hashlib
import json
import platform
import tarfile
import tempfile
from pathlib import Path
from report_harbor_validation import summarize


def verify(archive,repo):
    if platform.system()!='Linux':
        raise ValueError('Restore Unicode/case-sensitive artifacts on Linux')
    results=[]
    with tempfile.TemporaryDirectory(prefix='vi-m1-restore-') as temporary:
        root=Path(temporary)
        with tarfile.open(archive,'r:gz') as handle:
            handle.extractall(root,filter='data')
        for name,agent,count in [('m1-oracle-linux','oracle',6),('m1-nop-linux','nop',2)]:
            result=summarize(root/name,agent,count)
            recorded=json.loads((repo/'reports'/('harbor-'+agent+'-linux.json')).read_text(encoding='utf-8'))
            signature=lambda data:sorted((row['trial_name'],row['task_checksum'],row['reward'],json.dumps(row['checks'],sort_keys=True)) for row in data['trials'])
            if not result['all_matched'] or signature(result)!=signature(recorded):
                raise ValueError('Archive/report mismatch: '+name)
            results.append({'job':name,'trials':count,'matched':True})
    return {'kind':'m1-archive-restore-audit','archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'all_matched':True,'jobs':results}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();repo=Path(__file__).resolve().parents[1]
    result=verify(args.archive,repo)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('M1 archive restored on Linux; all 8 recorded trials match')
