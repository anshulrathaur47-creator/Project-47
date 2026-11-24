#!/usr/bin/env python3
"""The director: look at the footage, work out what kind of video it is, and decide how to edit it.

usage: director.py FILES_OR_FOLDER... [--goal "make reels for instagram"] [--platform reels] [--work W]
                   [--asr-seconds 150] [--model base] [--quick]

Measures every input (speech, language, faces, music/beat, shot rate, screen-recording look, light level,
orientation, duration, photos vs clips), scores every genre skill with reasons, and writes:
  W/director.json   facts + ranked choices + the exact run.py command
  W/director.md     the same, readable (Claude reads this, then follows the chosen genre skill)
Heuristics only: Claude makes the final call (see the video-director skill).
"""
import argparse, glob, json, os, re, subprocess, sys
import numpy as np
from vs_common import CORE, die, log, probe, save_json, load_json
from profile import asr_language, load as load_profile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(CORE)
VID = (".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm", ".mts", ".mxf")
IMG = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".tif", ".tiff")
AUD = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg")

# words that point at a genre (transcript, file names and the user's goal). Goal hits count double.
KEYWORDS = {
    "podcast-episode": "podcast episode guest host welcome show listeners",
    "clip-miner-pro": "clips shorts highlights viral moments",
    "tutorial-screen": "click install settings menu tab dashboard screen tutorial code terminal open button select",
    "saas-launch-demo": "app feature launch dashboard saas product demo signup",
    "product-review": "review unboxing specs battery camera price verdict pros cons",
    "recipe-video": "recipe cook cooking ingredients tablespoon teaspoon oven bake fry salt pan minutes boil",
    "fitness-video": "workout reps sets exercise squat push-up pushup cardio gym muscle stretch",
    "wedding-highlight": "wedding bride groom vows married ceremony reception bridesmaid",
    "wedding-india": "haldi mehndi sangeet pheras baraat nikah shaadi vidaai dulha dulhan",
    "real-estate-tour": "bedroom bathroom kitchen property listing square feet sqft apartment villa amenities",
    "travel-cinematic": "travel trip journey beach mountains city explore flight hotel",
    "sports-highlight": "goal match score team player game win season tournament",
    "gaming-vod": "game gaming level boss stream chat gameplay kill respawn",
    "interview-doc": "documentary interview tell me about remember story years ago",
    "conference-talk": "conference talk keynote slide audience thank you everyone session",
    "course-module": "lesson module course learn lecture students chapter",
    "news-explainer": "news report according government announced explained",
    "music-video": "song music video verse chorus",
    "lyric-video": "lyrics lyric song",
    "memorial-tribute": "memorial tribute remember loving memory passed away rip celebration of life",
    "event-recap": "event recap festival party concert launch meetup",
    "brand-film": "brand company mission founded team customers story",
    "testimonial-film": "testimonial customer recommend helped results",
    "ugc-ad-matrix": "ad ugc product link bio shop now discount",
    "ad-ladder": "commercial advert tvc 30 second spot cutdown bumper",
    "trailer-teaser": "trailer teaser coming soon",
    "kids-content": "kids children nursery rhyme toddler",
    "asmr-video": "asmr whisper tingles",
    "regional-devotional": "bhajan aarti devotional prayer mandir temple katha",
    "fashion-lookbook": "outfit fashion lookbook style wear collection",
    "localise-dub": "dub dubbing translate translation hindi version",
    "accessibility-pack": "accessibility subtitles sdh audio description",
    "vlog": "vlog today day my life morning",
    "retention-reel": "reel tips mistakes secret hack",
    "longform-retention": "youtube video long",
    "video-essay": "essay history analysis why",
    "reaction-duet": "reaction react reacting duet",
}
VERTICAL = {"reels", "reel", "tiktok", "shorts", "short", "instagram", "story", "stories", "vertical", "whatsapp"}
PLAT_WORDS = {"reels": ("reel", "instagram", "insta"), "tiktok": ("tiktok",), "shorts": ("shorts", "short"),
              "youtube": ("youtube",), "linkedin": ("linkedin",), "podcast": ("podcast", "spotify")}


# ---------------------------------------------------------------- measuring
def collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(f for f in glob.glob(os.path.join(p, "*")) if f.lower().endswith(VID + IMG + AUD))
        elif os.path.exists(p):
            files.append(p)
        else:
            die(f"not found: {p}")
    if not files:
        die("no media files found")
    return [os.path.abspath(f) for f in files]


