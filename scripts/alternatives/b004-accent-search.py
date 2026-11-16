import json
import re
import unicodedata


def solve(root):
    customers=json.loads((root/'data/customers.json').read_text(encoding='utf-8'))
    queries=json.loads((root/'data/queries.json').read_text(encoding='utf-8'))
    def fold(text):
        letters=[]
        for char in text:
            expanded=unicodedata.normalize('NFD',char)
            letters.extend(c for c in expanded if unicodedata.combining(c)==0)
        return ''.join(letters).translate(str.maketrans({'đ':'d','Đ':'D'})).casefold()
    result=[]
    for query in queries:
        key=fold(query['text'])
        matches=[] if not key else [dict(id=c['id'],name=c['name']) for c in customers if re.search(re.escape(key),fold(c['name']))]
        result.append({'error':None if key else 'empty_query','matches':sorted(matches,key=lambda r:r['id']),'query_id':query['id']})
    (root/'output').mkdir(parents=True,exist_ok=True)
    (root/'output/results.json').write_text(json.dumps(result,ensure_ascii=True),encoding='utf-8')
