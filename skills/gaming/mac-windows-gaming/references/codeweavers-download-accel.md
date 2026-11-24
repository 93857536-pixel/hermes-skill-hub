# CodeWeavers / CrossOver 下载加速(国内网络)

2026-08 实测于 Apple Silicon Mac(macOS 27),CrossOver 26.3.0,387MB zip。

## 关键事实
- 官方包是 **.zip 不是 .dmg**:`https://media.codeweavers.com/pub/crossover/cxmac/demo/crossover-<ver>.zip`(猜 .dmg 全部 404)
- **必须带 User-Agent**:无 UA 直接 http 000 拒连;`-A "Homebrew/6.0.17"` 即可
- 官网主站 www.codeweavers.com 对国内 IP 会 302 重定向到中国代理站(马软 mairuan / crossoverchina.com),其"试用下载"链接指向捆绑包(如 `cpv2.mairuan.com/.../trial/leigodarm64.dmg` 实为雷神加速器),**不要用**
- brew cask 拿版本:`brew info --cask crossover`(cask 定义的 URL 就是官方直链)

## 提速核心:指定 CDN 节点(--resolve)
默认 DNS 解析的节点限速严重(单连接 60KB/s),不同 IP 差异巨大(实测):
- 172.67.72.229(Cloudflare): 822KB/s ← 最快
- 151.101.2.217(Fastly): 529KB/s
- 151.101.90.217 / 146.75.46.217: ~430-510KB/s
- 默认解析节点: 60KB/s(慢 14 倍)

用法:`curl --resolve media.codeweavers.com:443:172.67.72.229 -A "Homebrew/6.0.17" <URL>`
先 `curl -r 0-1999999 -o /dev/null -w "%{speed_download}"` 对候选 IP 各测 2MB,选最快的。

## 分段并行下载(387MB 约 8 分钟)
```bash
# SIZE 从 HEAD 的 content-length 拿
for i in $(seq 0 3); do
  START=$(( i * CHUNK )); END=$(( START + CHUNK - 1 )); [ $END -ge $SIZE ] && END=$((SIZE-1))
  curl -sL --noproxy '*' --retry 5 --resolve media.codeweavers.com:443:172.67.72.229 \
    -A "Homebrew/6.0.17" -r $START-$END -o /tmp/cxseg_$i "$URL" &
done; wait; cat /tmp/cxseg_* > out.zip
```
合并后必须 `unzip -t out.zip` 校验(分段下载可能静默损坏)。

## 其他
- `brew install --cask crossover` 走同一 CDN,同样被限速;brew 缓存看进度:`du -sh ~/Library/Caches/Homebrew/downloads/`
- 装好后验证架构用 `lipo -info <App>/Contents/MacOS/<bin>`(本环境 file 命令 libmagic 版本不兼容会刷屏报错,勿用)
- 试用激活:启动 → 点"现在试用",14 天,无需邮箱注册
