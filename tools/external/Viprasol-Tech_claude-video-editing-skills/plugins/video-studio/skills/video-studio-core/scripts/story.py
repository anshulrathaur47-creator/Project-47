#!/usr/bin/env python3
"""Story / structure tools: a paper edit from the transcript, ranked hooks, genre structure map, and reordering.

usage: story.py outline --work W [--genre reel-talking-head]
           -> <work>/outline.json + <work>/outline.md: sentences s1..sN with source times, topic shifts,
              quotable lines scored for hook potential, ranked hook candidates, the genre's beat map and a proposed order
       story.py reorder --work W --order "s3,s1-s2,s4[0:6]" [--genre G] [--format 9:16] [--fps 30]
                        [--transition dissolve:0.3] [--out W/story_timeline.json]
           -> a timeline spec for timeline.py ({"clips":[{"src","in","out","transition"}], "format", "fps"})
              plus <work>/story_flags.md. sN = whole sentence, sA-sB = a run, sN[i:j] = words i..j-1 of a sentence.
              Partial-sentence splices and context-dependent moves are flagged as Frankenbite risk.
Times are on the SOURCE timeline (transcript.json + source.mp4), so reordering never stacks cut-on-cut.
"""
import argparse, os, re, sys
from vs_common import load_json, save_json, log, die, probe
import editor

PAD_IN, PAD_OUT = 0.12, 0.08
DISCOURSE = re.compile(r"^(so|now|next|okay|ok|anyway|but|first|firstly|second|secondly|third|finally|lastly|step|another|"
                       r"here'?s|the (first|second|third|next|last))\b", re.I)
ORDINAL = re.compile(r"^(first|firstly|second|secondly|third|thirdly|fourth|fifth|next|finally|lastly|step|number)\b", re.I)
BACKREF = re.compile(r"^(it|this|that|these|those|they|he|she|and|but|so|because|which|also|then|there)\b", re.I)
STOP = set("a an the and or but if so to of in on at for with from by as is are was were be i you he she it we they me my your "
           "this that these those there here what which who when where why how not no do does did have has had just very really "
           "also too can could would should will um uh like okay yeah".split())
FILL = {"um", "uh", "uhm", "umm", "erm", "er", "ah", "hmm", "mm", "uhh"}


def content(ws):
    return {editor.norm(w["w"]) for w in ws} - STOP - {""}


def build_sentences(words):
    out = []
    for n, idx in enumerate(editor.sentences(words), 1):
        body = list(idx)
        while len(body) > 1 and editor.norm(words[body[0]]["w"]) in FILL:     # trim leading hesitations
            body = body[1:]
        text = editor.text_of(words, body)
        hs, why = editor.hook_score(text)
        out.append({"id": f"s{n}", "start": words[body[0]]["start"], "end": words[body[-1]]["end"], "idx": body, "text": text,
                    "hook": hs, "why": why, "greeting": bool(editor.GREETING.search(text)), "cta": bool(editor.CTA.search(text)),
                    "ordinal": bool(ORDINAL.match(text))})
    return out


def topic_shifts(words, S):
    shifts = []
    for k in range(1, len(S)):
        prev = [words[i] for s in S[max(0, k - 2):k] for i in s["idx"]]
        cur = [words[i] for i in S[k]["idx"]]
        a, b = content(prev), content(cur)
        jac = len(a & b) / max(1, len(a | b))
        gap = S[k]["start"] - S[k - 1]["end"]
        why = []
        if gap >= 1.0: why.append(f"{gap:.1f}s pause")
        if DISCOURSE.match(S[k]["text"]): why.append(f"marker '{S[k]['text'].split()[0].strip(',')}'")
        if len(a) >= 3 and len(b) >= 3 and jac < 0.08: why.append("new vocabulary")
        if why:
            shifts.append({"before": S[k]["id"], "at": round(S[k]["start"], 2), "why": why})
    return shifts


def beat_map(S, g, total):
    beats, t = [], 0.0
    for b in g["structure"]:
        beats.append({"beat": b["beat"], "pct": b["pct"], "from": round(total * t / 100, 2), "to": round(total * (t + b["pct"]) / 100, 2), "ids": []})
        t += b["pct"]
    names = [b["beat"].lower() for b in beats]
    find = lambda *keys: next((i for i, n in enumerate(names) if any(k in n for k in keys)), None)
    body = find("step", "point", "value", "teach", "body", "act 1", "walkthrough", "feature 1", "conversation", "development") \
        or len(beats) // 2
    for s in S:
        mid = (s["start"] + s["end"]) / 2
        i = next((k for k, b in enumerate(beats) if b["from"] <= mid - S[0]["start"] < b["to"]), len(beats) - 1)
        if s["cta"] and find("cta", "outro", "next", "logo") is not None:
            i = find("cta", "outro", "next", "logo")
        elif s["ordinal"] and i < body:
            i = body
        beats[i]["ids"].append(s["id"])
    return beats


