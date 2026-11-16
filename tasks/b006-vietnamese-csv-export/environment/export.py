"""Existing broken exporter. You may fix it, or produce the required artifact another way."""
import json
from pathlib import Path

rows=json.loads(Path('/app/data/orders.json').read_text(encoding='utf-8'))
Path('/app/output').mkdir(exist_ok=True)
Path('/app/output/orders.csv').write_text('\n'.join(','.join(map(str,row.values())) for row in rows),encoding='utf-8')
