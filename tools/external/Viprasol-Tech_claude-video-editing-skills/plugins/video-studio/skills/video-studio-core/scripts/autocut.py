#!/usr/bin/env python3
"""Jump-cut editor: removes silences, filler words and any ranges you list, using word timestamps.
Writes <work>/cut.mp4, <work>/words.json (words re-timed to the cut), <work>/cutlist.json (segments + per-cut
metadata) and <work>/cuts.md (readable list of every cut).

usage: autocut.py --work WORKDIR [--max-gap 0.35] [--pad 0.08] [--fillers um,uh,erm]
                  [--cut "12.3-15.8,40-41.2"]   # extra ranges (source seconds) e.g. retakes
                  [--keep-all]                  # no silence/filler cutting, just copy (still writes words.json)
  editor-brain options (all off unless given; --genre NAME turns on that genre's preset from genres.json):
                  [--genre reel-talking-head]   # max gap, breath, filler policy, retakes, joins from the preset
                  [--breath 0.12]               # seconds kept before each word (natural breath); default = --pad
                  [--smart-cuts]                # cut at the quietest 10 ms inside each pause, never mid-word
                  [--filler-policy basic|remove|keep-natural|off]
                                                # basic = the --fillers list (default); remove = + you know, I mean,
                                                # basically, sort of, like-as-filler, Hindi matlab/toh/na (conservative)
                  [--retakes]                   # drop restarts ("let me start again", repeated openings < 8 s): keep the last take
                  [--xfade-ms 25]               # equal-power (qsin) audio crossfade at every join (default 25, min 20)
                  [--jcut 3]                    # audio leads video by N frames at joins between sentences
  Pauses come from Silero VAD (bundled with faster-whisper) as well as word gaps: a word Whisper stretched
  across a pause is shrunk back to its speech, so that pause gets cut. autocut.py --self-test runs the checks.
"""
import argparse, bisect, os, re, subprocess, sys, tempfile
from vs_common import load_json, save_json, run, probe, log, die, norm

BASIC_FILLERS = "um,uh,uhm,umm,erm,er,ah,hmm,mm,uhh"
# Hindi/Haryanvi discourse fillers: removed (policy "remove") only when they stand alone between pauses/punctuation
HINDI_FILLERS = {norm(x) for x in ("matlab", "toh", "haan", "accha", "acha", "achha", "yaani", "yani",
                                   "बस", "मतलब", "तो", "हाँ", "हां", "अच्छा", "यानी", "यानि")}
XFADE_MS, MIN_XFADE_MS = 25, 20           # joins always crossfade; a fade to silence leaves a hole in the noise floor
PUNCT_AFTER = re.compile(r"[,;:.!?…—\-।॥]$")
CUES = ["let me start again", "let me start over", "let me try that again", "let me try again", "let me redo that",
        "let me say that again", "let me rephrase", "start again", "start over", "scratch that", "one more time",
        "from the top", "take two", "phir se bolta", "dobara bolta"]


# ---------------- word analysis ----------------
def gap_before(words, i):
    return words[i]["start"] - words[i - 1]["end"] if i > 0 else 9.0


def gap_after(words, i):
    return words[i + 1]["start"] - words[i]["end"] if i + 1 < len(words) else 9.0


def bracketed(words, i, j, pause=0.2):
    """True when words[i..j] stand apart: clause break / pause before AND comma / pause after."""
    before = i == 0 or PUNCT_AFTER.search(words[i - 1]["w"]) or gap_before(words, i) > pause
    after = PUNCT_AFTER.search(words[j]["w"]) or gap_after(words, j) > pause
    return bool(before and after)


