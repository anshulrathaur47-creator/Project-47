#!/usr/bin/env python3
"""Broadcast-style subtitles and chapters from word timestamps. Used by deliver.py and qc.py.

Rules (Netflix/BBC timed-text practice): <= 42 chars per line, <= 2 lines, <= 20 chars/s
(17 for kids), 0.833 s (5/6 s) minimum and 7 s maximum on screen, 2-frame gap between cues,
break lines after punctuation / before conjunctions and prepositions, never between an
article and its noun, a first and last name, or a pronoun and its verb.

    from captions import build_cues, write_srt, write_vtt, write_ttml, validate_cues
    cues = build_cues(words, cps=20)          # words: [{w,start,end}]
    write_srt(cues, "out.srt"); validate_cues(parse_srt("out.srt"))

Run this file directly for a self-check.
"""
import re, unicodedata
import xml.etree.ElementTree as ET
from vs_common import norm, SENT_END
from xml.sax.saxutils import escape

MAX_CHARS, MAX_LINES, CPS_ADULT, CPS_KIDS = 42, 2, 20.0, 17.0
MIN_DUR, MAX_DUR, GAP_FRAMES = 5 / 6, 7.0, 2

ARTICLES = {"a", "an", "the", "my", "your", "his", "her", "its", "our", "their", "every", "each"}
CONJ = {"and", "but", "or", "nor", "so", "yet", "because", "although", "though", "while", "if",
        "when", "which", "who", "whereas", "unless", "until", "since"}
PREP = {"in", "on", "at", "to", "for", "with", "from", "of", "by", "about", "into", "over",
        "after", "before", "under", "between", "through", "during", "without", "than", "across"}
AUX = {"is", "are", "was", "were", "be", "been", "am", "will", "would", "can", "could", "should",
       "shall", "may", "might", "must", "do", "does", "did", "have", "has", "had", "not"}
PRONOUNS = {"i", "you", "he", "she", "it", "we", "they"}
STOP = ARTICLES | CONJ | PREP | AUX | PRONOUNS | {"this", "that", "some", "any", "no",
    "me", "him", "us", "them", "what", "how", "why", "where", "there", "here", "then", "just",
    "really", "very", "also", "too", "like", "get", "got", "going", "gonna", "want", "know", "think",
    "thing", "things", "one", "all", "more", "most", "much", "many", "now", "out", "up", "down",
    "first", "second", "third", "let", "lets", "okay", "ok", "yeah", "right", "well", "follow",
    "dont", "im", "youre", "its", "thats", "about", "make", "made", "huge", "big", "these", "those"}
_GLUE = tuple(",.!?;:%)]}'’…।॥")
_NUMWORDS = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
             "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12"}


def bare(w):
    return norm(w)   # keeps Devanagari vowel signs (a [^\w] strip turned "तो" into "त")


def glen(s):
    """On-screen length in grapheme clusters: a base letter plus its combining marks counts once, so Devanagari
    matras/virama/nukta add nothing ("राशि है फकीरा" = 8, not 13 code points). Latin text: same as len().
    ponytail: legacy clusters (stdlib only); a virama conjunct like "क्ष" counts 2, close to its width anyway."""
    return sum(1 for ch in s if not unicodedata.category(ch).startswith("M") and ch not in "\u200c\u200d")


# ---------------------------------------------------------------- tokens and line breaks
def merge_tokens(words):
    """Whisper splits '$10,000' into '$10' ',000.'; glue punctuation-led tokens to the previous word."""
    out = []
    for w in words:
        t = str(w.get("w", "")).strip()
        if not t:
            continue
        if out and (t.startswith(_GLUE) or out[-1]["w"].endswith(("$", "#", "(", "-"))):
            prev = out[-1]
            out[-1] = {**prev, "w": prev["w"] + t, "end": max(prev["end"], float(w["end"]))}
            if "p" in w or "p" in prev:  # keep the weakest confidence of the glued pieces
                out[-1]["p"] = min(float(prev.get("p", 1)), float(w.get("p", 1)))
        else:
            out.append({**{k: v for k, v in w.items() if k not in ("w", "start", "end")},
                        "w": t, "start": float(w["start"]), "end": float(w["end"])})
    return out