def frames(path, n, width=640, dur=None):
    """n evenly spaced RGB frames (numpy) via ffmpeg, cheap."""
    dur = dur or probe(path)["duration"] or 1
    out = []
    for k in range(n):
        t = dur * (k + 0.5) / n
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1",
                            "-vf", f"scale={width}:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        if p.stdout:
            h = len(p.stdout) // (width * 3)
            out.append(np.frombuffer(p.stdout[:h * width * 3], np.uint8).reshape(h, width, 3))
    return out


def faces_in(rgbs):
    """(share of frames with a real face, most faces in one frame, largest face area as share of the frame).
    Confidence 0.6 and a minimum size keep UI shapes and logos from counting as faces."""
    try:
        import track as T
        det = T._detector(0.6)
    except Exception as e:  # mediapipe missing: no face facts
        log(f"face check skipped ({e})")
        return None, 0, 0.0
    hit, most, big = 0, 0, 0.0
    for f in rgbs:
        h, w = f.shape[:2]
        boxes = [b for b in T._detect_frame(det, np.ascontiguousarray(f)) if b[2] * b[3] >= 0.004 * w * h]
        hit += bool(boxes); most = max(most, len(boxes))
        big = max([big] + [b[2] * b[3] / (w * h) for b in boxes])
    return hit / max(1, len(rgbs)), most, round(big, 4)


def look(rgbs):
    """Light level, saturation and 'screen recording' cues (flat colour + sharp edges, little texture)."""
    import cv2
    luma, sat, flat, edges = [], [], [], []
    for f in rgbs:
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV)
        luma.append(float(hsv[..., 2].mean())); sat.append(float(hsv[..., 1].mean()))
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        lap = cv2.Laplacian(g, cv2.CV_32F)
        flat.append(float((np.abs(lap) < 2).mean()))           # share of perfectly flat pixels
        edges.append(float((np.abs(lap) > 40).mean()))         # crisp text/UI edges
    m = lambda a: round(float(np.mean(a)), 3) if a else 0.0
    return {"luma": m(luma), "saturation": m(sat), "flat": m(flat), "edges": m(edges),
            "screen_like": bool(flat and np.mean(flat) > 0.55 and np.mean(edges) > 0.01 and np.mean(sat) < 90)}


def speech(path, seconds, model, work):
    """Transcribe the first `seconds` with faster-whisper (transcribe.py) -> coverage, wpm, language, text."""
    os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, "probe16k.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-t", str(seconds), "-vn", "-ac", "1", "-ar", "16000", wav])
    if not os.path.exists(wav) or os.path.getsize(wav) < 2000:
        return None
    r = subprocess.run([sys.executable, os.path.join(HERE, "transcribe.py"), "--work", work, "--audio", wav, "--model", model],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    tp = os.path.join(work, "transcript.json")
    if r.returncode != 0 or not os.path.exists(tp):
        log("speech check skipped (transcription failed)")
        return None
    tr = load_json(tp)
    ws = tr.get("words", [])
    span = min(seconds, probe(wav)["duration"] or seconds)
    talk = sum(max(0.0, w["end"] - w["start"]) for w in ws)
    return {"words": len(ws), "coverage": round(min(1.0, talk / max(1, span) * 1.25), 3),  # words leave small gaps
            "wpm": round(len(ws) / max(1, span) * 60), "language": tr.get("language"),
            "text": " ".join(w["w"] for w in ws[:120])}


def music(path, seconds):
    """Beat regularity of the audio (music bed / song) using beats.py on a clip of the audio."""
    try:
        import beats as B
    except Exception:
        return None
    tmp = os.path.join(os.path.dirname(path), ".director_beat.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-t", str(seconds), "-vn", "-ac", "1", "-ar", "22050", tmp])
    try:
        r = B.track(tmp)
    except Exception:
        return None
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    bt = np.diff(r["beats"]) if len(r["beats"]) > 3 else np.array([1.0])
    steady = float(1 - min(1, np.std(bt) / max(1e-3, np.mean(bt))))
    onsets_ps = len(r["onsets"]) / max(1, r["duration"])
    return {"bpm": r["bpm"], "steady": round(steady, 3), "onsets_per_s": round(onsets_ps, 2)}


