#!/usr/bin/env python3
"""Person matte for depth effects (text/shapes BEHIND the speaker).
Writes <work>/matte.mp4: a lossless grey-scale mask video (H.264 qp 0, gray, full range), white = person,
aligned frame-for-frame with the input, and <work>/matte.json (next to the --out file): edge contact per side
(share of border pixels with alpha > 0.5, median over frames) so planners can avoid showing cut frame edges.

usage: matte.py --work WORKDIR [--input work/cut.mp4] [--backend mediapipe|rvm|rembg|chroma]
                [--proc-width 512] [--smooth 0.7] [--guided 10] [--eps 1e-3] [--choke 1] [--feather 1]
       matte.py --self-test

Backends
  mediapipe (default) : fast on CPU. pip install mediapipe. Model auto-downloads once (~16 MB).
  rvm                 : Robust Video Matting MobileNetV3: real alpha (hair) with its own temporal memory.
                        Nothing is downloaded. Put rvm_mobilenetv3_fp32.onnx (GPL-3.0, personal use) from
                        https://github.com/PeterL1n/RobustVideoMatting/releases at
                        ~/.cache/video-studio/rvm_mobilenetv3_fp32.onnx . Needs onnxruntime.
  rembg               : slower, sometimes cleaner hair. pip install rembg onnxruntime
  chroma              : for footage shot on a green screen. No downloads.

Refinement (mediapipe/rembg/chroma; the rvm alpha only gets --choke and --feather)
  --smooth   temporal smoothing 0..0.9 for STILL pixels; pixels where the frame changes get none (no lag on movement)
  --guided   guided-filter radius in processing pixels, 0 = off: snaps the soft mask to the frame's real edges
  --eps      guided-filter edge sensitivity (smaller = follows image edges harder, 1e-4..1e-2)
  --choke    shrink the matte by this many output pixels (drops the background-coloured rim)
  --feather  final edge blur (Gaussian sigma) in output pixels, 0 = off
"""
import argparse, json, os, subprocess, tempfile, time, urllib.request
import numpy as np
from vs_common import probe, log, die, need

CACHE = os.path.join(os.path.expanduser("~"), ".cache", "video-studio")
RVM_MODEL = os.path.join(CACHE, "rvm_mobilenetv3_fp32.onnx")
MOTION_LEVELS = 12.0  # blurred grey-level change (0..255) from the last frame at which a pixel counts as moving
SIDES = ("top", "left", "right", "bottom")


def load_cv2(guided):
    try:
        import cv2
    except ImportError:
        die("OpenCV not installed. Run: pip install opencv-contrib-python")
    if guided and not hasattr(cv2, "ximgproc"):
        die("cv2.ximgproc missing: pip install opencv-contrib-python (not opencv-python), or pass --guided 0")
    return cv2


# ---------------- backends: rgb uint8 (h, w, 3) -> person probability (h, w) ----------------
def mk_mediapipe(fps):
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mpt
        from mediapipe.tasks.python import vision
    except ImportError:
        die("mediapipe not installed. Run: pip install mediapipe   (or use --backend rembg / chroma)")
    os.makedirs(CACHE, exist_ok=True)
    model = os.path.join(CACHE, "selfie_multiclass_256x256.tflite")
    if not os.path.exists(model):
        url = "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite"
        log("downloading MediaPipe selfie model (one time)…")
        urllib.request.urlretrieve(url, model)
    opts = vision.ImageSegmenterOptions(base_options=mpt.BaseOptions(model_asset_path=model),
                                        running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True)
    seg = vision.ImageSegmenter.create_from_options(opts)
    state = {"i": 0}

    def f(rgb):
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = seg.segment_for_video(img, int(state["i"] * 1000 / fps))
        state["i"] += 1
        bgm = res.confidence_masks[0].numpy_view()  # category 0 = background
        return 1.0 - np.squeeze(bgm)
    return f


def mk_rvm(fps):
    if not os.path.exists(RVM_MODEL):
        die(f"RVM model not found at {RVM_MODEL}\n"
            "  Nothing is downloaded automatically. To use --backend rvm, download rvm_mobilenetv3_fp32.onnx\n"
            "  (GPL-3.0, fine for personal use) from https://github.com/PeterL1n/RobustVideoMatting/releases\n"
            f"  and save it as {RVM_MODEL}\n  Or leave out --backend rvm to use MediaPipe.")
    try:
        import onnxruntime as ort
    except ImportError:
        die("onnxruntime not installed. Run: pip install onnxruntime")
    sess = ort.InferenceSession(RVM_MODEL, providers=["CPUExecutionProvider"])
    dt = np.float16 if "float16" in sess.get_inputs()[0].type else np.float32
    rec = [np.zeros((1, 1, 1, 1), dt)] * 4  # recurrent state, carried frame to frame

    def f(rgb):
        ratio = np.array([min(1.0, 480 / max(rgb.shape[:2]))], np.float32)  # RVM guide: ~480 px long side, portraits
        src = (rgb.transpose(2, 0, 1)[None] / 255.0).astype(dt)
        out = sess.run(["pha", "r1o", "r2o", "r3o", "r4o"], {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2],
                                                             "r4i": rec[3], "downsample_ratio": ratio})
        rec[:] = out[1:]
        return out[0][0, 0].astype(np.float32)
    return f


