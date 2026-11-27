"""Jamshedpur: CM Hemant Soren and MLA Kalpana Soren pay tribute to Arjun Munda's late mother.
News reel for The Media Times .live, built from the reporter's WhatsApp clips.

Video: vertical clips fill the frame; landscape clips and the photo sit in a panel over a soft blurred copy of
themselves. Python adds a slow push-in, dissolves and dips (calm cuts for a condolence story) and the
channel graphics: logo bug, place/date tag, ticker, lower thirds, byte subtitles, opening sting, end cards.
Audio: natural sound under the b-roll, the CM's byte at full level (it keeps running under its b-roll covers),
a soft piano bed, loudness-normalised at the end.

Usage: python3 make_news.py [--frames 30,300,...]
"""
import argparse
import os
import subprocess
import wave

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RAW = os.path.join(ROOT, "raw-videos", "2026-11-27-munda-shraddhanjali")
LOGO = os.path.join(ROOT, "brand-kit", "logo-the-media-times-live.jpg")
PHOTO = os.path.join(RAW, "IMG-20261127-WA0035.jpg")
SFX = os.path.join(ROOT, "assets", "sfx", "generated")
BED = os.path.join(ROOT, "assets", "music", "generated", "sad-piano-70bpm.mp3")
W, H, FPS, SR = 1080, 1920, 30, 48000
RED = (200, 16, 30)
DARK = (22, 10, 12)
GOLD = (255, 214, 110)
WHITE = (255, 255, 255)
FONT_B = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
PANEL_CY = 760          # vertical centre of the landscape panel
DISSOLVE = 9            # frames
DIP = 7                 # frames each side


def src(n):
    return os.path.join(RAW, f"VID-20261127-WA00{n}.mp4")


# ------------------------------------------------------------------ edit decision list
# kind: video | still | logo | endlogo
# layout: full (vertical clip) or panel with crop (x_centre, y0, w, h) in source pixels
# trans: cut | dissolve | dip (into this shot)
# audio: ("nat", gain) or ("byte", src_in) for clip 40, or None
def V(clip, t_in, dur, trans="dissolve", zoom=1.05, crop=None, audio=("nat", 0.45), sup=None, note=""):
    return dict(kind="video", clip=clip, t_in=t_in, dur=dur, trans=trans, zoom=zoom, crop=crop, audio=audio, sup=sup, note=note)


def S(rect, dur, trans="dissolve", zoom=1.08, audio=None, sup=None, note=""):
    return dict(kind="still", rect=rect, dur=dur, trans=trans, zoom=zoom, audio=audio, sup=sup, note=note)


HALL = lambda cx: (cx, 0, 574, 478)          # clip 39 (848x478) -> 1080x900 panel
BYTE = lambda cx: (cx, 0, 456, 380)          # clip 40 (848x478), top part, keeps the mic forest low
PORTRAIT = (300, 150, 600, 500)              # photo: the late mother's garlanded portrait
WIDE_PHOTO = (800, 0, 1599, 899)             # photo: whole frame

