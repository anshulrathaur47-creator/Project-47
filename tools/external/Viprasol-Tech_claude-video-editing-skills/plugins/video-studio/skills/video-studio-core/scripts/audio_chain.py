#!/usr/bin/env python3
"""Audio post-production for Video Studio: dialogue chain, procedural SFX, music bed + ducking,
room-tone fill and platform loudness. Importable module + CLI. numpy + FFmpeg only.

Public API (used by finish.py):
  LOUDNESS                                   platform -> {"I","TP","LRA","note"}
  voice_chain(cfg=None) -> str               FFmpeg filter chain for dialogue
  duck_filter(cfg=None, words=None) -> str   chain applied as "[music][key]<chain>[out]"
  measure(path) -> {"I","TP","LRA","threshold"}         ebur128, true peak
  loudnorm_two_pass(in_path, out_path, target=-14, tp=-1, lra=11, extra_filters="", sr=48000) -> dict
  SFX                                        name -> lavfi source string | numpy synth function
  sfx_input_args(kind, cache_dir) -> list    ffmpeg input args (-f lavfi -i ... | -i cached.wav)
  render_sfx(kind, out_path)                 write one SFX to a WAV (preview / QC)
  room_tone(src_path, out_path, seconds=20) -> floor dBFS | None
  build_mix_graph(plan, info, dur, platform=None, pdir=".", work=None, first_input=1)
        -> (extra_inputs, filter_lines, "[aout]")

CLI:
  audio_chain.py measure FILE [--platform youtube]
  audio_chain.py loudnorm IN OUT [--platform youtube] [--voice '{"eq":"clear"}']
  audio_chain.py voice IN OUT [--cfg '{"denoise":"strong","deess":true}']
  audio_chain.py sfx KIND --out x.wav     |   audio_chain.py sfx --all --out-dir DIR
  audio_chain.py list-sfx

This file is deliberately one module (> 800 lines) because the SFX library is data-like:
one short synth function per sound.
"""
import argparse, hashlib, json, math, os, re, struct, subprocess, sys, tempfile, zlib
import numpy as np
from vs_common import _compat, die, load_json, log, need, probe, run

SR = 48000

# ---------------------------------------------------------------- loudness targets
LOUDNESS = {
    # Only Spotify, Apple, Netflix, EBU and ATSC publish numbers; web/social -14 is observed practice.
    "youtube": {"I": -14, "TP": -1, "LRA": 11, "note": "observed, not published; YouTube only turns loud uploads down"},
    "tiktok": {"I": -14, "TP": -1, "LRA": 7, "note": "no published target; phone speakers -> keep LRA 5-8"},
    "reels": {"I": -14, "TP": -1, "LRA": 7, "note": "no published target"},
    "shorts": {"I": -14, "TP": -1, "LRA": 7, "note": "as YouTube"},
    "social": {"I": -14, "TP": -1, "LRA": 7, "note": "generic social"},
    "spotify": {"I": -14, "TP": -1, "LRA": 9, "note": "official; use TP -2 if master is louder than -14"},
    "podcast": {"I": -16, "TP": -1, "LRA": 8, "note": "stereo; mono podcasts -19"},
    "apple": {"I": -16, "TP": -1, "LRA": 8, "note": "Apple Podcasts -16 +/-1 LKFS"},
    "broadcast-eu": {"I": -23, "TP": -1, "LRA": 15, "note": "EBU R128 +/-0.5 LU, LRA up to ~20"},
    "broadcast-us": {"I": -24, "TP": -2, "LRA": 15, "note": "ATSC A/85 (CALM Act)"},
    "netflix": {"I": -27, "TP": -2, "LRA": 18, "note": "dialogue-gated +/-2 LU; this tool measures full-programme, "
                "so treat as approximate (full-programme ~ -24)"},
    "cinema": {"I": -27, "TP": -2, "LRA": 20, "note": "no LUFS spec: theatrical is calibrated to 85 dB SPL monitoring; "
               "-27 dialogue is the nearest proxy"},
}
LOUDNESS["instagram"] = LOUDNESS["reels"]
LOUDNESS["facebook"] = LOUDNESS["youtube"]
LOUDNESS["ebu"] = LOUDNESS["broadcast-eu"]
LOUDNESS["atsc"] = LOUDNESS["broadcast-us"]


def db2lin(db):
    return 10 ** (db / 20.0)


def ff_path(p):
    """Quote a file path for use inside a filter option (Windows drive colon escaped)."""
    return "'" + os.path.abspath(p).replace("\\", "/").replace(":", "\\:") + "'"


# ---------------------------------------------------------------- dialogue chain
VOICE_HPF = {"male": 80, "female": 110, "auto": 80}
WIND_HPF, BUTTER4_Q = 100, (0.5412, 1.3066)  # phone/outdoor: 4th-order Butterworth (24 dB/oct) = two biquads
# (freq, width_type, width, gain_dB) per preset; body/mud move up for female voices.
EQ = {
    "clear": lambda b, m: [(m, "q", 1.0, -3), (900, "q", 1.4, -1.5), (3500, "q", 1.0, 2.5), (11000, "h", 3000, 1.5)],
    "warm": lambda b, m: [(b, "q", 0.9, 2), (m, "q", 1.0, -2), (3000, "q", 1.0, 1), (9000, "h", 3000, -1.5)],
    "broadcast": lambda b, m: [(b, "q", 0.9, 2), (m, "q", 1.0, -3), (3000, "q", 1.0, 3), (6500, "q", 2.0, -1), (12000, "h", 3000, 1)],
    "phone": lambda b, m: [(1500, "q", 0.8, 4)],
    "radio": lambda b, m: [(1000, "q", 0.7, 3), (m, "q", 1.0, -2)],
}
EQ_BANDLIMIT = {"phone": (300, 3400), "radio": (200, 5000)}


def voice_chain(cfg=None):
    """FFmpeg filter chain (no labels) for dialogue. Order: HPF -> de-hum -> de-click -> de-noise ->
    EQ -> de-ess -> gate -> compressor -> soft limiter.
    cfg (all optional): {"denoise": true|"light"|"strong"|false, "rnnoise": "model.rnnn", "dehum": 50|60,
      "deess": true|0..1, "declick": true, "eq": "clear|warm|broadcast|phone|radio|off", "compress": true,
      "gate": false, "voice": "male|female|auto", "hpf": Hz, "wind": true}
    "wind" (default true): wind/handling-rumble high-pass, 4th order at max(voice HPF, 100 Hz) - phone and
    outdoor audio keep most of their noise below 100 Hz. false: gentle 2nd order at the voice HPF (studio mic).
    Defaults: light denoise + highpass + compress. cfg False -> "anull"."""
    if cfg is False:
        return "anull"
    c = dict(cfg or {})
    voice = c.get("voice", "auto")
    wind = c.get("wind", True)
    hz = c.get("hpf", max(VOICE_HPF.get(voice, 80), WIND_HPF if wind else 0))
    f = [f"highpass=f={hz}:p=2:t=q:w={q}" for q in BUTTER4_Q] if wind else [f"highpass=f={hz}:p=2"]
    if c.get("dehum"):
        base = int(c["dehum"])
        f += [f"equalizer=f={base * k}:t=q:w=30:g=-30" for k in range(1, 5)]
    if c.get("declick"):
        f.append("adeclick=w=20:o=75:t=4")
    dn = c.get("denoise", "light")
    if c.get("rnnoise"):
        f.append(f"arnndn=m={ff_path(c['rnnoise'])}:mix=0.85")
    elif dn:
        nr, nf = {"light": (10, -50), "strong": (20, -40)}.get(dn, (12, -45))
        f.append(f"afftdn=nr={nr}:nf={nf}:tn=1")
    eq = c.get("eq", "off")
    if eq in EQ:
        body, mud = (200, 400) if voice == "female" else (120, 300)
        if eq in EQ_BANDLIMIT:
            lo, hi = EQ_BANDLIMIT[eq]
            f += [f"highpass=f={lo}:p=2", f"lowpass=f={hi}:p=2"]
        for fr, t, w, g in EQ[eq](body, mud):
            f.append(f"highshelf=f={fr}:g={g}" if t == "h" else f"equalizer=f={fr}:t={t}:w={w}:g={g}")
    elif eq not in ("off", None, False):
        log(f"unknown eq preset '{eq}', skipping")
    if c.get("deess"):
        i = 0.4 if c["deess"] is True else float(c["deess"])
        f.append(f"deesser=i={i}:m=0.5:f=0.5:s=o")
    if c.get("gate"):
        f.append("agate=mode=downward:range=0.25:threshold=0.015:ratio=2:attack=10:release=250")
    if c.get("compress", True):
        # threshold 0.1 linear ~ -20 dBFS, makeup 2 linear ~ +6 dB
        f.append("acompressor=threshold=0.1:ratio=3:attack=10:release=120:makeup=2:knee=2.83")
    f.append("alimiter=limit=0.95:level=disabled:attack=5:release=50:latency=1")
    return ",".join(f)


