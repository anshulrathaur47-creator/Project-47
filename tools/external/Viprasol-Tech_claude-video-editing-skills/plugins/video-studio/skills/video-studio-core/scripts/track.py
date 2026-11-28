#!/usr/bin/env python3
"""Face tracking + auto-reframe (16:9 -> 9:16 etc.) with MediaPipe face detection (CPU, free).

  track.py analyze INPUT [--work W] [--sample-fps 6] [--conf 0.3]
      -> <work>/track.json  {fps, width, height, duration, sample_fps,
                             faces: [{id, frames: [{t, x, y, w, h, conf}]}],   # normalised 0..1, every frame
                             primary: id, active: [{start, end, id}]}         # active speaker (2+ faces)
  track.py reframe INPUT --out OUT --format 9:16 [--layout auto|single|stack2] [--follow primary|active]
                   [--mode smooth|fast|locked] [--headroom 0.3] [--zoom 1.0] [--track track.json]

Layouts: single = one moving crop that follows a face (or the active speaker, cutting between them);
stack2 = two speakers stacked top/bottom for 9:16 podcasts; auto = stack2 when two faces are on screen
most of the time, else single (following the active speaker when there are two).
Modes: smooth = dead-zone + critically-damped camera (feels like an operator), fast = tighter follow,
locked = one fixed crop at the median face position.

As a module:
  analyze(path, sample_fps=6, conf=0.3) -> track dict
  follow_crop_filter(track, src_w, src_h, out_w, out_h, fps, mode="smooth", headroom=0.3,
                     face_id=None, follow="primary", zoom=1.0, cuts=(), t0=0.0) -> "crop=...,scale=...,setsar=1"
Detection works on real faces; drawn/cartoon faces are detected only when they look face-like.
"""
import argparse, os, subprocess, urllib.request
import numpy as np
from vs_common import probe, run, log, die, save_json, load_json, parse_format, need

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/"
             "float16/latest/blaze_face_short_range.tflite")
PROC_W = 640          # detection resolution
MAX_GAP = 1.0         # seconds a face may vanish and still be the same track
SPEAKER_HOLD = 1.0    # minimum seconds on one speaker before switching
STACK_ZOOM = 1.4      # extra punch-in for each stack2 panel


# ---------------- detection ----------------
def _detector(conf):
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mpt
        from mediapipe.tasks.python import vision
    except ImportError:
        die("mediapipe not installed. Run: pip install mediapipe")
    cache = os.path.join(os.path.expanduser("~"), ".cache", "video-studio")
    os.makedirs(cache, exist_ok=True)
    model = os.path.join(cache, "blaze_face_short_range.tflite")
    if not os.path.exists(model):
        log("downloading MediaPipe face model (one time, 230 KB)…")
        urllib.request.urlretrieve(MODEL_URL, model)
    det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
        base_options=mpt.BaseOptions(model_asset_path=model), running_mode=vision.RunningMode.IMAGE,
        min_detection_confidence=conf))

    def f(rgb):
        r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        return [(d.bounding_box.origin_x, d.bounding_box.origin_y, d.bounding_box.width, d.bounding_box.height,
                 d.categories[0].score) for d in r.detections]
    return f


