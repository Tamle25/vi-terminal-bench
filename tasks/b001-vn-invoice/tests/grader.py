"""Trusted data-only grader. Never import or execute agent-produced code."""
import argparse
import hashlib
import json
import stat
import unicodedata
from pathlib import Path

MAX_BYTES = 1024 * 1024


class Rejected(ValueError):
    pass


def read_regular(root: Path, relative: str) -> bytes:
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise Rejected(f"Symlink: {relative}")
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise Rejected(f"Not a bounded regular file: {relative}")
        return path.read_bytes()
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        raise Rejected(f"Missing/unreadable artifact: {relative}") from exc


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_jsonl(root: Path, relative: str):
    raw = read_regular(root, relative)
    if raw.startswith(b"\xef\xbb\xbf"):
        raise Rejected(f"BOM forbidden: {relative}")
    try:
        text = raw.decode("utf-8", errors="strict")
        lines = text.split("\n")
        if lines[-1] == "":
            lines.pop()
        if not lines or any(not line.strip() for line in lines):
            raise Rejected(f"Empty records: {relative}")
        def invalid_constant(value):
            raise Rejected(f"Non-finite JSON number: {value}")
        return [json.loads(line, object_pairs_hook=unique_object, parse_constant=invalid_constant) for line in lines]
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise Rejected(f"Invalid UTF-8/JSON: {relative}") from exc


def grade(root: Path) -> None:
    trusted = Path(__file__).parent
    expected = json.loads((trusted / "expected.json").read_text(encoding="utf-8"))
    expected_hash = (trusted / "source.sha256").read_text(encoding="ascii").strip()
    source = read_regular(root, "data/hoa_don.csv")
    if hashlib.sha256(source).hexdigest() != expected_hash:
        raise Rejected("Input CSV changed")
    records = read_jsonl(root, "output/hoa_don.jsonl")
    errors = read_jsonl(root, "output/errors.jsonl")
    for row in records:
        if type(row) is not dict or set(row) != {"invoice_id", "customer_name", "invoice_date", "amount_vnd"}:
            raise Rejected("Invoice schema")
        if any(type(row[key]) is not str for key in ["invoice_id", "customer_name", "invoice_date"]) or type(row["amount_vnd"]) is not int:
            raise Rejected("Invoice types")
        if not unicodedata.is_normalized("NFC", row["customer_name"]):
            raise Rejected("Customer name must be NFC")
    for row in errors:
        if type(row) is not dict or set(row) != {"row_number", "reason"}:
            raise Rejected("Error schema")
        if type(row["row_number"]) is not int or type(row["reason"]) is not str:
            raise Rejected("Error types")
    if records != expected["records"]:
        raise Rejected("Invoice content/order/count mismatch")
    if errors != expected["errors"]:
        raise Rejected("Error report mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/app"))
    args = parser.parse_args()
    try:
        grade(args.root)
    except Rejected as exc:
        print(json.dumps({"passed": False, "reason": str(exc)}, ensure_ascii=False))
        return 1
    except Exception as exc:
        print(json.dumps({"verifier_error": type(exc).__name__, "detail": str(exc)}, ensure_ascii=False))
        return 2
    print('{"passed": true}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
