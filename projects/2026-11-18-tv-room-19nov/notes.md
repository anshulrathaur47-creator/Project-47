# 19 November: crying in front of the TV

**Idea (user):** a 2D anime boy in a closed, dim room, a TV playing the user's clip, the boy sad and
crying because India lost the final on 19 Nov 2023. TV and boy always in the same frame.

**Input:** `raw-videos/VID_20261118_181136_080.mp4` (39.9 s, 720x724, 25 fps). Post-final footage
(press conference, players walking off) with a sad song; it carries a "SLIPEDITZ" watermark (another
editor's edit) and broadcast graphics, so copyright/mute risk on Instagram; credit the editor.

**Scene (one frame, slow 8% push-in over the clip):**
- Old CRT TV on a cabinet (left), the clip pillarboxed inside with scanlines, flicker, glass glare and bloom;
  the clip's average colour lights the room and puts a rim light on him.
- The boy on the floor against the sofa (right), hugging his knees in a blanket, looking at the TV;
  tears run from both eyes on a loop, blinks, sob waves, his head drops now and then, and he wipes his
  eyes at ~9 s, ~17 s, ~24 s and ~33 s.
- Rain on the window, a "NOV 19" calendar circled in red, rabbit-ear antenna.
- Audio: the clip's own audio, untouched apart from a fade at the end.

**Render:** `python3 make_tvroom.py`.

## v2 (feedback: "lighting, camera angle mein maja nahi aaya; character TV ki taraf dekhe, dono frame mein aaye")

`python3 make_tvroom_v2.py` (`--frames 60,300` for previews). Every shot has the boy looking at the TV
and both in frame:

| Time | Shot | What it shows |
|---|---|---|
| 0.0 to 7.8 | OTS | Behind his shoulder, the TV big straight ahead; a sliver of his cheek with a tear |
| 7.8 to 16.4 | Profile | Side view: huddled in a blanket on the floor, face turned to the TV at the left; wipes his eye at ~11.5 s, head drops at ~14 s |
| 16.4 to 23.1 | Close | Close profile of his crying face, the TV glowing out of focus at the left edge; wipe at ~20 s |
| 23.1 to 29.6 | OTS (mirror) | Over the other shoulder, slow push |
| 29.6 to 36.7 | Profile | Same side view; wipe at ~32.8 s |
| 36.7 to end | Close | Final close-up, head drops, fade out |

**Lighting:** the TV is the only light. A light map uses the clip's live colour with 1/(1+d²) falloff
and a dim ambient fill, plus a beam of haze from the screen, floating dust, and rim light on every edge
that faces the TV (face, hair, blanket). In the OTS shots his back is turned to the light, so he gets a
soft glow on the outline and a faint cool fill from behind the camera. Slow zoom moves inside each shot,
soft dips between shots, vignette and grain.
