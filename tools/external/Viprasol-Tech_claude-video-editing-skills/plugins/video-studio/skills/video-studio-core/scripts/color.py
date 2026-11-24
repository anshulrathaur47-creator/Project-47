#!/usr/bin/env python3
"""Video Studio colour: analysis, technical correction, creative looks, film texture, shot matching, scopes, QC.

Pipeline order (see references/color.md):
  input transform (log LUT / user LUT) -> correction (WB, levels, contrast, sat | shot match)
  -> look (LUT, intensity, skin-protected)   [speaker source, BEFORE overlays: render.py]
  -> texture (grain, halation, bloom, weave, flicker, CA, letterbox) -> legal limiter   [final: finish.py]

usage:
  color.py analyze VIDEO --work W
  color.py preview VIDEO --look portra [--intensity 0.8] [--correct] [--t 3] --out x.png
  color.py looks-sheet VIDEO [--t 3] [--correct] --out sheet.png
  color.py scopes VIDEO [--t 3] --out s.png
  color.py qc VIDEO
Never uses drawtext (crashes on this machine); labels are drawn with Pillow.
"""
import argparse
import json
import math
import os
import subprocess
import tempfile

import cv2
import numpy as np

from vs_common import CORE, die, log, probe, run, save_json
import luts as L

LUT_DIR = os.path.join(CORE, "luts")

# The 13 original finish.py grades, kept byte-identical so old plans look the same.
GRADES = {
    "none": "",
    "warm": "colorbalance=rs=.05:bs=-.05:rm=.04:bm=-.04,eq=saturation=1.08",
    "cool": "colorbalance=rs=-.04:bs=.06:rm=-.02:bm=.04,eq=saturation=1.02",
    "teal-orange": "colorbalance=rs=-.08:gs=-.02:bs=.10:rh=.10:gh=.02:bh=-.08,eq=contrast=1.05:saturation=1.1",
    "punchy": "eq=contrast=1.12:saturation=1.25",
    "film": "curves=master='0/0.04 0.5/0.5 1/0.95',colorbalance=rm=.03:bm=-.03,eq=saturation=0.92",
    "bw": "hue=s=0,eq=contrast=1.18",
    "vintage": "curves=preset=vintage,eq=saturation=0.9",
    "faded": "curves=master='0/0.08 1/0.92',eq=saturation=0.85",
    "neon": "eq=contrast=1.1:saturation=1.35,colorbalance=rs=.03:bs=.06",
    "vhs": "rgbashift=rh=5:bh=-5,eq=saturation=1.35:contrast=1.08,scale=iw/2:-2,scale={W}:{H}:flags=bilinear",
    "pastel": "eq=saturation=0.8:brightness=0.04,curves=master='0/0.06 1/1'",
    "noir": "hue=s=0,curves=master='0/0 0.4/0.3 1/1',eq=contrast=1.3",
}
LOOK_NAMES = list(GRADES) + list(L.LOOKS)
LOG_NAMES = list(L.LOGS)
_uid = [0]


def _label(p="c"):
    _uid[0] += 1
    return f"{p}{_uid[0]}"


def ffpath(p: str) -> str:
    """Quote a file path for an FFmpeg filter option (Windows drive colon escaped)."""
    return "'" + os.path.abspath(p).replace("\\", "/").replace(":", "\\:").replace("'", "") + "'"


def lut_filter(path: str) -> str:
    return f"lut3d=file={ffpath(path)}:interp=tetrahedral"


def _blend_back(chain: str, opacity: float) -> str:
    """Mix `chain` over the untouched input at `opacity` (works inside a filter_complex or -vf)."""
    a, b, g = _label("ba"), _label("bb"), _label("bg")
    return f"split=2[{a}][{b}];[{b}]{chain}[{g}];[{g}][{a}]blend=all_mode=normal:all_opacity={opacity:.3f}"


# ---------------------------------------------------------------- frame sampling + stats
def _ss(t: float) -> list:
    """Seek args; none at t<=0 (a -ss 0 on a still image yields no frame)."""
    return ["-ss", f"{t:.3f}"] if t > 0 else []


