# Apple Intelligence On-Device Enablement — Knowledge Bank

Condensed findings from the iOS 26.x / 27.0b1–4 on-device AI-unlock research (mond / EnsWilde / misaka26 / Nugget / 3105). Dates to 2026-09. Facts are source-verified; items needing a live device are marked 需实测.

## 1. File paths

| Purpose | Path |
|---|---|
| MobileGestalt cache | `/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist` |
| AI eligibility (eligibilityd) | `/var/db/eligibilityd/eligibility.plist` |
| Region/EU eligibility (OSEligibility) | `/var/db/os_eligibility/eligibility.plist` + OSEligibility MobileAsset `Config.plist` (two asset hashes: `c55a421c...` and `247556c6...`) |

`/var` is a symlink to `/private/var` — both spellings hit the same file. mond uses the `/private/var/...` spelling; Nugget uses `/var/...`.

## 2. MobileGestalt CacheExtra key map (obfuscated → real name)

Source: Nugget `src/devicemanagement/generate_mga.py` (authoritative dump) + mond/EnsWilde usage.

| Obfuscated key | Real name |
|---|---|
| `h9jDsbgj7xIVeIQ8S3/X3Q` | ProductType |
| `h63QSdBCiT/z0WU6rdQv6Q` | RegionCode |
| `zHeENZu+wbg7PUprwNwBWg` | RegionInfo |
| `+3Uf0Pm5F8Xy7Onyvko0vA` | DeviceClass |
| `mZfUC7qo4pURNhyMHZ62RQ` | BuildVersion |
| `qNNddlUK+B/YlooNoymwgA` | ProductVersion |
| `LeSRsiLoJCMhjn6nd6GWbQ` | FirmwareVersion |
| `oPeik/9e8lQWMszEjbPzng` | ArtworkTraits (dict: ArtworkDeviceSubType, ArtworkDeviceProductDescription, …) |
| `A62OafQ85EJAiiqKn4agtg` | DeviceSupportsGenerativeModelSystems (18.x AI capability) |
| `YlEtTtHlNesRBMal1CqRaA` | Dynamic Island capability |
| `j8/Omm6s1lsmTDFsXjsBfA` / `2OOJf1VhaM7NxfRok3HbWQ` | Always-On Display |
| `9MZ5AdH43csAUajl/dU+IQ` | SupportedDeviceFamilies |
| `qeaj75wk3HF4DwQ8qbIi7g` | DeviceSupportsEnhancedMultitasking (Stage Manager) |
| `LBJfwOEzExRxzlAnSuI7eg` | Internal storage view |
| `EqrsVvjcYDdxHBiQmGhAWw` | Apple Internal Install / Metal HUD |

⚠️ **RegionInfo key ambiguity**: mond uses `yK+xavymRGZ3xWc1tb8XDg` for region info; Nugget/EnsWilde use `zHeENZu+wbg7PUprwNwBWg`. 需实测 which is the true 27.0 RegionInfo.

## 3. AI capability keys by iOS version (the critical split)

- **iOS 18.1 beta**: `CacheExtra["A62OafQ85EJAiiqKn4agtg"] = 1` (obfuscated DeviceSupportsGenerativeModelSystems). Patched server-side in 18.1 DB5.
- **iOS 26.x (misaka26 / Nugget 7.2)**: plaintext keys in CacheExtra:
  - `AppleIntelligenceAllowedDevice = 1`
  - `AppleIntelligenceSupportedDevice = 1`
  - `AppleIntelligenceMinimumRAM = 6` (GB)
- **iOS 27.0 b1–4 (mond)**: still writes only the old `A62OafQ85EJAiiqKn4agtg`; known issue "Apple Intelligence spoofing doesnt work on iPhone 15". Likely needs the 26.x plaintext keys — 需实测.

ProductType spoof targets (satisfy the `/v1/models` endpoint): `iPhone16,1` (15 Pro), `iPhone16,2` (15 Pro Max), `iPhone15,4` (iPhone 15 — reportedly also accepted for 15-class); iPad: `iPad16,3`/`iPad16,4`.

## 4. eligibilityd plist (GREYMATTER = Apple Intelligence)

`/var/db/eligibilityd/eligibility.plist` structure (Nugget `AITweak`, EnsWilde `Resources/eligibility.plist`):

```
OS_ELIGIBILITY_DOMAIN_GREYMATTER:
  os_eligibility_answer_source_t = 1
  os_eligibility_answer_t = 4            # 4 = eligible
  context.OS_ELIGIBILITY_CONTEXT_ELIGIBLE_DEVICE_LANGUAGES = ["en", ...]
  status:
    OS_ELIGIBILITY_INPUT_DEVICE_LANGUAGE = 3
    OS_ELIGIBILITY_INPUT_DEVICE_REGION_CODE = 3
    OS_ELIGIBILITY_INPUT_EXTERNAL_BOOT_DRIVE = 3
    OS_ELIGIBILITY_INPUT_GENERATIVE_MODEL_SYSTEM = 3
    OS_ELIGIBILITY_INPUT_SHARED_IPAD = 3
    OS_ELIGIBILITY_INPUT_SIRI_LANGUAGE = 3
OS_ELIGIBILITY_DOMAIN_CALCIUM:
  os_eligibility_answer_source_t = 1
  os_eligibility_answer_t = 2
  status.OS_ELIGIBILITY_INPUT_CHINA_CELLULAR = 2   # 国行蜂窝绕过
```

