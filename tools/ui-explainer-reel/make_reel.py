"""Build a ui-explainer reel from a script file.

  python3 tools/ui-explainer-reel/make_reel.py projects/<date>-<name>/script.json [--out exports/<file>.mp4] [--frames 30,120]

script.json:
{
  "name": "demo-3d", "theme": "cream" | "dark", "handle": "@yourhandle", "accent": "#e05a28" (optional), "terms": "..." (optional),
  "vo": "path/to/your_vo.mp3"   (optional: your own voice-over; without it a Kokoro draft voice is made from the "hi" lines)
  "voice": "hm_omega", "speed": 1.08, "music": 0.07,
  "lines": [
    { "hi": "देवनागरी line for the voice", "roman": "Hinglish *key* words for captions", "scene": { "type": "hero", ... }, "tag": "STEP 01 · ..." },
    { "hi": "...", "roman": "...", "mark": "typeAt" }        # mark: set that card field to this line's start (e.g. when typing begins)
  ]
}
A line with "scene" starts a new card at that line. Words in *stars* become boxed key words. Lines over 6 words split into two phrases.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
KIT_PY = os.path.join(ROOT, "tools", "external", "artemnovitckii_claude-animation-skills", "kit", ".venv", "bin", "python")
BROWSER = "/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell"


def wav_len(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return float(out.strip())


def roman_words(line):
    """'Na koi *mehenga software*, na' -> [('Na',False),('koi',False),('mehenga',True),('software,',True),('na',False)]"""
    out, key = [], False
    for tok in line.split():
        starts, ends = tok.startswith("*"), tok.rstrip(",.!?:;—").endswith("*")
        clean = tok.replace("*", "")
        if not re.sub(r"[\W_]", "", clean):   # a lone dash or punctuation mark is not a caption word
            continue
        if starts:
            key = True
        out.append((clean, key))
        if ends:
            key = False
    return out


def line_times_from_whisper(lines, words_json):
    """Own VO: share the Whisper words between the script lines by word count; returns [(start, end)]."""
    d = json.load(open(words_json))
    ws = [w for s in d.get("segments", []) for w in s.get("words", [])] or d.get("words", [])
    ws = [{"s": w.get("start", w.get("s")), "e": w.get("end", w.get("e"))} for w in ws]
    counts = [len(l["hi"].split()) if l.get("hi") else len(roman_words(l["roman"])) for l in lines]
    total, n = sum(counts), len(ws)
    out, acc = [], 0
    for c in counts:
        a = int(round(acc / total * n)); acc += c; b = max(a + 1, int(round(acc / total * n)))
        seg = ws[a:min(b, n)] or ws[-1:]
        out.append((seg[0]["s"], seg[-1]["e"]))
    return out


def build(script, work):
    lines = script["lines"]
    if script.get("vo"):
        vo = os.path.join(work, "vo" + os.path.splitext(script["vo"])[1])
        shutil.copy(script["vo"], vo)
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "transcribe.py"), vo, "--lang", "hi", "--no-vad", "--out", work], check=True)
        times = line_times_from_whisper(lines, os.path.splitext(vo)[0] + ".words.json")
    else:
        json.dump([l["hi"] for l in lines], open(os.path.join(work, "lines.json"), "w"), ensure_ascii=False)
        subprocess.run([KIT_PY, os.path.join(HERE, "tts.py"), os.path.join(work, "lines.json"), work, script.get("voice", "hm_omega"), str(script.get("speed", 1.08))], check=True)
        vo = os.path.join(work, "vo.wav")
        meta = json.load(open(os.path.join(work, "vo_lines.json")))
        times = [(m["start"], m["start"] + m["dur"]) for m in meta]
    # words inside each line, spread by length (syllable-ish weight)
    phrases, scenes, zone_flip = [], [], 0
    for li, (line, (s, e)) in enumerate(zip(lines, times)):
        rw = roman_words(line["roman"])
        weights = [max(2, len(re.sub(r"[^A-Za-z0-9]", "", w))) + 1.5 for w, _ in rw]
        tot = sum(weights); t = s; words = []
        for (w, key), wt in zip(rw, weights):
            d = (e - s) * wt / tot
            words.append({"t": w, "s": round(t, 3), "e": round(t + d, 3), **({"k": True} if key else {})}); t += d
        if line.get("scene") or li == 0:
            scenes.append({"start": 0.0 if li == 0 else round(s - 0.05, 3), "card": dict(line.get("scene", {"type": "big", "big": "?"})), **({"tag": line["tag"]} if line.get("tag") else {})})
            zone_flip = 0
        if line.get("mark"):
            scenes[-1]["card"][line["mark"]] = round(s - scenes[-1]["start"] + 0.2 + 0.35, 3)
        if len(words) <= 6:
            chunks = [words]
        else:   # split near the middle, preferring a break after punctuation
            mid = len(words) / 2
            cut = min(range(2, len(words) - 1), key=lambda i: abs(i - mid) - (1.6 if words[i - 1]["t"][-1] in ",?.!:" else 0))
            chunks = [words[:cut], words[cut:]]
        for ch in chunks:
            phrases.append({"zone": "top" if zone_flip % 2 == 0 else "bottom", "words": ch}); zone_flip += 1
    return vo, phrases, scenes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", default=None)
    ap.add_argument("--frames", default=None, help="only render these frames as stills (comma list) into <work>/stills")
    args = ap.parse_args()
    script = json.load(open(args.script))
    work = os.path.dirname(os.path.abspath(args.script))
    name = script.get("name", os.path.basename(work))
    vo, phrases, scenes = build(script, work)
    pub = os.path.join(HERE, "public", "reel"); os.makedirs(pub, exist_ok=True)
    vo_pub = f"reel/{name}{os.path.splitext(vo)[1]}"
    shutil.copy(vo, os.path.join(HERE, "public", vo_pub))
    spec = {"theme": script.get("theme", "cream"), "handle": script.get("handle", "@yourhandle"), "duration": round(wav_len(vo) + 1.2, 2),
            "vo": vo_pub, "music": script.get("music", 0.07), "phrases": phrases, "scenes": scenes}
    for k in ("accent", "accent2", "terms"):
        if script.get(k):
            spec[k] = script[k]
    spec_path = os.path.join(work, "spec.json")
    json.dump(spec, open(spec_path, "w"), ensure_ascii=False, indent=1)
    print(f"spec: {len(scenes)} scenes, {len(phrases)} phrases, {spec['duration']} s -> {spec_path}")
    env = dict(os.environ, REMOTION_BROWSER=BROWSER)
    base = ["npx", "remotion"]
    if args.frames:
        os.makedirs(os.path.join(work, "stills"), exist_ok=True)
        for f in args.frames.split(","):
            subprocess.run(base + ["still", "src/index.ts", "UIExplainer", os.path.join(work, "stills", f"f_{int(f):04d}.png"), f"--frame={f}", f"--props={spec_path}",
                                   f"--browser-executable={BROWSER}"], cwd=HERE, env=env, check=True, stdout=subprocess.DEVNULL)
        return
    raw = os.path.join(work, "_render.mp4")
    subprocess.run(base + ["render", "src/index.ts", "UIExplainer", raw, f"--props={spec_path}", "--concurrency=4", f"--browser-executable={BROWSER}", "--timeout=120000"],
                   cwd=HERE, env=env, check=True)
    out = args.out or os.path.join(ROOT, "exports", f"{name}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out], check=True)
    os.remove(raw)
    print("wrote", out)


if __name__ == "__main__":
    main()
