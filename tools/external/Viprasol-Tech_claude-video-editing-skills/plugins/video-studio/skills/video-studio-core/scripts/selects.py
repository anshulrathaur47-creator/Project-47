#!/usr/bin/env python3
"""Editor's selects from long footage: sentences, repeated takes, best take, paper edit.

  selects.py --work W [--input long.mp4] [--sim 0.6] [--gap 0.8]
      -> <work>/selects.json   every sentence with its take group, score and keep/drop reason
      -> <work>/paper_edit.md  editable: [x] keep / [ ] drop, reorder lines to reorder the edit
  selects.py --work W --apply [--input long.mp4] [--format 16:9]
      -> <work>/selects_spec.json   a timeline.py spec built from paper_edit.md (or selects.json)
         then: timeline.py build W/selects_spec.json --work W2

Uses <work>/transcript.json (source times; made by transcribe.py). With --input and no transcript it
transcribes the file first. Repeated takes = similar wording (difflib) within 2 minutes, or a false
start that the next sentence repeats. The kept take is the most complete, most confident, least
filler, without restart words ("sorry", "let me start again"...), with a small bonus for the last take.
Joining sentences more than 30 s apart (or out of order) is flagged FRANKENBITE: a constructed quote.
Check the meaning still matches what was said before you publish it.
"""
import argparse, difflib, os, re, subprocess, sys
from vs_common import probe, log, die, save_json, load_json

HERE = os.path.dirname(os.path.abspath(__file__))
FILL = {"um", "uh", "uhm", "umm", "erm", "er", "ah", "hmm", "mm", "like"}
RESTART = re.compile(r"\b(sorry|let me (start|try|say that) (again|over)|start(ing)? (again|over)|take (two|2|three|3)|"
                     r"scratch that|one more time|wait,? (no|let me)|from the top)\b", re.I)
WINDOW = 120.0        # seconds within which a similar sentence counts as a retake
FRANKEN = 30.0
PAD = 0.12


def norm(w):
    return re.sub(r"[^\w']", "", w.lower())


def sentences(words, gap):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt_gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 99
        if re.search(r"[.!?]$", w["w"]) or nxt_gap > gap:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    res = []
    for k, ws in enumerate(out, 1):
        toks = [norm(w["w"]) for w in ws]
        content = [t for t in toks if t and t not in FILL]
        res.append({"id": k, "start": ws[0]["start"], "end": ws[-1]["end"], "text": " ".join(w["w"] for w in ws),
                    "tokens": content, "filler": round(1 - len(content) / max(1, len(toks)), 3),
                    "conf": round(sum(w.get("p", 0.9) for w in ws) / len(ws), 3),
                    "complete": bool(re.search(r"[.!?]$", ws[-1]["w"])),
                    "restart": bool(RESTART.search(" ".join(w["w"] for w in ws)))})
    return res


