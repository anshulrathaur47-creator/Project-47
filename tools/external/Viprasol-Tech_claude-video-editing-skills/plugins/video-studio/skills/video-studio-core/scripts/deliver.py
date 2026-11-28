#!/usr/bin/env python3
"""Delivery: platform encodes, smart reframe, per-platform loudness, subtitles, chapters,
thumbnails and a post pack, plus a delivery report.

usage: deliver.py PLAN.json|VIDEO --to youtube,reels,tiktok [--out-dir W/deliver]
         [--track W/track.json] [--burn auto|yes|no] [--burn-engine auto|libass|pillow]
         [--kids | --cps 20] [--trim] [--chapters "0:00 Intro; 1:20 Setup"] [--headline "..."]
         [--no-thumbs] [--no-post] [--list]

PLAN input: delivers plan["outputFile"] (final.mp4), words from plan["words"], thumbnails from
the clean speaker video plan["source"]. VIDEO input: words from --words or a matching words.json.
Reframe for aspect changes: face-centred crop if a track.json is given/found (format:
{fps, width?, height?, faces:[{id, frames:[{t,x,y,w,h,conf}]}], primary}, x/y = box top-left in
video pixels or 0-1), centre crop for mild ratio changes (0.8-1.25x), otherwise blurred fill.
Outputs land in --out-dir: <name>_<preset>.<ext>, captions.srt/.vtt/.ttml, chapters.txt,
thumb_*.png, post.md, deliver_report.json/.md.
"""
import argparse, functools, json, math, os, re, shutil, subprocess, sys, tempfile, unicodedata
from vs_common import load_json, save_json, probe, log, need, _compat
import captions as C

# ------------------------------------------------------------------ presets
SAFE_916 = {"top": 0.13, "bottom": 0.22, "left": 0.05, "right": 0.14}   # conservative TikTok/IG/Shorts
TITLE_SAFE = {"top": 0.05, "bottom": 0.05, "left": 0.05, "right": 0.05}
_BASE = dict(kind="video", ext="mp4", w=None, h=None, fps=None, vcodec="h264", vbr="8M", pix_fmt="yuv420p",
             acodec="aac", abr="256k", ar=48000, lufs=-14.0, tp=-1.0, lra=11.0, max_dur=None, max_bytes=None,
             safe=TITLE_SAFE, burn=False, note="")


def _p(**kw):
    return {**_BASE, **kw}


GB, MB = 1024 ** 3, 1024 ** 2
PRESETS = {
    "youtube": _p(w=1920, h=1080, vbr="8M", abr="384k", max_dur=12 * 3600, max_bytes=256 * GB,
                  note="H.264 High, closed GOP fps/2, 2 B-frames, BT.709, faststart. Upload SRT/VTT as a caption track; 12 Mbps auto-used at 48-60 fps."),
    "youtube-4k": _p(w=3840, h=2160, vbr="40M", abr="384k", max_dur=12 * 3600, max_bytes=256 * GB,
                     note="4K gets VP9/AV1 on YouTube (better quality even from a 1080p master). 60 Mbps at 48-60 fps."),
    "youtube-hdr": _p(kind="note", note="Not produced: HDR needs a 10-bit Rec.2020 PQ/HLG grade (1080p 10-15 Mbps, 4K 44-56 Mbps). This pipeline is 8-bit SDR BT.709."),
    "shorts": _p(w=1080, h=1920, vbr="10M", max_dur=180, safe=SAFE_916, burn=True,
                 note="Vertical/square <= 3 min counts as a Short."),
    "reels": _p(w=1080, h=1920, vbr="10M", max_dur=180, max_bytes=4 * GB, safe={"top": 0.12, "bottom": 0.18, "left": 0.05, "right": 0.06}, burn=True,
                note="Hard limit reported as 20 min (contested); > 3 min is not recommended to new audiences."),
    "tiktok": _p(w=1080, h=1920, vbr="10M", max_dur=600, max_bytes=4 * GB, safe={"top": 0.06, "bottom": 0.25, "left": 0.05, "right": 0.14}, burn=True,
                 note="Uploads up to 60 min; 10 min via posting API. Web upload <= 4 GB."),
    "linkedin": _p(w=1080, h=1350, vbr="8M", max_dur=600, max_bytes=5 * GB, burn=True,
                   note="4:5 feed. Limits conflict (10/15/30 min); feed autoplays muted -> burn captions."),
    "x": _p(w=1280, h=720, vbr="6M", max_dur=140, max_bytes=512 * MB, burn=True,
            note="140 s for free accounts (Premium up to 4 h)."),
    "facebook": _p(w=1080, h=1350, vbr="8M", max_dur=240 * 60, max_bytes=10 * GB, burn=True, note="4:5 feed video."),
    "snapchat": _p(w=1080, h=1920, vbr="8M", max_dur=60, safe={"top": 0.10, "bottom": 0.20, "left": 0.05, "right": 0.05}, burn=True,
                   note="Spotlight/Snaps 60 s (third-party figure)."),
    "pinterest": _p(w=1080, h=1920, vbr="8M", max_dur=60, safe={"top": 0.10, "bottom": 0.25, "left": 0.05, "right": 0.10}, burn=True,
                    note="Idea/video pin pages 5-60 s."),
    "whatsapp-status": _p(w=720, h=1280, vbr="2M", abr="128k", max_dur=60, max_bytes=16 * MB, safe=SAFE_916, burn=True,
                          note="16 MB / 60 s (low-confidence limits); bitrate is lowered to fit the size budget."),
    "podcast-video": _p(w=1920, h=1080, vbr="6M", abr="320k", lufs=-16.0, max_dur=12 * 3600, note="Podcast loudness -16 LUFS / -1 dBTP."),
    "web-h265": _p(vcodec="h265", abr="160k", note="HEVC tagged hvc1 for Apple players."),
    "web-av1": _p(vcodec="av1", abr="160k", note="SVT-AV1 (libaom fallback)."),
    "prores-422hq": _p(ext="mov", vcodec="prores", pix_fmt="yuv422p10le", acodec="pcm_s24le", lufs=None,
                       note="Mezzanine master; mix left untouched (24-bit PCM)."),
    "prores-4444": _p(ext="mov", vcodec="prores4444", pix_fmt="yuva444p10le", acodec="pcm_s24le", lufs=None,
                      note="Alpha-capable master (alpha is opaque unless the input has alpha)."),
    "dnxhr-hq": _p(ext="mov", vcodec="dnxhr", pix_fmt="yuv422p", acodec="pcm_s24le", lufs=None, note="Avid/Resolve mezzanine."),
    "broadcast-xdcam": _p(ext="mxf", w=1920, h=1080, fps=25, vcodec="mpeg2_50", pix_fmt="yuv422p", acodec="pcm_s24le",
                          lufs=-23.0, tp=-1.0, lra=20.0, safe={"top": 0.05, "bottom": 0.05, "left": 0.05, "right": 0.05},
                          note="XDCAM-HD422-LIKE: MPEG-2 4:2:2 50 Mb/s 1080i25 TFF in MXF OP1a, 2x mono 24-bit PCM, EBU R128 -23 LUFS. Not a conformance-checked AS-11/RDD9 file."),
    "gif": _p(kind="gif", ext="gif", w=480, fps=10, max_dur=6, note="6 s preview from the start, long side 480, 128 colours."),
    "webp": _p(kind="webp", ext="webp", w=480, fps=15, max_dur=6, note="Animated WebP preview, long side 480."),
    "audio-wav": _p(kind="audio", ext="wav", acodec="pcm_s24le", lufs=None, note="48 kHz / 24-bit mix, untouched."),
    "podcast-mp3": _p(kind="audio", ext="mp3", acodec="libmp3lame", abr="192k", ar=44100, lufs=-16.0, note="Apple Podcasts -16 LUFS / -1 dBTP."),
}