SHOTS = [
    dict(kind="logo", dur=1.3, trans="cut", audio=None, sup=None, note="logo sting"),
    S(WIDE_PHOTO, 4.9, trans="dissolve", zoom=1.10, sup=None, note="HOOK: bowing before the portrait + headline"),
    # arrival
    V("42", 47.0, 3.0, sup=0, audio=("nat", 0.22), note="helicopter in the sky"),
    V("42", 63.8, 3.4, sup=0, audio=("nat", 0.22), note="helicopter lands, red carpet"),
    V("43", 4.0, 3.0, sup=1, note="police at the residence gate"),
    V("44", 21.0, 3.0, sup=1, note="residence courtyard, cars"),
    V("39", 17.0, 4.5, crop=HALL(540), sup=2, note="CM and Kalpana Soren walk in, folded hands"),
    # tribute
    V("41", 0.0, 1.5, sup=3, note="portrait on the table"),
    V("39", 24.5, 3.0, crop=HALL(470), sup=3, note="at the portrait"),
    V("39", 36.5, 3.5, crop=HALL(390), sup=4, note="CM offers flowers"),
    V("39", 43.0, 3.5, crop=HALL(430), sup=4, note="CM bows, hands folded"),
    V("39", 50.5, 5.0, crop=HALL(420), sup=5, note="Kalpana Soren offers flowers"),
    V("39", 62.5, 4.0, crop=HALL(400), sup=6, note="MLA offers flowers"),
    V("41", 14.5, 4.5, sup=7, note="with the family, crowd and cameras"),
    # byte (audio from clip 40 throughout; b-roll covers the jump cuts)
    V("40", 32.9, 4.9, trans="dip", zoom=1.03, crop=BYTE(300), audio=("byte", 32.9), sup=8, note="BYTE B1a"),
    S(PORTRAIT, 2.5, trans="cut", zoom=1.06, audio=("byte", 40.3), note="  cover: portrait"),
    S(WIDE_PHOTO, 3.5, trans="cut", zoom=1.06, audio=("byte", 52.3), note="  cover: the bow"),
    V("40", 55.8, 6.0, trans="cut", zoom=1.03, crop=BYTE(360), audio=("byte", 55.8), sup=9, note="BYTE B2"),
    V("44", 25.5, 2.5, trans="cut", audio=("byte", 63.2), note="  cover: residence"),
    V("40", 65.7, 4.9, trans="cut", zoom=1.03, crop=BYTE(310), audio=("byte", 65.7), note="BYTE B3a"),
    V("39", 56.0, 2.0, trans="cut", crop=HALL(420), audio=("byte", 76.9), note="  cover: flowers"),
    V("40", 86.9, 2.6, trans="cut", zoom=1.03, crop=BYTE(300), audio=("byte", 86.9), note="BYTE B4"),
    # close
    V("44", 47.5, 6.0, trans="dip", sup=None, note="convoy, folded hands from the car"),
    S(PORTRAIT, 4.0, trans="dip", zoom=1.10, note="tribute card"),
    dict(kind="endlogo", dur=3.2, trans="dissolve", audio=None, sup=None, note="logo end card"),
]

starts = []
_t = 0.0
for s in SHOTS:
    starts.append(_t)
    _t += s["dur"]
TOTAL = _t
NFRAMES = int(round(TOTAL * FPS))
IDX_HOOK, IDX_BYTE0, IDX_TRIB, IDX_END = 1, 14, 23, 24

# lower thirds keyed by shot "sup": (line1 on red, line2 on white)
SUP_TEXT = {
    0: ("मुख्यमंत्री का जमशेदपुर दौरा", "अर्जुन मुंडा के परिवार से मिलने पहुंचे"),
    1: ("टेल्को, घोड़ाबांधा", "पूर्व मुख्यमंत्री अर्जुन मुंडा का आवास"),
    2: ("हेमंत सोरेन और कल्पना सोरेन", "मुख्यमंत्री और गांडेय विधायक पहुंचे"),
    3: ("स्वर्गीय सायरा मुंडा", "अर्जुन मुंडा की माँ का इसी सप्ताह निधन"),
    4: ("मुख्यमंत्री ने दी श्रद्धांजलि", "तस्वीर पर फूल माला चढ़ाकर किया नमन"),
    5: ("विधायक कल्पना सोरेन", "माँ की तस्वीर पर अर्पित किए श्रद्धा सुमन"),
    6: ("पूर्वी सिंहभूम के विधायक", "सभी ने अर्पित किए श्रद्धा सुमन"),
    7: ("परिवार से मिले मुख्यमंत्री", "दुख की घड़ी में बढ़ाया हौसला"),
    8: ("हेमंत सोरेन", "मुख्यमंत्री, झारखंड"),
    9: ("हेमंत सोरेन", "मुख्यमंत्री, झारखंड"),
}


def sup_spans():
    """Merge consecutive shots with the same sup into one lower-third span."""
    spans = []
    for i, s in enumerate(SHOTS):
        k = s.get("sup")
        if k is None:
            continue
        a, b = starts[i], starts[i] + s["dur"]
        if spans and spans[-1][2] == k and abs(spans[-1][1] - a) < 1e-6:
            spans[-1][1] = b
        else:
            spans.append([a, b, k])
    out = []
    for a, b, k in spans:
        if k in (8, 9):
            b = min(b, a + 4.0)       # name strap: first 4 s of the byte face only
        out.append((a + 0.25, b - 0.1, k))
    return out


