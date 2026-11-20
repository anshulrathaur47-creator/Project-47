"""Emotional reel on "किसी के ना होने का एहसास सबको है, मगर मौजूदगी की कदर किसी को नहीं"
(assets/music/ReelAudio-38965.mp3, 12.4 s).

  0.0  night, a dining room: his chair is empty, his grey hoodie hangs on it, his glasses and a cold
       cup of tea lie on the table; the others sit with their heads down
  3.1  "किसी के ना होने का एहसास सबको है": they look at the empty chair, one reaches for it; an aching heart
  5.5  the camera pushes into his photo on the wall: flashback (warm, sepia)
  6.6  "मगर मौजूदगी की कदर किसी को नहीं": he sits there, waving, talking, smiling; everyone is on their phone;
       nobody looks; his smile fades and he slowly turns see-through
  9.1  now again: his ghost stands behind his own chair, watching them, then dissolves into light

Same character and rig as the "शक्ल" reel (glasses, freckles, grey hoodie): this script imports
../2026-11-20-shakal-sad/make_shakal.py (which imports the 19 Nov rig) and replaces the story.
No text on screen: the user asked for no lyrics (the word timings are kept in CHUNKS).

Usage: python3 make_kadar.py [--frames 30,150,...] [--workers 4]
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
AUDIO = os.path.join(HERE, "..", "..", "assets", "music", "ReelAudio-38965.mp3")
OUT = os.path.join(HERE, "kadar.mp4")
SILENT = os.path.join(HERE, "_kadar_silent.mp4")
DUR = 12.38
K = m.K
FB = (6.60, 9.10)          # the flashback
TABLE_Y = 1330             # table top (world y)

# ==============================================================================================
# words
# ==============================================================================================
WHITE, PINK, GOLD, GLASS, RED = sk.WHITE, sk.PINK, sk.GOLD, sk.GLASS, sk.RED
sk.CHUNKS = [
    ([("वो", 0.40), ("कहते", 0.60), ("हैं", 0.86), ("ना", 0.98), ("कि", 1.18)], "soft", 112, {}, 2.95, None),
    ([("किसी", 3.12), ("के", 3.32), ("ना", 3.42), ("होने", 3.66), ("का", 4.08)], "soft", 112, {"होने": GLASS}, 4.26, None),
    ([("एहसास", 4.28), ("सबको", 4.80), ("है", 5.24)], "soft", 124, {"एहसास": PINK}, 6.3, None),
    ([("मगर", 6.60), ("मौजूदगी", 6.88), ("की", 7.56)], "warm", 120, {"मौजूदगी": GOLD}, 7.66, None),
    ([("कदर", 7.68), ("किसी", 8.08), ("को", 8.42), ("नहीं", 8.58)], "dissolve", 116, {"कदर": GOLD, "नहीं": RED},
     10.0, 9.55),
]
sk.GLOW["warm"] = (255, 170, 90)
sk.BASE["warm"] = (255, 240, 220)
m.Y_CANDIDATES = (330, 450, 1500, 220)
m.CHUNK_Y.clear()

# ==============================================================================================
# acting (he only exists in the flashback, and as a ghost at the end)
# ==============================================================================================
T = dict(sk.T)
T.update({
    "walk": [(0, 0)], "speed": [(0, 0)], "swag": [(0, 0)], "shake": [(0, 0)], "cry": [(0, 0)],
    "sink": [(0, 160), (9.09, 160), (9.1, 0)],
    "slump": [(0, 0), (7.7, 0), (8.6, 0.45), (9.09, 0.45), (9.1, 0.3)],
    "head_dy": [(0, 0), (7.8, 0), (8.6, 14), (9.09, 14), (9.1, 6)],
    "tilt": [(0, 0), (6.6, 3), (7.2, -3), (7.7, 2), (8.6, -4), (9.1, -3), (12.4, -5)],
    "look": [(0, (0, 0)), (6.6, (-0.6, 0)), (7.1, (0.6, 0)), (7.6, (-0.4, 0.1)), (8.2, (0, 0.55)),
             (9.1, (-0.45, 0.35)), (10.4, (0.45, 0.35)), (11.2, (0, -0.4))],
    "lid": [(0, 0), (7.8, 0), (8.6, 0.32), (9.1, 0.35), (12.4, 0.4)],
    "happy": [(0, 0), (6.6, 1), (7.05, 1), (7.08, 0)],
    "brow": [(0, 0), (7.7, 0), (8.5, 0.85), (40, 0.9)],
    "tear": sk.saw(8.4, 40, 1.4),
    "tear_a": [(0, 0), (8.3, 0), (8.8, 1), (40, 1)],
    "blush": [(0, 0.3), (7.6, 0.3), (8.0, 0), (40, 0)],
    "laugh": [(0, 0)],
    "desat": [(0, 0.35), (6.59, 0.35), (6.6, 0.12), (9.09, 0.2), (9.1, 0.4), (12.4, 0.45)],
})
MOUTH = ([(0, "flat")] + [(6.6 + k * 0.18, "hum" if k % 2 else "smile") for k in range(6)] +
         [(7.7, "smile"), (8.0, "flat"), (8.5, "frown"), (9.1, "flat"), (10.3, "smile"), (11.0, "flat")])
TABLE_L, TABLE_R = ("hip", -96, -86), ("hip", 96, -86)
HAND_L = [(0, TABLE_L), (40, TABLE_L)]
HAND_R = [(0, TABLE_R), (6.6, ("wave",)), (7.6, ("wave",)), (7.95, TABLE_R), (40, TABLE_R)]
m.T, m.MOUTH, m.HAND_L, m.HAND_R = T, MOUTH, HAND_L, HAND_R


def presence(t):
    """How much of him is there: solid in the flashback, fading as nobody looks, then a faint ghost."""
    if t < FB[0]:
        return 0.0
    if t < FB[1]:
        return lerp(1.0, 0.3, smooth((t - 7.9) / 1.0))
    if t < 10.52:
        return 0.48 * smooth((t - 9.1) / 0.4) + 0.05 * math.sin(t * 9)
    return 0.48 * (1 - smooth((t - 10.6) / 0.9))


_sk_char = m.draw_character


def draw_character(t):
    pr = presence(t)
    if pr <= 0.01:
        return Image.new("RGBA", (4, 4), (0, 0, 0, 0)), (0, 0), (540, 924)
    img, origin, head = _sk_char(t)
    a = img.getchannel("A")
    if t >= FB[1]:   # ghost: cool glow around a see-through body
        small = a.resize((a.width // 8, a.height // 8)).filter(ImageFilter.GaussianBlur(3)).resize(a.size, Image.BILINEAR)
        glow = Image.new("RGBA", img.size, (150, 190, 255, 0))
        glow.putalpha(small.point(lambda v: int(v * 0.8)))
        img = img.convert("RGBA")
        tint = Image.new("RGBA", img.size, (170, 200, 255, 0))
        tint.putalpha(a.point(lambda v: int(v * 0.35)))
        img.alpha_composite(tint)
        img.putalpha(a.point(lambda v: int(v * pr)))
        glow.alpha_composite(img)
        return glow, origin, head
    img.putalpha(a.point(lambda v: int(v * pr)))
    return img, origin, head


m.draw_character = draw_character

# ==============================================================================================
# place, light, camera
# ==============================================================================================
m.LOCATIONS = [(0.0, "dining")]
m.LIGHT = [
    (0.0, ((14, 18, 30), (40, 46, 62), (0.9, 0.95, 1.06))),
    (6.59, ((14, 18, 30), (40, 46, 62), (0.9, 0.95, 1.06))),
    (6.6, ((60, 44, 30), (130, 96, 64), (1.12, 1.0, 0.8))),
    (9.09, ((60, 44, 30), (130, 96, 64), (1.1, 0.98, 0.82))),
    (9.1, ((10, 14, 26), (34, 40, 56), (0.88, 0.94, 1.08))),
    (12.4, ((10, 14, 26), (34, 40, 56), (0.86, 0.92, 1.08))),
]
m.SHOTS = [
    (0.00, 1.93, (2.80, 0, 250, 0), (3.00, 0, 255, 0), "fade"),          # his glasses, the cold tea
    (1.93, 3.12, (1.00, 0, -40, 0), (1.05, 0, -60, 0), "cut"),           # the table, the empty chair
    (3.12, 4.28, (1.60, -170, -150, 0), (1.70, -180, -160, 0), "cut"),   # they look at it, one reaches out
    (4.28, 5.48, (1.90, 0, -120, 0), (2.10, 0, -130, 0), "cut"),         # the empty chair, an aching heart
    (5.48, 6.60, (1.50, 300, -535, 0), (3.30, 300, -535, 0), "cut"),     # push into his photo
    (6.60, 7.68, (1.25, 0, -170, 0), (1.35, 0, -190, 0), "flash"),       # flashback: he is there
    (7.68, 9.10, (2.30, 0, -176, 0), (2.60, 0, -180, 0), "cut"),         # nobody looks; he fades
    (9.10, 10.52, (1.15, 0, -120, 0), (1.22, 0, -140, 0), "flash"),      # now: his ghost by his chair
    (10.52, 12.38, (1.55, 0, -260, 0), (1.00, 0, -40, 0), "cut"),        # he dissolves, pull back
]
m.OTS = []
m.DURATION = DUR

rnd = random.Random(8)
RAIN_W = [(rnd.uniform(40, 330), rnd.uniform(380, 900), rnd.uniform(500, 900)) for _ in range(40)]
SEATS = [(120, 0.86, -1), (285, 0.92, -1), (795, 0.92, 1), (960, 0.86, 1)]   # x, scale, side


def draw_face_photo(d, x, y, s):
    """A little portrait of him smiling (for the frame on the wall)."""
    d.rectangle([x - 70 * s, y - 80 * s, x + 70 * s, y + 90 * s], fill=(70, 96, 130, 255))
    d.ellipse([x - 44 * s, y - 40 * s, x + 44 * s, y + 52 * s], fill=(250, 222, 200, 255))
    pts = []
    for k in range(13):
        ang = math.radians(170 + k * 200 / 12)
        r = 50 * s if k % 2 == 0 else 62 * s
        pts.append((x + r * math.cos(ang), y - 8 * s + r * math.sin(ang)))
    d.polygon(pts + [(x + 46 * s, y - 2 * s), (x - 46 * s, y - 2 * s)], fill=(30, 30, 46, 255))
    for sx in (-1, 1):
        d.ellipse([x + sx * 18 * s - 13 * s, y + 4 * s, x + sx * 18 * s + 13 * s, y + 28 * s], outline=(36, 34, 46, 255), width=max(2, int(3 * s)))
        d.arc([x + sx * 18 * s - 7 * s, y + 10 * s, x + sx * 18 * s + 7 * s, y + 20 * s], 200, 340, fill=(30, 30, 40, 255), width=max(2, int(3 * s)))
    d.arc([x - 16 * s, y + 24 * s, x + 16 * s, y + 42 * s], 20, 160, fill=(120, 40, 50, 255), width=max(2, int(3 * s)))
    d.rectangle([x - 70 * s, y + 70 * s, x + 70 * s, y + 90 * s], fill=(92, 98, 120, 255))


def chair_back(d, a=255):
    d.rounded_rectangle([400, 990, 680, 1345], radius=26, fill=(70, 46, 36, a), outline=(40, 26, 20, a), width=6)
    for x in (460, 540, 620):
        d.rectangle([x - 14, 1040, x + 14, 1300], fill=(52, 34, 26, a))


def dining_env(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 8):
        f = y / H
        d.rectangle([0, y, W, y + 8], fill=(int(lerp(52, 30, f)), int(lerp(58, 34, f)), int(lerp(74, 44, f)), 255))
    for x in range(0, W, 120):
        d.line([(x, 0), (x, 1700)], fill=(60, 66, 84, 255), width=2)
    # window with rain
    d.rectangle([22, 362, 348, 918], fill=(20, 20, 28, 255))
    d.rectangle([40, 380, 330, 900], fill=(22, 30, 58, 255))
    for x, y, sp in RAIN_W:
        yy = 380 + (y - 380 + t * sp) % 520
        d.line([(x, yy), (x - 4, yy - 26)], fill=(150, 170, 220, 160), width=2)
    d.line([(185, 380), (185, 900)], fill=(20, 20, 28, 255), width=10)
    d.line([(40, 640), (330, 640)], fill=(20, 20, 28, 255), width=10)
    # his photo on the wall
    d.rectangle([742, 452, 938, 698], fill=(150, 120, 80, 255))
    d.rectangle([756, 466, 924, 684], fill=(18, 18, 24, 255))
    draw_face_photo(d, 840, 572, 1.08)
    # hanging lamp + its cone of light
    d.line([(540, 0), (540, 300)], fill=(20, 20, 26, 255), width=4)
    d.polygon([(486, 300), (594, 300), (630, 372), (450, 372)], fill=(60, 50, 40, 255))
    cone = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cone)
    cd.polygon([(462, 372), (618, 372), (1000, TABLE_Y + 40), (80, TABLE_Y + 40)], fill=(255, 210, 150, 46))
    cd.ellipse([500, 352, 580, 392], fill=(255, 236, 190, 255))
    img.alpha_composite(cone.filter(ImageFilter.GaussianBlur(24)))
    # floor
    d.rectangle([0, 1700, W, H], fill=(36, 28, 30, 255))
    # his chair (behind him) and, while he is gone, his hoodie hanging on it
    chair_back(d)
    if not (FB[0] <= t < FB[1]):
        hood = (92, 98, 120, 255)
        d.polygon([(410, 1000), (670, 1000), (690, 1080), (650, 1180), (430, 1180), (390, 1080)], fill=hood)
        d.polygon([(400, 1060), (440, 1080), (430, 1320), (392, 1310)], fill=(80, 86, 106, 255))
        d.polygon([(680, 1060), (640, 1080), (650, 1320), (688, 1310)], fill=(80, 86, 106, 255))
        d.arc([470, 960, 610, 1060], 0, 180, fill=(64, 68, 90, 255), width=14)
        d.line([(520, 1040), (516, 1110)], fill=(230, 230, 236, 255), width=4)
        d.line([(560, 1040), (564, 1110)], fill=(230, 230, 236, 255), width=4)
    # a warm glow around him while he is there ("मौजूदगी")
    aura = clamp((t - 6.88) / 0.3) * (1 - smooth((t - 7.9) / 1.0)) if FB[0] <= t < FB[1] else 0.0
    if aura > 0.01:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([300, 520, 780, 1360], fill=(255, 200, 120, int(150 * aura)))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
    return img


_orig_env = m.draw_env


def draw_env(t, kind, sky_bot):
    return dining_env(t) if kind == "dining" else _orig_env(t, kind, sky_bot)


m.draw_env = draw_env


def seated(d, x, sc, side, t, phone=False, reach=0.0, bow=0.0):
    """A faceless person sitting at the table; side = which way the centre (his chair) is (+1 = right)."""
    col = sk.SIL + (240,)
    toward = -side   # direction towards the centre of the table
    hx = x + toward * 14 * bow
    hy = TABLE_Y - 560 * sc + 40 * bow
    d.polygon([(x - 92 * sc, TABLE_Y - 420 * sc), (x + 92 * sc, TABLE_Y - 420 * sc), (x + 100 * sc, TABLE_Y + 10),
               (x - 100 * sc, TABLE_Y + 10)], fill=col)
    d.ellipse([x - 96 * sc, TABLE_Y - 450 * sc, x - 36 * sc, TABLE_Y - 380 * sc], fill=col)
    d.ellipse([x + 36 * sc, TABLE_Y - 450 * sc, x + 96 * sc, TABLE_Y - 380 * sc], fill=col)
    d.ellipse([hx - 52 * sc, hy - 60 * sc, hx + 52 * sc, hy + 60 * sc], fill=col)
    d.rectangle([x - 22 * sc, hy + 40 * sc, x + 22 * sc, TABLE_Y - 420 * sc], fill=col)
    if phone:   # head down over a glowing phone
        px, py = x + toward * 20 * sc, TABLE_Y - 230 * sc
        for r, al in ((150, 26), (100, 40), (60, 60)):
            d.ellipse([px - r * sc, py - r * sc * 1.4 - 60 * sc, px + r * sc, py + r * sc * 0.6 - 60 * sc],
                      fill=(170, 210, 255, al))
        d.line([(x - 60 * sc, TABLE_Y - 380 * sc), (px - 18 * sc, py + 30 * sc)], fill=col, width=int(30 * sc))
        d.line([(x + 60 * sc, TABLE_Y - 380 * sc), (px + 18 * sc, py + 30 * sc)], fill=col, width=int(30 * sc))
        fl = 0.8 + 0.2 * math.sin(t * 13 + x)
        d.rounded_rectangle([px - 26 * sc, py - 46 * sc, px + 26 * sc, py + 46 * sc], radius=int(8 * sc),
                            fill=(int(200 * fl), int(228 * fl), 255, 255))
    if reach > 0.01:   # an arm stretching to his empty chair
        sx, sy = x + toward * 80 * sc, TABLE_Y - 400 * sc
        ex, ey = lerp(sx + toward * 60, 410 if toward > 0 else 670, reach), lerp(sy + 140, 1130, reach)
        d.line([(sx, sy), (ex, ey)], fill=col, width=int(34 * sc))
        d.ellipse([ex - 24, ey - 24, ex + 24, ey + 24], fill=col)


def front_props(layer, t, inner=False):
    d = ImageDraw.Draw(layer)
    flash_back = FB[0] <= t < FB[1]
    for i, (x, sc, side) in enumerate(SEATS):
        reach = smooth((t - 3.3) / 0.6) * (1 - smooth((t - 5.6) / 0.4)) if (i == 1 and t < 6.6) else 0.0
        bow = 1.0 if not flash_back else 0.6
        seated(d, x, sc, side, t, phone=flash_back, reach=reach, bow=bow)
    if 9.1 <= t:   # his chair in front of his ghost
        chair_back(d, 235)
    # the table
    d.polygon([(30, TABLE_Y), (1050, TABLE_Y), (1080, TABLE_Y + 60), (0, TABLE_Y + 60)], fill=(226, 222, 214, 255))
    d.rectangle([0, TABLE_Y + 60, W, 1720], fill=(196, 190, 182, 255))
    for x in range(30, W, 90):
        d.line([(x, TABLE_Y + 60), (x + 10, 1720)], fill=(180, 174, 166, 255), width=3)
    d.rectangle([0, TABLE_Y + 56, W, TABLE_Y + 66], fill=(170, 164, 156, 255))
    for x in (160, 330, 750, 920):   # plates
        d.ellipse([x - 70, TABLE_Y + 8, x + 70, TABLE_Y + 46], fill=(250, 250, 252, 255), outline=(200, 200, 205, 255), width=3)
    d.ellipse([470, TABLE_Y + 8, 610, TABLE_Y + 46], fill=(250, 250, 252, 255), outline=(200, 200, 205, 255), width=3)
    # his cup; steam only while he is there
    d.rectangle([640, TABLE_Y - 34, 690, TABLE_Y + 22], fill=(240, 236, 228, 255))
    d.arc([680, TABLE_Y - 24, 708, TABLE_Y + 6], 270, 90, fill=(240, 236, 228, 255), width=6)
    if flash_back:
        for k in range(3):
            u = (t * 0.7 + k / 3) % 1
            d.line([(655 + k * 10 + 8 * math.sin(u * 8), TABLE_Y - 40 - u * 90),
                    (660 + k * 10 + 8 * math.sin(u * 8 + 1), TABLE_Y - 60 - u * 90)],
                   fill=(255, 255, 255, int(120 * (1 - u))), width=4)
    # his glasses on the table when he is gone
    if not flash_back:
        g = (30, 30, 40, 255)
        for sx in (-1, 1):
            d.ellipse([540 + sx * 40 - 30, TABLE_Y + 10, 540 + sx * 40 + 30, TABLE_Y + 40], outline=g, width=5)
            d.line([(540 + sx * 70, TABLE_Y + 22), (540 + sx * 92, TABLE_Y + 6)], fill=g, width=4)
        d.arc([528, TABLE_Y + 14, 552, TABLE_Y + 28], 180, 360, fill=g, width=4)
        glint = 0.5 + 0.5 * math.sin(t * 2.5)
        d.line([(486, TABLE_Y + 16), (500, TABLE_Y + 12)], fill=(255, 255, 255, int(200 * glint)), width=3)


def fx_layer(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, s_, sp, ph in m.DUST:   # dust in the lamp light
        py_ = (y - t * sp * 0.6) % H
        px_ = x + 24 * math.sin(t * 0.7 + ph)
        if 360 < py_ < TABLE_Y and abs(px_ - 540) < 120 + (py_ - 372) * 0.45:
            d.ellipse([px_ - s_, py_ - s_, px_ + s_, py_ + s_], fill=(255, 230, 190, 70))
    return layer.filter(ImageFilter.GaussianBlur(1.0))


m.front_props, m.fx_layer = front_props, fx_layer


# ==============================================================================================
# signs
# ==============================================================================================
def draw_signs(t, layer, cam, head):
    d = ImageDraw.Draw(layer)
    to_s, zd = m.world_to_screen(cam)
    # "एहसास": an aching heart over the empty chair, beating twice and cracking
    if 4.28 <= t < 5.9:
        dt = t - 4.28
        a = int(230 * clamp(dt / 0.15) * (1 - smooth((dt - 1.25) / 0.35)))
        x, y = to_s(540, 900)
        beat = 1 + 0.12 * (math.exp(-((dt - 0.25) / 0.08) ** 2) + math.exp(-((dt - 0.6) / 0.08) ** 2))
        s = 5.2 * zd / 1.9 * beat
        sk.heart(d, x, y, s, col=(230, 80, 110), a=a)
        if dt > 0.8:
            crack = [(0, -5), (-3, -1), (3, 3), (-2, 7), (0, 12)]
            d.line([(x + cx * s, y + cy * s) for cx, cy in crack], fill=(50, 0, 20, a), width=max(3, int(s * 0.5)))
    # he dissolves into light
    if 10.4 <= t < 12.38:
        hx, hy = to_s(head[0], head[1])
        rr = random.Random(3)
        for k in range(90):
            t0 = 10.45 + rr.uniform(0, 1.0)
            u = (t - t0) / 1.4
            if not 0 < u < 1:
                continue
            ox, oy = rr.uniform(-180, 180), rr.uniform(-120, 620)
            px = hx + (ox + 30 * math.sin(u * 6 + k)) * zd / 1.3
            py = hy + (oy - 420 * u) * zd / 1.3
            r_ = rr.uniform(3, 7) * (1 - u * 0.5)
            al = int(230 * math.sin(math.pi * u))
            d.ellipse([px - r_ * 2.4, py - r_ * 2.4, px + r_ * 2.4, py + r_ * 2.4], fill=(170, 205, 255, al // 4))
            d.ellipse([px - r_, py - r_, px + r_, py + r_], fill=(225, 240, 255, al))


m.draw_signs = draw_signs


# ==============================================================================================
# frame
# ==============================================================================================
def render_frame(t):
    rng = np.random.default_rng(int(t * 1000) + 11)
    _, _, tint = m.light_at(t)
    cam = m.camera_at(t)
    frame, char_l, flag_l, head = m.render_scene(t, cam)
    signs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_signs(t, signs, cam, head)
    frame.alpha_composite(signs.filter(ImageFilter.GaussianBlur(12)))
    frame.alpha_composite(signs)
    cm = np.asarray(char_l.getchannel("A").resize((W // 8, H // 8))) > 40
    om = np.asarray(signs.getchannel("A").resize((W // 8, H // 8))) > 40
    occ = (cm.astype(np.float32), om.astype(np.float32))
    blur, bright, flash = m.transition_fx(t)
    arr = np.asarray(frame.convert("RGB")).astype(np.float32) * np.array(tint, np.float32)
    de = track(T["desat"], t)
    if de > 0.01:
        lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
        arr = arr * (1 - de) + lum[:, :, None] * de
    for rt in (FB[0], FB[1]):   # memory ripple in and out of the flashback
        r = 1 - abs(t - rt) / 0.4
        if r > 0:
            amp = 30 * r * r
            shift = (amp * np.sin(np.arange(H) / 36.0 + t * 30)).astype(int)
            arr = np.stack([np.roll(arr[y], shift[y], axis=0) for y in range(H)])
    if FB[0] <= t < FB[1]:   # old-photo feel: soft halation
        arr = arr * 0.92 + 18
    if flash > 0.01:
        arr = arr + (255 - arr) * flash * 0.8
    arr *= m.VIGNETTE * bright
    arr += rng.normal(0, 4.0 if FB[0] <= t < FB[1] else 3.2, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))   # no words on screen (user: "No lyrics")
    fade = min(clamp(t / 0.35), clamp((DUR - t) / 0.9))
    if fade < 1:
        out = Image.blend(Image.new("RGB", (W, H)), out, fade)
    return out


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
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={DUR - 0.6:.2f}:d=0.6",
                    "-t", f"{DUR:.2f}", "-movflags", "+faststart", OUT], check=True)
    os.remove(SILENT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
