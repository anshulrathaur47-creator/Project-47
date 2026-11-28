#!/usr/bin/env python3
"""One-command pipeline: raw clip -> finished edit in a given style.

usage: run.py INPUT --style STYLE_DIR [--work WORKDIR] [--format 9:16] [--model small] [--language en]
              [--no-cut] [--max-gap 0.35] [--cut "12-14.5"] [--matte-backend mediapipe]
              [--cta "Follow for more"] [--title "..."] [--formats 1:1,16:9] [--stop-after plan]

  --stop-after plan   : stop after writing plan.json so Claude can refine it, then run
                        render.py and finish.py yourself.
  INPUT may be "-" with --no-source for type-only/promo styles that need no speaker video.
  --clip/--image/--image2/--logo pass media to styles that use them (device-fly, product-spotlight...).

v2 (all optional):
  --genre NAME          editorial preset from genres.json (pacing, cuts, captions, loudness). Style = the skin.
  --clips A B C         several clips: assembled with timeline.py (story order) instead of a single INPUT ("-")
  --timeline spec.json  full multi-clip timeline spec (transitions, J/L cuts, speed ramps) -> timeline.py build
  --auto montage|story|highlights  auto-assemble --clips/INPUT folder (montage cuts on --music beats)
  --music track.mp3     music for auto montage (beats) and the final mix
  --reframe 9:16        face-follow reframe the INPUT before prep (track.py)
  --smart-cuts / --retakes   editor-grade autocut (quietest-point cuts, keep last take)
  --broll DIR           auto-place B-roll from a folder after the plan is made (broll.py)
  --platform NAME       loudness/delivery target for finish.py (youtube, tiktok, reels, podcast, broadcast-eu ...)
  --deliver youtube,reels  extra platform exports with deliver.py after finishing
"""
import argparse, os, subprocess, sys
import sys as _sys
for _st in (_sys.stdout, _sys.stderr):  # UTF-8 output on Windows (Devanagari logs)
    if hasattr(_st, "reconfigure"):
        _st.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("input")
ap.add_argument("--style", required=True)
ap.add_argument("--work", default="work")
ap.add_argument("--format", default=None)
ap.add_argument("--fps", default="30")
ap.add_argument("--model", default="small")
ap.add_argument("--language", default=None)
ap.add_argument("--prompt", default=None)
ap.add_argument("--no-cut", action="store_true")
ap.add_argument("--max-gap", default=None, help="pause length to cut (default: genre preset, else 0.35)")
ap.add_argument("--cut", default="")
ap.add_argument("--matte-backend", default="mediapipe")
ap.add_argument("--no-matte", action="store_true")
ap.add_argument("--no-source", action="store_true")
ap.add_argument("--duration", default=None)
ap.add_argument("--cta", default=None)
ap.add_argument("--title", default=None)
ap.add_argument("--formats", default="")
ap.add_argument("--clip", default=None, help="screen recording / product video for styles that show one")
ap.add_argument("--image", default=None)
ap.add_argument("--image2", default=None)
ap.add_argument("--logo", default=None)
ap.add_argument("--genre", default=None)
ap.add_argument("--clips", nargs="+", default=None)
ap.add_argument("--timeline", default=None)
ap.add_argument("--auto", choices=["montage", "story", "highlights"], default=None)
ap.add_argument("--music", default=None)
ap.add_argument("--reframe", default=None, help="e.g. 9:16 - face-follow reframe before prep")
ap.add_argument("--stabilize", action="store_true", help="prep: vidstab handheld stabilisation")
ap.add_argument("--denoise", choices=["light", "strong"], default=None, help="prep: video noise reduction")
ap.add_argument("--deflicker", action="store_true", help="prep: remove light flicker")
ap.add_argument("--smart-cuts", action="store_true")
ap.add_argument("--retakes", action="store_true")
ap.add_argument("--broll", default=None, help="folder of b-roll clips/images")
ap.add_argument("--platform", default=None)
ap.add_argument("--deliver", default=None, help="comma list of deliver.py presets")
ap.add_argument("--no-sequence", action="store_true", help="skip the skin's scene recipe (sequence.py)")
ap.add_argument("--stop-after", choices=["timeline", "reframe", "prep", "transcribe", "cut", "matte", "plan", "broll", "render", "finish", "qc"], default=None)
a = ap.parse_args()


def step(name, args):
    print(f"\n=== {name} ===", flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, args[0])] + args[1:])
    if r.returncode != 0:
        sys.exit(r.returncode)
    if a.stop_after == name:
        print(f"stopped after {name}"); sys.exit(0)


