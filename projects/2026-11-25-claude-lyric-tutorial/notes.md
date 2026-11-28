# Tutorial reel: "Claude se Spotify-theme lyrical reel kaise banaye"

- **Voice-over:** Kokoro TTS, Hindi male voice `hm_omega`, speed 1.12.
  - Script: `script_hi.txt`. "Claude" is written क्लौड so it is said "klod".
  - Lines are timed in `vo_lines.json`.
- **Captions:** Hinglish (`script_roman.txt`), 3 words at a time in a white box, with the spoken word in pink, like the reference reel.
  - Timed from Whisper on `vo.wav`, aligned with `make_props.align`.
- **Build:** composition `Tutorial` in `tools/spotify-lyric-reel/src/Tutorial.tsx`. It embeds the real LyricCard and SpotifyLyric demos.

| Time | Scene |
|---|---|
| 0–4.4 | Hook: pink card playing, "Claude se banao" |
| 4.4–6.8 | Card shrinks into a phone: "Bina kisi editing app ke" |
| 6.8–10.3 | Chat: song file + lyrics + "Spotify theme mein pink lyrical reel bana do" |
| 10.3–15.8 | Waveform with a playhead, and words landing with timestamps |
| 15.8–19.7 | Two phones: Pink Card / Music Player, each lit on its word |
| 19.7–23.7 | Player close-up: glow + beat bars |
| 23.7–26.2 | Terminal: command typed, progress bar, "reel ready" |
| 26.2–31 | CTA: Comment "LYRICS", Follow → Following |

- **Audio:** VO, the demo song at about 0.2 under it, whooshes on cuts, loudnorm -14 LUFS.
- **Render:** `npx remotion render src/index.ts Tutorial out/tutorial.mp4`.

## v2: ElevenLabs voice-over
- The user generated the VO in ElevenLabs (Eleven v4, voice "Rohit - Calm Hindi Storyteller"): `vo_eleven.mp3`, 27.1 s.
- ElevenLabs added "बनाने" to the last line, so the script and captions were updated to match.
- Captions are re-timed from Whisper on that file (`captions_eleven.json`).
- Scenes now follow the VO automatically: one scene per VO line, from the caption start times. The "Pink Card" and "Music Player" highlights use the times of the words "pink" and "music".
- Export: `exports/2026-11-25_claude-lyric-tutorial_v2.mp4`, 28.1 s, -14.7 LUFS.
