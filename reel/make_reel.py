"""Render a vertical (9:16) explainer reel: "How air travel works around the world".

Frames are drawn with Pillow and piped straight into ffmpeg.
Usage: python3 make_reel.py  ->  writes aviation_reel.mp4 next to this file.
"""
import math
import os
import random
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "aviation_reel.mp4")
SILENT = os.path.join(HERE, "_video_only.mp4")

FONT_DIR = "/usr/share/fonts/truetype"
BOLD = f"{FONT_DIR}/dejavu/DejaVuSans-Bold.ttf"
REG = f"{FONT_DIR}/dejavu/DejaVuSans.ttf"
_fonts = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(BOLD if bold else REG, size)
    return _fonts[key]


# Palette
BG_TOP = (6, 14, 36)
BG_BOT = (14, 40, 82)
WHITE = (245, 248, 255)
SKY = (110, 200, 255)
GOLD = (255, 196, 64)
MUTED = (150, 170, 205)
CORAL = (255, 110, 100)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


# ---------- static background: gradient + dotted "world" grid ----------
def make_background():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(lerp(a, b, t)) for a, b in zip(BG_TOP, BG_BOT)))
    rnd = random.Random(7)
    # A loose dotted globe in the middle of the frame
    cx, cy, r = W / 2, H * 0.52, 470
    for lat in range(-80, 81, 6):
        for lon in range(-180, 180, 6):
            la, lo = math.radians(lat), math.radians(lon)
            x3 = math.cos(la) * math.sin(lo)
            z3 = math.cos(la) * math.cos(lo)
            if z3 < 0:
                continue
            # crude "landmass" noise so the dots look like continents
            n = math.sin(lo * 2.1 + la * 1.3) + math.cos(lo * 1.2 - la * 2.7) + rnd.random() * 0.6
            if n < 0.55:
                continue
            x = cx + r * x3
            y = cy - r * math.sin(la)
            s = 2 + 2 * z3
            d.ellipse([x - s, y - s, x + s, y + s], fill=(40, 80, 140))
    return img


BG = make_background()

# Moving "flights" drawn on top of the background
rnd = random.Random(42)
FLIGHTS = []
for _ in range(38):
    a = (rnd.uniform(80, W - 80), rnd.uniform(H * 0.25, H * 0.8))
    b = (rnd.uniform(80, W - 80), rnd.uniform(H * 0.25, H * 0.8))
    FLIGHTS.append((a, b, rnd.uniform(0, 1), rnd.uniform(0.08, 0.18)))


def arc_point(a, b, t, bend=0.25):
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    cx, cy = mx - dy * bend, my + dx * bend
    x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * cx + t ** 2 * b[0]
    y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * cy + t ** 2 * b[1]
    return x, y


def draw_traffic(d, time, alpha=1.0):
    col = tuple(int(c * alpha) for c in (90, 170, 240))
    head = tuple(int(c * alpha) for c in GOLD)
    for a, b, off, speed in FLIGHTS:
        t = (off + time * speed) % 1.0
        pts = [arc_point(a, b, max(0, t - k * 0.012)) for k in range(14)]
        d.line(pts, fill=col, width=3)
        x, y = pts[0]
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=head)


# ---------- text helpers ----------
def text_center(d, y, s, size, fill=WHITE, bold=True, t=1.0):
    """Draw centred text that slides up and fades in as t goes 0 -> 1."""
    e = ease(t)
    f = font(size, bold)
    w = d.textlength(s, font=f)
    col = tuple(int(c * e + BG_TOP[i] * (1 - e)) for i, c in enumerate(fill))
    d.text(((W - w) / 2, y + (1 - e) * 40), s, font=f, fill=col)


def pill(d, x0, y0, x1, y1, fill, outline=None):
    d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) // 2, fill=fill, outline=outline, width=3)


def plane(d, x, y, size=70, angle=0, fill=WHITE):
    """A simple vector airplane pointing right, rotated by angle (radians)."""
    shape = [(1.0, 0), (0.55, 0.08), (0.15, 0.55), (0.0, 0.55), (0.2, 0.08),
             (-0.55, 0.08), (-0.75, 0.3), (-0.85, 0.3), (-0.75, 0), (-0.85, -0.3),
             (-0.75, -0.3), (-0.55, -0.08), (0.2, -0.08), (0.0, -0.55), (0.15, -0.55),
             (0.55, -0.08)]
    ca, sa = math.cos(angle), math.sin(angle)
    pts = [(x + size * (px * ca - py * sa), y + size * (px * sa + py * ca)) for px, py in shape]
    d.polygon(pts, fill=fill)


