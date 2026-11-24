# Video Studio catalogue (v2.0.0)

This catalogue replaces the old "500 moves" list. Every item is tagged by what the code does **today**, checked against
`runtime/engine.js`, `scripts/timeline.py`, `scripts/color.py`, `scripts/audio_chain.py` and `scripts/deliver.py`.

| tag | meaning |
| --- | --- |
| **Ready** | Works now. The "how" column names the exact plan field, element type, CLI flag or script. |
| **Upgrade** | Not in the engine yet. The note says what our engine needs. |
| **Heavy** | Needs an optional model or a GPU that the pack does not bundle. The note names it and its licence. |

`CORE` = `video-studio-core`. "Plan" means `plan.json` (see `references/plan-schema.md`, `motion.md`, `color.md`, `audio.md`).
"Spec" means a `timeline.py` spec (see `references/timeline.md`). Times are seconds.

## Summary

| section | Ready | Upgrade | Heavy | rows |
| --- | --- | --- | --- | --- |
| 1. Skills (42 genre + 5 utility + 46 skins) | 93 | 0 | 0 | 93 |
| 2. Transitions | 43 | 11 | 1 | 55 |
| 3. Effects | 62 | 24 | 12 | 98 |
| 4. Text, title and caption animations | 98 | 11 | 1 | 110 |
| 5. Colour (tools + 51 looks in 45 rows) | 62 | 10 | 0 | 72 |
| 6. Sound moves | 44 | 15 | 7 | 66 |
| 7. Delivery presets and extras | 32 | 3 | 0 | 35 |
| **Total** | **434** | **74** | **21** | **529** |

Rows group close variants: one transition row can hold several `xfade` names (58 in total), one SFX row several of the 49 kinds.
Some skills are Ready with a stated gap (for example `localise-dub` has no lip-sync); the gap is tagged in the sections below.

Corrections to the old catalogue: it listed 373 items as Ready. Several of those are not implemented and are tagged Upgrade here. These include background blur and desaturate, subject outline and glow, chroma despill, echo trails and edge or duotone looks. Crash zoom with motion blur, the smash cut level contrast, music drop-outs, tracking-out titles, wave text, neon flicker and Lottie are also Upgrade. Stabilise, denoise, deflicker, region blur/pixelate and face-targeted punch-ins have since been built and are tagged Ready.

---

## 1. Skills

### 1a. Genre skills (42)

All are Ready: each is a `SKILL.md` that drives the engine with a matching genre preset (`editor.py genre NAME`).
How: ask Claude to use the skill, or run `run.py INPUT --style SKIN --genre NAME`.

| skill | tag | what it does | notes |
| --- | --- | --- | --- |
| `retention-reel` | Ready | 15-60 s talking-head reel, hook by 1.5 s, loop or CTA | |
| `clip-miner-pro` | Ready | 5-15 stand-alone moments from a long recording, reframed 9:16 | uses `clip_candidates.py`, `track.py reframe` |
| `reaction-duet` | Ready | source clip + facecam, PiP / split / stitch, source ducked | |
| `micro-drama` | Ready | 60-120 s vertical episodes, recap open, cliffhanger | |
| `gaming-vod` | Ready | stream highlights, facecam over gameplay | peaks from audio and motion only; no chat log or kill-feed input |
| `longform-retention` | Ready | long-form with minute-1 promise and re-engagements | |
| `video-essay` | Ready | VO-led essay, archival, quote cards, maps, charts | `map` is a stylised dot grid, not real map data |
| `vlog` | Ready | chronological day story, J/L cuts, B-roll | |
| `tutorial-screen` | Ready | screen how-to: promise, steps, recap; waiting cut | cursor zoom is a manual zoom; no cursor tracking |
| `product-review` | Ready | verdict tease, specs, pros/cons, score, disclosure | |
| `faceless-explainer` | Ready | offline TTS voice-over + one visual per sentence | best voice is the optional Kokoro |
| `news-explainer` | Ready | inverted-pyramid explainer with attribution | |
| `podcast-episode` | Ready | multicam by who talks, -16 LUFS | cameras must start in sync (no waveform sync) |
| `conference-talk` | Ready | speaker/slides, title card, applause trims | |
| `interview-doc` | Ready | paper edit, radio edit, B-roll cover, Frankenbite guard | |
| `vox-pop` | Ready | question on screen, answers grouped by intent | |
| `scene-editor` | Ready | line strings, best take per line, L-cut reactions | |
| `short-film-finisher` | Ready | per-shot colour, mix, masters after lock | M&E stem is an approximation |
| `trailer-teaser` | Ready | three acts, copy cards, risers into hits | |
| `ad-ladder` | Ready | 60/30 master, rebuilt 15 and 6 s, all ratios | |
| `ugc-ad-matrix` | Ready | hook variants x body x CTA | |
| `brand-film` | Ready | mission film + cutdowns | |
| `testimonial-film` | Ready | real-customer case-study film | real customers and real words only |
| `saas-launch-demo` | Ready | screen-recording launch/demo with callouts | PII blur is fixed boxes you place (plan `blurs`), not tracked |
| `wedding-highlight` | Ready | 3-5 min highlight, teaser, ceremony cut | |
| `wedding-india` | Ready | per-event highlight, reels, teaser, long film | |
| `event-recap` | Ready | 60-120 s beat-cut recap + 9:16 | |
| `concert-multicam` | Ready | 2-4 angles to the music over the board mix | sync each camera by hand (`prep.py --start`) |
| `music-video` | Ready | takes synced to the master, cut on downbeats | |
| `lyric-video` | Ready | line-timed lyrics with karaoke fill | Demucs vocal stem is optional (Heavy) |
| `memorial-tribute` | Ready | chronological photo-led tribute | |
| `recipe-video` | Ready | money shot first, ingredients, sped-up steps | |
| `fitness-video` | Ready | rep counters, interval timers, form split screens | |
| `fashion-lookbook` | Ready | beat cuts, product tags, true-colour grade | |
| `travel-cinematic` | Ready | match cuts, whips, speed ramps, ambience | match cuts are chosen by Claude, not searched automatically |
| `real-estate-tour` | Ready | buyer's-visit order, price/beds/baths cards | vertical-line correction not built |
| `course-module` | Ready | one objective, steps, quiz cards, recap, WCAG captions | |
| `kids-content` | Ready | bright, simple, sing-along captions at <= 12-13 cps | |
| `asmr-video` | Ready | long takes, untouched trigger audio, dissolves | |
| `regional-devotional` | Ready | long respectful takes, Indic-script lyrics | lyrics typed into the plan by hand |
| `localise-dub` | Ready | translated subtitles + time-fitted TTS dub | no lip-sync and no voice cloning (Heavy) |
| `sports-highlight` | Ready | plays from crowd peaks, freeze + spotlight | cannot read the scoreboard or find the ball |

### 1b. Utility skills (5)

| skill | tag | what it does | how |
| --- | --- | --- | --- |
| `finishing-pro` | Ready | correct, match, look, texture, mix, loudness, legal, encode, QC | `color` block + `finish.py` + `deliver.py` + `qc.py` |
| `platform-pack` | Ready | one master into every platform version | `deliver.py --to ...` |
| `accessibility-pack` | Ready | SDH subtitles, transcript, AD script, described version | `deliver.py --words`, `tts.py`; no diarisation, no SCC |
| `editor-handoff` | Ready | EDL / FCPXML / OTIO, ProRes 4444 overlays, mix WAV | `export_edl.py`; timelines carry the cut only |
| `versions-review` | Ready | v001, v002 never overwritten, A/B sheets, notes rounds | `render.py --frames` per version |

