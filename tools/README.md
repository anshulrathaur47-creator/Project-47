# tools

Everything needed for AI video editing. Cloud sessions start fresh, so run this first each session:

```bash
bash tools/setup.sh     # installs only what's missing, then runs the checks
bash tools/verify.sh    # just the checks (prints a ✅/❌ checklist)
```

| Tool | What it's for | How to use it |
|---|---|---|
| FFmpeg | cut, join, convert, encode | `ffmpeg ...` |
| yt-dlp (+ Deno) | download videos/audio from links | `yt-dlp -o "raw-videos/%(title)s.%(ext)s" <url>` |
| Whisper | transcripts and captions (.srt/.vtt/.txt + word timings) | `python3 tools/transcribe.py <file> --lang hi --out references/` (add `--no-vad` for songs) |
| Remotion | React-based video templates | copy `tools/remotion-starter/` into `projects/<name>/`, then `npx remotion render <CompId> out.mp4` |
| Hyperframes | HTML/CSS/GSAP-based videos | copy `tools/hyperframes-starter/` into `projects/<name>/`, then `npx hyperframes render -o out.mp4` |
| `sfx.py` | search and download SFX/music from Openverse (and Freesound with a key), with credits logged | `python3 tools/sfx.py search "whoosh"`, `python3 tools/sfx.py get openverse <id>` |

Notes:
- `models/whisper-small-int8/` is the Whisper small model (CTranslate2 int8, ~250 MB). It isn't committed; `setup.sh` re-downloads and checksums it.
- Remotion and Hyperframes use the preinstalled headless Chromium (paths set in `.claude/settings.json`).
- Hyperframes loads GSAP from `assets/vendor/gsap.min.js`, because the CDN is blocked here. Its telemetry is disabled.
- Official agent skills for both live in `.agents/skills/` (linked into `.claude/skills/`).
