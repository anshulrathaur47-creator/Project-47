#!/usr/bin/env python3
"""Word-level lyric alignment against a hand-stamped LRC.

Input: an isolated vocal stem (any format ffmpeg/soundfile reads) and the song's
line-level .lrc (hand-stamped with lyrics-sync; may carry [male]/[female]/[duet]/
[choir] voice tags, also written [female:] or (Female):). Output, in --out:

  <name>.aligned.lrc   line LRC, voice tags kept; each line starts at its first
                       aligned word when that line aligned well, else at the hand stamp
  <name>.words.json    per line: hand start, aligned start/end, tag, confidence,
                       words [{w, start, end, score, agree}]

Three passes with torchaudio's MMS_FA (wav2vec2 CTC, multilingual, romanised a-z):
  anchored each line alone inside its hand-stamped window
           [start - PRE, next start + POST]. This is the output.
  context  each line together with its neighbours, inside their joint window. Its word
           starts are the check on the anchored pass.
  global   all lyrics against the whole stem, no hints. Reported only (line_agreement:
           share of line starts within 0.75 s of the hand stamps); once it derails on
           a long song it stays derailed, so it does not drive the rating.

Scores are CTC posteriors (0..1), averaged over a word's characters. Sung vowels and
screams score low even when placed right, so confidence comes from agreement instead:
a word "agrees" when the anchored and the context pass put its start within 0.35 s.
Where they disagree the context timing wins if it keeps the word order (it sees the
next line, so it does not stretch a last word into an instrumental gap); such words
keep agree=false and from="context". A line's aligned start replaces the hand stamp
only when most of its words agree and it moves the stamp by at most 0.6 s. Word ends are capped at 3 s (CTC holds a last
character to the end of the window). A line needs checking ("check_lines", 1-based)
when fewer than 60% of its words agree or two of its words are over 4 s apart (both
passes can agree on a line smeared across an instrumental gap). Song rating, from
the share of words in lines that need no check: >= 0.85 high, >= 0.65 medium, else low. Emissions are cached next to the stem (*.mmsfa.pt).
"""
import argparse
import json
import math
import re
import statistics
import subprocess
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
import torch
import torchaudio
import torchaudio.functional as F

SR = 16000
PRE, POST = 0.5, 0.6          # anchored window around the hand stamps (s)
LAST_LINE_TAIL = 12.0         # window after the last stamp (s)
AGREE_TOL = 0.75              # global vs hand line start, counts as agreeing (s)
WORD_TOL = 0.35               # anchored vs context word start, counts as agreeing (s)
LINE_SHIFT_MAX = 0.6          # aligned line start may move this far from the hand stamp (s)
LINE_AGREE_OK = 0.6           # share of agreeing words for a line to count as checked
WORD_MAX = 3.0                # CTC holds a last character to the window end: cap word length (s)
LINE_GAP_MAX = 4.0            # a gap this long between words of one line is suspect (s)
FIRST_GAP = 0.6               # first word ending this long before the second one snapped early (s)

NUMS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
        "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten"}
TS = re.compile(r"^\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)$")
VOICE = re.compile(r"^(?:\[(male|female|duet|choir|both):?\]|\((male|female|duet|choir|both)\):)\s*", re.I)


def parse_lrc(path):
    lines = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        m = TS.match(raw.strip())
        if not m:
            continue
        t = int(m.group(1)) * 60 + float(m.group(2))
        text = m.group(3)
        voice = None
        v = VOICE.match(text)
        if v:
            voice, text = (v.group(1) or v.group(2)).lower(), text[v.end():]
        if text.strip():
            lines.append({"hand": t, "voice": voice, "text": text.strip()})
    lines.sort(key=lambda l: l["hand"])
    return lines


def norm_word(w):
    if w in NUMS:
        return NUMS[w]
    w = unicodedata.normalize("NFKD", w.lower())
    w = w.replace("’", "'").replace("‘", "'")
    w = "".join(c for c in w if ("a" <= c <= "z") or c == "'").strip("'")
    return w


