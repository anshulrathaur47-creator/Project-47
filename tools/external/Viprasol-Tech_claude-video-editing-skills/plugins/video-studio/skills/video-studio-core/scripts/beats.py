#!/usr/bin/env python3
"""Beat / downbeat / onset tracker (numpy only; uses librosa for beats if it happens to be installed).

Spectral-flux onset envelope from a log-mel STFT of 22.05 kHz mono, tempo from the autocorrelation of
the envelope (60-200 BPM, log-gaussian prior around 120), dynamic-programming beat tracking (Ellis 2007),
downbeats = every 4th beat, phase chosen by the strongest low-band accent.

usage: beats.py AUDIO_OR_VIDEO [--out work/beats.json] [--peaks] [--fps 30]
  writes {bpm, beats:[s], downbeats:[s], onsets:[s], duration}
  --peaks also writes <dir of --out>/peaks.json {fps, values:[0..1]} (per-video-frame peak, for waveforms)

API: track(path) -> dict, audio_peaks(path, fps=30, out=None) -> list
"""
import argparse, os
import numpy as np
from audio_chain import decode
from vs_common import log, save_json

SR = 22050
NFFT, HOP = 1024, 256
FPS_ENV = SR / HOP  # onset-envelope frames per second (~86)
LAG = 1.0 / FPS_ENV  # flux peaks ~1 frame before the true onset (measured on a click track)


def _mel_fb(n_mels=64, fmin=30.0, fmax=8000.0):
    mel = lambda f: 2595 * np.log10(1 + f / 700)
    imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = imel(np.linspace(mel(fmin), mel(fmax), n_mels + 2))
    f = np.fft.rfftfreq(NFFT, 1 / SR)
    fb = np.zeros((n_mels, len(f)))
    for i in range(n_mels):
        lo, c, hi = pts[i:i + 3]
        fb[i] = np.clip(np.minimum((f - lo) / (c - lo), (hi - f) / (hi - c)), 0, None)
    return fb, pts[1:-1]


