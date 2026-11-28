#!/usr/bin/env python3
"""Auto-switch between 2-4 synced camera angles by who is speaking (loudest mic wins).
Each camera file must contain that person's own microphone audio and start at the same moment.

usage: multicam.py camA.mp4 camB.mp4 [camC.mp4] --out work/multicam.mp4 [--min-shot 2.0] [--wide wide.mp4]
          [--audio mix.wav]   # final audio track (default: mix of all cameras)
Writes the edited video plus <out>.json with the shot list.
"""
import argparse, json, os, subprocess
import numpy as np
from vs_common import probe, run, log

ap = argparse.ArgumentParser()
ap.add_argument("cams", nargs="+")
ap.add_argument("--out", default="work/multicam.mp4")
ap.add_argument("--min-shot", type=float, default=2.0)
ap.add_argument("--wide", default=None, help="optional wide shot used when both talk or nobody talks")
ap.add_argument("--audio", default=None)
ap.add_argument("--width", type=int, default=1920)
ap.add_argument("--height", type=int, default=1080)
a = ap.parse_args()
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
SR, HOP = 16000, 0.25


def rms(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         stdout=subprocess.PIPE).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = int(SR * HOP)
    k = len(x) // n
    return np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1) + 1e-9)


levels = [rms(c) for c in a.cams]
L = min(len(x) for x in levels)
M = np.stack([x[:L] / (np.percentile(x[:L], 95) + 1e-6) for x in levels])  # normalise per mic
active = M.argmax(0)
quiet = M.max(0) < 0.15
both = (np.sort(M, 0)[-2] > 0.6 * M.max(0)) & ~quiet
shots, cur, start = [], None, 0.0
for i in range(L):
    choice = -1 if (a.wide and (both[i] or quiet[i])) else int(active[i])
    t = i * HOP
    if cur is None:
        cur, start = choice, t
    elif choice != cur and t - start >= a.min_shot:
        shots.append((cur, start, t)); cur, start = choice, t
shots.append((cur, start, L * HOP))
srcs = list(a.cams) + ([a.wide] if a.wide else [])
inputs, parts = [], []
for s in srcs:
    inputs += ["-i", s]
for k, (c, s, e) in enumerate(shots):
    idx = c if c >= 0 else len(a.cams)
    parts.append(f"[{idx}:v]trim=start={s}:end={e},setpts=PTS-STARTPTS,scale={a.width}:{a.height}:force_original_aspect_ratio=increase,crop={a.width}:{a.height},fps=30[v{k}]")
graph = ";".join(parts) + ";" + "".join(f"[v{k}]" for k in range(len(shots))) + f"concat=n={len(shots)}:v=1:a=0[v]"
if a.audio:
    inputs += ["-i", a.audio]; amap = f"{len(srcs)}:a"
    graph += ""
else:
    graph += ";" + "".join(f"[{i}:a]" for i in range(len(a.cams))) + f"amix=inputs={len(a.cams)}:normalize=0[a]"; amap = "[a]"
gf = a.out + ".graph.txt"; open(gf, "w").write(graph)
run(["ffmpeg", "-y", "-hide_banner"] + inputs + ["-filter_complex_script", gf, "-map", "[v]", "-map", amap,
     "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-c:a", "aac", "-shortest", a.out])
os.unlink(gf)
json.dump([{"cam": srcs[c if c >= 0 else len(a.cams)], "start": s, "end": e} for c, s, e in shots], open(a.out + ".json", "w"), indent=1)
log(f"{len(shots)} shots -> {a.out}")
