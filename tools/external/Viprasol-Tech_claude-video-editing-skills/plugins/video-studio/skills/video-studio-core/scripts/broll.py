#!/usr/bin/env python3
"""B-roll auto-placement from the transcript.
Matches words in <work>/words.json to a folder of clips/images by file name (plus optional sidecar
NAME.txt keyword files), covers jump cuts first, then adds keyword B-roll up to a density.
Writes <work>/broll.json: {"cutaways": [{src, start, end, srcStart}],        # videos (plan.json format)
                           "elements": [{type: "image", motion: "kenburns", ...}], # stills
                           "placements": [...why each one is there...], "uncovered_joins": [t, ...]}

usage: broll.py --work W --library FOLDER [FOLDER/FILE ...] [--frequency low|med|high]
                [--min 1.2] [--max 4] [--allow-hook] [--merge W/plan.json] [--out broll.json]

Rules: each B-roll lasts 1.2-4 s, jump cuts (cutlist.json joins) are covered first with the shot laid
across the edit (0.6 s before, 0.9 s after), nothing in the first 1.5 s hook unless --allow-hook,
at least 0.8 s of the speaker between two B-roll shots. Frequency: low ~ 1 per 12 s, med ~ 1 per 7 s,
high ~ 1 per 4 s. Name your files after what they show: "coffee-pouring.mp4", "city_night.jpg".
--merge adds the result to an existing plan.json (previous B-roll from this script is replaced).
"""
import argparse, glob, os, re
from vs_common import probe, log, die, save_json, load_json

VID = (".mp4", ".mov", ".mkv", ".m4v", ".webm")
IMG = (".jpg", ".jpeg", ".png", ".webp")
SPACING = {"low": 12.0, "med": 7.0, "high": 4.0}
HOOK = 1.5
GAP = 0.8                 # speaker time kept between two B-roll shots
JOIN_PRE, JOIN_POST = 0.6, 0.9
STOP = set("""a an the and or but so if then than that this these those there here is are was were be been being am
i me my we our you your he she it its they them their his her of to in on at by for with from as into about over
under up down out off again just very really also too not no yes do does did done have has had will would can could
should may might must shall what which who whom whose when where why how all any both each few more most other some
such only own same one two three first second third thing things get got make made like know think going want um uh
okay ok well right now let lets follow more""".split())


def stem(w):
    w = re.sub(r"[^a-z0-9]", "", w.lower().replace("'s", ""))
    for suf, rep, n in (("ies", "y", 5), ("ing", "", 6), ("ed", "", 5), ("es", "", 5), ("s", "", 4)):
        if w.endswith(suf) and len(w) >= n:
            return w[: -len(suf)] + rep
    return w


def keywords(path):
    name = os.path.splitext(os.path.basename(path))[0]
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    toks = re.split(r"[^A-Za-z0-9]+", name)
    side = os.path.splitext(path)[0] + ".txt"
    if os.path.exists(side):
        toks += re.split(r"[^A-Za-z0-9]+", open(side, encoding="utf-8").read())
    return {stem(t) for t in toks if len(t) > 2 and not t.isdigit() and t.lower() not in STOP}


def library(paths):
    files = []
    for p in paths:
        files += [f for f in glob.glob(os.path.join(p, "*")) if f.lower().endswith(VID + IMG)] if os.path.isdir(p) else [p]
    items = []
    for f in sorted(set(files)):
        kw = keywords(f)
        img = f.lower().endswith(IMG)
        items.append({"src": os.path.abspath(f), "kw": kw, "image": img,
                      "dur": None if img else probe(f)["duration"], "used": 0})
    if not items:
        die("no B-roll clips or images found in the library")
    return items


def jump_cuts(work):
    p = os.path.join(work, "cutlist.json")
    if not os.path.exists(p):
        return []
    segs = load_json(p)["segments"]
    if load_json(p).get("kind") == "timeline":  # different clips are real cuts, same clip with a gap is a jump cut
        return [b["out_start"] for a, b in zip(segs, segs[1:])
                if a["src"] == b["src"] and abs(b["src_start"] - a["src_end"]) > 0.05 and not b.get("transition_dur")]
    return [s["out_start"] for s in segs if s["out_start"] > 0.05]


def hit(st, kws):
    """Exact stem, or one a prefix of the other ("grow" ~ "growth")."""
    return st in kws or (len(st) >= 4 and any(len(k) >= 4 and (k.startswith(st) or st.startswith(k)) for k in kws))


def matches(words, items, t, span=(-1.0, 2.0)):
    """Best item for what is said around time t -> (score, item, word)."""
    best = (0.0, None, None)
    near = [w for w in words if span[0] <= w["start"] - t <= span[1]]
    for it in items:
        hits = [w for w in near if stem(w["w"]) not in STOP and hit(stem(w["w"]), it["kw"])]
        if hits:
            sc = len({stem(w["w"]) for w in hits}) / (len(it["kw"]) ** 0.5) - 0.3 * it["used"]
            if sc > best[0]:
                best = (sc, it, hits[0])
    return best


