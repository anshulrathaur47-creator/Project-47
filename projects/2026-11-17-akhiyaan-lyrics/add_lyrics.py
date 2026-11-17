"""Add glowing, animated lyrics to the Akhiyaan reel (song 0:13 to 0:40 = clip 0 to 27 s).

Input:  raw-videos/reel_akhiyaan_0013_0040.mp4 (never modified)
Output: akhiyaan_lyrics.mp4 next to this script (original audio copied untouched)

Word timings: Whisper (given the lyric sheet as a hint) aligned per line, checked against
where the vocals pause in the audio. Lyrics sit in the top band (y ~170 to 340), which is
clear of both characters in every shot and below the app's top bar.

Usage: python3 add_lyrics.py              # full render
       python3 add_lyrics.py --frames 30,90  # preview PNGs only
"""
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "raw-videos", "reel_akhiyaan_0013_0040.mp4")
OUT = os.path.join(HERE, "akhiyaan_lyrics.mp4")
W, H, FPS, DUR = 1080, 1920, 30, 27.0
BEAT = 60 / 143.6
Y_TEXT = 248          # centre of the lyric row
MAX_W = 960           # the row shrinks to fit this width
F_HI = "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf"

PINK, GOLD, LAV, ROSE, WHITE = (255, 120, 190), (255, 205, 110), (200, 160, 255), (255, 80, 140), (255, 255, 255)

# (words with start times, style, glow colour, key-word colours, end time)
CHUNKS = [
    ([("असी", 0.30), ("नींदर", 0.80)], "soft", PINK, {"नींदर": LAV}, 1.38),
    ([("चैन", 1.40), ("गवा", 2.10), ("बैठे", 2.76)], "soft", PINK, {"चैन": GOLD}, 3.62),
    ([("असी", 3.70), ("ना-ना", 4.18)], "flip", GOLD, {"ना-ना": GOLD}, 4.86),
    ([("करदे", 4.88), ("ला", 5.76), ("बैठे", 6.18)], "flip", GOLD, {}, 7.0),
    ([("असी", 7.05), ("नींदर", 7.58)], "wave", LAV, {"नींदर": LAV}, 8.24),
    ([("चैन", 8.26), ("गवा", 8.96), ("बैठे", 9.70), ("वे", 10.40)], "wave", LAV, {"चैन": GOLD}, 10.66),
    ([("असी", 10.70), ("ना-ना", 11.04)], "zoom", PINK, {"ना-ना": PINK}, 11.78),
    ([("करदे", 11.80), ("ला", 12.56), ("बैठे", 13.04)], "zoom", PINK, {}, 13.92),
    ([("असी", 13.96), ("तकदे-तकदे", 14.38)], "stare", GOLD, {"तकदे-तकदे": GOLD}, 16.18),
    ([("की", 16.20), ("तक्कियां?", 16.48)], "stare", GOLD, {"तक्कियां?": PINK}, 17.70),
    ([("तौबा", 17.78), ("तेरियां...", 18.40)], "trail", ROSE, {"तौबा": ROSE}, 19.75),
    ([("तौबा", 21.90), ("तेरियां", 22.40), ("ए", 23.10), ("अखियाँ", 23.40)], "heart", ROSE,
     {"तौबा": ROSE, "अखियाँ": GOLD}, 24.25),
    ([("तौबा", 24.30), ("तेरियां", 25.20), ("ए", 26.00), ("अखियाँ", 26.30)], "heart", ROSE,
     {"तौबा": ROSE, "अखियाँ": GOLD}, 27.0),
]


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
    c = 1.8
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