# byte subtitles: in clip-40 source seconds (Whisper word timings, cleaned up by hand)
BYTE_LINES = [
    (32.95, 37.8, "आप सब को पता है, कुछ दिन पहले"),
    (40.35, 42.8, "अर्जुन मुंडा जी की माता जी का निधन हुआ"),
    (52.4, 55.45, "राजनीतिक लोग तो हैं,"),
    (55.5, 61.8, "पर सामाजिक, व्यक्तिगत संबंध भी साथ चलते हैं"),
    (63.25, 65.4, "और उसी बाबत आज हम लोग"),
    (65.4, 67.9, "माता जी को श्रद्धांजलि देने"),
    (68.1, 70.6, "घोड़ाबांधा आए हैं"),
    (76.95, 78.9, "हम लोगों ने श्रद्धांजलि भी दी"),
    (86.95, 89.45, "भगवान उनकी आत्मा को शांति दे"),
]


def byte_subs():
    subs = []
    for i, s in enumerate(SHOTS):
        au = s.get("audio")
        if not au or au[0] != "byte":
            continue
        a_in, a_out = au[1], au[1] + s["dur"]
        for x, y, txt in BYTE_LINES:
            lo, hi = max(x, a_in), min(y, a_out)
            if hi - lo > 0.3:
                subs.append((starts[i] + lo - a_in, starts[i] + hi - a_in, txt))
    return subs


TICKER = ("जमशेदपुर: मुख्यमंत्री हेमंत सोरेन पूर्व मुख्यमंत्री अर्जुन मुंडा के टेल्को स्थित घोड़ाबांधा आवास पहुंचे   |   "
          "स्वर्गीय सायरा मुंडा की तस्वीर पर फूल माला चढ़ाकर दी श्रद्धांजलि   |   गांडेय विधायक कल्पना सोरेन भी रहीं साथ   |   "
          "पूर्वी सिंहभूम के सभी विधायकों ने अर्पित किए श्रद्धा सुमन   |   परिवार से मिलकर दुख की घड़ी में बढ़ाया हौसला   |   ")


# ------------------------------------------------------------------ graphics helpers
def font(size, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT_R, size, layout_engine=ImageFont.Layout.RAQM)


def text_box(text, size, fg, bg, pad=(26, 10), bold=True, radius=8, minw=0):
    f = font(size, bold)
    l, t, r, b = f.getbbox(text)
    w, h = max(minw, r - l + pad[0] * 2), int(size * 1.45) + pad[1] * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=bg)
    d.text((pad[0] - l, pad[1] + (int(size * 1.45) - size) // 2 - int(size * 0.18)), text, font=f, fill=fg)
    return im


def stroked_text(text, size, fill=WHITE, stroke=(0, 0, 0), sw=5, maxw=990):
    f = font(size)
    while f.getlength(text) > maxw and size > 30:
        size -= 2
        f = font(size)
    l, t, r, b = f.getbbox(text, stroke_width=sw)
    im = Image.new("RGBA", (r - l + 4, int(size * 1.7)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - l, int(size * 0.12)), text, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)
    return im


def to_np(im):
    return np.asarray(im, dtype=np.float32)


def paste(frame, layer, x, y, alpha=1.0):
    h, w = layer.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0 or alpha <= 0:
        return
    L = layer[y0 - y:y1 - y, x0 - x:x1 - x]
    a = L[..., 3:4] / 255.0 * alpha
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - a) + L[..., :3] * a


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def logo_rgba(size, radius):
    im = Image.open(LOGO).convert("RGB").resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), radius, fill=255)
    out = im.convert("RGBA")
    out.putalpha(m)
    # soft shadow + thin white rim
    pad = 18
    canvas = Image.new("RGBA", (size + pad * 2, size + pad * 2), (0, 0, 0, 0))
    sh = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 6, pad + size, pad + size + 6), radius, fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    canvas.paste((0, 0, 0, 255), (0, 0), sh)
    canvas.alpha_composite(out, (pad, pad))
    ImageDraw.Draw(canvas).rounded_rectangle((pad, pad, pad + size - 1, pad + size - 1), radius, outline=(255, 255, 255, 230), width=3)
    return canvas


