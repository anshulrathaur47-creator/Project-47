# "गाड़ी के शीशे पर जमी धूल": 3D reel

**Inputs:** `assets/music/ReelAudio-74390.mp3` (21 s), transcript `references/ReelAudio-74390_hin.txt`.
Lyric timing comes from Whisper word timings (`assets/music/ReelAudio-74390.words.json`).
The audience's "वाह" (6.04–6.5 s) gets no text.

**Build:** Remotion + three.js, same pipeline as `../2026-11-24-fursat-3d`.
- `src/Character.tsx`: rig copied from fursat-3d, plus new hair styles ("short" spiky fringe, "long" open hair),
  surprised "o" mouth, blush strength, happy closed eyes, no-swing pockets walk, and a hidden right arm for IK.
- `src/Sheesha3D.tsx`:
  - a parked old car with a dusty windshield drawn on a canvas texture every frame
  - finger lines (heart, then "मीरा + विहान") cut out of the dust
  - the sleeve wipe leaves smudges and a faint heart trace that the street light catches at the end
  - a world-space 2-bone IK arm so his finger follows the strokes on the glass
- Render: `REMOTION_BROWSER=<headless shell> npx remotion render src/index.ts Sheesha3D out/silent.mp4 --gl=swangle --concurrency=4`,
  then mux `public/audio.mp3` with ffmpeg.

**New characters:** Vihaan has a short spiky fringe, a grey hoodie, olive cargos and red shoes. Meera has long open
hair, a lavender top and cream pants. Two friends: teal and orange tops.

| Time | Camera | Story |
|---|---|---|
| 0–1.55 | Low dolly down the night lane | He walks up to a dusty parked car under a street lamp, hands in pockets |
| 1.55–3.08 | Insert, straight down on the glass | His finger draws a heart in the dust; a glint runs over the glass on "शीशे"; dust motes in the lamp light |
| 3.08–4.9 | Over the shoulder, low left | He writes "मीरा + विहान" inside the heart, blushing |
| 4.9–6.66 | Low, from the bonnet | Dreamy smile; eyes close on "वाह"; little hearts |
| 6.66–7.5 | Dutch tilt | Footsteps and laughter: he whips round, shocked |
| 7.5–8.44 | His point of view | The girls coming down the lane |
| 8.44–9.84 | Close on the glass, white flash | Panic sleeve wipe, dust puff; only smudges are left |
| 9.84–12.3 | Low wide | He leans on the car pretending to be casual; she passes laughing with friends and never looks |
| 12.3–13.52 | Close-up | "ये बात पता है मुझे": a sad, knowing smile, eyes down |
| 13.52–15.46 | Wide over his shoulder | Up the lane a friend turns and calls her name (voice rings); he looks up |
| 15.46–16.8 | Close-up | The smile he can't stop: blush, happy closed eyes, floating hearts |
| 16.8–end | Crane up and back | He walks off into the night; the faint heart trace on the glass glows; fade |
