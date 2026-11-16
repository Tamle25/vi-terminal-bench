# Sort a catalog using Vietnamese collation

Read `/app/data/catalog.json`, an array of objects with exactly `id` (unique ASCII) and `name` (Unicode). Do not modify the source. Write `/app/output/catalog.json` containing every original object in the new order, with display names and fields unchanged.

Compare NFC-normalized names using Vietnamese collation from **ICU 76.1, CLDR 46.0**, equivalent to Node 22.14.0:

```javascript
new Intl.Collator('vi', {
  usage: 'sort', sensitivity: 'variant', caseFirst: 'lower',
  numeric: false, ignorePunctuation: false
})
```

Locale `vi`, collation `default`; variant sensitivity distinguishes accents and case (tertiary), with lowercase before uppercase for case differences. Numeric collation is off: do not interpret digit sequences as integers. If the collator considers names equal, break ties by ascending ASCII ID. Normalize only for comparison; preserve original Unicode display names in the output.

The image provides `node` with full ICU; `/opt/collation-runtime.json` records versions and resolved options. Other tools are allowed if results are equivalent; do not download packages.

The output must be a UTF-8 JSON array without BOM, a regular file <=1 MiB, with no duplicate keys/NaN/Infinity. Key order/whitespace are unrestricted. Only artifacts for supplied data are required, not a reusable program. Code point order or accent-stripped sorting does not replace this collation.