def grab(video: str, t: float, width: int = 480, pre: str = "") -> np.ndarray:
    """One RGB float frame (H,W,3) in [0,1] at time t, optionally after an FFmpeg chain `pre`."""
    vf = ",".join(x for x in [pre, f"scale={width}:-2", "format=rgb24"] if x)
    p = subprocess.run(["ffmpeg", "-v", "error", *_ss(t), "-i", video, "-frames:v", "1",
                        "-vf", vf, "-f", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode or not p.stdout:
        die(f"cannot grab frame at {t}s from {video}: {p.stderr.decode(errors='ignore')[-400:]}")
    n = len(p.stdout) // 3
    h = n // width
    return np.frombuffer(p.stdout, np.uint8)[: h * width * 3].reshape(h, width, 3).astype(np.float32) / 255.0


def sample_frames(video: str, samples: int = 12, pre: str = "", width: int = 480) -> np.ndarray:
    dur = probe(video)["duration"]
    ts = [0.0] if dur < 0.2 else [dur * (i + 0.5) / samples for i in range(samples)]
    return np.stack([grab(video, t, width, pre) for t in ts])


def skin_mask_frame(rgb: np.ndarray) -> np.ndarray:
    """Boolean YCrCb skin mask (classic Cr 133-173, Cb 77-127) excluding very dark/bright pixels."""
    ycc = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2YCrCb)
    y, cr, cb = ycc[..., 0], ycc[..., 1], ycc[..., 2]
    return (cr >= 133) & (cr <= 173) & (cb >= 77) & (cb <= 127) & (y > 40) & (y < 240)


def _grey_estimate(px, Y, mx, skin):
    """Iterative grey-pixel estimate: grey-world over non-skin unclipped pixels, then re-pick the 30% least
    chromatic pixels *after* provisional correction (so a cast does not hide the true neutrals), 4 rounds.
    Confidence drops when even the picked 'neutrals' are strongly coloured (scene likely has no greys,
    e.g. a deliberately blue set), so WB strength is scaled down instead of neutralising the design."""
    base = (Y > 0.05) & (mx < 0.98) & ~skin
    if base.sum() < 200:
        base = np.ones(len(px), bool)
    est = px[base].mean(0)
    for _ in range(4):
        cp = px * (est[1] / np.maximum(est, 1e-3))
        ch = cp.max(1) - cp.min(1)
        sel = base & (ch <= np.percentile(ch[base], 30))
        if sel.sum() < 50:
            break
        est = px[sel].mean(0)
    rc = float((est.max() - est.min()) / max(est.mean(), 1e-3))
    return est, float(np.clip((0.55 - rc) / 0.25, 0.2, 1.0))


def stats_from_frames(fr: np.ndarray) -> dict:
    px = fr.reshape(-1, 3)
    Y = px @ L.LUMA
    mx, mn = px.max(1), px.min(1)
    chroma = mx - mn
    skin = np.concatenate([skin_mask_frame(f).ravel() for f in fr])
    grey, wb_conf = _grey_estimate(px, Y, mx, skin)
    pct = {f"p{q:g}": float(np.percentile(Y, q)) for q in (0.5, 1, 5, 50, 95, 99, 99.5)}
    s = {
        **pct,
        "mean_rgb": [float(x) for x in px.mean(0)],
        "grey_rgb": [float(x) for x in grey],
        "wb_confidence": wb_conf,
        "cast_rb": float(grey[0] - grey[2]),  # >0 warm, <0 blue
        "cast_g": float(grey[1] - (grey[0] + grey[2]) / 2),  # >0 green, <0 magenta
        "saturation": float(np.mean(chroma / np.maximum(mx, 1e-3) * (mx > 0.05))),
        "chroma": float(chroma.mean()),
        "chroma_wb": float(np.ptp(px * (grey[1] / np.maximum(grey, 1e-3)), axis=1).mean()),  # after neutralising
        "luma_std": float(Y.std()),
        "contrast": pct["p95"] - pct["p5"],
        "clip_low_pct": float((Y < 0.02).mean() * 100),
        "clip_high_pct": float((mx > 0.985).mean() * 100),
        "skin_pct": float(skin.mean() * 100),
    }
    if skin.sum() > 200:
        sp = px[skin]
        s["skin_luma"] = float(np.median(sp @ L.LUMA))
        s["skin_rgb"] = [float(x) for x in sp.mean(0)]
    s["likely_log"] = bool(s["p99"] - s["p1"] < 0.62 and s["p1"] > 0.05 and s["saturation"] < 0.22)
    return s


def analyze(video_path: str, samples: int = 12, work: str | None = None, pre: str = "") -> dict:
    """Measure levels/cast/saturation/skin/clipping/log-likelihood over `samples` frames. Saves <work>/color.json."""
    fr = sample_frames(video_path, samples, pre)
    s = {"path": os.path.abspath(video_path), "pre": pre, "samples": len(fr), **stats_from_frames(fr)}
    if work:
        save_json(os.path.join(work, "color.json"), s)
    return s


# ---------------------------------------------------------------- technical correction
def input_chain(cfg: dict) -> str:
    """Log -> Rec.709 (approximate generated LUT) and/or a user LUT (official camera LUT preferred)."""
    f = []
    lg = (cfg.get("log") or "").lower().replace("-", "").replace("_", "")
    if lg and lg not in ("off", "none", "auto"):
        if lg not in L.LOGS:
            die(f"unknown log '{cfg['log']}'. Use one of {', '.join(LOG_NAMES)} or pass an official LUT via \"lut\"")
        p = os.path.join(LUT_DIR, f"log-{lg}-to-709.cube")
        if not os.path.exists(p):
            L.generate(only={lg})
        f.append(lut_filter(p))
    if cfg.get("lut"):
        if not os.path.exists(cfg["lut"]):
            die(f"LUT not found: {cfg['lut']}")
        f.append(lut_filter(cfg["lut"]))
    return ",".join(f)


def _wb_filter(stats: dict, cfg: dict) -> str:
    mode = cfg.get("wb", True)
    if mode in (False, "off", "none"):
        return ""
    if isinstance(mode, (int, float)) and not isinstance(mode, bool):
        return f"colortemperature=temperature={int(mode)}:pl=1"
    # Applied AFTER the levels curve, so gains are black-referenced: a neutral lift (flat/log footage)
    # must not dilute the cast estimate.
    black = _bw_points(stats)[0]
    r, g, b = (np.array(stats["grey_rgb"]) - black).tolist()
    if min(r, g, b) < 0.02:
        return ""
    rc = (max(r, g, b) - min(r, g, b)) / (sum((r, g, b)) / 3)  # how coloured the 'neutrals' still are
    conf = min(stats.get("wb_confidence", 1.0), float(np.clip((0.55 - rc) / 0.25, 0.2, 1.0)))
    strength = float(cfg.get("wb_strength", 0.85)) * conf  # <1 keeps intended mood
    gr = 1 + (g / r - 1) * strength
    gb = 1 + (g / b - 1) * strength
    gr, gb = float(np.clip(gr, 0.7, 1.4)), float(np.clip(gb, 0.7, 1.4))
    norm = 1 / (L.LUMA @ [gr, 1, gb])  # keep luma unchanged
    gr, gg, gb = gr * norm, norm, gb * norm
    if max(abs(gr - 1), abs(gg - 1), abs(gb - 1)) < 0.03:  # deadband: leave near-neutral footage alone
        return ""
    return f"colorchannelmixer=rr={gr:.4f}:gg={gg:.4f}:bb={gb:.4f}"


def _bw_points(stats: dict) -> tuple[float, float]:
    """Black/white points. Normal footage: only trim near-black/near-white (a scene without whites stays
    without whites). Flat / log-like footage: full stretch."""
    flat = stats.get("likely_log") or stats["contrast"] < 0.35
    black = float(np.clip(stats["p0.5"], 0.0, 0.14 if flat else 0.08))
    white = float(np.clip(stats["p99.5"], 0.5 if flat else 0.85, 1.0))
    if "skin_luma" in stats:  # never let the black point bite into skin shadows
        black = min(black, stats["skin_luma"] * 0.35)
    return black, white


def _levels_filter(stats: dict, cfg: dict) -> str:
    """Black/white point + bounded mid-tone move as one curves filter. Mids are only moved when the
    stretched median is outside 0.30-0.55 (fixes under/over exposure, leaves deliberate low/high key alone),
    and never so far that skin clips."""
    black, white = _bw_points(stats)
    span = max(white - black, 0.2)
    mid_in = float(np.clip(stats["p50"], black + 0.05, white - 0.05))
    mid_lin = (mid_in - black) / span
    mid_out = float(np.clip(mid_lin, 0.30, 0.55))
    mid_out = float(np.clip(mid_out, mid_lin * 0.75, mid_lin * 1.8))  # bounded gamma move
    if "skin_luma" in stats and (stats["skin_luma"] - black) / span * (mid_out / mid_lin) > 0.9:
        mid_out = max(min(mid_out, mid_lin), 0.05)  # would clip skin: do not brighten mids
    if black < 0.01 and white > 0.985 and abs(mid_out - mid_lin) < 0.02:
        return ""
    return f"curves=master='{black:.4f}/0 {mid_in:.4f}/{mid_out:.4f} {white:.4f}/1'"


def _contrast_filter(stats: dict, cfg: dict) -> str:
    k = cfg.get("contrast")
    if k is None:  # auto: only add contrast to flat images
        k = float(np.clip(1 + (0.6 - stats["contrast"]) * 0.4, 1.0, 1.15)) if stats["contrast"] < 0.6 else 1.0
    k = float(k)
    if abs(k - 1) < 0.01:
        return ""
    d = 0.25 * (k - 1) * 0.5  # S-curve via 1/4 and 3/4 points
    return f"curves=master='0/0 0.25/{0.25 - d:.4f} 0.75/{0.75 + d:.4f} 1/1'"


SAT_TARGET = 0.16  # mean RGB chroma (max-min) after WB + levels for natural, healthy colour


def _sat_filter(stats: dict, cfg: dict, auto: bool) -> str:
    """Auto: bring chroma (measured after the black/white stretch) toward SAT_TARGET, but only lift
    dull images (<75% of target) or calm garish ones (>180%); everything between is left as shot."""
    s = 1.0
    if auto and "chroma" in stats:
        black, white = _bw_points(stats)
        eff = stats.get("chroma_wb", stats["chroma"]) / max(white - black, 0.2)
        if eff < SAT_TARGET * 0.75:
            s = float(np.clip(SAT_TARGET * 0.85 / max(eff, 0.02), 1.0, 1.4))
        elif eff > SAT_TARGET * 1.8:
            s = float(np.clip(SAT_TARGET * 1.8 / eff, 0.8, 1.0))
    s *= float(cfg.get("saturation", 1.0))
    return "" if abs(s - 1) < 0.02 else f"eq=saturation={s:.3f}"


def correction_chain(stats: dict | None, cfg: dict | None = None, work: str | None = None) -> str:
    """Technical primary correction chain for the speaker/source video (before looks and overlays).

    cfg = plan["color"]: {"auto": true, "wb": true|"off"|kelvin, "wb_strength": 0.8, "exposure": stops,
                          "contrast": 1.1, "saturation": 1.0, "log": "slog3"|..., "lut": path, "match": "ref.png"}
    `stats` comes from analyze(); if an input transform is configured and stats were measured without it,
    the source is re-analysed through the transform so the correction sees Rec.709-like data.
    """
    cfg = dict(cfg or {})
    pre = input_chain(cfg)
    auto = cfg.get("auto", True)
    if stats is None and (auto or cfg.get("match")):
        die("correction_chain needs stats from analyze() when auto/match is on")
    if stats is not None and stats.get("pre", "") != pre and (auto or cfg.get("match")):
        stats = analyze(stats["path"], stats.get("samples", 12), work, pre)
    f = [pre] if pre else []
    if auto:
        f += [_levels_filter(stats, cfg), _wb_filter(stats, cfg)]
    if cfg.get("exposure"):
        f.append(f"exposure=exposure={float(cfg['exposure']):.3f}")
    if auto or cfg.get("contrast") is not None:
        f.append(_contrast_filter(stats or {"contrast": 1}, cfg))
    f.append(_sat_filter(stats or {}, cfg, auto) if (auto or "saturation" in cfg) else "")
    if cfg.get("match"):  # fine-tune the already-corrected image toward the reference
        if cfg["match"] == "first":
            log("color.match='first' must be resolved to a file path by the caller; skipping match")
        else:
            done = ",".join(x for x in f if x)
            f.append(match_chain(stats["path"], cfg["match"], pre=done, work=work,
                                 strength=float(cfg.get("match_strength", 0.85))))
    return ",".join(x for x in f if x)


# ---------------------------------------------------------------- looks
def _intensity_lut(name: str, intensity: float, work: str | None) -> str:
    base = os.path.join(LUT_DIR, f"{name}.cube")
    if not os.path.exists(base):
        L.generate(only={name})
    if intensity >= 0.999:
        return base
    cache = os.path.join(work or tempfile.gettempdir(), "vs_luts")
    p = os.path.join(cache, f"{name}_i{int(round(intensity * 100)):03d}.cube")
    if not os.path.exists(p):
        rgb, n = L.read_cube(base)
        ident = L.lattice(n)
        L.write_cube(p, ident + (rgb - ident) * intensity, f"{name} @ {intensity:.2f}", n)
    return p


def halation_chain(strength: float = 0.4, W: int = 1920) -> str:
    """CineStill-style halation: highlights -> red/orange -> blur -> screen over the image."""
    a, b, h = _label("ha"), _label("hb"), _label("hh")
    sig = max(4, W / 90)
    return (f"format=gbrp,split=2[{a}][{b}];[{b}]curves=all='0/0 0.72/0 1/1',"
            f"colorchannelmixer=rr=1:rg=0.3:gr=0.25:gg=0.25:br=0.05:bb=0.05,gblur=sigma={sig:.1f}[{h}];"
            f"[{a}][{h}]blend=all_mode=screen:all_opacity={strength:.3f}")


def glow_chain(strength: float = 0.3, W: int = 1920, threshold: float = 0.6, sigma_div: float = 60) -> str:
    """Bloom / glow: untinted highlight blur screened over the image."""
    a, b, h = _label("ga"), _label("gb"), _label("gh")
    return (f"format=gbrp,split=2[{a}][{b}];[{b}]curves=all='0/0 {threshold:.2f}/0 1/1',gblur=sigma={W / sigma_div:.1f}[{h}];"
            f"[{a}][{h}]blend=all_mode=screen:all_opacity={strength:.3f}")


LOOK_EXTRAS = {  # spatial parts a LUT cannot hold
    "dreamy": lambda W, H: glow_chain(0.35, W, 0.45, 50),
    "90s-camcorder": lambda W, H: f"rgbashift=rh=2:bh=-2,scale=iw*2/3:-2,scale={W}:{H}:flags=bicubic",
}


def look_chain(name: str, intensity: float = 1.0, W: int = 1920, H: int = 1080,
               work: str | None = None, halation: float = 0.0) -> str:
    """Creative look. Legacy grade names give the exact old finish.py filters; others use generated LUTs.
    intensity 0..1 (LUT looks lerp inside the LUT; legacy grades mix via blend). halation>0 adds halation."""
    if not name or name == "none" or intensity <= 0.001:
        return halation_chain(halation, W) if halation else ""
    intensity = float(min(intensity, 1.0))
    if name in GRADES:
        g = GRADES[name].format(W=W, H=H)
        out = g if intensity >= 0.999 else _blend_back(g, intensity)
    elif name in L.LOOKS:
        out = lut_filter(_intensity_lut(name, intensity, work))
        if name in LOOK_EXTRAS:
            out += "," + LOOK_EXTRAS[name](W, H)
    else:
        die(f"unknown look '{name}'. Available: {', '.join(LOOK_NAMES)}")
    if halation:
        out += "," + halation_chain(halation, W)
    return out


# ---------------------------------------------------------------- plan integration
def grade_on_source(plan: dict) -> bool:
    """True when the creative grade belongs on the camera footage (render.py) rather than the final
    composite (finish.py). Pros grade the picture, not the graphics: captions keep their brand colours.
    Legacy finish.grade moves to the source too unless "finish": {"gradeStage": "final"}."""
    sp = plan.get("speaker") or {}
    has_src = bool(plan.get("source")) and sp.get("mode", "full") != "none"
    return has_src and (plan.get("finish") or {}).get("gradeStage", "source") != "final"


def source_chain(plan: dict, src: str, work: str, W: int, H: int) -> str:
    """Full source-stage chain for render.py: input transform + correction (plan["color"]) + look.
    Look comes from plan["color"]["look"], else the legacy plan["finish"]["grade"]."""
    cfg = dict(plan.get("color") or {})
    fin = plan.get("finish") or {}
    parts = []
    if cfg:
        want_stats = cfg.get("auto", True) or cfg.get("match")
        stats = analyze(src, 12, work) if want_stats else None
        if cfg.get("match") == "first":
            cfg.pop("match")
        parts.append(correction_chain(stats, cfg, work))
    if grade_on_source(plan):
        look = cfg.get("look") or fin.get("grade", "none")
        parts.append(look_chain(look, float(cfg.get("intensity", 1.0)), W, H, work, float(cfg.get("halation", 0))))
    return ",".join(p for p in parts if p)


# ---------------------------------------------------------------- texture + legal (final output)
LEGAL = {"strict": (16, 235, 16, 240), "ebu": (14, 241, 16, 240)}  # 8-bit Y and C (EBU R103 -1%..103% luma)


def _letterbox(v, W, H) -> str:
    v = str(v)
    ratio = float(v.split(":")[0]) / float(v.split(":")[1]) if ":" in v else float(v)
    bar = int(H * ratio) if ratio < 1 else int(round((H - W / ratio) / 2))
    if bar <= 0:
        return ""
    return (f"drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,"
            f"drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill")


def _grain(cfg, W) -> str:
    g = cfg.get("grain")
    if not g:
        return ""
    s = int(g if not isinstance(g, dict) else g.get("strength", 8))
    if isinstance(g, dict) and g.get("luma_weighted"):
        a, b, n = _label("na"), _label("nb"), _label("nn")
        return (f"format=yuv420p,split=2[{a}][{b}];[{b}]noise=c0s={s}:c0f=t+u[{n}];"
                f"[{a}][{n}]blend=c0_expr='A+(B-A)*(0.35+0.65*sin(PI*A/255))':c1_expr='A':c2_expr='A'")
    return f"noise=c0s={s}:c0f=t+u"


def texture_chain(cfg: dict | None, W: int = 1920, H: int = 1080) -> str:
    """Film finishing for the FINAL output (finish.py). cfg = plan["finish"] keys (all optional):
    diffusion 0..1 | halation 0..1 | bloom 0..1 | aberration px | sharpen 0..1.5 | vignette true|0..1 |
    weave px | flicker 0..0.1 | grain int or {"strength":8,"luma_weighted":true} | letterbox 2.39|"2.39:1"|0.1 |
    dither true | legal "strict"|"ebu"|false"""
    c = dict(cfg or {})
    f = []
    if c.get("diffusion"):
        d = float(c["diffusion"])
        f.append(glow_chain(0.25 * d, W, 0.35, 40))
        a, b, s = _label("da"), _label("db"), _label("ds")
        f.append(f"split=2[{a}][{b}];[{b}]gblur=sigma={W / 400:.1f}[{s}];[{s}][{a}]blend=all_mode=normal:all_opacity={0.35 * d:.3f}")
    if c.get("halation"):
        f.append(halation_chain(float(c["halation"]) if c["halation"] is not True else 0.4, W))
    if c.get("bloom"):
        f.append(glow_chain(float(c["bloom"]) if c["bloom"] is not True else 0.3, W))
    if c.get("aberration"):
        px = max(1, int(c["aberration"]))
        f.append(f"rgbashift=rh={px}:bh=-{px}")
    if c.get("sharpen"):
        amt = 0.45 if c["sharpen"] is True else float(c["sharpen"])
        f.append(f"unsharp=5:5:{amt:.2f}")
    if c.get("vignette"):
        v = 0.5 if c["vignette"] is True else float(c["vignette"])
        f.append(f"vignette=angle={0.2 + 0.5 * v:.3f}")  # 0.45 rad ~ PI/7 subtle .. 0.7 strong
    if c.get("weave"):
        p = float(c["weave"]) if c["weave"] is not True else 2.0
        m = int(math.ceil(p)) * 2 + 2
        f.append(f"crop=iw-{2 * m}:ih-{2 * m}:{m}+{p:.2f}*sin(t*2.1)*sin(t*0.37+1):{m}+{p * 0.7:.2f}*sin(t*1.7+2)*cos(t*0.53),"
                 f"scale={W}:{H}")
    if c.get("flicker"):
        a = float(c["flicker"]) if c["flicker"] is not True else 0.02
        f.append(f"eq=brightness='{a:.4f}*(sin(t*13)*0.6+sin(t*29+1)*0.4)':eval=frame")
    f.append(_grain(c, W))
    if c.get("letterbox"):
        f.append(_letterbox(c["letterbox"], W, H))
    if c.get("dither"):
        f.append("noise=c0s=1:c0f=t+u")
    legal = c.get("legal", "strict")
    if legal:
        ymin, ymax, cmin, cmax = LEGAL.get(legal, LEGAL["strict"])
        f.append(f"format=yuv420p,limiter=min={ymin}:max={ymax}:planes=1,limiter=min={cmin}:max={cmax}:planes=6")
    return ",".join(x for x in f if x)


# ---------------------------------------------------------------- shot matching
def _lab_stats(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    px = rgb.reshape(-1, 3)
    ok = (px.max(1) < 0.98) & (px.max(1) > 0.03)  # ignore clipped / crushed
    lab = cv2.cvtColor(px[ok if ok.sum() > 100 else slice(None)].reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_RGB2Lab)
    lab = lab.reshape(-1, 3)
    return lab.mean(0), lab.std(0) + 1e-3


def match_chain(src_video: str, ref: str, pre: str = "", work: str | None = None, strength: float = 0.85) -> str:
    """Reinhard Lab mean/std transfer from src -> ref, baked to a 33^3 .cube in the work folder."""
    src = sample_frames(src_video, 8, pre)
    ref_fr = sample_frames(ref, 6) if not ref.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")) \
        else np.stack([grab(ref, 0, 480)])
    ms, ss = _lab_stats(src)
    mr, sr = _lab_stats(ref_fr)
    ratio = np.clip(sr / ss, 0.5, 2.0)
    grid = L.lattice().astype(np.float32)
    lab = cv2.cvtColor(grid.reshape(-1, 1, 3), cv2.COLOR_RGB2Lab).reshape(-1, 3)
    out = (lab - ms) * ratio + mr
    rgb = cv2.cvtColor(out.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_Lab2RGB).reshape(-1, 3)
    rgb = grid + (np.clip(rgb, 0, 1) - grid) * strength
    tag = abs(hash((os.path.abspath(src_video), os.path.abspath(ref), pre, strength))) % 10 ** 8
    p = os.path.join(work or tempfile.gettempdir(), "vs_luts", f"match_{tag}.cube")
    L.write_cube(p, rgb, f"Reinhard match -> {os.path.basename(ref)}")
    return lut_filter(p)


# ---------------------------------------------------------------- scopes + QC
def _still(video: str, t: float, chain: str, out_png: str, width: int = 960) -> None:
    vf = ",".join(x for x in [chain, f"scale={width}:-2"] if x)
    run(["ffmpeg", "-y", "-v", "error", *_ss(t), "-i", video, "-frames:v", "1",
         "-filter_complex", f"[0:v]{vf}[o]", "-map", "[o]", out_png])


def scopes(video_path: str, t: float, out_png: str, chain: str = "") -> str:
    """Frame + luma waveform + RGB parade + vectorscope in one labelled PNG (Pillow labels)."""
    from PIL import Image, ImageDraw
    tmp = tempfile.mkdtemp(prefix="vs_scopes_")
    pre = (chain + ",") if chain else ""
    jobs = {
        "frame": f"{pre}scale=640:-2",
        "waveform": f"{pre}scale=640:-2,waveform=mode=column:filter=lowpass:graticule=green:flags=numbers+dots:scale=digital,scale=640:360",
        "parade": f"{pre}scale=640:-2,format=gbrp,waveform=mode=column:display=parade:components=7:graticule=green:flags=numbers,scale=640:360",
        "vectorscope": f"{pre}scale=640:-2,format=yuv444p,vectorscope=mode=color3:graticule=green:flags=name,scale=360:360",
    }
    ims = {}
    for k, vf in jobs.items():
        p = os.path.join(tmp, f"{k}.png")
        run(["ffmpeg", "-y", "-v", "error", *_ss(t), "-i", video_path, "-frames:v", "1",
             "-filter_complex", f"[0:v]{vf}[o]", "-map", "[o]", p])
        ims[k] = Image.open(p).convert("RGB")
    fh = ims["frame"].height
    sheet = Image.new("RGB", (640 + 640 + 30, max(fh, 360) + 360 + 70), (18, 18, 18))
    pos = {"frame": (10, 30), "waveform": (660, 30), "parade": (10, max(fh, 360) + 60),
           "vectorscope": (660 + 140, max(fh, 360) + 60)}
    d = ImageDraw.Draw(sheet)
    for k, (x, y) in pos.items():
        sheet.paste(ims[k], (x, y))
        d.text((x, y - 16), k.upper(), fill=(230, 230, 230))
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    sheet.save(out_png)
    return out_png


def qc(video_path: str, max_frames: int = 300) -> dict:
    """signalstats over the clip: YMIN/YMAX/BRNG (% out of broadcast range). Flags EBU R103 issues."""
    tmp = tempfile.mkdtemp(prefix="vs_qc_")
    video_path = os.path.abspath(video_path)  # ffmpeg runs with cwd=tmp
    dur = probe(video_path)["duration"] or 1
    step = max(1, int(dur * 25 / max_frames))
    subprocess.run(["ffmpeg", "-v", "error", "-i", video_path, "-vf",
                    f"select=not(mod(n\\,{step})),signalstats=stat=brng,metadata=mode=print:file=qc.txt",
                    "-f", "null", "-"], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    vals: dict[str, list[float]] = {}
    path = os.path.join(tmp, "qc.txt")
    if not os.path.exists(path):
        die(f"signalstats produced no data for {video_path}")
    for line in open(path, encoding="utf-8"):
        if line.startswith("lavfi.signalstats."):
            k, v = line.strip().split("=", 1)
            try:
                vals.setdefault(k.split(".")[-1], []).append(float(v))
            except ValueError:
                pass
    W = probe(video_path).get("width", 1) * probe(video_path).get("height", 1)
    brng = np.array(vals.get("BRNG", [0]))
    brng_pct = brng / W * 100 if brng.max() > 1 else brng * 100  # BRNG is a pixel count on recent builds
    r = {"frames": len(vals.get("YMIN", [])), "ymin": min(vals.get("YMIN", [0])), "ymax": max(vals.get("YMAX", [0])),
         "ylow_avg": float(np.mean(vals.get("YLOW", [0]))), "yhigh_avg": float(np.mean(vals.get("YHIGH", [0]))),
         "satmax": max(vals.get("SATMAX", [0])), "brng_pct_max": float(brng_pct.max()), "brng_pct_avg": float(brng_pct.mean())}
    # EBU R103 judges excursions by how many pixels exceed range (<=1% is tolerated), not by the single
    # extreme pixel: lossy encoders ring a few pixels past the limiter on hard edges.
    issues, notes = [], []
    if r["brng_pct_max"] > 1.0:
        issues.append(f"{r['brng_pct_max']:.2f}% pixels out of broadcast range on worst frame (EBU R103 allows 1%)")
    if r["ymin"] < 5 or r["ymax"] > 246:
        notes.append(f"isolated pixels outside 5-246 (min {r['ymin']:.0f}, max {r['ymax']:.0f}) - typical encoder overshoot")
    r["issues"], r["notes"], r["legal"] = issues, notes, not issues
    return r


# ---------------------------------------------------------------- CLI helpers
def _label_img(im, text):
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    d.rectangle([0, im.height - 18, im.width, im.height], fill=(0, 0, 0))
    d.text((5, im.height - 15), text, fill=(255, 255, 255))
    return im


def looks_sheet(video: str, t: float, out_png: str, correct: bool = False, cols: int = 7, tile_w: int = 320) -> str:
    from PIL import Image
    tmp = tempfile.mkdtemp(prefix="vs_sheet_")
    base = os.path.join(tmp, "base.png")
    pre = correction_chain(analyze(video, 6), {}) if correct else ""
    _still(video, t, pre, base, tile_w)
    tile_h = Image.open(base).height
    tiles = []
    for name in LOOK_NAMES:
        p = os.path.join(tmp, f"{name}.png")
        ch = look_chain(name, 1.0, tile_w, tile_h, work=tmp)
        run(["ffmpeg", "-y", "-v", "error", "-i", base, "-frames:v", "1",
             "-filter_complex", f"[0:v]{ch or 'null'}[o]", "-map", "[o]", p])
        tiles.append(_label_img(Image.open(p).convert("RGB"), name))
    th = tiles[0].height
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * (tile_w + 4) + 4, rows * (th + 4) + 4), (25, 25, 25))
    for i, im in enumerate(tiles):
        sheet.paste(im, (4 + (i % cols) * (tile_w + 4), 4 + (i // cols) * (th + 4)))
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    sheet.save(out_png)
    return out_png


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("analyze"); a1.add_argument("video"); a1.add_argument("--work", default=".")
    a1.add_argument("--samples", type=int, default=12)
    a2 = sub.add_parser("preview"); a2.add_argument("video"); a2.add_argument("--look", default="none")
    a2.add_argument("--intensity", type=float, default=1.0); a2.add_argument("--t", type=float, default=0)
    a2.add_argument("--correct", action="store_true"); a2.add_argument("--color", default="{}", help="plan color JSON")
    a2.add_argument("--finish", default="", help="plan finish JSON (texture)"); a2.add_argument("--out", required=True)
    a3 = sub.add_parser("looks-sheet"); a3.add_argument("video"); a3.add_argument("--t", type=float, default=0)
    a3.add_argument("--correct", action="store_true"); a3.add_argument("--out", required=True)
    a4 = sub.add_parser("scopes"); a4.add_argument("video"); a4.add_argument("--t", type=float, default=0)
    a4.add_argument("--out", required=True)
    a5 = sub.add_parser("qc"); a5.add_argument("video")
    a = ap.parse_args()
    if a.cmd == "analyze":
        s = analyze(a.video, a.samples, a.work)
        print(json.dumps(s, indent=2))
    elif a.cmd == "preview":
        info = probe(a.video)
        W, H = info.get("width", 1920), info.get("height", 1080)
        cfg = json.loads(a.color)
        parts = [correction_chain(analyze(a.video, 6), cfg) if (a.correct or cfg) else "",
                 look_chain(a.look, a.intensity, W, H),
                 texture_chain(json.loads(a.finish), W, H) if a.finish else ""]
        _still(a.video, a.t, ",".join(p for p in parts if p), a.out, min(W, 1920))
        log(f"preview -> {a.out}")
    elif a.cmd == "looks-sheet":
        log(f"looks sheet -> {looks_sheet(a.video, a.t, a.out, a.correct)}")
    elif a.cmd == "scopes":
        log(f"scopes -> {scopes(a.video, a.t, a.out)}")
    elif a.cmd == "qc":
        print(json.dumps(qc(a.video), indent=2))


if __name__ == "__main__":
    main()
