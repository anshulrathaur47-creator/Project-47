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

log "video-use skill dependencies (librosa, matplotlib, requests)"
if python3 -c "import librosa, matplotlib, requests" 2>/dev/null; then echo "already installed"
else python3 -m pip install -q librosa matplotlib requests; fi

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

log "3D: Blender (headless, software OpenGL)"
if have blender; then echo "already installed"; else apt-get update -qq && apt-get install -y -qq blender; fi
if ldconfig -p | grep -q libEGL_mesa; then echo "EGL/Mesa already installed"; else apt-get update -qq && apt-get install -y -qq libegl1 libegl-mesa0 libgl1-mesa-dri; fi

log "3D: Remotion + three.js starter (from github.com/remotion-dev/template-three)"
if [ -d tools/three-starter/node_modules/@remotion/three ]; then echo "already installed"
else (cd tools/three-starter && npm install --silent); fi

log "Style analysis toolkit (scene cuts, beats, OCR, faces, motion, colour, stems, cutouts)"
if have tesseract && tesseract --list-langs 2>/dev/null | grep -q hin; then echo "tesseract already installed"
else apt-get update -qq && apt-get install -y -qq tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng; fi
ldconfig -p | grep -q libGLESv2 || apt-get install -y -qq libgles2
if python3 -c "import scenedetect, pytesseract, mediapipe, cv2, moviepy, pyloudnorm, rembg, audio_separator, audioread, fastapi, fontTools" 2>/dev/null; then echo "python packages already installed"
else python3 -m pip install -q "scenedetect[opencv-headless]" pytesseract mediapipe opencv-python-headless moviepy pyloudnorm "rembg[cpu]" "audio-separator[cpu]" audioread auto-editor fastapi uvicorn fonttools
MP="$ROOT/tools/models/mediapipe"; mkdir -p "$MP"
for u in face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task \
         image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite face_landmarker/face_landmarker/float16/1/face_landmarker.task; do
  [ -s "$MP/$(basename $u)" ] || curl -fsSL -o "$MP/$(basename $u)" "https://storage.googleapis.com/mediapipe-models/$u"
done
RB="$ROOT/tools/models/rembg"; mkdir -p "$RB"
for m in u2net isnet-general-use; do [ -s "$RB/$m.onnx" ] || curl -fsSL -o "$RB/$m.onnx" "https://github.com/danielgatis/rembg/releases/download/v0.0.0/$m.onnx"; done
UV="$ROOT/tools/models/uvr"; mkdir -p "$UV"
[ -s "$UV/UVR-MDX-NET-Inst_HQ_3.onnx" ] || curl -fsSL -o "$UV/UVR-MDX-NET-Inst_HQ_3.onnx" "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/UVR-MDX-NET-Inst_HQ_3.onnx"
echo "models ready in tools/models/{mediapipe,rembg,uvr}"

log "Testing everything"
bash tools/verify.sh