def find_fillers(words, policy, basic):
    """Indices of filler words to remove. Conservative: multi-word / ambiguous fillers only when they stand apart."""
    if policy == "off":
        return {}
    hes = basic if policy == "basic" else basic | {"erm", "uh", "um", "uhm", "umm", "er", "hmm", "ahh", "uhh", "mmm"}
    out = {i: w["w"] for i, w in enumerate(words) if norm(w["w"]) in hes}
    if policy in ("basic", "keep-natural"):
        return out
    n = [norm(w["w"]) for w in words]
    pairs = {("you", "know"), ("i", "mean"), ("sort", "of"), ("kind", "of")}
    verbs = {"look", "looks", "looked", "feel", "feels", "felt", "seem", "seems", "sound", "sounds", "would", "i'd", "you'd",
             "we'd", "they'd", "don't", "didn't", "do", "does", "things", "something", "anything", "nothing"}
    for i in range(len(words)):
        if i + 1 < len(words) and (n[i], n[i + 1]) in pairs and bracketed(words, i, i + 1):
            if (n[i], n[i + 1]) == ("kind", "of") and not PUNCT_AFTER.search(words[i + 1]["w"]):
                continue                                   # "a kind of fish" is not a filler
            out[i] = words[i]["w"]; out[i + 1] = words[i + 1]["w"]
        elif n[i] in ("basically", "literally", "actually") and PUNCT_AFTER.search(words[i]["w"]) and bracketed(words, i, i):
            out[i] = words[i]["w"]
        elif n[i] == "like" and (words[i]["w"].endswith(",") or bracketed(words, i, i, 0.25)) and (i == 0 or n[i - 1] not in verbs):
            out[i] = words[i]["w"]
        elif n[i] in HINDI_FILLERS and bracketed(words, i, i, 0.25):
            out[i] = words[i]["w"]
        elif n[i] in ("na", "ना") and gap_before(words, i) > 0.25 and gap_after(words, i) > 0.25:
            out[i] = words[i]["w"]
    return out


def is_start(words, k):
    return k == 0 or PUNCT_AFTER.search(words[k - 1]["w"]) or gap_before(words, k) > 0.3


def find_retakes(words, skip, n_gram=3, window=8.0):
    """[(first, last_exclusive, reason)] word ranges to drop so only the last take survives."""
    n = [norm(w["w"]) for w in words]
    out = []
    # 1. spoken cue: drop the sentence holding the cue (and the flubbed sentence before it when the cue opens a sentence)
    for i in range(len(words)):
        for cue in CUES:
            c = cue.split()
            if n[i:i + len(c)] == c:
                s = i
                while s > 0 and not is_start(words, s):
                    s -= 1
                if s == i or (s >= i - 1 and n[s] == "sorry"):
                    p = s - 1
                    while p > 0 and not is_start(words, p):
                        p -= 1
                    if p >= 0 and words[s]["start"] - words[max(p, 0)]["start"] <= window:
                        s = max(p, 0)
                e = i + len(c)
                if e < len(words) and n[e] in ("sorry", "okay", "ok"):
                    e += 1
                out.append((s, e, f"retake cue '{cue}'"))
                break
    # 2. repeated opening n-gram within the window: speaker restarted the line
    kept = [i for i in range(len(words)) if i not in skip]
    pos = {i: k for k, i in enumerate(kept)}
    for m in kept:
        km = pos[m]
        g = [n[x] for x in kept[km:km + n_gram]]
        if len(g) < n_gram:
            break
        restart = gap_before(words, m) > 0.15 or PUNCT_AFTER.search(words[m - 1]["w"] if m else ".")
        if not restart:
            continue
        for kk in range(km - 1, -1, -1):
            k = kept[kk]
            if words[m]["start"] - words[k]["start"] > window or km - kk > 25:
                break
            if [n[x] for x in kept[kk:kk + n_gram]] == g and is_start(words, k):
                out.append((k, m, f"restart: '{' '.join(g)}...' repeated"))
                break
    return out


# ---------------- audio ----------------
def pcm16k(work, src):
    """Mono float32 16 kHz samples of <work>/audio16k.wav (or the source); None if FFmpeg cannot decode it."""
    import numpy as np
    wav = os.path.join(work, "audio16k.wav")
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", wav if os.path.exists(wav) else src, "-f", "f32le", "-ac", "1",
                        "-ar", "16000", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return np.frombuffer(p.stdout, dtype=np.float32) if p.returncode == 0 else None


def load_rms(work, src, hop=0.01):
    """RMS per 10 ms frame of the 16 kHz audio. None when numpy is unavailable or the audio cannot be decoded."""
    try:
        import numpy as np
    except ImportError:
        return None
    x, sr = pcm16k(work, src), 16000
    if x is None:
        return None
    X = np.fft.rfft(x)               # ignore < 150 Hz: wind/handling rumble is not "content" and not a quiet point
    X[: int(150 * len(x) / sr)] = 0
    x = np.fft.irfft(X, len(x))
    n = int(sr * hop)
    frames = len(x) // n
    if frames == 0:
        return None
    return np.sqrt((x[:frames * n].reshape(frames, n) ** 2).mean(axis=1) + 1e-12), hop