def _break_cost(left, right, l1, l2):
    lb, rb = bare(left), bare(right)
    cost = abs(l1 - l2) * 0.6 + max(0, l1 - l2) * 0.4          # balanced, bottom-heavy pyramid
    if min(l1, l2) < 8:
        cost += 15                                                # no orphan stubs like "so,"
    if left.endswith((",", ".", ";", ":", "!", "?", "…", "।", "॥")):
        cost -= 25
    if rb in CONJ or rb in PREP:
        cost -= 10
    if lb in ARTICLES:
        cost += 60                                                # keep article + noun
    if lb in PREP or lb in CONJ:
        cost += 20                                                # don't end a line on 'and' / 'of'
    if lb in PRONOUNS and rb in AUX:
        cost += 35                                                # subject pronoun + verb
    if rb in {"not", "n't"} or (lb in AUX and rb not in ARTICLES and not rb[:1].isdigit()):
        cost += 30                                                # verb + auxiliary / negation
    if left[:1].isupper() and right[:1].isupper() and not SENT_END.search(left):
        cost += 45                                                # first + last name
    return cost


def layout(tokens, max_chars=MAX_CHARS, max_lines=MAX_LINES):
    """Best line split for a list of word strings, or None if it cannot fit."""
    text = " ".join(tokens)
    if glen(text) <= max_chars:
        return [text]
    if max_lines < 2:
        return None
    best = None
    for i in range(1, len(tokens)):
        a, b = " ".join(tokens[:i]), " ".join(tokens[i:])
        if glen(a) > max_chars or glen(b) > max_chars:
            continue
        c = _break_cost(tokens[i - 1], tokens[i], glen(a), glen(b))
        if best is None or c < best[0]:
            best = (c, [a, b])
    return best[1] if best else None


# ---------------------------------------------------------------- cue building
def build_cues(words, cps=CPS_ADULT, max_chars=MAX_CHARS, max_lines=MAX_LINES, fps=30.0,
               min_dur=MIN_DUR, max_dur=MAX_DUR, gap_frames=GAP_FRAMES, pause_split=0.7):
    """Group words into subtitle cues: [{start, end, lines:[...]}]."""
    toks = merge_tokens(words)
    groups, cur = [], []

    def flush(upto=None):
        nonlocal cur
        upto = len(cur) if upto is None else upto
        if upto:
            groups.append(cur[:upto])
        cur = cur[upto:]

    for t in toks:
        if cur:
            fits = layout([x["w"] for x in cur + [t]], max_chars, max_lines) is not None
            if not fits:
                # prefer the latest phrase boundary (comma / before a conjunction) in the cue
                cut = None
                for i in range(len(cur) - 1, 0, -1):
                    if cur[i - 1]["w"].endswith((",", ";", ":")) or bare(cur[i]["w"]) in CONJ:
                        cut = i
                        break
                flush(cut)
            elif t["end"] - cur[0]["start"] > max_dur or t["start"] - cur[-1]["end"] > pause_split:
                flush()
            elif SENT_END.search(cur[-1]["w"]) and glen(" ".join(x["w"] for x in cur)) >= 6:
                flush()
        cur.append(t)
    flush()

    frame = 1.0 / fps
    snap = lambda x: round(round(x / frame) * frame, 3)
    cues = []
    for g in groups:
        lines = layout([x["w"] for x in g], max_chars, max_lines) or [" ".join(x["w"] for x in g)]
        cues.append({"start": g[0]["start"], "end": g[-1]["end"], "lines": lines})
    for i, c in enumerate(cues):
        chars = glen(" ".join(c["lines"]))
        end = max(c["end"], c["start"] + max(min_dur, chars / cps))
        end = min(end, c["start"] + max_dur)
        if i + 1 < len(cues):
            end = min(end, cues[i + 1]["start"] - gap_frames * frame)
        c["start"], c["end"] = snap(c["start"]), snap(max(end, c["start"] + frame))
    return cues


