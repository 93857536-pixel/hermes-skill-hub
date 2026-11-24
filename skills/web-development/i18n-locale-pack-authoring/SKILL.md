---
name: i18n-locale-pack-authoring
description: Use when generating or verifying i18n locale packs.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags:
      - i18n
      - localization
      - typescript
      - verification
    related_skills:
      - ios-localization-strings
      - tauri-app-development
---

# i18n Locale Pack Authoring

## When to Use

- A task asks to "translate the app into N languages", "add locale files", or "generate
  `zh-TW.ts` / `ja.ts` / …" against an existing base dictionary.
- Auditing locale packs someone else (or a subagent) wrote: key parity, placeholder integrity,
  and whether the strings actually reach the bundle.
- Mirroring a newly added key into many existing locales — same contract, run in reverse.
- Not for iOS `.lproj` / `.strings` catalogs; use `ios-localization-strings` for those.

For adding N languages to an existing TS/JS app (React/Vue/Vite/Tauri webview, plain
`Record<string, string>` dictionaries). Applies to both authoring a batch and auditing one
someone else (or a subagent) claims to have written.

## Iron rule: the base file is the contract, not the task description

The base locale (usually `en.ts` / `en.json`) is the only source of truth for key set and
order. Task specs, tickets, and your own earlier counts are frequently wrong.

- **Count the keys yourself before writing anything.** Specs get miscounted upstream
  (a real case: the brief said 87 keys, `en.ts` actually had 81 — writing 87 would have
  invented 6 keys and broken the `Dict` type / any exhaustive map).
- When a stated count disagrees with the file, **match the file** and surface the discrepancy
  in your summary instead of silently picking one.
- Never "fix" the base file to match the spec. Never add keys a locale needs but the base
  lacks — that key belongs in the base first, then gets mirrored out.

## Workflow

1. **Read the base locale fully** plus one existing translated locale (e.g. `zh-CN.ts`). The
   existing locale shows the house style: comment header form, blank-line grouping, identifier
   naming (`zhCN`, `ptBR`), whether `Dict` is re-exported, whether keys are grouped by feature.
2. **Extract the key list programmatically** (regex over `^  'key':` lines, or the JSON) and
   keep it as the checklist you work through. Do not hand-copy from the prompt.
3. **Write one file per locale** with `write_file` — full file, not patches. Match the
   identifier and header comment convention exactly.
4. **Verify in layers** (see below); each layer catches a different class of error.
5. **Check the registry/gating**, not just the files: does a language list (`LANG_META`,
   `SUPPORTED_LOCALES`, a `locales` array in config) need the new codes? If it already lists
   them and loading is a glob (`import.meta.glob('./locales/*.ts', { eager: true })`), adding
   files is enough — do not touch the registry.
6. **Report** file names, key count, and which verification actually ran.

## Translation requirements that reviewers check first

- **Placeholders are code, not prose**: `{n}`, `{msg}`, `{tag}`, `{name}`, `{online}`, `{max}`
  stay byte-identical. Translating `{n}` to `{N}` or a full-width `｛n｝` is a silent runtime bug.
  Some placeholders are grammatical — reorder words around them, never mutate them.
- **Brand / tech nouns stay verbatim**: product name, `Java`, `JDK`, `Temurin`, `Minecraft`,
  `Rosetta 2`, `MB`, loader names, file formats.
- **Natural target-language UI phrasing, not calque.** Read it as if the app were shipped in
  that language: pick the platform-standard verb for buttons (`設定`/`Einstellungen`/
  `Paramètres`/`Ajustes`/`Impostazioni`/`Configurações`), and prefer the term real users of the
  domain use (`伺服器`, `メモリ`, `메모리`, `Arbeitsspeicher`, `mémoire`, `memoria`) over a
  dictionary-literal translation.
- **Short strings stay short.** Nav items, tab labels, and buttons get a fixed-width slot;
  prefer the compact native word (`Logs` is idiomatic German in dev tooling and beats the longer
  `Protokolle`). Avoid doubling length on `common.del`-style abbreviations — use the language's
  own abbreviation (`Suppr.`, `Elim.`, `Excl.`).
