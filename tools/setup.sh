#!/usr/bin/env bash
# Install (only what's missing) everything this video workspace needs, then test it.
# Safe to run repeatedly; cloud sessions start fresh, so run it at the start of a session:
#   bash tools/setup.sh
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
log() { printf '\n== %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

log "FFmpeg"
if have ffmpeg && have ffprobe; then echo "already installed"; else apt-get update -qq && apt-get install -y -qq ffmpeg; fi

log "Devanagari fonts (Hindi text)"
if fc-list | grep -i "Noto Serif Devanagari" >/dev/null; then echo "already installed"; else apt-get install -y -qq fonts-noto-core; fi

log "yt-dlp + Deno (JS runtime yt-dlp needs for YouTube)"
if have yt-dlp; then echo "already installed ($(yt-dlp --version))"; else python3 -m pip install -q -U "yt-dlp[default]"; fi
if have deno; then echo "deno already installed"; else npm i -g --silent deno; fi

log "Whisper (faster-whisper)"
if python3 -c "import faster_whisper" 2>/dev/null; then echo "already installed"; else python3 -m pip install -q faster-whisper; fi
# faster-whisper 1.2.x is not compatible with PyAV >= 16
python3 -c "import av,sys; sys.exit(0 if int(av.__version__.split('.')[0]) < 16 else 1)" 2>/dev/null \
  || python3 -m pip install -q "av<16"

log "Whisper small model"
M="$ROOT/tools/models/whisper-small-int8"
SHA=ca732cb1379efc49417d028465f543d83a39de2c61f3027678de103dc404ce73
if [ -f "$M/model.bin" ] && echo "$SHA  $M/model.bin" | sha256sum -c --quiet 2>/dev/null; then
  echo "already present"
else
  # Hugging Face / OpenAI model hosts are blocked here, so use an npm mirror of the
  # same CTranslate2 int8 weights. Packages are fetched with `npm pack` (no scripts run)
  # and the joined file is checked against its published SHA-256.
  TMP=$(mktemp -d); mkdir -p "$M"
  ( cd "$TMP" && for i in 0 1 2 3; do npm pack --silent "@skillninja/shortmovie-telop-model-p$i@1.0.0" >/dev/null; done
    for f in *.tgz; do mkdir -p "x/$f"; tar -xzf "$f" -C "x/$f"; done )
  cat "$TMP"/x/*p0*/package/model.bin.part0 "$TMP"/x/*p1*/package/model.bin.part1 \
      "$TMP"/x/*p2*/package/model.bin.part2 "$TMP"/x/*p3*/package/model.bin.part3 > "$M/model.bin"
  cp "$TMP"/x/*p0*/package/{config.json,tokenizer.json,vocabulary.json,preprocessor_config.json,LICENSE} "$M/"
  rm -rf "$TMP"
  echo "$SHA  $M/model.bin" | sha256sum -c || { echo "checksum mismatch, removing"; rm -f "$M/model.bin"; }
fi

log "Remotion starter"
if [ -d tools/remotion-starter/node_modules/remotion ]; then echo "already installed"
else (cd tools/remotion-starter && npm ci --silent); fi

log "Hyperframes starter"
if [ -d tools/hyperframes-starter/node_modules/hyperframes ]; then echo "already installed"
else (cd tools/hyperframes-starter && npm ci --silent); fi
npx --yes hyperframes@0.9.45 telemetry disable >/dev/null 2>&1 || true

log "Testing everything"
bash tools/verify.sh
