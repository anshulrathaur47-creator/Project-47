# Audio reference (finish pass)

Scripts: `audio_chain.py` (dialogue chain, SFX, ducking, loudness, mix graph), `beats.py` (beats, downbeats,
onsets, waveform peaks), `music_fit.py` (cut music to an exact length on bar lines), `tts.py` (offline
voice-over), `stems.py` (Demucs separation). All free and local: FFmpeg + numpy.

## Plan fields

```json
"audio": {
  "platform": "youtube",            // loudness target, see table (default youtube)
  "lufs": -14, "tp": -1, "lra": 11,  // optional overrides of the platform numbers
  "voice": {"denoise": "light", "eq": "clear", "deess": true, "voice": "male"},   // false = no dialogue chain
  "roomTone": true                   // same as top-level "roomTone"
},
"roomTone": true,                    // fill autocut joins with matched room tone (needs <work>/cutlist.json)
"sfx":   [{"t": 1.2, "kind": "whoosh", "gain": 0.5}, {"t": 3, "file": "my_hit.wav", "gain": 0.6}],
"music": {"src": "music.mp3",
          "volume": 0.12,            // linear bed gain (legacy), or
          "under": 20,               // bed sits N LU under the processed dialogue (measured; preferred)
          "duck": true,              // true | "speech-aware" | false
          "duckDepth": 10, "duckAttack": 20, "duckRelease": 700, "speechDuck": 4,
          "start": 0, "fadeOut": 1.5, // legacy loop + trim + fade
          "fitTo": "beats",          // cut to the video length on bar lines, ending on a downbeat
          "endButton": true}         // end on a hit + short ring instead of a fade (implies fitTo)
```
Old plans (only `sfx` and `music` with src/volume/duck/start/fadeOut) render as before, plus the default
dialogue chain (HPF 80 Hz + light afftdn + 3:1 compressor) and measured loudness.

## Platform targets (`LOUDNESS`)

| key | LUFS | dBTP | LRA | note |
|---|---|---|---|---|
| youtube, facebook | -14 | -1 | 11 | observed, not published; YouTube only turns loud uploads down |
| tiktok, reels/instagram, shorts, social | -14 | -1 | 7 | no published number; phone speakers |
| spotify | -14 | -1 | 9 | official; -2 dBTP if master is louder than -14 |
| podcast, apple | -16 | -1 | 8 | Apple ±1 LU; mono podcasts -19 |
| broadcast-eu (ebu) | -23 | -1 | 15 | EBU R128 ±0.5 LU |
| broadcast-us (atsc) | -24 | -2 | 15 | ATSC A/85 |
| netflix | -27 | -2 | 18 | dialogue-gated ±2 LU; we measure full programme, so approximate |
| cinema | -27 | -2 | 20 | no LUFS spec (85 dB SPL calibrated room); nearest proxy |

The mix graph measures the premix once and applies an exact linear gain into an oversampled limiter
(ceiling = TP − 0.5 dB for AAC). Two-pass on a finished file: `audio_chain.py loudnorm IN OUT --platform podcast`.

## Dialogue chain (`voice_chain`)

Order: highpass → de-hum → de-click → de-noise → EQ → de-ess → gate → compressor → soft limiter.
- `voice`: male HPF 80 Hz, female 110 Hz, auto 80 Hz (`hpf` to override). Lav rumble: 120–150.
- `denoise`: `light` (afftdn nr 10 / nf -50, default), `true` (12/-45), `strong` (20/-40), or `rnnoise:
  "model.rnnn"` (arnndn, mix 0.85). Too much = "underwater" voice; A/B it.
- `dehum: 50|60`: notches at f, 2f, 3f, 4f. `declick: true`: mouth clicks (adeclick t=4).
- `eq`: `clear` (mud cut, presence +2.5 dB, air) · `warm` (body, softer top) · `broadcast` (body, -3 dB mud,
  +3 dB presence) · `phone` (300–3400 Hz) · `radio` (200–5000 Hz) · `off`.
- `deess: true|0..1` (deesser i=0.4; the FFmpeg default is 0 = off). `gate: true` lowers gaps ~12 dB (never mutes).
- `compress` (default on): threshold 0.1 (≈-20 dBFS, linear), 3:1, 10/120 ms, makeup ×2.
Test a chain: `audio_chain.py voice in.wav out.wav --cfg '{"eq":"broadcast","deess":true}'`.

## SFX library (procedural, no sample files; cached in `<work>/sfx/`)