def measure(files, a):
    vids = [f for f in files if f.lower().endswith(VID)]
    imgs = [f for f in files if f.lower().endswith(IMG)]
    auds = [f for f in files if f.lower().endswith(AUD)]
    infos = {f: probe(f) for f in vids + auds}
    fx = {"files": len(files), "videos": len(vids), "images": len(imgs), "audio_files": len(auds),
          "total_s": round(sum(infos[f]["duration"] for f in vids), 1),
          "longest_s": round(max([infos[f]["duration"] for f in vids] or [0]), 1),
          "names": " ".join(os.path.splitext(os.path.basename(f))[0] for f in files)[:600]}
    main = max(vids, key=lambda f: infos[f]["duration"]) if vids else (auds[0] if auds else None)
    if vids:
        i = infos[main]
        fx.update(width=i.get("width"), height=i.get("height"), fps=round(i.get("fps", 0), 2),
                  orientation="portrait" if i["height"] > i["width"] else "square" if i["height"] == i["width"] else "landscape",
                  has_audio=any(infos[f]["has_audio"] for f in vids))
        sample = []
        for f in vids[:8]:
            sample += frames(f, 6 if len(vids) > 1 else 14, dur=infos[f]["duration"])
        fx["face_frac"], fx["max_faces"], fx["face_area"] = faces_in(sample)
        fx.update(look(sample))
        if not a.quick:
            import scenes as S
            sc = S.detect(main, 0.3, 0.5)
            n = len(sc.get("scenes", [])) - 1
            fx["cuts_per_min"] = round(max(0, n) / max(1e-3, infos[main]["duration"] / 60), 1)
    elif imgs:
        fx["orientation"] = "photos"
    src_audio = main if (main and (main in auds or infos[main]["has_audio"])) else None
    if src_audio:
        fx["speech"] = None if a.quick else speech(src_audio, a.asr_seconds, a.model, os.path.join(a.work, "probe"))
        fx["music"] = music(src_audio, min(90, a.asr_seconds))
    if auds and (src_audio != auds[0] or imgs):  # a track next to clips/photos is the soundtrack
        fx["music_file"] = auds[0]
    return fx, main


# ---------------------------------------------------------------- deciding
def genre_skills():
    return {d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md"))
            and not os.path.exists(os.path.join(SKILLS, d, "theme.json")) and d != "video-studio-core"}


def score(fx, goal):
    sp = fx.get("speech") or {}
    cov, wpm = sp.get("coverage", 0.0), sp.get("wpm", 0)
    mus = fx.get("music") or {}
    musical = bool(mus) and mus.get("steady", 0) > 0.8 and cov < 0.35
    faces, most = fx.get("face_frac") or 0.0, fx.get("max_faces") or 0
    dur, vids, imgs = fx.get("longest_s", 0), fx.get("videos", 0), fx.get("images", 0)
    S, why = {}, {}

    def add(g, pts, reason):
        S[g] = S.get(g, 0) + pts
        why.setdefault(g, []).append(reason)

    talking = cov >= 0.45
    if talking and faces >= 0.4 and most >= 2:
        add("podcast-episode", 5 if dur > 600 else 3, f"{most} faces on screen and {cov:.0%} speech")
        add("clip-miner-pro", 3 if dur > 600 else 1, "long multi-person talk is a source of short clips")
        add("interview-doc", 2, "two people talking (interview)")
    if talking and faces >= 0.4 and most <= 1:
        if dur <= 120:
            add("retention-reel", 6, f"one person talking for {dur:.0f}s")
        elif dur <= 1500:
            add("longform-retention", 3, f"one person talking for {dur / 60:.1f} min")
            add("vlog", 3, "single presenter, mid-length")
        else:
            add("clip-miner-pro", 4, f"{dur / 60:.0f} min of talk: mine the best moments")
            add("conference-talk", 2, "very long single speaker")
    screen = fx.get("screen_like") and (faces < 0.5 or (fx.get("face_area") or 0) < 0.03)
    if talking and screen:
        add("tutorial-screen", 6, "screen-recording look (flat UI, crisp edges) with narration")
        add("saas-launch-demo", 2, "screen content with voice")
    if talking and faces < 0.2 and not screen and vids:
        add("video-essay", 3, "voice over pictures, no presenter on camera")
        add("faceless-explainer", 2, "narration without a face")
    if not vids and fx.get("audio_files") and cov >= 0.45:
        add("faceless-explainer", 6, "voice recording with no video")
    if not vids and not imgs and fx.get("audio_files") and musical:
        add("lyric-video", 4, "a song with no video")
    if imgs >= 3 and not vids:
        add("memorial-tribute", 2, f"{imgs} photos (tribute / slideshow)")
        add("event-recap", 3 if fx.get("audio_files") else 2, f"{imgs} photos" + (" + a music track: photo montage on the beat" if fx.get("audio_files") else " for a music montage"))
        add("real-estate-tour", 1, "photo tour")
    if vids >= 3 and not talking:
        add("event-recap", 4, f"{vids} clips without much talk: montage on music")
        add("travel-cinematic", 3, "many b-roll clips")
        if musical:
            add("music-video", 1, "steady beat under the clips")
    if vids == 1 and musical and faces >= 0.3:
        add("music-video", 5, f"steady {mus.get('bpm', 0):.0f} BPM music with a performer on screen")
    if vids and not fx.get("has_audio", True):
        add("travel-cinematic", 2, "silent clips: cut to music")
        add("event-recap", 2, "silent clips: montage")
    if fx.get("cuts_per_min", 0) > 20 and not talking:
        add("sports-highlight", 1, "fast cutting/motion")
        add("gaming-vod", 1, "fast visual changes")
    # words: transcript, file names, the user's goal (strongest signal)
    text = " ".join([sp.get("text", ""), fx.get("names", "")]).lower()
    gl = (goal or "").lower()
    for g, kws in KEYWORDS.items():
        hits = [k for k in kws.split() if re.search(rf"\b{re.escape(k)}", text)]
        ghits = [k for k in kws.split() if re.search(rf"\b{re.escape(k)}", gl)]
        if hits:
            add(g, min(4, len(hits)), "words: " + ", ".join(hits[:5]))
        if ghits:
            add(g, 6 * min(2, len(ghits)), "your goal says: " + ", ".join(ghits[:4]))
    if not S:
        add("vlog" if vids else "event-recap", 1, "no strong signal: general-purpose edit")
    allowed = genre_skills()
    ranked = sorted(((g, s) for g, s in S.items() if g in allowed), key=lambda x: -x[1])
    return [{"skill": g, "score": s, "why": why[g]} for g, s in ranked]


