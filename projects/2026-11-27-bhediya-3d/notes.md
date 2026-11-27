# Bhediya 3D: the boy who cried wolf, the true version (ReelAudio-95086)

**Input:** `assets/music/ReelAudio-95086.mp3` (123.5 s Hindi narration), text in `references/ReelAudio-95086_hin.txt`.
Whisper words: `assets/music/ReelAudio-95086.words.json`. Two stretches Whisper merged (47–65 s and 76–83 s) were re-timed from short windows and the speech envelope. All timings are estimated.

**Twist:** everyone says the boy lied and got punished. Here the wolf really came every time. It only ran off because the villagers came running. Once they stopped believing him, it had no reason to run.

## Look
- Same "realistic lighting" kit as Topiwala (`src/Real.tsx`):
  - physical sky with image-based light
  - PBR materials with canvas textures
  - alpha-tested leaves that cast dappled shadows
  - instanced grass, soft shadows, fog, film grain
- New in the kit:
  - an Indian grey wolf (walk, stalk, crouch, gallop, snarl, ears back, glowing eyes at dusk)
  - woolly desi sheep (graze, startle, scatter, fall)
  - a turban option for the human rig
- New characters:
  - the shepherd boy (red turban, teal shirt, barefoot, lathi)
  - a farmer (white turban, khaki shirt, dhoti)
  - a woman (yellow saree, green blouse)
  - a young man (red shirt)
  - two elders (one in a white turban, one in saffron)
- One world:
  - a pasture with a big rock
  - a forest edge with bushes where the wolf hides
  - the path down to a village with huts, a neem, a well, a haystack and a field
- The sun's shadow box follows whichever area is in shot.
- Light by part of the story:
  - classic tale: noon, old-film sepia
  - first time: morning
  - second time: noon
  - panchayat: golden hour
  - last day: dusk with the sun low behind the forest
  - ending: moonlit night

## Scene plan (Whisper times)
| Time | Line | Shot |
|---|---|---|
| 0–8.7 | उस मशहूर कहानी में… | The version everyone tells, sepia: the boy on the rock shouting, then laughing; villagers come and scold him. |
| 8.7–9.4 | | VHS rewind back through the tale, white flash. |
| 9.4–10.2 | पर सच्चाई… | Colour. Two yellow eyes in the bushes at the forest edge. |
| 10.2–17.5 | दरअसल… हमला करने आता था | The boy with his flock notices, cups his hands and shouts. The wolf stalks out low and snarls; the sheep startle. |
| 17.5–23.7 | गाँव वालों को आते देख… | Villagers come up the path. The wolf turns and runs into the forest. The boy pats the lamb. |
| 23.7–29.6 | पहली बार… दौड़े चले आए | In the village: the farmer hoeing and the woman at the well hear him, drop the hoe, the pot and the hay, and run. |
| 29.6–43.5 | भेड़िया वहाँ नहीं… भरोसा मत करना | They arrive to calm sheep. The boy points at the forest and pleads. The farmer scolds; the woman tells the others not to trust him again; they leave. |
| 43.5–50.8 | दूसरी बार… | Noon: the boy shouts with the wolf creeping in behind him. Two villagers come running, annoyed; the wolf slinks off. |
| 50.8–61.6 | यकीन हो गया… कोई नहीं जाएगा | Golden hour panchayat under the neem: the elder rules, and the others cross their arms and nod. |
| 61.6–66.3 | भेड़िया दोबारा आया… टूट पड़ा | Dusk: the wolf walks out boldly and charges; the sheep scatter. |
| 66.3–74.2 | पहले से भी ज़्यादा जोर से… उम्मीद | Close-up scream, over the shoulder to the lit village far below, his hopeful face. |
| 74.2–86.7 | घरों में बैठे… दरवाज़ा बंद | The village at dusk: the farmer smirks on his charpai, the young man laughs it off, the old man turns in and shuts his door. |
| 86.7–101.9 | एक-एक करके… पत्थर पर बैठकर | Kept non-graphic. In silhouette against the low sun, the wolf reaches the sheep one by one and they fall. The boy chases with his stick, then looks at the empty path, drops the stick and sits on the rock. |
| 101.9–106.7 | पूरी दुनिया ने कहानी बनाई… | Sepia again: villagers stand smug, arms crossed, watching the boy on the rock. |
| 106.7–116.3 | सच तो ये था… भाग जाता था | Cold flashback replays: the wolf was there every time, and ran each time the villagers came. |
| 116.3–125 | जिस दिन विश्वास छोड़ दिया… | Night: doors shut in the village. The wolf strolls through the pasture in the moonlight and looks at us. Wide on the boy alone on the rock. |

## Decisions
- Subtitles: narration only, static Devanagari at the lower third.
- Audio: used as-is. The video runs 1.5 s past the narration for a held last shot and fade.
- The 3D canvas can be rendered smaller via `--props='{"cw":720}'`. That was only 1.3x faster, so the final render uses the full 1080.

## Render
Rendered in five 750-frame chunks, so a fix only re-renders one chunk:

```
npx remotion render src/index.ts Bhediya3D out/part_N.mp4 --frames=A-B --gl=swangle --concurrency=4
```

The chunks are joined, the narration is muxed in, and the result goes to `exports/2026-11-27_bhediya-3d_v1.mp4`.