### 1c. Style skins (46)

All are Ready. How: `--style SKILLS/<skin>` (a folder with `theme.json` + `theme.css`). `*` = text behind the speaker (uses the matte). `†` = background replaced or blurred around the person cut-out (uses the matte).

| skin | category | format | look |
| --- | --- | --- | --- |
| `halo-cut` | Talking-head reel | 9:16 | tight jump cuts, word-by-word captions, zoom punches on key words |
| `depth-type`* | Talking-head reel | 9:16 | giant one-word headline behind the head, new word per sentence |
| `split-proof` | Talking-head reel | 9:16 | speaker bottom, proof card / number / image top for every claim |
| `neon-orbit`* | Talking-head reel | 9:16 | glowing ring and orbiting lights behind the head, neon captions |
| `paper-cut` | Talking-head reel | 9:16 | taped paper captions, tilted stickers, marker arrows |
| `chaos-stack` | Talking-head reel | 9:16 | one huge word at a time, snap zooms, flashes, emoji bursts |
| `bold-bounce` | Talking-head reel | 9:16 | two huge words bouncing in, green/yellow highlights |
| `minimal-mono` | Talking-head reel | 9:16 | small lowercase captions, slow push-in, faded tone |
| `frame-studio` | Talking-head reel | 9:16 | speaker in a rounded panel on a cream magazine page |
| `vhs-tape` | Talking-head reel | 9:16 | REC dot, timecode, colour bleed, yellow subtitles |
| `y2k-chrome`* | Talking-head reel | 9:16 | chrome bubble words behind the speaker, sparkles, pastel pills |
| `news-desk` | Talking-head reel | 9:16 | breaking-news lower third, ticker, LIVE chip, boxed captions |
| `doc-real` | Talking-head reel | 9:16 | letterbox, film grade, lowercase subtitles, location tag |
| `cinematic-phone` | Talking-head reel | 9:16 | wide letterbox, teal-orange tone, serif title card |
| `sticker-pop` | Talking-head reel | 9:16 | die-cut word stickers, emoji bursts, pops |
| `terminal-tech` | Talking-head reel | 9:16 | captions typed into a terminal, green on black |
| `comic-panel` | Talking-head reel | 9:16 | speech-bubble captions, halftone, POW/BAM stamps |
| `swiss-poster`* | Talking-head reel | 9:16 | huge left-aligned black/red type on a grid behind the speaker |
| `soft-gradient` | Talking-head reel | 9:16 | rounded frame on a moving pastel gradient, glassy chips |
| `countdown-list` | Talking-head reel | 9:16 | rank number stamps in with a name banner |
| `before-after` | Talking-head reel | 9:16 | wipe slider reveals the after over the before |
| `dual-subs` | Talking-head reel | 9:16 | original word-by-word on top, translated line below |
| `hook-lab` | Talking-head reel | 9:16 | freeze-flash, snap zoom, red circle, "wait for it" in the first 3 s |
| `glow-cutout`† | Talking-head reel | 9:16 | you cut out with a gold rim glow over a blurred copy of your shot, gold-accent title, boxed captions |
| `poster-pop`†* | Talking-head reel | 9:16 | new retro poster backdrop every sentence (stripes, checker, grid, sunburst), slab headline, film grain |
| `glass-ribbon`† | Talking-head reel | 9:16 | violet scene, glowing ribbon behind and across you, bokeh orbs, glass cards, sans + italic serif captions |
| `neon-marquee`* | Talking-head reel | 9:16 | giant neon-blue headline scrolling behind the head, caption chips with blue key word, lime labels |
| `grid-stage`†* | Talking-head reel | 9:16 | black grid stage, spotlight and disc, giant word behind the head, glass pills, chapter title cards |
| `editorial-cards` | YouTube explainer | 9:16 | paper page, footage in a tilted card that moves each sentence, big word-by-word type, hand-drawn circles |
| `essay-mode` | YouTube explainer | 16:9 | paper textures, highlighter, serif headings, a card every 8-10 s |
| `whiteboard-host` | YouTube explainer | 16:9 | speaker panel left, marker notes on a paper board right |
| `chapter-pro` | YouTube explainer | 16:9 | chapter cards, lower thirds, list cards, end screen |
| `highlighter-study` | YouTube explainer | 9:16 | highlighter swipes on key words, notes cards |
| `tutorial-steps` | YouTube explainer | 16:9 | screen recording full frame, face bubble, numbered banners |
| `data-story` | Explainer | 16:9 | numbers become counters and bar charts on a dark grid |
| `clip-miner` | Podcast / repurposing | 9:16 | best 20-60 s moments as captioned shorts |
| `pod-frame` | Podcast / repurposing | 16:9 | camera switching, name cards, quote pulls, audio bar |
| `quote-card-reel` | Podcast / repurposing | 4:5 | speaker darkened behind large serif sentences |
| `device-fly` | Product / app promo | 9:16 | screen recording on a phone or laptop flying over a gradient |
| `kinetic-launch` | Product / app promo | 9:16 | type-only, words slam in on the beat or voice-over |
| `ugc-ad-kit` | Product / app promo | 9:16 | native ad: text hook, product callouts, end card |
| `logo-sting` | Product / app promo | 16:9 | 3-6 s logo reveal with rays, ring burst, typed name |
| `testimonial-card` | Product / app promo | 4:5 | real review as a card: avatar, stars, typed quote |
| `event-promo` | Product / app promo | 9:16 | kinetic event name, date and place chips, ticket CTA |
| `product-spotlight` | Product / app promo | 9:16 | product image on a spotlight, callouts with arrows |
| `loop-ambient` | Product / app promo | 1:1 | seamless drifting gradient, blob and bars behind a quote |

---

## 2. Transitions

The pro default is a cut. Use one or two transition kinds per video. Real A/B blends come from FFmpeg `xfade` at
assembly time (`timeline.py`, spec `transition`). Overlay transitions are painted on top of a cut by the `transition` element.

### 2a. Cuts and split edits

| transition | tag | how |
| --- | --- | --- |
| Hard cut | Ready | default between clips (spec `transition: "cut"`); `autocut.py` joins |
| Jump cut | Ready | `autocut.py` (pauses, fillers, retakes); `--smart-cuts` cuts in the quietest gap |
| Punch-in cut | Ready | plan `speaker.zooms: [{start, end, scale: 1.15, snap: true}]` (aims at the face when the plan has `track`) |
| Punch-out cut | Ready | end a `speaker.zooms` window on the cut so the next shot returns to 1.0 |
| J-cut | Ready | spec `jcut: 0.4`; single clip: `autocut.py --jcut N` (frames, at sentence joins) |
| L-cut | Ready | spec `lcut: 0.3` |
| Sound bridge | Ready | spec `jcut` of 0.5-2 s on the incoming clip |
| Cutaway | Ready | plan `cutaways: [{src, start, end, srcStart}]`; auto: `broll.py --merge` |
| Cut on beat / downbeat | Ready | `timeline.py auto --mode montage --music m.wav --beats-per-shot N`; `make_plan.py --beats` snaps zooms and key words |
| Cross-cut | Ready | hand-written spec that interleaves clips (no automatic interleave) |
| Freeze and slide | Ready | spec `freeze: [{at, dur}]` + `transition: "slideleft"` on the next clip |
| Speed-ramp transition | Ready | spec `speedRamp: [{at, rate, ramp}]` into the cut |
| Match cut (shape / colour) | Upgrade | needs a shot-pair search (embedding + histogram); Claude picks pairs by eye today |
| Match on action | Upgrade | needs motion analysis to place the cut a third into the move |
| Cut on blink | Upgrade | needs blink detection (face landmarks) |
| Smash cut | Upgrade | the cut works; needs a music drop-out field for the level contrast |

