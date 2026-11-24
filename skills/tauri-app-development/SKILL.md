---
name: tauri-app-development
description: "Build Tauri v2 apps with Rust backend + React/Vue frontend."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, windows, linux]
metadata:
  hermes:
    tags: [tauri, rust, react, typescript, cross-platform]
    related_skills: [macos-app-build-packaging, node-inspect-debugger]
---

# Tauri v2 应用开发技能

## When to Use
- 构建跨平台桌面应用（macOS/Windows/Linux）
- 需要轻量级、高性能的 Electron 替代方案
- Rust 后端 + React/Vue/Svelte 前端技术栈

## 项目结构标准模板

> 实测结论：**Tauri v2 标准布局是把整个 Rust crate 放进 `src-tauri/`**。
> 根目录只放前端（`src/`）+ `package.json` + `vite.config.ts`。
> 曾把 `Cargo.toml` 放根目录、Rust 源码放根 `src/`，结果 `generate_context!` 找不到 config、
> `crate::commands` 在 bin crate 里解析失败（bin 和 lib 是两个 crate）。

```
MyApp/
├── src-tauri/              # ← Rust crate 根（Cargo.toml 在这里）
│   ├── Cargo.toml
│   ├── build.rs            # fn main() { tauri_build::build() }
│   ├── tauri.conf.json     # v2 配置，与 Cargo.toml 同级
│   ├── capabilities/       # 权限能力配置
│   ├── icons/              # 32x32.png / 128x128.png / 128x128@2x.png / icon.icns / icon.ico
│   └── src/
│       ├── main.rs         # 仅 2 行：fn main() { myapp_lib::run(); }
│       ├── lib.rs          # pub fn run() { Builder... }
│       ├── commands/       # #[tauri::command] 集合
│       ├── models/         # serde 数据结构
│       ├── services/       # 业务逻辑
│       ├── utils/
│       └── bin/            # 可选：额外的验证/冒烟二进制
├── src/                    # 前端源码（main.tsx / App.tsx / pages/）
├── index.html              # 必须引用 /src/main.tsx
├── package.json
├── tsconfig.json
└── vite.config.ts
```

**关键**：`main.rs` 必须调用 lib 的 `run()`。若在 `main.rs` 里写 `use crate::commands::*` 会失败——
bin crate 的 `crate::` 指向 main.rs 自己，永远看不到 lib 的模块。

## 关键技术要点

### 1. Cargo.toml 双 Target 配置
```toml
[package]
name = "myapp"
edition = "2021"  # 必须 2021+ 才能用 async

[lib]
name = "myapp_lib"
crate-type = ["staticlib", "cdylib", "rlib"]

[[bin]]
name = "myapp"
path = "src/main.rs"

[dependencies]
tauri = { version = "2", features = ["tray-icon"] }
tauri-plugin-shell = "2"
tauri-plugin-dialog = "2"
tauri-plugin-fs = "2"
tauri-plugin-notification = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
anyhow = "1"
uuid = { version = "1", features = ["v4", "serde"] }
chrono = { version = "0.4", features = ["serde"] }

[build-dependencies]
tauri-build = { version = "2" }
```

### 2. Tauri **v2** 配置（v1 的 `package`/`main`/`distDir`/`window` 全部失效）

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "MyApp",
  "version": "0.1.0",
  "identifier": "com.example.myapp",
  "build": {
    "beforeDevCommand": "npm run dev",
    "devUrl": "http://localhost:5173",
    "beforeBuildCommand": "npm run build",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      { "title": "MyApp", "width": 1100, "height": 720, "minWidth": 900, "center": true }
    ],
    "security": { "csp": null }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": ["icons/32x32.png", "icons/128x128.png", "icons/128x128@2x.png", "icons/icon.icns", "icons/icon.ico"]
  }
}
```

- `frontendDist` 相对 `src-tauri/`，所以 vite 输出到根 `dist/` 时写 `"../dist"`
- `bundle.icon` 里列出的文件**必须真实存在**，否则 `generate_context!` 直接 panic
  （报 `failed to open icon .../32x32.png`），`cargo check` 就会炸

### 3. 前端构建配置
```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
```

### 4. 跨平台路径处理
```rust
#[cfg(target_os = "macos")]
pub fn get_app_data_dir() -> PathBuf {
    dirs::home_dir().unwrap().join("Library/Application Support/MyApp")
}

#[cfg(target_os = "windows")]
pub fn get_app_data_dir() -> PathBuf {
    std::env::var("APPDATA")
        .map(|p| PathBuf::from(p).join("MyApp"))
        .unwrap_or_default()
}

