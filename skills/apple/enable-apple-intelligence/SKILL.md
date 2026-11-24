---
name: enable-apple-intelligence
description: "Force-enable Apple Intelligence: 国行/CN Macs (macOS) & region/hardware-gated iOS devices."
---

# Enable Apple Intelligence on region-locked (国行/CN) Macs

Apple Intelligence is region-blocked for devices sold in mainland China (model suffix CH/A). Official CN rollout (Alibaba Qwen + Baidu; 备案 passed 2026-07-15) expected fall 2026, but the international version can be force-enabled now via open-source tools. Always check the apple.com.cn support page for official status first.

## Step 0 — Confirm the device is region-locked
```bash
system_profiler SPHardwareDataType | grep -E "Model|Chip|Memory"   # Model Number ending CH/A = 国行
defaults read -g AppleLanguages; defaults read -g AppleLocale      # current language/region
sw_vers
```

## Step 1 — Diagnose eligibility BEFORE choosing a tool (validated)
The eligibility daemon keeps a per-input breakdown — read it first; it tells you exactly which gate blocks AI and whether the user's language is supported:
```bash
sudo /usr/libexec/PlistBuddy -c 'Print :OS_ELIGIBILITY_DOMAIN_GREYMATTER' /private/var/db/eligibilityd/eligibility.plist
```
- `os_eligibility_answer_t`: 4 = eligible, 2 = not eligible.
- In `status`, each `OS_ELIGIBILITY_INPUT_*` is 3 (eligible) or 2 (the failing input).
- `context.OS_ELIGIBILITY_CONTEXT_ELIGIBLE_SIRI_LANGUAGE` lists installed AI-supported Siri languages. If the user's language appears there (e.g. `zh-CN`), **keep the system fully Chinese — no English switch needed**.

Typical CN unit: only `OS_ELIGIBILITY_INPUT_DEVICE_REGION_CODE = 2`; billing, Siri lang, device lang, location all pass. Region spoofing alone then unlocks AI in the existing language. Full sample output: references/eligibility-plist-diagnosis.md.

## Step 2 — Pick the tool by macOS version
- macOS ≤ 26.5 beta3: `kanshurichard/enableAppleAI` (script, no kext, SIP can stay on).
- **macOS 27.x: `SkyBlue997/enableMacosAI`** (RegionSpoof kext, CH/A→LL/A in IORegistry; verified on 27.0). Old script methods break on 26.5 beta4+.