Render one to listen: `audio_chain.py sfx impact --out impact.wav`; all: `sfx --all --out-dir sfx`.

| use | kinds |
|---|---|
| transitions / camera moves | `whoosh` `whoosh-short` `whoosh-long` `swish` `swoosh-up` `swoosh-down` |
| reveals, title slams, beat hits | `impact` `hit-hard` `boom` `thud` `braam` (trailer) |
| low-end weight on a drop / reveal | `sub-drop` `bass-drop` |
| build tension into a hit | `riser` (1.2 s) `riser-long` (4 s) `reverse-cymbal` (2 s swell) `drum-roll` |
| comedic stop / rewind | `record-scratch` `tape-stop` `rewind` `boing` `slide-whistle` |
| UI / screen recordings | `ui-tap` `ui-swipe` `click` `pop` `digital-beep` `notification` `type` `typewriter-key` |
| result / status | `success-chime` `error-buzz` `ding` `glass-ding` `coin` `cash-register` `sparkle` |
| time / tension | `tick-tock` `clock-tick` `countdown-beep` (3-2-1-go, 3.7 s) `heartbeat` |
| tech glitch | `glitch` |
| photo | `camera` `camera-shutter` |
| crowd / room | `applause-light` `crowd-gasp` (breathy noise, no fake voices) `wind` `room-tone` `page-turn` |

Placement: `t` is where the sound **starts**. Whooshes peak at ~65% of their length, so start a 0.6 s
`whoosh` ~0.4 s before the cut. Risers end abruptly: start `riser` at hit − 1.2 s, `riser-long` at hit − 4 s,
`reverse-cymbal` at hit − 2 s, then put an `impact` on the hit. Gains: UI 0.3–0.5, whoosh 0.4–0.6, impacts
0.4–0.7 (they are dense). Pro rules: one sound per idea; whoosh on transitions, impacts on reveals, risers
into drops; don't stack more than two at once; leave most of the video dry — overuse reads as cheap;
silence is a tool: drop music (keep room tone) 0.5–2 s before a punchline or reveal so the hit lands louder.

## Music

- Bed level: under dialogue 18–24 LU (`"under": 20`); without dialogue let it rise near dialogue level.
- Ducking: `duck: true` ≈ 10 dB under speech (2:1-ish sidechain, 20 ms attack, 700 ms release).
  `"speech-aware"` = gentler 6 dB compressor + 4 dB extra dip on each spoken phrase from `plan.words`
  (ramps 200 ms down before, 500 ms up after) — smoother, no pumping in short pauses. Music-forward montage: `duckDepth: 5`.
- `fitTo: "beats"`: keeps the song's real ending, removes or repeats whole bars where the joined bars match
  (4-bar phrase aware), 60 ms equal-power crossfades into bar lines, exact length. `endButton: true` lands a
  hit on the last downbeat 0.6 s before the end and rings out — stronger than a fade.
- CLI: `beats.py music.mp3 --out work/beats.json [--peaks]` → `{bpm, beats, downbeats, onsets}` (cut visuals on
  `downbeats`; `peaks.json` drives waveform graphics). `music_fit.py music.mp3 --duration 14.7 --out fitted.wav`.
- Stems: `stems.py song.mp3 --out work/stems` → vocals.wav + music.wav (needs `pip install demucs`, slow on CPU).
  Use music.wav as a bed under talking, or to strip music from dialogue. Licence must allow modification.
- Licence-safe music: YouTube Audio Library, Pixabay Music, Incompetech (CC BY, credit), FMA (avoid NC).

## Voice-over (`tts.py`)

`tts.py --script vo.txt --out work/voice.wav --words` (writes `work/words.json` aligned to the script).
Backends: kokoro (Apache-2.0, best; `pip install kokoro soundfile`) → piper (GPL-3.0 engine, needs a voice
.onnx) → Windows SAPI (built in: "Microsoft David Desktop", "Microsoft Zira Desktop") → macOS `say` → espeak-ng.
`--rate 1.1` speeds up; `--list-voices`. Run the result through the dialogue chain like a real voice.

## QC before delivery

1. `audio_chain.py measure final.mp4 --platform youtube` → I within ±1 LU, TP ≤ target (reports pass).
2. Listen at the start, at every SFX and at the music ending; check on phone speakers / mono.
3. Dialogue always intelligible over music; no pumping; no clicks at jump cuts (use `roomTone`).
4. Nothing clips (TP ≤ -1); the sound ends with the picture (graph pads/trims to the exact duration).
