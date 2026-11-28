# Style analysis: gecko-love

Made by `tools/analyze_style.py`. Numbers are measured; read them with the contact sheet.

## Summary

- **duration**: 40.01
- **size**: 720x1280
- **fps**: 24.0
- **shots**: 11
- **cuts_per_min**: 15.0
- **shot_len**: {'mean': 3.64, 'median': 3.83, 'min': 0.83, 'max': 8.58}
- **first_3s_cuts**: 0
- **tempo_bpm**: 92.3
- **cuts_on_beat_pct**: 50.0
- **hits_on_cuts_pct**: 30.0
- **lufs**: -14.5
- **motion_mix**: {'handheld shake': 4, 'pan left': 1, 'pan right': 1, 'push-in': 2, 'static': 3}
- **scale_mix**: {'close-up': 1, 'extreme close-up': 1, 'no face': 9}
- **avg**: {'brightness': 0.44, 'saturation': 0.53, 'contrast': 0.38, 'warmth': 0.15}

## Shots

| # | start | dur | scale | motion | bright | sat | warmth | palette | on-screen text |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.0 | 5.38 | no face | push-in | 0.42 | 0.54 | 0.16 | #2f2017 #5c3b27 #905f39 |  |
| 2 | 5.38 | 0.83 | no face | handheld shake | 0.46 | 0.47 | 0.14 | #5a3d2e #8b5e3e #2e211b |  |
| 3 | 6.21 | 1.17 | no face | push-in | 0.39 | 0.57 | 0.16 | #38271b #583923 #784c2c |  |
| 4 | 7.38 | 2.62 | no face | static | 0.31 | 0.53 | 0.11 | #271b14 #4a3123 #794d30 |  |
| 5 | 10.0 | 1.29 | close-up | static | 0.47 | 0.56 | 0.17 | #7b5234 #5d3a23 #97704f |  |
| 6 | 11.29 | 3.83 | extreme close-up | handheld shake | 0.42 | 0.55 | 0.14 | #301c0e #4e331f #735236 |  |
| 7 | 15.12 | 3.96 | no face | handheld shake | 0.46 | 0.49 | 0.13 | #523521 #7f5e46 #dbc6b1 |  |
| 8 | 19.08 | 4.83 | no face | handheld shake | 0.46 | 0.57 | 0.17 | #835d3c #63442a #321d0e |  |
| 9 | 23.92 | 6.08 | no face | pan left | 0.49 | 0.56 | 0.18 | #8c6441 #341f10 #68462c |  |
| 10 | 30.0 | 1.42 | no face | static | 0.48 | 0.54 | 0.16 | #6e462d #956746 #382112 |  |
| 11 | 31.42 | 8.58 | no face | pan right | 0.48 | 0.48 | 0.13 | #6b4830 #452b1a #8a6850 |  |

## Audio

- tempo: 92.3 bpm, loudness: -14.5 LUFS
- sudden hits (likely SFX or drum hits): [3.69, 3.99, 5.39, 6.36, 9.98, 13.47, 13.86, 16.04, 17.55, 19.16, 19.88, 20.22, 21.71, 22.18, 25.57, 26.17, 26.98, 28.03, 29.09, 29.74, 30.12, 32.74, 35.36, 36.18, 38.01]
- silences: [[11.1, 11.52], [15.0, 16.0], [18.18, 19.18], [23.78, 24.47]]

## How to use this

- Match the pacing: aim for the same cuts per minute and median shot length; keep the first-3-seconds cut count for the hook.
- If cuts_on_beat_pct is high, cut on beats (use the beat list in style.json).
- Reuse the motion mix (e.g. mostly push-ins) and the scale mix (close-ups vs wides).
- Match the colour: brightness/saturation/warmth averages and the palettes.
- Copy the text placement (y position, size) from the on-screen text rows, not the words.