### 2b. A/B transitions (FFmpeg `xfade`, spec `transition: {"type": NAME, "dur": 0.4}`)

Audio crossfades for the same duration automatically. Each transition shortens the timeline by its duration.

| transition | tag | how (`type`) |
| --- | --- | --- |
| Cross dissolve | Ready | `fade` / `crossfade` / `dissolve` (dithered) / `fadefast` / `fadeslow` |
| Dip to black | Ready | `dip-black` (= `fadeblack`) |
| Dip to white / flash | Ready | `dip-white` (= `fadewhite`) |
| Fade through grey | Ready | `fadegrays` |
| Wipes | Ready | `wipeleft` `wiperight` `wipeup` `wipedown` |
| Soft wipes | Ready | `smoothleft` `smoothright` `smoothup` `smoothdown` |
| Diagonal wipes | Ready | `diagtl` `diagtr` `diagbl` `diagbr` `wipetl` `wipetr` `wipebl` `wipebr` |
| Iris | Ready | `circleopen` `circleclose` `circlecrop` `rectcrop` (frame-centred, not face-centred) |
| Clock wipe | Ready | `radial` |
| Barn doors | Ready | `vertopen` `vertclose` `horzopen` `horzclose` |
| Push / slide | Ready | `push` (= `slideleft`), `slideleft` `slideright` `slideup` `slidedown` |
| Cover / reveal | Ready | `coverleft` `coverright` `coverup` `coverdown` `revealleft` `revealright` `revealup` `revealdown` |
| Slices / blinds | Ready | `hlslice` `hrslice` `vuslice` `vdslice` |
| Wind | Ready | `hlwind` `hrwind` `vuwind` `vdwind` |
| Squeeze | Ready | `squeezeh` `squeezev` |
| Pixelize | Ready | `pixelize` |
| Blur dissolve | Ready | `hblur` |
| Distance morph | Ready | `distance` |
| Zoom-through | Ready | `zoom` (= `zoomin`) |
| Whip pan | Ready | `whip` (slide + 48 px horizontal motion blur); direction is not matched to camera motion |
| Luma fade | Upgrade | needs `xfade=custom` with a luma expression exposed in the spec |
| Spin, cube, page curl, ripple, swirl, doorway | Upgrade | needs a WebGL / gl-transitions stage |
| Lens-distortion transition | Upgrade | needs a ramped `lenscorrection` around the cut |
| Seamless zoom-in-to-zoom-out | Upgrade | needs per-clip scale ramps at the clip edges |
| Shape-morph wipe | Upgrade | needs SVG path morphing as an A/B mask |
| Pseudo-datamosh | Upgrade | needs a `minterpolate` smear mode at the cut |
| Object / body wipe | Upgrade | needs the MediaPipe person matte as an A/B mask; any other object needs SAM 2 (Heavy: Apache-2.0, GPU recommended) |
| AI morph | Heavy | RIFE (MIT) for a crude morph or a diffusion model (Wan-based VACE); GPU |

### 2c. Overlay transitions (plan element `{"type": "transition", "kind": K, "at": CUT, "dur": 0.4}`)

The frame is fully covered at `at`. These paint over a hard cut; they do not blend two clips.

| transition | tag | how (`kind`) |
| --- | --- | --- |
| Colour-band wipe | Ready | `wipe` (`dir`, `color`, `color2`) |
| Iris overlay | Ready | `iris` (`center: [fx, fy]`) |
| Shape mask | Ready | `shape-mask` (`shape`: `star` `diamond` `hex` `circle`) |
| Ink blot | Ready | `ink-blot` (`seed`) |
| Paper tear | Ready | `paper-tear` |
| Glitch / RGB slices | Ready | `glitch` |
| Whip blur bar | Ready | `whip-blur` |
| Light leak | Ready | `light-leak` |
| Flash to white | Ready | `flash-white`; or element `flash` with `times` (also `"beats"`) |
| Film burn | Ready | `film-burn` |
| Zoom blur ring burst | Ready | `zoom-blur` |

---

## 3. Effects

### 3a. Framing and camera

| effect | tag | how |
| --- | --- | --- |
| Zoom punch on a key word | Ready | plan `speaker.zooms` (`scale`, `ramp` 0.12, `snap`); themes add them via `auto.keywords.zoom` |
| Slow push-in | Ready | plan `speaker.push: 0.04` |
| Snap zoom | Ready | `speaker.zooms` with `snap: true` + `sfx` `whoosh-short` |
| Crash zoom with motion blur | Upgrade | needs a `tmix` / blur pass on fast zooms |
| Face-targeted punch-in | Ready | plan `speaker.zooms` centre on the primary face from plan `track` (`track.py analyze W/cut.mp4 --work W`, then `make_plan.py`); per zoom `cx`/`cy` (normalised source coords) aim anywhere; `toFace: false` keeps frame centre |
| Reframe crop point | Ready | plan `speaker.focusX`, `speaker.focusY` |
| Mirror | Ready | plan `speaker.mirror: true` |
| Speaker in a panel | Ready | plan `speaker.mode: "panel"`, `rect`, `radius` |
| Ken Burns on stills | Ready | spec image clips (default push-in, `kenburns`); element `image` with `motion: "kenburns"` |
| Device mock-up (phone / laptop / browser) | Ready | element `clip` with `device`, `motion` `flyIn` `tilt` `float` `orbit` |
| Picture-in-picture (picture) | Ready | element `clip` (from plan `clips`) placed with `x y w h`; the inset's own audio is not mixed |
| Picture-in-picture with its audio | Upgrade | needs clip audio in the mix graph |
| Split screen 2-4 up | Ready | element `split` (`panes` image or clip, `layout` `h` `v` `grid`); picture only |
| Face-follow reframe | Ready | `track.py reframe --format 9:16 --mode smooth\|fast\|locked`; `run.py --reframe 9:16`; spec `reframe: "face"`; `deliver.py --track` |
| Two-person stacked layout | Ready | `track.py reframe --layout stack2` (or `auto`) |
| Active-speaker cutting | Ready | `track.py reframe --follow active`; `multicam.py` (loudest mic) |
| Camera shake on graphics | Ready | element `shake: {amp, freq, rot, decay, seed}` |
| Camera shake / handheld drift on footage | Upgrade | needs a seeded `crop` offset on the speaker chain |
| Gate weave (whole frame) | Ready | plan `finish.weave: 2` |
| Stabilise | Ready | `prep.py --stabilize` / `run.py --stabilize` (two-pass vidstab, crops ~6%; `deshake` fallback) |
| Magnifier zoom-to-detail | Upgrade | needs a masked crop-and-scale copy |
| Dolly zoom (fake vertigo) | Upgrade | needs opposite scaling of matte and background |
| Rack focus / fake shallow depth | Heavy | Video Depth Anything Small (Apache-2.0) or Large (non-commercial); GPU |

### 3b. Time

