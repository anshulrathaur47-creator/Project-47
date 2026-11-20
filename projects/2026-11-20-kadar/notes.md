# "किसी के ना होने का एहसास सबको है, मगर मौजूदगी की कदर किसी को नहीं"

**Input:** the 12.4 s spoken line over music in `assets/music/ReelAudio-38965.mp3` (~136 bpm). The
transcript is in `references/ReelAudio-38965_hin.txt`. The user sent the files without a brief, so the
reel uses the same emotional story style as the last one.

**Timing (Whisper with the transcript as a hint, checked against the transcript's segment times):**
- वो 0.40, कहते 0.60, हैं 0.86, ना 0.98, कि 1.18
- किसी 3.12, के 3.32, ना 3.42, होने 3.66, का 4.08, एहसास 4.28, सबको 4.80, है 5.24
- मगर 6.60, मौजूदगी 6.88, की 7.56, कदर 7.68, किसी 8.08, को 8.42, नहीं 8.58

**Story:** v2 has a new character (the user wants a new one every reel): a girl with long hair, maroon kurti, bindi and jhumkas. Her shawl hangs on the chair and her bangles lie on the table. Everything happens at one
dining table at night.

| Time | Words | Shot | What happens |
|---|---|---|---|
| 0 to 1.9 | वो कहते हैं ना कि | detail | His glasses and a cold cup of tea on the table; his hoodie on the empty chair |
| 1.9 to 3.1 | | wide | The table: four faceless people, heads down, his chair empty |
| 3.1 to 4.3 | किसी के ना होने का | medium on the left | One of them reaches for his chair |
| 4.3 to 5.5 | एहसास सबको है | close on the chair | A heart beats twice and cracks |
| 5.5 to 6.6 | | push-in | Into his photo on the wall; flash and ripple into the past |
| 6.6 to 7.7 | मगर मौजूदगी की | flashback, warm and sepia | He sits there laughing, waving, talking; a warm glow around him; everyone is on their phone |
| 7.7 to 9.1 | कदर किसी को नहीं | close-up | Nobody looks; his smile drops, his eyes fill, and he turns see-through |
| 9.1 to 10.5 | | wide, cold | Now: his ghost stands behind his own chair, watching them |
| 10.5 to end | | pull back | He dissolves into specks of light; the empty chair; fade out |

**Text:** none. The user asked for "No lyrics", so nothing is drawn. The word timings are still in CHUNKS in case text is wanted later.

**Render:** `python3 make_kadar.py --workers 4` (`--frames 30,150` for previews). It imports
`../2026-11-20-shakal-sad/make_shakal.py` for the character, the word animation and the rig.