# ------------------------------------------------------------------ ffmpeg helpers
def ff(cmd, cwd=None):
    need(cmd[0])
    p = subprocess.run(_compat(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + "\n".join(p.stderr.strip().splitlines()[-15:]))
    return p.stderr


def _last_json(text):
    i = text.rfind("{")
    return json.loads(text[i:text.rfind("}") + 1]) if i >= 0 else {}


def measure_loudness(path, start=None, dur=None):
    """Integrated loudness (LUFS), true peak (dBTP), LRA (LU), gate threshold - EBU R128 via loudnorm.
    Split mono tracks (MXF) are merged first so the programme is measured, not one channel."""
    n = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path],
                       stdout=subprocess.PIPE, text=True).stdout.split()
    n = len(n)
    cmd = ["ffmpeg", "-hide_banner", "-nostats"] + (["-ss", str(start)] if start else []) + ["-i", path] + (["-t", str(dur)] if dur else [])
    if n > 1:
        cmd += ["-filter_complex", "".join(f"[0:a:{i}]" for i in range(n)) + f"amerge=inputs={n},loudnorm=print_format=json"]
    else:
        cmd += ["-vn", "-af", "loudnorm=print_format=json"]
    d = _last_json(ff(cmd + ["-f", "null", "-"]))
    return {"I": float(d["input_i"]), "TP": float(d["input_tp"]), "LRA": float(d["input_lra"]), "thresh": float(d["input_thresh"])}


def stream_info(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
                         stdout=subprocess.PIPE, text=True).stdout
    d = json.loads(out or "{}")
    v = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), {})
    a = next((s for s in d.get("streams", []) if s["codec_type"] == "audio"), {})
    num, den = (v.get("r_frame_rate") or v.get("avg_frame_rate") or "0/1").split("/")
    return {"vcodec": v.get("codec_name"), "profile": v.get("profile"), "width": v.get("width"), "height": v.get("height"),
            "pix_fmt": v.get("pix_fmt"), "fps": round(float(num) / float(den), 3) if float(den) else None,
            "field_order": v.get("field_order"), "color": [v.get("color_space"), v.get("color_primaries"), v.get("color_transfer")],
            "acodec": a.get("codec_name"), "sample_rate": a.get("sample_rate"), "channels": a.get("channels"),
            "duration": float(d.get("format", {}).get("duration", 0) or 0), "bytes": int(d.get("format", {}).get("size", 0) or 0),
            "bit_rate": int(d.get("format", {}).get("bit_rate", 0) or 0)}


def _even(x):
    return max(2, int(round(x / 2)) * 2)


def _rate(s):
    return float(s[:-1]) * {"k": 1e3, "M": 1e6}[s[-1]] if s[-1] in "kM" else float(s)


# ------------------------------------------------------------------ reframe
def load_track(path, vw, vh):
    """Primary face samples [(t, cx, cy, w, h)] in video pixels, or None if unusable for this video.
    `path` may also be an already-loaded track dict (see plan_track)."""
    if isinstance(path, dict):
        tr = path
    elif not path or not os.path.exists(path):
        return None
    else:
        tr = load_json(path)
    if tr.get("width") and (int(tr["width"]), int(tr["height"])) != (vw, vh):
        log(f"track.json is for {tr['width']}x{tr['height']}, video is {vw}x{vh} - not used")
        return None
    faces = tr.get("faces") or []
    face = next((f for f in faces if f.get("id") == tr.get("primary")), None) or max(faces, key=lambda f: len(f.get("frames", [])), default=None)
    fr = sorted((face or {}).get("frames", []), key=lambda f: f["t"])
    fr = [f for f in fr if f.get("conf", 1) >= 0.3]
    if not fr:
        return None
    norm = max(f["x"] + f["w"] for f in fr) <= 1.5
    sx, sy = (vw, vh) if norm else (1, 1)
    return [(f["t"], (f["x"] + f["w"] / 2) * sx, (f["y"] + f["h"] / 2) * sy, f["w"] * sx, f["h"] * sy) for f in fr]


def plan_track(plan):
    """plan["track"] (compact primary-face boxes of plan["source"], 0-1) in track.json form, or None."""
    fr = (plan or {}).get("track")
    if not fr:
        return None
    w, h = ((plan.get("sourceSize") or []) + [None, None])[:2]
    return {"width": w, "height": h, "faces": [{"id": 0, "frames": fr}], "primary": 0}


def face_cmds(samples, axis_len, win, along_x, smooth=0.5):
    """Offline camera: centred (zero-lag) moving average of the face over +-`smooth` s, then a
    dead zone so the frame holds still for small head moves."""
    key = 1 if along_x else 2
    ts, ps = [s[0] for s in samples], [s[key] for s in samples]
    sm, j0, j1, acc = [], 0, 0, 0.0
    for i, t in enumerate(ts):
        while j1 < len(ts) and ts[j1] <= t + smooth:
            acc += ps[j1]; j1 += 1
        while ts[j0] < t - smooth:
            acc -= ps[j0]; j0 += 1
        sm.append(acc / (j1 - j0))
    cam, dz, out, last = sm[0], 0.06 * win, [], None
    for t, p in zip(ts, sm):
        if abs(p - cam) > dz:
            cam = p - math.copysign(dz, p - cam)
        off = int(min(max(cam - win / 2, 0), axis_len - win)) // 2 * 2
        if last is None or abs(off - last) >= 2:
            out.append((t, off)); last = off
    return out


def reframe(vw, vh, tw, th, track=None, cmd_path=None):
    """(filter, mode). Writes a sendcmd file for the face path."""
    r = (vw / vh) / (tw / th)
    if abs(r - 1) < 0.01:
        return f"scale={tw}:{th}:flags=lanczos", "scale"
    if track and cmd_path:
        along_x = r > 1
        cw, ch = (_even(vh * tw / th), vh) if along_x else (vw, _even(vw * th / tw))
        cmds = face_cmds(track, vw if along_x else vh, cw if along_x else ch, along_x)
        axis = "x" if along_x else "y"
        with open(cmd_path, "w") as f:
            f.write("\n".join(f"{t:.3f} crop@rf {axis} {o};" for t, o in cmds) + "\n")
        x0, y0 = (cmds[0][1], 0) if along_x else (0, cmds[0][1])
        return (f"sendcmd=f={os.path.basename(cmd_path)},crop@rf={cw}:{ch}:{x0}:{y0},scale={tw}:{th}:flags=lanczos",
                f"face-crop ({len(cmds)} moves)")
    if 0.8 <= r <= 1.25:
        return f"scale={tw}:{th}:force_original_aspect_ratio=increase:flags=lanczos,crop={tw}:{th}", "centre-crop"
    return (f"split=2[rfa][rfb];[rfa]scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},"
            f"scale=iw/8:-2,gblur=sigma=6,scale={tw}:{th},eq=brightness=-0.08[rfbg];"
            f"[rfb]scale={tw}:{th}:force_original_aspect_ratio=decrease:flags=lanczos[rffg];"
            f"[rfbg][rffg]overlay=(W-w)/2:(H-h)/2"), "blurred-fill"


