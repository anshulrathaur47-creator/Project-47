""""Peeli Chhatri" (पीली छतरी): reel for "कोई पूछे तुमसे कौन हूँ मैं" (assets/music/ReelAudio-84356.mp3).

For years Ira held her yellow umbrella over her best friend Kabir. Tonight his new girlfriend asks who she
is and he says "nobody special". Her tear falls into a puddle and opens a golden memory (walking under one
umbrella, a pinky promise, a half-true lie on a rooftop). Back at the bus shelter he sits beside her but is
lost in his phone, then leaves. She gives him the umbrella so the two of them stay dry and walks home alone
in the rain, into the lens.

Story and shot list come from a three-designer / judge workflow (see notes.md). New character: Ira, a
chin-length black bob with blunt bangs, a mustard hair clip, indigo denim jacket over a cream high-neck,
silver hoops, a red-and-white friendship thread. Kabir and the girlfriend are faceless silhouettes
(slate / coral rim). Lyrics are static plain lines in two fixed bands.

Usage: python3 make_khas.py [--frames 30,150,...] [--workers 4]
"""
import math
import multiprocessing as mp
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "2026-11-16-remember-19-nov"))
import make_19nov as m  # noqa: E402

clamp, smooth, lerp, ease_out, back_out, track, step, Pen, ik = (m.clamp, m.smooth, m.lerp, m.ease_out, m.back_out,
                                                                m.track, m.step, m.Pen, m.ik)
W, H, FPS = 1080, 1920, 30
AUDIO = os.path.join(HERE, "..", "..", "assets", "music", "ReelAudio-84356.mp3")
OUT = os.path.join(HERE, "khas.mp4")
SILENT = os.path.join(HERE, "_khas_silent.mp4")
DUR = 20.08
K = 2
BEAT0, BEAT = 0.25, 0.441

MUSTARD, MUSTARD_D, MUSTARD_L = (232, 176, 32), (176, 128, 18), (250, 206, 90)
CORAL = (255, 122, 122)
SLATE, SEPIA = (58, 66, 80), (107, 74, 51)
LINE = (14, 14, 24)
SKIN, SKIN_SH = (201, 148, 106), (178, 126, 88)
HAIR = (20, 19, 26)
DENIM, DENIM_SH, DENIM_L = (43, 58, 103), (30, 40, 76), (78, 96, 150)
CREAM = (239, 230, 210)
JEANS = (52, 54, 62)
THREAD_R = (210, 40, 50)
STYLE = "female"          # "male": short hair with a side-swept fringe, bomber jacket over a tee (set by make_khas_male.py)
KIND_MAP, KIND_H = {}, {}  # remap silhouette kinds (e.g. the best friend becomes a girl) and their heights
CUFF = None               # sleeve cuff colour (None = light denim)
ARM_W = (58, 50)          # the friend's arm taking the umbrella in shot 13
FRIEND_CUP = True         # the friend wears headphones (shot 13 shoulder)

# ==============================================================================================
# lyrics: static lines, two fixed bands (lower third for shots 1-13, top for the last shot)
# ==============================================================================================
LINES = [
    (0.24, 2.10, "कोई पूछे तुमसे कौन हूँ मैं"),
    (2.14, 4.20, "तुम कह देना कोई ख़ास नहीं"),
    (5.26, 7.18, "एक दोस्त था पक्का कच्चा सा"),
    (7.30, 9.00, "एक झूठ था आधा सच्चा सा"),
    (10.55, 12.16, "जीवन का एक साथी था"),
    (12.24, 14.20, "जो पास होकर भी पास नहीं"),
    (14.25, 16.10, "कोई पूछे तुमसे कौन हूँ मैं"),
    (16.98, 19.00, "तुम कह देना कोई ख़ास नहीं"),
]
_lcache = {}


def lyric_sprite(text, size=66):
    if text in _lcache:
        return _lcache[text]
    f = m.kfont(size)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    x0, y0, x1, y1 = probe.textbbox((0, 0), text, font=f)
    pad = 28
    img = Image.new("RGBA", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad + 20), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - x0 + 2, pad - y0 + 4), text, font=f, fill=(0, 0, 0, 170), stroke_width=4, stroke_fill=(0, 0, 0, 170))
    out = sh.filter(ImageFilter.GaussianBlur(8))
    ImageDraw.Draw(out).text((pad - x0, pad - y0), text, font=f, fill=(250, 248, 244, 255), stroke_width=3, stroke_fill=(12, 14, 24, 255))
    _lcache[text] = out
    return out


def draw_lyrics(frame, t):
    for a, b, text in LINES:
        if a <= t < b:
            spr = lyric_sprite(text)
            cy = 320 if t >= 16.97 else 1340
            frame.alpha_composite(spr, (int(540 - spr.width / 2), int(cy - spr.height / 2)))


# ==============================================================================================
# Ira's acting
# ==============================================================================================
def saw(t0, t1, period):
    keys, t = [(0, 0)], t0
    while t < t1:
        keys += [(t, 0), (t + period * 0.97, 1), (t + period, 0)]
        t += period
    return keys


T = {
    "walk": [(0, 1), (0.6, 1), (0.75, 0), (5.25, 0), (5.26, 1), (6.15, 1), (6.16, 0), (9.05, 0), (9.06, 1), (10.3, 1),
             (10.42, 0), (16.96, 0), (16.97, 1), (18.4, 1), (18.55, 0), (19.0, 0), (19.05, 1)],
    "speed": [(0, 0), (5.25, 0), (5.26, 1.2), (6.15, 1.2), (6.16, 0), (16.96, 0), (16.97, 1.0), (18.4, 1.0), (18.55, 0),
              (19.0, 0), (19.05, 1.0)],
    "sink": [(0, 0), (7.28, 0), (7.29, 200), (9.04, 200), (9.05, 0), (10.54, 0), (10.55, 220), (14.24, 220), (14.25, 0)],
    "slump": [(0, 0.1), (3.0, 0.1), (3.8, 0.35), (4.2, 0.3), (5.26, 0.0), (7.29, 0.1), (10.55, 0.15), (13.4, 0.15),
              (14.0, 0.5), (14.25, 0.2), (16.97, 0.45)],
    "head_dy": [(0, 0), (3.1, 0), (3.5, 20), (4.2, 20), (5.26, 0), (13.6, 0), (14.0, 14), (14.25, 0), (16.6, 0),
                (16.7, 12), (16.85, 0), (17.94, 0), (18.1, 16), (18.5, 16), (18.65, 0)],
    "tilt": [(0, 0), (5.26, 3), (6.0, -3), (7.29, 0), (10.55, 0), (10.9, 7), (12.0, 7), (12.2, 3), (13.6, 3), (14.0, -3),
             (14.25, 0), (15.21, 0), (15.9, -4), (16.97, -3), (18.5, 2)],
    "shake": [(0, 0), (7.55, 0), (7.6, 0.3), (8.0, 0.3), (8.05, 0), (15.3, 0), (15.4, 0.08), (16.05, 0.08), (16.1, 0),
              (16.97, 0.04)],
    "look": [(0, (0, 0.1)), (0.8, (0, 0.1)), (0.95, (0.9, 0)), (2.14, (0.5, 0)), (3.05, (0.45, 0)), (3.25, (0, 0.9)),
             (5.26, (0.6, -0.2)), (7.29, (1.0, 0)), (7.6, (0.1, 0)), (8.0, (1.0, 0)), (8.2, (1.0, 0.1)), (8.45, (0.1, 0)),
             (8.7, (1.0, 0)), (10.55, (1.0, 0)), (12.2, (1.0, 0)), (13.5, (1.0, 0)), (13.8, (0, 0.85)), (14.25, (0, 0)),
             (15.21, (0, 0.4)), (16.09, (0.4, 0)), (16.97, (0, 0.45)), (17.94, (0, 0.95)), (18.46, (0, 0.1))],
    "lid": [(0, 0), (3.1, 0), (3.4, 0.3), (4.2, 0.3), (5.26, 0), (10.55, 0.15), (11.2, 0.15), (11.3, 1.0), (11.45, 1.0),
            (11.55, 0.15), (12.0, 0.3), (12.2, 0.15), (13.6, 0.15), (13.9, 0.3), (14.25, 0.1), (15.21, 0.2), (15.9, 1.0),
            (16.09, 0.25), (16.55, 0.25), (16.62, 1.0), (16.95, 1.0), (16.97, 0.3), (18.05, 0.3), (18.15, 1.0), (18.5, 1.0),
            (18.6, 0.2)],
    "happy": [(0, 0), (5.25, 0), (5.26, 1), (6.15, 1), (6.16, 0)],
    "brow": [(0, 0.15), (2.9, 0.2), (3.4, 0.85), (5.26, 0.0), (7.29, 0.7), (10.55, 0.5), (12.0, 0.6), (12.2, 0.45), (13.5, 0.45),
             (13.8, 0.95), (14.25, 0.7), (15.21, 0.85), (16.97, 0.95), (18.5, 0.6)],
    "tear": [(0, 0), (3.8, 0), (4.2, 1), (15.2, 0), (15.5, 0), (16.05, 1)],
    "tear_a": [(0, 0), (3.75, 0), (3.85, 1), (4.21, 1), (4.22, 0), (15.4, 0), (15.5, 1), (16.09, 1), (16.1, 0)],
    "cry": [(0, 0), (16.96, 0), (16.97, 1), (18.6, 1), (19.0, 0.8)],
    "blush": [(0, 0.15), (5.26, 0.55), (6.15, 0.55), (6.16, 0.15)],
    "laugh": [(0, 0), (5.26, 1), (6.15, 1), (6.16, 0)],
    "wet": [(0, 0), (16.53, 0), (16.73, 1)],
    "wet_shoulder": [(0, 0), (5.25, 0), (5.26, -1), (6.15, -1), (6.16, 0)],
    "split": [(0, 0), (7.29, 0.25), (8.05, 0.25), (8.15, 1.0), (9.05, 1.0), (9.06, 0)],
}
MOUTH = [(0, "smile"), (2.14, "smile"), (3.1, "smile"), (3.6, "flat"), (5.26, "grin"), (6.16, "flat"), (7.29, "bright"),
         (8.2, "flat"), (8.4, "bright"), (9.05, "flat"), (10.55, "smile"), (12.0, "flat"), (12.2, "flat"), (14.25, "smile"),
         (15.21, "smile"), (16.09, "smile"), (16.97, "crysmile"), (18.46, "smile")]
SIDE_L, SIDE_R = ("hip", -122, -15), ("hip", 122, -15)
UMB_R = ("head", 112, 170)          # umbrella held by the shoulder (wide shots)
UMB_CLOSE = ("head", 160, 430)      # umbrella handle low at the chest (close-ups), arm nearly straight
TABLE_L, TABLE_R = ("hip", -90, -150), ("hip", 90, -150)
LAP_L, LAP_R = ("hip", -80, -60), ("hip", 80, -60)
HAND_L = [(0, SIDE_L), (2.13, SIDE_L), (2.14, ("hip", -100, 0)), (4.21, ("hip", -100, 0)), (4.22, SIDE_L), (5.25, SIDE_L),
          (5.26, ("head", -200, 150)), (6.15, ("head", -200, 150)), (6.16, SIDE_L), (7.29, ("hip", -90, -20)),
          (9.04, ("hip", -90, -20)), (9.05, SIDE_L), (10.55, LAP_L), (14.24, LAP_L), (14.25, SIDE_L), (14.55, ("head", -190, -120)),
          (15.1, ("head", -190, -120)), (15.21, SIDE_L), (16.97, SIDE_L), (17.94, SIDE_L), (18.15, ("head", -24, 250)),
          (18.6, ("head", -24, 250)), (18.9, SIDE_L)]
HAND_R = [(0, UMB_R), (2.13, UMB_R), (2.14, UMB_CLOSE), (4.21, UMB_CLOSE), (4.22, SIDE_R), (5.25, SIDE_R), (5.26, SIDE_R),
          (5.5, ("head", 165, -290)), (5.85, ("head", 165, -290)), (6.1, SIDE_R), (6.16, SIDE_R), (7.29, TABLE_R), (9.04, TABLE_R),
          (9.05, SIDE_R), (10.55, LAP_R), (12.55, LAP_R), (13.1, ("head", 225, 250)), (13.55, ("head", 225, 250)), (13.95, LAP_R),
          (14.24, LAP_R), (14.25, UMB_R), (15.2, UMB_R), (15.21, UMB_CLOSE), (16.08, UMB_CLOSE), (16.09, ("head", 270, 250)),
          (16.53, ("head", 290, 250)), (16.85, SIDE_R), (16.97, SIDE_R)]


def resolve_hand(spec, t, hip, head):
    kind = spec[0]
    if kind == "wave":
        return (head[0] + 160 + 22 * math.sin(t * 10), head[1] - 90)
    ref = hip if kind == "hip" else head
    off = (0, 0)
    if spec == ("head", -190, -120):   # a small awkward wave
        off = (30 * math.sin(t * 11), 0)
    return (ref[0] + spec[1] + off[0], ref[1] + spec[2] + off[1])


def hand_at(keys, t, hip, head):
    if t <= keys[0][0]:
        return resolve_hand(keys[0][1], t, hip, head)
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            f = smooth((t - t0) / (t1 - t0)) if t1 > t0 else 1
            pa, pb = resolve_hand(a, t, hip, head), resolve_hand(b, t, hip, head)
            return (lerp(pa[0], pb[0], f), lerp(pa[1], pb[1], f))
    return resolve_hand(keys[-1][1], t, hip, head)


def params(t):
    p = {k: track(v, t) for k, v in T.items()}
    p["mouth"] = step(MOUTH, t)
    if p["lid"] < 0.9 and p["happy"] < 0.5 and (t + 0.3) % 3.3 < 0.1:
        p["lid"] = 1.0
    return p


