# Normalize Vietnamese invoices

Convert `/app/data/hoa_don.csv` into `/app/output/hoa_don.jsonl` and `/app/output/errors.jsonl`. Do not modify the source file.

The CSV is UTF-8 without BOM, comma-delimited with standard CSV quoting. The header is `invoice_id,customer_name,invoice_date,amount_vnd`. Each record occupies one physical line; there are no blank lines. Each row has exactly four fields; IDs are unique nonempty ASCII strings and names are nonempty after trimming. Only dates and amounts may be invalid.

## Valid rows

Each valid row produces an object with exactly four fields:

- `invoice_id`: unchanged string.
- `customer_name`: string with leading/trailing Unicode whitespace removed and normalized to NFC; preserve accents and internal whitespace.
- `invoice_date`: input must match `dd/mm/yyyy` (2/2/4 ASCII digits) and be a valid Gregorian date in years 0001–9999; output `yyyy-mm-dd`.
- `amount_vnd`: nonnegative JSON integer. Accept input `0`, an ungrouped integer without leading zeroes (such as `2500`), or dot-grouped digits: an initial group of 1–3 digits starting with 1–9, followed by one or more groups of exactly 3 digits. Thus `1.234.567` is valid; `01`, `12.34`, `1234.567`, negative values, whitespace, decimal fractions and currency symbols are invalid. Do not round.

Sort valid objects by `invoice_id` in ascending ASCII string order.

## Invalid rows

Exclude invalid rows from the invoice file. Each invalid row produces an object with exactly two fields: `row_number` (integer: header is line 1, first data row is line 2) and `reason` (string `invalid_date` or `invalid_amount`). If both are invalid, use `invalid_date`. Order error objects by ascending source line number.

## Output format

Both files must use UTF-8 without BOM, one JSON object per line, with no blank lines; each file must be at most 1 MiB. LF/CRLF and an optional final newline are accepted. Duplicate keys and NaN/Infinity numbers are forbidden. JSON key order and whitespace do not affect grading. Only produce artifacts for the supplied data; a reusable program is not required.
