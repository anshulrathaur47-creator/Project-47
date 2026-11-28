#!/usr/bin/env python3
"""Aurora scene recipe (glow-cutout skin): speaker scenes and full-screen pull-quote scenes, alternating per phrase.

  sequence.py PLAN --recipe aurora          (self-check: python recipes/aurora.py)

speaker scene - the gold-glow cut-out over the blurred, darkened shot; a dark caption chip (spoken word gold, the
                key word gold italic serif) and a small dark-glass UI card top-left (tiny gold "02 / 04" kicker +
                the phrase's key word) that lands on the key word.
quote scene   - the speaker hidden: the SAME footage blurred and darkened fills the frame (a cutaway of the source
                under a full-frame picture blur, then a dark tint), the phrase as a big sans line with its key word
                in gold italic serif, a tiny gold kicker above.
The first phrase is always the speaker, then scenes alternate; a phrase shorter than MIN_QUOTE s stays on the speaker.
Scene changes get a soft blur (softCuts) and a whoosh. The persistent top title is the skin's (make_plan --title);
a plain-text title gets its key word wrapped in <i> (gold italic serif), a title with its own markup is left alone.
Key word = the longest of the phrase's last three words, skipping refrains (words heard in 2+ phrases, e.g. "बरगी").
Everything written carries "_seq": true (elements, sfx, cutaways, blurs) and is replaced on a re-run.
"""
import os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sequence import phrases, bare, esc   # noqa: E402
from vs_common import norm, log   # noqa: E402

MIN_QUOTE = 1.2    # s: a quote scene needs time to be read
LEAD = 0.12        # s: a scene starts this long before its first word
BLUR = 40          # box-blur radius of the hidden-speaker background (~ the skin's backdropBlur 36 gaussian)


def key_of(words, idx, refrain):
    cand = [i for i in idx if norm(bare(words[i]["w"])) not in refrain] or idx
    return max(cand[-3:], key=lambda i: (len(bare(words[i]["w"])), i))   # ties go to the later word


def quote_html(words, idx, k):
    return " ".join(f"<i>{esc(bare(words[i]['w']))}</i>" if i == k else esc(bare(words[i]["w"])) for i in idx)


def italic_title(els, refrain):
    """The skin's title carries one gold italic word: wrap the key word of a plain-text title (a user's <i> wins)."""
    for x in els:
        text = str(x.get("text", ""))
        if "gc-title" in str(x.get("className", "")) and text.split() and "<" not in text:
            toks = text.split()
            k = key_of([{"w": t} for t in toks], list(range(len(toks))), refrain)
            b = bare(toks[k])
            toks[k] = toks[k].replace(b, f"<i>{b}</i>", 1)
            x.update(text=" ".join(toks), html=True)


def build(plan, a):
    if not plan.get("source"):
        sys.exit("aurora: the plan has no speaker video (source) - the quote scenes blur that footage")
    W, H = plan["output"]["width"], plan["output"]["height"]
    dur = plan["output"]["duration"]
    words = [w for w in plan["words"] if w.get("w", "").strip()]
    P = phrases(words)
    seen = Counter(key for idx in P for key in {norm(bare(words[i]["w"])) for i in idx})
    refrain = {key for key, c in seen.items() if c > 1}
    els, cuts, sfx, cutaways, blurs = [], [], [], [], []
    prev_quote = True   # so phrase 1 is the speaker
    for n, idx in enumerate(P):
        s = 0.0 if n == 0 else round(words[idx[0]]["start"] - LEAD, 3)
        e = round(words[P[n + 1][0]]["start"] - LEAD, 3) if n + 1 < len(P) else dur
        k = key_of(words, idx, refrain)
        tk = words[k]["start"]
        tag = f"{n + 1:02d} / {len(P):02d}"
        quote = not prev_quote and e - s >= MIN_QUOTE
        if n and quote != prev_quote:   # scene kind changes: soft blur + whoosh
            cuts.append(s)
            sfx.append({"t": round(s - 0.1, 3), "kind": "whoosh-short", "gain": 0.2})
        prev_quote = quote

        if quote:   # ---- full-screen pull quote on the blurred footage, speaker hidden: all scenery (decor) for QC
            cutaways.append({"src": plan["source"], "start": s, "end": e, "srcStart": s, "_seq": True})
            blurs.append({"x": 0, "y": 0, "w": W, "h": H, "start": s, "end": e, "strength": BLUR, "_seq": True})
            els += [
                {"type": "background", "layer": "front", "className": "gc-qbg", "start": s, "end": e},
                {"type": "shape", "kind": "glow", "layer": "front", "className": "gc-qglow", "x": round(W / 2), "y": round(H * 0.46),
                 "w": round(W * 1.1), "h": round(W * 1.1), "start": s, "end": e, "speed": 0.5, "pulseOn": [tk]},
                {"type": "text", "html": True, "className": "gc-kick", "text": esc(tag), "x": round(W / 2), "y": round(H * 0.355),
                 "start": round(s + 0.1, 3), "end": e, "in": {"name": "fade", "dur": 0.5}},
                {"type": "text", "html": True, "className": "gc-pq", "text": quote_html(words, idx, k), "x": round(W / 2),
                 "y": round(H * 0.46), "w": round(W * 0.74), "start": round(s + 0.06, 3), "end": e,   # 0.74 W: clear of the right rail
                 "in": {"name": "maskUp", "dur": 0.6}, "out": "fade"},
            ]
            for x in els[-4:]:
                x["decor"] = True
            sfx.append({"t": round(tk, 3), "kind": "sparkle", "gain": 0.28})
            continue

        # ---- speaker scene: caption chip + a UI card that lands on the key word
        els.append({"type": "captions", "className": "gc-cap", "mode": "karaoke", "maxWords": 3, "maxChars": 20,
                    "uppercase": True, "words": [words[i] for i in idx], "keywords": [bare(words[k]["w"])],
                    "y": round(H * 0.75), "hold": 0.25, "start": s, "end": e})
        c0 = round(min(tk - 0.05, e - 0.8), 3) if e - s > 1.0 else s
        els.append({"type": "text", "html": True, "decor": True, "className": "gc-ui", "anchor": "left",
                    "text": f"<span class='gc-k'>{esc(tag)}</span>{esc(bare(words[k]['w']))}",
                    "x": round(W * 0.07), "y": round(H * 0.19), "start": max(s, c0), "end": e,
                    "in": {"name": "blur", "dur": 0.45}, "out": "fade"})
        sfx.append({"t": round(max(s, c0), 3), "kind": "ui-tap", "gain": 0.22})

    for x in els:
        x["_seq"] = True
    keep = [x for x in plan.get("elements", []) if not x.get("_seq") and x.get("type") != "captions"
            and "gc-card" not in str(x.get("className", ""))]   # the skin's auto key-word cards: replaced by the UI cards
    italic_title(keep, refrain)
    plan["elements"] = keep + els
    plan["cutaways"] = [x for x in plan.get("cutaways", []) if not x.get("_seq")] + cutaways
    plan["blurs"] = [x for x in plan.get("blurs", []) if not x.get("_seq")] + blurs
    plan["softCuts"] = [{"at": c, "dur": 0.42, "sigma": 22} for c in cuts]
    plan["sfx"] = [x for x in plan.get("sfx", []) if not x.get("_seq")] + [dict(x, _seq=True) for x in sfx]
    log(f"aurora sequence: {len(P)} phrases, {len(cutaways)} quote scenes, {len(cuts)} scene changes, {len(els)} elements")
    return plan