# ---------------------------------------------------------------- measuring / normalising
def measure(path):
    """Integrated loudness (LUFS), true peak (dBTP) and LRA (LU) of a file's audio via ebur128."""
    need("ffmpeg")
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af",
                        "ebur128=peak=true:framelog=verbose", "-f", "null", "-"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
    if p.returncode != 0:
        die(f"measure failed for {path}: {p.stderr.strip()[-400:]}")
    s = p.stderr[p.stderr.rfind("Summary:"):]
    get = lambda pat: float(re.search(pat, s).group(1))
    return {"I": get(r"I:\s+(-?[\d.]+|-inf)") if "I:" in s else None, "LRA": get(r"LRA:\s+(-?[\d.]+)"),
            "TP": get(r"Peak:\s+(-?[\d.]+|-inf)"), "threshold": get(r"Threshold:\s+(-?[\d.]+)")}


def _loudnorm_json(stderr):
    j = stderr[stderr.rfind("{"):stderr.rfind("}") + 1]
    return json.loads(j)


def loudnorm_two_pass(in_path, out_path, target=-14, tp=-1, lra=11, extra_filters="", sr=48000):
    """Two-pass linear loudnorm. Pass 1 measures (print_format=json) after extra_filters; pass 2 applies
    measured values with linear=true. If the gain would break the TP ceiling (loudnorm would then fall back to
    dynamic mode), the gain + an oversampled peak limiter are applied first so the final pass stays linear.
    Video is stream-copied when present. Returns {"pass1": {...}, "pass2": {...}, "result": measure(out)}."""
    pre = (extra_filters + ",") if extra_filters else ""
    if os.path.splitext(out_path)[1].lower() in (".mp4", ".mov", ".m4a", ".mkv", ".aac", ".mp3"):
        tp -= 0.5  # lossy encoders add ~0.3-0.7 dB of inter-sample overs
    ln = f"loudnorm=I={target}:TP={tp}:LRA={lra}"

    def pass1(pre_):
        p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", in_path, "-vn", "-af",
                            f"{pre_}{ln}:print_format=json", "-f", "null", "-"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
        if p.returncode != 0:
            die(f"loudnorm pass 1 failed: {p.stderr.strip()[-600:]}")
        return _loudnorm_json(p.stderr)

    m = pass1(pre)
    gain = target - float(m["input_i"])
    if float(m["input_tp"]) + gain > tp - 0.1:
        # Linear mode would break the true-peak ceiling, so loudnorm would silently go dynamic and miss the
        # target. Apply the gain ourselves into an oversampled peak limiter (iterating, since limiting costs
        # loudness), so the final loudnorm pass stays linear.
        log(f"loudnorm: +{gain:.1f} dB needs limiting (input TP {m['input_tp']}), pre-limiting")
        base = pre
        for _ in range(4):
            pre = (f"{base}volume={gain:.2f}dB,aresample=192000,alimiter=limit={db2lin(tp - 0.3):.4f}:level=disabled"
                   f":attack=1:release=60:latency=1,aresample={sr},")
            m = pass1(pre)
            if abs(target - float(m["input_i"])) < 0.15:
                break
            gain += target - float(m["input_i"])
    af = (f"{pre}{ln}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json,"
          f"aresample={sr}")
    has_v = probe(in_path)["has_video"]
    cmd = ["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", in_path, "-af", af, "-ar", str(sr)]
    ext = os.path.splitext(out_path)[1].lower()
    if ext in (".mp4", ".mov", ".m4a", ".mkv"):
        cmd += (["-map", "0:v?", "-map", "0:a", "-c:v", "copy"] if has_v else []) + ["-c:a", "aac", "-b:a", "192k"]
    elif ext == ".wav":
        cmd += ["-c:a", "pcm_s24le"]
    p2 = subprocess.run(cmd + [out_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
    if p2.returncode != 0:
        die(f"loudnorm pass 2 failed: {p2.stderr.strip()[-600:]}")
    m2 = _loudnorm_json(p2.stderr)
    log(f"loudnorm: {m['input_i']} LUFS -> {m2['output_i']} LUFS ({m2.get('normalization_type')})")
    return {"pass1": m, "pass2": m2, "result": measure(out_path)}


# ---------------------------------------------------------------- numpy audio I/O
def decode(path, sr=SR, ch=2, start=0, dur=None):
    """Decode any audio/video file to float32 array (n, ch) with FFmpeg."""
    need("ffmpeg")
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(start)] if start else []) + ["-i", path]
    cmd += (["-t", str(dur)] if dur else []) + ["-vn", "-f", "f32le", "-ac", str(ch), "-ar", str(sr), "-"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        die(f"cannot decode {path}: {p.stderr.decode(errors='ignore')[-400:]}")
    return np.frombuffer(p.stdout, dtype=np.float32).reshape(-1, ch)


def write_wav(path, y, sr=SR):
    """Write a float32 WAV (IEEE float, 1 or 2 channels)."""
    y = np.asarray(y, dtype=np.float32)
    if y.ndim == 1:
        y = y[:, None]
    n, ch = y.shape
    data = y.tobytes()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE")
        fh.write(b"fmt " + struct.pack("<IHHIIHH", 16, 3, ch, sr, sr * ch * 4, ch * 4, 32))
        fh.write(b"data" + struct.pack("<I", len(data)) + data)
    return path


# ---------------------------------------------------------------- DSP helpers for synthesis
def _t(d):
    return np.arange(int(round(d * SR))) / SR


def _noise(n, color, rng):
    w = rng.standard_normal(n)
    if color == "white":
        return w / 3.0
    W = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    W /= f ** {"pink": 0.5, "brown": 1.0, "blue": -0.5}[color]
    x = np.fft.irfft(W, n)
    return x / (np.std(x) * 3 + 1e-12)


def _band(x, lo=None, hi=None, order=2):
    """Zero-phase FFT filter with Butterworth-shaped magnitude (padded, so no wrap-around)."""
    n = len(x)
    pad = 8192
    X = np.fft.rfft(np.concatenate([x, np.zeros((pad,) + x.shape[1:])]), axis=0)
    f = np.fft.rfftfreq(n + pad, 1 / SR)
    H = np.ones_like(f)
    if hi:
        H /= np.sqrt(1 + (f / hi) ** (2 * order))
    if lo:
        H /= np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    if x.ndim > 1:
        H = H[:, None]
    return np.fft.irfft(X * H, n + pad, axis=0)[:n]


def _stft_filter(x, fc, kind="bp", width=1.0, order=2, nfft=2048, hop=256):
    """Time-varying filter: fc = per-sample centre/cutoff (Hz). kind 'bp' (gaussian, width in octaves) or 'lp'."""
    n = len(x)
    win = np.hanning(nfft)
    xp = np.concatenate([np.zeros(nfft), x, np.zeros(nfft)])
    starts = np.arange(0, len(xp) - nfft, hop)
    frames = np.lib.stride_tricks.sliding_window_view(xp, nfft)[starts] * win
    X = np.fft.rfft(frames, axis=1)
    f = np.fft.rfftfreq(nfft, 1 / SR)[None, :]
    c = np.interp(starts + nfft // 2 - nfft, np.arange(n), fc)[:, None]
    if kind == "bp":
        H = np.exp(-0.5 * (np.log2(np.maximum(f, 1.0) / c) / (width / 2)) ** 2)
    else:
        H = 1 / np.sqrt(1 + (f / c) ** (2 * order))
    y = np.fft.irfft(X * H, nfft, axis=1) * win
    out = np.zeros(len(xp))
    norm = np.zeros(len(xp))
    for i, s in enumerate(starts):
        out[s:s + nfft] += y[i]
        norm[s:s + nfft] += win ** 2
    return (out / np.maximum(norm, 1e-6))[nfft:nfft + n]


def _phase(freq):
    return 2 * np.pi * np.cumsum(freq) / SR


def _saw(freq, kmax=40, rng=None):
    """Band-limited saw from a per-sample frequency array."""
    ph = _phase(freq) + (rng.uniform(0, 2 * np.pi) if rng is not None else 0)
    y = np.zeros_like(ph)
    for k in range(1, kmax + 1):
        y += np.sin(k * ph) / k * (k * freq < 0.45 * SR)
    return y * 0.6


def _square(freq, kmax=15):
    ph = _phase(freq)
    y = np.zeros_like(ph)
    for k in range(1, kmax * 2, 2):
        y += np.sin(k * ph) / k * (k * freq < 0.45 * SR)
    return y * 0.8


def _dec(t, tau, at=0.0, attack=0.001):
    """Exponential decay envelope starting at time `at` with a short linear attack."""
    u = t - at
    return np.where(u < 0, 0.0, np.minimum(u / attack, 1.0) * np.exp(-np.maximum(u, 0) / tau))


def _pan(m, p):
    a = (np.asarray(p) + 1) * np.pi / 4
    return np.stack([m * np.cos(a), m * np.sin(a)], axis=1)


def _st(m):
    return np.stack([m, m], axis=1) if m.ndim == 1 else m


def _reverb(x, rt60=1.0, wet=0.25, lp=6000, rng=None, pre=0.012):
    """Stereo convolution reverb with a decorrelated exponentially-decaying noise IR."""
    rng = rng or np.random.default_rng(7)
    x = _st(x)
    n_ir = int(rt60 * SR)
    t = np.arange(n_ir) / SR
    out = np.zeros((len(x) + n_ir, 2))
    out[:len(x)] += x
    N = 1 << int(np.ceil(np.log2(len(x) + n_ir)))
    for c in range(2):
        ir = rng.standard_normal(n_ir) * np.exp(-6.91 * t / rt60)
        ir[: int(pre * SR)] = 0
        ir = _band(ir, lo=150, hi=lp)
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-12
        out[:, c] += wet * np.fft.irfft(np.fft.rfft(x[:, c], N) * np.fft.rfft(ir, N), N)[:len(x) + n_ir]
    return out


def _place(dst, src, at):
    """Add src (1D/2D) into dst starting at time `at` seconds."""
    i = int(at * SR)
    n = min(len(src), len(dst) - i)
    if n > 0:
        dst[i:i + n] += src[:n]
    return dst


def _loop_src(rng, d=3.0):
    """A short musical loop (A minor chord + kick + hats at 120 BPM) used as source for tape effects."""
    t = _t(d)
    y = np.zeros(len(t))
    for f0 in (110, 220, 261.63, 329.63):
        y += 0.25 * _band(_saw(np.full(len(t), f0), 20, rng), hi=2500)
    for b in np.arange(0, d, 0.5):
        y = _place(y, 0.9 * np.sin(_phase(45 + 80 * np.exp(-_t(0.3) / 0.03))) * _dec(_t(0.3), 0.08), b)
        y = _place(y, 0.25 * _band(_noise(int(0.05 * SR), "white", rng), lo=6000) * _dec(_t(0.05), 0.01), b + 0.25)
    return y


def _fin(y, peak=0.6, fade_in=0.001, fade_out=0.005):
    y = _st(np.asarray(y, dtype=np.float64))
    y = y - np.mean(y, axis=0)
    n = len(y)
    fi, fo = max(1, int(fade_in * SR)), max(1, int(fade_out * SR))
    y[:fi] *= np.linspace(0, 1, fi)[:, None]
    y[n - fo:] *= np.linspace(1, 0, fo)[:, None]
    return (y * peak / (np.max(np.abs(y)) + 1e-12)).astype(np.float32)


# ---------------------------------------------------------------- SFX synths (rng -> stereo array)
def _whoosh(d, lo, hi, end, color="pink", pk=0.65, pan=(-0.6, 0.6), rt=0.6, wet=0.15, width=1.2):
    def f(rng):
        t = _t(d)
        u = t / d
        fc = np.where(u < pk, lo * (hi / lo) ** (u / pk), hi * (end / hi) ** ((u - pk) / (1 - pk)))
        y = _stft_filter(_noise(len(t), color, rng), fc, "bp", width)
        y *= np.where(u < pk, (u / pk) ** 2.2, ((1 - u) / (1 - pk)) ** 1.6)
        s = _pan(y, np.interp(u, [0, 1], pan))
        return _reverb(s, rt, wet, rng=rng)[: len(t) + int(0.25 * SR)] if wet else s
    return f


def _swoosh(up, d=0.8):
    def f(rng):
        t = _t(d)
        u = t / d
        fc = 300 * (5000 / 300) ** (u if up else 1 - u)
        y = _stft_filter(_noise(len(t), "pink", rng), fc, "bp", 1.0)
        y *= (u ** 1.8) if up else ((1 - u) ** 1.2 * np.minimum(u / 0.05, 1))
        y += 0.15 * np.sin(_phase(fc * 0.25)) * (u if up else 1 - u) ** 2
        return _reverb(_pan(y, np.interp(u, [0, 1], (-0.5, 0.5))), 0.5, 0.12, rng=rng)
    return f


def _riser(d, f0=180, octs=2.0):
    def f(rng):
        t = _t(d)
        u = t / d
        fr = f0 * 2 ** (octs * u ** 1.6)
        L = np.zeros(len(t))
        R = np.zeros(len(t))
        for i, cents in enumerate((-12, -4, 0, 5, 11)):
            v = _saw(fr * 2 ** (cents / 1200), 25, rng)
            (L if i % 2 else R)[:] += v
            if cents == 0:
                L += v * 0.5
                R += v * 0.5
        cut = 600 * 2 ** (3.5 * u)
        L, R = _stft_filter(L, cut, "lp"), _stft_filter(R, cut, "lp")
        nz = _stft_filter(_noise(len(t), "white", rng), 500 * 16 ** u, "bp", 1.5) * 1.2
        trem = 0.75 + 0.25 * np.sin(_phase(4 + 12 * u))
        env = u ** 1.5 * trem
        s = np.stack([(L * 0.25 + nz) * env, (R * 0.25 + np.roll(nz, 331)) * env], axis=1)
        return _reverb(s, 0.8, 0.15, rng=rng)[: len(t)]
    return f


def _impact(d=1.6, sub=(60, 32), sub_tau=0.45, body=0.5, sat=1.5, rt=1.2, wet=0.25):
    def f(rng):
        t = _t(d)
        s = np.sin(_phase(sub[1] + (sub[0] - sub[1]) * np.exp(-t / 0.25))) * _dec(t, sub_tau, attack=0.002)
        tr = _band(_noise(len(t), "white", rng), 800, 8000) * _dec(t, 0.006, attack=0.0003) * 2.5
        bd = _band(_noise(len(t), "pink", rng), 150, 2500) * _dec(t, 0.08, attack=0.0005) * 2 * body
        y = np.tanh(sat * (s + tr + bd)) / np.tanh(sat)
        return _reverb(y, rt, wet, lp=5000, rng=rng)[: len(t)] if wet else _st(y)
    return f


def s_thud(rng):
    t = _t(0.45)
    y = np.sin(_phase(50 + 35 * np.exp(-t / 0.05))) * _dec(t, 0.08, attack=0.001)
    y += _band(_noise(len(t), "brown", rng), hi=400) * _dec(t, 0.04) * 1.5
    return np.tanh(1.5 * y)


def s_sub_drop(rng):
    t = _t(2.2)
    y = np.sin(_phase(30 + 90 * np.exp(-t / 0.45))) * _dec(t, 0.9, attack=0.005) * np.minimum((2.2 - t) / 0.3, 1)
    return np.tanh(2.2 * y)  # saturation adds harmonics so phones still hear it


def s_bass_drop(rng):
    t = _t(3.0)
    fr = 41 + 40 * np.exp(-t / 0.35)
    sub = np.sin(_phase(fr)) * _dec(t, 1.4, attack=0.004)
    wob = 0.5 + 0.5 * np.sin(_phase(4 - 2 * t / 3.0) - np.pi / 2)
    saw = _stft_filter(_saw(fr, 40, rng), 180 + 1400 * wob * np.exp(-t / 1.6), "lp", order=3)
    hit = _impact(0.8, (70, 40), 0.15, 0.8, 2.5, 0, 0)(rng)[:, 0]
    y = np.tanh(1.8 * (sub + 0.6 * saw * _dec(t, 1.6, attack=0.01))) * np.minimum((3.0 - t) / 0.4, 1)
    y[: len(hit)] += 0.7 * hit
    return _reverb(y, 1.0, 0.12, lp=3000, rng=rng)[: len(t)]


def s_braam(rng):
    d = 3.0
    t = _t(d)
    L = np.zeros(len(t))
    R = np.zeros(len(t))
    for f0, g in ((55, 1.0), (82.41, 0.7), (110, 0.5)):
        for j, cents in enumerate((-7, 0, 7)):
            v = g * _saw(np.full(len(t), f0 * 2 ** (cents / 1200)), 40, rng)
            (L, R, L)[j][:] += v
            if cents == 0:
                R += v
    cut = np.where(t < 0.15, 200 * 11 ** (t / 0.15), 2200 * np.exp(-(t - 0.15) / 0.7) + 300)
    env = np.minimum(t / 0.03, 1) * np.exp(-t / 1.6) * np.minimum((d - t) / 0.6, 1)
    s = np.stack([_stft_filter(L, cut, "lp", order=3), _stft_filter(R, cut, "lp", order=3)], axis=1) * env[:, None]
    s = np.tanh(2.5 * s / np.max(np.abs(s)))
    return _reverb(s, 2.5, 0.35, lp=4000, rng=rng)[: len(t) + int(0.5 * SR)]


def s_reverse_cymbal(rng):
    t = _t(2.0)
    ch = []
    for c in range(2):
        y = _band(_noise(len(t), "white", rng), lo=3500) * 0.8
        for fr in (3150, 4280, 5620, 6990, 8330, 9640, 11200):
            y += rng.uniform(0.05, 0.15) * np.sin(_phase(np.full(len(t), fr * rng.uniform(0.99, 1.01))))
        ch.append(y * _dec(t, 0.55, attack=0.0005))
    s = _reverb(np.stack(ch, 1), 1.2, 0.3, lp=12000, rng=rng)[: len(t)]
    return s[::-1].copy()  # reversed: swells up, ends abruptly


def s_tape_stop(rng):
    d = 1.2
    src = _loop_src(rng, 2.0)
    t = _t(d)
    u = t / d
    rate = np.where(u < 0.06, 1.0, ((1 - u) / 0.94) ** 1.4)
    y = np.interp(np.cumsum(rate), np.arange(len(src)), src)
    return _st(_stft_filter(y, 300 + 9000 * rate, "lp") * np.minimum((d - t) / 0.05, 1))


def s_rewind(rng):
    d = 1.0
    src = _loop_src(rng, 4.0)[::-1].copy()
    t = _t(d)
    u = t / d
    rate = (2.0 + 3.0 * u) * (1 + 0.15 * np.sin(_phase(np.full(len(t), 7.0))))
    y = np.interp(np.cumsum(rate) % len(src), np.arange(len(src)), src)
    y = _band(y, 400, 7000) + 0.15 * _band(_noise(len(t), "white", rng), lo=3000)
    return _pan(y * np.sin(np.pi * u) ** 0.5, np.interp(u, [0, 1], (0.4, -0.4)))


def s_record_scratch(rng):
    d = 0.4
    src = _loop_src(rng, 2.0)
    t = _t(d)
    rate = 3.0 * np.sin(2 * np.pi * t / 0.2)
    pos = 0.5 * SR + np.cumsum(rate)
    y = np.interp(pos, np.arange(len(src)), src) * np.minimum(np.abs(rate) / 0.8, 1)
    y = _band(y, 300, 5000) + 0.2 * _band(_noise(len(t), "white", rng), 1000, 3000) * np.abs(rate) / 3
    return _st(y)


def s_glitch(rng):
    d = 0.45
    y = np.zeros((int(d * SR), 2))
    pos, prev = 0.0, None
    while pos < d - 0.01:
        L = rng.uniform(0.01, 0.04)
        n = int(L * SR)
        k = rng.integers(0, 4)
        if k == 0:
            seg = _square(np.full(n, rng.uniform(200, 2000)), 8)
        elif k == 1:
            seg = _noise(n, "white", rng) * 2
        elif k == 2 and prev is not None:
            seg = np.resize(prev, n)
        else:
            seg = np.zeros(n)
        hold = int(rng.integers(2, 9))
        seg = np.repeat(seg[::hold], hold)[:n]
        seg = np.round(seg * 8) / 8  # bitcrush
        prev = seg
        _place(y, _pan(seg, rng.uniform(-0.7, 0.7)), pos)
        pos += L
    return y


def _beep(fr, d, kind="square", tau=None):
    def f(rng):
        t = _t(d)
        y = _square(np.full(len(t), fr), 4) if kind == "square" else np.sin(_phase(np.full(len(t), fr)))
        env = np.minimum(t / 0.005, 1) * np.minimum((d - t) / 0.02, 1)
        return y * (env * np.exp(-t / tau) if tau else env)
    return f


def _notes(seq, d, harm=(1, 0.3, 0.1), rt=0.6, wet=0.15, kind="sine", pan_spread=0.0):
    """seq: list of (time, freq, decay). Bell/UI tones."""
    def f(rng):
        t = _t(d)
        s = np.zeros((len(t), 2))
        for i, (at, fr, tau) in enumerate(seq):
            u = t[: len(t) - int(at * SR)]
            if kind == "square":
                v = _square(np.full(len(u), fr), 5)
            else:
                v = sum(a * np.sin(_phase(np.full(len(u), fr * (k + 1) * (1.003 if k else 1)))) for k, a in enumerate(harm))
            v = v * _dec(u, tau, attack=0.004)
            p = (i / max(1, len(seq) - 1) - 0.5) * 2 * pan_spread
            _place(s, _pan(v, p), at)
        return _reverb(s, rt, wet, rng=rng)[: len(t)] if wet else s
    return f


def _bell(f0, d=2.0, ratios=(1, 2.32, 4.25, 6.63), amps=(1, 0.5, 0.25, 0.12), taus=(1.2, 0.7, 0.4, 0.25), wet=0.25):
    def f(rng):
        t = _t(d)
        y = np.zeros(len(t))
        for r, a, tau in zip(ratios, amps, taus):
            for det in (-0.4, 0.4):  # slight beating
                y += a * 0.5 * np.sin(_phase(np.full(len(t), f0 * r + det))) * _dec(t, tau, attack=0.001)
        y += 0.3 * _band(_noise(len(t), "white", rng), lo=4000) * _dec(t, 0.002, attack=0.0002)
        return _reverb(y, 1.5, wet, lp=10000, rng=rng)[: len(t)]
    return f


def _click(rng, n_t, tones, tau=0.012, noise_tau=0.0015, lo=2000):
    y = sum(a * np.sin(_phase(np.full(len(n_t), fr))) for fr, a in tones) * _dec(n_t, tau, attack=0.0003)
    return y + _band(_noise(len(n_t), "white", rng), lo=lo) * _dec(n_t, noise_tau, attack=0.0001) * 2


def s_ui_tap(rng):
    return _click(rng, _t(0.05), [(1400, 0.8)], tau=0.006)


def s_ui_swipe(rng):
    t = _t(0.2)
    u = t / 0.2
    y = _stft_filter(_noise(len(t), "white", rng), 1200 * 5 ** u, "bp", 1.0, nfft=1024, hop=128) * np.sin(np.pi * u) ** 1.5
    return _pan(y, np.interp(u, [0, 1], (-0.3, 0.3)))


def s_coin(rng):
    t = _t(0.55)
    fr = np.where(t < 0.07, 987.77, 1318.51)
    env = np.where(t < 0.07, 1.0, np.exp(-(t - 0.07) / 0.15)) * np.minimum(t / 0.0005, 1)
    return _square(fr, 6) * env


def s_cash_register(rng):
    d = 1.4
    t = _t(d)
    s = np.zeros((len(t), 2))
    for at, g in ((0.0, 1.0), (0.06, 0.8)):  # key mechanism
        _place(s, _pan(g * _click(rng, _t(0.06), [(2300, 0.4), (3400, 0.3)], 0.01, 0.004, 1800), -0.2), at)
    _place(s, _st(_bell(2637, 1.1, wet=0)(rng)[:, 0] * 0.6), 0.1)
    _place(s, _st(0.8 * s_thud(rng)), 0.32)  # drawer
    for _ in range(14):  # coins rattling in the drawer
        at = 0.34 + rng.uniform(0, 0.45)
        c = _click(rng, _t(0.04), [(rng.uniform(4000, 7000), 0.3)], 0.008, 0.001, 3000) * rng.uniform(0.15, 0.4)
        _place(s, _pan(c, rng.uniform(-0.5, 0.5)), at)
    return _reverb(s, 0.4, 0.12, rng=rng)[: len(t)]


def s_sparkle(rng):
    d = 1.4
    t = _t(d)
    s = np.zeros((len(t), 2))
    for _ in range(30):
        at = rng.uniform(0, 0.9)
        fr = 2500 * (9000 / 2500) ** rng.uniform()
        u = _t(0.25)
        v = (np.sin(_phase(np.full(len(u), fr))) + 0.3 * np.sin(_phase(np.full(len(u), fr * 2.01)))) \
            * _dec(u, rng.uniform(0.04, 0.12), attack=0.002) * rng.uniform(0.3, 1)
        _place(s, _pan(v, rng.uniform(-0.8, 0.8)), at)
    s += _st(0.15 * _band(_noise(len(t), "white", rng), lo=8000) * np.sin(np.pi * np.minimum(t / 1.0, 1)) ** 2)
    return _reverb(s, 1.2, 0.35, lp=12000, rng=rng)[: len(t)]


def s_heartbeat(rng):
    t = _t(1.7)
    y = np.zeros(len(t))
    for at, g, f0 in ((0.0, 1.0, 55), (0.28, 0.75, 62), (0.85, 1.0, 55), (1.13, 0.75, 62)):
        u = _t(0.3)
        b = np.sin(_phase(f0 - 15 * u / 0.3)) * _dec(u, 0.06, attack=0.004)
        b += _band(_noise(len(u), "brown", rng), hi=150) * _dec(u, 0.04, attack=0.003)
        _place(y, g * b, at)
    return np.tanh(1.5 * _band(y, hi=250))


def _tick(rng, high=True):
    tones = [(2600, 0.6), (3900, 0.3)] if high else [(1700, 0.6), (2550, 0.3)]
    return _click(rng, _t(0.1), tones, tau=0.012, noise_tau=0.001)


def s_tick_tock(rng):
    y = np.zeros(int(2.0 * SR))
    for i, at in enumerate((0.0, 0.5, 1.0, 1.5)):
        _place(y, _tick(rng, i % 2 == 0), at)
    return _reverb(y, 0.3, 0.1, rng=rng)[: len(y)]


def s_clock_tick(rng):
    return _reverb(_tick(rng, True), 0.3, 0.1, rng=rng)[: int(0.12 * SR)]


def s_boing(rng):
    t = _t(0.8)
    fr = (300 - 80 * t / 0.8) * (1 + 0.35 * np.exp(-t / 0.25) * np.sin(2 * np.pi * 11 * t))
    ph = _phase(fr)
    y = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)) * _dec(t, 0.3, attack=0.003)
    return y


