"""19 November: a sad boy alone in a dark room, crying while the user's clip plays on an old CRT TV.

One frame holds both: the CRT TV (left) playing raw-videos/VID_20261118_181136_080.mp4 with scanlines and
glow, its light spilling onto the room and onto him; the boy (right) on the floor wrapped in a blanket,
watching, tears running from both eyes, sobbing, wiping his eyes, head dropping. Rain on the window, a
"19 NOV" calendar. The clip's own audio is kept.

Built on the character rig of reel/make_story_reel.py (via the 19 Nov reel engine).
Usage: python3 make_tvroom.py [--frames 30,300,...]
"""
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
DURATION = 39.86
HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "..", "..", "raw-videos", "VID_20261118_181136_080.mp4")
OUT = os.path.join(HERE, "tvroom_19nov.mp4")
SILENT = os.path.join(HERE, "_tvroom_silent.mp4")
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
    (0.20, 3.30, "Ek normal si subah..."),
    (3.40, 5.75, "Phone: 'Aaj ke din, 3 saal pehle'"),
    (5.90, 8.40, "Aaine mein dekha... aur"),
    (8.75, 12.35, "19 Nov 2023, Ahmedabad. 1 lakh log, ek sapna"),
    (12.45, 15.20, "Bas ek jeet aur..."),
    (15.35, 20.10, "Australia ne final jeet liya. Stadium chup"),
    (20.30, 25.00, "3 saal baad bhi, aaina wahi yaad dikhata hai"),
    (25.20, 27.20, "Remember 19 November?"),
]

BEAT = 0.418  # the track runs at ~143.5 bpm; hops land on the beat

FB = (8.5, 20.2)   # flashback window (the 2023 final)

T = {
    "stand":   [(0, 1)],
    # sitting up in bed: the whole body starts low (legs hidden under the blanket)
    "sink":    [(0, 330), (0.9, 330), (1.9, 150), (5.75, 150), (5.83, 0)],
    "slump":   [(0, 0.8), (1.0, 0.8), (1.9, 0.2), (3.3, 0.2), (3.4, 0.4), (5.8, 0.4), (5.83, 0.1),
                (8.5, 0.1), (8.51, 0), (15.3, 0), (15.9, 0.9), (20.1, 0.9), (20.2, 0.5), (27.3, 0.6)],
    "head_dy": [(0, 30), (1.0, 30), (1.9, 0), (3.4, 0), (3.8, 22), (5.8, 22), (5.83, 0),
                (15.3, 0), (16.0, 24), (20.1, 24), (20.2, 8), (27.3, 10)],
    "tilt":    [(0, 14), (0.9, 14), (1.9, -3), (2.9, 4), (3.4, 0), (8.5, 0), (12.4, 0), (12.8, -4),
                (15.2, -4), (15.6, 0), (20.2, 0), (21.0, -5), (24.0, -5), (24.6, 2)],
    "shake":   [(0, 0)],
    "look":    [(0, (0, 0)), (3.4, (0, 0)), (3.7, (0.1, 0.8)), (5.8, (0.1, 0.8)), (5.83, (0, 0)),
                (12.4, (0, 0)), (12.7, (0, -0.55)), (15.2, (0, -0.55)), (15.6, (0, 0.7)),
                (20.1, (0, 0.7)), (20.2, (0, 0)), (27.3, (0, 0.15))],
    "lid":     [(0, 1.0), (0.95, 1.0), (1.3, 0.55), (1.9, 0.6), (2.0, 1.0), (2.8, 1.0), (3.0, 0.4),
                (4.3, 0.4), (4.5, 0.0), (5.8, 0.0), (5.83, 0.2), (8.4, 0.05), (8.5, 0.1), (12.4, 0.1),
                (12.7, 0.0), (15.2, 0.0), (15.7, 0.5), (20.1, 0.5), (20.3, 0.35), (27.3, 0.35)],
    "happy":   [(0, 0), (8.7, 0), (8.85, 1), (12.2, 1), (12.4, 0)],
    "brow":    [(0, 0.2), (3.4, 0.2), (4.3, 0.2), (4.5, -0.4), (5.8, -0.4), (5.83, 0.5), (8.5, 0.7),
                (8.51, -0.2), (12.4, -0.2), (12.8, 0.7), (15.2, 0.7), (15.6, 1.0), (27.3, 1.0)],
    "tear":    [(0, 0), (16.2, 0), (19.8, 1), (19.81, 0), (21.0, 0), (24.8, 1), (24.81, 0), (25.4, 0),
                (27.2, 0.8)],
    "tear_a":  [(0, 0), (16.0, 0), (16.4, 1), (19.9, 1), (20.15, 0), (20.9, 0), (21.2, 1), (27.3, 1)],
    "blush":   [(0, 0), (8.7, 0), (8.9, 0.45), (12.3, 0.45), (12.5, 0)],
    "laugh":   [(0, 0), (8.8, 0), (8.95, 1), (12.1, 1), (12.4, 0)],
    "crown":   [(0, 0)],
    "walk":    [(0, 0)],
    "swag":    [(0, 0)],
    "speed":   [(0, 0)],
    "flag_ang": [(0, 0.15), (8.7, 0.15), (8.9, 0.0), (12.3, 0.0), (12.6, 1.0), (15.3, 1.0)],
    "desat":   [(0, 0), (8.5, 0), (8.51, 0.22), (15.25, 0.22), (15.6, 0.8), (20.15, 0.8), (20.2, 0.15),
                (25.1, 0.15), (25.8, 0.4)],
    "hp":      [(0, 0), (8.5, 0), (8.51, 1), (20.19, 1), (20.2, 0)],
    "paint":   [(0, 0), (8.5, 0), (8.51, 1), (20.19, 1), (20.2, 0)],
}
MOUTH = [(0, "flat"), (1.95, "hum"), (2.85, "flat"), (4.5, "hum"), (5.2, "flat"), (5.83, "flat"),
         (7.4, "frown"), (8.5, "grin"), (12.4, "flat"), (13.2, "frown"), (13.8, "hum"), (14.9, "frown"),
         (20.2, "frown"), (25.6, "smile")]
# hand targets: ("hip"|"head", dx, dy), ("swing", side), ("wave",), ("pump", side)
HAND_L = [(0, ("hip", -122, -15)), (1.85, ("hip", -122, -15)), (2.1, ("head", -160, -240)),
          (2.8, ("head", -160, -240)), (3.15, ("hip", -122, -15)), (8.5, ("hip", -122, -15)),
          (8.75, ("pump", -1)), (12.2, ("pump", -1)), (12.55, ("head", -30, 100)), (15.25, ("head", -30, 100)),
          (15.7, ("hip", -122, -15)), (20.15, ("hip", -122, -15)), (20.25, ("hip", -122, -15)),
          (25.6, ("hip", -122, -15)), (26.1, ("head", -72, 40)), (26.8, ("head", -72, 40)),
          (27.2, ("hip", -122, -20))]
HAND_R = [(0, ("hip", 122, -15)), (1.85, ("hip", 122, -15)), (2.1, ("head", 160, -240)),
          (2.8, ("head", 160, -240)), (3.2, ("head", 45, 205)), (5.65, ("head", 45, 205)),
          (5.83, ("hip", 122, -15)), (8.5, ("hip", 122, -15)), (8.6, ("head", 165, -150)),
          (8.85, ("pump", 1)), (12.2, ("pump", 1)), (12.55, ("head", 30, 100)), (13.75, ("head", 30, 100)),
          (13.9, ("head", 12, 72)), (14.8, ("head", 12, 72)), (14.95, ("head", 30, 100)),
          (15.25, ("head", 30, 100)), (15.7, ("hip", 122, -15)), (20.15, ("hip", 122, -15)),
          (20.25, ("hip", 122, -15)), (21.6, ("hip", 122, -15)), (22.3, ("hip", 40, -330)),
          (24.4, ("hip", 40, -330)), (25.0, ("hip", 122, -20))]
FLAG_HELD = (8.5, 15.4)    # flashback only: in his right hand, falls at 15.4

# Shot list: (start, end, camera at start, camera at end, transition into the shot)
# camera = (zoom, pan_x, pan_y, roll_degrees); pan moves the point the camera looks at
# (negative y = look higher). His face sits around pan_y -336, his feet around +420.
SHOTS = [
    (0.00, 1.72, (1.50, 0, 0, 0), (1.45, 0, -110, 0), "fade"),          # bed: waking up
    (1.72, 3.37, (1.15, 0, -60, 0), (1.20, 0, -90, 0), "cut"),          # stretch + yawn
    (3.37, 5.83, (1.90, 0, -170, 0), (2.10, 0, -185, 0), "cut"),        # phone in hand
    (5.83, 7.40, (1.00, 0, -40, 0), (1.00, 0, -40, 0), "cut"),          # OTS: him + his reflection
    (7.40, 8.30, (1.60, 0, -300, 0), (2.40, 0, -340, 0), "cut"),        # reflection: push into his eyes
    (8.30, 8.71, (2.80, 0, -345, 0), (3.10, 0, -345, 0), "cut"),        # extreme close-up into the memory
    (8.71, 10.33, (1.00, 0, -60, 0), (1.06, 0, -90, 0), "flash"),       # 2023: stadium reveal
    (10.33, 12.40, (2.20, 0, -335, 0), (2.00, 0, -330, 0), "cut"),      # shouting with joy
    (12.40, 15.28, (1.30, 0, -220, 0), (3.00, 0, -345, -4), "cut"),     # tension push-in
    (15.28, 18.55, (1.60, 0, -250, 0), (1.00, 0, -40, 0), "dip"),       # loss: pull back, silence
    (18.55, 20.20, (2.40, 0, -335, 0), (2.60, 0, -338, 0), "cut"),      # the tear
    (20.20, 21.80, (2.30, 0, -335, 0), (2.00, 0, -320, 0), "cut"),      # reflection close-up, sad
    (21.80, 25.12, (1.00, 0, -40, 0), (1.00, 0, -40, 0), "cut"),        # OTS: hand meets the glass
    (25.12, 27.27, (1.00, 0, -40, 0), (1.00, 0, -40, 0), "dip"),        # OTS: end
]
RIPPLES = (8.5, 20.2)  # mirror ripple transitions into and out of the flashback
# over-the-shoulder windows: (start, end, outer zoom at start, outer zoom at end)
OTS = [(5.83, 7.40, 1.00, 1.07), (21.80, 25.12, 1.00, 1.07), (25.12, 27.27, 1.07, 1.00)]
INNER_CAM = (1.70, 0, -260, 0)       # how the reflection inside the mirror is framed
MIRROR = (330, 280, 1000, 1250)      # mirror glass rectangle in the OTS shot
TOUCH = (707, 972)                   # where hand and reflection meet on the glass


