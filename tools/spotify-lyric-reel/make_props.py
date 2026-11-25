#!/usr/bin/env python3
"""Prepare a Spotify-style lyric reel: copies the song and cover into public/, times every lyric word, picks colours.

Lyrics file: one lyric line per line. Optional explicit timing per line: "12.4|15.0|text".
Lines without times are aligned automatically to Whisper word timings (character-level fuzzy match), so the
user's correct spelling is shown while Whisper supplies the timing.

Usage:
  python3 make_props.py --audio song.mp3 --lyrics lines.txt --title "Song" --artist "Artist" [--cover cover.jpg]
                        [--words song.words.json] [--lang hi] [--start 0 --end 30] [--accent "#1ed760"]
Then render:
  npx remotion render src/index.ts SpotifyLyric out/reel.mp4 --props=public/props.json
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PUB = os.path.join(HERE, "public")


def norm(s):
    s = s.lower()
    s = re.sub(r"[़ँंः]", "", s)             # nukta, chandrabindu, anusvara, visarga
    s = re.sub(r"[^\wऀ-ॿ]", "", s)
    return s


def whisper_words(audio, lang, prompt):
    from faster_whisper import WhisperModel
    mp = os.path.join(ROOT, "tools", "models", "whisper-small-int8")
    m = WhisperModel(mp if os.path.isdir(mp) else "small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(audio, language=lang, word_timestamps=True, vad_filter=False, initial_prompt=prompt[:400] or None)
    return [{"word": w.word.strip(), "start": w.start, "end": w.end} for s in segs for w in (s.words or [])]


def load_words(path):
    d = json.load(open(path))
    if isinstance(d, dict) and "segments" in d:
        return [{"word": w["word"].strip(), "start": w["start"], "end": w["end"]} for s in d["segments"] for w in s.get("words", [])]
    if isinstance(d, dict) and "words" in d:
        return d["words"]
    return d


def align(lines, words):
    """Map each lyric word to a time using a character-level match against Whisper's words."""
    wchars, wtime = [], []
    for w in words:
        n = norm(w["word"])
        for k, c in enumerate(n):
            wchars.append(c)
            frac = k / max(1, len(n))
            wtime.append(w["start"] + (w["end"] - w["start"]) * frac)
    lchars, owner = [], []
    toks = []
    for li, line in enumerate(lines):
        for wi, tok in enumerate(line["text"].split()):
            toks.append((li, wi, tok))
            for c in norm(tok):
                lchars.append(c)
                owner.append(len(toks) - 1)
    sm = difflib.SequenceMatcher(None, lchars, wchars, autojunk=False)
    l2w = [None] * len(lchars)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            l2w[a + k] = b + k
    # first matched char per token gives its start time; interpolate the gaps
    tok_t = [None] * len(toks)
    for ci, ti in enumerate(owner):
        if tok_t[ti] is None and l2w[ci] is not None:
            tok_t[ti] = wtime[l2w[ci]]
    known = [i for i, v in enumerate(tok_t) if v is not None]
    if not known:
        return None
    for i in range(len(toks)):
        if tok_t[i] is None:
            prev = max([k for k in known if k < i], default=None)
            nxt = min([k for k in known if k > i], default=None)
            if prev is None:
                tok_t[i] = tok_t[nxt] - 0.3 * (nxt - i)
            elif nxt is None:
                tok_t[i] = tok_t[prev] + 0.3 * (i - prev)
            else:
                tok_t[i] = tok_t[prev] + (tok_t[nxt] - tok_t[prev]) * (i - prev) / (nxt - prev)
    for i in range(1, len(tok_t)):            # keep it monotonic
        tok_t[i] = max(tok_t[i], tok_t[i - 1] + 0.05)
    return toks, tok_t


