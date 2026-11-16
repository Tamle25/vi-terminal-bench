import csv
import io
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from checklib import Rejected, blob, same_typed, unchanged, entry


def grade(root):
    trusted=Path(__file__).parent
    unchanged(root,trusted)
    expected=json.loads((trusted/'expected.json').read_text(encoding='utf-8'))
    raw=blob(root,'output/orders.csv')
    if not raw.startswith(b'\xef\xbb\xbf') or raw[3:].startswith(b'\xef\xbb\xbf'):
        raise Rejected('Exactly one UTF-8 BOM required')
    try:
        text=raw[3:].decode('utf-8',errors='strict')
        remainder=text.replace('\r\n','')
        if '\r' in remainder or '\n' in remainder or not text.endswith('\r\n'):
            raise Rejected('All line breaks must be CRLF, including final record')
        rows=list(csv.reader(io.StringIO(text,newline=''),delimiter=';',strict=True))
    except (UnicodeError,csv.Error) as exc:
        raise Rejected('Invalid UTF-8/CSV') from exc
    if not same_typed(rows,expected):
        raise Rejected('CSV cells/header/order mismatch')


if __name__ == '__main__':
    raise SystemExit(entry(grade))
