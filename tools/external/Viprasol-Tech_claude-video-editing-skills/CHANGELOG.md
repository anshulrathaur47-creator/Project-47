# Changelog

## v2.2.0 (2026-11-20)

### Added

- Scene recipes for five more skins, auto-applied by `run.py` (`theme.json` `"sequence"`): `aurora` (glow-cutout), `retro` (poster-pop), `explainer` (editorial-cards), `eclipse` (neon-marquee), `layercut` (grid-stage). Recipes are plug-ins in `scripts/recipes/`.
- Hindi/Haryanvi: `profile.py` creator profile (language, script, platform, fonts); risky detections (ur/pa/sd/ne) fall back to the profile language; `transcribe.py --text` maps your own lines onto the speech timing; Devanagari key-word scoring and stop list; `poetry-reel` genre preset.
- Local review app: `app/server.py` (FastAPI, 127.0.0.1 + token): play, fix caption words, change style, re-plan, stills, render, live log.
- QC perceptual checks: caption script vs language, missing glyphs, text over the face, black tail.
- Matte: guided-filter edges, motion-aware smoothing, lossless output, `matte.json` edge contact (planners avoid showing frame edges).
- Audio: equal-power crossfades and room tone at every join, Silero VAD silence map, wind/rumble high-pass.

### Changed

- Overlay rendering about 2.3x faster (faster capture, frame reuse), same output.
- Grapheme-safe text effects (Intl.Segmenter) and danda-aware caption breaks; Devanagari font fallbacks.
- Thumbnails pick fonts by script (no tofu) and keep titles off the face.

### Fixed

- Windows: printing Devanagari through a pipe no longer crashes (UTF-8 output guard).
- Timeline speed ramps no longer crash; `dissolve` is a true crossfade (`dither-dissolve` keeps the old look).
- The last headline no longer drops to black at the end.

## v2.1.0 (2026-11-17)

### Added

- 6 skins: `glow-cutout`, `poster-pop`, `glass-ribbon`, `editorial-cards`, `neon-marquee`, `grid-stage` (46 skins in total).
- `render.py`: `speaker.backdrop` (`blur` / `hide`) shows a blurred copy of the shot or only the HTML backgrounds around the person cut-out; `speaker.glow` adds a rim glow; `personScale` / `personDrop` resize or lower the cut-out with a faded top edge; `speaker.layouts` moves the footage between tilted, rounded cards over time.
- `make_plan.py`: a headline or key-word template can be a list (a group of elements with the same timing); `auto.headlines.layouts` cycles card layouts per sentence; every sentence gets its headline (falls back to the longest word).

- `sequence.py --recipe ribbon`: scene sequencer for `glass-ribbon` - every phrase alternates a person scene (ticking frosted card, glass icons, phrase pill, payoff line) and a type-only scene (stacked glass notes, two-tone big type, search bar typing the next phrase), joined by `softCuts` (full-frame blur pulses) and whooshes.
- `render.py` plan `softCuts`; `checklist` `html` titles; elements with `"decor": true` are scenery that QC and the overlay review skip.

### Fixed

- Indic scripts: key-word matching (engine.js) and word scoring (make_plan.py) no longer strip vowel signs (Unicode category M), so Hindi/Haryanvi key words and headlines work. The Devanagari danda and a comma followed by a pause end a phrase.
- Back-to-back snap zooms no longer add their face offsets twice.
- Headlines hand over 0.08 s before the next sentence instead of overlapping (which dropped every other one).

## v2.0.0 (2026-11-17)

v2 turns the pack from 40 caption styles into a complete editor. Genre skills now decide how a video is cut. The 40 styles become skins that decide how it looks. The core gains the tools and the editorial judgement both depend on.

### Added

**Director (the boss skill)**

- `video-director` skill + `director.py`: hand over any footage and it reads it first (speech coverage, wpm and language from a faster-whisper probe, faces and face size via MediaPipe, beat steadiness, screen-recording look, shot rate, light, orientation, durations, photo/clip/audio counts). It scores all 42 genre skills with reasons, weighs the user's goal above the footage, and writes `director.md` plus a ready `run.py` command (genre, skin, format, platform, clean-up flags). Claude makes the final call and runs the chosen genre skill end to end.
- `editor.py` cut review: wordless montages are judged on rhythm, not on "mid-thought" speech cuts. On timeline assemblies, only joins within the same source count as jump cuts.

