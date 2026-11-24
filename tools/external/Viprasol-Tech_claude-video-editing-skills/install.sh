#!/usr/bin/env bash
# Installs all Video Studio skills into ~/.claude/skills (Claude Code personal skills)
set -e
DEST="${1:-$HOME/.claude/skills}"
SRC="$(cd "$(dirname "$0")" && pwd)/plugins/video-studio/skills"
mkdir -p "$DEST"
for d in "$SRC"/*/; do n=$(basename "$d"); rm -rf "$DEST/$n"; cp -r "$d" "$DEST/$n"; echo "installed $n"; done
echo
echo "Now install the tools once:"
echo "  pip install faster-whisper playwright numpy pillow opencv-contrib-python mediapipe fastapi uvicorn fonttools"
echo "  python -m playwright install chromium"
echo "  and FFmpeg (macOS: brew install ffmpeg | Linux: sudo apt install ffmpeg)"
echo "Check: python \"$DEST/video-studio-core/scripts/check_env.py\""