def tokenize_line(text):
    """Display words plus their normalised form; tokens that normalise to nothing
    (dashes, ellipses) are glued onto the previous word."""
    words = []
    for tok in text.replace("—", "— ").split():
        n = norm_word(tok)
        if n:
            words.append({"text": tok, "norm": n})
        elif words:
            words[-1]["text"] += " " + tok
        else:
            words.append({"text": tok, "norm": ""})
    if words and not words[0]["norm"]:
        lead = words.pop(0)["text"]
        if words:
            words[0]["text"] = lead + " " + words[0]["text"]
    return words


def load_audio(path):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], check=True, capture_output=True).stdout
    return torch.from_numpy(np.frombuffer(out, dtype=np.float32).copy())


class Aligner:
    def __init__(self):
        b = torchaudio.pipelines.MMS_FA
        self.model = b.get_model(with_star=False).eval()
        self.dict = b.get_dict(star=None)
        self.frame_s = 320 / SR   # wav2vec2 stride

    @torch.inference_mode()
    def emission(self, wav, chunk=20.0, ctx=2.0):
        """Log-probs for the whole song, computed in overlapping chunks."""
        n, c, x = len(wav), int(chunk * SR), int(ctx * SR)
        parts = []
        for s in range(0, n, c):
            a, b = max(0, s - x), min(n, s + c + x)
            em, _ = self.model(wav[a:b].unsqueeze(0))
            em = torch.log_softmax(em[0], dim=-1)
            f0 = round((s - a) / 320)
            f1 = f0 + math.ceil(min(c, n - s) / 320)
            parts.append(em[f0:f1])
        return torch.cat(parts)

    def align(self, em, norms):
        """CTC forced alignment of words (normalised) in emission slice em.
        Returns [(start_frame, end_frame, score)] per word, or None."""
        ids, owner = [], []
        for wi, w in enumerate(norms):
            for ch in w:
                if ch in self.dict:
                    ids.append(self.dict[ch])
                    owner.append(wi)
        if not ids:
            return None
        # CTC needs T >= tokens + repeats
        reps = sum(1 for i in range(1, len(ids)) if ids[i] == ids[i - 1])
        if em.shape[0] < len(ids) + reps:
            return None
        tgt = torch.tensor([ids], dtype=torch.int32)
        path, scores = F.forced_align(em.unsqueeze(0), tgt, blank=0)
        spans = F.merge_tokens(path[0], scores[0].exp())
        out = [None] * len(norms)
        for sp, wi in zip(spans, owner):
            if out[wi] is None:
                out[wi] = [sp.start, sp.end, [sp.score]]
            else:
                out[wi][1] = sp.end
                out[wi][2].append(sp.score)
        return [(o[0], o[1], float(np.mean(o[2]))) if o else None for o in out]


