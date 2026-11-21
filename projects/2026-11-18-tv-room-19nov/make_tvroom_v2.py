"""19 November, v2: a boy alone in a dark room lit only by the TV, crying while the user's clip plays.

Three camera angles, every one with both the boy and the TV in frame:
  OTS     over his shoulder: his rim-lit back and head in the foreground, the TV big ahead of him
  PROFILE side view: he sits hugging his knees, facing the TV across the room, tears on his cheek
  CLOSE   close profile of his crying face, the TV glowing out of focus beside him
Lighting: the room is near black; the TV is the only light. It takes the clip's colour, falls off with
distance, throws a hazy beam with dust, and rims the side of him that faces it.

Input clip: raw-videos/VID_20261118_181136_080.mp4 (its audio is kept).
Usage: python3 make_tvroom_v2.py [--frames 30,300,...]
"""
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
CLIP = os.path.join(HERE, "..", "..", "raw-videos", "VID_20261118_181136_080.mp4")
OUT = os.path.join(HERE, "tvroom_19nov_v2.mp4")
DUR = 39.77
CW, CH = 720, 724
SS = 2  # supersampling for line art
F_NUM = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"

# shots follow the song's phrases (Whisper segment boundaries)
SHOTS = [(0.0, 7.8, "ots", 1.00, 1.10), (7.8, 16.4, "profile", 1.08, 1.00), (16.4, 23.1, "close", 1.00, 1.08),
         (23.1, 29.6, "ots2", 1.10, 1.02), (29.6, 36.7, "profile", 1.00, 1.10), (36.7, DUR, "close", 1.06, 1.14)]
WIPES = [(11.0, 12.6), (19.2, 20.8), (32.0, 33.6)]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ----------------------------------------------------------------------------------------------
# acting (shared by every shot)
# ----------------------------------------------------------------------------------------------
def acting(t):
    sob = max(0.0, math.sin(t * 0.9)) ** 6                       # sob waves
    head_down = 0.0
    for a_, b_ in ((14.0, 15.8), (26.0, 28.6), (37.6, 39.7)):  # short moments of burying his face
        head_down = max(head_down, smooth((t - a_) / 0.5) * (1 - smooth((t - (b_ - 0.5)) / 0.5)))
    blink = 1.0 if (t % 3.6) < 0.13 else 0.0
    wipe = 0.0
    for a, b in WIPES:
        if a <= t <= b:
            wipe = smooth((t - a) / 0.35) * (1 - smooth((t - (b - 0.35)) / 0.35))
    return {"sob": sob, "down": head_down * (1 - wipe), "blink": blink, "wipe": wipe,
            "tear": (t / 2.2) % 1, "shudder": sob * math.sin(t * 22) * 4, "breath": math.sin(t * 1.8)}


