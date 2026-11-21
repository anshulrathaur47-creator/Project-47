#!/usr/bin/env python3
"""Transcribe audio/video with Whisper (faster-whisper) into captions.

Writes <name>.srt, <name>.vtt, <name>.txt and <name>.words.json (word-level
timestamps, handy for syncing lyrics, cuts and signs) next to --out.

Usage:
  python3 tools/transcribe.py assets/music/song.mp3                 # auto language
  python3 tools/transcribe.py clip.mp4 --lang hi --out references/  # Hindi
  python3 tools/transcribe.py clip.mp4 --task translate             # to English
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(HERE, "models", "whisper-small-int8")


def ts(sec, sep=","):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="audio or video file")
    ap.add_argument("--lang", default=None, help="language code, e.g. hi, en (default: auto-detect)")
    ap.add_argument("--task", default="transcribe", choices=["transcribe", "translate"])
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="model folder or faster-whisper model name (default: bundled whisper small int8)")
    ap.add_argument("--out", default=None, help="output folder (default: next to the input)")
    ap.add_argument("--no-vad", action="store_true", help="disable voice-activity filtering (try for songs)")
    args = ap.parse_args()

    if not os.path.exists(args.model) and os.sep in args.model:
        sys.exit(f"Model not found at {args.model}. Run tools/setup.sh first.")

    from faster_whisper import WhisperModel

    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    segments, info = model.transcribe(args.input, language=args.lang, task=args.task,
                                      word_timestamps=True, vad_filter=not args.no_vad, beam_size=5)
    segments = list(segments)

    base = os.path.splitext(os.path.basename(args.input))[0]
    out_dir = args.out or os.path.dirname(os.path.abspath(args.input))
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, base)

    with open(stem + ".srt", "w", encoding="utf-8") as f:
        for i, s in enumerate(segments, 1):
            f.write(f"{i}\n{ts(s.start)} --> {ts(s.end)}\n{s.text.strip()}\n\n")
    with open(stem + ".vtt", "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for s in segments:
            f.write(f"{ts(s.start, '.')} --> {ts(s.end, '.')}\n{s.text.strip()}\n\n")
    with open(stem + ".txt", "w", encoding="utf-8") as f:
        f.write("\n".join(s.text.strip() for s in segments) + "\n")
    with open(stem + ".words.json", "w", encoding="utf-8") as f:
        json.dump({"language": info.language, "duration": info.duration,
                   "segments": [{"start": s.start, "end": s.end, "text": s.text.strip(),
                                 "words": [{"start": w.start, "end": w.end, "word": w.word.strip()}
                                           for w in (s.words or [])]} for s in segments]},
                  f, ensure_ascii=False, indent=1)

    print(f"language={info.language} ({info.language_probability:.2f}), {len(segments)} segments")
    for s in segments:
        print(f"[{ts(s.start)} -> {ts(s.end)}] {s.text.strip()}")
    print(f"wrote {stem}.srt / .vtt / .txt / .words.json")


if __name__ == "__main__":
    main()
