# Xcode 27 Beta watchOS SDK Quirks

Verified against `/Applications/Xcode-beta.app` (Xcode 27.0, build 27A5228h, watchOS SDK). Check the actual SDK before relying on any watchOS API — this beta removed APIs that are standard in watchOS 10 docs.

## What's GONE from the watchOS SDK

- `DictationSession` (SwiftUI) — NOT in WatchOS SDK SwiftUI.swiftmodule (searched all arch swiftinterfaces: arm64_32, arm64e, armv7k).
- `@Environment(\.dictation)` — gone.
- `Speech.framework` — completely absent from WatchOS SDK `System/Library/Frameworks/` (exists in iPhoneOS SDK).
- `textSelection(.enabled)` — "unavailable in watchOS" at compile time.

## What's there instead

- Only `TextInputDictationBehavior` / `TextInputDictationActivation` (`.automatic`, `.inline(activation:)`, `.preventDictation`) — attaches to text-input views.
- `TextField` itself pops the system dictation when focused — but `textInputDictationBehavior` did NOT compile on watchOS in this beta (`value of type 'some View' has no member 'textInputDictationBehavior'` — it's iOS-only).

## Working voice-input pattern (watchOS 27 beta)

```swift
@State private var text = ""
@FocusState private var focused: Bool

TextField("输入指令…", text: $text, axis: .vertical)
    .focused($focused)

// "语音输入" button → pop the system dictation keyboard:
private func startDictation() async {
    focused = true
    try? await Task.sleep(nanoseconds: 300_000_000)
    focused = false
}
```

## How to check whether an API exists in an SDK (before writing code)

```bash
SDKW=/Applications/Xcode-beta.app/Contents/Developer/Platforms/WatchOS.platform/Developer/SDKs/WatchOS.sdk
grep -rn "DictationSession" $SDKW/System/Library/Frameworks/SwiftUI.framework/Modules/SwiftUI.swiftmodule/*.swiftinterface
ls $SDKW/System/Library/Frameworks/ | grep -i speech
```

Empty result = API does not exist in this SDK. Do this BEFORE writing the code, not after a failed build.

## Cross-check iOS SDK when something "should" exist

iOS SDK (iPhoneOS.platform) still had TextInputDictationBehavior in this beta — watchOS diverged. When an API fails on watchOS but the same project compiles for iOS, the SDKs differ; don't assume parity.
