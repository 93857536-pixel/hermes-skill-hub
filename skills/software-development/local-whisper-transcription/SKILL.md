---
name: local-whisper-transcription
description: Use when 集成 whisper-cli/whisper.cpp 本地语音转文字(ASR)。
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [whisper, whisper.cpp, asr, speech-to-text]
    related_skills: [wechat-exporter-development, macos-app-build-packaging]
---

# 本地 Whisper 转写集成 (local-whisper-transcription)

触发: 任何 App/脚本要接入 whisper.cpp(whisper-cli / whisper-cpp brew 包)做本地语音转文字、字幕生成、会议纪要转写。

## 环境速查
- brew 安装: `brew install whisper-cpp` → 可执行 `/opt/homebrew/bin/whisper-cli`(Apple Silicon)
- 模型目录约定: `~/.cache/whisper-cpp/ggml-*.bin`
- 支持输入格式(新版 ggml 0.19+): **flac / mp3 / ogg / wav**;m4a/mp4/mov 等必须先用 AVFoundation 提取音频轨转 16kHz 单声道 WAV
- Metal 加速: 首次加载 metal 库约 8 秒(正常,不是卡死)

## 关键 CLI 参数(ggml 0.19 新版)
```
whisper-cli -m <model.bin> -l zh -ojf -of <outBase> -f <input.wav> -np
```
- `-m` 模型路径;`-l zh` 语言(默认 en!);`-ojf` 输出 full JSON(带时间戳);`-of` 输出文件前缀(实际写 `<outBase>.json`);`-np` 不打印转写过程

## ⚠️ 三个必踩的坑(实测)
1. **JSON 结构新旧版不同,必须双格式兼容**:
   - 新版(ggml 0.19+): `transcription: [{ "offsets": {"from": 0, "to": 6800}, "text": "..." }]` — **毫秒**
   - 旧版: `segments: [{ "start": 0.0, "end": 6.8, "text": "..." }]` — **秒**
   - 解析代码先试 V2(transcription/offsets/1000),再回退 V1(segments);旧文档/网文写的 segments 结构在新版上必失败
2. **whisper-cli 不会自动创建输出目录**: `-of` 指向不存在的目录时,报错写 stderr 但**退出码仍为 0**,且无输出文件 → 调用方误判成功。必须在调用前显式 `mkdir` 输出目录
3. **模型语言**: 文件名 `ggml-base.bin` 可能是 **base.en**(非多语言),`-l zh` 会被忽略并输出拼音/英文音译。中文必须用多语言模型(large-v3-turbo / medium / small 多语版)

## 模型下载
- 中文质量推荐: `ggml-large-v3-turbo-q5_0.bin`(~550MB,速度快+中文好)
- ⚠️ 国内网络直连 HuggingFace 常被区域封锁(HTTP 401 "Invalid username or password",即使公开文件、走代理也一样);hf-mirror.com 对无缓存文件 308 转发回 HF 同样 401
- 应对: 多源下载脚本(见 scripts/download_model.sh 模式)、手动浏览器下载、换网络/代理节点;App 内模型路径自动探测(依次尝试 large-v3-turbo → medium → small → base)+ 环境变量 WHISPER_MODEL / WHISPER_CLI 覆盖

## 音频格式转换(m4a/mp4/mov → wav)
- AVFoundation 方案: AVURLAsset → loadTracks(withMediaType: .audio)(macOS 13+ 是 async,同步上下文用 DispatchSemaphore 包装)→ AVAssetReader + AVAssetReaderTrackOutput(输出设置 16kHz/1ch/16bit LinearPCM)→ 手写 WAV 头(RIFF/fmt/data)+ 回填长度
- FileHandle 的 truncate/write/seek/synchronize 是 throws,需 try

## 端到端验证(交付前必做)
1. 生成真实测试音频: `say -o /tmp/t.aiff "中文测试..."` + `afconvert -f WAVE -d LEI16@16000 /tmp/t.aiff /tmp/t.wav`(say 直接写 .wav 会报 "fmt?" 失败)
2. 命令行跑一遍 whisper-cli,用真实 JSON 文件验证自己的解析器(Swift/Python 都行)——**必须看真实字段名**,不要信旧文档
3. 有 GUI 时截图验证 UI 状态流转

## 支持文件
- references/voicenotes-case.md — VoiceNotes 实战:SwiftPM 菜单栏 App 架构、GUI 自动化验证技巧(osascript/窗口截图/调试参数)、AI 多服务商 OpenAI 兼容模式