def progress_bar(d, time, total):
    d.rectangle([0, 0, W, 10], fill=(20, 40, 70))
    d.rectangle([0, 0, int(W * time / total), 10], fill=GOLD)


# ---------- scenes ----------
# Each scene: (duration_seconds, draw_fn(draw, local_t_seconds, global_t_seconds))

def s_hook(d, t, g):
    draw_traffic(d, g)
    text_center(d, 330, "RIGHT NOW", 64, SKY, t=t / 0.5)
    text_center(d, 420, "10,000+ planes", 108, WHITE, t=(t - 0.3) / 0.6)
    text_center(d, 550, "are flying above us", 64, WHITE, bold=False, t=(t - 0.6) / 0.6)
    text_center(d, 1560, "So how does it all work?", 60, GOLD, t=(t - 1.6) / 0.6)
    text_center(d, 1640, "without crashing into each other", 44, MUTED, bold=False, t=(t - 2.0) / 0.6)


def s_numbers(d, t, g):
    draw_traffic(d, g, 0.35)
    text_center(d, 300, "EVERY SINGLE DAY", 60, SKY, t=t / 0.5)
    n = int(100000 * ease(t / 2.0))
    text_center(d, 420, f"~{n:,}", 150, GOLD, t=t / 0.4)
    text_center(d, 600, "flights take off", 64, WHITE, t=(t - 0.4) / 0.5)
    text_center(d, 1150, "~5 billion", 110, WHITE, t=(t - 1.6) / 0.6)
    text_center(d, 1290, "passengers every year", 60, MUTED, bold=False, t=(t - 1.9) / 0.6)


def s_rules(d, t, g):
    text_center(d, 280, "WHO MAKES THE RULES?", 60, SKY, t=t / 0.5)
    e = ease((t - 0.3) / 0.7)
    pill(d, 190, 430, 890, 640, (20, 60, 120), SKY)
    text_center(d, 470, "ICAO", 120, WHITE, t=(t - 0.3) / 0.7)
    text_center(d, 680, "UN aviation agency", 50, MUTED, bold=False, t=(t - 0.6) / 0.6)
    rows = [("193", "countries follow one rulebook"),
            ("English", "is the global language of the sky"),
            ("Same", "signs, signals & procedures everywhere")]
    for i, (big, small) in enumerate(rows):
        tt = (t - 1.3 - i * 0.55) / 0.5
        y = 900 + i * 230
        text_center(d, y, big, 90, GOLD, t=tt)
        text_center(d, y + 105, small, 44, WHITE, bold=False, t=tt)
    _ = e


