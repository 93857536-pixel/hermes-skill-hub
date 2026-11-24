# whisper.cpp CLI (whisper-cli) — embedding into an app

Verified 2026-08 on macOS (brew whisper-cpp 1.9.2, Apple Silicon). Applies when an app needs
local audio→text (e.g. transcribing listening-question audio before answering).

## Install & binary name

```bash
export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles \
       HOMEBREW_API_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles \
       HOMEBREW_NO_AUTO_UPDATE=1
brew install whisper-cpp
# binary is `whisper-cli` at /opt/homebrew/bin/whisper-cli (NOT `main`, NOT `whisper`)
ls /opt/homebrew/bin/ | grep whisper   # whisper-cli, whisper-server, whisper-bench, ...
```

`brew list | grep -i whisper` can miss it if the formula name differs — check
`/opt/homebrew/bin/whisper-cli` directly with `test -x`.

## Model: NOT auto-downloaded, default path is cwd-relative (the #1 trap)

- whisper-cli 1.9.x does **not** auto-download a missing model.
- Default `-m` is `models/ggml-base.en.bin` **relative to the CWD**. Apps launched from
  Finder/Dock have an unpredictable CWD, so the model is never found → `error: failed to
  initialize whisper context`. Symptom-free until a listening question actually arrives.
- Fix: pass `-m <abs path>` explicitly, e.g. `-m ~/.cache/whisper-cpp/ggml-base.bin`.
  A code pattern that works: check `FileManager.default.fileExists(atPath:)` and only add
  `-m` when present, but the robust version always requires the model file.

### Download (CN-friendly)

huggingface.co is often unreachable from CN; use the mirror. 148 MB for base.en:

```bash
mkdir -p ~/.cache/whisper-cpp
curl -L --progress-bar -o ~/.cache/whisper-cpp/ggml-base.bin \
  "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
```

## Format: cannot decode AIFF; transcode to 16 kHz WAV first

whisper-cli (miniaudio decoder) handles WAV/MP3/FLAC/OGG but **not AIFF** — an AIFF input
produces an empty transcript with no error. `say -o file.aiff` output is AIFF, so test
audio from `say` MUST be transcoded first:

```bash
afconvert -f WAVE -d LEI16@16000 -c 1 in.aiff in.wav   # system tool, no install
whisper-cli -m ~/.cache/whisper-cpp/ggml-base.bin -f in.wav -otxt -of out
cat out.txt
```

Non-WAV inputs (mp3/m4a) are also unreliable — the app-side pattern is: if extension !=
"wav", run afconvert to a temp `input.wav` first (args `-f WAVE -d LEI16@16000 -c 1`),
then whisper the WAV. Verified end-to-end: `say`-generated English speech → afconvert →
whisper-cli → exact transcript.

## Verification recipe

- A pure sine-wave WAV transcribes to an EMPTY result with a clean exit — that's
  expected, not a failure (no speech content). Use real speech for a meaningful test.
- Check the "loading model from '...'" line in output to confirm the model path was used,
  and `whisper_init_with_params_no_state: use gpu = 1` for Metal acceleration.
- macOS has no `timeout` command (POSIX coreutils not installed); rely on the tool
  runner's own timeout instead.