# ----------------------------------------------------------------------------------------------
# the TV picture
# ----------------------------------------------------------------------------------------------
def crt_picture(clip, t, w=640, h=520):
    pic = Image.new("RGB", (w, h), (0, 0, 0))
    sc = h / clip.height
    cl = clip.resize((int(clip.width * sc), h), Image.BILINEAR)
    pic.paste(cl, ((w - cl.width) // 2, 0))
    arr = np.asarray(pic).astype(np.float32)
    arr[::3] *= 0.8
    yy, xx = np.mgrid[0:h, 0:w]
    vig = 1 - 0.4 * (((xx - w / 2) / (w / 2)) ** 4 + ((yy - h / 2) / (h / 2)) ** 4)
    arr = arr * vig[:, :, None] * (0.95 + 0.05 * math.sin(t * 47)) * 1.12 + 8
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def quad_coeffs(dst, w, h):
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def tv_colour(clip):
    avg = np.asarray(clip.resize((8, 8))).reshape(-1, 3).mean(0)
    lum = avg.mean() + 1
    col = avg / lum * 200  # keep the hue, normalise brightness
    return np.clip(col * 0.7 + np.array([90, 110, 150]) * 0.3, 0, 255), clamp(lum / 120, 0.6, 1.2)


def paste_screen(frame, pic, quad):
    warped = pic.convert("RGBA").transform(frame.size, Image.PERSPECTIVE, quad_coeffs(quad, pic.width, pic.height),
                                           resample=Image.BILINEAR)
    m = Image.new("L", frame.size, 0)
    ImageDraw.Draw(m).polygon(quad, fill=255)
    frame.paste(warped, (0, 0), m.filter(ImageFilter.GaussianBlur(1.5)))
    return warped, m


# ----------------------------------------------------------------------------------------------
# the boy in profile (facing left), drawn at SS x scale
# ----------------------------------------------------------------------------------------------
SKIN, SKIN_SH, HAIR, HOOD, HOOD_D, PANTS, LINE = ((252, 222, 202), (226, 186, 168), (22, 22, 34), (52, 78, 140),
                                                  (36, 54, 100), (30, 32, 46), (12, 12, 20))
BLANKET, BLANKET_D = (104, 76, 96), (70, 50, 64)


def profile_head(d, P, cx, cy, s, a, rim):
    """Anime head in left-facing profile. P maps (x, y) -> canvas coords. rim = TV light colour."""
    def pt(x, y):
        return P(cx + x * s, cy + y * s)
    w = lambda v: max(1, int(v * SS * s))
    # neck (narrow, angled back)
    d.polygon([pt(-26, 86), pt(8, 74), pt(30, 150), pt(-18, 160)], fill=SKIN_SH, outline=LINE, width=w(2))
    face = [(-50, -80), (-78, -56), (-90, -28), (-93, -8), (-90, 4), (-96, 14), (-108, 30), (-95, 40), (-97, 47),
            (-92, 52), (-89, 56), (-94, 61), (-90, 70), (-84, 84), (-70, 95), (-30, 99), (8, 80), (26, 50), (30, 0),
            (24, -60), (0, -90)]
    d.polygon([pt(x, y) for x, y in face], fill=SKIN, outline=LINE, width=w(3))
    d.polygon([pt(-30, 99), pt(8, 80), pt(26, 50), pt(4, 60), pt(-36, 88)], fill=SKIN_SH)       # jaw shadow
    d.line([pt(x, y) for x, y in face[1:15]], fill=rim, width=w(6))                               # TV light on the profile
    d.ellipse([pt(-76, 38), pt(-48, 52)], fill=(255, 150, 160))                                     # blush
    # eye: white wedge, iris at the front, heavy sad lid
    lid = max(a["blink"], 0.32 + 0.3 * a["down"])
    if lid > 0.9:
        d.line([pt(-86, 16), pt(-68, 22), pt(-52, 16)], fill=LINE, width=w(5))
    else:
        d.polygon([pt(-84, 2), pt(-54, -2), pt(-56, 28), pt(-82, 25)], fill=(255, 255, 255))
        d.ellipse([pt(-83, 3), pt(-63, 27)], fill=(40, 62, 136))
        d.ellipse([pt(-80, 8), pt(-68, 22)], fill=(12, 14, 30))
        d.ellipse([pt(-79, 7), pt(-73, 13)], fill=(255, 255, 255))
        d.ellipse([pt(-70, 18), pt(-67, 21)], fill=(255, 255, 255))
        top = -2 + lid * 30
        d.polygon([pt(-88, -12), pt(-50, -16), pt(-52, top), pt(-86, top + 4)], fill=SKIN)
        d.line([pt(-88, top + 5), pt(-52, top), pt(-44, top - 7)], fill=LINE, width=w(6))
        d.ellipse([pt(-86, 24), pt(-62, 32)], fill=(190, 222, 255))                                # watery
    d.line([pt(-90, -30), pt(-72, -25), pt(-52, -18)], fill=HAIR, width=w(6))                       # sad brow
    if a["sob"] > 0.35:
        d.ellipse([pt(-97, 50), pt(-85, 64)], fill=(110, 30, 44), outline=LINE, width=w(2))
    else:
        d.line([pt(-95, 57), pt(-86, 58 + a["shudder"] * 0.3)], fill=LINE, width=w(3))
    for ph in (a["tear"], (a["tear"] + 0.5) % 1):                                                   # tears
        ty = 30 + ph * 70
        tx = -76 - ph * 10
        d.line([pt(-74, 28), pt(tx, ty)], fill=(170, 210, 255), width=w(4))
        d.polygon([pt(tx, ty - 9), pt(tx - 6, ty + 2), pt(tx + 6, ty + 2)], fill=(175, 218, 255))
        d.ellipse([pt(tx - 6, ty - 3), pt(tx + 6, ty + 8)], fill=(175, 218, 255))
        d.ellipse([pt(tx - 3, ty - 1), pt(tx + 1, ty + 3)], fill=(255, 255, 255))
    # hair: covers the top and the whole back of the head down to the nape; bangs over the forehead
    hair = [(-102, -12), (-122, -40), (-94, -54), (-120, -88), (-76, -90), (-84, -132), (-38, -112), (-26, -152),
            (10, -120), (40, -150), (56, -102), (100, -118), (88, -66), (128, -54), (98, -18), (124, 10), (86, 30),
            (104, 66), (60, 70), (44, 104), (14, 82), (14, 40), (4, -6), (-24, -36), (-52, -34), (-62, -4),
            (-76, -26), (-86, 4)]
    d.polygon([pt(x, y) for x, y in hair], fill=HAIR, outline=LINE, width=w(3))
    d.line([pt(x, y) for x, y in hair[:10]], fill=rim, width=w(6))                                  # TV rim on the bangs
    d.arc([pt(-44, -112), pt(64, -46)], 200, 320, fill=(76, 86, 128), width=w(8))                  # hair shine
    # ear on top of the hair
    d.ellipse([pt(0, 6), pt(28, 48)], fill=SKIN, outline=LINE, width=w(2))
    d.arc([pt(6, 14), pt(22, 40)], 90, 270, fill=SKIN_SH, width=w(3))


def draw_profile_boy(d, P, hx, hy, s, a, rim):
    """Huddled on the floor in a blanket, knees pulled up, facing left (towards the TV)."""
    down, sh, br = a["down"], a["shudder"], a["breath"]

    def pt(x, y):
        return P(hx + x * s, hy + y * s)
    w = lambda v: max(1, int(v * SS * s))
    neck = (-70 - 60 * down + sh * 0.4, -380 + 70 * down + br * 3)
    head = (neck[0] - 30 - 50 * down, neck[1] - 80 + 60 * down)
    # toes peeking out at the front
    d.ellipse([pt(-318, -26), pt(-262, 6)], fill=(222, 222, 230), outline=LINE, width=w(3))
    # blanket mound: over the back, round the knees, closed at the chest
    mound = [(neck[0] + 40, neck[1] - 10), (60, -390 + br * 2), (112, -260), (132, -90), (142, 0), (-290, 0),
             (-312, -90), (-286, -230), (-210, -300), (neck[0] - 50, neck[1] + 30)]
    d.polygon([pt(x, y) for x, y in mound], fill=BLANKET, outline=LINE, width=w(3))
    d.polygon([pt(60, -390 + br * 2), (pt(112, -260)), pt(132, -90), pt(142, 0), pt(60, 0), pt(40, -200)],
              fill=BLANKET_D)                                                            # far side in shadow
    d.arc([pt(-300, -280), pt(-120, -60)], 150, 300, fill=BLANKET_D, width=w(8))         # knee fold
    d.line([pt(-130, -30), pt(-110, -200)], fill=BLANKET_D, width=w(6))                  # folds
    d.line([pt(-30, -20), pt(-10, -230)], fill=BLANKET_D, width=w(6))
    # TV light along the front of the blanket
    d.line([pt(-290, 0), pt(-312, -90), pt(-286, -230), pt(-210, -300), pt(neck[0] - 50, neck[1] + 30)],
           fill=rim, width=w(7))
    # head
    profile_head(d, P, hx + head[0] * s, hy + head[1] * s, s, a, rim)
    # hand clutching the blanket under his chin, or up wiping his eye
    hand = (neck[0] - 70, neck[1] + 60)
    if a["wipe"] > 0.02:
        eye = (head[0] - 70, head[1] + 22)
        hand = (lerp(hand[0], eye[0], a["wipe"]), lerp(hand[1], eye[1], a["wipe"]))
        sh0 = (neck[0] - 40, neck[1] + 110)
        elb = ((sh0[0] + hand[0]) / 2 - 55 * a["wipe"], (sh0[1] + hand[1]) / 2 + 40 * a["wipe"])
        for col_, wd in ((LINE, 50), (BLANKET, 42)):
            d.line([pt(*sh0), pt(*elb), pt(*hand)], fill=col_, width=w(wd), joint="curve")
            r_ = wd / 2
            d.ellipse([pt(elb[0] - r_, elb[1] - r_), pt(elb[0] + r_, elb[1] + r_)], fill=col_)
        d.line([pt(*elb), pt(*hand)], fill=rim, width=w(4))
    d.ellipse([pt(hand[0] - 26, hand[1] - 24), pt(hand[0] + 26, hand[1] + 26)], fill=SKIN, outline=LINE, width=w(3))
    d.arc([pt(hand[0] - 26, hand[1] - 24), pt(hand[0] + 26, hand[1] + 26)], 120, 240, fill=rim, width=w(4))


def draw_back_boy(d, P, hx, hy, s, a, rim, side=1):
    """Over-the-shoulder: the back of his head and shoulders in a blanket, a sliver of his cheek showing."""
    down, sh = a["down"], a["shudder"]

    def pt(x, y):
        return P(hx + x * s + sh * 0.6, hy + y * s + 40 * down * s)
    w = lambda v: max(1, int(v * SS * s))
    d.polygon([pt(-46, 70), pt(46, 70), pt(52, 175), pt(-52, 175)], fill=(96, 74, 74))       # neck, in shadow
    body = [(-440, 900), (-410, 330), (-260, 200), (-120, 150), (-60, 128), (60, 128), (120, 150), (260, 200),
            (410, 330), (440, 900)]
    d.polygon([pt(x, y) for x, y in body], fill=BLANKET, outline=LINE, width=w(3))
    d.arc([pt(-130, 110), pt(130, 230)], 20, 160, fill=BLANKET_D, width=w(10))                # collar fold
    d.line([pt(-200, 420), pt(-150, 900)], fill=BLANKET_D, width=w(8))
    d.line([pt(180, 400), pt(140, 900)], fill=BLANKET_D, width=w(8))
    d.line([pt(-20, 300), pt(10, 900)], fill=BLANKET_D, width=w(6))
    # lost profile: the edge of his cheek, eyelashes and a tear on the side towards the camera
    cs = side
    d.polygon([pt(cs * 92, -40), pt(cs * 128, -10), pt(cs * 138, 30), pt(cs * 128, 70), pt(cs * 100, 96), pt(cs * 80, 40)],
              fill=SKIN, outline=LINE, width=w(2))
    d.line([pt(cs * 118, -6), pt(cs * 140, -16)], fill=LINE, width=w(4))                 # lashes
    ph = a["tear"]
    ty = 10 + ph * 70
    d.ellipse([pt(cs * 126 - 6, ty - 6), pt(cs * 126 + 6, ty + 8)], fill=(185, 225, 255))
    d.line([pt(cs * 124, 4), pt(cs * 126, ty)], fill=(185, 225, 255), width=w(3))
    for sg in (-1, 1):
        d.ellipse([pt(sg * 118 - 18, -10), pt(sg * 118 + 18, 44)], fill=SKIN_SH, outline=LINE, width=w(2))
    pts = []
    for k in range(27):
        ang = math.radians(150 + k * 240 / 26)
        r = 125 if k % 2 == 0 else 150
        pts.append((r * math.cos(ang), -6 + r * 1.06 * math.sin(ang)))
    pts += [(122, 60), (78, 100), (-78, 100), (-122, 60)]
    d.polygon([pt(x, y) for x, y in pts], fill=HAIR, outline=LINE, width=w(3))
    d.arc([pt(-80, -120), pt(60, -30)], 200, 320, fill=(70, 80, 120), width=w(8))


# ----------------------------------------------------------------------------------------------
# lighting helpers
# ----------------------------------------------------------------------------------------------
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)


def light_map(src, col, inten, reach, ambient=(0.16, 0.16, 0.22)):
    d2 = ((XX - src[0]) ** 2 + (YY - src[1]) ** 2) / (reach ** 2)
    k = inten / (1 + d2 * 1.6)
    return np.array(ambient, np.float32)[None, None, :] + k[:, :, None] * (col[None, None, :] / 255.0) * 1.25


def beam(frame, quad_or_poly, col, alpha):
    lay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).polygon(quad_or_poly, fill=tuple(int(c) for c in col) + (alpha,))
    frame.alpha_composite(lay.filter(ImageFilter.GaussianBlur(60)))