# ==============================================================================================
# Ira: head (bob with blunt bangs) and body (denim jacket) on the 19 Nov rig's proportions
# ==============================================================================================
HEAD_W, HEAD_H, PIVOT = 360, 500, (180, 430)


def draw_head(t, p):
    img = Image.new("RGBA", (HEAD_W * K, HEAD_H * K), (0, 0, 0, 0))
    pen = Pen(img, 0, 0, K)
    cx, cy = 180, 310
    wet = p["wet"]
    hair = tuple(int(c * (1 - 0.15 * wet)) for c in HAIR)
    sway = math.sin(t * 2.1) * 2
    if STYLE == "male":   # short hair at the back, ears showing
        back = [(cx - 150, cy + 30), (cx - 162, cy - 30)]
        back += [(cx + 172 * math.cos(math.radians(a)), cy - 34 + 170 * math.sin(math.radians(a))) for a in range(190, 351, 6)]
        back += [(cx + 162, cy - 30), (cx + 150, cy + 30)]
        pen.poly(back, hair, LINE, 3)
        for sx in (-1, 1):
            pen.ellipse(cx + sx * 118 - 15, cy - 5, cx + sx * 118 + 15, cy + 48, SKIN, LINE, 2.5)
    else:   # bob, back part (behind the face)
        back = [(cx - 170, cy + 150), (cx - 178, cy + 40)]
        back += [(cx + 182 * math.cos(math.radians(a)), cy - 30 + 178 * math.sin(math.radians(a))) for a in range(185, 356, 6)]
        back += [(cx + 178, cy + 40), (cx + 170, cy + 150)]
        pen.poly(back, hair, LINE, 3)
    # face
    pen.poly([(cx - 116, cy + 10), (cx - 100, cy + 85), (cx - 45, cy + 128), (cx, cy + 138), (cx + 45, cy + 128),
              (cx + 100, cy + 85), (cx + 116, cy + 10)], SKIN, LINE, 3)
    pen.ellipse(cx - 118, cy - 130, cx + 118, cy + 100, SKIN)
    pen.arc_line(cx, cy - 15, 118, 115, 180, 360, LINE, 3)
    pen.poly([(cx - 30, cy + 132), (cx + 30, cy + 132), (cx, cy + 141)], SKIN_SH)
    if p["blush"] > 0.01:
        bl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bp = Pen(bl, 0, 0, K)
        for sx in (-1, 1):
            bp.ellipse(cx + sx * 66 - 26, cy + 50, cx + sx * 66 + 26, cy + 70, (240, 110, 120, int(150 * p["blush"])))
        img.alpha_composite(bl.filter(ImageFilter.GaussianBlur(5 * K)))
    # eyes
    lid, happy, brow = p["lid"], p["happy"], p["brow"]
    lx, ly = p["look"]
    brows = []
    for sx in (-1, 1):
        ex, ey = cx + sx * 52, cy + 12
        rx, ry = 31, 39
        if happy > 0.5:
            pen.arc_line(ex, ey + 14, 26, 22, 200, 340, LINE, 7)
        elif lid > 0.9:
            pen.arc_line(ex, ey + 4, 27, 12, 20, 160, LINE, 6)
            pen.line([(ex + sx * 26, ey + 6), (ex + sx * 36, ey)], LINE, 4)
        else:
            pen.ellipse(ex - rx, ey - ry, ex + rx, ey + ry, (255, 255, 255))
            ix, iy = ex + lx * 18, ey + ly * 15
            il = Image.new("RGBA", img.size, (0, 0, 0, 0))   # iris on its own layer, clipped to the eye white
            ip = Pen(il, 0, 0, K)
            ip.ellipse(ix - 24, iy - 31, ix + 24, iy + 31, (52, 30, 22))
            ip.ellipse(ix - 19, iy - 12, ix + 19, iy + 28, (106, 64, 40))
            ip.ellipse(ix - 11, iy - 15, ix + 11, iy + 13, (14, 10, 10))
            ip.circle(ix - 9, iy - 13, 8, (255, 255, 255))
            ip.circle(ix + 9, iy + 12, 3.5, (255, 255, 255))
            if p["tear_a"] > 0.3 or p["cry"] > 0.3:
                ip.ellipse(ix - 18, iy + 16, ix + 18, iy + 24, (190, 220, 255))
            em = Image.new("L", img.size, 0)
            ImageDraw.Draw(em).ellipse([(ex - rx) * K, (ey - ry) * K, (ex + rx) * K, (ey + ry) * K], fill=255)
            il.putalpha(Image.fromarray(np.minimum(np.asarray(il.getchannel("A")), np.asarray(em))))
            img.alpha_composite(il)
            top = ey - ry - 4
            edge = top + lid * 2 * ry
            slant = 9 * max(brow, 0) * (1 if lid > 0.05 else 0.5)
            outer_y, inner_y = edge + slant, edge - slant * 0.4
            o_x, i_x = ex + sx * (rx + 6), ex - sx * (rx + 6)
            pen.poly([(o_x, top - 30), (i_x, top - 30), (i_x, inner_y), (o_x, outer_y)], SKIN)
            tail = (o_x + sx * 8, outer_y + 4) if brow > 0.3 else (o_x + sx * 11, outer_y - 8)
            pen.line([(i_x + sx * 4, inner_y + 2), (ex, (inner_y + outer_y) / 2 - 2), (o_x, outer_y + 1), tail], LINE, 7)
            pen.arc_line(ex, ey + 2, rx - 3, ry - 2, 50, 130, LINE, 2.5)
            if STYLE != "male":
                pen.line([(ex + sx * 18, ey + 36), (ex + sx * 26, ey + 32)], LINE, 2)     # lower lash
        by = cy - 48
        brows.append(((cx + sx * 22, by - 20 * brow + 4 * min(brow, 0) * -1), (cx + sx * 52, by - 8 - 3 * brow),
                      (cx + sx * 84, by + 6 * brow - 4)))
    if STYLE != "male":
        pen.circle(cx - 74, cy + 54, 3.2, (60, 36, 30))       # beauty mark under her right eye
    pen.line([(cx + 2, cy + 52), (cx - 3, cy + 60)], SKIN_SH, 4)
    # mouth
    mth = p["mouth"]
    mx, my = cx, cy + 90
    red = (130, 36, 50)
    if mth == "frown":
        pen.arc_line(mx, my + 12, 18, 9, 200, 340, LINE, 4)
    elif mth == "flat":
        pen.line([(mx - 13, my + 2), (mx + 13, my + 2)], LINE, 4)
    elif mth == "smile":
        pen.arc_line(mx, my - 6, 20, 10, 20, 160, LINE, 4)
    elif mth == "bright":   # a too-bright smile
        pen.poly([(mx - 28, my - 4)] + [(mx + 28 * math.cos(math.radians(a)), my - 4 + 16 * math.sin(math.radians(a))) for a in range(0, 181, 15)],
                 red, LINE, 3)
        pen.poly([(mx - 24, my - 2), (mx + 24, my - 2), (mx + 20, my + 4), (mx - 20, my + 4)], (255, 255, 255))
    elif mth == "grin":
        oh = 24 + 6 * math.sin(t * 20) * p["laugh"]
        pen.poly([(mx - 30, my - 6)] + [(mx + 30 * math.cos(math.radians(a)), my - 6 + oh * math.sin(math.radians(a))) for a in range(0, 181, 15)],
                 red, LINE, 3)
        pen.poly([(mx - 26, my - 4), (mx + 26, my - 4), (mx + 22, my + 3), (mx - 22, my + 3)], (255, 255, 255))
        pen.ellipse(mx - 13, my + oh - 17, mx + 13, my + oh - 4, (240, 110, 120))
    elif mth == "crysmile":   # wobbly mouth that still curves up
        wob = math.sin(t * 20) * 2.5
        pts = [(mx + x, my + 4 + 8 * (1 - (x / 22) ** 2) * 0.6 + wob * math.sin(x * 0.4)) for x in range(-22, 23, 4)]
        pts += [(mx + x, my + 12 + 4 * (1 - (x / 22) ** 2)) for x in range(22, -23, -4)]
        pen.poly(pts, red, LINE, 3)
    # single tear on her right cheek (screen left)
    if p["tear_a"] > 0.01:
        a = int(235 * p["tear_a"])
        tx, ty = cx - 70 - 6 * p["tear"], cy + 40 + 90 * p["tear"]
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        tp = Pen(lay, 0, 0, K)
        tp.line([(cx - 68, cy + 42), (tx, ty)], (170, 210, 255, a // 2), 4)
        tp.poly([(tx, ty - 18), (tx - 9, ty), (tx + 9, ty)], (160, 205, 255, a))
        tp.circle(tx, ty + 2, 9, (160, 205, 255, a))
        tp.circle(tx - 3, ty - 1, 3, (255, 255, 255, a))
        img.alpha_composite(lay)
    if p["cry"] > 0.01:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        lp = Pen(lay, 0, 0, K)
        a = int(200 * p["cry"])
        for sx in (-1, 1):
            x0, y0 = cx + sx * 56, cy + 44
            lp.line([(x0 + sx * 6 * (k / 6) + 2 * math.sin(t * 6 + k + sx), y0 + 13 * k) for k in range(7)], (170, 215, 255, a // 2), 7)
            u = (t * 0.8 + (0.4 if sx > 0 else 0)) % 1
            tx, ty = x0 + sx * 6 * u, y0 + 80 * u
            lp.poly([(tx, ty - 15), (tx - 7, ty), (tx + 7, ty)], (165, 210, 255, a))
            lp.circle(tx, ty + 2, 7, (165, 210, 255, a))
        img.alpha_composite(lay)
    if STYLE == "male":   # side-swept fringe, short sideburns
        fr = [(cx - 156, cy + 20), (cx - 166, cy - 50)]
        fr += [(cx + 170 * math.cos(math.radians(a)), cy - 40 + 160 * math.sin(math.radians(a))) for a in range(195, 346, 8)]
        fr += [(cx + 160, cy - 60), (cx + 150, cy + 10), (cx + 128, cy - 30)]
        for x, y in ((104, -34), (84, -66), (58, -32), (30, -70), (2, -38), (-28, -80), (-56, -50), (-86, -92), (-112, -58), (-134, -96)):
            fr.append((cx + x, cy + y + (sway * 0.5 if y > -50 else 0)))
        pen.poly(fr, hair, LINE, 3)
        pen.arc_line(cx - 20, cy - 92, 100, 50, 200, 320, (86, 72, 66) if wet < 0.5 else (66, 56, 52), 8)
        for sx in (-1, 1):
            pen.poly([(cx + sx * 110, cy - 34), (cx + sx * 128, cy - 34), (cx + sx * 124, cy + 30), (cx + sx * 114, cy + 26)], hair, LINE, 2)
    else:
        # blunt bangs over the forehead
        bang = [(cx - 160, cy - 30)]
        bang += [(cx + 168 * math.cos(math.radians(a)), cy - 36 + 166 * math.sin(math.radians(a))) for a in range(190, 351, 8)]
        bang += [(cx + 160, cy - 30), (cx + 120, cy - 36)]
        for k in range(9):   # slightly uneven blunt edge
            x = cx + 120 - k * 30
            bang.append((x, cy - 34 + (6 if k % 2 else 0) + sway * 0.5))
        bang += [(cx - 130, cy - 36)]
        pen.poly(bang, hair, LINE, 3)
        pen.poly([(cx - 96, cy - 120), (cx - 20, cy - 142), (cx + 60, cy - 138), (cx + 100, cy - 116), (cx + 60, cy - 124),
                  (cx - 20, cy - 128)], (70, 70, 96) if wet < 0.5 else (52, 52, 70))
        # face-framing locks and bob sides in front of the cheeks
        for sx in (-1, 1):
            lock = [(cx + sx * 116, cy - 40), (cx + sx * 142, cy - 30), (cx + sx * 150, cy + 60), (cx + sx * 140, cy + 150),
                    (cx + sx * 104, cy + 156), (cx + sx * 110, cy + 80), (cx + sx * 108, cy - 10)]
            pen.poly(lock, hair, LINE, 3)
            pen.line([(cx + sx * 126, cy - 10), (cx + sx * 128, cy + 30), (cx + sx * 124, cy + 60)], (60, 60, 82), 3)
            pen.circle(cx + sx * 116, cy + 112, 11, None, (210, 214, 224), 3)   # silver hoop peeking out
        pen.poly([(cx + 70, cy - 98), (cx + 116, cy - 82), (cx + 112, cy - 70), (cx + 66, cy - 86)], MUSTARD, LINE, 2)   # clip
    for inner, mid, outer in brows:   # brows sit on top of the hair (anime style)
        pen.line([inner, mid, outer], (60, 52, 62), 13 if STYLE == "male" else 12)
        pen.line([inner, mid, outer], (122, 90, 76), 9 if STYLE == "male" else 8)
    if wet > 0.3:   # stuck strands and rain on her face
        for k, x0 in enumerate((-60, 10, 70)):
            pen.line([(cx + x0, cy - 36), (cx + x0 + 8, cy + 6 + k * 10)], hair, 4)
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        lp = Pen(lay, 0, 0, K)
        for k in range(6):
            x = cx - 90 + k * 36
            y = cy - 10 + ((t * 300 + k * 47) % 140)
            lp.line([(x, y), (x - 2, y + 18)], (190, 215, 255, int(150 * wet)), 2)
        img.alpha_composite(lay)
    return img


def draw_ira(t, p=None):
    """Returns (supersampled sprite, world origin, head centre, hands{'L','R'}, world geometry dict)."""
    p = p or params(t)
    walk = p["walk"]
    phase = math.pi * (t - BEAT0) / BEAT
    hx = 540 + math.sin(phase) * 5 * walk
    bob = 9 * walk * abs(math.sin(phase))
    hip_y = 1250 - bob + p["sink"]
    tilt = p["tilt"] + p["shake"] * math.sin(t * 17) * 9
    breathe = math.sin(t * 2.2) * 3
    laugh = p["laugh"] * abs(math.sin(t * 11)) * 8
    sy = hip_y - 330 + p["slump"] * 34 + breathe + laugh * 0.5
    neck = (hx, sy - 36 + p["head_dy"] - laugh)
    head_c = (neck[0], neck[1] - 120)
    rx0, ry0 = 120, 150
    img = Image.new("RGBA", (840 * K, 1540 * K), (0, 0, 0, 0))
    pen = Pen(img, rx0, ry0, K)
    for s in (-1, 1):   # legs
        lift = max(0.0, math.sin(phase + (0 if s < 0 else math.pi))) * walk
        hipj = (hx + s * 48, hip_y)
        foot = (hx + s * 62, 1628 - lift * 58)
        knee = (hx + s * (58 + 14 * lift), (hipj[1] + foot[1]) / 2 - lift * 42)
        ankle = (foot[0], foot[1] - 6)
        left, right = [], []
        for (px_, py_), hw in ((hipj, 37), (knee, 32), (ankle, 27)):
            left.append((px_ - hw, py_))
            right.append((px_ + hw, py_))
        pen.poly(left + right[::-1], JEANS, LINE, 3)
        if lift > 0.2:
            pen.line([(knee[0] - 14, knee[1] + 4), (knee[0] + 10, knee[1] + 10)], (24, 24, 30), 3)
        pen.poly([(foot[0] - 44, foot[1] + 4), (foot[0] - 30, foot[1] - 16), (foot[0] + 30, foot[1] - 16), (foot[0] + 48, foot[1] + 6),
                  (foot[0] + 46, foot[1] + 22), (foot[0] - 44, foot[1] + 22)], (242, 242, 246), LINE, 3)
        pen.line([(foot[0] - 42, foot[1] + 16), (foot[0] + 44, foot[1] + 16)], (170, 170, 180), 5)
    if STYLE == "male":   # bomber jacket over a white tee
        pen.poly([(hx - 24, sy - 50), (hx + 24, sy - 50), (hx + 24, sy + 10), (hx - 24, sy + 10)], SKIN_SH, LINE, 2)
        body = [(hx - 122, sy + 6), (hx + 122, sy + 6), (hx + 108, hip_y + 22), (hx - 108, hip_y + 22)]
        pen.poly(body, DENIM, LINE, 3)
        for s_ in (-1, 1):
            pen.circle(hx + s_ * 104, sy + 34, 38, DENIM)
        pen.poly([(hx - 40, sy + 4), (hx + 40, sy + 4), (hx + 34, hip_y + 16), (hx - 34, hip_y + 16)], CREAM, LINE, 2)
        pen.arc_line(hx, sy + 4, 26, 18, 0, 180, (196, 196, 192), 4)
        for s_ in (-1, 1):
            pen.line([(hx + s_ * 40, sy + 6), (hx + s_ * 34, hip_y + 16)], (150, 152, 140), 4)    # open zip
            pen.poly([(hx + s_ * 30, sy - 10), (hx + s_ * 74, sy + 2), (hx + s_ * 46, sy + 30), (hx + s_ * 34, sy + 10)], DENIM_SH, LINE, 2)
        pen.poly([(hx - 108, hip_y), (hx + 108, hip_y), (hx + 108, hip_y + 24), (hx - 108, hip_y + 24)], DENIM_SH, LINE, 2)
        for k in range(-5, 6):
            pen.line([(hx + k * 18, hip_y + 4), (hx + k * 18, hip_y + 20)], (52, 60, 38), 2)
    else:
        # torso: denim jacket over a cream high-neck
        pen.poly([(hx - 26, sy - 50), (hx + 26, sy - 50), (hx + 26, sy + 10), (hx - 26, sy + 10)], CREAM, LINE, 2)
        body = [(hx - 118, sy + 6), (hx + 118, sy + 6), (hx + 104, hip_y + 22), (hx - 104, hip_y + 22)]
        pen.poly(body, DENIM, LINE, 3)
        for s in (-1, 1):
            pen.circle(hx + s * 100, sy + 34, 36, DENIM)
        pen.poly([(hx - 36, sy + 4), (hx + 36, sy + 4), (hx + 30, hip_y + 20), (hx - 30, hip_y + 20)], CREAM, LINE, 2)
        for s in (-1, 1):
            pen.poly([(hx + s * 36, sy + 4), (hx + s * 76, sy + 10), (hx + s * 44, sy + 120), (hx + s * 32, sy + 40)], DENIM_SH, LINE, 2)
            pen.poly([(hx + s * 52, sy + 70), (hx + s * 92, sy + 70), (hx + s * 92, sy + 110), (hx + s * 52, sy + 110)], DENIM_SH, LINE, 2)
            pen.line([(hx + s * 52, sy + 82), (hx + s * 92, sy + 82)], DENIM_L, 3)
        pen.line([(hx - 104, hip_y + 8), (hx + 104, hip_y + 8)], DENIM_L, 4)
        pen.line([(hx - 104, sy + 30), (hx + 92, hip_y - 10)], (24, 24, 28), 9)     # crossbody strap
    if abs(p["wet_shoulder"]) > 0.01:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        side = -1 if p["wet_shoulder"] < 0 else 1
        Pen(lay, rx0, ry0, K).ellipse(hx + side * 90 - 50, sy - 10, hx + side * 90 + 50, sy + 90, (10, 14, 30, 110))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6 * K)))
    hands = {}
    arms = []
    for s, keys in ((-1, HAND_L), (1, HAND_R)):
        sh = (hx + s * 104, sy + 30)
        target = hand_at(keys, t, (hx, hip_y), head_c)
        elbow, hand = ik(sh, target, 150, 148, 1 if s < 0 else -1)
        hands["L" if s < 0 else "R"] = hand
        arms.append((s, sh, elbow, hand))
    front = []
    for s, sh, elbow, hand in arms:
        at_face = abs(hand[0] - head_c[0]) < 110 and -60 < hand[1] - head_c[1] < 170
        if at_face:
            front.append((s, sh, elbow, hand))
            continue
        draw_arm(pen, s, sh, elbow, hand)
    head = draw_head(t, p)
    head = head.rotate(p["tilt"] if False else tilt, resample=Image.BICUBIC, center=(PIVOT[0] * K, PIVOT[1] * K))
    px = int((neck[0] - rx0) * K - PIVOT[0] * K)
    py = int((neck[1] - ry0) * K - PIVOT[1] * K)
    img.alpha_composite(head, (max(px, 0), max(py, 0)), (max(-px, 0), max(-py, 0)))
    for s, sh, elbow, hand in front:
        draw_arm(pen, s, sh, elbow, hand)
    return img, (rx0, ry0), head_c, hands, {"hip": (hx, hip_y), "sy": sy}


def draw_arm(pen, s, sh, elbow, hand):
    pen.limb(sh, elbow, 54, DENIM)
    pen.limb(elbow, hand, 50, DENIM)
    cuff = (lerp(elbow[0], hand[0], 0.78), lerp(elbow[1], hand[1], 0.78))
    pen.limb(cuff, (lerp(elbow[0], hand[0], 0.86), lerp(elbow[1], hand[1], 0.86)), 56, CUFF or DENIM_L)
    if s < 0:   # friendship thread on her right wrist (screen left)
        w = (lerp(elbow[0], hand[0], 0.9), lerp(elbow[1], hand[1], 0.9))
        pen.circle(*w, 24, None, THREAD_R, 5)
        pen.circle(*w, 20, None, (250, 250, 250), 2)
    ang = math.atan2(hand[1] - elbow[1], hand[0] - elbow[0])
    ca, sa = math.cos(ang), math.sin(ang)
    mit = [(hand[0] + ca * (u * 30) - sa * (v * 22), hand[1] + sa * (u * 30) + ca * (v * 22))
           for u, v in ((-0.8, -1), (0.6, -1.05), (1.15, -0.4), (1.15, 0.5), (0.6, 1.05), (-0.8, 1))]
    pen.poly(mit, SKIN, LINE, 3)
    th = (hand[0] + ca * 2 - sa * (-s * 26), hand[1] + sa * 2 + ca * (-s * 26))
    pen.circle(th[0], th[1], 10, SKIN, LINE, 2.5)


# ---------------------------------------------------------------------------------- placement
class Placed:
    """Ira drawn at screen position: head centre at (hx, hy) and scale s (world px -> screen px)."""

    def __init__(self, t, hx, hy, s, p=None):
        self.p = p or params(t)
        self.img, self.origin, self.head, self.hands, self.geo = draw_ira(t, self.p)
        self.s, self.ax, self.ay = s, hx, hy

    def ws(self, x, y):
        return (self.ax + (x - self.head[0]) * self.s, self.ay + (y - self.head[1]) * self.s)

    def layer(self):
        a = K / self.s
        c = K * (self.head[0] - self.origin[0]) - a * self.ax
        f = K * (self.head[1] - self.origin[1]) - a * self.ay
        return self.img.transform((W, H), Image.AFFINE, (a, 0, c, 0, a, f), resample=Image.BILINEAR)

    def hand(self, k):
        return self.ws(*self.hands[k])


def place_by_feet(t, x, feet_y, s):
    p = params(t)
    img, origin, head, hands, geo = draw_ira(t, p)
    hy = feet_y - (1640 - head[1]) * s
    return Placed(t, x, hy, s, p)


# ==============================================================================================
# props and other people
# ==============================================================================================
def umbrella_open(d, top, handle, R, open_amt=1.0, col=MUSTARD, a=255, shaft_behind=None):
    """Open umbrella seen from the side/front: canopy top at `top`, handle at `handle`."""
    tx, ty = top
    hx, hy = handle
    ang = math.atan2(hx - tx, hy - ty)   # axis direction (canopy faces away from handle)
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v):   # u across, v along the axis (positive towards the handle)
        return (tx + u * ca + v * sa, ty - u * sa + v * ca)
    Rw = R * (0.12 + 0.88 * open_amt)
    depth = R * 0.42 * (0.6 + 0.4 * open_amt)
    dome = [P(Rw * math.cos(math.radians(a_)), -depth * math.sin(math.radians(a_)) * 0.25 + depth * (1 - math.sin(math.radians(a_))))
            for a_ in range(0, 181, 6)]
    ribs = 8
    edge = []
    for k in range(ribs + 1):
        u = -Rw + 2 * Rw * k / ribs
        edge.append(P(u, depth))
        if k < ribs:
            um = u + Rw / ribs
            edge.append(P(um, depth - R * 0.05))
    canopy = [P(-Rw, depth)] + dome[::-1][1:-1] + [P(Rw, depth)] + edge[::-1]
    if shaft_behind is not False:
        d.line([P(0, -R * 0.12), (hx, hy)], fill=(120, 90, 60, a), width=max(2, int(R * 0.035)))
    d.polygon(canopy, fill=col + (a,), outline=LINE + (a,))
    for k in range(1, ribs):
        u = -Rw + 2 * Rw * k / ribs
        d.line([P(0, 0), P(u, depth)], fill=MUSTARD_D + (a,), width=max(1, int(R * 0.012)))
    d.line([P(-Rw * 0.6, depth * 0.35), P(Rw * 0.4, depth * 0.12)], fill=MUSTARD_L + (int(a * 0.7),), width=max(2, int(R * 0.03)))
    d.line([P(0, -R * 0.12), P(0, -R * 0.2)], fill=(90, 70, 50, a), width=max(2, int(R * 0.03)))
    r = R * 0.07   # J handle
    d.arc([hx - r, hy - r * 0.2, hx + r, hy + r * 1.8], 0, 180, fill=(120, 80, 46, a), width=max(2, int(R * 0.035)))


