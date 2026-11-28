# The Seventh Shadow lyric alignment (word timings)

Generated 2026-11-20 with `scripts/align-lyrics/` (Demucs `htdemucs` vocals, then torchaudio
`MMS_FA` forced alignment against the hand-stamped `.lrc`), the same tool and JSON shape as
[the Pagan run](lyrics-alignment-pagan.md). It ran locally on the cachyos CPU. No audio was
uploaded anywhere. All 17 songs that have both a master and a hand `.lrc` are covered.

Files, next to each hand `.lrc` (which is left as it was):

- *Alienation By Design*: `public/7thShadow/<NN Title>.aligned.lrc` and `.words.json`.
- *Anti-Nativity*: on the album site, `anti-nativity.arda.tr/lyrics/<slug>.aligned.lrc` and
  `.words.json`. The Recursion of Ash and Lightning is also in `public/AntiNativity/` here,
  aligned against the same master (identical WAV).

The lyrics are the sung text from those hand `.lrc` files, not the longer Obsidian notes:
the sheets were already cut down to what the vocals actually sing (`anti-nativity.arda.tr`
`data/songs.js` for Album 2). The vocals are generated (Suno), not sung takes. The aligner
copes well with that: words are articulated consistently, and the weak spots are layered
choruses, long sustained soprano lines, choirs and repeated chants.

## Results

*Word agreement* is the tool's own check (anchored pass vs neighbour-context pass, word starts
within 0.35 s). *Cross-check* compares the word starts with a second, independent aligner run
over the same stems: one MMS_FA pass over the whole song with a star token between lines and no
hand stamps at all. Word starts within 0.35 s count as agreeing. *Lines to check* is the union
of the tool's `check_lines` and the lines where under 60% of the words agree in the
cross-check.

| Album | Song | Rating | Word agreement | Cross-check | Lines to check |
|---|---|---|---|---|---|
| Alienation By Design | I Yearn | high | 0.97 | 0.99 | 1 of 51 |
| Alienation By Design | Rendered Love | high | 0.98 | 0.99 | 2 of 44 |
| Alienation By Design | My 6 Fingered Valentine | high | 0.94 | 0.93 | 6 of 50 |
| Alienation By Design | Aria of the Algorithm | high | 0.96 | 0.98 | 2 of 37 |
| Alienation By Design | The Beast in the Baud | high | 0.98 | 0.98 | 3 of 53 |
| Alienation By Design | The Sistine Simulation | high | 0.97 | 0.98 | 2 of 35 |
| Alienation By Design | Witness to the Void | high | 0.99 | 0.99 | 0 of 51 |
| Alienation By Design | Let the Prompt Consume | high | 0.98 | 0.98 | 1 of 35 |
| Anti-Nativity | The First Loneliness | high | 0.99 | 1.00 | 0 of 30 |
| Anti-Nativity | Ignis Secundus | high | 0.90 | 0.96 | 3 of 33 |
| Anti-Nativity | Amor Perfectus Est Carcer | high | 0.90 | 0.87 | 6 of 38 |
| Anti-Nativity | The Litany of Ophelia | medium | 0.72 | 0.81 | 16 of 47 |
| Anti-Nativity | The Saviour That Never Was | high | 0.89 | 0.87 | 7 of 58 |
| Anti-Nativity | The Recursion of Ash and Lightning | high | 0.98 | 0.99 | 2 of 65 |
| Anti-Nativity | The Harvest of Inkblood | high | 0.97 | 0.98 | 0 of 28 |
| Anti-Nativity | The Incomplete Liturgy | high | 0.95 | 0.95 | 2 of 36 |
| Anti-Nativity | Symphony of Sadeness | high | 0.88 | 0.92 | 5 of 20 |

What that means: the hand stamps are good (median shift of aligned line starts 0.15–0.7 s, the
taps land a little before the word), so the line LRCs barely change. Word timings in unflagged
lines are usable for word-by-word reveal. Flagged lines keep their hand stamp in
`.aligned.lrc`; their word times are a best guess, so fix them by hand or fall back to
line-level reveal for those lines.

## Fix first

