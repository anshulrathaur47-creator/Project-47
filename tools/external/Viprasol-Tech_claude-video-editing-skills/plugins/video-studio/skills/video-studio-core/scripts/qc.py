#!/usr/bin/env python3
"""Automated QC of a finished video (+ its plan) against a platform spec. Writes JSON + Markdown.

usage: qc.py VIDEO [--plan PLAN.json] [--platform reels|youtube|...|none] [--out-dir DIR] [--kids] [--strict]

Checks: duration/resolution/fps vs plan, codec/pix_fmt, faststart, keyframe interval, audio present,
integrated LUFS / true peak / LRA vs platform target, silences > 2 s, black frames, flash frames,
photosensitivity (>= 3 flashes in any 1 s), illegal levels (signalstats BRNG), A/V sync heuristic,
caption rules (broadcast cues from words; creator captions; overlay min 0.6 s; 9:16 safe zone
10-85 % height and clear of the right 12 %; <= 2 overlays at once on vertical), size/length limits.
Perceptual: caption script vs the expected language (--lang / plan.language / plan.script / plan.profile),
glyph coverage of the skin font stacks (tofu), text boxes over the face track > 0.5 s, black/blank last 0.3 s.
Exit code: 0, or 1 with --strict when any check FAILs.   Self-check: qc.py --self-test
"""
import argparse, bisect, functools, glob, html, json, os, re, shutil, struct, subprocess, sys, tempfile, unicodedata
import urllib.request
from collections import Counter, defaultdict
from vs_common import load_json, save_json, log
import captions as C
from deliver import PRESETS, stream_info

TEXT_TYPES = {"text", "headline", "chip", "tile", "sticker", "card", "counter", "bars", "lowerthird", "titlecard",
              "captions", "ticker", "compare", "clip", "image", "stars"}
FLASH_DELTA = 0.10        # 10 % of the luma range between frames = a transition
GLITCH_DELTA = 0.20


def mp4_atoms(path):
    """Top-level MP4 boxes in file order, e.g. ['ftyp', 'moov', 'mdat'] (faststart = moov before mdat)."""
    out = []
    with open(path, "rb") as f:
        size_total = os.path.getsize(path); pos = 0
        while pos + 8 <= size_total:
            f.seek(pos)
            size, typ = struct.unpack(">I4s", f.read(8))
            if size == 1:
                size = struct.unpack(">Q", f.read(8))[0]
            elif size == 0:
                size = size_total - pos
            out.append(typ.decode("latin-1"))
            if size < 8:
                break
            pos += size
    return out


def keyframe_interval(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time,flags",
                          "-of", "csv=p=0", path], stdout=subprocess.PIPE, text=True).stdout
    ts = sorted(float(l.split(",")[0]) for l in out.splitlines() if "K" in l.split(",")[-1] and l.split(",")[0] not in ("", "N/A"))
    gaps = [round(b - a, 3) for a, b in zip(ts, ts[1:])]
    return {"keyframes": len(ts), "max_gap_s": max(gaps) if gaps else None, "min_gap_s": min(gaps) if gaps else None}


def analyse(path, has_audio):
    """One decode pass: blackdetect + signalstats (per-frame YAVG/BRNG) + silencedetect + ebur128."""
    d = tempfile.mkdtemp()
    g = "[0:v]blackdetect=d=0.1:pix_th=0.10,signalstats=stat=brng,metadata=mode=print:file=stats.txt[vo]"
    maps = ["-map", "[vo]"]
    if has_audio:
        g += ";[0:a]silencedetect=n=-45dB:d=2,ebur128=peak=true:framelog=quiet[ao]"
        maps += ["-map", "[ao]"]
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", os.path.abspath(path), "-filter_complex", g] + maps + ["-f", "null", "-"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=d, encoding="utf-8", errors="replace")
    err = p.stderr
    yavg, brng, frames = [], [], []          # frames: [pts_time, YLOW, YHIGH] (10th / 90th percentile luma)
    if os.path.exists(os.path.join(d, "stats.txt")):
        for line in open(os.path.join(d, "stats.txt"), encoding="utf-8"):
            if line.startswith("frame:"):
                m = re.search(r"pts_time:(-?[\d.]+)", line)
                frames.append([float(m[1]) if m else None, None, None])
            elif "signalstats.YAVG=" in line:
                yavg.append(float(line.split("=")[1]))
            elif "signalstats.BRNG=" in line:
                brng.append(float(line.split("=")[1]))
            elif frames and "signalstats.YLOW=" in line:
                frames[-1][1] = float(line.split("=")[1])
            elif frames and "signalstats.YHIGH=" in line:
                frames[-1][2] = float(line.split("=")[1])
    shutil.rmtree(d, ignore_errors=True)
    blacks = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)]
    sil = [(float(a), float(b)) for a, b in re.findall(r"silence_start: ([\d.]+)[\s\S]*?silence_end: ([\d.]+)", err)]
    loud = {}
    summ = err[err.rfind("Summary:"):] if "Summary:" in err else ""
    for k, pat in (("I", r"I:\s+(-?[\d.]+|-inf) LUFS"), ("LRA", r"LRA:\s+(-?[\d.]+) LU"), ("TP", r"Peak:\s+(-?[\d.]+|-inf) dBFS")):
        m = re.search(pat, summ)
        if m:
            loud[k] = float(m[1].replace("-inf", "-99"))
    return {"yavg": yavg, "brng": brng, "frames": frames, "black": blacks, "silence": sil, "loudness": loud, "ok": p.returncode == 0}