## 5. Access mechanism (on-device, iOS 27 b1–4, mond)

Two methods, both `dlopen("/usr/lib/system/libsystem_containermanager.dylib")`:

- **bad_query (default, forcequit)**: `container_query_create` → `set_class(13)` → `set_group_identifiers("systemgroup.com.apple.mobilegestaltcache")` → `operation_set_part(3)` → `operation_set_part_domain("../../../../../../../..<gestalt_dir>")` → `operation_set_flags(0x0000008000000000)` → `get_single_result` → `container_copy_sandbox_token` → `sandbox_extension_consume(token)`. Returns an activated sandbox-extension handle; then plain `open(path, O_RDWR|O_CLOEXEC|O_NOFOLLOW)` works. Identical to 3105's `exploit/bad_query.c` — DeviceToolbox already has it.
- **cmg (johnny's MCM bug class)**: same query but `operation_set_flags((1<<32)|(1<<39))` + `container_object_sandbox_extension_activate(res, true)`. iOS 27 only; unlocks MobileGestalt but not PosterBoard/HouseArrest.

## 6. Safe write pattern (mond `mg_write`)

- Backup current gestalt to app Application Support (`SavedGestalt.plist`) on first load.
- Atomic in-place: `open(O_RDWR|O_CLOEXEC|O_NOFOLLOW)` → `ftruncate(fd,0)` → `write` → `fsync` → `lseek`+read-back verify → on failure rollback original bytes.
- Non-atomic alt: write `.tmp` then `replaceItemAt`/`moveItem` (mond labels in-place as "Persist after reboot").
- Respring via neon's WKWebView memory-pressure page (jailbreak.party `respringDocument`); some tweaks need full reboot.
- Known failure: "tweaks may disappear on reboot" (mobilegestaltd cache regen).

## 7. Server-side assertion

`IntelligencePlatform` daemon asserts against `intelligence.apple.com/v1/models`. This killed the 18.1b4 method at 18.1 DB5 and is the top uncertainty for A16 devices on 26/27. Three-phase flow: SPOOF ProductType → DOWNLOAD models (watch Settings → Storage "Apple Intelligence" grow 44MB→~2.2–3GB) → revert ProductType but keep capability keys (reverting early re-breaks Face ID via part serialization).

## 8. Version × model × target matrix

Targets: **H** hardware spoof (≤A16), **R** region unlock (A17 Pro+ 国行), **O** official.

| Device | 17.x | 18.0 | 18.1b1–4 | 18.1b5–18.7.1 | 26.0–26.6.1 | 27.0 b1–4 |
|---|---|---|---|---|---|---|
| A17 Pro/A18/A19 non-CN | ❌ | ❌ | ✅O | ✅O | ✅O | ✅O |
| A17 Pro+ 国行 CH/A | ❌ | ❌ | 🔧R | 🔧R❓ | 🔧R | 🔧R❓ |
| A16 and below | ❌ | ❌ | 🔧H | ❌ | 🔧H✅ | 🔧H❓ |
| A15 and below | ❌ | ❌ | ❓ | ❌ | ❓(RAM<6GB) | ❓ |

## 9. DeviceToolbox integration design (from spec-part2.md)

New files (do not touch existing; Sources/ auto-included so project.yml unchanged):
- `Sources/SystemAccess/AIEnablePolicy.swift` — enum version×model×target gate (inject params for tests).
- `Sources/SystemAccess/MobileGestaltService.swift` — enum statics: ensureWriteAccess / readGestalt / backupGestalt / writeGestalt(atomic) / writeAIEligibility / restoreBackup.
- `Sources/SystemAccess/AIEnableController.swift` — @MainActor singleton state machine (idle/running/active/failed), detached Task for C chain + file I/O, mirrors `ExploitController`.
- `Sources/Views/Settings/AIEnableView.swift` — Settings entry under the privilege engine section.
- Localizable keys prefixed `aienable.*` (en + zh-Hans).

Reuse: `bad_query.c`/`mcm_bridge.m` (write access), `ExploitController.isSandboxActive()`, `SupportPolicy.isSupportedCurrentDevice()`, `DeviceProbe.modelIdentifier`.

## 10. License audit

| Repo | License | Action |
|---|---|---|
| 3105 / ThreeOneOSFive | GPLv3 | safe, already integrated |
| mond (rooootdev) | AGPLv3 | facts only, no code |
| EnsWilde (YangJiiii) | AGPLv3 | facts only, no code |
| Nugget (leminlimez) | AGPLv3 | facts only, no code (note: MisakaX combined LICENSE lists leminlimez as MIT — relicense discrepancy, trust repo's own LICENSE) |
| MisakaX (straight-tamago) | MIT | safe with attribution |
