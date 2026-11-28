#!/usr/bin/env python3
"""The editor brain: genre presets, Rule-of-Six-lite cut scoring, pacing, retention, overlay and caption checks.

usage: editor.py review PLAN.json [--genre NAME] [--fix] [--out review.md]
       editor.py genres                 # list genre presets
       editor.py genre NAME             # print one preset as JSON

Importable: make_plan.py, autocut.py and story.py use load_genre(), sentences(), hook_score(), cut_score(),
review(), apply_fixes(), snap_to_beats(), load_beats(), compact_track(), apply_genre_defaults().
All scores are heuristics that encode editing conventions (see references/craft.md). They flag, they don't decide.
"""
import copy, json, os, re, shutil, sys
from vs_common import norm          # Indic-safe word key (keeps Devanagari vowel signs); story.py uses editor.norm
from captions import glen           # on-screen length in grapheme clusters

HERE = os.path.dirname(os.path.abspath(__file__))
GENRES_PATH = os.path.join(HERE, "genres.json")
_GENRES = None


# ---------------- genres ----------------
def genres():
    global _GENRES
    if _GENRES is None:
        with open(GENRES_PATH, encoding="utf-8") as f:
            _GENRES = json.load(f)["genres"]
    return _GENRES


def load_genre(name):
    """Return a copy of a genre preset, None for no name. Unknown names raise ValueError listing valid ones."""
    if not name:
        return None
    g = genres().get(name)
    if g is None:
        raise ValueError(f"unknown genre '{name}'. Known: {', '.join(sorted(genres()))}")
    return dict(copy.deepcopy(g), name=name)


def guess_genre(plan):
    o = plan.get("output", {})
    vertical = o.get("height", 1920) > o.get("width", 1080)
    return load_genre("reel-talking-head" if vertical or o.get("duration", 0) <= 90 else "youtube-longform")


# ---------------- text helpers ----------------
ENDS = re.compile(r"[.!?…।॥]['\")]*$")   # incl. Devanagari danda / double danda
GREETING = re.compile(r"^\s*(hi|hey|hello|yo|namaste|what'?s up|welcome( back)?|good (morning|evening|afternoon))\b|"
                      r"\b(hi|hey|hello) (guys|everyone|everybody|friends|all)\b|\bwelcome (back )?to (my|the|our)\b|"
                      r"\bin (this|today'?s) video\b|\btoday (we|i)('re| are| am|'m)? (going to|gonna)\b|\bbefore we (start|begin)\b|"
                      r"\bdon'?t forget to (like|subscribe)\b", re.I)
CTA = re.compile(r"\b(follow|subscribe|comment|link in (the )?bio|link below|click|tap|save this|share this|sign up|"
                 r"download|shop now|order now|book (a|your)|dm me|turn on notifications|watch (the )?(full|next))\b", re.I)
CURIOSITY = re.compile(r"\b(secret|nobody|no one|most people|why|how|here'?s|the reason|truth|actually|mistakes?|never|stop|"
                       r"don'?t|until|what happens|wait|turns out|biggest|worst|best|only|hidden|wrong)\b|\?", re.I)
CONTRAST = re.compile(r"\b(but|instead|yet|however|versus|vs|not .{1,30} but|everyone thinks|the opposite|used to)\b", re.I)
EMOTION = re.compile(r"\b(love|hate|scared|afraid|cried|crying|angry|happy|shocked|insane|crazy|incredible|amazing|terrible|"
                     r"broke|lost|failed|won|proud|ashamed|regret|dream|died|alone|finally|never again|heart)\b", re.I)
PAYOFF = re.compile(r"\b(so|that'?s why|which means|the point|the lesson|result|because|remember|fix|grow|that'?s how|in the end|now you)\b", re.I)
NUMBER = re.compile(r"(\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|billion|percent)\b)", re.I)
LAUGH = re.compile(r"\b(haha+|lol|\[laugh\w*\]|\(laugh\w*\))", re.I)
EARLY_END = re.compile(r"\b(in conclusion|to wrap (this|it) up|that'?s (it|all) for (today|this video)|before i go|to sum up)\b", re.I)
STRONG = set("free secret never always best worst money million billion mistake stop why how new fast easy huge viral truth "
             "hack hidden simple wrong right crazy insane biggest important first last only nobody everyone everything nothing "
             "win lose fail growth rich broke results proof real fake".split())


