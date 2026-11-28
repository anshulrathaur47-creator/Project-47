#!/usr/bin/env python3
"""Finishing pass: colour grade, grain, vignette, letterbox, sound effects, ducked music,
loudness normalisation (-14 LUFS for social) and extra aspect-ratio exports.

usage: finish.py PLAN.json [--in work/composite.mp4] [--out final.mp4] [--formats 1:1,16:9]

Reads from the plan:
  "finish": {"grade": "warm", "grain": 8, "vignette": true, "letterbox": 0.1, "lut": "x.cube", "sharpen": true}
  "sfx":    [{"t": 1.2, "kind": "pop", "gain": 0.8}]     kinds: pop click ding boom whoosh swish riser type camera
  "music":  {"src": "music.mp3", "volume": 0.12, "duck": true, "start": 0}
"""
import argparse, os, tempfile
from vs_common import load_json, run, probe, log, parse_format

ap = argparse.ArgumentParser()
ap.add_argument("plan")
ap.add_argument("--in", dest="inp", default=None)
ap.add_argument("--out", default=None)
ap.add_argument("--formats", default="", help="extra exports, e.g. 1:1,16:9")
ap.add_argument("--lufs", type=float, default=None, help="override loudness target (default: platform target, -14 for social)")
ap.add_argument("--platform", default=None, help="loudness/delivery target: youtube tiktok reels shorts podcast broadcast-eu broadcast-us netflix ...")
a = ap.parse_args()

pp = os.path.abspath(a.plan); pdir = os.path.dirname(pp)
plan = load_json(pp)
work = os.path.abspath(os.path.join(pdir, plan.get("workDir", ".")))
inp = a.inp or os.path.join(work, "composite.mp4")
out = a.out or os.path.join(pdir, plan.get("outputFile", "final.mp4"))
P = lambda p: p if os.path.isabs(p) else os.path.abspath(os.path.join(pdir, p))
O = plan["output"]; W, H = O["width"], O["height"]
info = probe(inp); DUR = info["duration"]
fin = plan.get("finish", {})

# ---------- picture: grade (only if not already applied on the source in render.py), texture, legal ----------
import color as COL
vf = []
if not COL.grade_on_source(plan):
    g = (plan.get("color") or {}).get("look") or fin.get("grade", "none")
    if g not in COL.LOOK_NAMES:
        log(f"unknown grade '{g}', using none"); g = "none"
    lk = COL.look_chain(g, float((plan.get("color") or {}).get("intensity", 1.0)), W, H, work)
    if lk:
        vf.append(lk)
if fin.get("lut"):
    vf.append(COL.lut_filter(P(fin["lut"])))
vf.append(COL.texture_chain(fin, W, H))  # grain/halation/vignette/letterbox/sharpen... + legal limiter, ends yuv420p
# tag as Rec.709 SDR (FFmpeg 9 ignores -color_primaries on the CLI; untagged files shift colour on some players)
vf.append("setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv")

# ---------- audio: dialogue chain, SFX, music + ducking, loudness (audio_chain.py) ----------
from audio_chain import build_mix_graph
if a.lufs is not None:
    plan.setdefault("audio", {})["lufs"] = a.lufs
extra_inputs, af, aout = build_mix_graph(plan, info, DUR, platform=a.platform, pdir=pdir, work=work,
                                         first_input=1, src_path=inp, measured=True)
inputs = ["-i", inp] + extra_inputs
graph = f"[0:v]{','.join(vf)}[vout];\n" + ";\n".join(af)
gf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False); gf.write(graph); gf.close()
log("finishing: grade/grain/audio")
run(["ffmpeg", "-y", "-hide_banner"] + inputs + ["-filter_complex_script", gf.name, "-map", "[vout]", "-map", aout,
     "-t", str(DUR), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
     "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
os.unlink(gf.name)
log(f"final -> {out}")

for f in [x.strip() for x in a.formats.split(",") if x.strip()]:
    fw, fh = parse_format(f)
    o2 = out.replace(".mp4", f"_{fw}x{fh}.mp4")
    run(["ffmpeg", "-y", "-hide_banner", "-i", out, "-filter_complex",
         f"[0:v]split=2[a][b];[a]scale={fw}:{fh}:force_original_aspect_ratio=increase,crop={fw}:{fh},scale=iw/8:-2,gblur=sigma=6,scale={fw}:{fh},eq=brightness=-0.08[bg];"
         f"[b]scale={fw}:{fh}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]",
         "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "19", "-c:a", "copy", o2])
    log(f"extra format -> {o2}")
