# 夸克 CLI (quarkclouddrive) 坑位与能力边界

2026-08-09 实测记录。均可在使用 `node scripts/quark-drive.cjs` 时参考。

## 1. execute_code 的 subprocess 直调报 -104

- **现象**: 在 `execute_code` 里用 `subprocess.run(["node", "scripts/quark-drive.cjs", ...])` 调用,返回 `{"code":-104,"msg":"无法识别当前 Agent 环境，禁止继续使用"}`;但在 terminal 工具里直接跑正常。
- **原因**: CLI 依赖 Hermes 平台注入的 agent 环境标识,execute_code 的裸 subprocess 不继承。
- **修复**: 一律用 `hermes_tools.terminal()`(或 terminal 工具)执行,且 `cd` 到 skill 目录:

```python
from hermes_tools import terminal
r = terminal('cd ~/.hermes/skills/quarkclouddrive && node scripts/quark-drive.cjs search --keyword "*" --session-id SID --session-input "..."', timeout=120)
```

## 2. search 无法全量枚举

- 每次最多返回 **100 条**,无分页参数,`--size` 上限 100。
- **没有 browse / list / 枚举根目录的命令** —— 网盘全量文件无法一次获取,别向用户承诺"全量整理"。
- 搜索结果排序不稳定:同名条目(FID 不同)每次搜索可能返回不同套 → 判断网盘真实全貌要以夸克 App 为准。
- 关键词匹配为主;`--keyword "*"` 可返回大量结果,`--category N` 配合类型词(图片/文档…)可分类检索。

## 3. move 限制

- 一次最多 **100 个 FID**,超过拆分多次。
- 整文件夹 move 保留内部结构(适合把散落项目目录归入分类,不破坏代码树)。

## 4. 能力边界: 无 delete、无 rename

- 命令全集只有: login/unauthorize/logout/upload/share/create-folder/move/share-detail/share-search/saveas/search/summary/qa/organize(-copy/-move)/download/update/get-user-info/resolve-agent。
- **删除文件、重命名文件只能用户在夸克 App/网页完成** —— 需要时给用户清晰指引(App 搜索名 → 重命名/删除),不要反复尝试 CLI。

## 5. 其他

- `file-organize` 仅支持个人图片/视频整理,不处理文档/代码/压缩包。
- 重名上传自动加后缀: WeChatExporter → WeChatExporter(1) → (2)… 网盘出现多个同名副本通常源于多次上传,夸克自动命名。
- 公共参数 `--session-id`(格式 `{timestamp}-{random}`,同对话复用)与 `--session-input`(用户原始提问)建议每次携带。
