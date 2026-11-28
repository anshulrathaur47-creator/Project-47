#!/usr/bin/env python3
"""Retro scene recipe (poster-pop skin): a new poster scene on every phrase, pattern interstitials every 2-3 phrases.

  sequence.py PLAN --recipe retro          (self-check: python recipes/retro.py)

speaker scene - the cut-out on the next backdrop of the cycle (royal blue, green graph paper, black, cream paper, red
                glow, checkerboard, stripes); the phrase's key word as a chunky slab headline at the top, partly behind
                the head, stamped in on the cut; a small italic tag under it (scene number - replace it with your own
                line, e.g. the English meaning) and small uppercase karaoke captions at the bottom.
interstitial  - every 2-3 phrases the tail of the phrase (from its key word on) goes full screen WITHOUT the speaker:
                a loud pattern (stripes, sunburst, checkerboard), the words being said as a big stacked headline (key
                word orange) and the words said just before as a small italic kicker. Never on the last phrase.
Hard cuts: every scene change gets a quick cream flash and a projector click; an interstitial lands with an impact.
Key word = the longest of the phrase's last three words, skipping refrains (words heard in 2+ phrases, e.g. "बरगी").
Everything written carries "_seq": true and is replaced on a re-run. The skin's own per-sentence backdrops and
headlines (pp-bg / pp-head, from make_plan) and the captions are dropped: these scenes replace them.
"""
import os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sequence import phrases, bare, esc   # noqa: E402
from vs_common import norm, log   # noqa: E402

LEAD = 0.12          # s: a scene starts this long before its first word
MIN_INTER = 0.8      # s: an interstitial needs time to be read
MIN_SPEAKER = 0.75   # s: speaker time before an interstitial (its tag must stay >= 0.6 s for qc)
INTER_AT = (1, 3)    # phrases with n % 5 in INTER_AT get an interstitial: every 2, then every 3 phrases
# speaker backdrop cycle: (pattern class, headline colour class: "" cream, "alt" orange, "red")
SCENES = [("pp-blue", ""), ("pp-grid", "alt"), ("pp-black", "alt"), ("pp-paper", "red"), ("pp-red", ""),
          ("pp-checker", ""), ("pp-stripes", "")]
INTERS = ["pp-stripes", "pp-sun", "pp-checker"]
HEAD_Y, TAG_Y, CAP_Y = 0.15, 0.235, 0.8   # fractions of H: headline (its foot behind the hair), italic tag, captions


def key_of(words, idx, refrain):
    cand = [i for i in idx if norm(bare(words[i]["w"])) not in refrain] or idx
    return max(cand[-3:], key=lambda i: (len(bare(words[i]["w"])), i))   # ties go to the later word


def stacked(words, tail, k):
    """The interstitial headline: one word per line (two when the tail is long), the key word in <em> (orange)."""
    per = 1 if len(tail) <= 3 else 2
    word = lambda i: f"<em>{esc(bare(words[i]['w']))}</em>" if i == k else esc(bare(words[i]["w"]))
    return "<br>".join(" ".join(word(i) for i in tail[j:j + per]) for j in range(0, len(tail), per))