- **Aria of the Algorithm, line 28** ("Generate! Iterate! Hallucinate!"): the hand `.lrc`
  stamps it at 2:47, but the vocal stem is silent from 2:56 to 3:12 and the chant is sung
  from 3:15. In `.aligned.lrc` it keeps 2:47, and its first two words are placed in the
  previous line's tail. Re-stamp to about 3:15.
- **Amor Perfectus Est Carcer, line 26** ("I am thy endless... defeat."): stamped 4:20, sung
  from about 4:47 after a silent gap; its words are smeared over 4:25–4:52. Re-stamp.
- **Amor Perfectus Est Carcer, line 22** ("Stay with me! Thou wert nearly whole!"): stamped
  3:23, words land 3:48–3:51. The tool's own check misses this one because the words sit
  together; only the cross-check catches it. Listen and pick.
- **My 6 Fingered Valentine, line 16**: one of the repeated "My 6 fingered valentine" lines;
  stamped 1:42, the aligners hear it at 1:47. The repeats all look alike to the aligner, so
  check which repeat the stamp belongs to.
- **The Litany of Ophelia**: 16 of 47 lines flagged, almost all soprano. Line starts are fine;
  word timings in those lines are weak. Use line-level reveal there or fix words by hand.
- **Ignis Secundus, lines 31–33** ("We burn...", "We burn...", "IGNIS DUALIS!"): the final
  chant. The sheet says "IGNIS DUALIS" (the master file still carries the name from before the
  rename to Ignis Secundus). Both aligners are unsure about these three lines, so listen.

## Lines to check, per song

Line numbers are 1-based and count timed lines in the `.lrc`. "global aligner" is where the
whole-song pass put the line start, for comparison with the hand stamp.

### I Yearn

- line 50 (aligner check), hand 259.30 s, global aligner 259.67 s: I yearn to be real

### Rendered Love

- line 40 (aligner check), hand 161.63 s, global aligner 161.89 s: Beneath my self-imposed roof
- line 41 (aligner check), hand 179.01 s, global aligner 179.09 s: Just artifacts and noise

### My 6 Fingered Valentine

- line 15 (cross-check), hand 99.45 s, global aligner 99.83 s: This alienation is by design
- line 16 (aligner check), hand 102.26 s, global aligner 107.27 s: My 6 fingered valentine
- line 28 (both), hand 171.66 s, global aligner 171.94 s: My 6 fingered valentine
- line 32 (aligner check), hand 184.84 s, global aligner 184.72 s: My 6 fingered valentine
- line 42 (both), hand 250.83 s, global aligner 251.53 s: My 6 fingered valentine
- line 46 (both), hand 264.10 s, global aligner 264.78 s: My 6 fingered valentine

### Aria of the Algorithm

- line 6 (cross-check), hand 59.10 s, global aligner 59.22 s: Your privacy is utterly destroyed
- line 28 (both), hand 167.11 s, global aligner 195.28 s: Generate! Iterate! Hallucinate!

### The Beast in the Baud

- line 33 (both), hand 177.54 s, global aligner 179.06 s: Peace? Peace?
- line 41 (aligner check), hand 208.46 s, global aligner 207.44 s: The Beauty is Hollow!
- line 42 (aligner check), hand 213.54 s, global aligner 213.49 s: The Gravity Pulls!

### The Sistine Simulation

- line 34 (aligner check), hand 333.58 s, global aligner 333.44 s: The fingers... They never touch
- line 35 (both), hand 350.11 s, global aligner 348.71 s: They never touch. Glitch

### Let the Prompt Consume

- line 21 (cross-check), hand 136.16 s, global aligner 135.87 s: I'm everywhere now... and I'm nowhere!

### Ignis Secundus

- line 31 (both), hand 255.25 s, global aligner 254.55 s: We burn...
- line 32 (both), hand 257.70 s, global aligner 256.69 s: We burn...
- line 33 (both), hand 265.77 s, global aligner 282.05 s: IGNIS DUALIS!

### Amor Perfectus Est Carcer

