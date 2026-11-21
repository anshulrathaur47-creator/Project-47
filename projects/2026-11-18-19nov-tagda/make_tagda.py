"""19 November 2023, "tagda" cut: a fan lives the final with the user's clip.

Split screen: the user's clip plays in a glowing panel at the top, and below it our anime fan
(India jersey, face paint, flag) watches it live in his room at night, lit only by the screen.
He cheers and jumps on the beat, prays before Head's catch, freezes when the catch lands (the
panel cracks), shakes his head when Kohli goes, hides his face at the Head century, and breaks
when Australia win (the panel shatters, the flag falls). The last section match-cuts the real
players with him: Rohit wipes his eyes, he wipes his; Kohli looks up, he looks up. The TV
switches off on the trophy shot.

Character rig comes from projects/2026-11-16-remember-19-nov/make_19nov.py (imported, with its
timeline replaced here). Audio: the clip's own track, untouched apart from a short fade.

Usage: python3 make_tagda.py [--frames 60,300,...] [--workers 4]
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

clamp, smooth, lerp, ease_out, track, step = m.clamp, m.smooth, m.lerp, m.ease_out, m.track, m.step

W, H, FPS = 1080, 1920, 30
CLIP = os.path.join(HERE, "..", "..", "raw-videos", "VID_20261118_235405_536.mp4")
OUT = os.path.join(HERE, "19nov_tagda.mp4")
SILENT = os.path.join(HERE, "_tagda_silent.mp4")
DUR = 39.77
CW, CH, CFPS = 964, 720, 28.473
BEAT0, BEAT = 0.07, 0.6151          # ~97.5 bpm, first beat at 0.07 s
K = m.K
PANEL = (40, 200, 1040, 947)        # clip panel in the split layout (1000 x 747)

XX, YY = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
VIG = np.clip(1.12 - (((XX - W / 2) / (W * 0.66)) ** 2 + ((YY - H / 2) / (H * 0.62)) ** 2) * 0.7, 0.3, 1)[:, :, None]


def beat_phase(t):
    return ((t - BEAT0) / BEAT) % 1.0


def since_beat(t):
    return beat_phase(t) * BEAT


# ==============================================================================================
# edit: layout per section + the camera on the fan
# cam = (zoom, focus_x, focus_y, roll, keystone); keystone > 0 = low angle (looking up at him)
# ==============================================================================================
SHOTS = [
    (0.00, "full", None, None),                                                   # aerial crowd
    (2.11, "split", (0.68, 540, 1010, 0, 0), (0.72, 540, 1000, 0, 0)),            # wide: flag + jumps
    (4.55, "split", (0.98, 540, 870, 0, 0), (1.05, 540, 860, 0, 0)),              # medium: clapping
    (6.39, "split", (0.80, 540, 990, -5, 0.22), (0.86, 540, 980, -5, 0.22)),      # low angle: fists
    (8.22, "split", (1.55, 540, 795, 0, 0), (1.72, 540, 790, 0, 0)),              # close: shouting
    (10.63, "split", (0.68, 540, 1010, 0, 0), (0.70, 540, 1005, 0, 0)),           # wide: jumping
    (13.12, "split", (0.95, 540, 880, 7, 0), (1.02, 540, 870, 7, 0)),             # dutch: chanting
    (16.18, "split", (0.92, 540, 860, 0, 0), (1.70, 540, 795, 0, 0)),             # push-in: praying
    (18.02, "boy", (1.95, 540, 770, 0, 0), (2.15, 540, 770, -3, 0)),              # catch: shock
    (19.25, "split", (0.68, 540, 1010, 0, 0), (0.76, 540, 995, 0, 0)),           # sits down
    (22.69, "split", (1.45, 540, 985, -8, 0), (1.58, 540, 980, -11, 0)),          # Kohli: "nahi"
    (24.75, "split", (0.95, 540, 1120, 0, 0), (1.02, 540, 1115, 0, 0)),             # hides his face
    (26.59, "split", (1.35, 540, 995, 0, 0), (1.62, 540, 990, 0, 0)),             # blank stare, eyes fill
    (28.42, "split", (0.72, 540, 1110, 0, 0.14), (0.76, 540, 1100, 0, 0.14)),     # low wide: the end comes
    (30.70, "split", (1.05, 540, 1090, 0, 0), (1.25, 540, 1060, -4, 0)),            # Australia win
    (32.09, "split", (1.30, 540, 1050, -4, 0), (0.72, 540, 1110, 0, 0)),           # pull back: crying
    (33.92, "full", None, None),                                                  # Kohli stares
    (35.00, "full", None, None),                                                  # Rohit wipes his eyes
    (35.76, "boy", (2.05, 540, 1000, 0, 0), (2.20, 540, 1000, 0, 0)),               # ...so does he
    (36.39, "full", None, None),                                                  # Rohit, head down
    (37.00, "full", None, None),                                                  # Kohli looks up
    (37.62, "boy", (1.95, 540, 975, 0, 0), (2.10, 540, 975, 3, 0)),               # ...so does he
    (38.28, "split", (0.72, 540, 1110, 0, 0), (0.76, 540, 1100, 0, 0)),           # trophy, TV switches off
]
# full-screen crops of the clip: (start, centre x at start, at end, zoom at start, at end)
FULL_CROP = [(0.00, 560, 430, 1.10, 1.00), (1.55, 482, 482, 1.00, 1.05), (33.92, 548, 548, 1.00, 1.04),
             (35.00, 550, 550, 1.00, 1.04), (36.39, 550, 550, 1.00, 1.03), (37.00, 482, 482, 1.00, 1.06)]
FREEZES = [(17.72, 18.02)]                    # hold the frame of the catch landing
IMPACTS = [(17.72, 1.0, (0.30, 0.78)), (22.69, 0.8, (0.62, 0.42)), (30.70, 1.35, (0.50, 0.52))]
TV_OFF = (39.02, 39.42)
HYPE = (2.11, 16.18)                          # cheering section: beat punches + confetti


def shot_at(t):
    i = max(k for k, s in enumerate(SHOTS) if s[0] <= t)
    t0, kind, c0, c1 = SHOTS[i]
    t1 = SHOTS[i + 1][0] if i + 1 < len(SHOTS) else DUR
    return i, t0, t1, kind, c0, c1


def clip_time(t):
    for a, b in FREEZES:
        if a <= t < b:
            return a
    return t


# ==============================================================================================
# the fan's acting (timeline for the imported rig)
# ==============================================================================================
def saw(t0, t1, period):
    keys, t = [(0, 0)], t0
    while t < t1:
        keys += [(t, 0), (t + period * 0.97, 1), (t + period, 0)]
        t += period
    return keys


T = {
    "stand": [(0, 1)],
    "sink": [(0, 0), (19.45, 0), (20.35, 190), (40, 190)],
    "slump": [(0, 0), (19.4, 0), (20.4, 0.4), (24.7, 0.45), (24.95, 0.8), (26.5, 0.8), (26.75, 0.5),
              (30.65, 0.55), (31.0, 1.0), (40, 1.0)],
    "head_dy": [(0, 0), (17.7, 0), (17.8, -8), (19.2, -8), (19.45, 0), (24.75, 0), (25.0, 22), (26.5, 22),
                (26.75, 4), (30.7, 4), (31.0, 34), (33.9, 28), (35.7, 22), (37.6, 22), (37.75, -16),
                (38.25, -16), (38.9, 30), (40, 36)],
    "tilt": [(0, 0), (17.7, 0), (17.8, 3), (19.2, -2), (19.5, 0), (24.75, 0), (25.0, -5), (26.5, -5),
             (26.75, 0), (30.7, 0), (31.0, -7), (33.9, -6), (35.7, -3), (37.6, 4), (38.2, 4), (38.9, -6)],
    "shake": [(0, 0), (22.85, 0), (22.95, 1), (23.9, 1), (24.1, 0), (31.2, 0), (31.35, 0.12), (33.9, 0.12),
              (34.0, 0)],
    "look": [(0, (0, -0.5)), (17.7, (0, -0.5)), (17.8, (0, -0.1)), (19.2, (0, -0.1)), (19.45, (0, -0.5)),
             (30.75, (0, -0.5)), (31.0, (0, 0.5)), (33.9, (0, 0.5)), (35.7, (0.15, 0.15)), (37.6, (0.15, 0.15)),
             (37.75, (0, -1.0)), (38.2, (0, -1.0)), (38.4, (0, 0.3))],
    "lid": [(0, 0), (19.3, 0), (19.6, 0.15), (22.6, 0.15), (22.7, 0), (24.6, 0), (24.75, 0.2), (26.6, 0.3),
            (28.4, 0.35), (30.7, 0.35), (30.9, 0.55), (35.7, 0.55), (35.76, 0.7), (36.4, 0.7),
            (37.6, 0.25), (38.3, 0.3), (38.9, 0.6), (40, 0.7)],
    "happy": [(0, 1), (3.3, 1), (3.33, 0), (8.22, 0), (8.25, 1), (9.4, 1), (9.43, 0), (10.63, 0),
              (10.66, 1), (13.1, 1), (13.13, 0), (40, 0)],
    "brow": [(0, 0), (6.3, 0), (6.4, -0.35), (8.2, -0.35), (8.25, 0), (16.0, 0), (16.6, 0.55), (17.7, 0.55),
             (17.75, 0.35), (19.2, 0.35), (19.6, 0.75), (22.6, 0.75), (22.7, 0.9), (26.5, 0.9),
             (26.75, 1.0), (40, 1.0)],
    "tear": saw(26.9, 40, 1.35),
    "tear_a": [(0, 0), (26.9, 0), (27.6, 1), (40, 1)],
    "blush": [(0, 0.4), (16.0, 0.4), (16.5, 0), (40, 0)],
    "laugh": [(0, 1), (16.0, 1), (16.2, 0), (40, 0)],
    "crown": [(0, 0)], "walk": [(0, 0)], "speed": [(0, 0)], "hp": [(0, 0)], "paint": [(0, 1)],
    "desat": [(0, 0)],
    "swag": [(0, 0.6), (16.0, 0.6), (16.2, 0)],
    "flag_ang": [(0, 0.25), (16.0, 0.25), (16.4, 1.0), (17.65, 1.0), (17.8, 0.1), (19.3, 0.1), (20.3, 0.75), (30.7, 0.85)],
    "cry": [(0, 0), (30.75, 0), (31.05, 1), (40, 1)],
}
_chant = [(13.12 + k * BEAT, "shout" if k % 2 == 0 else "hum") for k in range(5)]
MOUTH = ([(0, "grin"), (4.55, "grin"), (6.39, "shout"), (10.63, "grin")] + _chant +
         [(16.18, "hum"), (16.9, "flat"), (17.72, "shock"), (19.3, "flat"), (20.3, "frown"), (22.69, "shock"),
          (23.05, "frown"), (30.72, "cry"), (37.62, "frown"), (38.0, "cry")])
LAP_L, LAP_R = ("hip", -100, -6), ("hip", 100, -6)
ON_HEAD_L, ON_HEAD_R = ("head", -125, -95), ("head", 125, -95)
FACE_L, FACE_R = ("head", -46, 20), ("head", 46, 20)
HAND_L = [(0, ("pump", -1)), (4.45, ("pump", -1)), (4.6, ("clap", -1)), (6.3, ("clap", -1)),
          (6.45, ("pump", -1)), (16.0, ("pump", -1)), (16.4, ("head", -16, 172)), (17.65, ("head", -16, 172)),
          (17.8, ON_HEAD_L), (19.2, ON_HEAD_L), (19.65, LAP_L), (22.6, LAP_L), (22.8, ON_HEAD_L),
          (24.6, ON_HEAD_L), (24.85, FACE_L), (26.5, FACE_L), (26.75, LAP_L), (32.8, LAP_L), (33.0, ("rub", -1)),
          (33.6, ("rub", -1)), (33.8, LAP_L), (35.6, LAP_L), (35.76, ("rub", -1)), (36.4, ("rub", -1)),
          (36.6, LAP_L)]
HAND_R = [(0, ("wave",)), (4.45, ("wave",)), (4.6, ("clap", 1)), (6.3, ("clap", 1)), (6.45, ("pump", 1)),
          (10.5, ("pump", 1)), (10.63, ("wave",)), (13.0, ("wave",)), (13.12, ("pump", 1)), (16.0, ("pump", 1)),
          (16.4, ("head", 16, 172)), (17.65, ("head", 16, 172)), (17.8, ON_HEAD_R), (19.2, ON_HEAD_R),
          (19.65, LAP_R), (22.6, LAP_R), (22.8, ON_HEAD_R), (24.6, ON_HEAD_R), (24.85, FACE_R), (26.5, FACE_R),
          (26.75, LAP_R), (35.6, LAP_R), (35.76, ("rub", 1)), (36.4, ("rub", 1)), (36.6, LAP_R)]
FLAG_DROP = 30.72


def hand_pos(keys, t, hip, head, walk):
    phase = math.pi * (t - BEAT0) / BEAT

    def resolve(spec):
        kind = spec[0]
        if kind == "pump":
            s_ = spec[1]
            return (head[0] + s_ * 165, head[1] - 205 + 34 * math.sin(phase * 2 + (0 if s_ < 0 else 1.2)))
        if kind == "wave":
            return (head[0] + 180 + 38 * math.sin(t * 12), head[1] - 150)
        if kind == "clap":       # hands meet on every beat
            f = beat_phase(t)
            gap = 14 + 74 * smooth(min(f, 1 - f) * 2.2)
            return (head[0] + spec[1] * gap, head[1] + 182)
        if kind == "rub":        # sleeve rubbing the eye
            return (head[0] + spec[1] * 50 + 12 * math.sin(t * 16), head[1] + 16 + 4 * math.cos(t * 16))
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


def skip_at(t):
    """Jumps on every beat while cheering in the wide shots."""
    if 2.11 < t < 4.5 or 10.63 < t < 13.05:
        return abs(math.sin(math.pi * (t - BEAT0) / BEAT)) * 44
    return 0.0


_orig_head = m.draw_head


def blink(t):
    u = (t + 0.7) % 3.4
    return 1.0 if u < 0.11 else 0.0


def draw_head(t, p):
    """The rig's head plus a big shout, a shocked O, a crying mouth, tear streams and blinks."""
    p = dict(p)
    mouth = p["mouth"]
    custom = mouth in ("shout", "shock", "cry")
    if custom:
        p["mouth"] = "none"
    if p["happy"] < 0.5 and p["lid"] < 0.9 and blink(t):
        p["lid"] = 1.0
    img = _orig_head(t, p)
    pen = m.Pen(img, 0, 0, K)
    cx, cy = 180, 310
    mx, my = cx, cy + 90
    red, LINE = (120, 34, 50), m.LINE
    if mouth == "shout":
        oh = 34 + 8 * math.sin(t * 18) * p["laugh"]
        pen.poly([(mx - 34, my - 8)] + [(mx + 34 * math.cos(math.radians(a)), my - 8 + oh * math.sin(math.radians(a)))
                                         for a in range(0, 181, 12)], red, LINE, 3)
        pen.poly([(mx - 30, my - 6), (mx + 30, my - 6), (mx + 26, my + 2), (mx - 26, my + 2)], (255, 255, 255))
        pen.ellipse(mx - 16, my + oh - 22, mx + 16, my + oh - 6, (240, 110, 120))
    elif mouth == "shock":
        pen.ellipse(mx - 19, my - 12, mx + 19, my + 36, red, LINE, 3)
        pen.ellipse(mx - 11, my + 18, mx + 11, my + 32, (210, 90, 104))
    elif mouth == "cry":
        wob = math.sin(t * 24) * 3
        top = [(mx + x, my + 12 - 12 * (1 - (x / 28) ** 2)) for x in range(-28, 29, 7)]
        bot = [(mx + x, my + 24 + wob * math.sin(x * 0.3) + 3 * (1 - (x / 28) ** 2)) for x in range(28, -29, -7)]
        pen.poly(top + bot, red, LINE, 3)
        pen.line([(mx - 18, my + 4), (mx + 18, my + 4)], (255, 255, 255), 3)
    cry = p.get("cry", 0)
    if cry > 0.01:                       # two streams and drops sliding down to the chin
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        lp = m.Pen(lay, 0, 0, K)
        a = int(210 * cry)
        for sx in (-1, 1):
            x0, y0 = cx + sx * 56, cy + 44
            pts = [(x0 + sx * 6 * (k / 6) + 2 * math.sin(t * 6 + k + sx), y0 + 15 * k) for k in range(7)]
            lp.line(pts, (170, 215, 255, a // 2), 8)
            for ph in (0.0, 0.5):
                u = (t * 0.9 + ph + (0.25 if sx > 0 else 0)) % 1.0
                tx, ty = x0 + sx * 6 * u, y0 + 90 * u
                lp.poly([(tx, ty - 16), (tx - 8, ty), (tx + 8, ty)], (165, 210, 255, a))
                lp.circle(tx, ty + 2, 8, (165, 210, 255, a))
                lp.circle(tx - 3, ty - 1, 2.5, (255, 255, 255, a))
        img.alpha_composite(lay)
    return img


def walk_phase(t):
    return math.pi * (t - BEAT0) / BEAT


_orig_char = m.draw_character


def draw_character(t):
    """The rig draws arms behind the head; redraw a forearm on top when the hand is at his face."""
    img, origin, head = _orig_char(t)
    pen = m.Pen(img, origin[0], origin[1], K)
    p = {k: track(T[k], t) for k in ("sink", "slump", "laugh")}
    hip_y = 1250 + p["sink"] - skip_at(t)
    sy = hip_y - 330 + p["slump"] * 34 + math.sin(t * 2.2) * 3 + p["laugh"] * abs(math.sin(t * 11)) * 5
    for s_, key in ((-1, "L"), (1, "R")):
        hand = m.LAST_HANDS.get(key)
        if hand and abs(hand[0] - head[0]) < 95 and -40 < hand[1] - head[1] < 150:
            sh = (540 + s_ * 104, sy + 30)
            vx, vy = sh[0] - hand[0], sh[1] - hand[1]
            n = max(1.0, math.hypot(vx, vy))
            wrist = (hand[0] + vx / n * 80, hand[1] + vy / n * 80)   # sleeve heads back towards his shoulder
            pen.limb(wrist, hand, 50, m.HOOD)
            pen.circle(*hand, 27, m.SKIN, m.LINE, 3)
    return img, origin, head


m.T, m.MOUTH, m.HAND_L, m.HAND_R = T, MOUTH, HAND_L, HAND_R
m.draw_character = draw_character
m.hand_pos, m.skip_at, m.draw_head, m.walk_phase = hand_pos, skip_at, draw_head, walk_phase
m.BEAT, m.FB, m.FLAG_HELD = BEAT, (0, 99), (0, FLAG_DROP)


# ==============================================================================================
# the room (world space, same units as the rig: he stands at x 540, hips at y 1250)
# ==============================================================================================
EX0, EY0, EW, EH = -800, -1500, 2680, 3900


def build_room():
    img = Image.new("RGBA", (EW, EH), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)

    def P(x, y):
        return (x - EX0, y - EY0)
    for y in range(EY0, EY0 + EH, 8):                       # wall
        f = clamp((y + 300) / 2000)
        d.rectangle([P(EX0, y), P(EX0 + EW, y + 8)], fill=(int(lerp(40, 24, f)), int(lerp(44, 26, f)),
                                                            int(lerp(72, 44, f)), 255))
    for x in range(EX0, EX0 + EW, 130):
        d.line([P(x, EY0), P(x, 1700)], fill=(46, 50, 80, 255), width=3)
    # window at the left: night sky, moon, city lights
    wx0, wy0, wx1, wy1 = -360, 300, 160, 900
    d.rectangle([P(wx0 - 22, wy0 - 22), P(wx1 + 22, wy1 + 22)], fill=(16, 16, 24, 255))
    for y in range(wy0, wy1, 6):
        f = (y - wy0) / (wy1 - wy0)
        d.rectangle([P(wx0, y), P(wx1, y + 6)], fill=(int(lerp(14, 46, f)), int(lerp(20, 40, f)), int(lerp(52, 86, f)), 255))
    rnd = random.Random(4)
    for _ in range(60):
        sx_, sy_ = rnd.uniform(wx0, wx1), rnd.uniform(wy0, wy0 + 300)
        d.ellipse([P(sx_ - 2, sy_ - 2), P(sx_ + 2, sy_ + 2)], fill=(200, 210, 255, 255))
    x = wx0
    while x < wx1:
        bw, bh = rnd.randint(50, 110), rnd.randint(120, 330)
        d.rectangle([P(x, wy1 - bh), P(x + bw, wy1)], fill=(18, 18, 30, 255))
        for _ in range(bw * bh // 900):
            lx, ly = rnd.uniform(x + 6, x + bw - 10), rnd.uniform(wy1 - bh + 8, wy1 - 10)
            d.rectangle([P(lx, ly), P(lx + 7, ly + 9)], fill=(255, 205, 120, 255) if rnd.random() < 0.6 else (90, 110, 170, 255))
        x += bw + rnd.randint(2, 14)
    d.line([P((wx0 + wx1) / 2, wy0), P((wx0 + wx1) / 2, wy1)], fill=(16, 16, 24, 255), width=14)
    d.line([P(wx0, (wy0 + wy1) / 2), P(wx1, (wy0 + wy1) / 2)], fill=(16, 16, 24, 255), width=14)
    for side in (-1, 1):                                    # curtains
        bx = wx0 - 60 if side < 0 else wx1 + 60
        pts = [P(bx - 70, wy0 - 60), P(bx + 70, wy0 - 60), P(bx + 50 + 20 * side, wy1 + 120), P(bx - 50 + 20 * side, wy1 + 120)]
        d.polygon(pts, fill=(76, 30, 52, 255))
        for k in (-30, 10, 40):
            d.line([P(bx + k, wy0 - 50), P(bx + k + 10 * side, wy1 + 110)], fill=(56, 20, 38, 255), width=6)
    # moon with a soft glow
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([P(-10, 360), P(150, 520)], fill=(200, 210, 255, 90))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(30)))
    d.ellipse([P(36, 404), P(110, 478)], fill=(236, 234, 214, 255))
    d.ellipse([P(58, 398), P(126, 466)], fill=(30, 30, 62, 255))   # crescent
    # poster at the right: bat and ball under stars, tricolour band
    px0, py0, px1, py1 = 800, 380, 1080, 820
    d.rectangle([P(px0 - 12, py0 - 12), P(px1 + 12, py1 + 12)], fill=(14, 14, 20, 255))
    d.rectangle([P(px0, py0), P(px1, py1)], fill=(18, 40, 96, 255))
    for k, col in enumerate(((255, 153, 51), (245, 245, 245), (19, 136, 8))):
        d.rectangle([P(px0, py1 - 90 + k * 30), P(px1, py1 - 60 + k * 30)], fill=col + (255,))
    d.polygon([P(900, 470), P(930, 462), P(1000, 690), P(975, 700)], fill=(222, 196, 140, 255))
    d.rectangle([P(888, 440), P(922, 476)], fill=(80, 50, 30, 255))
    d.ellipse([P(1000, 640), P(1040, 680)], fill=(200, 40, 40, 255))
    for _ in range(14):
        sx_, sy_ = rnd.uniform(px0 + 10, px1 - 10), rnd.uniform(py0 + 10, py0 + 200)
        d.ellipse([P(sx_ - 3, sy_ - 3), P(sx_ + 3, sy_ + 3)], fill=(255, 240, 200, 255))
    # sofa behind him
    d.rounded_rectangle([P(10, 990), P(1070, 1420)], radius=70, fill=(36, 70, 84, 255), outline=(18, 34, 42, 255), width=8)
    for x0 in (60, 560):
        d.rounded_rectangle([P(x0, 1040), P(x0 + 460, 1330)], radius=50, fill=(44, 84, 100, 255))
    for x0 in (-80, 1000):
        d.rounded_rectangle([P(x0, 1150), P(x0 + 160, 1500)], radius=60, fill=(30, 60, 72, 255), outline=(18, 34, 42, 255), width=8)
    d.rounded_rectangle([P(30, 1340), P(1050, 1520)], radius=40, fill=(40, 78, 92, 255))
    # floor
    d.rectangle([P(EX0, 1660), P(EX0 + EW, EY0 + EH)], fill=(40, 30, 34, 255))
    for y in range(1680, 2400, 70):
        d.line([P(EX0, y), P(EX0 + EW, y)], fill=(30, 22, 26, 255), width=4)
    return img


def build_lights():
    """Warm fairy lights strung across the wall (drawn separately so they can twinkle)."""
    img = Image.new("RGBA", (EW, EH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bulbs = []
    for (x0, x1, y0, sag) in ((-500, 520, 250, 90), (520, 1560, 250, 90)):
        pts = []
        for k in range(41):
            u = k / 40
            x = lerp(x0, x1, u)
            y = y0 + sag * 4 * u * (1 - u)
            pts.append((x - EX0, y - EY0))
            if k % 4 == 2:
                bulbs.append((x, y + 14))
        d.line(pts, fill=(20, 20, 26, 255), width=4)
    return img, bulbs


def build_table():
    img = Image.new("RGBA", (1280, 560), (0, 0, 0, 0))   # world x -100..1180, y 1300..1860
    d = ImageDraw.Draw(img)

    def P(x, y):
        return (x + 100, y - 1300)
    d.polygon([P(90, 1470), P(990, 1470), P(1040, 1525), P(40, 1525)], fill=(104, 72, 54, 255))
    d.rectangle([P(40, 1525), P(1040, 1720)], fill=(74, 50, 38, 255))
    d.line([P(40, 1525), P(1040, 1525)], fill=(130, 94, 70, 255), width=5)
    for x in (70, 990):
        d.rectangle([P(x, 1720), P(x + 30, 1800)], fill=(50, 34, 26, 255))
    # popcorn bowl, two cans, the remote
    d.chord([P(160, 1400), P(360, 1520)], 0, 180, fill=(200, 40, 44, 255))
    for k in range(16):
        bx, by = 180 + (k * 37) % 170, 1418 + (k * 13) % 30
        d.ellipse([P(bx, by), P(bx + 26, by + 22)], fill=(250, 236, 190, 255) if k % 3 else (255, 210, 120, 255))
    d.rectangle([P(150, 1452), P(370, 1466)], fill=(230, 60, 64, 255))
    for i, col in enumerate(((40, 90, 200), (220, 40, 40))):
        x = 770 + i * 70
        d.rectangle([P(x, 1400), P(x + 46, 1480)], fill=col + (255,))
        d.ellipse([P(x, 1392), P(x + 46, 1408)], fill=(190, 190, 200, 255))
        d.ellipse([P(x, 1472), P(x + 46, 1488)], fill=tuple(int(c * 0.7) for c in col) + (255,))
    d.rounded_rectangle([P(520, 1482), P(640, 1504)], radius=8, fill=(26, 26, 32, 255))
    d.ellipse([P(530, 1488), P(542, 1498)], fill=(220, 50, 50, 255))
    return img


ROOM = build_room()
LIGHTS, BULBS = build_lights()
TABLE = build_table()


# ==============================================================================================
# clip
# ==============================================================================================
FR = None
COLS = None


def load_clip():
    global FR, COLS
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", CLIP, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE, check=True).stdout
    FR = np.frombuffer(raw, np.uint8).reshape(-1, CH, CW, 3)
    c = FR[:, ::12, ::12].reshape(len(FR), -1, 3).mean(axis=1)
    k = 9
    pad = np.pad(c, ((k // 2, k // 2), (0, 0)), mode="edge")
    COLS = np.stack([pad[i:i + len(c)] for i in range(k)]).mean(axis=0)


def clip_index(t):
    return int(clamp(clip_time(t) * CFPS, 0, len(FR) - 1))


def clip_image(t):
    return Image.fromarray(FR[clip_index(t)])


def tv_light(t):
    """Colour (0..1) and strength of the light the screen throws into the room."""
    c = COLS[clip_index(t)] / 255.0
    lum = float(c @ np.array([0.299, 0.587, 0.114]))
    sat = c / max(c.max(), 1e-3)
    on = 1.0 - smooth((t - TV_OFF[0]) / (TV_OFF[1] - TV_OFF[0]))
    if t > TV_OFF[1]:
        on = 0.0
    return sat * (0.55 + 0.6 * lum) * on, on


# ==============================================================================================
# helpers: transforms, cracks, hearts, impacts
# ==============================================================================================
def xform(img, origin, k, cam, anchor, depth=1.0):
    z, fx, fy, rot = cam[:4]
    z = 1 + (z - 1) * depth
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    ax, ay = anchor
    a, b = k * cr / z, k * sr / z
    d_, e = -k * sr / z, k * cr / z
    c = k * (fx - origin[0]) - a * ax - b * ay
    f = k * (fy - origin[1]) - d_ * ax - e * ay
    return img.transform((W, H), Image.AFFINE, (a, b, c, d_, e, f), resample=Image.BILINEAR)


def to_screen(cam, anchor, x, y):
    z, fx, fy, rot = cam[:4]
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    dx, dy = (x - fx) * z, (y - fy) * z
    return anchor[0] + cr * dx - sr * dy, anchor[1] + sr * dx + cr * dy


def persp_coeffs(src, dst):
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def keystone(img, k):
    """Low angle: the top of the picture shrinks towards the middle."""
    if k <= 0:
        return img
    src = [(-W * k / 2, -H * 0.04), (W + W * k / 2, -H * 0.04), (W, H), (0, H)]
    dst = [(0, 0), (W, 0), (W, H), (0, H)]
    return img.transform((W, H), Image.PERSPECTIVE, persp_coeffs(src, dst), resample=Image.BILINEAR)


def make_cracks(seed, ox, oy, n, reach):
    rnd = random.Random(seed)
    rays = []
    for i in range(n):
        ang = 2 * math.pi * i / n + rnd.uniform(-0.25, 0.25)
        L = reach * rnd.uniform(0.45, 1.0)
        pts, x, y = [(ox, oy)], ox, oy
        segs = rnd.randint(5, 8)
        for _ in range(segs):
            a2 = ang + rnd.uniform(-0.4, 0.4)
            x += math.cos(a2) * L / segs
            y += math.sin(a2) * L / segs * (1000 / 747)
            pts.append((x, y))
        rays.append(pts)
    rings = []
    for r in (0.05, 0.12):
        ring = []
        for pts in rays:
            j = min(len(pts) - 1, max(1, int(r / reach * len(pts) * 1.6)))
            ring.append(pts[j])
        if rnd.random() < 0.9:
            rings.append(ring + ring[:1])
    return rays, rings


CRACKS = [make_cracks(11 + i, o[0], o[1], int(6 + 3 * s), 0.28 + 0.22 * s) for i, (_, s, o) in enumerate(IMPACTS)]


def draw_cracks(size, t):
    pw, ph = size
    lay = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    any_ = False
    for (t0, s, o), (rays, rings) in zip(IMPACTS, CRACKS):
        g = clamp((t - t0) / 0.14)
        if g <= 0:
            continue
        any_ = True
        for pts in rays:
            n = max(2, int(math.ceil(len(pts) * g)))
            q = [(x * pw, y * ph) for x, y in pts[:n]]
            d.line([(x + 2, y + 2) for x, y in q], fill=(0, 0, 0, 150), width=4)
            d.line(q, fill=(235, 240, 255, 225), width=2)
        if g >= 1:
            for ring in rings:
                q = [(x * pw, y * ph) for x, y in ring]
                d.line(q, fill=(235, 240, 255, 150), width=2)
        d.ellipse([o[0] * pw - 14 * s, o[1] * ph - 14 * s, o[0] * pw + 14 * s, o[1] * ph + 14 * s], fill=(240, 245, 255, 120))
    return lay if any_ else None


def impact_fx(t):
    flash, shake, split, red = 0.0, (0.0, 0.0), 0.0, 0.0
    for t0, s, _ in IMPACTS:
        dt = t - t0
        if -0.05 < dt < 0.9:
            if dt >= 0:
                amp = 30 * s * math.exp(-dt / 0.22)
                shake = (shake[0] + amp * math.sin(dt * 71), shake[1] + amp * math.cos(dt * 53))
                split = max(split, 12 * s * math.exp(-dt / 0.18))
            fl = math.exp(-(dt / 0.07) ** 2) * min(1.0, 0.75 * s)
            flash = max(flash, fl)
            if s > 1.2:
                red = max(red, fl)
    return flash, shake, split, red


def heart(d, x, y, s, half=0, col=(235, 40, 70), a=255, rot=0.0, dx=0.0, dy=0.0):
    pts = m.heart_pts(0, 0, s, half)
    cr, sr = math.cos(rot), math.sin(rot)
    q = [(x + dx + px * cr - py * sr, y + dy + px * sr + py * cr) for px, py in pts]
    d.polygon(q, fill=col + (a,), outline=(60, 0, 20, a))


def draw_heart_break(frame, t, t0, x, y, s, shatter=False):
    """A glowing heart pops in, cracks, and falls apart in two halves (or shatters)."""
    dt = t - t0
    if dt < 0 or dt > 1.5:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    a = int(255 * clamp(dt / 0.08) * (1 - smooth((dt - 1.1) / 0.4)))
    sc = s * (m.back_out(dt / 0.25) if dt < 0.25 else 1.0)
    if dt < 0.42:
        heart(d, x, y, sc, a=a)
        if dt > 0.3:   # crack line
            crack = [(0, -5), (-3, -1), (3, 3), (-2, 7), (0, 12)]
            d.line([(x + cx * sc, y + cy * sc) for cx, cy in crack], fill=(30, 0, 10, a), width=max(3, int(sc * 0.5)))
    elif not shatter:
        u = dt - 0.42
        for side in (-1, 1):
            heart(d, x, y, sc, half=side, a=a, rot=side * 0.5 * u, dx=side * 70 * u, dy=260 * u * u)
    else:
        u = dt - 0.42
        rnd = random.Random(7)
        for k in range(14):
            ang = rnd.uniform(0, 2 * math.pi)
            sp = rnd.uniform(200, 520)
            px, py = x + math.cos(ang) * sp * u, y + math.sin(ang) * sp * u + 700 * u * u
            r = sc * rnd.uniform(1.5, 3.2)
            rot = rnd.uniform(0, 6) + u * rnd.uniform(-6, 6)
            tri = [(px + r * math.cos(rot + j * 2.1), py + r * math.sin(rot + j * 2.1)) for j in range(3)]
            d.polygon(tri, fill=(235, 40, 70, a), outline=(60, 0, 20, a))
    glow = lay.filter(ImageFilter.GaussianBlur(22))
    frame.alpha_composite(glow)
    frame.alpha_composite(lay)


def speed_lines(frame, t, cx, cy, a=170):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rnd = random.Random(int(t * 15))
    for _ in range(80):
        ang = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(560, 760)
        wdt = rnd.uniform(0.004, 0.012)
        p0 = (cx + math.cos(ang) * r0, cy + math.sin(ang) * r0 * 1.3)
        p1 = (cx + math.cos(ang - wdt) * 1500, cy + math.sin(ang - wdt) * 1950)
        p2 = (cx + math.cos(ang + wdt) * 1500, cy + math.sin(ang + wdt) * 1950)
        d.polygon([p0, p1, p2], fill=(255, 255, 255, a))
    frame.alpha_composite(lay)


def confetti(frame, t):
    if not (HYPE[0] <= t < HYPE[1] + 1.0):
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cols = ((255, 153, 51), (250, 250, 250), (19, 136, 8))
    nb = int((t - BEAT0) / BEAT)
    for b in range(nb - 2, nb + 1):
        tb = BEAT0 + b * BEAT
        if b % 2 or not (HYPE[0] <= tb < HYPE[1]):
            continue
        u = t - tb
        if not (0 <= u < 1.2):
            continue
        rnd = random.Random(b)
        for side in (-1, 1):
            ox, oy = (PANEL[0] + 20, PANEL[3] - 10) if side < 0 else (PANEL[2] - 20, PANEL[3] - 10)
            for _ in range(12):
                vx = -side * rnd.uniform(-60, 380) * -1
                vy = rnd.uniform(-520, -160)
                x, y = ox + vx * u, oy + vy * u + 900 * u * u
                r = rnd.uniform(7, 13)
                rot = rnd.uniform(0, 6) + u * 9
                col = cols[rnd.randrange(3)]
                al = int(255 * (1 - smooth((u - 0.8) / 0.4)))
                pts = [(x + r * math.cos(rot + j * math.pi / 2) * (1 if j % 2 else 0.5),
                        y + r * math.sin(rot + j * math.pi / 2) * (1 if j % 2 else 0.5)) for j in range(4)]
                d.polygon(pts, fill=col + (al,))
    frame.alpha_composite(lay)


# ==============================================================================================
# the room shot (lit by the screen)
# ==============================================================================================
G_ENV = np.clip(1.25 - (YY[:, :1] - 900) / 1500, 0.4, 1.25)[:, :, None]


def room_shot(t, cam, anchor):
    char_img, origin, head = m.draw_character(t)
    tvc, on = tv_light(t)
    amb = np.array([0.16, 0.17, 0.26], np.float32) * (0.75 + 0.25 * on)
    pulse = 0.18 * math.exp(-since_beat(t) / 0.16) if HYPE[0] <= t < HYPE[1] else 0.0
    env_mult = amb + tvc.astype(np.float32) * (0.55 + pulse) * G_ENV
    char_mult = (amb * 1.25 + tvc.astype(np.float32) * (0.95 + pulse)).reshape(1, 1, 3)

    env_cam = cam
    env = xform(ROOM, (EX0, EY0), 1, env_cam, anchor, depth=0.92)
    out = np.asarray(env.convert("RGB")).astype(np.float32) * env_mult
    # fairy lights twinkle (not affected by the TV light)
    lights = xform(LIGHTS, (EX0, EY0), 1, env_cam, anchor, depth=0.92)
    bl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bl)
    z = 1 + (cam[0] - 1) * 0.92
    for i, (bx, by) in enumerate(BULBS):
        sx, sy = to_screen((z,) + tuple(cam[1:4]), anchor, bx, by)
        tw = 0.55 + 0.45 * math.sin(t * 3 + i * 1.7)
        r = 9 * z
        col = ((255, 196, 110), (255, 150, 90), (255, 230, 160))[i % 3]
        bd.ellipse([sx - r * 3, sy - r * 3, sx + r * 3, sy + r * 3], fill=col + (int(60 * tw),))
        bd.ellipse([sx - r, sy - r, sx + r, sy + r], fill=col + (int(255 * (0.4 + 0.6 * tw)),))
    bl = bl.filter(ImageFilter.GaussianBlur(3 * z))
    lights.alpha_composite(bl)
    la = np.asarray(lights).astype(np.float32)
    out = out * (1 - la[:, :, 3:] / 255) + la[:, :, :3] * (la[:, :, 3:] / 255) * (0.5 + 0.5 * on)

    char = xform(char_img, origin, K, cam, anchor)
    flag = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m.draw_flag(flag, t)
    flag = xform(flag, (0, 0), 1, cam, anchor)
    table = xform(TABLE, (-100, 1300), 1, cam, anchor)
    layers = [(char, char_mult, True), (table, env_mult * 1.25 + 0.04, False)]
    if t < FLAG_DROP + 0.5:
        layers.insert(1, (flag, char_mult, False))
    else:
        layers.append((flag, char_mult * 0.8, False))
    for img, mult, rim in layers:
        arr = np.asarray(img).astype(np.float32)
        A = arr[:, :, 3:] / 255.0
        rgb = arr[:, :, :3] * mult
        if rim:   # cool moonlight rim on his left edges, warm TV rim on top
            sh = max(3, int(6 * cam[0]))
            A2 = np.roll(A, sh, axis=1)
            A3 = np.roll(A, sh, axis=0)
            rim_m = np.clip(A - A2, 0, 1) * 0.85
            top_m = np.clip(A - A3, 0, 1) * 0.6 * on
            rgb = rgb + rim_m * np.array([150, 180, 255], np.float32) + top_m * (tvc.astype(np.float32) * 255 + 60)
        out = out * (1 - A) + rgb * A
    res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    return keystone(res, cam[4] if len(cam) > 4 else 0), head


# ==============================================================================================
# panel / full clip
# ==============================================================================================
def grade_clip(img, t):
    arr = np.asarray(img).astype(np.float32)
    arr = (arr - 128) * 1.08 + 124
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def border_colour(t):
    if t < IMPACTS[0][0]:
        return None
    if t < IMPACTS[2][0]:
        fl = 0.8 + 0.2 * math.sin(t * 37) * math.exp(-(t - 17.72) / 1.5)
        return tuple(int(c * fl) for c in (190, 205, 255))
    return (int(150 + 60 * math.exp(-since_beat(t) / 0.3)), 40, 56)


def draw_panel(frame, t, rect, src_box=None, radius=28, alpha=1.0, glow=True):
    x0, y0, x1, y1 = [int(round(v)) for v in rect]
    pw, ph = max(2, x1 - x0), max(2, y1 - y0)
    img = clip_image(t)
    if src_box is not None:
        img = img.crop(tuple(int(v) for v in src_box))
    img = grade_clip(img.resize((pw, ph), Image.BILINEAR), t).convert("RGBA")
    cr = draw_cracks((pw, ph), t)
    if cr is not None:
        img.alpha_composite(cr)
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=radius, fill=int(255 * alpha))
    if glow:
        # light spill around the screen, then a tricolour / white / red rim
        spill = img.resize((max(2, pw // 8), max(2, ph // 8))).resize((pw + 160, ph + 160)).filter(ImageFilter.GaussianBlur(40))
        sm = Image.new("L", spill.size, 0)
        ImageDraw.Draw(sm).rounded_rectangle([60, 60, pw + 100, ph + 100], radius=radius + 30, fill=int(150 * alpha))
        spill.putalpha(sm.filter(ImageFilter.GaussianBlur(40)))
        frame.alpha_composite(spill, (x0 - 80, y0 - 80))
    frame.paste(img.convert("RGB"), (x0, y0), mask)
    if glow:
        rim = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rim)
        bc = border_colour(t)
        pulse = math.exp(-since_beat(t) / 0.18) if HYPE[0] <= t < HYPE[1] else 0.3
        if bc is None:   # tricolour: saffron top, white middle, green bottom
            band = Image.new("RGBA", rim.size, (0, 0, 0, 0))
            bdd = ImageDraw.Draw(band)
            for k, col in enumerate(((255, 153, 51), (255, 255, 255), (19, 170, 40))):
                bdd.rectangle([0, 40 + ph * k / 3 - (40 if k == 0 else 0), pw + 80, 40 + ph * (k + 1) / 3 + (40 if k == 2 else 0)], fill=col + (255,))
            ring = Image.new("L", rim.size, 0)
            ImageDraw.Draw(ring).rounded_rectangle([40, 40, pw + 40, ph + 40], radius=radius, outline=255, width=6)
            rim = Image.new("RGBA", rim.size, (0, 0, 0, 0))
            rim.paste(band, (0, 0), ring)
        else:
            rd.rounded_rectangle([40, 40, pw + 40, ph + 40], radius=radius, outline=bc + (255,), width=5)
        g = rim.filter(ImageFilter.GaussianBlur(16))
        ga = g.getchannel("A").point(lambda v: int(min(255, v * (1.6 + 1.4 * pulse) * alpha)))
        g.putalpha(ga)
        frame.alpha_composite(g, (x0 - 40, y0 - 40))
        ra = rim.getchannel("A").point(lambda v: int(v * alpha))
        rim.putalpha(ra)
        frame.alpha_composite(rim, (x0 - 40, y0 - 40))


def full_crop(t):
    i = max(k for k, c in enumerate(FULL_CROP) if c[0] <= t)
    t0, x0, x1, z0, z1 = FULL_CROP[i]
    t1 = next((s[0] for s in SHOTS if s[0] > t0 and s[1] != "full"), DUR)
    t1 = min(t1, FULL_CROP[i + 1][0]) if i + 1 < len(FULL_CROP) else t1
    f = smooth((t - t0) / max(0.01, t1 - t0))
    cx, z = lerp(x0, x1, f), lerp(z0, z1, f)
    ch = CH / z
    cw = ch * 9 / 16
    cx = clamp(cx, cw / 2, CW - cw / 2)
    cy = CH / 2
    return (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)


def full_frame(t):
    box = full_crop(t)
    img = clip_image(t).crop(tuple(int(v) for v in box)).resize((W, H), Image.BICUBIC)
    img = img.filter(ImageFilter.UnsharpMask(radius=3, percent=70, threshold=2))
    img = grade_clip(img, t).convert("RGBA")
    return img


# ==============================================================================================
# frame
# ==============================================================================================
DESAT = [(0, 0.0), (17.7, 0.0), (17.75, 0.18), (30.6, 0.22), (30.75, 0.45), (40, 0.5)]


def render_frame(t):
    rng = np.random.default_rng(int(t * 1000))
    i, t0, t1, kind, c0, c1 = shot_at(t)
    flash, shake, split, red = impact_fx(t)
    if kind == "full":
        frame = full_frame(t)
        u = t - t0
        if u < 0.25 and t0 > 1:   # punch-in on the cut
            s = 1 + 0.06 * (1 - ease_out(u / 0.25))
            frame = frame.resize((int(W * s), int(H * s)), Image.BILINEAR).crop(
                (int((W * s - W) / 2), int((H * s - H) / 2), int((W * s - W) / 2) + W, int((H * s - H) / 2) + H))
    else:
        f = clamp((t - t0) / (t1 - t0))
        f = f * 0.35 + smooth(f) * 0.65
        cam = [lerp(a, b, f) for a, b in zip(c0, c1)]
        if HYPE[0] <= t < HYPE[1]:
            cam[0] *= 1 + 0.025 * math.exp(-since_beat(t) / 0.12)
        cam[1] += math.sin(t * 0.9) * 4
        cam[2] += math.cos(t * 0.7) * 4
        anchor = (540, 1440) if kind == "split" else (540, 960)
        room, head = room_shot(t, tuple(cam), anchor)
        frame = room.convert("RGBA")
        if kind == "split":
            # the intro: the full-screen clip shrinks into the panel
            u = (t - SHOTS[1][0]) / 0.38
            if u < 1:
                e = ease_out(u)
                fb = full_crop(SHOTS[1][0] - 0.01)
                rect = tuple(lerp(a, b, e) for a, b in zip((0, 0, W, H), PANEL))
                box = tuple(lerp(a, b, e) for a, b in zip(fb, (0, 0, CW, CH)))
                draw_panel(frame, t, rect, box, radius=int(28 * e), glow=e > 0.5)
            elif t >= TV_OFF[0]:
                v = (t - TV_OFF[0]) / (TV_OFF[1] - TV_OFF[0])
                if v < 0.6:   # squash to a bright line
                    w_ = v / 0.6
                    cy = (PANEL[1] + PANEL[3]) / 2
                    hh = lerp((PANEL[3] - PANEL[1]) / 2, 3, ease_out(w_))
                    rect = (PANEL[0], cy - hh, PANEL[2], cy + hh)
                    draw_panel(frame, t, rect, radius=int(28 * (1 - w_)), glow=True)
                    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(lay).rectangle([PANEL[0], cy - hh, PANEL[2], cy + hh], fill=(255, 255, 255, int(255 * w_)))
                    frame.alpha_composite(lay)
                elif v < 1.0:  # then shrink to a dot
                    w_ = (v - 0.6) / 0.4
                    cy = (PANEL[1] + PANEL[3]) / 2
                    hw = lerp((PANEL[2] - PANEL[0]) / 2, 4, ease_out(w_))
                    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(lay).rectangle([540 - hw, cy - 3, 540 + hw, cy + 3], fill=(255, 255, 255, 255))
                    lay = Image.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10)), lay)
                    frame.alpha_composite(lay)
                elif v < 1.6:
                    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    r = 6 * (1 - (v - 1) / 0.6)
                    cy = (PANEL[1] + PANEL[3]) / 2
                    ImageDraw.Draw(lay).ellipse([540 - r, cy - r, 540 + r, cy + r], fill=(255, 255, 255, 255))
                    frame.alpha_composite(lay.filter(ImageFilter.GaussianBlur(3)))
            else:
                s = 1 + (0.03 * math.exp(-since_beat(t) / 0.12) if HYPE[0] <= t < HYPE[1] else 0)
                cx, cy = (PANEL[0] + PANEL[2]) / 2, (PANEL[1] + PANEL[3]) / 2
                hw, hh = (PANEL[2] - PANEL[0]) / 2 * s, (PANEL[3] - PANEL[1]) / 2 * s
                draw_panel(frame, t, (cx - hw, cy - hh, cx + hw, cy + hh))
            confetti(frame, t)
        if kind == "boy" and (t0 == 18.02 and t < 19.0):
            speed_lines(frame, t, 540, 900, a=int(190 * (1 - smooth((t - 18.6) / 0.4))))
        # signs: the heart breaks when the catch lands, and shatters when Australia win
        if t0 == 18.02:
            draw_heart_break(frame, t, 18.12, 250, 520, 9)
        if 30.7 <= t < 32.2:
            draw_heart_break(frame, t, 30.74, 540, 560, 10, shatter=True)

    arr = np.asarray(frame.convert("RGB")).astype(np.float32)
    if split > 0.5:    # chromatic split on impacts
        sp = int(split)
        arr[:, :, 0] = np.roll(arr[:, :, 0], sp, axis=1)
        arr[:, :, 2] = np.roll(arr[:, :, 2], -sp, axis=1)
    if abs(shake[0]) + abs(shake[1]) > 0.5:
        arr = np.roll(arr, (int(shake[1]), int(shake[0])), axis=(0, 1))
    de = track(DESAT, t)
    if de > 0.01:
        lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
        arr = arr * (1 - de) + lum[:, :, None] * de
        arr = arr * np.array([0.96, 0.99, 1.05], np.float32) ** (de * 2)
    if flash > 0.01:
        tint = np.array([1.0, 0.35, 0.35], np.float32) if red > 0.5 * flash else np.array([1.0, 1.0, 1.0], np.float32)
        arr = arr + (255 * tint - arr) * flash * 0.85
    # small white dip on the hard cuts of the match-cut section
    for s_ in SHOTS:
        if s_[0] >= 33.9:
            dt = t - s_[0]
            if 0 <= dt < 0.1:
                arr = arr + (255 - arr) * 0.35 * (1 - dt / 0.1)
    arr *= VIG
    arr += rng.normal(0, 4.0, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    fade = min(clamp(t / 0.35), clamp((DUR - t) / 0.45))
    arr *= fade
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _work(i):
    return render_frame(i / FPS).tobytes()


def main():
    load_clip()
    if "--frames" in sys.argv:
        idx = [int(v) for v in sys.argv[sys.argv.index("--frames") + 1].split(",")]
        for i in idx:
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
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", SILENT, "-i", CLIP, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={DUR - 0.6:.2f}:d=0.6",
                    "-t", f"{DUR:.2f}", "-movflags", "+faststart", OUT], check=True)
    os.remove(SILENT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
