# `windows` crate API 幻觉速查（2026-09-27 QQExporter v1.0.0 批次实锤）

LLM/子代理生成的 `#[cfg(windows)]` 代码极易写出不存在的 `windows` crate 符号。
QQExporter `src-tauri/src/core/keyscan.rs` 初版一次写错 5 处，全被 Windows CI
gate（`cargo check` 阶段）抓出；本地 mingw 交叉 check 也能抓（比等 CI 快 ~10min）。

## 幻觉 vs 真名对照（windows 0.58，版本以 Cargo.lock 为准）

| 幻觉写法 | 真名/真签名 |
|---|---|
| `VIRTUAL_MEM_INFO_64` | `MEMORY_BASIC_INFORMATION`（`Win32::System::Memory`；字段 `BaseAddress: *mut c_void` / `AllocationBase` / `AllocationProtect: PAGE_PROTECTION_FLAGS` / `PartitionId: u16` / `RegionSize: usize` / `State: VIRTUAL_ALLOCATION_TYPE` / `Protect: PAGE_PROTECTION_FLAGS` / `Type: PAGE_TYPE`；0.58 有 `Default`） |
| `Process32First(h, &mut ent)` | `Process32FirstW(h, ent: *mut PROCESSENTRY32W)` —— W 后缀；裸名 `Process32First` 收的是 ANSI `PROCESSENTRY32`（`*mut`，不是 `&mut`） |
| `Process32Next(...)` | 同上，`Process32NextW` |
| `ent.th32ProcID` | `ent.th32ProcessID` |
| `let snap = CreateToolhelp32Snapshot(...); snap.0.is_invalid()` | 该函数返 `windows_core::Result<HANDLE>`，不是 tuple，`.0` 即 E0609；`if let Ok(snap) = ...` 解包 |
| `VirtualQueryEx(h, addr as *mut _, &mut region, size)` | 第 2 参是 `Option<*const c_void>`：起始地址 0 传 `None`，非 0 传 `Some(addr as *const _)`；返回 `usize`（读到的字节数，0=结束枚举） |

## 其他伴生坑

- `PROCESSENTRY32W.szExeFile` 是 `[u16; 260]` 含尾随 NUL：做 exe 名匹配前必须先
  `position(|c| *c == 0).unwrap_or(len)` 截断再 `String::from_utf16_lossy`。
- `as` 优先级高于比较符：`addr as u64 < base` 被解析为 `addr as (u64 < base)`
  报 E0308 "interpreted as generic arguments"，须写 `(addr as u64) < base`。
- 只在 unix 分支用到的变量在 Windows 下 unused：声明处加
  `#[cfg(not(target_os = "windows"))]`（QQExporter `dbdetect.rs` 的 `HOME` 变量
  就是这么修的；Windows 段用 `USERPROFILE`/`APPDATA`）。
- 本地 toolchain 缺 target 时 `cargo tauri build --target universal-apple-darwin`
  会报 "Target x86_64-apple-darwin is not installed"——先 `rustup target add
  x86_64-apple-darwin aarch64-apple-darwin`（CI 的 macOS job 已含此步，本地首次
  构建 universal 要自己补）。

## 核实纪律（写 Windows API 前必做，不凭记忆）

```bash
# 版本先看 Cargo.lock（同机可能混 0.58/0.61 两版，grep -B15 'windows 0.61' Cargo.lock 看谁引用哪个）
grep -A3  'pub unsafe fn Process32FirstW' ~/.cargo/registry/src/*/windows-0.58.0/src/Windows/Win32/System/Diagnostics/ToolHelp/mod.rs
grep -A10 'pub struct MEMORY_BASIC_INFORMATION' ~/.cargo/registry/src/*/windows-0.58.0/src/Windows/Win32/System/Memory/mod.rs
grep -A3  'pub unsafe fn CreateToolhelp32Snapshot' ~/.cargo/registry/src/*/windows-0.58.0/src/Windows/Win32/System/Diagnostics/ToolHelp/mod.rs
```

## 修复后的本地验证（QQExporter 实测命令）

```bash
cd src-tauri
CC=x86_64-w64-mingw32-gcc AR=x86_64-w64-mingw32-ar cargo check --target x86_64-pc-windows-gnu   # 0 错 0 警告
cargo check --all-targets && cargo test                                                          # macOS 侧无回归
grep -cE 'VIRTUAL_MEM_INFO_64|th32ProcID[^e]|Process32First\(|Process32Next\(|MEM_IMAGE' src/core/keyscan.rs   # 应 0
```

## tag 触发 release 的重触发纪律（配套）

- release workflow 只在 **tag ref 被推送**时触发；修复提交推 main 不会重跑
  release。重发流程：`git push origin main`（修复 commit）→
  `git tag -f v1.0.0 && git push -f origin v1.0.0`。
- 旧 run 的 `gh run watch` 后台任务要 kill（强推后旧 run 被 cancel，但 watch
  通知会迟到误报）。
- 本地验证脚本里的 grep 路径带项目子目录（`src-tauri/src/...`），漏前缀会让
  `grep: No such file` 经 `!` 取反产生假 OK——断言前先 `ls` 确认路径存在。