def _iou(a, b):
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw, ih = max(0, min(ax2, bx2) - max(a[0], b[0])), max(0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    return inter / (a[2] * a[3] + b[2] * b[3] - inter + 1e-9)


def _detect_frame(det, rgb):
    """Full frame plus left/right square tiles on wide frames (the model is square, small faces get lost)."""
    h, w = rgb.shape[:2]
    boxes = list(det(rgb))
    if w > 1.3 * h:
        for x0 in (0, w - h):
            boxes += [(x + x0, y, bw, bh, c) for x, y, bw, bh, c in det(rgb[:, x0:x0 + h])]
    keep = []
    for b in sorted(boxes, key=lambda b: -b[4]):
        if all(_iou(b, k) < 0.4 for k in keep):
            keep.append(b)
    return keep


def _mouth_energy(prev, cur, box):
    """Motion in the lower half of the face minus motion in the upper half (head movement)."""
    x, y, w, h = [int(round(v)) for v in box[:4]]
    H, W = cur.shape
    x0, x1, y0, ym, y1 = max(0, x), min(W, x + w), max(0, y), max(0, y + h // 2), min(H, y + h)
    if x1 - x0 < 4 or y1 - ym < 4 or ym - y0 < 4:
        return 0.0
    d = np.abs(cur.astype(np.int16) - prev.astype(np.int16))
    return float(max(0.0, d[ym:y1, x0:x1].mean() - 0.5 * d[y0:ym, x0:x1].mean()))


class OneEuro:
    """One-Euro filter: steady when still, quick when the subject moves."""
    def __init__(self, min_cutoff=0.6, beta=4.0, d_cutoff=1.0):
        self.mc, self.beta, self.dc, self.x, self.dx, self.t = min_cutoff, beta, d_cutoff, None, 0.0, None

    @staticmethod
    def _a(cutoff, dt):
        r = 2 * np.pi * cutoff * dt
        return r / (r + 1)

    def __call__(self, t, x):
        if self.x is None:
            self.x, self.t = x, t
            return x
        dt = max(1e-3, t - self.t)
        dx = (x - self.x) / dt
        self.dx += self._a(self.dc, dt) * (dx - self.dx)
        self.x += self._a(self.mc + self.beta * abs(self.dx), dt) * (x - self.x)
        self.t = t
        return self.x


def analyze(path, sample_fps=6.0, conf=0.3):
    need("ffmpeg")
    info = probe(path)
    W, H, fps, dur = info["width"], info["height"], info["fps"], info["duration"]
    pw = min(PROC_W, W) // 2 * 2
    ph = int(round(H * pw / W)) // 2 * 2
    det = _detector(conf)
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={sample_fps},scale={pw}:{ph}",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    tracks, nid, k, prev = [], 0, 0, None
    while True:
        buf = rd.stdout.read(pw * ph * 3)
        if len(buf) < pw * ph * 3:
            break
        rgb = np.frombuffer(buf, np.uint8).reshape(ph, pw, 3)
        gray = rgb.mean(2).astype(np.uint8)
        t = k / sample_fps
        live = [tr for tr in tracks if t - tr["d"][-1][0] <= MAX_GAP]
        used = set()
        for b in _detect_frame(det, rgb):
            mouth = _mouth_energy(prev, gray, b) if prev is not None else 0.0
            best, bs = None, 0.0
            for tr in live:
                if id(tr) in used:
                    continue
                lb = tr["d"][-1][1:5]
                s = _iou(b, lb)
                cd = np.hypot(b[0] + b[2] / 2 - lb[0] - lb[2] / 2, b[1] + b[3] / 2 - lb[1] - lb[3] / 2)
                if s < 0.3 and cd < 0.6 * lb[2]:
                    s = 0.3
                if s > bs:
                    best, bs = tr, s
            if best is None or bs < 0.25:
                best = {"id": nid, "d": []}; nid += 1; tracks.append(best)
            used.add(id(best))
            best["d"].append((t, b[0], b[1], b[2], b[3], b[4], mouth))
        prev, k = gray, k + 1
    rd.wait()
    min_len = max(3, int(0.5 * sample_fps))
    tracks = [tr for tr in tracks if len(tr["d"]) >= min_len]
    faces = []
    for new_id, tr in enumerate(tracks):
        d = np.array(tr["d"], dtype=np.float64)
        filt = [OneEuro() for _ in range(4)]
        sm = np.array([[f(r[0], v) for f, v in zip(filt, r[1:5])] for r in d])
        times = np.arange(np.ceil(d[0, 0] * fps), np.floor(d[-1, 0] * fps) + 1) / fps
        # drop frames inside long gaps
        idx = np.searchsorted(d[:, 0], times)
        lo, hi = d[np.clip(idx - 1, 0, len(d) - 1), 0], d[np.clip(idx, 0, len(d) - 1), 0]
        times = times[(hi - lo) <= MAX_GAP + 1e-6]
        cols = [np.interp(times, d[:, 0], sm[:, j]) for j in range(4)]
        cf = np.interp(times, d[:, 0], d[:, 5])
        frames = [{"t": round(float(t), 3), "x": round(float(x / pw), 4), "y": round(float(y / ph), 4),
                   "w": round(float(w / pw), 4), "h": round(float(h / ph), 4), "conf": round(float(c), 3)}
                  for t, x, y, w, h, c in zip(times, *cols, cf)]
        tr["id"] = new_id
        faces.append({"id": new_id, "frames": frames,
                      "_mouth": [(float(r[0]), float(r[6])) for r in d], "_weight": float((d[:, 3] * d[:, 4] * d[:, 5]).sum())})
    primary = max(faces, key=lambda f: f["_weight"])["id"] if faces else None
    active = _active_speaker(faces, dur, sample_fps, primary)
    for f in faces:
        f.pop("_mouth"); f.pop("_weight")
    log(f"{len(faces)} face track(s), primary={primary}, {len(active)} speaker segment(s)")
    return {"source": os.path.abspath(path), "fps": fps, "width": W, "height": H, "duration": round(dur, 3),
            "sample_fps": sample_fps, "faces": faces, "primary": primary, "active": active}


def _active_speaker(faces, dur, sample_fps, primary):
    if len(faces) < 2:
        return [{"start": 0.0, "end": round(dur, 3), "id": primary}] if primary is not None else []
    n = int(np.ceil(dur * sample_fps)) + 1
    E = np.full((len(faces), n), -1.0)
    for i, f in enumerate(faces):
        for t, m in f["_mouth"]:
            E[i, min(n - 1, int(round(t * sample_fps)))] = m
    win = max(1, int(sample_fps))  # 1 s moving average
    ker = np.ones(win) / win
    S = np.stack([np.convolve(np.where(e < 0, 0, e), ker, "same") for e in E])
    S[E < 0] = -1  # not on screen -> cannot be the speaker
    segs, cur, start = [], int(np.argmax(S[:, 0])), 0.0
    for k in range(1, n):
        best = int(np.argmax(S[:, k]))
        t = k / sample_fps
        if best != cur and S[best, k] > 1.3 * max(S[cur, k], 1e-3) and t - start >= SPEAKER_HOLD:
            segs.append({"start": round(start, 3), "end": round(t, 3), "id": faces[cur]["id"]})
            cur, start = best, t
    segs.append({"start": round(start, 3), "end": round(dur, 3), "id": faces[cur]["id"]})
    return segs


# ---------------- reframe ----------------
def _face_at(track, fid):
    f = next((f for f in track["faces"] if f["id"] == fid), None)
    return {round(fr["t"] * track["fps"]): fr for fr in f["frames"]} if f else {}


def camera_path(track, src_w, src_h, cw, ch, fps, mode="smooth", headroom=0.3, face_id=None,
                follow="primary", cuts=()):
    """Per-frame crop top-left (x, y) in source pixels."""
    n = int(round(track["duration"] * fps)) + 1
    if face_id is None and follow == "active" and track.get("active"):
        segs = track["active"]
    else:
        segs = [{"start": 0, "end": track["duration"] + 1, "id": track["primary"] if face_id is None else face_id}]
    lookup = {s["id"]: _face_at(track, s["id"]) for s in segs if s["id"] is not None}
    cut_frames = {int(round(c * fps)) for c in cuts} | {int(round(s["start"] * fps)) for s in segs[1:]}
    tx, ty = np.full(n, np.nan), np.full(n, np.nan)
    si = 0
    for k in range(n):
        t = k / fps
        while si < len(segs) - 1 and t >= segs[si]["end"]:
            si += 1
        fr = lookup.get(segs[si]["id"], {}).get(round(t * track["fps"]))
        if fr:
            tx[k] = (fr["x"] + fr["w"] / 2) * src_w - cw / 2
            ty[k] = (fr["y"] + 0.4 * fr["h"]) * src_h - headroom * ch   # eyes at `headroom` from the top
    if np.all(np.isnan(tx)):
        log("no face found: centre crop")
        tx[:], ty[:] = (src_w - cw) / 2, (src_h - ch) / 2
    for arr in (tx, ty):  # hold last known position through gaps
        ok = np.where(~np.isnan(arr))[0]
        arr[:] = arr[ok[np.clip(np.searchsorted(ok, np.arange(n), "right") - 1, 0, len(ok) - 1)]]
    tx, ty = np.clip(tx, 0, src_w - cw), np.clip(ty, 0, src_h - ch)
    if mode == "locked":
        return np.full(n, np.median(tx)), np.full(n, np.median(ty))
    settle, dz = (0.8, 0.06) if mode == "smooth" else (0.3, 0.0)
    out = []
    for arr, size in ((tx, cw), (ty, ch)):
        w = 4.0 / settle
        dt = 1.0 / fps
        x, v, goal, res = arr[0], 0.0, arr[0], np.empty(n)
        for k in range(n):
            if k in cut_frames:
                x, v, goal = arr[k], 0.0, arr[k]
            if abs(arr[k] - goal) > dz * size:     # dead zone: ignore small drifts
                goal = arr[k] - np.sign(arr[k] - goal) * dz * size
            v += (w * w * (goal - x) - 2 * w * v) * dt  # critically damped spring
            x += v * dt
            res[k] = x
        out.append(res)
    return np.clip(out[0], 0, src_w - cw), np.clip(out[1], 0, src_h - ch)


def _rdp(t, x, tol):
    keep = np.zeros(len(t), bool); keep[[0, -1]] = True
    stack = [(0, len(t) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        line = x[a] + (x[b] - x[a]) * (t[a + 1:b] - t[a]) / (t[b] - t[a])
        i = int(np.argmax(np.abs(x[a + 1:b] - line)))
        if abs(x[a + 1 + i] - line[i]) > tol:
            keep[a + 1 + i] = True
            stack += [(a, a + 1 + i), (a + 1 + i, b)]
    return t[keep], x[keep]


def piecewise_expr(t, x, tol=1.0, var="t"):
    """FFmpeg expression of `var`: piecewise-linear through (t, x). Flat sum, no deep nesting."""
    kt, kx = _rdp(np.asarray(t, float), np.asarray(x, float), tol)
    if len(kt) == 1 or np.ptp(kx) < tol:
        return f"{kx[0]:.1f}"
    terms = []
    for i in range(len(kt) - 1):
        k = (kx[i + 1] - kx[i]) / (kt[i + 1] - kt[i])
        terms.append(f"gte({var},{kt[i]:.4f})*lt({var},{kt[i + 1]:.4f})*({kx[i] - k * kt[i]:.5f}+{k:.6f}*{var})")
    return (f"if(lt({var},{kt[0]:.4f}),{kx[0]:.4f},if(gte({var},{kt[-1]:.4f}),{kx[-1]:.4f},"
            + "+".join(terms) + "))")


def crop_size(src_w, src_h, out_w, out_h, zoom=1.0):
    ar = out_w / out_h
    cw, ch = (src_h * ar, src_h) if src_w / src_h > ar else (src_w, src_w / ar)
    return int(cw / zoom) // 2 * 2, int(ch / zoom) // 2 * 2


def follow_crop_filter(track, src_w, src_h, out_w, out_h, fps, mode="smooth", headroom=0.3,
                       face_id=None, follow="primary", zoom=1.0, cuts=(), t0=0.0):
    """t0: source time that the filtered stream's t=0 corresponds to (input seeked with -ss t0)."""
    cw, ch = crop_size(src_w, src_h, out_w, out_h, zoom)
    xs, ys = camera_path(track, src_w, src_h, cw, ch, fps, mode, headroom, face_id, follow, cuts)
    t = np.arange(len(xs)) / fps - t0
    return (f"crop={cw}:{ch}:x='{piecewise_expr(t, xs)}':y='{piecewise_expr(t, ys)}',"
            f"scale={out_w}:{out_h}:flags=lanczos,setsar=1")


def pick_layout(track, layout):
    if layout != "auto":
        return layout
    dur = max(track["duration"], 1e-3)
    two = [f for f in track["faces"] if len(f["frames"]) / track["fps"] > 0.5 * dur]
    return "stack2" if len(two) >= 2 else "single"


def reframe_graph(track, src_w, src_h, out_w, out_h, fps, layout="auto", **kw):
    layout = pick_layout(track, layout)
    if layout == "stack2":
        dur = track["duration"]
        two = sorted([f for f in track["faces"]], key=lambda f: -len(f["frames"]))[:2]
        if len(two) < 2:
            log("stack2 needs two faces; using single")
            layout = "single"
        else:
            two.sort(key=lambda f: np.median([fr["x"] for fr in f["frames"]]))  # left person on top
            hh = out_h // 2 // 2 * 2
            kw.pop("follow", None)
            kw["zoom"] = kw.get("zoom", 1.0) * STACK_ZOOM  # half-height panels need a tighter shot
            fa = follow_crop_filter(track, src_w, src_h, out_w, hh, fps, face_id=two[0]["id"], **kw)
            fb = follow_crop_filter(track, src_w, src_h, out_w, out_h - hh, fps, face_id=two[1]["id"], **kw)
            return layout, f"[0:v]split=2[s0][s1];[s0]{fa}[top];[s1]{fb}[bot];[top][bot]vstack,format=yuv420p[v]"
    return layout, f"[0:v]{follow_crop_filter(track, src_w, src_h, out_w, out_h, fps, **kw)},format=yuv420p[v]"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    an = sub.add_parser("analyze")
    an.add_argument("input"); an.add_argument("--work", default="work")
    an.add_argument("--sample-fps", type=float, default=6); an.add_argument("--conf", type=float, default=0.3)
    an.add_argument("--out", default=None)
    rf = sub.add_parser("reframe")
    rf.add_argument("input"); rf.add_argument("--out", required=True)
    rf.add_argument("--format", default="9:16")
    rf.add_argument("--layout", default="auto", choices=["auto", "single", "stack2"])
    rf.add_argument("--follow", default="active", choices=["primary", "active"])
    rf.add_argument("--mode", default="smooth", choices=["smooth", "fast", "locked"])
    rf.add_argument("--headroom", type=float, default=0.3)
    rf.add_argument("--zoom", type=float, default=1.0)
    rf.add_argument("--track", default=None, help="existing track.json (else analyses first)")
    rf.add_argument("--sample-fps", type=float, default=6); rf.add_argument("--conf", type=float, default=0.3)
    a = ap.parse_args()
    if a.cmd == "analyze":
        tr = analyze(a.input, a.sample_fps, a.conf)
        out = a.out or os.path.join(a.work, "track.json")
        save_json(out, tr)
        log(f"-> {out}")
        return
    tr = load_json(a.track) if a.track else analyze(a.input, a.sample_fps, a.conf)
    if not a.track:
        save_json(os.path.splitext(a.out)[0] + ".track.json", tr)
    info = probe(a.input)
    ow, oh = parse_format(a.format)
    fps = info["fps"]
    layout, graph = reframe_graph(tr, info["width"], info["height"], ow, oh, fps, a.layout, mode=a.mode,
                                  headroom=a.headroom, follow=a.follow, zoom=a.zoom)
    gf = os.path.splitext(a.out)[0] + ".graph.txt"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(gf, "w") as f:
        f.write(graph)
    log(f"reframing to {ow}x{oh} ({layout}, {a.mode})")
    run(["ffmpeg", "-y", "-hide_banner", "-i", a.input, "-filter_complex_script", gf, "-map", "[v]", "-map", "0:a?",
         "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-c:a", "copy", "-movflags", "+faststart", a.out])
    os.unlink(gf)
    log(f"done -> {a.out}")


if __name__ == "__main__":
    main()
