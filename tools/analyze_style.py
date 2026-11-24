#!/usr/bin/env python3
"""Analyse a reference reel's editing style in one go and write a report.

What it measures:
  cuts      - every cut (PySceneDetect), shot lengths, cuts per minute, pacing curve
  beats     - tempo and beats (librosa); how many cuts land on a beat
  motion    - per shot: static / push-in / pull-out / pan / tilt / shake (optical flow)
  framing   - per shot: face count and size, so close-up / medium / wide (MediaPipe)
  colour    - per shot: brightness, contrast, saturation, warmth, 5-colour palette
  text      - on-screen text with time and position (Tesseract, Hindi + English)
  audio     - loudness (LUFS), silences, sudden hits (likely SFX)
  speech    - optional word timings (faster-whisper) with --words
  stems     - optional vocals / music split (UVR MDX via audio-separator) with --stems
  sheet     - a contact sheet with one frame per shot

Output: references/analysis/<name>/ with report.md, style.json, contact_sheet.jpg (and stems/).

Usage:
  python3 tools/analyze_style.py <video> [--name slug] [--lang hi] [--words] [--stems] [--no-ocr]
"""
import argparse
import json
import os
import re
import subprocess
import sys

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS = os.path.join(ROOT, "tools", "models")


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    out = json.loads(sh(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path]).stdout)
    v = next(s for s in out["streams"] if s["codec_type"] == "video")
    num, den = (v.get("avg_frame_rate") or "30/1").split("/")
    return {"duration": float(out["format"]["duration"]), "width": int(v["width"]), "height": int(v["height"]),
            "fps": float(num) / max(1.0, float(den)), "has_audio": any(s["codec_type"] == "audio" for s in out["streams"])}


# ------------------------------------------------------------------ cuts
def detect_cuts(path):
    from scenedetect import ContentDetector, detect
    scenes = detect(path, ContentDetector(threshold=27.0, min_scene_len=6), show_progress=False)
    raw = [(s[0].seconds, s[1].seconds) for s in scenes]
    # flashes and whip-pans read as tiny extra "shots": fold anything under 0.4 s into the shot before it
    out = []
    for a, b in raw:
        if out and b - a < 0.4:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


# ------------------------------------------------------------------ audio
def load_mono(path, sr=22050):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32), sr


def audio_profile(path):
    import librosa
    import pyloudnorm
    y, sr = load_mono(path)
    if len(y) < sr:
        return {}
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_t = librosa.frames_to_time(beats, sr=sr).tolist()
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
    # sudden hits: onset peaks well above the median
    peaks = librosa.util.peak_pick(onset_env, pre_max=6, post_max=6, pre_avg=20, post_avg=20, delta=float(np.median(onset_env) * 2.5), wait=8)
    hits = librosa.frames_to_time(peaks, sr=sr).round(2).tolist()
    silent = rms < max(1e-4, float(np.percentile(rms, 10)) * 1.2)
    sil, start = [], None
    for t, s in zip(times, silent):
        if s and start is None:
            start = t
        if not s and start is not None:
            if t - start > 0.35:
                sil.append([round(float(start), 2), round(float(t), 2)])
            start = None
    meter = pyloudnorm.Meter(sr)
    try:
        lufs = float(meter.integrated_loudness(y.astype(np.float64)))
    except Exception:
        lufs = None
    return {"tempo_bpm": round(float(np.atleast_1d(tempo)[0]), 1), "beats": [round(b, 2) for b in beat_t], "hits": hits,
            "silences": sil, "lufs": None if lufs is None or not np.isfinite(lufs) else round(lufs, 1)}


# ------------------------------------------------------------------ per-shot visual analysis
class FaceFinder:
    def __init__(self):
        self.det = None
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions, vision
            p = os.path.join(MODELS, "mediapipe", "blaze_face_short_range.tflite")
            if os.path.exists(p):
                self.mp = mp
                self.det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(base_options=BaseOptions(model_asset_path=p), min_detection_confidence=0.5))
        except Exception as e:  # noqa: BLE001
            print("face detection off:", e, file=sys.stderr)

    def faces(self, rgb):
        if self.det is None:
            return []
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        h, w = rgb.shape[:2]
        out = []
        for d in self.det.detect(img).detections:
            b = d.bounding_box
            out.append({"x": (b.origin_x + b.width / 2) / w, "y": (b.origin_y + b.height / 2) / h, "h": b.height / h})
        return out


