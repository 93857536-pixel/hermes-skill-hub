# WeChatExporter Audit Patterns

Session-specific notes from WeChatExporter macOS Swift audit (2026-10-22).

## Shell Injection Vector Found

**File**: `Services/AutoSyncScheduler.swift:111`
**Pattern**:
```swift
p.arguments = ["-c", args.joined(separator: " ")]
```
**Impact**: User-controlled `exportDir` or `contactIDsJSON` passed through launchctl command string. If path contains `$;|&`, arbitrary command execution occurs.

## Error Silencing Pattern

**File**: `Services/CloudBackupService.swift:334`
**Code**:
```swift
_ = try EncryptedExport.encryptDirectory(dir, password: password, to: tmp, log: { _ in })
```
**Impact**: Encryption failure (disk full, IO error) silently swallowed; upload proceeds with 0-byte file; user sees "upload complete" but server has empty backup.

## Over-Eager Cleanup

**File**: `Services/UpdateService.swift:360`
**Code**:
```swift
try? FileManager.default.removeItem(atPath: URL(fileURLWithPath: path).deletingLastPathComponent().path)
```
**Impact**: Deletes parent directory of pending .app, potentially removing other files in pending-update dir.

## Task Cancellation Gap

**File**: `ViewModels/CloudBackupViewModel.swift:204`
**Code**:
```swift
await self?.refresh()
```
**Impact**: Called inside Task block after defer sets `isUploading = false`. If task cancelled, UI shows not-busy but refresh() updates files list.

## Path String Replacement Bug

**File**: `Services/SingleFileExporter.swift:588`
**Code**:
```swift
let rel = "media/" + fileURL.path.replacingOccurrences(of: mediaRoot.path + "/", with: "")
```
**Impact**: If `mediaRoot.path` lacks trailing slash normalization, prefix replacement fails, causing 404 on embedded images.

## Process Environment Inheritance

**File**: `Services/WxCliService.swift:594`
**Code**:
```swift
process.environment = ProcessInfo.processInfo.environment
```
**Impact**: HTTP_PROXY, custom PATH, etc. inherited by wx-cli subprocess, potentially affecting its internal path resolution.

## ExportMode rawValue Case Sensitivity

**File**: `Models/ExportMode.swift:39`
**Issue**: `ExportModePreferences.mode` getter uses `rawValue` directly. Invalid case (e.g., "Categorized") silently falls back to `.categorized`.
