from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).parent))
from checklib import Rejected, blob, safe_path, json_value, same_typed, unchanged, entry


def grade(root):
    trusted=Path(__file__).parent
    expected=json.loads((trusted/'expected.json').read_text(encoding='utf-8'))
    unchanged(root,trusted)
    report=json_value(blob(root,'output/report.json'))
    if not same_typed(report,expected['report']):
        raise Rejected('Conversion report mismatch')
    folder=safe_path(root,'output/text')
    if not folder.is_dir() or {p.name for p in folder.iterdir()} != set(expected['texts']):
        raise Rejected('Converted file set mismatch')
    for name,content in expected['texts'].items():
        if blob(root,'output/text/'+name) != content.encode('utf-8'):
            raise Rejected('Wrong encoding, Unicode, newline or text content')


if __name__ == '__main__':
    raise SystemExit(entry(grade))
