#!/usr/bin/env bash
# Quick functional test of every tool in the workspace; prints a checklist.
#   bash tools/verify.sh
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
T=$(mktemp -d)
export REMOTION_BROWSER=${REMOTION_BROWSER:-/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell}
export HYPERFRAMES_BROWSER_PATH=${HYPERFRAMES_BROWSER_PATH:-$REMOTION_BROWSER}
results=()
check() {  # name, command...
  local name=$1; shift
  if out=$("$@" 2>&1); then results+=("✅ $name"); else results+=("❌ $name -> $(echo "$out" | tail -1)"); fi
}

t_ffmpeg() {
  ffmpeg -loglevel error -f lavfi -i testsrc2=size=1080x1920:rate=30 -f lavfi -i sine=f=440 -t 2 \
    -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$T/ff.mp4" &&
  [ "$(ffprobe -v error -select_streams v -show_entries stream=height -of csv=p=0 "$T/ff.mp4")" = 1920 ]
}
t_ytdlp() {
  yt-dlp --no-progress -q -o "$T/yt.%(ext)s" \
    "https://raw.githubusercontent.com/mediaelement/mediaelement-files/master/big_buck_bunny.mp4" && [ -s "$T/yt.mp4" ]
}
t_whisper() {
  local f="$ROOT/assets/music/ReelAudio-98423.mp3"; [ -f "$f" ] || f="$ROOT/reel/assets/ReelAudio-98423.mp3"
  ffmpeg -loglevel error -i "$f" -t 6 "$T/clip.wav" &&
  python3 tools/transcribe.py "$T/clip.wav" --lang hi --no-vad --out "$T" >/dev/null && [ -s "$T/clip.srt" ]
}
t_remotion() {
  (cd tools/remotion-starter && npx remotion render ReelTest "$T/remotion.mp4" --log=error >/dev/null) && [ -s "$T/remotion.mp4" ]
}
t_hyperframes() {
  (cd tools/hyperframes-starter && npx hyperframes render -o "$T/hf.mp4" --quality draft --quiet >/dev/null) && [ -s "$T/hf.mp4" ]
}
t_skills() { [ -f .claude/skills/hyperframes/SKILL.md ] && [ -f .claude/skills/remotion-best-practices/SKILL.md ]; }
t_openverse() { python3 tools/sfx.py search whoosh -n 1; }
t_freesound() {
  if [ -z "${FREESOUND_API_KEY:-}" ]; then echo "no FREESOUND_API_KEY set (optional)"; return 1; fi
  python3 tools/sfx.py search whoosh --source freesound -n 1
}
t_youtube() { yt-dlp --simulate -q --no-warnings "https://www.youtube.com/watch?v=jNQXAC9IVRw"; }

check "FFmpeg $(ffmpeg -version | head -1 | awk '{print $3}')  (encode 1080x1920 H.264+AAC)" t_ffmpeg
check "yt-dlp $(yt-dlp --version 2>/dev/null)  (download a test video)" t_ytdlp
check "Whisper (faster-whisper, small model)  (Hindi transcript -> .srt)" t_whisper
check "Remotion  (render 1080x1920 test video)" t_remotion
check "Hyperframes  (render 1080x1920 test video)" t_hyperframes
check "Remotion + Hyperframes skills for Claude" t_skills
check "Openverse music/SFX search" t_openverse
check "Freesound SFX search" t_freesound
check "yt-dlp from YouTube" t_youtube

echo
printf '%s\n' "${results[@]}"
rm -rf "$T"
