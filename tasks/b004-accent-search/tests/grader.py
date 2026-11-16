from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).parent))
from checklib import Rejected, blob, json_value, same_typed, unchanged, entry


def grade(root):
    trusted=Path(__file__).parent
    unchanged(root,trusted)
    expected=json.loads((trusted/'expected.json').read_text(encoding='utf-8'))
    if not same_typed(json_value(blob(root,'output/results.json')),expected):
        raise Rejected('Search results/schema/order/display-name mismatch')


if __name__ == '__main__':
    raise SystemExit(entry(grade))
