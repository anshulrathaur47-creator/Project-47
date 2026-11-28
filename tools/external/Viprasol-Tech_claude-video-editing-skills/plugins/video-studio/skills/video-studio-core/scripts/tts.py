#!/usr/bin/env python3
"""Offline text-to-speech for voice-overs (faceless / explainer styles).

Backends, tried in this order with --backend auto:
  kokoro   pip install kokoro soundfile          Apache-2.0 weights, best quality, CPU ok (~330 MB first run)
  piper    `piper` CLI on PATH + a voice .onnx   pip install piper-tts. NOTE: current piper (piper1-gpl) is
           GPL-3.0; each voice has its own licence (some non-commercial) - check the voice card
  sapi     Windows System.Speech via PowerShell   always present on Windows (e.g. "Microsoft David Desktop")
  say      macOS built-in
  espeak   espeak-ng on PATH                       robotic, GPL-3.0

usage: tts.py --text "Hello there" --out work/voice.wav [--voice NAME] [--rate 1.0] [--backend auto]
       tts.py --script script.txt --out work/voice.wav --words [--model base]
  --voice   kokoro: af_heart (default), am_adam, bf_emma...; piper: path to voice .onnx;
            sapi: "Microsoft Zira Desktop"; say: "Samantha"; espeak: "en-us"
  --words   time the words with faster-whisper (transcribe.py) and write <out dir>/words.json
            {"language","words":[{w,start,end}],"duration"}, using the script's own spelling.
            Without faster-whisper the words are spread over the speech by character length.
Output: 48 kHz mono WAV.
"""
import argparse, difflib, json, math, os, platform, re, shutil, subprocess, sys, tempfile
from vs_common import die, log, probe, run, save_json, load_json

HERE = os.path.dirname(os.path.abspath(__file__))
HINTS = {
    "kokoro": "pip install kokoro soundfile   (Apache-2.0; downloads the 82M model from Hugging Face on first run)",
    "piper": "pip install piper-tts, then download a voice (.onnx + .onnx.json) from "
             "https://huggingface.co/rhasspy/piper-voices and pass --voice path/to/voice.onnx  (GPL-3.0 engine)",
    "sapi": "Windows only (System.Speech). Add voices in Settings > Time & language > Speech",
    "say": "macOS only",
    "espeak": "install espeak-ng (winget install espeak-ng / apt install espeak-ng / brew install espeak-ng)",
}


