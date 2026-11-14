"""Animated story reel for the Hindi audio in assets/.

An anime-style boy, drawn and rigged entirely in code, acts out the lyrics:

  1. "वो लेके आए थे पैमाना नापने मेरे दर्द यहाँ"  - he sits alone in the rain, crying;
     shadow people walk in and hold a giant ruler over him to measure his pain.
  2. "देख के मुझको हँसता हुआ वो लौट गए..."         - he looks up and laughs; confused,
     they drop the ruler and walk away. His smile fades a little after.
  3. "हम भी अपने शहजादे हैं"                      - he stands up proud, a crown lands.
  4. "हमें ख्वाब वाब नहीं आते हैं"                  - eyes close; dream bubbles stay empty and pop.
  5. "हम भूल गए हैं सारा कुछ"                      - memories float around him and dissolve.
  6. "अब यही हमारी बातें हैं"                       - he looks up at the moon; camera pulls back.

The song's lyrics are the only text, shown music-video style in the lower
third, word by word. Each line gets its own camera angles with cuts,
whip-pans, a flash and a dip to black, and small signs pop up on key words
(a breaking heart on "दर्द", an eye on "देख", footprints on "लौट गए",
sparkles on "शहजादे", a cross on "नहीं", speech bubbles on "बातें").
Layers move at different depths with the camera for a 3D (2.5D) feel.

Usage: python3 make_story_reel.py  ->  writes story_reel.mp4 next to this file.
       python3 make_story_reel.py --frames 0,150,300  ->  writes preview PNGs only.
"""
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
DURATION = 18.78
HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "assets", "ReelAudio-98423.mp3")
OUT = os.path.join(HERE, "story_reel.mp4")
SILENT = os.path.join(HERE, "_story_video_only.mp4")
F_SYM = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

GROUND = 1640
HOR = 760        # horizon (camera eye level)
K = 2  # supersampling factor for the character


# ======================================================================
# helpers
# ======================================================================
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def back_out(t):
    t = clamp(t)
    c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_col(a, b, t):
    return tuple(lerp(x, y, t) for x, y in zip(a, b))


