# iOS MobileGestalt / eligibility — full reference spec

Sources read (read-only, Sept 2026): `leminlimez/Nugget` (v5.2.0, AGPL-3.0), `straight-tamago/misakaX` (MIT, README-only), `username3006/apple-intelligence` + `sheevaahhh/apple-intelligence` (no license, mirror of f1shy-dev gist), f1shy-dev gist `23b4a78dc283edd30ae2b2e6429129b5`, icedmoca gist `0962d129c584b7dadda9ea4e75f2e8e9`, Nugget issue #1073, sumitduster-kiuzan discussion #2.

---

## A. Exact file paths

| purpose | path | source |
|---|---|---|
| MobileGestalt cache (edit `CacheExtra`) | `/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist` (equiv `/private/var/...`) | Nugget `src/tweaks/basic_plist_locations.py:6` (`FileLocation.mga`); f1shy gist Part1 |
| AI eligibility answer | `/var/db/eligibilityd/eligibility.plist` | Nugget `src/tweaks/eligibility_tweak.py:123` (`AITweak.apply_tweak` restore_path); f1shy gist Part2 |
| EU Enabler eligibility (DMA, same family) | `/var/db/os_eligibility/eligibility.plist` | Nugget `eligibility_tweak.py:59` (`EligibilityTweak`, lrdsnow EUEnabler) |
| EU Enabler policy Config (two asset hashes) | `/var/MobileAsset/AssetsV2/com_apple_MobileAsset_OSEligibility/purpose_auto/{c55a421c053e10233e5bfc15c42fa6230e5639a9 | 247556c634fc4cc4fd742f1b33af9abf194a986e}.asset/AssetData/Config.plist` | Nugget `eligibility_tweak.py:70,77` |
| Feature Flags | `/var/preferences/FeatureFlags/Global.plist` | Nugget `basic_plist_locations.py:9` |

## B. Gestalt key map (obfuscated hash → real name → value)

Primary source for name mapping: Nugget `src/devicemanagement/generate_mga.py` (comments map each hash to a real name). AI tweaks: Nugget `src/tweaks/tweak_loader.py`.

| obfuscated key | real name | type/value | use | source |
|---|---|---|---|---|
| `A62OafQ85EJAiiqKn4agtg` | DeviceSupportsGenerativeModelSystems | int 1 | AI capability switch | `tweak_loader.py:56`; f1shy gist Part1 |
| `h9jDsbgj7xIVeIQ8S3/X3Q` | ProductType | string, spoof | model spoof | `generate_mga.py:62`; `tweak_loader.py:59` |
| `oYicEKzVTz4/CxxE05pEgQ` | HardwareModel / TargetSubType | string, spoof | board spoof | `generate_mga.py:82`; `tweak_loader.py:100` |
| `5pYKlGnYYBzGvAlIU8RjEQ` | HardwarePlatform | string, spoof | SoC spoof | `generate_mga.py:28`; `tweak_loader.py:141` |
| `0+nc/Udy4WNG8S+Q7a/s1A` | ProductType (2nd cache-extra key) | string | same as `h9jD…` | `generate_mga.py:24` |
| `h63QSdBCiT/z0WU6rdQv6Q` | RegionCode | `"US"` | 国行 unlock | `tweak_loader.py:23` (`Shutter`); `generate_mga.py:61` |
| `zHeENZu+wbg7PUprwNwBWg` | RegionInfo | `"LL/A"` | region SKU | `tweak_loader.py:23`; `generate_mga.py:96` |

### Spoof value tables (Nugget built-in, `tweak_loader.py:59-181`)

ProductType: `iPhone16,1`(15 Pro) `iPhone16,2`(15 Pro Max) `iPhone17,1`(16 Pro) `iPhone17,2`(16 Pro Max) `iPhone17,3`(16) `iPhone17,4`(16 Plus) `iPhone18,3`(17); iPads: `iPad16,1/16,2`(mini A17Pro), `iPad16,3–16,6`(Pro M4), `iPad14,3–14,11`(Pro/Air M2), `iPad13,4–13,17`(Pro/Air M1).