DUST = [(random.Random(i).uniform(0, W), random.Random(i + 99).uniform(0, H), random.Random(i + 7).uniform(1.5, 4),
         random.Random(i + 3).uniform(0, 6.28)) for i in range(140)]


def dust(frame, t, region, col):
    lay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = region
    for x, y, r, ph in DUST:
        px = x0 + (x / W) * (x1 - x0) + 20 * math.sin(t * 0.3 + ph)
        py = y0 + ((y / H) * (y1 - y0) - t * 8 * (0.5 + r / 4)) % (y1 - y0)
        a = int(120 * (0.5 + 0.5 * math.sin(t * 1.3 + ph)))
        d.ellipse([px - r, py - r, px + r, py + r], fill=tuple(int(min(255, c + 60)) for c in col) + (a,))
    frame.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))


def lit(frame_rgba, lmap, keep_mask=None):
    """Multiply the scene by the light map; keep_mask (0..1) protects self-lit things (the TV picture)."""
    arr = np.asarray(frame_rgba.convert("RGB")).astype(np.float32)
    out = arr * lmap
    if keep_mask is not None:
        k = np.asarray(keep_mask).astype(np.float32)[:, :, None] / 255.0
        out = out * (1 - k) + arr * k
    return out


# ----------------------------------------------------------------------------------------------
# shots
# ----------------------------------------------------------------------------------------------
def room_wall(img, d, floor_y, col_top=(54, 56, 78), col_bot=(40, 40, 58)):
    for y in range(0, floor_y, 6):
        f = y / floor_y
        d.rectangle([0, y, W, y + 6], fill=(int(lerp(col_top[0], col_bot[0], f)), int(lerp(col_top[1], col_bot[1], f)),
                                            int(lerp(col_top[2], col_bot[2], f)), 255))
    d.rectangle([0, floor_y, W, H], fill=(52, 42, 46, 255))
    for k in range(12):
        d.line([(540 + (k - 6) * 80, floor_y), (540 + (k - 6) * 320, H)], fill=(60, 48, 52, 255), width=3)