def flash_analysis(yavg, fps, maxval=255.0):
    """Flash frames (single-frame luma spikes) and Harding-style flash rate (pairs of opposing
    >= 10 % luma transitions). ponytail: frame-average luma only; misses small-area / red flashes."""
    y = [v / maxval for v in yavg]
    glitches = [i for i in range(1, len(y) - 1)
                if abs(y[i] - y[i - 1]) > GLITCH_DELTA and abs(y[i] - y[i + 1]) > GLITCH_DELTA and (y[i] - y[i - 1]) * (y[i + 1] - y[i]) < 0]
    trans, last_sign = [], 0
    for i in range(1, len(y)):
        dlt = y[i] - y[i - 1]
        if abs(dlt) >= FLASH_DELTA:
            s = 1 if dlt > 0 else -1
            if s != last_sign:
                trans.append(i); last_sign = s
    win = int(round(fps))
    worst, at = 0, None
    for k, i in enumerate(trans):
        n = sum(1 for j in trans[k:] if j - i < win) // 2     # a flash = an opposing pair
        if n > worst:
            worst, at = n, i / fps
    return {"flash_frames": [round(i / fps, 3) for i in glitches], "max_flashes_per_s": worst, "at": at}


# ------------------------------------------------------------------ plan / caption checks
def creator_caption_chunks(el, words):
    """Mirror runtime/engine.js C.captions grouping exactly (maxWords/maxChars/breakGap/punctuation, hold,
    cpsMax splitting) so QC judges what is actually on screen."""
    import re
    ws = [w for w in words if str(w.get("w", "")).strip()]
    max_words, max_chars = int(el.get("maxWords") or 3), int(el.get("maxChars") or 22)
    gap, hold = float(el.get("breakGap") or 0.45), float(el.get("hold", 0.5))
    punct = re.compile(r"[.!?]$" if el.get("breakOnPunct") == "sentence" else r"[.!?,;:]$")
    groups, cur = [], []
    for i, w in enumerate(ws):
        chars = sum(len(b["w"]) + 1 for b in cur) + len(w["w"])
        if cur and (len(cur) >= max_words or chars > max_chars or (i and w["start"] - ws[i - 1]["end"] > gap)):
            groups.append(cur); cur = []
        cur.append(w)
        if el.get("breakOnPunct", True) is not False and punct.search(w["w"].strip()):
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)

    def timed(gs):
        return [(g, g[0]["start"], min(g[-1]["end"] + hold, gs[k + 1][0]["start"] if k + 1 < len(gs) else 1e9))
                for k, g in enumerate(gs)]
    cps_max, min_dur = float(el.get("cpsMax", 20) or 0), float(el.get("minDur", 0.3))
    for _ in range(4 if cps_max > 0 else 0):
        out, changed = [], False
        for g, s, e in timed(groups):
            chars = sum(len(w["w"].strip()) for w in g) + len(g) - 1
            m = (len(g) + 1) // 2
            if len(g) > 1 and chars / max(0.05, e - s) > cps_max and g[m]["start"] - s >= min_dur and e - g[m]["start"] >= min_dur:
                out += [g[:m], g[m:]]; changed = True
            else:
                out.append(g)
        groups = out
        if not changed:
            break
    res = []
    for g, s, e in timed(groups):
        text = " ".join(w["w"].strip() for w in g)
        res.append({"start": s, "dur": max(1e-3, e - s), "text": text.upper() if el.get("uppercase") else text})
    return res


def overlay_checks(plan, W, H, dur):
    res, els = [], [e for e in plan.get("elements", []) if e.get("type") in TEXT_TYPES and not e.get("decor")]   # decor = scene scenery
    vertical = H > W
    spans = []
    for e in els:
        s, en = float(e.get("start", 0)), float(e.get("end", dur))
        spans.append((s, en, e["type"]))
        name = f"{e['type']}@{s:.2f}"
        if e["type"] != "captions" and en - s < 0.6:
            res.append(("overlay_min_duration", "fail", round(en - s, 3), ">= 0.6 s", name))
        if vertical:
            y = float(e.get("y", H / 2))
            half = float(e.get("h", H * (0.06 if e["type"] in ("text", "headline", "chip", "captions") else 0.15))) / 2
            top, bot = (y - half) / H, (y + half) / H
            if top < 0.10 or bot > 0.85:
                res.append(("safe_zone_vertical", "fail", f"{top:.2f}-{bot:.2f} of height", "inside 0.10-0.85", name))
            if "w" in e or "x" in e:                         # box edge; centred text may be narrower -> warn
                x, w = float(e.get("x", W / 2)), float(e.get("w", 0))
                if (x + w / 2) / W > 0.88:
                    res.append(("safe_zone_right", "warn", f"box right edge at {(x + w / 2) / W:.2f} W", "<= 0.88 W (clear of buttons)",
                                name + " (box width; check the glyphs on a still)"))
    if vertical and spans:
        pts = sorted({s for s, _, _ in spans} | {e for _, e, _ in spans})
        worst = max((sum(1 for s, e, _ in spans if s <= t + 1e-6 < e), t) for t in pts)
        res.append(("max_overlays_at_once", "fail" if worst[0] > 2 else "pass", worst[0], "<= 2 (reels)", f"at {worst[1]:.2f}s"))
    return res


