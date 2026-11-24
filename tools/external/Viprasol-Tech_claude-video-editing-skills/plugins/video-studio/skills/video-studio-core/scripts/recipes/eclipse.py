#!/usr/bin/env python3
"""Eclipse scene recipe (neon-marquee skin): the real shot, full frame, cut into wide and tight shots per phrase.

  sequence.py PLAN --recipe eclipse          (self-check: python recipes/eclipse.py)

Every phrase is one shot; shots alternate and the last phrase is always a tight shot (the payoff):
  wide shot  - the plain frame; the caption chip runs until the key word, then a lime label bar slides in from the
               left with the key phrase (key word to the end of the phrase, at most LABEL_MAX words) and holds.
  tight shot - a close-up (CLOSE) that snaps to an extreme close-up (ECU) on the key word until the next word (the
               last phrase holds the ECU to the end); the caption chip drops below the chin while the ECU is on.
A dark shade (skin class nm-shade) sits over the whole shot. Over every shot a giant glowing blue marquee of the phrase's key words scrolls sideways at the top (direction
alternates). Shot changes get a heavy out-of-focus blur (softCuts) and a whoosh; zoom edges sit between frames.
Key word = the longest of the phrase's last three words, skipping refrains (words heard in 2+ phrases, e.g. "बरगी").
Everything written carries "_seq": true and is replaced on a re-run. The skin's auto captions, marquee headlines and
labels are dropped, and so are older zooms that overlap the new framing (zooms add up in render.py).
"""
import math, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sequence import phrases, bare   # noqa: E402
from vs_common import norm, log   # noqa: E402

LEAD = 0.12              # s: a shot starts this long before its first word
CLOSE, ECU = 1.3, 1.6    # tight-shot framings (scale of the full frame)
EYE = {CLOSE: 0.36, ECU: 0.34}   # where the eye line lands (fraction of H): rule of thirds, chin clear of the chip
ECU_MIN = 0.5            # s: shortest extreme close-up
MARQ_SPEED = 240         # px/s the marquee travels
MARQ_Y, LABEL_Y, CHIP_Y, ECU_CHIP_Y = 0.14, 0.775, 0.785, 0.845   # fractions of H
LABEL_MAX = 4            # words on the lime label
AUTO = {"nm-marq", "nm-label"}   # the skin's auto elements (make_plan) this recipe replaces


def key_of(words, idx, refrain):
    cand = [i for i in idx if norm(bare(words[i]["w"])) not in refrain] or idx
    return max(cand[-3:], key=lambda i: (len(bare(words[i]["w"])), i))   # ties go to the later word


def marquee_text(words, idx, refrain, k):
    """The key word plus the phrase's next-longest non-refrain word, in spoken order."""
    rest = [i for i in idx if i != k and norm(bare(words[i]["w"])) not in refrain]
    pick = sorted([k] + sorted(rest, key=lambda i: (len(bare(words[i]["w"])), i))[-1:])
    return " ".join(bare(words[i]["w"]) for i in pick)


