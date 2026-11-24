---
name: video-footage-sourcing
description: "Find & verify web/Douyin/WeChat video footage: B站API搜、抖音cookie下载、ffmpeg抽帧、微信缓存挖."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [video, download, bilibili, wechat, ffmpeg, vision-verify]
    category: media
---

# Video Footage Sourcing

## When to Use

- User asks to find/download a video clip matching content criteria (location, landmark, crowd, no-watermark, recency, orientation).
- User shares a WeChat 视频号 link and wants the video file.
- User shares a Douyin (抖音) link — a `v.douyin.com` short link, or copy-pasted share text (the code like `Asni0VdyYk` / `QihWyP02uJA` sits in the line with "复制打开抖音") — and wants the video file.

Find, download, and verify video clips that match content requirements (place, landmark in frame, crowd density, no watermark, landscape, recent). Delivery rule: verify with extracted frames + vision BEFORE telling the user it matches — titles and metadata lie (this session: a 【国庆】aerial whose frames showed no clock tower; a "泉州" video that was actually Xiamen).

## Workflow

1. Search platform, collect candidate BVIDs/URLs with metadata (title, upload date, duration, views).
2. Download top candidates (1080p is usually enough; B站/YouTube 30fps 1080p).
3. Extract 5-10 frames across the timeline, run structured vision_analyze per frame: (a) does the target landmark/scene appear? (b) any watermark/logo in the 4 corners or anywhere? (c) crowd density / shot quality?
4. Only deliver a clip when frames confirm ALL user criteria. Keep frame folders + all candidates on ~/Desktop; user may reject and ask for the next best.

## Bilibili search (use the API, not yt-dlp)

`yt-dlp "bilisearch20:..." --flat-playlist` gives BVIDs but ALL metadata is `NA` (title/views/date missing) — useless for filtering. Use the web search API:

```bash
# 1. get buvid3 cookie (search API 403s without it)
curl -s -c cookies.txt -L "https://www.bilibili.com" -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" > /dev/null
COOKIE=$(grep -E "buvid3|b_nut" cookies.txt | awk '{print $7"="$8}' | tr '\n' ' ')

# 2. search (order=click for popularity, order=pubdate for newest)
curl -s "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=$(urlencode KW)&order=pubdate" \
  -A "Mozilla/5.0" -H "Referer: https://search.bilibili.com" -H "Cookie: $COOKIE"
```

JSON: `data.result[]` has `bvid`, `title` (HTML-escaped, strip tags), `play`, `pubdate` (epoch), `author`, `duration`. 412 errors = transient, retry. Then `yt-dlp --no-download --print "..." https://www.bilibili.com/video/$bvid` for per-video details.

Download 1080p: `yt-dlp -f "30080+30280" --merge-output-format mp4`. B站 free tier caps at 1080p (30fps); "4K" titles often have no 4K stream. 30080=1080p video, 30280=hi audio. Vertical videos: 30080 is 1080x1920.

**Watermark reality (verified):** nearly all B站 UGC carries "UP主ID + bilibili" corner logo (platform-baked). To find clean clips: prioritize 4K uploads from prolific drone/stock UP主 (some are genuinely clean — verify per-frame anyway), or switch to YouTube. Official/CCTV sources (CCTV 4K, city ICC channels) carry their own 台标.

## YouTube

`yt-dlp --no-download "ytsearch15:Quanzhou"` works without auth; watch for fuzzy search drift (English queries can return other cities). Download: `yt-dlp -f "bestvideo[height<=1080]+bestaudio" --merge-output-format mp4`. Creator channels are usually watermark-free; verify frames regardless. 4K downloads can be 200-300MB.

## Douyin (抖音) links

Douyin requires "fresh cookies" — anonymous curl/yt-dlp fails with `Fresh cookies (not necessarily logged in) are needed`. A logged-in session is NOT required; headless Chrome's anonymous cookies are enough.