if __name__ == "__main__":   # self-check on the skin-test shayari timings (refrain "बरगी" must not become the key word)
    T = [("हर", 0.0, .28), ("बात", .3, .72), ("तीरा", .76, 1.31), ("बरगी,", 1.36, 2.06), ("राशि", 2.7, 3.19), ("है", 3.23, 3.47),
         ("फकीरा", 3.5, 4.11), ("बरगी,", 4.16, 4.77), ("एक", 5.14, 5.35), ("ए", 5.37, 5.47), ("छोरी", 5.48, 5.9), ("लाइफ", 5.93, 6.35),
         ("में", 6.39, 6.7), ("भाई,", 6.73, 7.14), ("वा", 7.5, 7.66), ("भी", 7.68, 7.84), ("जमा", 7.86, 8.1), ("हीरा", 8.12, 8.45),
         ("बरगी,", 8.48, 8.88)]
    plan = {"output": {"width": 1080, "height": 1920, "duration": 9.7}, "source": "cut.mp4", "speaker": {},
            "words": [{"w": w, "start": s, "end": e} for w, s, e in T],
            "elements": [{"type": "text", "className": "gc-title", "text": "हर बात तीरा बरगी,"}, {"type": "captions"},
                         {"type": "chip", "className": "gc-card"}]}
    plan = build(plan, None)
    n1 = len(plan["elements"])
    pq = [x["text"] for x in plan["elements"] if x.get("className") == "gc-pq"]
    ui = [x["text"].split("</span>")[1] for x in plan["elements"] if x.get("className") == "gc-ui"]
    assert ui == ["तीरा", "लाइफ"], ui                                   # speaker scenes 1 and 3
    assert pq == ["राशि है <i>फकीरा</i> बरगी", "वा भी जमा <i>हीरा</i> बरगी"], pq   # quote scenes 2 and 4
    assert [c["start"] for c in plan["cutaways"]] == [2.58, 7.38] and len(plan["blurs"]) == 2
    assert [c["at"] for c in plan["softCuts"]] == [2.58, 5.02, 7.38]
    assert not any(x.get("className") == "gc-card" for x in plan["elements"])
    assert all(x.get("_seq") for x in plan["elements"][1:]) and plan["elements"][0]["className"] == "gc-title"
    assert plan["elements"][0]["text"] == "हर बात <i>तीरा</i> बरगी," and plan["elements"][0]["html"]
    plan = build(plan, None)                                            # re-run replaces, never stacks
    assert plan["elements"][0]["text"] == "हर बात <i>तीरा</i> बरगी,"     # a title that has its <i> is left alone
    assert len(plan["elements"]) == n1 and len(plan["cutaways"]) == 2 and len(plan["sfx"]) == len({(x["t"], x["kind"]) for x in plan["sfx"]})
    print("aurora self-check ok")
