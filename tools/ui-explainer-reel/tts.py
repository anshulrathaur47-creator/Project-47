"""Draft voice-over with Kokoro (free, offline). Run with the animation kit's Python:

  tools/external/artemnovitckii_claude-animation-skills/kit/.venv/bin/python tools/ui-explainer-reel/tts.py lines.json out_dir [voice] [speed]

lines.json is a list of Hindi lines (Devanagari). Writes out_dir/vo.wav and out_dir/vo_lines.json (start and duration of every line).
Default voice hm_omega (Hindi male); hf_alpha / hf_beta are Hindi female voices.
"""
import json
import os
import shutil
import sys
import tempfile

import espeakng_loader
import numpy as np
import soundfile as sf
from kokoro_onnx import EspeakConfig, Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "external", "artemnovitckii_claude-animation-skills", "kit"))

data = espeakng_loader.get_data_path()
if len(data) > 100:   # espeak-ng fails on long data paths: use a short copy
    short = os.path.join(tempfile.gettempdir(), "kokoro-espeak-ng-data")
    if not os.path.exists(os.path.join(short, "phontab")):
        shutil.rmtree(short, ignore_errors=True)
        shutil.copytree(data, short)
    data = short
espeak = EspeakConfig(lib_path=espeakng_loader.get_library_path(), data_path=data)

lines = json.load(open(sys.argv[1]))
out_dir = sys.argv[2]
voice = sys.argv[3] if len(sys.argv) > 3 else "hm_omega"
speed = float(sys.argv[4]) if len(sys.argv) > 4 else 1.08
os.makedirs(out_dir, exist_ok=True)
k = Kokoro(os.path.join(KIT, "models/kokoro-v1.0.onnx"), os.path.join(KIT, "models/voices-v1.0.bin"), espeak_config=espeak)
out, meta, t, sr = [], [], 0.25, 24000
out.append(np.zeros(int(0.25 * sr), dtype=np.float32))
for i, line in enumerate(lines):
    samples, sr = k.create(line, voice=voice, speed=speed, lang="hi")
    a = np.abs(samples)
    idx = np.where(a > 0.01)[0]
    samples = samples[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.06 * sr)].astype(np.float32)
    meta.append({"i": i, "text": line, "start": round(t, 3), "dur": round(len(samples) / sr, 3)})
    out.append(samples)
    gap = 0.14 + (0.16 if line.rstrip().endswith(("?", "!")) else 0)
    out.append(np.zeros(int(gap * sr), dtype=np.float32))
    t += len(samples) / sr + gap
vo = np.concatenate(out)
sf.write(os.path.join(out_dir, "vo.wav"), vo, sr)
json.dump(meta, open(os.path.join(out_dir, "vo_lines.json"), "w"), ensure_ascii=False, indent=1)
print(f"{voice} {speed}: {len(vo) / sr:.2f}s, {len(lines)} lines")
