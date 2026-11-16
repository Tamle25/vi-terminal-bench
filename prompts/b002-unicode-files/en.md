# Preserve data while normalizing Vietnamese filenames

`/app/incoming` contains regular files with valid Unicode names, no subdirectories or symlinks. Names may differ in case, spaces, or Unicode NFC/NFD form, including two visually identical names. Contents may be binary. Do not change source filenames or bytes.

Copy every file into `/app/output/files` and create `/app/output/index.jsonl` using these rules:

1. List the exact original filenames, then sort ascending by their Unicode code point sequences (equivalent to Python `sorted` on strings). Do not normalize, remove accents, casefold, or apply locale collation when sorting.
2. Number files from 1 in that order. Every destination filename is the ordinal padded to at least 4 digits, followed by `--`, followed by the original filename normalized to NFC. For example, a first file named `Đơn.txt` becomes `0001--Đơn.txt`. Distinct numeric prefixes resolve collisions after NFC normalization. Do not remove accents or change case.
3. Copy the exact content bytes into the destination. The `files` directory must contain only destination files, with no extras, subdirectories, or symlinks.
4. Write the index in the same order, one object per line with exactly these fields: `source` (exact original filename, not normalized), `target` (destination filename without directory), `sha256` (lowercase hex SHA-256 of the content), `size_bytes` (JSON integer byte count).
5. Use UTF-8 without BOM for the index, no blank lines, one JSON object per line; its size must be at most 1 MiB. LF/CRLF and an optional final newline are accepted. Duplicate keys and NaN/Infinity numbers are forbidden. JSON key order and whitespace do not affect grading.

Only produce artifacts for the supplied data; a reusable program is not required. Preserve Vietnamese accents and distinguish source files containing different data.
