import json


def solve(root):
    data=json.loads((root/'data/orders.json').read_text(encoding='utf-8'))
    cells=[['ma_don','khach_hang','ngay','so_tien_vnd','ghi_chu']]
    for row in sorted(data,key=lambda r:r['id']):
        year,month,day=row['date'].split('-')
        digits=str(row['amount_vnd']); groups=[]
        while digits:
            groups.insert(0,digits[-3:]);digits=digits[:-3]
        note=row['note'].replace('\r\n','\n').replace('\r','\n').replace('\n','\r\n')
        cells.append([row['id'],row['customer'],day+'/'+month+'/'+year,'.'.join(groups),note])
    text=''.join(';'.join('"'+cell.replace('"','""')+'"' for cell in record)+'\r\n' for record in cells)
    (root/'output').mkdir(parents=True,exist_ok=True)
    (root/'output/orders.csv').write_bytes(b'\xef\xbb\xbf'+text.encode('utf-8'))
