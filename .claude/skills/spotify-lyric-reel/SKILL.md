---
name: spotify-lyric-reel
description: Make a music-player style lyric reel (the "Spotify theme" look). It has a now-playing card with cover art, title, artist, a heart, a progress bar and play controls; the song's lyrics scroll like a streaming app's lyrics view; the line being sung lights up word by word with a neon glow; and there are beat-reactive glowing spectrum bars, light leaks and floating particles. Colours come from the cover. Use when the user asks for a Spotify-style / music player / now-playing lyric reel, glowing lyrics, karaoke lyrics on a player screen, or "lyrical song Spotify theme mein".
---

# Spotify-style lyric reel

The project lives in `tools/spotify-lyric-reel/` (Remotion; `node_modules` links to `tools/remotion-starter/node_modules`).
It is a generic player look. Never add the Spotify logo or wordmark, or any other brand's logo.

## Steps

1. **Save the inputs.** Song in `assets/music/`, lyrics in `references/`, and the cover image in `assets/images/`.
   - With no cover, make one: a frame from a related reel, or an AI image (Figma AI costs credits, so ask first).
   - Or leave the cover out to get a plain gradient.
2. **Write a lyrics file,** one line per lyric line, in the user's correct spelling (Devanagari for Hindi).
   - Leave out audience shouts ("वाह") and music cues.
   - Optional exact timing per line: `12.4|15.0|text`.
3. **Prepare.** Whisper times each word, and the lyrics are aligned to it character by character, so the spelling shown is the user's:
   ```
   cd tools/spotify-lyric-reel
   python3 make_props.py --audio ../../assets/music/<song>.mp3 --lyrics <lines.txt> --title "<song>" --artist "<artist>" \
       --cover ../../assets/images/<cover>.jpg [--words ../../assets/music/<song>.words.json] [--start 30 --end 60] [--accent "#ff4f9a"]
   ```
   - `--words` reuses an existing Whisper file. Without it, the script transcribes with the local model.
   - `--start` and `--end` cut a 15–60 s clip of a long song.
   - It prints each line's timing. Check that the times look right.
   - If a section is missing, Whisper lost it: give those lines explicit times.
4. **Preview stills, then render:**
   ```
   npx remotion still src/index.ts SpotifyLyric out/f.png --frame=120 --props=public/props.json
   npx remotion render src/index.ts SpotifyLyric out/reel.mp4 --props=public/props.json --concurrency=4
   ```
   - The audio is already in the render.
   - Copy the result to `exports/YYYY-MM-DD_<name>_vN.mp4`.
   - Copy `public/props.json`, the cover and the lyrics into `projects/<date>-<name>/` so the reel can be re-made.

## Layout (1080x1920)

| Area | Position |
|---|---|
| Now-playing card | y 150–560 |
| Lyrics window | y 760–1460; the current line sits near y 880 |
| Spectrum bars | y 1480–1590, above Instagram's caption area |

What you can change:
- Colours: `bg` and `accent` in `props.json` (auto-picked from the cover; override with `--bg` / `--accent`).
- Font: `font` in `props.json` (default Noto Sans Devanagari).
- Effects: edit `src/SpotifyLyric.tsx`:
  - glow strength: the active words' `textShadow`
  - bar count: `bars`
  - particles: `Particles`
  - light leaks: the `radial-gradient` layer

## Related skills

- `lyric-video` (Video Studio): a 16:9 karaoke lyric video.
- `neon-orbit`, `neon-marquee` and `glow-cutout`: other glow looks.
- `music-video` for footage cut on the beat.
- `remotion-dev/template-music-visualization`, in `tools/external/`: waveform and spectrum components.
- `remotion-wrapped`, in `tools/external/`: Spotify Wrapped-style scenes.
- Hyperframes registry blocks: `spotify-card`, `light-leak`, `shimmer-sweep`, `grain-overlay`, `glitch`, `transitions-light`.