def s_airways(d, t, g):
    text_center(d, 260, "HIGHWAYS IN THE SKY", 64, SKY, t=t / 0.5)
    text_center(d, 360, "Planes don't fly anywhere they like", 44, MUTED, bold=False, t=(t - 0.3) / 0.5)
    # Airway network: waypoints joined by fixed routes
    nodes = [(170, 820), (420, 700), (700, 760), (920, 650), (300, 1080),
             (560, 1000), (840, 1080), (200, 1350), (520, 1300), (900, 1380)]
    edges = [(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (2, 5), (3, 6), (4, 5), (5, 6),
             (4, 7), (5, 8), (6, 9), (7, 8), (8, 9)]
    grow = ease((t - 0.5) / 1.2)
    for a, b in edges:
        (x0, y0), (x1, y1) = nodes[a], nodes[b]
        d.line([(x0, y0), (lerp(x0, x1, grow), lerp(y0, y1, grow))], fill=(70, 130, 200), width=5)
    for x, y in nodes:
        r = 14 * grow
        d.polygon([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], fill=SKY)
    # Planes travelling along a few routes
    routes = [[0, 1, 2, 3], [7, 8, 5, 6, 3], [4, 5, 2, 3], [9, 8, 7]]
    for k, route in enumerate(routes):
        if t < 1.6:
            break
        p = ((t - 1.6) * 0.22 + k * 0.23) % 1.0
        seg = p * (len(route) - 1)
        i = int(seg)
        f = seg - i
        (x0, y0), (x1, y1) = nodes[route[i]], nodes[route[i + 1]]
        plane(d, lerp(x0, x1, f), lerp(y0, y1, f), 40, math.atan2(y1 - y0, x1 - x0), GOLD)
    text_center(d, 1560, "Fixed routes + waypoints", 58, WHITE, t=(t - 1.8) / 0.6)
    text_center(d, 1640, "like lanes on a motorway", 44, MUTED, bold=False, t=(t - 2.1) / 0.6)


def s_journey(d, t, g):
    text_center(d, 230, "ONE FLIGHT, MANY HANDS", 60, SKY, t=t / 0.5)
    steps = [("GATE", "Ground control: pushback & taxi"),
             ("TOWER", "Clears the runway for take-off"),
             ("DEPARTURE", "Guides the climb out of the airport"),
             ("CENTRE", "Watches the cruise at ~35,000 ft"),
             ("APPROACH", "Lines planes up to descend"),
             ("TOWER", "Clears landing, then taxi to gate")]
    for i, (big, small) in enumerate(steps):
        tt = (t - 0.4 - i * 0.45) / 0.45
        if tt <= 0:
            continue
        e = ease(tt)
        y = 400 + i * 205
        x = 110 + (1 - e) * -200
        d.ellipse([x, y, x + 90, y + 90], fill=GOLD if i in (0, 5) else SKY)
        d.text((x + 45, y + 45), str(i + 1), font=font(46), fill=BG_TOP, anchor="mm")
        d.text((x + 130, y - 2), big, font=font(56), fill=WHITE)
        d.text((x + 130, y + 62), small, font=font(36, False), fill=MUTED)
        if i < len(steps) - 1:
            d.line([(x + 45, y + 95), (x + 45, y + 200)], fill=(60, 100, 160), width=4)
    text_center(d, 1680, "Handed off controller to controller", 46, GOLD, t=(t - 3.4) / 0.6)


def s_separation(d, t, g):
    text_center(d, 260, "THE INVISIBLE BUBBLE", 64, SKY, t=t / 0.5)
    text_center(d, 360, "Every plane gets its own space", 44, MUTED, bold=False, t=(t - 0.3) / 0.5)
    e = ease((t - 0.6) / 0.8)
    # Horizontal separation
    y = 760
    x0, x1 = 230, lerp(230, 850, e)
    plane(d, 230, y, 70, 0, WHITE)
    plane(d, x1, y, 70, 0, GOLD)
    if e > 0.2:
        d.line([(310, y + 110), (x1 - 80, y + 110)], fill=SKY, width=4)
        text_center(d, y + 140, "~5 nautical miles apart", 50, WHITE, t=(t - 1.0) / 0.5)
    # Vertical separation
    e2 = ease((t - 2.0) / 0.8)
    yA, yB = 1180, lerp(1180, 1430, e2)
    plane(d, 540, yA, 70, 0, WHITE)
    plane(d, 540, yB, 70, 0, GOLD)
    if e2 > 0.2:
        d.line([(700, yA), (700, yB)], fill=SKY, width=4)
        d.text((730, (yA + yB) / 2 - 30), "1,000 ft", font=font(52), fill=WHITE)
        text_center(d, 1560, "...or 1,000 ft above / below", 50, WHITE, t=(t - 2.4) / 0.5)


def s_tracking(d, t, g):
    text_center(d, 260, "HOW ARE THEY TRACKED?", 60, SKY, t=t / 0.5)
    cx, cy = W / 2, 900
    # Radar scope
    for r in (120, 240, 360):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(50, 120, 90), width=3)
    ang = g * 2.2
    d.line([(cx, cy), (cx + 360 * math.cos(ang), cy + 360 * math.sin(ang))], fill=(90, 230, 150), width=5)
    blips = [(0.6, 200), (2.1, 300), (3.3, 150), (4.6, 260), (5.4, 330)]
    for a, r in blips:
        diff = (ang - a) % (2 * math.pi)
        glow = max(0.25, 1 - diff / 3)
        c = tuple(int(v * glow) for v in (120, 255, 170))
        bx, by = cx + r * math.cos(a), cy + r * math.sin(a)
        d.ellipse([bx - 11, by - 11, bx + 11, by + 11], fill=c)
    text_center(d, 1340, "RADAR on the ground", 54, WHITE, t=(t - 0.6) / 0.5)
    text_center(d, 1440, "+ ADS-B: planes broadcast their", 46, MUTED, bold=False, t=(t - 1.4) / 0.5)
    text_center(d, 1505, "own GPS position every second", 46, MUTED, bold=False, t=(t - 1.6) / 0.5)
    text_center(d, 1640, "Over oceans? Satellites take over", 48, GOLD, t=(t - 2.4) / 0.5)


