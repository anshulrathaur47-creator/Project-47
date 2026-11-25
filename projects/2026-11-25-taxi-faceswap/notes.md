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
