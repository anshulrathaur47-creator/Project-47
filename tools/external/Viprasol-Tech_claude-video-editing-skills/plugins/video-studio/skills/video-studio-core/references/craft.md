# Craft: the editor's brain

How a veteran picture editor thinks, written as rules Claude can apply to a Video Studio edit.
Numbers marked *(convention)* are working practice, not measured law: tune them to the footage.
Sources: Murch (*In the Blink of an Eye*), Cutting et al. ASL studies, Cinemetrics, Frame.io / Art of the Cut
interviews (Hamilton, Welfling), the MrBeast production memo (**leaked, unofficial**), platform spec pages.
Machine-readable presets for 37 genres live in `scripts/genres.json` (`python scripts/editor.py genres`).

## 0. The one rule

Every cut, overlay and second must earn its place. "If something can be removed, it should be" (Hamilton).
When in doubt, ask: does this make the viewer *feel* more, *understand* more, or *want the next second* more?
If none of the three, cut it.

## 1. Murch's Rule of Six (how to choose between two cuts)

| criterion | weight | what it means in our pipeline | proxy we compute |
| --- | --- | --- | --- |
| emotion | 51% | is this the true moment? does it serve the feeling? | thought completed, emphasis word, laughter, a held beat after the line |
| story | 23% | does the cut advance the story / argument? | outgoing sentence complete, incoming starts a new thought |
| rhythm | 10% | is it at the right moment rhythmically? | segment length vs genre ASL, or distance to a beat |
| eye-trace | 7% | is the viewer's eye where the new shot needs it? | primary face position continuity (track.json) |
| 2D plane | 5% | screen direction / 180-degree line | not measurable from transcript: neutral |
| 3D space | 4% | spatial continuity of the action | not measurable: neutral |

Rules:
- Emotion is worth more than the other five combined. When criteria conflict, give up from the bottom of the list.
- **Never** fix a continuity error (2D/3D) at the cost of emotion or story.
- `editor.cut_score()` scores every autocut join 0-100 with these weights (see `cuts.md`). Below **45**: the cut
  probably lands mid-thought. Move it to the end of the thought, or hide it (B-roll, punch-in, L-cut).
- The weights are Murch's own "somewhat arbitrary" percentages. Use them to keep priorities straight, not as physics.

### Where exactly to cut
- **Cut when the thought completes**, not when the sound stops. Murch: the blink marks the end of a thought;
  the cut usually lands 1-2 frames *before* a blink. In talking heads: cut after the final word's decay,
  before the breath for the next idea.
- Audio edits go in **energy valleys** (the quiet between syllables / words). `autocut.py --smart-cuts` picks the
  quietest 10 ms inside each pause and never cuts inside a word.
- Keep **0.10-0.15 s before a word** (`--breath`). Less sounds clipped; it removes the intake that tells the ear a new
  phrase is coming. Keep **0.05-0.08 s after** (`--pad`) for the word's decay.
- Smallest join fade 10-12 ms (no click). Use 20-40 ms crossfades (`--xfade-ms 30`) for documentary / interview where
  the room tone differs between takes.
- Don't over-tighten. Removing every pause makes a speaker sound breathless and robotic. For emotional or narrative
  material, keep pauses over the genre `max_gap` and keep the breath before an emotional line.

## 2. Cut types: when and why

