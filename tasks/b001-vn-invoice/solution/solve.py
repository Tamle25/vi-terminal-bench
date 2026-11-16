"""Reference solution, only mounted for oracle validation."""
import argparse
import csv
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path


def solve(root: Path) -> None:
    records, errors = [], []
    with (root / "data/hoa_don.csv").open(encoding="utf-8", newline="") as source:
        for number, row in enumerate(csv.DictReader(source), 2):
            date_text = row["invoice_date"]
            try:
                if not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", date_text):
                    raise ValueError("date format")
                day = dt.datetime.strptime(date_text, "%d/%m/%Y").date()
            except ValueError:
                errors.append({"row_number": number, "reason": "invalid_date"})
                continue
            amount = row["amount_vnd"]
            if not re.fullmatch(r"(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:\.[0-9]{3})+)", amount):
                errors.append({"row_number": number, "reason": "invalid_amount"})
                continue
            records.append({
                "invoice_id": row["invoice_id"],
                "customer_name": unicodedata.normalize("NFC", row["customer_name"].strip()),
                "invoice_date": day.isoformat(),
                "amount_vnd": int(amount.replace(".", "")),
            })
    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    for filename, values in [("hoa_don.jsonl", sorted(records, key=lambda r: r["invoice_id"])), ("errors.jsonl", errors)]:
        text = "".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values)
        (output / filename).write_bytes(text.encode("utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/app"))
    solve(parser.parse_args().root)
