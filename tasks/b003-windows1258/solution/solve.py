import argparse
import json
import unicodedata
from pathlib import Path


def solve(root):
    sources = json.loads((root/'data/sources.json').read_text(encoding='utf-8'))
    output = root/'output'
    (output/'text').mkdir(parents=True, exist_ok=True)
    report = []
    for item in sources:
        name = item['file']
        try:
            content = (root/'data'/name).read_bytes().decode(item['encoding'], errors='strict')
        except UnicodeDecodeError:
            report.append(dict(file=name,status='invalid_encoding',output=None))
            continue
        content = unicodedata.normalize('NFC',content.replace('\r\n','\n').replace('\r','\n'))
        target = Path(name).stem+'.txt'
        (output/'text'/target).write_bytes(content.encode('utf-8'))
        report.append(dict(file=name,status='converted',output=target))
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,default=Path('/app'))
    solve(p.parse_args().root)
