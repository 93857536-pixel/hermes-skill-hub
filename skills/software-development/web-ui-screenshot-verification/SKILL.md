---
name: web-ui-screenshot-verification
description: "Use when 验证网页实际渲染效果;含 headless Chrome CDP 截图兜底(内置浏览器挂时)。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [web, browser, cdp, screenshot, spa, ui, verification, chrome, headless]
    category: software-development
---

# Web UI Screenshot Verification

## When to Use

- 你要确认「网页实际渲染出来的样子」而不只是 DOM 文本(布局、按钮位置、样式、双按钮是否并排、有没有白屏/报错)。
- 尤其 **SPA**:首屏有 boot spinner / session 恢复期,截图时机不当会拍到加载圈而非内容。
- 内置浏览器工具(`browser_exec` / browser-harness 守护进程)**起不来**时,需要一个不依赖它的兜底:自起 headless Chrome,用 CDP 直连截图。

## 决策阶梯(从省事到兜底)

1. **首选 `browser_exec`**(内置,带 js()/page_info()/screenshot)。先 `new_tab(url)`。
   - 若报 `daemon default didn't come up` → 看日志:
     `tail ~/.config/browser-harness/tmp/bu-default.log`
     - `chrome-not-running` = 没开 Chromium → 开一个 Chrome 再试。
     - `DevToolsActivePort not found` = 现有 Chrome 没开 remote debugging。
   - 能起来就直接用它,别绕远路。
2. **内置工具彻底起不来 → 自起 headless Chrome + CDP 直连**(下方「CDP 兜底配方」,已实测跑通)。

## CDP 兜底配方(实测可用,2026-09)

前提:目标页已在某端口可访问(如 `http://localhost:5173/login`,dev server 已起)。

### 步骤

```bash
# 1) 起一个带 remote-debugging 的 headless Chrome(全新 profile,避免锁冲突)
#    ⚠️ zsh 会把 --remote-allow-origins=* 的 * 当通配展开,必须加引号
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new --disable-gpu --no-first-run --no-default-browser-check \
  --remote-debugging-port=9333 --remote-allow-origins='*' \
  --user-data-dir=/tmp/lmh-cdp-<rand> --window-size=520,900 \
  "http://localhost:PORT/<page>"   &

# 2) 等 CDP 端点就绪
for i in $(seq 1 20); do curl -s http://localhost:9333/json/version && break; sleep 1; done
```

然后跑 `references/cdp-screenshot.py`(见下),它:
- 连 browser 级 CDP,找到/创建该 page target,连它**自己的** `webSocketDebuggerUrl`
- `Page.navigate` 后**轮询一个"就绪选择器"**(SPA 首屏 spinner 消失)再截图
- 输出 PNG 路径

```bash
python3 <skill_dir>/references/cdp-screenshot.py \
  --url http://localhost:5173/login \
  --ready-selector ".card" \
  --not-ready-selector ".boot" \
  --out /tmp/login-final.png --port 9333
```

### 关键坑(全是本次实测踩过)

- **SPA boot spinner**:React/Vite SPA 有 `loading` 阶段(如 `<div className="boot"><div className="spinner"/></div>`),**首屏截图常拍到 39KB 的加载圈而非内容**。必须轮询「就绪选择器出现 + 未就绪选择器消失」(本例:`.card` 出现、`.boot` 消失)再截图,内容截图会明显更大(本例 180KB vs 39KB)。
- **`--remote-allow-origins='*'` 漏了 → 403**:连 CDP websocket 会报 `Handshake status 403 ... Use --remote-allow-origins=*`。加引号别被 zsh 吞。
- **连「page target 自己的 webSocketDebuggerUrl」,别用 browser 级 flatten 路由**:browser 级 `Target.attachToTarget` + `flatten` 在 Python 手写 WS 帧时极易路由错/收不到响应(本次反复 NoneType)。直接 `/json` 拿 page target 的 `webSocketDebuggerUrl` 单独连最稳。
- **一次性 `--screenshot` 模式不够**:它不给你「等 SPA 就绪」的控制,SPA 场景一律走上面 CDP 交互流程。
- **依赖 `websocket-client`**:`python3 -c "import websocket"` 没有就 `pip3 install -q websocket-client`。
- **收尾清理**:`pkill -f "remote-debugging-port=9333"` + 删 `/tmp` 的 user-data-dir,别留僵尸 Chrome 占 profile 锁(下次起新实例会卡)。

### 验证截图(视觉模型读)

拿到 PNG 后用 `vision_analyze(image_url=<png>, question="底部有几个按钮/什么文字/是否白屏报错")` 确认实际渲染。

## 快速替代(不等 SPA 就绪、只要 DOM 文本)

- 纯文本够用:`curl -s http://localhost:PORT/ | ...` 或 headless `--dump-dom`(但 SPA 需 `--virtual-time-budget` 且仍可能停在加载态)。
- 只验证「构建产物里有这段 UI 文案」:`grep -o "登录中…" web/dist/assets/index-*.js` —— 无浏览器也能证明代码已编译进 bundle,比截图更省,适合「我改的按钮文本到底进了没」这类问题。

## 相关

- dogfood:系统性 web QA(本技能是它的「视觉证据获取」子能力,且覆盖内置浏览器工具挂掉时的兜底)。
- 若内置 `browser_exec` 正常,优先用它,别默认走 CDP。