**Engine modules (video-studio-core)**

- **Editor brain** (`editor.py`, `genres.json`): 69 genre presets covering pacing, ASL range, cut rules, captions, music, SFX density, allowed transitions, hook rules, structure beats, loudness and safe zones. Includes Rule-of-Six-lite cut scoring, pacing, retention, overlay and caption checks, and `review --fix` for safe automatic fixes.
- **Story and selects** (`story.py`, `selects.py`): outline and hook candidates, reorder into a timeline spec, best-take selects and an editable paper edit. A FRANKENBITE flag warns about constructed quotes.
- **Smart autocut** (`autocut.py`): cuts at the quietest point, keeps breaths, removes retakes, J-cuts at sentence joins (`--jcut N`), filler policies and genre defaults (`--genre`).
- **Timeline** (`timeline.py`): multi-clip build and `auto` (montage, story, highlights). It supports 58 FFmpeg xfade transitions plus dip-black, dip-white and whip, J/L cuts, constant speed, speed ramps, optical-flow slow motion, freeze, reverse, Ken Burns stills and beat-cut montages. Timing is frame-exact, and audio crossfades on every join.
- **Analysis and reframe** (`scenes.py`, `track.py`): shot, black, freeze and flash detection; MediaPipe face tracks and active speaker; a face-follow reframe to any aspect with smooth, fast or locked camera modes; a stacked two-person layout.
- **B-roll** (`broll.py`): places B-roll from a folder on matching words and covers jump cuts first.
- **Colour** (`color.py`, `luts.py`): auto white balance, levels, contrast and saturation. Approximate log to Rec.709 for S-Log3, V-Log, C-Log3, Apple Log and F-Log. Official LUT input, Reinhard shot matching, and 51 looks: 39 generated LUTs with skin protection plus 12 legacy grades. Film texture (grain, halation, bloom, diffusion, aberration, weave, flicker, letterbox, dither), scopes, a looks sheet and legal-level QC.
- **Motion** (`runtime/engine.js`): 30+ easings, cubic-bezier, springs, keyframes, shake, beat pulse and face anchoring. 17 new in/out animations and 10 text effects. 6 caption presets with safe zones, a reading-speed limit and face dodge. 25 new element types (charts, map, chat, code, callouts, lyric, split screen, texture layers and 11 transition overlays).
- **Sound** (`audio_chain.py`, `beats.py`, `music_fit.py`, `tts.py`, `stems.py`): a dialogue chain, room-tone fill, 49 synthesized SFX, speech-aware ducking, music cut to length on bar lines with an end button, beats and peaks, offline voice-over and optional Demucs stems.
- **Delivery and QC** (`deliver.py`, `captions.py`, `export_edl.py`, `qc.py`): 23 platform presets with two-pass loudness, face-aware reframe and size budgets. SRT, VTT and TTML to broadcast rules, chapters, thumbnails and a post pack. EDL, FCPXML and OTIO exports, ProRes 4444 overlays, and an automated QC report. BT.709 tagging on every encode.
- **Pipeline** (`run.py`): `--genre`, `--clips`, `--timeline`, `--auto`, `--music`, `--reframe`, `--smart-cuts`, `--retakes`, `--broll`, `--platform` and `--deliver`, with QC and deliver as pipeline steps.
- **Footage clean-up** (`prep.py`, `run.py`): `--stabilize` (two-pass vidstab, `deshake` fallback), `--denoise light|strong` (`hqdn3d`) and `--deflicker`.
- **Privacy blur** (`render.py`): plan `"blurs": [{x, y, w, h, start, end, strength, pixelate, block}]` blurs or pixelates a box of the picture under the graphics (plates, bystanders, screens, PII in screen recordings).
- **Face-aimed punch-ins** (`render.py`): `speaker.zooms` centre on the face when the plan has `track` (from `track.json` via `make_plan.py`), or on a zoom's own `cx`/`cy`; `"toFace": false` keeps the frame centre.
- **Voice-over timelines** (`timeline.py`): `"voiceover": true` in a spec's `music` block transcribes it, so photo and faceless edits get caption word times without copying words by hand.
- `check_env.py` now checks every FFmpeg filter v2 uses and lists the optional add-ons with their licences.

**47 skills**