def speech_regions(work, src, min_silence):
    """[(start, end)] s of speech from Silero VAD (ships inside faster-whisper); None if faster-whisper is missing.
    Only silences >= min_silence split regions (shorter ones are never cut anyway)."""
    try:
        from faster_whisper.vad import VadOptions, get_speech_timestamps
    except ImportError:
        return None
    x = pcm16k(work, src)          # not faster_whisper.decode_audio: it breaks on newer PyAV (metadata_errors)
    if x is None:
        die(f"cannot decode the audio of {src} (no audio track?)")
    opts = VadOptions(min_silence_duration_ms=int(min_silence * 1000), speech_pad_ms=30)
    return [(t["start"] / 16000, t["end"] / 16000) for t in get_speech_timestamps(x, opts)]


def vad_fix_words(words, regions, min_fix=0.1):
    """Whisper often stretches a word over the pause beside it, so the word gaps hide the pause. Shrink such a
    word to the VAD speech region it overlaps most (when >= min_fix s of it is VAD silence). A word with real
    speech on both sides of a pause, or none at all, is left alone: never cut sound you haven't heard."""
    starts = [s for s, _ in regions]
    out, fixed = [], 0
    for w in words:
        ov, j = [], bisect.bisect_left(starts, w["end"]) - 1
        while j >= 0 and regions[j][1] > w["start"]:
            s, e = regions[j]
            ov.append((min(w["end"], e) - max(w["start"], s), s, e)); j -= 1
        ov.sort(reverse=True)
        if not ov or ov[0][0] < 0.05 or (len(ov) > 1 and ov[1][0] >= min_fix):
            out.append(w); continue
        ns, ne = max(w["start"], ov[0][1]), min(w["end"], ov[0][2])
        if (ns - w["start"]) + (w["end"] - ne) < min_fix:
            out.append(w); continue
        out.append(dict(w, start=round(ns, 3), end=round(ne, 3))); fixed += 1
    return out, fixed


def quietest(rms, lo, hi):
    """Centre time of the quietest 10 ms frame in [lo, hi]."""
    r, hop = rms
    a, b = max(0, int(lo / hop)), min(len(r), int(hi / hop) + 1)
    if b - a < 1:
        return None
    return (a + int(r[a:b].argmin())) * hop + hop / 2


def keep_loud_gaps(segs, rms, words, dur, min_gap=0.5, margin_db=12.0):
    """Never cut sound you haven't heard: a word-free gap that is about as loud as the speech (singing,
    untranscribed dialect, music, laughter) is kept, not removed as a pause. Real pauses are 15-40 dB quieter."""
    import numpy as np
    r, hop = rms
    db = 20 * np.log10(r + 1e-9)
    sp = [db[int(w["start"] / hop):int(w["end"] / hop) + 1] for w in words]
    sp = np.concatenate([x for x in sp if len(x)]) if any(len(x) for x in sp) else db
    speech = float(np.median(sp))
    loud = lambda a, b: b - a >= min_gap and float(np.median(db[int(a / hop):int(b / hop) + 1])) > speech - margin_db
    out = [list(x) for x in segs]
    if out and loud(0.0, out[0][0]):
        out[0][0] = 0.0
    merged = [out[0]] if out else []
    for sg in out[1:]:
        if loud(merged[-1][1], sg[0]):
            merged[-1][1], merged[-1][3] = sg[1], sg[3]
        else:
            merged.append(sg)
    if merged and loud(merged[-1][1], dur):
        merged[-1][1] = dur
    if [tuple(x) for x in merged] != list(segs):
        log(f"kept loud word-free audio (singing/music/untranscribed speech): {len(segs)} -> {len(merged)} segments")
    return [tuple(round(v, 3) if isinstance(v, float) else v for v in x) for x in merged]