def umbrella_closed(d, tip, top, s, a=255):
    tx, ty = tip
    ux, uy = top
    ang = math.atan2(ux - tx, uy - ty)
    ca, sa = math.cos(ang), math.sin(ang)
    L = math.hypot(ux - tx, uy - ty)

    def P(u, v):
        return (tx + u * ca + v * sa, ty - u * sa + v * ca)
    d.line([P(0, 0), P(0, L)], fill=(120, 90, 60, a), width=max(2, int(6 * s)))
    d.polygon([P(0, L * 0.08), P(-26 * s, L * 0.55), P(-12 * s, L * 0.86), P(12 * s, L * 0.86), P(22 * s, L * 0.5)], fill=MUSTARD + (a,), outline=LINE + (a,))
    d.line([P(-8 * s, L * 0.3), P(-4 * s, L * 0.8)], fill=MUSTARD_D + (a,), width=max(1, int(3 * s)))
    d.line([P(-16 * s, L * 0.6), P(16 * s, L * 0.6)], fill=(110, 80, 20, a), width=max(2, int(6 * s)))   # strap
    hx, hy = P(0, L)
    d.arc([hx - 14 * s, hy - 4 * s, hx + 14 * s, hy + 24 * s], 0, 180, fill=(120, 80, 46, a), width=max(2, int(6 * s)))


def canopy_under(d, cx, cy, R, a=255, col=MUSTARD):
    """The underside of the canopy over the camera in close-ups."""
    pts = []
    for k in range(17):
        ang = math.radians(180 + k * 180 / 16)
        r = R * (1.0 if k % 2 == 0 else 0.93)
        pts.append((cx + r * math.cos(ang), cy - r * 0.45 * math.sin(ang) * -1 + 0))
    shade = tuple(int(c * 0.78) for c in col)
    d.polygon([(cx - R * 1.4, -50), (cx + R * 1.4, -50)] + [(cx + R * math.cos(math.radians(a_)), cy + R * 0.42 * math.sin(math.radians(a_)))
                                                           for a_ in range(0, 181, 10)][::-1], fill=shade + (a,))
    for k in range(9):
        ang = math.radians(k * 180 / 8)
        d.line([(cx, cy - R * 0.6), (cx + R * math.cos(ang), cy + R * 0.42 * math.sin(ang))], fill=MUSTARD_D + (a,), width=6)
    edge = [(cx + R * math.cos(math.radians(a_)), cy + R * 0.42 * math.sin(math.radians(a_))) for a_ in range(0, 181, 5)]
    d.line(edge, fill=MUSTARD_L + (a,), width=10)


