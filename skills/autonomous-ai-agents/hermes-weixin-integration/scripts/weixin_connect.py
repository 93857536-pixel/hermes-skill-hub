#!/usr/bin/env python3
"""微信(iLink Bot)扫码接入 Hermes —— 生成二维码 PNG + 扫码成功后自动写 WEIXIN_* 配置

用法:
    ~/.hermes/hermes-agent/venv/bin/python weixin_connect.py

行为:
  1. 调 gateway.platforms.weixin.qr_login() 取二维码
  2. 把二维码渲染成 PNG 存到 ~/Desktop/weixin_qr.png(用户用微信扫这张图)
  3. 扫码确认成功后, 把 WEIXIN_ACCOUNT_ID/TOKEN/BASE_URL/CDN/DM 策略写进 ~/.hermes/.env
  4. 之后手动执行: hermes gateway install --start-now --start-on-login
"""
import asyncio
import contextlib
import os
import pathlib
import re
import sys

HERMES_HOME = os.environ.get("HERMES_HOME", str(pathlib.Path.home() / ".hermes"))
REPO = pathlib.Path(HERMES_HOME) / "hermes-agent"
OUT = pathlib.Path.home() / "Desktop" / "weixin_qr.png"

# 死代理会让 aiohttp(trust_env=True)整体失败, 必须先清掉
for _k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)

sys.path.insert(0, str(REPO))
from gateway.platforms.weixin import qr_login  # noqa: E402

_state = {"done": False}


class Tee:
    """透传 stdout, 同时捕获 qr_login 打印的二维码 URL 并落盘成 PNG"""

    def __init__(self):
        self.buf = ""

    def write(self, s):
        sys.__stdout__.write(s)
        sys.__stdout__.flush()
        self.buf += s
        if not _state["done"]:
            m = re.search(r"https://[^\s]+", self.buf)
            if m:
                url = m.group(0).strip()
                try:
                    import qrcode

                    qrcode.make(url).save(OUT)
                    _state["done"] = True
                    print(f"\n[QR_IMAGE] {OUT}\n[QR_URL] {url}\n", flush=True)
                except Exception as e:  # noqa: BLE001
                    print(f"[QR_PNG_ERROR] {e}", flush=True)

    def flush(self):
        try:
            sys.__stdout__.flush()
        except Exception:
            pass


with contextlib.redirect_stdout(Tee()):
    creds = asyncio.run(qr_login(HERMES_HOME, timeout_seconds=600))

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
    if uid:  # 用扫码者 id 做 allowlist, 只有本人能对话
        pairs += [
            ("WEIXIN_DM_POLICY", "allowlist"),
            ("WEIXIN_ALLOW_ALL_USERS", "false"),
            ("WEIXIN_ALLOWED_USERS", uid),
            ("WEIXIN_HOME_CHANNEL", uid),
            ("WEIXIN_HOME_CHANNEL_NAME", "微信"),
        ]
    else:
        pairs += [("WEIXIN_DM_POLICY", "pairing"), ("WEIXIN_ALLOW_ALL_USERS", "false")]
    for k, v in pairs:
        if v:
            txt = setk(txt, k, v)
    env.write_text(txt)
    print("[ENV_WRITTEN] WEIXIN_* 已写入配置; 接着运行: hermes gateway install --start-now --start-on-login", flush=True)
