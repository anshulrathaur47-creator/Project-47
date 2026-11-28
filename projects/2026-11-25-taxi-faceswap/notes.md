# Taxi clip: main character replaced with the user's face

**Ask (user):** "Isme jo character hai, taxi chalana chahta hai, main character, usko mere character ke saath replace kar doge, and video smooth hona chahiye."
- Source: `raw-videos/2026-11-25-taxi/taxi_source.mp4`, a 23.5 s clip with Hindi subtitles, 720x720.
- Reference: `assets/images/characters/user_face_ref.jpg` (the user's own photo).

**Tool:** FaceFusion (`tools/external/facefusion`).
- Models compared on two frames: hyperswap 1a/1b/1c, inswapper_128, simswap_512.
- Chosen: `hyperswap_1c_256`, which keeps the user's moustache, goatee and skin tone best.
- Only the main character is swapped (reference mode, frame 15, distance 0.5). The manager and the woman stay as they are.
- Smoothness: box + occlusion mask with blur 0.4, and `gfpgan_1.4` at 65 % so the face stays sharp without flicker.

```
.venv/bin/python facefusion.py headless-run --download-providers github --execution-providers cpu --execution-thread-count 4 \
  --processors face_swapper face_enhancer --face-swapper-model hyperswap_1c_256 --face-swapper-pixel-boost 512x512 \
  --face-enhancer-model gfpgan_1.4 --face-enhancer-blend 65 --face-selector-mode reference --reference-frame-number 15 \
  --reference-face-distance 0.5 --face-mask-types box occlusion --face-mask-blur 0.4 \
  -s <ref.jpg> -t <video> -o swap_v1.mp4
```

## v2 (user: "dono characters pe kyun laga diya, fix karo aur smooth karo")
- v1 also swapped the manager in his two shots (3.7–6.2 s, 8.1–9.7 s), because reference mode at distance 0.5 was too loose.
- v2 splits the clip at the cuts (PySceneDetect) and runs FaceFusion only on the main-character shots: frames 0–110, 186–244, 292–341, 413–502 and 683–706, in `one` mode (largest face).
- Every other shot is copied untouched from the source.
- Smoother: enhancer blend 45 (was 65), mask blur 0.5, and light temporal smoothing (`hqdn3d=0:0:5:5`) on the swapped shots only.
- Re-join with `python3 assemble.py v2`.

## v3 (user: "driver ka face bhi stable nahi hai")
- The shimmer came from the face changing slightly every frame (brightness, brow shape), and the enhancer added to it.
- Re-swapped the main shots without the face enhancer, then ran `tools/face_stabilize.py --strength 0.8` on each one.
  - It smooths the swap's residual (swapped minus original) over time, warped by optical flow from the original footage.
  - The film's real motion and grain stay exact; only the new face's wobble is averaged.
- Measured extra flicker in the face area:

  | Shot | v2 | v3 |
  |---|---|---|
  | Driving close-up | 1.94 | 0.94 |
  | Last shot | 4.34 | 1.60 |
  | Interview | 3.34 | 2.62 |

- Re-join with `python3 assemble.py v3 stn`.