| cut | what | use it for | avoid when |
| --- | --- | --- | --- |
| straight cut | picture + sound change together | default everywhere | a dialogue scene of only straight cuts ("Dragnet" tennis rhythm) |
| jump cut | same framing, time skips | reels, vlogs, YouTube talking heads (energy, removes waffle) | documentary, corporate, testimonial, wedding: cover it |
| punch-in (axial) | same shot, scale >= 1.2x | hides a jump cut, adds emphasis on a key word | more than every 2nd cut (it becomes a tic) |
| J-cut | next shot's **audio** starts before its picture | pulls the viewer into the next scene, smooth sentence joins | comedy timing (kills the surprise) |
| L-cut | picture changes, previous **audio** continues | show the listener's reaction, B-roll over a statement | when the words need the face for credibility |
| cutaway / B-roll | insert over continuing audio | hide interview edits, illustrate the words | B-roll that contradicts or decorates without meaning |
| match cut | shape / action / sound matches across the cut | travel, fashion, trailers, transitions between ideas | forcing it: a weak match reads as a gimmick |
| smash cut | abrupt cut with a big contrast (loud to quiet) | comedy, shock, trailer button | more than once or twice per piece |
| cross-cut | alternate between parallel actions | tension, comparison, before/after | when the viewer can't tell the threads apart |
| dissolve | overlap of two shots | time passing, memorial, ceremony, dreamy montage | talking heads (looks amateur), fast pacing |
| dip to black | fade out / in | chapter ends, memorial, trailer act breaks | inside a sentence |
| whip / zoom transition | motion-blurred join | travel, vlog energy, outfit changes | serious or factual tone |

Continuity rules (for multi-camera and narrative): keep the 180-degree line; change angle >= 30 degrees or framing
>= 1.2x between shots of the same subject, otherwise it reads as an unintended jump cut; cut on action about a third
of the way into the move *(convention)*; eyeline after a look-off should match the next shot's subject position.

### J/L cuts in numbers *(convention)*
- Dialogue split edits: **4-12 frames** (0.13-0.4 s at 30 fps). `autocut.py --jcut 3` makes the next sentence's audio
  lead its picture by 3 frames at sentence joins.
- Scene transitions: bring the next scene's sound in **1-2 s** early.
- Reaction L-cuts during long answers break a static talking head; place them where the listener has a real reaction.

## 3. Pacing

Average shot length (ASL) fell from about 12 s (1930) to about 2.5 s today (Cutting). Action films sit near 2 s
(*Fury Road* 2.1 s). ASL alone misleads: check the spread too. Post-1980 films vary shot lengths in a 1/f pattern,
so **mix long holds and quick cuts**; uniform cutting feels mechanical (`editor.py review` flags low variance).

| genre | ASL target | visual change at least every | autocut max gap | captions |
| --- | --- | --- | --- | --- |
| reel / TikTok / Short talking head | 1.5-3 s | 2.5 s | 0.30 s | word-pop 1-3 words, <= 17 cps |
| UGC / ads 15-30 s | 1-2.5 s | 2 s | 0.25 s | short supers, <= 15 cps |
| 6 s bumper | 1-3 s | 1.5 s | 0.25 s | <= 3 words |
| YouTube long-form | 3-6 s | 5 s (2-5 s in minute 1) | 0.45 s | 2-line subtitle, <= 20 cps |
| tutorial / SaaS demo | 3-8 s | 4-6 s | 0.40 s | subtitles + shortcut overlays |
| video essay / doc YouTube | 4-8 s | 6 s | 0.60 s | subtitles |
| documentary interview | 5-15 s (B-roll 2-5 s) | 10 s | 0.90 s, keep-natural fillers | subtitles <= 17 cps |
| podcast full episode | 4-12 s (speaker switches) | 12 s, wide reset every 30-60 s | 0.90 s, light | optional |
| music video / fashion | 0.8-3 s on the beat | every bar or phrase | n/a | none |
| wedding highlight | 2-4 s, holds on emotion | phrase | 0.80 s (vows only) | none / vows |
| memorial / tribute | 4-7 s per photo | 7 s | n/a | names and dates only |
| ASMR | 15-60 s | rarely | none | none |

Rules:
- **Information needs time.** Give a shot more screen time when it carries more (more people, more text, a wide).
  Cutting: each extra character in frame added about 1.5 s to ASL.
- **Breathe after a big beat.** Hold 1-3 s (reaction, wide, or silence) after an emotional or plot peak before the next
  information beat *(convention)*.
