"""Render a moody 9:16 lyric reel with a hook for the Hindi audio in assets/.

Lyrics are revealed word by word, each with a short Hinglish line saying what
it means. A hook at the top plays on the song's idea: people came to measure
the pain, found a smile, and left.

Usage: python3 make_lyric_reel.py  ->  writes lyric_reel.mp4 next to this file.
"""
import math
import os
import random
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "assets", "ReelAudio-98423.mp3")
OUT = os.path.join(HERE, "lyric_reel.mp4")
SILENT = os.path.join(HERE, "_lyric_video_only.mp4")
DURATION = 18.78

NOTO = "/usr/share/fonts/truetype/noto"
F_DEV = f"{NOTO}/NotoSerifDevanagari-Bold.ttf"
F_HOOK = f"{NOTO}/NotoSerif-BoldItalic.ttf"
F_MEAN = f"{NOTO}/NotoSerif-Italic.ttf"
F_SMALL = f"{NOTO}/NotoSans-Regular.ttf"
_fonts = {}


def font(path, size):
    if (path, size) not in _fonts:
        kw = {"layout_engine": ImageFont.Layout.RAQM} if "Devanagari" in path else {}
        _fonts[(path, size)] = ImageFont.truetype(path, size, **kw)
    return _fonts[(path, size)]


# (start, end, lyric, what it means)
# Timings estimated from the song's loudness pattern: two long sung lines,
# then four short ones.
LINES = [
    (0.14, 4.85, "वो लेके आए थे पैमाना नापने मेरे दर्द यहाँ",
     "sab dekhne aaye the main kitna toota hoon"),
    (4.85, 9.55, "देख के मुझको हँसता हुआ वो लौट गए फिर जाने कहाँ",
     "par meri muskurahat dekh ke khud hi laut gaye"),
    (9.55, 11.80, "हम भी अपने शहजादे हैं",
     "hum apni duniya ke khud raja hain"),
    (11.80, 13.90, "हमें ख्वाब वाब नहीं आते हैं",
     "ab sapne dekhna chhod diya"),
    (13.90, 16.15, "हम भूल गए हैं सारा कुछ",
     "jo dard tha, sab bhula diya"),
    (16.15, 18.78, "अब यही हमारी बातें हैं",
     "bas... yahi hai ab hamari kahani"),
]

# Hook captions at the top of the frame
HOOKS = [
    (0.0, 4.85, ["Unhe laga tha", "main toot jaunga..."]),
    (4.85, 9.55, ["...par unhe", "meri hansi mili"]),
    (9.55, 16.15, ["Dard dikhana", "humne seekha hi nahi"]),
    (16.15, DURATION, ["Relate kiya?", "Save kar lo"]),
]

COLD = np.array([8, 12, 28], float)
COLD2 = np.array([30, 44, 80], float)
WARM = np.array([26, 14, 10], float)
WARM2 = np.array([92, 58, 28], float)
GOLD = (255, 205, 120)
WHITE = (250, 247, 240)
MUTED = (190, 200, 220)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------- background: AI-generated anime artwork + light effects ----------
ART = Image.open(os.path.join(HERE, "assets", "anime_bg.png")).convert("RGB")
# upscale once with a margin so the slow push-in never shows edges
ART_BIG = ART.resize((int(W * 1.08), int(H * 1.08)), Image.LANCZOS)
ART_ARR = np.asarray(ART_BIG).astype(np.float32)
WARM_TINT = np.array([1.18, 0.98, 0.78], np.float32)

rnd = random.Random(11)
PARTICLES = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(2, 6), rnd.uniform(25, 70),
              rnd.uniform(0, 6.28)) for _ in range(45)]

# Vignette mask (darken the edges)
yy, xx = np.mgrid[0:H, 0:W]
_d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.5) / (H * 0.62)) ** 2)
VIGNETTE = np.clip(1.15 - _d ** 2 * 0.85, 0.3, 1.0)[:, :, None].astype(np.float32)


def warmth_at(t):
    """0 = cold moonlight (pain), 1 = warm gold (pride) from the 'shehzaade' line on."""
    return smooth((t - 9.2) / 1.6) * (1 - 0.5 * smooth((t - 16.2) / 2.0))


def background(t):
    # slow Ken Burns push-in on the artwork
    z = 1.0 + 0.07 * (t / DURATION)
    bw, bh = ART_BIG.size
    cw, ch = W * 1.08 / z, H * 1.08 / z
    x0, y0 = (bw - cw) / 2, (bh - ch) * 0.6
    crop = ART_BIG.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)
    arr = np.asarray(crop).astype(np.float32)
    w = warmth_at(t)
    if w > 0:
        arr = arr * (1 + (WARM_TINT - 1) * 0.65 * w)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    # floating dust / ember particles
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    pc = (255, 210, 150) if w > 0.5 else (190, 215, 255)
    for x, y, s, sp, ph in PARTICLES:
        py = (y - t * sp) % H
        px = x + 20 * math.sin(t * 0.6 + ph)
        a = int(80 + 50 * math.sin(t * 2 + ph))
        ld.ellipse([px - s, py - s, px + s, py + s], fill=pc + (a,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(2.5)))
    return img