def onset_envelope(y):
    """Returns (envelope, low-band envelope, log-mel spectrogram), per STFT frame."""
    y = np.concatenate([np.zeros(NFFT // 2), y, np.zeros(NFFT // 2)])
    n = 1 + (len(y) - NFFT) // HOP
    fr = np.lib.stride_tricks.sliding_window_view(y, NFFT)[::HOP][:n] * np.hanning(NFFT)
    S = np.abs(np.fft.rfft(fr, axis=1))
    fb, centres = _mel_fb()
    M = np.log1p(100 * (S @ fb.T))
    D = np.maximum(0, np.diff(M, axis=0, prepend=np.zeros((1, M.shape[1]))))
    env = D.sum(axis=1)
    low = D[:, centres < 200].sum(axis=1)
    k = int(FPS_ENV)  # remove slow trend (~1 s)
    trend = np.convolve(env, np.ones(k) / k, mode="same")
    env = np.maximum(0, env - trend)
    return env / (env.max() + 1e-12), low / (low.max() + 1e-12), M


def estimate_period(env, lo_bpm=60, hi_bpm=200, prior_bpm=120):
    """Beat period in envelope frames (float) from the autocorrelation, with an octave-wide prior."""
    x = env - env.mean()
    ac = np.fft.irfft(np.abs(np.fft.rfft(x, 2 * len(x))) ** 2)[: len(x)]
    lags = np.arange(len(ac))
    bpm = 60 * FPS_ENV / np.maximum(lags, 1)
    w = np.exp(-0.5 * (np.log2(bpm / prior_bpm) / 1.0) ** 2) * (bpm >= lo_bpm) * (bpm <= hi_bpm)
    score = ac * w
    L = int(np.argmax(score))
    if 1 <= L < len(ac) - 1:  # parabolic refinement
        a, b, c = ac[L - 1], ac[L], ac[L + 1]
        L = L + 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    return float(L)


def dp_beats(env, period, tightness=100.0):
    """Ellis (2007) dynamic programming beat tracker. Returns beat frame indices."""
    p = period
    win = np.exp(-0.5 * (np.arange(-int(p), int(p) + 1) * 32.0 / p) ** 2)
    local = np.convolve(env, win, mode="same")
    n = len(local)
    cum = local.copy()
    back = -np.ones(n, dtype=int)
    lo, hi = int(round(p / 2)), int(round(2 * p))
    offs = np.arange(lo, hi + 1)
    pen = -tightness * np.log(offs / p) ** 2
    for t in range(lo, n):
        prev = t - offs
        ok = prev >= 0
        if not ok.any():
            continue
        cand = cum[prev[ok]] + pen[ok]
        j = int(np.argmax(cand))
        cum[t] = local[t] + cand[j]
        back[t] = prev[ok][j]
    # start from the best score in the last beat period
    tail = np.arange(max(0, n - int(p)), n)
    t = int(tail[np.argmax(cum[tail])])
    beats = []
    while t >= 0:
        beats.append(t)
        t = back[t]
    beats = np.array(beats[::-1])
    strong = local[beats] > 0.3 * np.sqrt(np.mean(local ** 2))  # trim silent lead-in / tail
    if strong.any():
        first, last = np.argmax(strong), len(strong) - 1 - np.argmax(strong[::-1])
        beats = beats[first:last + 1]
    return beats


def pick_onsets(env, delta=0.07, min_gap=0.05):
    w = int(0.1 * FPS_ENV)
    out, last = [], -1e9
    for i in range(len(env) - 1):
        seg = env[max(0, i - w): i + w + 1]
        if env[i] == seg.max() and env[i] > seg.mean() + delta and i / FPS_ENV - last >= min_gap:
            out.append(i / FPS_ENV + LAG)
            last = i / FPS_ENV
    return out


def downbeat_phase(beats_f, env, low, mel):
    """Which of the 4 beat phases is beat 1: low-band accent + harmonic/timbre change between beat-synchronous
    spectra (bars start where content changes) + a small prior for the first beat (most music starts on a 1)."""
    if len(beats_f) < 8:
        return 0
    acc = 0.6 * low + 0.4 * env
    seg = np.split(mel, beats_f[1:])
    B = np.array([s.mean(axis=0) for s in seg[: len(beats_f)]])
    nov = np.r_[0, np.linalg.norm(np.diff(B, axis=0), axis=1)]
    sc = []
    for k in range(4):
        a = acc[beats_f[k::4]].mean() / (acc[beats_f].mean() + 1e-9)
        n = nov[k::4].mean() / (nov.mean() + 1e-9)
        sc.append(a + n + (0.1 if k == 0 else 0))
    return int(np.argmax(sc))


def track(path):
    """Beat-track an audio or video file. Returns {bpm, beats, downbeats, onsets, duration} (seconds)."""
    y = decode(path, SR, 1)[:, 0].astype(np.float64)
    env, low, mel = onset_envelope(y)
    beats_t = None
    try:  # optional: librosa beats if installed
        import librosa
        tempo, bf = librosa.beat.beat_track(y=y.astype(np.float32), sr=SR, hop_length=HOP)
        beats_f = np.asarray(bf)
    except Exception:
        beats_f = dp_beats(env, estimate_period(env))
    # frame t of the envelope is centred at sample t*HOP (we padded NFFT/2)
    beats_t = beats_f * HOP / SR + LAG
    # tempo from a least-squares fit of beat index vs time (robust to 1-frame quantisation of each beat)
    bpm = 60 / float(np.polyfit(np.arange(len(beats_t)), beats_t, 1)[0]) if len(beats_t) > 2 else 0.0
    # downbeat phase: strongest summed accent (low band weighted) on every 4th beat
    phase = downbeat_phase(beats_f, env, low, mel)
    r = lambda a: [round(float(v), 3) for v in a]
    return {"bpm": round(bpm, 2), "beats": r(beats_t), "downbeats": r(beats_t[phase::4]),
            "onsets": r(pick_onsets(env)), "duration": round(len(y) / SR, 3)}


def audio_peaks(path, fps=30, out=None):
    """Per-video-frame peak amplitude normalised to 0..1. Writes {fps, values} to `out` if given."""
    y = np.abs(decode(path, 48000, 1)[:, 0])
    spf = 48000 / fps
    n = int(np.ceil(len(y) / spf))
    vals = [float(y[int(i * spf): int((i + 1) * spf)].max(initial=0)) for i in range(n)]
    m = max(vals) if vals and max(vals) > 0 else 1.0
    vals = [round(v / m, 3) for v in vals]
    if out:
        save_json(out, {"fps": fps, "values": vals})
    return vals


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out", default="work/beats.json")
    ap.add_argument("--peaks", action="store_true")
    ap.add_argument("--fps", type=float, default=30)
    a = ap.parse_args()
    res = track(a.src)
    save_json(a.out, res)
    log(f"{res['bpm']} BPM, {len(res['beats'])} beats, {len(res['downbeats'])} downbeats -> {a.out}")
    if a.peaks:
        p = os.path.join(os.path.dirname(os.path.abspath(a.out)), "peaks.json")
        audio_peaks(a.src, a.fps, p)
        log(f"peaks -> {p}")
