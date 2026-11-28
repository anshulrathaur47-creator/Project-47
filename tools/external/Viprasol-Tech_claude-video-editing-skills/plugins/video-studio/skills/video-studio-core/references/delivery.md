# Delivery, captions, thumbnails and editor hand-off

Scripts: `deliver.py` (encodes, captions, chapters, thumbnails, post pack), `captions.py` (subtitle
and chapter rules, shared), `export_edl.py` (EDL / FCPXML / OTIO, ProRes 4444 overlays), `qc.py`
(automated QC). Run `deliver.py --list` for the live preset table.

```bash
python CORE/scripts/deliver.py W/plan.json --to youtube,reels,tiktok --out-dir W/deliver
python CORE/scripts/qc.py W/deliver/final_reels.mp4 --plan W/plan.json --platform reels --strict
python CORE/scripts/export_edl.py W --out-dir W/handoff          # only when the user wants to finish in an NLE
```

With a plan, `deliver.py` delivers `plan.outputFile` (final.mp4), takes words from `plan.words`
and makes thumbnails from the clean speaker video `plan.source` (no burned captions in the frame).

## Platform table

Figures marked * are third-party / contested; tell the user when a limit matters.

| preset | frame | max length | size limit | loudness | video | safe zone (keep text out of) |
|---|---|---|---|---|---|---|
| youtube | 1920x1080 | 12 h | 256 GB | -14 LUFS / -1 dBTP | H.264 High 8 Mb/s (12 at 48-60 fps), closed GOP fps/2, 2 B-frames, BT.709, faststart, AAC 384k 48k | 5% title-safe |
| youtube-4k | 3840x2160 | 12 h | 256 GB | -14 / -1 | 40 Mb/s (60 HFR); 4K gets VP9/AV1 on YouTube | 5% |
| youtube-hdr | note only | | | | needs a 10-bit Rec.2020 PQ/HLG grade; not produced | |
| shorts | 1080x1920 | 3 min | | -14 / -1 | 10 Mb/s | top 13%, bottom 22%, right 14% |
| reels | 1080x1920 | 3 min recommended (20 min*) | 4 GB* | -14 / -1 | 10 Mb/s | top 12%, bottom 18%, right 6% |
| tiktok | 1080x1920 | 10 min API (60 min upload) | 4 GB web | -14 / -1 | 10 Mb/s | top 6%, bottom 25%, right 14% |
| linkedin | 1080x1350 (4:5) | 10 min* | 5 GB* | -14 / -1 | 8 Mb/s | 5% |
| x | 1280x720 | 140 s free tier | 512 MB | -14 / -1 | 6 Mb/s | 5% |
| facebook | 1080x1350 | 240 min | 10 GB | -14 / -1 | 8 Mb/s | 5% |
| snapchat | 1080x1920 | 60 s* | | -14 / -1 | 8 Mb/s | top 10%, bottom 20% |
| pinterest | 1080x1920 | 60 s per page* | | -14 / -1 | 8 Mb/s | top 10%, bottom 25%, right 10% |
| whatsapp-status | 720x1280 | 60 s* | 16 MB* | -14 / -1 | bitrate auto-lowered to the size budget | as shorts |
| podcast-video | 1920x1080 | | | -16 / -1 | 6 Mb/s | 5% |
| web-h265 / web-av1 | source | | | -14 / -1 | x265 CRF 24 hvc1 / SVT-AV1 CRF 32 | |
| prores-422hq / prores-4444 | source | | | untouched mix | prores_ks HQ 10-bit / 4444 + alpha, PCM 24-bit | |
| dnxhr-hq | source | | | untouched | DNxHR HQ 8-bit 4:2:2, PCM 24-bit | |
| broadcast-xdcam | 1920x1080 25i TFF | | | EBU R128 -23 / -1 | MPEG-2 4:2:2 50 Mb/s MXF OP1a, 2x mono PCM 24-bit. "XDCAM-like": not AS-11/RDD9 conformance-checked | 5% graphics-safe |
| gif / webp | 480 wide | 6 s | | | previews | |
| audio-wav / podcast-mp3 | | | | untouched / -16 / -1 | 48k 24-bit / MP3 192k 44.1k | |

Other loudness targets: Netflix -27 LKFS dialogue-gated +-2, -2 dBTP; ATSC A/85 -24 LKFS; Spotify -14.

## What deliver.py does per output

