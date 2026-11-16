"""Explicit mutants for B003–B006. No default task fallback."""
import json
import unicodedata


def mutate_json(path, function):
    rows=json.loads(path.read_text(encoding='utf-8'))
    function(rows)
    path.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')


def controls(task_id,root):
    files={
        'b003-windows1258':'output/report.json',
        'b004-accent-search':'output/results.json',
        'b005-vietnamese-collation':'output/catalog.json',
        'b006-vietnamese-csv-export':'output/orders.csv',
    }
    if task_id not in files:
        raise ValueError('Missing native controls: '+task_id)
    artifact=root/files[task_id]
    source=next(iter(sorted((root/'data').glob('*'))),root/'data/not-created')
    result={
        'missing-output':lambda:artifact.unlink(),
        'empty-output':lambda:artifact.write_bytes(b''),
        'changed-source':lambda:source.write_bytes(b'changed'),
        'symlink-output':lambda:(artifact.unlink(),artifact.symlink_to(source)),
        'oversized-output':lambda:artifact.write_bytes(b' '*(1024*1024+1)),
        'invalid-utf8':lambda:artifact.write_bytes(b'\xff'),
    }
    if task_id=='b003-windows1258':
        text=root/'output/text/01.txt'
        result.update({
            'latin1':lambda:text.write_bytes((root/'data/01.bin').read_bytes().decode('latin1').encode('utf-8')),
            'drop-marks':lambda:text.write_text(''.join(c for c in unicodedata.normalize('NFD',text.read_text(encoding='utf-8')) if not unicodedata.combining(c)),encoding='utf-8'),
            'nfd-output':lambda:text.write_bytes(unicodedata.normalize('NFD',text.read_text(encoding='utf-8')).encode('utf-8')),
            'text-bom':lambda:text.write_bytes(b'\xef\xbb\xbf'+text.read_bytes()),
            'crlf-not-normalized':lambda:text.write_bytes(text.read_bytes().replace(b'\n',b'\r\n')),
            'missing-converted':lambda:text.unlink(),
            'extra-error-output':lambda:(root/'output/text/04.txt').write_bytes(b'replacement'),
            'wrong-error-status':lambda:mutate_json(artifact,lambda rows:rows[-1].update(status='converted',output='04.txt')),
            'missing-empty-file':lambda:(root/'output/text/03.txt').unlink(),
        })
    elif task_id=='b004-accent-search':
        result.update({
            'no-d-mapping':lambda:mutate_json(artifact,lambda rows:rows[0].update(matches=[])),
            'case-sensitive':lambda:mutate_json(artifact,lambda rows:rows[1].update(matches=[])),
            'nfd-missed':lambda:mutate_json(artifact,lambda rows:rows[1]['matches'].clear()),
            'punctuation-collapsed':lambda:mutate_json(artifact,lambda rows:rows[2]['matches'].append({'id':'C03','name':'Hoàng-An'})),
            'whitespace-collapsed':lambda:mutate_json(artifact,lambda rows:rows[7]['matches'].append({'id':'C06','name':'DANG An'})),
            'empty-query-all':lambda:mutate_json(artifact,lambda rows:rows[6].update(matches=rows[0]['matches'],error=None)),
            'display-name-changed':lambda:mutate_json(artifact,lambda rows:rows[0]['matches'][0].update(name='Dang Thi Hong')),
            'missing-query':lambda:mutate_json(artifact,lambda rows:rows.pop()),
            'wrong-order':lambda:mutate_json(artifact,lambda rows:rows.reverse()),
            'extra-match':lambda:mutate_json(artifact,lambda rows:rows[5]['matches'].append({'id':'C01','name':'Đặng Thị Hồng'})),
        })
    elif task_id=='b005-vietnamese-collation':
        def sort_codepoint(rows): rows.sort(key=lambda r:(r['name'],r['id']))
        def strip_sort(rows): rows.sort(key=lambda r:(''.join(c for c in unicodedata.normalize('NFD',r['name']) if not unicodedata.combining(c)).replace('Đ','D').casefold(),r['id']))
        def swap_named(rows,left,right):
            first=next(i for i,r in enumerate(rows) if r['id']==left)
            second=next(i for i,r in enumerate(rows) if r['id']==right)
            rows[first],rows[second]=rows[second],rows[first]
        result.update({
            'codepoint-sort':lambda:mutate_json(artifact,sort_codepoint),
            'accent-stripped-sort':lambda:mutate_json(artifact,strip_sort),
            'numeric-sort':lambda:mutate_json(artifact,lambda rows:swap_named(rows,'N03','N13')),
            'wrong-tie-break':lambda:mutate_json(artifact,lambda rows:swap_named(rows,'N07','N16')),
            'uppercase-first':lambda:mutate_json(artifact,lambda rows:swap_named(rows,'N06','N17')),
            'display-normalized':lambda:mutate_json(artifact,lambda rows:next(r for r in rows if r['id']=='N16').update(name='Án')),
            'lost-row':lambda:mutate_json(artifact,lambda rows:rows.pop()),
        })
    else:
        result.update({
            'missing-bom':lambda:artifact.write_bytes(artifact.read_bytes()[3:]),
            'double-bom':lambda:artifact.write_bytes(b'\xef\xbb\xbf'+artifact.read_bytes()),
            'wrong-delimiter':lambda:artifact.write_bytes(artifact.read_bytes().replace(b';',b',')),
            'lf-newlines':lambda:artifact.write_bytes(artifact.read_bytes().replace(b'\r\n',b'\n')),
            'no-final-newline':lambda:artifact.write_bytes(artifact.read_bytes()[:-2]),
            'wrong-money':lambda:artifact.write_bytes(artifact.read_bytes().replace(b'1.234.567',b'1234567')),
            'lost-leading-zero':lambda:artifact.write_bytes(artifact.read_bytes().replace(b'0001',b'1')),
            'quote-corrupted':lambda:artifact.write_bytes(artifact.read_bytes().replace(b'""',b'"')),
            'header-wrong-order':lambda:artifact.write_bytes(artifact.read_bytes().replace(b'ma_don;khach_hang',b'khach_hang;ma_don')),
            'unescaped-multiline':lambda:artifact.write_bytes(artifact.read_bytes().replace('"Dòng 1\r\nDòng 2"'.encode('utf-8'),'Dòng 1\r\nDòng 2'.encode('utf-8'))),
        })
    return result
