# align-lyrics

Word timings for a song that already has a hand-stamped line `.lrc` (from
[lyrics-sync](https://lyrics-sync.arda.tr)). Everything runs locally on the CPU; no audio
leaves the machine.

1. Isolate the vocals with Demucs (`htdemucs`, two stems).
2. Force-align the known lyrics with torchaudio's `MMS_FA` (wav2vec2 CTC, multilingual):
   each line inside its own hand-stamped window, then again together with its neighbours
   in a wider window as a check.
3. Write `<name>.aligned.lrc` (line LRC, voice tags kept) and `<name>.words.json`
   (per-word start/end) next to the hand `.lrc`. The hand `.lrc` is never touched.

## Setup (cachyos, once)

```bash
uv venv -p 3.12 .venv   # outside the repo is fine too
uv pip install -p .venv/bin/python --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 torchaudio==2.8.0
uv pip install -p .venv/bin/python demucs soundfile numpy
```

CPU builds on purpose: the Radeon is shared (see `~/CLAUDE.md`). The MMS_FA model
(1.2 GB) downloads on first use.

## Run

```bash
.venv/bin/python -m demucs -n htdemucs --two-stems vocals -o stems --filename '{track}.{stem}.{ext}' "song.flac"
.venv/bin/python scripts/align-lyrics/align_lyrics.py "stems/htdemucs/song.vocals.wav" "song.lrc" --out out --title "Song" --audio-name "song.flac"
```

About 1 min of CPU per minute of audio for Demucs, ~3 min per song for the alignment
emissions (cached next to the stem as `*.mmsfa.pt`, so reruns take seconds).

## Reading the JSON

Same shape as the Seventh Shadow files: `title, audio, source_lrc, method, generated,
units, notes, confidence, lines[i, tag, text, start, end, hand_start, dev, confidence,
words[w, start, end, score]]`, plus:

- `rating` (`high` / `medium` / `low`) and `summary.word_agreement`: share of words whose
  start the two passes put within 0.35 s. This is the confidence to trust. The CTC
  `score` / `confidence` runs low on sung vowels and screams even when the timing is right.
- `summary.check_lines`: 1-based lines where fewer than 60% of the words agree. Fix these by hand.
- per line `source`: `aligned` (start = first word) or `hand` (kept the hand stamp because
  the words did not agree or the shift was over 0.6 s).
- per word `agree`, `from` (`anchored` or `context`: where the passes disagreed, the
  context timing is used when it keeps the word order), `context_start`, `global_start`
  (an unanchored whole-song pass, informational only).
