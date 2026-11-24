# Tauri v2 构建排障记录

## 问题 1：Rust Edition 错误

### 症状
```
error[E0670]: `async fn` is not permitted in Rust 2015
```

### 原因
Cargo.toml 缺少 `edition = "2021"` 或错误设置为 "2015"

### 解决方案
```toml
[package]
name = "craftcraft"
version = "0.1.0"
edition = "2021"  # 添加这一行
```

### 验证
```bash
cargo check 2>&1 | grep "async fn"
# 应该没有错误
```

---

## 问题 2：Tauri 配置找不到

### 症状
```
error: unable to read Tauri config file at /path/to/project/tauri.conf.json 
because entity not found
```

### 原因
配置文件放在了项目根目录，而不是 `src-tauri/` 目录

### 解决方案
移动配置文件：
```bash
mkdir -p src-tauri
mv tauri.conf.json src-tauri/
```

### 目录结构要求
```
project/
├── src/
│   └── main.rs
├── src-tauri/
│   ├── tauri.conf.json  # 必须在这里
│   └── icons/
└── Cargo.toml
```

---

## 问题 3：TypeScript 大小写敏感错误

### 症状
```
node_modules/@types/babel__core/index.d.ts(1,34): error TS1261: 
Already included file name '/Users/.../node_modules/@types/babel__generator/...' 
differs from file name '/Users/.../node_modules/@types/babel__generator/...' 
only in casing.
```

### 原因
macOS 文件系统默认大小写不敏感，但 TypeScript 严格模式检测到大小写不一致

### 解决方案
1. 统一导入路径大小写（推荐）
2. 避免在路径中使用不同大小写的相同字母

---

## 问题 4：模块找不到

### 症状
```
error[E0433]: cannot find `commands` in `crate`
```

### 原因
`src/lib.rs` 未声明模块

### 解决方案
```rust
// src/lib.rs
pub mod commands;
pub mod models;
pub mod services;
pub mod utils;
```

---

## 问题 5：async/sync 混用

### 症状
```
error[E0277]: `Result<Vec<String>, anyhow::Error>` is not a future
```

### 原因
Tauri command 使用了 `.await`，但服务层方法是同步的

### 解决方案
**选项 A**：去掉 `.await`
```rust
#[tauri::command]
pub fn list_instances() -> Result<Vec<Instance>, String> {
    let service = InstanceService::new();
    service.list().map_err(|e| e.to_string())  // 无 .await
}
```

**选项 B**：服务层改为 async
```rust
impl InstanceService {
    pub async fn list(&self) -> Result<InstanceList> {
        // async 实现
    }
}
```

---

## 构建验证流程

```bash
# 1. 清理并重新构建
cargo clean
npm run build

# 2. 检查 Rust 编译
cargo check --lib
cargo build --bin craftcraft

# 3. 检查前端构建
npm run build
ls -la dist/

# 4. 运行测试
./target/debug/craftcraft
```

---

## 性能对比

| 方案 | 包大小 | 内存占用 | 启动速度 |
|------|--------|----------|----------|
| Electron | ~150MB | ~300MB | 3-5s |
| Tauri v2 | ~8MB | ~30MB | 0.5-1s |
| 原生 Swift | ~20MB | ~50MB | 0.3-0.8s |

Tauri 优势：使用系统 WebKit/WebView，无需捆绑 Chromium

---

*最后更新: 2026-10-30*
