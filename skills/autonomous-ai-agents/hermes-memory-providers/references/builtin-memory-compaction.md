# 内置记忆存储(MEMORY.md / USER.md)容量调优 + 无损压缩

实测环境: macOS, Hermes CLI, 2026-09-12。触发语:「能不能把这个记忆提升一下」。
适用场景: 记忆显示接近满格(如 99% — 2,199/2,200)、要扩容、要精简去重且**不允许丢事实**。

## 0. 关键概念

- 两个独立文件, 均在 `$HERMES_HOME/memories/`(默认 `~/.hermes/memories/`):
  - `MEMORY.md` — 个人笔记(agent-facing), 默认上限 `memory.memory_char_limit = 2200`
  - `USER.md` — 用户画像, 默认上限 `memory.user_char_limit = 1375`
  - 同目录有 `*.md.lock`(文件锁, 空文件, 正常存在)
- 条目不换行, 以分隔符 `\n§\n` 串联(即文件里单独一行 `§`)
- 约 2.75 字符/token(2200 ≈ 800 tokens, 1375 ≈ 500 tokens)——扩容是**每轮系统提示**的线性成本, 属缓存前缀, 命中缓存后很便宜, 但不是免费
- `memory.provider`(如 hindsight)是**外部**长期记忆, 与内置文件存储并存; 字符上限只约束内置文件存储

## 1. 扩容(两步, 只改局部配置)

```bash
hermes config get memory                                  # 先看现状
hermes config set memory.memory_char_limit 4400           # 2200 → 4400(翻倍)
hermes config set memory.user_char_limit 2750             # 1375 → 2750(翻倍)
hermes config get memory                                  # 回读确认
```

本机现状(2026-09-12 设定): 4400 / 2750。

⚠️ **上限在 agent init 时注入到 MemoryStore 实例**。正在运行的会话仍按**旧**上限校验——压缩后工具仍回报 `2,199/2,200`,这是正常的、不是没生效。
由此推出两条硬规则:
1. 新上限要**新会话**才生效(重开 hermes 或 /new)
2. 想在**当前会话内**立刻完成压缩改写, 结果必须压到**旧上限**以内(不能按新上限规划体积)

验证配置真的被读取(不依赖开新会话):

```bash
cd ~/.hermes/hermes-agent && ./venv/bin/python -c "
from tools.memory_tool import load_on_disk_store
s = load_on_disk_store(); print(s.memory_char_limit, s.user_char_limit)"
# → 4400 2750
```

`load_on_disk_store()` 读 `load_config()` 的 `memory.*`, 与 live agent 在 `agent/agent_init.py` 的构造路径一致, 所以这是真实生效证据。

## 2. 字符计数模型反推(压缩前必做)

文件字节数 ≠ 计数字符数(中文 UTF-8 每字 3 字节): MEMORY.md 曾 2990 字节但只计 2199。
计数公式(源码实证): `len("\n§\n".join(entries))`。

**反推校验**: 用旧内容按此公式算, 若与工具回报一致(2199 / 1325 精确吻合), 就能在写入前预演新文案体积, 避免被"会超限"拒绝后再返工:

```python
D = "\n§\n"
new_mem = ["条目1", "条目2", ...]
print(len(D.join(new_mem)), "chars (limit 2200)")
```

## 3. 压缩原则: 只删冗余字, 不删事实

- **同类合并**: 同主题条目合成一条(如 GLM 密钥 + deepseek-r1 限制 → 「模型/密钥」条);跨库重复的偏好只在一边保留(MEMORY 留流程,USER 留期望)
- **长条目瘦身**: 删口语化修饰、已过期的细节(如某次部署日期),但**保留** ID/路径/端口/bundle/密钥位置/命令/账号
- **指向 skill 的内容可大幅缩写**: 条目里写"详见 skill X"时, 细节留在 skill, 条目只留 3-5 个关键标识
- **模糊条目先查证再补全, 不要猜**: 原注记「CLI 坑: search 是缓存(FID 每次不同/path 旧路径), 定位以 move 返回码为准」没写是谁的 CLI。用 search_files 在 skills 里查到 `quark-drive-ops` 明确写着同样的事实 → 确认是夸克网盘, 顺手补上返回码表(0=成功 / 14001=已在目标 / 21001=找不到 / 23003=不可移)

## 4. 一次性原子改写(推荐姿势)

用**一次** `memory` 调用, `operations` 数组里**先 remove 全部旧条目、再 add 全部新条目**:

- 上限**只在最终结果**上校验, 所以中途"先清空再重建"的中间态不会触发拒绝
- 原子生效: 任一 op 匹配失败则整批不落地(不会留下半新半旧), 失败时改 old_text 重发即可
- `remove` / `replace` 的 `old_text` 用**无标点的唯一子串**(如 `NOPASSWD: ALL`、`example-user`、`Xcode 27 beta`)。中文全角逗号/冒号容易与实际字符不一致, 别把它们包进 old_text
- 不要直接 write_file 去改 `MEMORY.md` / `USER.md`: 会话内 MemoryStore 持有内存副本, 之后任何一次记忆写入都会用内存副本**重写整个文件**, 把手改内容覆盖掉。要改就走 memory 工具
- 也别手改 config.yaml(缩进错误会毁配置)——一律 `hermes config set`

## 5. 校验(必做, 用户明确要求"不丢事实")

写完读回两个文件, 把旧版逐条拆成**关键事实片段**做集合包含断言, 打印缺失项:

```python
mem = read_file("~/.hermes/memories/MEMORY.md")["content"]   # 展开成绝对路径
keys = ["GLM_API_KEY=bigmodel", "140.82.112.3", "MobileHouseArrest",
        "himalaya-imap/smtp", "aliyun-ecs-admin", "cf-credentials.json", ...]  # 40-80 个
print("缺失:", [k for k in keys if k not in mem] or "无")
```

交付结论要给三样: 前后条数 / 前后字符数(含新旧上限百分比) / 缺失事实 = 0。本机实测:

| 存储 | 条数 | 字符 | 旧上限占用 | 新上限占用 |
|---|---|---|---|---|
| MEMORY.md | 12 → 11 | 2199 → 2129 | 97% → 48% | 余量 2271 |
| USER.md | 14 → 11 | 1325 → 1139 | 96% → 41% | 余量 1611 |

## 6. 坑位小结

- 工具回报的 usage 是**当前会话上限**, 别拿它判断扩容是否成功(用第 1 节的 load_on_disk_store 判)
- `memory` 工具必须显式带 `action`; 裸调用报 `Unknown action 'None'`
- 读取文件用 read_file 会带行号前缀, 自己数条数会数错(会把 `§` 行算进去); 以工具回报的 `entry_count` 为准
- 用户偏好(实测): 执行前先给方案简报(模型/子代理/视觉), 压缩后必须给出可核验的前后数据而非"已完成"