- 42 genre skills: retention-reel, clip-miner-pro, reaction-duet, micro-drama, gaming-vod, longform-retention, video-essay, vlog, tutorial-screen, product-review, faceless-explainer, news-explainer, podcast-episode, conference-talk, interview-doc, vox-pop, scene-editor, short-film-finisher, trailer-teaser, ad-ladder, ugc-ad-matrix, brand-film, testimonial-film, saas-launch-demo, wedding-highlight, wedding-india, event-recap, concert-multicam, music-video, lyric-video, memorial-tribute, recipe-video, fitness-video, fashion-lookbook, travel-cinematic, real-estate-tour, course-module, kids-content, asmr-video, regional-devotional, localise-dub, sports-highlight.
- 5 utility skills: finishing-pro, platform-pack, accessibility-pack, editor-handoff, versions-review.
- `docs/catalog.md`: the professional catalogue with Ready / Upgrade / Heavy tags checked against the code.

### Changed

- **The grade is applied to the footage, not the graphics.** Correction, shot match and look now run on the speaker source before overlays, so captions and titles keep their designed colours. Texture and the legal limiter run once, at the end. `finish.grade` still works and now accepts any of the 52 look names.
- **Loudness follows the platform.** -14 LUFS for social and YouTube, -16 for podcasts, -23 for EBU, -24 for ATSC, -27 for Netflix (approximate). A measured gain feeds a true-peak limiter, replacing the single fixed -14 LUFS pass.
- **Captions respect reading speed and safe zones.** `cpsMax` (default 20) splits fast groups, `safe` keeps captions between 10% and 85% of the height and clear of the right 12% in 9:16, and `dodgeFace` moves them off the face. QC mirrors the engine's grouping.
- **Autocut thinks like an editor.** Cut points come from the quietest gap, breaths are kept, retakes and fillers follow the genre preset, and `--max-gap` defaults to the genre's value.
- All skill manifests are now v2.0.0, and the 40 styles are documented as skins over the genre skills.

### Fixed

- FFmpeg 9 removed `-filter_complex_script`. Scripts now translate it to `-/filter_complex`, so they work on FFmpeg 7, 8 and 9.
- New PyAV builds broke faster-whisper's audio decode. Audio is now decoded through FFmpeg.
- Caption words merged into one another while `activeScale` was enlarging the active word.
- `theme.json` and `theme.css` are now read as UTF-8, which fixes crashes on Windows code pages.
- `lut3d` paths on Windows now escape the drive colon (`C\:/...`). An unescaped path failed.
- Number tokens that Whisper split (`$10` `,000.`) are re-joined at transcription and in subtitles.
- The legal-level judgement now follows EBU R103, using the percentage of out-of-range pixels instead of a single stray pixel.
- A fully opaque overlay frame (a full-screen `titlecard`) no longer turns the rest of the render black: overlay frames are always stored as RGBA.
- `run.py --timeline` skips autocut (the spec sets every in/out), `autocut.py --keep-all` keeps a timeline's cutlist, and `editor.py review` sees the timeline's joins.
- `qc.py` works on audio-only files; `--platform podcast` is accepted as an alias of `podcast-mp3`.
- Also fixed: the genre's max-gap is respected (`run.py --max-gap` now defaults to the preset), `--model` is forwarded to the timeline, cutaways show in contact sheets, and QC skips plan geometry on reframed deliveries. An explicit `deliver.py --words` now overrides the plan words (for SDH captions).

### Decisions

- **Kokoro instead of Piper** as the recommended voice-over. Piper's maintained engine is GPL-3.0, so it is only called as a separate program when the user installs it. Kokoro is Apache-2.0.
- **LUTs are generated, not committed.** `luts.py` writes the 44 `.cube` files (39 looks and 5 log transforms) deterministically. They are git-ignored, and any missing LUT is generated on first use.
- **`cpsMax` defaults to 20** characters per second for creator captions, matching the adult broadcast subtitle limit (17 for kids).
- Non-commercial models (ProPainter, XTTS-v2, F5-TTS, MusicGen) are listed for personal use only. They are never bundled or downloaded by the pack.

## v1.0.0

- First release: 40 style skills on one engine (`video-studio-core`). Transcription with faster-whisper, pause, filler and retake cuts, person matte for text behind the speaker, HTML motion-graphics overlays, 13 grade options (including `none`), 9 generated SFX, ducked music and -14 LUFS loudness.
