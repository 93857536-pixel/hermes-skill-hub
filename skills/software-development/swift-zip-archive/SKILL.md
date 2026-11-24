---
name: swift-zip-archive
description: Use when writing a self-made ZIP codec in Swift.
version: 1.0.0
author: curator
license: MIT
metadata:
  hermes:
    tags: [swift, zip, compression, crc32, codec, ios, macos, foundation]
    related_skills: []
---

# Swift ZIP Archive (zero-dependency codec)

## When to Use

- Implementing a ZIP reader/writer in Swift with no third-party dependencies (only
  `Foundation` + the system `Compression` framework).
- Debugging `compression_encode_buffer` / `compression_decode_buffer` calls or CRC/encoding
  issues in a ZIP codec.
- Adding stored/deflate round-trip, zip-slip rejection, or CRC-corruption tests.

Self-implementing ZIP read/write in Swift/iOS/macOS. Covers stored (method 0) and deflate
(method 8) entries, CRC32, filename encoding (UTF-8 + CP437 fallback), and zip-slip protection.

## Compression framework API — the #1 gotcha

`compression_encode_buffer` / `compression_decode_buffer` take the scratch buffer
**WITHOUT a size argument**. You allocate it via `*_scratch_buffer_size`, but do NOT
pass that size into the call. Passing an extra `scratchSize` arg produces
"extra argument in call" + "cannot convert Int to compression_algorithm".

```swift
import Compression

// correct Swift signatures (size_t → Int):
// compression_encode_buffer(dst, dstSize, src, srcSize, scratch /*UnsafeMutableRawPointer?*/, COMPRESSION_ZLIB) -> Int
// compression_decode_buffer(dst, dstSize, src, srcSize, scratch, COMPRESSION_ZLIB) -> Int

let scratchSize = compression_encode_scratch_buffer_size(COMPRESSION_ZLIB)  // allocate ONLY
var scratch = [UInt8](repeating: 0, count: scratchSize)
let written = data.withUnsafeBytes { srcBuf -> Int in
    let src = srcBuf.bindMemory(to: UInt8.self)
    return dst.withUnsafeMutableBytes { dstBuf -> Int in
        let d = dstBuf.bindMemory(to: UInt8.self)
        return scratch.withUnsafeMutableBytes { scBuf -> Int in
            let sc = scBuf.bindMemory(to: UInt8.self)
            return compression_encode_buffer(d.baseAddress!, dstSize,
                                             src.baseAddress!, data.count,
                                             sc.baseAddress!,          // NO size here
                                             COMPRESSION_ZLIB)
        }
    }
}
guard written > 0, written < data.count else { return nil }  // 0 = buffer too small / error
```

- Encode returns 0 on failure (buffer too small or error); returns bytes written otherwise.
- Decode returns bytes written; check `written == expectedSize` to catch truncation/corruption.
- For deflate, safe dst cap is roughly `srcSize + srcSize/8 + 1024`; if the result isn't smaller than the input, fall back to stored.

## UnicodeScalar init gotcha

`UnicodeScalar(UInt8)` is **non-failable**; `UnicodeScalar(UInt16)` and `UnicodeScalar(UInt32)`
are **failable** (return `Unicode.Scalar?`). So `guard let x = UnicodeScalar(byte)` fails to compile
for `UInt8`, and `Character(UnicodeScalar(u16value))` fails without `!`.
For CP437 high-half tables (all values are valid non-surrogate scalars), use `UnicodeScalar(u16value)!`.

## ZIP format quick reference