def shot_profile(t, clip, a):
    """Side view: TV on a cabinet at the left facing right, him sitting on the floor at the right facing it."""
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    P = lambda x, y: (x * SS, y * SS)
    big = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    bd = ImageDraw.Draw(big)
    room_wall(big, bd, 1300)
    # window with rain (right, behind him) + calendar near the TV
    bd.rectangle([700, 360, 1000, 760], fill=(16, 24, 52, 255), outline=(30, 28, 40, 255), width=14)
    bd.line([(850, 360), (850, 760)], fill=(30, 28, 40, 255), width=8)
    for k in range(40):
        rx = 710 + (k * 37) % 280
        ry = 370 + ((k * 53 + t * 600) % 380)
        bd.line([(rx, ry), (rx - 3, ry + 22)], fill=(100, 120, 170, 160), width=2)
    bd.rectangle([440, 520, 560, 660], fill=(200, 196, 188, 255))
    bd.rectangle([440, 520, 560, 552], fill=(150, 40, 46, 255))
    bd.text((500, 536), "NOV", font=ImageFont.truetype(F_NUM, 22), fill=(255, 255, 255, 255), anchor="mm")
    bd.text((500, 604), "19", font=ImageFont.truetype(F_NUM, 60), fill=(36, 36, 46, 255), anchor="mm")
    bd.ellipse([454, 560, 546, 650], outline=(180, 30, 40, 255), width=4)
    # cabinet + CRT seen from three-quarters (screen facing right)
    bd.polygon([(20, 1100), (430, 1080), (450, 1310), (10, 1330)], fill=(60, 42, 38, 255))
    bd.polygon([(40, 760), (90, 730), (430, 760), (440, 1100), (60, 1110), (30, 1080)], fill=(44, 42, 50, 255))
    bd.polygon([(40, 760), (90, 730), (95, 1090), (30, 1080)], fill=(30, 28, 36, 255))  # side panel
    screen = [(110, 800), (405, 780), (405, 1075), (110, 1050)]
    pic = crt_picture(clip, t)
    _, smask = paste_screen(big, pic, screen)
    big.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)))
    img.alpha_composite(big.resize((W * SS, H * SS), Image.BILINEAR))
    col, inten = tv_colour(clip)
    rim = tuple(int(min(255, c * 1.15 + 40)) for c in col)
    draw_profile_boy(d, P, 830, 1650, 1.55, a, rim)
    frame = img.resize((W, H), Image.LANCZOS)
    src = (300, 930)
    beam(frame, [(405, 790), (405, 1070), (1080, 1500), (1080, 650)], col, 52)
    lmap = light_map(src, col, 1.3 * inten, 820) + light_map((900, 500), np.array([90, 110, 170]), 0.35, 500,
                                                             ambient=(0, 0, 0))
    keep = smask.point(lambda v: v)
    arr = lit(frame, lmap, keep)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    bloom = pic.resize((300, 260)).filter(ImageFilter.GaussianBlur(30)).convert("RGBA")
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gl.paste(bloom, (110, 800))
    out.alpha_composite(Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 0)), gl.filter(ImageFilter.GaussianBlur(40)), 0.6))
    dust(out, t, (400, 700, 1080, 1500), col)
    return out


