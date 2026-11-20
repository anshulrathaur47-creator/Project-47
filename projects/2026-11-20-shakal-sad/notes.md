# "इस चेहरे के साथ..." (sad reel)

**Ask (user):** the audio `assets/music/ReelAudio-51331.mp3` (19.9 s, a spoken monologue over soft music)
plus its transcript `references/ReelAudio-51331_hin.txt`, "Sad banana".

**Timing:** Whisper (small) with the transcript as a hint. The first 12 s were aligned on their own, because
the full pass only picked up the second half. Word times are in `make_shakal.py` (CHUNKS) and in
`whisper_words.json` (second half). Music runs at ~99 bpm.

**Character:** the same rig with a new look: round glasses, freckles, a grey hoodie.

| Time | Words | Scene | Camera | Signs |
|---|---|---|---|---|
| 0 to 1.6 | इस चेहरे के साथ | sunset street, he walks with a rose, shy smile | wide, slow push | |
| 1.6 to 2.9 | तुम्हें कोई लड़की | stops and holds the rose out to a girl (silhouette) | medium, framed on both | pink heart |
| 2.9 to 3.7 | क्यों ही पसंद करेगी? | she turns and walks away, his smile drops | close-up | heart cracks in two, petals fall |
| 3.7 to 4.25 | तुम इतने | night and rain; faceless people surround him, laughing and pointing | wide, flash in | |
| 4.25 to 5.7 | बदसूरत लगते हो | he shuts his eyes, clutches his chest, the rose falls | dutch close-up | pointing hands from the edges, red jolt, the word shatters |
| 5.7 to 7.4 | यहाँ बच्चे तो बच्चे, बड़े भी तुम्हें | park, he gives the kids a shy wave | whip-pan, wide | |
| 7.4 to 9.0 | देखकर भाग डरते हैं | kids and grown-ups see him and run off | medium | an eye, "!" marks, dust puffs |
| 9.0 to 10.4 | अपनी शक्ल और | bathroom mirror, over his shoulder; hand on his cheek | over the shoulder | mirrored words |
| 10.4 to 12.1 | अपनी हालातों को देख मुझे शर्म आती है | reflection close-up; he hides his face, cheeks red | close-up | the mirror cracks on "देख" |
| 12.1 to 13.4 | वो कैसी | walking in the rain | feet shot | |
| 13.4 to 15.0 | ज़िंदगी जीऊँ मैं? वो कैसा | head down, hands in pockets | medium | question marks |
| 15.0 to 16.7 | इंसान बन जाऊँ मैं | he holds a smiling mask to his face, then lets it fall | close-up | the mask |
| 16.7 to 18.3 | जहाँ मैं दिखता कैसा हूँ | under a huge moon, looking up, crying | pull back | an eye |
| 18.3 to end | वो ज़्यादा मायने रखता है | last close-up, tears, eyes close, fade out | close-up | a balance where the face outweighs the heart; the words dissolve into dust |

**Text:** only the spoken words, word by word with a soft neon glow. Each line goes into the band (top or
lower third) with the least overlap with him and the signs. Hurtful words are red (बदसूरत, डरते, शर्म) and
hopeful ones are gold (ज़िंदगी, इंसान, मायने).

**Grade:** warm sunset at the start, then colder and greyer scene by scene, ending in blue moonlight.

**Render:** `python3 make_shakal.py --workers 4` (`--frames 30,150` for previews). It imports the rig and scenes
from `../2026-11-16-remember-19-nov/make_19nov.py`. Audio is the user's track, untouched apart from a
0.5 s fade at the end.
