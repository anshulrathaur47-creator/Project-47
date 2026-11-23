"""Reel for the sher "उसको फुर्सत नहीं मिलती कि पलट कर देखे, हम ही दीवाने हैं, दीवाने बने रहते हैं"
(assets/music/ReelAudio-62874.mp3, 13.1 s, recited at a mushaira with "वाह" from the audience).

He waits with a rose; she is always busy and never turns back to look. Day after day he waits at the same lamp
post (chocolates in the morning, a card at dusk, a rose at night); she passes every time. At night he sits on
the low wall under the lamp beside a pile of dried roses, smiling to himself with wet eyes: we are the mad ones,
and we stay mad.

New character: a young man in a white kurta with a charcoal Nehru jacket and white pyjama, jet-black hair
(the rig from ../2026-11-21-koi-khas-nahi/make_khas.py, male style). She is a long-haired silhouette.
Lyrics: plain static lines, only for the spoken sher (not for the audience's "वाह").

Usage: python3 make_fursat.py [--frames 30,150,...] [--workers 4]
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
sys.path.insert(0, os.path.join(HERE, "..", "2026-11-21-koi-khas-nahi"))
import make_khas as kh  # noqa: E402

m = kh.m
clamp, smooth, lerp, ease_out, back_out, track = kh.clamp, kh.smooth, kh.lerp, kh.ease_out, kh.back_out, kh.track
W, H, FPS = 1080, 1920, 30
AUDIO = os.path.join(HERE, "..", "..", "assets", "music", "ReelAudio-62874.mp3")
OUT = os.path.join(HERE, "fursat.mp4")
SILENT = os.path.join(HERE, "_fursat_silent.mp4")
DUR = 13.10

# ---------------------------------------------------------------- the new character
kh.STYLE = "male"
kh.SKIN, kh.SKIN_SH = (205, 150, 112), (182, 128, 94)
kh.HAIR = (14, 14, 18)
kh.DENIM, kh.DENIM_SH, kh.DENIM_L = (46, 48, 58), (32, 34, 42), (72, 74, 86)   # Nehru jacket
kh.CUFF = (226, 224, 216)
kh.SLEEVE = (240, 238, 232)             # kurta sleeves
kh.CREAM = (244, 242, 236)              # kurta front
kh.JEANS = (232, 228, 220)              # pyjama
kh.MEM_THUMB = Image.new("RGBA", (4, 4))

kh.LINES = [
    (0.10, 2.70, "उसको फ़ुर्सत नहीं मिलती"),
    (2.72, 4.00, "कि पलट कर देखे"),
    (5.38, 7.55, "उसको फ़ुर्सत नहीं मिलती"),
    (7.58, 8.95, "कि पलट कर देखे"),
    (9.04, 10.22, "हम ही दीवाने हैं"),
    (10.25, 11.34, "दीवाने बने रहते हैं"),
]

SIT = 210
kh.T = {
    "walk": [(0, 0)], "speed": [(0, 0)],
    "sink": [(0, 0), (9.03, 0), (9.04, SIT)],
    "slump": [(0, 0.05), (3.4, 0.05), (3.9, 0.35), (5.38, 0.1), (6.6, 0.1), (6.9, 0.3), (6.95, 0.1), (7.9, 0.3), (8.0, 0.1),
              (8.6, 0.4), (9.04, 0.3)],
    "head_dy": [(0, 0), (3.4, 0), (3.8, 10), (5.38, 0), (9.04, 6), (9.6, 14), (10.2, 14), (10.4, -6), (11.3, -6), (11.5, 4)],
    "tilt": [(0, 0), (2.72, 3), (3.9, -3), (5.38, 2), (8.0, 0), (9.04, -4), (10.3, 4), (12.0, 6)],
    "shake": [(0, 0)],
    "look": [(0, (0.2, -0.1)), (2.72, (0.2, -0.15)), (3.45, (0.1, 0.5)), (5.38, (-0.9, 0)), (6.6, (0.9, 0)), (6.94, (0.9, 0)),
             (7.9, (-0.9, 0)), (8.0, (-0.6, 0)), (8.15, (0.3, -0.1)), (8.6, (0.8, 0.2)), (9.04, (0, 0.7)), (10.25, (0, -0.4)),
             (11.4, (0.2, -0.6))],
    "lid": [(0, 0), (3.4, 0.0), (3.8, 0.3), (5.38, 0), (6.7, 0.3), (6.94, 0), (7.9, 0.3), (8.0, 0), (8.6, 0.3), (9.04, 0.25),
            (10.25, 0.15), (11.4, 0.2), (11.9, 1.0)],
    "happy": [(0, 0)],
    "brow": [(0, -0.1), (2.72, -0.15), (3.45, 0.7), (5.38, -0.1), (6.7, 0.6), (6.94, -0.1), (7.9, 0.6), (8.0, -0.2), (8.6, 0.8),
             (9.04, 0.6), (11.4, 0.5)],
    "tear": [(0, 0), (10.3, 0), (11.3, 1)],
    "tear_a": [(0, 0), (8.6, 0), (8.9, 0.6), (9.04, 0.6), (10.2, 1), (13.2, 1)],
    "cry": [(0, 0)],
    "blush": [(0, 0.2)],
    "laugh": [(0, 0)],
    "wet": [(0, 0)],
    "wet_shoulder": [(0, 0)],
    "split": [(0, 0)],
}
kh.MOUTH = [(0, "smile"), (3.45, "flat"), (5.38, "smile"), (6.7, "flat"), (6.94, "smile"), (7.9, "flat"), (8.0, "smile"),
            (8.6, "frown"), (9.04, "smile"), (11.9, "smile")]
SIDE_L, SIDE_R = ("hip", -122, -15), ("hip", 122, -15)
ROSE_R = ("head", 120, 240)
BOX_L, BOX_R = ("head", -46, 270), ("head", 46, 270)
HOLD_L, HOLD_R = ("head", -34, 250), ("head", 34, 250)
kh.HAND_L = [(0, SIDE_L), (5.37, SIDE_L), (5.38, BOX_L), (6.93, BOX_L), (6.94, SIDE_L), (9.03, SIDE_L), (9.04, HOLD_L)]
kh.HAND_R = [(0, ROSE_R), (3.5, ROSE_R), (3.9, ("hip", 128, -30)), (5.37, ("hip", 128, -30)), (5.38, BOX_R), (6.93, BOX_R),
             (6.94, ("head", 110, 220)), (8.0, ("head", 110, 220)), (8.01, ROSE_R), (9.03, ROSE_R), (9.04, HOLD_R)]

SHOTS = [0.0, 2.72, 4.0, 5.38, 6.94, 8.0, 9.04, 11.36, DUR]


def shot_index(t):
    return max(i for i, s in enumerate(SHOTS[:-1]) if s <= t)


def u_of(t, i):
    return clamp((t - SHOTS[i]) / (SHOTS[i + 1] - SHOTS[i]))


# ---------------------------------------------------------------- props
def rose(d, x, y, s, ang=0.25, wilt=0.0, a=255):
    L = 150 * s
    tx, ty = x + L * math.sin(ang), y - L * math.cos(ang)
    d.line([(x, y + 30 * s), (tx, ty)], fill=(40, 110, 50, a), width=max(2, int(7 * s)))
    d.ellipse([(x + tx) / 2 - 4 * s, (y + ty) / 2 - 10 * s, (x + tx) / 2 + 26 * s, (y + ty) / 2 + 6 * s], fill=(50, 130, 60, a))
    r = 34 * s * (1 - 0.25 * wilt)
    col = tuple(int(lerp(c, g, wilt)) for c, g in zip((214, 28, 58), (110, 46, 52)))
    d.ellipse([tx - r, ty - r * 1.1, tx + r, ty + r * 0.9], fill=col + (a,), outline=(110, 10, 30, a), width=max(1, int(3 * s)))
    d.arc([tx - r * 0.6, ty - r * 0.7, tx + r * 0.6, ty + r * 0.5], 180, 360, fill=(140, 10, 40, a), width=max(1, int(4 * s)))
    d.arc([tx - r * 0.3, ty - r * 0.4, tx + r * 0.3, ty + r * 0.2], 0, 180, fill=(140, 10, 40, a), width=max(1, int(3 * s)))


def gift_box(d, x, y, s):
    d.rectangle([x - 70 * s, y - 50 * s, x + 70 * s, y + 50 * s], fill=(180, 30, 60, 255), outline=(90, 10, 30, 255), width=3)
    d.rectangle([x - 10 * s, y - 50 * s, x + 10 * s, y + 50 * s], fill=(240, 200, 90, 255))
    d.ellipse([x - 34 * s, y - 80 * s, x - 2 * s, y - 50 * s], outline=(240, 200, 90, 255), width=max(2, int(8 * s)))
    d.ellipse([x + 2 * s, y - 80 * s, x + 34 * s, y - 50 * s], outline=(240, 200, 90, 255), width=max(2, int(8 * s)))


def card(d, x, y, s):
    d.polygon([(x - 60 * s, y - 80 * s), (x + 60 * s, y - 70 * s), (x + 56 * s, y + 80 * s), (x - 64 * s, y + 70 * s)], fill=(250, 236, 220, 255), outline=(120, 90, 80, 255))
    kh.heart(d, x - 2 * s, y - 6 * s, 2.0 * s, col=(220, 50, 80), a=255, outline=False)


def lamp_post(img, d, x, top, bottom, glow_a=150):
    d.rectangle([x - 9, top, x + 9, bottom], fill=(70, 74, 86, 255))
    d.line([(x, top), (x + 90, top - 10)], fill=(70, 74, 86, 255), width=10)
    d.polygon([(x + 66, top - 14), (x + 118, top - 14), (x + 110, top + 4), (x + 74, top + 4)], fill=(86, 90, 104, 255))
    kh.glow(img, (x - 120, top - 140, x + 320, top + 160), (255, 214, 150), glow_a, 40)
    cone = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(cone).polygon([(x + 76, top + 4), (x + 108, top + 4), (x + 420, bottom), (x - 240, bottom)], fill=(255, 210, 150, 38))
    img.alpha_composite(cone.filter(ImageFilter.GaussianBlur(30)))
    d.ellipse([x + 80, top - 6, x + 104, top + 8], fill=(255, 244, 210, 255))


def street(t, kind):
    if kind == "night":
        top, bot = (6, 10, 24), (24, 30, 52)
        env = "street"
    else:
        top, bot = {"dusk": ((110, 70, 80), (255, 170, 110)), "morning": ((150, 190, 230), (255, 236, 210))}[kind]
        env = "golden"
    g = m.GRAD_Y
    arr = np.array(top, np.float32) * (1 - g) + np.array(bot, np.float32) * g
    img = Image.fromarray(np.broadcast_to(arr, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(m.draw_env(t, env, bot))
    return img


def her(d, x, feet, h, t, pose="phone", a=255, rim=(255, 200, 150), turn=0.0):
    kh.person(d, x, feet, h, "girl", t, pose=pose, col=(50, 40, 50), rim=rim, a=a, walk=1.0)
    if turn > 0.01:   # her face turns a little towards him for a moment
        hr = 0.075 * h
        top = feet - h
        d.ellipse([x - hr * 0.5 + turn * hr * 0.4, top + hr * 0.7, x + hr * 0.1 + turn * hr * 0.6, top + hr * 1.3], fill=(150, 110, 100, int(200 * turn)))


# ---------------------------------------------------------------- shots
def f01(t):   # over his shoulder: she walks away down the sunset street, busy on her phone
    u = u_of(t, 0)
    img = street(t, "dusk")
    d = ImageDraw.Draw(img, "RGBA")
    fz = lerp(7.0, 13.0, u)
    sx, base = m.proj(0.5, 0, fz)
    hh = 1.62 * m.FOCAL / fz
    her(d, sx, base, hh, t, pose="phone")
    kh.phone_glow(img, sx - 0.02 * hh, base - hh + 0.36 * hh, max(0.3, hh / 1000))
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fg, "RGBA")
    kh.back_of_head(fd, 260 - 20 * u, 1200, 1.45)
    rose(fd, 470 - 20 * u, 1540, 1.6, ang=0.35)
    img.alpha_composite(fg.filter(ImageFilter.GaussianBlur(3)))
    kh.glow(img, (380, 520, 700, 840), (255, 220, 160), 70, 60)
    return kh.zoom_crop(img, lerp(1.0, 1.05, smooth(u)), 600, 960), "dusk"


def f02(t):   # front: hopeful, rose held up; on "देखे" the hope fades; an eye closes
    u = u_of(t, 1)
    img = street(t, "dusk")
    s = lerp(1.25, 1.35, smooth(u))
    ira = kh.Placed(t, 540, 760, s)
    img.alpha_composite(ira.layer())
    d = ImageDraw.Draw(img, "RGBA")
    hx_, hy_ = ira.hand("R")
    rose(d, hx_, hy_, 1.6, ang=lerp(0.2, 0.9, smooth((t - 3.5) / 0.4)), wilt=0.0)
    if 2.78 < t < 3.95:   # an eye that wants to see her turn, then closes
        q = back_out((t - 2.78) / 0.25) if t < 3.03 else 1.0
        close = smooth((t - 3.4) / 0.3)
        ex, ey = 820, 420
        if close < 0.95:
            hgt = 50 * q * (1 - close)
            d.ellipse([ex - 100 * q, ey - hgt, ex + 100 * q, ey + hgt], fill=(250, 250, 255, 220), outline=(30, 30, 40, 255), width=5)
            d.ellipse([ex - 30 * q, ey - min(30, hgt), ex + 30 * q, ey + min(30, hgt)], fill=(60, 40, 30, 255))
        d.arc([ex - 100 * q, ey - 30, ex + 100 * q, ey + 30], 0, 180, fill=(30, 30, 40, int(255 * close)), width=6)
    return kh.zoom_crop(img, 1.0), "dusk"


def f03(t):   # wide from behind him: she turns the corner into the sun and is gone; he lowers the rose
    u = u_of(t, 2)
    img = street(t, "dusk")
    d = ImageDraw.Draw(img, "RGBA")
    fz = lerp(13.0, 22.0, u)
    sx, base = m.proj(lerp(0.5, 2.2, smooth((u - 0.3) / 0.6)), 0, fz)
    hh = 1.62 * m.FOCAL / fz
    a = int(255 * (1 - smooth((u - 0.7) / 0.3)))
    if a > 0:
        her(d, sx, base, hh, t, pose="phone", a=a)
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fg, "RGBA")
    kh.back_of_head(fd, 540, 1380, 0.75)
    rose(fd, 700, lerp(1700, 1900, smooth((t - 4.3) / 0.6)), 0.9, ang=lerp(0.4, 2.4, smooth((t - 4.3) / 0.6)))
    img.alpha_composite(fg)
    kh.glow(img, (380, 520, 700, 840), (255, 220, 160), 90, 60)
    return kh.zoom_crop(img, lerp(1.0, 1.04, u), 540, 1000), "dusk"


def waiting_shot(t, i, kind, prop):
    """He waits at the lamp post; she passes behind him, busy, without looking."""
    u = u_of(t, i)
    img = street(t, kind)
    d = ImageDraw.Draw(img, "RGBA")
    lamp_post(img, d, 150, 520, 1660, glow_a=60 if kind != "night" else 170)
    d = ImageDraw.Draw(img, "RGBA")
    # her pass across the street behind him
    left_to_right = (i % 2 == 1)
    x = lerp(-120, 1200, u) if left_to_right else lerp(1200, -120, u)
    feet, hh = 1010, 430
    turn = 0.0
    if kind == "night":
        turn = math.sin(math.pi * clamp((t - 8.05) / 0.35)) * 0.8
    pose = "phone" if kind != "morning" else "stand"
    her(d, x, feet, hh, t, pose=pose, rim=(255, 210, 160) if kind != "night" else (150, 170, 210), turn=turn)
    if kind == "morning":   # with her friends, laughing
        for k, dx in enumerate((-150, 150)):
            kh.person(d, x + dx * (1 if left_to_right else -1), feet + 6, hh * (0.95 + 0.05 * k), "gf", t, col=(60, 50, 60), walk=1.0, ph=k + 1)
    if pose == "phone":
        kh.phone_glow(img, x - 0.02 * hh, feet - hh + 0.36 * hh, 0.6)
        d = ImageDraw.Draw(img, "RGBA")
    ira = kh.place_by_feet(t, 600, 1700, 0.95)
    img.alpha_composite(ira.layer())
    d = ImageDraw.Draw(img, "RGBA")
    if prop == "box":
        lx, ly = ira.hand("L")
        rx, ry = ira.hand("R")
        gift_box(d, (lx + rx) / 2, (ly + ry) / 2 - 20, 1.2)
    elif prop == "card":
        hx_, hy_ = ira.hand("R")
        card(d, hx_, hy_ - 60, 1.1)
    else:
        hx_, hy_ = ira.hand("R")
        rose(d, hx_, hy_, 1.2, ang=0.3)
    if kind == "night":
        img.alpha_composite(kh.rain_layer(t, 0.3, alpha=70))
    return kh.zoom_crop(img, lerp(1.0, 1.04, smooth(u)), 560, 1000), kind


def f04(t):
    return waiting_shot(t, 3, "morning", "box")


def f05(t):
    return waiting_shot(t, 4, "dusk", "card")


def f06(t):
    return waiting_shot(t, 5, "night", "rose")


def wall_scene(t, s, hx, hy, z_focus):
    img = street(t, "night")
    d = ImageDraw.Draw(img, "RGBA")
    lamp_post(img, d, 860, 300, 1500, glow_a=190)
    ira = kh.Placed(t, hx, hy, s)
    img.alpha_composite(ira.layer())
    d = ImageDraw.Draw(img, "RGBA")
    # the low brick wall he sits on hides his legs
    wy = ira.ws(540, 1440)[1]
    d.rectangle([0, wy, W, H], fill=(96, 62, 52, 255))
    for row, y in enumerate(range(int(wy), H, 46)):
        for x in range(-60 if row % 2 else -20, W, 120):
            d.rectangle([x + 3, y + 3, x + 116, y + 43], fill=(120, 76, 60, 255))
    d.rectangle([0, wy - 18, W, wy + 6], fill=(140, 120, 110, 255))
    # the pile of dried roses beside him: every day he waited
    pile_x = ira.ws(780, 1440)[0]
    for k in range(9):
        rose(d, pile_x + (k % 3) * 34 * s / 1.3 - 30, wy - 6 - (k // 3) * 6, 0.7 * s / 1.3, ang=1.2 + 0.15 * k, wilt=0.85)
    lx, ly = ira.hand("L")
    rx, ry = ira.hand("R")
    rose(d, (lx + rx) / 2, (ly + ry) / 2, 1.1 * s / 1.3, ang=0.15)
    return img, ira


def f07(t):   # "हम ही दीवाने हैं, दीवाने बने रहते हैं": on the wall under the lamp, smiling with wet eyes
    u = u_of(t, 6)
    s = lerp(1.35, 1.85, smooth(u))
    img, ira = wall_scene(t, s, 520, lerp(780, 700, u), 0)
    d = ImageDraw.Draw(img, "RGBA")
    for t0 in (9.44, 10.28):   # a glowing heart beats on each "दीवाने"
        dt = t - t0
        if 0 <= dt < 0.9:
            k = math.exp(-((dt - 0.12) / 0.1) ** 2) * 0.2
            a = int(230 * (1 - smooth((dt - 0.6) / 0.3)))
            x, y = ira.ws(540, 1060)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            kh.heart(ImageDraw.Draw(lay), 900, 420, 4.5 * (1 + k), col=(235, 50, 80), a=a, outline=False)
            img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(14)))
            img.alpha_composite(lay)
    img.alpha_composite(kh.rain_layer(t, 0.2, alpha=50))
    return img, "night"


def f08(t):   # "वाह वाह": pull back, alone under the lamp
    u = u_of(t, 7)
    s = lerp(1.0, 0.8, smooth(u))
    img, ira = wall_scene(t, s, 520, lerp(1000, 1060, u), 0)
    img.alpha_composite(kh.rain_layer(t, 0.25, alpha=55))
    return img, "night"


FUNCS = [f01, f02, f03, f04, f05, f06, f07, f08]


def grade(arr, kind):
    tint, de, lift = {"dusk": ((1.06, 0.98, 0.9), 0.05, 4), "morning": ((1.0, 1.02, 1.04), 0.05, 6),
                      "night": ((0.86, 0.94, 1.1), 0.3, 0)}[kind]
    lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
    out = arr * (1 - de) + lum[:, :, None] * de
    return out * np.array(tint, np.float32) + lift


def render_frame(t):
    rng = np.random.default_rng(int(t * 1000) + 41)
    i = shot_index(t)
    img, kind = FUNCS[i](t)
    arr = grade(np.asarray(img.convert("RGB")).astype(np.float32), kind)
    for c in SHOTS[1:-1]:   # soft dips on the montage cuts, a quick flash into the night
        dt = abs(t - c)
        if dt < 0.1:
            arr *= 0.55 + 0.45 * dt / 0.1
    arr *= m.VIGNETTE ** 0.8
    arr += rng.normal(0, 3.4, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    arr *= min(clamp(t / 0.3), clamp((DUR - t) / 0.9))
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    kh.draw_lyrics(out, t)
    return out.convert("RGB")


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
    proc.stdin.close()
    proc.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", SILENT, "-i", AUDIO, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={DUR - 0.6:.2f}:d=0.6", "-t", f"{DUR:.2f}",
                    "-movflags", "+faststart", OUT], check=True)
    os.remove(SILENT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