def s_slide_whistle(rng):
    d = 1.0
    t = _t(d)
    u = t / d
    fr = 600 * (1900 / 600) ** (0.5 - 0.5 * np.cos(np.pi * u)) * (1 + 0.015 * np.sin(2 * np.pi * 6 * t))
    y = np.sin(_phase(fr)) + 0.08 * np.sin(2 * _phase(fr))
    y += 0.25 * _stft_filter(_noise(len(t), "white", rng), fr, "bp", 0.3)
    return y * np.minimum(t / 0.06, 1) * np.minimum((d - t) / 0.1, 1)


def _snare(rng, g=1.0):
    u = _t(0.12)
    return g * (_band(_noise(len(u), "white", rng), 1500, 8000) * _dec(u, 0.045, attack=0.0005)
                + 0.5 * np.sin(_phase(np.full(len(u), 190))) * _dec(u, 0.03, attack=0.0005))


def s_drum_roll(rng):
    d = 2.6
    s = np.zeros((int(d * SR), 2))
    at, i = 0.0, 0
    while at < 2.0:
        g = (0.35 + 0.65 * at / 2.0) * (1.0 if i % 2 else 0.8)
        _place(s, _pan(_snare(rng, g), -0.15 if i % 2 else 0.15), at)
        at += 1 / (10 + 12 * at / 2.0)
        i += 1
    crash = _band(_noise(int(0.6 * SR), "white", rng), lo=3000) * _dec(_t(0.6), 0.25, attack=0.001)
    _place(s, _st(crash * 1.4), 2.0)
    _place(s, _st(_impact(0.6, (70, 45), 0.12, 0.4, 2.0, 0, 0)(rng)[:, 0]), 2.0)
    return _reverb(s, 0.9, 0.2, rng=rng)[: len(s)]