def dominant(cover):
    from PIL import Image
    im = Image.open(cover).convert("RGB").resize((64, 64))
    q = im.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:18]
    counts = sorted(q.getcolors(), reverse=True)
    cols = [tuple(pal[i * 3:i * 3 + 3]) for _, i in counts]

    def sat(c):
        mx, mn = max(c), min(c)
        return (mx - mn) / (mx + 1)
    base = max(cols[:3], key=lambda c: sat(c) * 0.6 + 0.4)
    bg = tuple(int(v * 0.55) for v in base)                 # darker, so white lyrics pop
    import colorsys
    h, s_, v = colorsys.rgb_to_hsv(*[x / 255 for x in max(cols, key=sat)])
    accent = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, max(s_, 0.55), 1.0))   # bright, saturated glow
    hb, sb, vb = colorsys.rgb_to_hsv(*[x / 255 for x in base])
    bg = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(hb, max(sb, 0.45), min(vb, 0.42)))
    return "#%02x%02x%02x" % bg, "#%02x%02x%02x" % accent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--lyrics", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--artist", default="")
    ap.add_argument("--cover")
    ap.add_argument("--words", help="existing Whisper .words.json (skips transcription)")
    ap.add_argument("--lang", default="hi")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--accent")
    ap.add_argument("--bg")
    a = ap.parse_args()
    os.makedirs(PUB, exist_ok=True)

    # audio (optionally trimmed)
    dst = os.path.join(PUB, "audio.mp3")
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(a.start), "-i", a.audio]
    if a.end:
        cmd += ["-t", str(a.end - a.start)]
    subprocess.run(cmd + ["-c:a", "libmp3lame", "-b:a", "192k", dst], check=True)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dst]).decode())

    raw = [l.strip() for l in open(a.lyrics, encoding="utf-8") if l.strip()]
    lines = []
    for l in raw:
        m = re.match(r"^\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(.+)$", l)
        lines.append({"start": float(m.group(1)) - a.start, "end": float(m.group(2)) - a.start, "text": m.group(3).strip()} if m else
                     {"start": None, "end": None, "text": l})
    words = load_words(a.words) if a.words else whisper_words(dst, a.lang, " ".join(x["text"] for x in lines))
    if a.words and a.start:
        words = [dict(w, start=w["start"] - a.start, end=w["end"] - a.start) for w in words]
    res = align(lines, words)
    out_lines = []
    if res:
        toks, tt = res
        for li, line in enumerate(lines):
            idx = [i for i, tk in enumerate(toks) if tk[0] == li]
            ws = []
            for n, i in enumerate(idx):
                nxt = tt[idx[n + 1]] if n + 1 < len(idx) else (tt[i] + 0.45)
                ws.append({"t": round(tt[i], 2), "e": round(min(nxt, tt[i] + 0.8), 2), "w": toks[i][2]})
            st = line["start"] if line["start"] is not None else max(0.0, ws[0]["t"] - 0.1)
            en = line["end"] if line["end"] is not None else None
            out_lines.append({"start": round(st, 2), "end": en, "text": line["text"], "words": ws})
        for i, l in enumerate(out_lines):     # a line lasts until the next one starts (or its last word ends + 1 s)
            if l["end"] is None:
                nxt = out_lines[i + 1]["start"] if i + 1 < len(out_lines) else dur
                l["end"] = round(min(nxt, l["words"][-1]["e"] + 1.2), 2)
            if lines[i]["start"] is not None:  # explicit times: spread words evenly inside the line
                n = len(l["words"])
                span = (l["end"] - l["start"]) * 0.9
                for k, w in enumerate(l["words"]):
                    w["t"] = round(l["start"] + span * k / n, 2)
                    w["e"] = round(l["start"] + span * (k + 1) / n, 2)
    else:
        sys.exit("could not align the lyrics to the audio; give explicit times as start|end|text")

    bg, accent = "#1f2a44", "#7ad7ff"
    cover_name = None
    if a.cover:
        ext = os.path.splitext(a.cover)[1].lower() or ".jpg"
        cover_name = "cover" + ext
        shutil.copy(a.cover, os.path.join(PUB, cover_name))
        bg, accent = dominant(a.cover)
    props = {"audio": "audio.mp3", "cover": cover_name, "title": a.title, "artist": a.artist, "bg": a.bg or bg,
             "accent": a.accent or accent, "durationSec": round(dur, 2), "lines": out_lines}
    json.dump(props, open(os.path.join(PUB, "props.json"), "w"), ensure_ascii=False, indent=1)
    print(f"public/props.json: {len(out_lines)} lines, {dur:.1f}s, bg {props['bg']}, accent {props['accent']}")
    for l in out_lines:
        print(f"  {l['start']:6.2f}-{l['end']:6.2f}  {l['text']}")


if __name__ == "__main__":
    main()