## Step 3 — Prerequisites
1. SIP **off** + Permissive security (recovery: `csrutil disable`). Ad-hoc kext fails "Bad code signature" under Reduced Security.
2. AMFI **on** — `nvram boot-args` must NOT contain `amfi_get_out_of_my_way` (kills SEP attestation → PCC cloud features dead; install.sh auto-removes it).
3. Apple ID media/billing region: verify via the plist (COUNTRY_BILLING was 3 on a CN account — don't assume it needs changing).
4. Language: system + Siri in an AI-supported language (zh-Hans OK since 2026; confirmed by Step 1 context).

## Step 4 — Install
```bash
git clone --depth 1 https://github.com/SkyBlue997/enableMacosAI
# READ install.sh + src/RegionSpoof.cpp before running (kext = root code)
sudo ./install.sh
```
PITFALL: install.sh copies `region-kext-load.sh` to `/usr/local/bin/` which may not exist → cp/chown/chmod errors (LaunchDaemon silently broken later). Fix: `sudo mkdir -p /usr/local/bin && sudo cp region-kext-load.sh /usr/local/bin/ && sudo chown 0:0 … && sudo chmod 755 …` then re-verify the LaunchDaemon files.

## Step 5 — Kext approval (the usual blocker)
`kmutil load` fails with "not approved to load. Please approve using System Settings."
- GUI path: 系统设置 → 隐私与安全性 → 安全性 section → Allow com.local.RegionSpoof → **reboot** (LaunchDaemon loads it at boot).
- DB shortcut is PARTIAL (do not present as sufficient): the policy row in `/var/db/SystemPolicyConfiguration/KextPolicy` (sqlite) is auto-created on failed load with allowed=1; syspolicyd then logs "Kernel Extension ALLOWED" — but kernelmanagerd still refuses while a "pending upgrade dialog" state exists. GUI Allow or reboot is still required.
- Admin auth dialog ("正在尝试修改你的系统设置"): the USER must Touch ID / type password. **Never type the user's password into a macOS GUI auth dialog via automation.**
- Reboot clears the pending state; `com.local.regionkext` LaunchDaemon then loads the kext automatically.

## Step 6 — Verify & enable
```bash
sudo ./install.sh status        # SIP/AMFI/region/kext/GREYMATTER overview
ioreg -ard1 -c IOPlatformExpertDevice | plutil -p - | grep region-info    # 4c4c2f41 = LL/A
# GREYMATTER answer 4:
sudo /usr/libexec/PlistBuddy -c 'Print :OS_ELIGIBILITY_DOMAIN_GREYMATTER:os_eligibility_answer_t' /private/var/db/eligibilityd/eligibility.plist
```
Then flip 系统设置 → Apple 智能与 Siri. Models download in background (GBs); `sudo ./install.sh diagnose` shows progress.

## Pitfalls
- SIP must STAY off — switching to Reduced Security silently kills the ad-hoc kext and AI turns off.
- PCC cloud features (语气改写, 图乐园, Reframe) need AMFI on + reachable Apple relay: from CN use a US/JP node, not HK. `32001 + RetryAfterDate` in privatecloudcomputed logs = rate-limited (stop clicking, wait hours). On-device features (校对/摘要/Genmoji) work without relay.
- Uninstall: `sudo ./install.sh uninstall` + reboot; re-enable SIP in recovery if desired.
- System Settings automation: deep link `open "x-apple.systempreferences:com.apple.settings.PrivacySecurity"` may not navigate — use the sidebar search field and type 隐私 instead. computer_use `scroll` fails with "ambiguous_window_target" even with window_id (app owns many windows) — use element AXPress (works off-screen) or keyboard paging.

## iOS: 强开(region lock / unsupported hardware)

Same two-file mechanism as macOS, different injection channel — iOS side is covered in depth by
**references/ios-force-enable.md** (full knowledge bank: keys, paths, GREYMATTER template, version × device matrix, tool-ecosystem license audit, uncertainties). Essentials:

- Write targets: MobileGestalt cache CacheExtra (`/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist`, read-only for sandboxed apps but readable) + `/var/db/eligibilityd/eligibility.plist` (GREYMATTER = AI domain; root-owned).
- Gestalt keys: 18.1-era obfuscated `A62OafQ85EJAiiqKn4agtg`=1; iOS 26.x+ plaintext `AppleIntelligenceAllowedDevice/SupportedDevice/MinimumRAM(=6)`; `h9jDsbgj7xIVeIQ8S3/X3Q`=ProductType; region `h63QSdBCiT/z0WU6rdQv6Q`=US + `zHeENZu+wbg7PUprwNwBWg`=LL/A.
- **Version reality (2026-09)**: AI exists only ≥18.1; hardware unlock (≤A16) server-blocked since 18.1b5 (needs kernel MIS hook, not file writes); in-app unlock needs an exploit write channel — kernel escape covers 17.0–26.0.x, bad_query only 27.0b1-4; 26.5+ eligibility rewrite reportedly dead (Nugget #1073). 国行 region unlock on A17 Pro+ hardware is the low-risk path.
- **License trap**: mond/Nugget/EnsWilde are AGPLv3 — extract facts (paths/keys), never copy code into a GPLv3 app; MisakaX is MIT but source-less.

## References
- references/eligibility-plist-diagnosis.md — full sample output, field meanings, KextPolicy schema, log signatures.
- references/ios-force-enable.md — iOS force-enable knowledge bank (keys/paths/matrix/licenses/in-app write primitives/uncertainties).
