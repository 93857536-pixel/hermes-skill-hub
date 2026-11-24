#!/usr/bin/env python3
"""
CDP 截图兜底脚本(不依赖 browser_exec / browser-harness)。

前提:
  - 一个带 --remote-debugging-port=<port> 的 Chrome 已在跑(见 SKILL.md 启动命令)
  - 依赖 websocket-client:`pip3 install -q websocket-client`

用法:
  python3 cdp-screenshot.py \
    --url http://localhost:5173/login \
    --ready-selector ".card" \
    --not-ready-selector ".boot" \
    --out /tmp/login-final.png --port 9333

逻辑:
  1. 连 browser 级 CDP(/json/version 的 webSocketDebuggerUrl)
  2. 在 /json 里找该 URL 的 page target;没有就 Target.createTarget
  3. 连该 page target **自己的** webSocketDebuggerUrl(不用 browser 级 flatten 路由,更稳)
  4. Page.navigate 后轮询:就绪选择器出现 AND 未就绪选择器消失,才截图
     (解决 SPA boot spinner 拍到加载圈的问题)
  5. Page.captureScreenshot → PNG
"""
import argparse, json, time, base64, urllib.request
import websocket


def get_targets(port):
    return json.load(urllib.request.urlopen(f"http://localhost:{port}/json", timeout=10))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--ready-selector", default="body", help="就绪选择器(出现才算渲染完)")
    ap.add_argument("--not-ready-selector", default="", help="未就绪选择器(消失才算渲染完)")
    ap.add_argument("--out", default="/tmp/cdp-shot.png")
    ap.add_argument("--port", type=int, default=9333)
    ap.add_argument("--width", type=int, default=520)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--scale", type=float, default=2)
    ap.add_argument("--wait-max", type=float, default=60, help="轮询就绪的最大秒数")
    a = ap.parse_args()

    # 1) 找 / 建 page target
    page = next((t for t in get_targets(a.port)
                 if t.get("type") == "page" and a.url in t.get("url", "")), None)
    if not page:
        ver = json.load(urllib.request.urlopen(
            f"http://localhost:{a.port}/json/version", timeout=10))
        bws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=30)
        bws.send(json.dumps({"id": 1, "method": "Target.createTarget",
                             "params": {"url": a.url}}))
        while True:
            j = json.loads(bws.recv())
            if j.get("id") == 1:
                break
        bws.close()
        time.sleep(2)
        page = next((t for t in get_targets(a.port)
                     if t.get("type") == "page" and a.url in t.get("url", "")), None)
    if not page:
        raise SystemExit("fATAL: no page target for " + a.url)

    print("target:", page["url"])

    # 2) 连 page target 自己的 CDP 端点(最稳,避开 flatten 路由)
    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=30)
    seq = [0]

    def cmd(m, p=None, timeout=30):
        seq[0] += 1
        ws.send(json.dumps({"id": seq[0], "method": m, "params": p or {}}))
        dl = time.time() + timeout
        while time.time() < dl:
            try:
                j = json.loads(ws.recv())
            except Exception:
                continue
            if j.get("id") == seq[0]:
                return j
        return None

    cmd("Page.enable")
    cmd("Emulation.setDeviceMetricsOverride",
        {"width": a.width, "height": a.height,
         "deviceScaleFactor": a.scale, "mobile": False})
    cmd("Page.navigate", {"url": a.url})

    # 3) 轮询就绪(就绪选择器出现 + 未就绪选择器消失)
    expr = (f"(({a.ready_selector!r}) ? (document.querySelector({a.ready_selector!r}) ? 1 : 0) : 0)"
            f" + ({('!document.querySelector(' + repr(a.not_ready_selector)) + ' * 0' if False else '')})")
    # 用简单双查询,避免拼接错误:
    expr = (
        f"((document.querySelector({a.ready_selector!r}) ? 1 : 0)"
        f" - (document.querySelector({a.not_ready_selector!r}) ? 1 : 0))"
    ) if a.not_ready_selector else (
        f"(document.querySelector({a.ready_selector!r}) ? 1 : 0)"
    )
    state = "?"
    deadline = time.time() + a.wait_max
    while time.time() < deadline:
        time.sleep(0.5)
        r = cmd("Runtime.evaluate",
                {"expression": expr, "returnByValue": True})
        if r and "result" in r and "result" in r["result"]:
            v = r["result"]["result"].get("value")
            state = "READY" if (v is True or v == 1) else f"pending({v})"
            if state == "READY":
                break
    print("ready state:", state)
    time.sleep(0.5)

    # 4) 截图
    res = cmd("Page.captureScreenshot", {"format": "png"}, timeout=30)
    if res and "result" in res and "data" in res["result"]:
        data = base64.b64decode(res["result"]["data"])
        open(a.out, "wb").write(data)
        print("OK:", a.out, len(data), "bytes")
    else:
        print("FAIL:", json.dumps(res)[:300])
    ws.close()


if __name__ == "__main__":
    main()
