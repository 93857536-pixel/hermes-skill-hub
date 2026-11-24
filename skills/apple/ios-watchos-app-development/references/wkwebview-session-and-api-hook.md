# WKWebView session persistence + in-app API capture hook

Worked example: TianXueBot (embedded-login + auto-answer app). Two goals: keep the
user logged in across restarts, and capture the site's own XHR/fetch traffic to
reverse-engineer its API without mitmproxy.

## 1. Session persistence reality check

- `configuration.websiteDataStore = .default()` IS persistent — but only when the
  process exits gracefully (Cmd+Q / `applicationShouldTerminate` path). A hard kill
  (`pkill`, SIGKILL, crash) can lose the login: cookies/localStorage never flushed.
  Symptom: login works, then after an agent-`pkill`-style restart the app is back on
  the login page. Not a code bug — a flush-window problem.
- Disk layout (non-sandboxed app, macOS): `~/Library/WebKit/<bundle-id>/WebsiteData/`
  - localStorage lives DEEP: `Default/<origin-hash>/<origin-hash>/LocalStorage/localstorage.sqlite3`
    (two identical hash dirs nested) — `find -maxdepth 2` misses it. Use `du -sh` +
    a full-depth find for `*.localstorage` / `Cookies*`.
  - localStorage values are UTF-16LE: `IsLatestLogin` reads as `f^@a^@l^@s^@e^@`.
  - Login tokens often live in cookies that are session-only → no BinaryCookies file
    on disk even after login. Don't conclude "no persistence" from missing cookie files.
- Practical consequence for embedded-login apps: expect the user to re-login after
  forced restarts; surface a "quit normally (Cmd+Q) to keep login" hint.

## 2. In-app API capture hook (WKUserScript)

Capture the site's own API calls to reverse parameters, no proxy needed:

```js
// injected atDocumentStart, forMainFrameOnly:false
window.__txhook = (function () {
  function post(p) { try { window.webkit.messageHandlers.tianxue.postMessage(p); } catch (e) {} }
  var o = XMLHttpRequest.prototype.open, s = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__m = m; this.__u = u; return o.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (b) {
    try { post({ cmd: "api", method: String(this.__m||"GET"), url: String(this.__u||""),
                 body: b ? String(b).slice(0,500) : "" }); } catch (e) {}
    return s.apply(this, arguments);
  };
  var f = window.fetch;
  window.fetch = function (i, init) {
    try { var u = typeof i === "string" ? i : (i && i.url) || "";
          post({ cmd: "api", method: String((init&&init.method)||"GET"), url: String(u),
                 body: init&&init.body ? String(init.body).slice(0,500) : "" }); } catch (e) {}
    return f.apply(this, arguments);
  };
  function checkLogin() {          // body-text heuristics, not cookie checks
    var t = (document.body && document.body.innerText) || "";
    var form = t.indexOf("获取手机验证码") >= 0 || t.indexOf("请登录") >= 0;
    var user = t.indexOf("我的教学班") >= 0 || t.indexOf("退出登录") >= 0;
    return (user && !form) ? "in" : (form ? "out" : "unknown");
  }
  return { post: post, checkLogin: checkLogin };
})();
```

- Register handler name `tianxue` on `WKUserContentController` (Swift side persists
  captured lines to `Documents/apis.log`).
- Poll `checkLogin()` every ~2s via `evaluateJavaScript`; on `"in"`, pull cookies with
  `httpCookieStore.getAllCookies`, filter by `domain.contains("up366")`-style suffix,
  then reuse them in `URLSession` for app-side API calls.
- UTF-8 note: Chinese sites — match on the literal strings above; `innerText` is fine.

## 3. Pitfalls

- `WKScriptMessageHandler` must be a weak-wrapped NSObject (WeakScriptMessageHandler
  pattern) or you get a retain cycle.
- `customUserAgent` matters: some sites serve different bundles to desktop vs mobile
  UAs; pick the one whose task set you want (mobile often has MORE task types).
- ATS: if app-side `URLSession` calls http(s) API hosts not used by the WebView, you
  may need `NSAllowsArbitraryLoads` (dev tool) or per-domain exceptions.
