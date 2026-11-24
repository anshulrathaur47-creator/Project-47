# Timeline, scenes, reframe, B-roll and selects

These tools turn several clips (or one long recording) into ONE assembled video plus the files the normal
pipeline reads: `cut.mp4`, `words.json`, `cutlist.json` in the work folder. After them, `make_plan.py`,
`render.py` and `finish.py` run exactly as for a single clip.

```
long footage ──selects.py──> paper_edit.md ──selects.py --apply──> selects_spec.json ─┐
many clips ───timeline.py auto (montage|story|highlights) ──> timeline_spec.json ─────┤
hand-written spec.json ────────────────────────────────────────────────────────────────┤
                                                       timeline.py build SPEC --work W ┘
   W/assembled.mp4 (= cut.mp4 = source.mp4), audio16k.wav, words.json, transcript.json, cutlist.json, timeline.json
   -> broll.py --work W --library broll/ -> make_plan.py -> broll.py --merge W/plan.json -> render.py -> finish.py
```

## Scripts

| script | does |
| --- | --- |
| `scenes.py INPUT --work W [--threshold 0.3] [--min-shot 0.5] [--thumbs]` | shots (FFmpeg scene score, PySceneDetect if installed), black, freeze and flash frames -> `scenes.json` |
| `track.py analyze INPUT --work W` | MediaPipe face tracks (6 fps, smoothed, every frame) + active speaker -> `track.json` |
| `track.py reframe INPUT --out OUT --format 9:16 [--layout auto\|single\|stack2] [--follow active\|primary] [--mode smooth\|fast\|locked] [--headroom 0.3] [--zoom 1]` | auto-reframe that keeps the face (or the active speaker) in frame |
| `timeline.py build SPEC --work W [--no-transcribe]` | assemble a multi-clip timeline |
| `timeline.py auto FILES/FOLDER --work W --mode montage\|story\|highlights --duration 30 [--music m.wav] [--format 9:16] [--transition cut] [--beats-per-shot N] [--dry-run]` | build the spec for you, then assemble (`--dry-run` stops at `timeline_spec.json` so you can edit it) |
| `broll.py --work W --library DIR [--frequency low\|med\|high] [--allow-hook] [--merge W/plan.json]` | place B-roll from the transcript -> `broll.json` |
| `selects.py --work W --input long.mp4` then `--apply` | best takes, paper edit, timeline spec |

Python API: `scenes.detect(path, threshold, min_shot)`, `track.analyze(path)`,
`track.follow_crop_filter(track, src_w, src_h, out_w, out_h, fps, mode, headroom, face_id, follow, zoom, cuts, t0)`
(returns an FFmpeg `crop=...,scale=...` chain), `timeline.build(spec_dict, work)`.

## Timeline spec

```json
{"format": "9:16", "fps": 30,
 "clips": [
   {"src": "intro.mp4", "in": 2.0, "out": 6.5},
   {"src": "talk.mp4", "in": 10, "out": 31, "transition": {"type": "dip-black", "dur": 0.5}, "jcut": 0.4,
    "reframe": "face", "words": "talk-work/transcript.json"},
   {"src": "broll_surf.mp4", "in": 3, "out": 9, "audio": "duck", "lcut": 0.3,
    "speedRamp": [{"at": 5.0, "rate": 0.35, "ramp": 0.4}, {"at": 7.0, "rate": 1.5, "ramp": 0.3}]},
   {"src": "cheers.mp4", "in": 0, "out": 2, "freeze": [{"at": 1.4, "dur": 1.0}], "transition": "whip"},
   {"src": "logo.png", "dur": 2.5, "transition": {"type": "fade", "dur": 0.6}, "kenburns": true}
 ],
 "music": {"src": "track.mp3", "volume": 0.2, "duck": true, "fadeOut": 2, "start": 0}}
```