def shot_scale(faces):
    if not faces:
        return "no face"
    hmax = max(f["h"] for f in faces)
    if hmax > 0.35:
        return "extreme close-up"
    if hmax > 0.18:
        return "close-up"
    if hmax > 0.08:
        return "medium"
    return "wide"


def colour_stats(bgr):
    small = cv2.resize(bgr, (96, int(96 * bgr.shape[0] / bgr.shape[1])))
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV).astype(np.float32)
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).astype(np.float32)
    px = small.reshape(-1, 3).astype(np.float32)
    k = 5
    _, labels, centers = cv2.kmeans(px, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.ravel(), minlength=k)
    order = np.argsort(-counts)
    palette = ["#%02x%02x%02x" % tuple(int(c) for c in centers[i][::-1]) for i in order]
    return {"brightness": round(float(hsv[..., 2].mean() / 255), 2), "saturation": round(float(hsv[..., 1].mean() / 255), 2),
            "contrast": round(float(lab[..., 0].std() / 128), 2), "warmth": round(float((lab[..., 2].mean() - 128) / 128), 2), "palette": palette}


def camera_motion(frames):
    """Classify motion across a shot from sparse optical flow between sampled frames."""
    if len(frames) < 2:
        return "static", 0.0
    zs, dxs, dys, jit = [], [], [], []
    for a, b in zip(frames[:-1], frames[1:]):
        ga, gb = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
        pts = cv2.goodFeaturesToTrack(ga, 200, 0.01, 8)
        if pts is None or len(pts) < 10:
            continue
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(ga, gb, pts, None)
        ok = st.ravel() == 1
        if ok.sum() < 8:
            continue
        m, _ = cv2.estimateAffinePartial2D(pts[ok], nxt[ok])
        if m is None:
            continue
        s = float(np.hypot(m[0, 0], m[1, 0]))
        h, w = ga.shape
        zs.append(s - 1)
        dxs.append(m[0, 2] / w)
        dys.append(m[1, 2] / h)
    if not zs:
        return "static", 0.0
    z, dx, dy = float(np.sum(zs)), float(np.sum(dxs)), float(np.sum(dys))
    jitter = float(np.std(dxs) + np.std(dys)) if len(dxs) > 2 else 0.0
    energy = abs(z) + abs(dx) + abs(dy)
    if jitter > 0.02 and jitter > energy * 0.5:
        return "handheld shake", round(energy, 3)
    if energy < 0.03:
        return "static", round(energy, 3)
    if abs(z) >= max(abs(dx), abs(dy)):
        return ("push-in" if z > 0 else "pull-out"), round(energy, 3)
    if abs(dx) >= abs(dy):
        return ("pan left" if dx > 0 else "pan right"), round(energy, 3)
    return ("tilt up" if dy > 0 else "tilt down"), round(energy, 3)


def ocr_text(bgr, lang):
    try:
        import pytesseract
    except Exception:
        return []
    h, w = bgr.shape[:2]
    scale = 1080 / max(1, w)
    img = cv2.resize(bgr, (int(w * scale), int(h * scale))) if scale > 1.05 else bgr
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    out = []
    for g in (gray, 255 - gray):
        data = pytesseract.image_to_data(g, lang=lang, config="--psm 11", output_type=pytesseract.Output.DICT)
        for i, txt in enumerate(data["text"]):
            txt = txt.strip()
            if len(txt) < 2 or float(data["conf"][i]) < 60 or not re.search(r"\w", txt):
                continue
            out.append({"text": txt, "y": round((data["top"][i] + data["height"][i] / 2) / img.shape[0], 2),
                        "size": round(data["height"][i] / img.shape[0], 3)})
    seen, uniq = set(), []
    for o in out:
        if o["text"] not in seen:
            seen.add(o["text"])
            uniq.append(o)
    return uniq


def grab(cap, t, fps):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
    ok, f = cap.read()
    return f if ok else None


