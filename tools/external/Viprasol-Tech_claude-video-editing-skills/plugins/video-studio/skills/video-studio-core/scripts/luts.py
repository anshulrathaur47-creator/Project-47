#!/usr/bin/env python3
"""Deterministic .cube generator for Video Studio looks and log->Rec.709 input transforms.

usage: luts.py [--out DIR] [--size 33] [--only name1,name2]

Writes <CORE>/luts/<name>.cube (33^3, text). All looks work on display-referred Rec.709
gamma-encoded RGB in [0,1]. Skin-protected looks blend back toward the input inside a soft
skin-hue mask computed per lattice point (hue 0-50 deg, moderate saturation).

Log transforms (slog3, vlog, clog3, applelog, flog) decode the published log curve to scene
linear, convert the camera gamut to Rec.709 primaries (matrices built from published
chromaticities), apply a gentle filmic tone map and encode with a 2.4 display gamma.
They are APPROXIMATE technical conversions, not manufacturer LUTs: prefer the official LUT
(plan "color": {"lut": path}) when you have it.
"""
import argparse
import os
import numpy as np
import sys as _sys
for _st in (_sys.stdout, _sys.stderr):  # UTF-8 output on Windows (Devanagari logs)
    if hasattr(_st, "reconfigure"):
        _st.reconfigure(encoding="utf-8", errors="replace")

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUT_DIR = os.path.join(CORE, "luts")
SIZE = 33
LUMA = np.array([0.2126, 0.7152, 0.0722])


# ---------------------------------------------------------------- lattice + io
def lattice(n: int = SIZE) -> np.ndarray:
    """(n^3, 3) RGB grid in .cube order: red fastest, then green, then blue."""
    v = np.linspace(0.0, 1.0, n)
    b, g, r = np.meshgrid(v, v, v, indexing="ij")
    return np.stack([r.ravel(), g.ravel(), b.ravel()], axis=1)


