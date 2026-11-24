#!/usr/bin/env bash
# Verify a locale patch batch is ADDITIVE ONLY (no existing key rewritten).
#
# The "add N keys to M locale files, change nothing else" task shape fails silently
# when the patch tool's fuzzy matcher rewrites a neighbouring non-ASCII anchor line.
# This catches it: every changed file must show `<additions> 0` in --numstat, and the
# diff must contain no removed/modified lines at all.
#
# Usage:
#   scripts/check-additive-diff.sh                         # default: src/i18n/locales
#   scripts/check-additive-diff.sh src/i18n/locales/ja.ts  # explicit paths
#   scripts/check-additive-diff.sh src/i18n/locales/*.ts
#
# Exit 0 = purely additive, 1 = something was removed/modified (inspect the output).

set -uo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "FAIL: not inside a git work tree" >&2
  exit 2
fi

if [ "$#" -eq 0 ]; then
  paths=(src/i18n/locales)
else
  paths=("$@")
fi

fail=0

# 1) Per-file numstat: deletions must be zero.
while IFS=$'\t' read -r add del file; do
  [ -z "${file:-}" ] && continue
  if [ "$del" != "0" ]; then
    printf 'FAIL %-40s +%s -%s (modified existing lines)\n' "$file" "$add" "$del"
    fail=1
  else
    printf 'ok   %-40s +%s\n' "$file" "$add"
  fi
done < <(git diff --numstat -- "${paths[@]}")

# 2) Any '-' line outside the '--- a/' header means a pre-existing line changed.
removed=$(git diff -U0 -- "${paths[@]}" | grep -E '^-[^-]' || true)
if [ -n "$removed" ]; then
  echo
  echo "FAIL: modified/removed lines detected:"
  printf '%s\n' "$removed" | head -50
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo
  echo "Recover byte-exactly instead of retyping Unicode, e.g.:"
  echo "  git show HEAD:<path> | grep '<anchor key>'   # original bytes"
  echo "  then splice in Python: cur.replace(cur_line, orig_line, 1)"
  exit 1
fi

echo
echo "PASS: additive-only diff (no existing locale key touched)"
