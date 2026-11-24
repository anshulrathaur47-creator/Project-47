# "ये चेहरे पे चेहरा लगा लेते हैं": 3D reel

**Inputs:** `assets/music/ReelAudio-64225.mp3` (39.6 s) and `references/ReelAudio-64225_hin.txt`.
- Lyric timing comes from chunked Whisper alignment with a transcript hint; the full pass lost the first 30 s.
- 12 lines, static lyrics, Noto Serif Devanagari at top 1290.

**Build:** Remotion + three.js.
- `src/Character.tsx`: the rig plus a "bun" hair style, a smiley mask on a stick (`pose.mask`) and a lopsided smirk (`pose.smirk`).
- `src/World.tsx`: street, buildings, lamps and trees, shared from the gaadi-sheesha reel; sky colours are now configurable.
- `src/Chehre3D.tsx`: the story, cameras and effects.
- Effects: a CSS sepia flashback, and a red-tinted replay with scanlines.

**New character:** Meher. She has a messy bun, a mustard jacket over a maroon top, navy jeans, white shoes and a red
thread on her wrist. Friends: F1 (teal, ponytail; the one who pushes), F2 (curly), F3 (short hair, red hoodie). There is
also a hooded enemy.

| Time | Camera | Story |
|---|---|---|
| 0–2.7 | Crane down behind her | Street birthday party; three friends hold smiley masks over their faces |
| 2.7–5.15 | Side, foreground | Her back is turned; F2 slips off and shakes hands with a hooded enemy |
| 5.15–7.66 | Dutch close pan, red light | The masks come down: smirks |
| 7.66–10 | Low, behind her | She cries on a crate; they laugh, point and film |
| 10–12.4 | High wide | Alone down the lane; a heart above her breaks in two |
| 12.4–15.1 | Orbit | Everyone's face is in a glowing phone; nobody looks at her |
| 15.1–19.8 | Bench, sepia | An old couple, arm in arm on a bench; they turn to dust; she finds the bench empty |
| 19.8–21.25 | Low at the foot of the stairs | She comes down the stairs on her phone; F1 behind her, masked |
| 21.25–22.1 | Dutch, low front, flash | The push; she falls |
| 22.1–23.85 | Her point of view | F1 at the top lowers the mask and smirks |
| 23.85–25.8 | Close-up | Tear; she knows |
| 25.8–27.3 | Insert | Two hands meet, both wearing the same red thread |
| 27.3–29.1 | Two-shot | She takes the hand and rises |
| 29.1–33.9 | Overhead, red replay | Slow-motion replay of the push |
| 33.9–end | Follow, then crane up | Hand in hand down the lane, the mask hidden behind F1's back; she glances back, eyes closed, tear |
