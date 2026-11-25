# Pagan lyric alignment (word timings)

Generated 2026-11-20 with `scripts/align-lyrics/` (Demucs `htdemucs` vocals, then torchaudio
`MMS_FA` forced alignment against the hand-stamped `.lrc`). It ran locally on the cachyos CPU;
no audio was uploaded anywhere. The Seventh Shadow albums were done in a separate session with
the same JSON shape.

| Release | Song | Rating | Lines to check |
|---|---|---|---|
| Acolytes | Acolytes | high | 2 of 50 |
| Acolytes | Sign of the Heathen Cult | high | 6 of 32 |
| Acolytes | Averse to His Minions | high | 5 of 43 |
| Heathen Upheaval | The Longing and the Ancient Ones | high | 2 of 30 |
| Heathen Upheaval | Shamanic Flames | medium | 4 of 22 |
| Heathen Upheaval | Marching of the Hordes | high | 1 of 21 |
| Heathen Upheaval | The Ascending | medium | 6 of 37 |
| Heathen Upheaval | Bitter Gates of Grief | medium | 8 of 39 |

Files, next to each hand `.lrc` (which is left as it was):

- Acolytes: on `main`, `public/Pagan/Acolytes/<name>.aligned.lrc` and `<name>.words.json`.
- Heathen Upheaval: on branch `pagan` (where its `.lrc` files and project live),
  `public/Pagan/HeathenUpheaval/<name>.aligned.lrc` and `<name>.words.json`.
  Tracks 01 and 07 have no lyrics.

All lyrics are English (Latin in places); no Turkish lines have audio yet. MMS_FA is
multilingual, so Turkish would align the same way once a recording exists.

## How to read the ratings

The CTC score in the JSON (`confidence`, word `score`) runs 0.25–0.5 on these screams even
where the timing is right, so the rating comes from a cross-check instead: every line is
aligned twice, alone in its hand-stamped window and together with its neighbours in a wider
one. A word agrees when both put its start within 0.35 s. A line needs checking when under
60% of its words agree, or when two of its words are more than 4 s apart (the line got
smeared across an instrumental passage; both passes can agree on that). Rating = share of
words in lines that need no check: 85%+ high, 65%+ medium.

What that means in practice: the hand stamps are good (median shift of aligned line starts
0.05–0.27 s), so the line LRCs barely change. Word timings in unflagged lines are usable for
word-by-word reveal. Flagged lines keep their hand stamp as the line start in
`.aligned.lrc`; their word times are the aligner's best guess and should be fixed by hand
(or the video can fall back to line-level reveal for those lines). Single-word shouted
lines ("Acolytes!", "Secrets", "Desire") disagree most often: one word gives the aligner
nothing to lock onto in distorted vocals.

## Per song

### Acolytes — high

50 lines, 149 words. Words in clean lines: 99%; word agreement between passes: 96%; unanchored pass within 0.75 s of the stamps: 94%. Line starts moved off the hand stamp: 46 of 50.

| Line | Stamp | Text | Why |
|---|---|---|---|
| 36 | 03:01.27 | Acolytes! | passes agree on 0% of words |
| 39 | 03:07.79 | Nescience | passes agree on 0% of words |

### Sign of the Heathen Cult — high

32 lines, 150 words. Words in clean lines: 85%; word agreement between passes: 83%; unanchored pass within 0.75 s of the stamps: 66%. Line starts moved off the hand stamp: 26 of 32.

| Line | Stamp | Text | Why |
|---|---|---|---|
| 1 | 00:25.06 | Sword in hand | passes agree on 33% of words |
| 2 | 00:26.57 | Storming through the land | passes agree on 50% of words |
| 5 | 00:32.63 | Temples ablaze | passes agree on 0% of words |
| 18 | 01:15.71 | The clergy in pain | passes agree on 25% of words |
| 23 | 01:26.33 | Vengeance for the gods | passes agree on 50% of words |
| 26 | 01:32.64 | The gleaming justice of heathendom | passes agree on 40% of words |

### Averse to His Minions — high

