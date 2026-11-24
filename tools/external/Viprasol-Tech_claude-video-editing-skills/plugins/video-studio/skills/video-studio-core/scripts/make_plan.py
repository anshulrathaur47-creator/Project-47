#!/usr/bin/env python3
"""Build a first-draft plan.json from the transcript and a style's theme.json.
Claude then refines the plan (better key words, headlines, cards) before rendering.

usage: make_plan.py --work WORKDIR --style /path/to/style-skill [--format 9:16] [--source cut.mp4]
                    [--duration 15] [--no-matte] [--out WORKDIR/plan.json] [--cta "Follow for more"]
                    [--genre reel-talking-head] [--beats WORKDIR/beats.json] [--no-review]
  --genre fills density / hook / captions from genres.json where the theme has none (theme.json always wins).
  Optional inputs read from WORKDIR when present: track.json -> plan["track"] (primary face, 10 fps),
  peaks.json -> plan["peaks"], beats.json -> plan["beats"] (+ beat snapping if auto.keywords.snap == "beats").
  Ends with a short editor.py review summary (advice only).

The style folder must contain theme.json (and usually theme.css). See references/theme-schema.md.
"""
import argparse, copy, json, math, os, re
from vs_common import load_json, save_json, probe, log, die, parse_format

ap = argparse.ArgumentParser()
ap.add_argument("--work", default="work")
ap.add_argument("--style", required=True)
ap.add_argument("--format", default=None)
ap.add_argument("--source", default=None, help="speaker video (default cut.mp4 or source.mp4 in work)")
ap.add_argument("--duration", type=float, default=None)
ap.add_argument("--no-matte", action="store_true")
ap.add_argument("--no-source", action="store_true", help="no speaker video (promo / type-only)")
ap.add_argument("--cta", default=None)
ap.add_argument("--title", default=None)
ap.add_argument("--clip", default=None, help="screen recording / product video available to elements as clip id 'main'")
ap.add_argument("--image", default=None, help="image available to elements as {image}")
ap.add_argument("--logo", default=None, help="logo image available to elements as {logo}")
ap.add_argument("--image2", default=None, help="second image available as {image2} (e.g. the 'after' photo)")
ap.add_argument("--out", default=None)
ap.add_argument("--genre", default=None, help="genre preset (editor.py genres): fills density/hook/captions the theme lacks")
ap.add_argument("--beats", default=None, help="beats.json; snaps zooms/flashes/key words to beats (default <work>/beats.json "
                                             "when theme auto.keywords.snap == 'beats')")
ap.add_argument("--no-review", action="store_true", help="skip the editor review summary")
a = ap.parse_args()

import editor
work = os.path.abspath(a.work)
style = os.path.abspath(a.style)
th = load_json(os.path.join(style, "theme.json"))
try:
    GENRE = editor.load_genre(a.genre)
except ValueError as e:
    die(str(e))
if GENRE:
    th = dict(th, auto=editor.apply_genre_defaults(th.get("auto", {}), GENRE))   # theme.json values always win
BEATS = []
_bp = a.beats or os.path.join(work, "beats.json")
if os.path.exists(_bp):
    BEATS = editor.load_beats(_bp)
SNAP = bool(BEATS) and (bool(a.beats) or th.get("auto", {}).get("keywords", {}).get("snap") == "beats")
bsnap = (lambda t: editor.snap_to_beats(t, BEATS)) if SNAP else (lambda t: t)
fmt = a.format or th.get("format", "9:16")
W, H = parse_format(fmt)
FPS = th.get("fps", 30)

# ---------- source & words ----------
src = None
if not a.no_source and th.get("speaker", {}).get("mode", "full") != "none":
    for cand in [a.source, os.path.join(work, "cut.mp4"), os.path.join(work, "source.mp4")]:
        if cand and os.path.exists(cand):
            src = os.path.abspath(cand); break
words = []
wpath = os.path.join(work, "words.json") if os.path.exists(os.path.join(work, "words.json")) else os.path.join(work, "transcript.json")
if os.path.exists(wpath):
    words = load_json(wpath).get("words", [])
    # glue Whisper's split tokens ("$10" ",000.", "50" "%") even for transcripts made before transcribe.py did it
    from captions import merge_tokens
    words = merge_tokens(words)
dur = a.duration or (probe(src)["duration"] if src else (words[-1]["end"] + 1.0 if words else
       (min(probe(a.clip)["duration"], th.get("maxDuration", 30)) if a.clip else th.get("defaultDuration", 10))))
