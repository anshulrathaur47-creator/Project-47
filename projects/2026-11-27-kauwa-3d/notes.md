# Kauwa 3D: the thirsty crow, the true version (ReelAudio-2110)

**Input:** `assets/music/ReelAudio-2110.mp3` (41.0 s Hindi narration), text in `references/ReelAudio-2110_hin.txt`.
Whisper words: `assets/music/ReelAudio-2110.words.json`. All timings below come from Whisper (estimated).

**Twist:** everyone knows the crow dropped stones into the pot to drink. Here, on his way to the pond he sees
those same stones hurting barefoot people on the path, so he clears the path and drops them into the pot.
Helping others is what fills his pot. Moral: "कभी-कभी अपना ना सोचके दूसरों की भी मदद करके अच्छा लगता है।"

## Characters (new for this reel)
- **Kauwa:** Indian house crow, black with a grey nape, big expressive eyes (tired, peering, wide-eyed, happy closed eyes).
- **Girl:** ponytail, orange top, red pants, barefoot, carries a brass lota.
- **Baba:** white beard, receding white hair, white kurta, walking stick, limps.

## Scene plan (Whisper times)
| Time | Line | Shot |
|---|---|---|
| 0–5.9 | सबको लगता है… | Storybook sepia page "प्यासा कौआ": the familiar crow dropping stones. The page tears away. |
| 5.9–8.6 | कौआ प्यासा दर-दर भटक रहा था | Harsh heat, orange sky, panting crow flying (tracking shot, heat shimmer). |
| 8.6–12.1 | मटके में थोड़ा सा पानी | Low 3/4 shot of him peering in, then POV down into the pot: a little dark water deep down. |
| 12.1–15.9 | दिमाग लगाया… कंकड़ उठाने गया | He turns to the camera, idea bulb, hops down toward the stones. |
| 15.9–18.9 | पानी का तालाब | Close-up: his eyes widen. Over-the-shoulder reveal of the lotus pond. |
| 18.9–21.3 | तालाब के पास जा ही रहा था | Tracking: he hops happily toward the pond. |
| 21.3–24.6 | कंकड़ रास्ते में पड़े थे | Ground-level shot: sharp stones in the foreground, the crow behind looking at them. |
| 24.6–27.4 | लोगों को चुभ रहे थे | Wide: the girl steps on a stone. Close-up: she cries (tear). Over the crow: Baba limps. He glances at the pond, then turns back to the path. |
| 27.4–31.5 | बारी-बारी उठाके मटके में डालने लगा | Down the path: stone by stone to the pot. POV insert: plink, splash ring, water rising. Low side shot. |
| 31.5–34.7 | सारे कंकड़ उठाके डाल दिए | The path is clear: the girl and Baba walk toward the camera, smiling. |
| 34.7–36.9 | अपनी प्यास बुझा ली | Pot full to the brim, he drinks with happy eyes. |
| 36.9–41.0 | moral | The girl kneels and leaves him a roti. Sunset crane-up. |

## Decisions
- Subtitles only (narration), static Devanagari at the lower third, clear of the bottom caption area.
- Audio used as-is (no music or SFX added).
- The crow is scaled true to size against the girl, and the cameras are pulled back so he never fills the frame (preview v0 had that issue).
- The crow is hidden in the two POV shots (the camera is his eyes).

## Render
`npx remotion render src/index.ts Kauwa3D out/silent.mp4 --gl=swangle --concurrency=4`, then mux with
`public/audio.mp3` → `exports/2026-11-27_kauwa-3d_v1.mp4` (crf 22, maxrate 7M, AAC 192k).
