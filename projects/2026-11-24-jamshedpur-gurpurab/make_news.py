"""Jamshedpur Guru Nanak Jayanti (557th Prakash Parv) news reel, built from the raw WhatsApp clips.

Video: each shot is decoded by ffmpeg (scaled to 1080x1920; landscape clips sit on a blurred fill), then
Python adds a slow push-in, the cut transitions (whip, flash, dip, punch) and the news graphics
(top tag, ticker, headline cards, lower thirds, interview subtitles). Audio is the natural sound of each
shot, the interview bites at full level, and a few transition SFX, loudness-normalised at the end.

Usage: python3 make_news.py [--frames 30,300,...]
"""
import argparse
import os
import subprocess
import wave

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RAW = os.path.join(ROOT, "raw-videos", "2026-11-24-jamshedpur-gurpurab")
SFX = os.path.join(ROOT, "assets", "sfx", "generated")
W, H, FPS, SR = 1080, 1920, 30, 48000
SAFFRON = (255, 140, 26)
NAVY = (12, 30, 78)
WHITE = (255, 255, 255)
FONT_B = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"


def src(n):
    return os.path.join(RAW, f"VID-20261124-WA{n}.mp4")


LANDSCAPE = {"0004", "0005", "0010", "0020"}

# ------------------------------------------------------------------ edit decision list
# video shots in order: (clip, in, dur, transition INTO this shot, push-in)
SHOTS = [
    ("0013", 10.0, 3.0, "none", 1.10),    # hook: aerial of the golchakkar packed with the sangat
    ("0019", 2.0, 2.0, "whip", 1.06),     # orange turbans and the Nishan Sahib
    ("0014", 31.0, 2.0, "whip", 1.06),    # school band drums
    ("0011", 18.5, 2.5, "flash", 1.05),   # gatka: the fire-wheel
    ("0016", 34.0, 2.0, "flash", 1.06),   # gatka: a little girl with the stick
    ("0012", 9.5, 2.0, "flash", 1.06),    # gatka team in blue
    ("0009", 0.0, 2.5, "whip", 1.05),     # gatka boy in blue
    ("0010", 12.0, 3.0, "punch", 1.04),   # wide: the procession round the circle
    ("0018", 26.1, 8.9, "dip", 1.03),     # BYTE 1
    ("0007", 8.5, 2.5, "dip", 1.06),      # procession in uniform
    ("0015", 21.0, 2.5, "whip", 1.05),    # kids' gatka in black and white
    ("0008", 4.0, 2.5, "whip", 1.05),     # the crowd at the big screen
    ("0006", 0.0, 2.5, "flash", 1.05),    # balloons and the sound truck
    ("0005", 33.0, 3.0, "whip", 1.04),    # seva stall serving the sangat
    ("0017", 45.4, 4.1, "dip", 1.03),     # BYTE 3 (face)
    ("0021", 2.0, 3.0, "none", 1.06),     #   b-roll over byte 3: welcome camp
    ("0004", 1.0, 3.0, "none", 1.04),     #   b-roll over byte 3: elders waiting
    ("0017", 55.5, 3.8, "none", 1.03),    # BYTE 3 (face again)
    ("0018", 60.8, 3.0, "dip", 1.03),     # BYTE 2 (face)
    ("0019", 6.0, 3.4, "none", 1.06),     #   b-roll over byte 2: the sangat
    ("0018", 67.2, 3.0, "none", 1.03),    # BYTE 2 (face again)
    ("0012", 1.0, 2.4, "whip", 1.06),     # kids march on
    ("0013", 30.0, 4.8, "dip", 1.08),     # closing aerial + end card
]

starts = []
_t = 0.0
for s in SHOTS:
    starts.append(_t)
    _t += s[2]
TOTAL = _t
NFRAMES = int(round(TOTAL * FPS))