dur = round(dur, 3)

# ---------- text analysis ----------
STOP = set("""a an the and or but if then so to of in on at for with from by as is are was were be been being am i you he she it we they me
him her us them my your his its our their this that these those there here what which who whom whose when where why how not no yes do does did
done have has had having just very really also too can could would should will shall may might must about into over under again more most some
any all each every other such only own same than s t don dont im youre its thats lets get got go going gonna wanna like um uh okay ok yeah
one thing things stuff kind sort lot lots out up down off now well even still way much many""".split())
STRONG = set("""free secret never always best worst money million billion mistake stop why how new fast easy huge viral truth
hack hidden simple wrong right crazy insane biggest important first last only nobody everyone everything nothing
win lose fail growth rich broke results proof real fake""".split())
import unicodedata
# keep letters, digits and combining marks (Devanagari/Indic vowel signs are category M, not \w)
clean = lambda s: "".join(ch for ch in unicodedata.normalize("NFC", s).lower() if ch.isalnum() or ch in "%$'.,_"
                          or unicodedata.category(ch).startswith("M")).strip(".,")
# Hindi / Haryanvi function words, pronouns, fillers and the refrain "बरगी" (like): never key words
STOP |= {clean(x) for x in """है हैं था थी थे हो हूँ हूं में मैं भी एक ए का की के को से और तो ना न नहीं वा हर ये यह वह वो
जो कि पर ने तू तुम आप हम मेरा मेरी मेरे तेरा तेरी तेरे इस उस कोई कुछ बस भाई यार बरगी सै सूं सा सी रे री जी हाँ हां अब जब
तब फिर कर करके रहा रही रहे गया गई गए म्हारा म्हारी थारा थारी कोनी""".split()}
glen = lambda s: sum(1 for ch in s if not unicodedata.category(ch).startswith("M"))   # visible length (aksharas)
NUM = re.compile(r"^(\$|₹|€|£)?(\d[\d,]*(\.\d+)?)(k|m|b|x|%)?$", re.I)


def score(w, i):
    c = clean(w["w"])
    caseless = any(unicodedata.category(ch) == "Lo" for ch in c)   # Devanagari etc.: no capital / proper-noun cue
    g = glen(c)
    if not c or c in STOP or g < (2 if caseless else 3) and not NUM.match(c):
        return 0
    s = 1.0
    if NUM.match(c): s += 5
    if c in STRONG: s += 4
    if caseless: s += 1.0 + 0.5 * min(g, 5)   # every content word clears minScore 2.5; longer words rank higher
    elif g >= 7: s += 1.5
    if w["w"][:1].isupper() and i > 0 and not re.search(r"[.!?]$", words[i - 1]["w"]): s += 1.5
    if w["w"].isupper() and len(c) > 1: s += 2
    if i in LAST_LINE: s += 2                 # genre emphasis "last-line": the punch line of a shayari / poem
    return s


def sentences():
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and (w["start"] - words[i - 1]["end"] > 0.6):
            out.append(cur); cur = []
        cur.append(i)
        nxt_gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 0
        new_line = i + 1 < len(words) and words[i + 1].get("line", w.get("line")) != w.get("line")   # transcribe.py --text
        if re.search(r"[.!?।॥]$", w["w"]) or (w["w"].endswith(",") and nxt_gap >= 0.3) or new_line:
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out


SENTS = sentences()
LAST_LINE = set(SENTS[-1]) if SENTS and (GENRE or {}).get("emphasis") == "last-line" else set()


def disp(w):
    return re.sub(r"^[\"'(]+|[\"'),.!?;:]+$", "", w["w"])


def ev(v):
    if isinstance(v, str) and v.startswith("="):
        return eval(v[1:], {"__builtins__": {}}, {"W": W, "H": H, "DUR": dur, "min": min, "max": max})
    return v


def fill(tpl, **kw):
    """deep copy a template, substitute {placeholders}, evaluate =expressions"""
    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str):
            if x.startswith("="):
                return ev(x)
            for k, v in kw.items():
                if x == "{" + k + "}":
                    return v
                x = x.replace("{" + k + "}", str(v))
            return x
        return x
    return walk(copy.deepcopy(tpl))


auto = th.get("auto", {})
els, sfx, zooms = [], [], []
first_sent = (" ".join(disp(words[i]) for i in SENTS[0][:8]) if SENTS else "")
PH = {"title": a.title or th.get("title") or first_sent or "Your title here", "cta": a.cta or th.get("cta", "Follow for more"),
      "dur": dur}