def group_takes(sents, sim):
    parent = list(range(len(sents)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i, a in enumerate(sents):
        for j in range(i + 1, min(len(sents), i + 9)):
            b = sents[j]
            if b["start"] - a["end"] > WINDOW or not a["tokens"] or not b["tokens"]:
                continue
            r = difflib.SequenceMatcher(None, a["tokens"], b["tokens"]).ratio()
            false_start = len(a["tokens"]) >= 2 and b["tokens"][:len(a["tokens"])] == a["tokens"]
            if r >= sim or false_start:
                parent[find(j)] = find(i)
    groups = {}
    for i, s in enumerate(sents):
        groups.setdefault(find(i), []).append(s)
    return list(groups.values())


def score(s, longest, is_last):
    return round(s["conf"] - 2.0 * s["filler"] - (1.0 if s["restart"] else 0) + (0.15 if is_last else 0)
                 + (0.1 if s["complete"] else 0) + 0.4 * len(s["tokens"]) / max(1, longest), 3)


def pick(sents, sim):
    for g in group_takes(sents, sim):
        longest = max(len(s["tokens"]) for s in g)
        for s in g:
            s["group"] = g[0]["id"]
            s["score"] = score(s, longest, s is g[-1])
        best = max(g, key=lambda s: s["score"])
        for s in g:
            s["keep"] = s is best and not (s["restart"] and len(s["tokens"]) <= 8)
            if s is not best:
                s["reason"] = f"alt take of S{best['id']}" + (" (restart)" if s["restart"] else "")
            elif not s["keep"]:
                s["reason"] = "restart / aside"
            elif len(g) > 1:
                s["reason"] = f"best of {len(g)} takes"
    return sents


def fmt_t(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def frankenbites(order):
    flags = []
    for a, b in zip(order, order[1:]):
        if b["start"] < a["end"] - 0.01 or b["start"] - a["end"] > FRANKEN:
            flags.append((a["id"], b["id"]))
    return flags


def write_paper(path, sents, src):
    kept = [s for s in sents if s["keep"]]
    fb = {b for _, b in frankenbites(kept)}
    lines = [f"# Paper edit: {os.path.basename(src) if src else 'source'}", "",
             "Keep a line with [x], drop it with [ ], move lines to reorder. Then run selects.py --work W --apply.",
             "FRANKENBITE = this line is joined to text said more than 30 s away or out of order: check the meaning.", ""]
    for s in sents:
        note = s.get("reason", "")
        if s["id"] in fb:
            note = (note + "; " if note else "") + "FRANKENBITE"
        lines.append(f"- [{'x' if s['keep'] else ' '}] S{s['id']} {fmt_t(s['start'])}-{fmt_t(s['end'])} | {s['text']}"
                     + (f"  <!-- {note} -->" if note else ""))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def read_paper(path, sents):
    by_id = {s["id"]: s for s in sents}
    order = []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\s*-\s*\[([xX ])\]\s*S(\d+)\b", line)
        if m and m.group(1).lower() == "x" and int(m.group(2)) in by_id:
            order.append(by_id[int(m.group(2))])
    return order


def to_spec(order, src, transcript, fmt, gap):
    clips = []
    for s in order:
        if clips and clips[-1]["_last"] == s["id"] - 1 and s["start"] - clips[-1]["out"] + PAD < gap:
            clips[-1]["out"] = round(s["end"] + PAD, 3); clips[-1]["_last"] = s["id"]
            clips[-1]["_ids"].append(s["id"])
            continue
        clips.append({"src": src, "in": round(max(0.0, s["start"] - PAD), 3), "out": round(s["end"] + PAD, 3),
                      "words": transcript, "_last": s["id"], "_ids": [s["id"]]})
    for a, b in zip(clips, clips[1:]):   # never let padding overlap the neighbouring source
        if b["in"] < a["out"] and b["in"] > a["in"]:
            mid = round((a["out"] + b["in"]) / 2, 3); a["out"] = b["in"] = mid
    fb = frankenbites(order)
    out = []
    for c in clips:
        ids = c.pop("_ids"); c.pop("_last")
        c["note"] = "S" + ",S".join(map(str, ids))
        if any(b in ids[:1] for _, b in fb):
            c["note"] += " FRANKENBITE"
        out.append(c)
    return {"format": fmt, "fps": 30, "clips": out}, fb


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default="work")
    ap.add_argument("--input", default=None, help="source footage (default <work>/source.mp4)")
    ap.add_argument("--sim", type=float, default=0.6)
    ap.add_argument("--gap", type=float, default=0.8)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--format", default="16:9")
    ap.add_argument("--model", default="small")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    tp = os.path.join(a.work, "transcript.json")
    src = os.path.abspath(a.input) if a.input else os.path.abspath(os.path.join(a.work, "source.mp4"))
    if not os.path.exists(tp):
        if not os.path.exists(src):
            die("no transcript.json in the work folder; pass --input footage.mp4")
        r = subprocess.run([sys.executable, os.path.join(HERE, "transcribe.py"), "--work", a.work, "--audio", src,
                            "--model", a.model])
        if r.returncode:
            die("transcription failed")
    sents = pick(sentences(load_json(tp)["words"], a.gap), a.sim)
    sj, pp = os.path.join(a.work, "selects.json"), os.path.join(a.work, "paper_edit.md")
    if not a.apply:
        save_json(sj, {"source": src, "sentences": [{k: v for k, v in s.items() if k != "tokens"} for s in sents]})
        write_paper(pp, sents, src)
        kept = [s for s in sents if s["keep"]]
        log(f"{len(sents)} sentences, {len(kept)} kept, {len(sents) - len(kept)} alt takes/restarts dropped "
            f"({sum(s['end'] - s['start'] for s in kept):.1f}s kept) -> {pp}")
        return
    order = read_paper(pp, sents) if os.path.exists(pp) else [s for s in sents if s["keep"]]
    if not order:
        die("nothing marked [x] in the paper edit")
    if not os.path.exists(src):
        die(f"{src} not found; pass --input")
    spec, fb = to_spec(order, src, os.path.abspath(tp), a.format, a.gap)
    out = os.path.join(a.work, "selects_spec.json")
    save_json(out, spec)
    for x, y in fb:
        log(f"FRANKENBITE: S{x} -> S{y} joins speech from different moments. Check the meaning is unchanged.")
    log(f"{len(spec['clips'])} clips -> {out}. Next: timeline.py build {out} --work <new work folder>")


if __name__ == "__main__":
    main()