def person(d, x, feet, h, kind, t, pose="stand", col=SLATE, rim=None, a=255, walk=0.0, ph=0.0, cut_y=None, arm_t=1.0):
    """A faceless silhouette. kind 'kabir' (tall, messy hair, headphones, backpack), 'gf' (ponytail, sling bag),
    'girl' (long hair) or 'boy' (short hair, cap)."""
    kind = KIND_MAP.get(kind, kind)
    h = h * KIND_H.get(kind, 1.0)
    def draw(dd, ox, colr):
        bob = abs(math.sin(t * 7 + ph)) * 0.012 * h * walk
        top = feet - h - bob
        hr = 0.075 * h
        hcx, hcy = x + ox, top + hr + 0.01 * h
        sh_y = top + 0.2 * h
        sw = {"kabir": 0.15, "boy": 0.16}.get(kind, 0.13) * h
        hip_y = top + 0.55 * h
        cola = colr + (a,)
        if pose == "shrug" or (pose == "shrug_t" and 0 < arm_t < 1):
            sh_y -= 0.03 * h * (1 if pose == "shrug" else math.sin(math.pi * arm_t))
        dd.polygon([(hcx - sw, sh_y), (hcx + sw, sh_y), (hcx + sw * 0.78, hip_y), (hcx - sw * 0.78, hip_y)], fill=cola)
        dd.ellipse([hcx - sw - 0.03 * h, sh_y - 0.02 * h, hcx - sw + 0.05 * h, sh_y + 0.06 * h], fill=cola)
        dd.ellipse([hcx + sw - 0.05 * h, sh_y - 0.02 * h, hcx + sw + 0.03 * h, sh_y + 0.06 * h], fill=cola)
        dd.rectangle([hcx - 0.03 * h, hcy + hr * 0.8, hcx + 0.03 * h, sh_y + 2], fill=cola)
        dd.ellipse([hcx - hr, hcy - hr, hcx + hr, hcy + hr * 1.05], fill=cola)
        if kind == "girl":   # long hair falling to the shoulders
            dd.polygon([(hcx - hr * 1.15, hcy - hr * 0.2), (hcx + hr * 1.15, hcy - hr * 0.2), (hcx + hr * 1.35, sh_y + 0.07 * h),
                        (hcx - hr * 1.35, sh_y + 0.07 * h)], fill=cola)
            dd.ellipse([hcx - hr * 1.12, hcy - hr * 1.15, hcx + hr * 1.12, hcy + hr * 0.6], fill=cola)
        elif kind == "boy":   # cap with a brim
            dd.chord([hcx - hr * 1.08, hcy - hr * 1.2, hcx + hr * 1.08, hcy + hr * 0.5], 180, 360, fill=cola)
            dd.polygon([(hcx + hr * 0.4, hcy - hr * 0.45), (hcx + hr * 1.7, hcy - hr * 0.35), (hcx + hr * 1.6, hcy - hr * 0.2),
                        (hcx + hr * 0.4, hcy - hr * 0.25)], fill=cola)
        elif kind == "kabir":
            cap = []
            for k in range(13):   # messy hair cap
                ang = math.radians(195 + k * 150 / 12)
                rr_ = hr * (1.22 if k % 2 else 1.05)
                cap.append((hcx + rr_ * math.cos(ang), hcy - hr * 0.1 + rr_ * math.sin(ang)))
            dd.polygon(cap + [(hcx + hr * 0.95, hcy), (hcx - hr * 0.95, hcy)], fill=cola)
            dd.arc([hcx - hr * 1.1, hcy + hr * 0.6, hcx + hr * 1.1, hcy + hr * 1.9], 200, 340, fill=cola, width=max(2, int(0.02 * h)))
            for s_ in (-1, 1):
                dd.ellipse([hcx + s_ * hr * 0.95 - hr * 0.3, hcy + hr * 0.95, hcx + s_ * hr * 0.95 + hr * 0.3, hcy + hr * 1.55], fill=cola)
            dd.rectangle([hcx + sw * 0.7, sh_y + 0.02 * h, hcx + sw * 1.15, sh_y + 0.26 * h], fill=cola)   # backpack bulge
        elif kind == "gf":
            dd.ellipse([hcx - hr * 0.5, hcy - hr * 1.5, hcx + hr * 0.5, hcy - hr * 0.6], fill=cola)          # high ponytail
            dd.polygon([(hcx + hr * 0.2, hcy - hr * 1.2), (hcx + hr * 1.3, hcy - hr * 0.4), (hcx + hr * 1.0, hcy + hr * 0.6), (hcx + hr * 0.4, hcy - hr * 0.4)], fill=cola)
            dd.ellipse([hcx + sw * 0.6, hip_y - 0.05 * h, hcx + sw * 1.15, hip_y + 0.03 * h], fill=cola)    # sling bag
        for s_ in (-1, 1):   # legs: tapered trousers and shoes
            sw_ = math.sin(t * 7 + ph + (0 if s_ < 0 else math.pi)) * walk
            ax_ = hcx + s_ * 0.055 * h + sw_ * 0.025 * h
            dd.polygon([(hcx + s_ * 0.005 * h, hip_y - 0.01 * h), (hcx + s_ * 0.11 * h, hip_y - 0.01 * h),
                        (ax_ + s_ * 0.03 * h, feet - 0.03 * h), (ax_ - s_ * 0.025 * h, feet - 0.03 * h)], fill=cola)
            dd.ellipse([ax_ - 0.045 * h, feet - 0.035 * h, ax_ + 0.05 * h, feet + 0.004 * h], fill=cola)
        aw = max(2, int(0.05 * h))
        for s_ in (-1, 1):   # arms
            shx = hcx + s_ * (sw + 0.01 * h)
            if pose in ("point_l", "point_r") and ((pose == "point_l" and s_ < 0) or (pose == "point_r" and s_ > 0)):
                ex = shx + s_ * 0.26 * h * arm_t
                ey = lerp(sh_y + 0.3 * h, sh_y + 0.10 * h, arm_t)
                dd.line([(shx, sh_y + 0.03 * h), (ex, ey)], fill=cola, width=aw)
                dd.ellipse([ex - aw * 0.55, ey - aw * 0.55, ex + aw * 0.55, ey + aw * 0.55], fill=cola)
                dd.polygon([(ex, ey - aw * 0.25), (ex + s_ * 0.07 * h, ey + 0.02 * h), (ex, ey + aw * 0.25)], fill=cola)
            elif pose == "phone":
                px, py = hcx + s_ * 0.03 * h, sh_y + 0.16 * h
                dd.line([(shx, sh_y + 0.03 * h), (hcx + s_ * 0.12 * h, sh_y + 0.27 * h), (px, py)], fill=cola, width=aw)
            elif pose == "reach_r" and s_ > 0:
                dd.line([(shx, sh_y + 0.03 * h), (shx + 0.3 * h * arm_t, sh_y + 0.1 * h)], fill=cola, width=aw)
            elif pose == "palm_l" and s_ < 0:
                ex, ey = shx - 0.01 * h, sh_y + 0.25 * h - 0.4 * h * arm_t
                dd.line([(shx, sh_y + 0.03 * h), (ex, ey)], fill=cola, width=aw)
                dd.ellipse([ex - 0.03 * h, ey - 0.035 * h, ex + 0.03 * h, ey + 0.02 * h], fill=cola)
            else:
                sw_ = math.sin(t * 7 + ph + (math.pi if s_ < 0 else 0)) * walk
                ex, ey = shx + s_ * 0.025 * h + sw_ * 0.04 * h, hip_y + 0.03 * h
                dd.line([(shx, sh_y + 0.03 * h), (ex, ey)], fill=cola, width=aw)
                dd.ellipse([ex - aw * 0.55, ey - aw * 0.5, ex + aw * 0.55, ey + aw * 0.7], fill=cola)
    if rim:
        draw(d, -max(2, 0.008 * h), rim)
    draw(d, 0, col)


def phone_glow(layer, x, y, s, col=CORAL, hearts_t=None):
    g = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    gd.ellipse([x - 120 * s, y - 120 * s, x + 120 * s, y + 80 * s], fill=col + (90,))
    layer.alpha_composite(g.filter(ImageFilter.GaussianBlur(30 * s)))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x - 22 * s, y - 36 * s, x + 22 * s, y + 36 * s], radius=int(6 * s), fill=(255, 190, 180, 255))
    if hearts_t is not None:
        for k in range(4):
            u = (hearts_t * 0.7 + k / 4) % 1
            hx, hy = x + 30 * s * math.sin(u * 6 + k), y - 40 * s - 180 * s * u
            heart(d, hx, hy, 1.4 * s, col=CORAL, a=int(230 * (1 - u)))


def heart(d, x, y, s, half=0, col=(235, 60, 100), a=255, rot=0.0, dx=0.0, dy=0.0, outline=True):
    pts = m.heart_pts(0, 0, s, half)
    cr, sr = math.cos(rot), math.sin(rot)
    d.polygon([(x + dx + px * cr - py * sr, y + dy + px * sr + py * cr) for px, py in pts], fill=col + (a,),
              outline=(70, 20, 30, a) if outline else None)


# ---------------------------------------------------------------------------------- fx
rnd = random.Random(23)
RAIN = [(rnd.uniform(-200, W + 200), rnd.uniform(0, H), rnd.uniform(1600, 2300), rnd.uniform(40, 110)) for _ in range(360)]
BOKEH = [(rnd.uniform(-60, W + 60), rnd.uniform(200, 1500), rnd.uniform(40, 120), rnd.random()) for _ in range(26)]


def rain_layer(t, amount=1.0, clear=None, col=(190, 210, 255), alpha=120, slant=0.12):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    n = int(len(RAIN) * amount)
    for x, y, sp, ln in RAIN[:n]:
        yy = (y + t * sp) % (H + 200) - 100
        xx = x - yy * slant
        d.line([(xx, yy), (xx - ln * slant, yy - ln)], fill=col + (alpha,), width=2)
    if clear:
        mask = Image.new("L", (W, H), 255)
        md = ImageDraw.Draw(mask)
        for poly in clear:
            md.polygon(poly, fill=0)
        mask = mask.filter(ImageFilter.GaussianBlur(8))
        lay.putalpha(Image.fromarray((np.asarray(lay.getchannel("A")).astype(np.float32) * np.asarray(mask) / 255).astype(np.uint8)))
    return lay


def bokeh_bg(t, top, bot, cols, blur=18, drift=1.0):
    g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    arr = np.array(top, np.float32) * (1 - g) + np.array(bot, np.float32) * g
    img = Image.fromarray(np.broadcast_to(arr, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, (x, y, r, c) in enumerate(BOKEH):
        col = cols[i % len(cols)]
        xx = x + 20 * math.sin(t * 0.3 * drift + i)
        d.ellipse([xx - r, y - r, xx + r, y + r], fill=col + (int(60 + 60 * c),))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)))
    return img


def glow(layer, box, col, a, blur):
    g = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse(box, fill=col + (a,))
    layer.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur)))