def sentences(words, gap=0.6):
    """Index lists, split on sentence punctuation or pauses > gap (same rule make_plan.py uses)."""
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and w["start"] - words[i - 1]["end"] > gap:
            out.append(cur); cur = []
        cur.append(i)
        if ENDS.search(w["w"]):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def text_of(words, idx):
    return re.sub(r"\s+([,.!?%।॥])", r"\1", " ".join(words[i]["w"] for i in idx)).strip()


def hook_score(text):
    """Hook potential of a line: numbers, contrast, curiosity gap, emotion; minus greetings / back-references."""
    s, why = 0.0, []
    n = len(text.split())
    if NUMBER.search(text): s += 2; why.append("number")
    if CURIOSITY.search(text): s += 2; why.append("curiosity gap")
    if CONTRAST.search(text): s += 1.5; why.append("contrast")
    if EMOTION.search(text): s += 1.5; why.append("emotion")
    if text.strip().endswith("?"): s += 1; why.append("question")
    if GREETING.search(text): s -= 4; why.append("greeting (-)")
    if CTA.search(text): s -= 3; why.append("CTA (-)")
    if re.match(r"^\s*(and|but|so|because|which|it|this|that|they|he|she|um|uh)\b", text, re.I): s -= 1.5; why.append("needs context (-)")
    if n < 4: s -= 1; why.append("too short (-)")
    if n > 22: s -= 1.5; why.append("too long (-)")
    return round(s, 2), why


# ---------------- Rule of Six (lite) ----------------
WEIGHTS = {"emotion": 0.51, "story": 0.23, "rhythm": 0.10, "eye_trace": 0.07, "plane_2d": 0.05, "space_3d": 0.04}


def cut_score(prev_words, next_words, gap=0.4, seg_len=None, asl=(2.0, 4.0), beat_dist=None, face_shift=None):
    """Score a cut (join) 0-100 with Murch's weights. Proxies (heuristic, documented in craft.md):
    emotion  - outgoing thought is complete, ends on an emphasis word, laughter, or a held beat (pause) after it
    story    - outgoing sentence complete + incoming starts a new sentence (no mid-thought splice)
    rhythm   - beat distance if beats are known, else segment length vs genre ASL target
    eye      - primary face position continuity across the cut (track.json), neutral 0.5 without it
    2D/3D    - not measurable from a transcript: neutral 0.5"""
    last = prev_words[-1]["w"] if prev_words else ""
    first = next_words[0]["w"] if next_words else ""
    complete = bool(ENDS.search(last))
    clause = last.rstrip().endswith((",", ";", ":", "-", "—"))
    tail = " ".join(w["w"] for w in prev_words[-4:])
    emo = 0.35 + (0.35 if complete else 0.15 if clause else 0)
    if norm(last) in STRONG or NUMBER.search(last) or EMOTION.search(tail): emo += 0.15
    if LAUGH.search(tail) or gap >= 0.5: emo += 0.15
    story = (0.6 if complete else 0.35 if clause else 0.05) + (0.4 if first[:1].isupper() or complete else 0.1)
    if beat_dist is not None:
        rhythm = max(0.0, 1 - beat_dist / 0.12)
    elif seg_len is not None:
        lo, hi = asl
        rhythm = 1.0 if lo <= seg_len <= hi else max(0.0, 1 - min(abs(seg_len - lo), abs(seg_len - hi)) / max(hi, 0.5))
    else:
        rhythm = 0.5
    eye = 0.5 if face_shift is None else max(0.0, 1 - face_shift / 0.25)
    parts = {"emotion": min(1, emo), "story": min(1, story), "rhythm": rhythm, "eye_trace": eye, "plane_2d": 0.5, "space_3d": 0.5}
    return {"score": round(100 * sum(WEIGHTS[k] * v for k, v in parts.items()), 1), "parts": {k: round(v, 2) for k, v in parts.items()}}


# ---------------- small plan utilities ----------------
OVERLAY_SKIP = {"captions", "progress", "background", "flash", "shape", "rec", "equalizer", "ticker"}
TEXTY = {"text", "headline", "chip", "tile", "sticker"}
PRIORITY = {"titlecard": 4, "card": 3, "counter": 3, "bars": 3, "compare": 3, "clip": 3, "image": 3, "lowerthird": 2,
            "headline": 2, "text": 2, "scribble": 1, "chip": 1, "tile": 1, "sticker": 1, "burst": 0}


def _span(e, dur):
    return float(e.get("start", 0) or 0), float(e.get("end", dur) if e.get("end") is not None else dur)


def overlays(plan):
    dur = plan["output"]["duration"]
    out = []
    for i, e in enumerate(plan.get("elements", [])):
        s, en = _span(e, dur)
        if e.get("type") in OVERLAY_SKIP or e.get("decor") or (s <= 0.05 and en >= dur * 0.9):
            continue
        out.append((i, e, s, en))
    return out


