---
name: tts-voiceover
description: Use when generating TTS narration MP3s from text scripts.
version: 1.0.0
author: hermes-curator
license: MIT
hermes:
  tags: [tts, audio, narration, edge-tts, ffmpeg]
  related_skills: [youtube-content, bilibili-video-download]
---

# TTS Voiceover / Narration Generation

## When to Use
- User asks for text to be read aloud as audio: video narration scripts, documentary 旁白, 朗读, podcast-style multi-section reads.
- The built-in `text_to_speech` tool is for one-shot platform delivery (voice blobs on messaging platforms). For file-based, multi-segment narration with section breaks and desktop delivery, use this workflow.

## Prerequisites
- ffmpeg (brew) for concat/silence.
- edge-tts (pip, free Microsoft TTS — no API key needed):
  ```
  python3 -m venv ~/.venvs/edge-tts
  ~/.venvs/edge-tts/bin/pip install edge-tts
  ```
  Do NOT use a /tmp venv — /tmp is wiped on reboot; recreate or use a persistent dir.

## Voice selection (zh-CN narration)
- List: `edge-tts --list-voices | grep zh-CN`
- Verified useful for narration:
  - zh-CN-YunjianNeural — male, sports/novel/documentary, 庄重深情. Good default for 纪录片旁白.
  - zh-CN-YunxiNeural — male, lively/sunny.
  - zh-CN-YunyangNeural — male, news, professional/reliable.
  - zh-CN-XiaoxiaoNeural — female, news/novel, warm (更舒展明朗).
  - zh-CN-XiaoyiNeural — female, lively.
- Documentary pacing: keep same voice across all segments; `rate=-8%` (slightly slow, leaves 气口) + `pitch=-4Hz` (slightly lower) works well.

## CLI pitfall (critical, cost me a failed run)
Values that start with a minus MUST be in attached form:
```
edge-tts --voice X --rate=-8% --pitch=-4Hz -t "text" --write-media out.mp3
```
`--rate -8%` fails with `argparse error: argument --rate: expected one argument` because `-8%` is parsed as a new option flag. Same for `--pitch=-4Hz`.

## Multi-section narration with breath pauses (proven)
1. Generate one mp3 per section (`seg1.mp3` … `segN.mp3`) with identical voice/rate/pitch.
2. 0.5–0.8s silence (match edge-tts output: 24 kHz mono):
   ```
   ffmpeg -f lavfi -i anullsrc=r=24000:cl=mono -t 0.6 -c:a libmp3lame sil.mp3
   ```
3. Write a concat list interleaving `sil.mp3` between segments, then:
   ```
   ffmpeg -f concat -safe 0 -i concat.txt -c:a libmp3lame -b:a 128k final.mp3
   ```
4. Verify with `ffprobe -show_entries format=duration`, then copy the final file to ~/Desktop (user delivery preference). Don't leave deliverables only in /tmp.

Reusable script: `templates/generate_narration.py` (edit the SEGMENTS list, run with python3, get finished MP3 out).

## When user asks to "clone my voice"
- Check for a sample first: short files (<1 min) are insufficient; cloning needs ~3–5 min of clean recordings of the target speaker.
- Available providers need credentials: ElevenLabs (tts.elevenlabs + API key) or MiniMax cloned voice. If none configured, say so plainly up front, fall back to a standard neural voice tuned to the script's tone, and offer the two paths: (a) provide 3–5 min of recordings, (b) provide a cloned-voice service key.
