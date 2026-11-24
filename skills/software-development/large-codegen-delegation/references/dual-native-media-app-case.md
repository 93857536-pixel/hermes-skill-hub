# Media Converter 实战记录 (2026-08-10)

双端原生媒体转换 App(macOS SwiftUI + Windows WinUI3,FFmpeg 底层)。验证了本技能的全部要点。

## 规模
- ~70 个源文件(macOS 26 Swift + 3 XCTest + 5 scripts;Windows 26 C#/XAML + 5 ps1)
- 2 个并行子代理(deepseek-v4-pro,pin 后 unset)
- 主会话: 架构、Core 契约 JSON、图标、文档、构建接管

## 规格文件样例结构(scripts/spec-macos.md, 18KB)
```
# <目标> 完整实现规格(子代理 A 专用)
## 0. 铁律      # 只写 X 目录/可读 Y 禁改 Z/零第三方依赖/版本 pin/修错≤6轮/诚实条款
## 1. 先读      # Core/README.md(FFmpeg 参数契约) + 5 个 JSON
## 2. 目录结构  # 完整树, 含 Resources 复制规则
## 3. project.yml 要点  # bundle id/图标设置/Info.plist 键/文档类型
## 4. 各文件功能规格  # 每文件一段: 模型层/FFmpeg 服务层/视图层/冒烟测试/Scripts
## 5. 构建与测试(必须执行)  # 精确命令
## 6. 报告要求  # 文件清单/BUILD 结果原文/测试数/已知问题
```

## 委派上下文(每任务 2 行, 其余全在规格文件里)
```
工作目录 <repo>。铁律: 只写 <dir>/ 目录(...); 本机无 ffmpeg 属正常; 不得假装成功。
最终回复用中文, 控制在 400 行内。
```

## 预算耗尽接管时序(实测)
1. 批次回传 `status=completed` 但 task-0 汇报**中途截断在工具调用里**(grep 调用),`build-notes.md` 空文件
2. transcript 尾部定位: 19:22:52 测试仍有 PresetCatalogTests 失败 → 19:23:04 打了最后补丁 → 19:23:33 max_iterations 截断,无最终验证
3. 主会话接管: 读代码发现最后补丁引入 3 处同类编译错误(`[String]?` 未解包 × 2 文件、`String?` label × 2 视图),全部是"可选值未解包"机械错误
4. 3 个 patch → BUILD SUCCEEDED → 19/19 测试通过 → 冒烟测试 JSON 正常
5. 资源布局核对: PresetCatalog 期望扁平 `formats.json`,bundle `Contents/Resources/` 扁平 ✅,project.yml `resources: Resources/Core/` ✅ —— 三处一致,无需改
6. 主会话写 build-notes.md + `hermes-verify-*.sh`(build+test+smoke 断言)跑完删除

## 契约驱动双端一致(可复用模式)
- Core/ 目录: 5 个 JSON(formats/encoders/profiles/presets/settings)+ README 写死 FFmpeg 参数契约(13 条: 定位顺序/进度解析/5 模式模板/兼容矩阵/防重名/硬件编码/暂停语义/临时文件/退出码)
- 两端各自实现同一契约,行为一致;兼容矩阵交叉校验(每个 format 引用的 codec 必须存在于 encoders.json)可脚本化验证

## 验证脚本模板(hermes-verify-*.sh)
```bash
# 1) 改动文件存在性断言  2) xcodebuild build | grep "BUILD SUCCEEDED"
# 3) xcodebuild test | grep "Executed 19 tests, with 0 failures"
# 4) 冒烟 --smoke-test | grep '"formats": 11'
# 失败分支打印 error: 行头部; 结束删除脚本
```

## 其他沉淀
- 图标: 无 PIL → Swift/AppKit 离屏绘制,阴影 from-rect bug、ICO 手写容器详见 `macos-app-icons` 的 `references/programmatic-icon-pitfalls.md`
- 冒烟钩子: `--smoke-test`(环境自检 JSON)/`--smoke-convert`(真实转码管线,无 ffmpeg 时正确报 notFound)让 GUI App 可无头验证
- git 教训: .gitignore 必须在首次 `git add -A` 之前存在,否则 .venv 会被提交(本会话 561 个文件误提交,事后 `git rm -r --cached` 清理)