def el_text(e):
    return str(e.get("text") or e.get("title") or e.get("label") or "")


def join_times(plan, work=None):
    """Cut points on the output timeline from <work>/cutlist.json (autocut), if present."""
    work = work or plan.get("_work")
    p = os.path.join(work, "cutlist.json") if work else None
    if not p or not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        segs = json.load(f).get("segments", [])
    return [s["out_start"] for s in segs if s.get("out_start", 0) > 0.05]


def jump_joins(plan, work=None):
    """Joins that are real jump cuts: every autocut join, but on a timeline assembly only joins between two pieces
    of the same source clip (a change to another clip/photo is a shot change, not a jump cut)."""
    work = work or plan.get("_work")
    p = os.path.join(work, "cutlist.json") if work else None
    if not p or not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        cl = json.load(f)
    segs = cl.get("segments", [])
    if cl.get("kind") != "timeline":
        return [s["out_start"] for s in segs if s.get("out_start", 0) > 0.05]
    return [b["out_start"] for a, b in zip(segs, segs[1:]) if a.get("src") == b.get("src")]


def word_index_at(words, t):
    return next((i for i, w in enumerate(words) if w["start"] >= t - 0.02), None)


# ---------------- checks ----------------
SEV = {"high": 25, "med": 12, "low": 5}


def _cat():
    return {"score": 100, "issues": [], "notes": []}


def _issue(cat, sev, msg, fix=None):
    cat["issues"].append({"sev": sev, "msg": msg, **({"fix": fix} if fix else {})})
    cat["score"] = max(0, cat["score"] - SEV[sev])


def check_cuts(plan, g, joins, jumps=None):
    cat, words = _cat(), plan.get("words", [])
    jumps = joins if jumps is None else jumps
    if not words:  # music/photo montage: nothing spoken to cut mid-thought; rhythm is judged in pacing
        cat["notes"].append(f"{len(joins)} cuts, no dialogue: cut points judged by pacing/beat only")
        joins = []
    scores = []
    asl = tuple(g["asl_s"])
    prev_t = 0.0
    for t in joins:
        pw = [w for w in words if w["end"] <= t + 0.02][-4:]
        nw = [w for w in words if w["start"] >= t - 0.02][:4]
        gap = (nw[0]["start"] - pw[-1]["end"]) if pw and nw else 0.4
        sc = cut_score(pw, nw, gap=gap, seg_len=t - prev_t, asl=asl)
        scores.append(sc["score"]); prev_t = t
        if sc["score"] < 45:
            ctx = f" ('{pw[-1]['w']}' | '{nw[0]['w']}')" if pw and nw else ""
            _issue(cat, "low", f"cut at {t:.2f}s scores {sc['score']:.0f}/100, likely mid-thought{ctx}",
                   "move the cut to the end of the thought or cover it (B-roll, punch-in, L-cut)")
    if scores:
        cat["notes"].append(f"{len(scores)} cuts, mean Rule-of-Six score {sum(scores) / len(scores):.0f}/100")
    allowed = " ".join(g["transitions"]["allowed"])
    if jumps and "jump" not in allowed:
        covered = _visual_times(plan, include_cuts=False)
        bare = [t for t in jumps if not any(abs(t - c) < 0.35 for c in covered) and not _in_cutaway(plan, t)]
        if bare:
            _issue(cat, "med", f"{len(bare)} jump cuts uncovered ({', '.join(f'{t:.1f}' for t in bare[:6])}s); "
                   f"{g['name']} hides interview cuts", "cover with B-roll (cutaways, >=0.5 s each side), an alternate angle or a >=1.2x punch-in")
    return cat


def _in_cutaway(plan, t):
    return any(c.get("start", 0) - 0.5 <= t <= c.get("end", 0) + 0.5 for c in plan.get("cutaways", []))


def _visual_times(plan, include_cuts=True, joins=()):
    sp = plan.get("speaker", {})
    ts = [z["start"] for z in sp.get("zooms", []) if sp.get("mode") != "none"]
    ts += [s for _, _, s, _ in overlays(plan)]
    ts += [c.get("start", 0) for c in plan.get("cutaways", [])]
    for e in plan.get("elements", []):
        if e.get("type") == "flash":
            ts += list(e.get("times", []))
    if include_cuts:
        ts += list(joins)
    return sorted(t for t in ts if t is not None)