if a.image: PH["image"] = os.path.abspath(a.image)
if a.logo: PH["logo"] = os.path.abspath(a.logo)
if a.image2: PH["image2"] = os.path.abspath(a.image2)
UNRESOLVED = re.compile(r"\{(image|image2|logo|title|cta|text|label)\}")


def has_unresolved(x):
    if isinstance(x, dict): return any(has_unresolved(v) for v in x.values())
    if isinstance(x, list): return any(has_unresolved(v) for v in x)
    return isinstance(x, str) and bool(UNRESOLVED.search(x))

# static elements (backgrounds, rings, progress bars, grain...)
for tpl in auto.get("static", []):
    e = fill(tpl, **PH)
    cond = e.pop("onlyIf", None)
    if (cond == "words" and not words) or (cond == "noWords" and words):
        continue
    if not has_unresolved(e):
        els.append(e)

# captions
if auto.get("captions") and words:
    els.append(fill(auto["captions"]))

# second caption track from sentences (e.g. translation placeholder)
if auto.get("captions2") and words:
    e = fill(auto["captions2"])
    e["lines"] = []
    for n, sidx in enumerate(SENTS):
        nxt = SENTS[n + 1] if n + 1 < len(SENTS) else None
        e["lines"].append({"text": " ".join(words[i]["w"] for i in sidx), "start": words[sidx[0]]["start"],
                           "end": words[nxt[0]]["start"] if nxt else words[sidx[-1]]["end"] + 0.5})
    els.append(e)

# keywords: pick best word per window
kw_picked = []
if auto.get("keywords") and words:
    k = auto["keywords"]
    every = k.get("every", 2.5)
    scored = sorted([(score(w, i), i) for i, w in enumerate(words)], reverse=True)
    for s, i in scored:
        if s < k.get("minScore", 2.5):
            break
        t = words[i]["start"]
        if all(abs(t - words[j]["start"]) >= every for j in kw_picked) and t > k.get("after", 0.4):
            kw_picked.append(i)
        if len(kw_picked) >= k.get("max", int(dur / every) + 1):
            break
    kw_picked.sort()
    tpls = k.get("element")
    tpls = tpls if isinstance(tpls, list) else ([tpls] if tpls else [])
    for n, i in enumerate(kw_picked):
        w = dict(words[i], start=bsnap(words[i]["start"]))
        on_beat = w["start"] != words[i]["start"]
        if tpls:
            tpl = tpls[n % len(tpls)]
            for t1 in (tpl if isinstance(tpl, list) else [tpl]):   # a list = a group (e.g. word + hand-drawn circle)
                e = fill(t1, text=disp(w).upper() if k.get("uppercase") else disp(w))
                e["start"] = round(w["start"] - 0.05, 3); e["end"] = round(w["start"] + k.get("hold", 1.3), 3)
                e["_role"] = 2; e["_grp"] = f"k{n}"; els.append(e)
        if k.get("zoom"):
            zooms.append({"start": round(w["start"] - (0 if on_beat else 0.06), 3), "end": round(w["start"] + k.get("zoomHold", 1.0), 3),
                          "scale": k["zoom"] if n % 2 == 0 or not k.get("alternate") else 1 + (k["zoom"] - 1) * 0.6,
                          **({"snap": True} if k.get("snap") else {})})
        if k.get("sfx"):
            sfx.append({"t": round(w["start"] - 0.02, 3), "kind": k["sfx"], "gain": k.get("sfxGain", 0.5)})
    # mark key words in captions
    for e in els:
        if e.get("type") == "captions":
            e["keywords"] = sorted({clean(disp(words[i])) for i in kw_picked})

