# Remember 19 November 2023: emotional meme reel

**Idea (user's story):** an ordinary morning. He wakes up, checks his phone and gets a
"3 years ago today" memory. He stares into the mirror, the glass ripples, and he falls into
a flashback of 19 Nov 2023, the World Cup final in Ahmedabad where Australia beat India.
The joy turns to silence; back in the present, his reflection is sad.

**Audio:** `assets/music/ReelAudio-43255.mp3` (user's track), 27.27 s, instrumental
(Whisper found no lyrics), ~143.5 bpm. Beat grid in `references/ReelAudio-43255.beats.json`.
Phrases every ~1.67 s; build to a peak at 13 to 14.9 s, lift-off at 15.3 s, new phrases at 20.2 s and 25.1 s.

**Text:** the track has no lyrics, so short Hinglish story lines run in the lower third, word by word.

| Time | Scene | Text | Extras |
|---|---|---|---|
| 0 to 3.4 | Bedroom, sunrise. Asleep (zzz), the alarm rings, he sits up, stretches and yawns | Ek normal si subah... | ringing clock, sun rays |
| 3.4 to 5.8 | Picks up his phone: a "Memories, 3 saal pehle" card with a stadium photo, he is shocked | Phone: 'Aaj ke din, 3 saal pehle' | phone insert, shock marks |
| 5.8 to 8.5 | Bathroom mirror: wide shot, then a slow push into his eyes; the mirror ripples | Aaine mein dekha... aur | ripple + white bloom |
| 8.5 to 12.4 | FLASHBACK 2023: stadium, flag, face paint, headphones, hops and fist pumps on the beat, confetti | 19 Nov 2023, Ahmedabad. 1 lakh log, ek sapna | warm memory tint, stars |
| 12.4 to 15.3 | Tension: hands together, nail-biting, push-in, floodlights flicker at the peak | Bas ek jeet aur... | heartbeat line |
| 15.3 to 20.2 | Australia win: dip to black, colour drains, flag falls, fans' heads in hands, tear | Australia ne final jeet liya. Stadium chup | muted speaker, breaking heart |
| 20.2 to 25.1 | Ripple back to the mirror: sad reflection, tear, his hand on the glass, a crack spreads | 3 saal baad bhi, aaina wahi yaad dikhata hai | glass crack |
| 25.1 to 27.3 | Ending: wipes a tear, small sad smile | Remember 19 November? | small broken heart |

**Rules kept:** no real players, team logos, ICC branding or real scores; only our character,
generic cricket items and the national flag carried by a fan.

**Render:** `python3 make_19nov.py` (built on `reel/make_story_reel.py`).
