---
name: ios-mobilegestalt-editing
description: Use when editing iOS MobileGestalt/eligibility on-device.
version: 1
author: hermes
license: MIT
metadata:
  hermes:
    tags: [ios, mobilegestalt, apple-intelligence, exploit, device-toolbox, jailbreak]
    related_skills: [web-api-reverse-engineering, ios-static-sdk-integration]
---

# iOS MobileGestalt / Eligibility On-Device Editing

How to research and build on-device iOS feature-unlock (Apple Intelligence, region, Dynamic Island, Stage Manager…) by editing the MobileGestalt cache and eligibility plists after a sandbox escape. Grounded in the DeviceToolbox work (3105 GPLv3 exploit chain) plus public projects mond / EnsWilde / misaka26 / Nugget.

## When to Use
- Adding or extending an iOS "feature unlock" / "Apple Intelligence 强开" / "region unlock" module.
- Researching how a public tweak (mond, misakaX, Nugget, EnsWilde) actually writes to the system.
- Auditing licenses before integrating third-party iOS tweak code.

## Two files are the whole game
1. **MobileGestalt cache** (read `CacheExtra`, write new keys):
   `/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist`
   (`/private/var/...` is the same file; `/var` → `/private/var`.)
2. **AI eligibility** (`OS_ELIGIBILITY_DOMAIN_GREYMATTER` = Apple Intelligence):
   `/var/db/eligibilityd/eligibility.plist`
   — NOT `/var/db/os_eligibility/eligibility.plist`, which is the separate OSEligibility region/EU subsystem.

## On-device write access (no root, no chown)
Reuse the containermanager "MCM bug class" sandbox-query escape (`bad_query` by forcequit, or `container_object_sandbox_extension_activate` by 0xjohnnydev):
- `container_query_create` → `set_class(13)` (system group container) → `set_group_identifiers("systemgroup.com.apple.mobilegestaltcache")` → `operation_set_part(3)` → `operation_set_part_domain("../../../../../../../..<gestalt_dir>")` → `operation_set_flags(0x0000008000000000)` → `get_single_result` → `container_copy_sandbox_token` → `sandbox_extension_consume(token)` → then plain `open(path, O_RDWR)` works.
- DeviceToolbox already ships this as `Sources/ExploitCore/bad_query.c` + `mcm_bridge.m` (from 3105 GPLv3) plus `sandbox_escape()` / `kexploit_opa334()` as a kernel-level fallback.