# headlines per sentence
LAYOUTS = []
if auto.get("headlines") and words:
    hcfg = auto["headlines"]
    tpls = hcfg["element"] if isinstance(hcfg["element"], list) else [hcfg["element"]]
    for n, sidx in enumerate(SENTS):
        if hcfg.get("layouts"):   # footage card moves to a new framed position every sentence (back to back, no gaps)
            nx = SENTS[n + 1] if n + 1 < len(SENTS) else None
            lo = dict(hcfg["layouts"][n % len(hcfg["layouts"])])
            lo["start"] = 0 if n == 0 else round(max(0, words[sidx[0]]["start"] - 0.08), 3)
            lo["end"] = round(words[nx[0]]["start"] - 0.08, 3) if nx else round(dur + 1, 3)
            LAYOUTS.append(lo)
        ws = [(score(words[i], i), i) for i in sidx]
        best = sorted([x for x in ws if x[0] > 0], reverse=True)[:hcfg.get("maxWords", 2)]
        if not best and tpls:   # every sentence gets its headline (scene): fall back to the longest word
            best = [max(((len(clean(words[i]["w"])), i) for i in sidx))]
        if not best:
            continue
        txt = " ".join(disp(words[i]) for _, i in sorted(best, key=lambda x: x[1]))
        if hcfg.get("full"):
            txt = " ".join(words[i]["w"] for i in sidx)
        if hcfg.get("uppercase", True):
            txt = txt.upper()
        s = words[sidx[0]]["start"]
        nxt = SENTS[n + 1] if n + 1 < len(SENTS) else None
        e_t = words[nxt[0]]["start"] if nxt else dur   # last sentence holds to the end: backdrops never drop to black
        tpl = tpls[n % len(tpls)] if tpls else []
        for gi, t1 in enumerate(tpl if isinstance(tpl, list) else [tpl]):   # a list = a group (e.g. backdrop + headline)
            e = fill(t1, text=txt)
            e["start"] = round(max(0, s - 0.08), 3); e["end"] = round(e_t - (0.08 if nxt else 0), 3)   # hand over cleanly to the next sentence
            e["_role"] = 2; e["_grp"] = f"h{n}"; els.append(e)

# numbers -> counters
if auto.get("numbers") and words:
    last = -9
    for i, w in enumerate(words):
        m = NUM.match(clean(w["w"]).replace(",", ""))
        if not m or w["start"] - last < 2.5:
            continue
        val = float(m.group(2).replace(",", ""))
        if val < 2 and not m.group(4):
            continue
        suf = (m.group(4) or "").upper().replace("X", "x")
        nxtw = clean(words[i + 1]["w"]) if i + 1 < len(words) else ""
        if not suf and nxtw in ("percent",): suf = "%"
        if not suf and nxtw in ("thousand", "million", "billion"): suf = {"thousand": "K", "million": "M", "billion": "B"}[nxtw]
        # label = the words that belong to this number in the same sentence: after it, else before it
        after = []
        if not re.search(r"[.!?]$", w["w"]):
            for x in words[i + 1:i + 5]:
                after.append(x)
                if re.search(r"[.!?,;:]$", x["w"]):
                    break
        before = []
        for x in reversed(words[max(0, i - 4):i]):
            if re.search(r"[.!?]$", x["w"]):
                break
            before.insert(0, x)
        pick = [x for x in after if clean(x["w"]) not in STOP and clean(x["w"]) not in ("percent", "thousand", "million", "billion")]
        if not pick:
            pick = [x for x in before if clean(x["w"]) not in STOP]
        label = " ".join(disp(x) for x in pick[:3])[:28]
        e = fill(auto["numbers"]["element"], label=label)
        e.update({"from": 0, "to": val, "prefix": m.group(1) or "", "suffix": suf, "decimals": 1 if m.group(3) else 0,
                  "start": round(w["start"] - 0.05, 3), "end": round(w["start"] + auto["numbers"].get("hold", 2.2), 3), "_role": 3})
        els.append(e); last = w["start"]
        if auto["numbers"].get("sfx"):
            sfx.append({"t": w["start"], "kind": auto["numbers"]["sfx"], "gain": 0.5})

# ordinal lists -> one card
if auto.get("lists") and words:
    ORD = re.compile(r"^(first|firstly|second|secondly|third|thirdly|fourth|fifth|next|finally|one|two|three|1|2|3|4|5)$")
    items = []
    for sidx in SENTS:
        c0 = clean(words[sidx[0]]["w"])
        c1 = clean(words[sidx[1]]["w"]) if len(sidx) > 1 else ""
        if ORD.match(c0) or (c0 == "number" and ORD.match(c1)) or (c0 == "step" and ORD.match(c1)):
            body = [words[i] for i in sidx[1:] if score(words[i], i) > 0][:4]
            if body:
                items.append({"text": " ".join(disp(x) for x in body), "at": words[sidx[0]]["start"]})
    if len(items) >= 2 and auto["lists"].get("each"):
        for k, it in enumerate(items):
            n = len(items) - k if auto["lists"].get("countdown") else k + 1
            nxt = items[k + 1]["at"] if k + 1 < len(items) else min(dur, it["at"] + 4)
            for tpl in auto["lists"]["each"]:
                e = fill(tpl, text=it["text"], n=n)
                e["start"] = round(it["at"] - 0.1, 3); e["end"] = round(nxt, 3)
                e["_role"] = 4; e["_grp"] = f"list{k}"; els.append(e)
    elif len(items) >= 2:
        e = fill(auto["lists"]["element"], title=a.title or auto["lists"].get("title", "In short"))
        e["items"] = items
        e["start"] = round(items[0]["at"] - 0.3, 3); e["end"] = round(min(dur, items[-1]["at"] + 4), 3)
        e["_role"] = 4; els.append(e)

