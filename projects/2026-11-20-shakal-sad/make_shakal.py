"""Sad reel on the "इस चेहरे के साथ..." monologue (assets/music/ReelAudio-51331.mp3).

A shy anime boy (round glasses, freckles, grey hoodie) acts out what is said to him and what he feels:
  0.0  he walks down a sunset street with a rose; a girl (silhouette) turns away; the heart cracks
  3.7  night: faceless people point and laugh at him ("बदसूरत"); the rose falls
  5.7  park: he waves at kids, they and the grown-ups see him and run away
  9.0  bathroom mirror: he looks at himself, the mirror cracks, he hides his face in shame
 12.1  walking alone in the rain, head down; he tries on a smiling mask and lets it fall
 16.7  under a huge moon he looks up, crying; last close-up, eyes close, fade out

Only the spoken words are on screen, word by word with a soft neon glow, placed in a band clear of
the boy (top or lower third). Rig, scenes and camera come from
projects/2026-11-16-remember-19-nov/make_19nov.py (imported; its timeline is replaced here).

Usage: python3 make_shakal.py [--frames 30,150,...] [--workers 4]
"""
import math
import multiprocessing as mp
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "2026-11-16-remember-19-nov"))
import make_19nov as m  # noqa: E402

clamp, smooth, lerp, ease_out, back_out, track, step = m.clamp, m.smooth, m.lerp, m.ease_out, m.back_out, m.track, m.step
W, H, FPS = 1080, 1920, 30
AUDIO = os.path.join(HERE, "..", "..", "assets", "music", "ReelAudio-51331.mp3")
OUT = os.path.join(HERE, "shakal_sad.mp4")
SILENT = os.path.join(HERE, "_shakal_silent.mp4")
DUR = 19.93
BEAT0, BEAT = 0.28, 0.60
K = m.K
GROUND = m.GROUND

# ==============================================================================================
# words (Whisper, given the transcript as a hint; see notes.md)
# ==============================================================================================
WHITE, PINK, RED, GOLD, GLASS, GREY = ((240, 242, 252), (255, 150, 190), (255, 92, 104), (255, 205, 110),
                                       (190, 230, 255), (175, 180, 198))
# (words with start times, style, size, colours, end, extra time for breaking styles)
CHUNKS = [
    ([("इस", 0.27), ("चेहरे", 0.81), ("के", 1.19), ("साथ", 1.35)], "soft", 112, {}, 1.55, None),
    ([("तुम्हें", 1.57), ("कोई", 1.95), ("लड़की", 2.13)], "soft", 116, {"लड़की": PINK}, 2.47, None),
    ([("क्यों", 2.49), ("ही", 2.89), ("पसंद", 2.91), ("करेगी?", 3.27)], "soft", 112, {"पसंद": PINK}, 3.71, None),
    ([("तुम", 3.73), ("इतने", 3.89)], "slam", 124, {}, 4.23, None),
    ([("बदसूरत", 4.25), ("लगते", 4.69), ("हो", 5.03)], "shatter", 120, {"बदसूरत": RED}, 5.69, 5.32),
    ([("यहाँ", 5.71), ("बच्चे", 5.97), ("तो", 6.31), ("बच्चे", 6.43)], "soft", 112, {}, 6.75, None),
    ([("बड़े", 6.77), ("भी", 7.07), ("तुम्हें", 7.17)], "soft", 116, {}, 7.41, None),
    ([("देखकर", 7.43), ("भाग", 7.75), ("डरते", 8.09), ("हैं", 8.39)], "slam", 112, {"डरते": RED}, 8.99, None),
    ([("अपनी", 9.01), ("शक्ल", 9.37), ("और", 9.83)], "mirror", 120, {"शक्ल": WHITE}, 10.09, None),
    ([("अपनी", 10.11), ("हालातों", 10.37), ("को", 10.95)], "mirror", 112, {}, 11.05, None),
    ([("देख", 11.07), ("मुझे", 11.33), ("शर्म", 11.62), ("आती", 11.85), ("है", 12.0)], "soft", 100,
     {"शर्म": RED}, 12.12, None),
    ([("वो", 12.14), ("कैसी", 12.78), ("ज़िंदगी", 13.42)], "rain", 116, {"ज़िंदगी": GOLD}, 13.82, None),
    ([("जीऊँ", 13.84), ("मैं?", 14.18)], "rain", 128, {}, 14.46, None),
    ([("वो", 14.48), ("कैसा", 14.64), ("इंसान", 15.04)], "rain", 116, {"इंसान": GOLD}, 15.54, None),
    ([("बन", 15.56), ("जाऊँ", 15.74), ("मैं", 16.04)], "rain", 124, {}, 16.66, None),
    ([("जहाँ", 16.68), ("मैं", 16.96), ("दिखता", 17.1), ("कैसा", 17.44), ("हूँ", 17.82)], "soft", 100,
     {"दिखता": GLASS}, 18.32, None),
    ([("वो", 18.34), ("ज़्यादा", 18.44), ("मायने", 18.82)], "soft", 116, {"मायने": GOLD}, 19.1, None),
    ([("रखता", 19.12), ("है", 19.44)], "dissolve", 124, {}, 19.93, 19.62),
]
GLOW = {"soft": (120, 150, 255), "slam": (255, 120, 120), "shatter": (255, 60, 80), "mirror": (120, 200, 255),
        "rain": (110, 130, 200), "dissolve": (130, 140, 190)}
BASE = {"soft": WHITE, "slam": WHITE, "shatter": WHITE, "mirror": GLASS, "rain": GREY, "dissolve": GREY}
m.Y_CANDIDATES = (330, 450, 1500, 220)

# ==============================================================================================
# acting
# ==============================================================================================


def saw(t0, t1, period):
    keys, t = [(0, 0)], t0
    while t < t1:
        keys += [(t, 0), (t + period * 0.97, 1), (t + period, 0)]
        t += period
    return keys


