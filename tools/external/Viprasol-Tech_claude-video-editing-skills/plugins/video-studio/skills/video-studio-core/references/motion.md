# Motion reference (engine.js motion upgrade)

Every field here is optional. Old plans keep working. Every element is a pure function of `t`,
so any frame renders the same in any order. All randomness comes from seeds. Times are seconds on
the cut timeline. Positions are output pixels unless a field says "fraction".

## Timing guidance (reels)

- Text builds take 8–15 frames (0.3–0.5 s). Exits run at about 60–75 % of the entrance.
- Hold any readable text for at least 0.6 s, and longer for full sentences.
- Bring a word-synced element in 0.05–0.1 s **before** the word, so it lands as the word is said.
- Keep at most 2 overlays on screen at once, plus captions. Stage one focal animation at a time.
- Stagger letters 0.03–0.06 s, words 0.06–0.12 s and lines 0.12–0.25 s.
- Ease-out (`expoOut`, `quintOut`) for arrivals, ease-in for departures, `inOut` for moves between two states.
  Use spring or `backOut` overshoot (5–15 %) for playful emphasis only.
- Captions: keep them at 20 cps or less, at least 0.3 s on screen, between 10 % and 85 % of the frame height, and
  clear of the right 12 % (the icon rail) in 9:16.
- Transitions: cut by default. Pick one or two transition kinds per video, at 0.2–0.4 s each, placed on the beat.

## Easing

Use `ease` on an element, inside an `in`/`out` object, or on a keyframe. The value can be:

- a name: `linear out in inOut back elastic` (the original set), `quadIn/Out/InOut`, `cubicIn/Out/InOut`,
  `quintIn/Out/InOut`, `expoIn/Out/InOut`, `circIn/Out/InOut`, `sineIn/Out/InOut`, `backIn/Out/InOut`,
  `elasticOut`, `bounce` (= `bounceOut`), `bounceIn`, `bounceInOut`
- `"cubic-bezier(0.16,1,0.3,1)"` or `[0.16,1,0.3,1]`
- `"spring"`, which uses stiffness 180 and damping 20, or `{"spring": {"stiffness": 240, "damping": 14, "mass": 1}}`.
  A closed-form damped spring is evaluated at `k × dur` and snaps to 1 at the end, so give it a `dur` of 0.5 s or more.

```json
{"type": "chip", "text": "Premium", "in": "maskUp", "ease": "cubic-bezier(0.16,1,0.3,1)"}
```

## In / out animations

`in` and `out` take a name or `{name, dur, ease, dir, dist, spring}`. An `out` animation plays its
`in` animation in reverse. `inDur` and `outDur` still work. The new names have their own default
durations, shown in brackets.

| name | look |
| --- | --- |
| original | `fade pop bounce rise drop slideLeft slideRight scale zoomIn blur spin wipe wipeUp stamp flip glitch none` |
| `maskUp` `maskDown` `maskLeft` `maskRight` (.5) | the content slides inside a fixed clip mask (editorial line reveal, expoOut) |
| `iris` (.5) | circular clip opens from the centre |
| `clockWipe` (.6) | conic sweep (clip-path polygon) |
| `slideUpFull` (.5) | enters from below the frame |
| `push` (.5) | full-distance slide. `dir` is the direction of travel (`left` default = enters from the right; `up`, `down`, `right`), and `dist` is in px |
| `zoomOut` (.45) | scales from 1.6 down to 1 while the blur clears |
| `whip` (.3) | fast directional slide with motion blur and stretch (`dir`) |
| `elastic` (.7) | elastic scale-in |
| `springPop` (.6) | real spring scale from 0.3, with overshoot. `spring:{stiffness,damping}` |
| `rotateIn` (.5) | rotates in from −90° with overshoot |
| `swing3d` (.6) | 3D door swing on the left edge |
| `unfold` (.45) | scaleY from the top edge |
| `blurIn` (.45) | blur from 30 px with a fade (no scale) |
| `typewriter` | on text: a real typewriter (see fx). On other elements: a stepped wipe |

```json
{"type": "tile", "text": "Step 2", "in": {"name": "push", "dir": "up", "dur": 0.45, "ease": "expoOut"}, "out": "blurIn"}
```

## Keyframes, idle motion, beats, face anchor (any element)

