#!/usr/bin/env python3
"""Find the strongest short-form moments in a long transcript (podcast, stream, webinar).
Scores sentence-aligned windows on hook strength, density and payoff, and writes
<work>/candidates.json + a readable list. Claude then reads the top windows and picks the final clips.

usage: clip_candidates.py --work WORKDIR [--min 20] [--max 60] [--top 12]
"""
import argparse, os, re
from vs_common import load_json, save_json, log

ap = argparse.ArgumentParser()
ap.add_argument("--work", default="work")
ap.add_argument("--min", type=float, default=20)
ap.add_argument("--max", type=float, default=60)
ap.add_argument("--top", type=int, default=12)
a = ap.parse_args()
tr = load_json(os.path.join(a.work, "transcript.json"))
words = tr["words"]
segs = []
cur = []
for i, w in enumerate(words):
    cur.append(w)
    if re.search(r"[.!?]$", w["w"]) or (i + 1 < len(words) and words[i + 1]["start"] - w["end"] > 0.8):
        segs.append({"start": cur[0]["start"], "end": cur[-1]["end"], "text": " ".join(x["w"] for x in cur)}); cur = []
if cur:
    segs.append({"start": cur[0]["start"], "end": cur[-1]["end"], "text": " ".join(x["w"] for x in cur)})

HOOK = re.compile(r"\b(nobody|secret|mistake|never|always|why|how|truth|actually|biggest|worst|best|stop|most people|here's|the reason|i was wrong|crazy|insane|lesson|if you)\b", re.I)
PAY = re.compile(r"\b(so|that's why|the point|which means|result|because|lesson|remember)\b", re.I)
NUM = re.compile(r"\d")
FILL = re.compile(r"\b(um|uh|like|you know|sort of|kind of)\b", re.I)

cands = []
for i in range(len(segs)):
    j = i
    while j < len(segs) and segs[j]["end"] - segs[i]["start"] < a.min:
        j += 1
    while j < len(segs) and segs[j]["end"] - segs[i]["start"] <= a.max:
        win = segs[i:j + 1]
        text = " ".join(s["text"] for s in win)
        dur = win[-1]["end"] - win[0]["start"]
        first = win[0]["text"]
        nwords = len(text.split())
        sc = 0
        sc += 3 * len(HOOK.findall(first)) + (2 if first.strip().endswith("?") else 0)
        sc += 1.5 * min(3, len(NUM.findall(text)))
        sc += 1.5 * len(PAY.findall(win[-1]["text"]))
        sc += min(3, nwords / dur / 1.0)          # pace (words per second)
        sc -= 0.5 * len(FILL.findall(text))
        sc -= 2 if re.match(r"^(and|but|so|because|which)\b", first.strip(), re.I) else 0  # starts mid-thought
        cands.append({"start": round(win[0]["start"], 2), "end": round(win[-1]["end"], 2), "duration": round(dur, 1),
                      "score": round(sc, 2), "hook": first[:140], "text": text})
        j += 1
cands.sort(key=lambda c: -c["score"])
picked = []
for c in cands:
    if all(c["end"] <= p["start"] or c["start"] >= p["end"] for p in picked):
        picked.append(c)
    if len(picked) >= a.top:
        break
save_json(os.path.join(a.work, "candidates.json"), picked)
for k, c in enumerate(picked, 1):
    print(f"#{k}  {c['start']:.1f}-{c['end']:.1f}s ({c['duration']}s) score {c['score']}\n    hook: {c['hook']}")
log(f"{len(picked)} candidates -> {os.path.join(a.work, 'candidates.json')}")
