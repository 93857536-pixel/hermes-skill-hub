#!/usr/bin/env python3
"""免全量下载核验 GitHub Release 资产里的某个 ZIP 成员内容（慢链路 / 本机被封时用）。

场景：要证明「Release 里的那个二进制真的含本次修复」，但整包几十~上百 MB 而链路很慢
（实测 ~12KB/s，全量要 1 小时+）。本脚本走 Release asset API 端点拿 302 直链，
再用 HTTP range 只取 ZIP 尾部中央目录 + 目标成员，inflate 后按 UTF-16LE/UTF-8 搜文案。

要求：在**能连 api.github.com 与 release-assets.githubusercontent.com** 的机器上运行
（例如中继服务器）；本机 github.com 被封也没关系，本脚本不碰 github.com。

用法：
  python3 verify-release-artifact-member.py \
      --repo example-user/WeChatExporter --tag v2.19.1 \
      --asset WeChatExporter-Windows-x64.zip --member WeChatExporter.dll \
      --probe "已保存的密钥无法解密数据库" --probe "正在校验缓存密钥是否可用" \
      [--token-file /tmp/tok]      # 公共仓库可不带 token；私有仓库必须带

退出码：0 = 目标成员找到且全部 probe 命中；1 = 有 probe 未命中 / 出错。
"""
import argparse
import json
import os
import struct
import subprocess
import sys
import tempfile
import zlib


def curl(args, timeout=600):
    cp = subprocess.run(["curl", "-sS"] + args, capture_output=True, timeout=timeout)
    if cp.returncode != 0 and cp.stderr:
        sys.stderr.write("curl stderr: " + cp.stderr.decode("utf-8", "replace")[:300] + "\n")
    return cp


def api_json(url, token, extra_headers=None, out=None):
    out = out or os.path.join(tempfile.gettempdir(), "gh_api.json")
    hdrs = ["-H", "User-Agent: release-verify", "-H", "Accept: application/vnd.github+json"]
    if token:
        hdrs += ["-H", f"Authorization: Bearer {token}"]
    for h in (extra_headers or []):
        hdrs += ["-H", h]
    curl(["-m", "60", "-o", out] + hdrs + [url])
    with open(out, "rb") as f:
        return json.loads(f.read().decode("utf-8", "replace"))


def head_headers(url, token):
    out = os.path.join(tempfile.gettempdir(), "gh_head.txt")
    hdrs = ["-H", "User-Agent: release-verify", "-H", "Accept: application/octet-stream"]
    if token:
        hdrs += ["-H", f"Authorization: Bearer {token}"]
    curl(["-I", "-m", "40", "-D", out, "-o", os.devnull] + hdrs + [url])
    txt = open(out, encoding="utf-8", errors="replace").read()
    headers = {}
    for line in txt.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return headers