| effect | tag | how |
| --- | --- | --- |
| Constant speed change | Ready | spec `speed` 0.25-4 (audio keeps pitch) |
| Speed ramp | Ready | spec `speedRamp: [{at, rate, ramp}]` |
| Smooth slow motion | Ready | spec `smooth: true` (FFmpeg `minterpolate`; slow, warps on complex motion) |
| AI slow motion | Heavy | RIFE (MIT); GPU or ncnn-vulkan build |
| Freeze frame | Ready | spec `freeze: [{at, dur}]`, `freezeEnd: 1.5`; pair with `sfx` `record-scratch` and a `lowerthird` |
| Reverse | Ready | spec `reverse: true` (keep clips short) |
| Boomerang | Ready | spec: the same clip twice, the second with `reverse: true` |
| Stutter / repeat on a beat | Ready | spec: repeat a short `in`/`out` range (hand-written) |
| Fast-forward / time-lapse up to 4x | Ready | spec `speed: 4` |
| Hyperlapse beyond 4x with deflicker | Upgrade | needs rates above 4 plus `tmix` and `deflicker` |
| Shutter motion blur | Upgrade | needs a `tmix` option |

### 3c. Texture and stylise

| effect | tag | how |
| --- | --- | --- |
| Film grain | Ready | plan `finish.grain: 8` or `{"strength": 10, "luma_weighted": true}`; element `grain` |
| Halation | Ready | plan `finish.halation: 0.4`; `color.halation` on the footage |
| Bloom / glow | Ready | plan `finish.bloom: 0.3` |
| Diffusion (Pro-Mist style) | Ready | plan `finish.diffusion: 0.5` |
| Chromatic aberration | Ready | plan `finish.aberration: 2` (px) |
| Sharpen | Ready | plan `finish.sharpen: 0.45` |
| Vignette | Ready | plan `finish.vignette: 0.5`; element `vignette` (`strength`, `size`, `color`) |
| Gate weave | Ready | plan `finish.weave: 2` |
| Brightness flicker | Ready | plan `finish.flicker: 0.02` |
| Letterbox | Ready | plan `finish.letterbox: 2.39`; element `letterbox` (`ratio`, animated bars) |
| Dither | Ready | plan `finish.dither: true` |
| Old-film damage | Ready | combine `finish.weave` + `finish.flicker` + `finish.grain` + look `sepia` or `kodachrome` |
| VHS / camcorder | Ready | look `vhs` or `90s-camcorder` + element `rec` (REC dot, timecode) |
| Light leak overlay | Ready | element `lightleak` (`intensity`, `colors`, `speed`, `seed`) |
| Lens flare / rays | Ready | element `shape` `kind: "rays"` or `"glow"` (alpha only, no screen blend) |
| Particles | Ready | element `shape` `kind` `sparkles` `bubbles` `confetti` `orbit`; element `burst` (emoji) |
| Decorative shapes | Ready | element `shape` `kind` `ring` `glow` `ribbon` `burst` `grid` `blob` `halftone` `spotlight` `frame` `bar` |
| Glitch burst | Ready | element `transition` `kind: "glitch"`; in-animation `glitch` |
| Audio-reactive waveform | Ready | element `waveform` with `beats.py --peaks` (plan `peaks`); `equalizer` is decorative only |
| Backgrounds | Ready | element `background` `kind` `solid` `gradient` `mesh` `paper` `grid` `dots`, or `image` |
| Echo trails | Upgrade | needs a `lagfun` option |
| Edge / sketch look | Upgrade | needs an `edgedetect` option |
| Duotone / brand tint | Upgrade | needs a two-colour mapping option |
| Mirror / kaleidoscope | Upgrade | needs a split + flip + stack option |
| Anamorphic streak | Upgrade | needs a horizontal-only highlight blur |
| Blend-mode overlays on video | Upgrade | overlays are alpha PNGs, so CSS `mix-blend-mode` cannot reach the footage |

### 3d. Compositing, masks and repair

| effect | tag | how |
| --- | --- | --- |
| Text / graphics behind the speaker | Ready | element `layer: "behind"` + `matte.py` (MediaPipe) |
| Background replace | Ready | an opaque full-frame element on `layer: "behind"` (image, `clip` or `background`) + the person matte |
| Green screen key | Ready | `matte.py --backend chroma`, then a `behind` background (no despill) |
| Cleaner hair matte | Heavy | `matte.py --backend rembg` (rembg, MIT; CPU, slower) |
| Before / after wipe | Ready | element `compare` (`before`, `after`, `wipeDelay`, `wipeDur`) |
| Background blur / desaturate | Upgrade | needs a matte-driven blur or desaturate of the speaker background |
| Subject outline / glow | Upgrade | needs an edge pass on the matte |
| Privacy blur / pixelate (fixed region) | Ready | plan `blurs: [{x, y, w, h, start, end, strength, pixelate, block}]` (output pixels, top-left box; under the graphics) |
| Tracked face blur (privacy, PII) | Upgrade | fixed boxes work (plan `blurs`); a box that follows `track.json` is not built |
| Tracked pixelate / censor | Upgrade | needs object tracking |
| Static logo removal | Upgrade | needs a `delogo` field |
| Video denoise | Ready | `prep.py --denoise light\|strong` / `run.py --denoise light\|strong` (`hqdn3d`) |
| Deflicker | Ready | `prep.py --deflicker` / `run.py --deflicker` (`deflicker`, 5-frame window) |
| Screen replacement | Upgrade | needs homography tracking |
| Clone (same person twice) | Upgrade | needs a split-screen matte for locked-off shots |
| Beauty / skin smoothing | Upgrade | needs a face-mesh skin mask |
| Tracked callout or text on a moving object | Upgrade | `anchorTo: "face"` works for faces only; objects need a point tracker |
| Object removal | Heavy | ProPainter (non-commercial, ~19 GB VRAM at 720p) or LaMa per frame (Apache-2.0) |
| Object-level text behind | Heavy | SAM 2 (Apache-2.0); GPU recommended |
| Sky replacement | Heavy | SAM 2 sky mask + plate tracking |
| 2.5D parallax photo | Heavy | Depth Anything V2 Small (Apache-2.0) + LaMa fill |
| Upscale | Heavy | Real-ESRGAN (BSD-3); ncnn-vulkan builds run on most GPUs |
| Face restore (old photos) | Heavy | GFPGAN (Apache-2.0) or CodeFormer (non-commercial) |
| Relight | Heavy | depth/normal models; GPU |
| Eye contact | Heavy | no permissively licensed model found |
| Generative B-roll / extend | Heavy | Wan 2.2 (reported Apache-2.0, ~24 GB VRAM) |

### 3e. Assembly and analysis

| effect | tag | how |
| --- | --- | --- |
| Multi-clip timeline | Ready | `timeline.py build SPEC --work W`; `run.py --clips A B C` / `--timeline spec.json` |
| Auto montage / story / highlights | Ready | `timeline.py auto FOLDER --mode montage\|story\|highlights --duration 30` (`--dry-run` to edit) |
| Selects + paper edit | Ready | `selects.py --work W --input long.mp4`, edit `paper_edit.md`, then `--apply` |
| Story outline and reorder | Ready | `story.py outline --work W`; `story.py reorder --order "s3,s1-s2"` |
| Best short-form moments | Ready | `clip_candidates.py --work W --min 20 --max 60` |
| Shot / black / freeze / flash detection | Ready | `scenes.py INPUT --work W` |
| Face tracking + active speaker | Ready | `track.py analyze INPUT --work W` |
| Auto B-roll placement | Ready | `broll.py --work W --library broll/ --merge W/plan.json` (file-name keywords) |
| Semantic B-roll matching | Upgrade | `open_clip` is listed in `check_env.py` but not used by `broll.py` yet |
| Multicam switch | Ready | `multicam.py camA camB --wide wide.mp4 --audio mix.wav` |
| Multicam waveform sync | Upgrade | needs audio cross-correlation; trim with `prep.py --start` today |
| Editor review and fixes | Ready | `editor.py review plan.json --genre G --fix` |

