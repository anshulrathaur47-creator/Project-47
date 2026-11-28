# plan.json reference

`make_plan.py` writes a first draft. Claude edits it, then runs `render.py` and `finish.py`.

> **v2 references:** this file covers the base elements. Also see `motion.md` (easing, springs, keyframes, caption presets,
> 28 new components, transition overlays, face anchoring, beats), `color.md` (the `"color"` block), `audio.md`
> (`"audio"`, `"music"`, `"sfx"`), `timeline.md` (multi-clip specs), `delivery.md`, and `craft.md` (how to cut).
> v2 plan keys added by `make_plan.py` when available: `genre`, `track` (face boxes), `beats`, `peaks`.
All times are in seconds on the **cut** timeline (after autocut). All positions are output pixels:
`x`,`y` is the anchor point (default centre of frame); `anchor` can be `center`, `top`, `bottom`,
`left`, `right`, `top-left` and so on.

```json
{
  "output": {"width": 1080, "height": 1920, "fps": 30, "duration": 18.4, "background": "black"},
  "source": "cut.mp4",              // speaker video, relative to the plan file. null for no speaker
  "matte": "matte.mp4",             // person mask from matte.py, needed for layer "behind"
  "speaker": {
    "mode": "full",                 // full | panel | none
    "rect": [60, 980, 960, 860],    // panel only: x, y, w, h
    "radius": 48,                   // rounded corners (panel)
    "focusX": 0.5, "focusY": 0.35,  // which part of a wider source to keep when cropping
    "push": 0.04,                   // slow push-in over the whole video (0.04 = +4%)
    "mirror": false,
    "zooms": [{"start": 2.1, "end": 3.4, "scale": 1.15, "snap": false}],  // + optional "cx","cy" / "toFace"
    "backdrop": "video",            // video | blur (blurred, dimmed copy of the shot) | hide (bg/behind layers only); blur/hide need matte
    "backdropBlur": 36, "backdropDim": 0.5,
    "glow": {"color": "#F5B942", "size": 16, "strength": 1.7},   // soft rim glow around the person cut-out (needs matte)
    "personScale": 1.0,             // <1 shrinks the cut-out, bottom-centred (for shots with headroom and room at the sides)
    "personDrop": 0,                // slide the cut-out down by this fraction of H at full width (tight selfies); top edge fades
    "layouts": [{"start": 0, "end": 3.2, "rect": [80, 700, 700, 800], "radius": 34, "rot": -3}]  // footage card moves over time (no matte)
  },
  "theme": {"vars": {"--c-accent": "#FFE14D"}, "fontsUrl": "https://fonts.googleapis.com/...", "cssFiles": ["/abs/theme.css"], "css": ""},
  "words": [{"w": "Hello", "start": 0.2, "end": 0.5}],
  "clips": [{"id": "rec", "src": "screen.mp4", "start": 0, "end": 12, "loop": false}],
  "cutaways": [{"src": "broll.mp4", "start": 4.0, "end": 6.5, "srcStart": 10}],
  "blurs": [{"x": 880, "y": 96, "w": 420, "h": 40, "start": 0, "end": 12.5}],
  "elements": [ ... ],
  "sfx": [{"t": 1.2, "kind": "pop", "gain": 0.5}],
  "music": {"src": "music.mp3", "volume": 0.12, "duck": true, "start": 0, "fadeOut": 1.5},
  "finish": {"grade": "warm", "grain": 6, "vignette": true, "letterbox": 0, "sharpen": false, "lut": null},
  "outputFile": "final.mp4"
}
```

## Layers (stacking order, back to front)

1. `bg`: opaque HTML background (only when an element uses it)
2. speaker video (full frame, panel or moving `layouts` cards; blurred or hidden with `backdrop`), then the `glow`
3. `behind`: HTML drawn **behind the person** (needs `matte`)
4. person cut-out (from `matte`)
5. `cutaways`: full-frame B-roll video
6. `blurs`: privacy blur / pixelate boxes on the picture (under the graphics)
7. `front`: captions, cards, everything on top

## Punch-in zooms (`speaker.zooms`)

Each zoom: `start`, `end`, `scale`, `snap` (hard cut in/out instead of an ease). Where it zooms toward:

- `"cx"`, `"cy"` (normalised source coords, 0-1, top-left origin): zoom toward that point (a UI button, a product).
- otherwise, when the plan has `track` (from `W/track.json`, copied in by `make_plan.py`), it centres on the primary
  face at the zoom's start (aimed a touch above centre, at the eyes). Make the track for the speaker video first:
  `python CORE/scripts/track.py analyze W/cut.mp4 --work W`, then `make_plan.py`.
- `"toFace": false` keeps that zoom on the frame centre. No track and no `cx`/`cy`: frame centre.

The centre holds for the whole zoom window; the crop always stays inside the frame. There is no automatic cursor or
object tracking: for a screen recording, set `cx`/`cy` per zoom to the spot being clicked.