_fonts, _sprites = {}, {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(F_HI, size, layout_engine=ImageFont.Layout.RAQM)
    return _fonts[size]


def sprite(word, size, col, glow):
    """Neon word: dark halo for contrast on bright shots, wide soft glow, tight glow, bright core."""
    key = (word, size, col, glow)
    if key in _sprites:
        return _sprites[key]
    f = font(size)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    x0, _, x1, _ = probe.textbbox((0, 0), word, font=f)
    pad = int(size * 0.6)
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (x1 - x0 + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    org = (pad - x0, pad)
    for fill, sw, blur in (((30, 0, 30, 190), size // 10, 0.13), (glow + (200,), size // 14, 0.30),
                           (glow + (255,), size // 24, 0.07)):
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).text(org, word, font=f, fill=fill, stroke_width=sw, stroke_fill=fill)
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(size * blur)))
    core = tuple(int(c + (255 - c) * 0.6) for c in col)
    ImageDraw.Draw(img).text(org, word, font=f, fill=core + (255,), stroke_width=max(1, size // 45),
                             stroke_fill=glow + (255,))
    _sprites[key] = (img, probe.textlength(word, font=f))
    return _sprites[key]


def shine(img, frac):
    """Diagonal light sweep across a word."""
    if not (-0.3 < frac < 1.3):
        return img
    arr = np.asarray(img).astype(np.float32)
    h_, w_ = arr.shape[:2]
    yy, xx = np.mgrid[0:h_, 0:w_]
    k = np.exp(-(((xx + yy * 0.45) / w_ - frac) / 0.07) ** 2) * (arr[:, :, 3] / 255.0) * 0.75
    arr[:, :, :3] += (255 - arr[:, :, :3]) * k[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def alpha_mul(img, a):
    if a >= 0.999:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return out


def paste_c(frame, img, cx, cy):
    frame.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def heart(d, x, y, s, col):
    pts = []
    for i in range(30):
        a = math.pi * i / 15 - math.pi
        pts.append((x + 16 * math.sin(a) ** 3 * s,
                    y - (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) * s))
    d.polygon(pts, fill=col)


def star(d, x, y, r, col):
    d.polygon([(x, y - r * 2), (x + r * 0.45, y - r * 0.45), (x + r * 2, y), (x + r * 0.45, y + r * 0.45),
               (x, y + r * 2), (x - r * 0.45, y + r * 0.45), (x - r * 2, y), (x - r * 0.45, y - r * 0.45)], fill=col)


def draw_chunk(frame, t, idx, words, style, glow, colours, end):
    if t < words[0][1] - 0.12 or t > end + 0.05:
        return
    size = 118
    while True:  # shrink until the row fits
        sprites = [sprite(w, size, colours.get(w, WHITE), glow) for w, _ in words]
        space = size * 0.32
        total = sum(a for _, a in sprites) + space * (len(words) - 1)
        if total <= MAX_W or size <= 60:
            break
        size -= 4
    x = 540 - total / 2
    exit_k = smooth((t - (end - 0.22)) / 0.22)
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i, ((w, wt), (spr, adv)) in enumerate(zip(words, sprites)):
        wx = x + adv / 2
        x += adv + space
        p = (t - wt) / 0.32
        if p <= 0:
            continue
        img, a, sx, sy, ang, dx, dy = spr, clamp(p * 2), 1.0, 1.0, 0.0, 0.0, 0.0
        if style == "soft":        # floats up out of a blur
            sx = sy = lerp(0.82, 1.0, ease_out(p))
            dy = (1 - ease_out(p)) * 36 + math.sin(t * 2 + i) * 4
            if p < 1:
                img = Image.blend(spr.filter(ImageFilter.GaussianBlur(10 * (1 - p))), spr, ease_out(p))
        elif style == "flip":      # 3D flip in, punch on the beat
            sy = clamp(back_out(p), 0.03, 1.25)
            sx = lerp(1.35, 1.0, ease_out(p))
            ang = (1 - ease_out(p)) * -10
        elif style == "wave":      # rides a gentle wave
            dy = (1 - ease_out(p)) * -50 + math.sin(t * 4 + i * 1.1) * 9
            sx = sy = lerp(1.3, 1.0, ease_out(p))
            ang = math.sin(t * 3 + i) * 2.5
        elif style == "zoom":      # rushes in from big, with a light trail
            k = ease_out(clamp((t - wt) / 0.2))
            sx = sy = lerp(2.3, 1.0, k)
            a = clamp(k * 2.5)
            if k < 1:
                trail = alpha_mul(spr.resize((int(spr.width * (sx + 0.4)), int(spr.height * (sy + 0.4)))), 0.25 * (1 - k))
                paste_c(overlay, trail, wx, Y_TEXT)
        elif style == "stare":     # slow push while staring, tiny shake on the beat
            sx = sy = lerp(0.9, 1.08, clamp((t - wt) / 2.0))
            if p < 1:
                sy *= clamp(back_out(p), 0.05, 1.2)
            bt = math.exp(-((t - round(t / BEAT) * BEAT) / 0.05) ** 2)
            dx = math.sin(t * 60) * 4 * bt
        elif style == "trail":     # slides in from the right with a streak, dots blink
            k = ease_out(clamp((t - wt) / 0.35))
            dx = (1 - k) * 420
            a = clamp(k * 2)
            if k < 1:
                d.line([(wx + dx + 60, Y_TEXT), (wx + dx + 60 + 380 * (1 - k), Y_TEXT)],
                       fill=glow + (int(180 * (1 - k)),), width=10)
        elif style == "heart":     # pops with overshoot, the key word beats like a heart
            sx = sy = clamp(back_out(p), 0.05, 1.3)
            if w == "अखियाँ":
                beat = abs(math.sin(math.pi * (t - wt) / BEAT))
                sx = sy = sx * (1 + 0.08 * beat)
                rr = random.Random(idx * 10 + i)
                for k in range(9):  # hearts and sparkles burst out
                    age = (t - wt) - k * 0.08
                    if 0 < age < 1.2:
                        ang_ = rr.uniform(-2.6, -0.5)
                        dist = 40 + age * rr.uniform(120, 220)
                        hx, hy = wx + math.cos(ang_) * dist, Y_TEXT + math.sin(ang_) * dist * 0.6
                        al = int(240 * (1 - age / 1.2))
                        if k % 2:
                            heart(d, hx, hy, 1.4, (255, 90, 150, al))
                        else:
                            star(d, hx, hy, 6, (255, 230, 160, al))
        a *= 1 - exit_k
        if a <= 0.01:
            continue
        beat = math.exp(-((t - round(t / BEAT) * BEAT) / 0.07) ** 2)
        sx, sy = sx * (1 + 0.025 * beat), sy * (1 + 0.025 * beat)
        img = shine(img, ((t - wt) * 0.9 + i * 0.12) % 2.2 - 0.3)
        if abs(sx - 1) > 1e-3 or abs(sy - 1) > 1e-3:
            img = img.resize((max(1, int(img.width * sx)), max(1, int(img.height * sy))), Image.BILINEAR)
        if abs(ang) > 0.2:
            img = img.rotate(ang, expand=True, resample=Image.BICUBIC)
        paste_c(overlay, alpha_mul(img, a), wx + dx, Y_TEXT + dy)
    if style == "trail" and t > words[-1][1] + 0.3:  # blinking dots after "तेरियां..."
        pass
    # drifting glitter around the line
    rr = random.Random(idx)
    for k in range(10):
        ph = rr.uniform(0, 6.28)
        px_ = rr.uniform(540 - total / 2 - 40, 540 + total / 2 + 40)
        py_ = Y_TEXT + rr.uniform(-80, 80) - ((t * 25 + k * 13) % 60)
        tw = max(0.0, math.sin(t * 5 + ph))
        al = int(200 * tw * (1 - exit_k) * clamp((t - words[0][1]) / 0.3))
        if al > 5:
            star(d, px_, py_, 2 + 3 * tw, glow + (al,))
    frame.alpha_composite(overlay)


def render(frame_rgb, t):
    frame = Image.frombytes("RGB", (W, H), frame_rgb).convert("RGBA")
    for idx, (words, style, glow, colours, end) in enumerate(CHUNKS):
        draw_chunk(frame, t, idx, words, style, glow, colours, end)
    return frame.convert("RGB")


def frames_from_source():
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        buf = proc.stdout.read(n)
        if len(buf) < n:
            break
        yield buf
    proc.wait()


def main():
    if "--frames" in sys.argv:
        want = [int(v) for v in sys.argv[sys.argv.index("--frames") + 1].split(",")]
        for i in want:
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{i / FPS:.3f}", "-i", SRC, "-frames:v", "1",
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            render(raw, i / FPS).save(os.path.join(HERE, f"_preview_{i:04d}.png"))
        return
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", SRC, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                            "-preset", "medium", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", OUT],
                           stdin=subprocess.PIPE)
    for i, buf in enumerate(frames_from_source()):
        enc.stdin.write(render(buf, i / FPS).tobytes())
        if i % 120 == 0:
            print(f"frame {i}", flush=True)
    enc.stdin.close()
    enc.wait()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
