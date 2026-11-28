#!/usr/bin/env python3
"""Cut a music track to an exact length, musically: edits only on bar lines, the ending lands on a downbeat.

How: beat/bar grid from beats.py -> keep the song's real ending (last strong downbeat) -> remove (or repeat)
whole bars where the joined bars sound most alike, keeping phrase position (4-bar) when possible ->
short equal-power crossfade into each bar line -> sub-bar remainder becomes a pickup before the first
downbeat (or extra tail) -> "button" ending (hit on the downbeat + short ringing decay) or a fade over the
last bar. Output length is exact to the sample.

usage: music_fit.py music.mp3 --duration 14.7 --out fitted.wav [--start 0] [--ending button|fade] [--tail 0.6]
API:   fit(src, duration, out, start=0, ending="button", tail=0.6) -> dict
"""
import argparse, json
import numpy as np
import beats as B
from audio_chain import decode, write_wav, _reverb
from vs_common import log

SR = 48000


def _bar_features(src, db):
    """Mean log-mel spectrum of each bar [db[i], db[i+1])."""
    y = decode(src, B.SR, 1)[:, 0].astype(np.float64)
    _, _, mel = B.onset_envelope(y)
    f = (np.asarray(db) * B.FPS_ENV).astype(int).clip(0, len(mel) - 1)
    return np.array([mel[f[i]:max(f[i + 1], f[i] + 1)].mean(axis=0) for i in range(len(db) - 1)])


def _edit(seq, D, feat, si):
    """Remove D bars (D > 0) or repeat -D bars (D < 0) at the most seamless bar line. Returns new seq."""
    dist = lambda a, b: float(np.linalg.norm(feat[a] - feat[b]))
    md = np.mean([dist(seq[i], seq[i + 1]) for i in range(len(seq) - 1)]) + 1e-9 if len(seq) > 1 else 1.0
    best = None
    if D > 0:
        for j in range(1 if len(seq) - D >= 2 else 0, len(seq) - D):  # keep the first and the final bar
            c = dist(seq[j + D], seq[j]) / md
            c -= 0.3 * (j % 4 == 0) + 0.3 * ((seq[j + D] - si) % 4 == j % 4)
            best = min(best or (c, j), (c, j))
        j = best[1]
        return seq[:j] + seq[j + D:]
    K = -D
    for j in range(0, len(seq) - K):
        c = dist(seq[j], seq[j + K]) / md - 0.3 * (K % 4 == 0) - 0.2 * (j % 4 == 0)
        best = min(best or (c, j), (c, j))
    j = best[1]
    return seq[:j + K] + seq[j:]


