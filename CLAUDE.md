# AI Video Editing Workspace

This repo is the user's workspace for making short-form videos (Instagram Reels / Shorts) with Claude.
Talk to the user in simple Hinglish (Hindi in Roman script mixed with English), matching how they write.

## Where files live

| Folder | What's in it | Rule |
|---|---|---|
| `raw-videos/` | Original footage | Read-only. Never edit or overwrite. |
| `references/` | Scripts, lyrics, transcripts, storyboards, briefs | Lyrics/timestamps for a song go here. |
| `inspirations/` | Reels and screenshots the user likes | Borrow pacing, transitions, colour, type. |
| `brand-kit/` | Logo, watermark, colours, handle, CTA, intro/outro | Apply to every export unless told otherwise. |
| `assets/music/` | Songs and background tracks | |
| `assets/sfx/` | Sound effects | |
| `assets/images/` | Backgrounds, characters, overlays, AI images | |
| `assets/fonts/` | Font files | |
| `skills/` | Reusable editing recipes and scripts | Save a recipe when a style works well. |
| `projects/<name>/` | One folder per video: script, previews, `notes.md` | All work-in-progress lives here. |
| `exports/` | Final ready-to-post videos | Name: `YYYY-MM-DD_<project>_vN.mp4`. |
| `reel/` | Earlier work, made before this layout existed (aviation explainer, lyric reel, animated story reel and their generator scripts) | Leave in place unless the user asks to move it into `projects/`. |

When the user uploads a file, save it into the matching folder above before using it.

## How the user likes videos edited

Learned from past feedback. Follow these unless the user says otherwise.

- **Format:** vertical 9:16, 1080×1920, 30 fps, H.264 + AAC `.mp4`, short (one song clip, ~15–60 s).
- **Story first:** build a real story from the song's lyrics and meaning, with emotions. Not just text over a static picture.
- **Character that acts:** anime-style character with expressions (crying, laughing, smirking, eyes closed), doing things.
- **Movement, not standing still:** the character should walk, move and travel through different locations, with a carefree, fun (*masti*) vibe.
- **Camera work:** different camera angles per line (wide, close-up, low angle, dutch tilt, feet shot), with cuts and transitions (whip-pan, flash, dip to black). Avoid one static framing.
- **Visual signs for words:** when a lyric names something, show it (e.g. "दिल" → a heart, "दर्द" → a breaking heart, "देख" → an eye, "ख्वाब" → a dream bubble).
- **Text on screen:** for song reels, show **only the song's lyrics**, music-video style (Devanagari, word by word, lower third, key words coloured), clear of the face and of Instagram's bottom caption area. No other captions or hooks unless asked.
- **Audio:** use the user's track as-is. Sync cuts, steps and signs to the beat and to the lyric timing.

## Tools and how to render

- **Start of every session:** run `bash tools/setup.sh`. It reinstalls whatever the fresh container is missing and prints a ✅/❌ checklist. See `tools/README.md` for each tool.
- Installed toolset: FFmpeg, yt-dlp (+ Deno), Whisper (`tools/transcribe.py`, faster-whisper small model), Remotion (`tools/remotion-starter/`), Hyperframes (`tools/hyperframes-starter/`), and `tools/sfx.py` for SFX/music from Openverse and Freesound. Official Remotion and Hyperframes skills are in `.claude/skills/`.
- **Use Whisper for lyric timing:** run `python3 tools/transcribe.py <song> --lang hi --no-vad` and sync lyrics, cuts and signs to the `.words.json` timings instead of guessing.
- When downloading SFX/music, keep the credit lines in `assets/*/CREDITS.md` and remind the user about attribution for CC-BY sounds.
- Blocked by this environment's network policy (until the user allows them): api.openverse.org, freesound.org, youtube.com, huggingface.co, cdn.jsdelivr.net.
- Hindi text needs Devanagari fonts with proper text shaping. If they are missing, install them with `apt-get install -y fonts-noto-core` and use `ImageFont.Layout.RAQM`.
- Scripted renders: draw frames with Pillow and pipe them into ffmpeg (see `reel/make_story_reel.py` for the full character, camera, lyrics and signs pipeline). Render long jobs in the background and check preview frames (`--frames`) before a full render.
- Keep files under GitHub's 100 MB limit (use CRF ~20 with a `-maxrate` cap).
- **Paid tools need permission first:** Figma AI image generation spends the user's Figma credits, and Weave (AI video) spends Weave credits and isn't linked yet. Ask before every paid run.
- The container can't download from figma.com directly. Get AI images through the Figma connector's screenshot tool instead.

## Skills

- `watch` (`.claude/skills/watch/`): study a video (link or file) frame by frame and save its editing style as a new `style-<name>` skill. Use when the user says "watch", "learn this video" or "copy this style". Downloads from links need the site to be reachable (YouTube and Instagram are blocked here right now), so ask for the video file instead. Use `--lang hi` for Hindi.
- Remotion and Hyperframes skills from their official repos are also in `.claude/skills/`.

## Learned styles

(none yet: each `watch` run adds a line here)

## Workflow

1. Save inputs into the right folders (audio → `assets/music/`, lyrics → `references/`).
2. Create `projects/<date>-<name>/` with a `notes.md` (idea, scene plan, decisions).
3. Render preview frames, check them visually, fix issues, then render the full video.
4. Copy the final video to `exports/` and send it to the user.
5. Commit and push to the working branch when done.
6. Lyric timing is usually estimated from the audio. Tell the user so they can ask for adjustments.
