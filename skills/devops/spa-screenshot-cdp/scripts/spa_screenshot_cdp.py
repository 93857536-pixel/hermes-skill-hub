#!/usr/bin/env python3
"""Screenshot a React SPA via CDP, waiting for boot spinner to clear.

Usage:
  # 1) Start a remote-debugging headless Chrome (see SKILL.md), then:
  python3 spa_screenshot_cdp.py --url http://localhost:5173/login \
      --out /tmp/shot.png --port 9333 --boot-sel .boot --content-sel .card

Requires: websocket-client (pip install websocket-client / installed on this Mac).

Exit: 0 on success, 2 if the CDP endpoint is unreachable.
"""
import argparse, json, sys, time, urllib.request, base64
try:
    import websocket
except ImportError:
    sys.exit("need websocket-client: pip3 install websocket-client")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="target page URL (e.g. http://localhost:5173/login)")
    ap.add_argument("--out", default="/tmp/spa-shot.png")
    ap.add_argument("--port", type=int, default=9333)
    ap.add_argument("--boot-sel", default=".boot", help="CSS selector of the loading/boot spinner")
    ap.add_argument("--content-sel", default=".card", help="CSS selector of the real content container")
    ap.add_argument("--wait-max", type=float, default=40.0)
    ap.add_argument("--width", type=int, default=520)
    ap.add_argument("--height", type=int, default=900)
    a = ap.parse_args()

    base = f"http://localhost:{a.port}"
    try:
        ver = json.load(urllib.request.urlopen(f"{base}/json/version", timeout=5))
        bws = ver["webSocketDebuggerUrl"]
    except Exception as e:
        print(f"CDP endpoint not reachable at {base}/json/version: {e}", file=sys.stderr)
        print("Start Chrome first: see SKILL.md '推荐工作流' step 1.", file=sys.stderr)
        return 2

    # browser-level ws: discover/create the page target
    bws_sock = websocket.create_connection(bws, timeout=30)
    i = [0]

    def bcmd(method, params=None, timeout=30):
        i[0] += 1
        bws_sock.send(json.dumps({"id": i[0], "method": method, "params": params or {}}))
        dl = time.time() + timeout
        while time.time() < dl:
            try:
                j = json.loads(bws_sock.recv())
            except Exception:
                continue
            if j.get("id") == i[0]:
                return j
        return None

    targets = json.load(urllib.request.urlopen(f"{base}/json", timeout=10))
    page = next((t for t in targets if t.get("type") == "page" and a.url in t.get("url", "")), None)
    if not page:
        r = bcmd("Target.createTarget", {"url": a.url})
        page = {"id": r["result"]["targetId"], "webSocketDebuggerUrl": None}
        time.sleep(2)
        targets = json.load(urllib.request.urlopen(f"{base}/json", timeout=10))
        page = next((t for t in targets if t.get("type") == "page" and a.url in t.get("url", "")), None)
        if not page:
            print("could not find the page target", file=sys.stderr)
            return 2
    if not page.get("webSocketDebuggerUrl"):
        # target created via CDP has no standalone WS; use the entry from /json
        pass
    pws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=30)
    j = [0]

    def pcmd(method, params=None, timeout=35):
        j[0] += 1
        pws.send(json.dumps({"id": j[0], "method": method, "params": params or {}}))
        dl = time.time() + timeout
        while time.time() < dl:
            try:
                x = json.loads(pws.recv())
            except Exception:
                continue
            if x.get("id") == j[0]:
                return x
        return None

    pcmd("Page.enable")
    pcmd("Emulation.setDeviceMetricsOverride",
         {"width": a.width, "height": a.height, "deviceScaleFactor": 2, "mobile": False})
    pcmd("Page.navigate", {"url": a.url})

    # poll SPA state until boot spinner clears and content node appears
    state = "unknown"
    deadline = time.time() + a.wait_max
    while time.time() < deadline:
        time.sleep(0.5)
        expr = (f"document.querySelector({a.boot_sel!r}) ? 'booting' : "
                f"(document.querySelector({a.content_sel!r}) ? 'card' : 'other')")
        r = pcmd("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        state = r["result"]["result"]["value"] if r and "result" in r else "?"
        if state == "card":
            break
    print("page state:", state)
    time.sleep(0.5)

    res = pcmd("Page.captureScreenshot", {"format": "png"})
    if res and "result" in res:
        data = base64.b64decode(res["result"]["data"])
        with open(a.out, "wb") as f:
            f.write(data)
        print(f"screenshot bytes: {len(data)} -> {a.out}")
    else:
        print("screenshot failed:", json.dumps(res)[:200], file=sys.stderr)
        pws.close()
        bws_sock.close()
        return 2
    pws.close()
    bws_sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