T = {
    "stand": [(0, 1)], "sink": [(0, 0)], "crown": [(0, 0)], "hp": [(0, 0)], "paint": [(0, 0)],
    "walk": [(0, 1), (1.45, 1), (1.75, 0), (12.14, 0), (12.15, 1), (14.8, 1), (15.1, 0)],
    "speed": [(0, 1.1), (1.45, 1.1), (1.75, 0), (12.14, 0), (12.15, 0.75), (14.8, 0.75), (15.1, 0)],
    "swag": [(0, 0.15), (1.5, 0.15), (1.6, 0)],
    "slump": [(0, 0), (3.7, 0), (4.3, 0.5), (5.6, 0.5), (5.8, 0.15), (7.5, 0.15), (8.6, 0.5), (11.5, 0.5),
              (12.0, 0.7), (12.14, 0.8), (16.6, 0.8), (16.8, 0.4), (40, 0.4)],
    "head_dy": [(0, 0), (3.2, 0), (3.6, 10), (4.25, 10), (4.5, 26), (5.6, 26), (5.8, 0), (8.2, 0), (8.8, 16),
                (11.5, 16), (11.7, 24), (12.14, 26), (16.6, 26), (16.8, -10), (40, -10)],
    "tilt": [(0, 0), (1.6, 0), (1.9, 4), (2.9, 4), (3.4, -2), (4.25, -2), (4.5, -9), (5.6, -9), (5.8, 3),
             (7.4, 3), (8.0, 0), (11.6, 0), (11.8, -4), (12.14, -3), (16.6, -3), (16.8, 2), (18.3, 2),
             (18.4, -3), (19.9, -5)],
    "shake": [(0, 0), (4.3, 0), (4.4, 0.18), (5.5, 0.18), (5.6, 0)],
    "look": [(0, (0, 0)), (1.6, (0, 0)), (1.8, (0.65, 0)), (3.0, (0.65, 0)), (3.4, (0, 0.6)), (3.73, (-0.7, 0)),
             (4.0, (0.7, 0)), (4.25, (0, 0.3)), (5.71, (0.55, 0.1)), (6.7, (-0.55, 0.1)), (7.4, (0, 0)),
             (8.4, (0, 0.5)), (9.0, (0, 0)), (12.14, (0, 0.7)), (15.0, (0, 0.2)), (16.0, (0, 0.6)),
             (16.68, (0, -0.85)), (19.9, (0, -0.85))],
    "lid": [(0, 0), (3.2, 0), (3.6, 0.25), (4.25, 0.25), (4.3, 1.0), (5.3, 1.0), (5.6, 0.3), (5.8, 0),
            (7.5, 0), (8.6, 0.35), (11.5, 0.35), (12.14, 0.45), (16.6, 0.45), (16.8, 0.2), (18.9, 0.25),
            (19.2, 1.0), (40, 1.0)],
    "happy": [(0, 0)],
    "brow": [(0, 0.1), (2.9, 0.1), (3.4, 0.7), (3.73, 0.85), (5.71, 0.4), (7.4, 0.4), (8.0, 1.0), (40, 1.0)],
    "tear": saw(4.4, 40, 1.3),
    "tear_a": [(0, 0), (4.4, 0), (4.7, 1), (5.6, 1), (5.8, 0), (8.5, 0), (8.9, 1), (40, 1)],
    "blush": [(0, 0.35), (1.6, 0.35), (1.9, 0.55), (2.9, 0.55), (3.3, 0), (11.55, 0), (11.75, 0.85), (12.14, 0.85),
              (12.4, 0), (40, 0)],
    "laugh": [(0, 0)],
    "flag_ang": [(0, 0)], "desat": [(0, 0.05), (3.7, 0.15), (9.0, 0.3), (12.1, 0.45), (19.9, 0.5)],
    "cry": [(0, 0), (16.68, 0), (17.0, 1), (40, 1)],
}
MOUTH = [(0, "smile"), (2.9, "flat"), (3.3, "frown"), (4.3, "cry"), (5.6, "flat"), (5.9, "smile"), (7.6, "flat"),
         (8.2, "frown"), (12.14, "frown"), (17.0, "cry")]
ROSE_HOLD_L, ROSE_HOLD_R = ("head", -26, 262), ("head", 24, 256)
SIDE_L, SIDE_R = ("hip", -122, -15), ("hip", 122, -15)
POCKET_L, POCKET_R = ("hip", -92, -24), ("hip", 92, -24)
CLUTCH_L, CLUTCH_R = ("head", -40, 176), ("head", 40, 176)
FACE_L, FACE_R = ("head", -46, 20), ("head", 46, 20)
HAND_L = [(0, ROSE_HOLD_L), (1.6, ROSE_HOLD_L), (1.85, SIDE_L), (4.25, SIDE_L), (4.45, CLUTCH_L), (5.6, CLUTCH_L),
          (5.8, SIDE_L), (9.2, SIDE_L), (9.6, ("head", -70, 44)), (11.5, ("head", -70, 44)), (11.65, FACE_L),
          (12.12, FACE_L), (12.14, POCKET_L), (16.6, POCKET_L), (16.9, SIDE_L)]
HAND_R = [(0, ROSE_HOLD_R), (1.6, ROSE_HOLD_R), (1.9, ("head", 200, 110)), (3.2, ("head", 200, 110)),
          (3.65, ("hip", 128, -20)), (4.25, ("hip", 128, -20)), (4.45, CLUTCH_R), (5.6, CLUTCH_R), (5.85, SIDE_R),
          (6.0, ("wave",)), (7.6, ("wave",)), (7.9, ("head", 170, -120)), (8.3, ("head", 170, -120)),
          (8.7, SIDE_R), (11.5, SIDE_R), (11.65, FACE_R), (12.12, FACE_R), (12.14, POCKET_R), (14.95, POCKET_R),
          (15.15, ("head", 34, 70)), (15.9, ("head", 34, 70)), (16.3, POCKET_R), (16.6, POCKET_R), (16.9, SIDE_R)]
ROSE_DROP = 4.32


def hand_pos(keys, t, hip, head, walk):
    phase = math.pi * (t - BEAT0) / BEAT

    def resolve(spec):
        kind = spec[0]
        if kind == "wave":   # small, shy wave
            return (head[0] + 175 + 26 * math.sin(t * 9), head[1] - 120)
        if kind == "swing":
            s = spec[1]
            sw = math.sin(phase + (math.pi if s > 0 else 0)) * walk
            return (hip[0] + s * (122 + 10 * sw), hip[1] - 20 + 26 * sw)
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


_orig_head = m.draw_head


def blink(t):
    return 1.0 if (t + 0.4) % 3.1 < 0.11 else 0.0