def track(keys, t):
    """Smoothly interpolate a list of (time, value) keys; values may be numbers or tuples."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            f = smooth((t - t0) / (t1 - t0)) if t1 > t0 else 1
            if isinstance(v0, tuple):
                return tuple(lerp(a, b, f) for a, b in zip(v0, v1))
            return lerp(v0, v1, f)
    return keys[-1][1]


def step(keys, t):
    v = keys[0][1]
    for k, val in keys:
        if t >= k:
            v = val
    return v


class Pen:
    """Draw in world coordinates onto a supersampled canvas."""

    def __init__(self, img, ox=0, oy=0, k=1):
        self.d = ImageDraw.Draw(img)
        self.ox, self.oy, self.k = ox, oy, k

    def p(self, x, y):
        return ((x - self.ox) * self.k, (y - self.oy) * self.k)

    def poly(self, pts, fill, outline=None, width=0):
        self.d.polygon([self.p(*q) for q in pts], fill=fill, outline=outline,
                       width=int(width * self.k))

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=None, width=0):
        a, b = self.p(x0, y0), self.p(x1, y1)
        self.d.ellipse([a, b], fill=fill, outline=outline, width=int(width * self.k))

    def circle(self, x, y, r, fill=None, outline=None, width=0):
        self.ellipse(x - r, y - r, x + r, y + r, fill, outline, width)

    def line(self, pts, fill, width):
        self.d.line([self.p(*q) for q in pts], fill=fill, width=max(1, int(width * self.k)),
                    joint="curve")

    def arc_line(self, cx, cy, rx, ry, a0, a1, fill, width, n=18):
        pts = [(cx + rx * math.cos(math.radians(lerp(a0, a1, i / n))),
                cy + ry * math.sin(math.radians(lerp(a0, a1, i / n)))) for i in range(n + 1)]
        self.line(pts, fill, width)

    def limb(self, a, b, w, col, outline=(14, 14, 24)):
        self.line([a, b], outline, w + 7)
        self.circle(*a, (w + 7) / 2, fill=outline)
        self.circle(*b, (w + 7) / 2, fill=outline)
        self.line([a, b], col, w)
        self.circle(*a, w / 2, fill=col)
        self.circle(*b, w / 2, fill=col)


def ik(s, target, l1, l2, bend):
    sx, sy = s
    dx, dy = target[0] - sx, target[1] - sy
    dist = clamp(math.hypot(dx, dy), 1, l1 + l2 - 1)
    a = math.atan2(dy, dx)
    alpha = math.acos(clamp((l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist), -1, 1))
    ea = a + bend * alpha
    elbow = (sx + l1 * math.cos(ea), sy + l1 * math.sin(ea))
    hand = (sx + dist * math.cos(a), sy + dist * math.sin(a))
    return elbow, hand


# ======================================================================
# story timeline (all character acting lives here)
# ======================================================================
LINES = [
    (0.14, 4.85, "वो लेके आए थे पैमाना नापने मेरे दर्द यहाँ"),
    (4.85, 9.55, "देख के मुझको हँसता हुआ वो लौट गए फिर जाने कहाँ"),
    (9.55, 11.80, "हम भी अपने शहजादे हैं"),
    (11.80, 13.90, "हमें ख्वाब वाब नहीं आते हैं"),
    (13.90, 16.15, "हम भूल गए हैं सारा कुछ"),
    (16.15, 18.78, "अब यही हमारी बातें हैं"),
]

BEAT = 0.47  # seconds per step: he walks on the song's beat

T = {
    "stand":   [(0, 1)],
    "slump":   [(0, 0.7), (4.95, 0.7), (5.5, 0.0)],
    "head_dy": [(0, 20), (4.95, 20), (5.45, 0), (16.2, 0), (16.9, -6)],
    "tilt":    [(0, -4), (4.9, -4), (5.4, 0), (5.9, 4), (7.6, 4), (8.2, 0), (11.8, 0),
                (12.4, 6), (13.9, 6), (14.4, -5), (16.1, -3), (16.9, 4)],
    "look":    [(0, (0.0, 0.7)), (4.95, (0.0, 0.7)), (5.4, (0.0, 0.0)), (14.1, (0, 0)),
                (14.5, (0.8, -0.1)), (15.6, (0.6, -0.2)), (16.0, (0, 0)), (17.4, (0, 0)),
                (17.9, (0.3, -0.6))],
    "lid":     [(0, 0.45), (4.95, 0.45), (5.35, 0.0), (7.6, 0.0), (8.0, 0.15), (11.9, 0.15),
                (12.5, 1.0), (13.9, 1.0), (14.2, 0.1)],
    "happy":   [(0, 0), (5.55, 0), (5.75, 1), (8.0, 1), (8.35, 0), (10.2, 0), (10.3, 1),
                (10.85, 1), (10.95, 0)],
    "brow":    [(0, 1.0), (5.0, 1.0), (5.5, 0.0), (7.8, 0.0), (8.3, -0.4), (11.8, -0.4),
                (12.4, 0.1), (14.3, 0.1), (14.6, 0.4), (15.6, 0.4), (16.2, -0.1)],
    "tear":    [(0, 0), (1.8, 0), (4.6, 1)],
    "tear_a":  [(0, 0), (1.8, 0), (2.2, 1), (5.0, 1), (5.5, 0)],
    "blush":   [(0, 0), (5.6, 0), (6.0, 0.7), (8.2, 0.7), (8.8, 0.3)],
    "laugh":   [(0, 0), (5.7, 0), (5.9, 1), (7.6, 1), (8.0, 0)],
    "crown":   [(0, 0), (10.35, 0), (10.75, 1)],
    # walking: step amplitude, swagger (bounce + sway) and forward speed (m/s)
    "walk":    [(0, 0.75), (4.9, 0.75), (5.4, 0.25), (6.2, 0.25), (6.6, 1.0), (10.0, 1.0),
                (10.1, 0.0), (10.8, 0.0), (11.1, 1.0), (12.2, 0.7), (13.9, 0.7), (14.1, 1.0)],
    "swag":    [(0, 0), (6.3, 0), (6.8, 1), (11.8, 1), (12.2, 0.55), (13.9, 0.55), (14.2, 1)],
    "speed":   [(0, 0.9), (4.9, 0.9), (5.4, 0.35), (6.2, 0.35), (6.8, 1.5), (10.0, 1.5),
                (10.2, 2.4), (10.8, 1.4), (12.0, 1.0), (13.9, 1.0), (14.2, 1.5), (18.78, 1.2)],
}
MOUTH = [(0, "frown"), (5.45, "smile"), (5.7, "grin"), (8.1, "smirk"), (10.2, "grin"),
         (10.95, "smirk"), (12.0, "hum"), (14.0, "smile"), (16.3, "grin"), (17.4, "smile")]
# hand targets: ("hip"|"head", dx, dy), ("swing", side), ("wave",)
HAND_L = [(0, ("hip", -62, -70)), (6.4, ("hip", -62, -70)), (6.9, ("head", -105, -35)),
          (9.9, ("head", -105, -35)), (10.2, ("head", -175, -210)), (10.8, ("head", -175, -210)),
          (11.15, ("swing", -1)), (11.9, ("swing", -1)), (12.3, ("head", -132, 15)),
          (13.85, ("head", -132, 15)), (14.2, ("swing", -1))]
HAND_R = [(0, ("hip", 62, -70)), (5.55, ("hip", 62, -70)), (6.0, ("head", 95, -40)),
          (6.9, ("head", 105, -35)), (9.9, ("head", 105, -35)), (10.2, ("head", 175, -210)),
          (10.8, ("head", 175, -210)), (11.15, ("swing", 1)), (11.9, ("swing", 1)),
          (12.3, ("head", 132, 15)), (13.85, ("head", 132, 15)), (14.2, ("swing", 1)),
          (14.4, ("swing", 1)), (14.9, ("hip", 330, -280)), (15.5, ("hip", 330, -270)),
          (15.9, ("swing", 1)), (16.4, ("swing", 1)), (16.8, ("wave",)), (18.78, ("wave",))]

# Shot list: (start, end, camera at start, camera at end, transition into the shot)
# camera = (zoom, pan_x, pan_y, roll_degrees); pan moves the point the camera looks at
# (negative y = look higher). His face sits around pan_y -336, his feet around +420.
SHOTS = [
    (0.00, 2.10, (1.00, 0, -20, 0), (1.10, 0, -40, 0), "fade"),         # wide: walking in the rain
    (2.10, 3.40, (2.20, 0, -335, 0), (2.40, 0, -338, 0), "cut"),        # close-up: tear
    (3.40, 4.85, (1.30, 0, -250, -4), (1.40, 0, -240, -4), "cut"),      # dutch medium: the ruler
    (4.85, 6.30, (2.50, 0, -332, 0), (2.20, 0, -335, 0), "whip"),       # close-up: he looks up, laughs
    (6.30, 7.60, (1.00, 0, 0, 0), (1.06, 0, -30, 0), "cut"),            # wide: swagger, they're confused
    (7.60, 8.70, (1.25, -170, -90, 2), (1.25, 130, -90, 2), "cut"),     # pan: hands behind head
    (8.70, 9.55, (1.80, 60, 380, 0), (1.80, -60, 380, 0), "cut"),       # low: stepping feet
    (9.55, 10.70, (1.30, 0, 150, 3), (1.12, 0, 40, 3), "cut"),          # low angle: the jump
    (10.70, 11.80, (1.90, 0, -330, 0), (2.15, 0, -340, 0), "flash"),    # hero close-up: crown
    (11.80, 13.90, (1.50, 0, -380, 0), (1.62, 0, -400, 0), "dip"),      # medium: vibing, no dreams
    (13.90, 16.15, (1.10, -70, -200, -2), (1.22, 70, -220, 2), "whip"), # orbit: memories dissolve
    (16.15, 18.78, (1.90, 0, -340, 0), (1.00, 0, -40, 0), "cut"),       # crane back: the moon road
]
WHIP = 0.2   # half-length of a whip-pan, seconds
DIP = 0.22   # half-length of a dip to black


def camera_at(t):
    for i, (t0, t1, c0, c1, _) in enumerate(SHOTS):
        if t0 <= t < t1 or i == len(SHOTS) - 1:
            f = clamp((t - t0) / (t1 - t0))
            f = f * 0.35 + smooth(f) * 0.65  # steady drift with a soft start/stop
            cam = list(lerp(a, b, f) for a, b in zip(c0, c1))
            break
    # whip-pans: the camera swings sideways through the cut
    for i, (t0, _, _, _, kind) in enumerate(SHOTS):
        if kind == "whip" and abs(t - t0) < WHIP:
            u = (t - t0) / WHIP  # -1..1
            cam[1] += 520 * (1 - abs(u)) ** 1.5 * (1 if u < 0 else -1)
    cam[1] += math.sin(t * 0.9) * 3  # handheld drift
    cam[2] += math.cos(t * 0.7) * 3
    return tuple(cam)


def transition_fx(t):
    """Returns (motion_blur 0..1, brightness 0..1, white_flash 0..1)."""
    blur, bright, flash = 0.0, 1.0, 0.0
    for t0, _, _, _, kind in SHOTS:
        if kind == "whip" and abs(t - t0) < WHIP:
            blur = max(blur, 1 - abs(t - t0) / WHIP)
        elif kind == "dip" and abs(t - t0) < DIP:
            bright = min(bright, smooth(abs(t - t0) / DIP))
        elif kind == "flash":
            flash = max(flash, math.exp(-((t - t0) / 0.1) ** 2) * 0.8)
    return blur, bright, flash


# Locations: (start, kind). Each is a road scene rendered in perspective.
LOCATIONS = [(0.0, "street"), (9.55, "golden"), (11.8, "park"), (13.9, "bridge"), (16.15, "moonroad")]


def location_at(t):
    return step(LOCATIONS, t)


# lighting per location: (sky top, sky bottom, scene tint); hard cuts between places
LIGHT = [
    (0.0, ((10, 14, 30), (30, 40, 70), (0.74, 0.85, 1.12))),
    (4.9, ((10, 14, 30), (30, 40, 70), (0.74, 0.85, 1.12))),
    (6.6, ((14, 20, 44), (52, 60, 100), (0.96, 0.96, 1.05))),
    (9.549, ((14, 20, 44), (52, 60, 100), (0.96, 0.96, 1.05))),
    (9.55, ((70, 34, 60), (250, 150, 80), (1.1, 1.0, 0.88))),
    (11.799, ((70, 34, 60), (250, 150, 80), (1.1, 1.0, 0.88))),
    (11.8, ((4, 8, 22), (16, 36, 52), (0.86, 0.96, 1.05))),
    (13.899, ((4, 8, 22), (16, 36, 52), (0.86, 0.96, 1.05))),
    (13.9, ((26, 12, 44), (120, 64, 136), (1.0, 0.9, 1.1))),
    (16.149, ((26, 12, 44), (120, 64, 136), (1.0, 0.9, 1.1))),
    (16.15, ((6, 10, 30), (40, 58, 104), (0.98, 0.97, 1.05))),
]


def light_at(t):
    keys = [(k, v[0] + v[1] + v[2]) for k, v in LIGHT]
    v = track(keys, t)
    return v[0:3], v[3:6], v[6:9]


def walk_phase(t):
    return math.pi * t / BEAT


def hand_pos(keys, t, hip, head, walk):
    phase = walk_phase(t)

    def resolve(spec):
        if spec[0] == "swing":
            s = spec[1]
            sw = math.sin(phase + (math.pi if s > 0 else 0)) * walk
            return (hip[0] + s * (122 + 10 * sw), hip[1] - 20 + 26 * sw)
        if spec[0] == "wave":
            return (head[0] + 180 + 38 * math.sin(t * 12), head[1] - 150)
        ref = hip if spec[0] == "hip" else head
        return (ref[0] + spec[1], ref[1] + spec[2])
    if t <= keys[0][0]:
        return resolve(keys[0][1])
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            f = smooth((t - t0) / (t1 - t0))
            pa, pb = resolve(a), resolve(b)
            return (lerp(pa[0], pb[0], f), lerp(pa[1], pb[1], f))
    return resolve(keys[-1][1])


def jump_at(t):
    """(height in px, squash in px) for the leap on 'शहजादे'."""
    crouch = math.sin(math.pi * clamp((t - 9.95) / 0.25)) * 26 if 9.95 < t < 10.2 else 0
    air = math.sin(math.pi * clamp((t - 10.2) / 0.55)) * 260 if 10.2 < t < 10.75 else 0
    land = math.sin(math.pi * clamp((t - 10.75) / 0.25)) * 30 if 10.75 < t < 11.0 else 0
    return air, crouch + land


def skip_at(t):
    """Little hops while walking on the bridge."""
    if 14.3 < t < 15.6:
        return abs(math.sin(walk_phase(t))) * 38
    return 0.0


# ======================================================================
# character
# ======================================================================
SKIN = (255, 226, 204)
SKIN_SH = (236, 190, 170)
HAIR = (30, 30, 46)
HAIR_HI = (86, 100, 150)
HOOD = (78, 92, 140)
HOOD_SH = (58, 68, 108)
PANTS = (34, 36, 52)
LINE = (14, 14, 24)
IRIS = (70, 110, 210)
IRIS_D = (32, 40, 100)

HEAD_W, HEAD_H = 360, 500
PIVOT = (180, 430)


def draw_head(t, p):
    img = Image.new("RGBA", (HEAD_W * K, HEAD_H * K), (0, 0, 0, 0))
    pen = Pen(img, 0, 0, K)
    cx, cy = 180, 310
    sway = math.sin(t * 2.3) * 3

    # hair back (spiky)
    pts = []
    for i in range(23):
        a = math.radians(150 + i * (240 / 22))
        r = 150 if i % 2 == 0 else 184
        if 200 < math.degrees(a) % 360 < 340:
            r += 6
        pts.append((cx + r * math.cos(a) + (sway if i % 2 else 0), cy - 18 + r * 1.02 * math.sin(a)))
    pts += [(cx + 150, cy + 70), (cx + 120, cy + 40), (cx - 120, cy + 40), (cx - 150, cy + 70)]
    pen.poly(pts, HAIR, LINE, 3)

    # ears
    for sx in (-1, 1):
        pen.ellipse(cx + sx * 118 - 15, cy - 5, cx + sx * 118 + 15, cy + 48, SKIN, LINE, 2.5)
    # face
    pen.poly([(cx - 116, cy + 10), (cx - 100, cy + 85), (cx - 45, cy + 128), (cx, cy + 138),
              (cx + 45, cy + 128), (cx + 100, cy + 85), (cx + 116, cy + 10)], SKIN, LINE, 3)
    pen.ellipse(cx - 118, cy - 130, cx + 118, cy + 100, SKIN)
    pen.arc_line(cx, cy - 15, 118, 115, 180, 360, LINE, 3)
    # neck shadow under chin
    pen.poly([(cx - 30, cy + 132), (cx + 30, cy + 132), (cx, cy + 141)], SKIN_SH)

    # blush
    if p["blush"] > 0.01:
        a = int(150 * p["blush"])
        blush = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bp = Pen(blush, 0, 0, K)
        for sx in (-1, 1):
            bp.ellipse(cx + sx * 68 - 26, cy + 52, cx + sx * 68 + 26, cy + 70, (255, 120, 140, a))
        img.alpha_composite(blush.filter(ImageFilter.GaussianBlur(5 * K)))

    # eyes
    lid, happy, brow = p["lid"], p["happy"], p["brow"]
    lx, ly = p["look"]
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
            ix, iy = ex + lx * 9, ey + ly * 9
            pen.ellipse(ix - 24, iy - 31, ix + 24, iy + 31, IRIS_D)
            pen.ellipse(ix - 19, iy - 12, ix + 19, iy + 28, IRIS)
            pen.ellipse(ix - 11, iy - 15, ix + 11, iy + 13, (12, 14, 34))
            pen.circle(ix - 9, iy - 13, 8, (255, 255, 255))
            pen.circle(ix + 9, iy + 12, 3.5, (255, 255, 255))
            if p["tear_a"] > 0.3:  # watery shine
                pen.ellipse(ix - 18, iy + 16, ix + 18, iy + 24, (190, 220, 255))
            # upper lid (skin) with sad droop toward the outer corner
            top = ey - ry - 4
            edge = top + lid * 2 * ry
            slant = 9 * max(brow, 0) * (1 if lid > 0.05 else 0.5)
            outer_y, inner_y = edge + slant, edge - slant * 0.4
            o_x, i_x = ex + sx * (rx + 6), ex - sx * (rx + 6)
            pen.poly([(o_x, top - 30), (i_x, top - 30), (i_x, inner_y), (o_x, outer_y)], SKIN)
            pen.line([(i_x + sx * 4, inner_y + 2), (ex, (inner_y + outer_y) / 2 - 2),
                      (o_x, outer_y + 1), (o_x + sx * 9, outer_y - 6)], LINE, 7)
            pen.arc_line(ex, ey + 2, rx - 3, ry - 2, 50, 130, LINE, 2.5)
        # brows
        by = cy - 48
        inner = (cx + sx * 22, by - 12 * brow + 4 * min(brow, 0) * -1)
        mid = (cx + sx * 52, by - 8 - 3 * brow)
        outer = (cx + sx * 84, by + 6 * brow - 4)
        p["_brows"] = p.get("_brows", []) + [(inner, mid, outer)]

    # nose
    pen.line([(cx + 2, cy + 52), (cx - 3, cy + 60)], SKIN_SH, 4)

    # mouth
    m = p["mouth"]
    mx, my = cx, cy + 90
    if m == "frown":
        pen.arc_line(mx, my + 12, 18, 9, 200, 340, LINE, 4)
    elif m == "flat":
        pen.line([(mx - 13, my + 2), (mx + 13, my + 2)], LINE, 4)
    elif m == "smile":
        pen.arc_line(mx, my - 6, 20, 10, 20, 160, LINE, 4)
    elif m == "smirk":
        pen.line([(mx - 16, my + 4), (mx + 4, my + 4), (mx + 20, my - 5)], LINE, 4)
    elif m == "hum":
        pen.ellipse(mx - 9, my - 6, mx + 9, my + 10, (120, 34, 50), LINE, 3)
    elif m == "grin":
        open_h = 26 + 6 * math.sin(t * 20) * p["laugh"]
        pen.poly([(mx - 30, my - 6)] + [
            (mx + 30 * math.cos(math.radians(a)), my - 6 + open_h * math.sin(math.radians(a)))
            for a in range(0, 181, 15)], (120, 34, 50), LINE, 3)
        pen.poly([(mx - 26, my - 4), (mx + 26, my - 4), (mx + 22, my + 3), (mx - 22, my + 3)],
                 (255, 255, 255))
        pen.ellipse(mx - 14, my + open_h - 18, mx + 14, my + open_h - 4, (240, 110, 120))

    # tear rolling down the cheek
    if p["tear_a"] > 0.01:
        a = int(235 * p["tear_a"])
        tx = cx - 70 - 6 * p["tear"]
        ty = cy + 40 + 80 * p["tear"]
        tear = Image.new("RGBA", img.size, (0, 0, 0, 0))
        tp = Pen(tear, 0, 0, K)
        tp.line([(cx - 68, cy + 42), (tx, ty)], (170, 210, 255, a // 2), 4)
        tp.poly([(tx, ty - 18), (tx - 9, ty), (tx + 9, ty)], (160, 205, 255, a))
        tp.circle(tx, ty + 2, 9, (160, 205, 255, a))
        tp.circle(tx - 3, ty - 1, 3, (255, 255, 255, a))
        img.alpha_composite(tear)

    # fringe
    fr = [(cx - 150, cy + 20), (cx - 138, cy - 70), (cx - 95, cy - 128), (cx - 30, cy - 150),
          (cx + 40, cy - 148), (cx + 100, cy - 125), (cx + 140, cy - 70), (cx + 150, cy + 20),
          (cx + 128, cy - 22), (cx + 110, cy - 60), (cx + 92, cy - 8), (cx + 70, cy - 70),
          (cx + 42, cy - 34 + sway), (cx + 22, cy - 82), (cx - 5, cy - 30 + sway),
          (cx - 25, cy - 86), (cx - 55, cy - 40 + sway), (cx - 72, cy - 84), (cx - 102, cy - 14),
          (cx - 116, cy - 64), (cx - 134, cy - 18)]
    pen.poly(fr, HAIR, LINE, 3)
    pen.poly([(cx - 90, cy - 112), (cx - 20, cy - 132), (cx + 60, cy - 128), (cx + 98, cy - 108),
              (cx + 60, cy - 114), (cx - 20, cy - 118)], HAIR_HI)
    for inner, mid, outer in p["_brows"]:
        pen.line([inner, mid, outer], HAIR, 8)

    # headphones: he's vibing to his own music
    hp, hp_d = (225, 60, 72), (110, 24, 34)
    pen.arc_line(cx, cy - 2, 136, 178, 192, 348, LINE, 24)
    pen.arc_line(cx, cy - 2, 136, 178, 192, 348, (40, 40, 52), 16)
    for sx in (-1, 1):
        ex = cx + sx * 132
        pen.ellipse(ex - 30, cy - 30, ex + 30, cy + 62, hp, LINE, 3)
        pen.ellipse(ex - 16, cy - 10, ex + 16, cy + 42, hp_d)
        pen.ellipse(ex - 22 + sx * 6, cy - 22, ex - 8 + sx * 6, cy - 2, (255, 160, 170))

    # crown
    c = p["crown"]
    if c > 0.01:
        drop = (1 - ease_out(c)) * -90
        a = int(255 * clamp(c * 1.6))
        crown = Image.new("RGBA", img.size, (0, 0, 0, 0))
        cp = Pen(crown, 0, 0, K)
        by = cy - 150 + drop
        pts = [(cx - 78, by + 40), (cx - 86, by - 30), (cx - 45, by + 5), (cx, by - 52),
               (cx + 45, by + 5), (cx + 86, by - 30), (cx + 78, by + 40)]
        cp.poly(pts, (255, 200, 60, a), (120, 70, 10, a), 3)
        cp.poly([(cx - 78, by + 22), (cx + 78, by + 22), (cx + 78, by + 40), (cx - 78, by + 40)],
                (230, 160, 40, a))
        for gx, col in ((-45, (230, 60, 80)), (0, (80, 170, 255)), (45, (90, 220, 140))):
            cp.circle(cx + gx, by + 31, 7, col + (a,))
        for gx, gy in ((-86, -30), (0, -52), (86, -30)):
            cp.circle(cx + gx, by + gy, 7, (255, 240, 170, a))
        glow = crown.filter(ImageFilter.GaussianBlur(10 * K))
        img.alpha_composite(glow)
        img.alpha_composite(crown)
    p.pop("_brows", None)
    return img


def draw_character(t):
    p = {k: track(v, t) for k, v in T.items()}
    p["mouth"] = step(MOUTH, t)
    slump, walk, swag = p["slump"], p["walk"], p["swag"]
    phase = walk_phase(t)
    air, squash = jump_at(t)
    hop = skip_at(t)
    # walking: sway side to side, bounce on every step (more swagger = more bounce)
    hx = 540 + math.sin(phase) * (6 + 16 * swag) * walk
    bob = (8 + 16 * swag) * walk * abs(math.sin(phase))
    hip_y = 1250 - bob - air - hop + squash
    p["tilt"] += math.sin(phase) * 4 * swag * walk
    breathe = math.sin(t * 2.2) * 3
    laugh = p["laugh"] * abs(math.sin(t * 11)) * 10
    nod = swag * 7 * (1 - abs(math.cos(phase)))  # head bobs to the beat
    sy = hip_y - 330 + slump * 34 + breathe + laugh * 0.5
    neck = (hx, sy - 36 + p["head_dy"] - laugh + nod)
    head_center = (neck[0], neck[1] - 120)

    rx0, ry0 = 120, 150
    cw, ch = 840, 1540
    img = Image.new("RGBA", (cw * K, ch * K), (0, 0, 0, 0))
    pen = Pen(img, rx0, ry0, K)

    # legs: front-view walk cycle (alternate knee lift), tucked during the jump
    tuck = clamp(air / 120)
    for s in (-1, 1):
        lift = max(0.0, math.sin(phase + (0 if s < 0 else math.pi))) * walk
        lift = max(lift, 0.75 * tuck)
        hipj = (hx + s * 50, hip_y)
        ground = GROUND - 12 - air - hop
        foot = (hx + s * (66 + 6 * lift), ground - lift * 62)
        knee = (hx + s * (62 + 16 * lift), (hipj[1] + foot[1]) / 2 - lift * 46 + squash * 0.5)
        pen.limb(hipj, knee, 76, PANTS)
        pen.limb(knee, foot, 64, PANTS)
        pen.ellipse(foot[0] - 48, foot[1] - 14, foot[0] + 48, foot[1] + 24, (236, 236, 242), LINE, 3)
        pen.line([(foot[0] - 44, foot[1] + 16), (foot[0] + 44, foot[1] + 16)], (150, 150, 165), 5)

    # torso (hoodie)
    pen.ellipse(hx - 88, sy - 40, hx + 88, sy + 32, HOOD_SH, LINE, 3)  # hood behind neck
    pen.poly([(hx - 26, sy - 50), (hx + 26, sy - 50), (hx + 26, sy + 10), (hx - 26, sy + 10)], SKIN_SH)
    body = [(hx - 116, sy + 6), (hx + 116, sy + 6), (hx + 100, hip_y + 18), (hx - 100, hip_y + 18)]
    pen.poly(body, HOOD, LINE, 3)
    for s in (-1, 1):
        pen.circle(hx + s * 98, sy + 34, 36, HOOD)
    pen.poly([(hx - 100, hip_y - 10), (hx + 100, hip_y - 10), (hx + 100, hip_y + 18),
              (hx - 100, hip_y + 18)], HOOD_SH, LINE, 2)
    pen.ellipse(hx - 70, hip_y - 110, hx + 70, hip_y - 40, None, HOOD_SH, 4)
    pen.poly([(hx - 40, sy + 2), (hx + 40, sy + 2), (hx, sy + 46)], HOOD_SH)
    for s in (-1, 1):
        pen.line([(hx + s * 22, sy + 20), (hx + s * 26, sy + 112)], (235, 235, 240), 4)
        pen.circle(hx + s * 26, sy + 116, 5, (235, 235, 240))

    # arms (behind the head when raised)
    for s, keys in ((-1, HAND_L), (1, HAND_R)):
        sh = (hx + s * 104, sy + 30)
        target = hand_pos(keys, t, (hx, hip_y), head_center, walk)
        elbow, hand = ik(sh, target, 150, 148, 1 if s < 0 else -1)
        pen.limb(sh, elbow, 54, HOOD)
        pen.limb(elbow, hand, 50, HOOD)
        pen.circle(*hand, 27, SKIN, LINE, 3)

    # head
    head = draw_head(t, p)
    head = head.rotate(p["tilt"], resample=Image.BICUBIC, center=(PIVOT[0] * K, PIVOT[1] * K))
    px = int((neck[0] - rx0) * K - PIVOT[0] * K)
    py = int((neck[1] - ry0) * K - PIVOT[1] * K)
    img.alpha_composite(head, (max(px, 0), max(py, 0)), (max(-px, 0), max(-py, 0)))

    # returned at full supersampled resolution so close-ups stay sharp
    return img, (rx0, ry0), head_center


# ======================================================================
# props & side characters
# ======================================================================
FONT_Q = ImageFont.truetype(F_SYM, 90)


def draw_ruler(d, cx, cy, ang, alpha, length=520):
    ca, sa = math.cos(ang), math.sin(ang)

    def r(x, y):
        return (cx + x * ca - y * sa, cy + x * sa + y * ca)

    hl, hh = length / 2, 26
    d.polygon([r(-hl, -hh), r(hl, -hh), r(hl, hh), r(-hl, hh)], fill=(232, 196, 110, alpha),
              outline=(110, 70, 20, alpha), width=4)
    for i in range(int(length // 20) + 1):
        x = -hl + i * 20
        L = 22 if i % 5 == 0 else 11
        d.line([r(x, -hh), r(x, -hh + L)], fill=(90, 55, 15, alpha), width=3)


def draw_shadow_people(t, layer):
    """Faceless judges walk beside him holding a ruler over his head, get confused when
    he laughs, drop it, and walk back into the distance (they shrink toward the horizon)."""
    if t > 9.4:
        return
    d = ImageDraw.Draw(layer)
    people = [(170, 0.78, 1555), (305, 0.85, 1580), (775, 0.85, 1580), (910, 0.78, 1555)]
    starts = [-180, -280, 1260, 1360]
    leave = smooth((t - 7.0) / 2.2)
    fade = 1 - smooth((t - 7.8) / 1.4)
    phase = walk_phase(t)
    for i, ((xf, sc0, base0), xs) in enumerate(zip(people, starts)):
        arrive = ease_out((t - 0.3 - i * 0.15) / 1.7)
        side = -1 if i < 2 else 1
        x = lerp(lerp(xs, xf, arrive), 540 + side * (50 + 25 * (i % 2)), leave)
        sc = lerp(sc0, 0.14, leave)
        base = lerp(base0, HOR + 70, leave)
        bob = abs(math.sin(phase + i)) * 10 * sc
        top = base - 980 * sc - bob
        a = int(225 * fade)
        col = (6, 6, 14, a)
        d.ellipse([x - 46 * sc, top, x + 46 * sc, top + 92 * sc], fill=col)
        d.polygon([(x - 80 * sc, top + 105 * sc), (x + 80 * sc, top + 105 * sc),
                   (x + 62 * sc, base), (x - 62 * sc, base)], fill=col)
        d.ellipse([x - 82 * sc, top + 92 * sc, x - 30 * sc, top + 150 * sc], fill=col)
        d.ellipse([x + 30 * sc, top + 92 * sc, x + 82 * sc, top + 150 * sc], fill=col)
        if leave < 0.25:
            ea = int(255 * fade)
            for ex in (-17, 17):
                d.ellipse([x + (ex - 9) * sc, top + 38 * sc, x + (ex + 9) * sc, top + 46 * sc],
                          fill=(255, 245, 230, ea))
        q = smooth((t - 6.0) / 0.3) * (1 - smooth((t - 7.2) / 0.3))
        if q > 0.01:
            ss = 0.6 + 0.4 * back_out((t - 6.0) / 0.4)
            f = FONT_Q.font_variant(size=int(90 * ss))
            d.text((x, top - 40), "?", font=f, fill=(255, 255, 255, int(255 * q)), anchor="ms")
        if i in (1, 2):
            hold = smooth((t - 1.9) / 0.5) * (1 - smooth((t - 6.2) / 0.3))
            if hold > 0.01:
                hand_y = lerp(top + 130 * sc, 525 + 18 * math.sin(t * 3), hold)
                hand_x = x + (70 if i == 1 else -70)
                d.line([(x + (40 if i == 1 else -40) * sc, top + 120 * sc), (hand_x, hand_y)],
                       fill=col, width=int(30 * sc))
    hold = smooth((t - 1.9) / 0.5)
    if hold > 0.01:
        if t < 6.3:
            draw_ruler(d, 540, 525 + 18 * math.sin(t * 3), 0.02 * math.sin(t * 2), int(255 * hold))
        else:
            fall = clamp((t - 6.3) / 1.0)
            a = int(255 * (1 - smooth((t - 6.9) / 0.6)))
            if a > 0:
                draw_ruler(d, 540 + 70 * fall, 525 + 1100 * fall ** 2, 1.1 * fall ** 1.5, a)


def draw_aura(t, layer):
    """Golden rays behind him when he stands as a prince."""
    a = smooth((t - 10.0) / 0.6) * (1 - smooth((t - 11.6) / 0.6))
    if a <= 0.01:
        return
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(rays)
    cx, cy = 540, 820
    for i in range(16):
        ang = t * 0.4 + i * math.tau / 16
        w = 0.07
        d.polygon([(cx, cy), (cx + 1400 * math.cos(ang - w), cy + 1400 * math.sin(ang - w)),
                   (cx + 1400 * math.cos(ang + w), cy + 1400 * math.sin(ang + w))],
                  fill=(255, 210, 110, int(70 * a)))
    d.ellipse([cx - 260, cy - 260, cx + 260, cy + 260], fill=(255, 220, 140, int(110 * a)))
    layer.alpha_composite(rays.filter(ImageFilter.GaussianBlur(18)))


def draw_bubbles(t, layer, head):
    """Empty dream bubbles that pop: he no longer dreams."""
    d = ImageDraw.Draw(layer)
    for start, side in ((12.2, 1), (12.85, -1)):
        lt = t - start
        if not (0 <= lt <= 1.1):
            continue
        grow = back_out(lt / 0.45)
        pop = smooth((lt - 0.75) / 0.25)
        a = int(235 * (1 - pop))
        s = grow * (1 + 0.35 * pop)
        bx, by = head[0] + side * 230, head[1] - 210
        for k, (fx, fy, r) in enumerate(((0.28, 0.85, 12), (0.55, 0.62, 20))):
            if lt > k * 0.12:
                x = lerp(head[0] + side * 110, bx, fx)
                y = lerp(head[1] - 40, by, fy)
                d.ellipse([x - r * s, y - r * s, x + r * s, y + r * s], fill=(245, 248, 255, a),
                          outline=(120, 140, 200, a), width=3)
        for ox, oy, r in ((0, 0, 90), (-70, 20, 62), (70, 18, 64), (-30, -45, 60), (40, -40, 62)):
            rr = r * s
            d.ellipse([bx + ox * s - rr, by + oy * s - rr, bx + ox * s + rr, by + oy * s + rr],
                      fill=(245, 248, 255, a))
        if pop > 0.05:
            for k in range(10):
                ang = k * math.tau / 10
                r0, r1 = 120 * s, 120 * s + 60 * pop
                d.line([(bx + r0 * math.cos(ang), by + r0 * math.sin(ang)),
                        (bx + r1 * math.cos(ang), by + r1 * math.sin(ang))],
                       fill=(255, 255, 255, int(200 * (1 - pop))), width=5)


MEMORIES = [(-330, -480, "heart"), (300, -560, "sun"), (380, -260, "two"), (-380, -170, "house"),
            (-60, -720, "star")]


def draw_memory_pic(d, x, y, kind, a, s=1.0):
    if kind == "heart":
        d.ellipse([x - 30 * s, y - 25 * s, x, y + 5 * s], fill=(230, 70, 90, a))
        d.ellipse([x, y - 25 * s, x + 30 * s, y + 5 * s], fill=(230, 70, 90, a))
        d.polygon([(x - 29 * s, y - 5 * s), (x + 29 * s, y - 5 * s), (x, y + 32 * s)], fill=(230, 70, 90, a))
    elif kind == "sun":
        d.rectangle([x - 45 * s, y + 10 * s, x + 45 * s, y + 40 * s], fill=(90, 170, 110, a))
        d.ellipse([x - 22 * s, y - 32 * s, x + 22 * s, y + 12 * s], fill=(255, 200, 70, a))
    elif kind == "two":
        for ox, col in ((-16, (90, 120, 200)), (16, (220, 110, 140))):
            d.ellipse([x + (ox - 11) * s, y - 32 * s, x + (ox + 11) * s, y - 10 * s], fill=col + (a,))
            d.polygon([(x + (ox - 16) * s, y + 30 * s), (x + (ox + 16) * s, y + 30 * s),
                       (x + ox * s, y - 8 * s)], fill=col + (a,))
    elif kind == "house":
        d.rectangle([x - 30 * s, y - 5 * s, x + 30 * s, y + 35 * s], fill=(210, 150, 100, a))
        d.polygon([(x - 40 * s, y - 2 * s), (x + 40 * s, y - 2 * s), (x, y - 38 * s)], fill=(170, 60, 60, a))
    else:
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            r = (36 if k % 2 == 0 else 15) * s
            pts.append((x + r * math.cos(ang), y + r * math.sin(ang)))
        d.polygon(pts, fill=(255, 220, 90, a))


def draw_memories(t, layer, hip):
    """Polaroid memories float around him, then dissolve into dust."""
    lt = t - 13.9
    if not (0 <= lt <= 2.4):
        return
    d = ImageDraw.Draw(layer)
    rnd = random.Random(9)
    for i, (dx, dy, kind) in enumerate(MEMORIES):
        appear = back_out((lt - i * 0.12) / 0.5)
        dissolve = smooth((lt - 1.1 - i * 0.12) / 0.7)
        if appear <= 0:
            continue
        x = hip[0] + dx * appear + math.sin(t * 1.4 + i) * 14
        y = hip[1] + dy * appear + math.cos(t * 1.2 + i) * 12 - 60 * dissolve
        a = int(240 * (1 - dissolve))
        ang = math.sin(i * 1.7) * 0.18
        if a > 2:
            w2, h2 = 72, 86
            ca, sa = math.cos(ang), math.sin(ang)
            corners = [(-w2, -h2), (w2, -h2), (w2, h2), (-w2, h2)]
            d.polygon([(x + cx_ * ca - cy_ * sa, y + cx_ * sa + cy_ * ca) for cx_, cy_ in corners],
                      fill=(250, 246, 236, a))
            inner = [(-58, -72), (58, -72), (58, 40), (-58, 40)]
            d.polygon([(x + cx_ * ca - cy_ * sa, y + cx_ * sa + cy_ * ca) for cx_, cy_ in inner],
                      fill=(70, 90, 140, a))
            draw_memory_pic(d, x, y - 16, kind, a)
        if dissolve > 0.02:
            for k in range(26):
                px = x + rnd.uniform(-75, 75) + rnd.uniform(-1, 1) * 120 * dissolve
                py = y + rnd.uniform(-90, 90) - rnd.uniform(40, 220) * dissolve
                r = rnd.uniform(2, 6)
                pa = int(220 * math.sin(math.pi * dissolve))
                d.ellipse([px - r, py - r, px + r, py + r], fill=(255, 225, 180, pa))


# ======================================================================
# environment (static layers, prerendered)
# ======================================================================
def make_stars():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = random.Random(3)
    for _ in range(200):
        x, y, s = r.uniform(0, W), r.uniform(0, HOR - 20), r.uniform(1, 3)
        d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 250, 235, int(r.uniform(90, 255))))
    return img


def make_moon(mx, my, mr, crescent=True):
    moon = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    md = ImageDraw.Draw(moon)
    md.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(255, 244, 218, 255))
    glow = moon.filter(ImageFilter.GaussianBlur(mr * 0.65))
    if crescent:
        md.ellipse([mx - mr + mr * 0.48, my - mr - mr * 0.22, mx + mr + mr * 0.48, my + mr - mr * 0.22],
                   fill=(0, 0, 0, 0))
    else:  # craters on a full moon
        for cx_, cy_, cr in ((-0.3, -0.2, 0.2), (0.25, 0.1, 0.14), (-0.05, 0.35, 0.1)):
            md.ellipse([mx + (cx_ - cr) * mr, my + (cy_ - cr) * mr, mx + (cx_ + cr) * mr,
                        my + (cy_ + cr) * mr], fill=(236, 222, 196, 255))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(glow)
    out.alpha_composite(moon)
    return out


STARS = make_stars()
MOON = make_moon(860, 360, 64)
BIG_MOON = make_moon(540, HOR - 290, 170, crescent=False)


# ----------------------------------------------------------------------
# perspective road scenes: the camera walks with him, the world comes toward us
# ----------------------------------------------------------------------
FOCAL, CAM_H, Z_NEAR, Z_FAR = 2285.0, 1.6, 2.2, 80.0


def proj(x, y, z):
    return (540 + FOCAL * x / z, HOR + FOCAL * (CAM_H - y) / z)


_dist_cache = {}


def distance_at(t):
    """Metres walked so far (integral of the speed track)."""
    key = round(t * FPS)
    if key not in _dist_cache:
        dt = 1 / FPS
        total = 0.0
        for i in range(key):
            total += track(T["speed"], i * dt) * dt
        _dist_cache[key] = total
    return _dist_cache[key]


def fog(col, z, fogc, a=255):
    f = clamp((z - 6) / 55) * 0.85
    return tuple(int(lerp(c, fc, f)) for c, fc in zip(col, fogc)) + (a,)


def repeat(dist, spacing, count, start=0.0):
    """Yield (z, index) of objects placed every `spacing` metres, far to near."""
    base = int(dist // spacing)
    off = dist % spacing
    for k in range(count, 0, -1):
        z = start + k * spacing - off
        if Z_NEAR < z < Z_FAR:
            yield z, base + k


def ground_quad(d, x0, x1, z0, z1, col):
    d.polygon([proj(x0, 0, z0), proj(x1, 0, z0), proj(x1, 0, z1), proj(x0, 0, z1)], fill=col)


def wall_quad(d, x, y0, y1, z0, z1, col):
    d.polygon([proj(x, y1, z0), proj(x, y1, z1), proj(x, y0, z1), proj(x, y0, z0)], fill=col)


def lamp(d, g, x, z, fogc, warm=(255, 210, 140), height=4.6):
    w = max(1, int(FOCAL * 0.13 / z))
    d.line([proj(x, 0, z), proj(x, height, z)], fill=fog((44, 46, 58), z, fogc), width=w)
    arm = -0.6 if x > 0 else 0.6
    d.line([proj(x, height, z), proj(x + arm, height, z)], fill=fog((44, 46, 58), z, fogc), width=w)
    hx, hy = proj(x + arm, height - 0.1, z)
    r = FOCAL * 0.16 / z
    d.ellipse([hx - r, hy - r * 0.6, hx + r, hy + r * 0.6], fill=warm + (255,))
    near = clamp((z - 3.0) / 4.0)
    gr = FOCAL * 0.7 / z
    g.ellipse([hx - gr, hy - gr, hx + gr, hy + gr], fill=warm + (int(140 * near * clamp(1.4 - z / 50)),))
    px, py = proj(x + arm, 0, z)  # light pool on the ground
    pr = FOCAL * 1.6 / z
    g.ellipse([px - pr, py - pr * 0.25, px + pr, py + pr * 0.25], fill=warm + (int(60 * near * clamp(1.4 - z / 50)),))


def draw_env(t, kind, sky_bot):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d, g = ImageDraw.Draw(img), ImageDraw.Draw(glow)
    dist = distance_at(t)
    fogc = tuple(int(c) for c in sky_bot)

    if kind in ("street", "golden"):
        golden = kind == "golden"
        if golden:  # setting sun right at the end of the road
            g.ellipse([540 - 330, HOR - 330, 540 + 330, HOR + 330], fill=(255, 190, 110, 200))
            d.ellipse([540 - 170, HOR - 170, 540 + 170, HOR + 170], fill=(255, 214, 140, 255))
        d.rectangle([0, HOR, W, H], fill=fog((30, 30, 40) if not golden else (70, 44, 40), 30, fogc))
        ground_quad(d, -3, 3, Z_FAR, Z_NEAR, (22, 22, 30, 255) if not golden else (60, 38, 36, 255))
        for sx in (-1, 1):
            ground_quad(d, sx * 3, sx * 5.5, Z_FAR, Z_NEAR, (44, 44, 56, 255) if not golden else (96, 64, 52, 255))
        for z, _ in repeat(dist, 5.0, 16):
            ground_quad(d, -0.09, 0.09, z, max(Z_NEAR, z - 2.0), fog((200, 200, 190), z, fogc))
        # buildings on both sides
        for z, idx in repeat(dist, 6.0, 13):
            r = random.Random(idx * 7 + 3)
            for sx in (-1, 1):
                h = r.uniform(6, 20)
                z0, z1 = z, max(Z_NEAR, z - 5.6)
                base_col = (18, 20, 34) if not golden else (64, 34, 38)
                wall_quad(d, sx * 5.5, 0, h, z0, z1, fog(base_col, z, fogc))
                # roof edge highlight
                d.line([proj(sx * 5.5, h, z0), proj(sx * 5.5, h, z1)], fill=fog((60, 64, 90), z, fogc), width=2)
                if 6.5 < z < 48:
                    for fy in np.arange(2.8, h - 1, 2.6):
                        for u in (0.2, 0.6):
                            if r.random() < (0.38 if not golden else 0.2):
                                wz0 = z0 - u * 5.6
                                wz1 = wz0 - 1.1
                                wall_quad(d, sx * 5.5, fy, fy + 1.3, wz0, max(Z_NEAR, wz1),
                                          fog((255, 204, 120), z, fogc, 230))
                    if r.random() < 0.5:  # shop sign at street level
                        col = r.choice([(80, 230, 255), (255, 90, 170), (255, 210, 90), (140, 255, 160)])
                        wall_quad(d, sx * 5.45, 2.4, 3.0, z0 - 1.0, max(Z_NEAR, z0 - 4.0), fog(col, z, fogc))
                        a_, b_ = proj(sx * 5.45, 2.7, z0 - 2.5), FOCAL * 1.4 / max(z0 - 2.5, 2.5)
                        g.ellipse([a_[0] - b_, a_[1] - b_ * 0.6, a_[0] + b_, a_[1] + b_ * 0.6],
                                  fill=col + (int(90 * clamp(1.3 - z / 45)),))
        for z, idx in repeat(dist, 12.0, 7, 4.0):
            for sx in (-1, 1):
                lamp(d, g, sx * 3.4, z, fogc, (255, 200, 120) if golden else (255, 214, 150))

    elif kind == "park":
        d.rectangle([0, HOR, W, H], fill=fog((14, 34, 26), 30, fogc))
        ground_quad(d, -1.6, 1.6, Z_FAR, Z_NEAR, (54, 50, 46, 255))
        for z, idx in repeat(dist, 1.6, 40):  # grass tufts
            r = random.Random(idx)
            for _ in range(2):
                gx = r.choice((-1, 1)) * r.uniform(2.0, 7.0)
                a_, b_ = proj(gx, 0, z), proj(gx, 0.35, z)
                d.line([a_, b_], fill=fog((40, 90, 60), z, fogc), width=max(1, int(FOCAL * 0.05 / z)))
        for z, idx in repeat(dist, 7.0, 11):
            r = random.Random(idx * 13)
            for sx in (-1, 1):
                tx = sx * r.uniform(3.2, 5.5)
                w = max(2, int(FOCAL * 0.32 / z))
                d.line([proj(tx, 0, z), proj(tx, 2.6, z)], fill=fog((50, 34, 26), z, fogc), width=w)
                cxp, cyp = proj(tx, 3.7, z)
                cr = FOCAL * 1.5 / z
                d.ellipse([cxp - cr, cyp - cr, cxp + cr, cyp + cr], fill=fog((18, 58, 40), z, fogc))
                d.ellipse([cxp - cr * 0.6, cyp - cr * 0.85, cxp + cr * 0.3, cyp - cr * 0.1],
                          fill=fog((34, 84, 56), z, fogc))
        for z, idx in repeat(dist, 14.0, 5, 6.0):
            lamp(d, g, (-1 if idx % 2 else 1) * 2.2, z, fogc, (210, 230, 255), 3.6)

    elif kind == "bridge":
        d.rectangle([0, HOR, W, H], fill=(36, 22, 60, 255))  # river
        rr = random.Random(2)
        for _ in range(70):  # shimmering reflections
            z = rr.uniform(4, 60)
            y = proj(0, 0, z)[1]
            x = rr.uniform(-12, 12)
            sx_, _ = proj(x, 0, z)
            w = FOCAL * rr.uniform(0.6, 2.0) / z
            a = int(120 * (0.5 + 0.5 * math.sin(t * 4 + rr.uniform(0, 6))))
            d.line([(sx_ - w, y), (sx_ + w, y)], fill=(255, 190, 220, a), width=2)
        # distant skyline across the river
        sx_ = 0
        while sx_ < W:
            bw, bh = rr.randint(20, 60), rr.randint(15, 90)
            d.rectangle([sx_, HOR - bh, sx_ + bw, HOR], fill=fog((30, 20, 50), 70, fogc))
            sx_ += bw + rr.randint(0, 8)
        ground_quad(d, -3.2, 3.2, Z_FAR, Z_NEAR, (56, 48, 66, 255))
        for z, _ in repeat(dist, 5.0, 16):
            ground_quad(d, -0.08, 0.08, z, max(Z_NEAR, z - 1.6), fog((210, 200, 220), z, fogc))
        for sx in (-1, 1):
            wall_quad(d, sx * 3.2, 0.95, 1.1, Z_FAR, Z_NEAR, (110, 96, 130, 255))
            wall_quad(d, sx * 3.2, 0.0, 0.12, Z_FAR, Z_NEAR, (80, 70, 96, 255))
            for z, _ in repeat(dist, 2.0, 38):
                d.line([proj(sx * 3.2, 0, z), proj(sx * 3.2, 1.0, z)], fill=fog((90, 80, 110), z, fogc),
                       width=max(1, int(FOCAL * 0.06 / z)))
        for z, _ in repeat(dist, 10.0, 8, 3.0):
            for sx in (-1, 1):
                lamp(d, g, sx * 3.25, z, fogc, (255, 200, 230), 4.2)

    else:  # moonroad: open fields, the road runs straight at a huge moon
        img.alpha_composite(BIG_MOON)
        d.rectangle([0, HOR, W, H], fill=fog((18, 26, 34), 30, fogc))
        for z, idx in repeat(dist, 1.4, 45):
            r = random.Random(idx * 3)
            for _ in range(3):
                gx = r.choice((-1, 1)) * r.uniform(2.6, 14.0)
                a_, b_ = proj(gx, 0, z), proj(gx + 0.05, 0.3, z)
                d.line([a_, b_], fill=fog((44, 70, 70), z, fogc), width=max(1, int(FOCAL * 0.04 / z)))
        ground_quad(d, -2.2, 2.2, Z_FAR, Z_NEAR, (36, 36, 46, 255))
        for z, _ in repeat(dist, 5.0, 16):
            ground_quad(d, -0.08, 0.08, z, max(Z_NEAR, z - 2.0), fog((220, 220, 200), z, fogc))
        for z, _ in repeat(dist, 4.0, 19):
            for sx in (-1, 1):
                d.line([proj(sx * 3.0, 0, z), proj(sx * 3.0, 1.0, z)], fill=fog((70, 60, 50), z, fogc),
                       width=max(1, int(FOCAL * 0.08 / z)))
        for sx in (-1, 1):
            wall_quad(d, sx * 3.0, 0.75, 0.82, Z_FAR, Z_NEAR, (80, 70, 58, 255))
        g.ellipse([540 - 420, HOR - 40, 540 + 420, HOR + 60], fill=(200, 220, 255, 50))

    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(26)))
    return img


yy, xx = np.mgrid[0:H, 0:W]
_d = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H * 0.5) / (H * 0.6)) ** 2)
VIGNETTE = np.clip(1.12 - _d ** 2 * 0.8, 0.28, 1.0)[:, :, None].astype(np.float32)
GRAD_Y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]

rnd_fx = random.Random(21)
RAIN = [(rnd_fx.uniform(-200, W + 200), rnd_fx.uniform(0, H), rnd_fx.uniform(900, 1500)) for _ in range(170)]
DUST = [(rnd_fx.uniform(0, W), rnd_fx.uniform(0, H), rnd_fx.uniform(2, 6), rnd_fx.uniform(15, 50),
         rnd_fx.uniform(0, 6.28)) for _ in range(50)]

CAM_C = (540, 1100)


def cam_coeffs(depth, cam):
    """Affine coefficients mapping screen -> world for a layer at this depth."""
    z, px, py, rot = cam
    zd = 1 + (z - 1) * depth
    cr, sr = math.cos(math.radians(rot)) / zd, math.sin(math.radians(rot)) / zd
    a, b, d, e = cr, sr, -sr, cr
    c = CAM_C[0] + px * depth - a * CAM_C[0] - b * CAM_C[1]
    f = CAM_C[1] + py * depth - d * CAM_C[0] - e * CAM_C[1]
    return a, b, c, d, e, f


def cam_transform(img, depth, cam, origin=(0, 0), scale=1):
    """Render a layer through the camera. `origin`/`scale` place a supersampled sprite in world space."""
    a, b, c, d, e, f = cam_coeffs(depth, cam)
    coeffs = (a * scale, b * scale, (c - origin[0]) * scale,
              d * scale, e * scale, (f - origin[1]) * scale)
    return img.transform((W, H), Image.AFFINE, coeffs, resample=Image.BILINEAR)


def world_to_screen(cam, depth=1.0):
    z, px, py, rot = cam
    zd = 1 + (z - 1) * depth
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def m(x, y):
        dx, dy = x - CAM_C[0] - px * depth, y - CAM_C[1] - py * depth
        return (CAM_C[0] + zd * (cr * dx - sr * dy), CAM_C[1] + zd * (sr * dx + cr * dy))
    return m, zd


# ======================================================================
# signs: little graphics that pop up on key words of the lyrics
# (drawn after the camera so they stay crisp in close-ups)
# ======================================================================
def pop(t, t0, t1, fade=0.3):
    """Scale and alpha for a sign living from t0 to t1."""
    if not (t0 <= t <= t1):
        return 0, 0
    return back_out((t - t0) / 0.35), clamp((t - t0) / 0.15) * (1 - smooth((t - (t1 - fade)) / fade))


def heart_pts(x, y, s, half=0):
    """Heart outline; half=-1/1 returns the left/right half."""
    pts = []
    for i in range(41):
        a = math.pi * i / 20 - math.pi
        hx = 16 * math.sin(a) ** 3
        hy = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        if half == 0 or (half < 0 and hx <= 0.01) or (half > 0 and hx >= -0.01):
            pts.append((x + hx * s, y + hy * s))
    if half:
        crack = [(0, -5), (-3, -1), (3, 3), (-2, 7), (0, 12)]
        pts += [(x + cx * s, y + cy * s) for cx, cy in (crack if half < 0 else crack[::-1])]
    return pts


def draw_signs(t, layer, cam, head):
    d = ImageDraw.Draw(layer)
    m, zd = world_to_screen(cam)

    # "दर्द": a heart appears by his chest, cracks and breaks apart
    s, a = pop(t, 3.55, 4.85)
    if a > 0:
        hx, hy = m(700, 1060)
        size = 4.2 * zd * s
        crack = smooth((t - 4.1) / 0.2)
        apart = smooth((t - 4.3) / 0.5)
        al = int(255 * a)
        if crack < 1:
            d.polygon(heart_pts(hx, hy, size), fill=(235, 50, 80, al))
            d.ellipse([hx - 7 * size, hy - 5 * size, hx - 3 * size, hy - 1 * size], fill=(255, 170, 185, al))
            if crack > 0:
                pts = [(hx, hy - 5 * size), (hx - 3 * size, hy - size), (hx + 3 * size, hy + 3 * size),
                       (hx - 2 * size, hy + 7 * size)]
                d.line(pts, fill=(40, 10, 20, al), width=max(2, int(size * 1.1)))
        else:
            for side in (-1, 1):
                ox = side * 9 * size * apart
                oy = 14 * size * apart ** 2
                pts = heart_pts(hx, hy, size, side)
                ang = side * 0.5 * apart
                ca, sa = math.cos(ang), math.sin(ang)
                pts = [(hx + ox + (px_ - hx) * ca - (py_ - hy) * sa, hy + oy + (px_ - hx) * sa + (py_ - hy) * ca)
                       for px_, py_ in pts]
                d.polygon(pts, fill=(200, 40, 70, int(al * (1 - apart * 0.6))))

    # "देख": an eye opens beside him
    s, a = pop(t, 4.95, 5.95)
    if a > 0:
        ex, ey = 250, 620  # fixed on screen: this beat is an extreme close-up
        w = 120 * s
        open_ = smooth((t - 5.05) / 0.25) * (1 - 0.9 * math.exp(-((t - 5.6) / 0.05) ** 2))
        hgt = w * 0.55 * open_
        al = int(255 * a)
        pts_top = [(ex + w * math.cos(math.pi * i / 16), ey - hgt * math.sin(math.pi * i / 16)) for i in range(17)]
        pts_bot = [(ex - w * math.cos(math.pi * i / 16), ey + hgt * math.sin(math.pi * i / 16)) for i in range(17)]
        d.polygon(pts_top + pts_bot, fill=(255, 255, 255, al), outline=(20, 20, 30, al), width=max(2, int(w / 14)))
        if open_ > 0.3:
            r = w * 0.42
            d.ellipse([ex - r, ey - min(r, hgt), ex + r, ey + min(r, hgt)], fill=(70, 120, 220, al))
            r2 = r * 0.5
            d.ellipse([ex - r2, ey - min(r2, hgt), ex + r2, ey + min(r2, hgt)], fill=(10, 12, 30, al))
            d.ellipse([ex - r * 0.6, ey - r * 0.6, ex - r * 0.25, ey - r * 0.25], fill=(255, 255, 255, al))
        for k in range(5):  # lashes
            ang = math.pi * (0.2 + 0.15 * k)
            x0, y0 = ex + w * math.cos(ang) * 1.0, ey - hgt * math.sin(ang) - 2
            d.line([(x0, y0), (x0 + w * 0.25 * math.cos(ang), y0 - w * 0.25 * math.sin(ang))],
                   fill=(20, 20, 30, al), width=max(2, int(w / 16)))

    # "हँसता": anime laugh marks around his head
    s, a = pop(t, 5.8, 7.5)
    if a > 0:
        al = int(255 * a)
        for side in (-1, 1):
            for k in range(3):
                ang = math.radians(-35 + k * 30)
                wig = 1 + 0.1 * math.sin(t * 25 + k)
                r0, r1 = 175 * wig, (175 + 55 * s) * wig
                x0 = head[0] + side * r0 * math.cos(ang)
                y0 = head[1] + r0 * math.sin(ang) - 20
                x1 = head[0] + side * r1 * math.cos(ang)
                y1 = head[1] + r1 * math.sin(ang) - 20
                d.line([m(x0, y0), m(x1, y1)], fill=(255, 225, 120, al), width=max(3, int(5 * zd)))

    # "लौट गए": footprints lead back down the road, where the judges are going
    if 7.4 <= t <= 9.3:
        for side in (-1, 1):
            for k in range(9):
                if t < 7.5 + k * 0.12:
                    continue
                fa = int(220 * (1 - smooth((t - 8.8) / 0.5)))
                z = 5.5 + k * 2.2
                fx_, fy_ = proj(side * (0.9 + 0.25 * (k % 2)), 0, z)
                sx, sy = m(fx_, fy_)
                r = FOCAL * 0.11 / z * zd
                d.ellipse([sx - r * 0.7, sy - r * 1.3, sx + r * 0.7, sy + r * 1.3], fill=(220, 225, 255, fa))
                for tt in (-1, 0, 1):
                    d.ellipse([sx + tt * r * 0.55 - r * 0.28, sy - r * 1.9 - r * 0.28,
                               sx + tt * r * 0.55 + r * 0.28, sy - r * 1.9 + r * 0.28], fill=(220, 225, 255, fa))

    # masti: music notes float out of his headphones while he vibes
    for t0, t1 in ((6.7, 9.5), (11.1, 13.9), (14.2, 16.1), (16.4, 18.6)):
        if not (t0 <= t <= t1):
            continue
        for k in range(6):
            born = t0 + k * 0.45
            age = (t - born) % 2.7
            if t - born < 0:
                continue
            side = 1 if k % 2 else -1
            nx = head[0] + side * (150 + age * 60) + math.sin(age * 4 + k) * 20
            ny = head[1] - 10 - age * 150
            sx, sy = m(nx, ny)
            r = 16 * zd * (0.8 + 0.25 * (k % 3))
            al = int(255 * clamp(age / 0.2) * (1 - smooth((age - 1.8) / 0.8)) * (1 - smooth((t - (t1 - 0.3)) / 0.3)))
            if al <= 0:
                continue
            col = ((255, 225, 120), (150, 220, 255), (255, 150, 200))[k % 3] + (al,)
            d.ellipse([sx - r * 1.2, sy - r * 0.85, sx + r * 1.2, sy + r * 0.85], fill=col)
            stem = max(2, int(r * 0.35))
            d.line([(sx + r * 1.0, sy), (sx + r * 1.0, sy - r * 3.4)], fill=col, width=stem)
            if k % 2:
                d.line([(sx + r * 1.0, sy - r * 3.4), (sx + r * 2.2, sy - r * 2.4)], fill=col, width=stem)
            else:  # beamed pair
                d.ellipse([sx + r * 1.8, sy - r * 1.1, sx + r * 4.2, sy + r * 0.6], fill=col)
                d.line([(sx + r * 4.0, sy - r * 0.3), (sx + r * 4.0, sy - r * 3.7)], fill=col, width=stem)
                d.line([(sx + r * 1.0, sy - r * 3.4), (sx + r * 4.0, sy - r * 3.7)], fill=col, width=stem * 2)

    # "शहजादे": sparkles around the crown
    if 10.7 <= t <= 11.8:
        rr = random.Random(4)
        for k in range(9):
            ph = rr.uniform(0, 6.28)
            tw = max(0.0, math.sin(t * 6 + ph))
            ang = rr.uniform(0, math.tau)
            dist = rr.uniform(150, 260)
            sx, sy = m(head[0] + dist * math.cos(ang), head[1] - 130 + dist * 0.8 * math.sin(ang))
            r = (10 + 14 * tw) * zd * 0.6
            al = int(255 * tw * (1 - smooth((t - 11.5) / 0.3)))
            d.polygon([(sx, sy - r * 2), (sx + r * 0.4, sy - r * 0.4), (sx + r * 2, sy), (sx + r * 0.4, sy + r * 0.4),
                       (sx, sy + r * 2), (sx - r * 0.4, sy + r * 0.4), (sx - r * 2, sy), (sx - r * 0.4, sy - r * 0.4)],
                      fill=(255, 240, 170, al))

    # "नहीं": a red cross strikes through the second dream bubble
    s, a = pop(t, 13.25, 13.75, fade=0.15)
    if a > 0:
        bx, by = m(head[0] - 230, head[1] - 210)
        r = 80 * zd * s
        al = int(255 * a)
        wdt = max(4, int(16 * zd))
        d.line([(bx - r, by - r), (bx + r, by + r)], fill=(235, 50, 60, al), width=wdt)
        d.line([(bx + r, by - r), (bx - r, by + r)], fill=(235, 50, 60, al), width=wdt)

    # "बातें": quiet speech bubbles drift up from him
    for k, t0 in enumerate((17.0, 17.45, 17.9)):
        s, a = pop(t, t0, 18.75, fade=0.5)
        if a <= 0:
            continue
        rise = (t - t0) * 40
        bx, by = m(head[0] + 200 + k * 40, head[1] - 170 - k * 110 - rise)
        w, h = 70 * zd * s * 0.75, 44 * zd * s * 0.75
        al = int(235 * a)
        d.rounded_rectangle([bx - w, by - h, bx + w, by + h], radius=int(h), fill=(250, 250, 255, al))
        d.polygon([(bx - w * 0.5, by + h * 0.6), (bx - w * 0.9, by + h * 1.6), (bx - w * 0.1, by + h * 0.8)],
                  fill=(250, 250, 255, al))
        for j in (-1, 0, 1):
            on = (t * 3 + j * 0.33) % 1 < 0.6
            r = h * 0.18
            d.ellipse([bx + j * w * 0.45 - r, by - r, bx + j * w * 0.45 + r, by + r],
                      fill=(60, 70, 110, al if on else al // 3))


def fx_layer(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rain = 1 - smooth((t - 5.2) / 1.0)
    if rain > 0.01:
        for x, y, sp in RAIN:
            yy_ = (y + t * sp) % (H + 200) - 100
            xx_ = x - (yy_ * 0.12)
            d.line([(xx_, yy_), (xx_ - 8, yy_ + 46)], fill=(170, 195, 240, int(120 * rain)), width=2)
    warm = smooth((t - 9.8) / 0.6) * (1 - smooth((t - 11.7) / 0.5))
    fire = smooth((t - 16.3) / 0.8)
    for x, y, s, sp, ph in DUST:
        py_ = (y - t * sp) % H
        px_ = x + 24 * math.sin(t * 0.7 + ph)
        if fire > 0.01:
            a = int(fire * (120 + 120 * math.sin(t * 3 + ph)))
            d.ellipse([px_ - s, py_ - s, px_ + s, py_ + s], fill=(255, 230, 140, max(a, 0)))
        elif warm > 0.01:
            d.ellipse([px_ - s, py_ - s, px_ + s, py_ + s], fill=(255, 210, 120, int(170 * warm)))
        elif rain < 0.5:
            d.ellipse([px_ - s, py_ - s, px_ + s, py_ + s], fill=(200, 215, 255, 70))
    return layer.filter(ImageFilter.GaussianBlur(1.6))


# ======================================================================
# lyrics, music-video style: lower third, words drift up out of a blur
# ======================================================================
F_DEV = "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf"
FONT_LYR = ImageFont.truetype(F_DEV, 78, layout_engine=ImageFont.Layout.RAQM)
EMPHASIS = {"पैमाना": (255, 214, 140), "दर्द": (255, 120, 130), "हँसता": (255, 215, 120),
            "शहजादे": (255, 200, 80), "ख्वाब": (160, 205, 255), "भूल": (215, 185, 255),
            "बातें": (255, 236, 190)}
LYRIC_Y = 1430   # centre of the lyric block; clear of the face and the app's caption area
_word_cache = {}


def word_sprite(word):
    """(sharp sprite, blurred sprite, advance, pad); all share one baseline."""
    if word in _word_cache:
        return _word_cache[word]
    col = EMPHASIS.get(word, (255, 255, 255))
    glow_col = col if word in EMPHASIS else (150, 180, 255)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    x0, _, x1, _ = probe.textbbox((0, 0), word, font=FONT_LYR)
    pad = 40
    ascent, descent = FONT_LYR.getmetrics()
    img = Image.new("RGBA", (x1 - x0 + 2 * pad, ascent + descent + 2 * pad), (0, 0, 0, 0))
    org = (pad - x0, pad)
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).text(org, word, font=FONT_LYR, fill=glow_col + (150,))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(14)))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((org[0] + 2, org[1] + 4), word, font=FONT_LYR, fill=(0, 0, 0, 235))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(img).text(org, word, font=FONT_LYR, fill=col + (255,))
    blurred = img.filter(ImageFilter.GaussianBlur(9))
    adv = probe.textlength(word, font=FONT_LYR)
    _word_cache[word] = (img, blurred, adv, pad)
    return _word_cache[word]


def layout_line(text):
    words = text.split()
    space = FONT_LYR.getlength(" ")
    rows, cur, cur_w = [], [], 0
    for w in words:
        adv = word_sprite(w)[2]
        if cur and cur_w + space + adv > 900:
            rows.append(cur)
            cur, cur_w = [w], adv
        else:
            cur_w += (space if cur else 0) + adv
            cur.append(w)
    rows.append(cur)
    placed = []
    row_h = 112
    top = LYRIC_Y - (len(rows) - 1) * row_h / 2
    for r, row in enumerate(rows):
        widths = [word_sprite(w)[2] for w in row]
        total = sum(widths) + space * (len(row) - 1)
        x = (W - total) / 2
        for w, adv in zip(row, widths):
            placed.append((w, x + adv / 2, top + r * row_h))
            x += adv + space
    return placed


LAYOUTS = [layout_line(text) for _, _, text in LINES]
_band = np.clip((np.linspace(0, 1, H, dtype=np.float32) - 0.62) / 0.2, 0, 1)
LYRIC_BAND = (1 - 0.45 * _band * (1 - np.clip((np.linspace(0, 1, H) - 0.86) / 0.14, 0, 1)))[:, None, None]


def with_alpha(img, a):
    if a >= 0.999:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return out


def draw_lyrics(frame, t):
    for (start, end, _), placed in zip(LINES, LAYOUTS):
        if not (start - 0.1 <= t < end):
            continue
        n = len(placed)
        exit_ = smooth((t - (end - 0.3)) / 0.3)
        for i, (w, cx, cy) in enumerate(placed):
            wt = start + (end - start) * 0.8 * i / n
            p = (t - wt) / 0.5
            if p <= 0:
                continue
            sharp, blurred, adv, pad = word_sprite(w)
            a = clamp(p * 1.8) * (1 - exit_)
            if a <= 0.01:
                continue
            focus = ease_out(p)  # blur -> sharp
            y = cy - (1 - focus) * 36 - exit_ * 30 - pad - FONT_LYR.getmetrics()[0] / 2
            x = cx - sharp.width / 2
            # emphasised words get a gentle pulse when they land
            if w in EMPHASIS and 0 < p < 1.6:
                sc = 1 + 0.12 * math.sin(math.pi * clamp(p / 1.6))
                nw, nh = int(sharp.width * sc), int(sharp.height * sc)
                sharp_s, blur_s = sharp.resize((nw, nh), Image.BILINEAR), blurred.resize((nw, nh), Image.BILINEAR)
                x, y = cx - nw / 2, y - (nh - sharp.height) / 2
            else:
                sharp_s, blur_s = sharp, blurred
            pos = (int(x), int(y))
            if focus < 0.999:
                frame.alpha_composite(with_alpha(blur_s, a * (1 - focus)), pos)
            frame.alpha_composite(with_alpha(sharp_s, a * focus), pos)


# ======================================================================
# frame assembly
# ======================================================================
def motion_blur(arr, amount):
    """Horizontal smear used for whip-pans."""
    if amount <= 0.02:
        return arr
    acc = np.zeros_like(arr)
    n = 9
    span = int(140 * amount)
    for k in range(n):
        acc += np.roll(arr, int((k / (n - 1) - 0.5) * span), axis=1)
    return acc / n


def render_frame(t, rng):
    top, bot, tint = light_at(t)
    cam = camera_at(t)

    sky = np.array(top, np.float32) * (1 - GRAD_Y) + np.array(bot, np.float32) * GRAD_Y
    frame = Image.fromarray(np.broadcast_to(sky, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    kind = location_at(t)
    star_a = {"street": 0.35 + 0.65 * smooth((t - 5.5) / 1.5), "golden": 0.12}.get(kind, 1.0)
    stars = STARS if star_a > 0.98 else Image.fromarray(
        (np.asarray(STARS) * np.array([1, 1, 1, star_a], np.float32)).astype(np.uint8))
    frame.alpha_composite(cam_transform(stars, 0.15, cam))
    if kind in ("street", "park", "bridge"):
        frame.alpha_composite(cam_transform(MOON, 0.15, cam))
    frame.alpha_composite(cam_transform(draw_env(t, kind, bot), 0.9, cam))

    # behind him: golden aura and the shadow people
    back = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_aura(t, back)
    air, _ = jump_at(t)
    sh = 1 - clamp(air / 320)  # contact shadow under his feet
    ImageDraw.Draw(back).ellipse([540 - 130 * sh, GROUND - 12, 540 + 130 * sh, GROUND + 26],
                                 fill=(0, 0, 0, int(110 * sh)))
    if t < 9.4:
        shadows = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_shadow_people(t, shadows)
        back.alpha_composite(shadows.filter(ImageFilter.GaussianBlur(1.2)))
    frame.alpha_composite(cam_transform(back, 1.0, cam))

    # the character, sampled straight from the supersampled render
    char_img, origin, head = draw_character(t)
    frame.alpha_composite(cam_transform(char_img, 1.0, cam, origin, K))

    # in front: dream bubbles, memories, weather
    front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hip = (540, 1250)
    draw_bubbles(t, front, head)
    draw_memories(t, front, hip)
    frame.alpha_composite(cam_transform(front.filter(ImageFilter.GaussianBlur(0.7)), 1.0, cam))
    frame.alpha_composite(cam_transform(fx_layer(t), 1.1, cam))

    # word signs (crisp, post-camera)
    signs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_signs(t, signs, cam, head)
    frame.alpha_composite(signs.filter(ImageFilter.GaussianBlur(0.6)))

    # colour grade, transitions, vignette, grain
    blur, bright, flash = transition_fx(t)
    arr = np.asarray(frame.convert("RGB")).astype(np.float32) * np.array(tint, np.float32)
    arr = motion_blur(arr, blur)
    if flash > 0.01:
        arr = arr + (255 - arr) * flash * np.array([1.0, 0.88, 0.6], np.float32)
    arr *= VIGNETTE * bright * LYRIC_BAND
    arr += rng.normal(0, 3, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    draw_lyrics(out, t)
    out = out.convert("RGB")
    fade = min(clamp(t / 0.4), clamp((DURATION - t) / 0.7))
    if fade < 1:
        out = Image.blend(Image.new("RGB", (W, H)), out, fade)
    return out


def main():
    rng = np.random.default_rng(1)
    if "--frames" in sys.argv:
        idx = [int(v) for v in sys.argv[sys.argv.index("--frames") + 1].split(",")]
        for i in idx:
            render_frame(i / FPS, rng).save(os.path.join(HERE, f"_preview_{i:04d}.png"))
        return
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", SILENT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(math.ceil(DURATION * FPS))
    for i in range(n):
        proc.stdin.write(render_frame(i / FPS, rng).tobytes())
        if i % 60 == 0:
            print(f"frame {i}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", SILENT, "-i", AUDIO,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-af", f"afade=t=out:st={DURATION - 0.6:.2f}:d=0.6", "-shortest",
                    "-movflags", "+faststart", OUT], check=True)
    os.remove(SILENT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