def shot_ots(t, clip, a, mirror=False):
    """Over his shoulder: his back in the foreground (bottom), the TV straight ahead and big."""
    big = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    bd = ImageDraw.Draw(big)
    room_wall(big, bd, 1240)
    bd.rectangle([110, 1150, 970, 1330], fill=(60, 42, 38, 255))           # cabinet
    bd.rounded_rectangle([170, 560, 910, 1150], radius=40, fill=(44, 42, 50, 255))  # CRT body
    bd.rounded_rectangle([200, 590, 880, 1120], radius=30, fill=(18, 18, 22, 255))
    bd.line([(540, 560), (420, 380)], fill=(70, 70, 76, 255), width=6)
    bd.line([(540, 560), (680, 370)], fill=(70, 70, 76, 255), width=6)
    bd.rectangle([30, 420, 150, 560], fill=(200, 196, 188, 255))           # calendar
    bd.rectangle([30, 420, 150, 452], fill=(150, 40, 46, 255))
    bd.text((90, 504), "19", font=ImageFont.truetype(F_NUM, 56), fill=(36, 36, 46, 255), anchor="mm")
    screen = [(232, 620), (848, 620), (848, 1090), (232, 1090)]
    pic = crt_picture(clip, t, 640, 500)
    _, smask = paste_screen(big, pic, screen)
    col, inten = tv_colour(clip)
    rim = tuple(int(min(255, c * 1.2 + 50)) for c in col)
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    P = lambda x, y: (x * SS, y * SS)
    hx = 290 if not mirror else 790
    hy0 = 1300
    S_OTS = 2.05
    draw_back_boy(d, P, hx, hy0, S_OTS, a, rim, side=1 if not mirror else -1)
    boy = img.resize((W, H), Image.LANCZOS)
    big.alpha_composite(boy)
    beam(big, [(232, 620), (848, 620), (1080, 1920), (0, 1920)], col, 30)
    lmap = (light_map((540, 850), col, 1.3 * inten, 950, ambient=(0.15, 0.15, 0.21))
            + light_map((540, 2100), np.array([80, 96, 150]), 0.32, 700, ambient=(0, 0, 0)))
    # his back is turned away from the light: darken the figure except its rim
    arr = lit(big, lmap, smask)
    balpha = np.asarray(boy.getchannel("A")).astype(np.float32)[:, :, None] / 255.0
    arr = arr * (1 - balpha * 0.08)
    rim_only = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(img)  # keep reference
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    # re-add the rim light strokes at full strength
    rim_img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim_img)
    s = S_OTS

    def pt(x, y):
        return P(hx + x * s + a["shudder"] * 0.6, hy0 + y * s + 40 * a["down"] * s)
    body = [(-405, 335), (-260, 205), (-125, 156)]
    rd.line([pt(x, y) for x, y in body], fill=rim + (255,), width=int(6 * SS))
    rd.line([pt(-x, y) for x, y in body], fill=rim + (255,), width=int(6 * SS))
    pts = [(125 * math.cos(math.radians(150 + k * 240 / 26)) * (1 if k % 2 == 0 else 150 / 125),
            -6 + 125 * 1.06 * math.sin(math.radians(150 + k * 240 / 26)) * (1 if k % 2 == 0 else 150 / 125))
           for k in range(6, 22)]
    rd.line([pt(x, y) for x, y in pts], fill=rim + (255,), width=int(7 * SS))
    rim_s = rim_img.resize((W, H), Image.LANCZOS)
    out.alpha_composite(rim_s.filter(ImageFilter.GaussianBlur(12)))   # soft glow only, no hard line
    soft = rim_s.filter(ImageFilter.GaussianBlur(4))
    soft.putalpha(soft.getchannel("A").point(lambda v: int(v * 0.55)))
    out.alpha_composite(soft)
    gl = pic.resize((W, H)).filter(ImageFilter.GaussianBlur(60)).convert("RGBA")
    gl.putalpha(smask.filter(ImageFilter.GaussianBlur(70)).point(lambda v: int(v * 0.5)))
    out.alpha_composite(gl)
    dust(out, t, (150, 600, 930, 1500), col)
    return out


