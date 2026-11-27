# Jamshedpur: CM Hemant Soren pays tribute to Arjun Munda's late mother (news reel)

**Ask (user):** "1 se 2 min ki edit krke acche se news bana do and also logo lga dena the media times.live ka".
The user sent a news script (Hindi), 6 WhatsApp clips, one photo and the channel logo.

**Facts used (only from the user's script):**
- Former CM Arjun Munda's mother, स्वर्गीय सायरा मुंडा, died this week.
- Today (27 Nov 2026), CM Hemant Soren and Gandey MLA Kalpana Soren visited his Ghorabandha residence in Telco, Jamshedpur.
- They garlanded her portrait and paid tribute.
- All East Singhbhum MLAs also offered flowers.
- The CM and the MLAs met the family and offered support.
- The byte is the CM's (as labelled in the script).

**Raw:** `raw-videos/2026-11-27-munda-shraddhanjali/`
- 0039: hall (landscape, 81 s). Arrival walk-in, then tributes at the portrait: the CM (36–47), Kalpana Soren (48–58), an MLA (59–68).
- 0040: CM's media byte (landscape, 134 s).
- 0041: the portrait on the table, the crowd, the room with the family (vertical).
- 0042: helicopter arriving and landing (vertical).
- 0043: police at the residence gate (vertical).
- 0044: residence courtyard, convoy, folded hands from the car (vertical).
- IMG-0035: high-res photo of the bow before the portrait.

**Byte text:** Whisper on the noisy byte was rough (`transcripts/`, `byte40_*.json`), so the subtitle lines were cleaned up by hand.
- 32.9–37.8: "आप सब को पता है, कुछ दिन पहले"
- 40.3–42.8: "अर्जुन मुंडा जी की माता जी का निधन हुआ"
- 52.3–61.8: "राजनीतिक लोग तो हैं, पर सामाजिक, व्यक्तिगत संबंध भी साथ चलते हैं"
- 63.2–70.6: "और उसी बाबत आज हम लोग माता जी को श्रद्धांजलि देने घोड़ाबांधा आए हैं"
- 76.9–78.9: "हम लोगों ने श्रद्धांजलि भी दी"
- 86.9–89.5: "भगवान उनकी आत्मा को शांति दे"
- Left out: 81–86 (unclear), and 105–131, a political question about the session, which is off-topic.

**Edit (90 s):** `make_news.py`.
- Calm cuts for a condolence story: dissolves and dips to black, no whips or flashes.
- Landscape clips and the photo sit in a 1080x900 panel over a blurred copy of themselves, with thin red rules.
- Brand: logo bug top-right on every shot, a logo sting at the start, and a logo end card with a follow CTA (`brand-kit/`).
- Graphics: "जमशेदपुर | 27 नवंबर 2026" tag, red "ताज़ा ख़बर" ticker at y 1530, red and white lower thirds, byte subtitles, a "विनम्र श्रद्धांजलि" card.
- Audio:
  - natural sound at 0.45 (helicopter at 0.22)
  - byte cleaned (highpass, light denoise, compressor) at full level
  - soft piano bed ducked under the byte
  - loudnorm -14 LUFS

| Time | Shot |
|---|---|
| 0–1.3 | Logo sting |
| 1.3–6.2 | Hook: photo of the bow before the portrait. Headline "अर्जुन मुंडा के आवास पहुंचे मुख्यमंत्री हेमंत सोरेन" |
| 6.2–18.6 | Helicopter in, landing; police at the gate; residence courtyard |
| 18.6–23.1 | CM and Kalpana Soren walk in, folded hands |
| 23.1–43.5 | Portrait; CM garlands and bows; Kalpana Soren; an MLA |
| 43.5–48.0 | With the family |
| 48.0–76.8 | CM byte; jump cuts covered with the portrait, the photo, the residence and the flowers |
| 76.8–82.8 | Convoy, folded hands from the car |
| 82.8–86.8 | "विनम्र श्रद्धांजलि / स्वर्गीय सायरा मुंडा" over the portrait |
| 86.8–90.2 | Logo end card |

**To verify with the user:**
- The helicopter footage is used as the CM's arrival.
- The byte subtitles are read from a noisy recording.
