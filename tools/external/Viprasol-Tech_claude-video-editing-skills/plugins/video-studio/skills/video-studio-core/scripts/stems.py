#!/usr/bin/env python3
"""Stem separation with Demucs (optional). Splits a mix into vocals + music (or 4 stems).
Uses: pull music out from under dialogue, karaoke beds, drums-only builds, dubbing (music + effects bed).

usage: stems.py INPUT [--out work/stems] [--four] [--model htdemucs]
  two stems (default): <out>/vocals.wav and <out>/music.wav (= everything but vocals)
  --four:              <out>/vocals.wav drums.wav bass.wav other.wav
Install: pip install demucs   (MIT code; CPU works but is slow, roughly 1-3x real time; first run
downloads the model ~80 MB). Check the music licence allows modification before splitting it.
"""
import argparse, glob, os, shutil, subprocess, sys, tempfile
from vs_common import die, log

HINT = "pip install demucs   (MIT; CPU is slow, ~1-3x real time; model downloads on first run)"


def available():
    try:
        import demucs  # noqa: F401
        return [sys.executable, "-m", "demucs"]
    except ImportError:
        return ["demucs"] if shutil.which("demucs") else None


def separate(inp, out_dir, four=False, model="htdemucs"):
    """Run demucs and copy stems into out_dir. Returns {stem: path}."""
    cmd = available()
    if not cmd:
        die(f"demucs is not installed. {HINT}")
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        args = cmd + ["-n", model, "-o", td, "-d", "cpu"] + ([] if four else ["--two-stems=vocals"]) + [inp]
        log(f"separating stems with demucs ({model}) - this is slow on CPU")
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
        if p.returncode != 0:
            die(f"demucs failed: {p.stderr.strip()[-600:]}")
        res = {}
        for f in glob.glob(os.path.join(td, model, "*", "*.wav")):
            name = os.path.splitext(os.path.basename(f))[0]
            name = "music" if name == "no_vocals" else name
            res[name] = os.path.join(out_dir, f"{name}.wav")
            shutil.copy(f, res[name])
    log(f"stems: {', '.join(sorted(res))} -> {out_dir}")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp")
    ap.add_argument("--out", default="work/stems")
    ap.add_argument("--four", action="store_true")
    ap.add_argument("--model", default="htdemucs")
    a = ap.parse_args()
    if not os.path.exists(a.inp):
        die(f"{a.inp} not found")
    separate(a.inp, a.out, a.four, a.model)