def validate_cues(cues, cps=CPS_ADULT, max_chars=MAX_CHARS, max_lines=MAX_LINES, fps=30.0,
                  min_dur=MIN_DUR, max_dur=MAX_DUR, gap_frames=GAP_FRAMES):
    """Return a list of rule violations: {cue, rule, value, limit}."""
    bad, eps = [], 1e-3
    for i, c in enumerate(cues):
        d = c["end"] - c["start"]
        text = " ".join(c["lines"])
        chk = [("lines", len(c["lines"]), max_lines, len(c["lines"]) > max_lines),
               ("chars_per_line", max(glen(l) for l in c["lines"]), max_chars, max(glen(l) for l in c["lines"]) > max_chars),
               ("min_duration", round(d, 3), round(min_dur, 3), d < min_dur - eps),
               ("max_duration", round(d, 3), max_dur, d > max_dur + eps),
               ("cps", round(glen(text) / max(d, 1e-6), 1), cps, glen(text) / max(d, 1e-6) > cps + 0.05)]
        if i + 1 < len(cues):
            g = cues[i + 1]["start"] - c["end"]
            chk.append(("gap_frames", round(g * fps, 2), gap_frames, g < gap_frames / fps - eps))
        bad += [{"cue": i + 1, "rule": r, "value": v, "limit": lim, "text": text} for r, v, lim, fail in chk if fail]
    return bad