def analyse_shots(path, shots, info, lang, do_ocr):
    cap = cv2.VideoCapture(path)
    ff = FaceFinder()
    res, thumbs = [], []
    for i, (a, b) in enumerate(shots):
        d = b - a
        ts = [a + d * k for k in (0.1, 0.35, 0.6, 0.9)] if d > 0.3 else [a + d / 2]
        frames = [f for f in (grab(cap, t, info["fps"]) for t in ts) if f is not None]
        if not frames:
            continue
        mid = frames[len(frames) // 2]
        small = [cv2.resize(f, (320, int(320 * f.shape[0] / f.shape[1]))) for f in frames]
        motion, energy = camera_motion(small)
        faces = ff.faces(cv2.cvtColor(mid, cv2.COLOR_BGR2RGB))
        row = {"shot": i + 1, "start": round(a, 2), "end": round(b, 2), "dur": round(d, 2), "motion": motion, "motion_energy": energy,
               "scale": shot_scale(faces), "faces": [{k: round(v, 2) for k, v in f.items()} for f in faces], **colour_stats(mid)}
        if do_ocr:
            row["text"] = ocr_text(mid, lang)
        res.append(row)
        thumbs.append((row, mid))
    cap.release()
    return res, thumbs


def contact_sheet(thumbs, out):
    from PIL import Image, ImageDraw
    if not thumbs:
        return
    tw = 180
    cols = 8
    th = int(tw * thumbs[0][1].shape[0] / thumbs[0][1].shape[1])
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 34)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (row, f) in enumerate(thumbs):
        im = Image.fromarray(cv2.cvtColor(cv2.resize(f, (tw, th)), cv2.COLOR_BGR2RGB))
        x, y = (i % cols) * tw, (i // cols) * (th + 34)
        sheet.paste(im, (x, y))
        d.text((x + 3, y + th + 2), f"#{row['shot']} {row['start']:.1f}s {row['dur']:.1f}s", fill="black")
        d.text((x + 3, y + th + 16), f"{row['scale']}, {row['motion']}"[:30], fill="#444")
    sheet.save(out, quality=85)


# ------------------------------------------------------------------ report
def summarise(info, shots, rows, audio):
    durs = np.array([r["dur"] for r in rows]) if rows else np.array([info["duration"]])
    cut_times = [r["start"] for r in rows[1:]]
    on_beat = None
    if audio.get("beats") and cut_times:
        beats = np.array(audio["beats"])
        near = [np.min(np.abs(beats - c)) < 0.09 for c in cut_times]
        on_beat = round(100 * float(np.mean(near)), 0)
    hits_on_cut = None
    if audio.get("hits") and cut_times:
        hits = np.array(audio["hits"])
        hits_on_cut = round(100 * float(np.mean([np.min(np.abs(hits - c)) < 0.12 for c in cut_times])), 0)
    count = lambda key: {k: sum(1 for r in rows if r[key] == k) for k in sorted({r[key] for r in rows})}  # noqa: E731
    return {
        "duration": round(info["duration"], 2), "size": f'{info["width"]}x{info["height"]}', "fps": round(info["fps"], 2),
        "shots": len(rows), "cuts_per_min": round(60 * max(0, len(rows) - 1) / max(1e-6, info["duration"]), 1),
        "shot_len": {"mean": round(float(durs.mean()), 2), "median": round(float(np.median(durs)), 2),
                     "min": round(float(durs.min()), 2), "max": round(float(durs.max()), 2)},
        "first_3s_cuts": sum(1 for c in cut_times if c < 3.0),
        "tempo_bpm": audio.get("tempo_bpm"), "cuts_on_beat_pct": on_beat, "hits_on_cuts_pct": hits_on_cut,
        "lufs": audio.get("lufs"), "motion_mix": count("motion"), "scale_mix": count("scale"),
        "avg": {k: round(float(np.mean([r[k] for r in rows])), 2) for k in ("brightness", "saturation", "contrast", "warmth")} if rows else {},
    }


def write_report(out_dir, name, summ, rows, audio, words):
    L = [f"# Style analysis: {name}", "", "Made by `tools/analyze_style.py`. Numbers are measured; read them with the contact sheet.", "",
         "## Summary", ""]
    for k, v in summ.items():
        L.append(f"- **{k}**: {v}")
    L += ["", "## Shots", "", "| # | start | dur | scale | motion | bright | sat | warmth | palette | on-screen text |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        txt = " ".join(t["text"] for t in r.get("text", []))[:60]
        pal = " ".join(r["palette"][:3])
        L.append(f'| {r["shot"]} | {r["start"]} | {r["dur"]} | {r["scale"]} | {r["motion"]} | {r["brightness"]} | {r["saturation"]} | {r["warmth"]} | {pal} | {txt} |')
    if audio:
        L += ["", "## Audio", "", f'- tempo: {audio.get("tempo_bpm")} bpm, loudness: {audio.get("lufs")} LUFS',
              f'- sudden hits (likely SFX or drum hits): {audio.get("hits", [])[:40]}', f'- silences: {audio.get("silences", [])[:20]}']
    if words:
        L += ["", "## Speech", "", " ".join(w["word"] for w in words)[:3000]]
    L += ["", "## How to use this", "",
          "- Match the pacing: aim for the same cuts per minute and median shot length; keep the first-3-seconds cut count for the hook.",
          "- If cuts_on_beat_pct is high, cut on beats (use the beat list in style.json).",
          "- Reuse the motion mix (e.g. mostly push-ins) and the scale mix (close-ups vs wides).",
          "- Match the colour: brightness/saturation/warmth averages and the palettes.",
          "- Copy the text placement (y position, size) from the on-screen text rows, not the words.", ""]
    open(os.path.join(out_dir, "report.md"), "w").write("\n".join(L))


def transcribe(path, lang):
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return []
    mp = os.path.join(MODELS, "whisper-small-int8")
    m = WhisperModel(mp if os.path.isdir(mp) else "small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(path, language=lang, word_timestamps=True, vad_filter=False)
    return [{"word": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)} for s in segs for w in (s.words or [])]


def stems(path, out_dir):
    d = os.path.join(out_dir, "stems")
    os.makedirs(d, exist_ok=True)
    r = sh(["audio-separator", path, "--model_filename", "UVR-MDX-NET-Inst_HQ_3.onnx", "--model_file_dir", os.path.join(MODELS, "uvr"),
            "--output_dir", d, "--output_format", "MP3"])
    return sorted(os.listdir(d)) if r.returncode == 0 else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--name")
    ap.add_argument("--lang", default="hi")
    ap.add_argument("--words", action="store_true", help="also transcribe speech with word timings")
    ap.add_argument("--stems", action="store_true", help="also split vocals and music")
    ap.add_argument("--no-ocr", action="store_true")
    a = ap.parse_args()
    name = a.name or re.sub(r"[^a-z0-9]+", "-", os.path.splitext(os.path.basename(a.video))[0].lower()).strip("-")
    out_dir = os.path.join(ROOT, "references", "analysis", name)
    os.makedirs(out_dir, exist_ok=True)
    info = probe(a.video)
    print(f"{name}: {info['duration']:.1f}s {info['width']}x{info['height']}")
    shots = detect_cuts(a.video) or [(0.0, info["duration"])]
    print(f"  {len(shots)} shots")
    audio = audio_profile(a.video) if info["has_audio"] else {}
    tess_lang = "hin+eng" if a.lang == "hi" else "eng"
    rows, thumbs = analyse_shots(a.video, shots, info, tess_lang, not a.no_ocr)
    words = transcribe(a.video, a.lang) if a.words and info["has_audio"] else []
    summ = summarise(info, shots, rows, audio)
    style = {"name": name, "source": os.path.relpath(os.path.abspath(a.video), ROOT), "summary": summ, "shots": rows, "audio": audio, "words": words}
    if a.stems and info["has_audio"]:
        style["stems"] = stems(a.video, out_dir)
    json.dump(style, open(os.path.join(out_dir, "style.json"), "w"), ensure_ascii=False, indent=1)
    contact_sheet(thumbs, os.path.join(out_dir, "contact_sheet.jpg"))
    write_report(out_dir, name, summ, rows, audio, words)
    print(f"  wrote {os.path.relpath(out_dir, ROOT)}/report.md, style.json, contact_sheet.jpg")
    print(json.dumps(summ, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
