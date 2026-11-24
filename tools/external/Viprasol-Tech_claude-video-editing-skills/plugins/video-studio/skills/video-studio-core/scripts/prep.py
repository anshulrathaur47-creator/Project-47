#!/usr/bin/env python3
"""Normalise a raw clip: constant frame rate, upright, long side <= 1920, AAC audio.
Writes <work>/source.mp4 and <work>/audio16k.wav (for transcription).

usage: prep.py INPUT --work WORKDIR [--fps 30] [--start S] [--end E]
               [--stabilize] [--denoise light|strong] [--deflicker]

Optional clean-up a pro does before cutting (all free FFmpeg filters):
  --stabilize   two-pass vidstab (handheld shake; crops ~6% at the edges), falls back to deshake
  --denoise     hqdn3d spatial+temporal noise reduction (light for phone low light, strong for very noisy)
  --deflicker   removes mains-light flicker / exposure pumping (deflicker, 5-frame window)
"""
import argparse, os
from vs_common import run, probe, log, save_json

ap = argparse.ArgumentParser()
ap.add_argument("input")
ap.add_argument("--work", default="work")
ap.add_argument("--fps", type=float, default=30)
ap.add_argument("--start", type=float, default=None, help="trim start (s)")
ap.add_argument("--end", type=float, default=None, help="trim end (s)")
ap.add_argument("--stabilize", action="store_true")
ap.add_argument("--denoise", choices=["light", "strong"], default=None)
ap.add_argument("--deflicker", action="store_true")
a = ap.parse_args()

os.makedirs(a.work, exist_ok=True)
info = probe(a.input)
if not info["has_video"]:
    raise SystemExit("input has no video stream")
w, h = info["width"], info["height"]
scale = min(1.0, 1920 / max(w, h))
tw, th = int(w * scale) // 2 * 2, int(h * scale) // 2 * 2

src = os.path.join(a.work, "source.mp4")
cmd = ["ffmpeg", "-y", "-hide_banner"]
if a.start is not None:
    cmd += ["-ss", str(a.start)]
if a.end is not None:
    cmd += ["-to", str(a.end)]
cmd += ["-i", a.input]
if not info["has_audio"]:
    cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest"]
pre = []
if a.deflicker:
    pre.append("deflicker=size=5:mode=pm")
if a.denoise:
    pre.append("hqdn3d=2:1.5:4:3" if a.denoise == "light" else "hqdn3d=5:4:8:6")
if a.stabilize:
    trf = os.path.join(a.work, "stab.trf").replace("\\", "/").replace(":", r"\:")
    det = ["ffmpeg", "-y", "-hide_banner"] + (["-ss", str(a.start)] if a.start is not None else []) +           (["-to", str(a.end)] if a.end is not None else []) +           ["-i", a.input, "-vf", f"vidstabdetect=shakiness=6:accuracy=12:result='{trf}'", "-f", "null", "-"]
    try:
        log("stabilising: motion analysis pass")
        run(det)
        pre.append(f"vidstabtransform=input='{trf}':smoothing=18:zoom=0:optzoom=1:interpol=bicubic,unsharp=5:5:0.4")
    except SystemExit:
        log("vidstab unavailable in this FFmpeg build - using deshake")
        pre.append("deshake")
cmd += ["-vf", ",".join(pre + [f"scale={tw}:{th}:flags=lanczos,fps={a.fps},format=yuv420p"]),
        "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-g", str(int(a.fps)),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", src]
log(f"normalising {a.input} -> {src} ({tw}x{th} @ {a.fps}fps)")
run(cmd)
run(["ffmpeg", "-y", "-hide_banner", "-i", src, "-vn", "-ac", "1", "-ar", "16000", os.path.join(a.work, "audio16k.wav")])
out = probe(src)
save_json(os.path.join(a.work, "source.json"), out)
log(f"done: {out['width']}x{out['height']} {out['duration']:.2f}s")