#[cfg(target_os = "linux")]
pub fn get_app_data_dir() -> PathBuf {
    dirs::config_dir().unwrap().join("MyApp")
}
```

## 常见陷阱与解决方案

### 陷阱 1：Rust Edition 错误
**症状**：`async fn` 报错 "not permitted in Rust 2015"
**解决**：Cargo.toml 设置 `edition = "2021"`

### 陷阱 2：Tauri 配置找不到
**症状**：`unable to read Tauri config file at tauri.conf.json because entity not found`
**解决**：配置文件必须位于 `src-tauri/` 目录

### 陷阱 3：TypeScript 大小写敏感错误（macOS）
**症状**：`Already included file name differs only in casing`
**解决**：确保导入路径大小写与实际文件名一致

### 陷阱 4：async/sync 混用
**症状**：`Result<T> is not a future`
**解决**：command 层和服务层要么都 async，要么都 sync

### 陷阱 5：模块找不到
**症状**：`cannot find 'commands' in 'crate'`
**解决**：`main.rs` 只写 `fn main() { myapp_lib::run(); }`，模块声明全放 `lib.rs`

### 陷阱 6：多加一个 bin 后 `tauri build` 报找不到主二进制
**症状**：`failed to find main binary, make sure you have a 'package > default-run' in the Cargo.toml file`
**原因**：`src-tauri/src/bin/` 下多了冒烟/工具二进制，cargo 无法确定哪个是主程序
**解决**：`Cargo.toml` 的 `[package]` 加 `default-run = "myapp"`

### 陷阱 7：`iconutil` 生成 icns 一直报 `Invalid Iconset`
**症状**：iconset 里 10 个文件名/尺寸全对，`iconutil -c icns` 仍失败
**解决**：直接手写 icns 容器（icns 就是 PNG 的 tag 容器），Python 几十行搞定：
```python
import struct, pathlib
ENTRIES = [("icon_16x16.png", b"ic11"), ("icon_32x32.png", b"ic12"),
           ("icon_128x128.png", b"ic07"), ("icon_256x256.png", b"ic08"),
           ("icon_512x512.png", b"ic09"), ("icon_16x16@2x.png", b"ic10"),
           ("icon_32x32@2x.png", b"ic13"), ("icon_128x128@2x.png", b"ic14"),
           ("icon_512x512@2x.png", b"ic15")]
recs = [tag + struct.pack(">I", 8 + len(d)) + d
        for d, tag in ((pathlib.Path(f"iconset/{f}").read_bytes(), t) for f, t in ENTRIES)]
pathlib.Path("icons/icon.icns").write_bytes(
    struct.pack(">4sI", b"icns", 8 + sum(map(len, recs))) + b"".join(recs))
```
`icon.ico` 用 PIL：`Image.open("icons/128x128.png").save("icons/icon.ico", sizes=[(16,16),(32,32),(48,48),(256,256)])`

### 陷阱 8：`State<'_, T>` 参数漏生命周期
**症状**：`implicit elided lifetime not allowed here`
**解决**：辅助函数签名写 `state: &State<'_, LauncherState>`（带 `'_`），命令签名里可以省略

### 陷阱 9：前端 `tsc` 报 `'await' expressions are only allowed within async functions`
**原因**：`await` 写在了 `setState((s) => ({...s, x: await f()}))` 这类非 async 回调里
**解决**：先 `const v = await f();` 再 `setState(s => ({...s, x: v}))`

## 构建流程

```bash
# 开发模式
npm install
npm run tauri dev

# 生产构建
npm run build              # 前端
cargo build --release      # Rust
```

## 性能对比

| 方案 | 包大小 | 内存占用 | 启动速度 |
|------|--------|----------|----------|
| Electron | ~150MB | ~300MB | 3-5s |
| Tauri v2 | ~8MB | ~30MB | 0.5-1s |
| 原生 Swift | ~20MB | ~50MB | 0.3-0.8s |

## 支持文件
- `templates/tauri-config.json` - Tauri 配置文件模板
- `templates/Cargo.toml` - Rust 依赖配置模板
- `templates/App.tsx` - React 组件模板
- `scripts/build.sh` - 一键构建脚本
- `references/build-troubleshooting.md` - 常见问题排障

## 示例项目
参考项目：`~/Programming/Projects/CraftCraftLauncher/`（Rust+Tauri2+React 的 Minecraft 启动器）
该项目的领域逻辑（Mojang API、启动流水线、Java 自动下载、端到端冒烟验证）见技能
`minecraft-launcher-development`，本技能只管 Tauri 壳与打包。

---

*创建时间: 2026-10-30*
*基于 CraftCraft Launcher 项目开发经验总结*