def s_applause(rng):
    d = 3.5
    t = _t(d)
    s = np.zeros((len(t), 2))
    at = 0.0
    while at < d - 0.05:
        at += rng.exponential(1 / 28)
        c = _band(_noise(int(0.03 * SR), "white", rng), 600, rng.uniform(2000, 4500)) * _dec(_t(0.03), 0.008, attack=0.0005)
        _place(s, _pan(c * rng.uniform(0.3, 1), rng.uniform(-0.9, 0.9)), at)
    s += np.stack([_band(_noise(len(t), "pink", rng), 1000, 4000) for _ in range(2)], 1) * 0.15
    s *= (np.minimum(t / 0.3, 1) * np.minimum((d - t) / 1.0, 1))[:, None]
    return _reverb(s, 0.6, 0.25, rng=rng)[: len(t)]


def s_crowd_gasp(rng):
    """Many breathy inhales (formant-shaped noise, no synthetic voices)."""
    d = 1.3
    t = _t(d)
    s = np.zeros((len(t), 2))
    for _ in range(12):
        n = int(0.9 * SR)
        u = _t(0.9)
        x = _noise(n, "pink", rng)
        f1, f2 = rng.uniform(600, 900), rng.uniform(1100, 1700)
        v = _band(x, f1 * 0.8, f1 * 1.25, 3) + 0.7 * _band(x, f2 * 0.85, f2 * 1.2, 3) + 0.2 * _band(x, lo=3000)
        env = np.where(u < 0.12, (u / 0.12) ** 1.5, np.exp(-(u - 0.12) / 0.25))
        _place(s, _pan(v * env * rng.uniform(0.5, 1), rng.uniform(-0.8, 0.8)), rng.uniform(0, 0.12))
    return _reverb(s, 0.7, 0.25, rng=rng)[: len(t)]