# ------------------------------------------------------------------ text rendering (Pillow; no drawtext)
# Per-script candidates as (file, ttc index). The first installed font that has a glyph for every character
# of the string wins, so no tofu boxes. Pillow finds bare names in C:/Windows/Fonts, in /Library/Fonts,
# /System/Library/Fonts and ~/Library/Fonts on macOS (recursive) and under the XDG data dirs on Linux
# (`apt install fonts-noto-core` -> NotoSansDevanagari-Bold.ttf, `fonts-lohit-deva` -> Lohit-Devanagari.ttf).
# Per-user Windows installs (right-click > Install) land in _UF, which Pillow does not search.
_UF = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")
LATIN_FONTS = [("ariblk.ttf", 0), ("impact.ttf", 0), ("arialbd.ttf", 0), ("seguibl.ttf", 0), ("DejaVuSans-Bold.ttf", 0),
               ("/System/Library/Fonts/Supplemental/Arial Black.ttf", 0), ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0)]
INDIC_FONTS = [("NotoSansDevanagari-Bold.ttf", 0), (os.path.join(_UF, "NotoSansDevanagari-Bold.ttf"), 0),
               ("Nirmala.ttc", 1),                                  # Windows 10/11 Nirmala UI Bold: every Indic script + Latin
               ("Kohinoor.ttc", 0), ("ITFDevanagari.ttc", 0),       # macOS
               ("Lohit-Devanagari.ttf", 0)]                         # Linux
INDIC = {"DEVANAGARI", "BENGALI", "GURMUKHI", "GUJARATI", "ORIYA", "TAMIL", "TELUGU", "KANNADA", "MALAYALAM"}
COMPLEX = INDIC | {"ARABIC", "HEBREW", "THAI"}                      # need libraqm (shaping / RTL) in Pillow


def script_of(text):
    """First non-Latin script of `text` by Unicode name ('DEVANAGARI', 'ARABIC', ...), else 'LATIN'."""
    names = (unicodedata.name(c, "").split(" ")[0] for c in text if c.isalpha())
    return next((n for n in names if n and n != "LATIN"), "LATIN")