def s_hubs(d, t, g):
    text_center(d, 260, "HUBS & SPOKES", 64, SKY, t=t / 0.5)
    text_center(d, 360, "Airlines funnel flights through giant hubs", 40, MUTED, bold=False, t=(t - 0.3) / 0.5)
    hubs = [("Atlanta", 230, 800), ("Dubai", 760, 760), ("London", 500, 620),
            ("Delhi", 860, 1050), ("Singapore", 640, 1300), ("Tokyo", 260, 1180)]
    rr = random.Random(3)
    grow = ease((t - 0.6) / 1.2)
    for name, x, y in hubs:
        for k in range(7):
            a = rr.uniform(0, 2 * math.pi)
            L = rr.uniform(80, 170) * grow
            d.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], fill=(70, 130, 200), width=3)
    for name, x, y in hubs:
        pulse = 22 + 6 * math.sin(g * 5)
        d.ellipse([x - pulse, y - pulse, x + pulse, y + pulse], fill=GOLD)
        d.text((x, y + 50), name, font=font(40), fill=WHITE, anchor="mt")
    text_center(d, 1560, "Fly in, connect, fly out", 58, WHITE, t=(t - 1.8) / 0.6)
    text_center(d, 1640, "Reach almost any city in 1-2 stops", 44, MUTED, bold=False, t=(t - 2.1) / 0.6)


def s_outro(d, t, g):
    draw_traffic(d, g, 0.6)
    p = ease(t / 2.0)
    plane(d, lerp(-150, W + 150, p), lerp(1100, 700, p), 110, -0.4, GOLD)
    text_center(d, 360, "Next time you fly...", 66, SKY, t=t / 0.5)
    text_center(d, 470, "thousands of people", 84, WHITE, t=(t - 0.5) / 0.6)
    text_center(d, 580, "are guiding your plane", 70, WHITE, bold=False, t=(t - 0.8) / 0.6)
    text_center(d, 1420, "SAFEST WAY TO TRAVEL", 66, GOLD, t=(t - 1.6) / 0.6)
    text_center(d, 1580, "Follow for more ✈", 54, WHITE, t=(t - 2.4) / 0.6)


SCENES = [(4.5, s_hook), (4.5, s_numbers), (5.0, s_rules), (5.0, s_airways),
          (5.5, s_journey), (4.8, s_separation), (4.6, s_tracking), (4.6, s_hubs), (4.5, s_outro)]
TOTAL = sum(s[0] for s in SCENES)
FADE = 0.35  # seconds of fade-through-dark between scenes


def render():
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", SILENT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frame_no = 0
    start = 0.0
    for dur, fn in SCENES:
        n = int(round(dur * FPS))
        for i in range(n):
            lt = i / FPS
            g = (frame_no) / FPS
            img = BG.copy()
            d = ImageDraw.Draw(img)
            fn(d, lt, g)
            progress_bar(d, g, TOTAL)
            # fade in/out at scene edges
            k = min(1.0, lt / FADE, (dur - lt) / FADE)
            if k < 1.0:
                img = Image.blend(Image.new("RGB", (W, H), BG_TOP), img, max(0.0, k))
            proc.stdin.write(img.tobytes())
            frame_no += 1
        start += dur
    proc.stdin.close()
    proc.wait()
    return frame_no / FPS


def add_music(duration):
    """Synthesize a soft ambient pad (no external assets) and mux it with the video."""
    d = f"{duration:.2f}"
    chord = "+".join(
        f"{amp}*sin(2*PI*{f}*t)" for f, amp in
        [(110, 0.25), (164.81, 0.18), (220, 0.15), (261.63, 0.10), (329.63, 0.08)])
    expr = f"({chord})*(0.75+0.25*sin(2*PI*0.25*t))"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", SILENT,
           "-f", "lavfi", "-i", f"aevalsrc={expr}:s=44100:d={d}",
           "-filter_complex",
           f"[1:a]lowpass=f=1200,aecho=0.8:0.7:120|240:0.3|0.2,volume=0.6,"
           f"afade=t=in:d=1.5,afade=t=out:st={duration - 2:.2f}:d=2[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
           "-shortest", "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True)
    os.remove(SILENT)


if __name__ == "__main__":
    dur = render()
    add_music(dur)
    print(f"Wrote {OUT} ({dur:.1f}s)")
