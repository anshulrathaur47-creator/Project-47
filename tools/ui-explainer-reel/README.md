# ui-explainer-reel

Remotion engine for faceless tech/AI explainer reels in the `style-ui-explainer` look (`.claude/skills/style-ui-explainer/`). The reel is:
- a voice-over over animated UI cards
- Hinglish word-by-word captions above and below the card, with key words in a boxed italic serif
- a dashed-arrow camera move between cards (no hard cuts)
- a cream or black-and-green theme
- a "Comment WORD" CTA

## Make a reel

1. Make `projects/<date>-<name>/script.json`. See `projects/2026-11-28-ui-explainer-demo/script.json`:
   - `theme`: `cream` or `dark`. You can also set `accent` and `accent2` hex colours.
   - `handle` and an optional `terms` note.
   - `vo`: your own voice-over file. Without it, a free Kokoro draft voice (`voice`, `speed`) is made from the `hi` lines.
   - `lines`: one per spoken sentence.
     - `hi`: Devanagari, for the voice.
     - `roman`: Hinglish caption text. `*Words*` in stars become boxed key words.
     - `scene` (optional): starts a new card.
     - `tag` (optional): adds a step pill above the card.
     - `mark` (optional): sets that card field to this line's start time, e.g. `"mark": "typeAt"` on a chat card.
2. Render the whole reel:
   `python3 tools/ui-explainer-reel/make_reel.py projects/<date>-<name>/script.json --out exports/<date>_<name>_v1.mp4`
   - To preview a few frames first, add `--frames 45,300,800`. The stills go to `<project>/stills/`.
3. The script then does the rest:
   - writes `spec.json`
   - copies the VO into `public/reel/`
   - renders with Remotion (about 1.5 min per 30 s)
   - normalises loudness to -14 LUFS

With your own VO, line times come from Whisper (`tools/transcribe.py`), split between the script lines by word count. Check the stills and nudge the line text if a caption lands early or late.

## Card types (`scene.type`)

| type | what it shows | fields |
|---|---|---|
| `hero` | app window: phone preview, a stat with a drawing line, checks | `title subtitle badge window phone{tag,title,sub} stat{value,label} checks[]` |
| `compare` | old-way rows struck out, the new way lands, a stamp | `title bad[{t,s}] good{t,s,chip} stamp` |
| `chat` | files dropped in, a prompt typed and sent, a reply | `title files[{name,size,kind}] prompt reply typeAt` |
| `terminal` | a command typed, log lines tick, "installed" pills | `title cmd logs[] pills[{t,s}]` |
| `checklist` | document rows tick one by one | `title icon items[] footer` |
| `download` | progress bar, Ready ✓, folder of files | `file size button folder[]` |
| `price` | price struck out, the new price pops | `plan price newPrice per features[] button` |
| `steps` | numbered steps light up, with an optional timer ring | `title steps[{t,s}] timer` |
| `cta` | keyword button, comment box typing it, auto-reply card | `keyword handle reply{title,files[]}` |
| `big` | one huge serif statement | `kicker big sub` |

## Sound

SFX are timed by the cards themselves:
- whoosh on each camera move
- click on cursor clicks
- typing under typed text
- pop on list items
- ding on Ready and on the CTA

The music bed is `public/music/bed.mp3` (a code-made lofi bed, CC0) at `music` volume (default 0.07). All sounds come from `assets/` and are CC0.

## Files

- `src/UIExplainer.tsx`: composition, camera, captions, arrows, audio.
- `src/cards.tsx`: card components and their SFX cues.
- `src/ui.tsx`: themes, fonts, primitives (panels, chips, checks, cursor).
- `make_reel.py`: script.json → spec.json → render → export.
- `tts.py`: Kokoro draft voice (run with the animation kit's Python).
- Fonts in `public/fonts` are OFL: Poppins, Playfair Display, JetBrains Mono. See `assets/fonts/CREDITS.md`.

`node_modules` is a symlink to `../three-starter/node_modules` (git-ignored). Run `bash tools/setup.sh` in a fresh container.
