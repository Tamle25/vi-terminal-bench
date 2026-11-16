import argparse
import json
import unicodedata
from pathlib import Path


def key(value):
    value=''.join(c for c in unicodedata.normalize('NFD',value) if not unicodedata.combining(c))
    return value.replace('đ','d').replace('Đ','D').casefold()


def solve(root):
    customers=json.loads((root/'data/customers.json').read_text(encoding='utf-8'))
    queries=json.loads((root/'data/queries.json').read_text(encoding='utf-8'))
    result=[]
    for query in queries:
        query_key=key(query['text'])
        matches=sorted([item for item in customers if query_key and query_key in key(item['name'])],key=lambda item:item['id'])
        result.append(dict(query_id=query['id'],matches=matches,error='empty_query' if not query_key else None))
    (root/'output').mkdir(parents=True,exist_ok=True)
    (root/'output/results.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('/app'));solve(p.parse_args().root)