# ==============================================================================================
# locations
# ==============================================================================================
def crossing(t, cam, layer=None):
    """Night street seen across: bus shelter on the near side (left), shop awning on the far side (right).
    cam = (zoom, cx, cy): world point (cx, cy) goes to the frame centre."""
    z, ccx, ccy = cam

    def S(x, y):
        return ((x - ccx) * z + 540, (y - ccy) * z + 960)

    def R(x0, y0, x1, y1):
        a_, b_ = S(x0, y0), S(x1, y1)
        return [a_[0], a_[1], b_[0], b_[1]]
    img = Image.new("RGBA", (W, H), (8, 12, 22, 255))
    d = ImageDraw.Draw(img, "RGBA")
    g = np.linspace(0, 1, H, dtype=np.float32)
    for y in range(0, H, 8):   # sky
        f = clamp(((y - 960) / z + ccy) / 900)
        d.rectangle([0, y, W, y + 8], fill=(int(lerp(10, 22, f)), int(lerp(16, 30, f)), int(lerp(32, 48, f)), 255))
    # far buildings with shopfronts
    rr = random.Random(4)
    x = -200
    while x < 1300:
        bw, bh = rr.randint(160, 300), rr.randint(380, 640)
        d.rectangle(R(x, 860 - bh, x + bw - 6, 860), fill=(24, 30, 44, 255))
        for wy in range(int(860 - bh + 30), 600, 64):
            for wx in range(int(x + 22), int(x + bw - 40), 52):
                on = rr.random() < 0.35
                d.rectangle(R(wx, wy, wx + 26, wy + 34), fill=(255, 210, 140, 210) if on else (36, 44, 64, 255))
        x += bw
    d.rectangle(R(640, 700, 1080, 860), fill=(40, 34, 32, 255))            # shopfront under the awning
    d.rectangle(R(680, 720, 1040, 850), fill=(255, 214, 160, 200))           # lit window (no signs)
    for k in range(9):   # striped awning
        d.polygon([S(700 + k * 38, 640), S(738 + k * 38, 640), S(744 + k * 38, 700), S(706 + k * 38, 700)],
                  fill=(176, 52, 58, 255) if k % 2 else (230, 222, 206, 255))
    for k in range(9):
        cxk = 719 + k * 38
        a_, b_ = S(cxk - 19, 690), S(cxk + 19, 716)
        d.chord([a_[0], a_[1], b_[0], b_[1]], 0, 180, fill=(176, 52, 58, 255) if k % 2 else (230, 222, 206, 255))
    glow(img, R(640, 680, 1080, 880), (255, 200, 140), 70, 30 * z)
    d.rectangle(R(-400, 860, 1500, 885), fill=(70, 72, 80, 255))             # far sidewalk
    # the road, wet, with lamp reflections
    d.rectangle(R(-400, 885, 1500, 1110), fill=(30, 34, 42, 255))
    for k in range(6):
        d.rectangle(R(-300 + k * 260, 990, -180 + k * 260, 998), fill=(150, 150, 140, 180))
    refl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(refl)
    for lx in (120, 560, 980):
        for k in range(5):
            a_, b_ = S(lx - 9, 892 + k * 44), S(lx + 9, 920 + k * 44)
            rd.rectangle([a_[0], a_[1], b_[0], b_[1]], fill=(220, 230, 255, int(70 - 8 * k)))
    img.alpha_composite(refl.filter(ImageFilter.GaussianBlur(max(2, 10 * z))))
    d.rectangle(R(-400, 1110, 1500, 1130), fill=(96, 98, 106, 255))          # near curb
    d.rectangle(R(-400, 1130, 1500, 2400), fill=(44, 48, 58, 255))           # near sidewalk
    for k in range(-2, 14):
        d.line([S(-400, 1130 + k * 90), S(1500, 1130 + k * 90)], fill=(56, 60, 70, 255), width=max(1, int(2 * z)))
    pud = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pdd = ImageDraw.Draw(pud)
    for px_, py_, pw in ((640, 1500, 260), (200, 1700, 200), (860, 1820, 240)):   # puddles
        pdd.ellipse(R(px_ - pw, py_ - pw * 0.18, px_ + pw, py_ + pw * 0.18), fill=(90, 106, 136, 130))
    img.alpha_composite(pud.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img, "RGBA")
    # street lamp (near side)
    d.rectangle(R(552, 520, 566, 1140), fill=(80, 86, 100, 255))
    d.line([S(559, 520), S(500, 500)], fill=(80, 86, 100, 255), width=max(2, int(10 * z)))
    d.polygon([S(480, 490), S(522, 490), S(516, 500), S(486, 500)], fill=(90, 96, 110, 255))
    glow(img, R(420, 420, 580, 580), (220, 232, 255), 160, 24 * z)
    d.ellipse(R(486, 492, 514, 512), fill=(240, 246, 255, 255))
    # bus shelter (near side, left)
    flick = 0.75 + 0.25 * (1 if (int(t * 13) % 7) else 0)
    d.rectangle(R(40, 690, 440, 718), fill=(70, 76, 90, 255))
    glow(img, R(40, 640, 440, 900), (220, 240, 255), int(110 * flick), 30 * z)
    d.rectangle(R(70, 718, 410, 726), fill=(235, 245, 255, int(255 * flick)))
    d.rectangle(R(56, 726, 424, 1140), fill=(120, 150, 170, 70))
    d.rectangle(R(56, 1000, 424, 1140), fill=(170, 186, 200, 150))           # frosted lower panel
    for xx in (56, 240, 424):
        d.rectangle(R(xx - 5, 718, xx + 5, 1140), fill=(80, 86, 100, 255))
    d.rectangle(R(90, 950, 390, 966), fill=(70, 70, 80, 255))                # bench seen through the glass
    return img, S


def rooftop_bg(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 6):
        f = clamp(y / 1100)
        col = (int(lerp(70, 250, f ** 1.4)), int(lerp(52, 150, f ** 1.6)), int(lerp(120, 120, f)))
        d.rectangle([0, y, W, y + 6], fill=col + (255,))
    rr = random.Random(8)
    x = -20
    while x < W:   # distant city
        bw, bh = rr.randint(40, 110), rr.randint(80, 300)
        d.rectangle([x, 1100 - bh, x + bw, 1100], fill=(44, 34, 60, 255))
        for _ in range(bw * bh // 900):
            lx, ly = rr.uniform(x + 4, x + bw - 8), rr.uniform(1100 - bh + 6, 1090)
            d.rectangle([lx, ly, lx + 5, ly + 7], fill=(255, 210, 130, 255))
        x += bw + 4
    d.rectangle([40, 700, 230, 1100], fill=(40, 34, 50, 255))                 # water tank
    d.ellipse([30, 660, 240, 740], fill=(54, 46, 66, 255))
    d.rectangle([0, 1100, W, H], fill=(70, 56, 64, 255))                      # parapet / floor
    pts = [(x, 330 + 70 * math.sin(math.pi * x / W)) for x in range(-20, W + 40, 20)]
    d.line(pts, fill=(30, 26, 30, 255), width=3)
    bl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bl)
    for i, (x, y) in enumerate(pts[::2]):
        tw = 0.6 + 0.4 * math.sin(t * 3 + i * 1.3)
        bd.ellipse([x - 26, y - 8, x + 26, y + 44], fill=(255, 196, 110, int(90 * tw)))
        bd.ellipse([x - 8, y + 8, x + 8, y + 28], fill=(255, 224, 160, int(255 * tw)))
    img.alpha_composite(bl.filter(ImageFilter.GaussianBlur(3)))
    return img


def shelter_inside(t, fog=0.0):
    """Inside the bus shelter, seen through its front glass."""
    img = Image.new("RGBA", (W, H), (18, 24, 34, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 8):
        f = y / H
        d.rectangle([0, y, W, y + 8], fill=(int(lerp(34, 16, f)), int(lerp(44, 22, f)), int(lerp(56, 30, f)), 255))
    d.rectangle([90, 300, 990, 1020], fill=(60, 76, 92, 255))                 # back ad lightbox (blank)
    d.rectangle([110, 320, 970, 1000], fill=(90, 106, 120, 255))
    glow(img, (110, 320, 970, 1000), (210, 230, 250), 30, 50)
    d.rectangle([0, 0, W, 90], fill=(60, 66, 80, 255))
    d.rectangle([140, 90, 940, 104], fill=(240, 248, 255, 255))               # tube light
    glow(img, (100, 40, 980, 300), (220, 240, 255), 110, 60)
    d.rectangle([0, 1080, W, 1130], fill=(80, 82, 92, 255))                   # bench seat
    return img


def glass_front(t, layer, frosted_top=1150, bar=False, streak_seed=1):
    """Front glass of the shelter: rain rivulets, frosted lower ad panel, optional centre steel bar."""
    d = ImageDraw.Draw(layer)
    rr = random.Random(streak_seed)
    for k in range(26):
        x0 = rr.uniform(0, W)
        sp = rr.uniform(120, 340)
        y = (rr.uniform(0, H) + t * sp) % (frosted_top + 200) - 100
        pts = [(x0 + 4 * math.sin((y - j * 18) * 0.03 + k), y - j * 18) for j in range(10)]
        d.line(pts, fill=(200, 220, 255, 90), width=3)
        d.ellipse([pts[0][0] - 6, pts[0][1] - 6, pts[0][0] + 6, pts[0][1] + 8], fill=(220, 236, 255, 150))
    for k in range(60):
        x, y = rr.uniform(0, W), rr.uniform(0, frosted_top)
        r = rr.uniform(2, 6)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(220, 236, 255, 80))
    d.rectangle([0, frosted_top, W, H], fill=(64, 76, 94, 235))
    d.rectangle([0, frosted_top, W, frosted_top + 10], fill=(110, 120, 136, 255))
    if bar:
        d.rectangle([530, 0, 550, H], fill=(70, 76, 90, 255))
        d.rectangle([536, 0, 540, H], fill=(140, 150, 170, 255))


# ==============================================================================================
# grading
# ==============================================================================================
def grade(arr, kind, amt=1.0):
    if kind == "present":
        tint, de, lift = np.array([0.86, 0.95, 1.1], np.float32), 0.35, 0
    elif kind == "memory":
        tint, de, lift = np.array([1.14, 1.0, 0.8], np.float32), 0.0, 14
    elif kind == "dusk":
        tint, de, lift = np.array([1.08, 0.96, 0.92], np.float32), 0.08, 8
    else:   # final, coldest
        tint, de, lift = np.array([0.74, 0.90, 1.22], np.float32), 0.5, np.array([0, 2, 10], np.float32)
    lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
    out = arr * (1 - de) + lum[:, :, None] * de
    out = out * tint + lift
    return arr * (1 - amt) + out * amt


def bloom(arr, strength=0.35):
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    small = img.resize((W // 6, H // 6)).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
    b = np.asarray(small).astype(np.float32)
    return arr + np.clip(b - 140, 0, 255) * strength


# ==============================================================================================
# shots
# ==============================================================================================
SHOTS = [0.0, 1.13, 2.14, 4.21, 5.26, 6.15, 7.29, 9.05, 10.55, 12.20, 14.25, 15.21, 16.09, 16.97, DUR]


def shot_index(t):
    return max(i for i, s in enumerate(SHOTS[:-1]) if s <= t)


def u_of(t, i):
    return clamp((t - SHOTS[i]) / (SHOTS[i + 1] - SHOTS[i]))


def zoom_crop(img, z, fx=540, fy=960):
    if abs(z - 1) < 1e-3:
        return img
    cw, ch = W / z, H / z
    x0 = clamp(fx - cw / 2, 0, W - cw)
    y0 = clamp(fy - ch / 2, 0, H - ch)
    return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BICUBIC)


def couple_at_awning(d, S, t, z, point=0.0, shrug=0.0, hf=1.0):
    kx, ky = S(830, 862)
    gx, gy = S(910, 862)
    person(d, kx, ky, 300 * z * hf, "kabir", t, pose="shrug_t" if shrug > 0 else "stand", col=SLATE, rim=(150, 170, 200), arm_t=shrug)
    person(d, gx, gy, 262 * z * hf, "gf", t, pose="point_l" if point > 0 else "stand", col=(60, 52, 60), rim=CORAL, arm_t=point)


def s01(t):
    u = u_of(t, 0)
    z = lerp(1.0, 1.12, smooth(u))
    img, S = crossing(t, (z, 540, lerp(900, 920, u)))
    d = ImageDraw.Draw(img, "RGBA")
    couple_at_awning(d, S, t, z, hf=0.65)
    fx, fy = S(lerp(300, 330, smooth(u / 0.55)), lerp(1080, 1146, smooth(u / 0.55)))
    pop = 1 + 0.1 * math.sin(math.pi * clamp((t - 0.69) / 0.1))
    s = 0.32 * z * pop
    ira = place_by_feet(t, fx, fy, s)
    img.alpha_composite(ira.layer())
    open_amt = ease_out((t - 0.69) / 0.13) if t > 0.69 else 0.0
    d = ImageDraw.Draw(img, "RGBA")
    hx_, hy_ = ira.hand("R")
    top = ira.ws(ira.head[0] + 30, ira.head[1] - 300)
    if open_amt > 0:
        umbrella_open(d, top, (hx_, hy_), 340 * s, open_amt)
        glow_y = top[1] + 60 * s
        glow(img, [top[0] - 300 * s, glow_y - 100 * s, top[0] + 300 * s, glow_y + 300 * s], MUSTARD, int(60 * open_amt), 30 * s)
    else:
        umbrella_closed(d, (hx_, hy_), (hx_ + 10, hy_ - 260 * s), s * 1.2)
    clear = [[(top[0] - 340 * s, top[1] + 120 * s), (top[0] + 340 * s, top[1] + 120 * s), (top[0] + 300 * s, fy), (top[0] - 300 * s, fy)]] if open_amt > 0.5 else None
    img.alpha_composite(rain_layer(t, 0.6, clear=clear, alpha=90))
    return img, "present"


def back_of_head(d, x, y, s, a=255):
    hair = HAIR + (a,)
    if STYLE == "male":
        d.ellipse([x - 176 * s, y - 196 * s, x + 176 * s, y + 130 * s], fill=hair)
        for sx in (-1, 1):
            d.ellipse([x + sx * 170 * s - 26 * s, y - 20 * s, x + sx * 170 * s + 26 * s, y + 70 * s], fill=SKIN_SH + (a,))
        d.polygon([(x - 56 * s, y + 100 * s), (x + 56 * s, y + 100 * s), (x + 66 * s, y + 240 * s), (x - 66 * s, y + 240 * s)], fill=SKIN_SH + (a,))
        d.polygon([(x - 340 * s, y + 900 * s), (x - 310 * s, y + 320 * s), (x - 150 * s, y + 220 * s), (x + 150 * s, y + 220 * s),
                   (x + 310 * s, y + 320 * s), (x + 340 * s, y + 900 * s)], fill=DENIM + (a,))
        d.chord([x - 160 * s, y + 170 * s, x + 160 * s, y + 290 * s], 180, 360, fill=DENIM_SH + (a,))
        d.arc([x - 130 * s, y - 180 * s, x + 70 * s, y - 50 * s], 200, 300, fill=(86, 72, 66, a), width=max(2, int(10 * s)))
        return
    d.ellipse([x - 190 * s, y - 200 * s, x + 190 * s, y + 170 * s], fill=hair)
    d.rectangle([x - 186 * s, y - 20 * s, x + 186 * s, y + 160 * s], fill=hair)
    d.polygon([(x - 50 * s, y + 150 * s), (x + 50 * s, y + 150 * s), (x + 60 * s, y + 250 * s), (x - 60 * s, y + 250 * s)], fill=(150, 108, 80, a))
    d.polygon([(x - 330 * s, y + 900 * s), (x - 300 * s, y + 330 * s), (x - 140 * s, y + 230 * s), (x + 140 * s, y + 230 * s),
               (x + 300 * s, y + 330 * s), (x + 330 * s, y + 900 * s)], fill=DENIM + (a,))
    d.chord([x - 100 * s, y + 200 * s, x + 100 * s, y + 290 * s], 180, 360, fill=CREAM + (a,))
    d.polygon([(x - 166 * s, y - 92 * s), (x - 120 * s, y - 110 * s), (x - 114 * s, y - 96 * s), (x - 160 * s, y - 78 * s)], fill=MUSTARD + (a,))
    d.arc([x - 140 * s, y - 180 * s, x + 80 * s, y - 40 * s], 200, 300, fill=(70, 70, 96, a), width=max(2, int(10 * s)))


def s02(t):
    u = u_of(t, 1)
    z = lerp(2.3, 2.45, smooth(u))
    img, S = crossing(t, (z, lerp(820, 830, u), 760))
    d = ImageDraw.Draw(img, "RGBA")
    point = smooth((t - 1.35) / 0.18) if t > 1.35 else 0.0
    shrug = clamp((t - 1.72) / 0.35) if t > 1.72 else 0.0
    couple_at_awning(d, S, t, z, point=point, shrug=shrug)
    if 1.42 < t < 2.0:   # a coral "?" beside the one who asks
        q = clamp((t - 1.42) / 0.1) * (1 - clamp((t - 1.88) / 0.12))
        gx, gy = S(910, 862)
        f = m.kfont(140)
        d.text((gx + 90, gy - 300 * z * 1.0), "?", font=f, fill=(255, 165, 165, int(240 * q)), anchor="mm",
               stroke_width=3, stroke_fill=(30, 10, 14, int(240 * q)))
    img.alpha_composite(rain_layer(t, 0.5, alpha=80))
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fg)
    hx0 = 170 - 30 * u
    canopy_under(fd, hx0 - 20, 470, 520)
    fd.line([(hx0 - 20, 470 - 300), (hx0 - 10, 900)], fill=(120, 90, 60, 255), width=12)
    back_of_head(fd, hx0, 1080, 1.35)
    img.alpha_composite(fg.filter(ImageFilter.GaussianBlur(5)))
    return img, "present"