HardwareModel: `D83AP`(15Pro) `D84AP`(15ProMax) `D47AP/D48AP`(16/16Plus) `D93AP/D94AP`(16Pro/Max) `V57AP`(17) `J410AP/J411AP`(mini A17Pro) `J717AP/J718AP`(Pro 11" M4) `J720AP/J721AP`(Pro 13" M4) `J620AP/J621AP`(Pro 12.9" M2) `J617AP/J618AP`(Pro 11" M2) `J507AP/J508AP`(Air 11" M2) `J517AP/J517xAP`(Pro 11" M1) `J522AP/J522xAP`(Pro 12.9" M1).

HardwarePlatform (SoC): `t8130`(A17Pro) `t8140`(A18) `t8150`(A19) `t8182`(M4) `t8112`(M2) `t8103`(M1).

> Correction vs. common folklore: `iPhone15,4` = iPhone 15 (A16, NOT AI-capable). AI starts at `iPhone16,1`.

## C. Feature flags (AI-related, `/var/preferences/FeatureFlags/Global.plist`)

- Category `Siri`: `sae_override`, `assistant_engine_override` → `{"Enabled": true}`
- Category `SiriUI`: `sae` → `{"Enabled": true}`
- f1shy gist also mentions `PrivateCloudCompute`, `TextComposer`, `Siri`, `SiriNL` (values unspecified — 需实测).

Source: `tweak_loader.py:57-58`.

## D. eligibility.plist GREYMATTER template (complete, f1shy gist + Nugget AITweak)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>OS_ELIGIBILITY_DOMAIN_CALCIUM</key>
	<dict>
		<key>os_eligibility_answer_source_t</key><integer>1</integer>
		<key>os_eligibility_answer_t</key><integer>2</integer>
		<key>status</key>
		<dict>
			<key>OS_ELIGIBILITY_INPUT_CHINA_CELLULAR</key><integer>2</integer>
		</dict>
	</dict>
	<key>OS_ELIGIBILITY_DOMAIN_GREYMATTER</key>
	<dict>
		<key>context</key>
		<dict>
			<key>OS_ELIGIBILITY_CONTEXT_ELIGIBLE_DEVICE_LANGUAGES</key>
			<array><string>en</string></array>
		</dict>
		<key>os_eligibility_answer_source_t</key><integer>1</integer>
		<key>os_eligibility_answer_t</key><integer>4</integer>
		<key>status</key>
		<dict>
			<key>OS_ELIGIBILITY_INPUT_DEVICE_LANGUAGE</key><integer>3</integer>
			<key>OS_ELIGIBILITY_INPUT_DEVICE_REGION_CODE</key><integer>3</integer>
			<key>OS_ELIGIBILITY_INPUT_EXTERNAL_BOOT_DRIVE</key><integer>3</integer>
			<key>OS_ELIGIBILITY_INPUT_GENERATIVE_MODEL_SYSTEM</key><integer>3</integer>
			<key>OS_ELIGIBILITY_INPUT_SHARED_IPAD</key><integer>3</integer>
			<key>OS_ELIGIBILITY_INPUT_SIRI_LANGUAGE</key><integer>3</integer>
		</dict>
	</dict>
</dict>
</plist>
```

Semantics: `answer_source_t` 1=device-answered / 4=asset-policy. `answer_t` 4=eligible / 2=not eligible. `status` input 3=passes/override / 2=failing. GREYMATTER=Apple Intelligence; CALCIUM=China Cellular. sumitduster shorthand "1,4,3,3,3,3" = source 1, answer 4, inputs all 3 (macOS shows 4 inputs, iOS 6 — 需实测 which set a given iOS build expects).

### ownership/permission (unresolved)
Nugget writes `501:501` (mobile:mobile), mode 0755 (default in `restore.py:13`, `tweak_classes.py:13`, `backup.py:14`). sumitduster macOS manual = root + read-only (`command+i` → lock). eligibilityd runs as root so 0755 world-readable works either way — **需实测**.

## E. Version matrix

| iOS | channel | gestalt | eligibility | note |
|---|---|---|---|---|
| 17.0–18.1.1 | sparserestore (symlink traversal) | ✅ | ✅ | `restore.py:128` `has_sparserestore_capability` |
| 18.1b1–b4 | sparserestore | ✅ hardware-force works (real model download) | ✅ | f1shy/username3006/sheevaahhh |
| 18.1b5+ | — | ❌ hardware-force patched server-side | UI-only | f1shy WARNING |
| 18.2–18.7.x | BookRestore (iBooks DB + backup domains) | ✅ | ✅ | README; `tweak_loader.py:465-470` (≤18.2 loads eligibility/mga) |
| 18.4+ | BookRestore | official 15Pro+; 国行 official | ✅ 国行 viable | README |
| 26.0–26.1 | BookRestore | ✅ (needs device-specific MGA file) | ✅ | README "Getting the File"; `constants.py:39` |
| 26.2+ | ❌ patched | ❌ MGA/AI Enabler unsupported | — | README; `constants.py:27-29` `is_exploit_fully_patched` |
| 26.5+ | ❌ | — | ❌ eligibility rewrite dead | issue #1073 |
| 27.0 | ❌ | ❌ | ❌ | README WARNING |

`constants.py` nuance vs README: `has_bookrestore()` returns False for `18.7.5 ≤ v < 26.0` (a gap README doesn't mention) — 需实测. `is_exploit_fully_patched()` = `!(bookrestore || partial_sparserestore)` → 26.2+.

## F. License audit

| repo | license | reuse note |
|---|---|---|
| leminlimez/Nugget | AGPL-3.0 | code reuse → AGPL obligations; key names/plist = functional facts |
| straight-tamago/misakaX | MIT (©2024 little_34306) | free w/ attribution; **source not in repo** (binary only) |
| username3006/apple-intelligence | none | read-only reference |
| sheevaahhh/apple-intelligence | none | read-only reference |
| f1shy-dev gist (origin) | none | read-only reference |
| lrdsnow/EUEnabler | not verified | EU Enabler origin |

## G. On-device vs PC (given kernel rw + root)

- **Pure file writes feasible on-device**: eligibility.plist (GREYMATTER), FeatureFlags, 国行 region unlock (RegionCode/RegionInfo + GREYMATTER eligibility) — no model download needed on supported hardware.
- **File writable but integrity-constrained**: MobileGestalt cache — write only `CacheExtra`, preserve `CacheData`/`CacheUUID`/`CacheVersion`; on-device root can READ the device-specific file directly (better than PC shortcut export).
- **Not solvable by file writes alone**: hardware-force (A16/A15) on 18.1b5+ — model-download endpoint validates real hardware via `MISValidateSignatureAndCopyInfo`; needs kernel/process hook returning spoofed identifiers (keep BoardId/UniqueDeviceID real). Beyond file-write scope.
- **PC tools use `crash_on_purpose`** (`restore.py:180-182`) to force cache reload; direct root write + reboot may be rebuilt/overwritten — 需实测.

## H. To-test list

1. eligibility.plist ownership: mobile:mobile 0755 vs root+read-only.
2. GREYMATTER input set: iOS 6 vs macOS 4 items per build.
3. `answer_t`/input value exact semantics (4=eligible, 3=override, 2=block — inference, cross-check Apple Wiki "Eligibility").
4. On-device MGA write persistence vs PC crash_on_purpose reload.
5. 18.7.5–25.x BookRestore gap (constants vs README).
6. `intelligence.apple.com/v1/models` server check details (icedmoca claim, low confidence).
7. 26.5+ eligibility patch mechanism (issue #1073 speculates signature/integrity/moved verification).
