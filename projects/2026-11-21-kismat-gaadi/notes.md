# "किस्मत की गाड़ी" reel

**Input:** `assets/music/ReelAudio-31260.mp3` (18.6 s song, ~103 bpm) and the lyrics in
`references/ReelAudio-31260_hin.txt`. No brief, so this follows the user's recent asks:
- a new character
- a sad story
- static lyrics with no animation, like the janaza reel

**Timing:** Whisper with the lyrics as a hint. 0 to 9.3 s and 12.8 s onward were aligned on their own,
because the full pass lost them under the music.

**Character (new):** a teenage chai boy: darker skin, messy brown hair, mustard shirt with a patch,
red-checked gamchha round his neck, dust on his cheeks.

| Time | Line | Scene |
|---|---|---|
| 0 to 2.7 | जिस उम्र में शोभा देते | Park at sunset: kids play cricket and fly kites; he stands with his tea kettle and crate, watching |
| 2.7 to 3.4 | मस्ती, | Close-up: a dream bubble of him batting, then it pops |
| 3.4 to 5.1 | सैर सपाटा | Kids ride past on bicycles with balloons; he looks down at his kettle |
| 5.1 to 7.5 | उस उम्र को ना बुरा है | Night at the dhaba: he scrubs a tub of dishes, sweating |
| 7.5 to 8.4 | यूं घड़ी का कांटा | The wall clock races through hours |
| 8.4 to 9.1 | | He nods off |
| 9.1 to 11.8 | अपनी किस्मत की गाड़ी की | Sunset street: he hauls an old handcart of sacks; feet shot with the wheel wobbling |
| 11.8 to 13.9 | खस्ता हालत है | The wheel rolls off, the cart tips, the sacks spill; hands to his head |
| 13.9 to 16.4 | अपनी किस्मत की गाड़ी की | Night rain: he sits on the road by the broken cart |
| 16.4 to 18.1 | खस्ता हालत है | Close-up: he wipes tears and rain with his gamchha, then looks up |
| 18.1 to end | ओ रे | Pull back, fade |

**Lyrics:** plain static lines that cut on and off, white with a soft shadow; किस्मत, घड़ी and मस्ती are in
soft gold. A line that spans a cut picks a new place in the next shot so it never sits on his face.

**Render:** `python3 make_kismat.py --workers 4`.