def caption_checks(plan, words, fps, cps):
    res = []
    if words:
        cues = C.build_cues(words, cps=cps, fps=fps)
        bad = C.validate_cues(cues, cps=cps, fps=fps)
        res.append(("broadcast_cues", "warn" if bad else "pass", f"{len(cues)} cues, {len(bad)} issues",
                    f"42 chars x 2 lines, {cps:g} cps, 0.833-7 s, 2-frame gap", "; ".join(f"#{b['cue']} {b['rule']}={b['value']}" for b in bad[:5])))
    for el in (plan or {}).get("elements", []):
        if el.get("type") != "captions" or not words:
            continue
        chunks = creator_caption_chunks(el, words)
        maxc = int(el.get("maxChars", C.MAX_CHARS))
        fast = [c for c in chunks if " " in c["text"] and len(c["text"]) / c["dur"] > cps]  # one word on screen cannot be split further
        short = [c for c in chunks if c["dur"] < 0.3]
        long_ = [c for c in chunks if len(c["text"]) > maxc]
        res.append(("creator_captions_cps", "warn" if fast else "pass", f"{len(fast)}/{len(chunks)} chunks over {cps:g} cps",
                    f"<= {cps:g} cps", "; ".join(f"'{c['text']}' {len(c['text']) / c['dur']:.0f}cps" for c in fast[:4])))
        res.append(("creator_captions_flash", "warn" if short else "pass", f"{len(short)} chunks < 0.3 s", ">= 0.3 s per chunk", ""))
        res.append(("creator_captions_chars", "warn" if long_ else "pass", f"{len(long_)} chunks > {maxc} chars", f"<= {maxc}", ""))
    return res


# ------------------------------------------------------------------ perceptual checks: script, glyphs, face, end frames
LANG_SCRIPT = {"hi": "DEVANAGARI", "bgc": "DEVANAGARI", "mr": "DEVANAGARI", "ne": "DEVANAGARI", "sa": "DEVANAGARI",
               "bho": "DEVANAGARI", "raj": "DEVANAGARI", "ur": "ARABIC", "ar": "ARABIC", "fa": "ARABIC", "pa": "GURMUKHI",
               "bn": "BENGALI", "gu": "GUJARATI", "or": "ORIYA", "ta": "TAMIL", "te": "TELUGU", "kn": "KANNADA",
               "ml": "MALAYALAM", "en": "LATIN", "es": "LATIN", "fr": "LATIN", "de": "LATIN", "pt": "LATIN", "it": "LATIN"}
SCRIPTS = set(LANG_SCRIPT.values()) | {"CYRILLIC", "GREEK", "CJK", "HIRAGANA", "KATAKANA", "HANGUL", "THAI"}
TEXT_KEYS = ("text", "title", "subtitle", "label", "query", "name", "role", "kicker")
GENERIC_FONTS = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "emoji", "math", "ui-sans-serif",
                 "ui-serif", "ui-monospace", "ui-rounded", "inherit", "initial", "unset"}
CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIRS = (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
             "/usr/share/fonts", os.path.expanduser("~/.local/share/fonts"), "/Library/Fonts", os.path.expanduser("~/Library/Fonts"))
FACE_TEXT_TYPES = {"text", "headline", "chip", "captions", "card", "lowerthird", "ticker", "counter", "tile", "sticker",
                   "checklist", "searchbar"}
FACE_STEP, FACE_MAX_S, FACE_MIN_COVER = 0.1, 0.5, 0.15   # sample step s, allowed time on the face, overlap share
END_S = 0.3


def script_of(ch):
    """Unicode script of a letter or mark ('DEVANAGARI', 'ARABIC', 'LATIN'...); None for digits, punctuation, spaces."""
    if unicodedata.category(ch)[0] not in "LM":
        return None
    word = unicodedata.name(ch, " ").split(" ")[0]
    return None if word in ("", "COMBINING", "MODIFIER") else word


def el_text(el):
    """All on-screen text of one plan element, HTML tags stripped."""
    vals = [el.get(k) for k in TEXT_KEYS] + [w.get("w") for w in el.get("words") or [] if isinstance(w, dict)]
    for k in ("items", "lines"):
        vals += [i.get("text") if isinstance(i, dict) else i for i in (el.get(k) if isinstance(el.get(k), list) else [])]
    return html.unescape(re.sub(r"<[^>]+>", " ", " ".join(v for v in vals if isinstance(v, str)))).strip()


