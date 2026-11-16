# Find customers with accent-insensitive queries

Read `/app/data/customers.json` (array of `id`, `name` objects) and `/app/data/queries.json` (array of `id`, `text` objects). IDs are unique ASCII strings within each array; strings are valid Unicode. Do not modify sources.

Create search keys for both names and queries in this exact order:

1. Normalize to NFD.
2. Remove every code point with nonzero Unicode canonical combining class (equivalent to `unicodedata.combining(c) != 0`).
3. Map `đ` to `d` and `Đ` to `D`, then apply Unicode casefold.

Match the query key as a **substring** of the name key. Do not trim or collapse whitespace, remove punctuation, or search IDs. An empty key must not match every customer.

Write `/app/output/results.json`: an array in query order. Each object has exactly `query_id` (query ID), `matches` (array of objects with exactly `id`, `name`), and `error`. Sort matches by ascending ASCII ID. Preserve each display name exactly, including NFD form. For an empty key: matches=[], error=`empty_query`; otherwise error=null, including zero matches. Repeated query text with distinct IDs still produces separate results.

The artifact must be a regular file <=1 MiB, UTF-8 without BOM, valid JSON without duplicate keys/NaN/Infinity. Key order/JSON whitespace are unrestricted. Only artifacts for supplied data are required, not a reusable program.
