---
name: style-ui-explainer
description: Use when making a faceless tech or AI explainer reel in the "ui-explainer" style. The look is a voice-over over animated UI cards (app windows, terminals, comment boxes, checklists, price cards), Hinglish word-by-word captions above and below the card with key words in boxed italic serif, dashed-arrow camera moves instead of cuts, a cream or a black-and-green theme, and a "Comment WORD" CTA. Use it when the user says "is type ki reel", "ui explainer", "tech reel like circuitly", or sends a VO for a tool, offer or how-to reel.
---

# Style: ui-explainer

Learned from two reels the user sent (2026-11-28), saved in `inspirations/`:
- `VID_20261128_093951_416.mp4`: cream theme, 35.2 s, "Claude se Reels banana seekh lo".
- `VID_20261128_093959_892.mp4`: dark theme, 61.6 s, a "$200 plan free" offer.

Studied range: both reels in full (a contact sheet every 1.3 s and 2.2 s, plus full-resolution frames). Format: vertical 9:16, 30 fps (the sources are 720x1280; we render 1080x1920).

Copy the style only. Never reuse the creator's handle, voice, music, the orange asterisk motif, or the exact cards. Keep third-party logos out (draw generic icons). Use the user's own handle or brand.

## 1. Quick recap
- **Pacing:** one continuous "shot" with no hard cuts. A new card about every 4–6 s (8 scenes in 35 s; 12 in 62 s). Each scene change is a 0.5–0.7 s camera move along a dashed arrow, with the outgoing card blurring and sliding away.
- **Captions:** Hinglish, word by word, on the spoken word, in two text zones (above and below the card).
  - Normal words: clean geometric sans, medium weight, letter-spaced.
  - Key words: about 2x bigger bold italic serif in the accent colour, inside a Figma-like selection box (thin outline with small square handles at the corners).
- **Motion:** slow push-in on each card (about 1.04x over the scene), elements building in one by one, a cursor that moves and clicks, typing in inputs and terminals, lines that draw, ticks that pop, prices struck through.
- **SFX:** soft clicks on cursor clicks, light whooshes on scene moves, a pop or tick on list items, keyboard typing under typed text. Sparse, about one hit every 2–4 s.
- **Music:** a light, low beat bed (about 112–118 bpm, no silences anywhere), well under the voice. Final loudness about -14 LUFS.

## 2. Pacing and cuts
- Average scene length: 4.4 s (A), 5.1 s (B). Hard cuts per minute: 0. Every change is a camera move.
- The voice runs continuously at 2.7–2.8 words/s, with no pauses longer than about 0.3 s.
- Hook speed: the first visual change happens by 0.5–1.2 s (the empty card fills in, or the price changes).