- **Pattern interrupts** (zoom punch, overlay, B-roll slot, sound effect, angle change) whenever a stretch exceeds the
  genre interval. `editor.py review --fix` adds zoom punches in stretches that run long. Alternate punch sizes
  (1.12x / 1.07x) so it doesn't feel like a metronome.
- Action cut too slowly is boring; drama cut too fast loses the performance. Read the genre first.
- Captions: <= 17 characters per second for adults, <= 12-13 for kids; on-screen text holds >= 0.6 s, a full line
  >= 1.5 s; enter **0.05-0.10 s before** the spoken word.

## 4. Retention structure

### Short-form (Reels / TikTok / Shorts / UGC)
- **0-1.5 s: the hook.** Platforms measure at 3 s; land the visual or spoken hook by 1.5 s. Hook = pattern interrupt
  + value promise + open loop. Two-thirds of plays start muted (vendor study): the hook must be **on screen as text**,
  <= 7 words.
- **Never open with:** "hi guys", "hey everyone", "welcome back", "in this video", "today I'm going to", a logo
  sting, or dead air (> 0.3 s before the first word). `editor.py review` flags all of these.
- **Open a loop** in the first 25%: a number ("three mistakes"), a question, a contrast, stakes. Close it at the end.
- **Body:** one idea per beat, a visual change every 1.5-3 s, no more than **2 overlays at once**.
- **Payoff before the end,** then **CTA in the last 2 s** or a seamless loop back to the first frame. Don't add
  an outro after the payoff.
- Hook-rate benchmarks (3-s views / impressions ~20-30%, top ads 40-50%) are vendor numbers: directional only.

### YouTube long-form (MrBeast production memo: leaked, unofficial, but widely corroborated)
- **Minute 0-1** is where most viewers leave. Front-load the best material; deliver the title/thumbnail promise.
  Pre-plan the opening lines.
- **Minutes 1-3:** stop telling, start showing (hype to action). Compress story time. A re-engagement spectacle
  near **3:00**.
- **Minutes 3-6:** quick scene changes, attachment to people; second re-engagement near **6:00**, then every ~3 min.
- **Back half:** energy can dip but stays good. Stair-step the stakes. **Never signal the end** ("in conclusion",
  "to wrap up") before the payoff. End within 1-2 s of the payoff (end screen 5-20 s).
- Judge by first-day AVD/AVP, CTR, and the second-by-second retention graph. The fast style can hurt educational
  content: match intensity to genre.

## 5. Interview and documentary editing

Workflow: transcribe, **paper edit** (`story.py outline`), **radio edit** (audio story first, no pictures), then cover.
1. Build the story from soundbites. Read the paper edit; pick the arc (question, development, answer).
2. Cut audio first, in valleys. Fill every gap with **room tone**, never digital silence (record 20+ s on set, again
   after the interview because the room drifts).