def write_cube(path: str, rgb: np.ndarray, title: str, n: int = SIZE) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    rgb = np.clip(rgb, 0.0, 1.0)
    with open(path, "w", newline="\n") as f:
        f.write(f'TITLE "{title}"\nLUT_3D_SIZE {n}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        np.savetxt(f, rgb, fmt="%.4f")


def read_cube(path: str) -> tuple[np.ndarray, int]:
    n, rows = SIZE, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s[0] == "#" or s.startswith(("TITLE", "DOMAIN")):
                continue
            if s.startswith("LUT_3D_SIZE"):
                n = int(s.split()[1]); continue
            rows.append([float(x) for x in s.split()[:3]])
    return np.array(rows), n


# ---------------------------------------------------------------- colour toolkit
def luma(c):
    return (c @ LUMA)[:, None]


def sat(c, s):
    l = luma(c)
    return l + (c - l) * s


def scurve(c, k, pivot=0.5):
    """Smooth S-curve (k>0 more contrast, k<0 flatter) fixed at 0, pivot, 1. Monotone for |k|<1."""
    x = np.clip(c, 0, 1)
    lo = x < pivot
    t = np.where(lo, x / pivot, (x - pivot) / (1 - pivot))
    bend = np.where(lo, -np.sin(np.pi * t) * pivot, np.sin(np.pi * t) * (1 - pivot)) * k / np.pi
    return x - bend


def levels(c, black=0.0, white=1.0, gamma=1.0):
    """Output levels (lift/fade = black>0, roll-off = white<1) plus a power gamma (>1 darker)."""
    return black + (white - black) * np.clip(c, 0, 1) ** gamma


def shoulder(c, start=0.8, k=0.6):
    """Soft highlight roll-off above `start`: slope 1 at start easing to 1-k; white lands at 1-k*(1-start)/2."""
    x = np.clip(c, 0, 1)
    u, r = np.maximum(x - start, 0), 1 - start
    return x - k * u * u / (2 * r)


def tone(c, shadows=(0, 0, 0), highs=(0, 0, 0), mids=(0, 0, 0)):
    """Split-tone: add RGB offsets weighted toward shadows / mids / highlights."""
    l = np.clip(luma(c), 0, 1)
    ws, wh = (1 - l) ** 2, l ** 2
    wm = 1 - ws - wh
    return c + ws * np.array(shadows) + wh * np.array(highs) + wm * np.array(mids)


def wb(c, warm=0.0, tint=0.0):
    """warm>0 = warmer (R up, B down); tint>0 = greener."""
    return c * np.array([1 + warm, 1 + tint, 1 - warm])


def mix(c, m):
    return c @ np.array(m).T


def rgb2hsv(c):
    c = np.clip(c, 0, 1)
    mx, mn = c.max(1), c.min(1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-9
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    rm = nz & (mx == r); gm = nz & (mx == g) & ~rm; bm = nz & ~rm & ~gm
    h[rm] = ((g - b)[rm] / d[rm]) % 6
    h[gm] = (b - r)[gm] / d[gm] + 2
    h[bm] = (r - g)[bm] / d[bm] + 4
    s = np.where(mx > 1e-9, d / np.maximum(mx, 1e-9), 0)
    return np.stack([h * 60.0, s, mx], 1)


def hsv2rgb(hsv):
    h, s, v = hsv[:, 0] % 360 / 60.0, np.clip(hsv[:, 1], 0, 1), hsv[:, 2]
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    table = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]
    out = np.zeros((len(h), 3))
    for k, (r, g, b) in enumerate(table):
        m = i == k
        out[m] = np.stack([r[m], g[m], b[m]], 1)
    return out


def hue_w(hue, center, width):
    """Smooth 0..1 weight for hues within +-width of center (degrees, wraps)."""
    d = np.abs((hue - center + 180) % 360 - 180)
    return np.clip(1 - d / width, 0, 1) ** 2 * (3 - 2 * np.clip(1 - d / width, 0, 1))


def hue_adjust(c, center, width, shift=0.0, satmul=1.0, valmul=1.0):
    """Secondary: rotate / saturate / brighten a hue range (a qualifier in LUT form)."""
    hsv = rgb2hsv(c)
    w = hue_w(hsv[:, 0], center, width) * np.clip(hsv[:, 1] * 4, 0, 1)
    hsv[:, 0] += shift * w
    hsv[:, 1] *= 1 + (satmul - 1) * w
    hsv[:, 2] *= 1 + (valmul - 1) * w
    return hsv2rgb(hsv)


def skin_mask(c):
    """Soft skin weight in the LUT domain: hue ~0-50 deg (centre 22), sat 0.12-0.7, not too dark."""
    hsv = rgb2hsv(c)
    h, s, v = hsv[:, 0], hsv[:, 1], hsv[:, 2]
    wh = hue_w(h, 22, 30)
    ws = np.clip((s - 0.08) / 0.1, 0, 1) * np.clip((0.78 - s) / 0.15, 0, 1)
    wv = np.clip((v - 0.12) / 0.15, 0, 1)
    return (wh * ws * wv)[:, None]


def overlay(a, b):
    return np.where(a < 0.5, 2 * a * b, 1 - 2 * (1 - a) * (1 - b))


# ---------------------------------------------------------------- creative looks
# Each entry: (function(c) -> c, skin_protect 0..1, "use for")
def _portra(c):
    c = levels(c, 0.03, 0.97); c = shoulder(c, 0.75); c = scurve(c, -0.08)
    c = tone(c, (-0.012, 0.008, 0.016), (0.03, 0.015, -0.02)); return sat(c, 0.9)


def _k2383(c):
    c = scurve(c, 0.38, 0.45); c = tone(c, (-0.025, 0.004, 0.022), (0.035, 0.012, -0.035))
    c = shoulder(c, 0.8); c = sat(c, 1.02)
    return levels(c, 0.012, 0.98)


def _ekta(c):
    c = scurve(c, 0.3); c = wb(c, -0.03); c = tone(c, (-0.01, 0.0, 0.03)); c = sat(c, 1.25)
    return hue_adjust(c, 220, 40, -6, 1.15)


def _eterna(c):
    c = levels(c, 0.04, 0.95); c = scurve(c, -0.05); c = hue_adjust(c, 110, 50, 18, 0.85)
    c = tone(c, (-0.01, 0.01, 0.02), (0.01, 0.005, -0.008)); return sat(c, 0.72)


def _velvia(c):
    c = scurve(c, 0.35); c = sat(c, 1.45); c = hue_adjust(c, 120, 50, 0, 1.15, 0.95)
    return tone(c, (0.01, -0.01, 0.02))


def _cinestill(c):
    c = wb(c, -0.06); c = scurve(c, 0.22); c = tone(c, (-0.03, 0.01, 0.03), (0.04, 0.01, -0.01))
    c = hue_adjust(c, 0, 30, 0, 1.2); return sat(c, 1.05)


def _kodachrome(c):
    c = scurve(c, 0.35, 0.47); c = wb(c, 0.02); c = sat(c, 1.2)
    c = hue_adjust(c, 0, 25, 0, 1.15); c = hue_adjust(c, 220, 40, 0, 1.15, 0.92)
    return hue_adjust(c, 110, 40, -8, 0.95, 0.9)


def _bleach(c):
    l = np.repeat(luma(c), 3, 1); c = overlay(c, l) * 0.6 + c * 0.4
    return sat(scurve(c, 0.3), 0.45)


def _cross(c):
    r = scurve(c[:, :1], 0.5); g = scurve(c[:, 1:2], 0.35); b = levels(c[:, 2:], 0.12, 0.85)
    return sat(np.hstack([r, g, b]), 1.1)


def _golden(c):
    c = wb(c, 0.07); c = tone(c, (0.01, 0.0, -0.01), (0.06, 0.03, -0.04)); c = scurve(c, 0.1)
    return sat(c, 1.1)


def _bluehour(c):
    c = wb(c, -0.08); c = tone(c, (-0.01, 0.0, 0.05), (0.02, 0.0, 0.03)); c = levels(c, 0, 1, 1.08)
    return sat(c, 0.95)


def _moody(c):
    c = levels(c, 0.03, 0.97, 1.18); c = scurve(c, 0.25); c = tone(c, (-0.02, 0.01, 0.025))
    return sat(c, 0.7)


def _highkey(c):
    return sat(scurve(levels(c, 0.05, 1.0, 0.72), -0.15), 0.9)


def _lowkey(c):
    return sat(scurve(levels(c, 0.0, 0.97, 1.35), 0.35), 0.9)


def _desert(c):
    c = wb(c, 0.07); c = tone(c, (0.03, 0.015, -0.01), (0.03, 0.02, -0.03)); c = scurve(c, 0.2)
    return hue_adjust(c, 210, 40, -20, 0.9)


def _nordic(c):
    c = wb(c, -0.04); c = levels(c, 0.05, 0.97); c = tone(c, (-0.01, 0.005, 0.02)); return sat(c, 0.65)


def _horror(c):
    c = sat(c, 0.55); c = tone(c, (-0.02, 0.03, 0.01), (-0.01, 0.03, 0.0)); c = levels(c, 0.0, 0.95, 1.25)
    return scurve(c, 0.3)


def _dreamy(c):
    c = levels(c, 0.06, 0.98); c = scurve(c, -0.12); c = tone(c, highs=(0.03, 0.0, 0.02)); return sat(c, 0.85)


def _finance(c):
    c = tone(c, (-0.012, 0.0, 0.035), (0.0, 0.0, 0.005)); c = scurve(c, 0.15); return sat(c, 0.95)


def _indian(c):
    c = wb(c, 0.05); c = tone(c, (0.01, 0.0, -0.01), (0.05, 0.035, -0.03))
    c = hue_adjust(c, 0, 30, 0, 1.25); c = hue_adjust(c, 45, 25, 0, 1.25); c = scurve(c, 0.15)
    return sat(c, 1.05)


def _wpastel(c):
    c = levels(c, 0.06, 0.96); c = scurve(c, -0.1); c = tone(c, highs=(0.02, 0.01, 0.0)); return sat(c, 0.8)


def _dfn(c):
    c = levels(c, 0.0, 0.62, 1.6); c = sat(c, 0.45); c = tone(c, (-0.01, 0.005, 0.05), (-0.02, 0.0, 0.03))
    return scurve(c, 0.15)


def _infrared(c):
    c = mix(c, [[0.15, 1.0, -0.15], [0.9, 0.1, 0.0], [0.0, 0.1, 0.9]]); return sat(scurve(c, 0.15), 1.15)


def _selred(c):
    hsv = rgb2hsv(c)
    w = (hue_w(hsv[:, 0], 0, 25) * np.clip((hsv[:, 1] - 0.2) / 0.2, 0, 1))[:, None]
    return scurve(sat(c, w), 0.2)


def _matrix(c):
    c = mix(c, [[0.8, 0.1, 0.0], [0.05, 1.0, 0.05], [0.0, 0.15, 0.7]]); c = tone(c, (-0.01, 0.025, 0.0))
    return sat(scurve(c, 0.3), 0.7)


def _tealorange(c):
    c = hue_adjust(c, 200, 70, -15, 1.1); c = hue_adjust(c, 120, 45, 45, 0.7); c = hue_adjust(c, 30, 30, 0, 1.15)
    c = tone(c, (-0.03, 0.01, 0.03), (0.04, 0.01, -0.03)); return scurve(c, 0.2)


def _clean(c):
    return sat(scurve(levels(c, 0, 1, 0.95), 0.15), 1.08)


def _docu(c):
    return sat(wb(scurve(c, 0.08), 0.01), 0.95)


def _mvneon(c):
    c = tone(c, (0.03, -0.02, 0.06), (0.0, 0.03, 0.05)); c = hue_adjust(c, 60, 30, -20, 1.0)
    return sat(scurve(c, 0.3), 1.4)


def _sepia(c):
    l = np.repeat(luma(c), 3, 1)
    return levels(scurve(l, 0.1), 0.03, 0.97) * np.array([1.0, 0.86, 0.66]) + np.array([0.02, 0.01, 0.0])


def _twostrip(c):
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    c = np.stack([r, 0.85 * g + 0.15 * b, 0.6 * g + 0.4 * b], 1)
    return scurve(wb(c, 0.02), 0.15)


def _cyber(c):
    c = hue_adjust(c, 120, 50, 50, 1.1); c = tone(c, (0.04, -0.02, 0.08), (-0.03, 0.03, 0.04))
    return sat(scurve(c, 0.3), 1.3)


def _seventies(c):
    c = wb(c, 0.05); c = hue_adjust(c, 110, 50, -18, 0.8); c = levels(c, 0.05, 0.95)
    c = tone(c, (0.02, 0.01, -0.01), (0.02, 0.015, -0.02)); return sat(c, 0.85)


def _camcorder(c):
    c = levels(c, 0.04, 1.0) * 1.06; c = wb(c, -0.015, 0.01); return sat(scurve(c, -0.05), 1.15)


def _sunset(c):
    c = tone(c, (0.03, -0.01, 0.04), (0.08, 0.02, -0.04)); c = scurve(c, 0.15); return sat(c, 1.2)


def _coolcorp(c):
    return sat(scurve(wb(c, -0.03), 0.1), 0.9)


def _food(c):
    c = hue_adjust(c, 25, 40, 0, 1.3); c = hue_adjust(c, 55, 25, 0, 1.2); c = wb(c, 0.02)
    return sat(scurve(levels(c, 0, 1, 0.95), 0.2), 1.12)


def _realestate(c):
    c = levels(c, 0.02, 1.0, 0.8); c = hue_adjust(c, 210, 35, 0, 1.2); return sat(scurve(c, 0.08), 1.08)


def _gaming(c):
    return sat(wb(scurve(c, 0.3), -0.01), 1.45)


LOOKS = {
    "portra": (_portra, 0.3, "warm, soft-contrast portraits, lifestyle, interviews"),
    "kodak-2383": (_k2383, 0.25, "cinematic print-film contrast for narrative / brand films"),
    "ektachrome": (_ekta, 0.35, "punchy cool slide-film: travel, outdoors, product"),
    "fuji-eterna": (_eterna, 0.3, "muted cinema neg: drama, documentary, moody brand"),
    "fuji-velvia": (_velvia, 0.5, "vivid landscapes, nature, travel B-roll"),
    "cinestill-800t": (_cinestill, 0.3, "night city / neon / tungsten scenes (pair with halation)"),
    "kodachrome": (_kodachrome, 0.35, "rich retro colour, nostalgia, travel"),
    "bleach-bypass": (_bleach, 0.0, "gritty high-contrast desaturated: action, war, sport"),
    "cross-process": (_cross, 0.2, "fashion / music lo-fi: yellow highs, blue shadows"),
    "golden-hour": (_golden, 0.3, "warm sunset feel on daylight footage"),
    "blue-hour": (_bluehour, 0.3, "cool dusk, calm, melancholy"),
    "moody": (_moody, 0.4, "dark desaturated storytelling, reflective talking heads"),
    "high-key": (_highkey, 0.2, "bright airy beauty, wellness, lifestyle"),
    "low-key": (_lowkey, 0.2, "dramatic dark, thriller, premium product"),
    "desert": (_desert, 0.3, "hot dusty western, adventure"),
    "nordic": (_nordic, 0.4, "cool clean minimal, Scandinavian lifestyle"),
    "horror-green": (_horror, 0.15, "horror, unease, sickly green-cyan"),
    "dreamy": (_dreamy, 0.3, "soft romantic, memories, flashbacks (adds glow)"),
    "finance-navy": (_finance, 0.6, "finance / trading / B2B explainers, trustworthy navy"),
    "indian-wedding": (_indian, 0.65, "Indian wedding: warm gold, rich reds, skin kept natural"),
    "wedding-pastel": (_wpastel, 0.5, "western wedding, soft pastel, lifted blacks"),
    "day-for-night": (_dfn, 0.0, "fake night from daylight footage"),
    "infrared": (_infrared, 0.0, "Aerochrome-style false colour, surreal music videos"),
    "selective-red": (_selred, 0.0, "B&W with reds kept: emphasis, art pieces"),
    "matrix": (_matrix, 0.2, "green tech / hacker / sci-fi"),
    "teal-orange-pro": (_tealorange, 0.7, "blockbuster teal & orange with natural skin"),
    "clean-commercial": (_clean, 0.3, "ads, product, corporate: clean bright neutral"),
    "documentary-natural": (_docu, 0.3, "true-to-life documentary / news, minimal look"),
    "music-video-neon": (_mvneon, 0.4, "music videos, nightlife, magenta/cyan neon"),
    "sepia": (_sepia, 0.0, "old photo, history, flashback"),
    "two-strip": (_twostrip, 0.0, "1930s two-strip Technicolor red/cyan"),
    "cyberpunk": (_cyber, 0.4, "futuristic magenta/teal night, gaming, tech"),
    "vintage-70s": (_seventies, 0.3, "70s faded warm olive, retro"),
    "90s-camcorder": (_camcorder, 0.2, "home video / VHS-C nostalgia (adds softness)"),
    "sunset": (_sunset, 0.3, "strong warm/magenta sky, romantic, travel"),
    "cool-corporate": (_coolcorp, 0.5, "SaaS, tech, corporate interviews: cool neutral"),
    "food-pop": (_food, 0.3, "food: rich warm reds/oranges/yellows"),
    "real-estate-bright": (_realestate, 0.2, "real estate / interiors: bright, open shadows, blue sky"),
    "gaming-vivid": (_gaming, 0.3, "gaming, esports, high-energy social"),
}


def build_look(name: str, n: int = SIZE) -> np.ndarray:
    fn, protect, _ = LOOKS[name]
    c = lattice(n)
    out = np.clip(fn(c.copy()), 0, 1)
    if protect:
        w = skin_mask(c) * protect
        out = out * (1 - w) + c * w
    return np.clip(out, 0, 1)


# ---------------------------------------------------------------- log -> Rec.709 (approximate)
def _rgb2xyz(prim, white=(0.3127, 0.3290)):
    xy = np.array(prim + [white])
    XYZ = np.stack([xy[:, 0] / xy[:, 1], np.ones(4), (1 - xy[:, 0] - xy[:, 1]) / xy[:, 1]], 1)
    S = np.linalg.solve(XYZ[:3].T, XYZ[3])
    return XYZ[:3].T * S


REC709 = [(0.64, 0.33), (0.30, 0.60), (0.15, 0.06)]
GAMUTS = {
    "sgamut3cine": [(0.766, 0.275), (0.225, 0.800), (0.089, -0.087)],
    "vgamut": [(0.730, 0.280), (0.165, 0.840), (0.100, -0.030)],
    "cinemagamut": [(0.740, 0.270), (0.170, 1.140), (0.080, -0.100)],
    "rec2020": [(0.708, 0.292), (0.170, 0.797), (0.131, 0.046)],
}


def _ire_to_code(v):
    """File values arrive as legal-range-expanded RGB (IRE 0..1); log specs use 10-bit code/1023."""
    return (64 + 876 * v) / 1023


def slog3(v):
    x = _ire_to_code(v)
    return np.where(x >= 171.2102946929 / 1023, 10 ** ((x * 1023 - 420) / 261.5) * 0.19 - 0.01,
                    (x * 1023 - 95) * 0.01125 / (171.2102946929 - 95))


def vlog(v):
    x = _ire_to_code(v)
    return np.where(x < 0.181, (x - 0.125) / 5.6, 10 ** ((x - 0.598206) / 0.241514) - 0.00873)


def clog3(x):
    return np.where(x < 0.097465473, -(10 ** ((0.12783901 - x) / 0.36726845) - 1) / 14.98325,
                    np.where(x <= 0.15277891, (x - 0.12512219) / 1.9754798,
                             (10 ** ((x - 0.12240537) / 0.36726845) - 1) / 14.98325)) * 0.9


def applelog(x):
    R0, Rt, c, b, g, be = -0.05641088, 0.01, 47.28711236, 0.00964052, 0.08550479, 0.69336945
    Pt = c * (Rt - R0) ** 2
    return np.where(x >= Pt, 2 ** ((x - be) / g) - b, np.where(x > 0, np.sqrt(np.maximum(x, 0) / c) + R0, R0))


def flog(x):
    a, b, c, d, e, f = 0.555556, 0.009468, 0.344676, 0.790453, 8.735631, 0.092864
    return np.where(x >= 0.100537775223865, (10 ** ((x - d) / c) - b) / a, (x - f) / e)


LOGS = {  # name: (decode, gamut, note)
    "slog3": (slog3, "sgamut3cine", "Sony S-Log3 / S-Gamut3.Cine"),
    "vlog": (vlog, "vgamut", "Panasonic V-Log / V-Gamut"),
    "clog3": (clog3, "cinemagamut", "Canon Log 3 / Cinema Gamut"),
    "applelog": (applelog, "rec2020", "Apple Log / Rec.2020 gamut"),
    "flog": (flog, "rec2020", "Fujifilm F-Log / F-Gamut (Rec.2020)"),
}


def _tonemap(lin):
    """Filmic-ish display transform: scene-linear (0.18 grey) -> display-linear, soft shoulder."""
    x = np.maximum(lin, 0) * 1.1
    y = x * (1 + x / 16.0) / (1 + x)  # extended Reinhard, white point 4.0
    return np.clip(y, 0, 1) ** (1 / 2.4)


def build_log(name: str, n: int = SIZE) -> np.ndarray:
    dec, gamut, _ = LOGS[name]
    c = lattice(n)
    lin = dec(c)
    M = np.linalg.inv(_rgb2xyz(REC709)) @ _rgb2xyz(GAMUTS[gamut])
    lin709 = lin @ M.T
    lin709 = np.maximum(lin709, 0)  # ponytail: hard gamut clip, a soft gamut compressor if out-of-gamut neon matters
    return _tonemap(lin709)


# ---------------------------------------------------------------- main
def generate(out_dir: str = LUT_DIR, n: int = SIZE, only=None) -> list[str]:
    written = []
    for name in LOOKS:
        if only and name not in only:
            continue
        p = os.path.join(out_dir, f"{name}.cube")
        write_cube(p, build_look(name, n), f"Video Studio look {name}", n); written.append(p)
    for name, (_, _, note) in LOGS.items():
        if only and f"log-{name}" not in only and name not in only:
            continue
        p = os.path.join(out_dir, f"log-{name}-to-709.cube")
        write_cube(p, build_log(name, n), f"APPROXIMATE {note} to Rec.709 (not a manufacturer LUT)", n)
        written.append(p)
    return written


def _selftest():
    c = lattice(9)
    assert np.allclose(hsv2rgb(rgb2hsv(c)), c, atol=1e-6)
    assert np.all(np.diff(scurve(np.linspace(0, 1, 101)[:, None], 0.5)[:, 0]) >= 0)
    for name in LOGS:  # 18% grey should land in a sane display range
        dec = LOGS[name][0]
        grey = {"slog3": 0.41, "vlog": 0.42, "clog3": 0.343, "applelog": 0.488, "flog": 0.459}[name]
        y = float(_tonemap(np.array([[dec(np.array(grey))]]))[0, 0])
        assert 0.3 < y < 0.6, (name, y)
    skin = np.array([[194, 150, 130], [115, 82, 68]]) / 255.0
    assert np.all(skin_mask(skin) > 0.5) and skin_mask(np.array([[0.2, 0.4, 0.8]]))[0, 0] < 0.05


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=LUT_DIR)
    ap.add_argument("--size", type=int, default=SIZE)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    _selftest()
    files = generate(a.out, a.size, set(x for x in a.only.split(",") if x) or None)
    print(f"[video-studio] wrote {len(files)} LUTs to {a.out}")
