# "उसको फुर्सत नहीं मिलती": 3D version

**Ask (user):** "3d m banao with better camera position angles and also story line". This uses the same sher as
`../2026-11-23-fursat`, rebuilt in real 3D with Remotion + three.js (React Three Fiber).

**Build:**
- `src/Character.tsx`: a toon-shaded 3D character rig built from primitives, with inverted-hull outlines, a face
  that has eyes, brows, a mouth and tears, and a walk cycle.
- `src/Fursat3D.tsx`:
  - the world: street, buildings with lit windows, lamp posts with spotlights and light cones, steps
  - time of day: a sky dome with fog, changing between morning, dusk and night
  - rain, petals and a pile of dried roses
  - 3D camera moves and the static lyrics overlay
- Render with `REMOTION_BROWSER=<headless shell> npx remotion render src/index.ts Fursat3D out/silent.mp4 --gl=swangle`,
  then mux `public/audio.mp3` with ffmpeg. The full render takes about 3 minutes.

**New character:** curly black hair, a maroon flannel shirt (plaid texture) over a black tee, blue jeans, white
sneakers. She has a ponytail, mustard kurta and white leggings.

| Time | Camera | Story |
|---|---|---|
| 0 to 2.7 | Crane down from the rooftops into an over-the-shoulder shot | She walks away down the dusk street on her phone; he holds a rose |
| 2.7 to 3.3 | Low-angle close-up with a slow orbit | His hopeful smile |
| 3.3 to 4.0 | Ahead of her, looking back | She stops and nearly turns back, then her phone buzzes and she walks on |
| 4.0 to 5.4 | High angle | He is left alone; the rose drops, petals fall |
| 5.4 to 9.0 | One continuous 360° orbit round the lamp post | Morning, dusk, then night: a gift box, a card, a rose. Each time she passes (with friends, on her phone, in a hurry) and never looks; at night she almost does |
| 9.0 to 11.4 | Dolly in to a close-up in the rain | He sits on the steps among dried roses, smiles at his rose with a tear; a glowing heart beats on each "दीवाने" |
| 11.4 to end | Crane up and back | Every dried rose around him on the steps, the rain, the lamp; fade |