def plan_broll(words, items, joins, dur, freq="med", dmin=1.2, dmax=4.0, allow_hook=False):
    taken = []
    hook = 0.0 if allow_hook else HOOK

    def free(s, e):
        return s >= hook and e <= dur - 0.3 and all(e + GAP <= a or s >= b + GAP for a, b, _ in taken)

    def fit(it, s, e):
        if not it["image"] and it["dur"] is not None:
            e = min(e, s + it["dur"])
        return (s, e) if e - s >= dmin else None

    out, uncovered = [], []
    for j in joins:
        sc, it, w = matches(words, items, j, (-3.0, 3.0))
        reason = f"covers jump cut at {j:.2f}s" + (f" ('{w['w']}')" if w else "")
        if it is None and freq != "low":
            it = min(items, key=lambda x: x["used"])
            reason += " (generic: no keyword match)"
        span = None
        for pre in (JOIN_PRE, 0.45, 0.3):   # slide later if the previous B-roll is too close
            s, e = j - pre, min(dur - 0.3, max(j + JOIN_POST, j - pre + dmin))
            cand = fit(it, s, e) if it and e - j >= 0.3 else None
            if cand and free(*cand):
                span = cand; break
        if span:
            taken.append((span[0], span[1], it)); it["used"] += 1
            out.append({"start": round(span[0], 3), "end": round(span[1], 3), "item": it, "reason": reason})
        else:
            uncovered.append(round(j, 3))
    target = max(1, int(dur / SPACING[freq]))
    cands = []
    for w in words:
        if stem(w["w"]) in STOP or len(stem(w["w"])) < 3:
            continue
        sc, it, hw = matches(words, items, w["start"], (0.0, 0.5))
        if it is not None:
            cands.append((sc, w, it))
    for sc, w, it in sorted(cands, key=lambda c: -c[0]):
        if len(out) >= target + len([o for o in out if "jump" in o["reason"]]):
            break
        s = w["start"] - 0.1
        span = fit(it, s, s + min(dmax, max(dmin, 2.5)))
        if span and free(*span) and it["used"] < 2:
            taken.append((span[0], span[1], it)); it["used"] += 1
            out.append({"start": round(span[0], 3), "end": round(span[1], 3), "item": it, "reason": f"says '{w['w']}'"})
    return sorted(out, key=lambda o: o["start"]), uncovered


def to_plan(placements, W, H):
    cutaways, elements, notes = [], [], []
    for p in placements:
        it, d = p["item"], p["end"] - p["start"]
        if it["image"]:
            elements.append({"type": "image", "layer": "front", "image": it["src"], "motion": "kenburns",
                             "start": p["start"], "end": p["end"], "x": W / 2, "y": H / 2, "w": W, "h": H,
                             "anchor": "center", "in": "fade", "out": "fade", "inDur": 0.15, "outDur": 0.15,
                             "style": {"overflow": "hidden"}, "broll": True})
        else:
            cutaways.append({"src": it["src"], "start": p["start"], "end": p["end"],
                             "srcStart": round(max(0.0, (it["dur"] - d) / 2), 3), "broll": True})
        notes.append({"start": p["start"], "end": p["end"], "src": os.path.basename(it["src"]), "reason": p["reason"]})
    return cutaways, elements, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default="work")
    ap.add_argument("--library", nargs="+", required=True)
    ap.add_argument("--frequency", default="med", choices=list(SPACING))
    ap.add_argument("--min", type=float, default=1.2)
    ap.add_argument("--max", type=float, default=4.0)
    ap.add_argument("--allow-hook", action="store_true")
    ap.add_argument("--merge", default=None, help="plan.json to add the B-roll to")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    wj = os.path.join(a.work, "words.json")
    if not os.path.exists(wj):
        die(f"{wj} not found (run autocut.py or timeline.py first)")
    wd = load_json(wj)
    words = wd["words"]
    vid = next((os.path.join(a.work, f) for f in ("cut.mp4", "source.mp4") if os.path.exists(os.path.join(a.work, f))), None)
    dur = wd.get("duration") or (probe(vid)["duration"] if vid else words[-1]["end"])
    if a.merge and os.path.exists(a.merge):
        o = load_json(a.merge)["output"]; W, H = o["width"], o["height"]
    elif vid:
        info = probe(vid); W, H = info["width"], info["height"]
    else:
        W, H = 1080, 1920
    items = library(a.library)
    joins = jump_cuts(a.work)
    placements, uncovered = plan_broll(words, items, joins, dur, a.frequency, a.min, a.max, a.allow_hook)
    cutaways, elements, notes = to_plan(placements, W, H)
    res = {"cutaways": cutaways, "elements": elements, "placements": notes, "uncovered_joins": uncovered}
    out = a.out or os.path.join(a.work, "broll.json")
    save_json(out, res)
    for n in notes:
        print(f"  {n['start']:6.2f}-{n['end']:6.2f}  {n['src']:<28} {n['reason']}")
    if uncovered:
        print(f"  jump cuts left uncovered (add a punch-in zoom or more B-roll): {uncovered}")
    if a.merge:
        plan = load_json(a.merge)
        plan["cutaways"] = [c for c in plan.get("cutaways", []) if not c.get("broll")] + cutaways
        plan["elements"] = elements + [e for e in plan.get("elements", []) if not e.get("broll")]  # behind captions
        save_json(a.merge, plan)
        log(f"merged {len(cutaways)} cutaways + {len(elements)} image elements into {a.merge}")
    else:
        log(f"{len(notes)} B-roll shots -> {out}. Merge with: broll.py ... --merge {os.path.join(a.work, 'plan.json')}"
            " (or copy 'cutaways' and prepend 'elements' in plan.json by hand)")


if __name__ == "__main__":
    main()