# ---------------- segments ----------------
def build_segments(words, removed, dur, max_gap, lead, tail, manual, rms=None):
    """Keep-segments in source time, plus a list of kept word index groups per segment."""
    segs = []                                     # [start, end, first_kept_idx, last_kept_idx]
    prev_kept = None
    for i, w in enumerate(words):
        if i in removed:
            continue
        s, e = max(0.0, w["start"] - lead), min(dur, w["end"] + tail)
        removed_between = prev_kept is not None and any(j in removed for j in range(prev_kept + 1, i))
        if segs and s - segs[-1][1] <= max_gap and not removed_between:
            segs[-1][1] = max(segs[-1][1], e); segs[-1][3] = i
        else:
            segs.append([s, e, i, i])
        prev_kept = i
    if rms:                                       # snap boundaries to the quietest point, never into a word
        for k, sg in enumerate(segs):
            fw, lw = words[sg[2]], words[sg[3]]
            prev_end = max([words[j]["end"] for j in range(sg[2]) if words[j]["end"] <= fw["start"]] or [0.0])
            nxt_start = min([words[j]["start"] for j in range(sg[3] + 1, len(words))] or [dur])
            if sg[2] > 0 or fw["start"] - lead > 0.05:
                q = quietest(rms, max(prev_end + 0.01, fw["start"] - lead - 0.10), fw["start"] - lead)
                if q is not None:
                    sg[0] = max(0.0, min(q, fw["start"] - 0.02))
            q = quietest(rms, lw["end"] + 0.03, min(nxt_start - 0.01, lw["end"] + max(tail, 0.12)))
            if q is not None:
                sg[1] = min(dur, max(q, lw["end"] + 0.02))
    segs = [tuple(s) for s in segs]
    for cs, ce in manual:
        out = []
        for s, e, a_, b_ in segs:
            if ce <= s or cs >= e:
                out.append((s, e, a_, b_)); continue
            if cs > s: out.append((s, cs, a_, b_))
            if ce < e: out.append((ce, e, a_, b_))
        segs = out
    segs = [(round(s, 3), round(e, 3), a_, b_) for s, e, a_, b_ in segs if e - s > 0.12]
    return segs


def snap_manual(manual, words):
    """--smart-cuts: a manual range edge inside a word moves to that word's edge (no mid-word cuts)."""
    out = []
    for cs, ce in manual:
        for w in words:
            if w["start"] < cs < w["end"]: cs = w["start"]
            if w["start"] < ce < w["end"]: ce = w["end"]
        out.append((cs, ce))
    return out


def audio_ranges(segs, words, fps, jcut, dur):
    """Audio keep-ranges. With --jcut, at a sentence join the next shot's audio starts N frames early (J-cut)."""
    a = [[s, e] for s, e, _, _ in segs]
    if not jcut:
        return a
    for k in range(len(segs) - 1):
        last_w, next_w = words[segs[k][3]], words[segs[k + 1][2]]
        if not re.search(r"[.!?…।॥]$", last_w["w"]):
            continue
        j = min(jcut / fps, a[k][1] - (last_w["end"] + 0.02), a[k + 1][0] - segs[k][1])
        if j >= 0.5 / fps:
            a[k][1] -= j; a[k + 1][0] -= j
    return [[round(s, 4), round(e, 4)] for s, e in a]


