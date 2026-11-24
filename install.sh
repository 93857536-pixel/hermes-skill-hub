#!/usr/bin/env bash
# install.sh — install skills from this repo into your agent's skills directory.
# Usage:
#   ./install.sh                     # install all skills to ~/.hermes/skills
#   ./install.sh --target DIR        # install to a custom target dir
#   ./install.sh --category devops   # install only one category
#   ./install.sh --list              # list available categories
set -euo pipefail

TARGET="$HOME/.hermes/skills"
CATEGORY=""
LIST=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --category) CATEGORY="$2"; shift 2 ;;
    --list) LIST=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

SRC="$(cd "$(dirname "$0")" && pwd)/skills"

if [[ $LIST -eq 1 ]]; then
  echo "Available skill categories:"
  for d in "$SRC"/*/; do
    n=$(find "$d" -name SKILL.md | wc -l | tr -d ' ')
    printf "  %-28s %s skills\n" "$(basename "$d")" "$n"
  done
  exit 0
fi

if [[ ! -d "$SRC" ]]; then
  echo "error: ./skills not found next to install.sh — run from a repo checkout" >&2
  exit 1
fi

mkdir -p "$TARGET"

install_dir() {
  local src="$1"
  local base
  base="$(basename "$src")"
  if [[ -n "$CATEGORY" && "$base" != "$CATEGORY" ]]; then
    return 0
  fi
  # category with nested skills (e.g. devops/cloudflare-tunnel-ops)
  if find "$src" -maxdepth 1 -name SKILL.md | grep -q .; then
    # single-skill folder at category level (rare: e.g. sqlite/, planner/)
    rm -rf "${TARGET:?}/${base}"
    cp -R "$src" "$TARGET/$base"
    echo "installed: $base"
  else
    mkdir -p "$TARGET/$base"
    for sub in "$src"/*/; do
      rm -rf "${TARGET:?}/$base/$(basename "$sub")"
      cp -R "$sub" "$TARGET/$base/"
      echo "installed: $base/$(basename "$sub")"
    done
  fi
}

if [[ -n "$CATEGORY" && ! -d "$SRC/$CATEGORY" ]]; then
  echo "error: category '$CATEGORY' not found (try --list)" >&2
  exit 1
fi

for d in "$SRC"/*/; do
  install_dir "$d"
done

echo
echo "Done. Target: $TARGET"
echo "Restart your agent (or start a new session) to pick up the new skills."