# ---------------------------------------------------------------- writers / parsers
def _ts(t, sep):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def write_srt(cues, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{_ts(c['start'], ',')} --> {_ts(c['end'], ',')}\n" + "\n".join(c["lines"]) + "\n\n")


def write_vtt(cues, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("WEBVTT\n\n")
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{_ts(c['start'], '.')} --> {_ts(c['end'], '.')}\n" + "\n".join(c["lines"]) + "\n\n")


def write_ttml(cues, path, lang="en"):
    """Simple IMSC1 text profile TTML."""
    ps = "\n".join(f'      <p begin="{_ts(c["start"], ".")}" end="{_ts(c["end"], ".")}">'
                   + "<br/>".join(escape(l) for l in c["lines"]) + "</p>" for c in cues)
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<tt xmlns="http://www.w3.org/ns/ttml" xmlns:tts="http://www.w3.org/ns/ttml#styling"
    xmlns:ttp="http://www.w3.org/ns/ttml#parameter" ttp:profile="http://www.w3.org/ns/ttml/profile/imsc1/text"
    ttp:timeBase="media" xml:lang="{lang}">
  <head>
    <styling>
      <style xml:id="s1" tts:color="white" tts:backgroundColor="#000000C0" tts:fontFamily="proportionalSansSerif"
             tts:fontSize="100%" tts:textAlign="center"/>
    </styling>
    <layout>
      <region xml:id="bottom" tts:origin="10% 10%" tts:extent="80% 80%" tts:displayAlign="after"/>
    </layout>
  </head>
  <body region="bottom" style="s1">
    <div>
{ps}
    </div>
  </body>
</tt>
'''
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(xml)


def _secs(ts):
    h, m, s = ts.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_srt(path):
    """Parses SRT and WebVTT."""
    txt = open(path, encoding="utf-8").read().replace("\r", "")
    cues = []
    for block in re.split(r"\n\s*\n", txt):
        lines = [l for l in block.strip().split("\n") if l.strip()]
        for k, l in enumerate(lines):
            m = re.match(r"(\d+:\d\d:\d\d[,.]\d{3})\s+-->\s+(\d+:\d\d:\d\d[,.]\d{3})", l)
            if m:
                cues.append({"start": _secs(m[1]), "end": _secs(m[2]), "lines": lines[k + 1:]})
                break
    return cues


parse_vtt = parse_srt


def parse_ttml(path):
    ns = {"tt": "http://www.w3.org/ns/ttml"}
    root = ET.parse(path).getroot()
    cues = []
    for p in root.iter("{http://www.w3.org/ns/ttml}p"):
        parts, cur = [], p.text or ""
        for ch in p:
            if ch.tag.endswith("br"):
                parts.append(cur); cur = ch.tail or ""
            else:
                cur += "".join(ch.itertext()) + (ch.tail or "")
        parts.append(cur)
        cues.append({"start": _secs(p.get("begin")), "end": _secs(p.get("end")), "lines": [x.strip() for x in parts]})
    return cues


def write_ass(cues, path, w, h, font="Arial", size=None, margin_v=None, margin_lr=None):
    """ASS file sized to the output frame (libass burn-in). Positions are output pixels."""
    size = size or int(h * 0.05)
    margin_v = int(h * 0.06) if margin_v is None else int(margin_v)
    ml, mr = margin_lr or (int(w * 0.05), int(w * 0.05))
    t = lambda x: f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"
    ev = "\n".join(f"Dialogue: 0,{t(c['start'])},{t(c['end'])},Default,,0,0,0,," + "\\N".join(c["lines"]) for c in cues)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,{max(2, size // 14)},{max(1, size // 28)},2,{ml},{mr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{ev}
""")


# ---------------------------------------------------------------- sentences, keywords, chapters
def sentences(words):
    toks, out, cur = merge_tokens(words), [], []
    for t in toks:
        cur.append(t)
        if SENT_END.search(t["w"]):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return [{"start": s[0]["start"], "end": s[-1]["end"], "text": " ".join(x["w"] for x in s).strip(), "words": s} for s in out]


def keywords(text_or_words, top=8):
    words = text_or_words if isinstance(text_or_words, list) else text_or_words.split()
    freq = {}
    for w in words:
        b = bare(w if isinstance(w, str) else w["w"]).replace("'", "")
        if len(b) >= 4 and b not in STOP and not b.isdigit():
            freq[b] = freq.get(b, 0) + 1
    return [k for k, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))][:top]


def numberize(text):
    return " ".join(_NUMWORDS.get(bare(w), w) if bare(w) in _NUMWORDS and w.isalpha() else w for w in text.split())


def chapter_title(text, n=6):
    ws = [w.strip(".,!?;:") for w in numberize(text).split()]
    while ws and bare(ws[0]) in {"so", "and", "but", "okay", "ok", "now", "well", "here", "are", "is", "this", "first", "second", "third", "next", "finally"}:
        ws = ws[1:]
    t = " ".join(ws[:n]) or text[:40]
    return t[:1].upper() + t[1:]


def fmt_chapter_time(t, long=False):
    t = int(t)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if long else f"{m:02d}:{s:02d}"


def auto_chapters(words, duration, min_len=10.0, max_chapters=None):
    """Chapter starts at sentence boundaries with the biggest pause + keyword shift. [] if the video
    is too short for YouTube rules (>= 3 chapters, each >= 10 s)."""
    sents = sentences(words)
    if duration < 3 * min_len or len(sents) < 3:
        return []
    k = max_chapters or max(3, min(12, int(duration // 90) + 2))
    cand = []
    for i in range(1, len(sents)):
        before = set(keywords(" ".join(s["text"] for s in sents[max(0, i - 3):i]), 20))
        after = set(keywords(" ".join(s["text"] for s in sents[i:i + 3]), 20))
        jac = len(before & after) / max(1, len(before | after))
        pause = sents[i]["start"] - sents[i - 1]["end"]
        cand.append((min(pause, 3.0) + (1 - jac), i))
    chosen = [0.0]
    for _, i in sorted(cand, reverse=True):
        t = sents[i]["start"]
        if all(abs(t - c) >= min_len for c in chosen) and duration - t >= min_len and len(chosen) < k:
            chosen.append(t)
    chosen.sort()
    if len(chosen) < 3:
        return []
    out = []
    for t in chosen:
        s = next(x for x in sents if x["start"] >= t - 1e-6)
        out.append({"start": 0.0 if t == 0 else round(t, 3), "title": chapter_title(s["text"])})
    return out


def parse_chapters(spec):
    """'0:00 Intro; 1:20 Setup' -> [{start, title}]"""
    out = []
    for part in [p.strip() for p in re.split(r"[;\n]", spec or "") if p.strip()]:
        ts, _, title = part.partition(" ")
        secs = 0.0
        for x in ts.split(":"):
            secs = secs * 60 + float(x)
        out.append({"start": secs, "title": title.strip() or f"Chapter {len(out) + 1}"})
    return sorted(out, key=lambda c: c["start"])


def youtube_chapters(chapters, duration):
    """(text, problems). YouTube: first at 00:00, >= 3 chapters, each >= 10 s, ascending."""
    probs = []
    if not chapters:
        return "", ["no chapters"]
    if chapters[0]["start"] > 0:
        probs.append("first chapter must start at 00:00")
    if len(chapters) < 3:
        probs.append("YouTube needs at least 3 chapters")
    ends = [c["start"] for c in chapters[1:]] + [duration]
    for c, e in zip(chapters, ends):
        if e - c["start"] < 10:
            probs.append(f"chapter '{c['title']}' is {e - c['start']:.1f} s (< 10 s)")
    lg = duration >= 3600
    return "\n".join(f"{fmt_chapter_time(c['start'], lg)} {c['title']}" for c in chapters), probs


def write_ffmetadata(chapters, duration, path, title=None):
    esc = lambda s: re.sub(r"([=;#\\\n])", r"\\\1", s)
    lines = [";FFMETADATA1"] + ([f"title={esc(title)}"] if title else [])
    ends = [c["start"] for c in chapters[1:]] + [duration]
    for c, e in zip(chapters, ends):
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(c['start'] * 1000)}", f"END={int(e * 1000)}", f"title={esc(c['title'])}"]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":   # self-check
    import os, tempfile
    assert layout(["Second,", "I", "hired", "too", "fast,", "and", "that", "was", "a", "huge", "mistake."], 42) == \
        ["Second, I hired too fast,", "and that was a huge mistake."]
    assert merge_tokens([{"w": "$10", "start": 0, "end": .5}, {"w": ",000.", "start": .5, "end": .9}])[0]["w"] == "$10,000."
    txt = ("Today we talk about pricing. Pricing is hard because customers compare everything. "
           "Next we cover hiring and the team. Hiring slow beats hiring fast for a small team. "
           "Finally marketing and growth loops matter. Growth comes from referrals and content.")
    ws, t = [], 0.0
    for w in txt.split():
        ws.append({"w": w, "start": t, "end": t + 0.35}); t += 0.45 + (1.2 if w.endswith(".") else 0)
    cues = build_cues(ws)
    assert not validate_cues(cues), validate_cues(cues)
    d = tempfile.mkdtemp()
    for wr, pa, ext in ((write_srt, parse_srt, "srt"), (write_vtt, parse_vtt, "vtt"), (write_ttml, parse_ttml, "ttml")):
        p = os.path.join(d, "c." + ext); wr(cues, p); back = pa(p)
        assert [c["lines"] for c in back] == [c["lines"] for c in cues] and abs(back[-1]["end"] - cues[-1]["end"]) < 2e-3, ext
    long_ws, off = [], 0.0
    for _ in range(3):                                   # ~75 s sample for chapter detection
        long_ws += [{"w": w["w"], "start": w["start"] + off, "end": w["end"] + off} for w in ws]; off += t + 2
    ch = auto_chapters(long_ws, off)
    assert len(ch) >= 3 and ch[0]["start"] == 0 and not youtube_chapters(ch, off)[1], ch
    assert youtube_chapters(parse_chapters("0:00 A; 0:12 B; 0:30 C"), 45)[1] == []
    assert youtube_chapters(parse_chapters("0:00 A; 0:05 B"), 45)[1]
    # Devanagari: vowel signs survive bare(), the danda ends sentences and cues, lengths are in graphemes
    assert bare("तो,") == "तो" and bare("है।") == "है" and glen("राशि है फकीरा") == 8 and glen("Hello, world") == 12
    hi = [{"w": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate("मैंने यह गलती की। आप मत करना। ठीक है".split())]
    assert [s["text"] for s in sentences(hi)] == ["मैंने यह गलती की।", "आप मत करना।", "ठीक है"], sentences(hi)
    assert all(not c["lines"][-1].endswith("आप") for c in build_cues(hi)), build_cues(hi)
    assert merge_tokens([{"w": "की", "start": 0, "end": .4}, {"w": "।", "start": .4, "end": .5}])[0]["w"] == "की।"
    line = "हर बात तीरा बरगी, राशि है फकीरा बरगी, एक ए छोरी"   # 49 code points, 34 graphemes
    assert len(line) > MAX_CHARS and layout(line.split()) == [line]
    print("captions.py self-check OK:", len(cues), "cues;", len(ch), "auto chapters on a", round(off), "s sample")