def mk_rembg(fps):
    try:
        from rembg import new_session, remove
    except ImportError:
        die("rembg not installed. Run: pip install rembg onnxruntime")
    from PIL import Image
    sess = new_session("u2net_human_seg")

    def f(rgb):
        m = remove(Image.fromarray(rgb), session=sess, only_mask=True)
        return np.asarray(m, dtype=np.float32) / 255.0
    return f


def mk_chroma(fps):
    def f(rgb):
        x = rgb.astype(np.float32)
        r, g, b = x[..., 0], x[..., 1], x[..., 2]
        greenness = g - np.maximum(r, b)
        return 1.0 - np.clip((greenness - 20) / 60, 0, 1)
    return f


BACKENDS = {"mediapipe": mk_mediapipe, "rvm": mk_rvm, "rembg": mk_rembg, "chroma": mk_chroma}


# ---------------- refinement ----------------
def make_refine(cv2, smooth, radius, eps, lo, hi, choke_px, refine=True):
    """(prob, rgb) -> alpha float32 0..1: motion-aware EMA -> guided filter (guide = frame) -> lo/hi -> choke."""
    st = {"m": None, "g": None}
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * choke_px + 1,) * 2) if choke_px > 0 else None

    def f(m, rgb):
        m = m.astype(np.float32)
        if refine:
            g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
            if st["m"] is not None and smooth > 0:
                moved = cv2.GaussianBlur(np.abs(g - st["g"]), (0, 0), 3)
                w = smooth * np.clip(1 - moved / MOTION_LEVELS, 0, 1)
                m = w * st["m"] + (1 - w) * m
            st["m"], st["g"] = m, g
            if radius > 0:
                m = cv2.ximgproc.guidedFilter(rgb.astype(np.float32) / 255, m, radius, eps)
            m = np.clip((m - lo) / (hi - lo), 0, 1)
        if kern is not None:  # erode keeps the frame border (border value = max), so edge contact survives
            m = cv2.erode(m, kern)
        return m
    return f


def edge_contact(m):
    """Share of border pixels with alpha > 0.5, in SIDES order."""
    return [float((m[0] > 0.5).mean()), float((m[:, 0] > 0.5).mean()),
            float((m[:, -1] > 0.5).mean()), float((m[-1] > 0.5).mean())]


