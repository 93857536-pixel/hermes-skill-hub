# SPA 前端静态 API 逆向(不登录找后端接口)

把一个 webpack/Vue SPA 的**后端 API 清单**扒出来,无需登录态。
Worked example 是天学网学生端 (student.up366.cn, Vue2 + webpack5 + Zuul 网关)。

## 通用步骤

### 1. 首页 HTML 找 JS 入口 + API 网关域名
```bash
curl -s -A "Mozilla/5.0" https://site/ -o home.html
grep -oE '<script[^>]*src="[^"]*"' home.html
grep -oE 'https?://[a-z0-9.-]*\.(com|cn)[a-z0-9.-]*' home.html | sort -u
```
天学网: 首页是 1KB 空壳, `zuulapis.js` 在 CDN 上,内容是
`window.UP366ZUULAPIS = ["dsb-config-api.up366.cn","textbook-api.up366.cn",...]` —— 全部微服务域名清单。

### 2. runtime chunk 里的 webpack5 chunk 映射表
`runtime~index.<hash>.js` 很小(几 KB),内有:
```js
function f(e){return t.p+"js/"+({}[e]||e)+"."+{"chunk-04b03ff4":"85ad066e","chunk-07a5bc02":"4b0c5897",...}[e]+".js"}
```
```python
pairs = re.findall(r'"("chunk-[a-f0-9]+)":"([a-f0-9]+)"', runtime_js)
# 批量下载(并发)
urls = ['https://site/js/%s.%s.js' % (k,v) for k,v in pairs]
# xargs -P 8 curl 或 python concurrent
```
92 个 chunk ≈ 5MB,几秒下完。

### 3. 域名配置模块: 属性字母 → API 域名
找含 `://xxx-api.domain` 字符串的 chunk,通常是一个模块(如 784f)导出几十个属性,
每个属性是一个服务的 base URL:
```js
var r="https", o=r+"://homework-api.up366.cn", c=r+"://studytask-api.up366.cn", p=r+"://study-api.up366.cn", ...
n.d(e,"k",(function(){return o})), n.d(e,"D",(function(){return c})), n.d(e,"C",(function(){return p})), ...
```
→ 属性字母→域名映射表(手写核对,别过度依赖正则)。

### 4. 提取接口清单: 字母 + "/路径"
全 chunk 扫 `变量["字母"]+"路径"` 模式:
```python
re.findall(r'[A-Za-z0-9$_]+\[["\']([A-Za-z])["\']\]\s*\+\s*["\'](/[a-zA-Z0-9_\-/]*)["\']', s)
```
字母→域名 + 路径 = 完整 URL。调用封装形如 `i(o["D"]+"/client/student/course/job", body, config)`。

### 5. 登录参数: 找登录页 chunk
grep `mobile`/`verifyCode`/`password` 的请求体构造:
```js
{mobile: this.bindForm.mobile, verifyCode: this.bindForm.code}
```
注意区分场景(登录 vs 绑定手机 vs 密码注册 —— up366 里 `{mobile,verifyCode}` 也有走
`pwd/check` 的绑定场景; 主登录通常是 `register`)。

### 6. 无登录验证接口可达性(不发真实验证码!)
```bash
curl -s -X POST https://xxx-api.domain/front/user/verify/send_v2 \
  -H "Content-Type: application/json" -d '{}'
# {"result":{"code":-1,"msg":"param_missing"}}  => 接口存在(但只是"缺参数",不代表无风控!)
```
空 body 只返回 param_missing,不触发发码。**探测阶段永远不要带真实手机号调 send 类接口。**

**param_missing 探测的正确解读**:它只证明端点存在。要挖出真实必填参数:
- **换 Content-Type**:很多国内后端(Java/Spring)接受 form 多于 JSON。同一请求从
  `application/json` 换成 `application/x-www-form-urlencoded`(body 改 `k=v&k2=v2`)后,
  错误信息往往直接说出缺什么 —— 实测 up366: JSON 永远是 `param_missing`,form 变成
  `{"code":9,"msg":"ut或picCode验证失败"}` → 字段名 + 验证码门禁一次暴露。
- **错误信息变了 = 字段猜对了**:带完整参数后错误从 `param_missing` 变成别的(如
  "验证码错误"/"ut无效"),说明字段名对了,只是值不对。迭代参数名直到错误变化。
- 补浏览器头(UA/Referer/Origin)再试网关 4xx。

### 8. 滑块验证码门禁(阿里云盾 u3Captcha / _dx_*)
Web 登录发码常被滑块挡:请求体要 `ut`/`picCode`(滑块 token,前端 `u3Captcha.showVerification()`
回调里拿到)。无头绕不过 → 两条出路,优先 1:
1. **抓官方移动 app 的登录接口**(app 常有无滑块登录路径) → §9 mitmproxy。
2. WebView 内嵌官方登录页拿 cookie 兜底(仅登录,业务仍走 API)。

