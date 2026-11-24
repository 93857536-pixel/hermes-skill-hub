# 平台 gate 的 Rust 陷阱(Windows runner 才现形)

来源: hermes-agent-migrator v0.2.0 CI 排障(2026-09)。这三类 bug 本地 unix 全绿,
只有 windows-latest job 能暴露。修好表层(tauri-build 图标)后逐层现形。

## 1. 只在 unix 分支写入的 `mut` 变量 → Windows `unused_mut` 挂编译

`crates/*/src/pack.rs` 里的 `permissions: BTreeMap<String, u32>` 只在
`#[cfg(unix)]` 块里 `insert`(存文件 mode bits), Windows 下声明为 `mut` 却从不写
→ `error: variable does not need to be mutable`, `-D warnings` 下直接挂编译。
unix 分支必须 mut, 不能删; 修在声明处:

```rust
#[cfg_attr(not(unix), allow(unused_mut))]
let mut permissions: BTreeMap<String, u32> = BTreeMap::new();
```

## 2. 测试夹具 `Path::display()` 在 Windows 出反斜杠, 与 `/` 归一化引擎错配

`pathmapper` 的规则统一 `/` 形式匹配(输入也 `replace('\\','/')` 归一化),
但 `tests/integration.rs` 用 `display().to_string()`(Windows = 反斜杠)写
fixture 源路径 + 写断言 → Windows 上源路径 `C:\Users\...` 匹配不上 `/` 规则,
修复不生效, 断言必挂; unix 正斜杠所以本地永远绿。

修法(测试侧, 与引擎契约一致):
```rust
// fixture
let hs = hermes.to_string_lossy().replace('\\', "/");
// 断言
let target_str = target.to_string_lossy().replace('\\', "/");
let src_home_str = src_home.to_string_lossy().replace('\\', "/");
```
引擎侧补齐(`restore.rs` `rewrite_paths`): 输入先归一化再匹配
`let mut out = s.replace('\\', "/");`(原来 `s.to_string()`, Windows 源文件的
反斜杠路径永远修不动——这是引擎真 bug 不只测试问题)。
配一个平台无关单测固化行为(`replace` 是纯字符串逻辑, unix 上验证等价于
Windows 行为): 反斜杠输入 + `/` 规则 → 替换成功 + 边界安全
(`/Alicex` 不误匹配 `/Alice` 规则)。

## 3. 本地无法完整交叉编译 Windows target 时: 优先 mingw-w64, 兜底最小 rustc repro

**首选(2026-09-25 实测, hermes-agent-migrator v0.3.0)**: `brew install
mingw-w64` 后, GNU target 全量 `cargo check` 可通过(含 C 依赖 lzma-sys,
mingw gcc 交叉编; 类型检查全 crate 覆盖, 包括 `#[cfg(windows)]` 分支):
```bash
brew install mingw-w64        # 可能首次静默失败, 用 brew list 确认, 不行重跑
rustup target add x86_64-pc-windows-gnu
CC_x86_64_pc_windows_gnu=x86_64-w64-mingw32-gcc \
AR_x86_64_pc_windows_gnu=x86_64-w64-mingw32-ar \
  cargo check -p migrator-core -p hermes-migrator-cli --target x86_64-pc-windows-gnu
```
MSVC target 在 Mac 上因缺 MSVC C 工具链仍会被 C 依赖挡死, 不再值得折腾。

**兜底(无 mingw 或只查某段无依赖逻辑的告警)**: 把出错逻辑抽成**无外部
crate 依赖**的独立 .rs, 直接 rustc 交叉编译验证告警:

```bash
rustup target add x86_64-pc-windows-msvc
# A) 带修复, Windows target → 期望无 unused_mut warning
rustc --edition 2021 --target x86_64-pc-windows-msvc -W unused_mut repro.rs -o /tmp/a.exe
# B) 去掉修复(sed 删掉 allow 行), Windows target → 期望必现 warning
sed 's/#\[cfg_attr(not(unix), allow(unused_mut))\]//' repro.rs > repro_nofix.rs
rustc --edition 2021 --target x86_64-pc-windows-msvc -W unused_mut repro_nofix.rs -o /tmp/b.exe
# C) 带修复, 默认(unix) target → 期望零回归
rustc --edition 2021 -W unused_mut repro.rs -o /tmp/c
```
三个坑: 输出路径别用 `/dev/null`(rustc 要在 TMPDIR 建临时文件, 报
"couldn't create a temp dir: Permission denied"); Windows target 链不到
`link.exe` 属正常——告警检查发生在链接之前, 证伪/证真已足够, 不必出 exe。

## 修完的验证顺序

本地 `cargo fmt --all -- --check` + `cargo clippy -p <core> -p <cli> -- -D warnings`
+ `cargo test -p <core> -p <cli>` 三件套绿了再推; 推完挂后台看护 CI, 平台差异
(这里就是 Windows test)由 runner 做最终裁决。
