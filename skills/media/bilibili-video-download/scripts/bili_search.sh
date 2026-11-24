#!/usr/bin/env bash
# Bilibili video search: buvid3 cookie + search API, no login needed.
# Usage: bili_search.sh "<keyword>" [limit]   (default limit 15)
# Prints: bvid | title (tags stripped) | play count | uploader, sorted by click.
set -euo pipefail

KW="${1:?usage: bili_search.sh \"keyword\" [limit]}"
LIMIT="${2:-15}"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

cd "$(mktemp -d)"
trap 'rm -rf "$PWD"' EXIT

# 1. Fresh buvid3 cookie (search API rejects requests without one; no login required).
curl -s -c cookies.txt -L "https://www.bilibili.com" -H "User-Agent: $UA" > /dev/null
COOKIE="$(awk '$7=="buvid3"{print "buvid3="$8}' cookies.txt)"
[ -n "$COOKIE" ] || { echo "ERROR: could not obtain buvid3 cookie" >&2; exit 2; }

# 2. Search, sort by most-clicked.
ENC="$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))' "$KW")"
HTTP_BODY="$(curl -s --max-time 20 \
  "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=${ENC}&order=click" \
  -H "User-Agent: $UA" \
  -H "Referer: https://search.bilibili.com" \
  -H "Cookie: $COOKIE")"

echo "$HTTP_BODY" | python3 - "$LIMIT" <<'PY'
import json, re, sys
limit = int(sys.argv[1])
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except json.JSONDecodeError:
    sys.exit(print("ERROR: API returned non-JSON (likely rate-limited; wait a few seconds, refresh cookie, retry)", file=sys.stderr))
code, msg = d.get("code"), d.get("message")
if code != 0:
    sys.exit(f"ERROR: Bilibili search API code={code} ({msg})")
res = d.get("data", {}).get("result", [])
if not res:
    print("no results")
    sys.exit(0)
for v in res[:limit]:
    title = re.sub(r"<[^>]+>", "", v.get("title", ""))
    bvid, play, author = v.get("bvid"), v.get("play"), v.get("author")
    print(f"{bvid} | {title} | {play} play | UP:{author}")
PY
