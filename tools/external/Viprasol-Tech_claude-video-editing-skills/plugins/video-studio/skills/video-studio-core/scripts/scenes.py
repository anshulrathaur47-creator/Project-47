#!/usr/bin/env python3
"""Shot / scene detection plus black, freeze and flash frames, in one FFmpeg pass.
Writes <work>/scenes.json:
  {"source", "duration", "fps", "threshold",
   "scenes": [{"start", "end", "score", "thumb"}],   # score = strength of the cut that opened the shot
   "black":  [{"start", "end"}], "freeze": [{"start", "end"}], "flash": [{"t", "dur"}]}

usage: scenes.py INPUT [--work W] [--threshold 0.3] [--min-shot 0.5] [--thumbs]
                       [--backend auto|ffmpeg|pyscenedetect]

  --threshold : FFmpeg scene score 0..1 that counts as a cut (0.3 hard cuts, 0.15 also catches soft ones).
  --thumbs    : writes <work>/scenes/scene_001.jpg ... (middle frame of each shot).
  PySceneDetect (pip install scenedetect) is used for the cuts when importable and --backend auto;
  black/freeze/flash always come from FFmpeg.
As a module: detect(path, threshold=0.3, min_shot=0.5) -> dict (same shape, no thumbs).
"""
import argparse, os, re, subprocess
from vs_common import probe, run, log, save_json, need

FLASH_LUMA = 60       # a flash frame is this much brighter (0-255) than the frames around it
FLASH_MAX_FRAMES = 4  # longer bright stretches are shots, not flashes


def _ffmpeg_pass(path):
    """Per-frame (time, scene_score, mean luma) plus black/freeze ranges from the FFmpeg log."""
    need("ffmpeg")
    graph = ("[0:v]scale=320:-2,format=yuv420p,split=3[a][b][c];"
             "[a]select='gte(scene,0)',signalstats,metadata=print,nullsink;"
             "[b]blackdetect=d=0.1:pix_th=0.10,nullsink;"
             "[c]freezedetect=n=-50dB:d=0.5[out]")
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-v", "info", "-i", path, "-filter_complex", graph,
                        "-map", "[out]", "-an", "-f", "null", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore")
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-1500:])
    frames, cur = [], None
    black, freeze, fz = [], [], None
    for line in p.stderr.splitlines():
        m = re.search(r"pts_time:([\d.eE+-]+)", line)
        if m and "frame:" in line:
            cur = {"t": float(m.group(1)), "score": 0.0, "y": 0.0}; frames.append(cur); continue
        m = re.search(r"lavfi\.scene_score=([\d.]+)", line)
        if m and cur is not None:
            cur["score"] = float(m.group(1)); continue
        m = re.search(r"lavfi\.signalstats\.YAVG=([\d.]+)", line)
        if m and cur is not None:
            cur["y"] = float(m.group(1)); continue
        m = re.search(r"black_start:([\d.]+) black_end:([\d.]+)", line)
        if m:
            black.append({"start": float(m.group(1)), "end": float(m.group(2))}); continue
        m = re.search(r"freeze_start: ([\d.]+)", line)
        if m:
            fz = float(m.group(1)); continue
        m = re.search(r"freeze_end: ([\d.]+)", line)
        if m and fz is not None:
            freeze.append({"start": fz, "end": float(m.group(1))}); fz = None
    return frames, black, freeze, fz


def _flashes(frames, fps):
    """Short bright bursts that return to the previous picture: not real cuts."""
    out, i, n = [], 1, len(frames)
    while i < n - 1:
        base = frames[i - 1]["y"]
        if frames[i]["y"] - base > FLASH_LUMA:
            j = i
            while j < n and j - i < FLASH_MAX_FRAMES + 1 and frames[j]["y"] - base > FLASH_LUMA / 2:
                j += 1
            if j < n and j - i <= FLASH_MAX_FRAMES and abs(frames[j]["y"] - base) < FLASH_LUMA / 2:
                out.append({"t": round(frames[i]["t"], 3), "dur": round((j - i) / fps, 3), "_i": i, "_j": j})
                i = j + 1; continue
        i += 1
    return out


def _pyscenedetect_cuts(path, threshold):
    try:
        from scenedetect import detect as sd_detect, ContentDetector
    except ImportError:
        return None
    scenes = sd_detect(path, ContentDetector(threshold=threshold * 90))  # 0.3 ~ 27 (PySceneDetect default)
    return [(s[0].get_seconds(), 1.0) for s in scenes[1:]]


def detect(path, threshold=0.3, min_shot=0.5, backend="auto"):
    info = probe(path)
    dur, fps = info["duration"], info.get("fps", 30) or 30
    frames, black, freeze, open_fz = _ffmpeg_pass(path)
    if open_fz is not None:
        freeze.append({"start": open_fz, "end": round(dur, 3)})
    flashes = _flashes(frames, fps)
    in_flash = set()
    for f in flashes:  # the flash and the return from it are not cuts
        in_flash.update(range(f.pop("_i"), f.pop("_j") + 1))
    cuts = _pyscenedetect_cuts(path, threshold) if backend in ("auto", "pyscenedetect") else None
    if cuts is None:
        if backend == "pyscenedetect":
            log("PySceneDetect not installed (pip install scenedetect); using FFmpeg")
        cuts = [(f["t"], f["score"]) for k, f in enumerate(frames) if k > 0 and f["score"] >= threshold and k not in in_flash]
    scenes, last = [], 0.0
    first_score = 0.0
    for t, sc in cuts:
        if t - last < min_shot:
            continue
        scenes.append({"start": round(last, 3), "end": round(t, 3), "score": round(first_score, 3)})
        last, first_score = t, sc
    if dur - last >= min_shot / 2 or not scenes:
        scenes.append({"start": round(last, 3), "end": round(dur, 3), "score": round(first_score, 3)})
    else:
        scenes[-1]["end"] = round(dur, 3)
    return {"source": os.path.abspath(path), "duration": round(dur, 3), "fps": fps, "threshold": threshold,
            "scenes": scenes, "black": black, "freeze": freeze, "flash": flashes}


def write_thumbs(res, outdir):
    os.makedirs(outdir, exist_ok=True)
    for k, s in enumerate(res["scenes"], 1):
        p = os.path.join(outdir, f"scene_{k:03d}.jpg")
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{(s['start'] + s['end']) / 2:.3f}", "-i", res["source"],
             "-frames:v", "1", "-vf", "scale=320:-2", "-q:v", "4", p])
        s["thumb"] = p


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--work", default="work")
    ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--min-shot", type=float, default=0.5)
    ap.add_argument("--thumbs", action="store_true")
    ap.add_argument("--backend", default="auto", choices=["auto", "ffmpeg", "pyscenedetect"])
    ap.add_argument("--out", default=None, help="default <work>/scenes.json")
    a = ap.parse_args()
    res = detect(a.input, a.threshold, a.min_shot, a.backend)
    if a.thumbs:
        write_thumbs(res, os.path.join(a.work, "scenes"))
    out = a.out or os.path.join(a.work, "scenes.json")
    save_json(out, res)
    for k, s in enumerate(res["scenes"], 1):
        print(f"  shot {k:3d}  {s['start']:8.2f} - {s['end']:8.2f}  ({s['end'] - s['start']:.2f}s)  cut score {s['score']}")
    for key in ("black", "freeze", "flash"):
        if res[key]:
            print(f"  {key}: " + ", ".join(f"{x.get('start', x.get('t'))}" + (f"-{x['end']}" if "end" in x else "") for x in res[key]))
    log(f"{len(res['scenes'])} shots -> {out}")
