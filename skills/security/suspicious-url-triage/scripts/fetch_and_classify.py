#!/usr/bin/env python3
"""拉取页面并做结构化分类：title / 正文 / 状态消息 / 内联 JS 常量 / 表单。

只做只读 GET（默认移动端 UA —— 国内灰产站的 HEAD 常被 WAF 判 403，GET 才正常）。
SSL 校验关闭，因为这类站点普遍使用错配的共享证书。

用法:
  python3 fetch_and_classify.py "http://host/recharge.php?c=TOKEN"
  python3 fetch_and_classify.py "http://host/recharge.php?c=TOKEN" --variants
  python3 fetch_and_classify.py "URL" --token c        # 显式指定凭据参数名

--variants 会额外探测「空值」和「同长度随机值」两个状态，用于枚举状态机。
"""
import argparse
import html as H
import random
import re
import ssl
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=25):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    req.add_header("Accept-Language", "zh-CN,zh;q=0.9")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.getcode(), dict(r.headers), r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "ignore")
    except Exception as e:
        return "ERR", {}, "EXC: " + str(e)[:200]


def visible_text(body):
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", body)
    t = H.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def analyze(body):
    msg = [re.sub(r"\s+", " ", m).strip()
           for m in re.findall(r'(?is)<div class="[^"]*\bmsg[^"]*"[^>]*>(.*?)</div>', body)]
    consts = dict(re.findall(r"const\s+(\w+)\s*=\s*([^;]{1,80});", body))
    ids = sorted(set(re.findall(r'id="(phoneForm|phoneInput|phoneBtn|codeInput|submitBtn|'
                                r'hiddenForm|hiddenCode|loginForm|rebindForm|hiddenLogin|hiddenRebind)"', body)))
    inputs = [re.sub(r"\s+", " ", m)[:160]
              for m in re.findall(r"(?is)<(?:input|select|textarea|button)\b[^>]*>", body)]
    return {"title": (re.findall(r"(?is)<title>(.*?)</title>", body) or [""])[0].strip(),
            "text": visible_text(body)[:700], "msg": msg, "consts": consts,
            "ids": ids, "inputs": inputs[:12]}


def report(label, url):
    code, headers, body = fetch(url)
    print("=" * 72)
    print(f"[{label}] {url}")
    print(f"  status={code}  len={len(body)}  server={headers.get('Server')}  "
          f"ctype={headers.get('Content-Type')}")
    if code == "ERR":
        print("  ", body)
        return
    a = analyze(body)
    print(f"  title : {a['title']}")
    if a["msg"]:
        print(f"  state : {a['msg']}")
    for k in ("cardCode", "isSuccess", "isError", "step", "waiting"):
        if k in a["consts"]:
            print(f"  const {k} = {a['consts'][k]}")
    if a["ids"]:
        print(f"  js-ids: {a['ids']}")
    for i in a["inputs"]:
        print(f"  input : {i}")
    print(f"  text  : {a['text']}")
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--token", help="凭据参数名，默认自动取第一个查询参数")
    ap.add_argument("--variants", action="store_true", help="额外探测 空值 / 随机值 状态")
    ap.add_argument("--sleep", type=float, default=1.5, help="请求间隔秒数，默认 1.5")
    args = ap.parse_args()

    parts = urllib.parse.urlsplit(args.url)
    q = urllib.parse.parse_qs(parts.query, keep_blank_values=True)
    tok = args.token or (list(q)[0] if q else None)

    report("原值", args.url)

    if args.variants:
        if not tok:
            print("! URL 没有查询参数，跳过 --variants", file=sys.stderr)
            return
        original = (q.get(tok) or [""])[0]
        empty = urllib.parse.urlunsplit(
            parts._replace(query=urllib.parse.urlencode({tok: ""}, doseq=True)))
        time.sleep(args.sleep)
        report("空值", empty)
        rand = "".join(random.choice(string.hexdigits.upper()) for _ in original) or "AAAA"
        rnd = urllib.parse.urlunsplit(
            parts._replace(query=urllib.parse.urlencode({tok: rand}, doseq=True)))
        time.sleep(args.sleep)
        report(f"随机值({tok}={rand})", rnd)


if __name__ == "__main__":
    main()