## 3. Framing and movement
- One central card, 82–88% of the frame width, centred around y 30–65% of the height.
- Cards:
  - cream theme: white rounded rectangles (radius about 3% of width) with soft long shadows and a slight 3D tilt in transitions
  - dark theme: dark glass (#1d1f22 at about 85%, a 1 px light border, soft blur)
  - macOS window chrome (three dots, a title pill) on app cards
- Push-in about 1.03–1.05x per scene. The outgoing card slides off diagonally (to the left/up or right/down) with motion blur and depth blur.

## 4. Transitions
- Main transition (100% of scene changes), about 0.6 s:
  - a dashed curved arrow (rounded dashes, accent colour, about 4 px at 1080) draws across empty space
  - the camera pans along it to the next card
  - captions drift and blur out
- Within a scene, items build in with a fade plus an 8–12 px rise, and stamps land with an overshoot.

## 5. Captions (word by word)
- **Words at a time:** a phrase of 3–6 words builds word by word; at most two lines per zone. The top zone sits above the card (y 17–24%) and the bottom zone below it (y 66–78%), alternating per phrase.
- **Timing:** each word appears on its spoken start (±0.05 s). A phrase clears when the next phrase starts in the same zone, or at the scene move.
- **Emphasis:** 1–2 key words per phrase: the nouns and numbers that carry the claim (tool names, prices, STEP numbers, FREE, the CTA keyword).
  - Key words are set in a bold italic serif (Playfair Display Black Italic look), about 2.0–2.3x the normal size.
  - Cream theme: orange-red #e05a28 to #c43a1a gradient. Dark theme: gold #f0b820 or red #e0303a gradient.
  - The selection box is a 2 px accent outline with 7 px square handles at the corners; neighbouring key words get one box each.
- **Normal words:** geometric sans (Poppins/Inter look), weight 500–600, letter-spacing about 0.06em, about 4.4% of width. Colour #3a3f4a on cream, #f2f2f2 on dark.
- **Casing:** as spoken, in Hinglish (Roman script). Key words are sometimes in CAPS (AALSI, FREE, STEP). No punctuation except "?" and ":".
- **Entry animation:**
  - Normal words: blur 8→0 px with opacity 0→1 over 0.18 s, and a small rise.
  - Key words: the same blur-in on a pale rounded backing card, then the selection outline draws in over 0.15 s.
- **Exit:** a blur and drift as the camera moves.

## 6. Overlays and graphics
- **Card types seen:**
  - app window with stat tiles
  - before/after comparison (red ✕ rows struck through, then a green "ready" row and a tilted stamp)
  - Instagram-style comment box typing the keyword, with a reply card holding a zip or PDF file
  - progress bar and download
  - dark terminal typing a prompt with ✓ log lines
  - PDF checklist
  - price card ($ struck, then FREE)
  - steps list with a timer ring
  - phone mock
  - console forms
  - a key icon with connector lines
- Small step tags above cards: a dark pill reading "STEP 01 · …".
- **Palettes:**
  - cream: bg #f0ede7, ink #192232, muted #ccc1bd, accent #e05a28, green #2fb456, red #e04848
  - dark: bg #000, card #1d1f22, glow #19e619 at the bottom, accents gold #f0b820 and red #e0303a
- **Background decoration:**
  - cream: big soft blurred accent shapes cut off at 2–3 corners
  - dark: one big green radial glow from the bottom
- **Handle watermark:** bottom centre at y about 93%, small, 50% grey.

## 7. Color and look
- Cream: bright (0.73), low saturation (0.20), neutral. Dark: brightness 0.21, saturation 0.52 from the green glow.
- No grain, no vignette, crisp UI. Depth of field only on moving elements.

## 8. Audio
- **Voice:** close, compressed, Hinglish, 2.7–2.8 words/s, normalised (-14 LUFS overall).
- **Music:** a light beat bed, constant, about -20 dB under the voice, ending with the voice.
- **SFX map:**
  - whoosh on each scene move, about 20–25% volume
  - click on cursor clicks
  - typing under typed text
  - pop or tick on list items and stamps
  - ding on the final CTA
- **Search keywords:** "soft whoosh transition", "ui click", "keyboard typing", "pop", "success ding". The local library is in `assets/sfx/`.

## 9. Hook (first 3 seconds)
- **Sees:** the main card already on screen, empty or showing a big claim ($200, 1.4M views). The first key word in its selection box lands by about 0.6 s.
- **Hears:** a direct-address question or command ("…seekh lo", "…nahi liya?") with no intro.
- **Pattern interrupt:** the card content changes (fills, or the price is struck through to FREE) by 1–2 s.

## 10. Ending
- The last 4–5 s are the CTA:
  - a big keyword button, or a comment box that types the keyword
  - an auto-reply card (zip, PDF or guide)
  - the line "Abhi comment mein **WORD** likho!" / "guide chahiye toh **COMMENT** **WORD**"
- The reel ends on the CTA card with no outro.

## 11. Step by step recipe for a new video
1. Get the VO (the user's recording or ElevenLabs file, or Kokoro TTS `hm_omega` for drafts) and its script. Save them in `projects/<date>-<name>/`.
2. Run `python3 tools/transcribe.py vo.mp3 --lang hi --no-vad` for word timings, and fix the words against the script.
3. Write `spec.json` for the engine in `tools/ui-explainer-reel/`:
   - theme
   - handle
   - key words (`*word*` in the caption lines)
   - one scene per idea, starting on the first word of that idea, with its card type and contents
4. Render with the engine: Remotion composition `UIExplainer`. See `tools/ui-explainer-reel/README.md`.
5. Check frames at each scene start and at the CTA. Mix the VO, music bed and SFX to -14 LUFS, and export to `exports/`.

## 12. Do not
- No hard cuts, flashes, glitches, emojis, grain or face cam.
- No long sentences on screen: never more than 6 words per line or 2 lines per zone.
- No third-party logos or the source creator's handle or motif.
- Don't overstate offers. Fact-check claims (prices, "free") and add a small terms note when needed.

## References in this skill
- `references/timeline_a.md`, `references/timeline_b.md`: scene-by-scene notes.
- `references/words_a.json`, `references/words_b.json`: word timings of the source VOs.
- `references/audio_profile_a.json`, `references/audio_profile_b.json`: loudness and SFX hits.
- `references/cuts_a.json`, `references/cuts_b.json`: cut times (none).
- `references/frames/`: hook, caption look, comparison stamp, transition, CTA and dark-theme frames.
