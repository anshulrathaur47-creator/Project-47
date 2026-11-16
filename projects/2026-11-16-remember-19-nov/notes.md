# Remember 19 November 2023: emotional meme reel

**Idea:** the 2023 World Cup final (India vs Australia, Ahmedabad, 19 Nov 2023). India were
unbeaten all tournament and lost the final. A fan's journey: josh, then hope, tension and
silence, then today: seeing "19 NOV" on the calendar and covering his ears ("nahi bhai, mat yaad dilao").

**Audio:** `assets/music/ReelAudio-43255.mp3` (user's track), 27.27 s, instrumental
(Whisper found no lyrics), ~143.5 bpm. Beat grid in `references/ReelAudio-43255.beats.json`.
Sections: build 0 to 13 s, peak 13 to 14.9 s, lift-off 15.3 s, new phrases at 20.2 s and 25.1 s.

**Text:** the track has no lyrics, so short Hinglish story lines run in the lower third, word by word.

| Time | Scene | Text | Signs |
|---|---|---|---|
| 0 to 5.4 | Walks to the final: blue jersey, tricolour face paint, flag up, swagger | 19 November 2023, Final ka din | glowing cup |
| 5.4 to 10.3 | Stadium: 1 lakh fans, phone torches, confetti, he hops and pumps fists on the beat | 1 lakh log, ek hi sapna | stars rising |
| 10.3 to 15.3 | Tension: hands together, nail-biting, push-in to the eyes, floodlights flicker at the peak | Bas ek jeet aur... | heartbeat line |
| 15.3 to 20.2 | Loss: dip to black, colour drains, flag falls, fans' heads in hands, tear | ...aur poora stadium chup | muted speaker, breaking heart |
| 20.2 to 25.1 | Present day, his room: the calendar flips 18 to 19 and is circled red; shock, then he covers his ears, shakes his head | Aaj bhi koi bole: Remember 19 Nov? | shock marks, gloom lines, sweat drop |
| 25.1 to 27.3 | Ending: a tear, a small sad smile | Dil: abhi bhi dukhta hai | small broken heart |

**Rules kept:** no real players, team logos, ICC branding or real scoreboard; only our
character, generic cricket items and the national flag carried by a fan.

**Render:** `python3 make_19nov.py` (built on `reel/make_story_reel.py`).
