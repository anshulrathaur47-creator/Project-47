"""Ghalib / Parveen Shakir "जनाजा" reel (assets/music/ReelAudio-35687.mp3, 22.4 s).

  0.0  "मिर्जा गालिब कहते हैं": an old street at dusk, empty, the sun low at the end of the road
  2.1  "एक जनाजे की खातिर सारा जहां निकला": a funeral procession comes down the street, a white-shrouded
       bier with marigold garlands on four shoulders, a whole crowd behind it, petals falling
  5.2  "बस वो ना निकला": one house; its door stays shut
  6.3  "जिसकी खातिर जनाजा था": the procession passes right in front of that shut door
  8.0  "मगर परवीन शाकिर कहती हैं": inside, she sits on the floor against that same door, crying
 11.3  "ऐ सनम मैं कैसे आती तेरे जनाजे के पीछे": over her shoulder at the jaali window, the procession below
 14.7  (again) close on her face behind the jaali, eyes shut, tears; the procession walks away
 18.6  "एक मेरा जनाजा था तेरे जनाजे के पीछे": her own white ghost walks behind his bier; inside she rests
       her head on the door, closes her eyes, the lamp goes out

New character (the user wants a new one every reel): a young woman in a pale suit with a white dupatta
over her head (gold border), kajal and a nose pin. Lyrics are static: plain lines that cut on and off with
the words, no glow, no motion (user: "No animation in lyrics").
Rig and road scenes come from ../2026-11-16-remember-19-nov/make_19nov.py (via ../2026-11-20-shakal-sad).

Usage: python3 make_janaza.py [--frames 30,150,...] [--workers 4]
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
sys.path.insert(0, os.path.join(HERE, "..", "2026-11-20-shakal-sad"))
import make_shakal as sk  # noqa: E402

m = sk.m
clamp, smooth, lerp, ease_out, back_out, track, step = m.clamp, m.smooth, m.lerp, m.ease_out, m.back_out, m.track, m.step
W, H, FPS = 1080, 1920, 30
AUDIO = os.path.join(HERE, "..", "..", "assets", "music", "ReelAudio-35687.mp3")
OUT = os.path.join(HERE, "janaza.mp4")
SILENT = os.path.join(HERE, "_janaza_silent.mp4")
DUR = 22.40
K = m.K
proj, FOCAL = m.proj, m.FOCAL

# ==============================================================================================
# lyrics: static lines (start, end, text, highlighted words)
# ==============================================================================================
LINES = [
    (0.18, 2.05, "मिर्ज़ा ग़ालिब कहते हैं"),
    (2.08, 3.42, "एक जनाज़े की ख़ातिर"),
    (3.44, 5.18, "सारा जहाँ निकला"),
    (5.22, 6.26, "बस वो ना निकला"),
    (6.28, 8.00, "जिसकी ख़ातिर जनाज़ा था"),
    (8.05, 11.30, "मगर परवीन शाकिर कहती हैं"),
    (11.35, 12.96, "ऐ सनम मैं कैसे आती"),
    (12.98, 14.70, "तेरे जनाज़े के पीछे"),
    (14.72, 16.47, "ऐ सनम मैं कैसे आती"),
    (16.49, 18.60, "तेरे जनाज़े के पीछे"),
    (18.62, 19.86, "एक मेरा जनाज़ा था"),
    (19.88, 22.10, "तेरे जनाज़े के पीछे"),
]
GOLDEN_WORDS = ("जनाज़े", "जनाज़ा")
_line_cache = {}


def line_sprite(text, size=78):
    if text in _line_cache:
        return _line_cache[text]
    f = m.kfont(size)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    words = text.split(" ")
    space = probe.textlength(" ", font=f)
    widths = [probe.textlength(w, font=f) for w in words]
    total = sum(widths) + space * (len(words) - 1)
    asc, desc = f.getmetrics()
    pad = 30
    img = Image.new("RGBA", (int(total) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd, d = ImageDraw.Draw(shadow), ImageDraw.Draw(img)
    x = pad
    for w, wd in zip(words, widths):
        col = (255, 222, 160) if w in GOLDEN_WORDS else (246, 244, 240)
        sd.text((x + 3, pad + 4), w, font=f, fill=(0, 0, 0, 200))
        d.text((x, pad), w, font=f, fill=col + (255,), stroke_width=2, stroke_fill=(20, 16, 14, 255))
        x += wd + space
    out = shadow.filter(ImageFilter.GaussianBlur(6))
    out.alpha_composite(img)
    _line_cache[text] = out
    return out


def draw_lyrics(frame, t, occ):
    for idx, (a, b, text) in enumerate(LINES):
        if a <= t < b:
            spr = line_sprite(text)
            if spr.width > 1000:
                spr = spr.resize((1000, int(spr.height * 1000 / spr.width)), Image.LANCZOS)
            cy = m.choose_y(("j", idx), spr.width, spr.height, occ)
            frame.alpha_composite(spr, (int(540 - spr.width / 2), int(cy - spr.height / 2)))


m.Y_CANDIDATES = (1480, 330, 450)

# ==============================================================================================
# the woman (new character)
# ==============================================================================================
m.HAIR, m.HAIR_HI = (20, 18, 24), (70, 70, 90)
m.HOOD, m.HOOD_SH = (196, 204, 222), (160, 168, 190)
m.IRIS, m.IRIS_D = (120, 78, 44), (62, 38, 22)
CREAM, CREAM_SH, GOLD_B = (244, 240, 232), (214, 208, 198), (214, 172, 84)


def saw(t0, t1, period):
    return sk.saw(t0, t1, period)


SIT, STAND = 300, 0
T = dict(sk.T)
T.update({
    "walk": [(0, 0)], "speed": [(0, 0)], "swag": [(0, 0)], "laugh": [(0, 0)], "happy": [(0, 0)],
    "sink": [(0, SIT), (11.34, SIT), (11.35, STAND), (19.87, STAND), (19.88, SIT)],
    "slump": [(0, 0.6), (11.3, 0.6), (11.35, 0.2), (19.87, 0.2), (19.88, 0.7), (22.4, 0.9)],
    "head_dy": [(0, 12), (11.3, 12), (11.35, 0), (19.87, 0), (19.88, 6), (21.0, -6)],
    "tilt": [(0, -4), (9.5, 4), (11.3, 3), (11.35, 4), (19.87, 2), (19.88, -3), (21.2, -9)],
    "shake": [(0, 0.12), (11.3, 0.12), (11.35, 0.05), (19.87, 0.05), (19.88, 0.03)],
    "look": [(0, (0, 0.5)), (9.6, (-0.3, 0.4)), (11.35, (0.35, 0.25)), (19.87, (0.35, 0.25)), (19.88, (0, 0.2))],
    "lid": [(0, 0.55), (9.0, 0.7), (10.0, 0.45), (11.3, 0.5), (11.35, 0.45), (15.3, 0.5), (15.6, 1.0), (16.5, 1.0),
            (19.87, 1.0), (19.88, 0.45), (20.4, 0.55), (21.4, 1.0)],
    "brow": [(0, 1.0)],
    "tear": saw(0, 40, 1.3),
    "tear_a": [(0, 1)],
    "blush": [(0, 0)],
    "cry": [(0, 0.8), (11.3, 0.8), (11.35, 1.0), (19.87, 1.0), (19.88, 0.7), (22.4, 0.5)],
    "desat": [(0, 0.15), (8.0, 0.2), (19.88, 0.3), (22.4, 0.65)],
})
MOUTH = [(0, "cry"), (19.88, "frown"), (21.3, "flat")]
MOUTH_L, MOUTH_R = ("head", -26, 112), ("head", 26, 116)
LAP_L, LAP_R = ("hip", -88, -60), ("hip", 88, -60)
HAND_L = [(0, MOUTH_L), (10.6, MOUTH_L), (11.0, LAP_L), (11.35, ("hip", -122, -15)), (19.87, ("hip", -122, -15)),
          (19.88, LAP_L)]
HAND_R = [(0, MOUTH_R), (10.6, MOUTH_R), (11.0, LAP_R), (11.35, ("head", 165, 60)), (19.87, ("head", 165, 60)),
          (19.88, LAP_R)]
m.T, m.MOUTH, m.HAND_L, m.HAND_R = T, MOUTH, HAND_L, HAND_R
_base_head = sk._orig_head


def woman_head(t, p):
    p = dict(p)
    mouth = p["mouth"]
    if mouth == "cry":
        p["mouth"] = "none"
    if p["lid"] < 0.9 and sk.blink(t):
        p["lid"] = 1.0
    img = _base_head(t, p)
    pen = m.Pen(img, 0, 0, K)
    cx, cy = 180, 310
    LINE = m.LINE
    for sx in (-1, 1):   # kajal: heavier lash line with a wing
        ex, ey = cx + sx * 52, cy + 12
        if p["lid"] < 0.9:
            top = ey - 43 + p["lid"] * 78
            pen.line([(ex - sx * 20, top + 4), (ex + sx * 30, top + 4), (ex + sx * 46, top - 8)], LINE, 7)
            pen.line([(ex + sx * 22, top + 2), (ex + sx * 34, top - 12)], LINE, 4)
        else:
            pen.line([(ex + sx * 24, ey + 6), (ex + sx * 40, ey)], LINE, 5)
    pen.circle(cx + 10, cy + 60, 4.5, (235, 195, 90))   # nose pin
    if mouth == "cry":
        mx, my = cx, cy + 90
        wob = math.sin(t * 22) * 2.5
        top = [(mx + x, my + 10 - 10 * (1 - (x / 22) ** 2)) for x in range(-22, 23, 5)]
        bot = [(mx + x, my + 18 + wob * math.sin(x * 0.3) + 3 * (1 - (x / 22) ** 2)) for x in range(22, -23, -5)]
        pen.poly(top + bot, (120, 34, 50), LINE, 3)
    cry = p.get("cry", 0)
    if cry > 0.01:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        lp = m.Pen(lay, 0, 0, K)
        a = int(200 * cry)
        for sx in (-1, 1):
            x0, y0 = cx + sx * 56, cy + 44
            pts = [(x0 + sx * 6 * (k / 6) + 2 * math.sin(t * 6 + k + sx), y0 + 13 * k) for k in range(7)]
            lp.line(pts, (170, 215, 255, a // 2), 7)
            for ph in (0.0, 0.5):
                u = (t * 0.8 + ph + (0.25 if sx > 0 else 0)) % 1.0
                tx, ty = x0 + sx * 6 * u, y0 + 80 * u
                lp.poly([(tx, ty - 15), (tx - 7, ty), (tx + 7, ty)], (165, 210, 255, a))
                lp.circle(tx, ty + 2, 7, (165, 210, 255, a))
        img.alpha_composite(lay)
    # dupatta over the head (covers the hair, frames the face)
    outer = [(cx - 172, cy + 190), (cx - 180, cy + 40)]
    outer += [(cx + 192 * math.cos(math.radians(a_)), cy - 20 + 205 * math.sin(math.radians(a_))) for a_ in range(190, 351, 8)]
    outer += [(cx + 180, cy + 40), (cx + 172, cy + 190)]
    inner = [(cx + 138, cy + 190), (cx + 134, cy + 10)]
    inner += [(cx + 134 * math.cos(math.radians(a_)), cy - 10 + 112 * math.sin(math.radians(a_))) for a_ in range(350, 189, -8)]
    inner += [(cx - 134, cy + 10), (cx - 138, cy + 190)]
    pen.poly(outer + inner, CREAM, LINE, 3)
    pen.line(inner, GOLD_B, 7)
    for k in (-1, 1):   # folds
        pen.line([(cx + k * 160, cy - 60), (cx + k * 158, cy + 180)], CREAM_SH, 5)
    return img


m.draw_head = woman_head
_sk_char = m.draw_character
VISIBLE = [(8.05, 11.35), (14.72, 16.49), (19.88, 22.4)]


def draw_character(t):
    img, origin, head = _sk_char(t)
    pen = m.Pen(img, origin[0], origin[1], K)
    hx, hy = head
    for sx in (-1, 1):   # dupatta falling over the shoulders
        drape = [(hx + sx * 140, hy + 120), (hx + sx * 178, hy + 140), (hx + sx * 196, hy + 330), (hx + sx * 176, hy + 470),
                 (hx + sx * 110, hy + 470), (hx + sx * 120, hy + 300)]
        pen.poly(drape, CREAM, m.LINE, 3)
        pen.line([(hx + sx * 176, hy + 470), (hx + sx * 110, hy + 470)], GOLD_B, 8)
        pen.line([(hx + sx * 160, hy + 200), (hx + sx * 150, hy + 440)], CREAM_SH, 5)
    bib = [(hx - 120, hy + 300), (hx + 120, hy + 300), (hx + 112, hy + 420), (hx, hy + 470), (hx - 112, hy + 420)]
    pen.poly(bib, CREAM, m.LINE, 3)
    pen.line([(hx - 112, hy + 420), (hx, hy + 470), (hx + 112, hy + 420)], GOLD_B, 7)
    return img, origin, head


m.draw_character = draw_character

# ==============================================================================================
# the procession (perspective, drawn into the street scene)
# ==============================================================================================
rnd = random.Random(12)
CROWD = [(rnd.uniform(-2.6, 2.6), rnd.uniform(2.6, 16.0), rnd.uniform(0, 6.28), rnd.uniform(0.92, 1.08)) for _ in range(46)]
CROWD = [c for c in CROWD if not (abs(c[0]) < 0.9 and c[1] < 3.0)]


def person_at(d, x, z, ph, size, t, col=(14, 12, 20), a=240, walk=True):
    if z < 2.6:
        return
    sc = 1.7 * size * FOCAL / z / 980
    sx, base = proj(x, 0, z)
    bob = abs(math.sin(t * 5 + ph)) * 8 * sc if walk else 0
    sk.silhouette(d, sx, base, sc, a=a, bob=bob)


def bier(d, x, z, t):
    """Four carriers and a white-shrouded bier with marigold garlands, pointing down the street."""
    zf, zb = z, z + 2.1
    for dx, dz in ((-0.42, 0), (0.42, 0), (-0.42, 2.1), (0.42, 2.1)):
        pass
    items = []
    for dx, dz in ((-0.42, 2.1), (0.42, 2.1)):
        items.append(("p", x + dx, z + dz))
    items.append(("b", 0, 0))
    for dx, dz in ((-0.42, 0), (0.42, 0)):
        items.append(("p", x + dx, z + dz))
    for kind, px, pz in items:
        if kind == "p":
            person_at(d, px, pz, px * 3, 1.0, t)
        else:
            y0, y1 = 1.48, 1.62
            top = [proj(x - 0.42, y1, zb), proj(x + 0.42, y1, zb), proj(x + 0.42, y1, zf), proj(x - 0.42, y1, zf)]
            d.polygon([proj(x - 0.42, y0, zf), proj(x + 0.42, y0, zf), proj(x + 0.42, y1, zf), proj(x - 0.42, y1, zf)],
                      fill=(90, 66, 44, 255))
            d.polygon(top, fill=(232, 228, 220, 255))
            # the shroud: a soft mound over the bier
            mound = [proj(x - 0.36, y1, zb - 0.1)]
            for k in range(9):
                u = k / 8
                mound.append(proj(x, y1 + 0.28 * math.sin(math.pi * u) ** 0.7, lerp(zb - 0.1, zf + 0.1, u)))
            mound.append(proj(x + 0.36, y1, zf + 0.1))
            d.polygon(mound + [proj(x - 0.36, y1, zf + 0.1)], fill=(246, 244, 240, 255))
            d.polygon([proj(x - 0.42, y1, zf), proj(x + 0.42, y1, zf), proj(x + 0.36, y1 + 0.12, zf + 0.1),
                       proj(x - 0.36, y1 + 0.12, zf + 0.1)], fill=(236, 232, 226, 255))
            for k in range(12):   # marigold garland along the shroud
                u = k / 11
                gx, gy = proj(x + 0.3 * math.cos(u * 6.28), y1 + 0.18, lerp(zb - 0.2, zf + 0.2, u))
                r = max(2, FOCAL * 0.05 / lerp(zb, zf, u))
                d.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(255, 150, 30, 255) if k % 2 else (255, 196, 40, 255))
            for k in range(6):   # red rose petals on the shroud
                u = (k + 0.5) / 6
                gx, gy = proj(x + 0.12 * math.sin(k * 2.3), y1 + 0.24, lerp(zb - 0.3, zf + 0.3, u))
                r = max(2, FOCAL * 0.035 / lerp(zb, zf, u))
                d.ellipse([gx - r, gy - r * 0.7, gx + r, gy + r * 0.7], fill=(190, 20, 50, 255))


def ghost_at(d, x, z, t, a):
    """Her white ghost in a dupatta, walking away down the street."""
    sc = 1.62 * FOCAL / z / 980
    sx, base = proj(x, 0, z)
    bob = abs(math.sin(t * 4)) * 6 * sc
    top = base - 980 * sc - bob
    col = (236, 240, 255, a)
    d.ellipse([sx - 62 * sc, top - 10 * sc, sx + 62 * sc, top + 120 * sc], fill=col)
    d.polygon([(sx - 70 * sc, top + 60 * sc), (sx + 70 * sc, top + 60 * sc), (sx + 120 * sc, top + 520 * sc),
               (sx + 90 * sc, base), (sx - 90 * sc, base), (sx - 120 * sc, top + 520 * sc)], fill=col)
    d.line([(sx - 120 * sc, top + 520 * sc), (sx + 120 * sc, top + 520 * sc)], fill=(240, 210, 140, a), width=max(2, int(10 * sc)))


def procession_layer(t, z_head, ghost=None):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    things = [(z_head + 1.05, "bier", 0)]
    for i, (x, dz, ph, size) in enumerate(CROWD):
        things.append((z_head + dz, "p", i))
    if ghost:
        things.append((ghost[0], "g", 0))
    for z, kind, i in sorted(things, reverse=True):
        if not (2.6 < z < 75):
            continue
        if kind == "bier":
            bier(d, 0.0, z_head, t)
        elif kind == "p":
            x, dz, ph, size = CROWD[i]
            person_at(d, x, z, ph, size, t)
        else:
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ghost_at(ImageDraw.Draw(glow), -0.2, z, t, 255)
            g2 = glow.filter(ImageFilter.GaussianBlur(14))
            g2.putalpha(g2.getchannel("A").point(lambda v: int(v * ghost[1])))
            img.alpha_composite(g2)
            gl = glow.copy()
            gl.putalpha(glow.getchannel("A").point(lambda v: int(v * 0.6 * ghost[1])))
            img.alpha_composite(gl)
            d = ImageDraw.Draw(img)
    return img


def z_head_at(t):
    if t < 5.22:          # comes towards us down the street
        return lerp(30, 8.0, smooth((t - 2.08) / 3.2))
    if t < 14.72:         # seen from her window, walking on
        return lerp(9.0, 15.0, (t - 11.35) / 3.4)
    return lerp(13.0, 26.0, clamp((t - 16.49) / 3.4))   # walking away


# ==============================================================================================
# places
# ==============================================================================================
# (start, kind) ; kinds: dusk street, house outside, inside by the door, window (over the shoulder),
# jaali close-up, night street
SCENES = [(0.0, "street_dusk"), (5.22, "house_ext"), (8.05, "house_int"), (11.35, "window_ots"), (14.72, "jaali"),
          (16.49, "street_night"), (19.88, "house_int")]


def scene_at(t):
    return step(SCENES, t)


m.LIGHT = [
    (0.0, ((110, 70, 90), (255, 160, 110), (1.04, 0.95, 0.88))),
    (5.21, ((110, 70, 90), (255, 160, 110), (1.04, 0.95, 0.88))),
    (5.22, ((70, 54, 70), (170, 120, 100), (1.0, 0.94, 0.88))),
    (8.04, ((70, 54, 70), (170, 120, 100), (1.0, 0.94, 0.88))),
    (8.05, ((30, 22, 20), (60, 44, 36), (1.02, 0.94, 0.84))),
    (11.34, ((30, 22, 20), (60, 44, 36), (1.02, 0.94, 0.84))),
    (11.35, ((16, 18, 34), (40, 44, 70), (0.92, 0.95, 1.06))),
    (19.87, ((8, 10, 24), (30, 36, 60), (0.88, 0.92, 1.08))),
    (19.88, ((26, 20, 18), (50, 40, 34), (0.98, 0.92, 0.86))),
    (22.4, ((26, 20, 18), (50, 40, 34), (0.9, 0.9, 0.9))),
]
m.SHOTS = [
    (0.00, 2.08, (1.10, 0, -140, 0), (1.00, 0, -60, 0), "fade"),          # empty dusk street
    (2.08, 3.44, (1.00, 0, -60, 0), (1.06, 0, -80, 0), "cut"),            # the procession appears
    (3.44, 5.22, (1.25, 0, -20, -3), (1.35, 0, -30, -3), "cut"),          # the whole crowd, petals
    (5.22, 6.28, (1.00, 0, -40, 0), (1.22, 0, -60, 0), "dip"),            # the shut door
    (6.28, 8.05, (1.10, 0, -60, 0), (1.14, 0, -60, 0), "cut"),            # passing the shut door
    (8.05, 9.60, (1.00, 0, -40, 0), (1.12, 0, -40, 0), "flash"),          # inside: she sits against it
    (9.60, 11.35, (1.85, 0, 10, 0), (2.10, 0, 14, 0), "cut"),             # crying, hand over her mouth
    (11.35, 14.72, (1.00, 0, -40, 0), (1.00, 0, -40, 0), "dip"),          # over her shoulder (custom)
    (14.72, 16.49, (2.50, 0, -300, 0), (2.75, 0, -305, 0), "cut"),        # behind the jaali, eyes shut
    (16.49, 18.62, (1.00, 0, -60, 0), (1.10, 0, -90, 0), "cut"),          # the procession walks away
    (18.62, 19.88, (1.15, 0, -90, 0), (1.25, 0, -110, 0), "cut"),         # her ghost follows
    (19.88, 22.40, (2.30, 0, 6, 0), (2.70, 0, 14, -4), "dip"),            # head on the door, lamp out
]
m.DURATION = DUR


def wood_door(d, x0, y0, x1, y1, shut=1.0):
    d.rectangle([x0 - 26, y0 - 26, x1 + 26, y1], fill=(70, 50, 38, 255))
    mid = (x0 + x1) / 2
    for a, b in ((x0, mid), (mid, x1)):
        d.rectangle([a + 4, y0, b - 4, y1], fill=(110, 72, 44, 255), outline=(60, 40, 26, 255), width=6)
        for yy in np.linspace(y0 + 60, y1 - 60, 6):
            for xx in np.linspace(a + 40, b - 40, 3):
                d.ellipse([xx - 8, yy - 8, xx + 8, yy + 8], fill=(60, 50, 40, 255))
    d.line([(mid, y0), (mid, y1)], fill=(40, 26, 18, 255), width=8)
    d.rectangle([mid - 40, (y0 + y1) / 2 - 10, mid + 40, (y0 + y1) / 2 + 10], fill=(150, 130, 90, 255))   # latch


def house_ext(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(0, 1700, 8):
        f = y / 1700
        d.rectangle([0, y, W, y + 8], fill=(int(lerp(150, 118, f)), int(lerp(120, 92, f)), int(lerp(96, 74, f)), 255))
    for k in range(40):   # weathered plaster
        r2 = random.Random(k)
        x, y = r2.uniform(0, W), r2.uniform(0, 1600)
        d.ellipse([x - 40, y - 14, x + 40, y + 14], fill=(130, 100, 80, 90))
    wood_door(d, 330, 860, 750, 1640)
    d.arc([300, 760, 780, 960], 180, 360, fill=(90, 66, 50, 255), width=26)
    # jharokha window above, dim lamp light inside
    d.rectangle([370, 300, 710, 640], fill=(40, 28, 22, 255))
    d.rectangle([390, 320, 690, 620], fill=(150, 100, 50, 255))
    for k in range(-6, 8):
        d.line([(390 + k * 50, 320), (390 + k * 50 + 300, 620)], fill=(60, 40, 28, 255), width=8)
        d.line([(690 - k * 50, 320), (690 - k * 50 - 300, 620)], fill=(60, 40, 28, 255), width=8)
    d.rectangle([370, 300, 710, 640], outline=(80, 56, 40, 255), width=22)
    d.rectangle([340, 640, 740, 672], fill=(96, 70, 52, 255))
    # lantern by the door
    d.line([(860, 760), (860, 840)], fill=(40, 30, 24, 255), width=5)
    d.rectangle([836, 840, 884, 920], fill=(255, 200, 110, 255), outline=(50, 36, 26, 255), width=5)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([760, 760, 960, 1000], fill=(255, 190, 100, 90))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(30)))
    d.rectangle([0, 1640, W, H], fill=(84, 70, 60, 255))     # street
    for x in range(0, W, 140):
        d.line([(x, 1640), (x - 80, H)], fill=(70, 58, 50, 255), width=3)
    return img


def house_int(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(0, 1700, 8):
        f = y / 1700
        d.rectangle([0, y, W, y + 8], fill=(int(lerp(70, 44, f)), int(lerp(52, 32, f)), int(lerp(44, 28, f)), 255))
    wood_door(d, 290, 480, 790, 1640)
    d.rectangle([0, 1640, W, H], fill=(60, 30, 30, 255))      # rug
    d.rectangle([60, 1680, 1020, 1880], outline=(150, 100, 50, 255), width=8)
    # a diya in a wall niche (left), it goes out at the very end
    d.rounded_rectangle([60, 900, 210, 1080], radius=60, fill=(36, 24, 20, 255))
    d.chord([105, 1030, 165, 1066], 0, 180, fill=(170, 100, 50, 255))
    on = 1 - smooth((t - 21.3) / 0.35) if t > 19.88 else 1.0
    if on > 0.02:
        fl = 1 + 0.15 * math.sin(t * 17) + 0.1 * math.sin(t * 31)
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([20, 880, 250, 1110], fill=(255, 180, 90, int(150 * on)))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(34)))
        d.polygon([(135, 1036 - 40 * fl * on), (124, 1030), (135, 1040), (146, 1030)], fill=(255, 210, 90, int(255 * on)))
    elif t < 22.4:   # smoke after it goes out
        u = clamp((t - 21.65) / 0.8)
        for k in range(6):
            v = k / 6
            d.ellipse([130 + 12 * math.sin(v * 6 + t * 3), 1020 - v * 140 * (0.4 + u), 140 + 12 * math.sin(v * 6 + t * 3),
                       1030 - v * 140 * (0.4 + u)], fill=(200, 200, 210, int(110 * (1 - v) * (1 - u))))
    return img


def jaali_bg(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 8):
        f = y / H
        d.rectangle([0, y, W, y + 8], fill=(int(lerp(40, 22, f)), int(lerp(32, 20, f)), int(lerp(36, 26, f)), 255))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([700, 300, 1000, 600], fill=(255, 180, 100, 130))   # a lamp behind her
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(50)))
    return img


def street_scene_env(t, kind, sky_bot):
    base = m.draw_env(t, "golden" if kind == "street_dusk" else "street", sky_bot)
    if kind == "street_dusk" and t >= 2.08:
        base.alpha_composite(procession_layer(t, z_head_at(t)))
    if kind == "street_night":
        ghost = None
        if t >= 18.62:
            ghost = (lerp(6.5, 13.0, (t - 18.62) / 1.3), clamp((t - 18.62) / 0.4))
        base.alpha_composite(procession_layer(t, z_head_at(t), ghost))
    return base


def env_for(t, kind, sky_bot):
    if kind in ("street_dusk", "street_night"):
        return street_scene_env(t, kind, sky_bot)
    if kind == "house_ext":
        return house_ext(t)
    if kind == "house_int":
        return house_int(t)
    return jaali_bg(t)


# ==============================================================================================
# props in front (world space)
# ==============================================================================================
def side_bier(d, x, base, s):
    """The procession passing sideways in front of the house: carriers, bier and shroud."""
    for k, dx in enumerate((-260, -120, 120, 260)):
        sk.silhouette(d, x + dx * s, base, 1.0 * s, a=245, bob=abs(math.sin((x + dx) * 0.03)) * 8)
    top = base - 840 * s
    d.rectangle([x - 330 * s, top, x + 330 * s, top + 26 * s], fill=(90, 66, 44, 255))
    d.chord([x - 300 * s, top - 120 * s, x + 300 * s, top + 60 * s], 180, 360, fill=(246, 244, 240, 255))
    for k in range(15):
        u = k / 14
        gx = x - 280 * s + 560 * s * u
        gy = top - 20 * s - 70 * s * math.sin(math.pi * u)
        d.ellipse([gx - 12 * s, gy - 12 * s, gx + 12 * s, gy + 12 * s], fill=(255, 150, 30, 255) if k % 2 else (255, 196, 40, 255))


def front_props(layer, t, kind):
    d = ImageDraw.Draw(layer)
    if kind == "house_ext" and t >= 6.28:      # passing right in front of the shut door
        u = (t - 6.28) / 1.77
        x = lerp(1500, -420, u)
        for k, dx in enumerate((470, 690, 900)):   # mourners following
            sk.silhouette(d, x + dx, 1760, 0.78, a=240, bob=abs(math.sin(t * 5 + k)) * 8)
        side_bier(d, x, 1760, 0.82)
        for k, dx in enumerate((-430, -620)):
            sk.silhouette(d, x + dx, 1760, 0.78, a=240, bob=abs(math.sin(t * 5 + k + 2)) * 8)
    if kind == "house_int":                    # her dupatta pooled over her knees
        d.ellipse([400, 1360, 540, 1500], fill=CREAM)
        d.ellipse([540, 1360, 680, 1500], fill=CREAM)
        d.polygon([(330, 1460), (750, 1460), (820, 1720), (260, 1720)], fill=CREAM)
        d.line([(260, 1716), (820, 1716)], fill=GOLD_B, width=10)
        for x in (420, 540, 660):
            d.line([(x, 1470), (x + (x - 540) * 0.3, 1700)], fill=CREAM_SH, width=5)
    if kind == "jaali":                        # the window lattice between us and her
        for k in range(-8, 14):
            x0 = -400 + k * 150
            d.line([(x0, 0), (x0 + 1100, 1920)], fill=(46, 30, 22, 235), width=16)
            d.line([(x0 + 1100, 0), (x0, 1920)], fill=(46, 30, 22, 235), width=16)


PETALS = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(60, 140), rnd.uniform(0, 6.28), rnd.random() < 0.6)
          for _ in range(46)]


def fx_layer(t, kind):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    petals = (3.0 < t < 8.05) or (kind in ("street_night",))
    if petals:
        for x, y, sp, ph, red in PETALS:
            yy = (y + t * sp) % H
            xx = x + 40 * math.sin(t * 1.3 + ph)
            col = (200, 26, 56) if red else (255, 160, 40)
            a = 210
            rot = t * 2 + ph
            d.ellipse([xx - 9 * abs(math.cos(rot)) - 3, yy - 6, xx + 9 * abs(math.cos(rot)) + 3, yy + 6], fill=col + (a,))
    for x, y, s_, sp, ph in m.DUST:
        py_ = (y - t * sp * 0.5) % H
        px_ = x + 24 * math.sin(t * 0.7 + ph)
        d.ellipse([px_ - s_, py_ - s_, px_ + s_, py_ + s_], fill=(230, 220, 255, 36))
    return layer.filter(ImageFilter.GaussianBlur(1.0))


# ==============================================================================================
# composition
# ==============================================================================================
def in_visible(t):
    return any(a <= t < b for a, b in VISIBLE)


def scene_frame(t, cam, kind):
    top, bot, _ = m.light_at(t)
    sky = np.array(top, np.float32) * (1 - m.GRAD_Y) + np.array(bot, np.float32) * m.GRAD_Y
    frame = Image.fromarray(np.broadcast_to(sky, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    frame.alpha_composite(m.cam_transform(env_for(t, kind, bot), 0.9, cam))
    char_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    head = (540, 1064)
    if kind in ("house_int", "jaali") and in_visible(t):
        char_img, origin, head = m.draw_character(t)
        char_l = m.cam_transform(char_img, 1.0, cam, origin, K)
        frame.alpha_composite(char_l)
    props = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    front_props(props, t, kind)
    pl = m.cam_transform(props.filter(ImageFilter.GaussianBlur(0.7 if kind != "jaali" else 3.0)), 1.0, cam)
    frame.alpha_composite(pl)
    frame.alpha_composite(m.cam_transform(fx_layer(t, kind), 1.1, cam))
    occ_c = np.asarray(char_l.getchannel("A").resize((W // 8, H // 8))) > 40
    occ_o = np.asarray(pl.getchannel("A").resize((W // 8, H // 8))) > 40
    return frame, (occ_c.astype(np.float32), occ_o.astype(np.float32) * (0.0 if kind == "jaali" else 1.0))


def back_woman(d, hx, hy, t, reach):
    """Her back, dupatta over her head and shoulders, one hand up on the jaali."""
    body = (150, 156, 176, 255)
    d.polygon([(hx - 330, H), (hx - 300, hy + 420), (hx - 170, hy + 300), (hx + 170, hy + 300), (hx + 300, hy + 420),
               (hx + 330, H)], fill=body)
    if reach > 0.01:
        sh = (hx + 210, hy + 380)
        tx, ty = lerp(hx + 260, 640, reach), lerp(hy + 700, 860, reach)
        el = (lerp(sh[0], tx, 0.5) + 60, lerp(sh[1], ty, 0.5) + 60)
        d.line([sh, el, (tx, ty)], fill=body, width=86, joint="curve")
        d.ellipse([tx - 40, ty - 50, tx + 40, ty + 40], fill=(200, 160, 140, 255))
        for k in range(3):
            d.arc([tx - 46, ty + 20 + k * 10, tx + 46, ty + 60 + k * 10], 0, 180, fill=(220, 40, 70, 255), width=6)
    cream = CREAM + (255,)
    d.ellipse([hx - 230, hy - 250, hx + 230, hy + 230], fill=cream)
    d.polygon([(hx - 228, hy - 20), (hx + 228, hy - 20), (hx + 320, hy + 560), (hx + 300, H), (hx - 300, H),
               (hx - 320, hy + 560)], fill=cream)
    for k in (-140, -40, 60, 160):
        d.line([(hx + k * 0.6, hy - 120), (hx + k * 1.4, H)], fill=CREAM_SH + (255,), width=8)
    d.line([(hx - 320, hy + 560), (hx + 320, hy + 560)], fill=GOLD_B + (255,), width=14)


def window_ots(t):
    """Over her shoulder at the jaali window: the procession in the street below."""
    z = 1 + 0.07 * smooth((t - 11.35) / 3.37)
    top, bot, _ = m.light_at(t)
    sky = np.array(top, np.float32) * (1 - m.GRAD_Y) + np.array(bot, np.float32) * m.GRAD_Y
    street = Image.fromarray(np.broadcast_to(sky, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    env = m.draw_env(t, "street", bot)
    env.alpha_composite(procession_layer(t, z_head_at(t)))
    street.alpha_composite(env)
    street.alpha_composite(fx_layer(t, "street_night"))
    wx0, wy0, wx1, wy1 = 170, 330, 910, 1300
    view = street.crop((60, 360, 1020, 1620)).resize((wx1 - wx0, wy1 - wy0), Image.LANCZOS)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(out)
    for y in range(0, H, 8):
        f = y / H
        d.rectangle([0, y, W, y + 8], fill=(int(lerp(60, 34, f)), int(lerp(44, 26, f)), int(lerp(38, 24, f)), 255))
    mask = Image.new("L", view.size, 0)
    md = ImageDraw.Draw(mask)
    md.rectangle([0, 200, view.width, view.height], fill=255)
    md.ellipse([0, 0, view.width, 400], fill=255)
    out.paste(view, (wx0, wy0), mask)
    jl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    jd = ImageDraw.Draw(jl)
    for k in range(-10, 16):
        x0 = wx0 - 600 + k * 90
        jd.line([(x0, wy0), (x0 + 970, wy1)], fill=(52, 34, 24, 255), width=11)
        jd.line([(x0 + 970, wy0), (x0, wy1)], fill=(52, 34, 24, 255), width=11)
    jm = Image.new("L", (W, H), 0)
    jmd = ImageDraw.Draw(jm)
    jmd.rectangle([wx0, wy0 + 200, wx1, wy1], fill=255)
    jmd.ellipse([wx0, wy0, wx1, wy0 + 400], fill=255)
    jl.putalpha(Image.fromarray(np.minimum(np.asarray(jl.getchannel("A")), np.asarray(jm))))
    out.alpha_composite(jl)
    d.arc([wx0 - 20, wy0 - 20, wx1 + 20, wy0 + 420], 180, 360, fill=(84, 58, 40, 255), width=36)
    d.line([(wx0 - 20, wy0 + 200), (wx0 - 20, wy1 + 20)], fill=(84, 58, 40, 255), width=36)
    d.line([(wx1 + 20, wy0 + 200), (wx1 + 20, wy1 + 20)], fill=(84, 58, 40, 255), width=36)
    d.rectangle([wx0 - 60, wy1, wx1 + 60, wy1 + 60], fill=(96, 68, 48, 255))
    # cool light spilling in
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).polygon([(wx0, wy1), (wx1, wy1), (wx1 + 200, H), (wx0 - 200, H)], fill=(120, 140, 200, 50))
    out.alpha_composite(g.filter(ImageFilter.GaussianBlur(40)))
    fig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    reach = smooth((t - 11.6) / 0.8)
    back_woman(ImageDraw.Draw(fig), 300, 1240 + 6 * math.sin(t * 2), t, reach)
    out.alpha_composite(fig.filter(ImageFilter.GaussianBlur(1.6)))
    if z > 1.001:
        cw, ch = W / z, H / z
        out = out.crop((560 - cw / 2, 900 - ch / 2, 560 + cw / 2, 900 + ch / 2)).resize((W, H), Image.BILINEAR)
    occ_c = np.asarray(fig.getchannel("A").resize((W // 8, H // 8))) > 40
    return out, (occ_c.astype(np.float32), np.zeros_like(occ_c, np.float32))


def render_frame(t):
    rng = np.random.default_rng(int(t * 1000) + 3)
    _, _, tint = m.light_at(t)
    kind = scene_at(t)
    if kind == "window_ots":
        frame, occ = window_ots(t)
    else:
        frame, occ = scene_frame(t, m.camera_at(t), kind)
    blur, bright, flash = m.transition_fx(t)
    arr = np.asarray(frame.convert("RGB")).astype(np.float32) * np.array(tint, np.float32)
    de = track(T["desat"], t)
    if de > 0.01:
        lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
        arr = arr * (1 - de) + lum[:, :, None] * de
    if flash > 0.01:
        arr = arr + (255 - arr) * flash * 0.8
    arr *= m.VIGNETTE * bright
    arr += rng.normal(0, 3.6, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    fade = min(clamp(t / 0.4), clamp((DUR - t) / 1.0))
    arr *= fade
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    if fade > 0.3:
        draw_lyrics(out, t, occ)
    return out.convert("RGB")


def _work(i):
    return render_frame(i / FPS).tobytes()


def main():
    if "--frames" in sys.argv:
        for i in [int(v) for v in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            render_frame(i / FPS).save(os.path.join(HERE, f"_preview_{i:04d}.png"))
        return
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "10M",
           "-bufsize", "20M", "-pix_fmt", "yuv420p", SILENT]
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
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={DUR - 0.8:.2f}:d=0.8",
                    "-t", f"{DUR:.2f}", "-movflags", "+faststart", OUT], check=True)
    os.remove(SILENT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
