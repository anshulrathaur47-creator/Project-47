#!/usr/bin/env python3
"""Layercut scene recipe (grid-stage skin): speaker scenes on the dark disc stage, cut with full-screen UI-panel and
title-card scenes.

  sequence.py PLAN --recipe layercut          (self-check: python recipes/layercut.py)

speaker scene - the cut-out on the grid stage with the turning vinyl disc (skin statics); one huge silver condensed
                word behind the head per scene (solid / outline alternating, masked by the person), small uppercase
                captions under the chin, white audio-level bars (odd phrases) or a thin wave line (even phrases)
                behind the speaker. The last phrase adds a glass pill (toggle + italic script word) at the bottom.
panel scene   - no speaker: a 3D-tilted dark app panel flies over the dotted stage; the key word is its title, the
                phrase's other words are slider / toggle rows.
card scene    - no speaker: a full-screen title card with diagonal light beams, a small kicker with a glowing dot
                (the words before the key word) over the key word in huge silver type.
The first and last phrases stay on the speaker. A middle phrase opens on the speaker and cuts to a panel (odd) or a
card (even) scene ON its key word, when both parts are long enough (MIN_FACE / MIN_CUT), else it stays on the speaker.
Key word = the longest of the phrase's last three words, skipping refrains (words heard in 2+ phrases, e.g. "बरगी").
Scene changes get softCuts + a whoosh. Everything written carries "_seq": true and is replaced on a re-run; the skin's
auto headlines (gs-head), captions and key-word pills (gs-pill) are replaced by the recipe's own.
"""
import os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sequence import phrases, bare, esc   # noqa: E402
from vs_common import norm, log   # noqa: E402

LEAD = 0.12       # s: a scene starts this long before its first word
MIN_FACE = 0.6    # s: shortest speaker part before a cutaway
MIN_CUT = 1.0     # s: shortest cutaway (time to read it)
CAP_Y = 0.83      # captions / pill centre (fraction of H): under the chin of a tight selfie at the skin's personDrop 0.14
SKIN_AUTO = ("gs-head", "gs-pill")   # make_plan's auto elements this recipe replaces


def key_of(words, idx, refrain):
    cand = [i for i in idx if norm(bare(words[i]["w"])) not in refrain] or idx
    return max(cand[-3:], key=lambda i: (len(bare(words[i]["w"])), i))   # ties go to the later word


def word(words, i):
    return bare(words[i]["w"]).upper()   # Devanagari has no case: unchanged


def speaker_scene(words, idx, s, e, n, head, W, H, pill=None):
    """Speaker on the stage: head word behind the person, bars or wave line, captions under the chin, optional pill."""
    els = [{"type": "headline", "layer": "behind", "decor": True, "className": "lc-head" + (" alt" if n % 2 else ""),
            "text": word(words, head), "x": round(W / 2), "y": round(H * 0.15), "w": round(W * 0.96),
            "start": s, "end": e, "in": {"name": "maskUp", "dur": 0.5}, "out": "fade",
            "keys": {"s": [[0, 1.07], [e - s, 1.0, "linear"]]}}]
    if n % 2:   # white audio-level bars behind the speaker
        els.append({"type": "equalizer", "layer": "behind", "decor": True, "className": "lc-bars", "count": 30,
                    "x": round(W / 2), "y": round(H * 0.34), "w": W, "h": round(H * 0.24), "start": s, "end": e, "in": "fade"})
    else:       # thin wave line across the frame, behind the speaker
        els.append({"type": "shape", "kind": "ribbon", "layer": "behind", "decor": True, "className": "lc-line",
                    "x": round(W / 2), "y": round(H * 0.25), "w": round(W * 1.1), "h": round(H * 0.07), "thickness": 3,
                    "color": "#FFFFFF", "color2": "#D4FF3A", "speed": 1.2, "start": s, "end": e, "in": "fade"})
    t = e if pill is None else round(max(s, words[pill]["start"] - 0.08), 3)   # the pill takes over the caption slot
    els.append({"type": "captions", "className": "lc-cap", "mode": "karaoke", "maxWords": 3, "maxChars": 20,
                "uppercase": True, "words": [words[i] for i in idx if words[i]["start"] < t], "y": round(H * CAP_Y),
                "hold": 0.2, "groupIn": {"name": "maskUp", "dur": 0.3}, "start": s, "end": t})
    if pill is not None:   # glass pill: toggle + italic script word, lands on that word
        els.append({"type": "text", "html": True, "className": "lc-pill",
                    "text": f"<span class='lc-tog'></span><em>{esc(bare(words[pill]['w']))}</em>",
                    "x": round(W / 2), "y": round(H * CAP_Y), "start": t, "end": e, "in": {"name": "springPop", "dur": 0.5}})
    return els


