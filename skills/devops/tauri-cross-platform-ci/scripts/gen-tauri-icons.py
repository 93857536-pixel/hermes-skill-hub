#!/usr/bin/env python3
"""Generate Tauri per-platform icons from a single 1024x1024 RGBA PNG.

Produces .ico (7 sizes) for the Windows runner, and emits the sips/iconutil
commands for .icns on macOS. Run from the repo root:

    python3 scripts/gen-tauri-icons.py gui/src-tauri/icons/icon.png

macOS .icns step (requires sips + iconutil, ship the .icns into the repo and
git-add it — CI runners only see committed files):

    mkdir -p /tmp/icon.iconset     # dir MUST end in .iconset (iconutil rejects others)
    for s in 16 32 64 128 256 512 1024; do
        sips -z $s $s icon.png --out /tmp/icon.iconset/icon_${s}x${s}.png
    done
    # @2x variants: icon_16x16@2x.png (32px), icon_32x32@2x.png (64px),
    # icon_128x128@2x.png (256px), icon_256x256@2x.png (512px),
    # icon_512x512@2x.png (1024px)
    iconutil -c icns /tmp/icon.iconset -o icons/icon.icns

Pitfalls:
- tauri.conf.json bundle.icon must list all three: icons/icon.png,
  icons/icon.ico, icons/icon.icns — Windows tauri-build hard-fails without .ico.
- PIL multi-size .ico: im.save("icon.ico", sizes=[(16,16),(24,24),(32,32),
  (48,48),(64,64),(128,128),(256,256)])
- git add the generated files; CI checks out the repo, it cannot regenerate.
"""
import sys
from PIL import Image

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "gui/src-tauri/icons/icon.png"
    im = Image.open(src)
    assert im.size == (1024, 1024) and im.mode == "RGBA", (im.size, im.mode)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    out = src.rsplit(".", 1)[0] + ".ico"
    im.save(out, sizes=sizes)
    # verify: re-open and list embedded sizes
    back = Image.open(out)
    print(f"{out}: sizes={sorted(back.info.get('sizes', []))}")

if __name__ == "__main__":
    main()
