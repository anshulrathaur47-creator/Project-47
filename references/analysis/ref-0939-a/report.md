# Style analysis: ref-0939-a

Made by `tools/analyze_style.py`. Numbers are measured; read them with the contact sheet.

## Summary

- **duration**: 35.24
- **size**: 720x1280
- **fps**: 30.0
- **shots**: 1
- **cuts_per_min**: 0.0
- **shot_len**: {'mean': 35.24, 'median': 35.24, 'min': 35.24, 'max': 35.24}
- **first_3s_cuts**: 0
- **tempo_bpm**: 112.3
- **cuts_on_beat_pct**: None
- **hits_on_cuts_pct**: None
- **lufs**: -14.1
- **motion_mix**: {'handheld shake': 1}
- **scale_mix**: {'no face': 1}
- **avg**: {'brightness': 0.73, 'saturation': 0.2, 'contrast': 0.7, 'warmth': 0.01}

## Shots

| # | start | dur | scale | motion | bright | sat | warmth | palette | on-screen text |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.0 | 35.24 | no face | handheld shake | 0.73 | 0.2 | 0.01 | #f0ede7 #192232 #ccc1bd | Ab badho icp par: Folder ko ode| mein kholo ७७ FOL Code PROM |

## Audio

- tempo: 112.3 bpm, loudness: -14.1 LUFS
- sudden hits (likely SFX or drum hits): [0.19, 1.83, 2.09, 2.86, 3.18, 4.25, 4.5, 5.04, 5.85, 6.11, 6.52, 6.9, 8.52, 9.59, 10.61, 11.19, 11.4, 11.73, 12.0, 12.26, 12.79, 13.56, 13.86, 14.88, 15.74, 15.95, 16.76, 17.35, 17.74, 18.78, 19.2, 19.9, 20.27, 20.55, 20.81, 21.08, 21.34, 21.59, 22.15, 23.75]
- silences: []

## Speech

भी अरीवाशे रीलज बनाना सीखबगसग्लो किसकी सब लोग ख्लाउट कोट से आजी वाडल रीलज बनागा हैं मिना किसी एज़िटटो की अडिटिटंग के ना कोई क्तिंग ना ही किसी महंगे सोफ़्ेर की सृरूर है सीथा स्टेप वाईडनी तो में रील ताईप करो, मेरी तरब से तुमें रील स्टूड्यो किट की जिप फाल मिल जाएगी पस दाईटूड़ कर के एकस्ट्ट्ट मारो अब बड़ो स्ट्ट्टूब तुपर इस पूल्डर को प्लोड कोड में अपन करो और लिख हो अभी कोमेंट मेरील लिख हो

## How to use this

- Match the pacing: aim for the same cuts per minute and median shot length; keep the first-3-seconds cut count for the hook.
- If cuts_on_beat_pct is high, cut on beats (use the beat list in style.json).
- Reuse the motion mix (e.g. mostly push-ins) and the scale mix (close-ups vs wides).
- Match the colour: brightness/saturation/warmth averages and the palettes.
- Copy the text placement (y position, size) from the on-screen text rows, not the words.
