# Worked example: DeviceToolbox 582-key iOS catalog (zh-Hans → ja)

Session detail behind the general workflow. Real run, real numbers.

## Layout

```
Sources/Resources/
  en.lproj/Localizable.strings        # reference: terminology + brand terms, 582 keys
  zh-Hans.lproj/Localizable.strings   # source, 582 keys, carries /* section */ comments
  ja.lproj/Localizable.strings        # target (was a byte-identical zh-Hans copy)
  ko.lproj/Localizable.strings        # still a zh-Hans copy  <-- outstanding
  zh-Hant.lproj/Localizable.strings   # still a zh-Hans copy  <-- outstanding
```

Detection that a language is an unstarted placeholder copy:

```bash
diff -q ja.lproj/Localizable.strings zh-Hans.lproj/Localizable.strings   # IDENTICAL
```

Key counts across all five languages were equal (582) even though three were Chinese
copies — so **equal key counts do NOT mean the translation is done.** Compare values.

## Required output shape (task-specified)

- same 582 keys, same order, no additions/removals;
- `%@ %lld %d` preserved verbatim in natural Japanese positions;
- plain `.strings`, one entry per line, escaped inner quotes, **no comments**;
- brand terms kept as in the English file.

The source carried 28 comment lines (`/* 通用 */`, `// ...appended 2026-09-12`) and the
target was required to be comment-free. The resulting ja file is exactly 582 lines with
zero comments — hence `raw.count("\n") == len(keys)` is a valid assertion for it.

## Keys whose *names* contain placeholders

Three keys carry placeholders on the left-hand side. They must be copied verbatim, and a
file-wide `grep -oE '%[@l0-9]+'` will match them on both files (measure both the same way):

```
"cleaner.result.body %lld %lld %@"      = "%lld 件をクリーンアップ · %lld 件失敗 · %@ を解放";
"gestalt.export.done %@"                = "%@ をワークスペースに書き出しました";
"system.container.export.done %@"       = "%@ をワークスペースに書き出しました(読み込み済み)";
```

Value-side placeholder keys: `wallpaper.store_summary` (`%@ %lld %lld`),
`wallpaper.package_summary`, `wallpaper.package_files`,
`wallpaper.install_warning_message` (four placeholders),
`wallpaper.import_done_message`, `wallpaper.reset_message`,
`wallpaper.error.dynamic_unsupported_detail`.

Escaped characters that break naive parsing: `\n\n` inside `disclaimer.body`, and
`{\"Enabled\": true}` inside `featureflags.source.note`.

## Result

- 559 / 582 values differ from the Chinese source.
- 23 keys are legitimately byte-identical — brand and shared-script terms:
  `Wi-Fi`, `IPv4`, `IPv6`, `最低 iOS` (×2), `操作`, `通知`, `保存` (×2), `作者`,
  `Feature Flags` (×2), `Siri`, `SiriUI`, `SiriNL`, `sae`, `sae_override`,
  `assistant_engine_override`, `Private Cloud Compute`,
  `com.apple.privatecloudcompute.override`, `Text Composer`, `text_composer_override`,
  `siri_nl_override`.
  This set is the allowlist the verifier warns about; anything *outside* it that still
  matches the source is a missed translation.

## The three false-positive FAILs (the actual lesson)

The first verification pass reported FAILs that were **checker defects**, not artifact
defects. Fixing the translations to satisfy them would have damaged correct output.

1. `"every line matches strict grammar"` — the checker parsed *all three* files with
   comments disabled, so the commented zh/en references showed 28 unparsed lines.
   Fix: skip comments **only** when parsing sources; a target that must be comment-free
   gets strictness, sources do not.
2. `"no value left as bare non-Latin text"` — the charset `\u3000-\u9fff` includes kana,
   so every Japanese string was flagged. 437 hits, all valid.
3. `"no Simplified-only characters"` — over-broad charset flagged `号` in
   `device.build.number = ビルド番号`. **号 is standard Japanese** (番号). Same class of
   error would flag 定/免/本/限/面/名/通/制/照/除.

Correct discriminator: (a) kana present ⇒ Japanese, stop; (b) equality-with-source
checked against an explicit brand allowlist; (c) a *curated* Simplified-only set, never a
Han range.

## Verification command actually run

```bash
V=$(mkdtemp ...)/hermes-verify-strings.py    # exact path, not a glob
python3 "$V"; rm -rf "$(dirname "$V")"
plutil -lint ja.lproj/Localizable.strings    # OK
```

Result: 13/13 PASS, exit 0. `plutil -lint` was OK on ja, and re-run on zh-Hans/en to
prove the sources were untouched (no edits, no commit).

## Temp-dir incident worth remembering

Re-running used `ls -d "$TMPDIR"/hermes-verify-*/ | tail -1` to find the script; the glob
matched a **different** tool's `hermes-verify-wallpaper-*` directory and the follow-up
`rm -rf` deleted it. In a shared temp dir, the glob is the bug. Always carry the exact
`mkdtemp` path; if you must search, match the full filename too
(`hermes-verify-strings.py`), never a bare prefix with `tail -1`.