# cut-point accents
cutlist = os.path.join(work, "cutlist.json")
if auto.get("cuts") and os.path.exists(cutlist):
    cts = [s["out_start"] for s in load_json(cutlist)["segments"] if s["out_start"] > 0.3]
    last, flashes = -9, []
    for t in cts:
        t = bsnap(t)
        if t - last >= auto["cuts"].get("minGap", 2.0):
            if auto["cuts"].get("sfx"): sfx.append({"t": t, "kind": auto["cuts"]["sfx"], "gain": auto["cuts"].get("gain", 0.25)})
            flashes.append(t); last = t
    if auto["cuts"].get("flash") and flashes:
        els.append({"type": "flash", "times": flashes, "color": auto["cuts"].get("flashColor", "#fff"), "opacity": 0.5, "dur": 0.12})

# hook title (first seconds)
if auto.get("hook"):
    hk = auto["hook"]
    first = SENTS[0] if SENTS else []
    txt = a.title or (" ".join(disp(words[i]) for i in first[:7]) if first else PH["title"])
    e = fill(hk["element"], **dict(PH, text=txt.upper() if hk.get("uppercase") else txt))
    e["start"] = 0; e["end"] = hk.get("dur", 2.2)
    e["_role"] = 5; els.append(e)
    if hk.get("sfx"): sfx.append({"t": 0.0, "kind": hk["sfx"], "gain": 0.5})

# end card
if auto.get("endcard"):
    ec = auto["endcard"]
    e = fill(ec["element"], **dict(PH, cta=a.cta or ec.get("cta", PH["cta"])))
    e["start"] = round(max(0, dur - ev(ec.get("dur", 2.0))), 3); e["end"] = round(dur + 1, 3)
    e["_role"] = 5; els.append(e)

# resolve overlaps: elements in the same screen slot must not overlap in time.
# priority: hook/endcard 5 > lists 4 > numbers 3 > keywords/headlines 2
def pos(e):
    return (e.get("x") if isinstance(e.get("x"), (int, float)) else W / 2, e.get("y") if isinstance(e.get("y"), (int, float)) else H / 2)


def near(a_, b_):
    if a_.get("layer", "front") != b_.get("layer", "front"):
        return False
    (x1, y1), (x2, y2) = pos(a_), pos(b_)
    return abs(x1 - x2) < W * 0.3 and abs(y1 - y2) < H * 0.16


ranked = [e for e in els if e.get("_role")]
ranked.sort(key=lambda e: -e["_role"])
kept = []
for e in ranked:
    for k2 in kept:
        if (e.get("_grp") and e.get("_grp") == k2.get("_grp")) or not near(k2, e) or e["end"] <= k2["start"] or e["start"] >= k2["end"]:
            continue
        if e["start"] < k2["start"]:
            e["end"] = k2["start"]           # lower priority ends when the higher one starts
        else:
            e["_drop"] = True
        if e["end"] - e["start"] < 0.6:
            e["_drop"] = True
        if e.get("_drop"):
            break
    if not e.get("_drop"):
        kept.append(e)
els = [e for e in els if not e.get("_drop")]
for e in els:
    e.pop("_role", None); e.pop("_drop", None); e.pop("_grp", None)

# 9:16 safe zone: centred boxes must stay clear of the right-side buttons (right 12%) -> max width 74% of W (with margin)
if H > W:
    for e in els:
        if e.get("type") in ("captions", "background", "progress", "flash", "ticker", "transition", "grain", "vignette",
                             "letterbox", "lightleak", "titlecard", "shape"):
            continue
        w_, x_ = e.get("w"), e.get("x", W / 2)
        if isinstance(w_, (int, float)) and isinstance(x_, (int, float)) and abs(x_ - W / 2) < 2                 and e.get("anchor", "center") == "center" and w_ > W * 0.74:
            e["w"] = round(W * 0.74)