---

## 4. Text, title and caption animations

Every element takes `in`, `out` (name or `{name, dur, ease, dir, dist, spring}`), `ease`, `keys`, `shake`, `pulseOn`
and `anchorTo`. Text elements are `text`, `headline`, `chip`, `tile` and `sticker`.

### 4a. Entrances and exits (`in` / `out`)

| animation | tag | how |
| --- | --- | --- |
| Fade | Ready | `in: "fade"` |
| Pop | Ready | `in: "pop"` |
| Bounce | Ready | `in: "bounce"` |
| Rise / drop | Ready | `in: "rise"` (`slideUp`), `"drop"` (`slideDown`) |
| Slide left / right | Ready | `in: "slideLeft"`, `"slideRight"` |
| Scale down / zoom in | Ready | `in: "scale"`, `"zoomIn"` |
| Blur-scale | Ready | `in: "blur"` |
| Spin | Ready | `in: "spin"` |
| Wipe / wipe up | Ready | `in: "wipe"`, `"wipeUp"` |
| Stamp / slam | Ready | `in: "stamp"` (+ `shake` with `decay`, element `flash`, `sfx` `impact` for a full slam) |
| Card flip | Ready | `in: "flip"` |
| Glitch jitter | Ready | `in: "glitch"` (position jitter, not RGB copies) |
| Mask line reveal | Ready | `in: "maskUp"` `"maskDown"` `"maskLeft"` `"maskRight"` |
| Iris reveal | Ready | `in: "iris"` |
| Clock wipe reveal | Ready | `in: "clockWipe"` |
| Enter from off frame | Ready | `in: "slideUpFull"` |
| Push | Ready | `in: {"name": "push", "dir": "up"}` |
| Zoom out with blur | Ready | `in: "zoomOut"` |
| Whip in | Ready | `in: {"name": "whip", "dir": "left"}` |
| Elastic | Ready | `in: "elastic"` |
| Spring pop | Ready | `in: {"name": "springPop", "spring": {"stiffness": 240, "damping": 14}}` |
| Rotate in | Ready | `in: "rotateIn"` |
| 3D door swing | Ready | `in: "swing3d"` |
| Unfold | Ready | `in: "unfold"` |
| Blur in | Ready | `in: "blurIn"` |
| Typewriter (non-text) | Ready | `in: "typewriter"` (stepped wipe on non-text elements) |
| Easing presets | Ready | `ease`: `linear` `out` `in` `inOut` `back` `elastic`, `quad/cubic/quint/expo/circ/sine/back` + `In/Out/InOut`, `elasticOut`, `bounce` `bounceIn` `bounceInOut` |
| Custom bezier / spring easing | Ready | `ease: "cubic-bezier(0.16,1,0.3,1)"`, `[0.16,1,0.3,1]`, `"spring"` or `{"spring": {...}}` |

### 4b. Kinetic type and text effects

| animation | tag | how |
| --- | --- | --- |
| Per-word / per-letter cascade | Ready | `split: "words"` or `"chars"`, `stagger`, `unitIn`, `unitDur`, `unitEase` |
| Line-by-line mask reveal | Ready | `split: "lines"` (default `unitIn: "maskUp"`, `stagger: 0.12`) |
| Typewriter with caret | Ready | `fx: {"name": "typewriter", "cps": 18, "caret": "\|"}` |
| Scramble / decode | Ready | `fx: "scramble"` (`dur`, `every`, `seed`) |
| Split-flap board | Ready | `fx: "splitflap"` |
| Highlighter swipe | Ready | `fx: {"name": "highlight", "target": "one habit"}` |
| Underline sweep | Ready | `fx: "underline"` |
| Strike-through | Ready | `fx: "strike"` (follow with a new element for the replacement word) |
| Gradient sweep | Ready | `fx: "gradientSweep"` |
| Counting numbers in text | Ready | `fx: "countWords"` |
| Outline draw, then fill / signature | Ready | `fx: "stroke-draw"` (single line only) |
| Karaoke fill on a text box | Ready | `fx: "karaoke-fill"` (sweeps the whole box) |
| Auto-fit headline | Ready | `fit: true` (default on `headline`) |
| Keyframed move / scale / rotate / opacity / blur | Ready | `keys: {x, y, tx, ty, s, r, o, blur}` |
| End-credits roll | Ready | `keys: {"ty": [[0, H], [30, -2000, "linear"]]}` |
| Beat pulse | Ready | `pulseOn: "beats"` or `"downbeats"` (plan `beats`) |
| Kinetic word stack on beats | Ready | `split: "words"` + `make_plan.py --beats` snapping; `kinetic-launch` skin |
| Text that follows a face | Ready | `anchorTo: "face"`, `offset: [dx, dy]` (plan `track`) |
| Text behind the head | Ready | `layer: "behind"` + matte |
| Static 3D / extruded type | Ready | layered `text-shadow` in `style` or `theme.css` (not animated) |
| Idle bob / drift / wobble | Ready | `float`, `drift`, `wobble` |
| Tracking-out title | Upgrade | needs `letter-spacing` in `keys` (static spacing works via `style`) |
| Wave text | Upgrade | needs a per-unit sine offset |
| Neon flicker | Upgrade | needs a seeded opacity-flicker option (hand-written `keys.o` is possible) |
| RGB-split glitch text | Upgrade | needs stacked colour copies |
| Variable-font weight pulse | Upgrade | needs `font-variation-settings` in `keys` |
| Word carousel / rotating word | Upgrade | needs a vertical ticker component |
| Liquid / blob text | Upgrade | needs SVG displacement filters |
| Perspective crawl | Upgrade | needs `rotateX` in `keys` |
| Text on a path | Upgrade | needs SVG `textPath` |
| Lottie stickers | Upgrade | needs lottie-web bundled in the runtime |

### 4c. Titles, cards and data graphics

| item | tag | how |
| --- | --- | --- |
| Lower third | Ready | element `lowerthird` (`name`, `role`) |
| Title card / chapter card | Ready | element `titlecard` (`kicker`, `title`, `subtitle`) |
| List / info card | Ready | element `card` (`title`, `items` with `at`, `numbered`, `image`, `clip`; classes `glass`, `paper`) |
| Pull quote | Ready | element `quote` (`text`, `author`, `role`) |
| Counter / number roll | Ready | element `counter` (`from`, `to`, `prefix`, `suffix`, `decimals`) |
| Bar chart | Ready | element `bars` |
| Bar-chart race | Ready | element `barrace` (`data`, `labels`, `top`) |
| Line chart | Ready | element `linechart` |
| Pie / donut | Ready | element `piechart` / `pie` / `donut` |
| Map route with pins | Ready | element `map` (seeded dot-grid land, not real geography) |
| Callout with leader line | Ready | element `callout` (`point`, or `anchorTo: "face"`) |
| Arrow / tapping hand | Ready | element `pointer` / `arrow` (`kind` `arrow` or `hand`); element `scribble` `kind: "arrow"` |
| Hand-drawn marks | Ready | element `scribble` `kind` `circle` `underline` `box` `cross` `check` `highlight` `zigzag` |
| Steps / timeline | Ready | element `steps` |
| Checklist | Ready | element `checklist` (`items` with `at`, `strike`) |
| Countdown timer | Ready | element `timer` (`from`, `warnAt`) |
| Poll | Ready | element `poll` |
| Chat thread | Ready | element `chat` (`messages` with `at`, typing dots) |
| Notification | Ready | element `notification` |
| Search bar | Ready | element `searchbar` (`query`, `results`) |
| Code block | Ready | element `codeblock` (`cps`, `diff`, `lineNumbers`) |
| Subscribe button | Ready | element `subscribe` (`clickAt`, `bellAt`) |
| Social post card | Ready | element `socialpost` (generic card only, never a real platform's UI or a real person's post) |
| Rating stars | Ready | element `stars` (real reviews only) |
| News ticker | Ready | element `ticker` |
| Progress bar | Ready | element `progress` (`position`) |
| Sticker / chip / tile labels | Ready | elements `sticker`, `chip`, `tile` |

