---
name: aliyun-marketplace-api
description: "Use when 接入阿里云云市场 API(cmapiXXXX):网关/路径发现、APPCODE、服务端代理。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [aliyun, marketplace, cmapi, appcode, api-gateway, id-verification, ocr]
    category: devops
---

# 阿里云云市场 HTTP API 接入(cmapiXXXX)

## When to Use

- 用户买了一个**阿里云云市场**的 API 商品(商品码形如 `cmapi00070693`,`sku` 形如 `yuncode6469300002`),要接进 App/后端
- 拿到的是 `AppKey / AppSecret / AppCode`,但**不知道调用地址和请求参数**(商品页是 SPA,翻不到)
- 要判断该按 APPCODE 简单认证还是 AppKey&AppSecret 签名认证
- 典型商品类别:身份证二要素/实名认证、OCR、手机号检测、发票查验、短信、AI 能力

## 关键认知(先读)

1. **云市场 API ≠ 阿里云 OpenAPI**。云市场 API 走**服务商自己的 API 网关域名** `<vendor>.market.alicloudapi.com`,用 `Authorization: APPCODE <code>`(或 AppKey 签名)认证;**不是** `dysmsapi.aliyuncs.com` 那套 AK/SK + 签名串。
2. **商品页拿不到接口路径**(SPA 动态渲染),但**商品码能查出网关域名**——这条几乎总能成。
3. **AppCode 只放服务端**。它等于该商品的调用凭证,泄露即可刷你的配额。客户端(App/前端)一律走自己的后端代理,绝不内置。
4. 免费试用额度通常很小(常见 50 次 / 30 天)。**调试要省着用**:能在本地拦掉的非法入参(格式/校验位)就别发上游。

## 第 1 步:查网关域名(必用,不用猜)

```bash
curl -s "https://market.aliyun.com/api/ajax/product/queryApiList.json?productCode=<cmapiXXXX>" | python3 -m json.tool
```

返回里直接有:

```json
{"result":{"endPoint":"apigateway.cn-hangzhou.aliyuncs.com",
  "ApiInfo":[{"GroupName":"…","ApiName":"…","ApiId":"…","GroupId":"…","StageName":"RELEASE"}],
  "DomainItems":{"DomainItem":[{"DomainName":"<vendor>.market.alicloudapi.com"}]}}}
```

`DomainItems.DomainItem[].DomainName` 就是**网关域名**。

## 第 2 步:拿接口路径(只有一条可靠路)

静态 HTML、`queryApiDoc.json`(**任何参数组合都返回 `result:null`**)都拿不到路径。**唯一可靠办法 = 无头 Chrome + CDP 渲染商品页,读 `document.body.innerText`**,在「调用地址」那一段就有完整 URL。

```bash
# 起一个常驻调试实例(不要带 --dump-dom,否则 dump 完就退)
'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --headless=new --disable-gpu --remote-debugging-port=9333 \
  --remote-allow-origins='*' --user-data-dir=/tmp/chr-mkt \
  "https://market.aliyun.com/detail/<cmapiXXXX>"
# 然后 python3 + websocket-client 连 CDP,读 innerText / 点开「成功响应」「错误码」tab
```

完整操作细节见 skill **`spa-screenshot-cdp`**(含「抓渲染后文本」「懒加载 tab 要点开再读」「execute_code 沙箱没有 websocket-client」等要点)。

**⚠️ 不要靠猜路径**:本 skill 作者按 camelCase 猜过 40+ 个候选(`/idcardAudit`、`/idcard/check`、`/checkIdcard`…)全部 404。真实路径可能是**全小写无分隔**(实测 `/idcardcheck`)。猜是浪费时间,渲染页面只要一分钟。

## 第 3 步:确认路径存在(便宜的探针法)

网关对不存在的路径返回 404 + 结构化错误头,可用来判别:

```bash
curl -s -i "https://<vendor>.market.alicloudapi.com/<path>" \
  -H "Authorization: APPCODE <code>" | head -12
```

```
x-ca-error-message: API not found with `GET /<path>`
x-ca-error-code: I404NF
```

| 观察 | 含义 |
|------|------|
| `I404NF` / `API not found with <METHOD> <PATH>` | **路径或方法不对**(注意错误信息会回显你的方法+路径,便于二分) |
| 返回业务 JSON(即便 `success:false`) | 路径+方法对了, **认证也已通过** |
| 403 `InvalidAppCode` 之类 | 路径对了, 但 AppCode 不对/未绑定该商品 |