def draw_head(t, p):
    """The rig's head with round glasses, freckles, a crying mouth, tear streams and blinks."""
    p = dict(p)
    mouth = p["mouth"]
    if mouth == "cry":
        p["mouth"] = "none"
    if p["lid"] < 0.9 and blink(t):
        p["lid"] = 1.0
    img = _orig_head(t, p)
    pen = m.Pen(img, 0, 0, K)
    cx, cy = 180, 310
    mx, my = cx, cy + 90
    LINE = m.LINE
    for sx in (-1, 1):   # freckles
        for fx, fy in ((62, 50), (76, 56), (88, 48), (70, 64), (84, 66)):
            pen.circle(cx + sx * fx, cy + fy, 3.2, (200, 136, 116))
    if mouth == "cry":
        wob = math.sin(t * 22) * 2.5
        top = [(mx + x, my + 10 - 10 * (1 - (x / 24) ** 2)) for x in range(-24, 25, 6)]
        bot = [(mx + x, my + 20 + wob * math.sin(x * 0.3) + 3 * (1 - (x / 24) ** 2)) for x in range(24, -25, -6)]
        pen.poly(top + bot, (120, 34, 50), LINE, 3)
    # round glasses
    lens = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lp = m.Pen(lens, 0, 0, K)
    for sx in (-1, 1):
        ex, ey = cx + sx * 52, cy + 14
        lp.ellipse(ex - 45, ey - 42, ex + 45, ey + 42, (220, 235, 255, 34))
        lp.line([(ex - 26, ey - 22), (ex - 6, ey - 34)], (255, 255, 255, 110), 4)
    img.alpha_composite(lens)
    for sx in (-1, 1):
        ex, ey = cx + sx * 52, cy + 14
        pen.ellipse(ex - 45, ey - 42, ex + 45, ey + 42, None, (36, 34, 46), 6)
        pen.line([(ex + sx * 45, ey - 6), (cx + sx * 118, cy + 2)], (36, 34, 46), 5)
    pen.line([(cx - 9, cy + 6), (cx, cy + 1), (cx + 9, cy + 6)], (36, 34, 46), 5)
    cry = p.get("cry", 0)
    if cry > 0.01:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        lp = m.Pen(lay, 0, 0, K)
        a = int(210 * cry)
        for sx in (-1, 1):
            x0, y0 = cx + sx * 58, cy + 52
            pts = [(x0 + sx * 6 * (k / 6) + 2 * math.sin(t * 6 + k + sx), y0 + 13 * k) for k in range(7)]
            lp.line(pts, (170, 215, 255, a // 2), 8)
            for ph in (0.0, 0.5):
                u = (t * 0.8 + ph + (0.25 if sx > 0 else 0)) % 1.0
                tx, ty = x0 + sx * 6 * u, y0 + 80 * u
                lp.poly([(tx, ty - 16), (tx - 8, ty), (tx + 8, ty)], (165, 210, 255, a))
                lp.circle(tx, ty + 2, 8, (165, 210, 255, a))
                lp.circle(tx - 3, ty - 1, 2.5, (255, 255, 255, a))
        img.alpha_composite(lay)
    return img


_orig_char = m.draw_character


def draw_character(t):
    """The rig draws arms behind the head; put the hand (and a bit of sleeve) on top at his face."""
    img, origin, head = _orig_char(t)
    pen = m.Pen(img, origin[0], origin[1], K)
    for s_, key in ((-1, "L"), (1, "R")):
        hand = m.LAST_HANDS.get(key)
        if hand and abs(hand[0] - head[0]) < 100 and -40 < hand[1] - head[1] < 150:
            sh = (head[0] + s_ * 104, head[1] + 330)
            vx, vy = sh[0] - hand[0], sh[1] - hand[1]
            n = max(1.0, math.hypot(vx, vy))
            wrist = (hand[0] + vx / n * 80, hand[1] + vy / n * 80)
            pen.limb(wrist, hand, 50, m.HOOD)
            pen.circle(*hand, 27, m.SKIN, m.LINE, 3)
    return img, origin, head


def walk_phase(t):
    return math.pi * (t - BEAT0) / BEAT


m.T, m.MOUTH, m.HAND_L, m.HAND_R = T, MOUTH, HAND_L, HAND_R
m.hand_pos, m.draw_head, m.walk_phase = hand_pos, draw_head, walk_phase
m.skip_at = lambda t: 0.0
m.draw_character = draw_character
m.BEAT, m.FB = BEAT, (99, 99)
m.HOOD, m.HOOD_SH = (92, 98, 120), (64, 68, 90)          # grey hoodie
m.DURATION = DUR

# ==============================================================================================
# places, light, camera
# ==============================================================================================
m.LOCATIONS = [(0.0, "golden"), (3.73, "street"), (5.71, "park"), (9.01, "bathroom"), (12.14, "street"),
               (16.68, "moonroad")]
m.LIGHT = [
    (0.0, ((96, 62, 96), (255, 150, 112), (1.05, 0.98, 0.92))),
    (3.72, ((96, 62, 96), (255, 150, 112), (1.05, 0.98, 0.92))),
    (3.73, ((8, 10, 26), (34, 40, 66), (0.9, 0.95, 1.08))),
    (5.70, ((8, 10, 26), (34, 40, 66), (0.9, 0.95, 1.08))),
    (5.71, ((44, 54, 84), (126, 126, 146), (0.95, 0.97, 1.03))),
    (9.00, ((44, 54, 84), (126, 126, 146), (0.92, 0.95, 1.03))),
    (9.01, ((30, 34, 44), (70, 76, 90), (0.95, 0.97, 1.04))),
    (12.13, ((26, 30, 40), (60, 66, 80), (0.9, 0.93, 1.04))),
    (12.14, ((6, 8, 20), (26, 32, 54), (0.85, 0.9, 1.06))),
    (16.67, ((6, 8, 20), (26, 32, 54), (0.85, 0.9, 1.06))),
    (16.68, ((4, 8, 26), (30, 42, 84), (0.9, 0.95, 1.1))),
    (19.93, ((4, 8, 26), (30, 42, 84), (0.86, 0.9, 1.08))),
]
# (start, end, camera at start, camera at end, transition); camera = (zoom, pan_x, pan_y, roll)
m.SHOTS = [
    (0.00, 1.57, (1.00, 0, -60, 0), (1.10, 0, -110, 0), "fade"),            # sunset street, rose in hand
    (1.57, 2.91, (1.35, 170, -170, 0), (1.42, 180, -180, 0), "cut"),        # offers the rose; she is there
    (2.91, 3.73, (2.35, 0, -335, 0), (2.60, 0, -335, 0), "cut"),            # close: she turns away
    (3.73, 4.25, (1.00, 0, -40, 0), (1.06, 0, -60, 0), "flash"),            # night: they surround him
    (4.25, 5.71, (2.10, 0, -320, -10), (2.40, 0, -330, -13), "cut"),        # dutch close: eyes shut
    (5.71, 7.43, (1.00, 0, -40, 0), (1.08, 0, -60, 0), "whip"),             # park: kids, a shy wave
    (7.43, 9.01, (1.55, 0, -240, 0), (1.70, 0, -250, 0), "cut"),            # they run
    (9.01, 10.37, (1.00, 0, -40, 0), (1.00, 0, -40, 0), "dip"),             # mirror, over the shoulder
    (10.37, 12.14, (1.90, 0, -300, 0), (2.25, 0, -320, 0), "cut"),          # reflection close-up
    (12.14, 13.42, (2.20, 0, 380, 0), (2.30, 0, 380, 0), "dip"),            # feet in the rain
    (13.42, 15.04, (1.30, 0, -190, 0), (1.55, 0, -240, 0), "cut"),          # walking, head down
    (15.04, 16.68, (2.25, 0, -320, 0), (2.40, 0, -330, 0), "cut"),          # the smiling mask
    (16.68, 18.34, (1.30, 0, -230, 0), (1.00, 0, -40, 0), "dip"),           # under the moon, pull back
    (18.34, 19.93, (2.50, 0, -395, 0), (2.85, 0, -400, 0), "cut"),          # last close-up
]
m.OTS = [(9.01, 10.37, 1.00, 1.07)]
m.RIPPLES = ()
m.PHOTOS = []


def draw_back_figure(layer, t):
    """Him from behind in the over-the-shoulder mirror shot (grey hoodie, glasses arms at the ears)."""
    d = ImageDraw.Draw(layer)
    slump = track(T["slump"], t)
    hx, hy = 250, 1265 + slump * 34 + math.sin(t * 2.2) * 4
    body, body_sh = (60, 64, 84, 255), (42, 44, 60, 255)
    d.polygon([(hx - 460, H), (hx - 430, 1640), (hx - 250, 1500), (hx - 110, 1460), (hx + 110, 1460),
               (hx + 250, 1500), (hx + 430, 1640), (hx + 470, H)], fill=body)
    d.ellipse([hx - 230, hy + 130, hx + 230, hy + 330], fill=body_sh)
    d.rectangle([hx - 62, hy + 120, hx + 62, hy + 205], fill=(150, 116, 106, 255))
    for sx in (-1, 1):
        d.ellipse([hx + sx * 222 - 32, hy - 20, hx + sx * 222 + 32, hy + 70], fill=(200, 160, 144, 255))
        d.line([(hx + sx * 200, hy + 6), (hx + sx * 236, hy + 14)], fill=(30, 30, 40, 255), width=8)
    pts = []
    for k in range(25):
        ang = math.radians(150 + k * 240 / 24)
        r = 240 if k % 2 == 0 else 285
        pts.append((hx + r * math.cos(ang), hy - 10 + r * 1.05 * math.sin(ang)))
    pts += [(hx + 236, hy + 120), (hx + 150, hy + 190), (hx - 150, hy + 190), (hx - 236, hy + 120)]
    d.polygon(pts, fill=(18, 18, 30, 255))
    d.arc([hx - 170, hy - 230, hx + 130, hy - 40], 200, 300, fill=(60, 70, 110, 255), width=14)


m.draw_back_figure = draw_back_figure

# ==============================================================================================
# props, people, fx (world space, drawn through the camera)
# ==============================================================================================
SIL = (12, 10, 22)


def silhouette(d, x, base, sc, a=235, hair=False, eyes=None, grin=False, point=0, bob=0.0, face=1):
    """A faceless person. eyes: None / 'laugh' / 'wide'. point: -1/1 = arm pointing left/right."""
    col = SIL + (a,)
    top = base - 980 * sc - bob
    d.ellipse([x - 46 * sc, top, x + 46 * sc, top + 92 * sc], fill=col)
    if hair:   # long hair and a ponytail
        d.polygon([(x - 50 * sc, top + 30 * sc), (x + 50 * sc, top + 30 * sc), (x + 58 * sc, top + 170 * sc),
                   (x - 58 * sc, top + 170 * sc)], fill=col)
        d.ellipse([x - face * 40 * sc - 30 * sc, top + 10 * sc, x - face * 40 * sc + 30 * sc, top + 70 * sc], fill=col)
    d.polygon([(x - 80 * sc, top + 105 * sc), (x + 80 * sc, top + 105 * sc), (x + 62 * sc, base),
               (x - 62 * sc, base)], fill=col)
    if hair:   # a skirt-like flare
        d.polygon([(x - 70 * sc, top + 500 * sc), (x + 70 * sc, top + 500 * sc), (x + 110 * sc, top + 700 * sc),
                   (x - 110 * sc, top + 700 * sc)], fill=col)
    d.ellipse([x - 82 * sc, top + 92 * sc, x - 30 * sc, top + 150 * sc], fill=col)
    d.ellipse([x + 30 * sc, top + 92 * sc, x + 82 * sc, top + 150 * sc], fill=col)
    if point:
        sx = x + point * 60 * sc
        ex, ey = x + point * 250 * sc, top + 210 * sc
        d.line([(sx, top + 130 * sc), (ex, ey)], fill=col, width=int(34 * sc))
        d.ellipse([ex - 22 * sc, ey - 22 * sc, ex + 22 * sc, ey + 22 * sc], fill=col)
        d.line([(ex, ey), (ex + point * 60 * sc, ey + 6 * sc)], fill=col, width=int(14 * sc))
    if eyes:
        ea = min(255, a + 20)
        for ex in (-17, 17):
            if eyes == "laugh":
                d.arc([x + (ex - 12) * sc, top + 34 * sc, x + (ex + 12) * sc, top + 54 * sc], 200, 340,
                      fill=(255, 245, 230, ea), width=max(2, int(5 * sc)))
            else:
                d.ellipse([x + (ex - 9) * sc, top + 34 * sc, x + (ex + 9) * sc, top + 52 * sc], fill=(255, 245, 230, ea))
    if grin:
        d.chord([x - 26 * sc, top + 52 * sc, x + 26 * sc, top + 84 * sc], 0, 180, fill=(255, 245, 230, min(255, a + 20)))


def draw_rose(d, hx, hy, ang, wilt=0.0, a=255):
    L = 120
    tx, ty = hx + L * math.sin(ang), hy - L * math.cos(ang)
    d.line([(hx, hy + 30), (tx, ty)], fill=(40, 110, 50, a), width=7)
    d.ellipse([(hx + tx) / 2 - 4, (hy + ty) / 2 - 10, (hx + tx) / 2 + 26, (hy + ty) / 2 + 6], fill=(50, 130, 60, a))
    r = 34 * (1 - 0.25 * wilt)
    col = tuple(int(lerp(c, g, wilt)) for c, g in zip((220, 30, 60), (120, 40, 60)))
    d.ellipse([tx - r, ty - r * 1.1, tx + r, ty + r * 0.9], fill=col + (a,), outline=(110, 10, 30, a), width=3)
    d.arc([tx - r * 0.6, ty - r * 0.7, tx + r * 0.6, ty + r * 0.5], 180, 360, fill=(140, 10, 40, a), width=4)
    d.arc([tx - r * 0.3, ty - r * 0.4, tx + r * 0.3, ty + r * 0.2], 0, 180, fill=(140, 10, 40, a), width=3)


def draw_mask(d, x, y, s, a=255):
    """A white smiling mask (the face people would like to see)."""
    d.ellipse([x - 120 * s, y - 150 * s, x + 120 * s, y + 150 * s], fill=(246, 244, 240, a), outline=(60, 60, 70, a), width=4)
    for sx in (-1, 1):
        d.arc([x + sx * 50 * s - 26 * s, y - 40 * s, x + sx * 50 * s + 26 * s, y - 4 * s], 200, 340,
              fill=(30, 30, 40, a), width=max(3, int(8 * s)))
        d.ellipse([x + sx * 70 * s - 20 * s, y + 20 * s, x + sx * 70 * s + 20 * s, y + 40 * s], fill=(255, 170, 180, a))
    d.arc([x - 60 * s, y + 10 * s, x + 60 * s, y + 90 * s], 20, 160, fill=(30, 30, 40, a), width=max(3, int(8 * s)))


def front_props(layer, t, inner=False):
    d = ImageDraw.Draw(layer)
    kind = m.location_at(t)
    hand = m.LAST_HANDS.get("R")
    # the rose: held up, offered, drooping, then dropped on "बदसूरत"
    if t < ROSE_DROP + 1.2 and hand:
        if t < 1.6:
            ang, wilt = 0.45, 0.0
        elif t < 3.2:
            ang, wilt = 0.6, 0.0
        else:
            ang, wilt = lerp(0.6, 2.6, smooth((t - 3.2) / 0.6)), smooth((t - 3.0) / 1.2)
        hx, hy = hand
        if t > ROSE_DROP:
            f = clamp((t - ROSE_DROP) / 0.7)
            hx, hy = hx + 50 * f, lerp(hy, GROUND - 20, f * f)
            ang = lerp(ang, 1.6, f)
        draw_rose(d, hx, hy, ang, wilt)
    # the girl: waits, turns away, walks off
    if 1.4 < t < 3.9:
        go = smooth((t - 3.0) / 0.75)
        a = int(235 * clamp((t - 1.4) / 0.3) * (1 - smooth((t - 3.55) / 0.3)))
        silhouette(d, 880 + 340 * go, GROUND - 10, 0.8, a=a, hair=True, face=-1 if t < 3.0 else 1,
                   bob=abs(math.sin(t * 7)) * 8 * go)
    # the mockers, pointing and laughing
    if 3.73 <= t < 5.71:
        for i, (x, sc, pnt) in enumerate(((120, 0.86, 1), (300, 0.94, 1), (780, 0.94, -1), (960, 0.86, -1))):
            arrive = ease_out((t - 3.73 - i * 0.06) / 0.35)
            xx = lerp(x + (-260 if x < 540 else 260), x, arrive)
            silhouette(d, xx, GROUND + 20 - (1 - sc) * 200, sc, a=int(240 * arrive), eyes="laugh", grin=True,
                       point=pnt if t < 4.25 else 0, bob=abs(math.sin(t * 15 + i)) * 14)
    # park: kids, then grown-ups; they see him and run off towards the horizon
    if 5.71 <= t < 9.01:
        people = [(180, 0.48, 5.80, False), (900, 0.5, 5.97, False), (1010, 0.44, 6.40, False),
                  (90, 0.92, 6.77, False), (770, 0.95, 6.95, False)]
        run = smooth((t - 7.65) / 1.1)
        for i, (x, sc0, t_in, _) in enumerate(people):
            if t < t_in:
                continue
            a = int(230 * clamp((t - t_in) / 0.25) * (1 - smooth((t - 8.5) / 0.4)))
            side = -1 if x < 540 else 1
            xx = lerp(x, 540 + side * 240, run)
            sc = lerp(sc0, sc0 * 0.25, run)
            base = lerp(GROUND - 10, m.HOR + 120, run)
            silhouette(d, xx, base, sc, a=a, eyes="wide" if t > 7.43 else None,
                       bob=abs(math.sin(t * (14 if run > 0 else 3) + i)) * (16 if run > 0 else 4) * sc)
            if 7.43 < t < 8.3:   # "!" over their heads
                q = back_out((t - 7.43) / 0.25) * (1 - smooth((t - 8.0) / 0.3))
                top = base - 980 * sc
                d.rectangle([xx - 7 * q, top - 120 * q, xx + 7 * q, top - 50 * q], fill=(255, 230, 120, int(255 * q)))
                d.ellipse([xx - 8 * q, top - 40 * q, xx + 8 * q, top - 24 * q], fill=(255, 230, 120, int(255 * q)))
            if run > 0.02:      # dust puffs as they run
                for k in range(3):
                    u = (t * 3 + k / 3 + i) % 1
                    pr = 30 * sc0 * (0.5 + u)
                    d.ellipse([xx - side * 50 * u * sc0 * 4 - pr, base - pr * 0.6, xx - side * 50 * u * sc0 * 4 + pr,
                               base + pr * 0.4], fill=(200, 200, 210, int(120 * (1 - u) * (1 - run))))
    # bathroom: mirror frame + sink in front (he reads as the reflection), the mirror cracks on "देख"
    if kind == "bathroom" and not inner:
        d.rounded_rectangle([150, 360, 930, 1480], radius=40, outline=(200, 205, 215, 255), width=26)
        shine = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shine)
        for x0, w_ in ((230, 70), (330, 26), (700, 50)):
            sd.polygon([(x0, 380), (x0 + w_, 380), (x0 + w_ - 260, 1460), (x0 - 260, 1460)], fill=(255, 255, 255, 26))
        layer.alpha_composite(shine.filter(ImageFilter.GaussianBlur(6)))
        if t > 11.07:
            grow = ease_out((t - 11.07) / 0.18)
            rr = random.Random(5)
            ox, oy = 610, 700
            for k in range(13):
                ang = k / 13 * math.tau + rr.uniform(-0.2, 0.2)
                x, y = ox, oy
                pts = [(x, y)]
                for _ in range(5):
                    stp = rr.uniform(40, 110) * grow
                    ang += rr.uniform(-0.35, 0.35)
                    x, y = x + stp * math.cos(ang), y + stp * math.sin(ang)
                    pts.append((x, y))
                d.line([(px + 2, py + 2) for px, py in pts], fill=(0, 0, 0, 120), width=5)
                d.line(pts, fill=(235, 240, 255, 230), width=3)
            for r in (60, 130):
                ring = [(ox + r * grow * math.cos(a_) * rr.uniform(0.8, 1.2), oy + r * grow * math.sin(a_) * rr.uniform(0.8, 1.2))
                        for a_ in np.linspace(0, math.tau, 12)]
                d.line(ring, fill=(235, 240, 255, 150), width=2)
        d.rectangle([0, 1480, W, H], fill=(214, 216, 222, 255))
        d.rectangle([0, 1480, W, 1520], fill=(236, 238, 242, 255))
        d.ellipse([360, 1540, 720, 1680], fill=(190, 194, 202, 255))
        d.rectangle([520, 1440, 560, 1540], fill=(170, 174, 184, 255))
    # the smiling mask he holds up to his face, then lets fall
    if 15.0 < t < 16.9 and hand:
        lift = smooth((t - 15.0) / 0.35)
        hx, hy = hand
        x, y, a = hx - 30, hy - 60, int(255 * lift)
        if t > 16.0:
            f = clamp((t - 16.0) / 0.8)
            y += 900 * f * f
            a = int(255 * (1 - smooth((t - 16.5) / 0.3)))
        draw_mask(d, x, y, 0.95, a)


rnd = random.Random(31)
RAIN = [(rnd.uniform(-200, W + 200), rnd.uniform(0, H), rnd.uniform(1400, 2100), rnd.uniform(40, 90)) for _ in range(230)]
SPLASH = [(rnd.uniform(0, W), rnd.uniform(GROUND - 80, GROUND + 260), rnd.uniform(0, 1)) for _ in range(40)]
PETALS = [(rnd.uniform(-60, 60), rnd.uniform(0, 1), rnd.uniform(0, 6.28)) for _ in range(9)]


def fx_layer(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    raining = (3.73 <= t < 5.71) or (12.14 <= t < 16.68)
    if raining:
        for x, y, sp, ln in RAIN:
            yy = (y + t * sp) % (H + 200) - 100
            xx = x - (yy * 0.12)
            d.line([(xx, yy), (xx - ln * 0.12, yy - ln)], fill=(190, 210, 255, 110), width=2)
        for x, y, ph in SPLASH:
            u = (t * 2.2 + ph) % 1
            r = 6 + 26 * u
            d.ellipse([x - r, y - r * 0.3, x + r, y + r * 0.3], outline=(200, 220, 255, int(140 * (1 - u))), width=2)
    if 2.95 < t < 4.4 and m.LAST_HANDS.get("R"):   # petals drift off the rose
        hx, hy = m.LAST_HANDS["R"]
        for dx, ph, rot in PETALS:
            u = clamp((t - 2.95 - ph * 0.6) / 1.2)
            if 0 < u < 1:
                px, py = hx + dx + 60 * math.sin(u * 5 + rot) + 40 * u, hy - 120 + u * 700
                d.ellipse([px - 9, py - 6, px + 9, py + 6], fill=(200, 30, 60, int(230 * (1 - u))))
    for x, y, s_, sp, ph in m.DUST:
        py_ = (y - t * sp) % H
        px_ = x + 24 * math.sin(t * 0.7 + ph)
        d.ellipse([px_ - s_, py_ - s_, px_ + s_, py_ + s_], fill=(210, 220, 255, 40))
    return layer.filter(ImageFilter.GaussianBlur(1.0))


m.front_props, m.fx_layer = front_props, fx_layer


# ==============================================================================================
# signs (screen space, after the camera)
# ==============================================================================================
def heart(d, x, y, s, half=0, col=(235, 60, 100), a=255, rot=0.0, dx=0.0, dy=0.0):
    pts = m.heart_pts(0, 0, s, half)
    cr, sr = math.cos(rot), math.sin(rot)
    d.polygon([(x + dx + px * cr - py * sr, y + dy + px * sr + py * cr) for px, py in pts], fill=col + (a,),
              outline=(70, 0, 25, a))


def pointing_hand(d, x, y, ang, s, a):
    """A dark hand with the index finger pointing along ang (radians)."""
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v):
        return (x + (u * ca - v * sa) * s, y + (u * sa + v * ca) * s)
    col = (10, 8, 18, a)
    d.line([P(-400, 0), P(-40, 0)], fill=col, width=int(56 * s))
    d.polygon([P(-70, -45), P(20, -40), P(30, 40), P(-70, 45)], fill=col)
    d.line([P(10, -18), P(120, -18)], fill=col, width=int(30 * s))
    tip = P(122, -18)
    d.ellipse([tip[0] - 15 * s, tip[1] - 15 * s, tip[0] + 15 * s, tip[1] + 15 * s], fill=col)
    for k in range(3):   # curled fingers
        c = P(14, 6 + k * 14)
        d.ellipse([c[0] - 18 * s, c[1] - 9 * s, c[0] + 18 * s, c[1] + 9 * s], fill=col)


def draw_signs(t, layer, cam, head):
    d = ImageDraw.Draw(layer)
    to_s, zd = m.world_to_screen(cam)
    hx, hy = to_s(*head)
    # "पसंद": a heart over his head cracks and falls apart
    if 2.91 <= t < 3.73 + 0.2:
        dt = t - 2.91
        a = int(255 * clamp(dt / 0.08) * (1 - smooth((dt - 0.7) / 0.25)))
        x, y, s = hx + 230, hy - 330, 8
        if dt < 0.36:
            heart(d, x, y, s * (back_out(dt / 0.25) if dt < 0.25 else 1), a=a)
            if dt > 0.22:
                crack = [(0, -5), (-3, -1), (3, 3), (-2, 7), (0, 12)]
                d.line([(x + cx * s, y + cy * s) for cx, cy in crack], fill=(40, 0, 15, a), width=5)
        else:
            u = dt - 0.36
            for side in (-1, 1):
                heart(d, x, y, s, half=side, a=a, rot=side * 0.6 * u, dx=side * 80 * u, dy=320 * u * u)
    # "लड़की": a little pink heart near her
    if 2.13 <= t < 2.95:
        sx, sy = to_s(880, GROUND - 900)
        q = back_out((t - 2.13) / 0.3) * (1 - smooth((t - 2.7) / 0.25))
        heart(d, sx, sy - 40, 3.2 * q * zd, col=(255, 150, 190), a=int(255 * min(1, q)))
    # "बदसूरत": pointing fingers slide in from the edges at his face
    if 4.25 <= t < 5.71:
        a = int(235 * (1 - smooth((t - 5.45) / 0.25)))
        for k, (ex, ey) in enumerate(((-80, 700), (1160, 600), (-80, 1560), (1160, 1500))):
            arrive = ease_out((t - 4.25 - k * 0.07) / 0.3)
            ang = math.atan2(hy - ey, hx - ex)
            dist = math.hypot(hx - ex, hy - ey)
            reach = dist - 470
            px, py = ex + math.cos(ang) * reach * arrive, ey + math.sin(ang) * reach * arrive
            jab = 14 * math.sin(t * 16 + k)
            pointing_hand(d, px + math.cos(ang) * jab, py + math.sin(ang) * jab, ang, 1.0, int(a * 0.9))
    # "देखकर": an eye opens over the scene
    if 7.43 <= t < 8.3:
        q = back_out((t - 7.43) / 0.3) * (1 - smooth((t - 8.0) / 0.3))
        ex, ey = 540, hy - 420
        d.ellipse([ex - 95 * q, ey - 48 * q, ex + 95 * q, ey + 48 * q], fill=(250, 250, 255, 230), outline=(30, 30, 40, 255), width=5)
        d.ellipse([ex - 30 * q, ey - 30 * q, ex + 30 * q, ey + 30 * q], fill=(40, 60, 120, 255))
        d.ellipse([ex - 12 * q, ey - 12 * q, ex + 12 * q, ey + 12 * q], fill=(10, 10, 20, 255))
    # "कैसी ज़िंदगी": question marks drift up beside him
    if 12.6 <= t < 14.5:
        f = ImageFont.truetype(m.F_SYM, 110)
        for k in range(3):
            u = clamp((t - 12.6 - k * 0.35) / 1.4)
            if 0 < u < 1:
                qx = 540 + (-260 if k % 2 == 0 else 250) + 20 * math.sin(t * 2 + k)
                qy = 980 - 380 * u
                d.text((qx, qy), "?", font=f, fill=(210, 220, 255, int(220 * math.sin(math.pi * u))), anchor="mm")
    # "दिखता": an eye
    if 17.1 <= t < 18.2:
        q = back_out((t - 17.1) / 0.3) * (1 - smooth((t - 17.9) / 0.3))
        ex, ey = min(900, hx + 300), hy - 120
        d.ellipse([ex - 110 * q, ey - 56 * q, ex + 110 * q, ey + 56 * q], fill=(235, 240, 255, 210), outline=(20, 20, 30, 255), width=5)
        d.ellipse([ex - 34 * q, ey - 34 * q, ex + 34 * q, ey + 34 * q], fill=(60, 90, 170, 255))
        d.ellipse([ex - 13 * q, ey - 13 * q, ex + 13 * q, ey + 13 * q], fill=(10, 10, 20, 255))
    # "मायने": a balance; the face side sinks, the heart side rises
    if 18.82 <= t < 19.85:
        q = clamp((t - 18.82) / 0.25) * (1 - smooth((t - 19.6) / 0.25))
        a = int(240 * q)
        tip = 0.32 * smooth((t - 19.0) / 0.5)
        cx, cy, L = 540, 480, 200
        d.line([(cx, cy), (cx, cy + 190)], fill=(52, 60, 104, a), width=8)
        d.polygon([(cx - 60, cy + 200), (cx + 60, cy + 200), (cx, cy + 170)], fill=(52, 60, 104, a))
        lx, ly = cx - L * math.cos(tip), cy + L * math.sin(tip)
        rx, ry = cx + L * math.cos(tip), cy - L * math.sin(tip)
        d.line([(lx, ly), (rx, ry)], fill=(52, 60, 104, a), width=8)
        for px, py, kind in ((lx, ly, "face"), (rx, ry, "heart")):
            d.line([(px, py), (px - 50, py + 90)], fill=(52, 60, 104, a), width=3)
            d.line([(px, py), (px + 50, py + 90)], fill=(52, 60, 104, a), width=3)
            d.chord([px - 70, py + 60, px + 70, py + 120], 0, 180, fill=(52, 60, 104, a))
            if kind == "face":
                d.ellipse([px - 34, py + 10, px + 34, py + 80], fill=(250, 226, 206, a), outline=(30, 30, 40, a), width=3)
                for sx in (-1, 1):
                    d.ellipse([px + sx * 13 - 8, py + 32, px + sx * 13 + 8, py + 46], outline=(30, 30, 40, a), width=3)
            else:
                heart(d, px, py + 46, 2.4, a=a)


m.draw_signs = draw_signs


# ==============================================================================================
# the words: soft neon, word by word, in a band clear of him
# ==============================================================================================
def draw_words(frame, t, occ):
    for idx, (words, style, size, cols, end, extra) in enumerate(CHUNKS):
        if t < words[0][1] - 0.1 or t > end + 0.05:
            continue
        glow, base = GLOW[style], BASE[style]
        sprites = [m.ksprite(w, size, cols.get(w, base), glow) for w, _ in words]
        space = size * 0.38
        total = sum(adv for _, adv in sprites) + space * (len(words) - 1)
        if total > 980:   # long line: scale down
            k = 980 / total
            size2 = int(size * k)
            sprites = [m.ksprite(w, size2, cols.get(w, base), glow) for w, _ in words]
            space = size2 * 0.38
            total = sum(adv for _, adv in sprites) + space * (len(words) - 1)
        cy = m.choose_y(("w", idx), total + size, size * (2.4 if style == "mirror" else 1.7), occ)
        x = 540 - total / 2
        out_k = smooth((t - (end - 0.2)) / 0.2)
        for i, ((w, wt), (spr, adv)) in enumerate(zip(words, sprites)):
            wx = x + adv / 2
            x += adv + space
            p = (t - wt) / 0.3
            if p <= 0:
                continue
            a, s, dx, dy, ang = clamp(p * 2) * (1 - out_k), 1.0, 0.0, 0.0, 0.0
            img = spr
            if style in ("soft", "mirror", "rain", "dissolve"):
                s = lerp(0.84, 1.0, ease_out(p))
                dy = (1 - ease_out(p)) * 30 + math.sin(t * 2 + i) * 4
                if p < 0.6:
                    img = spr.filter(ImageFilter.GaussianBlur((0.6 - p) * 14))
                if style == "rain":
                    dy += (t - wt) * 10
                    a *= 0.92
            if style in ("slam", "shatter"):
                k = clamp((t - wt) / 0.15)
                s = lerp(2.1, 1.0, ease_out(k))
                if t - wt > 0.15:
                    dec = math.exp(-(t - wt - 0.15) / 0.25)
                    dx, dy = math.sin(t * 70) * 12 * dec, math.cos(t * 63) * 9 * dec
                a = clamp(k * 3) * (1 - out_k)
            if style == "shatter" and extra and t > extra:
                brk = clamp((t - extra) / 0.5)
                cols_, rows = 6, 3
                tw, th = spr.width // cols_, spr.height // rows
                rr = random.Random(idx * 10 + i)
                for gy in range(rows):
                    for gx in range(cols_):
                        tile = spr.crop((gx * tw, gy * th, (gx + 1) * tw, (gy + 1) * th))
                        vx, vy, spin = rr.uniform(-160, 160), rr.uniform(-120, 40), rr.uniform(-160, 160)
                        tx_ = wx - spr.width / 2 + gx * tw + tw / 2 + vx * brk
                        ty_ = cy - spr.height / 2 + gy * th + th / 2 + vy * brk + 900 * brk ** 2
                        tile = tile.rotate(spin * brk, expand=True, resample=Image.BICUBIC)
                        m.paste_c(frame, m.alpha_mul(tile, 1 - brk), tx_, ty_)
                continue
            if style == "dissolve" and extra and t > extra:
                dis = clamp((t - extra) / 0.3)
                rr = random.Random(i + 5)
                lay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
                ld = ImageDraw.Draw(lay)
                for _ in range(70):
                    ox, oy = rr.uniform(-adv / 2, adv / 2), rr.uniform(-size * 0.4, size * 0.4)
                    px, py = wx + ox + rr.uniform(-40, 120) * dis, cy + oy - rr.uniform(20, 160) * dis
                    r_ = rr.uniform(2, 5)
                    ld.ellipse([px - r_, py - r_, px + r_, py + r_], fill=(200, 210, 240, int(200 * (1 - dis))))
                frame.alpha_composite(lay)
                a *= 1 - dis
            img = m.shine(img, (t - wt) / 0.9 - 0.15)
            if abs(s - 1) > 0.01:
                img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC)
            m.paste_c(frame, m.alpha_mul(img, a), wx + dx, cy + dy)
            if style == "mirror":   # faint reflection under the word
                ref = img.transpose(Image.FLIP_TOP_BOTTOM)
                grad = Image.linear_gradient("L").resize(ref.size).point(lambda v: int((255 - v) * 0.35))
                ra = Image.fromarray((np.asarray(ref.getchannel("A")).astype(np.float32) *
                                      np.asarray(grad).astype(np.float32) / 255).astype(np.uint8))
                ref.putalpha(ra)
                m.paste_c(frame, m.alpha_mul(ref, a), wx + dx, cy + dy + size * 0.95)