### 4d. Captions and subtitles

| item | tag | how |
| --- | --- | --- |
| Word-by-word reveal | Ready | element `captions` `mode: "reveal"` |
| Active-word highlight (all words shown) | Ready | `mode: "karaoke"`, `activeScale`, `activePop` |
| One word at a time | Ready | `mode: "single"` |
| Karaoke fill per word | Ready | `mode: "fill"`; preset `karaoke` |
| Static phrase captions | Ready | `mode: "static"`; preset `clean` |
| Bold caps, active word coloured | Ready | `preset: "hormozi"` |
| Chunky caps, colour cycle, tilt | Ready | `preset: "beast"` |
| Active word on an accent box | Ready | `preset: "boxed"` |
| Small lower reveal | Ready | `preset: "minimal-lower"` |
| Caption class looks | Ready | `className` `cap-pill` `cap-box` `cap-outline` `cap-soft` `cap-dim` |
| Key words in accent colour | Ready | `keywords: ["nobody"]` |
| Emoji pop on a word | Ready | `emoji: {"money": "💰"}` |
| Reading-speed limit | Ready | `cpsMax` (default 20), `minDur` 0.3 |
| Safe-zone clamp | Ready | `safe: true` (default): 10-85% of height, clear of the right 12% in 9:16 |
| Dodge the face / a graphic | Ready | `dodgeFace: true`; `dodge: [{start, end, y}]` |
| Sentence-only breaks | Ready | `breakOnPunct: "sentence"` |
| Dual-language captions | Ready | theme `auto.captions2` (the `dual-subs` skin); Claude translates |
| Lyric lines with next line dimmed | Ready | element `lyric` (`lines`, or `P.words` grouped by `maxWords`) |
| Broadcast subtitle files | Ready | `deliver.py` writes `captions.srt`, `.vtt`, `.ttml` (42 chars x 2 lines, 20 cps, 0.833-7 s, 2-frame gaps) |
| Kids reading speed | Ready | `deliver.py --kids` / `qc.py --kids` (17 cps) |
| Burned-in subtitles | Ready | `deliver.py --burn auto\|yes\|no`, `--burn-engine libass\|pillow` |
| SDH subtitles | Ready | `accessibility-pack` skill + `deliver.py --words` with `[sound]` tags |
| SCC (CEA-608) captions | Upgrade | needs a CEA-608 encoder; there is no free one |
| Speaker diarisation for captions | Heavy | needs a diarisation model (for example pyannote); not wired in |

---

## 5. Colour

Order is always: input transform, correction, shot match, look (all on the footage, before graphics), then texture and legal (on the finished frame).

### 5a. Correction tools

| tool | tag | how |
| --- | --- | --- |
| Auto correction (levels, WB, contrast, saturation) | Ready | plan `color.auto: true` (default) |
| White balance (auto / Kelvin / off) | Ready | `color.wb: true \| 5600 \| "off"`, `wb_strength` |
| Exposure | Ready | `color.exposure` (stops) |
| Contrast / saturation | Ready | `color.contrast`, `color.saturation` |
| Log to Rec.709 (approximate) | Ready | `color.log`: `slog3` `vlog` `clog3` `applelog` `flog` (generated from published formulas) |
| Official camera LUT | Ready | `color.lut: "path/to/official.cube"` |
| Shot-to-shot match | Ready | `color.match: "ref.png"` (Reinhard Lab, baked to a .cube), `match_strength` |
| Per-clip basic match in a timeline | Ready | spec clip `color: {brightness, contrast, saturation, gamma}` |
| Per-clip auto correction inside a timeline | Upgrade | plan `color` runs on the assembled source; needs per-clip analysis |
| Skin protection | Ready | built into every LUT look (hue-range, per-look strength) |
| Face-mask skin protection | Upgrade | needs a MediaPipe face mask in the look stage |
| Looks preview sheet | Ready | `color.py looks-sheet VIDEO --t 3 --out sheet.png [--correct]` |
| Single-frame preview | Ready | `color.py preview VIDEO --look portra --intensity 0.8 --correct` |
| Scopes (waveform, parade, vectorscope) | Ready | `color.py scopes VIDEO --t 3 --out s.png` |
| Legal levels | Ready | plan `finish.legal: "strict"` (Y 16-235, default) \| `"ebu"` \| `false` |
| Colour QC | Ready | `color.py qc VIDEO` (signalstats vs EBU R103); part of `qc.py` |
| BT.709 tagging | Ready | every `deliver.py` encode |
| Power window / tracked vignette | Upgrade | needs a feathered, face-tracked mask |
| Hue qualifier / secondary correction | Upgrade | needs `huesaturation` / `selectivecolor` fields |
| HDR to SDR tone map | Upgrade | needs a `zscale` + `tonemap` input stage |
| HDR delivery | Upgrade | `youtube-hdr` is a note only; needs a 10-bit Rec.2020 PQ/HLG grade |
| 10-bit grading pipeline | Upgrade | the pipeline works in 8-bit `yuv420p` |
| ACES / OCIO pipeline | Upgrade | needs OpenColorIO-baked LUTs |
| Fashion true-colour to a chart | Upgrade | needs chart-based colour mapping (use correction + `color.match` today) |

### 5b. Looks (51; plan `color.look: NAME`, `color.intensity` 0-1, or theme `finish.grade: NAME`)

Skin = how strongly the look is pulled back inside the skin-hue range. "-" = not protected.