def s03(t):
    u = u_of(t, 2)
    img = bokeh_bg(t, (14, 22, 40), (24, 36, 54), [(220, 232, 255), (170, 200, 255), (255, 210, 160), CORAL, SLATE])
    s = lerp(2.15, 2.3, smooth(u))
    ira = Placed(t, 520, 660, s)
    lay = ira.layer()
    warm = Image.new("RGBA", (W, H), MUSTARD + (0,))   # warm bounce from the canopy on the hair and forehead
    g = np.linspace(1, 0, H, dtype=np.float32) ** 3
    warm.putalpha(Image.fromarray((np.asarray(lay.getchannel("A")).astype(np.float32) * g[:, None] * 0.35).astype(np.uint8)))
    img.alpha_composite(lay)
    img.alpha_composite(warm)
    d = ImageDraw.Draw(img, "RGBA")
    hx_, hy_ = ira.hand("R")
    d.line([(hx_, hy_ - 20), (880, -40)], fill=(120, 90, 60, 255), width=14)
    d.arc([hx_ - 34, hy_ - 10, hx_ + 34, hy_ + 70], 0, 180, fill=(120, 80, 46, 255), width=14)
    canopy_under(d, 880, -40, 900)
    # "खास": a soft gold heart on the chest; "नहीं": it cracks, greys and drips away
    if t > 3.0:
        k = clamp((t - 3.0) / 0.2)
        cr = clamp((t - 3.6) / 0.15)
        drip = clamp((t - 3.78) / 0.4)
        col = tuple(int(lerp(c, g_, cr)) for c, g_ in zip((255, 200, 90), (150, 150, 160)))
        hx2, hy2 = 650, 1120 + 140 * drip
        a2 = int(220 * k * (1 - drip))
        lay2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay2)
        sc = 5.2 * (0.6 + 0.4 * back_out(k))
        heart(ld, hx2, hy2, sc, col=col, a=a2, outline=False)
        if cr > 0:
            crack = [(0, -5), (-3, -1), (3, 3), (-2, 7), (0, 12)]
            ld.line([(hx2 + cx * sc, hy2 + cy * sc) for cx, cy in crack], fill=(60, 50, 50, a2), width=5)
        img.alpha_composite(lay2.filter(ImageFilter.GaussianBlur(10)))
        img.alpha_composite(lay2)
    img.alpha_composite(rain_layer(t, 0.4, clear=[[(0, 0), (W, 0), (W, H), (0, H)]], alpha=60))
    return img, "present"


def s04(t):
    u = u_of(t, 3)
    img = Image.new("RGBA", (W, H), (20, 26, 38, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, 1100, 8):
        d.rectangle([0, y, W, y + 8], fill=(int(lerp(22, 46, y / 1100)), int(lerp(28, 50, y / 1100)), int(lerp(40, 60, y / 1100)), 255))
    d.rectangle([0, 1040, W, 1080], fill=(96, 98, 106, 255))   # curb edge
    ira = place_by_feet(t, 540, 1040, 2.3)
    upper = img.copy()
    upper.alpha_composite(ira.layer())
    glow(upper, (700, -200, 1100, 200), (220, 232, 255), 120, 40)
    ref = upper.crop((0, 0, W, 1040)).transpose(Image.FLIP_TOP_BOTTOM).resize((W, 860))
    rg = ImageDraw.Draw(ref, "RGBA")
    rg.ellipse([660, 640, 940, 860], fill=MUSTARD + (110,))   # the umbrella's glow, reflected at her hand's side
    ref = ref.filter(ImageFilter.GaussianBlur(3))
    arr = np.asarray(ref).astype(np.float32)
    warm_k = 0.0
    if t > 4.65:   # the tear lands: rings spread and turn the reflection into a golden memory
        r_t = (t - 4.65)
        yy, xx = np.mgrid[0:arr.shape[0], 0:W]
        dist = np.sqrt((xx - 540) ** 2 + ((yy - 300) * 2.2) ** 2)
        wave = np.sin(dist / 22 - r_t * 14) * np.exp(-dist / (200 + 900 * r_t)) * 14
        sx = np.clip(xx + wave, 0, W - 1).astype(int)
        arr = arr[yy, sx]
        warm_k = clamp(r_t / 0.55)
        warm = np.array([255, 190, 110], np.float32)
        circle = np.clip(1 - dist / (100 + 1500 * r_t), 0, 1)[:, :, None]
        arr[:, :, :3] = arr[:, :, :3] * (1 - circle * 0.6) + warm * circle * 0.6
    ref = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    mask = Image.new("L", ref.size, 0)
    ImageDraw.Draw(mask).ellipse([140, 60, 940, 820], fill=215)
    mask = mask.filter(ImageFilter.GaussianBlur(10))
    out = upper
    out.paste(Image.new("RGBA", (W, 860), (34, 38, 48, 255)), (0, 1060))
    od = ImageDraw.Draw(out, "RGBA")
    for k in range(10):
        od.line([(0, 1100 + k * 80), (W, 1100 + k * 80)], fill=(44, 48, 58, 255), width=3)
    out.paste(ref, (0, 1060), mask)
    od = ImageDraw.Draw(out, "RGBA")
    od.ellipse([140, 1120, 940, 1880], outline=(120, 132, 156, 120), width=3)
    if 4.22 < t < 4.66:   # the falling tear, big enough to follow
        fy = lerp(-60, 1360, smooth((t - 4.22) / 0.43))
        for k in range(4):
            od.ellipse([540 - 10 + k, fy - 120 - k * 30, 540 + 10 - k, fy - 90 - k * 30], fill=(190, 220, 255, 60 - k * 12))
        od.ellipse([520, fy - 26, 560, fy + 22], fill=(190, 220, 255, 235))
        od.polygon([(540, fy - 60), (520, fy - 12), (560, fy - 12)], fill=(190, 220, 255, 235))
        od.ellipse([528, fy - 16, 540, fy - 4], fill=(255, 255, 255, 230))
    if t > 4.65:
        r_t = t - 4.65
        rl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rl)
        for k in range(4):
            rr_ = 30 + (r_t * 420 + k * 60) % 500
            rd.ellipse([540 - rr_, 1360 - rr_ * 0.3, 540 + rr_, 1360 + rr_ * 0.3], outline=(220, 236, 255, int(180 * (1 - rr_ / 530))), width=2 + k % 3 + 1)
        out.alpha_composite(rl.filter(ImageFilter.GaussianBlur(2)))
    img = zoom_crop(out, lerp(1.0, 1.06, u))
    img = img.rotate(-3 * smooth(u), resample=Image.BICUBIC)
    img = zoom_crop(img, 1.06)
    return img, ("present", warm_k)


def golden_street(t):
    top, bot = (110, 70, 80), (255, 170, 110)
    g = m.GRAD_Y
    arr = np.array(top, np.float32) * (1 - g) + np.array(bot, np.float32) * g
    img = Image.fromarray(np.broadcast_to(arr, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(m.draw_env(t, "golden", bot))
    return img


def s05(t):
    u = u_of(t, 4)
    img = golden_street(t)
    s = 0.72
    ira = place_by_feet(t, 440, 1580, s)
    kx, kfeet, kh = 720, 1586, 930
    merge = smooth((t - 5.68) / 0.4)   # their long shadows slide together on "दोस्त"
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for x0, w0 in ((kx, 95), (440, 85)):
        xm = lerp(x0, 550, merge)
        sd.polygon([(x0 - w0, kfeet), (x0 + w0, kfeet), (xm + w0 * 2.2, H), (xm - w0 * 2.2, H)], fill=(40, 20, 20, 100))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(img, "RGBA")
    hf = smooth((t - 5.5) / 0.15) * (1 - smooth((t - 5.85) / 0.1))
    person(d, kx, kfeet, kh, "kabir", t, pose="palm_l" if hf > 0 else "stand", col=SEPIA, rim=(255, 200, 120), walk=1.0, ph=0.6, arm_t=hf)
    img.alpha_composite(ira.layer())
    d = ImageDraw.Draw(img, "RGBA")
    hx_, hy_ = ira.hand("L")
    top = (600, 380)
    umbrella_open(d, top, (hx_, hy_), 430)
    if 5.62 < t < 5.95:   # high-five glint where the palms meet
        q = math.sin(math.pi * (t - 5.62) / 0.33)
        glow(img, [560 - 110, 715 - 110, 560 + 110, 715 + 110], (255, 236, 170), int(190 * q), 18)
    img.alpha_composite(rain_layer(t, 0.35, col=(255, 220, 150), alpha=110, clear=[[(top[0] - 430, top[1] + 170), (top[0] + 430, top[1] + 170), (1000, 1600), (250, 1600)]]))
    glow(img, (380, 520, 700, 840), (255, 220, 160), 80, 60)   # flare at the sun
    return zoom_crop(img, lerp(1.0, 1.04, u), 540, 1000), "memory"


def hand_shape(d, x, y, s, flip, col, outline, hook=0.0, cuff=None, pinky_dir=-1):
    """A loose fist seen from the side, pinky reaching to the other hand; flip=-1 mirrors.
    pinky_dir=-1 curls the pinky tip upwards, +1 downwards (so two pinkies interlock)."""
    def P(px, py):
        return (x + flip * px * s, y + py * s)
    lw = max(2, int(3 * s))
    if cuff:
        d.polygon([P(-520, -96), P(-150, -110), P(-150, 104), P(-520, 92)], fill=cuff, outline=outline)
        d.polygon([P(-205, -112), P(-150, -114), P(-150, 108), P(-205, 104)], fill=tuple(min(255, c + 45) for c in cuff[:3]) + (255,), outline=outline)
    palm = [P(-150, -80), P(10, -92), P(60, -76), P(84, -58), P(80, -40), P(90, -22), P(86, -2), P(92, 16), P(86, 36), P(62, 70), P(-150, 80)]
    d.polygon(palm, fill=col, outline=outline)
    for k in range(3):   # knuckle creases
        d.line([P(56, -44 + k * 38), P(80, -40 + k * 38)], fill=outline, width=lw)
    d.polygon([P(-60, -82), P(20, -108), P(54, -98), P(34, -80), P(-40, -70)], fill=col, outline=outline)   # thumb
    tip_y = 60 + pinky_dir * 50 * hook
    pts = [P(60, 62), P(150, 62), P(196, tip_y)]
    d.line(pts, fill=outline, width=int(34 * s), joint="curve")
    d.line(pts, fill=col, width=int(28 * s), joint="curve")
    tx, ty = P(196, tip_y)
    d.ellipse([tx - 14 * s, ty - 14 * s, tx + 14 * s, ty + 14 * s], fill=col, outline=outline, width=lw)


def s06(t):
    u = u_of(t, 5)
    img = bokeh_bg(t, (105, 78, 62), (185, 135, 95), [(240, 200, 150), (230, 180, 120), (250, 220, 170)], blur=26)
    d = ImageDraw.Draw(img, "RGBA")
    slide = ease_out(clamp((t - 6.15) / 0.12))
    hook = smooth((t - 6.2) / 0.1)
    pulse = 1 + 0.05 * math.sin(math.pi * clamp((t - 6.28) / 0.16))
    s = 1.15 * pulse
    lx = lerp(-260, 355, slide)
    rx = lerp(1340, 750, slide)
    hand_shape(d, rx, 950, s, -1, SEPIA + (255,), (60, 40, 30, 255), hook=hook, pinky_dir=-1)
    hand_shape(d, lx, 850, s * 0.9, 1, SKIN + (255,), LINE + (255,), hook=hook, cuff=DENIM + (255,), pinky_dir=1)
    # the friendship thread on the wrist; one strand frays loose on "कच्चा"
    tx, ty = lx - 150 * s * 0.9, 850
    d.ellipse([tx - 20, ty - 110, tx + 20, ty + 110], outline=THREAD_R + (255,), width=14)
    d.ellipse([tx - 14, ty - 104, tx + 14, ty + 104], outline=(250, 250, 250, 255), width=4)
    if t > 6.52:
        fr = clamp((t - 6.52) / 0.6)
        pts = [(tx + 16 + 50 * fr * k / 8 + 16 * math.sin(t * 9 + k), ty - 90 - 150 * fr * k / 8) for k in range(9)]
        d.line(pts, fill=(235, 60, 70, 255), width=6)
    if t > 6.25:
        q = math.sin(math.pi * clamp((t - 6.25) / 0.5))
        glow(img, (440, 720, 640, 920), (255, 236, 180), int(90 * q), 24)
    img.alpha_composite(rain_layer(t, 0.25, col=(255, 230, 170), alpha=110))
    img = img.rotate(2 * smooth(u), resample=Image.BICUBIC)
    return zoom_crop(img, lerp(1.06, 1.14, smooth(u))), "memory"


def crossed_fingers(d, x, y, s, a=255):
    """Back of a hand lying on the table, index and middle finger crossed (middle over index)."""
    col, ol, rim = SKIN + (a,), LINE + (a,), (240, 226, 200, a)
    w = max(2, int(3 * s))
    d.polygon([(x - 64 * s, y - 14 * s), (x + 72 * s, y - 24 * s), (x + 84 * s, y + 38 * s), (x - 54 * s, y + 52 * s)], fill=col, outline=rim)
    for k in range(2):   # folded ring and little finger
        d.ellipse([x + (14 + k * 32) * s, y - 26 * s, x + (46 + k * 32) * s, y + 10 * s], fill=col, outline=ol, width=w)
    d.line([(x - 60 * s, y + 6 * s), (x - 94 * s, y - 30 * s)], fill=ol, width=int(32 * s))   # thumb
    d.line([(x - 60 * s, y + 6 * s), (x - 94 * s, y - 30 * s)], fill=col, width=int(26 * s))
    for (x0, x1, top) in ((-30, 4, -150), (8, -12, -146)):   # index first, middle last (on top), crossing at ~70%
        d.line([(x + x0 * s, y - 18 * s), (x + x1 * s, y + top * s)], fill=ol, width=int(30 * s))
        d.line([(x + x0 * s, y - 18 * s), (x + x1 * s, y + top * s)], fill=col, width=int(24 * s))
        d.ellipse([x + x1 * s - 12 * s, y + top * s - 12 * s, x + x1 * s + 12 * s, y + top * s + 12 * s], fill=col, outline=ol, width=w)


def s07(t):
    u = u_of(t, 6)
    img = rooftop_bg(t)
    d = ImageDraw.Draw(img, "RGBA")
    person(d, 930, 2050, 1600, "kabir", t, pose="phone", col=(80, 60, 50), rim=(255, 190, 120))
    phone_glow(img, 900, 1026, 1.8)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([860, 961, 940, 1091], radius=12, fill=(255, 150, 140, 255))
    heart(d, 900, 1020, 1.7, col=(255, 90, 100), a=255, outline=False)
    ira = Placed(t, 430, 650, 1.18)
    lay = ira.layer()
    sp = track(T["split"], t)   # "आधा सच्चा": warm on her left half, cool on her right half
    if sp > 0.01:
        arr = np.asarray(lay).astype(np.float32)
        xx = np.arange(W, dtype=np.float32)
        warm_side = np.clip((430 - xx) / 160 + 0.5, 0, 1)[None, :, None]
        cool = np.array([0.82, 0.9, 1.08], np.float32)
        add = np.array([26, 12, -6], np.float32)
        rgb = arr[:, :, :3]
        rgb = rgb * (1 - sp * (1 - warm_side) * (1 - cool)) + sp * warm_side * add
        arr[:, :, :3] = rgb
        lay = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    img.alpha_composite(lay)
    glow(img, (120, 300, 420, 600), (255, 200, 120), 50, 50)    # fairy lights on her hair
    glow(img, (520, 640, 700, 820), CORAL, int(40 * sp), 40)     # phone glow on her cheek
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 1080, W, 1520], fill=(104, 70, 54, 255))
    d.rectangle([0, 1080, W, 1110], fill=(140, 98, 74, 255))
    for x in range(40, W, 160):
        d.line([(x, 1112), (x + 20, 1520)], fill=(90, 60, 46, 255), width=3)
    for gx in (560, 690):
        d.polygon([(gx - 26, 990), (gx + 26, 990), (gx + 20, 1084), (gx - 20, 1084)], fill=(240, 236, 228, 140), outline=(200, 196, 190, 255))
        d.rectangle([gx - 22, 1010, gx + 22, 1080], fill=(200, 140, 80, 220))
    crossed_fingers(d, 300, 1110, 1.35)
    if 7.55 < t < 8.1:   # a small sparkle over the crossed fingers
        q = math.sin(math.pi * (t - 7.55) / 0.55)
        sx_, sy_ = 300, 880
        for ang in range(0, 360, 90):
            r_ = 30 * q
            d.line([(sx_, sy_), (sx_ + r_ * math.cos(math.radians(ang)), sy_ + r_ * math.sin(math.radians(ang)))], fill=(255, 245, 210, int(90 * q)), width=4)
    img = zoom_crop(img, lerp(1.0, 1.06, smooth(u)), 540, 960)
    img = img.rotate(-5, resample=Image.BICUBIC)
    return zoom_crop(img, 1.16), "dusk"