43 lines, 151 words. Words in clean lines: 87%; word agreement between passes: 93%; unanchored pass within 0.75 s of the stamps: 81%. Line starts moved off the hand stamp: 36 of 43.

| Line | Stamp | Text | Why |
|---|---|---|---|
| 12 | 01:41.79 | That petrifies the soul | 25 s gap between words |
| 24 | 03:03.64 | Crescent ! Arise ! | passes agree on 50% of words |
| 38 | 04:11.22 | Banners up high | passes agree on 0% of words |
| 39 | 04:14.26 | Time of sword and axe is nigh | 13 s gap between words |
| 40 | 05:47.72 | Glorify the horned one | passes agree on 0% of words |

### The Longing and the Ancient Ones — high

30 lines, 201 words. Words in clean lines: 93%; word agreement between passes: 92%; unanchored pass within 0.75 s of the stamps: 83%. Line starts moved off the hand stamp: 27 of 30.

| Line | Stamp | Text | Why |
|---|---|---|---|
| 1 | 00:46.58 | Stand I towards the pantheon of our deities | 5 s gap between words |
| 22 | 03:22.37 | Aradia, my lady of the Moon | passes agree on 50% of words |

### Shamanic Flames — medium

22 lines, 101 words. Words in clean lines: 82%; word agreement between passes: 97%; unanchored pass within 0.75 s of the stamps: 73%. Line starts moved off the hand stamp: 15 of 22.

| Line | Stamp | Text | Why |
|---|---|---|---|
| 2 | 01:30.81 | To the underworld, to the upperworld | 12 s gap between words |
| 8 | 02:34.20 | Each beat to the heart, each beat to the soul | 32 s gap between words |
| 9 | 04:25.68 | Secrets | passes agree on 0% of words |
| 13 | 05:16.08 | Desire | passes agree on 0% of words |

### Marching of the Hordes — high

21 lines, 126 words. Words in clean lines: 96%; word agreement between passes: 94%; unanchored pass within 0.75 s of the stamps: 86%. Line starts moved off the hand stamp: 20 of 21.

| Line | Stamp | Text | Why |
|---|---|---|---|
| 17 | 01:22.38 | Ahhh... Marching of the Hordes... | passes agree on 40% of words |

### The Ascending — medium

37 lines, 175 words. Words in clean lines: 82%; word agreement between passes: 88%; unanchored pass within 0.75 s of the stamps: 76%. Line starts moved off the hand stamp: 30 of 37.

| Line | Stamp | Text | Why |
|---|---|---|---|
| 9 | 02:15.58 | Ascend the throne of my demise | passes agree on 0% of words |
| 18 | 02:54.07 | for the glory of the sorrowful souls | 11 s gap between words |
| 19 | 04:02.20 | I look upon to the eternal sky | passes agree on 57% of words |
| 21 | 04:08.25 | Eyes scattered instead of | passes agree on 25% of words |
| 24 | 04:21.37 | they start to shine | passes agree on 50% of words |
| 27 | 04:29.65 | and still do I | passes agree on 50% of words |

### Bitter Gates of Grief — medium

39 lines, 205 words. Words in clean lines: 84%; word agreement between passes: 84%; unanchored pass within 0.75 s of the stamps: 85%. Line starts moved off the hand stamp: 29 of 39.

| Line | Stamp | Text | Why |
|---|---|---|---|
| 1 | 00:56.21 | Restrained am I | passes agree on 33% of words |
| 9 | 01:23.63 | A realm, | passes agree on 0% of words |
| 13 | 02:44.21 | As the night crawls in, | passes agree on 0% of words |
| 14 | 02:46.07 | sets loose the beasts within | passes agree on 40% of words |
| 19 | 03:13.90 | In the vaguest corners | passes agree on 50% of words |
| 30 | 04:04.69 | Through the endless and ruthless chasm of time | passes agree on 0% of words |
| 31 | 04:08.74 | I dream… | passes agree on 0% of words; 23 s gap between words |
| 32 | 05:05.03 | All was hidden | passes agree on 0% of words |