class Graphics:
    def __init__(self):
        self.bug = to_np(logo_rgba(150, 18))
        self.tag = to_np(text_box("जमशेदपुर", 40, WHITE, RED + (255,)))
        self.date = to_np(text_box("27 नवंबर 2026", 34, WHITE, DARK + (225,)))
        f = font(36)
        unit = int(f.getlength(TICKER))
        strip = Image.new("RGBA", (unit * 2, 70), DARK + (238,))
        d = ImageDraw.Draw(strip)
        for k in range(2):
            d.text((k * unit, 4), TICKER, font=f, fill=WHITE)
        self.ticker, self.ticker_unit = to_np(strip), unit
        self.ticker_label = to_np(text_box("ताज़ा ख़बर", 36, WHITE, RED + (255,), pad=(22, 4), radius=0))
        self.supers = []
        for a, b, k in sup_spans():
            l1, l2 = SUP_TEXT[k]
            self.supers.append((a, b, to_np(text_box(l1, 48, WHITE, RED + (255,))), to_np(text_box(l2, 38, DARK, WHITE + (245,)))))
        self.subs = [(a, b, to_np(stroked_text(t, 52))) for a, b, t in byte_subs()]
        # opening headline (over the photo)
        self.h_kick = to_np(text_box("श्रद्धांजलि", 46, WHITE, RED + (255,)))
        self.h_1 = to_np(stroked_text("अर्जुन मुंडा के आवास पहुंचे", 64, sw=6))
        self.h_2 = to_np(stroked_text("मुख्यमंत्री हेमंत सोरेन", 92, fill=GOLD, sw=8))
        self.h_3 = to_np(text_box("स्वर्गीय सायरा मुंडा को दी श्रद्धांजलि", 42, DARK, WHITE + (245,)))
        # tribute card
        self.t_1 = to_np(stroked_text("विनम्र श्रद्धांजलि", 96, fill=WHITE, sw=7))
        self.t_2 = to_np(text_box("स्वर्गीय सायरा मुंडा", 50, WHITE, RED + (255,)))
        # logo sting and end card
        self.logo_big = logo_rgba(560, 46)
        self.e_1 = to_np(stroked_text("ऐसी ही ख़बरों के लिए", 56, sw=5))
        self.e_2 = to_np(text_box("फॉलो करें", 54, WHITE, RED + (255,)))
        # gradient for subtitles over the byte panel
        g = np.zeros((300, W, 4), np.float32)
        g[..., 3] = np.linspace(0, 200, 300)[:, None]
        self.grad = g

    def chrome(self, fr, t):
        """Logo bug, tag, ticker: on every shot except the sting and the end card."""
        paste(fr, self.bug, W - self.bug.shape[1] - 30, 112)
        paste(fr, self.tag, 44, 150)
        paste(fr, self.date, 44 + self.tag.shape[1] + 10, 154)
        ty = 1530
        off = int((t * 140) % self.ticker_unit)
        paste(fr, self.ticker[:, off:off + W], 0, ty)
        paste(fr, self.ticker_label, 0, ty + 1)

    def draw(self, fr, t, shot_i):
        kind = SHOTS[shot_i]["kind"]
        if kind in ("logo", "endlogo"):
            return
        self.chrome(fr, t)
        if shot_i == IDX_HOOK:
            u = t - starts[IDX_HOOK]
            k0, k1, k2, k3 = (ease_out((u - d) / 0.4) for d in (0.25, 0.45, 0.7, 1.0))
            y = 1110
            paste(fr, self.h_kick, (W - self.h_kick.shape[1]) // 2, int(y + 30 * (1 - k0)), k0)
            paste(fr, self.h_1, (W - self.h_1.shape[1]) // 2, int(y + 95 + 30 * (1 - k1)), k1)
            paste(fr, self.h_2, (W - self.h_2.shape[1]) // 2, int(y + 190 + 30 * (1 - k2)), k2)
            paste(fr, self.h_3, (W - self.h_3.shape[1]) // 2, int(y + 335 + 30 * (1 - k3)), k3)
            return
        if shot_i == IDX_TRIB:
            u = t - starts[IDX_TRIB]
            k1, k2 = ease_out((u - 0.4) / 0.6), ease_out((u - 0.9) / 0.6)
            paste(fr, self.t_1, (W - self.t_1.shape[1]) // 2, int(1190 + 30 * (1 - k1)), k1)
            paste(fr, self.t_2, (W - self.t_2.shape[1]) // 2, int(1340 + 30 * (1 - k2)), k2)
            return
        for a, b, l1, l2 in self.supers:
            if a <= t < b:
                k = ease_out((t - a) / 0.35) * (1 - ease_out((t - (b - 0.3)) / 0.3))
                x = int(-760 * (1 - k)) + 44
                paste(fr, l1, x, 1300, k)
                paste(fr, l2, x, 1300 + l1.shape[0] + 6, k)
        active = [(a, b, im) for a, b, im in self.subs if a <= t < b]
        if active:
            paste(fr, self.grad, 0, 1210 - 300 + 40, 0.9)
        for a, b, im in active:
            k = min(1.0, (t - a) / 0.12, (b - t) / 0.12)
            paste(fr, im, (W - im.shape[1]) // 2, 1110, k)


# ------------------------------------------------------------------ picture
def push_in(img, z):
    if z <= 1.001:
        return img
    h, w = img.shape[:2]
    cw, ch = int(w / z), int(h / z)
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    return cv2.resize(img[y0:y0 + ch, x0:x0 + cw], (w, h), interpolation=cv2.INTER_LINEAR)


def soft_bg(panel):
    """Cheap heavy blur: fill 1080x1920 from the panel through a tiny thumbnail, then darken."""
    ph, pw = panel.shape[:2]
    s = H / ph
    fill = cv2.resize(panel, (int(pw * s), H), interpolation=cv2.INTER_AREA)
    x0 = (fill.shape[1] - W) // 2
    fill = fill[:, x0:x0 + W]
    tiny = cv2.resize(fill, (27, 48), interpolation=cv2.INTER_AREA)
    bg = cv2.resize(tiny, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    return bg * 0.42


def compose_panel(panel, z):
    """Panel (1080 x ph) with push-in, over its own blurred copy, with thin red rules."""
    ph = panel.shape[0]
    fr = soft_bg(panel)
    p = push_in(panel, z).astype(np.float32)
    y0 = PANEL_CY - ph // 2
    fr[y0:y0 + ph] = p
    fr[y0 - 6:y0, :] = RED
    fr[y0 + ph:y0 + ph + 6, :] = RED
    return fr


def video_reader(shot, n):
    clip, t_in = shot["clip"], shot["t_in"]
    if shot["crop"]:
        cx, y0, cw, ch = shot["crop"]
        x0 = int(min(max(0, cx - cw / 2), 848 - cw))
        ph = int(round(W * ch / cw / 2) * 2)
        vf = f"crop={cw}:{ch}:{x0}:{y0},scale={W}:{ph}:flags=lanczos,unsharp=5:5:0.7"
        oh = ph
    else:
        vf = f"scale={W}:{H}:flags=lanczos,unsharp=5:5:0.6"
        oh = H
    vf += ",eq=contrast=1.05:saturation=1.08,fps=30"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t_in}", "-i", src(clip), "-t", f"{n / FPS + 0.3}", "-vf", vf, "-an",
                         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    last = None
    for _ in range(n):
        buf = p.stdout.read(W * oh * 3)
        if len(buf) == W * oh * 3:
            last = np.frombuffer(buf, np.uint8).reshape(oh, W, 3)
        yield last if last is not None else np.zeros((oh, W, 3), np.uint8)
    p.stdout.close()
    p.kill()


_photo = None


def still_reader(shot, n):
    global _photo
    if _photo is None:
        _photo = np.asarray(Image.open(PHOTO).convert("RGB"))
    cx, y0, cw, ch = shot["rect"]
    x0 = int(min(max(0, cx - cw / 2), _photo.shape[1] - cw))
    crop = _photo[y0:y0 + ch, x0:x0 + cw]
    ph = int(round(W * ch / cw / 2) * 2)
    panel = cv2.resize(crop, (W, ph), interpolation=cv2.INTER_AREA if cw > W else cv2.INTER_CUBIC)
    for _ in range(n):
        yield panel


def logo_frame(u, end=False):
    """Opening sting / end card on a deep red radial background."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.42) / H) ** 2)
    base = np.clip(1.0 - r * 1.25, 0, 1)[..., None]
    fr = np.array([18, 2, 4], np.float32) + (np.array([150, 8, 14], np.float32) - [18, 2, 4]) * base
    return fr


_BG = None


def red_bg():
    global _BG
    if _BG is None:
        _BG = logo_frame(0)
    return _BG.copy()


def shot_frames(i, n):
    """Base frames (no graphics) for shot i: n frames, push-in applied per frame index."""
    s = SHOTS[i]
    N = int(round(s["dur"] * FPS))
    if s["kind"] in ("logo", "endlogo"):
        for j in range(n):
            yield red_bg()
        return
    reader = still_reader(s, n) if s["kind"] == "still" else video_reader(s, n)
    for j, img in enumerate(reader):
        z = 1 + (s["zoom"] - 1) * min(1.0, j / max(1, N - 1))
        if s["kind"] == "still" or s["crop"]:
            yield compose_panel(img, z)
        else:
            yield push_in(img, z).astype(np.float32)


def draw_logo_layer(fr, i, j, g):
    s = SHOTS[i]
    u = j / FPS
    if s["kind"] == "logo":
        k = ease_out(u / 0.5)
        sc = 0.82 + 0.18 * k
        im = g.logo_big.resize((int(g.logo_big.width * sc), int(g.logo_big.height * sc)), Image.LANCZOS)
        L = to_np(im)
        # light sweep across the logo
        sweep = np.zeros(L.shape[:2], np.float32)
        xs = np.arange(L.shape[1])[None, :] + np.arange(L.shape[0])[:, None] * 0.35
        cx = (u - 0.35) / 0.7 * (L.shape[1] * 1.6) - L.shape[1] * 0.3
        sweep = np.clip(1 - np.abs(xs - cx) / 60, 0, 1) * 0.45 * (L[..., 3] / 255)
        L[..., :3] = L[..., :3] + (255 - L[..., :3]) * sweep[..., None]
        paste(fr, L, (W - L.shape[1]) // 2, int(H * 0.42 - L.shape[0] / 2), k)
    elif s["kind"] == "endlogo":
        k = ease_out(u / 0.5)
        sc = 0.9 + 0.1 * k
        im = g.logo_big.resize((int(g.logo_big.width * sc), int(g.logo_big.height * sc)), Image.LANCZOS)
        L = to_np(im)
        paste(fr, L, (W - L.shape[1]) // 2, int(H * 0.38 - L.shape[0] / 2), k)
        k1, k2 = ease_out((u - 0.5) / 0.4), ease_out((u - 0.8) / 0.4)
        paste(fr, g.e_1, (W - g.e_1.shape[1]) // 2, int(1150 + 30 * (1 - k1)), k1)
        paste(fr, g.e_2, (W - g.e_2.shape[1]) // 2, int(1255 + 30 * (1 - k2)), k2)


def render_frames(only=None):
    g = Graphics()
    tail = None            # extra frames of the previous shot, for a dissolve into the next
    for i, s in enumerate(SHOTS):
        f0 = int(round(starts[i] * FPS))
        n = int(round(s["dur"] * FPS))
        nxt = SHOTS[i + 1]["trans"] if i + 1 < len(SHOTS) else "cut"
        extra = DISSOLVE if nxt == "dissolve" else 0
        need = only is None or any(f0 - DISSOLVE <= f < f0 + n + DISSOLVE for f in only)
        if not need:
            tail = None
            continue
        frames = shot_frames(i, n + extra)
        new_tail = []
        for j, base in enumerate(frames):
            f = f0 + j
            in_dissolve = s["trans"] == "dissolve" and tail and j < len(tail)
            if only is not None and j < n and f not in only and not in_dissolve:
                continue
            fr = base.copy()
            if s["kind"] in ("logo", "endlogo"):
                draw_logo_layer(fr, i, j, g)
            g.draw(fr, f / FPS, i)
            if j >= n:
                new_tail.append(fr)
                continue
            if in_dissolve:
                a = (j + 1) / (len(tail) + 1)
                fr = tail[j] * (1 - a) + fr * a
            if only is not None and f not in only:
                continue
            if s["trans"] == "dip" and j < DIP:
                fr *= j / DIP
            if nxt == "dip" and j >= n - DIP:
                fr *= (n - 1 - j) / DIP
            if i == 0 and j < 6:
                fr *= j / 6
            if f >= NFRAMES - 15:
                fr *= max(0.0, (NFRAMES - 1 - f) / 15)
            yield f, np.clip(fr, 0, 255).astype(np.uint8)
        tail = new_tail


# ------------------------------------------------------------------ audio
def load_audio(path, t_in=0.0, dur=None, af=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in}", "-i", path]
    if dur:
        cmd += ["-t", f"{dur}"]
    if af:
        cmd += ["-af", af]
    cmd += ["-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32).reshape(-1, 2).copy()


def place(mix, x, t0, fade=0.08):
    if len(x) == 0:
        return
    fl = min(int(fade * SR), len(x) // 2)
    if fl > 0:
        x[:fl] *= np.linspace(0, 1, fl)[:, None]
        x[-fl:] *= np.linspace(1, 0, fl)[:, None]
    s = int(t0 * SR)
    e = min(len(mix), s + len(x))
    mix[s:e] += x[: e - s]


def build_audio(path_out):
    mix = np.zeros((int((TOTAL + 0.5) * SR), 2), np.float32)
    byte_mask = np.zeros(len(mix), np.float32)
    BYTE_AF = "highpass=f=110,lowpass=f=7500,afftdn=nf=-28,acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=3"
    for i, s in enumerate(SHOTS):
        au = s.get("audio")
        if not au:
            continue
        if au[0] == "nat":
            x = load_audio(src(s["clip"]), s["t_in"], s["dur"] + 0.15, "highpass=f=90") * au[1]
            place(mix, x, starts[i] - 0.05, fade=0.15)
        else:
            x = load_audio(src("40"), au[1], s["dur"], BYTE_AF) * 1.0
            place(mix, x, starts[i], fade=0.03)
            a, b = int(starts[i] * SR), int((starts[i] + s["dur"]) * SR)
            byte_mask[a:b] = 1
    # piano bed, looped, ducked under the byte
    bed = load_audio(BED)
    reps = int(np.ceil(len(mix) / len(bed))) + 1
    xf = int(1.5 * SR)
    loop = bed.copy()
    for _ in range(reps):
        seg = bed.copy()
        ramp = np.linspace(0, 1, xf)[:, None]
        loop[-xf:] = loop[-xf:] * (1 - ramp) + seg[:xf] * ramp
        loop = np.concatenate([loop, seg[xf:]])
    loop = loop[: len(mix)]
    k = int(0.4 * SR)
    duck = np.convolve(byte_mask, np.ones(k) / k, mode="same")
    level = 0.16 * (1 - duck) + 0.035 * duck
    level[: int(starts[1] * SR)] = 0.2
    fade_in = int(1.0 * SR)
    level[:fade_in] *= np.linspace(0, 1, fade_in)
    mix += loop * level[:, None]

    def sfx(name, t, gain):
        place(mix, load_audio(os.path.join(SFX, name)) * gain, max(0.0, t), fade=0.01)

    sfx("whoosh-soft.wav", 0.0, 0.45)
    sfx("whoosh-soft.wav", starts[IDX_END] - 0.2, 0.35)
    mix = mix[: int(TOTAL * SR)]
    tail = int(0.8 * SR)
    mix[-tail:] *= np.linspace(1, 0, tail)[:, None]
    raw = path_out + ".raw.wav"
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(raw, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), path_out], check=True)
    os.remove(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=None)
    ap.add_argument("--audio-only", action="store_true")
    args = ap.parse_args()
    os.makedirs(os.path.join(HERE, "preview"), exist_ok=True)
    print(f"total {TOTAL:.2f}s, {NFRAMES} frames")
    for i, s in enumerate(SHOTS):
        print(f"  {i:2d} {starts[i]:6.2f}  {s['dur']:4.1f}  {s['note']}")
    if args.frames:
        only = {int(x) for x in args.frames.split(",")}
        for f, fr in render_frames(only):
            Image.fromarray(fr).save(os.path.join(HERE, "preview", f"f_{f:04d}.jpg"), quality=88)
        return
    audio = os.path.join(HERE, "_audio.wav")
    build_audio(audio)
    if args.audio_only:
        return
    silent = os.path.join(HERE, "_silent.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", silent],
                         stdin=subprocess.PIPE)
    for f, fr in render_frames():
        p.stdin.write(fr.tobytes())
        if f % 150 == 0:
            print("frame", f, flush=True)
    p.stdin.close()
    p.wait()
    out = os.path.join(HERE, "munda_shraddhanjali.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(silent)
    print("wrote", out)


if __name__ == "__main__":
    main()