# ---------- text ----------
def wrap_words(words, f, max_w, d):
    lines, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if cur and d.textlength(trial, font=f) > max_w:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def shadow_text(layer, xy, s, f, fill, alpha):
    """Draw text with a soft dark shadow onto an RGBA layer."""
    if alpha <= 0:
        return
    x0, y0, x1, y1 = ImageDraw.Draw(layer).textbbox(xy, s, font=f)
    pad = 24
    bx, by = int(x0) - pad, int(y0) - pad
    sh = Image.new("RGBA", (int(x1 - x0) + 2 * pad + 8, int(y1 - y0) + 2 * pad + 8), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0] + 3 - bx, xy[1] + 5 - by), s, font=f,
                            fill=(0, 0, 0, int(230 * alpha)))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    layer.alpha_composite(sh, (max(bx, 0), max(by, 0)), (max(-bx, 0), max(-by, 0)))
    ImageDraw.Draw(layer).text(xy, s, font=f, fill=fill + (int(255 * alpha),))


def draw_lyric(layer, t):
    d = ImageDraw.Draw(layer)
    for start, end, lyric, meaning in LINES:
        if not (start - 0.2 <= t < end + 0.05):
            continue
        out = 1 - smooth((t - (end - 0.25)) / 0.25)  # fade out at line end
        words = lyric.split()
        fd = font(F_DEV, 82 if len(words) <= 6 else 74)
        rows = wrap_words(words, fd, 920, d)
        line_h = 128
        top = 860 - (len(rows) * line_h) / 2
        sung = end - start
        idx = 0
        for r, row in enumerate(rows):
            row_w = d.textlength(" ".join(row), font=fd)
            x = (W - row_w) / 2
            y = top + r * line_h
            for w in row:
                # each word appears in turn across ~85% of the line's duration
                wt = start + sung * 0.85 * idx / len(words)
                a = ease((t - wt) / 0.35) * out
                lift = (1 - ease((t - wt) / 0.35)) * 25
                shadow_text(layer, (x, y + lift), w, fd, WHITE, a)
                x += d.textlength(w + " ", font=fd)
                idx += 1
        # meaning line
        size = 48
        while d.textlength(meaning, font=font(F_HOOK, size)) > 940 and size > 30:
            size -= 2  # shrink long meanings so they never run off the frame
        fm = font(F_HOOK, size)
        ma = ease((t - start - sung * 0.45) / 0.6) * out
        mw = d.textlength(meaning, font=fm)
        my = top + len(rows) * line_h + 30
        shadow_text(layer, ((W - mw) / 2, my), meaning, fm, GOLD, ma)


def draw_hook(layer, t):
    d = ImageDraw.Draw(layer)
    for start, end, rows in HOOKS:
        if not (start <= t < end):
            continue
        a = ease((t - start) / 0.35) * (1 - smooth((t - (end - 0.25)) / 0.25))
        if start == 0.0:
            a = 1.0 if t < end - 0.25 else a  # first frame must already show the hook
        # translucent pill behind the hook
        fh = font(F_HOOK, 68)
        widths = [d.textlength(s, font=fh) for s in rows]
        bw = max(widths) + 90
        y0 = 430
        pill = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle(
            [(W - bw) / 2, y0, (W + bw) / 2, y0 + 70 + 95 * len(rows)], radius=40,
            fill=(0, 0, 0, int(120 * a)))
        layer.alpha_composite(pill)
        for i, s in enumerate(rows):
            col = WHITE if i == 0 else GOLD
            shadow_text(layer, ((W - widths[i]) / 2, y0 + 25 + i * 95), s, fh, col, a)


def finish(img, t, rng):
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    arr *= VIGNETTE
    arr += rng.normal(0, 3.5, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)  # light film grain
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def render():
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "9M", "-bufsize", "18M", "-pix_fmt", "yuv420p", SILENT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    rng = np.random.default_rng(1)
    n = int(math.ceil(DURATION * FPS))
    for i in range(n):
        t = i / FPS
        img = background(t)
        draw_lyric(img, t)
        draw_hook(img, t)
        frame = finish(img, t, rng)
        # fade out to black over the last 0.6s
        k = min(1.0, (DURATION - t) / 0.6)
        if k < 1:
            frame = Image.blend(Image.new("RGB", (W, H)), frame, max(0.0, k))
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()


def mux():
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", SILENT, "-i", AUDIO,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-af", f"afade=t=out:st={DURATION - 0.6:.2f}:d=0.6",
                    "-shortest", "-movflags", "+faststart", OUT], check=True)
    os.remove(SILENT)


if __name__ == "__main__":
    render()
    mux()
    print(f"Wrote {OUT}")
