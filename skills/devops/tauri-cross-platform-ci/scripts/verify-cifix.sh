#!/bin/bash
# Ad-hoc local verification pattern for CI changes (write to system temp dir,
# delete after run). Adapt the -p package names to the repo's crates.
# Key lesson: this box has NO pyyaml — use ruby for YAML validity checks.
set -u
cd /path/to/repo
pass=0; fail=0
ok(){ echo "[PASS] $1"; pass=$((pass+1)); }
bad(){ echo "[FAIL] $1"; fail=$((fail+1)); }

# 1. workflow YAMLs valid (ruby stdlib; pyyaml usually missing on macOS)
for f in .github/workflows/ci.yml .github/workflows/release.yml; do
  ruby -ryaml -e "YAML.load_file('$f')" 2>/dev/null && ok "$f valid YAML" || bad "$f invalid YAML"
done

# 2. core job narrowed to core+cli, no --workspace leftovers
grep -q "clippy -p migrator-core -p hermes-migrator-cli -- -D warnings" .github/workflows/ci.yml \
  && ok "ci.yml core narrowed" || bad "ci.yml not narrowed"
grep -qE "cargo (clippy|test) --workspace" .github/workflows/ci.yml \
  && bad "ci.yml still has --workspace" || ok "no --workspace left"

# 3. tauri.conf.json valid JSON + every bundle icon exists on disk
python3 - <<'EOF' && ok "tauri.conf.json + icons on disk" || bad "tauri icons missing"
import json, os
cfg = json.load(open("gui/src-tauri/tauri.conf.json"))
icons = cfg["bundle"]["icon"]
assert "icons/icon.ico" in icons
for p in icons:
    assert os.path.exists(os.path.join("gui/src-tauri", p)), p
EOF

# 4. icon.ico genuine multi-size
python3 - <<'EOF' && ok "icon.ico 7 sizes" || bad "icon.ico wrong sizes"
from PIL import Image
s = Image.open("gui/src-tauri/icons/icon.ico").info.get("sizes")
assert s and len(s) == 7 and (256, 256) in s, s
EOF

# 5. release.yml idempotent + empty-artifact guard
grep -q 'gh release view "${{ github.ref_name }}"' .github/workflows/release.yml \
  && grep -q 'refusing to publish an empty release' .github/workflows/release.yml \
  && ok "release.yml guards" || bad "release.yml guards missing"

# 6. working tree clean (icons added?)
[ -z "$(git status --porcelain)" ] && ok "clean tree" || bad "dirty: $(git status --porcelain)"

echo "AD-HOC VERIFICATION: $pass passed, $fail failed"
exit $fail
