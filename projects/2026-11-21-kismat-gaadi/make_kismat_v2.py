""""किस्मत की गाड़ी" reel, v2: the story of an adult (user: "ek adult ke upar banao").

A young office worker who has no time to live his age:
  0.0  sunset street: his friends drive past in an open jeep, waving him along; he shakes his head
  2.7  "मस्ती": phone glow on his face, a dream bubble of the beach trip
  3.4  "सैर सपाटा": the phone rings (the boss), he answers, his shoulders drop
  5.1  night, an empty office: he types among piles of files
  7.5  "घड़ी का कांटा": the wall clock races; he nods off at the desk
  9.1  "अपनी किस्मत की गाड़ी की": riding home on his old scooter, it sputters smoke
 11.8  "खस्ता हालत है": it dies in a burst of smoke, the headlight goes out, hands to his head
 13.9  (again) rain: he pushes the dead scooter down the empty road
 16.4  close-up in the rain, he looks up; 18.1 "ओ रे" pull back, fade

New character: a man in his mid-twenties with stubble and tired eyes, a light-blue shirt with a loose tie,
an ID card on a lanyard, backpack straps and a wristwatch. Lyrics stay plain and static, as in v1.
Reuses make_kismat.py (lyrics, clock) and the rig via ../2026-11-20-shakal-sad.

Usage: python3 make_kismat_v2.py [--frames 30,150,...] [--workers 4]
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
sys.path.insert(0, HERE)
import make_kismat as kg  # noqa: E402

sk, m = kg.sk, kg.m
clamp, smooth, lerp, ease_out, back_out, track, step = m.clamp, m.smooth, m.lerp, m.ease_out, m.back_out, m.track, m.step
W, H, FPS = 1080, 1920, 30
AUDIO = kg.AUDIO
OUT = os.path.join(HERE, "kismat_v2.mp4")
SILENT = os.path.join(HERE, "_kismat_v2_silent.mp4")
DUR = kg.DUR
K = m.K
proj, FOCAL = m.proj, m.FOCAL

# ==============================================================================================
# the man (new character)
# ==============================================================================================
m.SKIN, m.SKIN_SH = (234, 192, 160), (208, 164, 134)
m.HAIR, m.HAIR_HI = (16, 16, 22), (62, 64, 84)
m.HOOD, m.HOOD_SH = (156, 186, 226), (116, 146, 196)
m.PANTS = (52, 56, 70)
m.IRIS, m.IRIS_D = (90, 60, 40), (46, 30, 20)
TIE, TIE_D = (34, 44, 86), (22, 28, 60)

DESK, RIDE = 200, 120
T = dict(sk.T)
T.update({
    "laugh": [(0, 0)], "happy": [(0, 0)], "swag": [(0, 0)], "blush": [(0, 0)],
    "walk": [(0, 0), (13.91, 0), (13.92, 1), (40, 1)],
    "speed": [(0, 0), (9.13, 0), (9.14, 3.2), (11.9, 3.2), (12.4, 0), (13.91, 0), (13.92, 0.8), (40, 0.8)],
    "sink": [(0, 0), (5.11, 0), (5.12, DESK), (9.13, DESK), (9.14, RIDE), (13.91, RIDE), (13.92, 0)],
    "slump": [(0, 0.1), (3.9, 0.1), (4.5, 0.5), (5.11, 0.5), (5.12, 0.4), (8.42, 0.5), (9.0, 0.8), (9.14, 0.2),
              (11.8, 0.2), (12.3, 0.4), (13.91, 0.4), (13.92, 0.7), (16.4, 0.7), (16.6, 0.3)],
    "head_dy": [(0, 0), (1.2, 0), (1.5, 0), (3.9, 0), (4.5, 16), (5.11, 16), (5.12, 14), (8.42, 14), (8.6, 30),
                (8.8, 8), (9.0, 36), (9.14, 0), (12.6, 0), (12.8, -8), (13.91, -8), (13.92, 26), (16.4, 26), (16.6, -14)],
    "tilt": [(0, 0), (2.7, 3), (3.44, 3), (3.9, 8), (5.1, 4), (5.12, 0), (8.42, 0), (8.7, 7), (9.1, -6), (9.14, 0),
             (12.4, 0), (12.6, -5), (13.9, -5), (13.92, -3), (16.4, -3), (16.6, 2)],
    "shake": [(0, 0), (1.3, 0), (1.4, 0.35), (2.2, 0.35), (2.3, 0), (9.14, 0), (9.2, 0.04), (11.8, 0.04), (11.9, 0)],
    "look": [(0, (0.6, 0)), (1.2, (-0.5, 0)), (2.3, (0, 0.1)), (2.7, (0, 0.55)), (3.44, (0.3, 0)), (4.5, (0, 0.8)),
             (5.12, (0, 0.65)), (8.42, (0, 0.4)), (9.14, (0, 0)), (11.9, (0, 0.7)), (13.92, (0, 0.55)),
             (16.42, (0, 0.3)), (17.2, (0, -0.9))],
    "lid": [(0, 0.15), (2.7, 0.2), (3.9, 0.35), (5.12, 0.45), (8.42, 0.55), (8.7, 0.95), (8.85, 0.55), (9.0, 1.0),
            (9.14, 0.35), (11.9, 0.3), (12.0, 0), (12.6, 0.2), (13.92, 0.55), (16.42, 0.5), (17.2, 0.3), (18.0, 0.8)],
    "brow": [(0, 0.45), (2.7, 0.2), (3.44, 0.5), (4.0, 0.85), (40, 0.85)],
    "tear": kg.saw(14.5, 40, 1.4),
    "tear_a": [(0, 0), (14.3, 0), (14.8, 0.8), (40, 0.8)],
    "cry": [(0, 0), (16.42, 0), (16.8, 0.6), (40, 0.6)],
    "sweat": [(0, 0), (5.12, 1), (8.4, 1), (8.42, 0), (11.9, 1), (13.9, 0)],
    "desat": [(0, 0.05), (5.1, 0.18), (9.1, 0.2), (13.9, 0.35), (18.6, 0.42)],
})
MOUTH = [(0, "smile"), (1.3, "flat"), (2.7, "smile"), (3.44, "flat"), (3.95, "hum"), (4.15, "flat"), (4.35, "hum"),
         (4.5, "frown"), (5.12, "flat"), (8.6, "hum"), (8.85, "flat"), (9.14, "flat"), (11.9, "hum"), (12.6, "frown"),
         (16.42, "frown"), (17.4, "flat")]
BAG_L, PHONE_R = ("hip", -122, -15), ("hip", 120, -30)
GRIP_L, GRIP_R = ("hip", -170, -230), ("hip", 170, -230)
PUSH_L, PUSH_R = ("hip", -170, -110), ("hip", 170, -110)
HAND_L = [(0, BAG_L), (1.2, BAG_L), (1.45, ("head", -110, 150)), (2.2, ("head", -110, 150)), (2.5, BAG_L),
          (5.11, BAG_L), (5.12, ("type", -1)), (8.4, ("type", -1)), (8.6, ("hip", -90, -110)), (9.13, ("hip", -90, -110)),
          (9.14, GRIP_L), (12.4, GRIP_L), (12.6, ("head", -150, -40)), (13.6, ("head", -150, -40)), (13.91, GRIP_L),
          (13.92, PUSH_L)]
HAND_R = [(0, ("wave",)), (1.2, ("wave",)), (1.45, ("head", 110, 150)), (2.2, ("head", 110, 150)), (2.5, PHONE_R),
          (2.7, ("head", 30, 200)), (3.44, ("head", 30, 200)), (3.9, ("head", 120, 30)), (4.6, ("head", 120, 30)),
          (5.0, ("hip", 122, -15)), (5.11, ("hip", 122, -15)), (5.12, ("type", 1)), (8.4, ("type", 1)),
          (8.6, ("hip", 90, -110)), (9.13, ("hip", 90, -110)), (9.14, GRIP_R), (12.15, GRIP_R), (12.3, ("hip", 120, -200)),
          (12.45, GRIP_R), (12.6, ("head", 150, -40)), (13.6, ("head", 150, -40)), (13.91, GRIP_R), (13.92, PUSH_R)]


def hand_pos(keys, t, hip, head, walk):
    def resolve(spec):
        kind = spec[0]
        if kind == "type":
            return (hip[0] + spec[1] * 80 + 10 * math.sin(t * 22 + spec[1]), hip[1] - 130 + 6 * abs(math.sin(t * 22 + spec[1])))
        if kind == "wave":
            return (head[0] + 175 + 30 * math.sin(t * 10), head[1] - 120)
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
_base_head = sk._orig_head


def man_head(t, p):
    p = dict(p)
    if p["lid"] < 0.9 and sk.blink(t):
        p["lid"] = 1.0
    img = _base_head(t, p)
    pen = m.Pen(img, 0, 0, K)
    cx, cy = 180, 310
    # stubble along the jaw and over the lip
    st = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sp = m.Pen(st, 0, 0, K)
    sp.poly([(cx - 114, cy + 30), (cx - 100, cy + 85), (cx - 45, cy + 128), (cx, cy + 138), (cx + 45, cy + 128),
             (cx + 100, cy + 85), (cx + 114, cy + 30), (cx + 92, cy + 70), (cx + 40, cy + 108), (cx + 30, cy + 76),
             (cx - 30, cy + 76), (cx - 40, cy + 108), (cx - 92, cy + 70)], (70, 60, 74, 90))
    sp.poly([(cx - 30, cy + 74), (cx + 30, cy + 74), (cx + 22, cy + 84), (cx - 22, cy + 84)], (70, 60, 74, 110))
    img.alpha_composite(st.filter(ImageFilter.GaussianBlur(2 * K)))
    for sx in (-1, 1):   # tired eye bags
        pen.arc_line(cx + sx * 52, cy + 40, 26, 10, 20, 160, m.SKIN_SH, 4)
    sweat = p.get("sweat", 0)
    if sweat > 0.05:
        for k, sx in enumerate((1, -1)):
            u = (t * 0.7 + k * 0.5) % 1
            x, y = cx + sx * 108, cy - 70 + 120 * u
            pen.poly([(x, y - 16), (x - 8, y), (x + 8, y)], (200, 230, 255))
            pen.circle(x, y + 2, 8, (200, 230, 255))
    cry = p.get("cry", 0)
    if cry > 0.01:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        lp = m.Pen(lay, 0, 0, K)
        for sx in (-1, 1):
            x0, y0 = cx + sx * 56, cy + 44
            lp.line([(x0 + sx * 6 * (k / 6), y0 + 13 * k) for k in range(7)], (170, 215, 255, int(110 * cry)), 6)
        img.alpha_composite(lay)
    return img


m.draw_head = man_head
_sk_char = kg._sk_char


def draw_character(t):
    img, origin, head = _sk_char(t)
    pen = m.Pen(img, origin[0], origin[1], K)
    hx, hy = head
    for sx in (-1, 1):   # backpack straps
        pen.line([(hx + sx * 96, hy + 186), (hx + sx * 92, hy + 430)], (40, 40, 48), 16)
    for sx in (-1, 1):   # shirt collar
        pen.poly([(hx + sx * 8, hy + 168), (hx + sx * 60, hy + 150), (hx + sx * 52, hy + 200)], (236, 242, 252), m.LINE, 2)
    knot = (hx + 4, hy + 186)   # loose tie
    pen.poly([(knot[0] - 14, knot[1] - 10), (knot[0] + 14, knot[1] - 10), (knot[0] + 10, knot[1] + 16), (knot[0] - 10, knot[1] + 16)], TIE, m.LINE, 2)
    pen.poly([(knot[0] - 10, knot[1] + 16), (knot[0] + 10, knot[1] + 16), (knot[0] + 26, hy + 390), (knot[0] + 6, hy + 414),
              (knot[0] - 12, hy + 390)], TIE, m.LINE, 2)
    pen.line([(knot[0] - 4, hy + 230), (knot[0] + 14, hy + 380)], TIE_D, 4)
    # ID card on a red lanyard
    pen.line([(hx - 40, hy + 160), (hx - 56, hy + 300)], (200, 40, 50), 5)
    pen.line([(hx - 10, hy + 166), (hx - 40, hy + 300)], (200, 40, 50), 5)
    pen.poly([(hx - 76, hy + 300), (hx - 26, hy + 300), (hx - 26, hy + 370), (hx - 76, hy + 370)], (250, 250, 252), m.LINE, 2)
    pen.poly([(hx - 76, hy + 300), (hx - 26, hy + 300), (hx - 26, hy + 318), (hx - 76, hy + 318)], (60, 110, 200))
    pen.circle(hx - 51, hy + 340, 10, (200, 180, 160))
    hand = m.LAST_HANDS.get("L")   # wristwatch
    if hand:
        pen.ellipse(hand[0] - 30, hand[1] + 14, hand[0] + 30, hand[1] + 36, (30, 30, 36), m.LINE, 2)
        pen.circle(hand[0], hand[1] + 25, 9, (220, 220, 230))
    return img, origin, head


m.draw_character = draw_character

# ==============================================================================================
# scenes
# ==============================================================================================
SCENES = [(0.0, "street_dusk"), (5.12, "office"), (9.14, "street_night")]
m.LIGHT = [
    (0.0, ((110, 64, 80), (255, 150, 100), (1.05, 0.96, 0.9))),
    (5.11, ((110, 64, 80), (255, 150, 100), (1.0, 0.94, 0.9))),
    (5.12, ((14, 18, 30), (34, 40, 60), (0.96, 0.98, 1.04))),
    (9.13, ((14, 18, 30), (34, 40, 60), (0.96, 0.98, 1.04))),
    (9.14, ((6, 8, 20), (24, 30, 52), (0.9, 0.93, 1.05))),
    (18.6, ((6, 8, 20), (24, 30, 52), (0.84, 0.88, 1.06))),
]
m.SHOTS = [
    (0.00, 2.70, (1.00, 0, -60, 0), (1.06, 0, -80, 0), "fade"),           # friends drive past in a jeep
    (2.70, 3.44, (2.30, 0, -335, 0), (2.50, 0, -335, 0), "cut"),          # phone glow, beach dream
    (3.44, 5.12, (1.45, 0, -230, 0), (1.55, 0, -250, 0), "cut"),          # the boss calls
    (5.12, 7.50, (1.10, 0, -40, 0), (1.22, 0, -60, 0), "dip"),            # empty office, typing
    (7.50, 8.42, (3.00, -280, -580, 0), (3.30, -280, -580, 0), "cut"),    # the clock races
    (8.42, 9.14, (2.40, 0, -136, 6), (2.60, 0, -136, 8), "cut"),          # nodding off
    (9.14, 10.96, (1.00, 0, -40, 0), (1.08, 0, -60, 0), "whip"),          # riding the old scooter
    (10.96, 11.82, (2.20, 0, 380, 0), (2.30, 0, 380, 0), "cut"),          # wheel and sputtering exhaust
    (11.82, 13.92, (1.25, 0, -150, -6), (1.35, 0, -170, -9), "cut"),      # it dies
    (13.92, 16.42, (1.00, 0, -40, 0), (1.12, 0, -60, 0), "dip"),          # pushing it in the rain
    (16.42, 18.12, (2.40, 0, -310, 0), (2.60, 0, -320, 0), "cut"),        # rain on his face, looks up
    (18.12, 18.58, (1.40, 0, -40, 0), (1.00, 0, -40, 0), "cut"),          # pull back
]
m.DURATION = DUR


def scene_at(t):
    return step(SCENES, t)


# ---------------------------------------------------------------- the friends' jeep
FRIEND_COLS = [(240, 80, 90), (80, 170, 240), (250, 210, 60), (120, 210, 120)]


def jeep(d, x, base, sc, t):
    w, h = 520 * sc, 150 * sc
    for wx in (x - w * 0.32, x + w * 0.32):
        r = 62 * sc
        d.ellipse([wx - r, base - 2 * r, wx + r, base], fill=(30, 30, 36))
        d.ellipse([wx - r * 0.45, base - r * 1.45, wx + r * 0.45, base - r * 0.55], fill=(150, 150, 160))
    d.rounded_rectangle([x - w / 2, base - 70 * sc - h, x + w / 2, base - 70 * sc], radius=int(20 * sc), fill=(60, 120, 76))
    d.line([(x + w * 0.2, base - 70 * sc - h), (x + w * 0.28, base - 70 * sc - h - 90 * sc)], fill=(40, 40, 46), width=max(2, int(8 * sc)))
    for k, col in enumerate(FRIEND_COLS):   # friends standing up, arms waving
        fx = x - w * 0.34 + k * w * 0.22
        top = base - 70 * sc - h - 200 * sc + 8 * sc * math.sin(t * 9 + k)
        d.polygon([(fx - 30 * sc, top + 90 * sc), (fx + 30 * sc, top + 90 * sc), (fx + 34 * sc, top + 210 * sc), (fx - 34 * sc, top + 210 * sc)], fill=col)
        d.ellipse([fx - 30 * sc, top + 20 * sc, fx + 30 * sc, top + 82 * sc], fill=(236, 196, 164))
        d.chord([fx - 32 * sc, top + 14 * sc, fx + 32 * sc, top + 60 * sc], 180, 360, fill=(30, 26, 24))
        ang = -2.2 + 0.5 * math.sin(t * 12 + k)
        d.line([(fx + 20 * sc, top + 100 * sc), (fx + 20 * sc + 110 * sc * math.cos(ang), top + 100 * sc + 110 * sc * math.sin(ang))],
               fill=col, width=max(2, int(16 * sc)))
    for k in range(3):   # music notes floating up
        u = (t * 0.8 + k / 3) % 1
        nx, ny = x - w * 0.2 + k * w * 0.2, base - 420 * sc - 260 * sc * u
        d.ellipse([nx - 14 * sc, ny - 10 * sc, nx + 14 * sc, ny + 10 * sc], fill=(255, 255, 255, int(230 * (1 - u))))
        d.line([(nx + 12 * sc, ny), (nx + 12 * sc, ny - 60 * sc)], fill=(255, 255, 255, int(230 * (1 - u))), width=max(2, int(5 * sc)))


def street_dusk_env(t, sky_bot):
    img = m.draw_env(t, "golden", sky_bot)
    if 0.2 < t < 2.9:
        d = ImageDraw.Draw(img, "RGBA")
        x = lerp(6.5, -6.5, (t - 0.2) / 2.6)
        sx, base = proj(x, 0, 7.0)
        jeep(d, sx, base, 2.1 * FOCAL / 7.0 / 600, t)
    return img


# ---------------------------------------------------------------- the empty office
def office_env(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(0, 1700, 8):
        f = y / 1700
        d.rectangle([0, y, W, y + 8], fill=(int(lerp(56, 34, f)), int(lerp(64, 40, f)), int(lerp(82, 54, f)), 255))
    # window: night city
    d.rectangle([620, 260, 1060, 900], fill=(14, 18, 40, 255))
    r2 = random.Random(3)
    x = 620
    while x < 1060:
        bw, bh = r2.randint(40, 90), r2.randint(150, 520)
        d.rectangle([x, 900 - bh, x + bw, 900], fill=(22, 26, 46, 255))
        for _ in range(bw * bh // 700):
            lx, ly = r2.uniform(x + 4, x + bw - 8), r2.uniform(900 - bh + 6, 890)
            d.rectangle([lx, ly, lx + 6, ly + 8], fill=(255, 210, 120, 255) if r2.random() < 0.55 else (70, 90, 140, 255))
        x += bw + 6
    for xx in (766, 912):
        d.line([(xx, 260), (xx, 900)], fill=(40, 44, 60, 255), width=10)
    d.rectangle([620, 260, 1060, 900], outline=(40, 44, 60, 255), width=14)
    # empty cubicles behind him
    for x0 in (-40, 760):
        d.rectangle([x0, 1060, x0 + 360, 1180], fill=(90, 96, 110, 255))
        d.rectangle([x0, 1060, x0 + 360, 1074], fill=(120, 126, 140, 255))
        d.ellipse([x0 + 120, 980, x0 + 230, 1080], fill=(30, 30, 38, 255))   # an empty chair back
    # wall clock (left)
    cx, cy, r = 260, 520, 110
    d.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], fill=(40, 40, 46, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(240, 240, 236, 255))
    for k in range(12):
        a = k / 12 * math.tau
        d.line([(cx + (r - 18) * math.cos(a), cy + (r - 18) * math.sin(a)), (cx + (r - 6) * math.cos(a), cy + (r - 6) * math.sin(a))],
               fill=(40, 40, 40, 255), width=5)
    am, ah = kg.clock_angles(t)
    d.line([(cx, cy), (cx + 60 * math.cos(ah), cy + 60 * math.sin(ah))], fill=(30, 30, 30, 255), width=10)
    d.line([(cx, cy), (cx + 92 * math.cos(am), cy + 92 * math.sin(am))], fill=(30, 30, 30, 255), width=6)
    if 7.5 < t < 8.42:
        for k in range(1, 6):
            a2 = am - k * 0.35
            d.line([(cx, cy), (cx + 92 * math.cos(a2), cy + 92 * math.sin(a2))], fill=(30, 30, 30, 120 - k * 20), width=6)
    d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=(180, 40, 40, 255))
    # one desk lamp still on: its glow on him
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([300, 700, 780, 1300], fill=(170, 200, 255, 70))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(70)))
    d.rectangle([0, 1700, W, H], fill=(44, 46, 56, 255))
    return img


def env_for(t, kind, sky_bot):
    if kind == "street_dusk":
        return street_dusk_env(t, sky_bot)
    if kind == "office":
        return office_env(t)
    return m.draw_env(t, "street", sky_bot)


# ---------------------------------------------------------------- the old scooter (front view, in front of him)
def scooter_state(t):
    """(running, dead amount, headlight)"""
    if t < 11.9:
        return 1.0, 0.0, 1.0 if t >= 9.14 else 0.0
    flick = 1.0 if (t < 12.2 and int(t * 20) % 2) else 0.0
    return 0.0, clamp((t - 11.9) / 0.4), flick


def draw_scooter(layer, t):
    d = ImageDraw.Draw(layer)
    run, dead, light = scooter_state(t)
    bump = 4 * math.sin(t * 23) * run if t < 13.92 else 3 * abs(math.sin(t * 5))
    teal, teal_d = (78, 150, 150, 255), (52, 108, 110, 255)
    # front wheel + mudguard
    d.ellipse([480, 1460 + bump, 600, 1660 + bump], fill=(26, 26, 30, 255))
    d.ellipse([515, 1520 + bump, 565, 1600 + bump], fill=(130, 130, 140, 255))
    d.chord([466, 1430 + bump, 614, 1560 + bump], 180, 360, fill=teal)
    # floorboard and leg shield
    d.rectangle([380, 1520 + bump, 700, 1556 + bump], fill=(40, 40, 46, 255))
    d.polygon([(420, 1180 + bump), (660, 1180 + bump), (720, 1530 + bump), (360, 1530 + bump)], fill=teal, outline=(30, 60, 62, 255))
    d.polygon([(470, 1200 + bump), (610, 1200 + bump), (640, 1500 + bump), (440, 1500 + bump)], fill=teal_d)
    for k, (rx, ry) in enumerate(((400, 1440), (680, 1380), (450, 1260), (630, 1480))):   # rust
        d.ellipse([rx - 18, ry - 10 + bump, rx + 18, ry + 10 + bump], fill=(140, 84, 50, 200))
    # handlebar, mirrors, headlight
    d.line([(350, 1120 + bump), (730, 1120 + bump)], fill=(60, 60, 66, 255), width=20)
    for sx in (-1, 1):
        d.rounded_rectangle([540 + sx * 190 - 34, 1106 + bump, 540 + sx * 190 + 34, 1134 + bump], radius=10, fill=(30, 30, 34, 255))
        d.line([(540 + sx * 140, 1112 + bump), (540 + sx * 170, 1010 + bump)], fill=(80, 80, 88, 255), width=6)
        d.ellipse([540 + sx * 170 - 26, 980 + bump, 540 + sx * 170 + 26, 1020 + bump], fill=(170, 180, 196, 255), outline=(60, 60, 66, 255), width=4)
    d.polygon([(470, 1100 + bump), (610, 1100 + bump), (600, 1190 + bump), (480, 1190 + bump)], fill=teal)
    lcol = (255, 236, 170, 255) if light > 0.5 else (90, 90, 80, 255)
    d.ellipse([500, 1110 + bump, 580, 1180 + bump], fill=lcol, outline=(40, 40, 44, 255), width=6)
    if light > 0.5:
        g = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([380, 1000 + bump, 700, 1300 + bump], fill=(255, 236, 170, 120))
        layer.alpha_composite(g.filter(ImageFilter.GaussianBlur(30)))
    # exhaust smoke: small sputters while running, a big burst when it dies
    rr = random.Random(9)
    for k in range(14):
        ph = rr.random()
        if run > 0.5 and t >= 9.14:
            u = (t * 1.6 + ph) % 1
            a, rad = int(120 * (1 - u)), 20 + 50 * u
            sx, sy = 760 + 120 * u + rr.uniform(-20, 20), 1300 - 260 * u
        elif 11.9 <= t < 14.2:
            u = clamp((t - 11.9) / 2.0 + ph * 0.3)
            a, rad = int(170 * (1 - u)), 40 + 160 * u
            sx, sy = 540 + rr.uniform(-260, 260) * u, 1250 - 500 * u * rr.uniform(0.6, 1.2)
        else:
            continue
        d.ellipse([sx - rad, sy - rad, sx + rad, sy + rad], fill=(150, 150, 160, a))


def front_props(layer, t, kind):
    d = ImageDraw.Draw(layer)
    hand = m.LAST_HANDS
    if kind == "street_dusk" and "R" in hand and 2.5 <= t < 5.0:   # his phone
        x, y = hand["R"]
        d.rounded_rectangle([x - 34, y - 64, x + 34, y + 60], radius=10, fill=(24, 24, 30, 255), outline=(80, 80, 90, 255), width=3)
        if t < 3.44:
            g = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            ImageDraw.Draw(g).ellipse([x - 160, y - 300, x + 160, y + 40], fill=(170, 200, 255, 80))
            layer.alpha_composite(g.filter(ImageFilter.GaussianBlur(40)))
        if 3.44 <= t < 3.95:   # ringing
            for k in range(3):
                r = 60 + k * 26 + (t * 120) % 26
                d.arc([x - r, y - r, x + r, y + r], 300, 360, fill=(255, 255, 255, 220), width=5)
                d.arc([x - r, y - r, x + r, y + r], 180, 240, fill=(255, 255, 255, 220), width=5)
    if kind == "office":   # desk: laptop from behind, piles of files, coffee
        d.rectangle([0, 1330, W, 1720], fill=(96, 84, 74, 255))
        d.rectangle([0, 1330, W, 1350], fill=(124, 110, 98, 255))
        d.polygon([(400, 1150), (680, 1150), (700, 1336), (380, 1336)], fill=(190, 196, 206, 255), outline=(110, 116, 126, 255))
        d.ellipse([524, 1224, 556, 1256], fill=(240, 244, 255, 255))
        for x0, n in ((80, 9), (820, 12)):
            for k in range(n):
                col = ((236, 226, 196), (210, 220, 236), (240, 210, 170))[k % 3]
                d.rectangle([x0 + (k % 2) * 6, 1320 - k * 22, x0 + 180 + (k % 2) * 6, 1340 - k * 22], fill=col + (255,), outline=(150, 140, 120, 255))
        for k, mx in enumerate((300, 740)):
            d.rectangle([mx, 1270, mx + 50, 1334], fill=(240, 240, 236, 255))
            d.arc([mx + 40, 1282, mx + 66, 1314], 270, 90, fill=(240, 240, 236, 255), width=6)
    if kind == "street_night":
        draw_scooter(layer, t)


rnd = random.Random(15)
RAIN = [(rnd.uniform(-200, W + 200), rnd.uniform(0, H), rnd.uniform(1500, 2200), rnd.uniform(50, 100)) for _ in range(260)]


def fx_layer(t, kind):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if kind == "street_night" and t >= 13.92:
        for x, y, sp, ln in RAIN:
            yy = (y + t * sp) % (H + 200) - 100
            xx = x - yy * 0.1
            d.line([(xx, yy), (xx - ln * 0.1, yy - ln)], fill=(190, 210, 255, 120), width=2)
    for x, y, s_, sp, ph in m.DUST:
        py_ = (y - t * sp * 0.5) % H
        px_ = x + 24 * math.sin(t * 0.7 + ph)
        d.ellipse([px_ - s_, py_ - s_, px_ + s_, py_ + s_], fill=(255, 235, 210, 36))
    return layer.filter(ImageFilter.GaussianBlur(1.0))


def draw_signs(t, layer, cam, head):
    d = ImageDraw.Draw(layer)
    if 2.75 <= t < 3.44:   # dream bubble: the beach trip with friends
        u = (t - 2.75) / 0.69
        q = back_out(u / 0.3) if u < 0.3 else 1.0
        a = int(240 * (1 - smooth((u - 0.82) / 0.18)))
        bx, by, r = 800, 610, 150 * q
        for ox, oy, rr in ((-200, 280, 16), (-150, 215, 26)):
            d.ellipse([bx + ox - rr, by + oy - rr, bx + ox + rr, by + oy + rr], fill=(255, 255, 255, a))
        d.ellipse([bx - r * 1.25, by - r, bx + r * 1.25, by + r], fill=(255, 255, 255, a), outline=(200, 210, 230, a), width=4)
        if q > 0.6:
            d.chord([bx - 150, by - 90, bx + 150, by + 40], 180, 360, fill=(255, 190, 120, a))
            d.ellipse([bx - 40, by - 70, bx + 40, by + 10], fill=(255, 150, 60, a))
            d.rectangle([bx - 150, by - 26, bx + 150, by + 40], fill=(70, 150, 210, a))
            d.rectangle([bx - 150, by + 40, bx + 150, by + 90], fill=(240, 214, 160, a))
            d.line([(bx + 90, by + 70), (bx + 110, by - 70)], fill=(110, 76, 46, a), width=8)
            for k in range(4):
                ang = math.pi + k * 0.5
                d.line([(bx + 110, by - 70), (bx + 110 + 60 * math.cos(ang - 0.3), by - 70 + 40 * math.sin(ang - 0.3) + 20)],
                       fill=(60, 140, 70, a), width=8)
            for k in range(3):
                fx = bx - 90 + k * 50
                jy = by + 50 - 14 * abs(math.sin(t * 8 + k))
                d.ellipse([fx - 9, jy - 40, fx + 9, jy - 22], fill=(30, 30, 40, a))
                d.line([(fx, jy - 22), (fx, jy + 10)], fill=(30, 30, 40, a), width=8)


def scene_frame(t, cam, kind):
    top, bot, _ = m.light_at(t)
    sky = np.array(top, np.float32) * (1 - m.GRAD_Y) + np.array(bot, np.float32) * m.GRAD_Y
    frame = Image.fromarray(np.broadcast_to(sky, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    frame.alpha_composite(m.cam_transform(env_for(t, kind, bot), 0.9, cam))
    char_img, origin, head = m.draw_character(t)
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
    rng = np.random.default_rng(int(t * 1000) + 9)
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
        kg.draw_lyrics(out, t, occ)
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