def platform_of(goal, fx, skill):
    gl = (goal or "").lower()
    for p, ws in PLAT_WORDS.items():
        if any(re.search(rf"\b{w}", gl) for w in ws):
            return p
    if skill in ("podcast-episode",):
        return "youtube"
    if fx.get("orientation") == "portrait" or skill in ("retention-reel", "clip-miner-pro", "ugc-ad-matrix", "micro-drama"):
        return "reels"
    return "youtube"


def plan_command(choice, fx, main, files, goal, platform):
    skill = choice["skill"]
    try:
        gen = json.load(open(os.path.join(HERE, "genres.json"), encoding="utf-8"))
        g = gen.get("genres", gen).get(skill, {})
    except Exception:
        g = {}
    skins = [s for s in g.get("styles", []) if os.path.exists(os.path.join(SKILLS, s, "theme.json"))] or ["halo-cut"]
    vertical = platform in ("reels", "tiktok", "shorts") or (goal and any(w in goal.lower() for w in VERTICAL))
    fmt = "9:16" if vertical else (g.get("aspect") or "16:9")
    vids = [f for f in files if f.lower().endswith(VID)]
    imgs = [f for f in files if f.lower().endswith(IMG)]
    q = lambda p: f'"{p}"' if " " in p else p
    flags = ["--style", f"SKILLS/{skins[0]}", "--genre", skill, "--format", fmt]
    talking = (fx.get("speech") or {}).get("coverage", 0) >= 0.45
    music_file = fx.get("music_file")
    if len(vids) + len(imgs) > 1:
        inp = "-"
        flags = ["--clips"] + [q(f) for f in vids + imgs] + ["--auto", "story" if talking else "montage"] + flags
        if music_file:
            flags += ["--music", q(music_file)]
    else:
        inp = q(main) if main else "INPUT"
        if talking:
            flags += ["--smart-cuts", "--retakes"]
        if fx.get("orientation") == "landscape" and fmt == "9:16" and (fx.get("face_frac") or 0) >= 0.3:
            flags += ["--reframe", "9:16"]
        if music_file:
            flags += ["--music", q(music_file)]
        if fx.get("luma", 255) < 70:
            flags += ["--denoise", "light"]
    flags += ["--platform", platform, "--work", f"edit-{skill}", "--stop-after", "plan"]
    # never forward a ur/pa/sd/ne mis-ID for Hindi-belt speech: the creator profile language wins (default hi)
    lang = asr_language((fx.get("speech") or {}).get("language"))
    if lang and lang != "en":
        flags += ["--language", lang]
    return {"skin": skins[0], "alt_skins": skins[1:4], "format": fmt, "platform": platform,
            "command": f"python CORE/scripts/run.py {inp} " + " ".join(flags)}


