# Ghalib / Parveen Shakir "जनाजा" reel

**Input:** `assets/music/ReelAudio-35687.mp3` (22.4 s, the shayari recited over music) and the transcript
`references/ReelAudio-35687_hin.txt`. The user said "No animation in lyrics", read as: show the lyrics,
but as plain static lines with no glow or motion.

**Timing:** Whisper with the transcript as a hint. The second half (from 7.8 s) was aligned on its own;
the full pass lost it under the music.

**Character (new, per the "new character every reel" rule):** a young woman in a pale suit with a white
dupatta over her head (gold border), kajal and a nose pin.

| Time | Lines | Scene |
|---|---|---|
| 0 to 2.1 | मिर्ज़ा ग़ालिब कहते हैं | Old street at dusk, empty, sun low at the end of the road |
| 2.1 to 5.2 | एक जनाज़े की ख़ातिर / सारा जहाँ निकला | The procession comes down the street: a white-shrouded bier with marigold garlands on four shoulders, a crowd behind, petals falling |
| 5.2 to 6.3 | बस वो ना निकला | One house; its door stays shut |
| 6.3 to 8.0 | जिसकी ख़ातिर जनाज़ा था | The procession passes right in front of that shut door |
| 8.0 to 11.3 | मगर परवीन शाकिर कहती हैं | Inside, she sits against that same door, hands over her mouth, crying |
| 11.3 to 14.7 | ऐ सनम मैं कैसे आती / तेरे जनाज़े के पीछे | Over her shoulder at the jaali window, her hand on the lattice, the procession in the street below |
| 14.7 to 16.5 | ऐ सनम मैं कैसे आती | Close on her face behind the jaali, eyes shut, tears |
| 16.5 to 18.6 | तेरे जनाज़े के पीछे | Night street, the procession walking away |
| 18.6 to 19.9 | एक मेरा जनाज़ा था | Her white ghost walks behind his bier |
| 19.9 to end | तेरे जनाज़े के पीछे | Inside, head on the door, eyes close, the diya goes out, colour drains, fade |

**Lyrics:** static Devanagari lines (Noto Serif Devanagari) that cut on and off with the phrases. White with
a soft shadow; जनाज़े/जनाज़ा in pale gold. Each line sits in the lower third, or at the top when she is there.

**Render:** `python3 make_janaza.py --workers 4` (`--frames 30,150` for previews).