def writer_cmd(pw, ph, fps, W, H, feather, out):
    vf = f"scale={W}:{H}:flags=bicubic" + (f",gblur=sigma={feather}" if feather > 0 else "") + ",format=gray"
    return ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{pw}x{ph}", "-r", str(fps),
            "-i", "-", "-vf", vf, "-c:v", "libx264", "-qp", "0", "-preset", "veryfast", "-pix_fmt", "gray",
            "-color_range", "pc", out]  # lossless: no blocky or banded edges; render.py/cv2 read it as before


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default="work")
    ap.add_argument("--input", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--backend", default="mediapipe", choices=sorted(BACKENDS))
    ap.add_argument("--proc-width", type=int, default=512)
    ap.add_argument("--smooth", type=float, default=0.7, help="temporal smoothing 0..0.9 for still pixels")
    ap.add_argument("--guided", type=int, default=10, help="guided-filter radius in processing px (0 = off)")
    ap.add_argument("--eps", type=float, default=1e-3, help="guided-filter eps (smaller = harder edges)")
    ap.add_argument("--choke", type=float, default=1, help="shrink the matte by N output pixels")
    ap.add_argument("--feather", type=float, default=1, help="edge blur sigma in output pixels")
    ap.add_argument("--lo", type=float, default=0.35)
    ap.add_argument("--hi", type=float, default=0.75)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not (0 <= a.lo < a.hi <= 1 and 0 <= a.smooth <= 0.95 and a.guided >= 0 and a.eps > 0
            and a.choke >= 0 and a.feather >= 0):
        die("bad settings: need 0 <= lo < hi <= 1, 0 <= smooth <= 0.95, guided/choke/feather >= 0, eps > 0")
    need("ffmpeg")
    inp = a.input or os.path.join(a.work, "cut.mp4")
    if not os.path.exists(inp):
        inp = os.path.join(a.work, "source.mp4")
    out = a.out or os.path.join(a.work, "matte.mp4")
    side = os.path.splitext(out)[0] + ".json"
    info = probe(inp)
    W, H, fps = info["width"], info["height"], info["fps"]
    pw = min(a.proc_width, W) // 2 * 2
    ph = int(H * pw / W) // 2 * 2
    refine = a.backend != "rvm"  # rvm: real alpha + its own temporal memory; smoothing would only add lag
    cv2 = load_cv2(refine and a.guided > 0)
    seg = BACKENDS[a.backend](fps)
    choke_px = int(round(a.choke * pw / W))
    ref = make_refine(cv2, a.smooth, a.guided, a.eps, a.lo, a.hi, choke_px, refine)

    reader = subprocess.Popen(["ffmpeg", "-v", "error", "-i", inp, "-vf", f"scale={pw}:{ph}", "-f", "rawvideo",
                               "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    writer = subprocess.Popen(writer_cmd(pw, ph, fps, W, H, a.feather, out), stdin=subprocess.PIPE)
    frame_bytes = pw * ph * 3
    n, contacts, t0 = 0, [], time.time()
    total = int(info["duration"] * fps)
    while True:
        buf = reader.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        rgb = np.frombuffer(buf, np.uint8).reshape(ph, pw, 3)
        m = seg(rgb).astype(np.float32)
        if m.shape != (ph, pw):
            m = cv2.resize(m, (pw, ph), interpolation=cv2.INTER_LINEAR)
        m = ref(m, rgb)
        contacts.append(edge_contact(m))
        writer.stdin.write((m * 255 + 0.5).astype(np.uint8).tobytes())
        n += 1
        if n % 60 == 0:
            log(f"matte {n}/{total} frames")
    writer.stdin.close()
    if writer.wait() != 0 or reader.wait() != 0:
        die(f"ffmpeg failed while making {out}")
    if n == 0:
        die("no frames read")
    secs = time.time() - t0
    edges = dict(zip(SIDES, np.round(np.median(np.array(contacts), axis=0), 3).tolist()))
    meta = {"source": os.path.abspath(inp), "matte": os.path.abspath(out), "frames": n, "fps": fps,
            "duration": info["duration"], "size": [W, H], "backend": a.backend, "edges": edges,
            "edges_note": "share of border pixels with alpha > 0.5, median over frames",
            "settings": {k: getattr(a, k) for k in ("proc_width", "smooth", "guided", "eps", "choke", "feather", "lo", "hi")}}
    with open(side, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    log(f"matte done: {n} frames in {secs:.1f} s ({secs / n:.3f} s/frame) -> {out}")
    log(f"edge contact (median): {edges} -> {side}")


def self_test():
    cv2 = load_cv2(True)
    h, w = 96, 64
    rgb = np.zeros((h, w, 3), np.uint8); rgb[:, :32] = 200                     # person = bright left half
    coarse = cv2.GaussianBlur((rgb[..., 0] > 0).astype(np.float32), (0, 0), 6)  # soft, model-like edge
    width = lambda m: int(((m[48] > 0.1) & (m[48] < 0.9)).sum())
    sharp = make_refine(cv2, 0, 8, 1e-3, 0.35, 0.75, 0)(coarse, rgb)
    assert width(sharp) <= width(coarse) // 2 and sharp[48, 26] > 0.9 > 0.1 > sharp[48, 38], (width(coarse), width(sharp))
    # motion-aware EMA: a still frame keeps the old mask, a changed frame follows the new one at once
    ema = make_refine(cv2, 0.8, 0, 1e-3, 0, 1, 0)
    ema(np.ones((h, w), np.float32), rgb)
    still = ema(np.zeros((h, w), np.float32), rgb)
    assert abs(still.mean() - 0.8) < 1e-3, still.mean()
    moved = ema(np.zeros((h, w), np.float32), 255 - rgb)
    assert moved.max() < 1e-3, moved.max()
    # choke shrinks the person edge but not the frame border; edge contact per side
    m = np.zeros((h, w), np.float32); m[:, :32] = 1
    ch = make_refine(cv2, 0, 0, 1e-3, 0, 1, 2, refine=False)(m, rgb)
    assert ch[50, 29] == 1 and ch[50, 30] == 0 and ch[0, 0] == 1
    assert edge_contact(m) == [0.5, 1.0, 0.0, 0.5], edge_contact(m)
    # lossless round trip, read back the way render.py (format=gray) and deliver.py (cv2) do
    ramp = np.tile(np.arange(256, dtype=np.uint8), (16, 1))
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "m.mp4")
        subprocess.run(writer_cmd(256, 16, 30, 256, 16, 0, p), input=ramp.tobytes() * 3, check=True)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", "scale=256:16:flags=lanczos,format=gray",
                              "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
        back = np.frombuffer(raw, np.uint8).reshape(-1, 16, 256)
        assert back.shape[0] == 3 and np.abs(back.astype(int) - ramp).max() == 0, np.abs(back.astype(int) - ramp).max()
        cap = cv2.VideoCapture(p); ok, fr = cap.read(); cap.release()
        assert ok and np.abs(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(int) - ramp).max() <= 1
    log("matte self-test OK")


if __name__ == "__main__":
    main()