def _to48k(src, out):
    run(["ffmpeg", "-y", "-hide_banner", "-i", src, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", out])


def have(backend):
    if backend == "kokoro":
        try:
            import kokoro  # noqa: F401
            return True
        except ImportError:
            return False
    if backend == "piper":
        return shutil.which("piper") is not None
    if backend == "sapi":
        return platform.system() == "Windows" and shutil.which("powershell") is not None
    if backend == "say":
        return platform.system() == "Darwin" and shutil.which("say") is not None
    if backend == "espeak":
        return shutil.which("espeak-ng") is not None
    return False


def tts_kokoro(text, out, voice, rate):
    import numpy as np
    from kokoro import KPipeline
    from audio_chain import write_wav
    voice = voice or "af_heart"
    pipe = KPipeline(lang_code=voice[0])
    chunks = [np.asarray(a, dtype=np.float32) for _, _, a in pipe(text, voice=voice, speed=rate)]
    tmp = out + ".24k.wav"
    write_wav(tmp, np.concatenate(chunks), 24000)
    _to48k(tmp, out)
    os.unlink(tmp)


def tts_piper(text, out, voice, rate):
    if not voice or not os.path.exists(voice):
        die("piper needs --voice path/to/voice.onnx. " + HINTS["piper"])
    tmp = out + ".piper.wav"
    p = subprocess.run(["piper", "--model", voice, "--output_file", tmp, "--length_scale", f"{1 / rate:.3f}"],
                       input=text, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        die(f"piper failed: {p.stderr[-400:]}")
    _to48k(tmp, out)
    os.unlink(tmp)


def tts_sapi(text, out, voice, rate):
    # SAPI Rate is -10..10; roughly x3 speed per 10 steps.
    r = max(-10, min(10, round(10 * math.log(rate) / math.log(3))))
    with tempfile.TemporaryDirectory() as td:
        tf = os.path.join(td, "text.txt")
        with open(tf, "w", encoding="utf-8") as fh:
            fh.write(text)
        raw = os.path.join(td, "sapi.wav")
        q = lambda s: "'" + s.replace("'", "''") + "'"
        ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              + (f"$s.SelectVoice({q(voice)}); " if voice else "")
              + f"$s.Rate = {r}; $s.SetOutputToWaveFile({q(raw)}); "
              f"$s.Speak([IO.File]::ReadAllText({q(tf)}, [Text.Encoding]::UTF8)); $s.Dispose()")
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
        if p.returncode != 0 or not os.path.exists(raw):
            die(f"SAPI failed: {p.stderr.strip()[-500:]}\nList voices: tts.py --list-voices")
        _to48k(raw, out)


def tts_say(text, out, voice, rate):
    with tempfile.TemporaryDirectory() as td:
        raw = os.path.join(td, "say.aiff")
        run(["say"] + (["-v", voice] if voice else []) + ["-r", str(int(175 * rate)), "-o", raw, text])
        _to48k(raw, out)


def tts_espeak(text, out, voice, rate):
    with tempfile.TemporaryDirectory() as td:
        raw = os.path.join(td, "es.wav")
        run(["espeak-ng", "-v", voice or "en-us", "-s", str(int(165 * rate)), "-w", raw, text])
        _to48k(raw, out)


BACKENDS = {"kokoro": tts_kokoro, "piper": tts_piper, "sapi": tts_sapi, "say": tts_say, "espeak": tts_espeak}


def list_voices():
    if have("sapi"):
        ps = ("Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer)"
              ".GetInstalledVoices() | % { $_.VoiceInfo.Name }")
        print(subprocess.run(["powershell", "-NoProfile", "-Command", ps], stdout=subprocess.PIPE, text=True).stdout)
    if have("say"):
        print(subprocess.run(["say", "-v", "?"], stdout=subprocess.PIPE, text=True).stdout)
    print("kokoro voices: af_heart af_bella am_adam am_michael bf_emma bm_george ... (if installed)")


def synthesize(text, out, voice=None, rate=1.0, backend="auto"):
    """Write `out` (48 kHz mono WAV). Returns the backend used."""
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if backend != "auto":
        if not have(backend):
            die(f"TTS backend '{backend}' is not available. Install: {HINTS[backend]}")
        BACKENDS[backend](text, out, voice, rate)
        return backend
    for b in BACKENDS:
        if have(b):
            if b == "piper" and not voice:
                continue  # piper needs a voice model path
            log(f"TTS backend: {b}" + ("" if b == "kokoro" else f"  (better quality: {HINTS['kokoro']})"))
            BACKENDS[b](text, out, voice if b != "kokoro" or (voice or "").count("_") else None, rate)
            return b
    die("no TTS backend found. Install one: " + "; ".join(f"{k}: {v}" for k, v in HINTS.items()))


def _norm(w):
    return re.sub(r"[^\w']", "", w.lower())


def word_times(script, wav, model="base"):
    """Word timings for the script's words: faster-whisper timings aligned with difflib; fallback = spread by length."""
    words = script.split()
    dur = probe(wav)["duration"]
    rec = []
    try:
        import faster_whisper  # noqa: F401
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable, os.path.join(HERE, "transcribe.py"), "--work", td, "--audio", wav,
                                "--model", model], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if p.returncode == 0:
                rec = load_json(os.path.join(td, "transcript.json"))["words"]
            else:
                log(f"transcribe.py failed, using estimated timings: {p.stderr.strip()[-300:]}")
    except ImportError:
        log("faster-whisper not installed (pip install faster-whisper): word timings are estimated")
    out = [None] * len(words)
    if rec:
        sm = difflib.SequenceMatcher(a=[_norm(w) for w in words], b=[_norm(w["w"]) for w in rec], autojunk=False)
        for a, b, n in sm.get_matching_blocks():
            for k in range(n):
                out[a + k] = (rec[b + k]["start"], rec[b + k]["end"])
    if not any(out):  # spread over the whole file by character length
        tot = sum(len(w) + 1 for w in words)
        t = 0.0
        for i, w in enumerate(words):
            d = dur * (len(w) + 1) / tot
            out[i] = (t, t + d)
            t += d
    # fill unmatched words by interpolating between their matched neighbours
    i = 0
    while i < len(out):
        if out[i] is None:
            j = i
            while j < len(out) and out[j] is None:
                j += 1
            s = out[i - 1][1] if i else 0.0
            e = out[j][0] if j < len(out) else dur
            step = (e - s) / (j - i)
            for k in range(i, j):
                out[k] = (s + (k - i) * step, s + (k - i + 1) * step)
            i = j
        i += 1
    return [{"w": w, "start": round(s, 3), "end": round(e, 3)} for w, (s, e) in zip(words, out)], dur


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text")
    ap.add_argument("--script")
    ap.add_argument("--out", default="work/voice.wav")
    ap.add_argument("--voice")
    ap.add_argument("--rate", type=float, default=1.0)
    ap.add_argument("--backend", default="auto", choices=["auto"] + list(BACKENDS))
    ap.add_argument("--words", action="store_true")
    ap.add_argument("--model", default="base", help="whisper model for --words")
    ap.add_argument("--list-voices", action="store_true")
    a = ap.parse_args()
    if a.list_voices:
        list_voices()
        raise SystemExit(0)
    text = a.text if a.text else (open(a.script, encoding="utf-8").read() if a.script else None)
    if not text or not text.strip():
        die("give --text or --script")
    used = synthesize(text.strip(), a.out, a.voice, a.rate, a.backend)
    log(f"{used}: {probe(a.out)['duration']:.2f}s -> {a.out}")
    if a.words:
        ws, dur = word_times(text.strip(), a.out, a.model)
        wp = os.path.join(os.path.dirname(os.path.abspath(a.out)), "words.json")
        save_json(wp, {"language": "en", "words": ws, "duration": round(dur, 3)})
        log(f"{len(ws)} words -> {wp}")