def shot_close(t, clip, a):
    """Close profile of his face; the TV glows out of focus at the left edge."""
    out = Image.new("RGBA", (W, H), (10, 10, 16, 255))
    col, inten = tv_colour(clip)
    blur = crt_picture(clip, t, 520, 440).resize((760, 640)).filter(ImageFilter.GaussianBlur(22)).convert("RGBA")
    out.alpha_composite(blur, (-380, 520))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([-500, 380, 520, 1360], fill=tuple(int(c) for c in col) + (90,))
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    P = lambda x, y: (x * SS, y * SS)
    rim = tuple(int(min(255, c * 1.15 + 50)) for c in col)
    s = 3.1
    hx, hy = 690, 900 + 60 * a["down"]
    # shoulder + blanket edge under the head
    d.polygon([P(430, 1250), P(980, 1150), P(1180, 1920), P(380, 1920)], fill=BLANKET, outline=LINE, width=int(3 * SS))
    d.line([P(430, 1250), P(980, 1150)], fill=rim, width=int(10 * SS))
    profile_head(d, P, hx, hy, s, a, rim)
    if a["wipe"] > 0.1:  # forearm in the blanket sleeve rising to the eye
        ex, ey = hx - 68 * s, hy + 22 * s
        hand = (lerp(470, ex, a["wipe"]), lerp(2050, ey, a["wipe"]))
        base = (640, 2100)
        for col_, wd in ((LINE, 150), (BLANKET, 136)):
            d.line([P(*base), P(*hand)], fill=col_, width=int(wd * SS))
        d.line([P(base[0] - 68, base[1]), P(hand[0] - 60, hand[1] + 20)], fill=rim, width=int(8 * SS))
        d.ellipse([P(hand[0] - 70, hand[1] - 64), P(hand[0] + 70, hand[1] + 70)], fill=SKIN, outline=LINE, width=int(4 * SS))
        d.arc([P(hand[0] - 70, hand[1] - 64), P(hand[0] + 70, hand[1] + 70)], 110, 250, fill=rim, width=int(6 * SS))
    face = img.resize((W, H), Image.LANCZOS)
    out.alpha_composite(face)
    lmap = light_map((0, 900), col, 1.25 * inten, 900, ambient=(0.12, 0.12, 0.17))
    arr = lit(out, lmap)
    res = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    res.alpha_composite(blur.point(lambda v: v), (-380, 520)) if False else None
    dust(res, t, (0, 500, 700, 1500), col)
    return res


