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
