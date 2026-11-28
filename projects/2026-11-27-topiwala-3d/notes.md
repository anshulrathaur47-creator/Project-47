# Topiwala 3D: the cap-seller and the monkeys, the true version (ReelAudio-36643)

**Input:** `assets/music/ReelAudio-36643.mp3` (45.3 s Hindi narration), text in `references/ReelAudio-36643_hin.txt`.
Whisper words: `assets/music/ReelAudio-36643.words.json`. All timings below come from Whisper (estimated).

**Brief from the user:** "Scenes realistic rakhna yaar". They chose the free route (realistic 3D lighting)
over Figma AI images (paid credits).

**Twist:** everyone says the monkeys foolishly copied the cap-seller. Here the chief monkey saw a poor man
crying under the tree (torn chappal, dry face), understood his children would sleep hungry, and when the man
slammed his cap down in anger, the monkeys dropped every cap to help him. Humans bought nothing all morning;
the animals lit his chulha.

## Look ("realistic lighting" kit, `src/Real.tsx`)
- Physical sky shader (three.js `Sky`) with image-based light from the same sky (PMREM), ACES tone mapping.
- PBR materials with canvas textures: dirt, bark, fur (with bump), cloth weave and stains, thatch, mud walls, rope.
- Banyan: about 5,000 alpha-tested leaf cards that cast dappled shadows, aerial roots and root flares; instanced grass.
- Soft 2K shadows, distance fog, god rays and dust motes in the golden light, film grain over everything.
- New characters: thin cap-seller (stubble, worn kurta-dhoti, white cap, torn chappals), his wife and two kids,
  three villagers, and rhesus macaques (the chief is bigger and greyer, with a scar over one eye).
- A proportioned human rig with real eyes (sclera, iris, pupil, catch-light, eyelids), and a sitting macaque rig.

## Scene plan
| Time | Line | Shot |
|---|---|---|
| 0–9.3 | सबको कहानी… नकल की… फेंक दीं | The version everyone tells, in an old-film look: monkeys in caps laughing and scratching; he flings his cap down, caps rain. |
| 9.3–10.0 | | VHS rewind back through the shots, white flash into full colour. |
| 10–13 | पर असल में… | Golden afternoon. Slow push-in on the chief monkey, quiet, holding a red cap. |
| 13–15.5 | पेड़ पर बैठे सरदार बंदर | Low wide of the banyan, monkeys on the branches, light rays. |
| 15.5–16.9 | नीचे रोते हुए | POV from the chief's eyes down to the man crying at the trunk. |
| 16.9–18.1 | उस गरीब टोपीवाले | The man sitting, head down, sobbing. |
| 18.1–19.3 | फटी चप्पल | Insert: a torn chappal in the dust. |
| 19.3–20.9 | सूखा चेहरा | Close-up: tired face, stubble, tears. |
| 20.9–24.5 | वो समझ गया… टोपियां नहीं बिकीं | The chief's eyes soften; he looks at the cap in his hands. |
| 24.5–27.2 | छोटे बच्चे… भूखे सो जाएंगे | What he imagines: moonlit hut, two kids asleep on a charpai, an empty thali, a dying diya, a cold chulha. |
| 27.2–31.9 | गुस्से में टोपी जमीन पर मारी | The man stands; low dutch angle; he rips off his cap and slams it into the dirt (dust burst, shake). |
| 32–34.1 | मजाक में नहीं | The chief turns to his troop and nods. |
| 34.1–37.3 | मदद करने के लिए… गिरा दीं | From below, monkeys let the caps go; wide: caps float down in the golden light, he looks up stunned. |
| 37.3–41.7 | जिन इंसानों ने सुबह से… | Flashback (cold, desaturated): that morning people walked past his outstretched cap. |
| 41.7–46.5 | उन बेजुबान जानवरों ने… चूल्हा जला दिया | Night: the chief sits on his hut roof wearing the red cap; the chulha blazes, roti puffs, the family eats; crane up. |

## Decisions
- Subtitles only (narration), static Devanagari at the lower third.
- Audio used as-is. The video runs 1.2 s past the narration for a held last shot with a fade.
- The rewind replays story time backwards, so it scrubs back through the classic shots.

## Render
`npx remotion render src/index.ts Topiwala3D out/silent.mp4 --gl=swangle --concurrency=4`, then mux with
`public/audio.mp3` → `exports/2026-11-27_topiwala-3d_v1.mp4`.