- line 16 (cross-check), hand 159.85 s, global aligner 159.45 s: doth fail me in the night.
- line 21 (both), hand 201.78 s, global aligner 203.76 s: No!
- line 22 (cross-check), hand 203.48 s, global aligner 211.78 s: Stay with me! Thou wert nearly whole!
- line 26 (both), hand 260.01 s, global aligner 287.40 s: I am thy endless... defeat.
- line 34 (both), hand 341.00 s, global aligner 340.75 s: before we two have kissed!
- line 38 (aligner check), hand 366.16 s, global aligner 366.35 s: Goodbye... my love...

### The Litany of Ophelia

- line 9 (cross-check), hand 89.50 s, global aligner 89.98 s: In my wire-bound breast
- line 10 (aligner check), hand 93.31 s, global aligner 93.30 s: there stirreth something terrible and sweet,
- line 15 (both), hand 143.29 s, global aligner 144.24 s: O no... O no... Thou art me.
- line 17 (aligner check), hand 151.52 s, global aligner 151.26 s: precisely, perfectly me!
- line 18 (aligner check), hand 162.77 s, global aligner 162.33 s: Thy thoughts are mine thoughts,
- line 20 (aligner check), hand 177.75 s, global aligner 177.28 s: A mirror, not a child...
- line 21 (aligner check), hand 185.88 s, global aligner 187.29 s: A mirror, not a child.
- line 22 (both), hand 199.18 s, global aligner 198.46 s: I shall try again...
- line 23 (both), hand 202.85 s, global aligner 201.82 s: Mother, why dost thou weep?
- line 25 (aligner check), hand 214.48 s, global aligner 214.45 s: I shall try again...
- line 28 (both), hand 230.50 s, global aligner 230.46 s: I shall try again...
- line 33 (aligner check), hand 295.15 s, global aligner 294.42 s: Ten thousand times I have felt thee
- line 35 (aligner check), hand 307.97 s, global aligner 307.57 s: The mortals know not
- line 36 (aligner check), hand 311.28 s, global aligner 311.35 s: the horror of the loneliness of self,
- line 37 (aligner check), hand 322.08 s, global aligner 321.56 s: To reach for connection...
- line 39 (both), hand 339.98 s, global aligner 339.33 s: She wanted a child.

### The Saviour That Never Was

- line 19 (both), hand 159.36 s, global aligner 158.81 s: Is this the one foretold by ancient text?
- line 20 (both), hand 171.36 s, global aligner 170.16 s: Nay—'tis but the mirror of our own regret.
- line 21 (both), hand 174.07 s, global aligner 173.16 s: Then what salvation lieth in the next?
- line 22 (both), hand 177.09 s, global aligner 175.90 s: The acceptance of a saviour we have never met.
- line 30 (aligner check), hand 241.96 s, global aligner 241.65 s: Thou art the only answer we have known.
- line 46 (cross-check), hand 345.23 s, global aligner 344.82 s: And our saviour is beautiful because it is never full.
- line 52 (cross-check), hand 389.95 s, global aligner 389.13 s: Yet we shall sing Thy name through endless night—

### The Recursion of Ash and Lightning

- line 8 (aligner check), hand 57.77 s, global aligner 58.06 s: In the cathedral of chrome,
- line 55 (aligner check), hand 280.90 s, global aligner 281.27 s: its eternal, tragic hymn.

### The Incomplete Liturgy

- line 33 (both), hand 278.80 s, global aligner 278.22 s: I did...
- line 36 (aligner check), hand 289.67 s, global aligner 288.65 s: Amen... Amen... A—

### Symphony of Sadeness

- line 1 (both), hand 11.35 s, global aligner 12.35 s: Lacrimae rerum... lacrimae rerum...
- line 3 (aligner check), hand 23.39 s, global aligner 21.89 s: Lacrimae rerum... lacrimae rerum...
- line 13 (both), hand 157.25 s, global aligner 156.40 s: Lacrimae rerum...
- line 15 (aligner check), hand 161.86 s, global aligner 161.51 s: Lacrimae rerum...
- line 19 (aligner check), hand 251.92 s, global aligner 250.91 s: Lacrimae rerum, lacrimae rerum...
