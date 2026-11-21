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

## v2: an adult's story (user: "Aree ek adult ke upar banao")

`python3 make_kismat_v2.py --workers 4`. It reuses the lyrics and clock from `make_kismat.py`.

**New character:** a man in his mid-twenties: stubble, tired eyes, light-blue shirt, loose navy tie, an ID card
on a red lanyard, backpack straps and a wristwatch.

| Time | Line | Scene |
|---|---|---|
| 0 to 2.7 | जिस उम्र में शोभा देते | Sunset street: his friends pass in an open jeep, music notes rising, waving him along; he shakes his head |
| 2.7 to 3.4 | मस्ती, | Phone glow on his face, a dream bubble of the beach trip |
| 3.4 to 5.1 | सैर सपाटा | The phone rings (the boss); he answers and his shoulders drop |
| 5.1 to 7.5 | उस उम्र को ना बुरा है | An empty office at night: he types between piles of files, sweating |
| 7.5 to 9.1 | यूं घड़ी का कांटा | The wall clock races; he nods off at the desk |
| 9.1 to 11.8 | अपनी किस्मत की गाड़ी की | He rides home on his old rusty teal scooter, which sputters smoke; low shot of the wheel |
| 11.8 to 13.9 | खस्ता हालत है | It dies in a burst of smoke, the headlight flickers out, hands to his head |
| 13.9 to 16.4 | अपनी किस्मत की गाड़ी की | Rain: he pushes the dead scooter down the empty road |
| 16.4 to end | खस्ता हालत है… ओ रे | Close-up in the rain, he looks up; pull back, fade |