def panel_scene(words, idx, k, m, e, W, H):
    """No speaker: a 3D-tilted app panel flies in over the dotted stage."""
    rows = [i for i in idx if i != k][:3]
    html = "".join(f"<div class='lc-row'><span>{esc(word(words, i))}</span>"
                   + ("<b class='lc-tg'></b>" if j == len(rows) - 1 else f"<b class='lc-sl' style='--v:{(72, 38)[j]}%'><i></i></b>")
                   + "</div>" for j, i in enumerate(rows))
    html = (f"<div class='lc-ui'><div class='lc-ui-top'><i></i><i></i><i></i><span>{len(idx):02d}</span></div>"
            f"<div class='lc-ui-title'>{esc(word(words, k))}</div>{html}</div>")
    d = round(e - m, 3)
    return [
        {"type": "background", "layer": "front", "className": "lc-stage", "start": m, "end": e},
        {"type": "shape", "kind": "ring", "layer": "front", "className": "gs-disc", "x": round(W * 0.92), "y": round(H * 0.16),
         "w": round(W * 0.95), "h": round(W * 0.95), "speed": 0.4, "start": m, "end": e, "in": "none", "keys": {"r": [[0, 0], [d, 30, "linear"]]}},
        {"type": "shape", "kind": "ribbon", "layer": "front", "className": "lc-line", "x": round(W / 2), "y": round(H * 0.8),
         "w": round(W * 1.1), "h": round(H * 0.06), "thickness": 3, "color": "#FFFFFF", "color2": "#D4FF3A", "speed": 1.2,
         "start": m, "end": e, "in": "fade"},
        {"type": "text", "html": True, "className": "lc-panel", "text": html, "x": round(W / 2), "y": round(H * 0.46),
         "w": round(W * 0.86), "start": m, "end": e, "in": {"name": "fade", "dur": 0.15}, "out": "fade",
         "keys": {"tx": [[0, round(W * 0.9)], [0.6, 0, "expoOut"], [d, -40, "linear"]],
                  "ty": [[0, 160], [0.6, 0, "expoOut"]], "r": [[0, 12], [0.6, 0, "expoOut"]], "s": [[0, 0.82], [0.6, 1, "expoOut"]]}},
    ]


def card_scene(words, idx, k, m, e, W, H):
    """No speaker: title card with diagonal light beams, a kicker with a glowing dot, the key word huge."""
    kick = [word(words, i) for i in idx if i < k][-4:]
    tail = [i for i in idx if i > k][:4]
    if not kick:   # the key word opens the phrase: its tail becomes the kicker
        kick, tail = [word(words, i) for i in tail], []
    d = round(e - m, 3)
    return [
        {"type": "background", "layer": "front", "className": "lc-tc", "start": m, "end": e},
        {"type": "text", "html": True, "className": "lc-beams", "text": "<i></i><i></i><i></i><i></i>", "x": round(W / 2),
         "y": round(H / 2), "w": W, "h": H, "start": m, "end": e, "in": "none", "keys": {"tx": [[0, -70], [d, 70, "linear"]]}},
        {"type": "text", "html": True, "className": "lc-kick", "text": f"<span class='lc-gdot'></span>{esc(' '.join(kick))}",
         "x": round(W / 2), "y": round(H * 0.41), "w": round(W * 0.8), "start": round(m + 0.05, 3), "end": e,
         "in": {"name": "maskUp", "dur": 0.4}},
        {"type": "headline", "className": "lc-title", "text": word(words, k), "x": round(W / 2), "y": round(H * 0.5),
         "w": round(W * 0.86), "start": round(m + 0.1, 3), "end": e, "in": {"name": "maskUp", "dur": 0.5},
         "keys": {"s": [[0, 1.0], [d, 1.06, "linear"]]}},
    ] + ([{"type": "text", "html": True, "className": "lc-kick lc-tail", "text": esc(" ".join(word(words, i) for i in tail)),
           "x": round(W / 2), "y": round(H * 0.645), "w": round(W * 0.8), "start": round(max(m + 0.2, words[tail[0]]["start"] - 0.06), 3),
           "end": e, "in": {"name": "maskUp", "dur": 0.35}}] if tail else [])


