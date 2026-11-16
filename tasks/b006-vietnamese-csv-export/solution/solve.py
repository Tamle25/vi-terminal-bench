import argparse
import csv
import datetime
import io
import json
from pathlib import Path


def solve(root):
    rows=json.loads((root/'data/orders.json').read_text(encoding='utf-8'))
    stream=io.StringIO(newline='')
    writer=csv.writer(stream,delimiter=';',lineterminator='\r\n')
    writer.writerow(['ma_don','khach_hang','ngay','so_tien_vnd','ghi_chu'])
    for row in sorted(rows,key=lambda r:r['id']):
        note=row['note'].replace('\r\n','\n').replace('\r','\n').replace('\n','\r\n')
        writer.writerow([row['id'],row['customer'],datetime.date.fromisoformat(row['date']).strftime('%d/%m/%Y'),f"{row['amount_vnd']:,}".replace(',','.'),note])
    (root/'output').mkdir(parents=True,exist_ok=True)
    (root/'output/orders.csv').write_bytes(stream.getvalue().encode('utf-8-sig'))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('/app'));solve(p.parse_args().root)
