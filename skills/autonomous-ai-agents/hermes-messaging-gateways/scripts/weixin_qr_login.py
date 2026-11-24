#!/usr/bin/env python3
"""个人微信 (腾讯 iLink Bot) 扫码接入 Hermes —— 生成桌面二维码 PNG + 扫码成功后自动写 WEIXIN_* 到 .env

用法:
    ~/.hermes/hermes-agent/venv/bin/python weixin_qr_login.py
    # 建议后台跑并 tee 日志,再从日志抓 [QR_IMAGE] / [QR_URL] 报给用户去扫:
    #   后台启动后 sleep ~12s;grep -a -E "QR_IMAGE|QR_URL|CREDS|FATAL" <log>

为什么需要它: `hermes gateway setup` 的向导是把二维码画在它自己的终端里(ASCII),用户不在
终端前就没法扫。本脚本复用同一个 `qr_login()`,额外把二维码存成 PNG 丢到桌面,用户双击即可扫。

前提: hermes venv 里已装 aiohttp / cryptography / qrcode:
    ~/.hermes/hermes-agent/venv/bin/python -m pip install qrcode

改这个常量即可复用到别的机器/用户。
"""
import asyncio
import contextlib
import os
import pathlib
import re
import sys

HERMES_HOME = str(pathlib.Path.home() / ".hermes")
REPO = str(pathlib.Path(HERMES_HOME) / "hermes-agent")   # hermes 源码目录(内含 gateway 包)
OUT_PNG = pathlib.Path.home() / "Desktop" / "weixin_qr.png"
TIMEOUT_SECONDS = 600

# 死代理会让 aiohttp(trust_env=True) 连不出去,先清干净
for _k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)

sys.path.insert(0, REPO)
from gateway.platforms.weixin import qr_login  # noqa: E402

state = {"png_done": False}


class Tee:
    """边转发 stdout,边抓 qr_login 打出来的 liteapp URL 生成 PNG。"""

    def __init__(self):
        self.buf = ""

    def write(self, s):
        sys.__stdout__.write(s)
        sys.__stdout__.flush()
        self.buf += s
        if not state["png_done"]:
            m = re.search(r"https://[^\s]+", self.buf)
            if m:
                url = m.group(0).strip()
                try:
                    import qrcode

                    qrcode.make(url).save(OUT_PNG)
                    state["png_done"] = True
                    print(f"\n[QR_IMAGE] {OUT_PNG}\n[QR_URL] {url}\n", flush=True)
                except Exception as exc:  # noqa: BLE001
                    print(f"[QR_PNG_ERROR] {exc}", flush=True)

    def flush(self):
        try:
            sys.__stdout__.flush()
        except Exception:  # noqa: BLE001
            pass


try:
    with contextlib.redirect_stdout(Tee()):
        creds = asyncio.run(qr_login(HERMES_HOME, timeout_seconds=TIMEOUT_SECONDS))
except Exception as exc:  # noqa: BLE001
    print(f"[FATAL] {type(exc).__name__}: {exc}", flush=True)
    creds = None

print(f"[CREDS] {creds}", flush=True)

if creds:
    env = pathlib.Path(HERMES_HOME) / ".env"
    txt = env.read_text()

    def setk(t, k, v):
        if re.search(rf"^{k}=.*$", t, flags=re.M):
            return re.sub(rf"^{k}=.*$", f"{k}={v}", t, flags=re.M)
        return t.rstrip("\n") + f"\n{k}={v}\n"

    pairs = [
        ("WEIXIN_ACCOUNT_ID", creds.get("account_id", "")),
        ("WEIXIN_TOKEN", creds.get("token", "")),
        ("WEIXIN_BASE_URL", creds.get("base_url", "")),
        ("WEIXIN_CDN_BASE_URL", "https://novac2c.cdn.weixin.qq.com/c2c"),
    ]
    uid = creds.get("user_id", "")
    if uid:  # 只允许扫码者本人私聊(最安全);没有 user_id 就退回 pairing 审批
        pairs += [
            ("WEIXIN_DM_POLICY", "allowlist"),
            ("WEIXIN_ALLOW_ALL_USERS", "false"),
            ("WEIXIN_ALLOWED_USERS", uid),
        ]
    else:
        pairs += [("WEIXIN_DM_POLICY", "pairing"), ("WEIXIN_ALLOW_ALL_USERS", "false")]
    for k, v in pairs:
        if v:
            txt = setk(txt, k, v)
    env.write_text(txt)
    print("[ENV_WRITTEN] WEIXIN_* 已写入 ~/.hermes/.env;接着跑 hermes gateway start 即可", flush=True)