def fetch_range(url, start, end, token, dest):
    """返回实际取到的字节数（链路慢时会短读，调用方可重试）。"""
    hdrs = ["-H", "User-Agent: release-verify", "-H", "Accept: application/octet-stream"]
    if token:
        hdrs += ["-H", f"Authorization: Bearer {token}"]
    curl(["-sSL", "--max-redirs", "6", "-m", "900", "-r", f"{start}-{end}", "-o", dest] + hdrs + [url])
    return os.path.getsize(dest) if os.path.exists(dest) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--asset", required=True, help="资产文件名（Release 资产名）")
    ap.add_argument("--member", required=True, help="ZIP 内成员名/后缀（如 WeChatExporter.dll）")
    ap.add_argument("--probe", action="append", default=[], help="期望出现的字符串，可重复")
    ap.add_argument("--probe-utf16", action="store_true", default=True,
                    help="按 UTF-16LE 搜（.NET/C# 默认；可用 --no-probe-utf16 关掉）")
    ap.add_argument("--no-probe-utf16", dest="probe_utf16", action="store_false")
    ap.add_argument("--token-file", help="含 GitHub token 的文件（私有仓库必需）")
    args = ap.parse_args()

    token = ""
    if args.token_file and os.path.exists(args.token_file):
        token = open(args.token_file, encoding="utf-8").read().strip()

    tmp = tempfile.mkdtemp(prefix="relverify-")
    release = api_json(f"https://api.github.com/repos/{args.repo}/releases/tags/{args.tag}", token)
    asset = next((a for a in release.get("assets", []) if a["name"] == args.asset), None)
    if not asset:
        print("FAIL: 资产不存在:", args.asset)
        print("  可用资产:", [a["name"] for a in release.get("assets", [])])
        return 1
    print(f"asset={asset['name']} size={asset['size']} api_digest={asset.get('digest')}")

    hdrs = ["-H", "User-Agent: release-verify", "-H", "Accept: application/octet-stream"]
    if token:
        hdrs += ["-H", f"Authorization: Bearer {token}"]
    hout = os.path.join(tmp, "h.txt")
    curl(["-I", "-m", "40", "-D", hout, "-o", os.devnull] + hdrs +
         [f"https://api.github.com/repos/{args.repo}/releases/assets/{asset['id']}"])
    loc = None
    for line in open(hout, encoding="utf-8", errors="replace").read().splitlines():
        if line.lower().startswith("location:"):
            loc = line.split(":", 1)[1].strip()
    if not loc:
        print("FAIL: 未拿到资产直链（302 Location）")
        return 1
    total = head_headers(loc, token).get("content-length")
    total = int(total) if total and total.isdigit() else asset["size"]
    print(f"asset url ok, content_length={total}")

    tail_len = 262144
    start = max(0, total - tail_len)
    tail_path = os.path.join(tmp, "tail.bin")
    got = fetch_range(loc, start, total - 1, token, tail_path)
    tail = open(tail_path, "rb").read()
    print(f"tail fetched {got} bytes")
    i = tail.rfind(b"PK\x05\x06")
    if i < 0:
        print("FAIL: 尾部未见 EOCD（资产不是 ZIP 或尾块不完整）")
        return 1
    cd_size, cd_off = struct.unpack("<II", tail[i + 12:i + 20])

    pos = cd_off - start
    entries = {}
    while pos < len(tail) - 46 and tail[pos:pos + 4] == b"PK\x01\x02":
        (_sig, _vmb, _vn, _flags, comp_type, _mt, _md, _crc, comp_size, uncomp_size,
         nlen, elen, clen, _disk, _iattr, _eattr, lho) = struct.unpack("<4s6H3I5H2I", tail[pos:pos + 46])
        name = tail[pos + 46:pos + 46 + nlen].decode("utf-8", "replace")
        entries[name] = (comp_type, comp_size, uncomp_size, lho)
        pos += 46 + nlen + elen + clen
    print(f"central dir entries={len(entries)} (cd_size={cd_size})")

    member = next((n for n in entries if n == args.member), None) or \
             next((n for n in entries if n.lower().endswith(args.member.lower())), None)
    if not member:
        print("FAIL: ZIP 内未见成员:", args.member)
        return 1
    comp_type, comp_size, uncomp_size, lho = entries[member]
    print(f"member={member} comp_type={comp_type} comp_size={comp_size} uncomp_size={uncomp_size}")

    lh_path = os.path.join(tmp, "lh.bin")
    fetch_range(loc, lho, lho + 63, token, lh_path)
    lh = open(lh_path, "rb").read()
    nlen, elen = struct.unpack("<HH", lh[26:30])
    data_off = lho + 30 + nlen + elen

    data_path = os.path.join(tmp, "member.bin")
    got = fetch_range(loc, data_off, data_off + comp_size - 1, token, data_path)
    raw = open(data_path, "rb").read()
    print(f"member bytes fetched={got} (expected {comp_size})")
    if got != comp_size:
        print("WARN: 短读/超时，重跑一次通常可补齐（链路抖动）")
    data = zlib.decompress(raw, -15) if comp_type == 8 else raw
    print(f"inflate ok: {len(data)} bytes (expected {uncomp_size})")

    failed = 0
    for probe in args.probe:
        hit = probe.encode("utf-8") in data
        if args.probe_utf16 and not hit:
            hit = probe.encode("utf-16-le") in data
        print(("HIT  " if hit else "MISS ") + probe)
        if not hit:
            failed += 1
    print("RESULT:", "PASS" if (args.probe and failed == 0) else ("NO_PROBE" if not args.probe else "FAIL"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
