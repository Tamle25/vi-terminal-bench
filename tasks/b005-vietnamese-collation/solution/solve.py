import argparse
import subprocess
from pathlib import Path


SCRIPT = r'''
const fs = require('fs');
const root=process.argv[1];
const rows=JSON.parse(fs.readFileSync(root+'/data/catalog.json','utf8'));
const col=new Intl.Collator('vi',{usage:'sort',sensitivity:'variant',caseFirst:'lower',numeric:false,ignorePunctuation:false});
rows.sort((a,b)=>col.compare(a.name.normalize('NFC'),b.name.normalize('NFC')) || (a.id<b.id?-1:a.id>b.id?1:0));
fs.mkdirSync(root+'/output',{recursive:true});
fs.writeFileSync(root+'/output/catalog.json',JSON.stringify(rows));
'''


def solve(root):
    subprocess.run(['node','-e',SCRIPT,str(root)],check=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('/app'));solve(p.parse_args().root)