def build(plan, a):
    if plan.get("source") and not plan.get("matte"):
        sys.exit("retro: the speaker scenes put the cut-out on poster backdrops - make the matte first (matte.py)")
    W, H = plan["output"]["width"], plan["output"]["height"]
    dur = plan["output"]["duration"]
    words = [w for w in plan["words"] if w.get("w", "").strip()]
    P = phrases(words)
    seen = Counter(key for idx in P for key in {norm(bare(words[i]["w"])) for i in idx})
    refrain = {key for key, c in seen.items() if c > 1}
    els, zooms, sfx, cuts = [], [], [], []
    n_inter = 0
    for n, idx in enumerate(P):
        s = 0.0 if n == 0 else round(words[idx[0]]["start"] - LEAD, 3)
        e = round(words[P[n + 1][0]]["start"] - LEAD, 3) if n + 1 < len(P) else dur
        k = key_of(words, idx, refrain)
        m = round(words[k]["start"] - 0.06, 3)
        inter = (n + 1 < len(P) and n % 5 in INTER_AT and k != idx[0]
                 and m - s >= MIN_SPEAKER and e - m >= MIN_INTER)
        p_end = m if inter else e
        sp = [i for i in idx if words[i]["start"] < p_end]   # the words said on camera
        pat, tone = SCENES[n % len(SCENES)]
        if n:
            cuts.append(s)

        # ---- speaker scene [s, p_end): backdrop + headline behind the person, tag + captions in front
        if n % 2:
            zooms.append({"start": s, "end": p_end, "scale": 1.08, "snap": True})
        els += [
            {"type": "background", "layer": "behind", "decor": True, "className": f"pp-bg {pat}", "start": s, "end": p_end},
            {"type": "headline", "layer": "behind", "className": f"pp-head {tone}".strip(),
             "text": bare(words[key_of(words, sp, refrain)]["w"]), "x": round(W / 2), "y": round(H * HEAD_Y),
             "w": round(W * 0.74), "start": s, "end": p_end, "in": {"name": "stamp", "dur": 0.3}},
            {"type": "text", "className": "pp-tag", "text": f"— {n + 1:02d} / {len(P):02d} —", "x": round(W / 2),
             "y": round(H * TAG_Y), "start": round(s + 0.12, 3), "end": p_end, "in": {"name": "rise", "dur": 0.3},
             "keys": {"r": [[0, -2]]}},
            {"type": "captions", "className": "pp-cap", "mode": "karaoke", "maxWords": 3, "maxChars": 18,
             "uppercase": True, "words": [words[i] for i in sp], "y": round(H * CAP_Y), "hold": 0.2, "start": s, "end": p_end},
        ]
        if not inter:
            continue

        # ---- interstitial [m, e): full-screen pattern, no speaker - all scenery (decor) for QC
        nxt = SCENES[(n + 1) % len(SCENES)][0]
        ip = next(x for j in range(len(INTERS)) for x in [INTERS[(n_inter + j) % len(INTERS)]] if x not in (pat, nxt))
        n_inter += 1
        cuts.append(m)
        tail = [i for i in idx if words[i]["start"] >= p_end]
        inter_els = [
            {"type": "background", "layer": "front", "className": f"pp-bg {ip}", "start": m, "end": e},
            {"type": "text", "className": "pp-tag", "text": " ".join(bare(words[i]["w"]) for i in sp) + " …",
             "x": round(W / 2), "y": round(H * 0.33), "start": round(m + 0.1, 3), "end": e,
             "in": {"name": "rise", "dur": 0.3}, "keys": {"r": [[0, 2]]}},
            {"type": "headline", "layer": "front", "html": True, "className": "pp-big", "text": stacked(words, tail, k),
             "x": round(W / 2), "y": round(H * 0.37), "anchor": "top", "w": round(W * 0.74), "start": m, "end": e,
             "in": {"name": "stamp", "dur": 0.32}, "keys": {"r": [[0, -3]]}},
        ]
        for x in inter_els:
            x["decor"] = True
        els += inter_els
        sfx.append({"t": round(m + 0.02, 3), "kind": "impact", "gain": 0.3})

    if cuts:
        els.append({"type": "flash", "decor": True, "times": cuts, "color": "#FFF1D6", "opacity": 0.7, "dur": 0.1})
        sfx += [{"t": round(c - 0.02, 3), "kind": "click", "gain": 0.35} for c in cuts]
    for x in els:
        x["_seq"] = True
    keep = [x for x in plan.get("elements", []) if not x.get("_seq") and x.get("type") != "captions"
            and not any(c in str(x.get("className", "")).split() for c in ("pp-bg", "pp-head"))]
    plan["elements"] = keep + els
    spk = plan.setdefault("speaker", {})
    spk["zooms"] = [z for z in spk.get("zooms", []) if not z.get("_seq")] + [dict(z, _seq=True) for z in zooms]
    plan["softCuts"] = []   # hard cuts only (drops another recipe's blur transitions)
    plan["sfx"] = [x for x in plan.get("sfx", []) if not x.get("_seq")] + [dict(x, _seq=True) for x in sfx]
    log(f"retro sequence: {len(P)} phrases, {n_inter} interstitials, {len(cuts)} hard cuts, {len(els)} elements")
    return plan