- **Regional variants differ, not just glyphs**: `zh-TW` wants `設定/儲存/建立/伺服器/記憶體/
  執行環境`, not Simplified vocabulary with converted characters (character conversion alone
  isn't enough — lexical swaps like `视频`→`影片` also apply). `pt-BR` wants
  `Configurações/Excluir`, not `Ajustes/Eliminar` (European Portuguese).
- **Quoting**: when the file uses single-quoted TS strings, every inner apostrophe must be
  `\'`. This bites hardest in `fr` and `it` (`l\'interface`, `così com\'è`, `un\'istanza`).
  Welsh is worse still, and it is the densest apostrophe language in these batches: the
  mutation apostrophe is grammatical (`i\'r`, `gosodiadau\'r`, `wedi\'i`). Prefer the
  non-elided construction where the sentence allows (`osodiadau y gêm`, `at y gêm`,
  `a drosglwyddir i\'r gêm` when it doesn't) so no escape is needed. Catalan elisions
  (`s\'envia`, `l\'instant`) and Afrikaans/Filipino possessives are the same trap.
  Cheaper fix where the wording allows: rephrase to avoid the apostrophe
  (`Aucune instance pour le moment` instead of `... pour l'instant`), or use the language's
  native quotation marks for quoted UI labels (`« Tester »`, `„Testen“`, `「テスト」`).
- **Reuse the file's own vocabulary for the same concept.** Before translating
  `instances.language`, grep the file for the neighbouring key it must agree with
  (`grep -n "settings.language" f.ts`). French shipped `'Langue'` there, so `Langage du jeu`
  was wrong on contact (`langage` = the faculty of speech; `langue` = a language). The same
  class of slip produced `Spieldate` for `Spielsprache`, `Spil sprog` for Danish `Spilsprog`
  (one word), `Wikaan ng laro` for Filipino `Wika`, and Welsh `Ieithydd` (a linguist) where
  `Ieithoedd` (languages) was meant. These survive `tsc`, the count invariant, and diff
  review — only a second read of the shipped term, against the file's existing keys, catches
  them.
- Empty string values are always a bug — a "translation" of `''` renders a blank label.

## RTL batches (ar / he / fa / ur)

**RTL is registry-driven, not per-file.** Before writing anything, read the language registry
(`LANG_META`, `SUPPORTED_LOCALES`) and check whether the codes are already there with an
`rtl` flag. In the common Vite pattern the provider does
`document.documentElement.dir = rtl ? 'rtl' : 'ltr'`, so:

- codes already listed with `rtl: true` → write the files and **touch nothing else**;
- codes missing → the locale file alone ships *LTR-rendered* Arabic: every string is correct and
  every layout is mirrored wrong. Add the registry entry (or report it, in a parallel batch).

Content rules that only bite in RTL:

- Native script in the file header (`/** العربية */`) and in every UI word — never Latin
  transliteration.
- Latin brand nouns (`CraftCraft`, `Java`, `JDK`, `Temurin`, `Minecraft`, `Rosetta 2`, `MB`,
  `x86_64`) stay Latin inside the RTL string. They are bidi islands; no wrapping marks needed.
- Placeholders keep ASCII braces: the interpolator matches `/\{(\w+)\}/g` only. Arabic-Indic
  digits inside `{n}` or full-width `｛n｝` silently fail to interpolate.
- Leading `+` and trailing `…` are direction-neutral and land correctly on their own — keep them
  byte-identical to the base rather than reordering.
- Persian needs the half-space (ZWNJ, U+200C) in compounds like `نمونه‌ها`, `گزارش‌ها`; a plain
  space is a visible typo. Copy shipped strings verbatim instead of retyping.
- Don't sprinkle RTL control chars (`RLM`/`LRM`) into strings — the `dir` attribute already
  handles direction, and stray marks leak into grep checks and screenshots.

## Plural forms: identical `count_one` / `count_other` is sometimes right

Splitting the two keys is correct only where the language inflects. Arabic and Hebrew do
(`نسخة`/`نسخ`, `מופע`/`מופעים`) and must differ. Persian, Urdu, Thai, Vietnamese and Indonesian
take a singular noun after numerals or have no plural inflection at all, so **identical text in
both keys is the correct output** — do not "fix" it, and do not treat it as a bug when auditing.
Flag genuinely missing Slavic `few`/`many` forms instead of faking them.

## Additive-only batches: insert the same keys into N locales

The "add these 5 keys to 16 files, change nothing else" shape is *not* the rewrite path above —
never regenerate whole files. Anchor on a neighbouring key and insert:

1. Locate the anchor by **text, not line number** (`grep -n "instances.newCard" *.ts` — line
   numbers differ per file because some locales have extra comment/section lines).
2. Baseline the per-file key count first: `grep -cE "^\s*'" f.ts` (e.g. 81). After inserting
   five, the invariant is 86 for **every** file — cheap, and it catches a dropped or duplicated
   line instantly.
3. Patch with `old_string` = the full anchor line, `new_string` = anchor line + the new lines,
   in fixed order, no blank lines between them, matching existing indent + quote style.
   **When the new keys belong at the tail of the dict (new feature block), don't anchor on a
   neighbouring key at all** — anchor on the object close plus the export, which is ASCII-only,
   unique, and immune to both the fuzzy-Unicode trap and the glued-line trap:
   ```
   old_string = "};\n\nexport default ru;"      # confirm uniqueness first: grep -c '^};$' f.ts == 1
   new_string = <7 inserted lines> + "\n" + old_string
   ```
   One `patch` call per file, no hand-typed anchor in a non-Latin script. Used cleanly on a
   15-locale × 7-key batch (93-key invariant, `tsc` + `npm run build` green).
4. **Prove the diff is purely additive before moving to the next file.** `git diff --numstat`
   must read `5 0` per file and `git diff -U0 -- path | grep -E '^-[^-]'` must be empty. A `-`
   line means an existing key changed, which this class of task forbids. Run with
   `scripts/check-additive-diff.sh <paths…>`.
5. Verify with both layers: `tsc --noEmit` (syntax/type) **and** the app build
   (`npm run build`) — for an additive batch the build is the authoritative rung and it is
   cheap enough to always run.

### Pitfall: string-offset insertion glues the last inserted line onto the next key

The scripted batch (recommended above) has its own off-by-one. Splicing at a character offset
with a block that does **not** end in `\n` — the natural shape of
`text[:i] + "\n" + "\n".join(new_lines) + text[i:]` — is only safe when the anchor is followed
by a blank line. When the anchor is the last key before a section comment, the tail of the
insertion lands on the next key:

```
  'instances.languageDesc': '… --language',  'wizard.title': 'Opret instans',
```

Symptom in a 16-file batch: exactly the 4 locales whose anchor sat directly before a
`// section` comment came back `85` instead of `86`, and `tsc` reported
`TS1005: ',' expected` at that line. The other 12 were clean — so a green spot-check proves
nothing.

- Build by **line list, not character offset**: `lines = text.split("\n")`, find the anchor
  index, then `lines[idx+1:idx+1] = new_lines` (and `"\n".join(lines)`). No newline arithmetic,
  immune to blank-line placement.
- If you must splice on offsets, terminate the block: `+ "\n".join(new_lines) + "\n"`.
- Detect: the count invariant (`86`) plus `grep -nE "',\s{2,}'" f.ts` for a glued pair.
- Repair without re-running the batch: split the glued line at `  'wizard.` (or whatever key
  follows) into two lines, then re-count.

**Structural check beats the count alone.** Parse the 5 lines back out and assert they are
contiguous, in fixed order, and comma-terminated:

```python
import re
lines = open(p, encoding="utf-8").read().split("\n")
i = [n for n, l in enumerate(lines) if "'instances.newCard'" in l][0]
block = lines[i + 2:i + 7]          # +1 is the blank line sep
names = [(re.match(r"^\s*'(instances\.language\w*)':", b) or [None, None])[1] for b in block]
assert names == ["instances.languageAuto", "instances.language", "instances.languageCommon",
                 "instances.languageMore", "instances.languageDesc"]
```

Same for `grep -cE` inside a `for` loop over 16 files: prefer one invocation with many file
arguments (`grep -cE "^\\s*'" af.ts ar.ts …`) over a giant inline shell loop — the loop form
trips the agent's command-parser guard and gets blocked outright.

**The guard fires on bracket classes, not on loops per se.** `for f in …; do grep -cE
"^[[:space:]]*'" …; done` inline was rejected as `BLOCKED (hardline): command parser limit or
malformed executable payload` (POSIX `[[:space:]]` reads as a malformed payload). Two escapes,
both verified:

- one `grep` with all file arguments and a plain pattern (`grep -cE "^ *'" *.ts`), or
- `write_file` the loop to `/tmp/<name>.sh` and run `bash /tmp/<name>.sh`. This is the reliable
  form when you need per-file arithmetic (count + placeholder count + key-presence in one pass);
  the blocked command is saved to `~/.hermes/cache/blocked-scripts/` and shows this recovery.
  Delete the helper scripts when the batch is verified.

### Pitfall: fuzzy patching silently rewrites a non-ASCII anchor line

`patch` matches fuzzily, so it can "succeed" while rewriting your anchor line's *value* to the
`old_string` you typed. Real case: the anchor `'instances.newCard': 'नया इंस्टेंस'` (U+092F)
came back as `'नय़ा इंस्टैंस'` (U+092F U+093C, plus a different vowel sign) — a different word
to a native reader, and an edit to a key the task said not to touch. The mojibake is invisible
when eyeballing a diff, and Devanagari/Arabic/Thai combining marks make hand-typed `old_string`
almost never byte-exact.

- Detect: `git diff --numstat` says `5 1` instead of `5 0`.
- Recover byte-exactly — never retype the Unicode. Pull the original line out of git and splice
  it in with Python:
  ```python
  orig = subprocess.run(["git","-C",repo,"show",f"HEAD:{rel}"],
                        capture_output=True).stdout.decode()
  orig_line = next(l for l in orig.split("\n") if "instances.newCard" in l)
  cur = open(path, encoding="utf-8").read()
  cur_line = next(l for l in cur.split("\n") if "instances.newCard" in l)
  open(path, "w", encoding="utf-8").write(cur.replace(cur_line, orig_line, 1))
  ```
  A second hand-typed `patch` attempt at the fix will *also* fail to match (or corrupt further);
  go straight to bytes.
- Prevention: prefer an ASCII-safe anchor line where one exists, and always run step 4 on
  non-Latin-script files.

### Pitfall: hand-typed non-Latin `new_string` arrives corrupted

The other half of the same trap, and the one that actually bit in a 13-file batch: the anchor
was fine, but hand-typing the *translated lines* into `new_string` corrupted exactly one file.
The Thai insert picked up Han characters (`'ส่ง传给เกมผ่าน'` instead of `'ส่งต่อให้เกมผ่าน'`)
**and** lost its trailing comma, so `'instances.newCard': 'อินสแตนซ์ใหม่',` came back with no
`,` → `TS1005: ',' expected`. The other 12 files were clean: a ~1-in-13 corruption rate that no
diff review catches, because the string still looks "foreign" and the 86-key invariant still
passes.

- **Build the insertion with a script, not 13 hand-typed tool calls.** Keep a
  `{file: {key: translation}}` table and do
  `text.replace(anchor_line, anchor_line + "\n" + "\n".join(new_lines), 1)` in a loop. The
  translations then live in a file you can read back and diff; the `patch`/tool argument
  carries no Unicode for the model to garble. This is the single highest-value change for
  batches above ~5 files.
- If you do hand-type, run these over the **inserted** lines immediately:
  ```bash
  # 1. every inserted key line must still end with a comma (catches the dropped separator)
  grep -nE "^\s*'instances\.language[A-Za-z]*': '[^']*'$" f.ts        # expect no output
  # 2. no cross-script contamination — Han chars anywhere in a non-CJK locale
  python3 -c "import sys,re;[print(f'{f}:{i}:{l.strip()}') for f in sys.argv[1:] \
    for i,l in enumerate(open(f,encoding='utf-8'),1) if re.search(r'[\u4e00-\u9fff]',l)]" \
    th.ts ur.ts ru.ts uk.ts sr.ts sq.ts sk.ts sl.ts sw.ts tr.ts vi.ts
  ```
  (`grep -P` is not on stock macOS BSD grep — use the `python3` form above.)
- Also confirm the **anchor line still ends with `,`**: the classic failure is a patch that
  swallowed the separator while inserting after it.
- Recovery is one targeted `patch` on the single bad line, then re-run the count grep and the
  build. Do not re-run the batch, and do not retype the whole block.

## Verification ladder (do all four)

Run from the project root. Each rung is cheap; skipping a rung is how bad packs ship.

1. **Parity scan** — keys, count, order, placeholder sets, duplicates, empties, plus a
   `leak=` warning for values byte-identical to the base (pasted-English smell).
   `node scripts/verify-locales.mjs` (bundled with this skill; see below).
   **Run it again immediately before packaging**, not only after writing the batch — a key
   added to the base in between silently invalidates the earlier pass (see baseline drift).
2. **Type check the files themselves** — use the *project-local* compiler, not `npx`:
   ```bash
   ./node_modules/.bin/tsc --noEmit --strict --target ES2020 --module ESNext \
     --moduleResolution bundler src/i18n/locales/*.ts
   ```
   `npx tsc` in a project without a matching `typescript` resolution can print
   `This is not the tsc command you are looking for` — always prefer `./node_modules/.bin/tsc`.
   Add `--skipLibCheck` if `node_modules/@types/*` pulls in decoration errors about `Set`/`Map`/
   `Iterable`; those come from the repo's `lib` setting, not from your file. This rung is what
   catches an unescaped `'`.
3. **Runtime evaluation** — bundle each locale with esbuild and actually import it
   (`node scripts/verify-locales.mjs --runtime`). Regex scans can't see through escapes; a real
   `import` proves the object evaluates and the dicts are non-empty.
4. **Whole-app build** — `npm run build` (or `tsc && vite build`). Then the question that
   matters: **did the strings actually ship?**
   ```bash
   grep -c '<a distinctive translation>' dist/assets/*.js
   grep -rn "from '.*i18n" src | head
   ```
   A green build does **not** mean the locales are in the bundle. If nothing imports the i18n
   entry (`src/i18n/index.tsx` existing on disk is not an import), the eager glob is
   tree-shaken and the bundle contains zero translations. Report that as "not yet wired",
   not as a failure of the locale files — and say so explicitly rather than implying the
   translations are live.

## Multi-agent / parallel batches

- Locale files are per-file independent: safe to write in parallel, safe to hand to subagents.
- **Per-file independent only when the file lists don't overlap** — and in practice they do.
  Sibling subagents get overlapping assignments (two agents both handed `th.ts` / `ur.ts`), and
  `patch` answers with `_warning: … was modified by sibling subagent 'sa-…' but this agent never
  read it`. Treat that warning as "re-verify after my write", not as noise: two clean inserts of
  the same 5 keys produce a **duplicated key set** (91 matches) rather than a syntax error, and
  TypeScript happily accepts last-one-wins duplicates.
  ```bash
  grep -cE "^\s*'instances\.language(Auto|Common|More|Desc)?':" f.ts   # must be 5, not 10
  grep -cE "^\s*'" f.ts                                                # must be 86, not 91
  ```
  Run this **after** your own edit, not just against the pre-edit baseline — the baseline tells
  you nothing about what a sibling did in between.
- The same collision can **hard-fail** instead of warning:
  `Failed to read file: …/<f>.ts` with the sibling warning attached, `success: false`. It is a
  lock/settle race, not a permission problem: check the file is still at the pre-edit count
  (`grep -cE "^ *'" f.ts`, e.g. 86 not 93), then **re-issue the identical `patch`** — the retry
  succeeds and inserts exactly once. Do not rewrite the file wholesale to "force" it, and do not
  assume the earlier sibling write already added your keys.
  `patch`'s built-in lint line is NOT a signal here: it prints whole-repo
  `node_modules/@types/*` errors (`Cannot find name 'Set'`, `ReactNode circularly references
  itself`) on *every* edit in a `lib`-mismatched project and even times out at 30s. Judge only by
  `npx tsc --noEmit` / `npm run build` at the project root.
- **Do not edit the shared registry** (`index.tsx`, `LANG_META`, `SUPPORTED_LOCALES`) while
  other agents may be touching it — a conflict there is more expensive than the edit. Report
  the needed change instead, unless the task explicitly owns that file.
- Keep one shared term sheet across the batch (see
  `references/launcher-ui-term-sheet.md`) so parallel files don't translate `instance` three
  different ways inside the same language.

### Baseline drift: the base file moves while a batch is in flight (this shipped a defect)

Parity verified at **authoring** time proves nothing at **release** time. Real case (2026-10,
CraftCraft v0.2.0): three parallel subagent batches produced 24 locales, each a clean 81/81
against the then-current `en.ts`. Feature work then added 5 keys to `en.ts` **after** those
files were written. Result: 48 locales were 5 keys short, every authoring-time check was green,
and the gap **shipped inside the released dmg**.

- Missing keys do **not** crash or even look broken: `t()` falls back
  `dict[key] ?? base[key] ?? key`, so those 5 labels silently render in the base language.
  Only a native speaker notices. This is precisely why parity is a **release gate**, not a
  dev-time nicety.
- **Re-run the parity scan against the final base immediately before packaging** —
  `node scripts/verify-locales.mjs` — not just when the batch was written. "The base gained keys
  since the batch" invalidates every previously "verified" locale.
- When you add a key to the base yourself, grep the locales in the same breath:
  `grep -L "instances.language" src/i18n/locales/*.ts` lists exactly the files still missing it.
- The repair is the additive batch below (insert the keys, prove an `N 0` diff) — never
  regenerate whole files, and never "fix" the base.
- **Recurrence is the signal: make the gate executable, not remembered.** The same project
  shipped this drift **twice in one afternoon** — 5 keys missing across 48 locales (surfaced
  only when cutting v0.3.1), then 7 *more* keys missing across the same 48 (v0.3.2). Both times
  every manual parity check had been green at the moment it ran; the miss was that nobody re-ran
  it after the next feature landed in the base. A step you have to remember is not a gate.
  Wire it into the build so it fails loudly instead:
  ```jsonc
  // package.json — runs on every tauri/vite build, no memory required
  "scripts": { "prebuild": "node scripts/verify-locales.mjs" }
  ```
  or, more robustly, a unit test asserting `set(keys(base)) == set(keys(locale))` for **every**
  file `glob(locales/*.ts)` yields. Two extra patch releases for one class of miss is the price
  of a habit; the test costs nothing after the first write.

### Coverage: scan the whole directory, not your assignment list

A hand-assembled subagent assignment list is where files get lost. Real case: three batches
covered 45 of the 48 files — `ga`, `pt-BR`, `ro` were omitted (one task context even asserted
"ga.ts 不在本批", which was wrong), and only a full-directory scan caught them.

```bash
# every locale file vs the expected key count — no assignment list involved
for f in src/i18n/locales/*.ts; do
  n=$(grep -cE "^\s*'" "$f"); [ "$n" -eq 86 ] || echo "SHORT $f $n"
done
```

Derive the file list from the filesystem (`ls src/i18n/locales`), never from memory or from the
task text you wrote earlier, then reconcile: base keys × files present must satisfy the expected
count for **all** files — including the ones you think you didn't assign.

## Pitfalls

- Trusting the brief's key count. Count from the base file. (See Iron rule.)
- Verifying only "81 keys" per file and not *which* keys — a file can hit the count with 2
  missing + 2 invented. Compare sets and order.
- Checking placeholders on a sample instead of every key. One mistyped `{online}` in
  `{online}/{max} players` blanks the whole server row.
- **Grep the placeholder as `\{n\}` / `{n}`, never `({n})`.** A literal-paren pattern reports a
  false negative for any locale that writes native brackets around it — `zh-TW` ships
  `包含快照版（{n}）` with full-width `（）`, which is *correct* (the interpolator only matches
  `{n}`) but makes `grep -c "({n})"` return 0 and looks like a lost placeholder. Count with
  `grep -c "{n}"` / `grep -o "{[a-zA-Z]*}"`, and treat full-width parens as fine so long as the
  ASCII `{n}` itself survived.
- Treating `tsc` exit 0 as "translations work". It proves syntax, not content, and not shipping.
- Translating `Del`-style abbreviations as full words — they overflow the button.
- Letting `count_one` / `count_other` collapse to identical text **when the language genuinely
  inflects** (Slavic `few`/`many` arrive later; flag it, don't fake it). The converse matters
  more often in practice: for fa/ur/th/vi/id identical text is correct — see the plural section.
- `esbuild src/i18n/locales/ar.ts --loader=ts` errors with
  `"loader" without extension only applies when reading from stdin`. Drop the flag — the `.ts`
  extension already selects the loader; just use `--format=esm --outfile=/dev/null`.
- **Blame the right thing when a write is reported as a lint error.** `write_file` runs a
  project-wide type check and can report pre-existing failures from `node_modules/@types/*`
  (`Cannot find name 'Set'`, `react` `ReactNode circularly references itself`). Those appear on
  every file in the repo and say nothing about the locale you just wrote. Confirm with the
  project's own config (`./node_modules/.bin/tsc --noEmit -p tsconfig.json | grep i18n/locales`,
  expecting no output) and only then believe a syntax problem is yours.
- Auditing only "81 keys" per file rather than the placeholder sets — a batch-wide loop that
  compares `set(re.findall(r'\{(\w+)\}', v))` per key against the base is the cheap version that
  catches a swapped `{msg}`/`{tag}`.
- Widening scope: rewriting the base file, refactoring the i18n runtime, or converting dicts to
  nested objects. Batch translation is additive only.

## Bundled support files

- `scripts/verify-locales.mjs` — read-only parity checker; `--runtime` adds the esbuild
  bundle + node import pass. Reports key count, missing/extra/order, per-key placeholders,
  duplicates, empty values, and a non-fatal `leak=` list for values still identical to the
  base. Usage: `node scripts/verify-locales.mjs [localeDir] [baseFile]`.
- `scripts/check-additive-diff.sh` — proves a key-insertion batch only added lines
  (`git diff --numstat` must show `N 0`). Usage: `scripts/check-additive-diff.sh [paths…]`.
- `references/launcher-ui-term-sheet.md` — verified per-language wording for launcher vocabulary
  (instance, loader, Logs, memory, server, offline…) across zh-TW/ja/ko/de/fr/es/it/pt-BR.
- `references/rtl-and-asian-locale-term-sheet.md` — same, for **ar / he / fa / ur / hi / th / vi
  / id**: RTL registry pitfalls, native-script rules, plural-form traps, and the exact shipped
  vocabulary plus the grep loop that proves the native strings reached the bundle.
- `references/minecraft-language-keys.md` — the whole `instances.language*` 5-key block:
  verified values for ru/uk/sr/sk/sl/sv/sq/sw/th/tr/ur/vi/zh-TW, the local forms of
  Klingon / Quenya / toki pona per language, and two known defects to fix on contact.
- `references/game-language-key-terms.md` — verified `instances.language*` wording across 32
  locales in two batches (he/hi/hr/hu/id/is/it/ja/ko/lt/lv/mk/ms/nb/nl/pl, then
  af/ar/bg/ca/cs/cy/da/de/el/eo/es/et/fa/fi/fil/fr); reuse when extending the same keys to more
  languages so terminology stays consistent. The second batch's notes cover the Welsh
  apostrophe escapes, `Spilsprog`/`Spielsprache`/`Wika`/`Ieithoedd` word traps, and
  `Langue` vs `Langage`.
- `references/version-selector-keys.md` — the 7-key version-picker block
  (`wizard.selectVersion`, `wizard.releases`, `wizard.snapshots`, `wizard.oldBeta`,
  `wizard.oldAlpha`, `wizard.showSnapshots`, `instances.versionDesc`) as shipped in 15 locales
  (pt-BR/ro/ru/sk/sl/sq/sr/sv/sw/th/tr/uk/ur/vi/zh-TW), with official-Minecraft snapshot terms
  per language and the tail-anchor batch recipe (86 → 93 keys).
