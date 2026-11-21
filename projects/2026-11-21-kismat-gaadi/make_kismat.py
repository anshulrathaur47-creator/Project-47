""""किस्मत की गाड़ी" reel (assets/music/ReelAudio-31260.mp3, 18.6 s).

A chai boy who works when he should be playing:
  0.0  park at sunset: kids play cricket and fly kites; he stands with his tea kettle, watching
  2.7  "मस्ती": close-up, a dream bubble of him batting pops
  3.4  "सैर सपाटा": kids ride past on bicycles with balloons; he looks down at his kettle
  5.1  night at the dhaba: he scrubs a pile of dishes, sweating
  7.5  "घड़ी का कांटा": the wall clock spins hours away; he nods off
  9.1  "अपनी किस्मत की गाड़ी की": sunset street, he hauls an old handcart of sacks; feet shot
 11.8  "खस्ता हालत है": a wheel wobbles off, the cart tips, sacks spill
 13.9  (again) night rain: he sits by the broken cart
 16.4  close-up: he wipes tears and rain with his gamchha, looks up
 18.1  "ओ रे": pull back, alone under a street lamp, fade out

New character (a new one every reel): a teenage chai boy, darker skin, messy brown hair, mustard shirt,
red-checked gamchha round his neck, dust on his cheeks. Lyrics are plain static lines (no animation),
like the last reel. Rig and road scenes come from the 19 Nov engine (via ../2026-11-20-shakal-sad).

Usage: python3 make_kismat.py [--frames 30,150,...] [--workers 4]
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
AUDIO = os.path.join(HERE, "..", "..", "assets", "music", "ReelAudio-31260.mp3")
OUT = os.path.join(HERE, "kismat.mp4")
SILENT = os.path.join(HERE, "_kismat_silent.mp4")
DUR = 18.58
K = m.K
proj, FOCAL = m.proj, m.FOCAL
BEAT0, BEAT = 0.07, 0.58

# ==============================================================================================
# lyrics: plain static lines
# ==============================================================================================
LINES = [
    (0.66, 2.68, "जिस उम्र में शोभा देते"),
    (2.70, 5.08, "मस्ती, सैर सपाटा"),
    (5.12, 7.46, "उस उम्र को ना बुरा है"),
    (7.50, 9.10, "यूं घड़ी का कांटा"),
    (9.14, 11.78, "अपनी किस्मत की गाड़ी की"),
    (11.82, 13.88, "खस्ता हालत है"),
    (13.92, 16.40, "अपनी किस्मत की गाड़ी की"),
    (16.42, 18.10, "खस्ता हालत है"),
    (18.12, 18.58, "ओ रे"),
]
GOLDEN_WORDS = ("किस्मत", "घड़ी", "मस्ती,")
_line_cache = {}


def line_sprite(text, size=80):
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
        col = (255, 214, 130) if w in GOLDEN_WORDS else (248, 246, 240)
        sd.text((x + 3, pad + 4), w, font=f, fill=(0, 0, 0, 210))
        d.text((x, pad), w, font=f, fill=col + (255,), stroke_width=2, stroke_fill=(24, 18, 12, 255))
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
            shot = max(i for i, s_ in enumerate(m.SHOTS) if s_[0] <= t)
            cy = m.choose_y(("k", idx, shot), spr.width, spr.height, occ)
            frame.alpha_composite(spr, (int(540 - spr.width / 2), int(cy - spr.height / 2)))


m.Y_CANDIDATES = (1480, 330, 450)

# ==============================================================================================
# the chai boy (new character)
# ==============================================================================================
m.SKIN, m.SKIN_SH = (222, 170, 132), (196, 144, 110)
m.HAIR, m.HAIR_HI = (48, 32, 24), (110, 80, 60)
m.HOOD, m.HOOD_SH = (212, 150, 58), (168, 112, 40)
m.PANTS = (92, 66, 48)
m.IRIS, m.IRIS_D = (110, 72, 42), (58, 36, 20)
GAMCHHA, GAMCHHA_D = (196, 40, 44), (140, 24, 30)


def saw(t0, t1, period):
    return sk.saw(t0, t1, period)


SQUAT, SIT = 230, 300
T = dict(sk.T)
T.update({
    "laugh": [(0, 0)], "happy": [(0, 0)], "shake": [(0, 0)], "swag": [(0, 0)],
    "walk": [(0, 0), (9.13, 0), (9.14, 1), (12.4, 1), (12.6, 0)],
    "speed": [(0, 0), (9.13, 0), (9.14, 1.0), (12.4, 1.0), (12.6, 0)],
    "sink": [(0, 0), (5.11, 0), (5.12, SQUAT), (9.13, SQUAT), (9.14, 0), (13.91, 0), (13.92, SIT)],
    "slump": [(0, 0.1), (3.4, 0.1), (4.6, 0.35), (5.11, 0.35), (5.12, 0.4), (8.4, 0.5), (9.1, 0.7), (9.14, 0.35),
              (12.4, 0.35), (12.6, 0.1), (13.9, 0.2), (13.92, 0.8), (16.4, 0.8), (16.6, 0.5)],
    "head_dy": [(0, 0), (4.4, 0), (4.8, 14), (5.11, 14), (5.12, 18), (8.42, 18), (8.6, 30), (8.85, 10), (9.0, 34),
                (9.14, 10), (12.48, 10), (12.6, -6), (13.9, -6), (13.92, 30), (16.4, 30), (16.6, -14)],
    "tilt": [(0, 0), (2.7, 4), (3.4, 4), (4.0, -4), (5.1, -4), (5.12, 0), (8.4, 0), (8.7, 8), (9.1, -6), (9.14, 0),
             (12.48, 0), (12.6, -6), (13.9, -6), (13.92, -4), (16.4, -4), (16.6, 3)],
    "look": [(0, (0.4, -0.1)), (2.0, (-0.4, -0.1)), (2.7, (0.3, -0.25)), (3.44, (-0.7, 0)), (4.3, (0.7, 0)),
             (4.6, (0, 0.8)), (5.12, (0, 0.7)), (9.14, (0, 0.1)), (12.48, (0.75, 0.1)), (13.92, (0, 0.6)),
             (16.42, (0, 0.3)), (17.3, (0, -0.9))],
    "lid": [(0, 0), (4.6, 0), (4.8, 0.3), (5.12, 0.4), (8.42, 0.5), (8.7, 0.95), (8.85, 0.5), (9.0, 1.0),
            (9.14, 0.3), (12.48, 0.3), (12.55, 0), (13.9, 0), (13.92, 0.55), (16.42, 0.5), (17.3, 0.3)],
    "brow": [(0, 0.5), (2.7, 0.3), (3.4, 0.6), (5.12, 0.8), (12.5, 0.8), (12.55, 0.4), (13.9, 0.6), (13.92, 1.0)],
    "tear": saw(13.92, 40, 1.3),
    "tear_a": [(0, 0), (4.4, 0), (4.8, 0.6), (5.1, 0), (13.9, 0), (14.4, 1), (40, 1)],
    "blush": [(0, 0)],
    "cry": [(0, 0), (16.42, 0), (16.7, 1), (40, 1)],
    "sweat": [(0, 0), (5.12, 1), (8.4, 1), (8.42, 0), (9.14, 1), (12.6, 1), (13.9, 0)],
    "desat": [(0, 0.05), (5.1, 0.15), (9.1, 0.15), (12.5, 0.2), (13.9, 0.35), (18.6, 0.4)],
})
MOUTH = [(0, "flat"), (2.7, "smile"), (3.44, "flat"), (4.6, "frown"), (5.12, "flat"), (8.6, "hum"), (8.85, "flat"),
         (9.14, "frown"), (12.5, "hum"), (13.0, "frown"), (13.92, "cry"), (17.3, "frown")]
KETTLE_R, CRATE_L = ("hip", 128, -10), ("hip", -128, -10)
POLE_L, POLE_R = ("hip", -124, 4), ("hip", 124, 4)
HAND_L = [(0, CRATE_L), (5.11, CRATE_L), (5.12, ("scrub", -1)), (8.4, ("scrub", -1)), (8.6, ("hip", -90, -40)),
          (9.13, ("hip", -90, -40)), (9.14, POLE_L), (12.48, POLE_L), (12.65, ("head", -150, -40)), (13.5, ("head", -150, -40)),
          (13.9, ("hip", -122, -15)), (13.92, ("hip", -70, -60))]
HAND_R = [(0, KETTLE_R), (5.11, KETTLE_R), (5.12, ("scrub", 1)), (8.4, ("scrub", 1)), (8.6, ("hip", 90, -40)),
          (9.13, ("hip", 90, -40)), (9.14, POLE_R), (12.48, POLE_R), (12.65, ("head", 150, -40)), (13.5, ("head", 150, -40)),
          (13.9, ("hip", 122, -15)), (13.92, ("hip", 70, -60)), (16.42, ("hip", 70, -60)), (16.7, ("rub", 1)),
          (17.2, ("rub", 1)), (17.4, ("hip", 70, -60))]
WHEEL_OFF = 12.48


def hand_pos(keys, t, hip, head, walk):
    def resolve(spec):
        kind = spec[0]
        if kind == "scrub":
            return (hip[0] + spec[1] * 70 + 30 * math.sin(t * 13 + (0 if spec[1] < 0 else 2)), hip[1] - 40 + 8 * math.cos(t * 13))
        if kind == "rub":
            return (head[0] + spec[1] * 48 + 12 * math.sin(t * 14), head[1] + 18 + 4 * math.cos(t * 14))
        ref = hip if kind == "hip" else head
        return (ref[0] + spec[1], ref[1] + spec[2])
    if t <= keys[0][0]:
        return resolve(keys[0][1])
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            f = smooth((t - t0) / (t1 - t0))
            pa, pb = resolve(a), resolve(b)
            return (lerp(pa[0], pb[0], f), lerp(pa[1], pb[1], f))
    return resolve(keys[-1][1])


m.T, m.MOUTH, m.HAND_L, m.HAND_R = T, MOUTH, HAND_L, HAND_R
m.hand_pos = hand_pos
m.walk_phase = lambda t: math.pi * (t - BEAT0) / BEAT
m.BEAT = BEAT
_base_head = sk._orig_head


def boy_head(t, p):
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
    dust = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dp = m.Pen(dust, 0, 0, K)
    for x, y, r in ((-74, 62, 18), (82, 40, 12), (30, -70, 14), (-20, 112, 10)):
        dp.circle(cx + x, cy + y, r, (120, 84, 60, 90))
    img.alpha_composite(dust.filter(ImageFilter.GaussianBlur(4 * K)))
    for k in range(4):   # messy loose strands
        x0 = cx - 60 + k * 40
        pen.line([(x0, cy - 140), (x0 + 14 * math.sin(k * 2.1), cy - 96)], m.HAIR, 6)
    if mouth == "cry":
        mx, my = cx, cy + 90
        wob = math.sin(t * 22) * 2.5
        top = [(mx + x, my + 10 - 10 * (1 - (x / 24) ** 2)) for x in range(-24, 25, 6)]
        bot = [(mx + x, my + 20 + wob * math.sin(x * 0.3) + 3 * (1 - (x / 24) ** 2)) for x in range(24, -25, -6)]
        pen.poly(top + bot, (120, 34, 50), LINE, 3)
    sweat = p.get("sweat", 0)
    if sweat > 0.05:   # beads of sweat sliding down his temple
        for k, sx in enumerate((1, -1)):
            u = (t * 0.7 + k * 0.5) % 1
            x, y = cx + sx * 108, cy - 70 + 120 * u
            pen.poly([(x, y - 16), (x - 8, y), (x + 8, y)], (200, 230, 255))
            pen.circle(x, y + 2, 8, (200, 230, 255))
    cry = p.get("cry", 0)
    if cry > 0.01:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        lp = m.Pen(lay, 0, 0, K)
        a = int(200 * cry)
        for sx in (-1, 1):
            x0, y0 = cx + sx * 56, cy + 44
            pts = [(x0 + sx * 6 * (k / 6) + 2 * math.sin(t * 6 + k + sx), y0 + 13 * k) for k in range(7)]
            lp.line(pts, (170, 215, 255, a // 2), 7)
        img.alpha_composite(lay)
    return img


m.draw_head = boy_head
_sk_char = m.draw_character


def checked(pen, pts, base, dark):
    pen.poly(pts, base, m.LINE, 3)


def draw_character(t):
    img, origin, head = _sk_char(t)
    pen = m.Pen(img, origin[0], origin[1], K)
    hx, hy = head
    # gamchha round his neck, one end hanging down his chest
    band = [(hx - 118, hy + 158), (hx - 60, hy + 140), (hx + 60, hy + 140), (hx + 118, hy + 158), (hx + 104, hy + 196),
            (hx + 40, hy + 182), (hx - 40, hy + 182), (hx - 104, hy + 196)]
    pen.poly(band, GAMCHHA, m.LINE, 3)
    end = [(hx + 40, hy + 176), (hx + 98, hy + 180), (hx + 108, hy + 380), (hx + 52, hy + 384)]
    pen.poly(end, GAMCHHA, m.LINE, 3)
    for k in range(5):
        pen.line([(hx + 44 + k * 2, hy + 220 + k * 34), (hx + 104, hy + 222 + k * 34)], (250, 240, 230), 3)
    pen.line([(hx + 66, hy + 180), (hx + 72, hy + 382)], GAMCHHA_D, 4)
    pen.line([(hx - 90, hy + 168), (hx + 90, hy + 168)], (250, 240, 230), 3)
    # a patch on his shirt
    pen.poly([(hx - 80, hy + 330), (hx - 30, hy + 326), (hx - 28, hy + 372), (hx - 78, hy + 376)], (180, 120, 48), m.LINE, 2)
    # wiping with the gamchha: a bunch of red cloth at his hand
    hand = m.LAST_HANDS.get("R")
    if hand and 16.6 < t < 17.4:
        pen.ellipse(hand[0] - 40, hand[1] - 34, hand[0] + 44, hand[1] + 40, GAMCHHA, m.LINE, 3)
    return img, origin, head


m.draw_character = draw_character

# ==============================================================================================
# scenes
# ==============================================================================================
SCENES = [(0.0, "park"), (5.12, "dhaba"), (9.14, "street_dusk"), (13.92, "street_night")]


def scene_at(t):
    return step(SCENES, t)


m.LIGHT = [
    (0.0, ((120, 110, 150), (255, 190, 130), (1.05, 0.98, 0.9))),
    (5.11, ((120, 110, 150), (255, 190, 130), (1.0, 0.95, 0.9))),
    (5.12, ((20, 16, 14), (40, 30, 24), (1.04, 0.96, 0.86))),
    (9.13, ((20, 16, 14), (40, 30, 24), (1.04, 0.96, 0.86))),
    (9.14, ((110, 64, 80), (255, 150, 100), (1.05, 0.95, 0.88))),
    (13.91, ((110, 64, 80), (255, 150, 100), (1.0, 0.92, 0.88))),
    (13.92, ((6, 8, 20), (24, 30, 52), (0.86, 0.9, 1.06))),
    (18.6, ((6, 8, 20), (24, 30, 52), (0.84, 0.88, 1.06))),
]
m.SHOTS = [
    (0.00, 2.70, (1.00, 0, -60, 0), (1.06, 0, -80, 0), "fade"),           # park, he watches the kids
    (2.70, 3.44, (2.30, 0, -335, 0), (2.50, 0, -335, 0), "cut"),          # close: a dream bubble
    (3.44, 5.12, (1.30, 0, -200, 0), (1.40, 0, -220, 0), "cut"),          # bicycles pass behind him
    (5.12, 7.50, (1.15, 0, -40, 0), (1.25, 0, -60, 0), "dip"),            # dhaba, scrubbing dishes
    (7.50, 8.42, (3.00, 280, -580, 0), (3.30, 280, -580, 0), "cut"),      # the clock spins
    (8.42, 9.14, (2.40, 0, -150, 6), (2.60, 0, -150, 8), "cut"),          # he nods off
    (9.14, 10.96, (1.00, 0, -40, 0), (1.08, 0, -60, 0), "whip"),          # hauling the cart
    (10.96, 11.82, (2.20, 0, 400, 0), (2.30, 0, 400, 0), "cut"),          # feet and the wobbly wheel
    (11.82, 13.92, (1.20, 0, -120, -6), (1.30, 0, -140, -9), "cut"),      # the wheel comes off
    (13.92, 16.42, (1.00, 0, -40, 0), (1.15, 0, -40, 0), "dip"),          # night rain, by the broken cart
    (16.42, 18.12, (2.40, 0, -100, 0), (2.60, 0, -110, 0), "cut"),        # wiping his tears, looking up
    (18.12, 18.58, (1.40, 0, -40, 0), (1.00, 0, -40, 0), "cut"),          # "ओ रे": pull back
]
m.DURATION = DUR

# ---------------------------------------------------------------- park
KID_COLS = [(230, 60, 70), (60, 140, 230), (250, 200, 50), (90, 190, 110), (200, 90, 200)]


def kid(d, x, base, sc, col, t, pose="stand", ph=0.0):
    skin = (236, 196, 160)
    bob = abs(math.sin(t * 6 + ph)) * 10 * sc if pose in ("run", "bowl") else 0
    top = base - 600 * sc - bob
    d.ellipse([x - 50 * sc, top, x + 50 * sc, top + 100 * sc], fill=skin)
    d.chord([x - 54 * sc, top - 6 * sc, x + 54 * sc, top + 70 * sc], 180, 360, fill=(40, 30, 26))
    d.polygon([(x - 50 * sc, top + 110 * sc), (x + 50 * sc, top + 110 * sc), (x + 44 * sc, top + 330 * sc),
               (x - 44 * sc, top + 330 * sc)], fill=col)
    sw = math.sin(t * 9 + ph) if pose in ("run", "bowl") else 0
    for s in (-1, 1):
        d.line([(x + s * 22 * sc, top + 330 * sc), (x + s * 26 * sc + s * sw * 30 * sc, base - bob)], fill=(60, 60, 80), width=max(2, int(26 * sc)))
    if pose == "bat":
        ang = -0.6 + 1.6 * max(0, math.sin(t * 3 + ph)) ** 4
        bx, by = x + 40 * sc, top + 200 * sc
        d.line([(x - 30 * sc, top + 150 * sc), (bx, by)], fill=col, width=max(2, int(22 * sc)))
        ex, ey = bx + 240 * sc * math.cos(ang), by + 240 * sc * math.sin(ang)
        d.line([(bx, by), (ex, ey)], fill=(220, 190, 120), width=max(3, int(30 * sc)))
    elif pose == "kite":
        hx_, hy_ = x + 30 * sc, top + 140 * sc
        d.line([(x, top + 150 * sc), (hx_, hy_ - 60 * sc)], fill=col, width=max(2, int(22 * sc)))
        return (hx_, hy_ - 60 * sc)
    else:
        for s in (-1, 1):
            d.line([(x + s * 50 * sc, top + 130 * sc), (x + s * (70 + 40 * sw) * sc, top + 300 * sc)], fill=col, width=max(2, int(22 * sc)))
    return None


def kite(d, x, y, s, col, t, string_to=None):
    sway = 14 * math.sin(t * 1.7 + x)
    x += sway
    d.polygon([(x, y - 50 * s), (x + 38 * s, y), (x, y + 56 * s), (x - 38 * s, y)], fill=col + (255,))
    d.line([(x, y - 50 * s), (x, y + 56 * s)], fill=(60, 40, 30, 255), width=2)
    d.line([(x - 38 * s, y), (x + 38 * s, y)], fill=(60, 40, 30, 255), width=2)
    tail = [(x + 6 * math.sin(t * 6 + k), y + 56 * s + k * 14 * s) for k in range(6)]
    d.line(tail, fill=col + (255,), width=3)
    if string_to:
        d.line([(x, y + 10 * s), string_to], fill=(230, 230, 230, 160), width=1)


def bicycle_kid(d, x, base, sc, col, t, balloon):
    r = 70 * sc
    for wx in (x - 110 * sc, x + 110 * sc):
        d.ellipse([wx - r, base - 2 * r, wx + r, base], outline=(40, 40, 50), width=max(2, int(9 * sc)))
    d.line([(x - 110 * sc, base - r), (x, base - r - 40 * sc), (x + 110 * sc, base - r), (x - 20 * sc, base - r - 120 * sc)],
           fill=(200, 40, 40), width=max(2, int(10 * sc)))
    kid(d, x - 10 * sc, base - r - 10 * sc, sc * 0.9, col, t, "stand", x)
    if balloon:
        bx, by = x + 40 * sc, base - 820 * sc
        d.line([(x + 30 * sc, base - 520 * sc), (bx, by + 70 * sc)], fill=(230, 230, 230), width=2)
        d.ellipse([bx - 50 * sc, by - 60 * sc, bx + 50 * sc, by + 70 * sc], fill=balloon)


def park_env(t, sky_bot):
    img = m.draw_env(t, "park", sky_bot)
    d = ImageDraw.Draw(img, "RGBA")
    # kites high in the sky
    for i, (x, y, s, col) in enumerate(((200, 300, 1.0, (255, 80, 90)), (820, 230, 0.8, (80, 160, 255)), (620, 420, 0.6, (255, 210, 60)))):
        kite(d, x, y, s, col, t, string_to=(proj(-1.6, 1.25, 9)) if i == 0 else None)
    # kids playing cricket on the lawn
    for x, z, col, pose, ph in ((-1.6, 9.0, KID_COLS[0], "kite", 0), (1.4, 8.0, KID_COLS[1], "bat", 0.5),
                                (2.4, 13.0, KID_COLS[2], "bowl", 1.4), (-2.2, 12.0, KID_COLS[3], "run", 2.2),
                                (0.9, 15.0, KID_COLS[4], "run", 3.1)):
        sx, base = proj(x, 0, z)
        sc = 1.25 * FOCAL / z / 600
        kid(d, sx, base, sc, col, t, pose, ph)
    # bicycles riding past behind him ("सैर सपाटा")
    if 3.44 <= t < 5.12:
        for k, (dx, col, bal) in enumerate(((0, KID_COLS[2], (255, 90, 120)), (-2.6, KID_COLS[1], (120, 220, 255)),
                                            (-5.0, KID_COLS[3], None))):
            x = lerp(-6, 7, (t - 3.44) / 1.68) + dx
            sx, base = proj(x, 0, 6.5)
            bicycle_kid(d, sx, base, 1.3 * FOCAL / 6.5 / 600, col, t, bal)
    return img


# ---------------------------------------------------------------- dhaba
def clock_angles(t):
    mins = 40 + 60 * 3 * smooth((t - 7.5) / 0.92) if t > 7.5 else 40 + (t - 5.12) * 0.5
    hrs = 22 + mins / 60
    return math.radians(mins / 60 * 360 - 90), math.radians((hrs % 12) / 12 * 360 - 90)


def dhaba_env(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for row, y in enumerate(range(0, 1700, 46)):   # bricks
        for x in range(-60 if row % 2 else -20, W, 120):
            d.rectangle([x + 3, y + 3, x + 116, y + 43], fill=(120, 60, 44, 255))
    d.rectangle([0, 0, W, 1700], fill=(0, 0, 0, 60))
    # shelf of steel glasses and plates
    d.rectangle([40, 640, 360, 660], fill=(90, 60, 40, 255))
    for k in range(6):
        d.rectangle([60 + k * 50, 570, 96 + k * 50, 640], fill=(190, 196, 206, 255), outline=(120, 126, 136, 255), width=3)
    d.rectangle([40, 900, 360, 920], fill=(90, 60, 40, 255))
    for k in range(4):
        d.ellipse([60 + k * 76, 820, 140 + k * 76, 900], fill=(200, 206, 214, 255), outline=(130, 136, 146, 255), width=4)
    # the wall clock
    cx, cy, r = 820, 520, 110
    d.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], fill=(60, 40, 30, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(246, 240, 226, 255))
    for k in range(12):
        a = k / 12 * math.tau
        d.line([(cx + (r - 18) * math.cos(a), cy + (r - 18) * math.sin(a)), (cx + (r - 6) * math.cos(a), cy + (r - 6) * math.sin(a))],
               fill=(40, 40, 40, 255), width=5)
    am, ah = clock_angles(t)
    d.line([(cx, cy), (cx + 60 * math.cos(ah), cy + 60 * math.sin(ah))], fill=(30, 30, 30, 255), width=10)
    d.line([(cx, cy), (cx + 92 * math.cos(am), cy + 92 * math.sin(am))], fill=(30, 30, 30, 255), width=6)
    if 7.5 < t < 8.42:   # motion trails while the hands race
        for k in range(1, 6):
            a2 = am - k * 0.35
            d.line([(cx, cy), (cx + 92 * math.cos(a2), cy + 92 * math.sin(a2))], fill=(30, 30, 30, 120 - k * 20), width=6)
    d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=(180, 40, 40, 255))
    # the bulb
    d.line([(540, 0), (540, 280)], fill=(20, 20, 20, 255), width=4)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([340, 120, 740, 520], fill=(255, 200, 120, 120))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
    d.ellipse([515, 270, 565, 330], fill=(255, 240, 190, 255))
    d.rectangle([0, 1700, W, H], fill=(56, 48, 44, 255))
    return img


def env_for(t, kind, sky_bot):
    if kind == "park":
        return park_env(t, sky_bot)
    if kind == "dhaba":
        return dhaba_env(t)
    if kind == "street_dusk":
        return m.draw_env(t, "golden", sky_bot)
    return m.draw_env(t, "street", sky_bot)


# ---------------------------------------------------------------- the handcart (behind him) and props
def cart_state(t):
    """(wobble, tip angle, wheel roll-away 0..1)"""
    if t < 10.4:
        return 0.0, 0.0, 0.0
    if t < WHEEL_OFF:
        return smooth((t - 10.4) / 1.5), 0.0, 0.0
    off = clamp((t - WHEEL_OFF) / 1.2)
    return 0.0, 0.26 * ease_out(clamp((t - WHEEL_OFF) / 0.4)), off


def draw_cart(d, t, behind=True):
    """An old wooden handcart he pulls behind him (world space, he is at x 540)."""
    wob, tip, off = cart_state(t)
    dist = m.distance_at(t)
    cx, cy = 540, 1170
    ca, sa = math.cos(tip), math.sin(tip)

    def R(x, y):
        x, y = x - cx, y - cy
        return (cx + x * ca - y * sa, cy + x * sa + y * ca + (40 * tip / 0.26 if tip else 0))
    for i, (wx, side) in enumerate(((300, -1), (780, 1))):   # wheels with spokes
        wy = 1450 + (6 * math.sin(t * 20) * wob if side > 0 else 0)
        x_ = wx
        if side > 0 and off > 0:
            x_ = wx + 700 * off
            wy = 1450 + 60 * math.sin(off * 9) * (1 - off)
        else:
            x_, wy = R(wx, wy) if tip else (wx, wy)
        r = 110
        d.ellipse([x_ - r - 4, wy - r - 4, x_ + r + 4, wy + r + 4], outline=(40, 26, 18, 255), width=24)
        d.ellipse([x_ - r, wy - r, x_ + r, wy + r], outline=(176, 128, 80, 255), width=16)
        rot = dist * 2.2 + (off * 12 if side > 0 else 0)
        for k in range(6):
            a = rot + k * math.pi / 3
            d.line([(x_, wy), (x_ + r * math.cos(a), wy + r * math.sin(a))], fill=(150, 108, 68, 255), width=8)
        d.ellipse([x_ - 16, wy - 16, x_ + 16, wy + 16], fill=(70, 50, 36, 255))
    box = [R(310, 1080), R(770, 1080), R(770, 1300), R(310, 1300)]
    d.polygon(box, fill=(130, 90, 56, 255), outline=(70, 46, 30, 255))
    for y in (1140, 1210):
        d.line([R(310, y), R(770, y)], fill=(100, 68, 44, 255), width=5)
    for k, (sx, sy) in enumerate(((380, 1010), (520, 990), (660, 1010), (450, 930), (600, 930))):   # sacks
        if off > 0 and k >= 3:
            continue
        pts = [R(sx - 80, sy + 80), R(sx - 70, sy - 40), R(sx, sy - 70), R(sx + 70, sy - 40), R(sx + 80, sy + 80)]
        d.polygon(pts, fill=(196, 176, 130, 255), outline=(120, 100, 70, 255))
        d.line([R(sx - 40, sy - 50), R(sx + 40, sy - 50)], fill=(150, 130, 90, 255), width=4)
    for sx in (-1, 1):   # the two poles reaching his hands
        hand = m.LAST_HANDS.get("L" if sx < 0 else "R", (540 + sx * 124, 1250))
        d.line([R(540 + sx * 230, 1200), hand], fill=(110, 76, 46, 255), width=18)


def fallen_sacks(d, t):
    f = ease_out(clamp((t - WHEEL_OFF) / 0.5))
    for k, (sx, sy) in enumerate(((250, 1600), (830, 1620), (400, 1690))):
        y = lerp(1000, sy, f * f) if t < 13.92 else sy
        x = sx
        rot = (k - 1) * 0.5 * f
        pts = [(x - 120, y + 50), (x - 110, y - 60), (x + 110, y - 70), (x + 124, y + 46)]
        cr, sr = math.cos(rot), math.sin(rot)
        pts = [(x + (px - x) * cr - (py - y) * sr, y + (px - x) * sr + (py - y) * cr) for px, py in pts]
        d.polygon(pts, fill=(196, 176, 130, 255), outline=(120, 100, 70, 255))
        for g in range(5):   # spilled grain
            gx, gy = x + (g - 2) * 40 + 30, y + 70
            d.ellipse([gx - 9, gy - 5, gx + 9, gy + 5], fill=(230, 200, 120, 255))


def behind_layer(t, kind):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if kind in ("street_dusk", "street_night"):
        draw_cart(ImageDraw.Draw(layer), t)
    return layer


def front_props(layer, t, kind):
    d = ImageDraw.Draw(layer)
    hand = m.LAST_HANDS
    if kind == "park":
        if "R" in hand:   # tea kettle
            x, y = hand["R"]
            d.ellipse([x - 50, y + 10, x + 50, y + 120], fill=(190, 196, 206, 255), outline=(110, 116, 126, 255), width=4)
            d.polygon([(x + 40, y + 50), (x + 96, y + 20), (x + 100, y + 30), (x + 48, y + 70)], fill=(170, 176, 186, 255))
            d.arc([x - 30, y - 30, x + 30, y + 30], 180, 360, fill=(90, 96, 106, 255), width=6)
            if t < 2.7:
                for k in range(3):
                    u = (t * 0.6 + k / 3) % 1
                    d.line([(x + 96 + 10 * math.sin(u * 6), y + 10 - 80 * u), (x + 100 + 10 * math.sin(u * 6 + 1), y - 10 - 80 * u)],
                           fill=(255, 255, 255, int(110 * (1 - u))), width=4)
        if "L" in hand:   # wire crate of glasses
            x, y = hand["L"]
            d.rectangle([x - 70, y + 10, x + 50, y + 100], outline=(90, 90, 100, 255), width=6)
            for k in range(4):
                d.rectangle([x - 62 + k * 28, y + 30, x - 42 + k * 28, y + 94], fill=(220, 180, 120, 230))
    if kind == "dhaba":   # tub of water and a pile of dishes
        d.ellipse([200, 1300, 880, 1420], fill=(170, 176, 186, 255), outline=(110, 116, 126, 255), width=8)
        d.ellipse([230, 1318, 850, 1402], fill=(120, 150, 170, 255))
        d.polygon([(200, 1360), (880, 1360), (840, 1720), (240, 1720)], fill=(156, 162, 172, 255))
        d.ellipse([200, 1300, 880, 1420], outline=(110, 116, 126, 255), width=8)
        for k in range(8):   # bubbles
            u = (t * 0.5 + k / 8) % 1
            bx, by = 300 + k * 64, 1350 - 40 * u
            d.ellipse([bx - 10, by - 10, bx + 10, by + 10], outline=(240, 250, 255, int(200 * (1 - u))), width=3)
        for side, x0 in ((-1, 30), (1, 870)):
            for k in range(7):
                d.ellipse([x0, 1610 - k * 26, x0 + 180, 1650 - k * 26], fill=(214, 218, 226, 255), outline=(140, 146, 156, 255), width=3)
    if kind in ("street_dusk", "street_night") and t >= WHEEL_OFF:
        fallen_sacks(d, t)


rnd = random.Random(5)
RAIN = [(rnd.uniform(-200, W + 200), rnd.uniform(0, H), rnd.uniform(1500, 2200), rnd.uniform(50, 100)) for _ in range(260)]


def fx_layer(t, kind):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if kind == "street_night":
        for x, y, sp, ln in RAIN:
            yy = (y + t * sp) % (H + 200) - 100
            xx = x - yy * 0.1
            d.line([(xx, yy), (xx - ln * 0.1, yy - ln)], fill=(190, 210, 255, 120), width=2)
    for x, y, s_, sp, ph in m.DUST:
        py_ = (y - t * sp * 0.5) % H
        px_ = x + 24 * math.sin(t * 0.7 + ph)
        d.ellipse([px_ - s_, py_ - s_, px_ + s_, py_ + s_], fill=(255, 230, 200, 40))
    return layer.filter(ImageFilter.GaussianBlur(1.0))


def draw_signs(t, layer, cam, head):
    d = ImageDraw.Draw(layer)
    to_s, zd = m.world_to_screen(cam)
    hx, hy = to_s(*head)
    # "मस्ती": a dream bubble of him batting with the kids, then it pops
    if 2.75 <= t < 3.44:
        u = (t - 2.75) / 0.69
        q = back_out(u / 0.3) if u < 0.3 else 1.0
        a = int(240 * (1 - smooth((u - 0.8) / 0.2)))
        bx, by, r = 810, 610, 140 * q
        for k, (ox, oy, rr) in enumerate(((-210, 300, 18), (-160, 230, 28))):
            d.ellipse([bx + ox - rr, by + oy - rr, bx + ox + rr, by + oy + rr], fill=(255, 255, 255, a))
        d.ellipse([bx - r * 1.2, by - r, bx + r * 1.2, by + r], fill=(255, 255, 255, a), outline=(200, 210, 230, a), width=4)
        if q > 0.6:
            d.line([(bx - 60, by + 70), (bx + 40, by - 80)], fill=(220, 180, 110, a), width=16)
            d.ellipse([bx + 60, by - 40, bx + 90, by - 10], fill=(220, 40, 50, a))
            d.ellipse([bx - 110, by - 40, bx - 60, by + 10], fill=(222, 170, 132, a))
            d.line([(bx - 85, by + 10), (bx - 85, by + 90)], fill=(212, 150, 58, a), width=24)


def scene_frame(t, cam, kind):
    top, bot, _ = m.light_at(t)
    sky = np.array(top, np.float32) * (1 - m.GRAD_Y) + np.array(bot, np.float32) * m.GRAD_Y
    frame = Image.fromarray(np.broadcast_to(sky, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    frame.alpha_composite(m.cam_transform(env_for(t, kind, bot), 0.9, cam))
    char_img, origin, head = m.draw_character(t)   # draw first so the cart poles know where his hands are
    frame.alpha_composite(m.cam_transform(behind_layer(t, kind), 1.0, cam))
    char_l = m.cam_transform(char_img, 1.0, cam, origin, K)
    frame.alpha_composite(char_l)
    props = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    front_props(props, t, kind)
    pl = m.cam_transform(props.filter(ImageFilter.GaussianBlur(0.7)), 1.0, cam)
    frame.alpha_composite(pl)
    frame.alpha_composite(m.cam_transform(fx_layer(t, kind), 1.1, cam))
    signs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_signs(t, signs, cam, head)
    frame.alpha_composite(signs)
    occ_c = np.asarray(char_l.getchannel("A").resize((W // 8, H // 8))) > 40
    occ_o = (np.asarray(pl.getchannel("A").resize((W // 8, H // 8))) > 40) | (np.asarray(signs.getchannel("A").resize((W // 8, H // 8))) > 40)
    return frame, (occ_c.astype(np.float32), occ_o.astype(np.float32))


def render_frame(t):
    rng = np.random.default_rng(int(t * 1000) + 5)
    _, _, tint = m.light_at(t)
    kind = scene_at(t)
    frame, occ = scene_frame(t, m.camera_at(t), kind)
    blur, bright, flash = m.transition_fx(t)
    arr = np.asarray(frame.convert("RGB")).astype(np.float32) * np.array(tint, np.float32)
    de = track(T["desat"], t)
    if de > 0.01:
        lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
        arr = arr * (1 - de) + lum[:, :, None] * de
    arr = m.motion_blur(arr, blur)
    if flash > 0.01:
        arr = arr + (255 - arr) * flash * 0.8
    arr *= m.VIGNETTE * bright
    arr += rng.normal(0, 3.4, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    fade = min(clamp(t / 0.35), clamp((DUR - t) / 0.5))
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
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={DUR - 0.4:.2f}:d=0.4",
                    "-t", f"{DUR:.2f}", "-movflags", "+faststart", OUT], check=True)
    os.remove(SILENT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
