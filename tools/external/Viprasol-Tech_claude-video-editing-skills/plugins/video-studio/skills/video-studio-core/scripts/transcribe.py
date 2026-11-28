#!/usr/bin/env python3
"""Word-level transcription with faster-whisper (runs locally, free).
Writes <work>/transcript.json : {"language", "words":[{"w","start","end"}], "segments":[{"text","start","end"}]}

usage: transcribe.py --work WORKDIR [--model small] [--language en] [--audio path]
       transcribe.py --work WORKDIR --from-srt subs.srt     (import existing subtitles instead)
       transcribe.py --work WORKDIR --text lines.txt [--asr-words WORK/asr.json]
           your exact words (lyrics / shayari / script, one line per phrase) placed on the ASR word timings;
           writes transcript.json + words.json with your words and the raw ASR to asr.json (re-align from it
           with --asr-words, no new ASR run). Run it on the audio you will render (--audio cut.mp4 after autocut).
       transcribe.py --self-test

Models: tiny, base, small (default), medium, large-v3. Bigger = slower, more accurate.
First run downloads the model from Hugging Face (~460 MB for small).
No --language: a detection of ur/pa/sd/ne (common mis-IDs for Hindi/Haryanvi) becomes the creator profile
language (profile.py, default hi) so captions come out in Devanagari.
"""
import argparse, difflib, os, re, unicodedata
from vs_common import save_json, load_json, log, die, norm, probe
from profile import asr_language, load as load_profile

ap = argparse.ArgumentParser()
ap.add_argument("--work", default="work")
ap.add_argument("--audio", default=None)
ap.add_argument("--model", default="small")
ap.add_argument("--language", default=None)
ap.add_argument("--from-srt", default=None)
ap.add_argument("--no-vad", action="store_true", help="keep Whisper's voice filter off (dialects, singing, noisy outdoor speech it may skip)")
ap.add_argument("--prompt", default=None, help="initial prompt: names/jargon to spell correctly")
ap.add_argument("--text", default=None, help="your exact words, one line per phrase: replace the ASR words, keep its timing")
ap.add_argument("--asr-words", default=None, help="with --text: take the timing from this asr.json, no new ASR run")
ap.add_argument("--self-test", action="store_true")
a = ap.parse_args()
out_path = os.path.join(a.work, "transcript.json")


def srt_time(s):
    hh, mm, rest = s.replace(",", ".").split(":")
    return int(hh) * 3600 + int(mm) * 60 + float(rest)


if a.from_srt:
    # Spread each subtitle's words evenly across its time span.
    txt = open(a.from_srt, encoding="utf-8").read()
    blocks = re.split(r"\n\s*\n", txt.strip())
    words, segs = [], []
    for b in blocks:
        lines = b.strip().splitlines()
        tl = next((l for l in lines if "-->" in l), None)
        if not tl:
            continue
        s, e = [srt_time(x.strip().split(" ")[0]) for x in tl.split("-->")]
        text = " ".join(l for l in lines[lines.index(tl) + 1:]).strip()
        ws = text.split()
        if not ws:
            continue
        step = (e - s) / len(ws)
        for i, w in enumerate(ws):
            words.append({"w": w, "start": round(s + i * step, 3), "end": round(s + (i + 1) * step, 3)})
        segs.append({"text": text, "start": s, "end": e})
    save_json(out_path, {"language": a.language or load_profile()["language"], "words": words, "segments": segs})
    log(f"imported {len(words)} words from {a.from_srt}")
    raise SystemExit(0)


def glen(s):
    """Visible length: base characters only (Devanagari vowel signs / virama are marks and add no width)."""
    return max(1, sum(1 for ch in norm(s) if not unicodedata.category(ch).startswith("M")))