def s_wind(rng):
    d = 5.0
    t = _t(d)
    ch = []
    for c in range(2):
        walk = np.cumsum(rng.standard_normal(len(t) // 2400 + 2))
        walk = (walk - walk.min()) / (np.ptp(walk) + 1e-9)
        fc = 250 + 650 * np.interp(t, np.arange(len(walk)) * 0.05, walk)
        amp = 0.5 + 0.5 * np.interp(t, np.arange(len(walk)) * 0.05, np.roll(walk, 7))
        ch.append(_stft_filter(_noise(len(t), "pink", rng), fc, "bp", 1.3) * amp)
    return np.stack(ch, 1) * (np.minimum(t / 0.5, 1) * np.minimum((d - t) / 0.5, 1))[:, None]


def s_room_tone(rng):
    n = int(5.0 * SR)
    return np.stack([_band(0.6 * _noise(n, "brown", rng) + 0.4 * _noise(n, "pink", rng), 40, 5000) for _ in range(2)], 1)


def s_camera_shutter(rng):
    s = np.zeros(int(0.3 * SR))
    _place(s, _click(rng, _t(0.06), [(3200, 0.5), (4700, 0.2)], 0.01, 0.004, 2000), 0.0)
    _place(s, 0.6 * np.sin(_phase(np.full(int(0.05 * SR), 180))) * _dec(_t(0.05), 0.012), 0.02)  # mirror slap
    _place(s, 0.8 * _click(rng, _t(0.06), [(2900, 0.5), (4400, 0.2)], 0.01, 0.004, 2000), 0.11)
    return _reverb(s, 0.2, 0.1, rng=rng)[: len(s)]


def s_typewriter_key(rng):
    t = _t(0.18)
    y = _click(rng, t, [(1650, 0.5), (3100, 0.3)], tau=0.02, noise_tau=0.003, lo=1500)
    y += 0.5 * np.sin(_phase(np.full(len(t), 220))) * _dec(t, 0.025, attack=0.0005)
    y += 0.12 * _band(_noise(len(t), "white", rng), 2000, 6000) * _dec(t, 0.01, at=0.03)
    return _reverb(y, 0.25, 0.1, rng=rng)[: len(t)]


def s_page_turn(rng):
    d = 0.8
    t = _t(d)
    u = t / d
    x = 0.6 * _noise(len(t), "pink", rng) + 0.4 * _noise(len(t), "white", rng)
    fc = np.where(u < 0.6, 1500 * 3 ** (u / 0.6), 4500 * (2500 / 4500) ** ((u - 0.6) / 0.4))
    y = _stft_filter(x, fc, "bp", 1.5)
    crinkle = 1 + 2.5 * _band((rng.uniform(size=len(t)) > 0.9985).astype(float), hi=300) * 40
    y *= np.sin(np.pi * u) ** 2 * np.clip(crinkle, 0, 4)
    return _pan(y, np.interp(u, [0, 1], (-0.4, 0.4)))


def s_error_buzz(rng):
    t = _t(0.5)
    y = _band(_saw(np.full(len(t), 120.0), 40, rng) + _saw(np.full(len(t), 127.0), 40, rng), hi=2500)
    gate = ((t < 0.18) | ((t > 0.24) & (t < 0.42))).astype(float)
    return y * _band(gate, hi=150)


def s_countdown(rng):
    s = np.zeros(int(3.7 * SR))
    for at in (0.0, 1.0, 2.0):
        _place(s, _beep(880, 0.15, "sine")(rng) + 0.2 * _beep(1760, 0.15, "sine")(rng), at)
    _place(s, _beep(1760, 0.6, "sine", tau=0.35)(rng) + 0.2 * _beep(3520, 0.6, "sine", tau=0.25)(rng), 3.0)
    return s


LAVFI = {  # legacy single-expression sounds kept bit-compatible with the original finish.py
    "pop": "aevalsrc='0.6*sin(2*PI*(500+900*exp(-35*t))*t)*exp(-22*t)':d=0.18:s=48000",
    "click": "aevalsrc='0.6*sin(2*PI*2200*t)*exp(-140*t)':d=0.05:s=48000",
    "type": "aevalsrc='0.35*sin(2*PI*1800*t)*exp(-160*t)+0.2*(random(0)-0.5)*exp(-200*t)':d=0.04:s=48000",
    "ding": "aevalsrc='0.35*(sin(2*PI*1320*t)+0.5*sin(2*PI*2640*t))*exp(-5*t)':d=1.0:s=48000",
    "camera": "aevalsrc='0.6*sin(2*PI*2500*t)*exp(-150*t)+0.5*sin(2*PI*1800*(t-0.08))*exp(-150*(t-0.08))*gte(t,0.08)':d=0.16:s=48000",
}

# name -> (synth, peak). Peak normalisation keeps the library consistent; plan "gain" sets level in the mix.
SYNTH = {
    "whoosh": (_whoosh(0.6, 300, 2500, 600), 0.6),
    "whoosh-long": (_whoosh(1.4, 200, 1800, 400, rt=0.9, wet=0.2), 0.6),
    "whoosh-short": (_whoosh(0.3, 600, 4000, 1500, wet=0.1), 0.6),
    "swish": (_whoosh(0.28, 2500, 8000, 5000, color="white", pan=(-0.3, 0.3), wet=0.08, width=1.5), 0.5),
    "swoosh-up": (_swoosh(True), 0.6),
    "swoosh-down": (_swoosh(False), 0.6),
    "riser": (_riser(1.2, 180, 2.0), 0.55),
    "riser-long": (_riser(4.0, 150, 2.5), 0.55),
    "boom": (_impact(1.6, (90, 38), 0.6, 0.4, 1.8, 1.4, 0.2), 0.7),
    "impact": (_impact(), 0.7),
    "hit-hard": (_impact(0.9, (75, 42), 0.15, 1.0, 3.0, 0.5, 0.15), 0.75),
    "thud": (s_thud, 0.7),
    "sub-drop": (s_sub_drop, 0.7),
    "bass-drop": (s_bass_drop, 0.7),
    "braam": (s_braam, 0.65),
    "reverse-cymbal": (s_reverse_cymbal, 0.55),
    "tape-stop": (s_tape_stop, 0.6),
    "rewind": (s_rewind, 0.55),
    "record-scratch": (s_record_scratch, 0.6),
    "glitch": (s_glitch, 0.5),
    "digital-beep": (_beep(1000, 0.16), 0.4),
    "notification": (_notes([(0, 880, 0.18), (0.12, 1320, 0.25)], 0.7), 0.5),
    "ui-tap": (s_ui_tap, 0.45),
    "ui-swipe": (s_ui_swipe, 0.45),
    "cash-register": (s_cash_register, 0.6),
    "coin": (s_coin, 0.4),
    "sparkle": (s_sparkle, 0.5),
    "heartbeat": (s_heartbeat, 0.7),
    "tick-tock": (s_tick_tock, 0.5),
    "clock-tick": (s_clock_tick, 0.5),
    "boing": (s_boing, 0.55),
    "slide-whistle": (s_slide_whistle, 0.5),
    "drum-roll": (s_drum_roll, 0.6),
    "applause-light": (s_applause, 0.45),
    "crowd-gasp": (s_crowd_gasp, 0.45),
    "wind": (s_wind, 0.35),
    "room-tone": (s_room_tone, 0.05),
    "camera-shutter": (s_camera_shutter, 0.55),
    "typewriter-key": (s_typewriter_key, 0.5),
    "page-turn": (s_page_turn, 0.45),
    "glass-ding": (_bell(1760), 0.5),
    "error-buzz": (s_error_buzz, 0.45),
    "success-chime": (_notes([(0, 1046.5, 0.3), (0.09, 1318.5, 0.3), (0.18, 1568, 0.35), (0.27, 2093, 0.6)], 1.1,
                             (1, 0.25, 0.1), 1.0, 0.2, pan_spread=0.3), 0.5),
    "countdown-beep": (s_countdown, 0.45),
}
ALIASES = {"crowd-gasp-ish": "crowd-gasp", "applause": "applause-light", "shutter": "camera-shutter", "hit": "impact"}
SFX = {**LAVFI, **{k: v[0] for k, v in SYNTH.items()}}
SYNTH_VERSION = 1


def _kind(kind):
    k = ALIASES.get(kind, kind)
    if k not in SFX:
        die(f"unknown sfx '{kind}'. Known: {', '.join(sorted(SFX))}")
    return k


def sfx_wav(kind, cache_dir):
    """Path to the cached synthesized WAV for a numpy SFX (rendered on first use)."""
    k = _kind(kind)
    path = os.path.join(cache_dir, "sfx", f"{k}.v{SYNTH_VERSION}.wav")
    if not os.path.exists(path):
        fn, peak = SYNTH[k]
        write_wav(path, _fin(fn(np.random.default_rng(zlib.crc32(k.encode()))), peak))
    return path


def sfx_input_args(kind, cache_dir):
    """FFmpeg input args for one SFX: lavfi source for legacy expressions, cached WAV otherwise."""
    k = _kind(kind)
    return ["-f", "lavfi", "-i", LAVFI[k]] if k in LAVFI else ["-i", sfx_wav(k, cache_dir)]


def render_sfx(kind, out_path):
    """Write one SFX to a 48 kHz stereo WAV."""
    k = _kind(kind)
    if k in LAVFI:
        run(["ffmpeg", "-y", "-hide_banner", "-f", "lavfi", "-i", LAVFI[k], "-ac", "2", "-c:a", "pcm_s16le", out_path])
    else:
        fn, peak = SYNTH[k]
        write_wav(out_path, _fin(fn(np.random.default_rng(zlib.crc32(k.encode()))), peak))
    return out_path


# ---------------------------------------------------------------- room tone
def room_tone(src_path, out_path, seconds=20, sr=SR):
    """Write a seamless loop of noise matched to the source's noise floor (level + average spectrum of the
    quietest 10% of 50 ms windows). Returns the floor in dBFS, or None if the source is digitally silent."""
    x = decode(src_path, sr, 1)[:, 0].astype(np.float64)
    win = sr // 20
    fr = x[: len(x) // win * win].reshape(-1, win)
    rms = np.sqrt(np.mean(fr ** 2, axis=1))
    ok = rms > 1e-5
    if ok.sum() < 4:
        return None
    quiet = fr[ok & (rms <= np.percentile(rms[ok], 10))]
    floor = float(np.median(np.sqrt(np.mean(quiet ** 2, axis=1))))
    if 20 * math.log10(floor) < -80:
        return None
    mag = np.mean(np.abs(np.fft.rfft(quiet * np.hanning(win), axis=1)), axis=0)
    n = int(seconds * sr)
    X = np.fft.rfft(np.random.default_rng(3).standard_normal(n))
    X *= np.interp(np.fft.rfftfreq(n, 1 / sr), np.fft.rfftfreq(win, 1 / sr), mag)
    y = np.fft.irfft(X, n)  # circular filtering -> loops seamlessly
    y *= floor / (np.sqrt(np.mean(y ** 2)) + 1e-12)
    write_wav(out_path, np.stack([y, y], 1), sr)
    return 20 * math.log10(floor)


def _trapezoids(regions, ramp_in, ramp_out):
    """ffmpeg expression: 0..1, 1 inside each (s, e) region with linear ramps outside it."""
    terms = [f"clip(min((t-{s - ramp_in:.3f})/{ramp_in},({e + ramp_out:.3f}-t)/{ramp_out}),0,1)" for s, e in regions]
    return "min(1," + "+".join(terms) + ")" if terms else "0"


# ---------------------------------------------------------------- ducking
def duck_filter(cfg=None, words=None):
    """Chain to use as "[music][key]<chain>[out]" (key = processed dialogue).
    cfg = plan["music"]: "duck": true | "speech-aware" | false, "duckDepth" dB (default 10; 6 in speech-aware),
    "duckAttack" ms (20), "duckRelease" ms (700), "speechDuck" extra dB during words (default 4).
    Depth maps to the compressor ratio assuming processed dialogue sits ~18 dB over the threshold
    (calibrated on voice_chain() output; approximate, +/-3 dB).
    speech-aware also needs `words` ([{start,end}] on the output timeline) for the word-level dip."""
    c = cfg or {}
    mode = c.get("duck", True)
    if not mode:
        return "anull"  # caller must still consume the key input
    aware = mode == "speech-aware"
    depth = float(c.get("duckDepth", 6 if aware else 10))
    ratio = min(20.0, 1 / max(0.05, 1 - depth / 18.0))
    f = (f"sidechaincompress=threshold=0.03:ratio={ratio:.2f}:attack={c.get('duckAttack', 20)}"
         f":release={c.get('duckRelease', 700)}:makeup=1:knee=4:detection=rms:link=maximum")
    if aware and words:
        regs = []
        for w in sorted(words, key=lambda w: w["start"]):
            if regs and w["start"] - regs[-1][1] < 0.35:
                regs[-1][1] = max(regs[-1][1], w["end"])
            else:
                regs.append([w["start"], w["end"]])
        g = 1 - db2lin(-float(c.get("speechDuck", 4)))
        f += f",volume=eval=frame:volume='1-{g:.4f}*{_trapezoids(regs, 0.2, 0.5)}'"
    return f


# ---------------------------------------------------------------- mix graph
def _measure_chain(path, chain):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af",
                        f"{chain},ebur128=framelog=verbose", "-f", "null", "-"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    return float(m[-1]) if m else None


def _measure_graph(src, inputs, lines, label, tail, dur):
    """Render the graph up to `label` (+ tail filters) to null and return ebur128 stats."""
    g = ";\n".join(lines + [f"{label}{tail},ebur128=peak=true:framelog=verbose[mout]"])
    gf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    gf.write(g)
    gf.close()
    cmd = _compat(["ffmpeg", "-hide_banner", "-nostats", "-i", src] + inputs +
                  ["-filter_complex_script", gf.name, "-map", "[mout]", "-t", str(dur), "-f", "null", "-"])
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
    os.unlink(gf.name)
    if p.returncode != 0:
        log(f"loudness measuring pass failed, using single-pass loudnorm: {p.stderr.strip()[-300:]}")
        return None
    s = p.stderr[p.stderr.rfind("Summary:"):]
    f = lambda pat: float(re.search(pat, s).group(1)) if re.search(pat, s) else None
    return {"I": f(r"I:\s+(-?[\d.]+) LUFS"), "TP": f(r"Peak:\s+(-?[\d.]+)")}


def build_mix_graph(plan, info, dur, platform=None, pdir=".", work=None, first_input=1, src_path=None, measured=True):
    """Audio section of finish.py as filtergraph lines.
    plan: full plan dict. info: probe() of the composite (input 0). dur: output seconds.
    platform: LOUDNESS key (plan["audio"]["platform"] wins; default youtube). pdir: plan folder for relative
    paths. work: work folder (cache for SFX/room tone/fitted music, cutlist.json). first_input: index the
    first extra input will get on the ffmpeg command line. src_path: the composite file (input 0); needed
    for room tone (noise-floor match), music "under" (dialogue loudness) and measured loudness.
    measured=True (needs src_path): renders the premix once (audio only, a few seconds) and sets an exact linear
    gain + limiter, so the result hits the target within ~0.3 LU; otherwise single-pass loudnorm (+/-1-2 LU).
    Returns (extra_inputs, filter_lines, "[aout]"): append extra_inputs after "-i composite", join
    filter_lines with ";\\n" into the -filter_complex script, map "[aout]".
    Plan fields: "audio": {"voice": cfg|false, "platform", "lufs", "tp", "lra", "roomTone"}, "roomTone": true|false
    (unset = on whenever an autocut cutlist.json has joins),
    "sfx": [{t, kind, gain, file?}], "music": {src, volume|under, duck, start, fadeOut, fitTo, endButton, ...},
    "words": [...] (for speech-aware ducking)."""
    work = work or pdir
    P = lambda p: p if os.path.isabs(p) else os.path.abspath(os.path.join(pdir, p))
    A = plan.get("audio") or {}
    tgt = dict(LOUDNESS.get(A.get("platform") or platform or "youtube", LOUDNESS["youtube"]))
    tgt.update({k.upper(): A[k] for k in ("lufs", "tp", "lra") if k in A})
    if "LUFS" in tgt:
        tgt["I"] = tgt.pop("LUFS")
    inputs, lines, mix = [], [], []
    idx = first_input

    def add_input(args):
        nonlocal idx
        inputs.extend(args)
        idx += 1
        return idx - 1

    vcfg = A.get("voice", {})
    chain = voice_chain(vcfg)
    has_a = info.get("has_audio")
    if has_a:
        raw = "[0:a]aformat=sample_rates=48000:channel_layouts=stereo"
        rt = A.get("roomTone", plan.get("roomTone"))
        cut = os.path.join(work, "cutlist.json")
        cl = load_json(cut) if os.path.exists(cut) else None
        if rt is None and cl:  # autocut joins get room tone unless the plan says no; timelines have own transitions
            rt = cl.get("kind") != "timeline"
        if rt and cl:
            joins = [s["out_start"] for s in cl["segments"][1:]]
            rt_path = os.path.join(work, "roomtone.wav")
            floor = room_tone(src_path, rt_path) if src_path else None
            if floor is not None and joins:
                ri = add_input(["-stream_loop", "-1", "-i", rt_path])
                gain = rt.get("gain", 1.0) if isinstance(rt, dict) else 1.0
                lines.append(f"[{ri}:a]atrim=duration={dur},asetnsamples=n=240,volume=eval=frame:volume="
                             f"'{gain}*{_trapezoids([(j, j) for j in joins], 0.03, 0.03)}',"
                             f"aformat=sample_rates=48000:channel_layouts=stereo[rtone]")
                lines.append(f"{raw}[araw];[araw][rtone]amix=inputs=2:duration=first:normalize=0[dxin]")
                raw = "[dxin]anull"
                log(f"room tone at {len(joins)} joins (floor {floor:.1f} dBFS)")
            elif rt:
                log("room tone skipped (no noise floor or no joins)")
        lines.append(f"{raw},{chain},asplit=2[dx][dxkey]")
    else:
        lines.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={dur}[dx]")
        lines.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={dur}[dxkey]")
    mix.append("[dx]")

    for k, s in enumerate(plan.get("sfx") or []):
        if s.get("file"):
            args = ["-i", P(s["file"])]
        else:
            kind = ALIASES.get(s.get("kind", "pop"), s.get("kind", "pop"))
            if kind not in SFX:
                log(f"unknown sfx '{kind}', skipped")
                continue
            args = sfx_input_args(kind, work)
        si = add_input(args)
        d = int(max(0, s.get("t", 0)) * 1000)
        lines.append(f"[{si}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={s.get('gain', 0.7)},"
                     f"adelay={d}|{d}[s{k}]")
        mix.append(f"[s{k}]")

    m = plan.get("music")
    if m and m.get("src"):
        src = P(m["src"])
        fit = m.get("fitTo") == "beats" or m.get("endButton")
        if fit:
            import music_fit
            key = hashlib.md5(f"{src}|{dur}|{m.get('start', 0)}|{m.get('endButton')}".encode()).hexdigest()[:10]
            fitted = os.path.join(work, f"music_fit_{key}.wav")
            if not os.path.exists(fitted):
                music_fit.fit(src, dur, fitted, start=m.get("start", 0), ending="button" if m.get("endButton") else "fade")
            mi = add_input(["-i", fitted])
            body = f"[{mi}:a]atrim=duration={dur},aformat=sample_rates=48000:channel_layouts=stereo"
        else:
            mi = add_input(["-stream_loop", "-1", "-i", src])
            fo = m.get("fadeOut", 1.5)
            body = (f"[{mi}:a]atrim=start={m.get('start', 0)}:duration={dur},asetpts=PTS-STARTPTS,"
                    f"aformat=sample_rates=48000:channel_layouts=stereo,afade=t=in:d=0.6,"
                    f"afade=t=out:st={max(0, dur - fo)}:d={fo}")
        vol = m.get("volume", 0.12)
        if "under" in m and has_a:
            vI = _measure_chain(src_path, chain) if src_path else None
            mI = measure(fitted if fit else src)["I"]
            if vI is not None and mI is not None:
                vol = db2lin(vI - float(m["under"]) - mI)
                log(f"music bed {m['under']} LU under dialogue (dialogue {vI:.1f}, music {mI:.1f} LUFS) -> x{vol:.3f}")
        lines.append(f"{body},volume={vol:.4f}[mus]")
        if m.get("duck", True) and has_a:
            lines.append(f"[mus][dxkey]{duck_filter(m, plan.get('words'))}[mduck]")
            mix.append("[mduck]")
        else:
            lines.append("[dxkey]anullsink")
            mix.append("[mus]")
    else:
        lines.append("[dxkey]anullsink")

    ceil = tgt["TP"] - 0.5  # headroom for AAC / inter-sample overs
    lines.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:normalize=0[premix]")
    lim = (f"aresample=192000,alimiter=limit={db2lin(ceil - 0.1):.4f}:level=disabled:attack=1:release=60:latency=1,"
           f"aresample=48000")
    gain = None
    if measured and src_path:
        # "two-pass inside the graph": render the premix once to measure it, then apply a linear gain into an
        # oversampled true-peak-ish limiter (re-measured once, because limiting costs loudness).
        m0 = _measure_graph(src_path, inputs, lines, "[premix]", "anull", dur)
        if m0 and m0["I"] is not None and m0["I"] > -70:
            gain = tgt["I"] - m0["I"]
            for _ in range(2 if m0["TP"] + gain > ceil else 0):
                m1 = _measure_graph(src_path, inputs, lines, "[premix]", f"volume={gain:.2f}dB,{lim}", dur)
                if not m1 or m1["I"] is None or abs(tgt["I"] - m1["I"]) < 0.3:
                    break
                gain += tgt["I"] - m1["I"]
            log(f"mix loudness {m0['I']:.1f} LUFS -> gain {gain:+.2f} dB (target {tgt['I']} LUFS / {tgt['TP']} dBTP)")
    if gain is not None:
        lines.append(f"[premix]volume={gain:.2f}dB,{lim},apad,atrim=duration={dur}[aout]")
    else:  # single-pass fallback (no source path given / measuring failed)
        lines.append(f"[premix]loudnorm=I={tgt['I']}:TP={ceil}:LRA={tgt['LRA']},{lim},apad,atrim=duration={dur}[aout]")
    return inputs, lines, "[aout]"


# ---------------------------------------------------------------- CLI
def _cli():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("measure"); s.add_argument("file"); s.add_argument("--platform")
    s = sub.add_parser("loudnorm"); s.add_argument("inp"); s.add_argument("out")
    s.add_argument("--platform", default="youtube"); s.add_argument("--voice", default=None, help="voice cfg JSON")
    s = sub.add_parser("voice"); s.add_argument("inp"); s.add_argument("out"); s.add_argument("--cfg", default="{}")
    s = sub.add_parser("sfx"); s.add_argument("kind", nargs="?"); s.add_argument("--out")
    s.add_argument("--all", action="store_true"); s.add_argument("--out-dir", default="sfx")
    sub.add_parser("list-sfx")
    a = ap.parse_args()
    if a.cmd == "measure":
        r = measure(a.file)
        if a.platform:
            t = LOUDNESS[a.platform]
            r["target"] = t
            r["pass"] = abs(r["I"] - t["I"]) <= 1 and r["TP"] <= t["TP"]
        print(json.dumps(r, indent=2))
    elif a.cmd == "loudnorm":
        t = LOUDNESS[a.platform]
        ex = voice_chain(json.loads(a.voice)) if a.voice else ""
        print(json.dumps(loudnorm_two_pass(a.inp, a.out, t["I"], t["TP"], t["LRA"], ex)["result"], indent=2))
    elif a.cmd == "voice":
        run(["ffmpeg", "-y", "-hide_banner", "-i", a.inp, "-vn", "-af", voice_chain(json.loads(a.cfg)), "-ar", "48000", a.out])
        print(json.dumps(measure(a.out), indent=2))
    elif a.cmd == "sfx":
        if a.all:
            for k in sorted(SFX):
                render_sfx(k, os.path.join(a.out_dir, f"{k}.wav"))
            log(f"{len(SFX)} sfx -> {a.out_dir}")
        else:
            render_sfx(a.kind, a.out or f"{a.kind}.wav")
    elif a.cmd == "list-sfx":
        print("\n".join(sorted(SFX)))


if __name__ == "__main__":
    _cli()
