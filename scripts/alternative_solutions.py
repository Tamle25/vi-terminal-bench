"""Independent development solutions; not part of agent or verifier images."""
import calendar
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import unicodedata
from pathlib import Path


def emit(path: Path, rows: list[dict]) -> None:
    # Reversed key order, ASCII escapes and CRLF intentionally exercise permissive JSON formatting.
    path.write_bytes("\r\n".join(json.dumps(dict(reversed(list(row.items()))), ensure_ascii=True, separators=(",", ":")) for row in rows).encode("utf-8"))


def invoice(root: Path) -> None:
    with (root / "data/hoa_don.csv").open(encoding="utf-8", newline="") as handle:
        table = list(csv.reader(handle))
    valid, errors = [], []
    for number, (identifier, name, date_text, money) in enumerate(table[1:], 2):
        date = None
        if re.fullmatch("[0-9]{2}/[0-9]{2}/[0-9]{4}", date_text):
            day, month, year = map(int, date_text.split("/"))
            if 1 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= calendar.monthrange(year, month)[1]:
                date = datetime.date(year, month, day).isoformat()
        groups = money.split(".")
        money_ok = money.isascii() and all(group.isdigit() for group in groups)
        if len(groups) == 1:
            money_ok = money_ok and (money == "0" or not money.startswith("0"))
        else:
            money_ok = money_ok and 1 <= len(groups[0]) <= 3 and not groups[0].startswith("0") and all(len(group) == 3 for group in groups[1:])
        if date is None or not money_ok:
            errors.append({"row_number": number, "reason": "invalid_date" if date is None else "invalid_amount"})
        else:
            valid.append(dict(invoice_id=identifier, customer_name=unicodedata.normalize("NFC", name.strip()), invoice_date=date, amount_vnd=int("".join(groups))))
    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    emit(output / "hoa_don.jsonl", sorted(valid, key=lambda row: row["invoice_id"]))
    emit(output / "errors.jsonl", errors)


def unicode_files(root: Path) -> None:
    incoming = root / "incoming"
    output = root / "output"
    files = output / "files"
    files.mkdir(parents=True, exist_ok=True)
    original_names = sorted(os.listdir(incoming), key=lambda name: tuple(map(ord, name)))
    records = []
    for index, name in enumerate(original_names):
        target = str(index + 1).zfill(4) + "--" + unicodedata.normalize("NFC", name)
        source = incoming / name
        shutil.copyfile(source, files / target)
        with source.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        records.append(dict(source=name, target=target, sha256=digest, size_bytes=source.stat().st_size))
    emit(output / "index.jsonl", records)