## Writing the gestalt cache safely
- **Backup before edit** to app's Application Support (restore path in case of bootloop risk).
- **Atomic in-place write**: `open(O_RDWR|O_CLOEXEC|O_NOFOLLOW)` → `ftruncate(fd,0)` → `write` → `fsync` → `lseek`+read-back verify → rollback original on failure. Same-inode write is what mond calls "Persist after reboot" (best-effort against mobilegestaltd regenerating the cache).
- Then **respring** (neon's WKWebView memory-pressure respring) or **reboot**. Known failure: tweaks may disappear on reboot (mobilegestaltd cache regen).

## Key facts (full mapping in references/apple-intelligence-enablement.md)
- `CacheExtra` keys are obfuscated; see the reference for the real-name ↔ obfuscated table (ProductType `h9jDsbgj7xIVeIQ8S3/X3Q`, RegionCode `h63QSdBCiT/z0WU6rdQv6Q`, …).
- AI capability: **18.1 used obfuscated `A62OafQ85EJAiiqKn4agtg`=1**; **26.x switched to plaintext keys `AppleIntelligenceAllowedDevice`/`AppleIntelligenceSupportedDevice`=1 and `AppleIntelligenceMinimumRAM`=6** — the version split is the #1 cause of "spoof worked on 18 but not 26/27".
- IntelligencePlatform daemon does a **server-side assertion** against `intelligence.apple.com/v1/models` — the reason 18.1 DB5 killed the old method and the #1 thing to flag 需实测 on A16 devices.
- The spoof is three-phase: SPOOF ProductType → DOWNLOAD models → revert ProductType but keep the capability keys.

## Version × model matrix (summary)
- iOS 17.x / 18.0: **impossible** (AI ships in 18.1).
- 18.1 b1–4: old obfuscated-key method worked; 18.1 DB5+: server-patched, hardware spoof dead, region unlock only.
- 26.x: primary target — misaka26/Nugget 7.2 plaintext keys, A16 iPhone 15 Plus success reported.
- 27.0 b1–4: mond proves the on-device write path works, but its AI spoof "doesn't work on iPhone 15" (it still writes the old 18.x key). 需实测 with 26.x plaintext keys.

## Licensing (hard rule)
- 3105 = **GPLv3** (already integrated, safe).
- mond, EnsWilde, Nugget = **AGPLv3** — stricter copyleft; merging their code into a GPLv3 app forces the whole app to AGPLv3. **Extract facts (paths/key names/mechanisms), never copy their Swift/ObjC.**
- misakaX = **MIT** (safe with attribution).
- Key names, file paths, and mechanisms are facts (not copyrightable); the eligibility plist structure is data to regenerate fresh, not copy.

## Pitfalls
- Distinguish the two eligibility dirs (`eligibilityd` = AI, `os_eligibility` = region/EU).
- Mark everything not verified on-device as 需实测 rather than asserting it works — especially: 26.x plaintext keys on iOS 27, server-side assertion strength on A16, gestalt persistence across reboot, eligibilityd recompute-on-boot.
- Region unlock (A17 Pro+ 国行) is the lowest-risk first target — no hardware spoof, no model download.

## Gestalt key map(完整 6 行,直接可用的最难得数据)

| obfuscated | real name | use |
|---|---|---|
| `A62OafQ85EJAiiqKn4agtg` | DeviceSupportsGenerativeModelSystems | AI capability (integer 1,仅 18.1 旧混淆键;26.x 改明文键,见上) |
| `h9jDsbgj7xIVeIQ8S3/X3Q` | ProductType | model spoof(`iPhone16,1`=15Pro … `iPhone18,3`=17) |
| `oYicEKzVTz4/CxxE05pEgQ` | HardwareModel/TargetSubType | board spoof(`D83AP`…) |
| `5pYKlGnYYBzGvAlIU8RjEQ` | HardwarePlatform | SoC spoof(`t8130`=A17Pro…) |
| `h63QSdBCiT/z0WU6rdQv6Q` | RegionCode | 国行 unlock → `"US"` |
| `zHeENZu+wbg7PUprwNwBWg` | RegionInfo | region SKU → `"LL/A"` |

Spoofing = Model + Hardware + CPU **三键同写**。AI-capable 从 `iPhone16,1`(15 Pro)起;`iPhone15,4`=iPhone 15(A16,**不支持**,常见错)。

## eligibility 语义

`os_eligibility_answer_t`:**4 = eligible,2 = not eligible**;`status` inputs:**3 = passes/override,2 = failing input**。GREYMATTER = Apple Intelligence 域;CALCIUM = China Cellular(`CHINA_CELLULAR`)。完整 GREYMATTER 模板逐字段:`references/ios-gestalt-eligibility-spec.md`。

## 注入通道 × iOS 版本矩阵

- 17.0–18.1.1 → **sparserestore**(symlink traversal);18.2–26.1 → **BookRestore**(iBooks DB + backup domains);26.2+ → 两者均已 patch。
- 硬件强开(A16/A15 机型):仅 **18.1b1–4** 有效;18.1b5+ 服务端已 patch(模型下载端点验真硬件,纯文件伪装下不了模型)。
- 国行/region unlock(在**支持硬件**上)= eligibility + region 文件即可(无模型下载)→ 18.4+ / 26.x 仍可用。
- 26.5+:eligibility 改写失效(Nugget #1073,疑似签名/完整性校验);27.0:restore 通道彻底 patch(勿用)。

## 研究/解码技巧(可复用)

- `search_files`(grep)混淆键或域名名(`A62OafQ85EJAiiqKn4agtg`、`GREYMATTER`)直跳 AI 相关代码;键↔名映射在 Nugget `src/devicemanagement/generate_mga.py`,AI tweaks 在 `src/tweaks/tweak_loader.py` + `eligibility_tweak.py`。
- 解码二进制 `.plist`:`python3 -c "import plistlib; plistlib.load(open(f,'rb'))"`。
- `web_extract` 对 `gist.github.com`/`theapplewiki.com`/github issues 误报 `Blocked: URL targets a private or internal network address` → 改用 `curl -sL https://api.github.com/gists/{id}`、`/repos/{o}/{r}/issues/{n}`(未认证可用);GitHub Discussions API 返回 None → 走 GraphQL 或 web-search 摘要。theapplewiki.com 有 CF challenge,内容已被主 repo 的 plists 镜像,别硬刚。

## Pitfalls

- 两目录分工:`eligibilityd` = AI,`os_eligibility` = region/EU。
- 未实测一律标「需实测」:26.x 明文键在 iOS 27、A16 的服务端断言强度、gestalt 重启持久性、eligibilityd 开机重算。
- 国行 region unlock(A17 Pro+)是最低风险首选目标——无硬件伪装、无模型下载。
- 真机 root 直写 MGA 缓存 ≠ PC exploit 路径:PC 工具用 `crash_on_purpose` 强制重载缓存;直写 + 重启可能被 mobilegestaltd 重建/覆盖,需实测。

## References

- `references/apple-intelligence-enablement.md` — full key tables, eligibility plist structure, access-mechanism detail, version×model matrix, DeviceToolbox integration design (files + API sketches + Localizable keys), license audit.
- `references/ios-gestalt-eligibility-spec.md` — 完整 GREYMATTER/CALCIUM 模板、ProductType/Hardware/CPU 伪装值表、注入通道版本矩阵、license 审计表、on-device vs PC 可行性分析。
