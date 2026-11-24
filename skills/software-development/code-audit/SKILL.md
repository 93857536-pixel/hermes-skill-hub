---
name: code-audit
description: "Systematic code audit for bug discovery."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [audit, code-review, bug-discovery, security, reliability]
    related_skills: [systematic-debugging, subagent-driven-development, codebase-inspection]
---

# Code Audit Skill

Systematic code audit for discovering real, reproducible bugs in a codebase. Focus on user-facing impact and verifiable code paths.

## When to Use

- User asks for code audit / bug hunting / reliability review
- Security review requested without explicit vulnerability scanning tooling
- Pre-release checklist for production-critical systems
- Subagent delegated task: "find all bugs in X"

**Do NOT use for**: simple code review (PR feedback), style checking, or LOC counting (use `codebase-inspection`).

## Audit Methodology

### Phase 1: Scope & Triage (Fast)

1. **Locate the repo** — `find <repo-root>/Sources -name "*.swift"` (or language equivalent)
2. **Count scope** — `wc -l Sources/**/*.swift` to understand size
3. **Check HEAD state** — `git log --oneline -3 && git status --short` to know if repo is clean
4. **Verify compile baseline** — `swift build -c release 2>&1 | tail -5` (capture PASS/FAIL before starting)

### Phase 2: Targeted Reading (Layered)

Read files in priority order, not alphabetical:

| Priority | Category | Typical Files |
|----------|----------|---------------|
| HIGH | File I/O + deletion | EncryptedExport.swift, MediaOrganizer.swift, UpdateService.swift |
| HIGH | Process execution | WxCliService.swift, AutoSyncScheduler.swift, DatImageDecoder.swift |
| HIGH | Credential handling | KeyCaptureService.swift, CryptoService.swift |
| MED | Network + retry | CloudBackupService.swift, DiagnosticUploader.swift |
| MED | Concurrency + actors | CloudBackupViewModel.swift, AppViewModel.swift |
| LOW | UI state | Views/*.swift, Models/*.swift |

**Read pattern**: First 100 lines → last 100 lines → middle on-demand. Large files (>50K chars) read in chunks.

### Phase 3: Pattern Search (Parallel)

Run these searches concurrently across the target directory:

```bash
# Data destruction
grep -rn "removeItem\|removeItemAtPath\|removeAllFiles" Sources/

# Silent error swallowing
grep -rn "_ = try\|try?\|catch { return false\|catch { return nil" Sources/

# Process injection risk
grep -rn 'joined(separator:' Sources/ | grep -i "sh\|bash\|launchctl\|script"
grep -rn 'process\.environment\s*=' Sources/

# Concurrency hazards
grep -rn "Task\.sleep\|DispatchQueue.*async" Sources/
grep -rn "@MainActor" Sources/ | head -30

# Path handling
grep -rn "\.path\b" Sources/ | grep -v "//\|test\|comment"

# Client↔server contract drift (see Pitfall 7) — client call sites vs registered routes
grep -rhoE '"/[a-z0-9/_-]+"' <client>/ | sort -u          # endpoints the client calls
grep -rhoE "\.(get|post|patch|put|delete)\('/[a-z0-9/:-]+'" <server>/routes/ | sort -u
grep -rn "app\.use('/" <server>/                          # verify every router is actually mounted
```

### Phase 4: Bug Classification

Classify each finding by severity:

| Severity | Criteria | Examples |
|----------|----------|----------|
| **HIGH** | User data loss, privilege escalation, arbitrary code execution | Shell injection, silent delete of user directories |
| **MED** | Wrong output, degraded UX, partial data loss | Error swallowed, race condition on UI state |
| **LOW** | Minor edge case, non-reproducible in practice, cosmetic | Case-sensitive enum fallback, verbose logging |

### Phase 5: Verification

For each bug report:
1. **Confirm line number** — `read_file(path, offset=line_no-5, limit=10)`
2. **Confirm pattern exists** — search for the triggering condition
3. **Trace call path** — find who calls the buggy function
4. **Document repro steps** — minimal path to trigger

## Output Format

Return compact JSON:

```json
{
  "bugs": [
    {
      "file": "path/to/File.swift",
      "line": 123,
      "severity": "high|med|low",
      "title": "Short title ≤ 50 chars",
      "detail": "Description ≤ 300 chars with trigger path",
      "suggested_fix": "One-line fix suggestion"
    }
  ],
  "compile": "PASS|FAIL",
  "notes": "Brief summary"
}
```

## Critical Pitfalls

### Pitfall 1: Don't Report Ledger Bugs
If user provides an existing bug ledger (like "14 台账 bug"), skip those. Only report NEW bugs not in the ledger.

### Pitfall 2: Shell Injection via Joined Strings
Any place that does `args.joined(separator: " ")` and passes to `/bin/sh -c` is a shell injection vector. Common in:
- Launchd plist management (`AutoSyncScheduler.swift`)
- CLI argument building (`WxCliService.swift`)
- Script generation (`UpdateService.swift` replaceApp)

**Fix**: Use `process.executableURL` directly with argument array, never `/bin/sh -c`.

### Pitfall 3: `_ = try` in Async Context
```swift
_ = try await someAsyncFunction() // SILENT FAILURE
```
This discards all errors including network failures, IO errors, and authentication errors. In backup/upload flows, this means "success" UI while server receives empty/invalid data.

**Fix**: Remove `_ =` prefix; let errors propagate.

### Pitfall 4: Parent Directory Deletion
```swift
FileManager.default.removeItem(atPath: URL(fileURLWithPath: path).deletingLastPathComponent().path)
```
This deletes the parent DIRECTORY, not just the file. If `path` points to `/app/MyApp.app`, this deletes the entire `pending-update-v2.0/` directory.

**Fix**: Delete only the specific path: `removeItem(atPath: path)`.

### Pitfall 5: Task Cancellation After Work
In `Task { ... }` blocks on @MainActor ViewModels, calling `await refresh()` or other side effects after the task may have been cancelled causes inconsistent UI state.

**Fix**: Add `if Task.isCancelled { return }` before side effects.

### Pitfall 6: String Path Prefix Matching
```swift
let rel = "media/" + fileURL.path.replacingOccurrences(of: mediaRoot.path + "/", with: "")
```
If `mediaRoot.path` doesn't end with `/`, the replacement won't match and `rel` will be incorrect.

**Fix**: Ensure consistent path formatting or use `URL.standardizedFileURL` before comparison.

### Pitfall 7: Client Calls an Endpoint the Server Never Implemented (contract drift)

Real case: iOS client called `POST /keys/import-package` while the server router only had `/export-package`. Because the call site was written `_ = try await request(...) as R`, every failure was swallowed → the feature silently never worked, for months, with zero user-visible error.

Reading only server code can never find this. **Do a contract diff**:
1. Extract every client request path: `grep -rn 'request("' <client>/ | grep -o '"/[^"]*"' | sort -u`
2. Extract every registered route: `grep -rnE "\.(get|post|patch|put|delete)\('/" <server>/routes/`
3. Diff the two sets — paths present client-side but absent server-side (or with a different method) are silent-failure bugs.

Same class in reverse: a route that exists but is **never mounted** (`app.use('/api/x', xRouter)` missing) — file present ≠ route live.

### Pitfall 8: A "Feature" That Is Actually a Privacy Leak

Real case: the WS `presence` frame shipped `onlineIps` (deduped count of members' real IPs) as a "X users online" feature — meaning **every room member received every other member's real IP**. Nobody classified it as a bug because it had a product rationale.

When auditing any broadcast/presence/telemetry payload, ask per field: *who receives this, and what does it reveal about the subject?* IPs, device ids, precise timestamps, read-state, and "last seen" are the usual offenders.

### Pitfall 9: Global Auth Middleware Makes the 401-vs-404 Probe Useless

`router.use(authRequired)` runs **before** route matching, so `/api/x/anything` returns 401 for nonexistent paths too. So "401 means the new endpoint deployed" is false on any router with a global auth guard — a fresh route and a typo'd path look identical.

Better deployment-verification probes, in order of strength:
1. **Artifact hash match**: deployed file `Get-FileHash`/`shasum` == local build output (strongest).
2. Authenticated call using a token you mint server-side (sign with the service's own secret against `127.0.0.1`) — avoids real SMS/email/third-party side effects.
3. `node --check` pass + process uptime reset (proves syntax + restart only, not route presence).

## Verification Checklist

Before finalizing audit report:
- [ ] All bugs verified with `read_file` at reported line numbers
- [ ] No bugs duplicate existing ledger (cross-check with user-provided list)
- [ ] Compile state captured: `swift build -c release 2>&1 | tail -3`
- [ ] Each bug has a clear trigger path
- [ ] Severity classification is defensible
- [ ] `detail` field ≤ 300 characters
- [ ] Client↔server contract diffed (Pitfall 7) — no client-called endpoints missing server-side
- [ ] Every broadcast/telemetry payload field justified against Pitfall 8 (who receives it, what it reveals)
- [ ] Ad-hoc verification scripts use **positive** assertions only: if one check reports FAIL while everything else passes, suspect the assertion (an inverted "should not exist" helper is the usual culprit) before suspecting the code

## Tools Reference

| Tool | Purpose |
|------|---------|
| `search_files(pattern, path, output_mode='content')` | Find code patterns |
| `read_file(path, offset, limit)` | Read specific file sections |
| `terminal(command)` | Run grep, swift build, git commands |
| `execute_code(code)` | Write verification scripts |

## Example Session: WeChatExporter Swift Audit

See `references/wechatexporter-audit-2026-10.md` for patterns discovered in a recent macOS Swift code audit:
- Shell injection via `args.joined(separator: " ")` + `/bin/sh -c` (HIGH)
- Silent error swallowing with `_ = try` in async upload flow (MED)
- Parent directory deletion instead of file deletion (MED)
- Task cancellation gap in @MainActor ViewModel (MED)
- Path string replacement bug due to missing trailing slash normalization (MED)
- Process environment inheritance affecting subprocess behavior (LOW)
- ExportMode rawValue case sensitivity edge case (LOW)
