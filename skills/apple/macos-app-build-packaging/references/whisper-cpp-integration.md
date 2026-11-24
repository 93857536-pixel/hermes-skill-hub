# whisper-cpp 集成（whisper-cli）实测笔记

2026-08-10 TianXueBot 听力题集成时验证。用于把 whisper 转写嵌入 macOS app（BotEngine 听力链路：下载音频 → afconvert 转 WAV → whisper-cli 转写 → LLM 答题）。
2026-08-25 VoiceNotes（言记）更新：ggml 0.19 新行为 + 国内网络模型下载实测。

## 安装

```bash
export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles \
       HOMEBREW_API_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles/api \
       HOMEBREW_NO_AUTO_UPDATE=1
brew install whisper-cpp
```

- 可执行文件是 **whisper-cli**（新版名；旧版叫 whisper-cpp/whisper，代码里候选路径都要留）。
- **模型不随包下载**（brew caveats 明确提示），必须手动下载到 `~/.cache/whisper-cpp/`：
  - 中文推荐 `ggml-large-v3-turbo-q5_0.bin`（~550MB，多语言，M2 上中文转写质量可用）
  - ⚠️ 千万别用 base.en/ggml-base.bin 转中文——非多语言模型，输出是拼音

## 三大坑（2026-08-10 实测）

1. **默认模型路径是 CWD 相对路径** `models/ggml-base.en.bin`。
   报错特征：`whisper_init_from_file_with_params_no_state: failed to open 'models/ggml-base.en.bin'`。
   任何 app/脚本调用必须显式 `-m ~/.cache/whisper-cpp/ggml-base.bin`（绝对路径），没有环境变量可配。
2. **mp3/m4a 直接喂会失败**：`read_audio_data: failed to read audio data`。
   解法：先用系统 afconvert 转 16kHz 单声道 WAV：
   ```bash
   afconvert -f WAVE -d LEI16@16000 -c 1 in.m4a out.wav
   ```
3. **Swift 侧检查文件存在**用 `FileManager.default.fileExists(atPath:)` —— 没有 `isFile(atPath:)` 方法。

## 2026-08-25 更新（ggml 0.19 新行为，VoiceNotes 实测）

### 4. 中文必须用多语言模型
`ggml-base.bin`（base.en）启动时打印 `WARNING: model is not multilingual, ignoring language and translation options`，`-l zh` 无效，中文输出成拼音（实测 "你好" → "Nihal, joshuyu..."）。选模型时看 `multilingual: true`（`-ojf` 输出 JSON 的 `model.multilingual` 字段）。

### 5. JSON 输出格式变了（-ojf）
- 新版（ggml 0.19+）：`{ "transcription": [{ "offsets": {"from": 0, "to": 6800}, "timestamps": {"from": "00:00:00,000", ...}, "text": "..." }] }` —— **offsets 单位是毫秒**
- 旧版：`{ "segments": [{ "start": 0.0, "end": 6.8, "text": "..." }] }` —— 单位是秒
- 解析必须双格式兼容（先试 V2 再试 V1），否则"同一命令换个 whisper-cli 版本就挂"

### 6. whisper-cli 不会创建输出目录
`-of <前缀>` 的父目录不存在时：stderr 报 `open: failed to open '...json' for writing`，**但退出码仍是 0** → 调用方误判成功、报"未生成结果文件"。必须在跑之前 mkdir（无论输入是 wav 还是需要提取的格式——提取分支会建目录，wav 直传分支不会，两个分支都要保证目录存在）。

### 7. 格式支持范围变了
新版 `--help` 明确：`supported audio formats: flac, mp3, ogg, wav`——**mp3 现在原生支持**；m4a/mp4 仍不支持。App 内处理 m4a/mp4 最稳的是 AVFoundation AVAssetReader（输出 16kHz 单声道 LinearPCM WAV），避免外部 afconvert 依赖；注意 AVAssetReader 的 FileHandle 方法（truncate/write/seek/synchronize）在 macOS 15+ SDK 是 throws，要 try。

### 8. 国内网络模型下载（2026-08-25 实测全链路）
- HF 直连：`401 Invalid username or password`（公开文件也拒，区域封锁；本地代理 127.0.0.1:1082 同样 401）
- hf-mirror.com：对 ggml-org/whisper.cpp 的 LFS 文件**无缓存**，308 转发到 huggingface.co → 401
- modelscope（keepitsimple/whisper.cpp 等路径）：404
- GitHub releases：whisper.cpp 的 release 只带 Windows 二进制，不带模型
- **有效兜底**：可用代理节点跑 `HTTPS_PROXY=... download_model.sh` / 手机热点 / 浏览器手动下载后放 `~/.cache/whisper-cpp/`
- 结论：下载脚本要多源 + 明确报错指引，别假设某个镜像一定可用

## 验证全链路（模拟 app 调用）

```bash
# 测试语音：say 不能直接写 wav（"Opening output file failed: fmt?"），先 aiff 再 afconvert
say -o t.aiff "这是语音转文字的测试"
afconvert -f WAVE -d LEI16@16000 t.aiff t.wav
whisper-cli -m ~/.cache/whisper-cpp/ggml-large-v3-turbo-q5_0.bin -l zh -ojf -of t_out -f t.wav -np
# 验证输出 JSON：python 检查 transcription[0].offsets.from/to（毫秒）
```

- Metal 加速正常（load_backend: MTL backend），短音频秒级完成；首次加载 metal 库约 8.5s。
- 输出参数：`-otxt -of <前缀>` → `<前缀>.txt`；`-ojf` → `<前缀>.json`（full，含 tokens）。
- 转写失败的常见误导：`-of` 前缀 + `-f` 用原文件，结果空——先确认输入已转 WAV + 输出目录存在。

## App 集成代码模式（Swift）

```swift
// 1. 非 wav/flac/mp3/ogg 先 AVAssetReader 转 16kHz mono WAV（临时目录，用完 defer 删除）
// 2. 确保输出 tmp 目录存在（whisper-cli 不自动建！）
// 3. whisper-cli -m <绝对模型路径> -l zh -ojf -of prefix -f input.wav -np
// 4. 读 prefix.json，双格式解析（transcription/offsets 毫秒 OR segments/start 秒）
// 5. Process 调用的 stdout/stderr 用 Pipe 读；-np 抑制控制台输出
```

模型路径解析：`FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".cache/whisper-cpp/ggml-large-v3-turbo-q5_0.bin")`，不存在时依次回退 medium/small/base；支持 `WHISPER_MODEL`/`WHISPER_CLI` 环境变量覆盖（跨机调试必需）。