def plan_texts(plan):
    """[(where, text)] for the plan's caption words and every element that puts text on screen."""
    out = [("words", " ".join(str(w.get("w", "")) for w in plan.get("words") or []).strip())]
    out += [(f"{el.get('type')}@{float(el.get('start', 0)):.2f}", el_text(el)) for el in plan.get("elements", [])]
    return [(k, t) for k, t in out if t]


def expected_script(plan, lang=None):
    """Expected caption script from --lang, else plan.script / plan.language / plan.profile; None when unset."""
    prof = plan.get("profile") if isinstance(plan.get("profile"), dict) else {}
    v = lang or plan.get("script") or plan.get("language") or prof.get("script") or prof.get("language")
    if not v:
        return None
    s = LANG_SCRIPT.get(str(v).strip().lower().replace("_", "-").split("-")[0], str(v).strip().upper())
    if s not in SCRIPTS:
        raise ValueError(f"unknown caption language/script {v!r}: use a code ({', '.join(sorted(LANG_SCRIPT))}) or a script name")
    return s


def script_checks(texts, expected):
    """FAIL when caption/text letters are in a script other than the expected one (Latin is allowed: English words)."""
    counts, where = Counter(), defaultdict(list)
    for k, t in texts:
        for s in filter(None, map(script_of, t)):
            counts[s] += 1
            if k not in where[s]:
                where[s].append(k)
    hist = ", ".join(f"{s.title()} {n}" for s, n in counts.most_common()) or "no letters"
    if not counts:
        return [("caption_script", "info", hist, "", "")]
    if not expected:
        other = [s for s in counts if s != "LATIN"]
        return [("caption_script", "warn" if len(other) > 1 else "info", hist, "set plan.language or --lang to enforce",
                 "mixed non-Latin scripts" if len(other) > 1 else "")]
    want = f"{expected.title()} (+ Latin)"
    wrong = [s for s in counts if s not in (expected, "LATIN")]
    if wrong:
        return [("caption_script", "fail", hist, want, "; ".join(f"{s.title()} in {', '.join(where[s][:4])}" for s in wrong))]
    if expected != "LATIN" and counts["LATIN"] > counts[expected]:
        return [("caption_script", "warn", hist, want, "mostly Latin letters: romanised transcript?")]
    return [("caption_script", "pass", hist, want, "")]


def font_stacks(plan):
    """Ordered family lists the skin uses: --font-* vars (base.css defaults unless the theme sets them) and the
    font-family rules of the skin CSS. ponytail: element-specific fonts inside base.css (mono, VT323) are skipped."""
    th = plan.get("theme") or {}
    fvars, stacks, missing = {}, [], []
    for k, v in re.findall(r"(--font-(?:display|body))\s*:\s*([^;]+);", open(os.path.join(CORE, "runtime", "base.css"), encoding="utf-8").read()):
        fvars.setdefault(k, v)
    fvars.update({k: v for k, v in (th.get("vars") or {}).items() if k.startswith("--font")})
    stacks += fvars.values()
    for p in th.get("cssFiles") or []:
        if os.path.exists(p):
            stacks += re.findall(r"font-family\s*:\s*([^;}]+)", open(p, encoding="utf-8").read())
        else:
            missing.append(p)
    out = []
    for s in stacks:
        fams = [f.strip().strip("'\"").strip() for f in s.split("!")[0].split(",")]
        fams = [f for f in fams if f and not f.startswith("var(") and f.lower() not in GENERIC_FONTS]
        if fams and fams not in out:
            out.append(fams)
    return out, missing


def parse_font_ranges(css):
    """{family lower: [(lo, hi)]}: the unicode-range each @font-face serves (no range = all, as in CSS)."""
    out = {}
    for block in re.findall(r"@font-face\s*{([^}]*)}", css):
        fam, rng = re.search(r"font-family:\s*['\"]?([^;'\"]+)", block), re.search(r"unicode-range:\s*([^;]+)", block)
        if not fam:
            continue
        spans = out.setdefault(fam[1].strip().lower(), [])
        for part in (rng[1].split(",") if rng else ["U+0-10FFFF"]):
            lo, _, hi = part.strip().upper().removeprefix("U+").partition("-")
            spans.append((int(lo.replace("?", "0"), 16), int((hi or lo).replace("?", "F"), 16)))
    return out


def google_font_ranges(url):
    """Web-font coverage straight from the skin's fontsUrl (a Chrome UA gets the per-subset unicode-range)."""
    req = urllib.request.Request(url, headers={"User-Agent": CHROME_UA})
    return parse_font_ranges(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))


@functools.lru_cache(maxsize=1)
def local_fonts():
    """{family lower: font file} for installed fonts (~2 s for a full Windows font folder; built only when needed)."""
    from PIL import ImageFont
    out = {}
    for d in FONT_DIRS:
        for p in sorted(glob.glob(os.path.join(d, "**", "*.[ot]t[fc]"), recursive=True)):
            try:
                out.setdefault(ImageFont.truetype(p, 12).getname()[0].lower(), p)
            except OSError:      # unreadable font file: the renderer cannot use it either
                continue
    return out