# ==============================================================================================
# frame
# ==============================================================================================
def render_frame(t):
    rng = np.random.default_rng(int(t * 1000) + 7)
    _, _, tint = m.light_at(t)
    zoom = m.ots_at(t)
    if zoom is not None:
        frame, occ = m.compose_ots(t, zoom)
    else:
        cam = m.camera_at(t)
        frame, char_l, flag_l, head = m.render_scene(t, cam)
        signs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_signs(t, signs, cam, head)
        frame.alpha_composite(signs.filter(ImageFilter.GaussianBlur(14)))
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
    arr = m.motion_blur(arr, blur)
    if flash > 0.01:
        arr = arr + (255 - arr) * flash * 0.8
    if 4.25 <= t < 4.45:   # red jolt on "बदसूरत"
        k = 1 - (t - 4.25) / 0.2
        arr[:, :, 0] = np.roll(arr[:, :, 0], int(14 * k), axis=1)
        arr[:, :, 2] = np.roll(arr[:, :, 2], -int(14 * k), axis=1)
        arr = arr * (1 - 0.35 * k) + np.array([255, 40, 60], np.float32) * 0.35 * k
    arr *= m.VIGNETTE * bright
    arr += rng.normal(0, 3.5, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    draw_words(out, t, occ)
    out = out.convert("RGB")
    fade = min(clamp(t / 0.35), clamp((DUR - t) / 0.7))
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
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={DUR - 0.5:.2f}:d=0.5",
                    "-t", f"{DUR:.2f}", "-movflags", "+faststart", OUT], check=True)
    os.remove(SILENT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
