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
  ffmpeg -loglevel error -i "$f" -t 12 "$T/clip.wav" &&
  python3 tools/transcribe.py "$T/clip.wav" --lang hi --no-vad --out "$T" >/dev/null && [ -s "$T/clip.srt" ]
}
t_remotion() {
  (cd tools/remotion-starter && npx remotion render ReelTest "$T/remotion.mp4" --log=error >/dev/null) && [ -s "$T/remotion.mp4" ]
}
t_hyperframes() {
  (cd tools/hyperframes-starter && npx hyperframes render -o "$T/hf.mp4" --quality draft --quiet >/dev/null) && [ -s "$T/hf.mp4" ]
}
t_three() {
  (cd tools/three-starter && npx remotion render src/index.ts Cube3D "$T/three.mp4" --gl=swangle --frames=0-5 --log=error >/dev/null) && [ -s "$T/three.mp4" ]
}
t_blender() {
  blender -b -noaudio -P tools/blender/test_scene.py -- "$T/blender.mp4" 2 >/dev/null 2>&1 && [ -s "$T/blender.mp4" ]
}
t_analyze() {
  python3 tools/analyze_style.py reel/story_reel.mp4 --name _verify --no-ocr >/dev/null 2>&1 && [ -s references/analysis/_verify/report.md ]
  local ok=$?; rm -rf references/analysis/_verify; return $ok
}
t_extskills() { [ -f .claude/skills/halo-cut/SKILL.md ] && [ -f .claude/skills/storytelling/SKILL.md ] && [ -f .claude/skills/zach-3d-films/SKILL.md ] && [ -f .claude/skills/reel-editor/SKILL.md ]; }
t_skills() { [ -f .claude/skills/hyperframes/SKILL.md ] && [ -f .claude/skills/remotion-best-practices/SKILL.md ]; }
t_videouse() {
  local H=.claude/skills/video-use/helpers V="$T/vu"
  mkdir -p "$V" && ffmpeg -loglevel error -i reel/story_reel.mp4 -t 6 -c copy "$V/C0001.mp4" &&
  python3 $H/transcribe_batch.py "$V" --language hi >/dev/null &&
  python3 $H/pack_transcripts.py --edit-dir "$V/edit" >/dev/null &&
  printf '{"version":1,"sources":{"C0001":"%s"},"ranges":[{"source":"C0001","start":0.1,"end":2.5},{"source":"C0001","start":3.0,"end":5.5}],"grade":"warm_cinematic","overlays":[],"subtitles":"%s"}' \
    "$V/C0001.mp4" "$V/edit/master.srt" > "$V/edit/edl.json" &&
  python3 $H/render.py "$V/edit/edl.json" -o "$V/edit/out.mp4" --draft --build-subtitles >/dev/null && [ -s "$V/edit/out.mp4" ]
}
t_openverse() { python3 tools/sfx.py search whoosh --source openverse -n 1; }
t_library() {
  [ "$(python3 tools/sfx.py search whoosh -n 3 | wc -l)" -ge 3 ] && [ "$(python3 tools/sfx.py search footstep -n 3 | wc -l)" -ge 3 ] &&
  [ -n "$(python3 tools/sfx.py search masti --music -n 1)" ]
}
t_freesound() {
  if [ -z "${FREESOUND_API_KEY:-}" ]; then echo "no FREESOUND_API_KEY set (optional)"; return 1; fi
  python3 tools/sfx.py search whoosh --source freesound -n 1
}
t_youtube() {
  local c=(); [ -f tools/secrets/youtube-cookies.txt ] && c=(--cookies tools/secrets/youtube-cookies.txt)
  out=$(yt-dlp "${c[@]}" --simulate -q --no-warnings "https://www.youtube.com/watch?v=jNQXAC9IVRw" 2>&1) && return 0
  if echo "$out" | grep -q "not a bot"; then
    echo "reachable, but YouTube wants a login from this server: add tools/secrets/youtube-cookies.txt"
  else echo "$out" | tail -1; fi
  return 1
}

check "FFmpeg $(ffmpeg -version | head -1 | awk '{print $3}')  (encode 1080x1920 H.264+AAC)" t_ffmpeg
check "yt-dlp $(yt-dlp --version 2>/dev/null)  (download a test video)" t_ytdlp
check "Whisper (faster-whisper, small model)  (Hindi transcript -> .srt)" t_whisper
check "Remotion  (render 1080x1920 test video)" t_remotion
check "Hyperframes  (render 1080x1920 test video)" t_hyperframes
check "3D: Remotion + three.js  (render a 3D test scene)" t_three
check "3D: Blender $(blender --version 2>/dev/null | head -1 | awk '{print $2}')  (headless Eevee render)" t_blender
check "Remotion + Hyperframes skills for Claude" t_skills
check "Style analyzer  (cuts, beats, faces, motion, colour on a test reel)" t_analyze
check "GitHub editing skills (Video Studio, artemnovitckii, rsdabid)" t_extskills
check "video-use skill  (transcribe -> cut -> grade -> subtitles render)" t_videouse
check "Local SFX/music library (253 sounds, offline)" t_library
check "Openverse music/SFX search" t_openverse
check "Freesound SFX search" t_freesound
check "yt-dlp from YouTube" t_youtube

echo
printf '%s\n' "${results[@]}"
rm -rf "$T"