# audio regions: (clip, in, dur, timeline start, gain). Nat sound follows the shots; bites run under their b-roll.
BYTE_SHOTS = {8, 14, 15, 16, 17, 18, 19, 20}
AUDIO = []
for i, (c, a, d, _, _) in enumerate(SHOTS):
    if i not in BYTE_SHOTS:
        AUDIO.append((c, a, d, starts[i], 0.55))
AUDIO.append(("0018", 26.1, 8.9, starts[8], 1.0))
AUDIO.append(("0017", 45.4, 13.9, starts[14], 1.0))    # one continuous take under the b-roll
AUDIO.append(("0018", 60.8, 9.4, starts[18], 1.0))

# subtitles for the bites: (timeline start, end, text)
def _sub(shot_idx, src_in, chunks):
    t0 = starts[shot_idx]
    return [(t0 + a - src_in, t0 + b - src_in, txt) for a, b, txt in chunks]


SUBS = (
    _sub(8, 26.1, [(26.1, 31.0, "आज सोनारी से नगर कीर्तन निकला है"), (31.4, 35.0, "और लाखों लोग इस नगर कीर्तन में हैं")])
    + _sub(14, 45.4, [(45.4, 47.2, "गुरु महाराज की कृपा है"), (47.2, 49.2, "हम सब मिल-जुलकर खुशी मना रहे हैं"),
                      (49.3, 51.3, "हर गुरुद्वारे में लंगर चल रहा है"), (51.4, 55.0, "लंगर छककर सब अपने-अपने स्थान पर बैठे हैं"),
                      (55.1, 57.0, "अभी नगर कीर्तन का इंतज़ार कर रहे हैं"), (57.1, 59.3, "उन्हीं के स्वागत के लिए हम बैठे हैं")])
    + _sub(18, 60.8, [(60.8, 64.8, "आपसी सद्भावना, आपसी भाईचारा बरकरार रखने के लिए"), (65.3, 67.9, "हम लोगों से आह्वान करेंगे"),
                      (68.0, 70.2, "देश को आगे बढ़ाएं, राज्य को आगे बढ़ाएं")])
)

# lower thirds: (start, end, line1 (saffron), line2 (white))
SUPERS = [
    (starts[1] + 0.2, starts[3], "संगत का सैलाब", "भारी संख्या में श्रद्धालु नगर कीर्तन में शामिल"),
    (starts[3] + 0.2, starts[7], "गतका का जलवा", "बच्चों ने दिखाए सिख मार्शल आर्ट के करतब"),
    (starts[7] + 0.2, starts[8], "सोनारी से साकची तक", "करीब 7.5 किमी लंबा नगर कीर्तन"),
    (starts[8] + 0.3, starts[9], "प्रमोद लाल", "केंद्रीय नेता, झामुमो"),
    (starts[9] + 0.2, starts[12], "स्कूली टोलियां भी शामिल", "बैंड-बाजे के साथ निकले बच्चे"),
    (starts[12] + 0.2, starts[14], "सेवा भाव", "जगह-जगह स्टॉल, संगत की सेवा"),
    (starts[14] + 0.3, starts[14] + 4.0, "स्थानीय श्रद्धालु", "स्वागत शिविर, जमशेदपुर"),
    (starts[18] + 0.3, starts[18] + 3.0, "प्रमोद लाल", "केंद्रीय नेता, झामुमो"),
]

TICKER = ("गुरु नानक देव जी के 557वें प्रकाश पर्व पर जमशेदपुर में भव्य नगर कीर्तन   |   "
          "सोनारी गुरुद्वारा से साकची गुरुद्वारा तक उमड़ी संगत   |   गतका दलों ने दिखाए हैरतअंगेज़ करतब   |   "
          "शहर भर में गुरु का लंगर और सेवा शिविर   |   ")


# ------------------------------------------------------------------ graphics
def font(size, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT_R, size, layout_engine=ImageFont.Layout.RAQM)


