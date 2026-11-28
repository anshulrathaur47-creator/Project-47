# Style analysis: ref-0939-b

Made by `tools/analyze_style.py`. Numbers are measured; read them with the contact sheet.

## Summary

- **duration**: 61.65
- **size**: 720x1280
- **fps**: 30.0
- **shots**: 1
- **cuts_per_min**: 0.0
- **shot_len**: {'mean': 61.65, 'median': 61.65, 'min': 61.65, 'max': 61.65}
- **first_3s_cuts**: 0
- **tempo_bpm**: 117.5
- **cuts_on_beat_pct**: None
- **hits_on_cuts_pct**: None
- **lufs**: -14.4
- **motion_mix**: {'push-in': 1}
- **scale_mix**: {'no face': 1}
- **avg**: {'brightness': 0.21, 'saturation': 0.52, 'contrast': 0.4, 'warmth': 0.08}

## Shots

| # | start | dur | scale | motion | bright | sat | warmth | palette | on-screen text |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.0 | 61.65 | no face | push-in | 0.21 | 0.52 | 0.08 | #050908 #262a2e #02a403 | search karo aws Bedr Console Home Last visited: min ago Rece |

## Audio

- tempo: 117.5 bpm, loudness: -14.4 LUFS
- sudden hits (likely SFX or drum hits): [0.26, 0.6, 0.93, 1.28, 1.93, 3.04, 4.11, 4.41, 5.04, 5.92, 6.18, 6.41, 6.92, 7.27, 8.82, 10.17, 10.54, 10.8, 11.17, 12.17, 12.82, 13.14, 14.16, 16.16, 16.42, 16.65, 16.88, 17.3, 17.55, 17.93, 18.16, 19.5, 20.36, 20.67, 20.9, 21.5, 22.15, 22.48, 22.87, 24.15]
- silences: [[32.58, 33.18], [37.69, 38.34], [43.05, 43.42], [44.54, 44.95], [46.21, 46.67]]

## Speech

अगर तुमने क्लोड का तोसो डोलर वाला प्लन प्री में नहीं लिया तो तुम बहुत बड़े आल्सी हो तुकि जेप भेजोस हुद ये प्लान तुमें बिलकुल फ्री में दे रहें और इस में सिर्फ क्लोड के मोडल्स नहीं जाड जी पी ती जेमनाई सारे मोडल्स फ्री में युज कर सकतें सिर्फ तीन स्टेप्स हैं और दो मिनेट लगें बस तो मुझे फ्लोग करो इस रील को सेव करो और कोमिंट में क्लोड लेगतें मैं तुहें स्टेप बाट स्टेप गाईद भेजों बहला, बस गुगल पे एडव्लूस स्टर्ज करो वहां साईनिन का अप्षन आजाएगा नया अकाउन पना, साईनिन करते ही प्री क्रेटिट्स मिल जाते हैं तुस्टरा, सर्च करो बेट्रोक वहां API कीज में जाओ और लोंग तर्म API की बनाब और तीस्रा, मोडल काटलोग कोलो वहां सारे मोडल्स दिखेंगे जो चाहीए वो सेलेक्त करो और सीड़ा प्लेग्राउन में चाँ। और सबसे मस्थ बात ये API की तुम अपने कोडिं तुज में भी लगा सकते है मतलब एक की और सब कुछ तुमहरे हाथ में और हां, गाईट चाहीए तो कौमेंट में क्लोड लिखना मत भूलना

## How to use this

- Match the pacing: aim for the same cuts per minute and median shot length; keep the first-3-seconds cut count for the hook.
- If cuts_on_beat_pct is high, cut on beats (use the beat list in style.json).
- Reuse the motion mix (e.g. mostly push-ins) and the scale mix (close-ups vs wides).
- Match the colour: brightness/saturation/warmth averages and the palettes.
- Copy the text placement (y position, size) from the on-screen text rows, not the words.