def render(t, clip, rng):
    a = acting(t)
    idx = max(i for i, s in enumerate(SHOTS) if s[0] <= t)
    t0, t1, kind, z0, z1 = SHOTS[idx]
    if kind == "profile":
        fr = shot_profile(t, clip, a)
        focus = (640, 1100)
    elif kind == "close":
        fr = shot_close(t, clip, a)
        focus = (600, 950)
    else:
        fr = shot_ots(t, clip, a, mirror=(kind == "ots2"))
        focus = (540, 1000)
    # slow camera move inside the shot
    z = lerp(z0, z1, smooth((t - t0) / (t1 - t0)))
    cw, ch = W / z, H / z
    cx = clamp(focus[0], cw / 2, W - cw / 2) + 4 * math.sin(t * 0.4)
    cy = clamp(focus[1], ch / 2, H - ch / 2) + 4 * math.cos(t * 0.35)
    fr = fr.crop((cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).resize((W, H), Image.BILINEAR)
    arr = np.asarray(fr.convert("RGB")).astype(np.float32)
    vig = np.clip(1.1 - (((XX - W / 2) / (W * 0.62)) ** 2 + ((YY - H / 2) / (H * 0.62)) ** 2) * 0.75, 0.25, 1)
    arr *= vig[:, :, None]
    arr += rng.normal(0, 3.5, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    # soft dip between shots
    for s_ in SHOTS[1:]:
        dt = abs(t - s_[0])
        if dt < 0.18:
            arr *= 0.35 + 0.65 * (dt / 0.18)
    fade = min(clamp(t / 0.6), clamp((DUR - t) / 0.9))
    arr *= fade
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def clip_frames():
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", CLIP, "-vf", f"fps={FPS}", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = CW * CH * 3
    last = None
    while True:
        buf = proc.stdout.read(n)
        if len(buf) < n:
            break
        last = Image.frombytes("RGB", (CW, CH), buf)
        yield last
    proc.wait()
    while True:
        yield last


def clip_at(t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", CLIP, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.frombytes("RGB", (CW, CH), raw)


def main():
    rng = np.random.default_rng(2)
    if "--frames" in sys.argv:
        for i in [int(v) for v in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            render(i / FPS, clip_at(i / FPS), rng).save(os.path.join(HERE, f"_preview_{i:04d}.png"))
        return
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", CLIP, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                            "-preset", "medium", "-crf", "20", "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={DUR - 0.9:.2f}:d=0.9", "-shortest",
                            "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for i, clip in zip(range(n), clip_frames()):
        enc.stdin.write(render(i / FPS, clip, rng).tobytes())
        if i % 120 == 0:
            print(f"frame {i}/{n}", flush=True)
    enc.stdin.close()
    enc.wait()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
