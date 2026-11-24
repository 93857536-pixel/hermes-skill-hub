---
name: ios-localization-strings
description: Use when localizing .lproj/.strings app catalogs.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [localization, i18n, ios, strings, plutil, translation]
    related_skills: [ios-watchos-app-development, macos-appkit-development]
---

# Localizing string catalogs (.lproj / .strings)

## When to Use

- Translating an app's `Localizable.strings` into a new language.
- Adding a new `.lproj` directory and its catalog.
- Auditing localization completeness: missing/extra keys, key-order drift, placeholder
  drift, or un-translated placeholder copies across languages.
- The same discipline applies to Android `strings.xml` / gettext `.po` — swap the
  lint/format steps for the platform tool.

Covers: iOS/macOS `Localizable.strings`.

Class of task: take a source-language catalog and produce/repair a target-language
catalog — same keys, same order, same count, placeholders intact — then **prove** it
mechanically.

Recurring shape: this is a batch job repeated per language (`ja`, `ko`, `zh-Hant`, …).
Adding one language is not a one-off; expect sibling directories next. Inspect their
current state early.

## Workflow

1. **Read the whole reference set first, before writing a single value.**
   - Source language (what you translate *from*) plus the English file (terminology and
     brand reference). Diff their key sequences up front:
     `diff <(grep -oE '^"[^"]+"' a) <(grep -oE '^"[^"]+"' b)`
   - Count keys in every language present. Siblings that are byte-identical to the source
     are usually placeholder copies — flag them in your report.
2. **Write in source key order**, one entry per line, plain `"key" = "value";`.
   Keep the file comment-free if the task says so. Sources often *do* carry comments —
   don't let those leak into the target, and don't apply a "no comments" rule to sources.
3. **Preserve placeholders verbatim**: `%@ %lld %d %f`, including keys that themselves
   contain placeholders (`"cleaner.result.body %lld %lld %@"`). Re-position them into
   natural target-language word order; never drop, duplicate, or renumber.
4. **Keep brand/technical terms as in the English file** (product names, `MCM`, `MDM`,
   `ESign`, `WeChat`, `PosterBoard`, `MobileGestalt`, flag key names, `Wi-Fi`, `IPv4`).
   These legitimately end up byte-identical to the source — correct, not a miss.
5. **Verify with a script, not vibes**: run `scripts/verify_strings_catalog.py`, then
   `plutil -lint` on the output.
6. **Report evidence**: key count (source vs target), placeholder diff result, lint
   status — concrete numbers, not "looks good".

## Verification

The bundled script is read-only and re-runnable:

```bash
python3 scripts/verify_strings_catalog.py SOURCE.strings TARGET.strings --no-comments
plutil -lint TARGET.strings
```

It checks: strict per-line grammar, key sequence identity, per-key placeholder multiset,
no raw newlines inside values, optional comment-free, and `plutil -lint`. It *warns*
(never fails) on values identical to the source, so you can judge each as brand term vs
missed translation.

Worked example, including what the false-positive FAILs looked like, is in
`references/device-toolbox-example.md`.

## Pitfalls (all hit for real)

- **Your checker is more likely to be wrong than the artifact.** A FAIL means
  "artifact OR checker". Validate the checker against a **known-good** file first (the
  English reference should pass trivially) and read the failing *values* before "fixing"
  the translation. In one run the checker produced three bogus FAILs: a CJK range that
  matched valid Japanese text, and a "no comments" rule misapplied to the commented
  reference file. Never rewrite correct translations to satisfy a broken check.
- **Han characters are shared between Chinese and Japanese — codepoint ranges cannot
  separate them.** `定 免 本 限 面 名 通 制 照 号 除 私` are all valid Japanese kanji
  (設定/免責/制限/画面/名前/通知/参照/番号). Only flag *Simplified-only* forms
  (设 备 页 选 择 换 权 项 单 击 扫 态 无 为 …). **Kana = `\u3040-\u30ff`; a value with
  kana is Japanese, full stop.** An over-broad "non-Latin" charset flags hundreds of
  good strings and buries the real signal.
- **Keys can contain spaces and `%` placeholders.** Parse whole lines with
  `^"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;\s*$` so escaped quotes (`\"`) and
  escaped newlines (`\n`, not a literal newline) are handled. Any line failing that regex
  is a real defect worth printing.
- **The placeholder regex is not anchored to the value side.** `grep -oE '%[@l0-9]+'`
  over the file also picks up placeholders inside *key* names — correct and expected, as
  long as both files are measured the same way.
- **Temp-file hygiene: never glob-and-delete in a shared temp dir.** Carrying the exact
  `mkdtemp` path forward is safe; `ls -d "$TMPDIR"/hermes-verify-*/ | tail -1` is not —
  it matched a different tool's directory and `rm -rf` destroyed it. Always keep the
  exact path.
- **Don't touch the source languages.** No edits, no `git commit`/`push` unless asked.
  Re-lint the sources at the end to prove they are unchanged.
- `plutil -lint` is the cheapest structural check for `.strings`; `-s` silences the OK
  banner for scripted use. It also converts: `plutil -convert binary1|xml1`.
