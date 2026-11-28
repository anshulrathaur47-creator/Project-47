#!/usr/bin/env python3
"""Scene sequencer: turns a draft plan into a designed edit that changes scene every phrase.

  sequence.py PLAN --recipe ribbon [--out PLAN] [--split 0.55]

Each phrase (sentence, or comma + pause) becomes two scenes:
  person scene  - the speaker cut-out with a frosted checklist card, glass icon buttons, a phrase pill and
                  (on the last phrase) the payoff line in big serif;
  type scene    - no speaker: stacked glass note cards, big two-tone type, a search bar typing the next phrase.
The last phrase stays on the speaker. Scene changes get a soft full-frame blur (plan "softCuts") and a whoosh.
The skin (theme.json/theme.css) supplies the backgrounds, ribbon, colours and fonts; this script only writes
timed elements, zooms, softCuts and sfx into the plan. Re-running replaces what it wrote before.
"""
import argparse, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vs_common import load_json, save_json, log  # noqa: E402

TAG = "seq"   # every element this script writes carries "_seq": true so a re-run can replace it


def phrases(words):
    """Group words into phrases: sentence ends, danda, or a comma followed by a pause, or a long gap."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 9
        if re.search(r"[.!?।॥]$", w["w"]) or (w["w"].endswith(",") and gap >= 0.25) or gap > 0.6:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def bare(w):
    return re.sub(r"^[\"'(]+|[\"'),.!?;:।॥]+$", "", w)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def key_index(words, idx):
    """The word that carries the phrase: the longest of the last two (payoff words sit at the end)."""
    tail = idx[-2:] if len(idx) > 1 else idx
    return max(tail, key=lambda i: (len(bare(words[i]["w"])), i))   # ties go to the later word


def ribbon(plan, a):
    W, H = plan["output"]["width"], plan["output"]["height"]
    words = [w for w in plan["words"] if w.get("w", "").strip()]
    dur = plan["output"]["duration"]
    P = phrases(words)
    els, zooms, cuts, sfx = [], [], [], []
    for n, idx in enumerate(P):
        s = 0.0 if n == 0 else round(words[idx[0]]["start"] - 0.12, 3)
        e = round(words[P[n + 1][0]]["start"] - 0.12, 3) if n + 1 < len(P) else dur
        last = n == len(P) - 1
        k = key_index(words, idx)
        # split point: snap ~55% of the phrase to a word start (never before the 2nd word)
        target = s + (e - s) * a.split
        cands = [i for i in idx[1:] if words[i]["start"] >= s + 0.6] or idx[-1:]
        m_i = min(cands, key=lambda i: abs(words[i]["start"] - target))
        m = round(words[m_i]["start"] - 0.06, 3)
        p_end = e if last else m
        text = [bare(words[i]["w"]) for i in idx]
        key = bare(words[k]["w"])

        # ---- person scene [s, p_end)
        if n % 2:
            zooms.append({"start": s, "end": p_end, "scale": 1.16, "snap": True})
        others = [i for i in idx if i != k][:3]
        lead = " ".join([bare(words[i]["w"]) for i in idx if i != k][:2])
        els.append({"type": "checklist", "_seq": True, "className": "gr-glass gr-check", "html": True,
                    "title": f"{esc(lead)}<br><em>{esc(key)}</em>",
                    "items": [{"text": bare(words[i]["w"]), "at": words[i]["start"]} for i in others],
                    "x": round(W * 0.27), "y": round(H * 0.17), "w": round(W * 0.42),
                    "start": s, "end": p_end, "in": {"name": "springPop", "dur": 0.55}, "out": "fade",
                    "keys": {"r": [[0, -2]]}})
        for j, (ic, x, y) in enumerate([("↗", 0.86, 0.12), ("◎", 0.86, 0.27), ("✓", 0.12, 0.55)]):
            els.append({"type": "chip", "_seq": True, "decor": True, "text": ic, "className": "gr-icon", "x": round(W * x), "y": round(H * y),
                        "start": round(s + 0.12 + j * 0.08, 3), "end": p_end, "in": "springPop", "out": "fade"})
        els.append({"type": "captions", "_seq": True, "className": "gr-pill", "mode": "static", "maxWords": 4, "maxChars": 26,
                    "words": [words[i] for i in idx if words[i]["start"] < p_end], "y": round(H * 0.745),
                    "groupIn": {"name": "springPop", "dur": 0.4}, "hold": 0.2, "start": s, "end": p_end})
        if last:
            pay = " ".join(text[-2:]) if len(text) > 1 else text[0]
            els.append({"type": "text", "_seq": True, "html": True, "className": "gr-pay",
                        "text": f"<em>{esc(pay)}</em>", "x": round(W / 2), "y": round(H * 0.82), "w": round(W * 0.74),
                        "start": round(words[idx[-2 if len(idx) > 1 else -1]]["start"] - 0.05, 3), "end": dur + 1,
                        "in": {"name": "maskUp", "dur": 0.5}, "fit": True})
            sfx.append({"t": words[k]["start"], "kind": "sparkle", "gain": 0.35})
        if last:
            continue

        # ---- type scene [m, e): a full-screen scene of its own, so its parts are scenery for QC (decor)
        n_before = len(els)
        cuts.append(m)
        sfx.append({"t": round(m - 0.12, 3), "kind": "whoosh-short", "gain": 0.22})
        els.append({"type": "background", "_seq": True, "layer": "front", "className": "gr-tbg", "start": m, "end": e})
        els.append({"type": "shape", "_seq": True, "kind": "bubbles", "layer": "front", "className": "gr-orbs gr-orbs-big",
                    "count": 7, "x": round(W / 2), "y": round(H / 2), "w": W, "h": H, "speed": 0.2, "start": m, "end": e, "in": "none"})
        els.append({"type": "shape", "_seq": True, "kind": "ribbon", "layer": "front", "className": "gr-thread",
                    "x": round(W / 2), "y": round(H * 0.44), "w": round(W * 1.2), "h": round(H * 0.5), "thickness": 7,
                    "color": "#FFFFFF", "color2": "#B98CFF", "speed": 0.9, "start": m, "end": e, "in": "none",
                    "keys": {"r": [[0, 74]]}})
        if n > 0:   # the previous phrase as a card above
            prev = [bare(words[i]["w"]) for i in P[n - 1]]
            els.append({"type": "text", "_seq": True, "html": True, "className": "gr-note",
                        "text": f"{esc(' '.join(prev[-2:]))}<span class='gr-dots'>…</span>",
                        "x": round(W * 0.58), "y": round(H * 0.3), "start": m, "end": e, "in": "none", "keys": {"r": [[0, 4]]}})
        els.append({"type": "text", "_seq": True, "html": True, "className": "gr-note",
                    "text": f"{esc(' '.join(text[-2:]))}<span class='gr-dots'>…</span>",
                    "x": round(W * 0.4), "y": round(H * 0.47), "start": round(m + 0.05, 3), "end": e,
                    "in": {"name": "springPop", "dur": 0.5}, "keys": {"r": [[0, -3]]}})
        sfx.append({"t": round(m + 0.08, 3), "kind": "pop", "gain": 0.25})
        head = " ".join(text[:-1]) if len(text) > 1 else ""
        els.append({"type": "text", "_seq": True, "className": "gr-tpill", "text": head or text[0],
                    "x": round(W / 2), "y": round(H * 0.64), "start": round(m + 0.1, 3), "end": e, "in": "springPop"})
        els.append({"type": "text", "_seq": True, "html": True, "className": "gr-big",
                    "text": f"{esc(' '.join(text[-2:-1]))} <em>{esc(key if k == idx[-1] else text[-1])}</em>".strip(),
                    "x": round(W / 2), "y": round(H * 0.72), "w": round(W * 0.74), "fit": True,
                    "start": round(m + 0.15, 3), "end": e, "in": {"name": "maskUp", "dur": 0.45}})
        nxt = " ".join(bare(words[i]["w"]) for i in P[n + 1])
        els.append({"type": "searchbar", "_seq": True, "className": "gr-search", "query": nxt, "cps": 16, "delay": 0.25,
                    "x": round(W / 2), "y": round(H * 0.79), "w": round(W * 0.72), "start": round(m + 0.2, 3), "end": e, "in": "rise"})
        for x in els[n_before:]:
            x["decor"] = True
        cuts.append(e)
        sfx.append({"t": round(e - 0.12, 3), "kind": "whoosh-short", "gain": 0.18})

    plan["elements"] = [x for x in plan.get("elements", []) if not x.get("_seq") and x.get("type") != "captions"] + els
    plan["speaker"]["zooms"] = [z for z in plan["speaker"].get("zooms", []) if not z.get("_seq")] + [dict(z, _seq=True) for z in zooms]
    plan["softCuts"] = [{"at": c, "dur": 0.34, "sigma": 20} for c in cuts]
    plan["sfx"] = [x for x in plan.get("sfx", []) if not x.get("_seq")] + [dict(x, _seq=True) for x in sfx]
    log(f"ribbon sequence: {len(P)} phrases, {len(cuts)} scene changes, {len(els)} elements")
    return plan


RECIPES = {"ribbon": ribbon}


def _load_recipes():
    """Plug-in recipes: scripts/recipes/<name>.py exposing build(plan, args) -> plan."""
    import importlib.util, glob
    for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "recipes", "*.py"))):
        name = os.path.splitext(os.path.basename(f))[0]
        if name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"recipe_{name}", f)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        RECIPES[name] = mod.build


_load_recipes()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--recipe", default="ribbon", choices=sorted(RECIPES))
    ap.add_argument("--split", type=float, default=0.55, help="where in each phrase the type scene takes over (0..1)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    plan = load_json(a.plan)
    if not plan.get("words"):
        sys.exit("sequence.py: the plan has no words (transcribe first)")
    save_json(a.out or a.plan, RECIPES[a.recipe](plan, a))


if __name__ == "__main__":
    main()
