---
name: spa-screenshot-cdp
description: "Screenshot a React SPA headlessly when browser-use is down."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [chrome, cdp, headless, screenshot, react, spa, dev-server]
    category: devops
---

# SPA 无头截图/验证(Chrome DevTools 协议)

## When to Use

- 需要验证 Web SPA(React/Vite dev server)某页面的**渲染后** UI(按钮、文案、布局)
- browser-use 守护进程连不上(日志 `chrome-not-running` / `DevToolsActivePort not found`),或 computer_use 的 typed-browser rung 被拒
- 一次性 headless 截图(`--dump-dom` / `--screenshot`)卡住,或截到的是 boot 加载态(spinner)而非真实页面
- 不需要完整交互,只要「等页面真正渲染完 → 截图/DOM 断言」

## 核心结论(先读)

1. **一次性 headless Chrome 在这台 Mac 上会挂**:带 `--virtual-time-budget` 或 `--screenshot` 的 headless 进程经常**截图文件已写出但进程不退出**(卡 60s+/120s 超时)。不要依赖它做可重复验证。
2. **SPA 首屏有 loading 态**:React 应用首屏先渲染 boot spinner(会话恢复/路由加载),过早截图只拿到 spinner。**必须轮询页面状态**(`document.querySelector('.boot') ? 'booting' : 'card'`)直到内容节点出现再截图。
3. **CDP 连接需要 `--remote-allow-origins`**:Chrome 111+ 默认拒绝来自 `http://localhost:<port>` 的 WebSocket 连接,报 `403 ... Use --remote-allow-origins`。必须起 Chrome 时加该 flag。
4. **zsh 通配展开坑**:`--remote-allow-origins=*` 在 zsh/terminal 里 `*` 会被 glob 展开报 `no matches found`,必须加引号 `--remote-allow-origins='*'`。

## 推荐工作流(CDP + websocket-client)

```bash
# 1. 后台起一个带 remote-debugging 的 headless Chrome
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new --disable-gpu --no-first-run --no-default-browser-check \
  --remote-debugging-port=9333 --remote-allow-origins='*' \
  --user-data-dir=/tmp/<unique-profile> --window-size=520,900 \
  "http://localhost:5173/<page>"
# 用 terminal background=true 起; 进程常驻,验证完 pkill -f <unique-profile> 清理

# 2. 轮询 CDP 端点就绪
for i in $(seq 1 20); do curl -s http://localhost:9333/json/version >/dev/null && break; sleep 1; done

# 3. 用 python3 + websocket-client(本机已装)连 CDP,轮询 SPA 状态后截图
#    完整脚本:scripts/spa_screenshot_cdp.py(见下)
```

关键点(脚本已封装):
- 连 **browser 级** WS 拿 `/json` 找 page target → 连 **target 级** WS(`webSocketDebuggerUrl`)
- `Page.navigate` 后**轮询** `Runtime.evaluate` 判断 `.boot` 是否消失、内容节点是否出现(最多 40s)
- 等到 `card` 再 `Page.captureScreenshot`(format=png)

## 备选:纯 DOM 断言(不截图,最快)

若只需确认「按钮/文案是否存在」而非视觉布局,直接 headless `--dump-dom` 抓渲染后 HTML 再 grep:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new --disable-gpu --no-first-run --user-data-dir=/tmp/<prof> \
  --virtual-time-budget=6000 --dump-dom "http://localhost:5173/<page>" 2>/dev/null > /tmp/d.html
grep -o '注册中…' /tmp/d.html; grep -o '登录中…' /tmp/d.html
```

⚠️ 两个失败模式**都要防**,别只顾其一:
1. 进程不退出但**文件已写出** → 先 kill 再读文件,不要等 exit;
2. 页面有长连接/埋点/轮询时,`--dump-dom` **可能一个字节都不输出**并挂到超时(详见 Pitfalls)→ 改走常驻 Chrome + CDP 读 `innerText`。

对**能干净收敛**的 React SPA,`--dump-dom` 在 virtual-time-budget 内通常能抓到渲染后 DOM(比 `--screenshot` 可靠,因为不需要像素渲染管线);对持续联网的页面不要指望它。

## 变体:抓「渲染后的文本」而非截图(取数据 / 挖隐藏内容)

需求常常不是截图,而是**取出只在 JS 渲染后才存在的文字**(接口地址、文档表格、动态价格)。这时别截图,直接 `Runtime.evaluate` 读文本——更快、更准,还能顺手拿 DOM:

```python
def js(expr):
    r = send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
    return (r.get('result', {}).get('result', {}) or {}).get('value')