def cmd_outline(a):
    work = a.work
    tr = load_json(os.path.join(work, "transcript.json"))
    words = tr.get("words", [])
    if not words:
        die("transcript.json has no words")
    g = editor.load_genre(a.genre) if a.genre else editor.load_genre("reel-talking-head")
    S = build_sentences(words)
    total = S[-1]["end"] - S[0]["start"]
    shifts = topic_shifts(words, S)
    ranked = sorted([s for s in S if not s["greeting"] and not s["cta"]], key=lambda s: -s["hook"])
    hooks = [{"id": s["id"], "score": s["hook"], "why": s["why"], "text": s["text"],
              "cold_open_ok": not BACKREF.match(s["text"])} for s in ranked[:5]]
    beats = beat_map(S, g, total)
    best = next((h for h in hooks if h["cold_open_ok"]), None)
    order = [s["id"] for s in S if not s["greeting"]]
    if best and order and best["id"] != order[0] and best["score"] > S[0]["hook"] + 1:
        order = [best["id"]] + [x for x in order if x != best["id"]]
    ctas = [s["id"] for s in S if s["cta"]]
    order = [x for x in order if x not in ctas] + ctas
    out = {"genre": g["name"], "duration": round(total, 2),
           "sentences": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items() if k != "idx"} for s in S],
           "topic_shifts": shifts, "hook_candidates": hooks, "structure": beats, "proposed_order": order}
    save_json(os.path.join(work, "outline.json"), out)
    L = [f"# Paper edit ({g['name']})", "", f"{len(S)} sentences, {total:.1f}s of speech (source timeline).", "",
         "| id | time | hook | text |", "| --- | --- | --- | --- |"]
    shift_ids = {x["before"]: x for x in shifts}
    for s in S:
        if s["id"] in shift_ids:
            L.append(f"| -- | {shift_ids[s['id']]['at']:.1f} | | *topic shift: {', '.join(shift_ids[s['id']]['why'])}* |")
        tags = [t for t, on in (("greeting", s["greeting"]), ("CTA", s["cta"]), ("list", s["ordinal"])) if on]
        L.append(f"| {s['id']} | {s['start']:.2f}-{s['end']:.2f} | {s['hook']} | {s['text']}{' `' + ', '.join(tags) + '`' if tags else ''} |")
    L += ["", "## Hook candidates (ranked)"]
    for n, h in enumerate(hooks, 1):
        L.append(f"{n}. **{h['id']}** ({h['score']}; {', '.join(h['why']) or 'plain'}){'' if h['cold_open_ok'] else ' - needs context, weak cold open'}: {h['text']}")
    L += ["", f"## Structure ({' -> '.join(b['beat'] for b in beats)})"]
    for b in beats:
        L.append(f"- **{b['beat']}** ({b['pct']}%, {b['from']:.1f}-{b['to']:.1f}s): {', '.join(b['ids']) or '(empty - shoot or write it)'}")
    L += ["", "## Proposed order", "", f"`{','.join(order)}`", "",
          f"Build it: `python story.py reorder --work {work} --order \"{','.join(order)}\" --genre {g['name']}` then `timeline.py build`.",
          "Whole-sentence moves are safe; sN[i:j] slices that join different sentences are Frankenbites - flagged, never silent."]
    with open(os.path.join(work, "outline.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L[:6 + len(S) + len(shifts)]))
    log(f"outline -> {os.path.join(work, 'outline.md')} ({len(hooks)} hook candidates, {len(shifts)} topic shifts)")


TOK = re.compile(r"^s(\d+)(?:-s(\d+))?(?:\[(\d*):(\d*)\])?$")


def parse_order(order, S):
    """-> list of (sentence_index, word_slice_or_None)"""
    out = []
    for tok in [x.strip() for x in order.split(",") if x.strip()]:
        m = TOK.match(tok)
        if not m:
            die(f"bad order token '{tok}' (use s3, s1-s4 or s3[2:7])")
        a_, b_ = int(m.group(1)), int(m.group(2) or m.group(1))
        if not (1 <= a_ <= len(S) and 1 <= b_ <= len(S)):
            die(f"'{tok}': only s1..s{len(S)} exist")
        sl = (int(m.group(3) or 0), int(m.group(4)) if m.group(4) else None) if m.group(3) is not None or m.group(4) is not None else None
        if sl and a_ != b_:
            die(f"'{tok}': word slices need a single sentence")
        step = 1 if b_ >= a_ else -1
        out += [(k - 1, sl) for k in range(a_, b_ + step, step)]
    return out


def cmd_reorder(a):
    work = a.work
    tr = load_json(os.path.join(work, "transcript.json"))
    words = tr.get("words", [])
    S = build_sentences(words)
    items = parse_order(a.order, S)
    g = editor.load_genre(a.genre) if a.genre else None
    strict = bool(g) and g["name"] in ("documentary-interview", "testimonial", "news-explainer", "corporate-brand")
    src = "source.mp4"
    info = probe(os.path.join(work, src)) if os.path.exists(os.path.join(work, src)) else {}
    fmt = a.format or (g["aspect"] if g else ("16:9" if info.get("width", 9) > info.get("height", 16) else "9:16"))
    fps = a.fps or round(info.get("fps", 30) or 30)
    tr_type, _, tr_dur = (a.transition or "cut").partition(":")
    flags, clips, prev = [], [], None
    for n, (k, sl) in enumerate(items):
        s = S[k]
        idx = s["idx"][sl[0]:sl[1]] if sl else s["idx"]
        if not idx:
            die(f"s{k + 1}{sl}: empty word slice")
        partial = bool(sl) and (idx[0] != s["idx"][0] or idx[-1] != s["idx"][-1])
        lo = words[s["idx"][0] - 1]["end"] + 0.01 if s["idx"][0] > 0 and idx[0] == s["idx"][0] else (words[idx[0] - 1]["end"] + 0.01 if idx[0] > 0 else 0.0)
        hi_w = words[idx[-1] + 1]["start"] - 0.01 if idx[-1] + 1 < len(words) else words[idx[-1]]["end"] + PAD_OUT
        t_in = round(max(lo, words[idx[0]]["start"] - PAD_IN, 0.0), 3)
        t_out = round(min(hi_w, words[idx[-1]]["end"] + PAD_OUT), 3)
        text = editor.text_of(words, idx)
        if prev is not None:
            pk, ppartial = prev
            if k == pk + 1 and not partial and not ppartial and clips and abs(clips[-1]["out"] - t_in) < 0.5:
                clips[-1]["out"] = t_out                      # natural continuation: one clip, keep the real pause
                prev = (k, partial); continue
            if partial or ppartial:
                flags.append(("HIGH", f"Frankenbite: '{text[:50]}' (s{k + 1}) is spliced onto s{pk + 1} mid-sentence - a constructed quote"
                              + (". Not allowed in this genre without the speaker's approval." if strict else ". Check the meaning matches the source.")))
            elif abs(k - pk) > 1:
                if BACKREF.match(text):
                    flags.append(("MED", f"s{k + 1} starts with '{text.split()[0]}' - it refers back to s{k}, which it no longer follows"))
                if strict:
                    flags.append(("HIGH", f"s{pk + 1} -> s{k + 1}: sentences reordered ({abs(k - pk)} apart) in a factual genre - keep meaning, get approval"))
                elif n == 1 or abs(S[k]["start"] - S[pk]["end"]) > 30:
                    flags.append(("LOW", f"s{pk + 1} -> s{k + 1}: reordered (cold open / restructure) - fine for entertainment, log it"))
        if any(x == (k, sl) for x in items[:n]):
            flags.append(("MED", f"s{k + 1} is used twice"))
        clips.append({"src": src, "in": t_in, "out": t_out,
                      "transition": {"type": tr_type} if not tr_dur or n == 0 else {"type": tr_type, "duration": float(tr_dur)}})
        if n == 0:
            clips[0]["transition"] = {"type": "cut"}
        prev = (k, partial)
    spec = {"clips": clips, "format": fmt, "fps": fps}
    out = a.out or os.path.join(work, "story_timeline.json")
    save_json(out, spec)
    L = [f"# Reorder flags", "", f"order: `{a.order}` -> {len(clips)} clips, {sum(c['out'] - c['in'] for c in clips):.1f}s", ""]
    L += [f"- **{sev}** {msg}" for sev, msg in flags] or ["- no Frankenbite risk: whole sentences in a safe order"]
    with open(os.path.join(work, "story_flags.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    for sev, msg in flags:
        log(f"[{sev}] {msg}")
    log(f"timeline spec -> {out} ({len(clips)} clips, {fmt} @ {fps} fps). Build: timeline.py build {out} --work {work}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("outline"); o.add_argument("--work", default="work"); o.add_argument("--genre", default=None)
    r = sub.add_parser("reorder"); r.add_argument("--work", default="work"); r.add_argument("--order", required=True)
    r.add_argument("--genre", default=None); r.add_argument("--format", default=None); r.add_argument("--fps", type=int, default=None)
    r.add_argument("--transition", default=None, help="TYPE[:SECONDS] between clips, e.g. dissolve:0.3 (default cut)")
    r.add_argument("--out", default=None)
    a = ap.parse_args()
    try:
        cmd_outline(a) if a.cmd == "outline" else cmd_reorder(a)
    except ValueError as e:
        die(str(e))


if __name__ == "__main__":
    main()
