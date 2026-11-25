# tools

Everything needed for AI video editing. Cloud sessions start fresh, so run this first each session:

```bash
bash tools/setup.sh     # installs only what's missing, then runs the checks
bash tools/verify.sh    # just the checks (prints a ✅/❌ checklist)
```

| Tool | What it's for | How to use it |
|---|---|---|
| FFmpeg | cut, join, convert, encode | `ffmpeg ...` |
| yt-dlp (+ Deno) | download videos/audio from links | `bash tools/download.sh <url> [folder]` (uses cookies from `tools/secrets/` for YouTube/Instagram if present) |
| Whisper | transcripts and captions (.srt/.vtt/.txt + word timings) | `python3 tools/transcribe.py <file> --lang hi --out references/` (add `--no-vad` for songs) |
| Remotion + three.js (3D) | Code-driven 3D scenes (React Three Fiber), from github.com/remotion-dev/template-three | `cd tools/three-starter && npx remotion render src/index.ts <CompId> out.mp4 --gl=swangle` (test comp: `Cube3D`, 1080x1920) |
| Blender 4.0 (3D) | Real 3D: models, lights, shadows, cameras, rigs, Python-scripted scenes | `blender -b -noaudio -P script.py -- out.mp4` (example: `tools/blender/test_scene.py`). Software rendering only: Eevee takes about 7 s per 1080x1920 frame, so render previews at low resolution first |
| Remotion | React-based video templates | copy `tools/remotion-starter/` into `projects/<name>/`, then `npx remotion render <CompId> out.mp4` |
| Hyperframes | HTML/CSS/GSAP-based videos | copy `tools/hyperframes-starter/` into `projects/<name>/`, then `npx hyperframes render -o out.mp4` |
| `sfx.py` | find SFX/music: the local library by default (offline), or online on Openverse/Freesound, with credits logged | `python3 tools/sfx.py search "whoosh"`, `... search "rain" --source openverse`, `python3 tools/sfx.py get openverse <id>` |
| `make_sfx.py` | regenerates the code-made SFX pack and music beds (CC0) | `python3 tools/make_sfx.py` |

Notes:
- `models/whisper-small-int8/` is the Whisper small model (CTranslate2 int8, ~250 MB). It isn't committed; `setup.sh` re-downloads and checksums it.
- Remotion and Hyperframes use the preinstalled headless Chromium (paths set in `.claude/settings.json`).
- Hyperframes loads GSAP from `assets/vendor/gsap.min.js`, because the CDN is blocked here. Its telemetry is disabled.
- Official agent skills for both live in `.agents/skills/` (linked into `.claude/skills/`).

## save_uploads.py

Copies every uploaded file into `reference-library/<date>/` for good and rebuilds `reference-library/INDEX.md`. The project hooks in `.claude/settings.json` run it on every message and at the end of every turn. Run by hand with `python3 tools/save_uploads.py`.

## analyze_style.py (reference reel analyser)

`python3 tools/analyze_style.py <video> [--name slug] [--lang hi] [--words] [--stems] [--no-ocr]`

It writes `references/analysis/<slug>/report.md`, `style.json` and `contact_sheet.jpg`:
- **Cuts and pacing:** cuts (PySceneDetect), shot lengths, cuts per minute, and the cuts in the first 3 s.
- **Beats:** tempo and beats (librosa), the share of cuts that land on a beat or an SFX hit, and loudness (LUFS).
- **Per shot:**
  - camera motion (OpenCV optical flow: static, push-in, pull-out, pan, tilt, shake)
  - shot size from faces (MediaPipe: close-up, medium, wide)
  - brightness, saturation, contrast, warmth and a 5-colour palette
  - on-screen text with position (Tesseract, hin + eng)
- `--words` adds word timings (faster-whisper).
- `--stems` splits vocals and music (UVR MDX via `audio-separator`).

Other tools from the same setup:
- `audio-separator <song> --model_filename UVR-MDX-NET-Inst_HQ_3.onnx --model_file_dir tools/models/uvr`: splits vocals and instrumental.
- `rembg` (models in `tools/models/rembg`, set `U2NET_HOME=tools/models/rembg`): cuts the subject out of a photo or frame.
- MediaPipe models in `tools/models/mediapipe`: face, face landmarks, pose and selfie segmentation (person cut-out for "text behind the person").
- `auto-editor`: removes silence and dead air from talking clips.
- `moviepy`: quick Python video edits.

## GitHub editing skills (vendored in tools/external, linked into .claude/skills)

Chosen on 2026-11-24 from the most-cited Claude video skill repos. Sources and commits are in `tools/external/SOURCES.md`.
- **Viprasol-Tech/claude-video-editing-skills ("Video Studio", about 95 skills on one engine, `video-studio-core`):**
  - halo-cut, bold-bounce, chaos-stack, hook-lab, lyric-video, music-video
  - news-desk, news-explainer, regional-devotional, wedding-india, dual-subs
  - micro-drama, clip-miner, event-recap, finishing-pro, and more
- **artemnovitckii/claude-editing-skills:** storytelling, trial-reels, behind-the-person, explainer, split-screen, orbit-reel, scene-switch and more.
  - Their transcription expects `GROQ_API_KEY`; in this workspace use local Whisper (`tools/transcribe.py`) instead.
  - The kit is set up (venv, matting model `kit/models/rvm_mobilenetv3_fp32.onnx`, GSAP).
  - `kit/transcribe.py` is patched to use local faster-whisper when there is no Groq key.
- **artemnovitckii/claude-animation-skills:** zach-3d-films, zach-d-films, low-poly, stick-figure, minecraft, kurzgesagt, map-route, graph and more (animated reels with no footage).
  - The kit is set up: `kit/node_modules` (three.js, Playwright without a browser download), the Kokoro TTS voice and Parakeet word timings in `kit/models`.
  - The engines (zach-d-films, stick-figure) are patched to launch `/opt/pw-browsers/chromium`; never run `playwright install`.
  - zach-d-films test still rendered fine (`GL=swiftshader node render.mjs stills 1.5 stills`).
- **rsdabid/claude-video-editing-skills:** reel-editor (Remotion, word-by-word captions, person cut-out) and fullscreen-talking-head-edit.
- **Catalogue of about 180 more repos:** `references/awesome-claude-video-skills/README.md`.