if __name__ == "__main__":   # self-check on the skin-test shayari timings (refrain "बरगी" must never be a headline)
    T = [("हर", 0.0, .28), ("बात", .3, .72), ("तीरा", .76, 1.31), ("बरगी,", 1.36, 2.06), ("राशि", 2.7, 3.19), ("है", 3.23, 3.47),
         ("फकीरा", 3.5, 4.11), ("बरगी,", 4.16, 4.77), ("एक", 5.14, 5.35), ("ए", 5.37, 5.47), ("छोरी", 5.48, 5.9), ("लाइफ", 5.93, 6.35),
         ("में", 6.39, 6.7), ("भाई,", 6.73, 7.14), ("वा", 7.5, 7.66), ("भी", 7.68, 7.84), ("जमा", 7.86, 8.1), ("हीरा", 8.12, 8.45),
         ("बरगी,", 8.48, 8.88)]
    plan = {"output": {"width": 1080, "height": 1920, "duration": 9.7}, "source": "cut.mp4", "matte": "matte.mp4", "speaker": {},
            "words": [{"w": w, "start": s, "end": e} for w, s, e in T], "softCuts": [{"at": 1, "dur": .3, "sigma": 20}],
            "elements": [{"type": "text", "className": "mine", "text": "keep me"}, {"type": "captions"},
                         {"type": "background", "className": "pp-bg pp-stripes"}, {"type": "headline", "className": "pp-head alt"}]}
    plan = build(plan, None)
    E = plan["elements"]
    n1, s1 = len(E), len(plan["sfx"])
    bgs = [(x["className"], x["start"], x["end"]) for x in E if x["type"] == "background"]
    assert [b[0] for b in bgs] == ["pp-bg pp-blue", "pp-bg pp-grid", "pp-bg pp-stripes", "pp-bg pp-black", "pp-bg pp-paper"], bgs
    assert bgs[2][1:] == (3.44, 5.02) and bgs[-1][2] == 9.7, bgs            # interstitial from फकीरा; last scene to the end
    heads = [x["text"] for x in E if x.get("className", "").startswith("pp-head")]
    assert heads == ["तीरा", "राशि", "लाइफ", "हीरा"], heads                   # never the refrain बरगी
    big = [x["text"] for x in E if x.get("className") == "pp-big"]
    assert big == ["<em>फकीरा</em><br>बरगी"], big
    caps = [[w["w"] for w in x["words"]] for x in E if x["type"] == "captions"]
    assert caps[1] == ["राशि", "है"] and len(caps) == 4, caps               # no captions on the interstitial
    assert [x["times"] for x in E if x["type"] == "flash"] == [[2.58, 3.44, 5.02, 7.38]]
    assert E[0]["className"] == "mine" and all(x.get("_seq") for x in E[1:]) and plan["softCuts"] == []
    assert all(x.get("decor") for x in E if x.get("className") in ("pp-big", "pp-bg pp-stripes"))
    tags = [(x["start"], x["end"]) for x in E if x.get("className") == "pp-tag"]
    assert all(e - s >= 0.6 for s, e in tags), tags                         # qc overlay_min_duration
    assert [z["start"] for z in plan["speaker"]["zooms"]] == [2.58, 7.38]
    plan = build(plan, None)                                                # re-run replaces, never stacks
    assert len(plan["elements"]) == n1 and len(plan["sfx"]) == s1 and len(plan["speaker"]["zooms"]) == 2
    print("retro self-check ok")