import json
theme = json.load(open(os.path.join(a.style, "theme.json"), encoding="utf-8"))
needs_matte = theme.get("matte") and not a.no_matte and not a.no_source

multi = a.timeline or a.clips or a.auto
if multi:
    # several clips -> one assembled timeline; downstream steps are unchanged
    if a.timeline:
        tl = ["timeline.py", "build", a.timeline, "--work", a.work, "--model", a.model]
    else:
        files = a.clips or [a.input]
        tl = ["timeline.py", "auto"] + files + ["--work", a.work, "--mode", a.auto or "story"]
        if a.format: tl += ["--format", a.format]
        if a.music: tl += ["--music", a.music]
        if a.duration: tl += ["--duration", a.duration]
        tl += ["--model", a.model]
    step("timeline", tl)
    if a.auto != "montage" and not a.timeline:  # a timeline spec already sets every in/out point
        ac = ["autocut.py", "--work", a.work] + (["--max-gap", a.max_gap] if a.max_gap else [])
        if a.no_cut: ac.append("--keep-all")
        if a.genre: ac += ["--genre", a.genre]
        if a.smart_cuts: ac.append("--smart-cuts")
        if a.retakes: ac.append("--retakes")
        step("cut", ac)
    if needs_matte:
        step("matte", ["matte.py", "--work", a.work, "--backend", a.matte_backend])
elif not a.no_source:
    src_in = a.input
    if a.reframe:
        os.makedirs(a.work, exist_ok=True)
        src_in = os.path.join(a.work, "reframed.mp4")
        step("reframe", ["track.py", "reframe", a.input, "--out", src_in, "--format", a.reframe])
    pp = ["prep.py", src_in, "--work", a.work, "--fps", a.fps]
    if a.stabilize: pp.append("--stabilize")
    if a.denoise: pp += ["--denoise", a.denoise]
    if a.deflicker: pp.append("--deflicker")
    step("prep", pp)
    tr = ["transcribe.py", "--work", a.work, "--model", a.model]
    if a.language: tr += ["--language", a.language]
    if a.prompt: tr += ["--prompt", a.prompt]
    step("transcribe", tr)
    ac = ["autocut.py", "--work", a.work] + (["--max-gap", a.max_gap] if a.max_gap else [])
    if a.no_cut: ac.append("--keep-all")
    if a.cut: ac += ["--cut", a.cut]
    if a.genre: ac += ["--genre", a.genre]
    if a.smart_cuts: ac.append("--smart-cuts")
    if a.retakes: ac.append("--retakes")
    step("cut", ac)
    if needs_matte:
        step("matte", ["matte.py", "--work", a.work, "--backend", a.matte_backend])
mp = ["make_plan.py", "--work", a.work, "--style", a.style]
if a.format: mp += ["--format", a.format]
if a.no_source: mp.append("--no-source")
if a.no_matte: mp.append("--no-matte")
if a.duration: mp += ["--duration", a.duration]
if a.cta: mp += ["--cta", a.cta]
if a.title: mp += ["--title", a.title]
for k in ("clip", "image", "image2", "logo"):
    if getattr(a, k): mp += ["--" + k, getattr(a, k)]
if a.genre: mp += ["--genre", a.genre]
plan = os.path.join(a.work, "plan.json")
if theme.get("sequence") and not a.no_sequence:   # the skin's scene recipe turns the draft into a designed edit
    step("plan-draft", mp)
    step("plan", ["sequence.py", plan, "--recipe", theme["sequence"]])
else:
    step("plan", mp)
if a.music and a.auto != "montage":
    p = json.load(open(plan, encoding="utf-8"))
    p["music"] = dict(p.get("music") or {}, src=os.path.abspath(a.music))
    json.dump(p, open(plan, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
if a.broll:
    step("broll", ["broll.py", "--work", a.work, "--library", a.broll, "--merge", plan])
step("render", ["render.py", plan])
fin = ["finish.py", plan]
if a.formats: fin += ["--formats", a.formats]
if a.platform: fin += ["--platform", a.platform]
step("finish", fin)
final = os.path.join(a.work, "final.mp4")
qc = ["qc.py", final, "--plan", plan, "--out-dir", a.work]
if a.platform: qc += ["--platform", a.platform]
step("qc", qc)          # report only (qc.py exits non-zero only with --strict)
if a.deliver:
    step("deliver", ["deliver.py", plan, "--to", a.deliver, "--out-dir", os.path.join(a.work, "deliver")])