txt  = js('document.body.innerText')             # 可见文本:最快,用来 grep 定位关键词
html = js('document.documentElement.outerHTML')  # 含隐藏/懒加载节点,用来抓 tab 面板里的 JSON 样本
```

实测收益:某云市场商品页把「调用地址」埋在 SPA 里,静态 HTML 和文档接口(各种参数组合)全都取不到;CDP 读一次 `innerText` 就拿到了 `https://<vendor>.market.alicloudapi.com/<path>`。**先读 innerText 定位段落,再用 outerHTML 抠细节**。

**懒加载 tab 必须点开再读**:非默认 tab 的面板内容**不在初始 DOM 中**,`innerText` 读不到。用 JS 点标签叶子节点,等待,再读:

```python
js("""(()=>{const e=[...document.querySelectorAll('*')]
  .filter(x=>x.children.length===0&&x.textContent.trim()===%s);
  if(!e.length)return 'nf'; e[0].click(); return 'ok';})()""" % json.dumps('成功响应'))
time.sleep(2.5)                                 # 等面板渲染
print(js('document.body.innerText')[-900:])     # 取该 tab 之后的文本
```

## Pitfalls

- **`execute_code` 沙箱里没有 `websocket-client`**:系统 python3 装了(实测 1.9.0),但 execute_code 用的是另一个沙箱解释器 → `import websocket` 报 ModuleNotFoundError。**把 CDP 脚本写成文件,用 terminal 跑 `python3 <file>`**,别在 execute_code 里内联。
- **`--dump-dom --virtual-time-budget` 可能一个字节都不输出**(修正下面「备选」一节的乐观说法):对**有长连接 / 永不 settle 的页面**(广告、埋点、轮询),实测直接挂到 300s 超时且**没写出任何文件**——此时「先 kill 再读文件」也没得读。判据:页面有持续网络活动 → **直接走常驻 Chrome + CDP 路线**,不要浪费时间试一次性 dump。
- **起调试实例时不要带 `--dump-dom`**:它 dump 完就退出,CDP 连不上。只带 `--remote-debugging-port` 的裸 Chrome 才会常驻。
- **本机 fake-IP DNS 会让 web_extract 拦掉外部站点**:走 sing-box 代理时域名解析成 `198.18.x.x`(保留段),`web_extract` 判定为「private or internal network address」直接拒绝。绕过办法:用 `curl`(带浏览器 UA)或本节的无头 Chrome。**这是本机 DNS 形态导致的,不代表该站点不可访问**,别据此下"抓不到"的结论。
- **截图拿到 spinner**:SPA 首屏 loading。解法 = CDP 轮询页面状态(核心结论 2)。一次性 `--dump-dom`/`--screenshot` 因无法插入等待逻辑常截到 spinner。
- **CDP WS 403**:缺 `--remote-allow-origins`(核心结论 3)。
- **zsh glob**:`--remote-allow-origins=*` 不引号报 `no matches found`(核心结论 4)。
- **Chrome 进程不退出**:headless 卡住属正常,验证完 `pkill -f <user-data-dir 名>` 清理即可,别等它自然退出。
- **端口被旧实例占**:重启前 `lsof -i :9333 | grep LISTEN` 确认,旧实例 `pkill -f remote-debugging-port=9333` 清掉。
- **macOS 大小写不敏感文件系统**:用 search_files / 读文件时 `Login.tsx` 与 `login.tsx` 看似同名,但 **git 记录的是真实大小写**。引用前端文件前先跑 `git ls-files <dir>`(terminal)确认真实文件名,勿凭记忆写,避免大小写错(实例:某聊天App 的 `web/src/pages/Login.tsx` 是大写 L)。

## Verification

- 脚本打印 `page state: card` 且截图字节数明显大于 spinner 图(>100KB)即成功
- 用 vision_analyze 确认截图里有目标按钮/文案、无白屏/加载圈

## 相关

- 需要真正交互(点击、填表、登录流)而非截图:用 browser-use(browser_exec)或 computer_use typed-browser;本 skill 只覆盖「无头截图/DOM 断言」这一类。