def ots_at(t):
    for a, b, z0, z1 in OTS:
        if a <= t < b:
            return lerp(z0, z1, smooth((t - a) / (b - a)))
    return None
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


# Locations: (start, kind).
LOCATIONS = [(0.0, "bedroom"), (5.83, "bathroom"), (8.5, "stadium"), (20.2, "bathroom")]


def location_at(t):
    return step(LOCATIONS, t)


LIGHT = [
    (0.0, ((60, 70, 110), (240, 170, 120), (1.04, 1.0, 0.96))),     # morning
    (5.82, ((60, 70, 110), (240, 170, 120), (1.04, 1.0, 0.96))),
    (5.83, ((30, 34, 44), (70, 76, 90), (0.98, 1.0, 1.04))),        # bathroom, cool
    (8.49, ((30, 34, 44), (70, 76, 90), (0.98, 1.0, 1.04))),
    (8.5, ((6, 10, 30), (34, 46, 92), (1.1, 1.0, 0.86))),           # 2023: warm memory tint
    (12.4, ((6, 10, 30), (34, 46, 92), (1.1, 1.0, 0.86))),
    (15.2, ((6, 10, 30), (34, 46, 92), (1.02, 0.96, 0.9))),
    (15.6, ((4, 6, 16), (16, 20, 40), (0.72, 0.74, 0.84))),
    (20.19, ((4, 6, 16), (16, 20, 40), (0.72, 0.74, 0.84))),
    (20.2, ((30, 34, 44), (70, 76, 90), (0.92, 0.95, 1.04))),       # bathroom again, colder
    (25.1, ((30, 34, 44), (70, 76, 90), (0.92, 0.95, 1.04))),
    (25.8, ((20, 22, 30), (46, 50, 62), (0.84, 0.86, 0.95))),
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
        if spec[0] == "pump":  # fists pumping in the air on the beat
            s_ = spec[1]
            return (head[0] + s_ * 165, head[1] - 205 + 34 * math.sin(phase * 2 + (0 if s_ < 0 else 1.2)))
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
    return 0.0, 0.0


def skip_at(t):
    """Cheering: hop on every beat in the stadium."""
    if 8.85 < t < 12.15:
        return abs(math.sin(walk_phase(t))) * 42
    return 0.0


LAST_HANDS = {}


# ======================================================================
# character
# ======================================================================
SKIN = (255, 226, 204)
SKIN_SH = (236, 190, 170)
HAIR = (30, 30, 46)
HAIR_HI = (86, 100, 150)
HOOD = (38, 92, 205)   # blue fan jersey
HOOD_SH = (26, 64, 150)
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

    # tricolour face paint on both cheeks (only in the 2023 flashback)
    for sx in ((-1, 1) if p.get("paint", 0) > 0.5 else ()):
        x0, y0 = cx + sx * 74 - 22, cy + 40
        for k, col in enumerate(((255, 153, 51), (250, 250, 250), (19, 136, 8))):
            pen.poly([(x0, y0 + k * 9), (x0 + 44, y0 + k * 9 - 4), (x0 + 44, y0 + k * 9 + 5),
                      (x0, y0 + k * 9 + 9)], col)

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
        tear = Image.new("RGBA", img.size, (0, 0, 0, 0))
        tp = Pen(tear, 0, 0, K)
        for sgn, ph in ((-1, p["tear"]), (1, p.get("tear2", -1))):
            if ph < 0:
                continue
            tx = cx + sgn * (70 + 6 * ph)
            ty = cy + 40 + 80 * ph
            tp.line([(cx + sgn * 68, cy + 42), (tx, ty)], (170, 210, 255, a // 2), 4)
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

    # headphones: only in the 2023 flashback
    hp, hp_d = (225, 60, 72), (110, 24, 34)
    if p.get("hp", 0) > 0.5:
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
    hip_y = 1250 - bob - air - hop + squash + p["sink"]
    p["tilt"] += math.sin(phase) * 4 * swag * walk
    p["tilt"] += p["shake"] * math.sin(t * 17) * 9  # "nahi bhai" head shake
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
        LAST_HANDS["L" if s < 0 else "R"] = hand

    # head
    head = draw_head(t, p)
    head = head.rotate(p["tilt"], resample=Image.BICUBIC, center=(PIVOT[0] * K, PIVOT[1] * K))
    px = int((neck[0] - rx0) * K - PIVOT[0] * K)
    py = int((neck[1] - ry0) * K - PIVOT[1] * K)
    img.alpha_composite(head, (max(px, 0), max(py, 0)), (max(-px, 0), max(-py, 0)))

    # returned at full supersampled resolution so close-ups stay sharp
    return img, (rx0, ry0), head_center


def draw_flag(layer, t):
    """Indian tricolour on a pole in his right hand; it slips and falls after the loss."""
    if not (FB[0] <= t < FB[1]) or "R" not in LAST_HANDS:
        return
    d = ImageDraw.Draw(layer)
    ang = track(T["flag_ang"], t)
    hx, hy = LAST_HANDS["R"]
    fall = clamp((t - FLAG_HELD[1]) / 0.9)
    if fall > 0:  # drop to the floor, tipping over
        hx += 60 * fall
        hy = lerp(hy, GROUND - 30, fall ** 2)
        ang = lerp(ang, 1.45, fall ** 1.5)
    L = 330
    tx, ty = hx + L * math.sin(ang), hy - L * math.cos(ang)
    d.line([(hx, hy + 40), (tx, ty)], fill=(120, 90, 60, 255), width=10)
    fw, fh = 230, 150
    wave_amt = (1 - fall) * (1.0 if t < 10.2 else 0.35)
    cols = ((255, 153, 51), (250, 250, 250), (19, 136, 8))
    ca, sa = math.cos(ang), math.sin(ang)
    strips = 23
    for i in range(strips):
        u0, u1 = i / strips, (i + 1) / strips
        def pt(u, v):
            off = math.sin(u * 5 - t * 9) * 14 * u * wave_amt
            x_, y_ = u * fw, v * fh + off
            # flag hangs from the pole top, perpendicular-ish to the pole
            return (tx + x_ * ca - y_ * sa, ty + x_ * sa + y_ * ca)
        for k, col in enumerate(cols):
            v0, v1 = k / 3, (k + 1) / 3
            d.polygon([pt(u0, v0), pt(u1, v0), pt(u1, v1), pt(u0, v1)], fill=col + (255,))
    cxp, cyp = (lambda u, v: (tx + u * fw * ca - v * fh * sa, ty + u * fw * sa + v * fh * ca))(0.5, 0.5)
    r = fh / 6 * 0.85
    d.ellipse([cxp - r, cyp - r, cxp + r, cyp + r], outline=(0, 0, 128, 255), width=3)
    for k in range(24):
        a_ = k * math.pi / 12
        d.line([(cxp, cyp), (cxp + r * math.cos(a_), cyp + r * math.sin(a_))], fill=(0, 0, 128, 255), width=1)


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


_rs = random.Random(19)
CROWD = [(_rs.uniform(-60, W + 60), _rs.uniform(HOR - 330, HOR + 150), _rs.random(), _rs.uniform(0, 6.28))
         for _ in range(2600)]
NEAR_FANS = [(x, _rs.uniform(0, 6.28)) for x in (40, 175, 905, 1040)]


def stadium_env(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d, g = ImageDraw.Draw(img), ImageDraw.Draw(glow)
    dim = smooth((t - 15.3) / 0.5)            # lights go dull after the loss
    flick = 1.0
    if 14.85 < t < 15.3:                        # floodlights flicker at the peak
        flick = 0.45 + 0.55 * (int(t * 22) % 2)
    bright = (1 - 0.6 * dim) * flick
    cheer = smooth((t - 5.6) / 0.4) * (1 - smooth((t - 10.2) / 0.4))
    # stand bowl (three tiers)
    for k, (y0, y1, col) in enumerate(((HOR - 340, HOR - 170, (26, 30, 60)), (HOR - 170, HOR - 10, (32, 38, 74)),
                                       (HOR - 10, HOR + 160, (38, 46, 88)))):
        d.rectangle([0, y0, W, y1], fill=tuple(int(c * (0.6 + 0.4 * bright)) for c in col) + (255,))
        d.line([(0, y1), (W, y1)], fill=(70, 80, 120, 255), width=3)
    # the crowd: blue shirts + phone torches, waving on the beat while cheering
    ph = walk_phase(t)
    for x, y, r, phs in CROWD:
        jump = cheer * 5 * abs(math.sin(ph + phs))
        shirt = (40, 90, 200) if r < 0.62 else ((255, 153, 51) if r < 0.72 else (230, 230, 240))
        c = tuple(int(v * (0.45 + 0.55 * bright)) for v in shirt)
        d.ellipse([x - 4, y - 4 - jump, x + 4, y + 4 - jump], fill=c + (255,))
        if r > 0.93 and t < 15.3:              # phone flashlights twinkle
            a = int(255 * (0.5 + 0.5 * math.sin(t * 7 + phs)) * bright)
            g.ellipse([x - 9, y - 9 - jump, x + 9, y + 9 - jump], fill=(255, 255, 240, a))
    # big screen on the far stand: "FINAL" (no real scores, no logos)
    d.rectangle([380, HOR - 300, 700, HOR - 190], fill=(10, 12, 20, 255), outline=(80, 90, 130, 255), width=4)
    sf = ImageFont.truetype(F_SYM, 46)
    if t < 15.3:
        d.text((540, HOR - 245), "FINAL", font=sf, fill=(255, 210, 90, int(255 * bright)), anchor="mm")
    else:
        d.text((540, HOR - 245), "...", font=sf, fill=(120, 130, 160, 255), anchor="mm")
    # pitch / outfield at the bottom of the bowl
    d.rectangle([0, HOR + 160, W, HOR + 330], fill=tuple(int(c * (0.5 + 0.5 * bright)) for c in (30, 110, 60)) + (255,))
    for k in range(6):
        d.rectangle([0, HOR + 160 + k * 28, W, HOR + 174 + k * 28],
                    fill=tuple(int(c * (0.5 + 0.5 * bright)) for c in (36, 124, 68)) + (255,))
    # floodlight towers
    for fx in (110, 970):
        d.line([(fx, HOR - 330), (fx, 120)], fill=(50, 56, 80, 255), width=12)
        d.rectangle([fx - 90, 60, fx + 90, 150], fill=(60, 66, 90, 255))
        for i in range(4):
            for j in range(2):
                lx, ly = fx - 66 + i * 44, 82 + j * 44
                d.ellipse([lx - 14, ly - 14, lx + 14, ly + 14], fill=(255, 252, 230, int(255 * bright)))
        g.ellipse([fx - 300, 105 - 240, fx + 300, 105 + 240], fill=(255, 250, 220, int(150 * bright)))
    # our stand: seat rows behind him, nearby fans
    d.rectangle([0, HOR + 330, W, H], fill=(20, 24, 44, 255))
    for k in range(6):
        y = HOR + 360 + k * 95
        d.rounded_rectangle([20, y, W - 20, y + 38], radius=10, fill=(28 + k * 3, 52, 120 - k * 6, 255))
    for x, phs in NEAR_FANS:
        sad = dim
        bob = cheer * 26 * abs(math.sin(ph + phs))
        top = 1030 + sad * 60 - bob
        col = (16, 30, 70, 255)
        d.ellipse([x - 52, top, x + 52, top + 104], fill=col)
        d.polygon([(x - 92, top + 120), (x + 92, top + 120), (x + 110, H), (x - 110, H)], fill=col)
        if cheer > 0.05:  # arms up
            for sgn in (-1, 1):
                d.line([(x + sgn * 70, top + 140), (x + sgn * 110, top - 80 - bob * 0.5)], fill=col, width=34)
        if sad > 0.5:     # heads in hands
            d.line([(x - 70, top + 150), (x - 30, top + 70)], fill=col, width=30)
            d.line([(x + 70, top + 150), (x + 30, top + 70)], fill=col, width=30)
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(28)))
    return img


def bedroom_env(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 6):  # warm morning wall
        f = y / H
        d.rectangle([0, y, W, y + 6], fill=(int(lerp(120, 70, f)), int(lerp(96, 56, f)), int(lerp(110, 70, f)), 255))
    # window with sunrise and light rays across the room
    d.rectangle([640, 260, 1010, 760], fill=(255, 196, 140, 255), outline=(70, 50, 56, 255), width=16)
    d.ellipse([760, 470, 900, 610], fill=(255, 236, 190, 255))
    d.line([(825, 260), (825, 760)], fill=(70, 50, 56, 255), width=10)
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    for k in range(4):
        rd.polygon([(650 + k * 90, 280), (700 + k * 90, 280), (300 + k * 160, H), (120 + k * 160, H)],
                   fill=(255, 220, 160, 38))
    img.alpha_composite(rays.filter(ImageFilter.GaussianBlur(20)))
    # headboard + pillow behind him
    d.rounded_rectangle([140, 860, 940, 1220], radius=60, fill=(86, 56, 48, 255), outline=(60, 38, 34, 255), width=8)
    d.rounded_rectangle([240, 1000, 840, 1180], radius=70, fill=(236, 232, 240, 255))
    # bedside table + clock
    d.rectangle([20, 1240, 150, 1560], fill=(96, 64, 52, 255))
    return img


def bathroom_env(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 90):  # tiles
        for x in range(0 if (y // 90) % 2 == 0 else -45, W, 90):
            d.rectangle([x + 2, y + 2, x + 88, y + 88], fill=(70, 82, 92, 255))
    # inside the mirror: a cooler, slightly darker copy of the room behind him
    d.rounded_rectangle([150, 360, 930, 1480], radius=40, fill=(40, 50, 62, 255))
    for y in range(360, 1480, 70):
        d.line([(150, y), (930, y)], fill=(48, 60, 72, 255), width=2)
    d.rectangle([700, 420, 860, 640], fill=(70, 86, 104, 255))  # a reflected doorway
    return img


def draw_env(t, kind, sky_bot):
    if kind == "stadium":
        return stadium_env(t)
    if kind == "bedroom":
        return bedroom_env(t)
    if kind == "bathroom":
        return bathroom_env(t)
    return _draw_road_env(t, kind, sky_bot)


def front_props(layer, t, inner=False):
    """Things in front of him: the blanket in bed, the phone, the mirror frame + sink."""
    d = ImageDraw.Draw(layer)
    kind = location_at(t)
    if kind == "bedroom":
        # blanket covering his legs, with folds
        d.rounded_rectangle([60, 1260, 1020, 1980], radius=80, fill=(70, 120, 190, 255), outline=(40, 80, 140, 255), width=8)
        for k in range(5):
            d.arc([100 + k * 170, 1300, 300 + k * 170, 1520], 200, 340, fill=(50, 96, 160, 255), width=8)
        d.rectangle([60, 1260, 1020, 1330], fill=(236, 232, 240, 255))  # sheet fold
        # alarm clock on the bedside table, shaking while it rings
        ring = 0.3 < t < 1.6
        sh = math.sin(t * 60) * 7 if ring else 0
        cx, cy = 85 + sh, 1180
        d.ellipse([cx - 52, cy - 52, cx + 52, cy + 52], fill=(220, 60, 60, 255), outline=(60, 20, 20, 255), width=5)
        d.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=(250, 248, 240, 255))
        d.line([(cx, cy), (cx, cy - 28)], fill=(30, 30, 40, 255), width=5)
        d.line([(cx, cy), (cx + 20, cy + 6)], fill=(30, 30, 40, 255), width=5)
        for sx in (-1, 1):
            d.ellipse([cx + sx * 40 - 18, cy - 70, cx + sx * 40 + 18, cy - 40], fill=(220, 60, 60, 255))
        if ring:
            for k in range(3):
                r = 70 + k * 22 + (t * 80) % 22
                d.arc([cx - r, cy - r, cx + r, cy + r], 290, 340, fill=(255, 240, 200, 220), width=5)
                d.arc([cx - r, cy - r, cx + r, cy + r], 200, 250, fill=(255, 240, 200, 220), width=5)
    if 3.2 < t < 5.8 and "R" in LAST_HANDS:  # phone in his hand
        hx, hy = LAST_HANDS["R"]
        d.rounded_rectangle([hx - 52, hy - 110, hx + 52, hy + 70], radius=16, fill=(20, 22, 30, 255))
        d.rounded_rectangle([hx - 44, hy - 100, hx + 44, hy + 60], radius=10, fill=(120, 170, 255, 255))
    if kind == "bathroom" and not inner:
        # mirror frame + glass shine (in front, so he reads as the reflection)
        d.rounded_rectangle([150, 360, 930, 1480], radius=40, outline=(200, 205, 215, 255), width=26)
        shine = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shine)
        for k, (x0, w_) in enumerate(((230, 70), (330, 26), (700, 50))):
            sd.polygon([(x0, 380), (x0 + w_, 380), (x0 + w_ - 260, 1460), (x0 - 260, 1460)], fill=(255, 255, 255, 26))
        layer.alpha_composite(shine.filter(ImageFilter.GaussianBlur(6)))
        # sink counter hides his legs
        d.rectangle([0, 1480, W, H], fill=(214, 216, 222, 255))
        d.rectangle([0, 1480, W, 1520], fill=(236, 238, 242, 255))
        d.ellipse([360, 1540, 720, 1680], fill=(190, 194, 202, 255))
        d.rectangle([520, 1440, 560, 1540], fill=(170, 174, 184, 255))  # tap


def _draw_road_env(t, kind, sky_bot):
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


def phone_card(d, t):
    """POV insert of the phone screen: a generic 'Memories' card from 3 years ago."""
    sc, a = pop(t, 4.0, 5.75, fade=0.25)
    if a <= 0:
        return
    al = int(255 * a)
    w_, h_ = 640 * clamp(sc, 0.2, 1.05), 860 * clamp(sc, 0.2, 1.05)
    x0, y0 = W / 2 - w_ / 2, 560 - h_ / 2 + 140
    d.rounded_rectangle([x0 - 16, y0 - 16, x0 + w_ + 16, y0 + h_ + 16], radius=60, fill=(16, 16, 22, al))
    d.rounded_rectangle([x0, y0, x0 + w_, y0 + h_], radius=46, fill=(246, 246, 250, al))
    if sc < 0.8:
        return
    f1, f2, f3 = (ImageFont.truetype(F_SYM, n) for n in (34, 46, 30))
    d.text((x0 + 40, y0 + 50), "Memories", font=f1, fill=(90, 90, 110, al))
    d.text((x0 + 40, y0 + 100), "Aaj ke din, 3 saal pehle", font=f2, fill=(20, 20, 30, al))
    # photo thumbnail: a stadium full of blue at night
    px0, py0, px1, py1 = x0 + 40, y0 + 190, x0 + w_ - 40, y0 + 560
    d.rounded_rectangle([px0, py0, px1, py1], radius=24, fill=(14, 20, 50, al))
    rr = random.Random(23)
    for _ in range(420):
        x, y = rr.uniform(px0 + 10, px1 - 10), rr.uniform(py0 + 30, py0 + 230)
        c = (40, 90, 200) if rr.random() < 0.7 else (255, 153, 51)
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=c + (al,))
    d.rectangle([px0, py0 + 240, px1, py1 - 20], fill=(30, 110, 60, al))
    for fx in (px0 + 60, px1 - 60):
        d.ellipse([fx - 40, py0 + 8, fx + 40, py0 + 40], fill=(255, 250, 220, al))
    d.text((x0 + 40, y0 + 600), "19 Nov 2023  -  Ahmedabad", font=f3, fill=(60, 60, 80, al))
    d.rounded_rectangle([x0 + 40, y0 + 680, x0 + w_ - 40, y0 + 760], radius=40, fill=(40, 100, 230, al))
    d.text((x0 + w_ / 2, y0 + 720), "Dekho yaadein", font=f1, fill=(255, 255, 255, al), anchor="mm")


def draw_signs(t, layer, cam, head):
    d = ImageDraw.Draw(layer)
    m, zd = world_to_screen(cam)

    # sleeping: zzz floating up, then the alarm
    if t < 1.0:
        for k in range(3):
            age = (t * 1.2 + k * 0.33) % 1
            x, y = m(head[0] + 110 + age * 90, head[1] - 120 - age * 160)
            sz = int((26 + k * 8) * zd * 0.6)
            al = int(230 * math.sin(math.pi * age) * (1 - smooth((t - 0.8) / 0.2)))
            d.text((x, y), "z", font=ImageFont.truetype(F_SYM, max(10, sz)), fill=(255, 255, 255, al))

    phone_card(d, t)

    # phone shock: anime surprise marks
    sc, a = pop(t, 4.45, 5.6, fade=0.15)
    if a > 0:
        al = int(255 * a)
        for ang in (-0.5, 0.0, 0.5):
            x0, y0 = m(head[0] + 230 * math.sin(ang), head[1] - 200 - 30 * math.cos(ang))
            x1, y1 = m(head[0] + 300 * math.sin(ang), head[1] - 260 - 50 * math.cos(ang))
            d.line([(x0, y0), (lerp(x0, x1, sc), lerp(y0, y1, sc))], fill=(255, 230, 120, al), width=max(4, int(3 * zd)))

    # flashback tag
    if FB[0] + 0.3 < t < FB[1] - 0.1:
        al = int(220 * smooth((t - FB[0] - 0.3) / 0.4))
        f = ImageFont.truetype(F_SYM, 34)
        d.rounded_rectangle([60, 150, 400, 210], radius=30, fill=(0, 0, 0, int(al * 0.6)))
        d.text((90, 160), "FLASHBACK  2023", font=f, fill=(255, 220, 160, al))

    # "sapna": stars rise from the crowd
    if 9.0 < t < 12.3:
        rr = random.Random(7)
        for k in range(14):
            born = 9.0 + rr.uniform(0, 2.8)
            age = t - born
            if 0 < age < 1.6:
                x = rr.uniform(80, W - 80)
                y = 1000 - age * 260
                r = 16 * math.sin(math.pi * age / 1.6)
                al = int(230 * math.sin(math.pi * age / 1.6))
                d.polygon([(x, y - r * 2), (x + r * 0.5, y - r * 0.5), (x + r * 2, y), (x + r * 0.5, y + r * 0.5),
                           (x, y + r * 2), (x - r * 0.5, y + r * 0.5), (x - r * 2, y), (x - r * 0.5, y - r * 0.5)],
                          fill=(255, 235, 150, al))

    # "jeet...": heartbeat line races across the top
    if 12.5 < t < 15.3:
        al = int(255 * smooth((t - 12.5) / 0.4) * (1 - smooth((t - 15.0) / 0.3)))
        pts = []
        speed = 1 + 1.5 * smooth((t - 12.5) / 2.6)
        for xp in range(60, W - 60, 6):
            u = (xp / W * 3 - t * speed) % 1
            yv = -90 if 0.42 < u < 0.46 else (60 if 0.46 < u < 0.5 else (18 if 0.38 < u < 0.42 else 0))
            pts.append((xp, 470 + yv))
        d.line(pts, fill=(255, 90, 100, al), width=6)

    # loss: muted speaker, heart breaking apart
    sc, a = pop(t, 15.5, 17.6)
    if a > 0:
        x, y, r = 880, 520, 46 * sc
        al = int(255 * a)
        col = (235, 235, 245, al)
        d.rectangle([x - r, y - r * 0.4, x - r * 0.4, y + r * 0.4], fill=col)
        d.polygon([(x - r * 0.4, y - r * 0.4), (x + r * 0.2, y - r), (x + r * 0.2, y + r), (x - r * 0.4, y + r * 0.4)],
                  fill=col)
        d.line([(x + r * 0.45, y - r * 0.45), (x + r * 1.15, y + r * 0.45)], fill=(255, 90, 90, al), width=8)
        d.line([(x + r * 1.15, y - r * 0.45), (x + r * 0.45, y + r * 0.45)], fill=(255, 90, 90, al), width=8)
    sc, a = pop(t, 16.1, 18.5)
    if a > 0:
        hx, hy = m(head[0] + 170, head[1] + 210)
        size = 4.0 * zd * sc * 0.6
        apart = smooth((t - 16.9) / 0.6)
        al = int(255 * a)
        for side in (-1, 1):
            pts = heart_pts(hx, hy, size, side)
            ox, oy = side * 9 * size * apart, 14 * size * apart ** 2
            d.polygon([(px_ + ox, py_ + oy) for px_, py_ in pts], fill=(220, 40, 70, int(al * (1 - apart * 0.5))))

    # back in the mirror: a crack spreads where his hand touches the glass
    if 22.4 < t < 27.27:
        grow = smooth((t - 22.4) / 1.2)
        al = int(200 * (1 - smooth((t - 26.6) / 0.6)))
        rr = random.Random(11)
        cx, cy = m(580, 920)
        for k in range(9):
            ang = k / 9 * math.tau + rr.uniform(-0.2, 0.2)
            pts = [(cx, cy)]
            x, y = cx, cy
            for j in range(4):
                step_ = rr.uniform(40, 80) * zd * 0.5 * grow
                ang += rr.uniform(-0.4, 0.4)
                x, y = x + step_ * math.cos(ang), y + step_ * math.sin(ang)
                pts.append((x, y))
            d.line(pts, fill=(235, 240, 255, al), width=3)

    # ending: a small broken heart drifting up
    sc, a = pop(t, 25.4, 27.27, fade=0.6)
    if a > 0:
        hx, hy = m(head[0] + 200, head[1] - 160 - (t - 25.4) * 40)
        size = 2.6 * zd * sc * 0.6
        for side in (-1, 1):
            pts = heart_pts(hx, hy, size, side)
            d.polygon([(px_ + side * size * 2, py_) for px_, py_ in pts], fill=(220, 40, 70, int(230 * a)))


CONFETTI = [(rnd_fx.uniform(0, W), rnd_fx.uniform(0, H), rnd_fx.uniform(90, 200), rnd_fx.uniform(0, 6.28),
             rnd_fx.choice([(255, 153, 51), (250, 250, 250), (19, 136, 8)])) for _ in range(90)]


def fx_layer(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    joy = smooth((t - 8.8) / 0.4) * (1 - smooth((t - 12.2) / 0.4))
    if joy > 0.01:
        for x, y, sp, ph, col in CONFETTI:
            yy_ = (y + t * sp) % H
            xx_ = x + 30 * math.sin(t * 2 + ph)
            ang = t * 6 + ph
            w_, h_ = 9 * abs(math.cos(ang)) + 2, 14
            d.polygon([(xx_ - w_, yy_ - h_ / 2), (xx_ + w_, yy_ - h_ / 2), (xx_ + w_, yy_ + h_ / 2),
                       (xx_ - w_, yy_ + h_ / 2)], fill=col + (int(220 * joy),))
    for x, y, s_, sp, ph in DUST:
        py_ = (y - t * sp) % H
        px_ = x + 24 * math.sin(t * 0.7 + ph)
        d.ellipse([px_ - s_, py_ - s_, px_ + s_, py_ + s_], fill=(210, 220, 255, 45))
    return layer.filter(ImageFilter.GaussianBlur(1.2))


# ======================================================================
# lyrics, music-video style: lower third, words drift up out of a blur
# ======================================================================
F_DEV = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
FONT_LYR = ImageFont.truetype(F_DEV, 70, layout_engine=ImageFont.Layout.RAQM)
EMPHASIS = {"Final": (255, 205, 80), "sapna": (140, 205, 255), "jeet": (130, 230, 150),
            "chup": (190, 195, 215), "Remember": (255, 120, 110), "19": (255, 120, 110),
            "dukhta": (255, 110, 130)}
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


LAYOUTS = []
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
# kinetic lyrics: each chunk of the song gets its own motion-graphics style
# (word timings aligned with Whisper against the user's lyric sheet)
# ======================================================================
F_HI = "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf"
_kfont = {}


def kfont(size):
    if size not in _kfont:
        _kfont[size] = ImageFont.truetype(F_HI, size, layout_engine=ImageFont.Layout.RAQM)
    return _kfont[size]


GOLD_K, SKY_K, RED_K, GLASS_K, WHITE_K, GREY_K = ((255, 205, 90), (130, 205, 255), (255, 96, 110),
                                                  (190, 230, 255), (255, 255, 255), (170, 175, 190))

# (words with start times, style, centre x, centre y, font size, colours per word, end time)
CHUNKS = [
    ([("कह", 0.42), ("दो", 0.58), ("जो", 0.80), ("हो", 1.22)], "soft", 540, 1530, 101, {}, 1.85),
    ([("तुम", 1.48), ("एक", 1.92), ("बार", 2.52)], "soft", 520, 1530, 108, {"बार": GOLD_K}, 3.2),
    ([("मेरे", 3.24), ("हो", 4.06)], "flip", 560, 1530, 139, {"मेरे": GOLD_K}, 4.28),
    ([("बस", 4.30), ("तुम", 4.94)], "flip", 540, 1530, 122, {}, 5.72),
    ([("मेरे", 5.76), ("नजरों", 6.68), ("में", 7.70)], "soft", 540, 1530, 113, {"नजरों": SKY_K}, 8.15),
    ([("तुम", 8.20), ("हम", 8.52), ("से", 8.98)], "ripple", 540, 1530, 132, {"हम": GOLD_K}, 9.9),
    ([("रह", 13.98), ("जाऊंगा", 14.25)], "slam", 540, 1530, 155, {"जाऊंगा": WHITE_K}, 15.5),
    ([("यूं", 15.58), ("ही", 15.94)], "shatter", 540, 1530, 177, {"यूं": RED_K, "ही": RED_K}, 16.75),
    ([("बस", 16.80), ("यूं", 17.08), ("ही", 17.52)], "grey", 540, 1530, 132, {}, 18.35),
    ([("बस", 18.40), ("यूं", 18.70), ("ही", 19.05)], "dissolve", 540, 1530, 132, {}, 20.1),
    ([("रह", 20.58), ("जाऊंगा", 20.85)], "mirror", 540, 1440, 132, {}, 22.1),
    ([("यूं", 22.18), ("ही", 22.54)], "mirror", 540, 1440, 151, {}, 23.35),
    ([("बस", 23.40), ("यूं", 23.68), ("ही", 24.12)], "mirror", 540, 1440, 132, {}, 24.95),
    ([("बस", 25.00), ("यूं", 25.30), ("ही", 25.65)], "final", 540, 1530, 165, {"यूं": RED_K, "ही": RED_K}, 27.25),
]
STYLE_COLOUR = {"soft": WHITE_K, "flip": WHITE_K, "ripple": WHITE_K, "slam": (255, 230, 200),
                "shatter": RED_K, "grey": GREY_K, "dissolve": GREY_K, "mirror": GLASS_K, "final": WHITE_K}
STYLE_GLOW = {"soft": (255, 200, 150), "flip": (255, 190, 90), "ripple": (150, 200, 255), "slam": (255, 140, 60),
              "shatter": (255, 60, 80), "grey": (90, 100, 130), "dissolve": (110, 120, 150),
              "mirror": (120, 200, 255), "final": (255, 80, 100)}
_ksprite = {}


def ksprite(word, size, col, glow):
    """Neon lyric sprite: wide soft halo + tight glow + bright core with a thin coloured edge."""
    key = (word, size, col, glow)
    if key in _ksprite:
        return _ksprite[key]
    f = kfont(size)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    x0, y0, x1, y1 = probe.textbbox((0, 0), word, font=f)
    pad = int(size * 0.6)
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (x1 - x0 + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    org = (pad - x0, pad)
    dark = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(dark).text(org, word, font=f, fill=(0, 0, 0, 170), stroke_width=size // 12, stroke_fill=(0, 0, 0, 170))
    img.alpha_composite(dark.filter(ImageFilter.GaussianBlur(size * 0.12)))
    wide = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(wide).text(org, word, font=f, fill=glow + (190,), stroke_width=size // 14, stroke_fill=glow + (190,))
    img.alpha_composite(wide.filter(ImageFilter.GaussianBlur(size * 0.30)))
    tight = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(tight).text(org, word, font=f, fill=glow + (255,), stroke_width=size // 22, stroke_fill=glow + (255,))
    img.alpha_composite(tight.filter(ImageFilter.GaussianBlur(size * 0.07)))
    core = tuple(int(c + (255 - c) * 0.55) for c in col)
    ImageDraw.Draw(img).text(org, word, font=f, fill=core + (255,), stroke_width=max(1, size // 45),
                             stroke_fill=glow + (255,))
    adv = probe.textlength(word, font=f)
    _ksprite[key] = (img, adv)
    return _ksprite[key]


def shine(img, frac):
    """A diagonal light sweep passing across the glowing word."""
    if not (-0.3 < frac < 1.3):
        return img
    arr = np.asarray(img).astype(np.float32)
    h_, w_ = arr.shape[:2]
    yy_, xx_ = np.mgrid[0:h_, 0:w_]
    band = np.exp(-(((xx_ + yy_ * 0.45) / w_ - frac) / 0.07) ** 2)
    k = band * (arr[:, :, 3] / 255.0) * 0.75
    arr[:, :, :3] = arr[:, :, :3] + (255 - arr[:, :, :3]) * k[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def alpha_mul(img, a):
    if a >= 0.999:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return out


def paste_c(frame, img, cx, cy):
    frame.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def row_ripple(img, amp, phase):
    if amp < 0.5:
        return img
    arr = np.asarray(img).copy()
    for y in range(arr.shape[0]):
        arr[y] = np.roll(arr[y], int(amp * math.sin(y / 9.0 + phase)), axis=0)
    return Image.fromarray(arr, "RGBA")


CHUNK_Y = {}
Y_CANDIDATES = (210, 330, 450, 1560, 1690)


def choose_y(key, width, height, occ):
    """Pick (once) the free band with the least character/flag/sign coverage; prefer the top."""
    if key in CHUNK_Y:
        return CHUNK_Y[key]
    best, best_cost = Y_CANDIDATES[0], None
    x0, x1 = int(max(0, 540 - width / 2) / 8), int(min(W, 540 + width / 2) / 8)
    for rank, y in enumerate(Y_CANDIDATES):
        y0, y1 = int(max(0, y - height / 2) / 8), int(min(H, y + height / 2) / 8)
        cost = 0.0
        if occ is not None:
            char_m, other_m = occ
            cost = char_m[y0:y1, x0:x1].mean() * 10 + other_m[y0:y1, x0:x1].mean() * 3
        cost += rank * 0.02
        if best_cost is None or cost < best_cost:
            best, best_cost = y, cost
    CHUNK_Y[key] = best
    return best


def draw_chunk(frame, t, words, style, cx, cy, size, colours, end, key=None, occ=None):
    if t < words[0][1] - 0.12 or t > end + 0.05:
        return
    base_col = STYLE_COLOUR[style]
    glow = STYLE_GLOW[style]
    sprites = [ksprite(w, size, colours.get(w, base_col), glow) for w, _ in words]
    space = size * 0.32
    total = sum(adv for _, adv in sprites) + space * (len(words) - 1)
    if key is not None:
        cy = choose_y(key, total + size, size * (2.6 if style == "mirror" else 1.7), occ)
    x = cx - total / 2
    out_k = smooth((t - (end - 0.25)) / 0.25)  # generic exit
    for i, ((w, wt), (spr, adv)) in enumerate(zip(words, sprites)):
        wx = x + adv / 2
        x += adv + space
        p = (t - wt) / 0.32
        if p <= 0:
            continue
        img, a, sx, sy, ang, dx, dy = spr, clamp(p * 2), 1.0, 1.0, 0.0, 0.0, 0.0
        if style == "soft":
            sx = sy = lerp(0.82, 1.0, ease_out(p))
            dy = (1 - ease_out(p)) * 34 + math.sin(t * 2 + i) * 4
            a *= 1 - out_k
        elif style == "flip":
            sy = clamp(back_out(p), 0.03, 1.25)
            sx = lerp(1.35, 1.0, ease_out(p))
            ang = (1 - ease_out(p)) * -10
            beat = math.exp(-((t - round(t / BEAT) * BEAT) / 0.06) ** 2)
            sx *= 1 + 0.05 * beat
            sy *= 1 + 0.05 * beat
            a *= 1 - out_k
        elif style == "ripple":
            sx = sy = lerp(1.25, 1.0, ease_out(p))
            amp = 30 * max(0.0, 1 - abs(t - 8.5) / 0.6) + 6 * smooth((t - 9.2) / 0.6)
            img = row_ripple(spr, amp, t * 25 + i)
            a *= 1 - smooth((t - 9.45) / 0.45)
        elif style == "slam":
            k = clamp((t - wt) / 0.16)
            sx = sy = lerp(2.4, 1.0, ease_out(k))
            if t - wt > 0.16:
                dec = math.exp(-(t - wt - 0.16) / 0.25)
                dx, dy = math.sin(t * 70) * 14 * dec, math.cos(t * 63) * 10 * dec
            a = clamp(k * 3) * (1 - out_k)
        elif style == "shatter":
            k = clamp((t - wt) / 0.16)
            sx = sy = lerp(2.2, 1.0, ease_out(k))
            brk = clamp((t - 16.35) / 0.55)
            if brk > 0:  # the word cracks into falling pieces
                cols, rows = 6, 3
                tw, th = spr.width // cols, spr.height // rows
                rr = random.Random(hash(w) % 1000 + i)
                for gy in range(rows):
                    for gx in range(cols):
                        tile = spr.crop((gx * tw, gy * th, (gx + 1) * tw, (gy + 1) * th))
                        vx, vy, spin = rr.uniform(-160, 160), rr.uniform(-120, 40), rr.uniform(-160, 160)
                        tx_ = wx - spr.width / 2 + gx * tw + tw / 2 + vx * brk
                        ty_ = cy - spr.height / 2 + gy * th + th / 2 + vy * brk + 900 * brk ** 2
                        tile = tile.rotate(spin * brk, expand=True, resample=Image.BICUBIC)
                        paste_c(frame, alpha_mul(tile, 1 - brk), tx_, ty_)
                continue
            a = clamp(k * 3)
        elif style == "grey":
            sx = sy = 1.0
            dy = (t - wt) * 24
            a *= (1 - out_k) * 0.85
        elif style == "dissolve":
            dy = (t - wt) * 18
            dis = clamp((t - 19.45) / 0.6)
            if dis > 0:  # breaks into drifting dust
                rr = random.Random(i + 7)
                arr = np.asarray(spr)
                ys, xs = np.nonzero(arr[:, :, 3] > 160)
                d = ImageDraw.Draw(frame)
                for j in rr.sample(range(len(xs)), min(260, len(xs))):
                    px_ = wx - spr.width / 2 + xs[j] + rr.uniform(-60, 60) * dis
                    py_ = cy - spr.height / 2 + ys[j] - rr.uniform(40, 220) * dis + dy
                    r = 2.4 * (1 - dis) + 0.6
                    d.ellipse([px_ - r, py_ - r, px_ + r, py_ + r], fill=GREY_K + (int(230 * (1 - dis)),))
                a *= 1 - smooth(dis * 2.5)
        elif style == "mirror":  # glassy text with its reflection, revealed through a ripple
            amp = 22 * (1 - ease_out(p * 0.8))
            img = row_ripple(spr, amp, t * 18 + i)
            a *= 1 - out_k
            refl = img.transpose(Image.FLIP_TOP_BOTTOM)
            grad = Image.linear_gradient("L").resize(refl.size).point(lambda v: int(v * 0.0 + (255 - v) * 0.32))
            ra = Image.fromarray((np.asarray(refl.getchannel("A")).astype(np.float32) *
                                  np.asarray(grad).astype(np.float32) / 255).astype(np.uint8))
            refl.putalpha(ra)
            paste_c(frame, alpha_mul(refl, a), wx, cy + spr.height * 0.78)
        elif style == "final":
            sx = sy = lerp(0.7, 1.0, ease_out(p)) * (1 + 0.04 * (t - wt))
            pulse = 0.9 + 0.1 * math.sin(t * 5)
            a *= pulse * (1 - smooth((t - 26.6) / 0.55))
        if a <= 0.01:
            continue
        beat = math.exp(-((t - round(t / BEAT) * BEAT) / 0.07) ** 2)
        sx *= 1 + 0.03 * beat
        sy *= 1 + 0.03 * beat
        img = shine(img, ((t - wt) * 0.9 + i * 0.12) % 2.2 - 0.3)
        if sx != 1.0 or sy != 1.0:
            img = img.resize((max(1, int(img.width * sx)), max(1, int(img.height * sy))), Image.BILINEAR)
        if abs(ang) > 0.2:
            img = img.rotate(ang, expand=True, resample=Image.BICUBIC)
        paste_c(frame, alpha_mul(img, a), wx + dx, cy + dy)
        # impact ring when a slammed word lands
        if style in ("slam", "shatter") and 0.1 < t - wt < 0.5:
            rk = (t - wt - 0.1) / 0.4
            d = ImageDraw.Draw(frame)
            r = lerp(60, 260, ease_out(rk))
            d.ellipse([wx - r, cy - r * 0.55, wx + r, cy + r * 0.55], outline=glow + (int(200 * (1 - rk)),), width=6)


def draw_date_slam(frame, t, occ=None):
    """Instrumental gap (no vocals): '19.11.2023' slams in digit by digit on the beat."""
    if not (10.2 < t < 13.95):
        return
    txt = "19.11.2023"
    f = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", 150)
    d0 = ImageDraw.Draw(frame)
    widths = [d0.textlength(c, font=f) for c in txt]
    x = 540 - sum(widths) / 2
    yc = choose_y("date", sum(widths) + 80, 330, occ)
    out = smooth((t - 13.55) / 0.4)
    for i, (c, w) in enumerate(zip(txt, widths)):
        wt = 10.33 + i * 0.209  # every half beat
        k = clamp((t - wt) / 0.14)
        if k <= 0:
            x += w
            continue
        spr, _ = ksprite_latin(c)
        sc = lerp(2.6, 1.0, ease_out(k))
        img = spr.resize((int(spr.width * sc), int(spr.height * sc)), Image.BILINEAR)
        shake = math.sin(t * 80 + i) * 8 * math.exp(-(t - wt) / 0.2) if t > wt + 0.14 else 0
        paste_c(frame, alpha_mul(img, clamp(k * 3) * (1 - out)), x + w / 2 + shake, yc)
        x += w
    lk = clamp((t - 12.45) / 0.5)
    if lk > 0:
        d0.line([(540 - 360 * lk, yc + 110), (540 + 360 * lk, yc + 110)], fill=(255, 153, 51, int(255 * (1 - out))), width=8)
        f2 = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", 44)
        d0.text((540, yc + 160), "AHMEDABAD", font=f2, fill=(255, 235, 210, int(255 * lk * (1 - out))), anchor="mm")


_lat = {}


def ksprite_latin(c):
    if c not in _lat:
        f = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", 150)
        img = Image.new("RGBA", (170, 230), (0, 0, 0, 0))
        gl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(gl).text((85, 115), c, font=f, fill=(255, 150, 60, 220), anchor="mm")
        img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(16)))
        ImageDraw.Draw(img).text((85, 115), c, font=f, fill=(255, 245, 225, 255), anchor="mm",
                                 stroke_width=4, stroke_fill=(40, 20, 10, 255))
        _lat[c] = (img, 170)
    return _lat[c]


def draw_kinetic(frame, t, occ=None):
    draw_date_slam(frame, t, occ)
    for idx, (words, style, cx, cy, size, colours, end) in enumerate(CHUNKS):
        draw_chunk(frame, t, words, style, cx, cy, size, colours, end, key=idx, occ=occ)


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


def draw_back_figure(layer, t):
    """Him from behind, big in the foreground of the over-the-shoulder mirror shot."""
    d = ImageDraw.Draw(layer)
    slump = track(T["slump"], t)
    breathe = math.sin(t * 2.2) * 4
    tilt = track(T["tilt"], t)
    hx, hy = 250 - tilt * 3, 1265 + slump * 34 + breathe
    body, body_sh = (20, 46, 110, 255), (14, 32, 80, 255)
    # shoulders and back of the hoodie
    d.polygon([(hx - 460, H), (hx - 430, 1640), (hx - 250, 1500), (hx - 110, 1460), (hx + 110, 1460),
               (hx + 250, 1500), (hx + 430, 1640), (hx + 470, H)], fill=body)
    d.ellipse([hx - 230, hy + 130, hx + 230, hy + 330], fill=body_sh)  # hood bunched at the neck
    d.rectangle([hx - 62, hy + 120, hx + 62, hy + 205], fill=(190, 150, 135, 255))
    # raised arm when he touches the mirror
    reach = smooth((t - 22.0) / 0.5) * (1 - smooth((t - 24.6) / 0.5))
    if reach > 0.01:
        sh = (hx + 330, 1600)
        tx, ty = lerp(hx + 420, TOUCH[0], reach), lerp(2050, TOUCH[1] + 40, reach)
        el = (lerp(sh[0], tx, 0.5) + 70, lerp(sh[1], ty, 0.5) + 40)
        d.line([sh, el, (tx, ty)], fill=body, width=120, joint="curve")
        d.ellipse([tx - 58, ty - 70, tx + 58, ty + 46], fill=(205, 165, 148, 255))
    # ears + back of the head (all hair)
    for sx in (-1, 1):
        d.ellipse([hx + sx * 222 - 32, hy - 20, hx + sx * 222 + 32, hy + 70], fill=(200, 160, 144, 255))
    pts = []
    for k in range(25):
        ang = math.radians(150 + k * 240 / 24)
        r = 240 if k % 2 == 0 else 285
        pts.append((hx + r * math.cos(ang), hy - 10 + r * 1.05 * math.sin(ang)))
    pts += [(hx + 236, hy + 120), (hx + 150, hy + 190), (hx - 150, hy + 190), (hx - 236, hy + 120)]
    d.polygon(pts, fill=(18, 18, 30, 255))
    d.arc([hx - 170, hy - 230, hx + 130, hy - 40], 200, 300, fill=(60, 70, 110, 255), width=14)


def render_scene(t, cam, inner=False):
    """Environment + character + props through one camera. Returns (frame, char layer, flag layer, head)."""
    top, bot, _ = light_at(t)
    sky = np.array(top, np.float32) * (1 - GRAD_Y) + np.array(bot, np.float32) * GRAD_Y
    frame = Image.fromarray(np.broadcast_to(sky, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    kind = location_at(t)
    star_a = {"stadium": 0.25}.get(kind, 0.0)
    if star_a > 0:
        stars = Image.fromarray((np.asarray(STARS) * np.array([1, 1, 1, star_a], np.float32)).astype(np.uint8))
        frame.alpha_composite(cam_transform(stars, 0.15, cam))
    frame.alpha_composite(cam_transform(draw_env(t, kind, bot), 0.9, cam))
    back = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(back).ellipse([410, GROUND - 12, 670, GROUND + 26], fill=(0, 0, 0, 110))
    frame.alpha_composite(cam_transform(back, 1.0, cam))
    char_img, origin, head = draw_character(t)
    char_l = cam_transform(char_img, 1.0, cam, origin, K)
    frame.alpha_composite(char_l)
    flag = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_flag(flag, t)
    flag_l = cam_transform(flag.filter(ImageFilter.GaussianBlur(0.7)), 1.0, cam)
    frame.alpha_composite(flag_l)
    props = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    front_props(props, t, inner=inner)
    frame.alpha_composite(cam_transform(props.filter(ImageFilter.GaussianBlur(0.7)), 1.0, cam))
    frame.alpha_composite(cam_transform(fx_layer(t), 1.1, cam))
    return frame, char_l, flag_l, head


def compose_ots(t, zoom):
    """Over-the-shoulder: his back in the foreground, his reflection in the mirror."""
    inner, _, _, _ = render_scene(t, INNER_CAM, inner=True)
    mx0, my0, mx1, my1 = MIRROR
    mw, mh = mx1 - mx0, my1 - my0
    crop_h = int(W * mh / mw)
    refl = inner.crop((0, 120, W, 120 + crop_h)).resize((mw, mh), Image.LANCZOS)
    out = bathroom_env(t).copy()
    mask = Image.new("L", (mw, mh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, mw - 1, mh - 1], radius=36, fill=255)
    out.paste(refl, (mx0, my0), mask)
    d = ImageDraw.Draw(out)
    # crack where his hand meets the glass
    if t > 22.4:
        grow = smooth((t - 22.4) / 1.2)
        rr = random.Random(11)
        for k in range(10):
            ang = k / 10 * math.tau + rr.uniform(-0.2, 0.2)
            x, y = TOUCH
            pts = [(x, y)]
            for j in range(4):
                stp = rr.uniform(30, 70) * grow
                ang += rr.uniform(-0.4, 0.4)
                x, y = x + stp * math.cos(ang), y + stp * math.sin(ang)
                pts.append((x, y))
            d.line(pts, fill=(235, 240, 255, 220), width=3)
    shine_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shine_l)
    for x0, w_ in ((420, 80), (540, 30), (860, 60)):
        sd.polygon([(x0, my0 + 10), (x0 + w_, my0 + 10), (x0 + w_ - 300, my1 - 10), (x0 - 300, my1 - 10)],
                   fill=(255, 255, 255, 24))
    out.alpha_composite(shine_l.filter(ImageFilter.GaussianBlur(6)))
    d.rounded_rectangle([mx0, my0, mx1, my1], radius=36, outline=(200, 205, 215, 255), width=24)
    d.rectangle([0, 1330, W, H], fill=(214, 216, 222, 255))  # sink counter
    d.rectangle([0, 1330, W, 1368], fill=(236, 238, 242, 255))
    d.rectangle([760, 1290, 800, 1380], fill=(170, 174, 184, 255))
    fig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_back_figure(fig, t)
    out.alpha_composite(fig.filter(ImageFilter.GaussianBlur(2.2)))  # shallow depth of field
    # slow outer camera move
    if abs(zoom - 1) > 1e-3:
        cw, ch_ = W / zoom, H / zoom
        cx_, cy_ = 600, 980
        out = out.crop((cx_ - cw / 2 * (cx_ / 540), cy_ - ch_ / 2 * (cy_ / 960),
                        cx_ - cw / 2 * (cx_ / 540) + cw, cy_ - ch_ / 2 * (cy_ / 960) + ch_)).resize((W, H), Image.BILINEAR)
    occ_char = np.zeros((H // 8, W // 8), np.float32)
    occ_char[my0 // 8:my1 // 8, mx0 // 8:mx1 // 8] = 1.0
    figm = np.asarray(fig.getchannel("A").resize((W // 8, H // 8))) > 40
    occ_char = np.maximum(occ_char, figm.astype(np.float32))
    return out, (occ_char, np.zeros_like(occ_char))


# ----------------------------------------------------------------------
# real photos in the flashback (free-licence, see assets/images/flashback-2023/CREDITS.md)
# ----------------------------------------------------------------------
PHOTO_DIR = os.path.join(HERE, "..", "..", "assets", "images", "flashback-2023")
PHOTOS = [  # (start, end, file, look); only photos from the 2023 World Cup period
    (8.62, 9.45, "stadium-2023.jpg", "warm"),
]

_photo_cache = {}


def photo_at(t):
    for a, b, f, look in PHOTOS:
        if a <= t < b:
            return a, b, f, look
    return None


def load_photo(f, look):
    key = (f, look)
    if key not in _photo_cache:
        im = Image.open(os.path.join(PHOTO_DIR, f)).convert("RGB")
        # trim the photographer's watermark strip at the very bottom; credit is in CREDITS.md
        im = im.crop((0, 0, im.width, int(im.height * 0.93)))
        if look == "bw":
            g = im.convert("L")
            g = Image.eval(g, lambda v: int(clamp((v - 128) * 1.25 + 128, 0, 255)))
            im = Image.merge("RGB", (g, g, g))
        else:
            arr = np.asarray(im).astype(np.float32)
            tintv = np.array([1.08, 1.0, 0.86] if look == "warm" else [0.95, 0.97, 1.02], np.float32)
            lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
            sat = 0.95 if look == "warm" else 0.6
            arr = (arr * sat + lum[:, :, None] * (1 - sat)) * tintv
            im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        _photo_cache[key] = im
    return _photo_cache[key]


def compose_photo(t, a, b, f, look):
    """A real photo as a memory: blurred backdrop, a film-print card with a slow push-in,
    an orange camera date stamp and a drifting light leak."""
    im = load_photo(f, look)
    p = (t - a) / (b - a)
    # backdrop: the same photo, enlarged, blurred and dimmed
    sc = max(W / im.width, H / im.height) * 1.1
    bg = im.resize((int(im.width * sc), int(im.height * sc)), Image.BILINEAR)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    bg = Image.eval(bg.filter(ImageFilter.GaussianBlur(28)), lambda v: int(v * 0.42)).convert("RGBA")
    # the card: Ken Burns push inside a white film-print border
    cw = 940
    ch = int(cw * im.height / im.width)
    zoom = 1.0 + 0.12 * p
    iw, ih = im.width / zoom, im.height / zoom
    ox, oy = (im.width - iw) * (0.3 + 0.4 * p), (im.height - ih) * 0.5
    inner = im.crop((ox, oy, ox + iw, oy + ih)).resize((cw, ch), Image.BICUBIC)
    card = Image.new("RGBA", (cw + 48, ch + 120), (246, 242, 232, 255))
    card.paste(inner, (24, 24))
    cd = ImageDraw.Draw(card)
    fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 38)
    cd.text((24 + cw - 20, 24 + ch - 20), "19 11 '23", font=fnt, fill=(255, 140, 40, 235), anchor="rs")
    # entrance: drops in slightly big and rotated, settles
    k = ease_out(clamp((t - a) / 0.22))
    rot = lerp(4.0, -1.5, k) + 0.6 * math.sin(t * 1.3)
    scl = lerp(1.12, 1.0, k)
    card = card.resize((int(card.width * scl), int(card.height * scl)), Image.BICUBIC)
    card = card.rotate(rot, expand=True, resample=Image.BICUBIC)
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 160), (0, 0), card.getchannel("A"))
    cx, cy = 540, 1010
    bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)), (int(cx - card.width / 2 + 14), int(cy - card.height / 2 + 22)))
    bg.alpha_composite(card, (int(cx - card.width / 2), int(cy - card.height / 2)))
    # light leak drifting across
    leak = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lx = lerp(-200, W + 200, p)
    ImageDraw.Draw(leak).ellipse([lx - 380, 300, lx + 380, 1600],
                                 fill=(255, 150, 60, 70) if look != "bw" else (255, 255, 255, 40))
    bg.alpha_composite(leak.filter(ImageFilter.GaussianBlur(120)))
    # quick white flash on the cut in, fade on the way out
    fl = math.exp(-((t - a) / 0.07) ** 2) * 0.7
    if fl > 0.02:
        bg.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * fl))))
    occ_c = np.zeros((H // 8, W // 8), np.float32)
    occ_c[int((cy - card.height / 2) / 8):int((cy + card.height / 2) / 8),
          int((cx - card.width / 2) / 8):int((cx + card.width / 2) / 8)] = 1.0
    return bg, (occ_c, np.zeros_like(occ_c))


def render_frame(t, rng):
    _, _, tint = light_at(t)
    zoom = ots_at(t)
    ph = photo_at(t)
    if ph is not None:
        frame, occ = compose_photo(t, *ph)
    elif zoom is not None:
        frame, occ = compose_ots(t, zoom)
    else:
        cam = camera_at(t)
        frame, char_l, flag_l, head = render_scene(t, cam)
        signs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_signs(t, signs, cam, head)
        frame.alpha_composite(signs.filter(ImageFilter.GaussianBlur(0.6)))
        cm = np.asarray(char_l.getchannel("A").resize((W // 8, H // 8))) > 40
        om = (np.asarray(flag_l.getchannel("A").resize((W // 8, H // 8))) > 40) | \
             (np.asarray(signs.getchannel("A").resize((W // 8, H // 8))) > 40)
        occ = (cm.astype(np.float32), om.astype(np.float32))

    # colour grade, transitions, vignette, grain
    blur, bright, flash = transition_fx(t)
    arr = np.asarray(frame.convert("RGB")).astype(np.float32) * np.array(tint, np.float32)
    desat = track(T["desat"], t)
    if desat > 0.01:  # the loss drains the colour
        lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
        arr = arr * (1 - desat) + lum[:, :, None] * desat
    arr = motion_blur(arr, blur)
    for rt in RIPPLES:  # mirror ripple into / out of the flashback, with a soft white bloom
        r = 1 - abs(t - rt) / 0.45
        if r > 0:
            amp = 38 * r * r
            shift = (amp * np.sin(np.arange(H) / 38.0 + t * 30)).astype(int)
            arr = np.stack([np.roll(arr[y], shift[y], axis=0) for y in range(H)])
            arr = arr + (255 - arr) * (0.55 * r * r)
    if flash > 0.01:
        arr = arr + (255 - arr) * flash * np.array([1.0, 0.88, 0.6], np.float32)
    arr *= VIGNETTE * bright
    arr += rng.normal(0, 3, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    draw_kinetic(out, t, occ)
    out = out.convert("RGB")
    fade = min(clamp(t / 0.4), clamp((DURATION - t) / 0.7))
    if fade < 1:
        out = Image.blend(Image.new("RGB", (W, H)), out, fade)
    return out


# ======================================================================
# TV room: one frame with the CRT TV playing the user's clip and the crying boy
# ======================================================================
CLIP = AUDIO
SCREEN = [(96, 618), (548, 644), (548, 968), (96, 994)]   # CRT screen quad (TL, TR, BR, BL)
CHAR_CAM = (1.12, -161, 19, 0)                           # places him bottom-right, sitting on the floor
SIT = 230                                                # how far he sits down (legs under the blanket)
F_NUM = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
rr_room = random.Random(42)
RAIN_TV = [(rr_room.uniform(700, 1010), rr_room.uniform(260, 700), rr_room.uniform(500, 900)) for _ in range(60)]


def make_room():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, 1380, 4):  # back wall
        f = y / 1380
        d.rectangle([0, y, W, y + 4], fill=(int(lerp(26, 16, f)), int(lerp(30, 18, f)), int(lerp(52, 32, f)), 255))
    d.rectangle([0, 1380, W, H], fill=(30, 24, 28, 255))  # floor
    for k in range(10):
        d.line([(540 + (k - 5) * 70, 1380), (540 + (k - 5) * 300, H)], fill=(38, 30, 34, 255), width=3)
    d.line([(0, 1380), (W, 1380)], fill=(44, 38, 48, 255), width=6)
    # window frame (rain is drawn per frame)
    d.rectangle([700, 260, 1010, 700], fill=(12, 18, 40, 255), outline=(36, 32, 44, 255), width=16)
    d.line([(855, 260), (855, 700)], fill=(36, 32, 44, 255), width=10)
    d.line([(700, 480), (1010, 480)], fill=(36, 32, 44, 255), width=10)
    d.polygon([(680, 240), (760, 240), (735, 740), (680, 760)], fill=(40, 30, 56, 255))      # curtains
    d.polygon([(1030, 240), (950, 240), (975, 740), (1030, 760)], fill=(40, 30, 56, 255))
    # wall calendar: NOVEMBER 19, circled
    d.rectangle([486, 300, 626, 470], fill=(210, 206, 198, 255))
    d.rectangle([486, 300, 626, 340], fill=(160, 40, 48, 255))
    d.text((556, 320), "NOV", font=ImageFont.truetype(F_NUM, 26), fill=(255, 255, 255, 255), anchor="mm")
    d.text((556, 405), "19", font=ImageFont.truetype(F_NUM, 72), fill=(40, 40, 50, 255), anchor="mm")
    d.ellipse([504, 352, 608, 458], outline=(190, 30, 40, 255), width=5)
    # sofa behind him
    d.rounded_rectangle([430, 1120, 1100, 1460], radius=50, fill=(46, 40, 66, 255))
    d.rounded_rectangle([470, 1040, 1080, 1200], radius=60, fill=(54, 46, 76, 255))
    # TV cabinet + old CRT TV
    d.rectangle([10, 1010, 640, 1200], fill=(46, 32, 30, 255))
    d.rectangle([10, 1010, 640, 1030], fill=(64, 46, 40, 255))
    d.rectangle([60, 1060, 300, 1170], outline=(30, 22, 20, 255), width=5)
    d.rectangle([340, 1060, 600, 1170], outline=(30, 22, 20, 255), width=5)
    d.polygon([(50, 560), (610, 590), (620, 1010), (40, 1010)], fill=(36, 34, 40, 255))   # TV body
    d.polygon([(70, 582), (590, 608), (594, 994), (66, 1004)], fill=(24, 24, 28, 255))     # bezel
    for k in range(6):  # speaker grille + knobs under the screen area (right side of the bezel)
        d.line([(560, 700 + k * 14), (586, 700 + k * 14)], fill=(50, 50, 56, 255), width=4)
    d.ellipse([560, 820, 586, 846], fill=(70, 70, 78, 255))
    d.ellipse([560, 860, 586, 886], fill=(70, 70, 78, 255))
    d.line([(330, 560), (250, 430)], fill=(60, 60, 66, 255), width=6)  # rabbit-ear antenna
    d.line([(330, 560), (420, 420)], fill=(60, 60, 66, 255), width=6)
    return img


ROOM = make_room()


def quad_coeffs(dst, w, h):
    """PIL PERSPECTIVE coefficients mapping the output quad `dst` back to a w x h source."""
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


SCREEN_COEFFS = None


def crt_frame(clip_rgb, t):
    """Fit the square clip into a 4:3-ish CRT picture: pillarbox, scanlines, curvature-ish vignette."""
    cw_, ch_ = 640, 560
    pic = Image.new("RGB", (cw_, ch_), (0, 0, 0))
    sc = ch_ / clip_rgb.height
    cl = clip_rgb.resize((int(clip_rgb.width * sc), ch_), Image.BILINEAR)
    pic.paste(cl, ((cw_ - cl.width) // 2, 0))
    arr = np.asarray(pic).astype(np.float32)
    arr[::4] *= 0.78                                              # scanlines
    yy_, xx_ = np.mgrid[0:ch_, 0:cw_]
    vig = 1 - 0.35 * (((xx_ - cw_ / 2) / (cw_ / 2)) ** 4 + ((yy_ - ch_ / 2) / (ch_ / 2)) ** 4)
    arr *= vig[:, :, None] * (0.96 + 0.04 * math.sin(t * 50))      # flicker
    arr = arr * 1.05 + 6
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def tv_room(t, clip_rgb):
    global SCREEN_COEFFS
    frame = ROOM.copy()
    d = ImageDraw.Draw(frame)
    for x, y, sp in RAIN_TV:  # rain on the window
        yy_ = 260 + ((y - 260 + t * sp) % 440)
        d.line([(x, yy_), (x - 4, yy_ + 26)], fill=(120, 140, 190, 120), width=2)
    # the clip on the TV
    pic = crt_frame(clip_rgb, t)
    if SCREEN_COEFFS is None:
        SCREEN_COEFFS = quad_coeffs(SCREEN, pic.width, pic.height)
    warped = pic.convert("RGBA").transform((W, H), Image.PERSPECTIVE, SCREEN_COEFFS, resample=Image.BILINEAR)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(SCREEN, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    frame.paste(warped, (0, 0), mask)
    # glass reflection on the screen
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).polygon([(150, 630), (260, 636), (170, 990), (110, 990)], fill=(255, 255, 255, 18))
    frame.alpha_composite(gl)
    # TV light: the clip's average colour spills into the room
    avg = np.asarray(clip_rgb.resize((8, 8))).reshape(-1, 3).mean(0)
    light = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(light)
    col = tuple(int(min(255, c * 1.1 + 30)) for c in avg)
    ld.ellipse([-200, 380, 900, 1500], fill=col + (70,))
    ld.polygon([(548, 650), (1080, 900), (1080, 1700), (548, 960)], fill=col + (38,))
    frame.alpha_composite(light.filter(ImageFilter.GaussianBlur(90)))
    bloom = warped.filter(ImageFilter.GaussianBlur(40))
    bloom.putalpha(mask.point(lambda v: int(v * 0.45)).filter(ImageFilter.GaussianBlur(40)))
    frame.alpha_composite(bloom)
    return frame, col


def set_acting(t):
    """Crying loop: tears on both cheeks, blinks, sobs, head drops, wiping eyes."""
    sob = max(0.0, math.sin(t * 0.9)) ** 6           # sob waves every ~7 s
    head_down = smooth((math.sin(t * 0.35 - 1.2) + 0.35) * 2)  # sometimes drops his head
    blink = 1.0 if (t % 3.7) < 0.12 else 0.0
    T["tear"] = [(0, (t / 2.3) % 1)]
    T["tear2"] = [(0, (t / 2.3 + 0.5) % 1)]
    T["tear_a"] = [(0, 1.0)]
    T["lid"] = [(0, max(blink, 0.42 + 0.25 * head_down))]
    T["head_dy"] = [(0, 6 + 16 * head_down + 7 * sob * abs(math.sin(t * 9)))]
    T["slump"] = [(0, 0.55 + 0.25 * head_down)]
    T["look"] = [(0, (lerp(-0.85, -0.2, head_down), lerp(0.05, 0.75, head_down)))]
    T["tilt"] = [(0, -4 + 3 * math.sin(t * 0.5))]
    T["brow"] = [(0, 1.0)]
    globals()["MOUTH"] = [(0, "hum" if sob > 0.35 else "frown")]


T.update({k: [(0, 0)] for k in ("stand", "sink", "shake", "happy", "blush", "laugh", "crown", "walk", "swag",
                                "speed", "hp", "paint", "desat", "flag_ang")})
T["stand"] = [(0, 1)]
T["sink"] = [(0, SIT)]
HAND_L = [(0, ("hip", -50, -165)), (16.8, ("hip", -50, -165)), (17.2, ("head", -55, 25)), (18.3, ("head", -55, 25)),
          (18.7, ("hip", -50, -165)), (32.8, ("hip", -50, -165)), (33.2, ("head", -55, 25)), (34.4, ("head", -55, 25)),
          (34.8, ("hip", -50, -165))]
HAND_R = [(0, ("hip", 45, -165)), (8.8, ("hip", 45, -165)), (9.2, ("head", 55, 25)), (10.4, ("head", 55, 25)),
          (10.8, ("hip", 45, -165)), (24.0, ("hip", 45, -165)), (24.4, ("head", 55, 25)), (25.6, ("head", 55, 25)),
          (26.0, ("hip", 45, -165))]


WIPES = ((9.0, 10.6, 1), (17.0, 18.5, -1), (24.2, 25.8, 1), (33.0, 34.6, -1))


def draw_blanket(layer, t, head):
    """He sits hugging his knees, wrapped in a soft blanket; his hands hold it closed over his knees."""
    hx = head[0]
    sy = head[1] + 160
    hip = 1250 + SIT
    br = math.sin(t * 2.2) * 3
    left = [(hx - 70, sy - 30 + br), (hx - 150, sy - 14), (hx - 205, sy + 18), (hx - 232, sy + 80),
            (hx - 246, hip - 60), (hx - 278, hip + 120), (hx - 315, hip + 300)]
    outline = left + [(2 * hx - x, y) for x, y in reversed(left)]
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.polygon(outline, fill=255)
    md.ellipse([hx - 215, hip - 150, hx + 215, hip + 140], fill=255)  # knees
    mask = mask.filter(ImageFilter.GaussianBlur(1.5))
    # soft shading: lighter in the middle, darker at the sides and bottom
    xx_ = np.arange(W, dtype=np.float32)[None, :]
    yy_ = np.arange(H, dtype=np.float32)[:, None]
    shade = 1 - 0.45 * np.clip(np.abs(xx_ - hx) / 320, 0, 1) ** 1.6 - 0.15 * np.clip((yy_ - hip) / 300, 0, 1)
    base = np.array([112, 84, 102], np.float32)
    rgb = np.clip(base[None, None, :] * shade[:, :, None], 0, 255).astype(np.uint8)
    blanket = Image.fromarray(rgb, "RGB").convert("RGBA")
    blanket.putalpha(mask)
    layer.alpha_composite(blanket)
    d = ImageDraw.Draw(layer)
    d.polygon([(hx - 70, sy - 30 + br), (hx, sy + 64), (hx + 70, sy - 30 + br)], fill=(70, 50, 64, 255))
    d.line(left[:4], fill=(150, 118, 136, 255), width=7, joint="curve")
    d.line([(2 * hx - x, y) for x, y in left[:4]], fill=(150, 118, 136, 255), width=7, joint="curve")
    d.arc([hx - 205, hip - 145, hx + 205, hip + 120], 200, 340, fill=(150, 118, 136, 255), width=7)  # knee highlight
    d.arc([hx - 215, hip - 150, hx + 215, hip + 140], 20, 160, fill=(70, 50, 64, 255), width=5)
    for k in range(3):  # folds falling from the knees
        x = hx - 120 + k * 120
        d.line([(x, hip + 150), (x - 14 + k * 14, hip + 290)], fill=(80, 58, 72, 255), width=6)
    wiping = [side for a, b, side in WIPES if a <= t <= b]
    for side, x in ((-1, hx - 82), (1, hx + 78)):
        if side in wiping:
            continue
        y = hip - 132 + (4 if side > 0 else 0)
        d.ellipse([x - 32, y - 26, x + 32, y + 30], fill=(250, 220, 200, 255), outline=(14, 14, 24, 255), width=3)
        d.line([(x - 18, y - 4), (x + 18, y - 4)], fill=(220, 180, 160, 255), width=3)


def render_tv_frame(t, clip_rgb, rng):
    frame, tv_col = tv_room(t, clip_rgb)
    set_acting(t)
    char_img, origin, head = draw_character(t)
    char_l = cam_transform(char_img, 1.0, CHAR_CAM, origin, K)
    frame.alpha_composite(char_l)
    bl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_blanket(bl, t, head)
    bl_l = cam_transform(bl.filter(ImageFilter.GaussianBlur(0.8)), 1.0, CHAR_CAM)
    frame.alpha_composite(bl_l)
    # the wiping hand: sleeve out of the blanket's neck opening, hand over his eye (drawn on top of the face)
    for a_, b_, side in WIPES:
        if a_ <= t <= b_ and ("R" if side > 0 else "L") in LAST_HANDS:
            k = smooth((t - a_) / 0.35) * (1 - smooth((t - (b_ - 0.35)) / 0.35))
            if k <= 0.02:
                continue
            z = CHAR_CAM[0]
            def scr(x, y):
                return (CAM_C[0] + z * (x - CAM_C[0] - CHAR_CAM[1]), CAM_C[1] + z * (y - CAM_C[1] - CHAR_CAM[2]))
            sy_w = head[1] + 160
            start = scr(head[0] + side * 55, sy_w - 10)
            eye = (head[0] + side * 48, head[1] + 28 + 6 * math.sin(t * 10))  # rubbing
            end_w = (lerp(head[0] + side * 60, eye[0], k), lerp(sy_w + 40, eye[1], k))
            end = scr(*end_w)
            hd = ImageDraw.Draw(frame)
            hd.line([start, end], fill=(14, 14, 24, 255), width=int(56 * z))
            hd.line([start, end], fill=HOOD + (255,), width=int(48 * z))
            r = 27 * z
            hd.ellipse([end[0] - r, end[1] - r, end[0] + r, end[1] + r], fill=(250, 220, 200, 255),
                       outline=(14, 14, 24, 255), width=3)
    # TV light rim on what is visible of him (head + blanket)
    vis = np.maximum(np.asarray(char_l.getchannel("A")).astype(np.float32) *
                     (1 - np.asarray(bl_l.getchannel("A")).astype(np.float32) / 255),
                     np.asarray(bl_l.getchannel("A")).astype(np.float32))
    rim = Image.new("RGBA", (W, H), tv_col + (0,))
    rim.putalpha(Image.fromarray((vis * 0.2).astype(np.uint8)))
    shift = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shift.paste(rim, (-6, 0))
    frame.alpha_composite(shift)
    # slow push-in over the whole clip, very gentle drift
    z = 1.0 + 0.08 * smooth(t / DURATION)
    cx_, cy_ = 560 + 6 * math.sin(t * 0.3), 1000 + 6 * math.cos(t * 0.25)
    cw, ch = W / z, H / z
    frame = frame.crop((cx_ - cw / 2, cy_ - ch / 2, cx_ + cw / 2, cy_ + ch / 2)).resize((W, H), Image.BILINEAR)
    arr = np.asarray(frame.convert("RGB")).astype(np.float32)
    arr *= VIGNETTE * 0.95
    arr += rng.normal(0, 3, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    fade = min(clamp(t / 0.5), clamp((DURATION - t) / 0.8))
    if fade < 1:
        out = Image.blend(Image.new("RGB", (W, H)), out, fade)
    return out


def cam_point(y_world):
    z, px, py, _ = CHAR_CAM
    return CAM_C[1] + z * (y_world - CAM_C[1] - py)


def clip_frames():
    """The clip resampled to 30 fps, as PIL images, in order."""
    cw, ch = 720, 724
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", CLIP, "-vf", f"fps={FPS}", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = cw * ch * 3
    last = None
    while True:
        buf = proc.stdout.read(n)
        if len(buf) < n:
            break
        last = Image.frombytes("RGB", (cw, ch), buf)
        yield last
    proc.wait()
    while True:  # pad with the last frame if the clip is a hair short
        yield last


def clip_frame_at(t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", CLIP, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.frombytes("RGB", (720, 724), raw)


def main():
    rng = np.random.default_rng(1)
    if "--frames" in sys.argv:
        idx = [int(v) for v in sys.argv[sys.argv.index("--frames") + 1].split(",")]
        for i in idx:
            render_tv_frame(i / FPS, clip_frame_at(i / FPS), rng).save(os.path.join(HERE, f"_preview_{i:04d}.png"))
        return
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", CLIP, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-af", f"afade=t=out:st={DURATION - 0.8:.2f}:d=0.8", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    for i, clip in zip(range(n), clip_frames()):
        proc.stdin.write(render_tv_frame(i / FPS, clip, rng).tobytes())
        if i % 90 == 0:
            print(f"frame {i}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