def run(vocals, lrc, out_dir, name, aligner, title=None, audio_name=None):
    lines = parse_lrc(lrc)
    for l in lines:
        l["words"] = tokenize_line(l["text"])
    wav = load_audio(vocals)
    dur = len(wav) / SR
    cache = Path(str(vocals) + ".mmsfa.pt")
    if cache.exists() and cache.stat().st_mtime > Path(vocals).stat().st_mtime:
        em = torch.load(cache)
    else:
        em = aligner.emission(wav)
        torch.save(em, cache)
    fs = aligner.frame_s

    def window(i, j):
        """Seconds covered by lines i..j: from line i's stamp to the stamp after line j."""
        a = max(0.0, lines[i]["hand"] - PRE)
        b = lines[j + 1]["hand"] + POST if j + 1 < len(lines) else min(dur, lines[j]["hand"] + LAST_LINE_TAIL)
        return int(a / fs), min(em.shape[0], int(b / fs))

    def fix_first(ws):
        """A short first word often snaps to noise at the window start: pull it up to the second."""
        if len(ws) > 1 and ws[1]["start"] - ws[0]["end"] > FIRST_GAP:
            d = min(ws[0]["end"] - ws[0]["start"], 0.4)
            ws[0]["start"], ws[0]["end"] = round(ws[1]["start"] - d, 2), ws[1]["start"]

    # context pass: each line aligned together with its neighbours in their joint window;
    # its word starts are the check for the anchored pass (local, so it cannot drift)
    ctx_words = []
    for i in range(len(lines)):
        lo, hi = max(0, i - 1), min(len(lines) - 1, i + 1)
        f0, f1 = window(lo, hi)
        seq = [(li, w) for li in range(lo, hi + 1) for w in lines[li]["words"] if w["norm"]]
        r = aligner.align(em[f0:f1], [w["norm"] for _, w in seq]) if seq else None
        mine = [{"start": round((f0 + x[0]) * fs, 2), "end": round((f0 + x[1] + 1) * fs, 2)} if x else None
                for (li, _), x in zip(seq, r or [None] * len(seq)) if li == i]
        if mine and all(mine):
            fix_first(mine)
        ctx_words.append([(m["start"], m["end"]) if m else None for m in mine] if r else [])

    # global pass: every line's words in one sequence
    flat = [(li, w["norm"]) for li, l in enumerate(lines) for w in l["words"] if w["norm"]]
    g = aligner.align(em, [n for _, n in flat]) or [None] * len(flat)
    g_start, g_words = {}, [[] for _ in lines]
    for (li, _), r in zip(flat, g):
        g_words[li].append(r[0] * fs if r else None)
        if r and li not in g_start:
            g_start[li] = r[0] * fs
    diffs = [abs(g_start[i] - l["hand"]) for i, l in enumerate(lines) if i in g_start]
    agree = sum(d <= AGREE_TOL for d in diffs) / max(1, len(lines))

    # anchored pass
    for i, l in enumerate(lines):
        f0, f1 = window(i, i)
        words = [w for w in l["words"] if w["norm"]]
        r = aligner.align(em[f0:f1], [w["norm"] for w in words]) if words else None
        l["global_start"] = round(g_start[i], 2) if i in g_start else None
        if not r:
            l["score"] = 0.0
            l["agree"] = 0.0
            l["max_gap"] = 0.0
            l["check"] = True
            for w in l["words"]:
                w.update(start=None, end=None, score=0.0)
            continue
        for w, (s, e, sc) in zip(words, r):
            w.update(start=round((f0 + s) * fs, 2), end=round((f0 + e + 1) * fs, 2), score=round(sc, 3))
        for w in l["words"]:
            w.setdefault("start", None); w.setdefault("end", None); w.setdefault("score", 0.0)
        fix_first(words)
        for k, w in enumerate(words):
            gs = g_words[i][k] if k < len(g_words[i]) else None
            ce = ctx_words[i][k] if k < len(ctx_words[i]) else None
            cs = ce[0] if ce else None
            w["global_start"] = round(gs, 2) if gs is not None else None
            w["context_start"] = cs
            w["agree"] = cs is not None and abs(cs - w["start"]) <= WORD_TOL
            w["from"] = "anchored"
        # where the passes disagree, take the context timing if it keeps the word order:
        # it sees the next line's words, so it does not stretch a last word into a gap
        nxt = lines[i + 1]["hand"] if i + 1 < len(lines) else dur
        for k, w in enumerate(words):
            ce = ctx_words[i][k] if k < len(ctx_words[i]) else None
            if w["agree"] or not ce:
                continue
            lo = words[k - 1]["start"] if k else l["hand"] - PRE
            hi = words[k + 1]["start"] if k + 1 < len(words) else nxt
            if lo < ce[0] < hi:
                w["start"], w["end"], w["from"] = ce[0], min(ce[1], hi), "context"
        for k, w in enumerate(words):
            hi = words[k + 1]["start"] if k + 1 < len(words) else nxt
            w["end"] = round(min(w["end"], hi, w["start"] + WORD_MAX), 2)
        l["score"] = round(float(np.mean([w["score"] for w in words])), 3)
        l["agree"] = round(sum(w["agree"] for w in words) / len(words), 3)
        l["max_gap"] = round(max([b["start"] - a["end"] for a, b in zip(words, words[1:])], default=0.0), 2)
        l["check"] = l["agree"] < LINE_AGREE_OK or l["max_gap"] > LINE_GAP_MAX

    all_words = [w for l in lines for w in l["words"] if w["norm"]]
    wscores = [w["score"] for w in all_words]
    summary = {
        "lines": len(lines),
        "words": len(all_words),
        "mean_word_score": round(float(np.mean(wscores)), 3) if wscores else 0.0,
        "word_agreement": round(sum(w.get("agree", False) for w in all_words) / max(1, len(all_words)), 3),
        "line_agreement": round(agree, 3),
        "line_median_offset": round(statistics.median(diffs), 2) if diffs else None,
        "check_lines": [i + 1 for i, l in enumerate(lines) if l["check"]],
        "ok_words": round(sum(len([w for w in l["words"] if w["norm"]]) for l in lines if not l["check"])
                          / max(1, len(all_words)), 3),
    }
    ok = summary["ok_words"]
    summary["confidence"] = "high" if ok >= 0.85 else "medium" if ok >= 0.65 else "low"

    out_dir.mkdir(parents=True, exist_ok=True)
    lrc_out, js_lines = [], []
    for i, l in enumerate(lines):
        timed = [w for w in l["words"] if w.get("start") is not None]
        first = timed[0]["start"] if timed else None
        use_aligned = first is not None and not l["check"] and abs(first - l["hand"]) <= LINE_SHIFT_MAX
        start = first if use_aligned else l["hand"]
        end = timed[-1]["end"] if timed else None
        tag = f"[{l['voice']}]" if l["voice"] else ""
        m, s_ = divmod(start, 60)
        lrc_out.append(f"[{int(m):02d}:{s_:05.2f}] " + (tag + " " if tag else "") + l["text"])
        js_lines.append({
            "i": i, "tag": tag, "text": l["text"], "start": round(start, 2), "end": end,
            "hand_start": round(l["hand"], 2), "dev": round(start - l["hand"], 2),
            "confidence": l["score"],
            "source": "aligned" if use_aligned else "hand", "agree": l["agree"],
            "check": l["check"], "max_gap": l["max_gap"],
            "global_start": l["global_start"],
            "words": [{"w": w["text"], "start": w["start"], "end": w["end"], "score": w["score"],
                       "agree": w.get("agree", False), "from": w.get("from"), "context_start": w.get("context_start"),
                       "global_start": w.get("global_start")}
                      for w in l["words"]],
        })
    line_scores = [l["score"] for l in lines]
    (out_dir / f"{name}.aligned.lrc").write_text("\n".join(lrc_out) + "\n", encoding="utf-8")
    (out_dir / f"{name}.words.json").write_text(json.dumps({
        "title": title or name, "audio": audio_name, "source_lrc": Path(lrc).name,
        "method": "htdemucs vocal stem -> torchaudio MMS_FA forced alignment, each line inside its "
                  "hand-stamped window, checked by a pass with each line's neighbours in a wider window",
        "generated": date.today().isoformat(), "units": "seconds",
        "notes": "start/end: aligned onset/offset (line start falls back to hand_start when its words "
                 "do not agree between the two passes). hand_start: the hand-stamped LRC time. "
                 "dev = start - hand_start. score/confidence: mean CTC posterior (0..1); sung vowels "
                 "score low even when placed right. agree: the anchored and the context pass put "
                 "the word start within 0.35 s; rating comes from the share of agreeing words.",
        "confidence": round(float(np.mean(line_scores)), 3) if line_scores else 0.0,
        "rating": summary["confidence"], "summary": summary,
        "lines": js_lines}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vocals")
    ap.add_argument("lrc")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--name")
    ap.add_argument("--title")
    ap.add_argument("--audio-name", help="original audio file name, recorded in the JSON")
    a = ap.parse_args()
    name = a.name or Path(a.lrc).stem
    s = run(a.vocals, a.lrc, a.out, name, Aligner(), a.title, a.audio_name)
    print(json.dumps({name: s}))


if __name__ == "__main__":
    main()
