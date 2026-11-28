#!/usr/bin/env python3
"""Synthesize a small library of sound effects and music beds from code.

Everything here is generated from scratch (noise, sine waves, envelopes), so it is
ours: free for any use, no attribution needed (CC0).

  python3 tools/make_sfx.py            # writes assets/sfx/generated/ and assets/music/generated/
"""
import os
import subprocess

import numpy as np

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR = os.path.join(ROOT, "assets", "sfx", "generated")
MUSIC_DIR = os.path.join(ROOT, "assets", "music", "generated")
rng = np.random.default_rng(7)


# ---------------- building blocks ----------------
def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def noise(dur):
    return rng.standard_normal(int(SR * dur))


def env(n, attack, release, shape=2.0):
    """Attack/release envelope over n samples (attack/release as fractions of n)."""
    x = np.linspace(0, 1, n)
    a = np.clip(x / max(attack, 1e-4), 0, 1)
    r = np.clip((1 - x) / max(release, 1e-4), 0, 1)
    return (a * r) ** shape


def sweep_filter(sig, f0, f1, q=0.5):
    """Time-varying one-pole band-ish filter: low-pass at a cutoff sweeping f0 -> f1."""
    n = len(sig)
    cut = np.geomspace(f0, f1, n)
    alpha = 1 - np.exp(-2 * np.pi * cut / SR)
    out = np.zeros(n)
    lp = 0.0
    lp2 = 0.0
    for i in range(n):
        lp += alpha[i] * (sig[i] - lp)
        lp2 += alpha[i] * q * (lp - lp2)
        out[i] = lp - lp2 * 0.6
    return out


def lowpass(sig, cutoff):
    alpha = 1 - np.exp(-2 * np.pi * cutoff / SR)
    out = np.zeros_like(sig)
    y = 0.0
    for i in range(len(sig)):
        y += alpha * (sig[i] - y)
        out[i] = y
    return out


def tone(freq, dur, harmonics=(1.0,), decay=None):
    t = t_axis(dur)
    sig = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(harmonics))
    if decay:
        sig *= np.exp(-t / decay)
    return sig


def norm(sig, peak=0.9):
    m = np.max(np.abs(sig)) or 1
    return sig / m * peak


def reverb(sig, wet=0.25, delays=(0.029, 0.037, 0.043, 0.051), fb=0.5):
    out = sig.copy()
    for d in delays:
        k = int(SR * d)
        buf = np.zeros(len(sig) + k * 6)
        buf[: len(sig)] += sig
        for i in range(1, 6):
            buf[k * i: k * i + len(sig)] += sig * (fb ** i)
        out = out + wet / len(delays) * buf[: len(sig)]
    return out


def write(path, sig, stereo_width=0.0):
    sig = norm(sig)
    if stereo_width:
        d = int(SR * 0.012)
        right = np.concatenate([np.zeros(d), sig[:-d]])
        data = np.stack([sig, sig * (1 - stereo_width) + right * stereo_width], axis=1)
        ch = 2
    else:
        data, ch = sig, 1
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2").tobytes()
    ext = os.path.splitext(path)[1]
    codec = ["-c:a", "libmp3lame", "-b:a", "192k"] if ext == ".mp3" else ["-c:a", "pcm_s16le"]
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", str(ch),
                    "-i", "-", *codec, path], input=pcm, check=True)


# ---------------- sound effects ----------------
def whoosh(dur=0.6, f0=300, f1=6000):
    n = noise(dur)
    s = sweep_filter(n, f0, f1) * env(len(n), 0.55, 0.45, 1.6)
    return s