def _pillow_coverage(path):
    """ch -> bool without fontTools: a missing char renders the same bitmap as .notdef (glyph 0)."""
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(path, 40)

    def ink(ch):
        im = Image.new("L", (96, 96))
        ImageDraw.Draw(im).text((24, 16), ch, font=f, fill=255)
        return im.tobytes()
    notdef = ink("\U0010FFFD")                        # private-use char no font maps
    return lambda ch: ink(ch) != notdef


def file_coverage(path):
    """ch -> bool for a font file: fontTools cmap when installed, else the Pillow .notdef comparison."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return _pillow_coverage(path)
    cmap = TTFont(path, lazy=True, fontNumber=0).getBestCmap() or {}
    return lambda ch: ord(ch) in cmap


def family_coverage(fam, webfonts):
    """ch -> bool for a CSS family as the renderer resolves it (web font first, then an installed font);
    None when it is neither loaded nor installed, so the browser skips it."""
    spans = webfonts.get(fam.lower())
    if spans is not None:
        return lambda ch: any(lo <= ord(ch) <= hi for lo, hi in spans)
    path = local_fonts().get(fam.lower())
    return file_coverage(path) if path else None


def glyph_checks(plan, texts):
    """Tofu: every letter/mark/digit on screen must be in some family of each skin font stack.
    ponytail: web fonts are judged by their subset unicode-range, not per-glyph cmap."""
    chars = sorted({ch for _, t in texts for ch in t if unicodedata.category(ch)[0] in "LMN"})
    if not chars:
        return []
    stacks, missing = font_stacks(plan)
    url, webfonts, note = (plan.get("theme") or {}).get("fontsUrl") or "", {}, ""
    if url:
        try:
            webfonts = google_font_ranges(url)
        except (OSError, ValueError) as e:
            note = f" Web fonts unverified: fonts CSS unreachable ({e})."
    res = [("glyph_coverage", "warn", f"{len(missing)} skin CSS files missing", "theme.cssFiles exist", "; ".join(missing))] if missing else []
    for fams in stacks:
        left, used = chars, []
        for fam in fams:
            cov = family_coverage(fam, webfonts)
            if cov is None:
                used.append(f"{fam}: not loaded")
                continue
            got = [c for c in left if cov(c)]
            used.append(f"{fam}: {len(got)}")
            left = [c for c in left if not cov(c)]
            if not left:
                break
        stack = ", ".join(fams)
        if left:
            scr = sorted({(script_of(c) or "DIGIT").title() for c in left})
            res.append(("glyph_coverage", "warn", f"{len(left)} chars missing in {stack}", f"every char in [{stack}]",
                        f"no glyph for {''.join(left[:12])} ({', '.join(scr)}): tofu or a system fallback font ({'; '.join(used)}).{note}"))
        else:
            res.append(("glyph_coverage", "pass", f"{len(chars)} chars", f"every char in [{stack}]", "; ".join(used)))
    return res


def face_at(track, ts, t):
    """engine.js faceAt: linear interpolation of the normalized {t,x,y,w,h} face boxes, clamped at the ends."""
    i = bisect.bisect_right(ts, t) - 1
    if i < 0:
        return track[0]
    if i >= len(track) - 1:
        return track[-1]
    a, b = track[i], track[i + 1]
    k = min(1.0, max(0.0, (t - a["t"]) / ((b["t"] - a["t"]) or 1)))
    return {q: a[q] + (b[q] - a[q]) * k for q in "xywh"}


def text_box(el, W, H):
    """(left, top, right, bottom) px of a centred plan element. ponytail: plan geometry, not the rendered DOM;
    a missing h is one 0.06 H line, a missing w is chars x 0.5 line height (render-measured boxes would be exact)."""
    h = float(el.get("h") or H * (0.06 if el["type"] in ("text", "headline", "chip", "captions") else 0.15))
    n = int(el.get("maxChars") or 22) if el["type"] == "captions" else len(el_text(el))
    w = float(el.get("w") or min(W * 0.9, max(n, 4) * 0.5 * h))
    x, y = float(el.get("x", W / 2)), float(el.get("y", H * 0.68 if el["type"] == "captions" else H / 2))
    return x - w / 2, y - h / 2, x + w / 2, y + h / 2


def face_checks(plan, W, H, dur):
    """WARN when a text box covers >= 15 % of the face box (or of itself) for more than 0.5 s. Decor is skipped."""
    track = sorted((f for f in plan.get("track") or [] if all(k in f for k in "txywh")), key=lambda f: f["t"])
    if not track:
        return [("text_over_face", "info", "no face track in plan", "", "")]
    ts, hits = [f["t"] for f in track], []
    for el in plan.get("elements", []):
        if el.get("type") not in FACE_TEXT_TYPES or el.get("decor"):
            continue
        l, t, r, b = text_box(el, W, H)
        s, e = float(el.get("start", 0)), min(float(el.get("end", dur)), dur)
        n = 0
        for k in range(max(0, int((e - s) / FACE_STEP))):
            f = face_at(track, ts, s + (k + 0.5) * FACE_STEP)
            fl, ft, fr, fb = f["x"] * W, f["y"] * H, (f["x"] + f["w"]) * W, (f["y"] + f["h"]) * H
            inter = max(0.0, min(r, fr) - max(l, fl)) * max(0.0, min(b, fb) - max(t, ft))
            n += inter > 0 and inter >= FACE_MIN_COVER * min((r - l) * (b - t), (fr - fl) * (fb - ft))
        if n * FACE_STEP > FACE_MAX_S:
            hits.append(f"{el['type']}@{s:.2f} {n * FACE_STEP:.1f}s")
    return [("text_over_face", "warn" if hits else "pass", len(hits), "no text box on the face > 0.5 s", "; ".join(hits[:6]))]


def end_frame_check(frames, dur, maxval=255.0):
    """FAIL when a frame in the last 0.3 s is black (90th-percentile luma under 10 % grey) or blank (10-90 % luma
    spread <= 8 levels: an empty background). ponytail: a bright, heavily vignetted empty background is missed."""
    black, flat = (16 + 0.10 * 219) / 255 * maxval, 8 / 255 * maxval
    tail = [(t, lo, hi) for t, lo, hi in frames if None not in (t, lo, hi) and t >= dur - END_S - 1e-6]
    if not tail:
        return ("end_frames", "warn", "no frame stats for the last 0.3 s", "no black or empty frames at the end", "")
    bad = [f"{t:.2f}s {'black' if hi <= black else 'blank'}" for t, lo, hi in tail if hi <= black or hi - lo <= flat]
    return ("end_frames", "fail" if bad else "pass", f"{len(bad)}/{len(tail)} frames black/blank",
            "no black or empty frames in the last 0.3 s", ", ".join(bad[:6]))


# ------------------------------------------------------------------ main QC
def _add(rows, check, status, value, expected="", detail=""):
    rows.append({"check": check, "status": status, "value": value, "expected": expected, "detail": detail})


def _reframed(st, O):
    """A delivery in a different aspect ratio than its plan (e.g. 9:16 cut of a 16:9 master)."""
    if not (O.get("width") and st.get("width")):
        return False
    return abs(st["width"] / st["height"] - O["width"] / O["height"]) > 0.02


def _tech_checks(rows, st, pr, plan, path):
    if not st.get("width"):  # audio-only delivery (podcast mp3/wav): only audio checks apply
        _add(rows, "audio_present", "pass" if st["acodec"] else "fail", f"{st['acodec']} {st['sample_rate']} Hz x{st['channels']}", "audio stream")
        return
    O = (plan or {}).get("output", {})
    if O.get("duration"):
        dd = abs(st["duration"] - float(O["duration"]))
        _add(rows, "duration_vs_plan", "pass" if dd <= 1.5 / (st["fps"] or 30) else "warn" if dd <= 0.5 else "fail",
             round(st["duration"], 3), f"{O['duration']} s (+-1 frame)")
    if O.get("width"):
        ok = (st["width"], st["height"]) == (O["width"], O["height"])
        reframed = _reframed(st, O)
        _add(rows, "resolution_vs_plan", "pass" if ok else ("info" if reframed else "fail"), f"{st['width']}x{st['height']}",
             f"{O['width']}x{O['height']}", "platform reframe of the master: plan geometry checks skipped" if reframed else "")
    if O.get("fps") and st["fps"]:
        _add(rows, "fps_vs_plan", "pass" if abs(st["fps"] - O["fps"]) < 0.01 else "warn", st["fps"], O["fps"])
    if pr and pr["w"]:
        ok = (st["width"], st["height"]) == (pr["w"], pr["h"])
        _add(rows, "resolution_vs_platform", "pass" if ok else "warn", f"{st['width']}x{st['height']}", f"{pr['w']}x{pr['h']}")
    if pr and pr["vcodec"] == "h264":
        _add(rows, "codec", "pass" if st["vcodec"] == "h264" else "fail", st["vcodec"], "h264")
        _add(rows, "pix_fmt", "pass" if st["pix_fmt"] == "yuv420p" else "fail", st["pix_fmt"], "yuv420p (4:2:0 8-bit)")
        _add(rows, "colour_tags", "pass" if st["color"][0] == "bt709" else "warn", st["color"], "bt709 x3")
    else:
        _add(rows, "codec", "info", f"{st['vcodec']} {st['pix_fmt']}")
    if path.lower().endswith((".mp4", ".mov", ".m4v")):
        atoms = mp4_atoms(path)
        fs = "moov" in atoms and "mdat" in atoms and atoms.index("moov") < atoms.index("mdat")
        _add(rows, "faststart", "pass" if fs else "warn", " ".join(atoms[:4]), "moov before mdat")
    ki = keyframe_interval(path)
    _add(rows, "keyframe_interval", "info", ki, "YouTube: closed GOP = fps/2")
    _add(rows, "audio_present", "pass" if st["acodec"] else "fail", f"{st['acodec']} {st['sample_rate']} Hz x{st['channels']}", "audio stream")
    if pr and pr["max_bytes"]:
        _add(rows, "file_size", "pass" if st["bytes"] <= pr["max_bytes"] else "fail", f"{st['bytes'] / 2 ** 20:.1f} MB", f"<= {pr['max_bytes'] / 2 ** 20:.0f} MB")
    if pr and pr["max_dur"]:
        _add(rows, "max_length", "pass" if st["duration"] <= pr["max_dur"] else "fail", round(st["duration"], 2), f"<= {pr['max_dur']} s")


def _signal_checks(rows, an, st, pr, fps):
    lo = an["loudness"]
    if lo and pr and pr["lufs"] is not None:
        di = abs(lo.get("I", -99) - pr["lufs"])
        _add(rows, "integrated_loudness", "pass" if di <= 1 else "warn" if di <= 2 else "fail", lo.get("I"), f"{pr['lufs']} LUFS +-1")
        tp = lo.get("TP", 0)
        _add(rows, "true_peak", "pass" if tp <= pr["tp"] + 0.1 else "warn" if tp <= pr["tp"] + 0.5 else "fail", tp, f"<= {pr['tp']} dBTP")
        _add(rows, "loudness_range", "pass" if lo.get("LRA", 0) <= pr["lra"] else "warn", lo.get("LRA"), f"<= {pr['lra']} LU")
    elif lo:
        _add(rows, "loudness", "info", lo)
    gaps = [s for s in an["silence"] if s[1] - s[0] > 2]
    _add(rows, "silence_gaps_gt_2s", "warn" if gaps else "pass", len(gaps), "none", "; ".join(f"{a:.1f}-{b:.1f}s" for a, b in gaps[:5]))
    _add(rows, "black_frames", "warn" if an["black"] else "pass", len(an["black"]), "none",
         "; ".join(f"{a:.2f}-{b:.2f}s" for a, b in an["black"][:5]))
    bits = 1023.0 if st["pix_fmt"] and "10" in st["pix_fmt"] else 255.0
    fl = flash_analysis(an["yavg"], fps, bits)
    _add(rows, "flash_frames", "warn" if fl["flash_frames"] else "pass", len(fl["flash_frames"]), "no 1-frame luma spikes",
         ", ".join(map(str, fl["flash_frames"][:8])))
    _add(rows, "photosensitivity", "fail" if fl["max_flashes_per_s"] >= 3 else "pass", fl["max_flashes_per_s"],
         "< 3 flashes in any 1 s (Netflix/Harding)", f"worst at {fl['at']:.2f}s" if fl["at"] is not None else "")
    if st.get("width"):
        _add(rows, *end_frame_check(an["frames"], st["duration"], bits))
    if an["brng"]:
        badf = sum(1 for b in an["brng"] if b > 0.01) / len(an["brng"])
        strict = pr is not None and pr["vcodec"] == "mpeg2_50"
        _add(rows, "illegal_levels_brng", "pass" if badf <= 0.01 else ("fail" if strict else "warn"), f"{badf * 100:.1f}% frames > 1% out-of-range px",
             "<= 1% of frames", f"max BRNG {max(an['brng']):.4f}")


def av_sync(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time,duration", "-of", "json", path],
                         stdout=subprocess.PIPE, text=True).stdout
    ss = {s["codec_type"]: s for s in json.loads(out or "{}").get("streams", [])}
    if "video" not in ss or "audio" not in ss:
        return None
    f = lambda s, k: float(s.get(k) or 0)
    return {"start_offset_ms": round((f(ss["audio"], "start_time") - f(ss["video"], "start_time")) * 1000, 1),
            "duration_diff_ms": round((f(ss["audio"], "duration") - f(ss["video"], "duration")) * 1000, 1)}


def perceptual_checks(plan, st, lang=None):
    """Caption script, glyph coverage and text-over-face rows for a plan (geometry in plan output pixels)."""
    texts, O = plan_texts(plan), plan.get("output") or {}
    try:
        rows = script_checks(texts, expected_script(plan, lang))
    except ValueError as e:
        rows = [("caption_script", "warn", str(e), "a known language code or script", "")]
    return rows + glyph_checks(plan, texts) + face_checks(plan, O.get("width") or st["width"], O.get("height") or st["height"],
                                                          float(O.get("duration") or st["duration"]))


def qc(video, plan_path=None, platform="auto", cps=C.CPS_ADULT, lang=None):
    plan = load_json(plan_path) if plan_path else None
    st = stream_info(video)
    if platform == "auto":
        platform = ("podcast-mp3" if not st.get("width") else
                    "reels" if st["height"] and st["width"] and st["height"] > st["width"] else "youtube")
    platform = {"podcast": "podcast-mp3", "audio": "audio-wav"}.get(platform, platform)
    pr = PRESETS.get(platform) if platform != "none" else None
    fps = st["fps"] or 30
    rows = []
    _tech_checks(rows, st, pr, plan, video)
    an = analyse(video, bool(st["acodec"]))
    _signal_checks(rows, an, st, pr, fps)
    sync = av_sync(video)
    if sync:
        bad = abs(sync["start_offset_ms"]) > 1000 / fps or abs(sync["duration_diff_ms"]) > 100
        _add(rows, "av_sync_heuristic", "warn" if bad else "pass", sync, "start offset <= 1 frame, durations within 100 ms",
             "stream timing only; lip-sync itself is not measured")
    if plan:
        words = plan.get("words") or []
        for check, status, value, expected, detail in caption_checks(plan, words, fps, cps) + \
                overlay_checks(plan, st["width"], st["height"], st["duration"]) + perceptual_checks(plan, st, lang):
            _add(rows, check, status, value, expected, detail)
    summary = {s: sum(1 for r in rows if r["status"] == s) for s in ("pass", "warn", "fail", "info")}
    return {"video": os.path.abspath(video), "plan": plan_path, "platform": platform, "stream": st,
            "measured_loudness": an["loudness"], "summary": summary, "checks": rows}


def write_md(rep, path):
    L = [f"# QC report: {os.path.basename(rep['video'])}", "", f"Platform spec: **{rep['platform']}**. "
         f"Result: {rep['summary']['fail']} FAIL, {rep['summary']['warn']} WARN, {rep['summary']['pass']} pass.", "",
         "| status | check | value | expected | detail |", "|---|---|---|---|---|"]
    order = {"fail": 0, "warn": 1, "pass": 2, "info": 3}
    for r in sorted(rep["checks"], key=lambda r: order[r["status"]]):
        L.append(f"| {r['status'].upper()} | {r['check']} | {r['value']} | {r['expected']} | {str(r['detail'])[:120]} |")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


def _self_test():
    plan = {"language": "hi", "words": [{"w": w} for w in "हर बात तीरा".split()],
            "elements": [{"type": "text", "text": "<em>Life</em> ہر بات", "start": 1}]}
    assert script_of("ह") == "DEVANAGARI" and script_of("ب") == "ARABIC" and script_of("।") is None
    r = script_checks(plan_texts(plan), expected_script(plan))[0]
    assert r[1] == "fail" and "text@1.00" in r[4], r
    plan["elements"][0]["text"] = "<em>Life</em> में"
    assert script_checks(plan_texts(plan), expected_script(plan))[0][1] == "pass"
    assert script_checks(plan_texts(plan), expected_script({}, "ur"))[0][1] == "fail"
    track = [{"t": 0, "x": 0.25, "y": 0.2, "w": 0.5, "h": 0.3}, {"t": 10, "x": 0.25, "y": 0.2, "w": 0.5, "h": 0.3}]
    on = {"type": "text", "text": "hello there", "x": 540, "y": 700, "start": 0, "end": 2}
    assert face_checks({"track": track, "elements": [on]}, 1080, 1920, 10)[0][1] == "warn"
    assert face_checks({"track": track, "elements": [dict(on, y=1500), dict(on, end=0.4), dict(on, decor=True)]}, 1080, 1920, 10)[0][1] == "pass"
    ok = [(i / 30, 20.0, 180.0) for i in range(300)]
    assert end_frame_check(ok, 10)[0] == "end_frames" and end_frame_check(ok, 10)[1] == "pass"
    assert end_frame_check(ok[:-3] + [(9.95, 16.0, 17.0)], 10)[1] == "fail"           # black last frame
    assert end_frame_check(ok[:-3] + [(9.95, 120.0, 124.0)], 10)[1] == "fail"         # flat (empty) last frame
    rng = parse_font_ranges("@font-face { font-family: 'Mukta'; unicode-range: U+0900-097F, U+20B9; }")
    assert family_coverage("Mukta", rng)("ह") and not family_coverage("Mukta", rng)("A")
    arial = os.path.join(FONT_DIRS[0], "arial.ttf")
    if os.path.exists(arial):
        for cov in (file_coverage(arial), _pillow_coverage(arial)):
            assert cov("A") and not cov("ह")
    log("qc self-test ok")


def main():
    if sys.argv[1:] == ["--self-test"]:
        return _self_test()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--plan")
    ap.add_argument("--platform", default="auto", help="preset name from deliver.py, 'auto' or 'none'")
    ap.add_argument("--lang", help="expected caption language or script (hi, ur, en, Devanagari...); "
                                   "default plan.script / plan.language / plan.profile")
    ap.add_argument("--out-dir")
    ap.add_argument("--kids", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any check fails")
    a = ap.parse_args()
    if a.platform not in ("auto", "none", "podcast", "audio") and a.platform not in PRESETS:
        sys.exit(f"unknown platform {a.platform}")
    if a.lang:
        try:
            expected_script({}, a.lang)
        except ValueError as e:
            sys.exit(str(e))
    rep = qc(a.video, a.plan, a.platform, C.CPS_KIDS if a.kids else C.CPS_ADULT, a.lang)
    od = a.out_dir or os.path.dirname(os.path.abspath(a.video))
    stem = os.path.splitext(os.path.basename(a.video))[0]
    save_json(os.path.join(od, f"qc_{stem}.json"), rep)
    write_md(rep, os.path.join(od, f"qc_{stem}.md"))
    s = rep["summary"]
    log(f"QC {stem} ({rep['platform']}): {s['fail']} fail, {s['warn']} warn, {s['pass']} pass -> {od}")
    for r in rep["checks"]:
        if r["status"] in ("fail", "warn"):
            log(f"  {r['status'].upper():4} {r['check']}: {r['value']} (expected {r['expected']}) {r['detail']}")
    sys.exit(1 if a.strict and s["fail"] else 0)


if __name__ == "__main__":
    main()