def tapered_leg(d, x_top, y_top, x_bot, y_bot, w_top, w_bot, col, outline, rim=None):
    poly = [(x_top - w_top, y_top), (x_top + w_top, y_top), (x_bot + w_bot, y_bot), (x_bot - w_bot, y_bot)]
    if rim:
        d.polygon([(px - 6, py) for px, py in poly], fill=rim)
    d.polygon(poly, fill=col, outline=outline)


def s08(t):
    u = u_of(t, 7)
    teal = clamp((t - 9.93) / 0.3)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(0, H, 8):
        f = y / H
        warm = (int(lerp(150, 60, f)), int(lerp(96, 50, f)), int(lerp(70, 50, f)))
        cold = (int(lerp(30, 24, f)), int(lerp(48, 34, f)), int(lerp(60, 44, f)))
        d.rectangle([0, y, W, y + 8], fill=tuple(int(lerp(a, b, teal)) for a, b in zip(warm, cold)) + (255,))
    for k in range(12):   # road texture slides towards us
        yy = 900 + ((k * 120 + (t - 9.05) * 380) % 1100)
        d.line([(0, yy), (W, yy)], fill=(0, 0, 0, 40), width=3)
    for px_, py_, pw in ((300, 1600, 220), (820, 1780, 240)):
        d.ellipse([px_ - pw, py_ - pw * 0.2, px_ + pw, py_ + pw * 0.2], fill=(200, 160, 120, 70) if teal < 0.5 else (80, 100, 130, 90))
    # his legs beside hers, until they veer away on the 9.93 beat
    leave = smooth((t - 9.93) / 0.45)
    kx = lerp(860, 1500, leave)
    rim = (255, 200, 120, 255) if teal < 0.5 else (120, 150, 190, 255)
    for s_ in (-1, 1):
        sw_ = math.sin(math.pi * (t - BEAT0) / BEAT + (0 if s_ < 0 else math.pi))
        lift = max(0, sw_) * 60 * (1 - leave)
        fx = kx + s_ * 95 + leave * 160
        tapered_leg(d, fx - 30 * leave, -20, fx, 1600 - lift, 84, 66, (44, 36, 32, 255), (20, 16, 14, 255), rim=rim)
        d.polygon([(fx - 90, 1610 - lift), (fx - 70, 1570 - lift), (fx + 70, 1570 - lift), (fx + 120, 1600 - lift), (fx + 116, 1650 - lift),
                   (fx - 90, 1650 - lift)], fill=(30, 28, 32, 255), outline=(14, 14, 18, 255))
        d.line([(fx - 86, 1640 - lift), (fx + 112, 1640 - lift)], fill=(230, 230, 236, 255), width=10)
    for k in range(6):   # drops falling off the umbrella edge, between the two of them
        yy = (t * 900 + k * 240) % 1500
        d.polygon([(700, yy - 18), (692, yy), (708, yy)], fill=(220, 236, 255, 170 if leave < 0.5 else 70))
        d.ellipse([692, yy - 6, 708, yy + 10], fill=(220, 236, 255, 170 if leave < 0.5 else 70))
    ira = place_by_feet(t, 330, 1760, 3.2)
    img.alpha_composite(ira.layer())
    img.alpha_composite(rain_layer(t, 0.3 + 0.4 * teal, alpha=90))
    kind = "memory" if teal < 0.01 else ("present", 1 - teal)
    return img, kind


def masked_above(lay, y_cut):
    a = np.asarray(lay.getchannel("A")).copy()
    a[y_cut:, :] = 0
    lay.putalpha(Image.fromarray(a))
    return lay


def s09(t):
    u = u_of(t, 8)
    img = shelter_inside(t)
    ira = Placed(t, 420, 700, 1.25)
    img.alpha_composite(masked_above(ira.layer(), 1150))
    d = ImageDraw.Draw(img, "RGBA")
    umbrella_closed(d, (120, 1140), (150, 690), 2.3)   # leaning on the bench beside him/her
    for k in range(3):
        yy = 1140 + ((t * 300 + k * 60) % 100)
        d.ellipse([114, yy, 126, yy + 14], fill=(200, 220, 255, 200))
    glass = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glass_front(t, glass, 1150, streak_seed=4)
    # "साथी": a golden memory of the two of them under the umbrella appears on the glass; "था": rain washes it off
    if t > 11.5:
        a_in = clamp((t - 11.5) / 0.25)
        wash = clamp((t - 11.94) / 0.35)
        glow(img, (600, 420, 1040, 1100), MUSTARD, int(70 * a_in * (1 - wash)), 60)
        mem = MEM_THUMB.copy()
        ma = np.asarray(mem.getchannel("A")).astype(np.float32) * 0.6 * a_in
        if wash > 0:
            yy = np.arange(mem.height, dtype=np.float32)[:, None]
            ma = ma * np.clip((yy - wash * mem.height * 1.2) / 60, 0, 1)
        rgb = np.asarray(mem.convert("RGB")).astype(np.float32) * np.array([1.2, 1.0, 0.7], np.float32)
        mem = Image.fromarray(np.clip(np.dstack([rgb, ma]), 0, 255).astype(np.uint8), "RGBA")
        img.alpha_composite(mem, (600, 380))
    img.alpha_composite(glass)
    if t < 10.65:
        img = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), img, clamp((t - 10.55) / 0.1))
    return zoom_crop(img, lerp(1.0, 1.06, smooth(u))), "present"


def s10(t):
    u = u_of(t, 9)
    img = shelter_inside(t)
    d = ImageDraw.Draw(img, "RGBA")
    umbrella_closed(d, (150, 1120), (170, 700), 1.8)
    leave = smooth((t - 13.89) / 0.35)
    if t > 13.6:   # a coral light arrives from the right: the one he is leaving for
        glow(img, (900, 300, 1400, 1300), CORAL, int(90 * smooth((t - 13.6) / 0.4)), 80)
        d = ImageDraw.Draw(img, "RGBA")
    if leave < 1:   # lost in the coral phone
        kx = lerp(760, 1350, leave)
        person(d, kx, 1850, 1600, "kabir", t, pose="phone", col=SLATE, rim=(150, 170, 200))
        hk = KIND_H.get(KIND_MAP.get("kabir", "kabir"), 1.0)
        phone_glow(img, kx - 48 * hk, 1850 - 1600 * hk + 0.36 * 1600 * hk, 1.5, hearts_t=t)
        d = ImageDraw.Draw(img, "RGBA")
    ira = Placed(t, 330, 760, 1.05)
    img.alpha_composite(masked_above(ira.layer(), 1150))
    if 12.24 < t < 13.4:   # the hand-width gap on the bench glows
        q = math.sin(math.pi * (t - 12.24) / 1.16)
        glow(img, (420, 1030, 660, 1140), (255, 230, 170), int(110 * q), 20)
    fog = smooth((t - 13.3) / 0.6)
    if fog > 0:   # a fog wall spreads from the steel bar over the other half
        arr = np.asarray(img).astype(np.float32)
        blurred = np.asarray(img.filter(ImageFilter.GaussianBlur(16))).astype(np.float32)
        xx = np.arange(W, dtype=np.float32)
        front = 540 + fog * 560
        mk = (np.clip((front - xx) / 120, 0, 1) * (xx > 540))[None, :, None]
        haze = np.array([170, 184, 204, 255], np.float32)
        arr = arr * (1 - mk) + (blurred * 0.6 + haze * 0.4) * mk
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    glass = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glass_front(t, glass, 1150, bar=True, streak_seed=6)
    img.alpha_composite(glass)
    return zoom_crop(img, lerp(1.0, 1.04, smooth(u))), "present"