def aim(track, t0, t1, z):
    """(cx, cy) of a punch-in from the face track (median over the window): the eye line lands at EYE[z].
    render.py aims centred on the eyes, which pushes a selfie's chin under the caption chip."""
    fs = [f for f in track if t0 <= f["t"] <= t1] or [min(track, key=lambda f: abs(f["t"] - (t0 + t1) / 2))]
    med = lambda v: sorted(v)[len(v) // 2]
    eyes = med([f["y"] + 0.25 * f["h"] for f in fs])   # ponytail: eye line at 1/4 of the detector box, tune if a tracker differs
    return round(med([f["x"] + f["w"] / 2 for f in fs]), 4), round(eyes + (0.5 - EYE[z]) / z + 0.06, 4)   # +0.06: render lifts cy


def build(plan, a):
    if not plan.get("source") or plan.get("speaker", {}).get("mode", "full") == "none":
        sys.exit("eclipse: the plan has no speaker video (source) - every shot is the real footage")
    W, H = plan["output"]["width"], plan["output"]["height"]
    dur, fps = plan["output"]["duration"], plan["output"].get("fps", 30)
    fb = lambda t: round((math.ceil(round(t * fps, 6)) - 0.5) / fps, 4)   # zoom edge just before the first frame >= t
    words = [w for w in plan["words"] if w.get("w", "").strip()]
    P = phrases(words)
    seen = Counter(key for idx in P for key in {norm(bare(words[i]["w"])) for i in idx})
    refrain = {key for key, c in seen.items() if c > 1}
    # dark moody shade over the whole shot: top band for the neon glow, bottom band for the chips, edge vignette
    els, zooms, cuts, sfx = [{"type": "background", "layer": "front", "className": "nm-shade", "decor": True,
                              "start": 0, "end": dur + 1}], [], [], []
    for n, idx in enumerate(P):
        s = 0.0 if n == 0 else round(words[idx[0]]["start"] - LEAD, 3)
        e = round(words[P[n + 1][0]]["start"] - LEAD, 3) if n + 1 < len(P) else dur
        last, tight = n == len(P) - 1, (len(P) - 1 - n) % 2 == 0
        k = key_of(words, idx, refrain)
        key = bare(words[k]["w"])
        if n:   # shot change under a heavy blur
            cuts.append(s)
            sfx.append({"t": round(s - 0.12, 3), "kind": "whoosh-short", "gain": 0.22})
        mq = marquee_text(words, idx, refrain, k)
        go = (1 if n % 2 == 0 else -1) * MARQ_SPEED * (e - s) / 2
        els.append({"type": "headline", "className": "nm-marq", "decor": True, "text": " · ".join([mq] * 4),
                    "uppercase": True, "fit": False, "x": round(W / 2), "y": round(H * MARQ_Y), "start": s, "end": e,
                    "in": {"name": "blurIn", "dur": 0.3}, "keys": {"tx": [[0, round(go)], [round(e - s, 3), round(-go), "linear"]]}})
        cap = {"type": "captions", "className": "nm-cap", "mode": "karaoke", "maxWords": 3, "maxChars": 18,
               "words": [words[i] for i in idx], "keywords": [key], "y": round(H * CHIP_Y), "hold": 0.2,
               "start": s, "end": e}

        if tight:   # close-up, ECU on the key word
            e0 = fb(words[k]["start"] - 0.05)
            nxt = words[k + 1]["start"] if k < idx[-1] and not last else e
            e1 = fb(min(e, max(nxt, words[k]["start"] + ECU_MIN)))
            b0, b1 = fb(s) if n else -0.5 / fps, fb(e)
            zooms += [z for z in ({"start": b0, "end": e0, "scale": CLOSE}, {"start": e0, "end": e1, "scale": ECU},
                                  {"start": e1, "end": b1, "scale": CLOSE}) if z["end"] - z["start"] > 0.02]
            cap["dodge"] = [{"start": e0, "end": e1, "y": ECU_CHIP_Y}]
            els.append(cap)
            sfx.append({"t": round(words[k]["start"] - 0.05, 3), "kind": "impact", "gain": 0.22})
            continue

        # wide shot: the chip hands over to the lime label at the key phrase
        pos = max(idx.index(k), len(idx) - LABEL_MAX)
        t_l = round(max(s + 0.05, words[idx[pos]]["start"] - 0.08), 3)
        if pos:
            els.append(dict(cap, words=[words[i] for i in idx[:pos]], end=t_l))
        els.append({"type": "chip", "className": "nm-label", "text": " ".join(bare(words[i]["w"]) for i in idx[pos:]),
                    "uppercase": True, "anchor": "left", "x": round(W * 0.07), "y": round(H * LABEL_Y), "start": t_l, "end": e,
                    "in": {"name": "push", "dir": "right", "dist": round(W * 0.9), "dur": 0.45, "ease": "expoOut"}})
        sfx.append({"t": t_l, "kind": "swish", "gain": 0.2})

    for x in els:
        x["_seq"] = True
    for z in zooms if plan.get("track") else []:
        z["cx"], z["cy"] = aim(plan["track"], z["start"], z["end"], z["scale"])
    mine = [dict(z, _seq=True) for z in zooms]
    old = [z for z in plan["speaker"].get("zooms", []) if not z.get("_seq")]
    kept = [z for z in old if not any(z["start"] < m["end"] and m["start"] < z["end"] for m in mine)]
    plan["elements"] = [x for x in plan.get("elements", []) if not x.get("_seq") and x.get("type") != "captions"
                        and not AUTO & set(str(x.get("className", "")).split())] + els
    plan["speaker"]["zooms"] = kept + mine
    plan["softCuts"] = [c for c in plan.get("softCuts", []) if not c.get("_seq")] + \
        [{"at": c, "dur": 0.5, "sigma": 40, "_seq": True} for c in cuts]
    plan["sfx"] = [x for x in plan.get("sfx", []) if not x.get("_seq")] + [dict(x, _seq=True) for x in sfx]
    log(f"eclipse sequence: {len(P)} shots, {len(mine)} framing zooms ({len(old) - len(kept)} older dropped), "
        f"{len(cuts)} blur cuts, {len(els)} elements")
    return plan


if __name__ == "__main__":   # self-check on the skin-test shayari timings (refrain "बरगी" must not become the key word)
    T = [("हर", 0.0, .28), ("बात", .3, .72), ("तीरा", .76, 1.31), ("बरगी,", 1.36, 2.06), ("राशि", 2.7, 3.19), ("है", 3.23, 3.47),
         ("फकीरा", 3.5, 4.11), ("बरगी,", 4.16, 4.77), ("एक", 5.14, 5.35), ("ए", 5.37, 5.47), ("छोरी", 5.48, 5.9), ("लाइफ", 5.93, 6.35),
         ("में", 6.39, 6.7), ("भाई,", 6.73, 7.14), ("वा", 7.5, 7.66), ("भी", 7.68, 7.84), ("जमा", 7.86, 8.1), ("हीरा", 8.12, 8.45),
         ("बरगी,", 8.48, 8.88)]
    plan = {"output": {"width": 1080, "height": 1920, "duration": 9.7, "fps": 30}, "source": "cut.mp4",
            "speaker": {"zooms": [{"start": 3.0, "end": 3.9, "scale": 1.12}, {"start": 0.1, "end": 0.3, "scale": 1.1}]},
            "track": [{"t": t / 10, "x": 0.2, "y": 0.26, "w": 0.6, "h": 0.4} for t in range(98)],
            "words": [{"w": w, "start": s, "end": e} for w, s, e in T],
            "elements": [{"type": "captions"}, {"type": "headline", "className": "nm-marq"}, {"type": "chip", "className": "nm-label"},
                         {"type": "text", "className": "mine", "text": "keep me"}]}
    plan = build(plan, None)
    E = plan["elements"]
    by = lambda c: [x for x in E if x.get("className") == c]
    assert [x["text"].split(" · ")[0] for x in by("nm-marq")] == ["बात तीरा", "राशि फकीरा", "छोरी लाइफ", "जमा हीरा"]
    assert all(x["decor"] and x["text"].count(" · ") == 3 for x in by("nm-marq"))
    assert [x["text"] for x in by("nm-label")] == ["तीरा बरगी", "लाइफ में भाई"]            # wide shots 1 and 3
    caps = by("nm-cap")
    assert [" ".join(w["w"] for w in c["words"]) for c in caps] == ["हर बात", "राशि है फकीरा बरगी,", "एक ए छोरी", "वा भी जमा हीरा बरगी,"]
    assert caps[0]["end"] == by("nm-label")[0]["start"] == 0.68 and caps[1]["keywords"] == ["फकीरा"]
    Z = sorted((z for z in plan["speaker"]["zooms"] if z.get("_seq")), key=lambda z: z["start"])
    assert [z["scale"] for z in Z] == [CLOSE, ECU, CLOSE, CLOSE, ECU]                    # tight shots 2 and 4
    assert all(a_["end"] <= b_["start"] for a_, b_ in zip(Z, Z[1:]))                       # no stacked scales
    assert all(abs(t * 30 - round(t * 30)) > 0.4 for z in Z for t in (z["start"], z["end"]))   # edges between frames
    assert Z[-1]["scale"] == ECU and Z[-1]["end"] > 9.7 - 1 / 30                              # the payoff ECU holds to the last frame
    assert Z[1]["start"] < 3.5 < Z[1]["end"] < 4.16                                           # ECU from "फकीरा" to the next word
    assert caps[1]["dodge"][0]["start"] == Z[1]["start"]
    assert (Z[0]["cx"], Z[0]["cy"]) == (0.5, round(0.36 + 0.14 / 1.3 + 0.06, 4))           # eye line at 0.36 H in the close-up
    assert [c["at"] for c in plan["softCuts"]] == [2.58, 5.02, 7.38]
    assert {"start": 0.1, "end": 0.3, "scale": 1.1} in plan["speaker"]["zooms"]           # older zoom in a wide shot kept
    assert not any(z.get("scale") == 1.12 for z in plan["speaker"]["zooms"])              # older zoom under a tight shot dropped
    assert E[0] == {"type": "text", "className": "mine", "text": "keep me"} and all(x["_seq"] for x in E[1:])
    n1, z1, s1 = len(E), len(plan["speaker"]["zooms"]), len(plan["sfx"])
    plan = build(plan, None)                                                                 # re-run replaces, never stacks
    assert (len(plan["elements"]), len(plan["speaker"]["zooms"]), len(plan["sfx"]), len(plan["softCuts"])) == (n1, z1, s1, 3)
    print("eclipse self-check ok")
