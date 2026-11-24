#!/usr/bin/env python3
"""Multi-section TTS narration generator (edge-tts + ffmpeg).

Usage: copy, edit SECTIONS/VOICE/RATE/PITCH/OUT below, run with python3.
Requires: edge-tts in the venv you point EDGE at, and ffmpeg on PATH.
"""
import subprocess, os, json

EDGE = os.path.expanduser("~/.venvs/edge-tts/bin/edge-tts")  # or /path/to/venv
WORKDIR = "/tmp/quanzhou-tts"  # scratch dir; copy final OUT somewhere persistent

VOICE = "zh-CN-YunjianNeural"
RATE = "-8%"     # attached form is MANDATORY when value starts with '-'
PITCH = "-4Hz"   # same rule

SEGMENTS = [
    ("晨曦·开篇", "当国庆的晨光，掠过泉州古城的天际线，我们的镜头，首先定格在了这座钟楼上。"),
    ("俯瞰·老城", "镜头缓缓升高，老城成片的红瓦屋顶，在天地间铺展开来。每一片瓦，都藏着老泉州的烟火故事。"),
    # ... add as many (label, text) pairs as needed
]

OUT = os.path.expanduser("~/Desktop/泉州古城·东西塔_旁白.mp3")
SIL_SEC = 0.6

os.makedirs(WORKDIR, exist_ok=True)
os.chdir(WORKDIR)
mp3s = []
for i, (label, text) in enumerate(SEGMENTS, 1):
    out = f"seg{i}.mp3"
    # NOTE the '=' attached flags — `--rate -8%` is an argparse error.
    args = [EDGE, "--voice", VOICE, "--rate=" + RATE, "--pitch=" + PITCH,
            "--text", text, "--write-media", out]
    subprocess.run(args, check=True)
    mp3s.append(out)
    print(f"seg{i} {label} ok ({os.path.getsize(out)}B)")

sil = "sil.mp3"
subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                "-t", str(SIL_SEC), "-c:a", "libmp3lame", sil], check=True)

with open("concat.txt", "w") as f:
    for i, m in enumerate(mp3s):
        f.write(f"file '{os.path.abspath(m)}'\n")
        if i < len(mp3s) - 1:
            f.write(f"file '{os.path.abspath(sil)}'\n")

subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt",
                "-c:a", "libmp3lame", "-b:a", "128k", OUT], check=True)

dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", OUT], capture_output=True,
                     text=True, check=True).stdout.strip()
print(f"FINAL: {OUT} ({os.path.getsize(OUT)} bytes, {dur}s)")
