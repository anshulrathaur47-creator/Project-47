# QC checklist (finishing / post supervisor)

`qc.py VIDEO --plan PLAN --platform NAME [--strict]` automates the items marked (auto). Do the rest
by eye and ear on a contact sheet and one full watch-down with headphones. FAIL = fix before
delivery. WARN = look at it and decide; say what you decided.

## Picture

- [ ] (auto) Resolution, frame rate and duration match the plan (duration +-1 frame).
- [ ] (auto) Codec / profile / pix_fmt match the platform (H.264 High, yuv420p for social).
- [ ] (auto) BT.709 colour tags present (untagged files can shift colour in some players).
- [ ] (auto) No black frames except intended fades; no one-frame flash frames (bad edit points).
- [ ] (auto) Photosensitivity: fewer than 3 flashes in any 1 s (Netflix/Harding). The check uses
      average luma; also look for small bright flashes and saturated red flashing by eye.
- [ ] (auto) Legal levels: signalstats BRNG under 1% of frames (FAIL for broadcast, WARN for web).
- [ ] Nothing cut off by the reframe; the face is not cropped; no jitter in face-follow crops.
- [ ] No compression banding in gradients or skies; grain not smeared into blocks.
- [ ] Graphics: spelling, names, numbers checked against the transcript or the user's notes.

## Sound

- [ ] (auto) Audio present, 48 kHz.
- [ ] (auto) Integrated loudness within +-1 LU of the platform target; true peak at or under the
      ceiling (-1 dBTP social/podcast, -2 Netflix); LRA sensible (<= 11 LU web, 5-8 for phones).
- [ ] (auto) No silences > 2 s unless intended.
- [ ] (auto) A/V stream timing (start offset <= 1 frame, durations within 100 ms). Lip-sync itself
      is not measured: watch a few hard consonants (p, b, t) at the start, middle and end.
- [ ] No clicks at cut points, no music clipping, ducking audible but not pumping.

## Text, captions, overlays

- [ ] (auto) Broadcast captions: <= 42 chars/line, <= 2 lines, <= 20 cps (17 kids), 0.833-7 s,
      2-frame gaps. Sidecar files parse back cleanly.
- [ ] (auto) Creator captions (plan `captions`): chunk cps, chunks under 0.3 s, chars per chunk.
- [ ] (auto) Overlays on screen >= 0.6 s.
- [ ] (auto) 9:16: overlays inside 10%-85% of the height, box clear of the right 12% (box-based:
      confirm on a still), max 2 overlays at once.
- [ ] Caption words match the audio (names, numbers, jargon); no captions over faces.

## Container and delivery

- [ ] (auto) MP4 faststart (moov before mdat). (auto) Keyframe interval reported (YouTube: closed
      GOP of half the frame rate; deliver.py makes 15-frame closed GOPs at 30 fps).
- [ ] (auto) File size and length inside the platform limits.
- [ ] Chapters valid (00:00 first, >= 3, each >= 10 s) if used. Thumbnail readable at 160 px wide.
- [ ] File names, a delivery report and the QC report go to the user with the files.

## Known limits of the automation

Average-luma flash detection, stream-timing A/V sync, box-based safe zones and the absence of a
dialogue-gated loudness measure (Netflix) are heuristics. They catch the common mistakes; they do
not replace a watch-down.
