# Chakki 3D: the magic mill, the elder brother's side (ReelAudio-21913)

**Input:** `assets/music/ReelAudio-21913.mp3` (127.2 s Hindi narration), text in `references/ReelAudio-21913_hin.txt`.
- Whisper words are in `assets/music/ReelAudio-21913.words.json`.
- Whisper's VAD dropped 66–88 s. That stretch was re-timed from short windows and the speech envelope.
- All timings are estimated.

**Twist:**
- Everyone calls the rich brother greedy. But he had built his shop over years and helped his younger brother again and again.
- He said no once, because his help was making his brother dependent. He wanted him to learn to stand on his own feet.
- The younger brother found a magic mill, got rich, and when the elder's business failed, threw that one "no" back at him.
- Hurt and angry, the elder stole the mill. He didn't know the mantra to stop it, so salt kept flowing until his boat sank.

## Look
- Same realistic-lighting kit as the earlier 3D reels (`src/Real.tsx`, with `canvasTex` now exported).
- **Village:**
  - the elder's grain shop "अनाज भंडार" (plinth, counter, a brass scale, jute sacks that empty as the business fails, a ledger and diya at night, a swinging signboard in the storm)
  - the younger brother's mud hut with a charpai and a field gone to weeds
  - the hut becomes a two-storey painted mansion with pillars, bunting and lamp strings at night
- **The mill:** two stones and a wooden peg. It glows gold with sparkles, and gold coins pour out of it into a pile.
- **The sea at night:**
  - a moon with its reflection path, waves in the vertex shader
  - a wooden boat with oars and a stern lantern
  - salt streaming into a growing heap; the boat sinks bow-first and the lantern dies
- **The dawn sea:** a glow under the water where the mill still grinds, and his shawl floating. Then the shore at sunrise, where the younger brother stands holding the shawl.
- **New characters:**
  - the elder: maroon kurta, cream dhoti, gold shawl, moustache
  - the younger: worn blue shirt and torn chappals; when rich, a gold kurta, red sash and red pagdi
  - three villagers
- **Grades:**
  - old-film sepia for the story everyone tells (start and 100.7–104 s)
  - a warm memory grade for the past and the reflection replays
  - a white flash when the hut turns into the mansion

## Scene plan (Whisper times)
| Time | Shot |
|---|---|
| 0–9.1 | Sepia: the elder sneaking off with the glowing mill, grinning; villagers point at his full shop; close-up as the question lands; rewind. |
| 9.1–17.7 | The younger walks to the shop and pleads; the elder shakes his head; the younger points ("स्वार्थी") and storms off. |
| 17.7–21.5 | Years of work: carrying sacks by day, the ledger by a diya at night. |
| 21.5–27.8 | Memory: the elder hands over a red money pouch, again and again (morning, noon, evening), getting wearier. |
| 27.9–45.8 | The elder thinks. The younger lounges on his charpai by a weedy field while the elder watches. He clutches the pouch back. Feet shot: "अपने पैरों पर". |
| 45.8–56 | The younger finds the glowing mill in the weeds; gold coins pour out; flash, and the hut becomes a mansion; villagers greet the rich brother. |
| 56–62.1 | Storm sky and the signboard swinging; the shop empties; the elder sits on its edge by an empty money box. |
| 62.1–74.7 | Dusk: he walks to the mansion and folds his hands. The younger, arms crossed and smug, says his lines, turns in, and the doors close. The elder walks home alone. |
| 74.7–88 | Night: alone with a diya, a tear, looking across at the lit mansion. Then he steals the mill from its stool in the yard (dutch angle). |
| 88–100.7 | The moonlit sea: he rows out, turns the mill and salt flows; he can't stop it; the salt heaps up; the boat sinks and the lantern dies. |
| 100.7–108 | Sepia: villagers retell "the greedy brother". Dawn sea: the glow under the water, his shawl floating. |
| 108–117.3 | Warm replays: the pouch handed over; the one refusal; the younger's anger. |
| 117.3–128.5 | Dawn shore: the younger holds the shawl and looks at the sea; a wide sunrise, then fade. |

## Decisions
- Subtitles: narration only, static Devanagari at the lower third.
- Audio: used as-is. A 1.3 s hold at the end.
- The younger brother at the shore holding the shawl is not in the narration. It was added as a quiet visual for the closing question.

## Render
Rendered in 750-frame chunks:

```
render_chunks2.sh <dir> Chakki3D 3855 0..5
```

The chunks are joined, the narration is muxed in, and the result goes to `exports/2026-11-28_chakki-3d_v1.mp4`.
