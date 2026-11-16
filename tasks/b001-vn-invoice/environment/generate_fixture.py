"""Deterministic synthetic invoice data; no answer files in the agent image."""
import argparse
import csv
import io
import unicodedata
from pathlib import Path


def generate(root: Path) -> None:
    rows = [
        ["INV010", "  Đặng Thị Hồng  ", "03/04/2026", "1.234.567"],
        ["INV002", unicodedata.normalize("NFD", "Nguyễn Văn Ước"), "29/02/2024", "0"],
        ["INV003", "Công ty Hoa, Việt", "31/12/2025", "2500"],
        ["INV004", "Đỗ Thị Ánh", "01/01/2026", "123"],
        ["INV005", "Lê Bình", "29/02/2025", "100"],
        ["INV006", "Trần Hòa", "15/03/2026", "12.34"],
        ["INV007", "Vũ Minh", "31/04/2026", "-1"],
        ["INV008", "Phạm An", "12/31/2026", "1.000"],
        ["INV009", "  Hồ Ngọc  ", "01/12/2026", "10.000"],
        ["INV001", unicodedata.normalize("NFD", "Đặng Đình Tâm"), "02/01/2026", "1000000"],
        ["INV011", "Bùi Tú", "1/02/2026", "100"],
        ["INV012", "Ngô Mai", "28/02/2025", "01"],
    ]
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["invoice_id", "customer_name", "invoice_date", "amount_vnd"])
    writer.writerows(rows)
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "hoa_don.csv").write_bytes(stream.getvalue().encode("utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/app"))
    generate(parser.parse_args().root)
