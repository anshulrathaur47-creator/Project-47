# "उसको फुर्सत नहीं मिलती कि पलट कर देखे"

**Input:** `assets/music/ReelAudio-62874.mp3` (13.1 s, a sher recited at a mushaira, with the audience's "वाह").
The transcript is in `references/ReelAudio-62874_hin.txt`. Word timings come from Whisper with the transcript as a hint.

**New character:** a young man in a white kurta, charcoal Nehru jacket and white pyjama, with jet-black hair.
He is drawn on the `make_khas.py` rig with the male style and a new `SLEEVE` colour. She is a long-haired silhouette.

| Time | Words | Scene |
|---|---|---|
| 0 to 2.7 | उसको फ़ुर्सत नहीं मिलती | Over his shoulder: she walks away down the sunset street on her phone; he holds a rose |
| 2.7 to 4.0 | कि पलट कर देखे | Front: a hopeful smile, the rose held up; an eye sign waits, then closes; his smile fades |
| 4.0 to 5.4 | (वाह, क्या बात है) | Wide from behind him: she turns the corner into the sun and is gone; the rose drops |
| 5.4 to 6.9 | उसको फ़ुर्सत नहीं मिलती | Another day, morning: he waits at the lamp post with a gift box; she passes laughing with friends |
| 6.9 to 8.0 | कि पलट… | Dusk: with a card; she passes on her phone |
| 8.0 to 9.0 | …कर देखे | Night: with a rose; she almost turns, then hurries on |
| 9.0 to 11.4 | हम ही दीवाने हैं, दीवाने बने रहते हैं | Under the lamp on a low wall, beside a pile of dried roses: he smiles at his rose with wet eyes; a heart beats on each "दीवाने" |
| 11.4 to end | (वाह वाह) | Pull back: alone under the lamp, eyes closing; fade |

**Lyrics:** static lines for the sher only, not for the audience's "वाह".

**Render:** `python3 make_fursat.py --workers 4`.