### 9. 移动 app 流量抓包(mitmproxy,ground truth)
官方 app 的真实请求(URL/headers/body/Set-Cookie) = 最可靠参数来源。
```bash
brew install mitmproxy   # 生成 ~/.mitmproxy/mitmproxy-ca-cert.pem
mitmdump -q -w /tmp/flows.mitm "~d target.example.com" &   # 按域名过滤记录
python3 -m http.server 8000 --directory ~/.mitmproxy &     # 证书分发
```
iPhone: Safari 打开 `http://<Mac-LAN-IP>:8000/mitmproxy-ca-cert.pem` → 下载描述文件 →
设置→通用→VPN与设备管理→安装 → 设置→通用→关于本机→证书信任设置→完全信任 →
Wi-Fi ⓘ → 配置代理 → 手动 → 服务器 `<Mac-LAN-IP>` 端口 `8080`。然后正常用官方 app,
分析 `/tmp/flows.mitm`(mitmdump -nr 或 python mitmproxy 库)。要求 iPhone 与 Mac 同网段
(家庭 Wi-Fi 即可; iPhone 热点时 Mac 的 en0 IP 是 172.20.10.x)。

### 7. 运行时补全(登录后)
静态只能拿到 URL 和方法;参数与响应结构靠运行时:
- WKWebView 注入 XHR/fetch hook(WKUserScript, atDocumentStart):
```js
// XHR: 包 open 记录 method/url, 包 send postMessage({cmd:"api",method,url,body})
// fetch: 包 window.fetch 同样记录
// 登录态轮询: checkLogin() 看 body.innerText 是否含登录表单/用户区文案
```
- Swift 侧把 hook 消息写日志文件(控制台 Tab 展示),用户正常浏览即可采集真实请求。

## 天学网 (up366) 逆向成果 (2026-08-10)

### 域名表(784f 模块)
| 属性 | 域名 | 业务 |
|---|---|---|
| F | user-api.up366.cn | 用户/登录 |
| D | studytask-api.up366.cn | 学习任务 |
| C | study-api.up366.cn | 作业提交 |
| d | book-api.up366.cn | 课本/章节 |
| i | dsb-api.up366.cn | 答题/得分/答案 |
| f | course-api.up366.cn | 课程/班级 |
| K | words-api.up366.cn | 单词 |
| L | wrongnote-api.up366.cn | 错题本 |
| s | sso.up366.cn | SSO(v2/tickets-v3) |

### 登录(⚠️ 状态: 2026-08-10 被滑块门禁阻塞,参数未最终确认)
- 发码: POST https://user-api.up366.cn/front/user/verify/send_v2  —— **必须 form-urlencoded**,
  必填 `ut` 或 `picCode`(阿里云盾滑块 token);JSON body 永远 `param_missing`,
  form + 假 token 返回 `{"code":9,"msg":"ut或picCode验证失败"}`
- 登录(候选): POST https://user-api.up366.cn/front/user/register  {mobile, verifyCode}
  —— 静态推断,未实跑成功;iOS app 登录失败即此因
- 校验: POST https://user-api.up366.cn/front/user/verify/check    (绑定场景另有 pwd/check)
- 待办: mitmproxy 抓官方 iOS app(可能有无滑块登录路径)确认真实登录参数

### 任务/答题
- 任务列表: POST https://studytask-api.up366.cn/client/student/course/job
- 任务详情: POST https://studytask-api.up366.cn/client/student/job/info
- 课本作业: POST https://studytask-api.up366.cn/client/student/course/book/job/list
- 章节/题目: book-api /client/task/info, /client/task/linked, /front/chapters/info
- 答案详情: dsb-api /client/student/task/answer/detail/v2
- 提交答案: POST https://study-api.up366.cn/client/job/submit
- 完成列表: dsb-api /client/book/finished-task/list

### 响应包裹
所有接口返回 `{"result":{"code":0,"msg":"success",...}}`; code!=0 时 msg 是错误信息。

### 其他坑
- 首页 JS 的 `index.<hash>.js` 是 webpack runtime(含模块定义),chunk 文件名映射在 `runtime~index` 里。
- `grep "*.js"` 全文件找 chunk 引用会 0 命中 —— 映射表是 `{"chunk-id":"hash"}` 对象,没有 .js 后缀字符串。
- 登录页/业务页面是懒加载 chunk,chunk-common 只是公共库+接口封装,别指望它含全部接口。