def build(plan, a):
    W, H = plan["output"]["width"], plan["output"]["height"]
    dur = plan["output"]["duration"]
    words = [w for w in plan["words"] if w.get("w", "").strip()]
    P = phrases(words)
    seen = Counter(key for idx in P for key in {norm(bare(words[i]["w"])) for i in idx})
    refrain = {key for key, c in seen.items() if c > 1}
    els, cuts, sfx = [], [], []
    for n, idx in enumerate(P):
        s = 0.0 if n == 0 else round(words[idx[0]]["start"] - LEAD, 3)
        e = round(words[P[n + 1][0]]["start"] - LEAD, 3) if n + 1 < len(P) else dur
        last = n == len(P) - 1
        k = key_of(words, idx, refrain)
        m = round(words[k]["start"] - 0.06, 3)
        if 0 < n and not last and m - s >= MIN_FACE and e - m >= MIN_CUT:   # speaker, then the cutaway on the key word
            before = [i for i in idx if words[i]["start"] < m]
            head = key_of(words, before, refrain)
            els += speaker_scene(words, before, s, m, n, head, W, H)
            cut = panel_scene(words, idx, k, m, e, W, H) if n % 2 else card_scene(words, idx, k, m, e, W, H)
            for x in cut:
                x["decor"] = True   # a full-screen scene of its own: scenery for QC
            els += cut
            cuts += [m, e]
            sfx += [{"t": round(m - 0.12, 3), "kind": "whoosh-short", "gain": 0.22},
                    {"t": round(m + (0.5 if n % 2 else 0.1), 3), "kind": "ui-tap" if n % 2 else "impact", "gain": 0.22},
                    {"t": round(e - 0.12, 3), "kind": "whoosh-short", "gain": 0.18}]
            continue
        pill = None
        if last and len(idx) > 1:   # the pill carries the phrase's last word (often the refrain) unless that is the key
            pill = idx[-1] if idx[-1] != k else max((i for i in idx if i != k), key=lambda i: (len(bare(words[i]["w"])), i))
            sfx.append({"t": round(words[pill]["start"] - 0.05, 3), "kind": "click", "gain": 0.3})
        els += speaker_scene(words, idx, s, e, n, k, W, H, pill)
    cuts = sorted(c for c in set(cuts) if 0 < c < dur)

    for x in els:
        x["_seq"] = True
    keep = [x for x in plan.get("elements", []) if not x.get("_seq") and x.get("type") != "captions"
            and not any(c in str(x.get("className", "")).split() for c in SKIN_AUTO)]
    plan["elements"] = keep + els
    plan["speaker"]["zooms"] = [z for z in plan["speaker"].get("zooms", []) if not z.get("_seq")]
    plan["softCuts"] = [{"at": c, "dur": 0.34, "sigma": 20} for c in cuts]
    plan["sfx"] = [x for x in plan.get("sfx", []) if not x.get("_seq")] + [dict(x, _seq=True) for x in sfx]
    log(f"layercut sequence: {len(P)} phrases, {len(cuts)} scene changes, {len(els)} elements")
    return plan


if __name__ == "__main__":   # self-check on the skin-test shayari timings (refrain "बरगी" must not become a key word)
    T = [("हर", 0.0, .28), ("बात", .3, .72), ("तीरा", .76, 1.31), ("बरगी,", 1.36, 2.06), ("राशि", 2.7, 3.19), ("है", 3.23, 3.47),
         ("फकीरा", 3.5, 4.11), ("बरगी,", 4.16, 4.77), ("एक", 5.14, 5.35), ("ए", 5.37, 5.47), ("छोरी", 5.48, 5.9), ("लाइफ", 5.93, 6.35),
         ("में", 6.39, 6.7), ("भाई,", 6.73, 7.14), ("वा", 7.5, 7.66), ("भी", 7.68, 7.84), ("जमा", 7.86, 8.1), ("हीरा", 8.12, 8.45),
         ("बरगी,", 8.48, 8.88)]
    plan = {"output": {"width": 1080, "height": 1920, "duration": 9.7}, "speaker": {},
            "words": [{"w": w, "start": s, "end": e} for w, s, e in T],
            "elements": [{"type": "background", "className": "gs-bg"}, {"type": "captions"},
                         {"type": "headline", "className": "gs-head alt"}, {"type": "chip", "className": "gs-pill"}]}
    plan = build(plan, None)
    n1, E = len(plan["elements"]), plan["elements"]
    by = lambda c: [x for x in E if x.get("className") == c]   # noqa: E731
    assert [x["text"] for x in E if "lc-head" in x.get("className", "")] == ["तीरा", "राशि", "छोरी", "हीरा"]
    assert [x["start"] for x in by("lc-stage")] == [3.44] and [x["start"] for x in by("lc-tc")] == [5.87]   # cut on the key word
    assert "फकीरा" in by("lc-panel")[0]["text"] and [x["text"] for x in by("lc-title")] == ["लाइफ"]
    assert by("lc-kick")[0]["text"].endswith("एक ए छोरी")
    assert len(by("lc-pill")) == 1 and "<em>बरगी</em>" in by("lc-pill")[0]["text"] and by("lc-pill")[0]["start"] == 8.4
    assert [x["text"] for x in by("lc-kick lc-tail")] == ["में भाई"]
    assert [c["at"] for c in plan["softCuts"]] == [3.44, 5.02, 5.87, 7.38]
    caps = [x for x in E if x["type"] == "captions"]
    assert [x["end"] for x in caps] == [2.58, 3.44, 5.87, 8.4] and all(w["start"] < 3.44 for w in caps[1]["words"])
    assert [w["w"] for w in caps[3]["words"]] == ["वा", "भी", "जमा", "हीरा"]   # the pill word is the pill's, not the caption's
    assert E[0]["className"] == "gs-bg" and all(x.get("_seq") for x in E[1:])
    assert all(x.get("decor") for x in E if x.get("start", 0) >= 3.44 and x.get("end", 0) <= 5.02 and x["type"] != "captions")
    plan = build(plan, None)                                            # re-run replaces, never stacks
    assert len(plan["elements"]) == n1 and len(plan["sfx"]) == len({(x["t"], x["kind"]) for x in plan["sfx"]})
    print("layercut self-check ok")