@functools.lru_cache(maxsize=None)
def _has_glyphs(name, index, chars):
    """True when the font loads and no character of `chars` draws as its .notdef glyph (the tofu box)."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        f = ImageFont.truetype(name, 32, index=index)
    except OSError:
        return False

    def ink(s):
        im = Image.new("L", (128, 64))
        ImageDraw.Draw(im).text((32, 8), s, font=f, fill=255)
        return im.tobytes()
    tofu = ink("\U0010FFFD")                                         # private-use codepoint no font maps
    return all(ink(c) != tofu for c in chars)


@functools.lru_cache(maxsize=None)
def font_face(text, prefer=None):
    """(file, ttc index) of the first installed font for the script of `text` that draws all of it
    (None = Pillow's bundled Latin font). Raises when nothing installed covers the script."""
    s = script_of(text)
    chars = "".join(sorted({c for c in text if unicodedata.category(c)[0] in "LMN"}))
    for name, idx in ([(prefer, 0)] if prefer else []) + (INDIC_FONTS if s in INDIC else []) + LATIN_FONTS:
        if _has_glyphs(name, idx, chars):
            return name, idx
    if s == "LATIN":
        return None
    raise RuntimeError(f"no installed font draws this {s.title()} text {text[:40]!r}: install Noto Sans {s.title()}"
                       " (Windows 10/11 ship Nirmala UI for Indic scripts)")


def font(size, text="", prefer=None):
    from PIL import ImageFont
    face = font_face(text, prefer)
    return ImageFont.truetype(face[0], size, index=face[1]) if face else ImageFont.load_default(size)


def shaping_note(text):
    """Warning when `text` needs complex shaping that this Pillow build cannot do (no libraqm), else None."""
    from PIL import features
    s = script_of(text)
    if s in COMPLEX and not features.check("raqm"):
        return (f"{s.title()} text drawn by Pillow without libraqm: glyphs are right but conjuncts/matras are unshaped"
                " (e.g. the i-matra after its consonant, visible halant). Fix: a fribidi DLL for Pillow's raqm, or browser-rendered titles.")
    return None


def burn_layout(w, h, safe):
    vertical = h > w
    size = int(w * 0.05) if vertical else int(h * 0.045)
    mv = int(h * (safe["bottom"] + 0.02)) if vertical else int(h * 0.07)
    return size, mv, (int(w * safe["left"]) + 10, int(w * safe["right"]) + 10)


def render_cue_pngs(cues, w, h, safe, folder):
    """Pillow fallback for burn-in: full-frame RGBA PNG per cue + an ffconcat list (one overlay input)."""
    from PIL import Image, ImageDraw
    os.makedirs(folder, exist_ok=True)
    size, mv, _ = burn_layout(w, h, safe)
    Image.new("RGBA", (w, h), (0, 0, 0, 0)).save(os.path.join(folder, "blank.png"))
    lst, t = ["ffconcat version 1.0"], 0.0
    for i, c in enumerate(cues):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        y = h - mv
        for line in reversed(c["lines"]):
            fnt = font(size, line, "arialbd.ttf")                    # per line: Devanagari lines get an Indic font
            l, tp, r, b = d.textbbox((0, 0), line, font=fnt, stroke_width=max(2, size // 12))
            y -= (b - tp) + int(size * 0.2)
            d.text(((w - (r - l)) / 2 - l, y - tp), line, font=fnt, fill="white", stroke_width=max(2, size // 12), stroke_fill="black")
        im.save(os.path.join(folder, f"c{i:04d}.png"))
        if c["start"] > t:
            lst += ["file blank.png", f"duration {c['start'] - t:.3f}"]
        lst += [f"file c{i:04d}.png", f"duration {c['end'] - c['start']:.3f}"]
        t = c["end"]
    lst += ["file blank.png", "duration 1", "file blank.png"]
    p = os.path.join(folder, "list.ffconcat")
    open(p, "w").write("\n".join(lst) + "\n")
    return p


_LIBASS = None


def libass_ok():
    global _LIBASS
    if _LIBASS is None:
        d = tempfile.mkdtemp()
        open(os.path.join(d, "t.srt"), "w").write("1\n00:00:00,000 --> 00:00:01,000\nOK\n")
        try:
            ff(["ffmpeg", "-y", "-hide_banner", "-f", "lavfi", "-i", "color=c=gray:s=160x90:d=1", "-vf", "subtitles=t.srt",
                "-frames:v", "1", "-update", "1", "t.png"], cwd=d)
            _LIBASS = os.path.getsize(os.path.join(d, "t.png")) > 0
        except RuntimeError:
            _LIBASS = False
        shutil.rmtree(d, ignore_errors=True)
    return _LIBASS


# ------------------------------------------------------------------ encoding
BT709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def video_codec_args(pr, fps, dur):
    vc = pr["vcodec"]
    if vc == "h264":
        vbr = _rate(pr["vbr"]) * (1.5 if fps > 31 else 1)
        if pr["max_bytes"] and dur:                              # fit the platform size budget
            vbr = max(2e5, min(vbr, pr["max_bytes"] * 8 * 0.92 / dur - _rate(pr["abr"])))
        gop = str(max(1, round(fps / 2)))                        # YouTube: closed GOP of half the frame rate
        return ["-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-b:v", str(int(vbr)),
                "-maxrate", str(int(vbr * 1.5)), "-bufsize", str(int(vbr * 2)), "-g", gop, "-keyint_min", gop,
                "-sc_threshold", "0", "-bf", "2", "-flags", "+cgop", "-coder", "1"] + BT709
    if vc == "h265":
        return ["-c:v", "libx265", "-preset", "medium", "-crf", "24", "-tag:v", "hvc1", "-x265-params", "log-level=error"] + BT709
    if vc == "av1":
        enc = available_av1()
        if enc == "libsvtav1":
            return ["-c:v", "libsvtav1", "-preset", "8", "-crf", "32", "-g", str(int(fps * 5))] + BT709
        return ["-c:v", "libaom-av1", "-crf", "32", "-b:v", "0", "-cpu-used", "6", "-row-mt", "1"] + BT709
    if vc in ("prores", "prores4444"):
        return ["-c:v", "prores_ks", "-profile:v", "3" if vc == "prores" else "4", "-vendor", "apl0"] + \
               (["-alpha_bits", "16"] if vc == "prores4444" else []) + BT709
    if vc == "dnxhr":
        return ["-c:v", "dnxhd", "-profile:v", "dnxhr_hq"] + BT709
    if vc == "mpeg2_50":
        return ["-c:v", "mpeg2video", "-b:v", "50M", "-minrate", "50M", "-maxrate", "50M", "-bufsize", "17825792",
                "-rc_init_occupancy", "17825792", "-g", "12", "-bf", "2", "-flags", "+ildct+ilme",
                "-intra_vlc", "1", "-non_linear_quant", "1", "-intra_dc_precision", "2", "-qmin", "1", "-qmax", "12"] + BT709
    raise ValueError(vc)


def available_av1():
    enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], stdout=subprocess.PIPE, text=True).stdout
    return next((e for e in ("libsvtav1", "libaom-av1") if f" {e} " in enc), None)


def audio_chain(pr, loud, extra_gain=0.0):
    """(filter, mode). Two-pass: `loud` is the pass-1 measurement of the input. Exact static gain when
    the peaks allow it (= linear loudnorm); otherwise gain into a 4x-oversampled peak limiter, which
    acts as a true-peak limiter and still lands on the integrated target (dynamic loudnorm drifts)."""
    parts, mode = ["aformat=channel_layouts=stereo"], "untouched"
    if pr["lufs"] is not None and loud:
        gain = pr["lufs"] - loud["I"] + extra_gain
        if loud["TP"] + gain - extra_gain <= pr["tp"] - 0.3:
            parts.append(f"volume={gain:.2f}dB"); mode = f"linear gain {gain:+.2f} dB"
        else:
            lim = 10 ** ((pr["tp"] - 0.6) / 20)
            parts.append(f"volume={gain:.2f}dB,aresample=192000,alimiter=limit={lim:.4f}:attack=1:release=60:level=false")
            mode = f"gain {gain:+.2f} dB + true-peak limiter"
    parts.append(f"aresample={pr['ar']}")
    return ",".join(parts), mode


def fitted_audio(src, pr, loud, cache):
    """audio_chain, plus up to 2 audio-only trial passes when the limiter eats loudness, so the
    integrated result lands within 0.3 LU of target. Cached per (LUFS, TP) target."""
    key = (pr["lufs"], pr["tp"], pr["ar"])
    if key not in cache:
        extra = 0.0
        ac, mode = audio_chain(pr, loud)
        for _ in range(2):
            if "limiter" not in mode:
                break
            got = measure_loudness_chain(src, ac)
            if abs(got - pr["lufs"]) <= 0.3:
                break
            extra += pr["lufs"] - got
            ac, mode = audio_chain(pr, loud, extra)
        cache[key] = (ac, mode)
    return cache[key]


def measure_loudness_chain(src, chain):
    err = ff(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-vn", "-af", chain + ",loudnorm=print_format=json", "-f", "null", "-"])
    return float(_last_json(err)["input_i"])


def encode_video(name, pr, src, info, out, ctx):
    W, H = (pr["w"], pr["h"]) if pr["w"] else (_even(info["width"]), _even(info["height"]))
    fps = pr["fps"] or min(info["fps"], 60)
    cwd = os.path.dirname(out)
    rf, mode = reframe(info["width"], info["height"], W, H, ctx.get("track"), os.path.join(cwd, f"_reframe_{name}.cmd"))
    inputs, g = ["-i", src], ["[0:v]" + rf + ("[b0]" if pr["fps"] is None else "[b0p]")]
    if pr["fps"] is not None:
        g.append(f"[b0p]fps=50,interlace=scan=tff,setfield=tff[b0]" if pr["vcodec"] == "mpeg2_50" else f"[b0p]fps={fps}[b0]")
    last, burned = "[b0]", None
    cues = ctx.get("burn_cues", {}).get(name)
    if cues:
        if ctx["burn_engine"] == "libass":
            assp = os.path.join(cwd, f"_captions_{name}.ass")
            size, mv, mlr = burn_layout(W, H, pr["safe"])
            C.write_ass(cues, assp, W, H, size=size, margin_v=mv, margin_lr=mlr)
            g.append(f"[b0]subtitles={os.path.basename(assp)}[b1]")
        else:
            lst = render_cue_pngs(cues, W, H, pr["safe"], os.path.join(cwd, f"_burn_{name}"))
            inputs += ["-f", "concat", "-safe", "0", "-i", lst]
            g.append(f"[1:v]format=rgba[sb];[b0][sb]overlay=0:0:eof_action=pass[b1]")
        last, burned = "[b1]", ctx["burn_engine"]
    g.append(f"{last}setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv,"
             f"format={pr['pix_fmt']},setsar=1[v]")
    maps = ["-map", "[v]"]
    if info["has_audio"]:
        ac, amode = fitted_audio(src, pr, ctx.get("loud"), ctx.setdefault("afit", {}))
        if pr["vcodec"] == "mpeg2_50":
            g.append(f"[0:a]{ac},channelsplit=channel_layout=stereo[aL][aR]"); maps += ["-map", "[aL]", "-map", "[aR]"]
        else:
            g.append(f"[0:a]{ac}[a]"); maps += ["-map", "[a]"]
    if ctx.get("meta") and pr["ext"] in ("mp4", "mov"):
        inputs += ["-i", ctx["meta"]]
        k = sum(1 for x in inputs if x == "-i") - 1
        maps += ["-map_metadata", str(k), "-map_chapters", str(k)]
    gf = os.path.join(cwd, f"_graph_{name}.txt")
    open(gf, "w").write(";\n".join(g))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-nostats"] + inputs + ["-filter_complex_script", gf] + maps
    if ctx.get("trim_to"):
        cmd += ["-t", str(ctx["trim_to"])]
    cmd += video_codec_args(pr, fps, min(info["duration"], ctx.get("trim_to") or 1e9))
    if info["has_audio"]:
        cmd += ["-c:a", pr["acodec"], "-ar", str(pr["ar"])] + (["-b:a", pr["abr"]] if pr["acodec"] == "aac" else [])
    cmd += (["-movflags", "+faststart"] if pr["ext"] in ("mp4", "mov") else []) + (["-f", "mxf"] if pr["ext"] == "mxf" else [])
    ff(cmd + [out], cwd=cwd)
    os.unlink(gf)
    return {"reframe": mode, "burned_captions": burned, "loudness_mode": amode if info["has_audio"] else None}


def encode_other(name, pr, src, info, out, ctx):
    if pr["kind"] in ("gif", "webp"):
        t = ["-t", str(pr["max_dur"])]
        n = pr["w"]
        fit = f"scale='if(gte(iw,ih),{n},-2)':'if(gte(iw,ih),-2,{n})':flags=lanczos"     # long side = n
        if pr["kind"] == "gif":
            ff(["ffmpeg", "-y", "-hide_banner"] + t + ["-i", src, "-filter_complex",
                f"[0:v]fps={pr['fps']},{fit},split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];"
                f"[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle", "-loop", "0", out])
        else:
            ff(["ffmpeg", "-y", "-hide_banner"] + t + ["-i", src, "-vf", f"fps={pr['fps']},{fit}",
                "-c:v", "libwebp_anim", "-loop", "0", "-q:v", "70", "-an", out])
        return {}
    if not info["has_audio"]:
        raise RuntimeError("input has no audio")
    ac, amode = fitted_audio(src, pr, ctx.get("loud"), ctx.setdefault("afit", {}))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", src, "-vn", "-af", ac,
           "-c:a", pr["acodec"], "-ar", str(pr["ar"])] + (["-b:a", pr["abr"]] if pr["acodec"] == "libmp3lame" else [])
    ff(cmd + (["-t", str(ctx["trim_to"])] if ctx.get("trim_to") else []) + [out])
    return {"loudness_mode": amode}


# ------------------------------------------------------------------ thumbnails
def _lum(rgb):
    f = lambda c: (c / 255) / 12.92 if c / 255 <= 0.03928 else ((c / 255 + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hex(c):
    c = (c or "").strip().lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) if re.fullmatch(r"[0-9a-fA-F]{6,8}", c) else (255, 225, 77)


def pick_frames(video, track=None, n=3):
    """Best n frames: sharpness (Laplacian variance), exposure, contrast, face presence; spread out in time."""
    import cv2
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    times = [0.3 + i * (dur - 0.6) / 39 for i in range(40)] if dur > 1 else [0]
    cands = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if not ok:
            continue
        sm = cv2.resize(fr, (640, int(640 * fr.shape[0] / fr.shape[1])))
        g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY)
        face = min(track, key=lambda s: abs(s[0] - t)) if track else None
        face = face if face and abs(face[0] - t) < 0.5 else None
        cands.append({"t": t, "frame": fr, "lap": cv2.Laplacian(g, cv2.CV_64F).var(), "mean": g.mean() / 255,
                      "std": g.std() / 255, "face": face})
    cap.release()
    mx = max((c["lap"] for c in cands), default=1) or 1
    for c in cands:
        c["score"] = (0.5 * c["lap"] / mx + 0.25 * (1 - min(1, abs(c["mean"] - 0.45) * 2))
                      + 0.25 * min(1, c["std"] / 0.25) + (0.5 if c["face"] else 0))
    picked, gap = [], max(1.0, dur / 10)
    for c in sorted(cands, key=lambda c: -c["score"]):
        if all(abs(c["t"] - p["t"]) >= gap for p in picked):
            picked.append(c)
        if len(picked) == n:
            break
    return picked


def _wrap(draw, words, fnt, max_w):
    lines, cur = [], []
    for w in words:
        if cur and draw.textlength(" ".join(cur + [w]), font=fnt) > max_w:
            lines.append(cur); cur = []
        cur.append(w)
    return lines + ([cur] if cur else [])


THUMB_LAYOUT = {  # where the face goes (x, y fraction of the thumb) and the text box (x0, width as fraction of W)
    "left": ((0.70, 0.42), (0.05, 0.54)), "right": ((0.30, 0.42), (0.43, 0.53)),
    "bottom": ((0.5, 0.33), (0.05, 0.90)), "top": ((0.5, 0.62), (0.06, 0.88)), "low": ((0.5, 0.30), (0.06, 0.88))}


def _scrim(layout, W, H):
    import numpy as np
    x, y = np.linspace(0, 1, W)[None, :], np.linspace(0, 1, H)[:, None]
    g = {"left": 1 - x / 0.62, "right": (x - 0.38) / 0.62, "bottom": (y - 0.45) / 0.55,
         "top": 1 - y / 0.45, "low": 1 - np.abs(y - 0.66) / 0.3}[layout]
    return (np.clip(np.broadcast_to(g, (H, W)), 0, 1) * 190).astype("uint8")


def estimate_subject(frame_bgr, matte=None):
    """Head point (x, y) without a face track: matte if present, else pixels that differ from the
    border colour (works for plain backgrounds). ponytail: saliency heuristic; a face track beats it."""
    import numpy as np
    if matte is not None:
        m = matte > 127
    else:
        g = frame_bgr[::4, ::4].astype(np.int16)
        border = np.concatenate([g[0], g[-1], g[:, 0], g[:, -1]])
        m = np.abs(g - np.median(border, 0)).sum(2) > 60
        m = np.kron(m, np.ones((4, 4), bool))[:frame_bgr.shape[0], :frame_bgr.shape[1]]
    ys, xs = np.nonzero(m)
    if len(xs) < m.size * 0.01:
        return None
    top, bot = ys.min(), ys.max()
    head = ys < top + 0.25 * (bot - top)
    return (float(xs[head].mean()), float(top + 0.14 * (bot - top)))


def _crop_box(fw, fh, W, H, fx, fy, want, zoom=1.0):
    """Smallest zoom (>= zoom, <= 1.6) that lets the face sit at `want`; returns the source crop box."""
    s0 = max(W / fw, H / fh)
    cw0, ch0 = W / s0, H / s0
    lim = lambda f, full, w: min(f / w, (full - f) / (1 - w)) if 0 < w < 1 else full
    z = min(1.6, max(zoom, cw0 / max(1, lim(fx, fw, want[0])), ch0 / max(1, lim(fy, fh, want[1]))))
    cw, ch = cw0 / z, ch0 / z
    x0 = min(max(fx - want[0] * cw, 0), fw - cw); y0 = min(max(fy - want[1] * ch, 0), fh - ch)
    return (int(x0), int(y0), int(x0 + cw), int(y0 + ch))


def _face_span(face, box, H):
    """Face box top/bottom in thumbnail pixels when the source crop `box` fills a thumbnail H px tall."""
    k = H / (box[3] - box[1])
    return (face[2] - face[4] / 2 - box[1]) * k, (face[2] + face[4] / 2 - box[1]) * k


def _title_band(ft, fb, H, lo=0.13, hi=0.76, pad=0.02):
    """(y0, y1, side): the larger free band above ('top') or below ('low') a face spanning ft..fb px,
    kept inside lo..hi of H (the 3:4 grid crop of a 9:16 cover)."""
    up, down = (H * lo, min(ft, H * hi) - H * pad), (max(fb, H * lo) + H * pad, H * hi)
    return (*up, "top") if up[1] - up[0] >= down[1] - down[0] else (*down, "low")


def compose_thumb(frame_bgr, face, headline, accent, layout, W, H, matte=None):
    """layout: 'left' (text left, subject right), 'right', 'bottom', or 'cover' (vertical; text above or below the face).
    `face` = a load_track sample; with its box (5th value) the cover title goes in the larger free band off the face."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    import numpy as np
    img = Image.fromarray(np.ascontiguousarray(frame_bgr[:, :, ::-1]))
    fw, fh = img.size
    head = (face[1], face[2]) if face else estimate_subject(frame_bgr, matte)
    fx, fy = head or (fw / 2, fh * 0.4)
    boxed = bool(face) and len(face) > 4
    if layout == "cover":                                         # text where the face is not
        b0 = _crop_box(fw, fh, W, H, fx, fy, (0.5, 0.5))
        layout = (_title_band(*_face_span(face, b0, H), H)[2] if boxed
                  else "low" if (fy - b0[1]) / (b0[3] - b0[1]) < 0.5 else "top")
    want, (ax, aw) = THUMB_LAYOUT[layout]
    box = _crop_box(fw, fh, W, H, fx, fy, want, 1.15 if layout in ("left", "right") else 1.0)
    band = _title_band(*_face_span(face, box, H), H) if boxed and layout in ("top", "low") else None
    if band:
        layout = band[2]
    frame = img.crop(box).resize((W, H), Image.LANCZOS)
    base = ImageEnhance.Color(ImageEnhance.Contrast(frame).enhance(1.08)).enhance(1.12)
    base = Image.composite(Image.new("RGB", (W, H)), base, Image.fromarray(_scrim(layout, W, H)))
    d = ImageDraw.Draw(base)
    area = (ax * W, aw * W)
    vertical = layout in ("top", "low")
    words, size = headline.split(), int(H * (0.1 if vertical else 0.2))
    max_lines, max_h = (2 if layout == "bottom" else 3), H * (0.22 if vertical else 0.4 if layout == "bottom" else 0.75)
    if band:
        max_h = min(max_h, band[1] - band[0])
    while True:
        fnt = font(size, headline)
        lines, lh = _wrap(d, words, fnt, area[1]), int(size * 1.05)
        if size <= 24 or (len(lines) <= max_lines and lh * len(lines) <= max_h
                          and all(d.textlength(" ".join(ln), font=fnt) <= area[1] for ln in lines)):
            break
        size -= 4
    total = lh * len(lines)
    y = (band[0] + band[1] - total) / 2 if band else {
        "left": (H - total) / 2, "right": (H - total) / 2, "bottom": H * 0.94 - total, "top": H * 0.13,
        "low": H * 0.76 - total}[layout]
    region = np.asarray(base.crop((int(area[0]), int(y), int(area[0] + area[1]), int(y + total))))
    bg = tuple(int(v) for v in region.reshape(-1, 3).mean(0)) if region.size else (0, 0, 0)
    main = max([(255, 255, 255), accent], key=lambda c: contrast(c, bg))
    hi = accent if main != accent and contrast(accent, bg) >= 3 else (255, 255, 255)
    stroke = max(3, size // 11)
    for line in lines:
        lw = d.textlength(" ".join(line), font=fnt)
        x = area[0] + {"left": 0, "right": area[1] - lw}.get(layout, (area[1] - lw) / 2)
        for w in line:
            d.text((x, y), w, font=fnt, fill=hi if re.search(r"\d", w) else main, stroke_width=stroke, stroke_fill=(0, 0, 0))
            x += d.textlength(w + " ", font=fnt)
        y += lh
    if matte is not None:                                        # text behind the subject (matte from matte.py)
        m = Image.fromarray(matte).crop(box).resize((W, H)).filter(ImageFilter.GaussianBlur(1))
        base = Image.composite(frame, base, m.convert("L"))
    face_font = font_face(headline)
    return base, {"contrast": round(contrast(main, bg), 2), "font_px": size, "text_color": main,
                  "font": f"{os.path.basename(face_font[0])}#{face_font[1]}" if face_font else "pillow-default",
                  "text_over_face": bool(band) and total > band[1] - band[0]}


def headline_from(plan, words, override=None):
    """Thumbnail headline from the transcript's first sentence (or the plan hook) - never invented."""
    if override:
        return override.upper()
    sents = C.sentences(words) if words else []
    hook = next((re.sub(r"<[^>]+>", "", e["text"]) for e in (plan or {}).get("elements", [])   # skins put HTML in hooks
                 if e.get("type") in ("text", "headline") and float(e.get("start", 9)) < 3 and e.get("text")), None)
    src = sents[0]["text"] if sents else (hook or "")
    if hook and sents and not sents[0]["text"].lower().startswith(hook.lower()[:12]):
        src = hook
    ws = C.numberize(src).split()
    while ws and C.bare(ws[0]) in {"here", "are", "is", "this", "so", "today", "and", "okay", "heres"}:
        ws = ws[1:]
    return " ".join(ws[:7]).rstrip(".,!?;:।॥…").upper()


def read_matte(matte_path, t):
    if not matte_path or not os.path.exists(matte_path):
        return None
    import cv2
    cap = cv2.VideoCapture(matte_path); cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, fr = cap.read(); cap.release()
    return cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if ok else None


def make_thumbnails(video, out_dir, headline, accent=(255, 225, 77), track=None, matte_path=None):
    """3 x 1280x720 (text left / right / bottom, the last one text-behind-subject if a matte exists) + 1080x1920 cover."""
    picks, outs = pick_frames(video, track, 3), []
    for k, (c, lay) in enumerate(zip(picks, ["left", "right", "bottom"])):
        m = read_matte(matte_path, c["t"]) if lay == "bottom" else None
        im, meta = compose_thumb(c["frame"], c["face"], headline, accent, lay, 1280, 720, m)
        p = os.path.join(out_dir, f"thumb_{k + 1}_{lay}.png"); im.save(p, optimize=True)
        outs.append({"file": p, "t": round(c["t"], 2), "score": round(c["score"], 3), "face": bool(c["face"]),
                     "layout": lay, "cutout": m is not None, "bytes": os.path.getsize(p), **meta})
    if picks:
        im, meta = compose_thumb(picks[0]["frame"], picks[0]["face"], headline, accent, "cover", 1080, 1920)
        p = os.path.join(out_dir, "thumb_cover_1080x1920.png"); im.save(p, optimize=True)
        outs.append({"file": p, "t": round(picks[0]["t"], 2), "layout": "cover", "bytes": os.path.getsize(p), **meta})
    for o in outs:
        o["text_color"] = "#%02X%02X%02X" % o["text_color"]
    return outs


# ------------------------------------------------------------------ post pack
def write_post_pack(path, words, headline, chapter_text, chapter_ok, caption_text):
    sents = [s["text"] for s in C.sentences(words)] if words else []
    tc = lambda s: " ".join(w if re.search(r"\d|\$", w) else w.capitalize() for w in s.lower().split())
    cap1 = lambda s: s[:1].upper() + s[1:]
    payoff = sorted(sents[1:], key=lambda s: (not re.search(r"\d", s), -min(len(s.split()), 12)))
    titles = [tc(headline)] + ([sents[0].rstrip(".")] if sents else [])
    if payoff:
        pay = re.sub(r"^(so|and|but),?\s+", "", payoff[0].rstrip("."), flags=re.I)
        titles.append(f"{tc(headline)}: {cap1(pay)}")
    tags = ["#" + k for k in C.keywords(words, 6)] if words else []
    md = ["# Post pack (DRAFT)", "",
          "> Drafts derived only from the transcript. Nothing here adds claims; check facts, numbers and names before posting.",
          "", "## Title options", ""] + [f"{i + 1}. {t}" for i, t in enumerate(titles[:3])]
    md += ["", "## Description", "", " ".join(sents[:2]), ""]
    if chapter_text:
        md += ["Chapters:" if chapter_ok else "Chapters (NOT valid for YouTube chapters - see deliver_report.md):", chapter_text, ""]
    md += [" ".join(tags), "", "## Hashtags", "", " ".join(tags) or "(none)", "", "## Caption", "", caption_text or "(no transcript)", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return titles[:3], tags


# ------------------------------------------------------------------ orchestration
def resolve_input(inp, words_path=None):
    """What to deliver from a plan or a plain video: video, words, clean video for thumbs, matte, accent."""
    inp = os.path.abspath(inp)
    r = {"plan": None, "video": inp, "work": os.path.dirname(inp), "words": [], "clean": inp, "matte": None, "accent": (255, 225, 77)}
    if inp.lower().endswith(".json"):
        plan = load_json(inp); pdir = os.path.dirname(inp)
        P = lambda p: p if os.path.isabs(p) else os.path.abspath(os.path.join(pdir, p))
        work = P(plan.get("workDir", "."))
        video = P(plan.get("outputFile", "final.mp4"))
        if not os.path.exists(video):
            video = os.path.join(work, "composite.mp4")
        r.update(plan=plan, work=work, video=video, clean=video, words=plan.get("words") or [])
        if plan.get("source") and os.path.exists(P(plan["source"])):
            r["clean"] = P(plan["source"])
        if plan.get("matte") and os.path.exists(P(plan["matte"])):
            r["matte"] = P(plan["matte"])
        r["accent"] = _hex(plan.get("theme", {}).get("vars", {}).get("--c-accent"))
    wp = words_path or os.path.join(r["work"], "words.json")
    if words_path:  # an explicit --words file (e.g. SDH with [sound] tags) always wins over the plan's words
        r["words"] = []
    if not r["words"] and os.path.exists(wp):
        wj = load_json(wp)
        ws = wj.get("words", []) if isinstance(wj, dict) else wj
        vdur = probe(r["video"])["duration"]
        if words_path or (ws and abs((wj.get("duration") if isinstance(wj, dict) else ws[-1]["end"]) - vdur) < 0.5):
            r["words"] = ws
        else:
            log(f"{wp} does not match the video length - no captions (pass --words to force)")
    return r


def check_output(pr, path, target_dur):
    st = stream_info(path)
    warn = []
    if pr["max_bytes"] and st["bytes"] > pr["max_bytes"]:
        warn.append(f"file {st['bytes'] / MB:.1f} MB exceeds limit {pr['max_bytes'] / MB:.0f} MB")
    if abs(st["duration"] - target_dur) > 0.15 and pr["kind"] in ("video", "audio"):
        warn.append(f"duration {st['duration']:.2f}s vs expected {target_dur:.2f}s")
    if st["acodec"] and pr["kind"] in ("video", "audio"):
        st["loudness"] = measure_loudness(path)
        if pr["lufs"] is not None:
            if abs(st["loudness"]["I"] - pr["lufs"]) > 1.0:
                warn.append(f"integrated {st['loudness']['I']} LUFS vs target {pr['lufs']}")
            if st["loudness"]["TP"] > pr["tp"] + 0.2:
                warn.append(f"true peak {st['loudness']['TP']} dBTP over {pr['tp']}")
    return st, warn


def fix_codec_overshoot(pr, src, out, ctx, margin):
    """Lossy audio codecs (AAC at low rates) can push true peak over the ceiling. Re-encode only the
    audio with the ceiling lowered by the measured overshoot and remux (video stream copied)."""
    ac, _ = fitted_audio(src, {**pr, "tp": pr["tp"] - margin}, ctx.get("loud"), {})
    tmp = out + ".fix" + os.path.splitext(out)[1]
    ff(["ffmpeg", "-y", "-hide_banner", "-i", out, "-i", src, "-map", "0:v", "-map", "1:a", "-af", ac,
        "-c:v", "copy", "-c:a", pr["acodec"], "-b:a", pr["abr"], "-ar", str(pr["ar"]), "-map_metadata", "0",
        "-map_chapters", "0", "-shortest", "-movflags", "+faststart", tmp])
    os.replace(tmp, out)


def deliver_one(name, video, info, words, has_cap_el, burn, cps, trim, out_dir, stem, ctx):
    """Encode one preset and return its report entry (never raises)."""
    pr, dur, fps = PRESETS[name], info["duration"], info.get("fps", 30)
    entry = {"preset": name, "note": pr["note"], "safe_zone": pr["safe"], "lufs_target": pr["lufs"],
             "captions_recommendation": "burn in (muted autoplay)" if pr["burn"] else "sidecar SRT/VTT"}
    if pr["kind"] == "note":
        return {**entry, "ok": None}
    want_burn = burn == "yes" or (burn == "auto" and pr["burn"] and not has_cap_el)
    if want_burn and words and pr["kind"] == "video":
        H, W = pr["h"] or info["height"], pr["w"] or info["width"]
        ctx["burn_cues"][name] = C.build_cues(words, cps=cps, fps=fps, max_chars=26 if H > W else 42)
    if pr["burn"] and has_cap_el and burn == "auto":
        entry["captions_note"] = "not burned: the plan already shows creator captions"
    too_long = bool(pr["max_dur"] and dur > pr["max_dur"] and pr["kind"] not in ("gif", "webp"))
    ctx["trim_to"] = pr["max_dur"] if (trim and too_long) else None
    warn = [f"duration {dur:.1f}s exceeds {name} max {pr['max_dur']}s (use --trim)"] if too_long and not trim else []
    out = os.path.join(out_dir, f"{stem}_{name}.{pr['ext']}")
    try:
        log(f"{name} -> {os.path.basename(out)}")
        extra = (encode_video if pr["kind"] == "video" else encode_other)(name, pr, video, info, out, ctx)
        target = min(dur, ctx["trim_to"] or dur, pr["max_dur"] if pr["kind"] in ("gif", "webp") else dur)
        st, w2 = check_output(pr, out, target)
        lo = st.get("loudness")
        if lo and pr["lufs"] is not None and lo["TP"] > pr["tp"] + 0.2 and pr["ext"] in ("mp4", "mov"):
            extra["loudness_mode"] += f"; codec overshoot {lo['TP']} dBTP corrected"
            fix_codec_overshoot(pr, video, out, ctx, lo["TP"] - pr["tp"] + 0.3)
            st, w2 = check_output(pr, out, target)
        entry.update(ok=True, file=out, **extra, probe=st, warnings=warn + w2)
    except (RuntimeError, ValueError, SystemExit) as e:
        entry.update(ok=False, error=str(e)[-800:], warnings=warn)
        log(f"{name} FAILED: {str(e)[-300:]}")
    return entry


def deliver(inp, to, out_dir, track_path=None, words_path=None, burn="auto", burn_engine="auto", cps=C.CPS_ADULT,
            trim=False, chapters_spec=None, headline=None, thumbs=True, post=True):
    src = resolve_input(inp, words_path)
    video, words, plan = src["video"], src["words"], src["plan"]
    os.makedirs(out_dir, exist_ok=True)
    info = {**probe(video), **{k: v for k, v in stream_info(video).items() if k in ("pix_fmt", "vcodec")}}
    fps, dur = info.get("fps", 30), info["duration"]
    track = load_track(track_path or os.path.join(src["work"], "track.json"), info["width"], info["height"])
    loud = measure_loudness(video) if info["has_audio"] else None
    rep = {"input": video, "plan": inp if plan else None, "source_info": info, "source_loudness": loud,
           "track": bool(track), "outputs": [], "notes": []}
    stem = os.path.splitext(os.path.basename(video))[0]

    # subtitles (sidecars, broadcast rules)
    if words:
        cues = C.build_cues(words, cps=cps, fps=fps)
        files = {"srt": (C.write_srt, C.parse_srt), "vtt": (C.write_vtt, C.parse_vtt), "ttml": (C.write_ttml, C.parse_ttml)}
        rep["captions"] = {"cues": len(cues), "cps_limit": cps, "files": {}, "scc": "skipped: needs CEA-608 encoding (no free encoder in FFmpeg)"}
        for ext, (wr, pa) in files.items():
            p = os.path.join(out_dir, f"captions.{ext}"); wr(cues, p)
            back = pa(p)
            rep["captions"]["files"][ext] = {"file": p, "parsed_cues": len(back), "issues": C.validate_cues(back, cps=cps, fps=fps)}
        caption_text = " ".join(" ".join(c["lines"]) for c in cues)
    else:
        caption_text = ""
        rep["notes"].append("no transcript words: no captions, chapters or post text")

    # chapters
    chapters = C.parse_chapters(chapters_spec) if chapters_spec else (plan or {}).get("chapters") or \
        (C.auto_chapters(words, dur) if words else [])
    meta, ch_text, ch_probs = None, "", ["no chapters (video too short for >= 3 x 10 s or no transcript)"]
    if chapters:
        ch_text, ch_probs = C.youtube_chapters(chapters, dur)
        open(os.path.join(out_dir, "chapters.txt"), "w", encoding="utf-8").write(ch_text + "\n")
        meta = os.path.join(out_dir, "chapters.ffmeta")
        C.write_ffmetadata(chapters, dur, meta)
    rep["chapters"] = {"list": chapters, "youtube_text": ch_text, "youtube_valid": not ch_probs, "problems": ch_probs}

    # burn-in decision
    has_cap_el = any(e.get("type") == "captions" for e in (plan or {}).get("elements", []))
    engine = burn_engine if burn_engine != "auto" else ("libass" if libass_ok() else "pillow")
    ctx = {"loud": loud, "track": track, "meta": meta, "burn_engine": engine, "burn_cues": {}}

    for name in to:
        rep["outputs"].append(deliver_one(name, video, info, words, has_cap_el, burn, cps, trim, out_dir, stem, ctx))

    hl = headline_from(plan, words, headline)
    if thumbs:
        tt = track
        if src["clean"] != video:                       # thumbs come from the clean source: use its own face track
            cw, ch = _dims(src["clean"])
            tt = next(filter(None, (load_track(p, cw, ch) for p in
                                    (track_path, plan_track(plan), os.path.join(src["work"], "track.json")))), None)
        rep["thumbnails"] = {"headline": hl, "source": src["clean"], "face_track": bool(tt)}
        try:
            rep["thumbnails"]["files"] = make_thumbnails(src["clean"], out_dir, hl, src["accent"], tt, src["matte"])
        except RuntimeError as e:                       # e.g. no installed font for the headline's script
            log(f"thumbnails FAILED: {e}"); rep["notes"].append(f"thumbnails failed: {e}")
    for t in ([hl] if thumbs else []) + ([caption_text] if ctx["burn_cues"] and engine == "pillow" else []):
        n = shaping_note(t)
        if n and n not in rep["notes"]:
            log(n); rep["notes"].append(n)
    if post:
        titles, tags = write_post_pack(os.path.join(out_dir, "post.md"), words, hl, ch_text, not ch_probs, caption_text)
        rep["post"] = {"file": os.path.join(out_dir, "post.md"), "titles": titles, "hashtags": tags}
    for f in os.listdir(out_dir):
        if f.startswith(("_graph_", "_reframe_", "_burn_")):
            fp = os.path.join(out_dir, f)
            shutil.rmtree(fp) if os.path.isdir(fp) else os.unlink(fp)
    save_json(os.path.join(out_dir, "deliver_report.json"), rep)
    write_report_md(rep, os.path.join(out_dir, "deliver_report.md"))
    return rep


def _dims(path):
    i = probe(path)
    return i["width"], i["height"]


def write_report_md(rep, path):
    L = ["# Delivery report", "", f"Input: `{rep['input']}`", ""]
    if rep.get("source_loudness"):
        s = rep["source_loudness"]; L += [f"Source loudness: {s['I']} LUFS, {s['TP']} dBTP, LRA {s['LRA']}", ""]
    L += ["| preset | ok | file | size MB | WxH | fps | codec | LUFS / dBTP (target) | reframe | warnings |", "|---|---|---|---|---|---|---|---|---|---|"]
    for o in rep["outputs"]:
        p = o.get("probe", {}); lo = p.get("loudness")
        ld = f"{lo['I']} / {lo['TP']} ({o['lufs_target']})" if lo else "-"
        L.append(f"| {o['preset']} | {o.get('ok')} | {os.path.basename(o.get('file', '')) or o.get('error', o['note'])[:80]} | "
                 f"{p.get('bytes', 0) / MB:.2f} | {p.get('width')}x{p.get('height')} | {p.get('fps')} | {p.get('vcodec') or p.get('acodec')} | "
                 f"{ld} | {o.get('reframe', '-')} | {'; '.join(o.get('warnings', []))} |")
    if rep.get("captions"):
        c = rep["captions"]; L += ["", f"Captions: {c['cues']} cues, {c['cps_limit']} cps limit. " +
                                   ", ".join(f"{k}: {len(v['issues'])} issues" for k, v in c["files"].items()) + f". SCC {c['scc']}."]
    ch = rep["chapters"]
    L += ["", "Chapters: " + ("valid for YouTube" if ch["youtube_valid"] else "; ".join(ch["problems"])), "", ch["youtube_text"]]
    for t in rep.get("thumbnails", {}).get("files", []):
        L.append(f"- thumbnail `{os.path.basename(t['file'])}` t={t['t']}s layout={t['layout']} contrast={t.get('contrast')}:1")
    L += ["", "Notes: " + "; ".join(rep["notes"] + [f"{o['preset']}: {o['note']}" for o in rep["outputs"] if o.get("ok") is None])]
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


def self_test():
    assert script_of("हर बात 5") == "DEVANAGARI" and script_of("ok नमस्ते") == "DEVANAGARI"
    assert script_of("Top 5 tips") == "LATIN" and script_of("") == "LATIN"
    assert _title_band(0, 960, 1920)[2] == "low" and _title_band(960, 1728, 1920)[2] == "top"   # head at top / at bottom
    y0, y1, _ = _title_band(461, 1248, 1920)                     # whatsapp-spiral selfie: face 0.24-0.65 of the cover
    assert y1 <= 461 or y0 >= 1248, "title band overlaps the face"
    assert _face_span((0, 50, 100, 40, 60), (0, 0, 100, 200), 400) == (140.0, 260.0)
    hi = font_face("हर बात तीरा ज़िन्दगी")                         # raises if no Devanagari font is installed
    assert _has_glyphs(*hi, "हरबातीज़िन्दगी"), hi
    if _has_glyphs("arialbd.ttf", 0, "abc"):                     # Windows: Arial Bold has no Devanagari -> tofu detected
        assert not _has_glyphs("arialbd.ttf", 0, "ह") and font_face("Top 5 tips", "arialbd.ttf")[0] == "arialbd.ttf"
    print("self-test ok:", hi, "|", shaping_note("हर") or "shaping ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?")
    ap.add_argument("--to", default="youtube")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--track", default=None)
    ap.add_argument("--words", default=None)
    ap.add_argument("--burn", choices=["auto", "yes", "no"], default="auto")
    ap.add_argument("--burn-engine", choices=["auto", "libass", "pillow"], default="auto")
    ap.add_argument("--cps", type=float, default=C.CPS_ADULT)
    ap.add_argument("--kids", action="store_true", help="17 cps reading speed")
    ap.add_argument("--trim", action="store_true", help="cut to the platform max duration")
    ap.add_argument("--chapters", default=None)
    ap.add_argument("--headline", default=None)
    ap.add_argument("--no-thumbs", action="store_true")
    ap.add_argument("--no-post", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true", help="check script-aware font picking and the cover title band")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.list or not a.input:
        for k, p in PRESETS.items():
            print(f"{k:16} {p['kind']:5} {str(p['w'] or 'src')}x{str(p['h'] or 'src'):5} {p['vcodec']:10} lufs={p['lufs']} "
                  f"max={p['max_dur']}s  {p['note'][:70]}")
        return
    to = [t.strip() for t in a.to.split(",") if t.strip()]
    bad = [t for t in to if t not in PRESETS]
    if bad:
        sys.exit(f"unknown preset(s): {bad}. See --list")
    base = os.path.dirname(os.path.abspath(a.input))
    rep = deliver(a.input, to, os.path.abspath(a.out_dir or os.path.join(base, "deliver")), a.track, a.words, a.burn,
                  a.burn_engine, C.CPS_KIDS if a.kids else a.cps, a.trim, a.chapters, a.headline, not a.no_thumbs, not a.no_post)
    failed = [o["preset"] for o in rep["outputs"] if o.get("ok") is False]
    log(f"delivered {sum(1 for o in rep['outputs'] if o.get('ok'))}/{len(to)} -> {os.path.dirname(rep['post']['file']) if rep.get('post') else ''}"
        + (f"  FAILED: {failed}" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