| field | meaning |
| --- | --- |
| `keys` | `{prop: [[t, value, ease?], ...]}` with t relative to the element start. Props: `x` `y` (absolute anchor position, px), `tx` `ty` (offset px), `s` (scale ×), `r` (deg, added), `o` (opacity ×), `blur` (px, added). The ease on a key shapes the segment that arrives at it (default `inOut`, or the element's `ease`). Combines with in/out. |
| `shake` | `{amp: 12, freq: 8, rot: 0, decay: 0, seed}`. Seeded 2D value noise. Add `decay` (per second) for an impact shake |
| `pulseOn` | `"beats"` or `"downbeats"` scales the element on each beat from `P.beats` (`pulseAmp` 0.06, `pulseDecay` 9). On `shape`, an array of times still works as before |
| `anchorTo` | `"face"` makes the anchor follow the centre of the interpolated `P.track` face box. `offset: [dx, dy]`: a value with abs ≤ 3 is a fraction of the face size, otherwise px |

```json
{"type": "chip", "text": "keys + shake", "start": 1, "end": 4,
 "keys": {"x": [[0, 200], [1.2, 700, "backOut"]], "r": [[0, -10], [1.2, 6, "expoOut"]]},
 "shake": {"amp": 6, "freq": 9}, "pulseOn": "beats"}
```

Plan-level data, all optional:

- `"beats": {"bpm": 120, "beats": [..], "downbeats": [..], "offset": 0, "beatsPerBar": 4}`. Beats are derived from `bpm` when the list is absent.
- `"track": [{"t": 0, "x": .36, "y": .18, "w": .3, "h": .2}, ...]` holds normalised face boxes. `x`,`y` is the top-left corner.
- `"peaks": {"fps": 30, "values": [0..1, ...]}` holds audio amplitude for `waveform`.

The `flash` element also accepts `"times": "beats"` or `"downbeats"`.

## Text (`text` / `headline` / `chip` / `tile` / `sticker`)

- `split: "lines"` wraps each line in a mask and staggers them. Lines come from `\n`, or from where the browser wraps the text inside `w`.
  The defaults are `unitIn: "maskUp"`, `stagger: 0.12` and `unitDur: 0.55`.
- `unitIn` accepts every animation name, including the object form. `unitEase` sets the per-unit ease.
- `fx`: a name or `{name, ...}`. When `fx` is set, `split` is ignored.

| fx | options | look |
| --- | --- | --- |
| `typewriter` | `cps` 18, `delay`, `caret` (char or `false`) | characters appear with a caret. The remaining text is reserved, so nothing reflows |
| `scramble` | `dur` 0.9, `delay`, `every` 2 (frames), `seed` | deterministic decode, left to right |
| `splitflap` | `stagger` .045, `flips` 8, `flipDur` .05 | departure-board tiles flip to each character |
| `highlight` | `target` (substring), `color`, `textColor`, `delay` .25, `dur` .4 | marker sweep behind the text |
| `underline` | `target`, `color`, `delay` .3, `dur` .35 | line sweeps under the text |
| `strike` | `target`, `color`, `delay` .35, `dur` .3 | strike drawn over the glyphs, word by word (wraps correctly) |
| `gradientSweep` | `color`, `period` 2.2 | an accent band sweeps through the text fill |
| `countWords` | `dur` 1.2, `delay` | every number in the text counts up from 0 (`$12,400`, `3.5`) and keeps its final width |
| `stroke-draw` | `dur` 1.4, `color`, `width`, `fill` | SVG outline drawn with dashoffset, then the fill fades in (single line) |
| `karaoke-fill` | `from`/`to` (absolute) or `delay`/`dur` 1.6, `color` | the accent fill sweeps left to right across the whole box |

```json
{"type": "text", "text": "the one habit that matters", "fx": {"name": "highlight", "target": "one habit", "textColor": "#000"}}
```

## Captions

New fields, all optional:

| field | meaning |
| --- | --- |
| `preset` | `hormozi` (bold caps, 3 words, active word coloured with a spring scale, heavy stroke), `beast` (chunky caps, 2 words, colour cycle, spring pop, alternating tilt), `clean` (sentence case, up to 2 lines of about 32 chars in 9:16 or 42 in 16:9, no animation), `karaoke` (line visible, each word fills as it is spoken), `boxed` (active word on an accent box), `minimal-lower` (small sentence-case reveal near the bottom). Your own fields override the preset. The class `cap-preset-<name>` is added |
| `safe` | default `true`. Clamps y so the caption box stays between 10 % and 85 % of H. In 9:16 it shifts the text left if it reaches the right 12 % |
| `dodge` | `[{start, end, y}]` moves the caption to `y` (px, or a fraction if ≤ 1) during that window |
| `dodgeFace` | `true` moves the caption below or above the `P.track` face box when they overlap (smoothed over 5 samples). Tune with `dodgeMargin` 30 |
| `emoji` | `{"money": "💰"}` pops the emoji above that word as it is spoken |
| `cpsMax` | default 20. Groups faster than this are split in half, unless a half would be on screen less than `minDur` (0.3 s). `0` turns it off |
| `mode` | adds `static` (no per-word state) and `fill` (karaoke sweep per word) to `karaoke`/`reveal`/`single` |
| `activePop` | spring the `activeScale` from the start of each word |
| `breakOnPunct` | `"sentence"` breaks only on `.!?` |
| `wordEase`, `tilt` | ease for `wordIn`, and the alternating group tilt in degrees |

```json
{"type": "captions", "preset": "hormozi", "emoji": {"money": "💰"}, "keywords": ["nobody"], "dodgeFace": true}
```

## New element types

Fields marked "absolute" use cut-timeline seconds. Everything else is relative to the element start.
All types also take `start`, `end`, `x`, `y`, `w`, `h`, `anchor`, `in`, `out`, `className`, `style`, `keys` and the rest of the common fields.

| type | key fields | example |
| --- | --- | --- |
| `timer` | `from` (s, default 10), `label`, `warnAt` 3, `delay` | `{"type":"timer","from":5,"label":"seconds","w":330,"h":330}` |
| `poll` | `question`, `options:[{label,pct}]`, `revealAt` .7, `footer` | `{"type":"poll","question":"Would you rather?","options":[{"label":"A","pct":72},{"label":"B","pct":28}]}` |
| `chat` | `messages:[{text, side:"left"/"right", at (absolute), name}]`, `title`, `status`, `typing` .8 (dots before incoming messages) | `{"type":"chat","title":"Sam","h":700,"messages":[{"text":"done?","side":"left","at":12.3}]}` |
| `notification` | `app`, `title`, `body`, `icon`, `time`. Slides down from the top by default | `{"type":"notification","app":"Bank","title":"Payment received","body":"$2,400"}` |
| `searchbar` | `query`, `cps` 14, `delay`, `results:[..]`, `placeholder` | `{"type":"searchbar","query":"how to edit faster","results":["... in premiere"]}` |
| `codeblock` | `code`, `title`, `cps` 38, `linePause` .12, `lineNumbers`, `diff: true` (lines starting `+` or `-` are coloured), `showAll` | `{"type":"codeblock","title":"app.js","diff":true,"code":"-a\n+b"}` |
| `callout` | `x`,`y` = label position, `point:[x,y]` = target (or `anchorTo:"face"` + `offset`), `title`, `text`, `color`, `drawDur`, `labelIn` | `{"type":"callout","point":[540,700],"x":820,"y":300,"title":"New button"}` |
| `pointer` / `arrow` | `x`,`y` = target. `kind:"arrow"` (`from:[x,y]`, `curve` .22, `gap`, `headSize`) or `"hand"` (`emoji`, `period`) | `{"type":"pointer","x":300,"y":980,"from":[620,1200]}` |
| `map` | `pins:[{x,y (0..1),label}]`, `title`, `routeDelay` .6, `legDur` 1, `seed`. Seeded dot-grid land, not real map data | `{"type":"map","pins":[{"x":.2,"y":.4,"label":"Lisbon"},{"x":.8,"y":.55,"label":"Tokyo"}]}` |
| `barrace` | `data:[{label, values:[..], color}]`, `labels` (period names), `top` 6, `raceDur`, `prefix`/`suffix`/`decimals`/`compact` | `{"type":"barrace","labels":["2024","2025"],"data":[{"label":"A","values":[1,5]}]}` |
| `linechart` | `series:[{values,label,color}]` or `values`, `labels`, `min`/`max`, `drawDur` 1.4, `prefix`/`suffix` | `{"type":"linechart","labels":["W1","W2"],"series":[{"values":[3,9]}]}` |
| `piechart` / `pie` / `donut` | `items:[{label,value,color}]`, `donut`, `center`, `centerLabel`, `drawDur` 1.1 | `{"type":"donut","items":[{"label":"Edit","value":55},{"label":"Film","value":45}]}` |
| `waveform` | `peaks` (array + `peaksFps`, or `{fps,values}`) or `P.peaks`. `mode:"scroll"` (window of `span` 2.4 s centred on t) or `"static"`, `count` 56, `gain`. Without peaks it falls back to the fake equaliser | `{"type":"waveform","h":180}` |
| `lyric` | `lines:[{text,start,end,words?}]` (absolute), or words from `P.words` grouped by `maxWords` 6. Each word fills as it is sung, and the next line shows dimmed | `{"type":"lyric","lines":[{"text":"seek it anywhere","start":31.6,"end":33}]}` |
| `subscribe` | `name`, `handle`, `avatar`, `label`, `doneLabel`, `clickAt` .9, `bellAt`. The cursor clicks the button, then rings the bell | `{"type":"subscribe","name":"Video Studio","clickAt":1.0}` |
| `socialpost` | `name`, `handle`, `time`, `verified`, `text` (with #tags and @mentions coloured), `image`, `avatarImage`, `likes`, `likesFrom`, `likeAt` .8, `comments`, `shares`. Class `dark` gives a dark card. It is a generic card: never imitate a real platform or a real person's post | `{"type":"socialpost","name":"Studio Notes","text":"Cut every pause.","likes":48200}` |
| `checklist` | `items:[{text, at (absolute)}]`, `title`, `strike`, `reveal`, `itemStagger` | `{"type":"checklist","title":"Before you post","items":[{"text":"Hook","at":21.6}]}` |
| `steps` | `steps:["Plan",..]` or `[{label, at}]`, `vertical`, `stepStagger` .9 | `{"type":"steps","steps":["Plan","Shoot","Edit","Post"]}` |
| `quote` | `text`, `author`, `role`, `stagger`, `unitIn` | `{"type":"quote","text":"Restraint is the craft.","author":"An editor"}` |
| `split` | `panes:[{image | clip, label, clipOffset}]` (2–4), `layout:"h"/"v"/"grid"`, `paneIn` (`maskUp`), `stagger`. Relative pane paths resolve against workDir | `{"type":"split","layout":"grid","panes":[{"image":"a.jpg","label":"Before"},{"image":"b.jpg"}]}` |
| `vignette` | `strength` .6, `size` .5, `color` `"r,g,b"`, `cy` | `{"type":"vignette"}` |
| `letterbox` | `bar` (px) or `ratio` (e.g. 2.39), `color`. Bars slide in and out | `{"type":"letterbox","ratio":2.39}` |
| `grain` | `amount` .16, `scale` 2, `fps`, `seed`. Seeded per-frame noise canvas | `{"type":"grain","amount":0.12}` |
| `lightleak` | `intensity` .55, `colors:["r,g,b"]`, `speed` .25, `count` 3, `seed` | `{"type":"lightleak","intensity":0.4}` |
| `transition` | `kind`, `at` (the cut, absolute), `dur` .4, `dir`, `color`, `color2`, `center:[fx,fy]`, `shape` (`star diamond hex circle`), `seed`, `peak`. The frame is fully covered at `at` | `{"type":"transition","kind":"ink-blot","at":12.4,"dur":0.5}` |

Transition kinds: `wipe` (two colour bands), `iris`, `shape-mask`, `ink-blot`, `paper-tear` (jagged edges),
`glitch` (RGB slices), `whip-blur` (blur bar with streaks), `light-leak`, `flash-white`, `film-burn`, `zoom-blur` (ring burst).
These are overlays painted at a cut. Real A/B blends (dissolve, push between two clips) belong to FFmpeg
`xfade` at concat time.

## Notes and limits

- Overlay layers are captured as transparent PNGs and composited by FFmpeg, so `mix-blend-mode`
  cannot reach the video underneath. Grain, light leaks and burns use plain alpha. For blend-mode
  grain or a vignette, use `finish.grain` or `finish.vignette`.
- `stroke-draw` draws one line only. `karaoke-fill` on multi-line text sweeps the whole box, not line by line.
- `split:"lines"` measures the wrap once, at the first visible frame, after `fit`.
- CSS hooks for themes: `.cap-preset-*`, `.timer`, `.poll`, `.chat`, `.notif`, `.search`, `.code`, `.callout`,
  `.pointer`, `.map`, `.race`, `.lc`, `.pie`, `.wave`, `.lyric`, `.subscribe`, `.post`, `.check`, `.steps`,
  `.quote`, `.split`, `.tr-<kind>`. Colours come from `--c-accent`, `--c-accent2`, `--c-card`, `--c-card-fg`,
  `--c-mark`, `--font-display`, `--font-body` and `--font-mono`.