def fit(src, duration, out, start=0.0, ending="button", tail=0.6, xfade=0.06):
    """Write `out` (48 kHz stereo float WAV) exactly `duration` s long. Returns a summary dict."""
    x = decode(src, SR, 2).astype(np.float64)
    n_out = int(round(duration * SR))
    g = B.track(src)
    db = [t for t in g["downbeats"] if t < len(x) / SR]
    if len(db) < 3:  # no usable grid: plain trim/loop with fade
        log("music_fit: no bar grid found, plain trim + fade")
        y = np.resize(x[int(start * SR):].T, (2, n_out)).T
        y[-int(min(1.5, duration / 3) * SR):] *= np.linspace(1, 0, int(min(1.5, duration / 3) * SR))[:, None]
        write_wav(out, y)
        return {"path": out, "bpm": g["bpm"], "edits": 0, "grid": False}
    bar = float(np.median(np.diff(db)))
    db = db + [db[-1] + bar] if db[-1] + bar <= len(x) / SR + 0.05 else db
    rms = np.array([np.sqrt(np.mean(x[int(a * SR):int(b * SR)] ** 2)) for a, b in zip(db[:-1], db[1:])])
    strong = [i for i in range(1, len(db)) if rms[i - 1] >= 0.3 * np.median(rms)]
    tail = tail if ending == "button" else 0.0
    ei = strong[-1] if strong else len(db) - 1  # song's real ending downbeat
    si = next((i for i, t in enumerate(db) if t >= start - 0.05), 0)
    si = min(si, ei - 1)
    t_hit = max(0.0, duration - tail)
    nb = int(np.floor(t_hit / bar + 1e-6))
    r = t_hit - nb * bar
    seq = list(range(si, ei))
    feat = _bar_features(src, db)
    edits = 0
    if nb == 0:
        seq = []
    while seq and len(seq) != nb:
        D = len(seq) - nb
        seq = _edit(seq, D if D > 0 else -min(-D, len(seq) - 1), feat, si)
        edits += 1
    # pickup (anacrusis) before the first downbeat if there is audio there, else extend the tail
    head = int(r * SR) if (seq and db[seq[0]] - r >= 0) else 0
    tail_eff = duration - nb * bar - head / SR
    xf = int(xfade * SR)
    parts = []
    if head:
        p = x[int(db[seq[0]] * SR) - head:int(db[seq[0]] * SR)].copy()
        p[: min(len(p), int(0.03 * SR))] *= np.linspace(0, 1, min(len(p), int(0.03 * SR)))[:, None]
        parts.append(p)
    runs = []
    for b in seq:
        if runs and runs[-1][1] == b:
            runs[-1][1] = b + 1
        else:
            runs.append([b, b + 1])
    for k, (a, b) in enumerate(runs):
        seg = x[int(db[a] * SR):int(db[b] * SR)].copy()
        if parts and k > 0 and int(db[a] * SR) - xf >= 0:  # equal-power crossfade into this bar line
            pre = x[int(db[a] * SR) - xf:int(db[a] * SR)]
            th = np.linspace(0, np.pi / 2, xf)[:, None]
            parts[-1][-xf:] = parts[-1][-xf:] * np.cos(th) + pre * np.sin(th)
        parts.append(seg)
    e0 = int(db[ei] * SR) if seq else int(start * SR)
    tl = x[e0:e0 + int(tail_eff * SR) + 1]
    tl = np.vstack([tl, np.zeros((max(0, int(tail_eff * SR) + 1 - len(tl)), 2))])
    if ending == "button" and seq:
        t = np.arange(len(tl)) / SR
        env = np.where(t < 0.08, 1.0, np.exp(-(t - 0.08) / max(0.05, (tail_eff - 0.08) / 5)))
        hit = tl[: int(0.25 * SR)] * np.hanning(2 * min(len(tl), int(0.25 * SR)))[-min(len(tl), int(0.25 * SR)):, None]
        ring = _reverb(hit, rt60=max(0.4, tail_eff), wet=0.5, lp=5000)[:len(tl)] - np.vstack(
            [hit, np.zeros((max(0, len(tl) - len(hit)), 2))])[:len(tl)]
        tl = tl * env[:, None] + ring[:len(tl)] * np.minimum(1, t / 0.08)[:, None] * 0.6
    parts.append(tl)
    y = np.vstack(parts)[:n_out]
    y = np.vstack([y, np.zeros((n_out - len(y), 2))])
    fo = int(min(bar, 2.5, duration / 2) * SR) if ending == "fade" else int(0.02 * SR)
    y[-fo:] *= (np.cos(np.linspace(0, np.pi / 2, fo)) ** 2)[:, None]
    if start > 0 and not head:
        y[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
    pk = np.max(np.abs(y))
    if pk > 0.99:
        y *= 0.99 / pk
    write_wav(out, y)
    res = {"path": out, "bpm": g["bpm"], "bar": round(bar, 3), "bars": nb, "edits": edits, "pickup": round(head / SR, 3),
           "hit": round(head / SR + nb * bar, 3) if ending == "button" else None, "duration": round(len(y) / SR, 4)}
    log(f"music_fit: {json.dumps(res)}")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--ending", choices=["button", "fade"], default="button")
    ap.add_argument("--tail", type=float, default=0.6)
    a = ap.parse_args()
    fit(a.src, a.duration, a.out, a.start, a.ending, a.tail)