def report_md(fx, ranked, rec, ask):
    sp = fx.get("speech") or {}
    mus = fx.get("music") or {}
    L = ["# Director's read", "", "## What the footage is", ""]
    L.append(f"- **Inputs:** {fx['videos']} video, {fx['images']} photo, {fx['audio_files']} audio; longest {fx['longest_s']} s, total {fx['total_s']} s")
    if fx.get("width"):
        L.append(f"- **Picture:** {fx['width']}x{fx['height']} {fx.get('orientation')}, {fx.get('fps')} fps, light {fx.get('luma')}/255"
                 + (", looks like a screen recording" if fx.get("screen_like") else ""))
        L.append(f"- **People:** faces in {fx.get('face_frac') or 0:.0%} of sampled frames, up to {fx.get('max_faces')} at once")
        if "cuts_per_min" in fx:
            L.append(f"- **Shots:** {fx['cuts_per_min']} cuts/min already in the source")
    if sp:
        L.append(f"- **Speech:** {sp.get('coverage', 0):.0%} of the opening is talk, {sp.get('wpm')} wpm, language `{sp.get('language')}`")
        L.append(f"- **Opening words:** \"{sp.get('text', '')[:300]}\"")
    if mus:
        L.append(f"- **Music/beat:** ~{mus.get('bpm', 0):.0f} BPM, steadiness {mus.get('steady')}")
    L += ["", "## Ranked choices", "", "| skill | score | why |", "| --- | --- | --- |"]
    for r in ranked[:5]:
        L.append(f"| `{r['skill']}` | {r['score']} | {'; '.join(r['why'])} |")
    if rec:
        L += ["", "## Recommended edit", "",
              f"- **Genre skill:** `{rec['skill']}` (read `SKILLS/{rec['skill']}/SKILL.md` and follow it)",
              f"- **Skin:** `{rec['skin']}` (alternatives: {', '.join(rec['alt_skins']) or '-'})",
              f"- **Format / platform:** {rec['format']} for {rec['platform']}", "", "```bash", rec["command"], "```"]
    if ask:
        L += ["", "## Ask the user (one question)", "", ask]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--goal", default="", help="what the user asked for, in their words")
    ap.add_argument("--platform", default=None)
    ap.add_argument("--work", default="director")
    ap.add_argument("--asr-seconds", type=int, default=150, help="seconds of audio to transcribe for the read")
    ap.add_argument("--model", default="base")
    ap.add_argument("--quick", action="store_true", help="skip transcription and shot detection")
    a = ap.parse_args()
    a.work = os.path.abspath(a.work)
    os.makedirs(a.work, exist_ok=True)
    files = collect(a.inputs)
    log(f"reading {len(files)} file(s)")
    fx, main_file = measure(files, a)
    ranked = score(fx, a.goal)
    rec, ask = None, None
    if ranked:
        top = ranked[0]
        plat = a.platform or platform_of(a.goal, fx, top["skill"])
        rec = dict(top, **plan_command(top, fx, main_file, files, a.goal, plat))
        if len(ranked) > 1 and ranked[1]["score"] >= top["score"] * 0.85 and not a.goal:
            ask = (f"Close call between `{top['skill']}` and `{ranked[1]['skill']}`. Ask what the video is for "
                   f"(one question), or go with `{top['skill']}`.")
    if load_profile()["script"] == "Deva" and re.search(r"[؀-ۿ਀-੿]", (fx.get("speech") or {}).get("text", "")):
        ask = ("The speech came out in Urdu/Punjabi script, not Devanagari. Ask the user for their exact words (one line "
               "per phrase) and run `transcribe.py --text FILE` so the captions use them.")
    out = {"facts": fx, "ranked": ranked, "recommendation": rec, "ask": ask, "goal": a.goal}
    save_json(os.path.join(a.work, "director.json"), out)
    open(os.path.join(a.work, "director.md"), "w", encoding="utf-8").write(report_md(fx, ranked, rec, ask))
    if rec:
        log(f"recommend: {rec['skill']} + skin {rec['skin']} ({rec['format']}, {rec['platform']})")
        log(rec["command"])
    log(f"read -> {os.path.join(a.work, 'director.md')}")


if __name__ == "__main__":
    main()