def sfx_library():
    lib = {}
    lib["whoosh-soft"] = whoosh(0.8, 200, 3000)
    lib["whoosh-fast"] = whoosh(0.35, 400, 8000)
    lib["whoosh-deep"] = lowpass(whoosh(1.0, 80, 1200), 1500) * 1.5
    lib["swoosh-reverse"] = whoosh(0.6, 6000, 300)[::-1]
    # whip pan: two quick whooshes stacked
    w = whoosh(0.3, 600, 9000)
    lib["whip-pan"] = np.concatenate([w, w[: len(w) // 2] * 0.6])
    # riser: rising noise + rising tone
    t = t_axis(2.5)
    rise = sweep_filter(noise(2.5), 200, 9000) * np.linspace(0, 1, len(t)) ** 2
    pitch = np.sin(2 * np.pi * np.cumsum(np.geomspace(150, 1200, len(t))) / SR) * np.linspace(0, 0.6, len(t)) ** 3
    lib["riser"] = rise + pitch
    lib["downlifter"] = lib["riser"][::-1] * env(len(t), 0.02, 0.6)
    # impacts
    t = t_axis(1.6)
    sub = np.sin(2 * np.pi * np.cumsum(np.geomspace(120, 35, len(t))) / SR) * np.exp(-t / 0.45)
    click = noise(1.6) * np.exp(-t / 0.015)
    lib["boom-hit"] = sub * 1.2 + lowpass(click, 3000) * 0.6
    t = t_axis(0.5)
    kick = np.sin(2 * np.pi * np.cumsum(np.geomspace(160, 45, len(t))) / SR) * np.exp(-t / 0.12)
    lib["punch-hit"] = kick + noise(0.5) * np.exp(-t / 0.02) * 0.4
    # pop / bubble
    t = t_axis(0.18)
    lib["pop"] = np.sin(2 * np.pi * np.cumsum(np.geomspace(300, 1100, len(t))) / SR) * np.exp(-t / 0.035)
    t = t_axis(0.12)
    lib["click"] = (noise(0.12) * np.exp(-t / 0.004) + np.sin(2 * np.pi * 2200 * t) * np.exp(-t / 0.01)) * 0.8
    # ding / sparkle
    lib["ding"] = reverb(tone(1318.5, 1.6, (1, 0.4, 0.15), decay=0.45), 0.35)
    sp = np.zeros(int(SR * 1.4))
    for k, f in enumerate([1568, 2093, 2637, 3136, 2349]):
        s = tone(f, 0.6, (1, 0.3), decay=0.12)
        st = int(SR * 0.09 * k)
        sp[st: st + len(s)] += s * (0.9 - 0.1 * k)
    lib["sparkle"] = reverb(sp, 0.4)
    # glitch: chopped noise + square bursts
    t = t_axis(0.6)
    g = np.sign(np.sin(2 * np.pi * 220 * t)) * 0.4 + noise(0.6) * 0.6
    gate = (np.floor(t * 40) % 3 != 0).astype(float) * (rng.random(len(t)) > 0.002)
    lib["glitch"] = g * np.repeat(rng.random(int(len(t) / 800) + 1) > 0.35, 800)[: len(t)] * gate
    # camera shutter
    t = t_axis(0.25)
    sh = noise(0.25) * (np.exp(-t / 0.01) + 0.6 * np.exp(-np.clip(t - 0.09, 0, None) / 0.012) * (t > 0.09))
    lib["camera-shutter"] = lowpass(sh, 6000)
    # heartbeat (two thumps), looped 4 times
    t = t_axis(0.9)
    thump = lambda: np.sin(2 * np.pi * 55 * t_axis(0.25)) * np.exp(-t_axis(0.25) / 0.06)
    hb = np.zeros(len(t))
    hb[: int(SR * 0.25)] += thump()
    hb[int(SR * 0.28): int(SR * 0.28) + int(SR * 0.25)] += thump() * 0.7
    lib["heartbeat"] = np.tile(hb, 4)
    # ambience loops
    r = noise(12)
    lib["rain-loop"] = lowpass(r, 5000) * 0.5 + (rng.random(len(r)) > 0.9993) * rng.standard_normal(len(r)) * 3
    wind = sweep_filter(noise(12), 150, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t_axis(12)))
    lib["wind-loop"] = wind
    # typing: random clicks
    ty = np.zeros(int(SR * 3))
    pos = 0
    while pos < len(ty) - SR // 10:
        c = lib["click"] * rng.uniform(0.4, 1.0)
        ty[pos: pos + len(c)] += c
        pos += int(SR * rng.uniform(0.07, 0.2))
    lib["typing"] = ty
    # heartbreak: crack + low groan
    t = t_axis(1.2)
    crack = noise(1.2) * np.exp(-t / 0.03) * 1.2
    groan = np.sin(2 * np.pi * np.cumsum(np.geomspace(220, 90, len(t))) / SR) * np.exp(-t / 0.5) * 0.5
    lib["heart-break"] = lowpass(crack, 4000) + groan
    return lib


# ---------------- music beds ----------------
NOTE = {n: 440 * 2 ** ((i - 9) / 12) for i, n in enumerate(
    ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def f(name, octave):
    return NOTE[name] * 2 ** (octave - 4)


def place(track, sig, at):
    i = int(SR * at)
    j = min(len(track), i + len(sig))
    track[i:j] += sig[: j - i]


def piano(freq, dur):
    s = tone(freq, dur, (1, 0.5, 0.25, 0.12, 0.06), decay=dur * 0.35)
    return s * env(len(s), 0.004, 0.2, 1)


def pad(freq, dur):
    t = t_axis(dur)
    s = sum(np.sin(2 * np.pi * freq * m * t + rng.uniform(0, 6)) / m for m in (1, 1.003, 2, 0.997))
    return lowpass(s, 1800) * env(len(s), 0.3, 0.3, 1)


def drums(bpm, bars, style):
    beat = 60 / bpm
    tr = np.zeros(int(SR * beat * 4 * bars) + SR)
    t = t_axis(0.4)
    kick = np.sin(2 * np.pi * np.cumsum(np.geomspace(140, 45, len(t))) / SR) * np.exp(-t / 0.11)
    snare = lowpass(noise(0.25), 6000) * np.exp(-t_axis(0.25) / 0.06) + np.sin(2 * np.pi * 190 * t_axis(0.25)) * np.exp(-t_axis(0.25) / 0.04)
    hat = (noise(0.06) - lowpass(noise(0.06), 7000)) * np.exp(-t_axis(0.06) / 0.015)
    for b in range(bars * 4):
        at = b * beat
        if style == "masti":
            place(tr, kick, at)
            if b % 2 == 1:
                place(tr, snare * 0.7, at)
            place(tr, hat * 0.5, at + beat / 2)
        else:  # lofi
            if b % 4 in (0, 2) or (b % 4 == 3 and b % 8 == 7):
                place(tr, kick * 0.8, at + (0.02 if b % 4 == 2 else 0))
            if b % 2 == 1:
                place(tr, snare * 0.45, at + 0.015)
            place(tr, hat * 0.25, at)
            place(tr, hat * 0.18, at + beat / 2 + 0.03)
    return tr


def music_library():
    lib = {}
    # 1) sad piano: Am - F - C - G, slow arpeggios with a soft pad
    bpm, bars = 70, 8
    beat = 60 / bpm
    prog = [("A", "C", "E"), ("F", "A", "C"), ("C", "E", "G"), ("G", "B", "D")]
    tr = np.zeros(int(SR * beat * 4 * bars) + SR * 3)
    for bar in range(bars):
        chord = prog[bar % 4]
        place(tr, pad(f(chord[0], 3), beat * 4) * 0.25, bar * 4 * beat)
        for k, step_ in enumerate([0, 1, 2, 1, 0, 2, 1, 2]):
            note = chord[step_]
            octave = 4 if step_ else 3
            place(tr, piano(f(note, octave + (1 if k >= 4 else 0)), beat * 1.6) * 0.5, (bar * 4 + k * 0.5) * beat)
    lib["sad-piano-70bpm"] = reverb(tr, 0.45, fb=0.6)
    # 2) lofi chill: Dm7 - G7 - Cmaj7 - Am7 with lazy drums
    bpm, bars = 82, 8
    beat = 60 / bpm
    prog = [("D", "F", "A", "C"), ("G", "B", "D", "F"), ("C", "E", "G", "B"), ("A", "C", "E", "G")]
    tr = drums(bpm, bars, "lofi") * 0.8
    for bar in range(bars):
        chord = prog[bar % 4]
        for k, n in enumerate(chord):
            place(tr, piano(f(n, 4 if k else 3), beat * 3.5) * 0.28, bar * 4 * beat + k * 0.02)
        place(tr, tone(f(chord[0], 2), beat * 3, (1, 0.3), decay=0.8) * 0.4, bar * 4 * beat)
    lib["lofi-chill-82bpm"] = lowpass(reverb(tr, 0.25), 6500)
    # 3) masti upbeat: C - G - Am - F, four-on-the-floor, plucky bass and chords
    bpm, bars = 120, 12
    beat = 60 / bpm
    prog = [("C", "E", "G"), ("G", "B", "D"), ("A", "C", "E"), ("F", "A", "C")]
    tr = drums(bpm, bars, "masti")
    for bar in range(bars):
        chord = prog[bar % 4]
        for b in range(4):
            place(tr, tone(f(chord[0], 2), beat * 0.45, (1, 0.5, 0.2), decay=0.12) * 0.55, (bar * 4 + b + 0.5) * beat)
            for n in chord:
                place(tr, tone(f(n, 4), beat * 0.3, (1, 0.6, 0.3), decay=0.08) * 0.18, (bar * 4 + b + 0.5) * beat)
    lib["masti-upbeat-120bpm"] = reverb(tr, 0.15)
    return lib


def main():
    os.makedirs(SFX_DIR, exist_ok=True)
    os.makedirs(MUSIC_DIR, exist_ok=True)
    for name, sig in sfx_library().items():
        write(os.path.join(SFX_DIR, f"{name}.wav"), sig)
        print("sfx  ", name)
    for name, sig in music_library().items():
        write(os.path.join(MUSIC_DIR, f"{name}.mp3"), sig, stereo_width=0.6)
        print("music", name)
    for d in (SFX_DIR, MUSIC_DIR):
        with open(os.path.join(d, "LICENSE.txt"), "w") as fh:
            fh.write("Generated from code by tools/make_sfx.py in this workspace. "
                     "Free for any use, no attribution needed (CC0 1.0).\n")


if __name__ == "__main__":
    main()