| look | tag | skin | use for |
| --- | --- | --- | --- |
| `portra` | Ready | 0.30 | warm soft portraits, lifestyle, interviews |
| `kodak-2383` | Ready | 0.25 | print-film contrast for narrative and brand |
| `ektachrome` | Ready | 0.35 | punchy cool slide film: travel, product |
| `fuji-eterna` | Ready | 0.30 | muted cinema negative: drama, documentary |
| `fuji-velvia` | Ready | 0.50 | vivid landscapes and nature |
| `cinestill-800t` | Ready | 0.30 | night city and tungsten (add `color.halation`) |
| `kodachrome` | Ready | 0.35 | rich retro colour, nostalgia |
| `bleach-bypass` | Ready | - | gritty, desaturated: action, sport |
| `cross-process` | Ready | 0.20 | lo-fi fashion and music |
| `golden-hour` | Ready | 0.30 | warm sunset feel |
| `blue-hour` | Ready | 0.30 | cool dusk, calm |
| `moody` | Ready | 0.40 | dark desaturated storytelling |
| `high-key` | Ready | 0.20 | bright airy beauty and wellness |
| `low-key` | Ready | 0.20 | dramatic dark, premium product |
| `desert` | Ready | 0.30 | hot dusty western, adventure |
| `nordic` | Ready | 0.40 | cool clean minimal |
| `horror-green` | Ready | 0.15 | sickly green-cyan unease |
| `dreamy` | Ready | 0.30 | soft romantic memories (adds a glow) |
| `finance-navy` | Ready | 0.60 | finance and B2B explainers |
| `indian-wedding` | Ready | 0.65 | warm gold and rich reds, natural skin |
| `wedding-pastel` | Ready | 0.50 | soft pastel western weddings |
| `day-for-night` | Ready | - | fake night from daylight |
| `infrared` | Ready | - | Aerochrome-style false colour |
| `selective-red` | Ready | - | black and white with reds kept |
| `matrix` | Ready | 0.20 | green tech and sci-fi |
| `teal-orange-pro` | Ready | 0.70 | blockbuster teal and orange, natural skin |
| `clean-commercial` | Ready | 0.30 | clean neutral ads and corporate |
| `documentary-natural` | Ready | 0.30 | true-to-life documentary and news |
| `music-video-neon` | Ready | 0.40 | magenta and cyan nightlife |
| `sepia` | Ready | - | old photos, history |
| `two-strip` | Ready | - | 1930s two-strip Technicolor |
| `cyberpunk` | Ready | 0.40 | magenta and teal night: gaming, tech |
| `vintage-70s` | Ready | 0.30 | faded warm olive retro |
| `90s-camcorder` | Ready | 0.20 | home-video nostalgia (adds softness and RGB shift) |
| `sunset` | Ready | 0.30 | strong warm and magenta sky |
| `cool-corporate` | Ready | 0.50 | SaaS, tech and corporate interviews |
| `food-pop` | Ready | 0.30 | warm reds, oranges, yellows for food |
| `real-estate-bright` | Ready | 0.20 | bright interiors, open shadows |
| `gaming-vivid` | Ready | 0.30 | gaming and esports |
| `warm` / `cool` | Ready | - | legacy simple shifts |
| `teal-orange` | Ready | - | legacy teal and orange (prefer `teal-orange-pro`) |
| `punchy` | Ready | - | legacy contrast and saturation boost |
| `film` | Ready | - | legacy faded film curve |
| `bw` / `noir` | Ready | - | legacy black and white / high-contrast noir |
| `vintage` / `faded` / `pastel` | Ready | - | legacy retro, faded, pastel |
| `neon` | Ready | - | legacy saturated neon |
| `vhs` | Ready | - | legacy VHS (RGB shift, half-res softness) |
| Spectral film-stock emulation | Upgrade | - | today's film looks are craft characterisations, not measured stock data |

(The table lists 39 LUT looks and 12 legacy grades in 45 rows, because some legacy rows hold two or three names. `none` is the 52nd name.)

---

## 6. Sound moves

### 6a. Dialogue (plan `audio.voice`, applied by `finish.py`)

| move | tag | how |
| --- | --- | --- |
| High-pass by voice | Ready | `audio.voice.voice: "male" \| "female" \| "auto"` (80 / 110 Hz), `hpf` to override |
| De-hum | Ready | `audio.voice.dehum: 50 \| 60` |
| De-click (mouth clicks) | Ready | `audio.voice.declick: true` |
| De-noise | Ready | `audio.voice.denoise: "light" \| true \| "strong"` (afftdn) |
| RNNoise de-noise | Ready | `audio.voice.rnnoise: "model.rnnn"` (you supply the model file) |
| Clarity / warm / broadcast EQ | Ready | `audio.voice.eq: "clear" \| "warm" \| "broadcast" \| "off"` |
| Telephone / radio voice | Ready | `audio.voice.eq: "phone"` (300-3400 Hz) \| `"radio"` (200-5000 Hz) |
| De-ess | Ready | `audio.voice.deess: true` or 0-1 |
| Gate (lowers gaps, never mutes) | Ready | `audio.voice.gate: true` |
| Dialogue compression | Ready | on by default (3:1, makeup x2); `audio.voice.compress: false` to turn off |
| No dialogue chain | Ready | `audio.voice: false` |
| Room-tone fill at cuts | Ready | plan `roomTone: true` (needs `cutlist.json`) |
| Click-free joins | Ready | `autocut.py --smart-cuts` (quietest point) + `--xfade-ms`; timeline 30 ms crossfades |
| Try a chain on a file | Ready | `audio_chain.py voice in.wav out.wav --cfg '{...}'` |
| Heavy de-noise / speech enhance | Heavy | Resemble Enhance (MIT) or DeepFilterNet (licence unconfirmed); GPU helps |
| Plosive fix | Upgrade | needs onset detection + local high-pass |
| Breath attenuation | Upgrade | autocut keeps breaths (`--breath`); turning them down needs VAD-driven gain |
| Per-speaker level match | Upgrade | needs diarisation + per-speaker loudness |
| Lav / boom mic match | Upgrade | needs spectrum matching |
| Mono-compatibility check | Upgrade | needs a phase-correlation check in QC |
| Megaphone / underwater / inner-voice treatments | Upgrade | needs extra EQ presets (`acrusher`, `chorus`, `aecho`) |
| Perspective match (close vs wide) | Upgrade | needs per-shot reverb and EQ |

### 6b. Music (plan `music`)

| move | tag | how |
| --- | --- | --- |
| Music bed under dialogue | Ready | `music.src` + `under: 20` (LU under the dialogue) or `volume` |
| Sidechain ducking | Ready | `music.duck: true` (`duckDepth`, `duckAttack`, `duckRelease`) |
| Speech-aware ducking | Ready | `music.duck: "speech-aware"` (dips on each spoken phrase from `plan.words`) |
| Cut music to length on bars | Ready | `music.fitTo: "beats"`; CLI `music_fit.py music.mp3 --duration 14.7 --out fitted.wav` |
| End on a hit (button) | Ready | `music.endButton: true`; `music_fit.py --ending button` |
| Fade out | Ready | `music.fadeOut: 1.5` |
| Beats, downbeats, onsets | Ready | `beats.py music.mp3 --out W/beats.json [--peaks]` |
| Montage music bed | Ready | spec `music: {src, volume, duck, fadeOut}` |
| Clip audio keep / mute / duck | Ready | spec clip `audio: "keep" \| "mute" \| "duck"`, `volume` |
| Stem split (vocals / music) | Heavy | `stems.py song.mp3 --out W/stems` (Demucs, MIT; slow on CPU) |
| Silence before the drop / pre-reveal suck-out | Upgrade | needs a music drop-out window field |
| Tempo match | Upgrade | needs rubberband |
| Key detect / shift | Upgrade | needs chroma analysis + pitch shift |
| Music generation | Heavy | MusicGen (CC-BY-NC weights, personal use) or Stable Audio Open (own licence) |

### 6c. Sound effects (plan `sfx: [{t, kind, gain}]` or `{t, file, gain}`; 49 procedural kinds, no sample files)