def s11(t):
    u = u_of(t, 10)
    z = lerp(1.0, 1.08, smooth(u))
    img = Image.new("RGBA", (W, H), (10, 14, 24, 255))
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(0, 900, 8):
        d.rectangle([0, y, W, y + 8], fill=(int(lerp(12, 24, y / 900)), int(lerp(16, 30, y / 900)), int(lerp(30, 46, y / 900)), 255))
    d.rectangle([0, 780, W, 1300], fill=(36, 40, 50, 255))
    d.rectangle([0, 1300, W, 1330], fill=(96, 98, 106, 255))
    d.rectangle([0, 1330, W, H], fill=(30, 34, 42, 255))
    refl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(refl)
    for lx in (300, 760):
        for k in range(6):
            rd.rectangle([lx - 9, 1340 + k * 90, lx + 9, 1400 + k * 90], fill=(220, 230, 255, int(30 - 4 * k)))
    img.alpha_composite(refl.filter(ImageFilter.GaussianBlur(10)))
    # the shelter, lit, now on his/her right (reverse angle)
    d.rectangle([560, 760, 900, 780], fill=(70, 76, 90, 255))
    glow(img, (540, 720, 920, 980), (220, 240, 255), 120, 30)
    d.rectangle([580, 780, 880, 1300], fill=(120, 150, 170, 70))
    d.rectangle([580, 1150, 880, 1300], fill=(170, 186, 200, 120))
    ira = place_by_feet(t, 470, 1300, 0.48)
    img.alpha_composite(ira.layer())
    d = ImageDraw.Draw(img, "RGBA")
    hx_, hy_ = ira.hand("R")
    top = ira.ws(ira.head[0] + 30, ira.head[1] - 300)
    open_amt = ease_out((t - 14.30) / 0.13) if t > 14.30 else 0.0
    if open_amt > 0:
        umbrella_open(d, top, (hx_, hy_), 340 * 0.48, open_amt)
        glow(img, [top[0] - 150, top[1] - 20, top[0] + 150, top[1] + 180], MUSTARD, int(60 * open_amt), 20)
    else:
        umbrella_closed(d, (hx_, hy_), (hx_ + 6, hy_ - 120), 0.6)
    img.alpha_composite(rain_layer(t, 0.5, alpha=80))
    # foreground: the friend's head and shoulder (right), the new partner (left) pointing across at him/her
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fg, "RGBA")
    spread = 50 * smooth(u)
    person(fd, 1110 + spread, 3660, 2700, "kabir", t, col=(24, 26, 34), rim=(120, 140, 170))
    person(fd, -40 - spread, 3700, 2600, "gf", t, col=(40, 30, 38), rim=CORAL)
    point = smooth((t - 14.6) / 0.2)
    if point > 0:
        sx_, sy_ = 230 - spread, 1560
        ex_, ey_ = lerp(sx_, 340, point), lerp(sy_, 1060, point)
        fd.polygon([(sx_ - 70, sy_), (sx_ + 70, sy_), (ex_ + 26, ey_), (ex_ - 26, ey_)], fill=CORAL + (255,))
        fd.polygon([(sx_ - 64, sy_), (sx_ + 64, sy_), (ex_ + 20, ey_ + 4), (ex_ - 20, ey_ + 4)], fill=(40, 30, 38, 255))
        fd.ellipse([ex_ - 30, ey_ - 30, ex_ + 30, ey_ + 30], fill=(40, 30, 38, 255))
        fd.polygon([(ex_ - 10, ey_ - 20), (ex_ + 70, ey_ - 66), (ex_ + 12, ey_ + 6)], fill=(40, 30, 38, 255))
    img.alpha_composite(fg.filter(ImageFilter.GaussianBlur(6)))
    return zoom_crop(img, z, 520, 1000), "present"


def s12(t):
    u = u_of(t, 11)
    img = bokeh_bg(t, (14, 20, 36), (26, 34, 50), [(200, 220, 255), (150, 180, 230), (255, 210, 160)], blur=22)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([648, 0, 1080, H], fill=(90, 120, 150, 60))       # the shelter's glass side panel
    d.rectangle([636, 0, 648, H], fill=(80, 86, 100, 255))
    ira = Placed(t, 380, 760, lerp(2.2, 2.35, smooth(u)))
    lay = ira.layer()
    # the reflection in the glass: mirrored, smaller, darker, colder; a raindrop smears its face away
    ref = lay.transpose(Image.FLIP_LEFT_RIGHT)
    ref = ref.resize((int(W * 0.85), int(H * 0.85)), Image.BILINEAR)
    arr = np.asarray(ref).astype(np.float32)
    arr[:, :, :3] *= np.array([0.55, 0.65, 0.85], np.float32)
    arr[:, :, 3] *= 0.28
    ref = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))
    smear = clamp((t - 15.31) / 0.6)
    hx_m, hy_m = (W - 380) * 0.85, 760 * 0.85
    if smear > 0:
        box = (int(hx_m - 200), int(hy_m - 220), int(hx_m + 200), int(hy_m + 240))
        face = ref.crop(box)
        st = face.copy()
        for k in range(1, 9):
            st.alpha_composite(face.transform(face.size, Image.AFFINE, (1, 0, 0, 0, 1, -k * 16 * smear)))
        st = st.filter(ImageFilter.GaussianBlur(10 * smear))
        ref.paste(Image.new("RGBA", face.size, (0, 0, 0, 0)), box[:2])
        ref.alpha_composite(st, box[:2])
    refl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    refl.paste(ref, (int(960 - hx_m), int(760 - hy_m)))
    rm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(rm).rectangle([648, 0, W, 1150], fill=255)
    refl.putalpha(Image.fromarray(np.minimum(np.asarray(refl.getchannel("A")), np.asarray(rm.filter(ImageFilter.GaussianBlur(20))))))
    img.alpha_composite(refl)
    d = ImageDraw.Draw(img, "RGBA")
    for k, x0 in enumerate((700, 820, 960)):   # glass highlights
        d.polygon([(x0, 0), (x0 + 40, 0), (x0 - 260, 1150), (x0 - 300, 1150)], fill=(255, 255, 255, 14))
    if t > 15.31:   # the fat raindrop and the rivulets
        dy = clamp((t - 15.31) / 0.12)
        d.ellipse([942, 600 + 60 * dy, 978, 640 + 60 * dy], fill=(210, 230, 255, 200))
        for k in range(5):
            x = 880 + k * 40
            d.line([(x, 600), (x + 4, 600 + 500 * smear)], fill=(200, 220, 255, 110), width=4)
    img.alpha_composite(lay)
    d = ImageDraw.Draw(img, "RGBA")
    hx_, hy_ = ira.hand("R")
    d.line([(hx_, hy_ - 20), (hx_, -60)], fill=(120, 90, 60, 255), width=12)
    canopy_under(d, hx_, -60, 820)
    warm = Image.new("RGBA", (W, H), MUSTARD + (0,))
    g = np.linspace(1, 0, H, dtype=np.float32) ** 3
    warm.putalpha(Image.fromarray((np.asarray(lay.getchannel("A")).astype(np.float32) * g[:, None] * 0.3).astype(np.uint8)))
    img.alpha_composite(warm)
    img.alpha_composite(rain_layer(t, 0.3, alpha=60, clear=[[(0, 0), (640, 0), (640, H), (0, H)]]))
    return img, "present"


def s13(t):
    u = u_of(t, 12)
    img = bokeh_bg(t, (14, 20, 34), (30, 34, 46), [(255, 214, 160), (220, 232, 255), (176, 52, 58)], blur=20)
    d = ImageDraw.Draw(img, "RGBA")
    for k in range(8):   # awning stripes, top right
        d.polygon([(560 + k * 70, 0), (630 + k * 70, 0), (640 + k * 70, 150), (570 + k * 70, 150)], fill=(176, 52, 58, 255) if k % 2 else (230, 222, 206, 255))
    glow(img, (500, 100, 1180, 600), (255, 200, 140), 80, 50)
    # the new partner waiting behind, partly out of frame
    person(d, 1260, 2300, 1700, "gf", t, col=(40, 32, 40), rim=CORAL, a=170)
    ira = Placed(t, 420, 640, 1.3)
    img.alpha_composite(ira.layer())
    d = ImageDraw.Draw(img, "RGBA")
    hx_, hy_ = ira.hand("R")
    gone = smooth((t - 16.53) / 0.3)
    reach = smooth((t - 16.15) / 0.3)
    kx = lerp(lerp(1240, hx_ + 40, reach), 1300, gone)
    ky = hy_ + 4
    # the friend's shoulder at the right edge, sleeve tapering to a fist round the shaft
    d.polygon([(960, 640), (1180, 600), (1200, 1300), (980, 1320)], fill=(150, 170, 200, 255))
    d.polygon([(970, 650), (1190, 610), (1210, 1310), (990, 1330)], fill=SLATE + (255,))
    if FRIEND_CUP:
        d.ellipse([990, 560, 1060, 660], fill=SLATE + (255,))
    w0, w1 = ARM_W[0] * 0.7, ARM_W[0] * 0.5
    ang = math.atan2(ky - 760, kx - 1010)
    nx, ny = -math.sin(ang), math.cos(ang)
    d.polygon([(1010 + nx * w0, 760 + ny * w0), (kx + nx * w1, ky + ny * w1), (kx - nx * w1, ky - ny * w1), (1010 - nx * w0, 760 - ny * w0)],
              fill=SLATE + (255,), outline=(150, 170, 200, 255))
    handle_x = hx_ if gone < 0.01 else kx
    top = (handle_x - 60, hy_ - 820)
    umbrella_open(d, top, (handle_x, hy_), 480)
    d.ellipse([kx - 30, ky - 40, kx + 30, ky + 20], fill=SLATE + (255,), outline=(150, 170, 200, 255))
    if gone < 0.5:
        glow(img, [ira.ax - 300, ira.ay - 300, ira.ax + 300, ira.ay + 200], MUSTARD, int(70 * (1 - gone * 2)), 50)
    clear = [[(top[0] - 520, top[1] + 220), (top[0] + 520, top[1] + 220), (top[0] + 450, 1400), (top[0] - 450, 1400)]] if gone < 0.5 else None
    img.alpha_composite(rain_layer(t, 0.4 + 0.5 * gone, clear=clear, alpha=110))
    return zoom_crop(img, lerp(1.0, 1.05, smooth(u)), 480, 900), "present"


def s14(t):
    u = u_of(t, 13)
    top, bot = (6, 10, 22), (26, 32, 54)
    g = m.GRAD_Y
    arr = np.array(top, np.float32) * (1 - g) + np.array(bot, np.float32) * g
    img = Image.fromarray(np.broadcast_to(arr, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(m.draw_env(t, "street", bot))
    d = ImageDraw.Draw(img, "RGBA")
    # far away, right of the hero: the yellow umbrella over the two of them, walking off into the rain
    fz = lerp(16, 40, clamp((t - 16.97) / 2.5))
    fa = 1 - smooth((t - 19.1) / 0.4)
    if fa > 0:
        sx, base = m.proj(1.5, 0, fz)
        hh = 1.7 * m.FOCAL / fz
        person(d, sx - hh * 0.12, base, hh, "kabir", t, col=(30, 34, 46), walk=1, a=int(220 * fa))
        person(d, sx + hh * 0.12, base, hh * 0.88, "gf", t, col=(40, 34, 44), walk=1, ph=1, a=int(220 * fa))
        R = max(hh * 0.55, 45)
        umbrella_open(d, (sx, base - hh * 1.25), (sx, base - hh * 0.55), R, a=int(255 * fa))
        glow(img, [sx - R * 1.4, base - hh * 1.5, sx + R * 1.4, base - hh * 0.6], MUSTARD, int(130 * fa), max(8, hh * 0.2))
    into = smooth((t - 19.0) / 0.8)
    s = lerp(0.74, 3.6, into ** 1.6)
    hy = lerp(660, 300, into)
    ira = Placed(t, lerp(390, 540, into), hy, s)
    img.alpha_composite(ira.layer())
    img.alpha_composite(rain_layer(t, 1.0, alpha=130))
    bk = smooth((t - 19.6) / 0.25)
    if bk > 0:
        img = Image.blend(img, Image.new("RGBA", (W, H), (0, 0, 0, 255)), bk)
    return img, "final"


SHOT_FUNCS = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12, s13, s14]
MEM_THUMB = None


def make_mem_thumb():
    """A small warm frame of them under the umbrella (from shot 5) for the reflection on the glass."""
    img, _ = s05(5.7)
    thumb = img.resize((440, 782)).filter(ImageFilter.GaussianBlur(1.5))
    mask = Image.new("L", thumb.size, 0)
    ImageDraw.Draw(mask).ellipse([20, 40, 420, 760], fill=255)
    thumb.putalpha(mask.filter(ImageFilter.GaussianBlur(30)))
    return thumb


def render_frame(t):
    global MEM_THUMB
    if MEM_THUMB is None:
        MEM_THUMB = make_mem_thumb()
    rng = np.random.default_rng(int(t * 1000) + 21)
    i = shot_index(t)
    img, kind = SHOT_FUNCS[i](t)
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    if isinstance(kind, tuple):   # blend between present (cold) and memory (warm)
        k0, amt = kind
        a = grade(arr, "present")
        b = grade(arr, "memory")
        arr = a * amt + b * (1 - amt) if k0 == "present" else b * amt + a * (1 - amt)
        if k0 == "present" and SHOT_FUNCS[i] is s04:   # the tear ripple warms the frame
            arr = a * (1 - amt) + b * amt
    else:
        arr = grade(arr, kind)
    if kind == "memory" or (isinstance(kind, tuple) and kind[0] == "memory"):
        arr = bloom(arr, 0.4)
    # transitions
    if 9.05 <= t < 9.22:   # whip-pan into the feet shot
        k = 1 - (t - 9.05) / 0.17
        arr = m.motion_blur(arr, k)
    if 16.09 <= t < 16.26:
        k = 1 - (t - 16.09) / 0.17
        arr = m.motion_blur(arr, k)
    for ft, dur, strength in ((7.29, 0.1, 0.7), (14.25, 0.07, 0.9)):
        if ft <= t < ft + dur:
            arr = arr + (255 - arr) * strength * (1 - (t - ft) / dur)
    if 10.40 <= t < 10.55:
        arr *= 1 - (t - 10.40) / 0.15
    arr *= m.VIGNETTE ** 0.8
    grain = 5.0 if kind in ("memory", "dusk") else 3.4
    arr += rng.normal(0, grain, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    fade = clamp(t / 0.24)
    arr *= fade
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    draw_lyrics(out, t)
    return out.convert("RGB")


m.T = {"speed": T["speed"]}   # the road scenes scroll with her walk


def _work(i):
    return render_frame(i / FPS).tobytes()


def main():
    if "--frames" in sys.argv:
        for i in [int(v) for v in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            render_frame(i / FPS).save(os.path.join(HERE, f"_preview_{i:04d}.png"))
        return
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "12M", "-bufsize", "24M",
           "-pix_fmt", "yuv420p", SILENT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(round(DUR * FPS))
    with mp.get_context("fork").Pool(workers) as pool:
        for k, buf in enumerate(pool.imap(_work, range(n), chunksize=2)):
            proc.stdin.write(buf)
            if k % 60 == 0:
                print(f"frame {k}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", SILENT, "-i", AUDIO, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{DUR:.2f}", "-movflags", "+faststart", OUT], check=True)
    os.remove(SILENT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
