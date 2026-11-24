# Eligibility plist & kext approval internals (macOS 27, verified 2026-08)

## GREYMATTER eligibility dict — full sample from a CN Mac (macOS 27.0, zh-Hans, M2)

```bash
sudo /usr/libexec/PlistBuddy -c 'Print :OS_ELIGIBILITY_DOMAIN_GREYMATTER' /private/var/db/eligibilityd/eligibility.plist
```

Output (only region failing):
```
Dict {
    status = Dict {
        OS_ELIGIBILITY_INPUT_DEVICE_REGION_CODE = 2        <- the ONLY failing input (CH/A)
        OS_ELIGIBILITY_INPUT_DEVICE_CLASS = 3
        OS_ELIGIBILITY_INPUT_SIRI_LANGUAGE = 3             <- zh-CN is AI-supported
        OS_ELIGIBILITY_INPUT_COUNTRY_BILLING = 3           <- CN Apple account billing passes
        OS_ELIGIBILITY_INPUT_GENERATIVE_MODEL_SYSTEM = 3
        OS_ELIGIBILITY_INPUT_COUNTRY_LOCATION = 3
        OS_ELIGIBILITY_INPUT_EXTERNAL_BOOT_DRIVE = 3
        OS_ELIGIBILITY_INPUT_DEVICE_AND_SIRI_LANGUAGE_MATCH = 3
        OS_ELIGIBILITY_INPUT_SHARED_IPAD = 3
        OS_ELIGIBILITY_INPUT_DEVICE_LANGUAGE = 3
    }
    os_eligibility_answer_source_t = 1
    os_eligibility_answer_t = 2                             <- 4 = eligible; 2 = not
    context = Dict {
        OS_ELIGIBILITY_CONTEXT_ELIGIBLE_SIRI_LANGUAGE = zh-CN
        OS_ELIGIBILITY_CONTEXT_ELIGIBLE_DEVICE_LANGUAGES = Array { zh }
    }
}
```

Reading it: 10 inputs, any one at 2 blocks the whole domain; answer flips to 4 only when all are 3.
`context` is the ground truth for "can I keep Chinese?" — it lists the AI languages the OS actually supports for this install. If the user's Siri language is there AND its input is 3, do not force English.

## Kext policy DB (/var/db/SystemPolicyConfiguration/KextPolicy, sqlite)

Schema (macOS 27):
- `kext_policy(team_id, bundle_id, allowed BOOLEAN, developer_name, flags, PRIMARY KEY(team_id, bundle_id))`
- `kext_load_history_v3(path, team_id, bundle_id, boot_uuid, created_at, last_seen, flags, cdhash)`

Observed behavior: a failed `kmutil load` attempt AUTO-CREATES the policy row
(e.g. `('', 'com.local.RegionSpoof', 1, 'Unidentified - RegionSpoof', 4)` — allowed already 1).
syspolicyd then logs "Kernel Extension ALLOWED", but kernelmanagerd STILL refuses with
"not approved to load" while a "pending upgrade dialog" state is set
(log: "Blocking upgrade dialog for kext that is already pending upgrade").
Conclusion: the DB row alone is NOT sufficient — the GUI Allow click (or a reboot to clear
the ephemeral pending state) is still required. Don't sell the DB trick as a full bypass.

## Log signatures

```bash
sudo log show --last 15m --predicate 'eventMessage CONTAINS[c] "RegionSpoof" OR eventMessage CONTAINS[c] "not approved"' --style compact
```
- "Kernel Extension ALLOWED: Kext ((null), com.local.RegionSpoof)" = syspolicyd OK (policy DB honored)
- "failed to load/rebuild extensions: Extension with identifiers … not approved to load" = kernelmanagerd refused (pending-dialog state / GUI approval missing)
- Error 27 from kmutil = same refusal

`syspolicyd` is NOT a launchd service on macOS 27 (`launchctl kickstart` fails with "Could not find service"); `com.apple.kernelmanagerd` IS one — but kicking it requires user approval of the command and did not get tested to completion this session.

## Tool selection by macOS version

| macOS | tool | method | SIP |
|---|---|---|---|
| ≤ 26.5 beta3 | kanshurichard/enableAppleAI | eligibility override script | can stay on |
| 27.x | SkyBlue997/enableMacosAI (RegionSpoof) | IORegistry kext CH/A→LL/A (ad-hoc arm64e) | must be off (Permissive) |

RegionSpoof kext: 20-line IOService matching IOPlatformExpertDevice, sets
`region-info`="LL/A" (32-byte OSData) + `country-of-origin`="USA". No network, no other side effects.

## Region string check
```bash
ioreg -ard1 -c IOPlatformExpertDevice | plutil -p - | grep region-info
# bytes 0x43482f41 = "CH/A" (locked); 0x4c4c2f41 = "LL/A" (spoofed US)
```

## Installation file map (enableMacosAI)
- install.sh → /Library/Extensions/RegionSpoof.kext, /Library/LaunchDaemons/com.local.regionkext.plist, /usr/local/bin/region-kext-load.sh
- LaunchDaemon runs region-kext-load.sh at boot: kmutil load → wait for LL/A → kickstart eligibilityd/modelcatalogd/modelmanagerd
- /usr/local/bin may be missing on clean machines → mkdir -p first, else the daemon silently fails
