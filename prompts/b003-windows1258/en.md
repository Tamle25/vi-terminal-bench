# Convert Windows-1258 data to UTF-8

`/app/data/sources.json` is an ordered array of objects with `file` (a .bin filename directly under `/app/data`) and `encoding` (always `windows-1258`). Filenames are unique ASCII strings; metadata is valid. Sources may be empty or contain invalid bytes. Do not change any source or metadata bytes.

For each source, in metadata order:

1. Decode Windows-1258 **strictly**. If any byte is undefined, produce no text file for that source; do not use replacement or ignore.
2. For valid sources: convert CRLF and standalone CR to LF, normalize the entire text to NFC, and preserve all other content. Do not add a newline. Write UTF-8 without BOM to `/app/output/text/<stem>.txt`, where stem is the source name without `.bin`. An empty source produces an empty file.
3. Create `/app/output/report.json`, an array in source order, each object containing exactly `file`, `status`, `output`. For valid sources: status=`converted`, output is the .txt filename without directory. For invalid sources: status=`invalid_encoding`, output=null.

The `text` directory must contain only successfully converted files: no extras, subdirectories or symlinks. Artifacts must be regular files <=1 MiB. JSON must use UTF-8 without BOM, no duplicate keys or NaN/Infinity; key order/whitespace are unrestricted. Only artifacts for the supplied data are required, not a reusable program. Windows-1258 may represent tone marks as combining characters; NFC normalization does not mean accent removal.