## Privacy blurs (`blurs`)

`"blurs": [{"x", "y", "w", "h", "start", "end", "strength"?, "pixelate"?, "block"?}]` blurs the **picture** (speaker
video, cutaways) under the graphics, so captions and cards stay sharp. Use it for number plates, faces of bystanders
who did not consent, screens, addresses, emails, API keys and customer data in screen recordings.

| field | meaning |
| --- | --- |
| `x`, `y`, `w`, `h` | box in **output** pixels, `x`,`y` = top-left corner (not the element anchor) |
| `start`, `end` | seconds on the cut timeline (default: the whole video) |
| `strength` | box-blur radius, default 24 (capped to the box size) |
| `pixelate`, `block` | `true` for a mosaic instead of a blur; `block` = mosaic cell size, default 24 |

Blurs cover the speaker video and `cutaways` only, not `clip`/`image` elements (those are graphics: blur the
source file or cover them). The box is fixed in output pixels: split it into short boxes when the subject moves
or a punch-in zoom changes the framing. Check every box in the `--frames`
stills (stills show blurs and cutaways) and scrub the full render.

## Shared element fields

| field | meaning |
| --- | --- |
| `type` | component name (below) |
| `layer` | `bg`, `behind` or `front` |
| `start`, `end` | visible window |
| `x`, `y`, `w`, `h`, `anchor`, `rotate`, `z` | placement |
| `in`, `out` | `fade` `pop` `bounce` `rise` `drop` `slideLeft` `slideRight` `scale` `zoomIn` `blur` `spin` `wipe` `wipeUp` `stamp` `flip` `glitch` `none` |
| `inDur`, `outDur` | seconds (default 0.35 / 0.25) |
| `float`, `drift`, `wobble` | idle motion: bob in px, scale growth per second, rotation wobble in degrees |
| `className` | extra CSS classes (themes style them) |
| `style` | inline CSS object, e.g. `{"fontSize": "120px", "color": "#fff"}` |

## Components

| type | key fields |
| --- | --- |
| `captions` | `mode` (`karaoke` all words shown, active highlighted · `reveal` words appear as spoken · `single` one word at a time), `maxWords`, `maxChars`, `y`, `w`, `uppercase`, `lowercase`, `wordIn`, `activeScale`, `keywords` (list of words coloured with accent 2), `hold`. Class presets: `cap-pill`, `cap-box`, `cap-outline`, `cap-soft`, `cap-dim` |
| `text` / `headline` / `chip` / `tile` / `sticker` | `text`, `split` (`words`/`chars` for kinetic type) with `stagger`, `unitIn`, `unitDur`; `fit: true` shrinks to fit `w` (default on for `headline`); `wrap` |
| `card` | `kicker`, `title`, `body`, `items` (strings or `{text, at}`), `numbered`, `marker`, `image`, `clip`, `itemStagger`. Classes `glass`, `paper` |
| `clip` | `clip` (id from `clips`), `device` (`phone` `laptop` `browser`), `motion` (`flyIn` `tilt` `float` `kenburns` `orbit`), `clipOffset`, `image` (a still instead of a clip) |
| `image` | `image`, same motions as clip |
| `counter` | `from`, `to`, `prefix`, `suffix`, `decimals`, `label`, `countDur` |
| `bars` | `title`, `items` `[{label, value, highlight}]`, `max`, `prefix`, `suffix` |
| `lowerthird` | `name`, `role` |
| `titlecard` | `kicker`, `title`, `subtitle` (full frame) |
| `shape` | `kind`: `ring` `glow` `orbit` `ribbon` `rays` `burst` `grid` `blob` `sparkles` `bubbles` `confetti` `halftone` `spotlight` `frame` `bar`; `color`, `color2`, `speed`, `count`, `thickness`, `pulseOn` (times to pulse) |
| `scribble` | `kind`: `circle` `underline` `arrow` `box` `cross` `check` `highlight` `zigzag`; `color`, `strokeWidth`, `drawDur` |
| `progress` | `position` (`top`/`bottom`) |
| `background` | `kind`: `solid` `gradient` `mesh` `paper` `grid` `dots`; `image` |
| `burst` | `chars` (emoji), `count`, `radius` |
| `ticker` | `label`, `text`, `y`, `speed` |
| `rec` | camcorder REC dot + timecode, `date` |
| `flash` | `times` list, `color`, `opacity`, `dur` |
| `compare` | `before`, `after` images, labels, `wipeDelay`, `wipeDur`, `wipeTo` |
| `equalizer` | fake audio bars that move while someone speaks |
| `stars` | rating stars (only for real reviews the user supplies) |

## Tips

- Check the look before a full render: `render.py plan.json --frames 1,4,8,12` writes `contact_sheet.png`. Look at it.
- Keep text out of the bottom 15% and top 10% of a 9:16 frame (platform buttons cover them).
- Change one thing, preview, repeat. A full render of 30 s at 1080x1920 takes about 1–3 minutes.