3. Every remaining interview jump cut gets covered: **B-roll overlapping >= 0.5-1 s each side**, a second angle, or a
   >= 1.2x punch-in. Otherwise flag it (`editor.py review` does, for genres that don't allow jump cuts).
4. Keep the best **performance**, not the cleanest take. Hamilton builds line strings so every reading can be compared.
5. Remove fillers lightly (`--filler-policy keep-natural` keeps "you know", "I mean" and only drops um/uh).
   Keep breaths before emotional lines. Cap pause removal so the person still sounds like themselves.
6. Use listener reactions (L-cuts) to break long answers; a reaction changes the meaning of what came before it
   (Kuleshov), so choose reactions as story decisions and never fake one in factual content.

## 6. Multi-take selection (retakes)

- The **last complete take** is usually the keeper (the speaker restarted because the earlier one was wrong).
  `autocut.py --retakes` drops: a sentence followed by a cue ("let me start again", "scratch that", "one more time",
  "from the top"), and an opening phrase repeated within 8 s (a restart). It logs every drop in `cuts.md`.
- Override when an earlier take has better energy: use `--cut` ranges and keep it. Performance beats polish.
- String-outs for many takes: lay all takes of a line back to back, watch them in a row, mark the best reading.

## 7. Music editing

- Cut music **on downbeats and phrase changes** (every 4 or 8 bars), not mid-phrase. Edits hide best right before
  a strong beat or under a hit / whoosh.
- Pictures cut on beats (`beats.json` + `auto.keywords.snap: "beats"` snaps zooms, flashes and key words to the
  nearest beat within 0.12 s). Don't cut on every beat: vary between every beat, every 2nd, every bar.
- End on a resolved bar; never fade out mid-phrase unless the genre is ambient.
- Music under dialogue: bed **-22 to -28 dB** below dialogue, duck 8-12 dB under speech; lift it in gaps.
  Music-led genres (music video, travel, wedding highlight) let music lead and dip it under vows / soundbites.
- Silence before the drop is the strongest trailer tool: 0.5-1 s of near silence before the hit.
- Only licensed music. Shorts with Content ID matches may be blocked.

## 8. Sound-led editing

- **Sound is half the picture.** Amateur edits fail on audio more than on cuts.
- Dialogue first: consistent level, de-noised gently (heavy noise reduction ruins ASMR and sounds underwater).
- Room tone under every gap. Ambience layered under montage makes places feel real.
- SFX density by genre: none (documentary, ASMR, e-learning), low (long-form 3-6 / min), medium (reels 10-15 / min),
  high (gaming, kids, trailers 20+ / min). Every whoosh should be motivated by motion on screen.
- Loudness targets: YouTube / social **-14 LUFS, -1 dBTP**; podcast feeds **-16 LUFS**; US broadcast **-24 LKFS,
  -2 dBTP** (ATSC A/85); EU broadcast -23 LUFS (EBU R128). `finish.py` normalises to -14 by default.

## 9. Colour and sound handoff (picture lock)

- **Picture lock** = clip timing will not change again. Only then: colour, final mix, captions, VFX, graphics.
  Changing timing after lock means re-doing every downstream department.
- Before handoff: balance cameras (same white balance / exposure), remove filters, export a reference.
- Grade intent per genre (see `genres.json` `grade`): punchy for short-form, warm for weddings / food, film for
  essays and docs, none (accurate) for real estate, SaaS and fashion e-commerce (garment colour drives returns).
- Skin tones first, then the look. Never grade a vertical cut and the 16:9 master differently.

## 10. Workflow stages and checklists

1. **Ingest.** Copy, verify, organise by day / event / camera. Make proxies for heavy codecs. `prep.py` normalises to
   30 fps, upright, <= 1920.
2. **Log.** Transcript (`transcribe.py`), faces (track.json), peaks, beats. Name things.
3. **Selects.** Best takes and moments (`clip_candidates.py` for long recordings, `story.py outline` for hooks).
4. **Assembly.** Everything usable, in order. Expect 1.5-3x target length.
5. **Rough cut.** Structure from the genre template (`story.py outline` maps sentences onto beats). Cold open on the
   best hook (`story.py reorder`).
6. **Fine cut.** Cut points, J/L cuts, breaths, retakes, pacing interrupts (`autocut.py --genre`, `editor.py review --fix`).
   Top-and-tail every scene: once joined, the starts and ends you don't need become obvious (Welfling).
7. **Picture lock.** Then graphics (`make_plan.py`, refine `plan.json`), colour and sound (`finish.py`).
8. **QC.** Contact sheet (`render.py --frames`), review (`editor.py review`), ffprobe duration / audio, loudness,
   safe zones, spelling of every name, captions vs audio.
9. **Delivery.** Every version the genre needs (`genres.json` `deliverables`), named clearly:
   `client_project_v003_9x16_captions.mp4`.

QC checklist (all genres): no black frames or flashes unintended; no clipped audio; first word <= 0.3 s (short-form);
text inside safe zones (9:16: 10%-85% of height, clear of the right 12%); nothing covers the face unless intended;
captions match the words; names, numbers and dates triple-checked; correct loudness; correct duration
(ads frame-accurate: 6.0 / 15.0 / 30.0 s).

## 11. Notes rounds

- Version every round (v001, v002...) and keep each one. Never overwrite the version the client approved.
- Read all notes before touching anything; group by type (story, timing, graphics, sound, colour, spelling).
- Fix the **note behind the note**: "it feels slow at 0:40" often means the hook promise was unclear at 0:05.
- Try the client's suggestion as asked and, if you disagree, also show your alternative. Not precious (Hamilton).
- Agree the number of rounds up front (2 rounds is common for weddings and social); list changes in a short diff.
- After each round, re-run QC: notes fixes introduce new problems (orphaned captions, broken safe zones).

## 12. Ethics

- **Frankenbites** (splicing words from different sentences into a new statement) are common in reality TV and
  forbidden in documentary, news, testimonials and anything presented as someone's real words, unless the speaker
  approves and the meaning matches the source. `story.py reorder` flags every partial-sentence splice as HIGH and every
  out-of-order sentence that starts with a back-reference ("it", "this", "so") as MED.
- Reordering whole sentences for a cold open is normal in entertainment; log it. In factual genres get approval.
- **Testimonials and reviews must be real**: real customers, their real words, in their real order. No fake ratings,
  no actors presented as customers, sponsorship disclosed (FTC / ASCI).
- Don't change meaning with a reaction shot (Kuleshov) in factual content.
- Respect culture and grief: rituals (pheras, nikah, aarti), funerals and memorials get respectful framing, correct
  names and family-approved order.

## 13. Mistakes veterans see most

1. Slow openings: logo, greeting, "in this video". The first frame should already be the story.
2. Cutting for continuity over emotion; keeping the clean take instead of the true one.
3. Dragnet dialogue: every line its own straight cut. Use L-cuts and reactions.
4. Keeping material that doesn't earn its place; scenes that enter early and leave late.
5. Breathless over-cutting: every pause gone, breaths clipped, words chopped mid-decay.
6. Uncovered jump cuts in docs / corporate; unmotivated axis flips in multi-cam.
7. Uniform rhythm (all shots the same length); action cut too slowly.
8. Too many overlays at once; text under the platform buttons; text over the face.
9. Captions out of sync or too fast (> 17 cps); burned-in captions with spelling mistakes in names.
10. Music too loud under speech; no room tone (digital silence holes); clipping; wrong loudness for the platform.
11. Signalling the end early; an outro after the payoff.
12. Missing deliverables: no vertical, no textless, no unbranded MLS version, no clean audio stems.
13. Promising in the title / thumbnail what the first minute doesn't deliver.
14. Constructed quotes in factual content.

## 14. Using the tools as an editor

```bash
python scripts/editor.py genres                                  # pick the genre first
python scripts/story.py outline --work W --genre reel-talking-head   # read outline.md: hooks, structure, order
python scripts/story.py reorder --work W --order "s5,s1-s4,s6"   # cold open -> spec for timeline.py
python scripts/autocut.py --work W --genre reel-talking-head     # breath, quiet joins, fillers, retakes; read cuts.md
python scripts/make_plan.py --work W --style STYLE --genre reel-talking-head
python scripts/editor.py review W/plan.json --fix                # scores + review.md; --fix keeps plan.json.bak
python scripts/render.py W/plan.json --frames 1,4,8,12           # look at the contact sheet before the full render
```

Read `review.md` like a note from a senior editor: fix the high-severity items by hand (hook, greeting, dead air),
let `--fix` handle the mechanical ones (timings, overlap, interrupts), then look at the frames again.
