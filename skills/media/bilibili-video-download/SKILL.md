---
name: bilibili-video-download
description: Find, download, vision-verify B站 videos by content criteria.
version: 1
author: hermes
license: MIT
metadata:
  hermes:
    tags: [bilibili, yt-dlp, video, download, vision, search]
    related_skills: [youtube-content]
---

# Bilibili Video Search, Download & Content Verification

## When to Use
User asks to find, fetch, or verify a B站 video matching concrete content criteria (a place/landmark/scene, a time-of-year, crowd density, quality). Especially when the request implies "verify before you deliver" — a title alone is not proof of content, so this skill adds a frame-sampling + vision verification stage.

## Overview
Find a bilibili video by scene/content criteria (e.g. "航拍泉州钟楼、国庆、人要多、画面清晰"), download via yt-dlp, and verify actual content with frame sampling + vision before delivering.

## Workflow

### 1. Search (API, not yt-dlp search)
`yt-dlp --flat-playlist "bilisearch20:..."` returns bare numeric aids whose URLs fail (see Pitfall 1). Use the Bilibili search API instead — one script does cookie + search + parse:

```bash
bash ~/.hermes/skills/media/bilibili-video-download/scripts/bili_search.sh "泉州钟楼 航拍" 15
# prints: bvid | title | 播放数 | UP主, sorted by click
```

- `order=click` = most played.
- Multiple keyword variants ("钟楼 航拍", "国庆 航拍", "钟楼 人群") usually beat one exact-phrase search.
- If the response is not JSON (rate limit), `sleep 3`, refresh the cookie (re-run script), retry.

### 2. Metadata + formats
For each candidate bvid:
```bash
yt-dlp --no-download --print "标题:%(title)s | 时长:%(duration_string)s | 播放:%(view_count)s | 日期:%(upload_date)s | UP:%(uploader)s | 简介:%(description).120s" "https://www.bilibili.com/video/<bvid>"
yt-dlp --no-download -F "https://www.bilibili.com/video/<bvid>"
```
- upload_date + 简介 are the festival/timing evidence (e.g. pubdate 20231001 = 国庆第一天, 简介 "国庆节去拍的，好多人啊").
- 简介/发布日期 beat the title for "is it actually 国庆".

### 3. Download (no login needed up to 1080p30)
Without cookies, free formats cap at 1080p30 (1080p60 / 1M 高码率 need premium or `--cookies`). For "画面要清晰", 1080p30 is enough:
```bash
yt-dlp -f "30080+30280" --merge-output-format mp4 --user-agent "Mozilla/5.0" \
  -o "<clean_name>.mp4" "https://www.bilibili.com/video/<bvid>"
```
- Format ids differ per video; if 30080/30280 are absent use `-f "bv*[height<=1080]+ba/b"`.
- 竖版 (1080x1920) videos list formats as width<height — note it in the report to the user.

### 4. Verify content (do NOT trust titles)
Titles mislabel landmarks — a "西街+东西塔" video contained no 钟楼; a "混剪" had the 钟楼 at only one timestamp, with few people. Verify:
```bash
ffprobe -v error -show_entries stream=width,height:format=duration -of default=noprint_wrappers=1 file.mp4
# sample frames: every ~15-25s, or targeted at interesting moments
for t in 5 20 40 60 80 100; do ffmpeg -v error -ss $t -i file.mp4 -frames:v 1 -q:v 3 frames/f_$t.jpg -y; done
```
Then `vision_analyze` each frame with a TARGETED question set: (a) is the target landmark present and where (b) crowd density — 人山人海 or sparse (c) aerial vs ground-pov (d) sharpness. A landmark that appears in only 1 of N frames is a weak match; report honestly.

### 5. Deliver
User's standing rule: put final copies under `~/Desktop/<topic>/` (never /tmp only). Download the top 2-3 candidates, verify, report with per-file verdict (which frame timestamp shows the landmark, which don't). Keep the frames dirs so the user can spot-check.

## Pitfalls
1. **yt-dlp bilisearch ids are bare aids**: `bilibili.com/video/910770386` (no `av` prefix) makes the BiliBili extractor fall back to generic → "Unsupported URL". Use bvids from the search API, or `av<aid>` URLs.
2. **Search API needs a buvid3 cookie**: grab via `curl -s -c cookies.txt https://www.bilibili.com` (with a UA header), `awk '$7=="buvid3"{print "buvid3="$8}'`. No login required.
3. **Rate limiting**: repeated search calls can return non-JSON empty bodies (JSONDecodeError). Sleep ~1s between calls, longer on failure.
4. **No-cookies format cap**: 1080p60/1M require cookies/premium; without them, 1080p30 (~2.9Mbps) is the ceiling — usually fine for "清晰" requests.
5. **vision_analyze on a missing path errors** ("media file not found") — confirm the frame files exist (search_files target=files, glob `frames/f_*.jpg`) before calling.
6. **Timestamp grid matters**: pick frame offsets spanning the whole video; in a 混剪 the landmark may appear only mid-video.