def graph(segs, aud, xfade, dur):
    """Video: hard cuts. Audio: every join is an equal-power (qsin) crossfade of `xfade` s centred on the cut, so
    the noise floor runs straight through (uncorrelated sides: cos^2 + sin^2 = 1, no dip)."""
    parts = [f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}]" for i, (s, e, _, _) in enumerate(segs)]
    parts.append("".join(f"[v{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[v]")
    total = sum(e - s for s, e, _, _ in segs)
    if xfade > 0 and len(aud) > 1:
        x = min(xfade, min(e - s for s, e in aud) / 3)
        ext = [[max(0.0, s - x / 2), min(dur, e + x / 2)] for s, e in aud]
        lead0 = aud[0][0] - ext[0][0]
        for i, (s, e) in enumerate(ext):
            parts.append(f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS[a{i}]")
        cur = "a0"
        for i in range(1, len(ext)):
            parts.append(f"[{cur}][a{i}]acrossfade=d={x:.4f}:c1=qsin:c2=qsin[x{i}]"); cur = f"x{i}"
        parts.append(f"[{cur}]atrim=start={lead0:.4f}:end={lead0 + total:.4f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.012,afade=t=out:st={max(0, total - 0.012):.4f}:d=0.012[a]")
    else:
        for i, (s, e) in enumerate(aud):
            d = e - s
            f = min(0.012, d / 4)
            parts.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS,afade=t=in:d={f},afade=t=out:st={d - f:.4f}:d={f}[a{i}]")
        parts.append("".join(f"[a{i}]" for i in range(len(aud))) + f"concat=n={len(aud)}:v=0:a=1[a]")
    return ";\n".join(parts)


# ---------------- reports ----------------
def describe_cuts(segs, words, removed, retake_idx, manual, dur, asl, fps):
    """One record per removed region (head, every join, tail) with type, duration and a Rule-of-Six score for joins."""
    from editor import cut_score
    cuts, out_t = [], 0.0
    bounds = [(0.0, segs[0][0], None, 0)] + [(segs[k][1], segs[k + 1][0], k, None) for k in range(len(segs) - 1)] + \
             [(segs[-1][1], dur, len(segs) - 1, None)]
    seg_out = []
    for s, e, _, _ in segs:
        seg_out.append(out_t); out_t += e - s
    for cs, ce, kprev, _ in bounds:
        if ce - cs < 0.005:
            continue
        inside = [i for i, w in enumerate(words) if w["start"] >= cs - 0.01 and w["end"] <= ce + 0.01]
        if any(i in retake_idx for i in inside):
            typ = "retake"
        elif any(cs < me and ce > ms for ms, me in manual):
            typ = "manual"
        elif any(i in removed for i in inside):
            typ = "filler"
        else:
            typ = "pause"
        rec = {"type": typ, "src_start": round(cs, 3), "src_end": round(ce, 3), "removed": round(ce - cs, 3),
               "out_at": round(seg_out[kprev + 1] if kprev is not None and kprev + 1 < len(segs) else (0.0 if kprev is None else out_t), 3)}
        if inside:
            rec["words"] = " ".join(words[i]["w"] for i in inside)[:120]
        if typ == "retake":
            rec["reason"] = retake_idx.get(inside[0]) if inside and inside[0] in retake_idx else "retake"
        if kprev is None:
            rec["where"] = "head"
        elif kprev == len(segs) - 1:
            rec["where"] = "tail"
        else:
            k = kprev
            pw = [words[i] for i in range(segs[k][2], segs[k][3] + 1) if i not in removed][-4:]
            nw = [words[i] for i in range(segs[k + 1][2], segs[k + 1][3] + 1) if i not in removed][:4]
            sc = cut_score(pw, nw, gap=ce - cs, seg_len=segs[k][1] - segs[k][0], asl=asl)
            rec["score"] = sc["score"]; rec["parts"] = sc["parts"]
        cuts.append(rec)
    return cuts


def write_md(path, cuts, dur, t0, settings):
    L = ["# Cut list", "", f"{dur:.2f}s -> {t0:.2f}s, removed {dur - t0:.2f}s in {len(cuts)} cuts.", "",
         "Settings: " + ", ".join(f"{k}={v}" for k, v in settings.items()), "",
         "| # | type | source | removed | at (out) | score | words |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for n, c in enumerate(cuts, 1):
        L.append(f"| {n} | {c['type']}{' (' + c['where'] + ')' if c.get('where') else ''} | {c['src_start']:.2f}-{c['src_end']:.2f} | "
                 f"{c['removed']:.2f}s | {c['out_at']:.2f} | {c.get('score', '')} | {c.get('words', '').replace('|', '/')} |")
    L += ["", "score = Rule-of-Six-lite (emotion 51, story 23, rhythm 10, eye-trace 7, 2D 5, 3D 4), heuristic. Below 45: check the join."]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work")
    ap.add_argument("--max-gap", type=float, default=None, help="pauses longer than this are cut (default 0.35)")
    ap.add_argument("--pad", type=float, default=None, help="breathing room kept around words (default 0.08)")
    ap.add_argument("--fillers", default=None, help=f"basic filler list (default {BASIC_FILLERS})")
    ap.add_argument("--cut", default="", help="comma list of start-end ranges to remove (source time)")
    ap.add_argument("--keep-all", action="store_true")
    ap.add_argument("--genre", default=None, help="genre preset from genres.json (editor.py genres)")
    ap.add_argument("--breath", type=float, default=None, help="seconds kept before each word (default = --pad)")
    ap.add_argument("--smart-cuts", action="store_true", default=None, help="quietest-point joins, no mid-word cuts")
    ap.add_argument("--filler-policy", choices=["basic", "remove", "keep-natural", "off"], default=None)
    ap.add_argument("--retakes", action="store_true", default=None)
    ap.add_argument("--xfade-ms", type=float, default=None)
    ap.add_argument("--jcut", type=int, default=None, help="frames audio leads picture at sentence joins")
    a = ap.parse_args()

    g = None
    if a.genre:
        from editor import load_genre
        try:
            g = load_genre(a.genre)
        except ValueError as e:
            die(str(e))
    ga = g["autocut"] if g else {}
    pick = lambda v, key, default: v if v is not None else ga.get(key, default)
    max_gap = pick(a.max_gap, "max_gap", 0.35)
    pad = pick(a.pad, "pad", 0.08)
    lead = pick(a.breath, "breath", pad)
    smart = bool(pick(a.smart_cuts, "smart_cuts", False))
    policy = a.filler_policy or ({"remove": "remove", "keep-natural": "keep-natural", "off": "off"}.get(ga.get("fillers")) if g else None) or "basic"
    retakes = bool(pick(a.retakes, "retakes", False))
    xfade = max(MIN_XFADE_MS, pick(a.xfade_ms, "xfade_ms", XFADE_MS)) / 1000.0  # presets saying 0/15 get 20
    jcut = pick(a.jcut, "jcut_frames", 0)
    keep_all = a.keep_all or (g is not None and not ga.get("enabled", True) and a.max_gap is None)

    src = os.path.join(a.work, "source.mp4")
    old_cl = os.path.join(a.work, "cutlist.json")
    if keep_all and os.path.exists(old_cl) and load_json(old_cl).get("kind") == "timeline":
        # a timeline.py assembly: its cut list (clip joins, transitions) is the edit - keep it, words already match
        log("keep-all on a timeline assembly: keeping timeline cutlist.json unchanged")
        return
    tr = load_json(os.path.join(a.work, "transcript.json"))
    info = probe(src)
    dur, fps = info["duration"], info.get("fps", 30) or 30
    words = tr["words"]
    if words and not keep_all:
        regions = speech_regions(a.work, src, max_gap)
        if regions is None:
            log("VAD unavailable (faster-whisper not installed): pauses come from word timestamps only")
        else:
            words, fixed = vad_fix_words(words, regions)
            log(f"VAD: {len(regions)} speech regions, re-timed {fixed} words that ran over a pause")
    basic = {norm(f) for f in (a.fillers or BASIC_FILLERS).split(",") if f.strip()}

    manual = []
    for r in [x for x in a.cut.split(",") if x.strip()]:
        s, e = r.split("-")
        manual.append((float(s), float(e)))
    if smart:
        manual = snap_manual(manual, words)

    removed, retake_idx = {}, {}
    if not keep_all:
        removed = find_fillers(words, policy, basic)
        if retakes:
            for s, e, why in find_retakes(words, set(removed)):
                for i in range(s, e):
                    removed[i] = words[i]["w"]; retake_idx[i] = why
                log(f"retake: drop '{' '.join(words[i]['w'] for i in range(s, e))[:70]}' ({why})")
    if keep_all or not words:
        segs = [(0.0, round(dur, 3), 0, max(0, len(words) - 1))]
    else:
        rms = load_rms(a.work, src) if smart else None
        if smart and rms is None:
            log("smart cuts: no audio analysis available (numpy / audio16k.wav), using padded word edges")
        segs = build_segments(words, removed, dur, max_gap, lead, pad, manual, rms)
        rms_all = rms or load_rms(a.work, src)
        if rms_all and segs and not manual:
            segs = keep_loud_gaps(segs, rms_all, [w for i, w in enumerate(words) if i not in removed], dur)
    if not segs:
        segs = [(0.0, round(dur, 3), 0, max(0, len(words) - 1))]

    aud = audio_ranges(segs, words, fps, jcut, dur) if words else [[s, e] for s, e, _, _ in segs]
    gf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    gf.write(graph(segs, aud, xfade, dur)); gf.close()
    out = os.path.join(a.work, "cut.mp4")
    log(f"cutting into {len(segs)} segments")
    run(["ffmpeg", "-y", "-hide_banner", "-i", src, "-filter_complex_script", gf.name, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", out])
    os.unlink(gf.name)

    # retime words
    new_words, t0, mapping = [], 0.0, []
    for s, e, _, _ in segs:
        mapping.append({"src_start": s, "src_end": e, "out_start": round(t0, 3)})
        for i, w in enumerate(words):
            if i in removed:
                continue
            if w["start"] >= s - 1e-3 and w["end"] <= e + 1e-3:
                nw = dict(w); nw["start"] = round(t0 + w["start"] - s, 3); nw["end"] = round(t0 + w["end"] - s, 3)
                new_words.append(nw)
        t0 += e - s
    save_json(os.path.join(a.work, "words.json"), {"language": tr.get("language"), "words": new_words, "duration": round(t0, 3)})
    settings = {"genre": a.genre, "max_gap": max_gap, "pad": pad, "breath": lead, "smart_cuts": smart, "filler_policy": policy,
                "retakes": retakes, "xfade_ms": round(xfade * 1000), "jcut_frames": jcut, "keep_all": keep_all}
    cuts = [] if keep_all else describe_cuts(segs, words, removed, retake_idx, manual, dur,
                                             tuple(g["asl_s"]) if g else (2.0, 4.0), fps)
    cl = {"segments": mapping, "removed_seconds": round(dur - t0, 2), "cuts": cuts, "settings": settings}
    if aud != [[s, e] for s, e, _, _ in segs]:
        cl["audio_segments"] = [{"src_start": s, "src_end": e} for s, e in aud]
    save_json(os.path.join(a.work, "cutlist.json"), cl)
    write_md(os.path.join(a.work, "cuts.md"), cuts, dur, t0, settings)
    by = {}
    for c in cuts:
        by[c["type"]] = by.get(c["type"], 0) + c["removed"]
    log(f"{dur:.1f}s -> {t0:.1f}s (removed {dur - t0:.1f}s). words.json has {len(new_words)} words"
        + (" | " + ", ".join(f"{k} {v:.1f}s" for k, v in by.items()) if by else ""))


def _self_test():
    w = lambda t, s, e: {"w": t, "start": s, "end": e}
    # Devanagari keeps its vowel signs: a stand-alone "तो" is a filler, "तो" inside a phrase is not
    ws = [w("बात", 0.0, 0.4), w("तो,", 0.8, 1.0), w("ये", 1.4, 1.6), w("है", 1.6, 1.8), w("तो", 1.8, 2.0), w("सही", 2.0, 2.3)]
    assert find_fillers(ws, "remove", set()) == {1: "तो,"}, find_fillers(ws, "remove", set())
    # "की बात है, के बात हो..." is not a restart (old norm turned both openings into "क बत ह")
    rt = [w("की", 0, .2), w("बात", .2, .5), w("है,", .5, .7), w("के", 1.0, 1.2), w("बात", 1.2, 1.5), w("हो", 1.5, 1.7),
          w("रही", 1.7, 1.9), w("थी", 1.9, 2.1)]
    assert find_retakes(rt, set()) == [], find_retakes(rt, set())
    # a pause Whisper swallowed into the next word is found by VAD and cut
    regs = [(0.29, 1.92), (2.56, 4.35), (4.99, 6.75)]
    ws = [w("हर", 0.3, 1.9), w("रास्सी", 1.9, 3.14)]
    assert len(build_segments(ws, {}, 4.0, 0.35, 0.08, 0.08, [])) == 1
    fw, n = vad_fix_words(ws, regs)
    assert n == 1 and (fw[1]["start"], fw[1]["end"]) == (2.56, 3.14), fw
    assert len(build_segments(fw, {}, 4.0, 0.35, 0.08, 0.08, [])) == 2
    # speech on both sides of a pause, or no speech at all: the word is left alone
    fw, n = vad_fix_words([w("एक", 4.0, 5.3), w("x", 7.0, 7.2)], regs)
    assert n == 0 and fw[0]["start"] == 4.0 and fw[1]["end"] == 7.2, fw
    g = graph([(0.0, 1.0, 0, 0), (2.0, 3.0, 1, 1)], [[0.0, 1.0], [2.0, 3.0]], 0.025, 3.0)
    assert "acrossfade=d=0.0250:c1=qsin:c2=qsin" in g, g
    log("autocut self-test OK")


if __name__ == "__main__":
    _self_test() if "--self-test" in sys.argv else main()