```bash
# 1. Resolve the short link to a numeric video id (the share text's code is the last path segment)
curl -s -o /dev/null -w "%{redirect_url}\n" -A "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)" \
  "https://v.douyin.com/<CODE>/"     # -> iesdouyin.com/share/video/<ID>/?...  ; the ID is the douyin video id
# Use the canonical page: https://www.douyin.com/video/<ID>

# 2. Get fresh anonymous cookies: launch headless Chrome (port 9337, see devops/spa-screenshot-cdp),
#    navigate to douyin.com, dump Storage.getCookies -> Netscape file
#    Pitfall: CDP cookie dumps contain entries with empty name/value (e.g. "douyin.com") that BREAK
#    yt-dlp's Netscape parser ("invalid Netscape format ... AssertionError"). Filter: keep only
#    lines with exactly 7 tab-separated fields, non-empty name AND value.
#    Needed cookie names include ttwid, odin_tt, s_v_web_id, __ac_nonce, __ac_signature.

# 3. Download with yt-dlp
yt-dlp -f "bv*[height<=1080]+ba/b" --merge-output-format mp4 \
  --cookies /tmp/dy_nets.txt --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ... Chrome ..." \
  -o "out.mp4" "https://www.douyin.com/video/<ID>"
```

Verified facts (2026-10): anonymous cookies cap resolution at ~720p (1366x720 / 1280x720 HEVC). The raw CDN stream has NO douyin watermark or UP-corner logo (unlike Bilibili) — so douyin is the best source for clean Chinese UGC clips. HEVC delivery: re-encode for broad compatibility `ffmpeg -i in.mp4 -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac out_H264.mp4`. The old `iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids=` endpoint is dead (empty response); the web `aweme/v1/web` detail API is signed — don't bother hand-crafting requests when yt-dlp works.

## Watermark-free stock sites (Pexels / Pixabay)

Royalty-free, no watermark by license — but both sit behind Cloudflare: plain curl gets a 2.5KB "Just a moment" challenge page. Requires a real browser session (headless Chrome via CDP, see `devops/spa-screenshot-cdp`). If the goal is just clean footage and B站/YouTube already has a clean hit, skip the stock sites (usually less location-specific).

## Frame extraction gotchas (ffmpeg)

- Default jpg output FAILS on some streams ("Non full-range YUV is non-standard ... Invalid argument") — 4K/HEVC and other high-bit-depth streams. Fix: output png with `-pix_fmt rgb24`: `ffmpeg -ss T -i in.mp4 -frames:v 1 -pix_fmt rgb24 out.png`.
- Frames for inspection can go to /tmp; delivered artifacts + frame folders go to ~/Desktop (user inspects there).
- Loop over multiple timestamps as one ffmpeg invocation per timestamp; don't use image2 sequence patterns.

## WeChat 视频号 (channels / sph links)

`sph` share links CANNOT be downloaded externally (verified: yt-dlp unsupported; web endpoints return risk-control errCode 10012; the SPA's data fetch is wired to the WeChat client's WeixinJSBridge; headless Chrome CDP captures 0 network requests and no `<video>` ever renders). Dead end by design.

Working path: the Mac WeChat client caches video messages as plaintext mp4 (HEVC+aac, directly playable):

```
~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/<wxid>_<hash>/msg/video/YYYY-MM/*.mp4
```

Find the target: `find` that dir for `-mtime -1` mp4s, ffprobe sizes, frame-extract + vision-confirm content. If the target video isn't cached yet, ask the user to open it in Mac WeChat / forward it to 文件传输助手 (that forces a local download), then re-scan.

## 交付前核验清单(before reporting)

1. `ffprobe` 宽/高(横屏 = w>h)+ 时长。
2. 2–3 帧 vision 确认:目标地标在画面内、四角干净、镜头类型;vision 对同一角落的水印文字会幻觉(同位置报出不同假字样),文字内容视为未确认,只看多帧一致的有无。
3. 文件确实在你引用的路径上(`ls -lh`),勿凭下载日志断言。

## Pitfalls

- Never trust titles: "钟楼" in a title does not mean the tower is in frame; "泉州" videos can be Xiamen. Frame-verify every claim.
- vision_analyze corner/watermark answers can contradict across frames of the same video — resolve by checking more frames, not the first answer.
- B站 `--flat-playlist` bilisearch metadata is NA; don't filter on it.
- Don't promise a 视频号 link "I'll download it" — external download is architecturally impossible; offer the cache-dig path instead.
- Douyin Netscape cookie file: a raw CDP `Storage.getCookies` dump contains entries with empty name AND value (e.g. `douyin.com` and `device_web_cpu_core` duplicated with literal values) that crash yt-dlp with `AssertionError: domain_specified == initial_dot` / "invalid Netscape format". Always filter to 7-field lines where name and value are both non-empty before passing `--cookies`.
- Douyin: the `v.douyin.com` share code is the path segment before the query string; resolve with `curl -o /dev/null -w "%{redirect_url}"` to get the numeric id, then use the canonical `www.douyin.com/video/<id>` URL.
