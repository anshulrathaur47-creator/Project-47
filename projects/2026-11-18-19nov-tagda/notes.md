# 19 November 2023: "tagda" cut

**Ask (user):** "Lo ish clip se 19 nov ke liye bana do kuch tagda sa."

**Input:** `raw-videos/VID_20261118_235405_536.mp4`. It is a 39.8 s landscape fan edit (964x720, 28.5 fps) of the
final day, set to a sad song at ~97.5 bpm. It has a "19 NOVEMBER 2023 💔" title burned into the centre and a
"kohliii_driveee_18" watermark. The content runs in this order:
- crowd and gate, toss
- Rohit and Gill batting
- Head's diving catch (17.6 to 18.4 s)
- Rohit walking off, then Kohli out and walking off (22.7 to 24.4 s)
- Head's century (24.5 s), scoreboard, Australian dugout, the winning runs and the team rush (30.7 s)
- Kohli and Rohit close-ups (34 to 38 s), then the trophy (38.3 s)

**Lyrics:** Whisper (hi, en, auto, vocal band) could not make out the words, so no lyrics are on screen
(wrong lyrics would be worse). If the user sends the song name or lyrics, glowing lyrics can be added.

**Idea:** The fan lives the final with the clip. The clip plays in a glowing panel at the top. Below it,
our anime fan (India jersey, face paint, flag) watches live in his room at night, lit only by the screen.

| Time | Clip | Fan | Camera on him |
|---|---|---|---|
| 0 to 2.1 | aerial crowd (full screen) | | |
| 2.1 to 8.2 | gate, fans, toss | waves the flag, jumps and claps on the beat | wide, medium, low angle |
| 8.2 to 16.2 | Rohit batting | shouts, jumps, chants on the beat | close, wide, dutch |
| 16.2 to 17.7 | Head runs back | hands together, praying | slow push-in |
| 17.7 | catch lands | frame freezes, flash, shake, the panel cracks | |
| 18.0 to 19.3 | | shock, hands on head; a heart cracks in two; speed lines | full-screen close-up |
| 19.3 to 22.7 | Rohit walks off | sits down, stunned | wide |
| 22.7 | Kohli out | second crack; shakes his head, "nahi" | dutch close-up |
| 24.8 | Head century | hides his face | medium |
| 26.6 | | blank stare, eyes fill up | close |
| 30.7 | Australia win | red flash, the panel border turns red, a heart shatters, the flag falls, he breaks down | |
| 32 to 34 | | crying, wipes his eyes | pull back |
| 34 to 38.3 | full-screen match cuts | Kohli stares; Rohit wipes his eyes, and so does he; Kohli looks up, and so does he | |
| 38.3 to end | trophy on the panel | the TV switches off (line, then dot); he sits in the dark; fade out | |

**Look:**
- The room light takes the clip's live colour (blue crowds early, Australian yellow later).
- Moonlight rim from the window, twinkling fairy lights.
- Tricolour panel border that pulses on the beat, and tricolour confetti on beats in the cheering part.
- After the catch the colour drains a little; after the loss it drains more.

**Render:** `python3 make_tagda.py --workers 4` (`--frames 60,300` for previews). It uses the character rig
from `../2026-11-16-remember-19-nov/make_19nov.py`. Audio: the clip's own track, untouched apart from a
0.6 s fade at the end.

**Rights:** the clip is someone else's edit (watermark) of broadcast footage, so there is copyright and mute
risk on Instagram. Credit the editor.
