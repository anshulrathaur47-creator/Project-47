"""Day 1 of the "100 Days of AI Editing" series: a 20s vertical explainer reel.

Scenes: DAY 1 stamp hook -> chat with Claude -> what it does (cut / auto captions /
color grade) -> today's setup checklist -> DAY 1 done stamp + follow CTA.
Music: assets/music/generated/masti-upbeat-120bpm.mp3 (CC0, ours); SFX from the
library are placed on the 0.5s beat grid by render.sh (built alongside).

Usage:
  python3 make_day1.py --frames 15,60,...   # preview PNGs only
  python3 make_day1.py                      # full silent render (_day1_silent.mp4)
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
DUR = 20.0
BEAT = 0.5  # 120 bpm
HERE = os.path.dirname(os.path.abspath(__file__))
SILENT = os.path.join(HERE, "_day1_silent.mp4")

NOTO = "/usr/share/fonts/truetype/noto"
F_BOLD = f"{NOTO}/NotoSans-Bold.ttf"
F_REG = f"{NOTO}/NotoSans-Regular.ttf"
_fonts = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(F_BOLD if bold else F_REG, size)
    return _fonts[key]


BG_TOP = (8, 12, 30)
BG_BOT = (26, 38, 74)
GOLD = (255, 200, 80)
SKY = (110, 200, 255)
WHITE = (246, 248, 255)
MUTED = (152, 170, 205)
GREEN = (110, 230, 150)
CORAL = (255, 110, 100)
USER_BLUE = (46, 110, 240)
CARD = (22, 30, 56)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def back(t):
    t = clamp(t)
    c = 1.8
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


# ---------- static layers ----------
def make_bg():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        f = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(lerp(a, b, f)) for a, b in zip(BG_TOP, BG_BOT)))
    rnd = np.random.default_rng(5)
    for _ in range(90):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        s = rnd.uniform(1, 2.6)
        a = int(rnd.uniform(30, 90))
        d.ellipse([x - s, y - s, x + s, y + s], fill=(200, 215, 255))
        d.ellipse([x - s, y - s, x + s, y + s], fill=(200 - a // 2, 210 - a // 2, 240 - a // 3))
    return img


BG = make_bg()
yy, xx = np.mgrid[0:H, 0:W]
_dd = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.5) / (H * 0.62)) ** 2)
VIG = np.clip(1.12 - _dd ** 2 * 0.8, 0.3, 1.0)[:, :, None].astype(np.float32)


def mini_scene(warm):
    """A tiny landscape 'video clip' used in the captions / grade demos."""
    w, h = 640, 380
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    if warm:
        sky1, sky2, sun, m1, m2, gnd = (255, 150, 90), (255, 210, 120), (255, 240, 200), (120, 70, 110), (80, 50, 90), (50, 36, 66)
    else:
        sky1, sky2, sun, m1, m2, gnd = (120, 126, 140), (160, 166, 178), (210, 212, 218), (96, 100, 112), (78, 82, 94), (64, 66, 76)
    for y in range(h):
        f = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(lerp(a, b, f)) for a, b in zip(sky1, sky2)))
    d.ellipse([w * 0.58, h * 0.18, w * 0.58 + 110, h * 0.18 + 110], fill=sun)
    d.polygon([(0, h * 0.78), (w * 0.38, h * 0.38), (w * 0.72, h * 0.78)], fill=m1)
    d.polygon([(w * 0.42, h * 0.78), (w * 0.74, h * 0.46), (w, h * 0.78)], fill=m2)
    d.rectangle([0, h * 0.76, w, h], fill=gnd)
    return img


CLIP_WARM = mini_scene(True)
CLIP_GREY = mini_scene(False)


# ---------- drawing helpers ----------
def text_c(d, y, s, size, fill=WHITE, bold=True, t=1.0, x=None, pop=False):
    if t <= 0:
        return
    f = font(size, bold)
    w = d.textlength(s, font=f)
    cx = (W - w) / 2 if x is None else x
    if pop:
        k = back(t)
        f2 = font(max(8, int(size * clamp(k, 0.05, 1.35))), bold)
        w2 = d.textlength(s, font=f2)
        cx2 = cx + w / 2 - w2 / 2
        a = clamp(t * 3)
        col = tuple(int(c * a + BG_TOP[i] * (1 - a)) for i, c in enumerate(fill))
        d.text((cx2 + 3, y + 5), s, font=f2, fill=(0, 0, 0))
        d.text((cx2, y), s, font=f2, fill=col)
    else:
        e = ease(t)
        col = tuple(int(c * e + BG_TOP[i] * (1 - e)) for i, c in enumerate(fill))
        d.text((cx + 2, y + (1 - e) * 30 + 4), s, font=font(size, bold), fill=(0, 0, 0))
        d.text((cx, y + (1 - e) * 30), s, font=f, fill=col)


def rrect(d, box, r, fill=None, outline=None, width=3):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def chip(d, cy, s, t, fg=GOLD, bg=(14, 18, 38)):
    if t <= 0:
        return
    k = back(t)
    f = font(int(40 * clamp(k, 0.2, 1.15)))
    w = d.textlength(s, font=f)
    pad = 34
    a = clamp(t * 3)
    rrect(d, [(W - w) / 2 - pad, cy - 36, (W + w) / 2 + pad, cy + 36], 36,
          fill=bg, outline=tuple(int(c * a) for c in fg), width=3)
    d.text(((W - w) / 2, cy - f.size * 0.72), s, font=f, fill=fg)


def vcheck(d, x, y, s, col, wdt=10, t=1.0):
    """Vector check mark, drawn progressively."""
    p1, p2, p3 = (x - s, y), (x - s * 0.25, y + s * 0.7), (x + s, y - s * 0.75)
    e = ease(t)
    if e < 0.45:
        f = e / 0.45
        q = (lerp(p1[0], p2[0], f), lerp(p1[1], p2[1], f))
        d.line([p1, q], fill=col, width=wdt)
    else:
        f = (e - 0.45) / 0.55
        q = (lerp(p2[0], p3[0], f), lerp(p2[1], p3[1], f))
        d.line([p1, p2], fill=col, width=wdt)
        d.line([p2, q], fill=col, width=wdt)


def sparkle(d, x, y, r, col, a=255):
    pts = []
    for k in range(8):
        ang = k * math.pi / 4
        rr = r if k % 2 == 0 else r * 0.32
        pts.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
    d.polygon(pts, fill=col + (a,) if len(col) == 3 else col)


def scissors(d, x, y, s, col):
    d.line([(x - s, y - s * 0.7), (x + s * 0.9, y + s * 0.55)], fill=col, width=9)
    d.line([(x - s, y + s * 0.7), (x + s * 0.9, y - s * 0.55)], fill=col, width=9)
    for sy in (-1, 1):
        d.ellipse([x - s - 26, y + sy * s * 0.7 - 13, x - s, y + sy * s * 0.7 + 13], outline=col, width=7)


def claude_logo(d, x, y, r, t=1.0):
    """Generic AI sparkle badge (not any company's logo)."""
    a = int(255 * clamp(t))
    d.ellipse([x - r, y - r, x + r, y + r], fill=(50, 44, 80), outline=GOLD, width=3)
    sparkle(d, x, y, r * 0.55, GOLD, a)


# ---------- scenes ----------
def s_hook(d, t, g):
    # DAY 1 slam
    if t > 0.03:
        k = clamp((t - 0.03) / 0.3)
        size = int(lerp(430, 185, ease(k)))
        f = font(size)
        s = "DAY 1"
        w = d.textlength(s, font=f)
        d.text(((W - w) / 2 + 4, 560 + (185 - size) * 0.4 + 6), s, font=f, fill=(0, 0, 0))
        d.text(((W - w) / 2, 560 + (185 - size) * 0.4), s, font=f, fill=GOLD)
        if 0.3 < t < 0.75:  # impact ring
            rr = lerp(120, 560, smooth((t - 0.3) / 0.45))
            al = int(200 * (1 - (t - 0.3) / 0.45))
            d.ellipse([W / 2 - rr, 700 - rr * 0.55, W / 2 + rr, 700 + rr * 0.55],
                      outline=(255, 220, 140, al), width=6)
    text_c(d, 820, "/ 100", 86, MUTED, t=(t - 0.5) / 0.3, pop=True)
    text_c(d, 1180, "AI se video editing", 70, WHITE, t=(t - 1.0) / 0.4)
    text_c(d, 1280, "100 din ka experiment", 48, MUTED, bold=False, t=(t - 1.25) / 0.4)
    chip(d, 1480, "AAJ: SETUP + PLAN", (t - 1.9) / 0.35)


def s_chat(d, t, g):
    text_c(d, 400, "Maine AI se seedha pooch liya...", 46, MUTED, bold=False, t=t / 0.4)
    # user bubble (typing 0.5-1.7, lands 1.75)
    ut = (t - 0.5) / 1.2
    if ut > 0:
        full = "Claude, meri reel edit karoge?"
        n = max(1, int(len(full) * clamp(ut)))
        s = full[:n]
        f = font(44)
        w = d.textlength(full, font=f)
        x1, y0 = W - 90, 560
        box = [x1 - w - 70, y0, x1, y0 + 110]
        rrect(d, box, 34, fill=USER_BLUE)
        d.polygon([(x1 - 26, y0 + 108), (x1, y0 + 108), (x1, y0 + 78)], fill=USER_BLUE)
        d.text((box[0] + 35, y0 + 28), s, font=f, fill=WHITE)
    # Claude typing dots then reply at 2.75
    if t > 2.0:
        claude_logo(d, 150, 890, 52, (t - 2.0) / 0.3)
    if 2.1 < t < 2.75:
        rrect(d, [230, 830, 440, 940], 34, fill=CARD, outline=(60, 70, 105), width=3)
        for k in range(3):
            ph = (t * 3 - k * 0.33) % 1
            r = 9 + 4 * math.sin(ph * math.pi)
            d.ellipse([290 + k * 55 - r, 885 - r, 290 + k * 55 + r, 885 + r], fill=MUTED)
    if t > 2.75:
        k = back((t - 2.75) / 0.3)
        lines = ["Haan! Cut, captions, SFX,", "color grade - sab ho jayega"]
        f = font(44)
        w = max(d.textlength(s, font=f) for s in lines)
        x0, y0 = 230, 830
        box = [x0, y0, x0 + (w + 150) * clamp(k, 0.3, 1), y0 + 230]
        rrect(d, box, 34, fill=CARD, outline=GOLD, width=3)
        if k > 0.7:
            for i, s in enumerate(lines):
                d.text((x0 + 40, y0 + 35 + i * 62), s, font=f, fill=WHITE)
            vcheck(d, x0 + w + 95, y0 + 115, 26, GREEN, 9, (t - 3.1) / 0.4)
    text_c(d, 1560, "Aur phir jo hua...", 52, SKY, t=(t - 3.6) / 0.5)


def filmstrip(d, t):
    """CUT demo: playhead, scissors, boring part drops, clips snap together."""
    y0, h = 900, 150
    xs, widths = 100, [250, 150, 180, 300]
    cols = [(70, 110, 180), (120, 80, 90), (110, 170, 130), (150, 100, 170)]
    labels = ["take 1", "boring", "take 2", "take 3"]
    cut_done = t > 1.25  # snap moment (local)
    shift = -170 * ease((t - 1.25) / 0.35)
    x = xs
    for i, (wd, col) in enumerate(zip(widths, cols)):
        dx = 0
        dy = 0
        rot_drop = 0
        if i == 1 and t > 0.5:  # boring piece falls away
            f = clamp((t - 0.5) / 0.9)
            dy = 900 * f * f
            dx = 40 * f
            col = (170, 70, 70)
        if i >= 2:
            dx = shift
        box = [x + dx, y0 + dy, x + wd + dx, y0 + h + dy]
        rrect(d, box, 14, fill=col, outline=(16, 20, 38), width=4)
        for sx in range(int(box[0]) + 14, int(box[2]) - 10, 34):  # sprockets
            d.rectangle([sx, box[1] + 8, sx + 14, box[1] + 20], fill=(16, 20, 38))
            d.rectangle([sx, box[3] - 20, sx + 14, box[3] - 8], fill=(16, 20, 38))
        f = font(30, False)
        d.text((box[0] + 20, box[1] + h / 2 - 16), labels[i], font=f, fill=(240, 240, 250))
        x += wd
    # playhead + scissors click at 0.5
    px = lerp(xs, xs + sum(widths), clamp(t / 1.9))
    d.line([(px, y0 - 60), (px, y0 + h + 40)], fill=GOLD, width=5)
    if 0.25 < t < 0.95:
        scissors(d, xs + widths[0], y0 - 90 + 25 * math.sin(t * 18), 44, WHITE)
    if 0.45 < t < 0.75:  # cut flash
        d.line([(xs + widths[0], y0 - 10), (xs + widths[0], y0 + h + 10)], fill=(255, 255, 255), width=9)
    if cut_done and t < 1.9:
        text_c(d, y0 + 240, "boring part? GONE", 46, CORAL, t=(t - 1.3) / 0.3, pop=True)


def s_montage(d, t, g):
    text_c(d, 260, "Claude ye sab karega:", 56, WHITE, t=t / 0.35)
    if t < 2.0:  # STEP 1 CUT (0-2)
        chip(d, 420, "STEP 1  -  SMART CUT", (t - 0.1) / 0.3)
        filmstrip(d, t - 0.3)
    elif t < 4.0:  # STEP 2 CAPTIONS (2-4)
        lt = t - 2.0
        chip(d, 420, "STEP 2  -  AUTO CAPTIONS", lt / 0.3)
        frame_box = [220, 640, 860, 1020]
        img = CLIP_WARM
        d._image.paste(img, (220, 640))
        rrect(d, frame_box, 8, outline=(16, 20, 38), width=6)
        words = [("Bolo,", WHITE, 48), ("captions", WHITE, 48), ("AUTO", GOLD, 60),
                 ("aa", WHITE, 48), ("jayenge", WHITE, 48)]
        total = sum(d.textlength(s, font=font(sz)) + 22 for s, _, sz in words) - 22
        x = (W - total) / 2
        for i, (s, col, sz) in enumerate(words):
            wt = (lt - 0.55 - i * 0.25) / 0.3
            if wt > 0:
                k = back(wt)
                f = font(max(8, int(sz * clamp(k, 0.1, 1.3))))
                d.text((x + 2, 1130 + (48 - sz) + 4), s, font=f, fill=(0, 0, 0))
                d.text((x, 1130 + (48 - sz)), s, font=f, fill=col)
            x += d.textlength(s, font=font(sz)) + 22
        text_c(d, 1290, "(Whisper: Hindi bhi samajhta hai)", 38, MUTED, bold=False, t=(lt - 1.5) / 0.4)
    else:  # STEP 3 GRADE (4-6)
        lt = t - 4.0
        chip(d, 420, "STEP 3  -  COLOR GRADE", lt / 0.3)
        wipe = int(640 * smooth((lt - 0.25) / 1.15))
        base = CLIP_GREY.copy()
        if wipe > 0:
            base.paste(CLIP_WARM.crop((0, 0, wipe, 380)), (0, 0))
        d._image.paste(base, (220, 640))
        rrect(d, [220, 640, 860, 1020], 8, outline=(16, 20, 38), width=6)
        if 0 < wipe < 640:
            d.line([(220 + wipe, 640), (220 + wipe, 1020)], fill=GOLD, width=6)
        text_c(d, 1110, "flat  -->  cinematic", 52, WHITE, t=(lt - 0.5) / 0.4)
        if lt > 2.25 - 2.0 + 2.0:  # sparkle at 12.25 global
            pass
        if lt > 2.2:
            for k, (sx, sy) in enumerate([(300, 700), (780, 720), (700, 960)]):
                ph = clamp((lt - 2.2 - k * 0.1) / 0.5)
                if 0 < ph < 1:
                    sparkle(d, sx, sy, 26 * math.sin(ph * math.pi) + 6, GOLD)
        text_c(d, 1290, "ek command me", 38, MUTED, bold=False, t=(lt - 1.6) / 0.4)


CHECKS = ["FFmpeg render pipeline", "Whisper - auto captions", "253 SFX + music library", "Remotion + Hyperframes"]


def s_checklist(d, t, g):
    text_c(d, 300, "Day 1 ka result:", 62, WHITE, t=t / 0.35)
    text_c(d, 395, "poora editing setup READY", 46, MUTED, bold=False, t=(t - 0.2) / 0.35)
    rrect(d, [120, 520, 960, 1480], 36, fill=CARD, outline=(60, 70, 105), width=3)
    for i, item in enumerate(CHECKS):
        it = (t - 0.5 - i * 0.5) / 0.35
        if it <= 0:
            continue
        y = 640 + i * 210
        k = back(it)
        r = 46 * clamp(k, 0.1, 1.2)
        d.ellipse([205 - r, y - r, 205 + r, y + r], fill=(30, 60, 50), outline=GREEN, width=4)
        vcheck(d, 205, y + 4, 22, GREEN, 9, it * 1.4)
        a = clamp(it * 2)
        col = tuple(int(c * a + CARD[j] * (1 - a)) for j, c in enumerate(WHITE))
        d.text((300, y - 28), item, font=font(45), fill=col)
    chip(d, 1600, "SAB FREE TOOLS", (t - 2.7) / 0.35, fg=GREEN)


def s_outro(d, t, g):
    # rubber stamp
    if t > 0.0:
        k = clamp((t) / 0.28)
        sc = lerp(2.3, 1.0, ease(k))
        shake = math.sin(t * 40) * 6 * max(0.0, 0.6 - t) if t > 0.28 else 0
        stamp = Image.new("RGBA", (700, 330), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp)
        rrect(sd, [10, 10, 690, 320], 26, outline=GOLD, width=10)
        f = font(130)
        s = "DAY 1"
        w = sd.textlength(s, font=f)
        sd.text(((700 - w) / 2 - 60, 75), s, font=f, fill=GOLD)
        sd.ellipse([530, 90, 670, 230], outline=GREEN, width=8)
        vcheck(sd, 600, 165, 38, GREEN, 11, (t - 0.25) / 0.3)
        sw, sh = int(700 * sc), int(330 * sc)
        stamp = stamp.resize((sw, sh), Image.BILINEAR).rotate(-7, expand=True, resample=Image.BICUBIC)
        a = clamp(t * 4)
        if a < 1:
            al = stamp.getchannel("A").point(lambda v: int(v * a))
            stamp.putalpha(al)
        d._image.alpha_composite(stamp.convert("RGBA"),
                                 (int(W / 2 - stamp.width / 2 + shake), int(640 - stamp.height / 2)))
    text_c(d, 1030, "COMPLETE", 66, WHITE, t=(t - 0.5) / 0.3, pop=True)
    text_c(d, 1220, "Kal Day 2:", 48, MUTED, bold=False, t=(t - 0.9) / 0.4)
    text_c(d, 1290, "pehli raw clip ka FULL edit", 56, SKY, t=(t - 1.05) / 0.4)
    # follow pill pulsing
    ft = (t - 1.5) / 0.35
    if ft > 0:
        pulse = 1 + 0.035 * math.sin(g * 6.28 * 2)
        f = font(int(46 * clamp(back(ft), 0.2, 1.1) * pulse))
        s = "FOLLOW  -  100 DAYS SERIES"
        w = d.textlength(s, font=f)
        rrect(d, [(W - w) / 2 - 44, 1500, (W + w) / 2 + 44, 1600], 50, fill=GOLD)
        d.text(((W - w) / 2, 1550 - f.size * 0.72), s, font=f, fill=(20, 16, 6))


SCENES = [(2.5, s_hook), (4.5, s_chat), (6.0, s_montage), (3.5, s_checklist), (3.5, s_outro)]
FADE = 0.3


def render_frame(i, rng):
    g = i / FPS
    img = BG.copy().convert("RGBA")
    d = ImageDraw.Draw(img)
    d._image = img
    k = 1.0
    start = 0.0
    for dur, fn in SCENES:
        if start <= g < start + dur or (fn is SCENES[-1][1] and g >= start):
            lt = g - start
            fn(d, lt, g)
            k = min(1.0, lt / FADE, max(0.0, (dur - lt)) / FADE if fn is not SCENES[-1][1] else 1.0)
            break
        start += dur
    # series chip + progress bar (always)
    if g > 2.5:
        f = font(30)
        s = "100 DAYS  -  AI EDITING  -  DAY 01"
        w = d.textlength(s, font=f)
        rrect(d, [(W - w) / 2 - 28, 60, (W + w) / 2 + 28, 118], 30, fill=(12, 16, 34), outline=(60, 70, 105), width=2)
        d.text(((W - w) / 2, 72), s, font=f, fill=MUTED)
    d.rectangle([0, 0, W, 10], fill=(24, 32, 60))
    d.rectangle([0, 0, int(W * g / DUR), 10], fill=GOLD)

    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    arr *= VIG
    arr += rng.normal(0, 2.5, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if k < 1.0:
        out = Image.blend(Image.new("RGB", (W, H), BG_TOP), out, max(0.0, k))
    fade_g = min(clamp(g / 0.3), clamp((DUR - g) / 0.5))
    if fade_g < 1:
        out = Image.blend(Image.new("RGB", (W, H)), out, fade_g)
    return out


def main():
    rng = np.random.default_rng(3)
    if "--frames" in sys.argv:
        for i in [int(v) for v in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            render_frame(i, rng).save(os.path.join(HERE, f"_prev_{i:04d}.png"))
        return
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-maxrate", "9M", "-bufsize", "18M", "-pix_fmt", "yuv420p", SILENT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for i in range(n):
        proc.stdin.write(render_frame(i, rng).tobytes())
        if i % 120 == 0:
            print(f"frame {i}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"wrote {SILENT}")


if __name__ == "__main__":
    main()