| field | meaning |
| --- | --- |
| `src` | video or image, relative to the spec file. Images take `dur` (default 3 s) and get a slow push-in unless `"kenburns": false` |
| `in`, `out` | source seconds (default whole clip) |
| `speed` | constant rate 0.25–4. Audio keeps its pitch (atempo) |
| `speedRamp` | `[{at, rate, ramp}]`: reach `rate` at source second `at`, easing (smoothstep) over the `ramp` seconds before it. Video is mapped exactly; audio uses short constant-rate pieces |
| `smooth` | `true` = optical-flow slow motion (minterpolate) when the clip runs below 1x. Much slower to render (~1 min per 4 s of 1080p); without it slow motion repeats frames |
| `freeze` | `[{at, dur}]` hold the frame at source second `at` for `dur` s (audio is silent during the hold). `freezeEnd: 1.5` holds the last frame |
| `reverse` | play backwards (audio reversed too; J/L cuts ignored). Keep reversed clips short: FFmpeg buffers the whole clip |
| `audio` | `keep` (default), `mute`, `duck` (25 %). `volume` scales further |
| `transition` | INTO this clip from the previous one: `cut` (default), `dip-black`, `dip-white`, `whip` (slide + horizontal motion blur), `zoom` (xfade zoomin), `crossfade`/`fade`, or any xfade name below. `dur` default 0.4 s, clamped to half of either clip. Each transition shortens the timeline by its duration |
| `jcut` | seconds this clip's sound starts BEFORE its picture (the previous clip's sound stops there) |
| `lcut` | seconds this clip's sound continues OVER the next clip's picture |
| `fit` | `cover` (default, crop to fill) or `contain` (letterbox/pillarbox) |
| `reframe` | `face`: follow the main face (track.py) instead of a centre crop. Analysis runs on the whole source once and is cached in `W/tracks/` |
| `color` | FFmpeg `eq`: `brightness` (-1..1), `contrast`, `saturation`, `gamma` (1 = unchanged). Use it to match clips, leave the look to `finish.py` |
| `words` | transcript/words JSON in this clip's source time (e.g. its `transcript.json`). If every audible clip has one, they are re-timed onto the timeline (J/L and speed aware) and Whisper is skipped; otherwise the assembled audio is transcribed |
| `music` | bed under the edit. `duck` = sidechain compression under the dialogue. For talking videos prefer `finish.py`'s music (it already ducks); use this in montages |

Timing rules (all frame-exact): clip length D = time-mapped length (speed, ramps, freezes) rounded to frames;
clip k starts at `S_k = S_(k-1) + D_(k-1) - transition_k.dur`; total = ΣD − Σtransition durations.
Audio edit point between clips = middle of the transition − `jcut` of the incoming clip + `lcut` of the outgoing
clip, with a 30 ms crossfade on plain cuts (no clicks) or a crossfade as long as the picture transition.
`cutlist.json` lists every clip with `out_start/out_end` (picture) and `audio_start/audio_end` (sound).

### All transition names (FFmpeg 9 `xfade`)
fade, wipeleft, wiperight, wipeup, wipedown, slideleft, slideright, slideup, slidedown, circlecrop, rectcrop,
distance, fadeblack, fadewhite, radial, smoothleft, smoothright, smoothup, smoothdown, circleopen, circleclose,
vertopen, vertclose, horzopen, horzclose, dissolve, pixelize, diagtl, diagtr, diagbl, diagbr, hlslice, hrslice,
vuslice, vdslice, hblur, fadegrays, wipetl, wipetr, wipebl, wipebr, squeezeh, squeezev, zoomin, fadefast,
fadeslow, hlwind, hrwind, vuwind, vdwind, coverleft, coverright, coverup, coverdown, revealleft, revealright,
revealup, revealdown. Aliases: dip-black = fadeblack, dip-white = fadewhite, crossfade = fade, zoom = zoomin,
push = slideleft, whip = slideleft + motion blur.

## How a pro uses them (restraint)

- **Cuts are the default.** Most edits in good work are straight cuts, many of them split (J/L). One transition
  language per video; never a different effect on every cut.
- **J/L cuts for dialogue and interviews.** Default offsets: 4–12 frames (0.15–0.4 s) inside a conversation;
  0.5–2 s when bringing in the next scene's sound early (J) or letting a line land over a reaction or B-roll (L).
  They hide plain cuts better than any effect. Avoid "tennis-match" cutting where every line gets its own picture.
- **Dissolve / fade (12–30 frames):** time passing, montage, soft mood. Never between every shot of a dialogue.
- **Dip to black (0.5–1 s):** section or act breaks, endings. **Dip to white (8–20 frames):** flashback, flash, impact.
- **Whip / zoom / slide (6–12 frames):** energy in vlogs, travel, hype. Pair with a whoosh (finish.py sfx) and use
  on matching camera motion. Glitch/pixelize: tech/gaming only, 4–10 frames.
- **Match cuts:** join shots that share shape, motion or colour; cut on action about a third into the movement.
  Cut a frame or two before a blink when the thought ends.
- **30-degree rule:** two shots of the same subject must differ by ≥30° or a ≥1.2× size change, otherwise it reads
  as a jump cut. Cover it with B-roll, a punch-in (plan `speaker.zooms`) or another angle.