Signatures: local `0x04034b50`, central `0x02014b50`, EOCD `0x06054b50`.
- Local header: 30 fixed bytes — crc @14, compressedSize @18, uncompressedSize @22, nameLen @26, extraLen @28; then name, extra, then data.
- Central header: 46 fixed bytes — flags @8, method @10, crc @16, compressedSize @20, uncompressedSize @24, nameLen @28, extraLen @30, commentLen @32, diskStart @34, externalAttrs @38, localOffset @42.
- EOCD: diskNum @4, centralDisk @6, diskEntries @8, totalEntries @10, centralSize @12, centralOffset @16, commentLen @20.
- Flag bit 11 = UTF-8 filename. Flag bit 0 = encrypted (reject). Method 0 = stored, 8 = deflate.
- DOS time/date packed (time = hour<<11|min<<5|sec/2; date = (year-1980)<<9|month<<5|day).

Full field-by-field layout: see `references/zip-format-layout.md`.

## CRC32 (self-implemented)

Reflected polynomial `0xEDB88320`. Build a 256-entry table once, then per-byte update:
`crc = table[(crc ^ byte) & 0xFF] ^ (crc >> 8)`, seed `0xFFFFFFFF`, finalize with `^ 0xFFFFFFFF`.
Share ONE `CRC32` enum between writer and reader (compute over the *uncompressed* bytes — ZIP's
CRC field is over uncompressed content, both for stored and deflate).

## Filename decoding

- Flag bit 11 set → decode UTF-8 (throw if invalid).
- Otherwise try UTF-8 first, then fall back to CP437 (DOS code page). CP437 high half (0x80–0xFF)
  is a fixed 128-entry Unicode table (public standard, not GPL).

## Security: zip-slip + limits

- Reject names that are empty, start with `/`, contain `\`, contain control chars, or have any
  component of `""`, `.`, `..`. Throw `.unsafeArchive`-mapped error.
- Defense-in-depth: build the target URL component-by-component, then verify
  `standardizedFileURL.path.hasPrefix(root.standardizedFileURL.path + "/")`.
- Reject symlink entries (external attr file type `0o120000`).
- Enforce per-entry 256MB / total 1GB / 5000 entries; also reject ZIP64 markers (0xFFFF / 0xFFFFFFFF).

## Pitfalls (each cost a build round once)

1. **Staging file location**: when writing an archive whose destination lives inside the source
   tree being enumerated, a staging file created in `destinationURL.deletingLastPathComponent()`
   gets enumerated as a phantom entry. Put staging in `FileManager.default.temporaryDirectory`,
   then `moveItem` to the destination (same volume = atomic).
2. **Swift target requires unique source basenames**: two files named `Models.swift`/`Errors.swift`
   in different subdirectories fail with `Filename "X.swift" used twice`. Swift uses the filename
   to disambiguate private declarations. In multi-directory/multi-agent projects, name each domain's
   files uniquely (e.g. `FileEntry.swift`, `FileOperationError.swift`) — renaming a file does not
   change its types.
3. **deflate buffers whole file into memory**: acceptable for small files; for large files use a
   stored streaming path (two-pass: first stream to compute CRC + size, then write header + stream).
4. **Empty file**: deflate of empty input is never smaller — return nil from compress so it uses stored.
5. **File-scope extensions must be at file scope**: a `private extension Data { mutating func appendLE(_ v: UInt16) }` helper written *inside* a type body (enum/struct) fails with `declaration is only valid at file scope`. Put byte-append helpers at file scope, after the closing brace of the type that uses them.
6. **EPUB writer**: `mimetype` must be the FIRST entry, method 0 (stored), and its local header must have **no extra field** (extraLen = 0). Set flags bit 11 (0x0800) for UTF-8 filenames. Verify with python: `zipfile.ZipFile(f).infolist()[0]` → `compress_type == 0 and extra == b""` + `testzip() is None` + `minidom.parseString` on each XML part.

## Verification

- Round-trip: write → extract → byte-compare content, assert `fileCount` and `byteCount`.
- Reject tests: hand-build a stored ZIP (bytes) with an overridden name (`../evil.txt`), overridden
  declared size (300MB), overridden CRC, or 5001 entries → assert the service throws `unsafeArchive`.
- Proving deflate engaged: compress a highly-repetitive buffer and assert archive size << input size.
