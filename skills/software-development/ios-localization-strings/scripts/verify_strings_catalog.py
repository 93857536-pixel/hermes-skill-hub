#!/usr/bin/env python3
"""Verify a localized .strings catalog against its source-language catalog.

READ-ONLY: never writes to or reformats the catalogs.

Usage:
    python3 verify_strings_catalog.py SOURCE.strings TARGET.strings [--no-comments]
    python3 verify_strings_catalog.py SOURCE.strings TARGET.strings --siblings a b c

Exit code 0 = all hard checks passed (warnings allowed), 1 = at least one FAIL.

Design note: the only thing this script fails on is a *structural* defect. Values that
are byte-identical to the source are reported as WARNINGS, because brand/technical terms
and shared-script words legitimately match — a human/agent must adjudicate those. Do not
"fix" a FAIL by rewriting a correct translation; first suspect this checker. Validate it
by running it against the reference catalog itself as TARGET (it must come back clean),
and read the failing *values* before touching the artifact.
"""
import argparse
import re
import shutil
import subprocess
import sys
from collections import Counter

# Whole-line grammar: "key" = "value";  (handles \" inside either side)
ENTRY = re.compile(r'^"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;\s*$')
PLACEHOLDER = re.compile(r"%[@l0-9]+")
KANA = re.compile(r"[\u3040-\u30ff]")          # presence of kana => Japanese text
COMMENT = re.compile(r"^\s*(/\*|//)")

# Codepoints that exist in Simplified Chinese but NOT in Japanese orthography.
# Shared Han characters (定 免 本 限 面 名 通 制 照 号 除 私 ...) are deliberately
# EXCLUDED: they are valid Japanese kanji, and flagging them buries the real signal.
SIMPLIFIED_ONLY = set(
    "们这确删设备页选择换缓权项计检测试补仓导压缩复联蓝网验证据时间问题单击扫态极效"
    "无为层显视觉动纸忆签认标关图应书说读华语译让类经过还进运远点结级约红绿门开长转"
    "输载录库户买单请谢对错边连达织归处传递记览查阅"
)


def parse(path, skip_comments=False):
    """Return (keys, values, bad_lines). Order is preserved."""
    keys, vals, bad = [], [], []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if skip_comments and COMMENT.match(line):
                continue
            m = ENTRY.match(line)
            if m:
                keys.append(m.group(1))
                vals.append(m.group(2))
            else:
                bad.append((lineno, line[:100]))
    return keys, vals, bad


def lint(path):
    if not shutil.which("plutil"):
        return None  # non-Apple host: skip silently
    r = subprocess.run(["plutil", "-lint", "-s", path], capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("target")
    ap.add_argument("--no-comments", action="store_true",
                    help="fail if the TARGET file contains /* or // comments")
    ap.add_argument("--siblings", nargs="*", default=[],
                    help="extra catalogs to compare key counts against")
    args = ap.parse_args()

    sk, sv, sbad = parse(args.source, skip_comments=True)   # sources may hold comments
    tk, tv, tbad = parse(args.target)
    fails, warns = [], []

    def chk(ok, msg):
        print(("PASS  " if ok else "FAIL  ") + msg)
        if not ok:
            fails.append(msg)

    def warn(msg):
        print("WARN  " + msg)
        warns.append(msg)

    print("== %s -> %s ==" % (args.source, args.target))

    # 1. grammar. Strict only for the TARGET; sources legitimately carry comments.
    chk(not tbad, "target: every non-empty line matches \"key\" = \"value\";")
    for lineno, line in tbad[:10]:
        print("        line %d: %s" % (lineno, line))
    chk(not sbad, "source: all entry lines parse (comments excluded)")

    # 2. keys: same set, same order, same count.
    chk(len(tk) == len(sk), "key count equal (source=%d target=%d)" % (len(sk), len(tk)))
    chk(tk == sk, "key sequence identical to source (same keys, same order)")
    if tk != sk:
        for i, (a, b) in enumerate(zip(tk, sk)):
            if a != b:
                print("        first divergence at index %d: target=%r source=%r" % (i, a, b))
                break
        extra = set(tk) - set(sk)
        missing = set(sk) - set(tk)
        if extra:
            print("        keys only in target: %s" % sorted(extra)[:10])
        if missing:
            print("        keys only in source: %s" % sorted(missing)[:10])

    # 3. placeholders: per-key multiset, and file-wide.
    mismatch = []
    for i, k in enumerate(tk):
        if k in sk:
            a = Counter(PLACEHOLDER.findall(sv[sk.index(k)]))
            b = Counter(PLACEHOLDER.findall(tv[i]))
            if a != b:
                mismatch.append((k, dict(a), dict(b)))
    chk(not mismatch, "per-key placeholder multiset preserved (mismatches=%d)" % len(mismatch))
    for k, a, b in mismatch[:10]:
        print("        %s: source=%s target=%s" % (k, a, b))
    chk(Counter(x for v in sv for x in PLACEHOLDER.findall(v))
        == Counter(x for v in tv for x in PLACEHOLDER.findall(v)),
        "file-wide placeholder multiset preserved")

    # 4. output-file hygiene.
    raw = open(args.target, encoding="utf-8").read()
    if args.no_comments:
        chk(not any(COMMENT.match(l) for l in raw.splitlines()),
            "target: no comment lines (plain catalog)")
    chk(raw.count("\n") == len(tk),
        "target: one entry per line, no blank lines (%d lines / %d entries)"
        % (raw.count("\n"), len(tk)))
    chk(all("\n" not in v.replace("\\n", "") for v in tv),
        "no raw newline inside any value (newlines must be escaped \\n)")

    # 5. translation coverage. WARN only — shared-script terms are legitimate.
    unchanged = [k for i, k in enumerate(tk) if k in sk and tv[i] == sv[sk.index(k)]]
    if unchanged:
        warn("%d value(s) identical to source — confirm each is a brand/technical or "
             "shared-script term, not a missed translation" % len(unchanged))
        for k in unchanged[:40]:
            v = tv[tk.index(k)]
            # kana present => genuinely target-language text; bare Han => shared-kanji
            # compound, which needs a judgement call (e.g. 保存/通知 are valid Japanese).
            tag = "target-language text (verify!)" if KANA.search(v) else "shared-script/brand"
            print("        [%s] %s = %s" % (tag, k, v))
    contam = {k: "".join(sorted(set(tv[i]) & SIMPLIFIED_ONLY))
              for i, k in enumerate(tk) if set(tv[i]) & SIMPLIFIED_ONLY}
    chk(not contam, "no Simplified-only characters in target values (hits=%d)" % len(contam))
    for k, chars in list(contam.items())[:10]:
        print("        %s: %s" % (k, chars))

    # 6. platform lint.
    res = lint(args.target)
    if res is None:
        print("SKIP  plutil not available on this host")
    else:
        ok, detail = res
        chk(ok, "plutil -lint target => %s" % ("OK" if ok else detail))
    for s in args.siblings:
        try:
            k, _, _ = parse(s)
            print("INFO  sibling %s: %d keys" % (s, len(k)))
        except OSError as exc:
            print("INFO  sibling %s: unreadable (%s)" % (s, exc))

    print("\nRESULT: %s (%d FAIL, %d WARN)"
          % ("ALL CHECKS PASSED" if not fails else "%d FAILURE(S)" % len(fails),
             len(fails), len(warns)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
