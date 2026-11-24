#!/usr/bin/env python3
"""用证书透明日志枚举某域名的全部子域，可选逐个抓首页 title。

主源用 certspotter —— crt.sh 的 `?output=json` 经常返回非 JSON / 被限流，
不能再当作可靠数据源。

用法:
  python3 ct_subdomains.py example.com
  python3 ct_subdomains.py example.com --titles        # 逐个抓 title（本类任务最关键的一步）

关键用法：子域列表拿到后一定要抓 title —— 兄弟站往往直接暴露运营方真实业务
（例：主站叫「充值服务中心」，子域却是「作业帮验证中心」「迅雷扫码系统」）。
"""
import html as H
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def _read(url, timeout=40, limit=300000):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read(limit).decode("utf-8", "ignore")


def subdomains(domain):
    found = {}
    urls = [
        "https://api.certspotter.com/v1/issuances?domain=%s&include_subdomains=true&expand=dns_names" % domain,
        "https://api.certspotter.com/v1/issuances?domain=%s&include_subdomains=false&expand=dns_names" % domain,
    ]
    for u in urls:
        for attempt in range(3):
            try:
                for rec in json.loads(_read(u)):
                    for name in rec.get("dns_names", []):
                        found.setdefault(name.strip().lstrip("*."),
                                         (rec.get("not_before") or "")[:10])
                break
            except Exception as e:  # 限流 / 非 JSON / 网络抖动
                print("  ! certspotter 第%d次失败: %s" % (attempt + 1, e), file=sys.stderr)
                time.sleep(3)
    return found


def title_of(host, timeout=15):
    for scheme in ("https", "http"):
        for path in ("/", "/index.php", "/recharge.php"):
            try:
                body = _read("%s://%s%s" % (scheme, host, path), timeout=timeout, limit=200000)
            except Exception:
                continue
            title = re.findall(r"(?is)<title>(.*?)</title>", body)
            txt = re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", re.sub(
                r"(?is)<(script|style).*?</\1>", " ", body)))).strip()
            if title or txt:
                return (title[0].strip() if title else ""), txt[:160]
    return "", ""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    domain = sys.argv[1].strip().lower()
    want_titles = "--titles" in sys.argv

    subs = subdomains(domain)
    print("distinct names: %d" % len(subs))
    for name in sorted(subs):
        print("  %-45s first_seen=%s" % (name, subs[name]))

    if want_titles:
        print("\n--- titles (只读 GET，间隔 1.5s) ---")
        for name in sorted(subs):
            time.sleep(1.5)
            t, txt = title_of(name)
            print("%-45s | %s" % (name, t or "(no title)"))
            if txt and txt != t:
                print("      %s" % txt[:150])


if __name__ == "__main__":
    main()
