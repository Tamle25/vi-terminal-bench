# Export Vietnamese CSV to a specified import contract

`/app/export.py` is an existing exporter with incorrect formatting. Read `/app/data/orders.json` and create `/app/output/orders.csv`. You may fix the exporter or produce the artifact another way; the verifier grades only the CSV, does not execute your code, and does not check exporter modifications. Do not change the bytes of `data/orders.json`.

Input is an array of objects with `id` (unique ASCII), `customer`, `date` (valid ISO date), `amount_vnd` (nonnegative integer), `note` (Unicode string, possibly empty, containing punctuation/quotes/line breaks).

CSV contract:

- Exactly one UTF-8 BOM at the beginning, delimiter `;`, standard `"` CSV quoting (double embedded quotes). Minimal quoting or quoting every cell is accepted.
- Exact header order: `ma_don;khach_hang;ngay;so_tien_vnd;ghi_chu`.
- Records sorted by ascending ASCII ID; preserve IDs including leading zeroes and customer accents.
- Dates become `dd/mm/yyyy`; amounts use dot-separated thousands, no decimals/currency symbols; zero becomes `0`.
- Preserve notes except normalize CRLF/CR/LF to CRLF. Every line break in the entire file, including inside cells, must be CRLF; the last record also ends with CRLF. No extra blank rows.
- Cell values must be exact; do not add apostrophes, formulas, extra columns, or a `sep=` directive.

The artifact must be a regular file <=1 MiB. This is a specific format contract, not a requirement to open Excel or guarantee type inference in every Excel version. Only output for the supplied data is required.