def align_text(lines, asr):
    """Put the user's words (one phrase per line) on ASR word timings. difflib matches normalised words and hands
    every matched/replaced ASR word to a user line (unmatched ASR words, e.g. hallucinated tails, are dropped).
    A line with as many ASR words as its own words takes their times 1:1; otherwise its span is shared out by
    character length. A line with no ASR words goes into the gap between its neighbours. -> (words, segments)
    ponytail: word-level difflib, no acoustics; a CTC forced aligner (audit-brain C1a) is the upgrade path."""
    toks = [(n, t) for n, line in enumerate(lines) for t in line.split()]
    if not toks:
        die("--text file has no words")
    if not asr:
        die("no ASR words to align the text to (silent audio, or VAD dropped it: try --no-vad)")
    sm = difflib.SequenceMatcher(None, [norm(w["w"]) for w in asr], [norm(t) for _, t in toks], autojunk=False)
    got = [[] for _ in lines]
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ("equal", "replace"):
            for i in range(i1, i2):
                got[toks[j1 + (i - i1) * (j2 - j1) // (i2 - i1)][0]].append(asr[i])
    span = [(min(w["start"] for w in g), max(w["end"] for w in g)) if g else None for g in got]
    for n, line in enumerate(lines):
        if span[n] is None:
            prev = span[n - 1][1] if n else 0.0
            nxt = next((sp[0] for sp in span[n + 1:] if sp), prev + 0.35 * len(line.split()))
            if nxt - prev < 0.2:
                die(f"text line {n + 1} '{line}' matched no speech and has no room between its neighbours: "
                    "check the text against the audio")
            log(f"warning: text line {n + 1} '{line}' matched no speech; placed in the gap {prev:.2f}-{nxt:.2f}s")
            span[n] = (prev, nxt)
    words, segs = [], []
    for n, line in enumerate(lines):
        ut, (s, e) = line.split(), span[n]
        if len(got[n]) == len(ut):
            times = [(w["start"], w["end"]) for w in got[n]]
        else:
            cum = [0]
            for t in ut:
                cum.append(cum[-1] + glen(t))
            times = [(s + (e - s) * cum[k] / cum[-1], s + (e - s) * cum[k + 1] / cum[-1]) for k in range(len(ut))]
        words += [{"w": t, "start": round(t0, 3), "end": round(t1, 3), "p": 1.0, "line": n} for t, (t0, t1) in zip(ut, times)]
        segs.append({"text": line, "start": round(s, 3), "end": round(e, 3)})
    return words, segs


def save_text_result(lines, asr, lang, audio):
    words, segs = align_text(lines, asr)
    save_json(os.path.join(a.work, "asr.json"), {"language": lang, "words": asr})
    save_json(out_path, {"language": lang, "words": words, "segments": segs, "text": os.path.abspath(a.text)})
    dur = probe(audio)["duration"] if audio and os.path.exists(audio) else words[-1]["end"]
    save_json(os.path.join(a.work, "words.json"), {"language": lang, "words": words, "duration": round(dur, 3)})
    log(f"{len(words)} words from {a.text} on {len(asr)} ASR words ({len(lines)} lines), language={lang} -> {out_path}"
        f" + words.json. Re-align edited text: --text FILE --asr-words {os.path.join(a.work, 'asr.json')}")


def _self_test():
    W = lambda w, s, e: {"w": w, "start": s, "end": e}
    asr = [W("हर", 0, .3), W("बात", .3, .6), W("ती", .6, .8), W("राबर", .8, 1.0), W("की", 1.0, 1.2), W("राशि", 1.9, 2.3),
           W("है", 2.3, 2.5), W("फकी", 2.5, 2.9), W("बरगी", 2.9, 3.3), W("Thank", 5, 5.2), W("you", 5.2, 5.4)]
    ws, sg = align_text(["हर बात तीरा बरगी,", "राशि है फकीरा बरगी"], asr)
    assert [w["w"] for w in ws][2:4] == ["तीरा", "बरगी,"] and len(ws) == 8 and len(sg) == 2
    assert ws[0]["start"] == 0 and ws[3]["end"] == 1.2 and ws[3]["start"] > ws[2]["start"]   # 5 ASR -> 4 words: by length
    assert (ws[6]["w"], ws[6]["start"], ws[6]["end"]) == ("फकीरा", 2.5, 2.9) and ws[-1]["end"] == 3.3   # 1:1, tail dropped
    assert ws[4]["line"] == 1 and sg[1] == {"text": "राशि है फकीरा बरगी", "start": 1.9, "end": 3.3}
    ws, sg = align_text(["हर बात", "अनसुनी लाइन", "राशि है"], [asr[0], asr[1], asr[5], asr[6]])
    assert (sg[1]["start"], sg[1]["end"], ws[2]["start"], ws[3]["end"]) == (0.6, 1.9, 0.6, 1.9)   # unheard line: in the gap
    assert glen("राशि") == 2 and glen("फकीरा") == 3 and glen("hello") == 5
    print("transcribe.py self-test ok")


if a.self_test:
    _self_test()
    raise SystemExit(0)
lines = None
if a.text:
    lines = [ln.strip() for ln in open(a.text, encoding="utf-8-sig").read().splitlines() if ln.strip()]
    if not lines:
        die(f"{a.text} has no text lines")
if a.asr_words:
    if not lines:
        die("--asr-words needs --text")
    _asr = load_json(a.asr_words)
    save_text_result(lines, _asr["words"], asr_language(_asr.get("language"), a.language), a.audio)
    raise SystemExit(0)

try:
    from faster_whisper import WhisperModel
except ImportError:
    die("faster-whisper is not installed. Run: pip install faster-whisper")

audio = a.audio or os.path.join(a.work, "audio16k.wav")
if not os.path.exists(audio):
    die(f"{audio} not found. Run prep.py first.")

device, ctype = "cpu", "int8"
try:
    import ctranslate2
    if ctranslate2.get_cuda_device_count() > 0:
        device, ctype = "cuda", "float16"
except Exception:
    pass
log(f"loading whisper '{a.model}' on {device}")
model = WhisperModel(a.model, device=device, compute_type=ctype)


def load_pcm(path):
    """Decode to 16 kHz mono float32 with FFmpeg. Passing an array instead of a path avoids
    faster-whisper's PyAV decoder, which breaks whenever the installed PyAV version changes its API."""
    import subprocess
    import numpy as np
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        die(f"cannot decode {path}: {p.stderr.decode(errors='ignore')[-400:]}")
    return np.frombuffer(p.stdout, dtype=np.float32)


pcm = load_pcm(audio)
kw = dict(word_timestamps=True, vad_filter=not a.no_vad, initial_prompt=a.prompt, condition_on_previous_text=False)
segments, info = model.transcribe(pcm, language=a.language, **kw)   # lazy generator: only language detection ran
lang = asr_language(info.language, a.language)
if lang != info.language:
    log(f"detected '{info.language}' (p={info.language_probability:.2f}), a common mis-ID for Hindi-belt speech: "
        f"using profile language '{lang}' (pass --language {info.language} to keep it)")
    segments, info = model.transcribe(pcm, language=lang, **kw)
words, segs = [], []
for seg in segments:
    segs.append({"text": seg.text.strip(), "start": round(seg.start, 3), "end": round(seg.end, 3)})
    for w in seg.words or []:
        t = w.word.strip()
        if t:
            words.append({"w": t, "start": round(w.start, 3), "end": round(w.end, 3), "p": round(w.probability, 3)})
# Whisper sometimes hallucinates on short or dialect clips: symbol-only tokens ("༼") or the same token repeated
# many times. Drop tokens with no letters/digits and any run of >3 identical tokens.
import re as _re
_clean, _run = [], 0
for _w in words:
    if not _re.search(r"\w", _w["w"]):
        continue
    _run = _run + 1 if _clean and _clean[-1]["w"] == _w["w"] else 0
    if _run < 3:
        _clean.append(_w)
if len(_clean) < len(words):
    log(f"dropped {len(words) - len(_clean)} hallucinated/repeated tokens")
words = _clean
# Whisper splits "$10,000" -> "$10" ",000." and "50%" -> "50" "%": glue them so captions/counters see one word
from captions import merge_tokens
words = [dict(m, start=round(m["start"], 3), end=round(m["end"], 3)) for m in merge_tokens(words)]
if lines:
    save_text_result(lines, words, lang, audio)
    raise SystemExit(0)
if load_profile()["script"] == "Deva" and re.search(r"[؀-ۿ਀-੿]", " ".join(w["w"] for w in words)):
    log("warning: captions came out in Urdu/Punjabi script. Give the exact words with --text FILE "
        "(one line per phrase) or try --model medium")
save_json(out_path, {"language": lang, "words": words, "segments": segs})
log(f"{len(words)} words, language={lang} -> {out_path}")