| move | tag | how (`kind`) |
| --- | --- | --- |
| Whooshes for transitions and moves | Ready | `whoosh` `whoosh-short` `whoosh-long` `swish` `swoosh-up` `swoosh-down` |
| Impacts for reveals and slams | Ready | `impact` (`hit`) `hit-hard` `boom` `thud` `braam` |
| Low-end drops | Ready | `sub-drop` `bass-drop` |
| Tension builds | Ready | `riser` (1.2 s) `riser-long` (4 s) `reverse-cymbal` (2 s) `drum-roll` |
| Comedic stops | Ready | `record-scratch` `tape-stop` `rewind` `boing` `slide-whistle` |
| UI and screen sounds | Ready | `ui-tap` `ui-swipe` `click` `pop` `digital-beep` `notification` `type` `typewriter-key` |
| Results and rewards | Ready | `success-chime` `error-buzz` `ding` `glass-ding` `coin` `cash-register` `sparkle` |
| Time and tension | Ready | `tick-tock` `clock-tick` `countdown-beep` (3-2-1-go) `heartbeat` |
| Tech glitch | Ready | `glitch` |
| Camera | Ready | `camera` `camera-shutter` (`shutter`) |
| Crowd and room | Ready | `applause-light` (`applause`) `crowd-gasp` `wind` `room-tone` `page-turn` |
| Your own sound file | Ready | `{"t": 3, "file": "my_hit.wav", "gain": 0.6}` |
| Audition | Ready | `audio_chain.py sfx impact --out impact.wav`; `sfx --all --out-dir sfx` |
| Theme-driven SFX | Ready | theme `auto.keywords.sfx`, `auto.cuts.sfx`, `auto.hook.sfx`, `auto.numbers.sfx` |
| Stinger in the music's key | Upgrade | needs key detection |
| Continuous ambience bed | Upgrade | needs a long procedural ambience generator |

### 6d. Voice generation

| move | tag | how |
| --- | --- | --- |
| Offline voice-over (system voices) | Ready | `tts.py --script vo.txt --out W/voice.wav --words` (Windows SAPI, macOS `say`, espeak-ng) |
| Best offline voice-over | Heavy | `tts.py --backend kokoro` (Kokoro-82M, Apache-2.0; small, runs on CPU) |
| Piper voice-over | Heavy | `tts.py --backend piper --voice voice.onnx` (GPL-3.0; run as a separate program) |
| Script-aligned words for captions | Ready | `tts.py --words` (writes `words.json`) |
| Voice cloning | Heavy | XTTS-v2 / F5-TTS (non-commercial weights) or OpenVoice V2 (MIT); with consent only |
| Lip-sync for dubs | Heavy | LatentSync (Apache-2.0, GPU) or Wav2Lip (non-commercial) |

### 6e. Mix and loudness

| move | tag | how |
| --- | --- | --- |
| Platform loudness | Ready | `finish.py --platform NAME` or plan `audio.platform`: `youtube` `facebook` `tiktok` `reels` `instagram` `shorts` `social` `spotify` `podcast` `apple` `broadcast-eu` (`ebu`) `broadcast-us` (`atsc`) `netflix` `cinema` |
| Custom target | Ready | plan `audio.lufs`, `audio.tp`, `audio.lra`; `finish.py --lufs` |
| True-peak limiting | Ready | measured gain into an oversampled limiter (ceiling = TP - 0.5 dB for AAC) |
| Two-pass loudnorm on a file | Ready | `audio_chain.py loudnorm IN OUT --platform podcast` |
| Measure | Ready | `audio_chain.py measure final.mp4 --platform youtube` |
| Netflix dialogue-gated loudness | Upgrade | measured on the full programme today (approximate) |
| DX / MX / FX stems that null | Upgrade | dialogue stem works by dropping music and SFX; a true M&E needs separated production audio |
| 5.1 mix and downmix | Upgrade | stereo only |

---

## 7. Delivery presets and extras

`deliver.py PLAN_OR_VIDEO --to a,b,c` (`deliver.py --list` prints the live table). Every video encode is BT.709-tagged with two-pass loudness. Aspect changes reframe on the face when a `track.json` exists; otherwise they centre-crop or use a blurred fill.

| preset | tag | output |
| --- | --- | --- |
| `youtube` | Ready | 1920x1080 H.264 High 8 Mb/s, closed GOP, faststart, -14 LUFS |
| `youtube-4k` | Ready | 3840x2160 H.264 40 Mb/s |
| `youtube-hdr` | Upgrade | note only: needs a 10-bit Rec.2020 PQ/HLG grade |
| `shorts` | Ready | 1080x1920, 3 min max |
| `reels` | Ready | 1080x1920, 3 min recommended |
| `tiktok` | Ready | 1080x1920, 10 min (API) |
| `linkedin` | Ready | 1080x1350 (4:5) |
| `x` | Ready | 1280x720, 140 s (free tier) |
| `facebook` | Ready | 1080x1350 (4:5) |
| `snapchat` | Ready | 1080x1920, 60 s |
| `pinterest` | Ready | 1080x1920, 60 s |
| `whatsapp-status` | Ready | 720x1280, 60 s, bitrate lowered to fit 16 MB |
| `podcast-video` | Ready | 1920x1080, -16 LUFS |
| `web-h265` | Ready | x265 CRF 24, `hvc1` tag |
| `web-av1` | Ready | SVT-AV1 CRF 32 (libaom fallback) |
| `prores-422hq` | Ready | ProRes 422 HQ 10-bit, mix untouched (24-bit PCM) |
| `prores-4444` | Ready | ProRes 4444 (alpha when the input has alpha) |
| `dnxhr-hq` | Ready | DNxHR HQ, mix untouched |
| `broadcast-xdcam` | Ready | XDCAM-like MPEG-2 4:2:2 50 Mb/s 1080i25 MXF, -23 LUFS (not AS-11 / RDD9 conformance-checked) |
| `gif` | Ready | 6 s preview, 480 px, 128 colours |
| `webp` | Ready | 6 s animated WebP preview |
| `audio-wav` | Ready | 48 kHz / 24-bit mix, untouched |
| `podcast-mp3` | Ready | MP3 192k, -16 LUFS |

| extra | tag | how |
| --- | --- | --- |
| Subtitle sidecars | Ready | always written: `captions.srt`, `.vtt`, `.ttml` |
| Chapters | Ready | `--chapters "0:00 Intro; 1:20 Setup"`, plan `chapters`, or automatic; embedded in MP4/MOV, `chapters.txt` |
| Thumbnails | Ready | `thumb_1_left.png` `thumb_2_right.png` `thumb_3_bottom.png` (1280x720), `thumb_cover_1080x1920.png`; `--headline`, `--no-thumbs` |
| Post pack | Ready | `post.md` (titles, description, hashtags from the transcript); `--no-post` |
| Trim to the platform maximum | Ready | `--trim` |
| Delivery report | Ready | `deliver_report.json` / `.md` |
| EDL / FCPXML / OTIO hand-off | Ready | `export_edl.py W --out-dir W/handoff` (cut only; overlays travel as ProRes 4444) |
| Overlays as ProRes 4444 with alpha | Ready | `render.py plan.json --keep`, then `export_edl.py --encode-alpha "W/render/front/%05d.png"` |
| Automated QC report | Ready | `qc.py VIDEO --plan PLAN --platform NAME [--strict] [--kids]` (spec, loudness, black/flash frames, photosensitivity, legal levels, caption cps, overlays, safe zones, faststart, GOP, A/V timing) |
| Textless version | Ready | render a copy of the plan without text elements |
| Broadcast slate, bars and tone | Upgrade | not generated |
| IMF / AS-11 packages | Upgrade | not generated |