def check_pacing(plan, g, joins):
    cat = _cat()
    dur = plan["output"]["duration"]
    iv = g["interrupt_s"]
    ev = [0.0] + [t for t in _visual_times(plan, joins=joins) if 0 < t < dur] + [dur]
    stretches = [(a, b) for a, b in zip(ev, ev[1:]) if b - a > iv * 1.15]
    longest = max((b - a for a, b in zip(ev, ev[1:])), default=dur)
    changes = len(ev) - 2
    cat["notes"].append(f"{changes} visual changes in {dur:.1f}s (every {dur / max(1, changes + 1):.1f}s), longest static stretch "
                        f"{longest:.1f}s, genre interval {iv}s")
    shots = [0.0] + sorted(set(joins) | {c.get("start", 0) for c in plan.get("cutaways", [])}) + [dur]
    lens = [b - a for a, b in zip(shots, shots[1:]) if b - a > 0.05]
    if lens:
        asl = sum(lens) / len(lens)
        lo, hi = g["asl_s"]
        cat["notes"].append(f"ASL {asl:.1f}s over {len(lens)} shots (target {lo}-{hi}s)")
        if len(lens) >= 4:
            mean = asl
            sd = (sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5
            if sd / mean < 0.15:
                _issue(cat, "low", f"shot lengths are uniform (sd {sd:.2f}s) - rhythm feels mechanical", "vary shot lengths: mix long holds and quick cuts")
    for a, b in stretches:
        _issue(cat, "med" if b - a > iv * 2 else "low", f"{b - a:.1f}s without a visual change ({a:.1f}-{b:.1f}s)",
               "add a pattern interrupt: zoom punch, overlay, B-roll slot or sfx (--fix adds zoom punches)")
    cat["_stretches"] = stretches
    return cat


def check_retention(plan, g, joins):
    cat, words = _cat(), plan.get("words", [])
    dur = plan["output"]["duration"]
    short = g["family"] in ("short-form", "ad") or dur <= 90
    sents = sentences(words)
    first = text_of(words, sents[0]) if sents else ""
    if words and words[0]["start"] > 0.3:
        _issue(cat, "high" if short else "low", f"dead air at the start: first word at {words[0]['start']:.2f}s",
               "trim the head (autocut.py --breath 0.1 or prep.py --start)")
    within = g["hook"]["within_s"]
    hooks = [e for _, e, s, en in overlays(plan) if s <= min(0.5, within) and el_text(e).strip()]
    if short and not hooks:
        _issue(cat, "high", f"no hook text on screen in the first {within}s (most short-form plays start muted)",
               "add a hook element at 0s: <=7 words, the promise or the curiosity gap")
    for e in hooks:
        n = len(el_text(e).split())
        if n > g["hook"]["max_words"]:
            _issue(cat, "med", f"hook text is {n} words: '{el_text(e)[:60]}'", f"cut it to <= {g['hook']['max_words']} words")
    if first and GREETING.search(first):
        _issue(cat, "high" if short else "med", f"first spoken line is a greeting/preamble: '{first[:70]}'",
               "cold open on the strongest line (story.py outline ranks hook candidates)")
    elif first:
        hs, why = hook_score(first)
        if hs < 1.5:
            _issue(cat, "med", f"first line has weak hook potential ({hs}): '{first[:70]}'", "lead with a number, contrast, question or stakes")
        else:
            cat["notes"].append(f"first line hooks ({', '.join(why)})")
    if not short:
        early = [w for w in words if w["start"] < dur * 0.85]
        txt = " ".join(w["w"] for w in early)
        if EARLY_END.search(txt):
            _issue(cat, "med", "the ending is signalled before the payoff ('in conclusion', 'to wrap up'...)", "don't signal the end; end soon after the payoff")
        return cat
    head = " ".join(w["w"] for w in words if w["start"] < max(3.0, dur * 0.25))
    if words and not (CURIOSITY.search(head) or NUMBER.search(head)):
        _issue(cat, "med", "no open loop in the opening (no promise, number, question or curiosity gap)",
               "pose the question early and answer it at the end")
    tail_s = [text_of(words, s) for s in sents if words[s[0]]["start"] >= dur * 0.55 and words[s[-1]]["end"] <= dur - 0.5]
    if words and not any(PAYOFF.search(t) or NUMBER.search(t) for t in tail_s):
        _issue(cat, "low", "no clear payoff line in the back half", "land the payoff (result / lesson) before the CTA")
    wants_cta = any("cta" in b["beat"].lower() or "outro" in b["beat"].lower() for b in g["structure"])
    end_el = [e for _, e, s, en in overlays(plan) if en >= dur - 0.2 and s >= dur - 4 and el_text(e)]
    spoken = " ".join(w["w"] for w in words if w["start"] >= dur - 3.0)
    if wants_cta and not end_el and not CTA.search(spoken):
        _issue(cat, "med", "no CTA in the last 2-3 s", "add an end card or a spoken CTA in the last 2 s (or end on a loop)")
    return cat


def _face_boxes(plan):
    tr = plan.get("track")
    if not tr:
        return None
    W, H = plan["output"]["width"], plan["output"]["height"]
    if max(max(f["x"], f["y"], f["w"], f["h"]) for f in tr) > 1.5:
        return tr                                    # assume already in output pixels
    sp = plan.get("speaker", {})
    sw, sh = plan.get("sourceSize", [W, H])            # approximate: cover-crop from source aspect
    k = max(W / sw, H / sh)
    ox, oy = (sw * k - W) * sp.get("focusX", 0.5), (sh * k - H) * sp.get("focusY", 0.5)
    return [{"t": f["t"], "x": f["x"] * sw * k - ox, "y": f["y"] * sh * k - oy, "w": f["w"] * sw * k, "h": f["h"] * sh * k} for f in tr]


def check_overlays(plan, g):
    cat = _cat()
    W, H, dur = plan["output"]["width"], plan["output"]["height"], plan["output"]["duration"]
    ov = overlays(plan)
    mx = g.get("max_overlays", 2)
    marks = sorted({round(t, 2) for _, _, s, en in ov for t in (s, en)})
    worst = 0
    for t in marks:
        live = [i for i, _, s, en in ov if s <= t + 1e-3 < en]
        if len(live) > mx:
            worst = max(worst, len(live))
    if worst:
        _issue(cat, "med", f"up to {worst} overlays on screen at once (max {mx} for {g['name']})", "drop or shift the weakest (--fix drops)")
    for i, e, s, en in ov:
        if en - s < 0.6:
            _issue(cat, "low", f"element #{i} ({e.get('type')}) is on screen {en - s:.2f}s (< 0.6 s)", "extend to >= 0.6 s or drop (--fix)")
    words = plan.get("words", [])
    for i, e, s, en in ov:
        if e.get("type") not in TEXTY or s < 0.3:
            continue
        tok = norm(el_text(e).split()[0]) if el_text(e).split() else ""
        hit = next((w for w in words if norm(w["w"]) == tok and abs(w["start"] - s) < 0.6), None)
        if hit:
            lead = hit["start"] - s
            if not 0.03 <= lead <= 0.15:
                _issue(cat, "low", f"'{el_text(e)[:24]}' enters {lead:+.2f}s vs its word (want 0.05-0.10 s before)", "--fix sets start = word - 0.08 s")
    if H > W:
        sz = g.get("safe_zone", {"top": 0.10, "bottom": 0.85, "right": 0.88})
        for i, e, s, en in ov + [(i, e) + _span(e, dur) for i, e in enumerate(plan.get("elements", [])) if e.get("type") == "captions"]:
            y, x = e.get("y"), e.get("x")
            if isinstance(y, (int, float)) and not (H * sz["top"] <= y <= H * sz["bottom"]) and e.get("type") != "titlecard":
                _issue(cat, "med", f"element #{i} ({e.get('type')}) at y={y:.0f}px is outside the 9:16 safe zone", "--fix clamps into the safe zone")
            if isinstance(x, (int, float)) and isinstance(e.get("w"), (int, float)) and x + e["w"] / 2 > W * sz["right"] + 2:
                _issue(cat, "low", f"element #{i} ({e.get('type')}) reaches under the right-edge buttons", "move left / narrow it")
    faces = _face_boxes(plan)
    if faces:
        hits = 0
        for i, e, s, en in ov:
            if e.get("layer") == "behind" or not isinstance(e.get("y"), (int, float)):
                continue
            ex, ey = (e["x"] if isinstance(e.get("x"), (int, float)) else W / 2), e["y"]
            ew = e["w"] if isinstance(e.get("w"), (int, float)) else min(W * 0.9, 45 * max(4, glen(el_text(e))))
            eh = e["h"] if isinstance(e.get("h"), (int, float)) else 140
            for f in faces:
                if s <= f["t"] <= en and abs(ex - (f["x"] + f["w"] / 2)) < (ew + f["w"]) / 2 and abs(ey - (f["y"] + f["h"] / 2)) < (eh + f["h"]) / 2:
                    hits += 1
                    _issue(cat, "med", f"element #{i} ({e.get('type')}) covers the face at {f['t']:.1f}s", "move it above/below the face or put it behind (layer 'behind')")
                    break
        if not hits:
            cat["notes"].append("no overlay covers the tracked face")
    return cat


def check_captions(plan, g):
    cat = _cat()
    caps = [e for e in plan.get("elements", []) if e.get("type") == "captions"]
    words = plan.get("words", [])
    lim = g["captions"]["cps"]
    if not caps:
        if g["captions"]["mode"] != "none" and words:
            _issue(cat, "high" if g["family"] == "short-form" else "med", "no captions (most short-form plays muted; accessibility)", "add a captions element")
        return cat
    if not words:
        return cat
    n = int(caps[0].get("maxWords", g["captions"]["max_words"] or 3)) or 3
    fast = []
    for k in range(0, len(words), n):
        ch = words[k:k + n]
        span = max(0.2, ch[-1]["end"] - ch[0]["start"])
        cps = sum(glen(w["w"]) for w in ch) / span
        if cps > lim:
            fast.append((ch[0]["start"], cps))
    speak = sum(w["end"] - w["start"] for w in words)
    cat["notes"].append(f"speech {sum(glen(w['w']) for w in words) / max(0.1, speak):.1f} chars/s while talking, limit {lim} cps, {n} words per caption")
    if len(fast) > max(1, len(words) // (n * 5)):
        _issue(cat, "low", f"{len(fast)} caption groups exceed {lim} cps (first at {fast[0][0]:.1f}s, {fast[0][1]:.0f} cps)",
               "fewer words per group (word-pop) or loosen the cut (--max-gap / --breath) so lines can be read")
    return cat


def review(plan, g=None, work=None):
    """Run every check. Returns {"genre", "overall", "categories": {name: {score, issues, notes}}}."""
    g = g or (load_genre(plan["genre"]) if plan.get("genre") in genres() else guess_genre(plan))
    joins = join_times(plan, work)
    cats = {"retention": check_retention(plan, g, joins), "pacing": check_pacing(plan, g, joins),
            "overlays": check_overlays(plan, g), "captions": check_captions(plan, g), "cuts": check_cuts(plan, g, joins, jump_joins(plan, work))}
    wts = {"retention": 30, "pacing": 25, "overlays": 20, "captions": 15, "cuts": 10}
    overall = round(sum(cats[k]["score"] * w for k, w in wts.items()) / sum(wts.values()))
    return {"genre": g["name"], "overall": overall, "categories": cats, "_g": g}


def render_md(rep, plan_path=""):
    g = rep["_g"]
    L = [f"# Edit review: {os.path.basename(plan_path) or 'plan'}", "",
         f"Genre: **{rep['genre']}** ({g['label']}). Overall **{rep['overall']}/100**. Scores are editor heuristics, not truths.", "",
         "| category | score | issues |", "| --- | --- | --- |"]
    for k, c in rep["categories"].items():
        L.append(f"| {k} | {c['score']} | {len(c['issues'])} |")
    for k, c in rep["categories"].items():
        L += ["", f"## {k} ({c['score']}/100)"]
        L += [f"- {n}" for n in c["notes"]]
        for i in c["issues"]:
            L.append(f"- **[{i['sev']}]** {i['msg']}" + (f"  \n  fix: {i['fix']}" if i.get("fix") else ""))
        if not c["issues"]:
            L.append("- no issues")
    L += ["", "## genre checklist", f"- target length {g['duration_s'][0]}-{g['duration_s'][1]} s, ASL {g['asl_s'][0]}-{g['asl_s'][1]} s, "
          f"pattern interrupt every {g['interrupt_s']} s", f"- loudness {g['loudness']['lufs']} LUFS / {g['loudness']['true_peak']} dBTP ({g['loudness']['platform']})",
          f"- structure: {' -> '.join(b['beat'] + ' ' + str(b['pct']) + '%' for b in g['structure'])}"]
    L += [f"- QC: {q}" for q in g["qc"]]
    L += [f"- client judges: {', '.join(g['client_judges'])}", f"- deliverables: {'; '.join(g['deliverables'])}"]
    return "\n".join(L) + "\n"


def summary(rep):
    c = rep["categories"]
    top = next((i for k in ("retention", "pacing", "overlays", "captions", "cuts") for i in c[k]["issues"] if i["sev"] == "high"), None) or \
        next((i for k in c for i in c[k]["issues"]), None)
    s = f"review [{rep['genre']}] {rep['overall']}/100 - " + ", ".join(f"{k} {v['score']}" for k, v in c.items())
    return s + (f"\n  top issue: {top['msg']}" if top else "")


# ---------------- safe automatic fixes ----------------
def apply_fixes(plan, g=None, work=None):
    """Returns (new_plan, changes). Safe only: clamp timings, fix entry leads, drop overlap excess, add zoom-punch interrupts."""
    p = copy.deepcopy(plan)
    g = g or (load_genre(p["genre"]) if p.get("genre") in genres() else guess_genre(p))
    W, H, dur = p["output"]["width"], p["output"]["height"], p["output"]["duration"]
    ch, words = [], p.get("words", [])
    els = p.get("elements", [])
    # 1. clamp timings
    for i, e in enumerate(els):
        if "start" in e and e["start"] < 0:
            e["start"] = 0; ch.append(f"#{i} start clamped to 0")
        if "end" in e and e["end"] > dur + 1:
            e["end"] = round(dur + 1, 3); ch.append(f"#{i} end clamped to {dur + 1:.2f}")
    for z in p.get("speaker", {}).get("zooms", []):
        z["start"], z["end"] = max(0, z["start"]), min(dur, z["end"])
    p["sfx"] = [dict(s, t=min(max(0, s["t"]), dur)) for s in p.get("sfx", [])]
    # 2. entry leads + min duration + safe zone
    sz = g.get("safe_zone", {"top": 0.10, "bottom": 0.85})
    for i, e, s, en in overlays(p):
        if e.get("type") in TEXTY and s >= 0.3 and el_text(e).split():
            tok = norm(el_text(e).split()[0])
            hit = next((w for w in words if norm(w["w"]) == tok and abs(w["start"] - s) < 0.6), None)
            if hit and not 0.03 <= hit["start"] - s <= 0.15:
                e["start"] = round(max(0, hit["start"] - 0.08), 3); s = e["start"]; ch.append(f"#{i} enters 0.08 s before '{hit['w']}'")
        if en - s < 0.6:
            if s + 0.6 <= dur + 1:
                e["end"] = round(s + 0.6, 3); ch.append(f"#{i} extended to 0.6 s")
            else:
                e["_drop"] = True; ch.append(f"#{i} dropped (too short)")
        y = e.get("y")
        if H > W and isinstance(y, (int, float)) and e.get("type") != "titlecard" and not (H * sz["top"] <= y <= H * sz["bottom"]):
            e["y"] = round(min(max(y, H * (sz["top"] + 0.02)), H * (sz["bottom"] - 0.03))); ch.append(f"#{i} y clamped into safe zone")
    # 3. too many overlays at once -> drop lowest priority (never the hook at 0 s or the end card)
    mx = g.get("max_overlays", 2)
    for _ in range(50):
        ov = [(i, e, s, en) for i, e, s, en in overlays(p) if not e.get("_drop")]
        bad = None
        for t in sorted({s for _, _, s, _ in ov}):
            live = [x for x in ov if x[2] <= t + 1e-3 < x[3]]
            if len(live) > mx:
                cand = [x for x in live if x[2] > 0.3 and x[3] < dur - 0.2] or live
                bad = min(cand, key=lambda x: (PRIORITY.get(x[1].get("type"), 1), -x[2]))
                break
        if not bad:
            break
        bad[1]["_drop"] = True; ch.append(f"#{bad[0]} ({bad[1].get('type')}) dropped: more than {mx} overlays at once")
    p["elements"] = [e for e in els if not e.pop("_drop", False)]
    # 4. pattern interrupts: zoom punches inside long static stretches
    sp = p.get("speaker", {})
    if sp.get("mode", "full") != "none" and p.get("source"):
        cat = check_pacing(p, g, join_times(p, work))
        iv = g["interrupt_s"]
        zooms = sp.setdefault("zooms", [])
        n = 0
        for a, b in cat["_stretches"]:
            k = int((b - a) // iv)
            for j in range(1, k + 1):
                t = a + (b - a) * j / (k + 1)
                wi = word_index_at(words, t - 0.4)
                if wi is not None and abs(words[wi]["start"] - t) < iv / 2:
                    t = words[wi]["start"]
                if any(z["start"] - 0.5 < t < z["end"] + 0.5 for z in zooms):
                    continue
                zooms.append({"start": round(max(0, t - 0.06), 3), "end": round(min(dur, t + min(1.0, iv * 0.45)), 3),
                              "scale": 1.12 if n % 2 == 0 else 1.07, "snap": True})
                n += 1
        zooms.sort(key=lambda z: z["start"])
        if n:
            ch.append(f"added {n} zoom-punch interrupts")
    return p, ch


# ---------------- make_plan helpers ----------------
def load_beats(path):
    """beats.json: [t,...] | {"beats":[t|{t}...], "downbeats":[...]} -> sorted floats"""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    src = d if isinstance(d, list) else (d.get("beats") or d.get("times") or [])
    out = [float(x["t"] if isinstance(x, dict) else x) for x in src]
    return sorted(out)


def snap_to_beats(t, beats, tol=0.12):
    if not beats:
        return t
    b = min(beats, key=lambda x: abs(x - t))
    return round(b, 3) if abs(b - t) <= tol else t


def compact_track(track, step=0.1):
    """track.json {fps, faces:[{id, frames:[{t,x,y,w,h}]}], primary} -> [{t,x,y,w,h}] for the primary face at 1/step fps."""
    faces = track.get("faces", [])
    if not faces:
        return []
    face = next((f for f in faces if f.get("id") == track.get("primary")), None) or max(faces, key=lambda f: len(f.get("frames", [])))
    fr = sorted(face.get("frames", []), key=lambda f: f["t"])
    if not fr:
        return []
    out, j, t = [], 0, 0.0
    end = fr[-1]["t"]
    while t <= end + 1e-6:
        while j + 1 < len(fr) and abs(fr[j + 1]["t"] - t) <= abs(fr[j]["t"] - t):
            j += 1
        if abs(fr[j]["t"] - t) <= max(step, 0.2):
            f = fr[j]
            out.append({"t": round(t, 2), **{k: round(float(f[k]), 4) for k in ("x", "y", "w", "h")}})
        t = round(t + step, 6)
    return out


DEFAULT_HOOK = {"type": "chip", "text": "{text}", "y": "=H*0.16", "w": "=W*0.86", "fit": True, "in": "pop"}


def apply_genre_defaults(auto, g):
    """Fill density / hook / caption settings the theme does not define. theme.json always wins."""
    a = copy.deepcopy(auto)
    if not g:
        return a
    cap = g["captions"]
    if cap["mode"] != "none":
        if "captions" not in a:
            vertical = g["aspect"] == "9:16"
            a["captions"] = {"type": "captions", "mode": cap["mode"], "maxWords": cap["max_words"] or 3,
                             "uppercase": cap["uppercase"], "y": "=H*0.70" if vertical else "=H*0.88",
                             **({"className": "cap-soft"} if not vertical else {})}
        else:
            a["captions"].setdefault("maxWords", cap["max_words"] or 3)
    if "keywords" in a:
        a["keywords"].setdefault("every", g["interrupt_s"])
    elif g["family"] in ("short-form", "ad"):
        a["keywords"] = {"every": g["interrupt_s"], "zoom": 1.1, "alternate": True, "zoomHold": 0.9}
    if "hook" not in a and g["family"] in ("short-form", "ad"):
        a["hook"] = {"dur": max(1.5, min(3.0, g["hook"]["within_s"] + 1)), "element": copy.deepcopy(DEFAULT_HOOK)}
    elif "hook" in a:
        a["hook"].setdefault("dur", max(1.5, min(3.0, g["hook"]["within_s"] + 1)))
    return a


# ---------------- CLI ----------------
def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("review", help="score a plan.json and write review.md")
    r.add_argument("plan"); r.add_argument("--genre", default=None); r.add_argument("--fix", action="store_true")
    r.add_argument("--out", default=None)
    sub.add_parser("genres", help="list presets")
    s = sub.add_parser("genre", help="print one preset"); s.add_argument("name")
    a = ap.parse_args(argv)
    if a.cmd == "genres":
        for k, g in genres().items():
            print(f"{k:22s} {g['aspect']:5s} {g['duration_s'][0]:>5}-{g['duration_s'][1]:<5}s  {g['label']}")
        return 0
    if a.cmd == "genre":
        print(json.dumps(load_genre(a.name), indent=2, ensure_ascii=False)); return 0
    path = os.path.abspath(a.plan)
    with open(path, encoding="utf-8") as f:
        plan = json.load(f)
    work = os.path.abspath(os.path.join(os.path.dirname(path), plan.get("workDir", ".")))
    try:
        g = load_genre(a.genre) if a.genre else None
    except ValueError as e:
        print(f"[video-studio] ERROR: {e}", file=sys.stderr); return 2
    if a.fix:
        new, changes = apply_fixes(plan, g, work)
        shutil.copyfile(path, path + ".bak")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new, f, ensure_ascii=False, indent=2)
        print(f"[video-studio] --fix: {len(changes)} changes (backup {os.path.basename(path)}.bak)")
        for c in changes:
            print("  - " + c)
        plan = new
    rep = review(plan, g, work)
    out = a.out or os.path.join(work, "review.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(render_md(rep, path))
    print(summary(rep))
    print(f"[video-studio] review -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
