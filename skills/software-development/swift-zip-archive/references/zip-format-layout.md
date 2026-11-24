# ZIP format field-by-field layout (stored + deflate, no ZIP64)

Byte offsets below are from the start of each structure. All multi-byte fields are
little-endian. Signatures are the first 4 bytes of each structure.

## Local file header (signature 0x04034B50) — 30 fixed bytes + variable

| offset | size | field |
|---|---|---|
| 0  | 4 | signature 0x04034B50 |
| 4  | 2 | version needed to extract (20) |
| 6  | 2 | general purpose flags (bit 0 = encrypted, bit 11 = UTF-8 name) |
| 8  | 2 | compression method (0 stored, 8 deflate) |
| 10 | 2 | last mod file time (DOS) |
| 12 | 2 | last mod file date (DOS) |
| 14 | 4 | CRC-32 of uncompressed data |
| 18 | 4 | compressed size |
| 22 | 4 | uncompressed size |
| 26 | 2 | file name length (n) |
| 28 | 2 | extra field length (m) |
| 30 | n | file name bytes |
| 30+n | m | extra field |
| 30+n+m | ... | file data (compressed size bytes) |

## Central directory header (signature 0x02014B50) — 46 fixed bytes + variable

| offset | size | field |
|---|---|---|
| 0  | 4 | signature 0x02014B50 |
| 4  | 2 | version made by (0x0314 = 3.20) |
| 6  | 2 | version needed (20) |
| 8  | 2 | flags |
| 10 | 2 | method |
| 12 | 2 | mod time |
| 14 | 2 | mod date |
| 16 | 4 | CRC-32 |
| 20 | 4 | compressed size |
| 24 | 4 | uncompressed size |
| 28 | 2 | name length (n) |
| 30 | 2 | extra length (m) |
| 32 | 2 | comment length (c) |
| 34 | 2 | disk number start (0) |
| 36 | 2 | internal attrs (0) |
| 38 | 4 | external attrs: `(unixMode << 16) | (isDir ? 0x10 : 0)` |
| 42 | 4 | local header offset |
| 46 | n+m+c | name + extra + comment |

Unix mode constants: dir `0o040755`, regular file `0o100600`.
File-type detection on read: `(externalAttrs >> 16) & 0o170000` → `0o040000` dir,
`0o100000` regular, `0o120000` symlink (reject), `0` means regular (unset).

## End of central directory / EOCD (signature 0x06054B50) — 22 bytes + comment

| offset | size | field |
|---|---|---|
| 0  | 4 | signature 0x06054B50 |
| 4  | 2 | disk number (0) |
| 6  | 2 | central directory start disk (0) |
| 8  | 2 | entries on this disk |
| 10 | 2 | total entries |
| 12 | 4 | central directory size |
| 16 | 4 | central directory offset |
| 20 | 2 | comment length |
| 22 | ... | comment |

Reader note: locate EOCD by scanning the last 65557 bytes for the signature (handles
a trailing comment); validate `centralOffset + centralSize == eocdOffset`.

## DOS date/time packing

- time: `(hour << 11) | (minute << 5) | (second / 2)`
- date: `((year - 1980) << 9) | (month << 5) | day`
- Valid year range 1980–2107.

## Reader validation checklist (from a working implementation)

1. EOCD: disk==0, centralDisk==0, diskEntries==totalEntries, no 0xFFFF/0xFFFFFFFF ZIP64 markers.
2. Per central entry: flags&1==0 (no encryption), method in {0,8}, diskStart==0, no ZIP64 size/offset.
3. Name decode: UTF-8 (flag bit 11) else UTF-8→CP437 fallback.
4. `safeComponents`: reject empty/absolute (`/` prefix)/`\`/control chars/`.`/`..` components.
5. Symlink file type `0o120000` → reject.
6. Duplicate name → reject; a file must not precede a directory with the same prefix path.
7. Per-entry uncompressed ≤ 256MB; running total ≤ 1GB; entry count ≤ 5000.
8. Local header must match central (signature, method, name bytes); data offset in bounds.
9. On extract: inflate (method 8) via `compression_decode_buffer`, assert decoded count ==
   declared uncompressed size, then CRC32 over uncompressed bytes == declared CRC.