**注意**:404 时 AppCode 根本不会被校验(路径解析在前),所以**不能从 404 反推 AppCode 是否有效**。

## 认证方式

| 方式 | 用法 | 适用 |
|------|------|------|
| **简单认证(AppCode)** | Header `Authorization: APPCODE <AppCode>` | 服务端内部调用;最省事 |
| 签名认证(AppKey&AppSecret) | `X-Ca-Key` + `X-Ca-Signature`(HMAC) | 需可轮换凭证/更高安全等级 |

多数商品两种都支持,商品页「API 调用」一栏会写明。**同一个 AppCode 也能从 Query 传**(`?AppCode=…`),但 Header 更好(不进 access log/Referer)。

## 服务端代理模式(收口在这里)

云市场 API 一律**只在后端调**,统一成自己的接口暴露给客户端:

1. **凭证落服务端 env**:写进 `env.json`/环境变量(如 `REALNAME_APPCODE`)。多份 env 文件时**每份都要写**(见下「坑」)。
2. **入参本地先校验**,不合法直接拒 → **不消耗付费配额**(格式、长度、校验位、枚举值)。
3. **限流三层**:同用户短窗防连点 + 同用户每日上限(**保护付费额度**)+ 同 IP 每小时。按次计费的商品,日限是刚需。
4. **错误语义化**:服务商的 msg/错误码映射成自己的 error 码再返回给客户端,别把上游原文透出去(可能含内部信息/回显入参)。
5. **日志只记结果码**,不记姓名/证件号/手机号等 PII。
6. **上游超时必设**(如 `AbortSignal.timeout(8000)`);上游异常返回 502 而不是 500,便于区分。
7. 缓存能力状态:未配置凭证时应 fail-closed 返回「服务未开通」而不是静默失败。

## Pitfalls

- **⚠️ 不要把 `env.json` 内容经工具输出中转**:这类文件含 PII/密钥,工具输出会对长 token 自动脱敏 → 你若「读出来改一改再写回」,写回的是**被打码的假值**,会写坏线上配置。**必须在目标机器上用脚本本地读改写**(例:上传一个 node 脚本,脚本内 `JSON.parse` → 改键 → `writeFileSync`,只 `console.log` 键名不打印值)。
- **多份配置文件**:应用常有多处 `env.json`(如 `app/config/env.json` 与 `DATA_ROOT/config/env.json`)。按加载顺序只写一份可能不生效 → **两份都写**,并确认哪份优先(`cwd/config` 常优先)。
- **商品页/文档接口取不到路径**是常态,别反复换参数试 `queryApiDoc.json`(作者试过十几种组合全 `null`)。
- **`web_extract` 可能拒绝云市场/开发者社区域名**:本机走代理时 fake-IP DNS 解析成 `198.18.x.x`,被判定为内网地址而拦截 → 改用 `curl`(带 UA)。这不代表站点不可访问。
- **实名/证件类接口的隐私红线**:绝不落明文证件号。库里只存**掩码(姓 `张*三`、证号前 4 后 2)** + **HMAC 指纹**(带服务端 pepper,不可逆,可用于查重);响应里也不回显服务商返回的个人信息字段(性别/生日/地址)。
- **注意上游「不一致也返回权威信息」的行为**:不少二要素接口在 `result=不一致` 时**仍返回**该证号对应的性别/生日/地址。不要把这些字段透给调用方,否则等于提供任意人信息查询。

## Verification

- 未带凭证打自己的代理端点应得 **401**(而非 404 = 没挂载)
- 非法入参应得**语义化 4xx**,且**不消耗上游配额**(可用一次上游调用前后对比数据校验)
- 用一次**格式合法但非真人**的入参打真实上游,确认全链路(APPCODE → 上游 → 解析)通:应返回业务结果(如 `不一致/无记录`)而不是 401/403/超时
- 「不一致」的结果**不得**把用户状态置为已认证

## 参考

- `references/id-card-two-factor.md` — 身份证二要素(九天创界 `jtidcard`)完整接口规格、错误码表、响应样例与本地校验规则
- 渲染 SPA 拿接口文档:skill `spa-screenshot-cdp`
- 号码认证/一键登录(Dypns,与云市场不同体系):skill `aliyun-number-auth`