- **Pacing:** short-form changes picture every 1–3 s and lands the hook within 1.5 s; YouTube every 2–5 s in
  the first minute; interviews 5–15 s with 2–5 s B-roll. Vary shot length (don't cut every shot the same length)
  except in music-locked montages.

## Speed ramps
Ramp INTO the moment (fast → slow just before the action, `ramp` 0.3–0.6 s), hold the slow part 0.5–1.5 s, then
snap back faster. 0.25–0.5x for impact, 1.5–3x for travel/transitions. Smooth slow motion needs footage shot at
high frame rate; on 30 fps footage `smooth: true` interpolates frames (good on simple motion, warps on complex
motion). Mute or duck ramped dialogue; let music carry the ramp.

## Reframe
- `--layout auto`: two faces on screen most of the time → `stack2` (left person on top, each panel follows its
  face with a 1.4x tighter shot); otherwise `single`. `--follow active` cuts between speakers by mouth movement
  (switches at most every 1 s, lags speech by up to ~0.3 s); `--follow primary` stays on the main face.
- `--mode smooth` (default) behaves like a camera operator: a dead zone ignores small head moves, then a
  critically damped move (~0.8 s). `fast` follows tightly; `locked` is one fixed crop (best for interviews that
  barely move).
- `--headroom 0.3` places the eyes a third from the top. Faces must be visible and reasonably frontal: MediaPipe's
  short-range detector misses tiny faces (<5 % of the frame width) and profiles. With no face it centre-crops.

## B-roll rules (broll.py)
- Name library files after what they show (`coffee-pouring.mp4`, `city_night.jpg`) or add `NAME.txt` with keywords.
- Each shot lasts 1.2–4 s; jump cuts from `cutlist.json` are covered first (shot starts ~0.6 s before the cut,
  ends ~0.9 s after); then words that match a file name get B-roll starting 0.1 s before the word.
- Nothing in the first 1.5 s (the hook shows the face) unless `--allow-hook`; at least 0.8 s of speaker between
  shots; frequency low/med/high ≈ one shot per 12/7/4 s.
- Videos become plan `cutaways`, images become full-frame `image` elements with `motion: kenburns` placed before
  the captions so captions stay on top. `uncovered_joins` lists jump cuts that still need a punch-in.
- Run it after `make_plan.py` with `--merge W/plan.json` (it replaces its own earlier B-roll), or copy by hand.

## Selects (selects.py)
- Splits the transcript into sentences, groups retakes (similar wording within 2 minutes, or a false start the
  next sentence repeats) and keeps the best: complete, confident, few fillers, no "sorry / let me start again",
  small bonus for the last take (it is usually the one the speaker meant).
- `paper_edit.md` is the editor's paper edit: flip `[x]`/`[ ]`, move lines to reorder, then `--apply`.
  Adjacent kept sentences merge into one clip; each clip carries its transcript, so words are re-timed without
  re-transcribing.
- FRANKENBITE: two kept lines joined across >30 s or out of order make a constructed quote. Allowed in
  entertainment edits; in interviews, documentary or anything factual confirm with the user that the meaning
  is unchanged.

## Hooking into run.py (for the coordinator)
`run.py` can stay single-clip; for many clips run `timeline.py build|auto` first, then
`run.py`'s later steps on the same work folder (`make_plan.py --work W ...`, `render.py`, `finish.py`).
`timeline.py` also writes `source.mp4` + `audio16k.wav`, so `autocut.py --work W` can still tighten pauses in
the assembled result (it re-uses `transcript.json`).

### Voice-over as the soundtrack (photos / faceless edits)

When no clip carries audio and the narration is laid as the spec's music, add `"voiceover": true` to the spec's
`music` block. `timeline.py build` then transcribes the assembled audio so `words.json` has word timings for captions:
`"music": {"src": "vo/voice.wav", "volume": 1.0, "voiceover": true}`. A plain music bed is never transcribed.
`run.py --timeline` skips autocut (the spec already sets every in/out); `autocut.py --keep-all` leaves a timeline's
`cutlist.json` untouched so `editor.py review` still sees every clip join.

### Cleaning up clips before a spec (stabilise, denoise, deflicker)

`run.py --stabilize / --denoise light|strong / --deflicker` apply to the single-input prep step only. For a
multi-clip spec, clean just the clips that need it first and point the spec at the result:
`python CORE/scripts/prep.py shaky.mp4 --work fix/shaky --stabilize --denoise light` -> use `fix/shaky/source.mp4`
as that clip's `src`. prep also normalises the clip (constant `--fps`, default 30; long side <= 1920), so pass
`--fps 60` for 60 fps footage you want to keep at 60.