# speaker config (fractions -> pixels)
spk = copy.deepcopy(th.get("speaker", {"mode": "full"}))
if not src:
    spk["mode"] = "none"
if "rectFrac" in spk:
    x, y, w, h = spk.pop("rectFrac"); spk["rect"] = [int(x * W), int(y * H), int(w * W) // 2 * 2, int(h * H) // 2 * 2]
spk.setdefault("zooms", [])
if LAYOUTS and spk.get("mode") != "none":
    for lo in LAYOUTS:
        if "rectFrac" in lo:
            x, y, w, h = lo.pop("rectFrac"); lo["rect"] = [int(x * W), int(y * H), int(w * W) // 2 * 2, int(h * H) // 2 * 2]
    spk["layouts"] = LAYOUTS
if spk.get("mode") != "none":
    spk["zooms"] += zooms
# matte.py edge contact (share of each border the person touches): a shrunk cut-out (personScale < 1) would show
# hard side edges, so slide it down at full width instead (personDrop keeps the sides at the frame edges)
_mj = os.path.join(work, "matte.json")
if os.path.exists(_mj) and spk.get("mode") != "none":
    _m = load_json(_mj)
    edge = _m.get("edge_contact") or _m.get("edges")
    if not isinstance(edge, dict):
        log(f"warning: {_mj} has no edge_contact {{left,right,top,bottom}}: cut-out framing not checked")
    elif max(edge.get("left", 0), edge.get("right", 0)) > 0.15 and spk.get("personScale", 1) < 1:
        spk.pop("personScale")
        spk["personDrop"] = spk.get("personDrop") or 0.12
        log(f"person touches the side edges (left {edge.get('left', 0):.2f}, right {edge.get('right', 0):.2f}): "
            f"personScale -> personDrop {spk['personDrop']}")

matte = None
if src and th.get("matte") and not a.no_matte:
    matte = os.path.join(work, "matte.mp4")

rel = lambda p: os.path.relpath(p, work) if p else None
theme = {"vars": th.get("vars", {}), "fontsUrl": th.get("fontsUrl"),
         "cssFiles": [os.path.join(style, f) for f in th.get("cssFiles", ["theme.css"]) if os.path.exists(os.path.join(style, f))]}
plan = {
    "version": 1, "style": th.get("name"), "workDir": ".",
    "output": {"width": W, "height": H, "fps": FPS, "duration": dur, "background": th.get("background", "black")},
    "source": rel(src), "matte": rel(matte), "speaker": spk, "theme": theme,
    "words": words, "clips": ([{"id": "main", "src": os.path.relpath(os.path.abspath(a.clip), work), "loop": True}] if a.clip else []),
    "cutaways": [], "elements": [e for e in els if not (e.get("clip") == "main" and not a.clip)],
    "sfx": sfx + [copy.deepcopy(x) for x in th.get("sfx", [])],
    "music": th.get("music"), "finish": th.get("finish", {}), "outputFile": "final.mp4",
}
# optional analysis inputs (only added when present, so old plans keep their exact shape)
if GENRE:
    plan["genre"] = GENRE["name"]
if os.path.exists(os.path.join(work, "track.json")):
    _tr = load_json(os.path.join(work, "track.json"))
    plan["track"] = editor.compact_track(_tr)          # primary face [{t,x,y,w,h}] at 10 fps
    if src and _tr.get("width"):
        plan["sourceSize"] = [_tr["width"], _tr["height"]]
    elif src:
        _p = probe(src); plan["sourceSize"] = [_p.get("width", W), _p.get("height", H)]
if os.path.exists(os.path.join(work, "peaks.json")):
    plan["peaks"] = load_json(os.path.join(work, "peaks.json"))
if BEATS:
    plan["beats"] = BEATS
out = a.out or os.path.join(work, "plan.json")
save_json(out, plan)
log(f"plan -> {out}  ({len(els)} elements, {len(kw_picked)} key words, {len(zooms)} zooms, {len(sfx)} sfx)")
if matte and not os.path.exists(matte):
    log("this style uses depth effects: run matte.py before render.py")
if not a.no_review:
    try:                                                   # editor review is advice only, never fails the plan
        log(editor.summary(editor.review(plan, GENRE, work)))
        log(f"full review: python {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'editor.py')} review {out}"
            + (f" --genre {GENRE['name']}" if GENRE else "") + "   (add --fix for safe fixes)")
    except Exception as e:
        log(f"(review skipped: {e})")