def text_box(text, size, fg, bg, pad=(26, 10), bold=True, radius=10):
    f = font(size, bold)
    l, t, r, b = f.getbbox(text)
    w, h = r - l + pad[0] * 2, int(size * 1.45) + pad[1] * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=bg)
    d.text((pad[0] - l, pad[1] + (int(size * 1.45) - size) // 2 - int(size * 0.18)), text, font=f, fill=fg)
    return im


def stroked_text(text, size, fill=WHITE, stroke=(0, 0, 0), sw=5, maxw=980):
    f = font(size)
    while f.getlength(text) > maxw and size > 34:
        size -= 2
        f = font(size)
    l, t, r, b = f.getbbox(text, stroke_width=sw)
    im = Image.new("RGBA", (r - l + 4, int(size * 1.7)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - l, int(size * 0.12)), text, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)
    return im


def to_np(im):
    return np.asarray(im, dtype=np.float32)


def paste(frame, layer, x, y, alpha=1.0):
    """Alpha-composite an RGBA float layer onto an RGB float frame at (x, y)."""
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


class Graphics:
    def __init__(self):
        self.tag = to_np(text_box("जमशेदपुर", 40, WHITE, SAFFRON + (255,)))
        self.date = to_np(text_box("24 नवंबर 2026", 34, WHITE, NAVY + (230,)))
        # ticker strip
        f = font(36)
        unit = int(f.getlength(TICKER))
        strip = Image.new("RGBA", (unit * 2, 70), NAVY + (240,))
        d = ImageDraw.Draw(strip)
        for k in range(2):
            d.text((k * unit, 4), TICKER, font=f, fill=WHITE)
        self.ticker = to_np(strip)
        self.ticker_unit = unit
        self.ticker_label = to_np(text_box("ख़ास ख़बर", 36, WHITE, (205, 30, 40, 255), pad=(22, 4), radius=0))
        self.supers = [(a, b, to_np(text_box(l1, 46, NAVY, SAFFRON + (255,))), to_np(text_box(l2, 38, NAVY, WHITE + (245,)))) for a, b, l1, l2 in SUPERS]
        self.subs = [(a, b, to_np(stroked_text(t, 50))) for a, b, t in SUBS]
        # opening headline
        self.h_kicker = to_np(text_box("जो बोले सो निहाल", 52, NAVY, SAFFRON + (255,)))
        self.h_main1 = to_np(stroked_text("जमशेदपुर में गुरु नानक देव जी का", 60, sw=6))
        self.h_main2 = to_np(stroked_text("557वां प्रकाश पर्व", 104, fill=(255, 214, 120), sw=8))
        # end card
        self.e1 = to_np(stroked_text("वाहेगुरु जी का खालसा", 76, sw=7))
        self.e2 = to_np(stroked_text("वाहेगुरु जी की फ़तह", 76, sw=7))
        self.e3 = to_np(text_box("गुरु नानक जयंती की लख-लख बधाइयाँ", 44, NAVY, SAFFRON + (255,)))

    def draw(self, fr, t):
        intro = t < starts[1]
        endc = t >= starts[-1] + 0.6
        if not intro:
            paste(fr, self.tag, 48, 150)
            paste(fr, self.date, 48 + self.tag.shape[1] + 12, 154)
        # ticker (above Instagram's caption area)
        ty = 1530
        off = int((t * 150) % self.ticker_unit)
        paste(fr, self.ticker[:, off:off + W], 0, ty)
        paste(fr, self.ticker_label, 0, ty + 1)
        # headline card
        if intro:
            k1, k2, k3 = ease_out((t - 0.15) / 0.35), ease_out((t - 0.4) / 0.35), ease_out((t - 0.65) / 0.4)
            paste(fr, self.h_kicker, (W - self.h_kicker.shape[1]) // 2, int(1080 + 40 * (1 - k1)), k1)
            paste(fr, self.h_main1, (W - self.h_main1.shape[1]) // 2, int(1185 + 40 * (1 - k2)), k2)
            s = 0.7 + 0.3 * k3 + 0.06 * np.sin(min(1, max(0, (t - 0.65) / 0.4)) * np.pi)
            m2 = cv2.resize(self.h_main2, None, fx=s, fy=s) if k3 > 0 else self.h_main2
            paste(fr, m2, (W - m2.shape[1]) // 2, int(1280 + (self.h_main2.shape[0] - m2.shape[0]) / 2), k3)
            return
        # lower thirds slide in from the left
        for a, b, l1, l2 in self.supers:
            if a <= t < b:
                k = ease_out((t - a) / 0.35) * (1 - ease_out((t - (b - 0.3)) / 0.3))
                x = int(-700 * (1 - k)) + 48
                paste(fr, l1, x, 1290, k)
                paste(fr, l2, x, 1290 + l1.shape[0] + 6, k)
        for a, b, im in self.subs:
            if a <= t < b:
                k = min(1.0, (t - a) / 0.12, (b - t) / 0.12)
                paste(fr, im, (W - im.shape[1]) // 2, 1150, k)
        if endc:
            k1, k2, k3 = ease_out((t - starts[-1] - 0.6) / 0.4), ease_out((t - starts[-1] - 1.0) / 0.4), ease_out((t - starts[-1] - 1.5) / 0.4)
            fr *= 1 - 0.45 * k1
            paste(fr, self.e1, (W - self.e1.shape[1]) // 2, int(760 + 30 * (1 - k1)), k1)
            paste(fr, self.e2, (W - self.e2.shape[1]) // 2, int(870 + 30 * (1 - k2)), k2)
            paste(fr, self.e3, (W - self.e3.shape[1]) // 2, int(1010 + 30 * (1 - k3)), k3)


# ------------------------------------------------------------------ video
def shot_reader(clip, t_in, dur):
    if clip in LANDSCAPE:
        vf = ("split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:2,eq=brightness=-0.1:saturation=1.1[bg];"
              "[b]scale=1080:-2:flags=lanczos,unsharp=5:5:0.6[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2-80")
    else:
        vf = "scale=1080:1920:flags=lanczos,unsharp=5:5:0.6"
    vf += ",eq=contrast=1.05:saturation=1.12,fps=30"
    n = int(round(dur * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t_in}", "-i", src(clip), "-t", f"{dur + 0.2}", "-vf", vf, "-an",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    last = None
    for _ in range(n):
        buf = p.stdout.read(W * H * 3)
        if len(buf) == W * H * 3:
            last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        yield last if last is not None else np.zeros((H, W, 3), np.uint8)
    p.stdout.close()
    p.kill()


def push_in(img, z):
    if z <= 1.001:
        return img
    cw, ch = int(W / z), int(H / z)
    x0, y0 = (W - cw) // 2, (H - ch) // 2
    return cv2.resize(img[y0:y0 + ch, x0:x0 + cw], (W, H), interpolation=cv2.INTER_LINEAR)


def whip(img, k, direction):
    """k in 0..1: amount of whip; shifts and smears horizontally."""
    if k <= 0:
        return img
    shift = int(direction * k * 260)
    out = np.roll(img, shift, axis=1)
    ks = max(3, int(k * 90)) | 1
    return cv2.blur(out, (ks, 1))


def render_frames(only=None):
    g = Graphics()
    TR = 4   # frames each side of a cut
    cut_at = {i: (int(round(starts[i] * FPS)), SHOTS[i][3]) for i in range(len(SHOTS))}
    for i, (clip, t_in, dur, trans, zoom) in enumerate(SHOTS):
        f0 = int(round(starts[i] * FPS))
        n = int(round(dur * FPS))
        next_tr = SHOTS[i + 1][3] if i + 1 < len(SHOTS) else "none"
        need = only is None or any(f0 <= f < f0 + n for f in only)
        if not need:
            continue
        for j, img in enumerate(shot_reader(clip, t_in, dur)):
            f = f0 + j
            if only is not None and f not in only:
                continue
            t = f / FPS
            u = j / max(1, n - 1)
            z = 1 + (zoom - 1) * u
            if trans == "punch" and j < 8:
                z += 0.12 * (1 - j / 8)
            fr = push_in(img, z)
            # transitions
            if next_tr == "whip" and j >= n - TR:
                fr = whip(fr, (j - (n - TR) + 1) / TR, -1)
            if trans == "whip" and j < TR:
                fr = whip(fr, 1 - j / TR, -1)
            fr = fr.astype(np.float32)
            if trans == "flash" and j < 5:
                fr = fr + (255 - fr) * (0.85 * (1 - j / 5))
            if next_tr == "flash" and j >= n - 2:
                fr = fr + (255 - fr) * 0.35
            if trans == "dip" and j < 6:
                fr *= j / 6
            if next_tr == "dip" and j >= n - 6:
                fr *= (n - 1 - j) / 6
            if i == 0 and j < 8:
                fr *= j / 8
            g.draw(fr, t)
            if f >= NFRAMES - 18:   # final fade
                fr *= max(0.0, (NFRAMES - 1 - f) / 18)
            yield f, np.clip(fr, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ audio
def load_audio(path, t_in=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in}", "-i", path]
    if dur:
        cmd += ["-t", f"{dur}"]
    cmd += ["-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    a = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32).reshape(-1, 2)
    return a.copy()


def build_audio(path_out):
    mix = np.zeros((int((TOTAL + 0.5) * SR), 2), np.float32)
    fade = int(0.06 * SR)
    for clip, a, d, t0, gain in AUDIO:
        x = load_audio(src(clip), a, d) * gain
        # denoise-ish: tame rumble and hiss on nat sound
        if len(x) == 0:
            continue
        r = np.ones(len(x), np.float32)
        r[:fade] = np.linspace(0, 1, min(fade, len(x)))[: len(r[:fade])]
        r[-fade:] = np.minimum(r[-fade:], np.linspace(1, 0, fade))
        x *= r[:, None]
        s = int(t0 * SR)
        mix[s:s + len(x)] += x[: len(mix) - s]
    # nat sound ducks under the bites (the byte regions only carry the bite audio already)
    def sfx(name, t, g):
        y = load_audio(os.path.join(SFX, name)) * g
        s = int(t * SR)
        mix[s:s + len(y)] += y[: max(0, len(mix) - s)]
    sfx("boom-hit.wav", 0.05, 0.5)
    for i, s in enumerate(SHOTS):
        if s[3] == "whip":
            sfx("whip-pan.wav", starts[i] - 0.12, 0.35)
        elif s[3] == "flash":
            sfx("camera-shutter.wav", starts[i] - 0.02, 0.3)
        elif s[3] == "punch":
            sfx("boom-hit.wav", starts[i], 0.35)
        elif s[3] == "dip":
            sfx("whoosh-soft.wav", starts[i] - 0.25, 0.3)
    sfx("riser.wav", starts[-1] - 1.2, 0.25)
    mix = mix[: int(TOTAL * SR)]
    tail = int(0.6 * SR)
    mix[-tail:] *= np.linspace(1, 0, tail)[:, None]
    raw = path_out + ".raw.wav"
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(raw, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", "highpass=f=90,loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), path_out], check=True)
    os.remove(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=None)
    args = ap.parse_args()
    os.makedirs(os.path.join(HERE, "preview"), exist_ok=True)
    print(f"total {TOTAL:.2f}s, {NFRAMES} frames")
    if args.frames:
        only = {int(x) for x in args.frames.split(",")}
        for f, fr in render_frames(only):
            Image.fromarray(fr).save(os.path.join(HERE, "preview", f"f_{f:04d}.jpg"), quality=88)
        return
    audio = os.path.join(HERE, "_audio.wav")
    build_audio(audio)
    silent = os.path.join(HERE, "_silent.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", silent],
                         stdin=subprocess.PIPE)
    for f, fr in render_frames():
        p.stdin.write(fr.tobytes())
        if f % 150 == 0:
            print("frame", f, flush=True)
    p.stdin.close()
    p.wait()
    out = os.path.join(HERE, "jamshedpur_gurpurab.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(silent)
    print("wrote", out)


if __name__ == "__main__":
    main()