- **Reframe** when the aspect changes. Face-centred crop if a track.json is passed (`--track`) or
  found in the work dir (`{fps, width?, height?, faces:[{id, frames:[{t,x,y,w,h,conf}]}], primary}`;
  x/y = box top-left in that video's pixels, or 0-1). The camera holds inside a dead zone and eases
  after the face (FFmpeg `sendcmd` driving `crop`). A track whose width/height differ from the input
  is ignored. Without a track: centre crop for mild changes (0.8-1.25x ratio), else blurred fill
  (the subject is never cut off). final.mp4 from a 9:16 plan going to YouTube = blurred pillarbox;
  if the user wants a true 16:9 cut, re-render the plan at 1920x1080 instead.
- **Loudness (two-pass)**: pass 1 measures the input (EBU R128). If plain gain reaches the target
  without breaking the true-peak ceiling it applies exact gain (what linear loudnorm does). If not,
  gain goes into a 4x-oversampled limiter (true-peak limiting), and an audio-only trial pass
  corrects the gain so the result lands within 0.3 LU. Dynamic loudnorm was rejected: it landed
  0.9-1.1 LU low on the test clip. Masters (ProRes, DNxHR, WAV) keep the mix untouched.
- **Size budget**: presets with a size limit lower the bitrate so the file fits (WhatsApp).
- **Too long**: warns; `--trim` cuts to the platform maximum.
- **Chapters** are embedded in MP4/MOV outputs (ffmetadata) when available.

## Subtitles

Sidecars `captions.srt`, `.vtt`, `.ttml` (IMSC1 text profile) are always written from the words.
Rules (Netflix/BBC practice), enforced by `captions.build_cues` and checked by `validate_cues`:

- max 42 characters per line, max 2 lines; one line when it fits
- max 20 characters per second (17 for children: `--kids`); counted with spaces
- on screen 5/6 s (0.833) minimum, 7 s maximum; 2-frame gap between cues
- a new cue at sentence ends and pauses > 0.7 s; long cues split at commas or before conjunctions
- line breaks after punctuation, before conjunctions/prepositions; never after an article or
  possessive (keep "the team" together), never between first and last name, pronoun and verb,
  auxiliary and verb; no orphan stubs; bottom-heavy when balanced
- Whisper's split tokens (`$10` `,000.`) are re-joined
- SCC is skipped (needs CEA-608 encoding, no free encoder). Say so if a broadcaster asks for it.

Burn-in: `--burn auto` (default) burns only where the preset recommends it (vertical/social feeds
autoplay muted) **and** the plan has no `captions` element (otherwise the edit already shows
creator captions). `--burn yes|no` overrides. Vertical burn-ins use 26 chars/line so the text
stays legible; placement sits above the platform's bottom safe zone. Engine: libass (`subtitles`
filter, ASS file sized to the output) when it works, else Pillow PNGs overlaid (`--burn-engine`).
FFmpeg `drawtext` is never used.

Upload sidecars rather than burning for YouTube (searchable, switchable, translatable).

## Chapters

Order: `--chapters "0:00 Intro; 1:20 Setup"`, then `plan["chapters"]` (`[{start, title}]`), then
automatic (sentence boundaries scored by pause length + keyword shift; titles are the first words
of the chapter's opening sentence). YouTube needs the first at 00:00, at least 3 chapters, each at
least 10 s; `chapters.txt` holds the description text and the report says why a list is invalid.
Videos under 30 s get no automatic chapters.

## Thumbnails

`thumb_1_left.png`, `thumb_2_right.png`, `thumb_3_bottom.png` (1280x720) and
`thumb_cover_1080x1920.png`. Frames are scored on sharpness (Laplacian variance), exposure,
contrast and face presence (track.json), spread out in time. The subject is located from the track,
else the matte, else a border-colour saliency guess, and the crop zooms (max 1.6x) so the face sits
clear of the headline. The headline is the first sentence of the transcript (number words as
digits, filler openers dropped, max 7 words) or `--headline`. Text colour is chosen for the highest
WCAG contrast against the area behind it (reported, aim >= 4.5:1), black stroke, digits in the
theme accent. With a matte, thumb 3 puts the headline behind the subject. LOOK at them before
handing over; YouTube wants <= 2 MB (PNG may be larger: convert to JPG q90 if needed).

## Post pack (`post.md`)

Three title options, a description (first two sentences + chapters), hashtags from transcript
keywords and the full caption text. All drafts come from the transcript only; never add claims,
numbers or promises that the speaker did not say.

## Editor hand-off

- `export_edl.py W` writes `W/handoff/<name>.edl` (CMX3600, reel = file stem, `* FROM CLIP NAME`,
  `* LOC` markers), `.fcpxml` (1.10, asset-clips on the spine, markers) and `.otio`
  (OpenTimelineIO JSON; via the library if installed, else hand-written to the same schema).
  Record starts at 01:00:00:00 (`--record-start`). Drop-frame is used for 29.97/59.94.
  Markers = plan elements (`type: text`) and speaker zooms. Source = `W/source.mp4`.
- Overlays as ProRes 4444 with alpha: `render.py plan.json --keep`, then
  `export_edl.py --encode-alpha "W/render/front/%05d.png" --fps 30 --out front_4444.mov`
  (or `overlay_to_prores(pattern, fps, out)`). FFmpeg reports these as yuva444p12le on decode;
  that is normal for ProRes 4444.
- Hand over: EDL/FCPXML/OTIO + source.mp4 + overlay .mov(s) + captions.srt + the mix (audio-wav).

## Report

`deliver_report.json/.md`: per output file, size, frame, fps, codec, measured LUFS/dBTP vs
target, loudness mode, reframe mode, warnings; caption/chapter validation; thumbnail picks.
Always follow with `qc.py` on the files you will hand over.
