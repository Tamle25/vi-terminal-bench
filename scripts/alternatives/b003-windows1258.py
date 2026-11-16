import codecs
import io
import json
import unicodedata


def solve(root):
    output=root/'output'; (output/'text').mkdir(parents=True,exist_ok=True)
    entries=json.loads((root/'data/sources.json').read_text(encoding='utf-8'))
    report=[]
    for item in entries:
        name=item['file']; target=name.removesuffix('.bin')+'.txt'
        try:
            with io.TextIOWrapper(io.BytesIO((root/'data'/name).read_bytes()),encoding='cp1258',newline=None,errors='strict') as stream:
                value=stream.read()
        except UnicodeDecodeError:
            report.append({'output':None,'status':'invalid_encoding','file':name})
        else:
            (output/'text'/target).write_bytes(unicodedata.normalize('NFC',value).encode('utf-8'))
            report.append({'output':target,'status':'converted','file':name})
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=True,indent=2),encoding='utf-8')
