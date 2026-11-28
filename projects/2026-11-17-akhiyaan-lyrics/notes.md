# Akhiyaan: glowing lyrics on the user's reel

**Input:** `raw-videos/reel_akhiyaan_0013_0040.mp4`, the user's 27 s animated reel (library love story),
song 0:13 to 0:40. Lyric sheet (auto transcript) in `references/akhiyaan_lyrics_hin_raw.txt`.

**Timing:** Whisper (small, given the lyric sheet as a hint), run per section and checked against where
the vocals pause (harmonic vs. stereo-side energy). Vocals run 0.3 to 19.6 s, a pause until ~21.9 s, then
the "तौबा तेरियां ए अखियाँ" hook. Line 1 of the sheet says "नींद" and line 3 says "नींदर"; Whisper heard
"नींदर" both times, so both lines use "नींदर".

| Clip time | Lyrics | Motion style |
|---|---|---|
| 0.3 to 3.6 | असी नींदर / चैन गवा बैठे | soft float out of a blur (pink) |
| 3.7 to 7.0 | असी ना-ना / करदे ला बैठे | 3D flip with beat punch (gold) |
| 7.0 to 10.6 | असी नींदर / चैन गवा बैठे वे | wave (lavender) |
| 10.7 to 13.9 | असी ना-ना / करदे ला बैठे | zoom rush with light trail (pink) |
| 14.0 to 17.7 | असी तकदे-तकदे / की तक्कियां? | slow stare push with beat shake (gold) |
| 17.8 to 19.7 | तौबा तेरियां... | slides in with a light streak (rose) |
| 21.9 to 27.0 | तौबा तेरियां ए अखियाँ (x2) | heart pop; "अखियाँ" beats like a heart with hearts and sparkles bursting out |

All words: neon glow (dark halo + wide glow + tight glow + bright core), a light sweep, a beat pulse and
drifting glitter. Placement: top band (centre y = 248), which is clear of both characters in every shot
(checked frame by frame) and below the app's top bar.

**Render:** `python3 add_lyrics.py` (original audio copied untouched).
