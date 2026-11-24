# theme.json reference (for style skills)

Every style skill holds a `theme.json` and usually a `theme.css`. `make_plan.py` turns them into a draft plan.
Strings that start with `=` are expressions using `W`, `H` and `DUR` (output width, height, duration), e.g. `"=H*0.7"`.
`{text}`, `{label}`, `{cta}`, `{title}`, `{dur}` are filled in automatically.

```json
{
  "name": "my-style",
  "format": "9:16",                     // default output; user can override with --format
  "fps": 30,
  "fontsUrl": "https://fonts.googleapis.com/css2?family=...",
  "vars": {"--c-accent": "#FFE14D"},   // CSS variables (see runtime/base.css :root)
  "cssFiles": ["theme.css"],
  "speaker": {"mode": "full", "rectFrac": [0.05, 0.5, 0.9, 0.45], "radius": 40, "focusY": 0.35, "push": 0.03},
  "matte": true,                         // style needs the person cut-out (text behind head)
  "background": "#000",
  "auto": {
    "static":   [ elements shown for the whole video ],
    "captions": { captions element },
    "keywords": {"every": 2.5, "max": 10, "minScore": 2.5, "element": {..."{text}"...} or [variants],
                 "uppercase": true, "hold": 1.3, "zoom": 1.12, "alternate": true, "zoomHold": 1.0, "snap": false,
                 "sfx": "pop", "sfxGain": 0.4},
    "headlines": {"maxWords": 2, "uppercase": true, "element": {..."{text}"...} or [variants]},
    "numbers":  {"element": {"type": "counter", "label": "{label}", ...}, "hold": 2.2, "sfx": "ding"},
    "lists":    {"title": "3 rules", "element": {"type": "card", "title": "{title}", ...}},
    "cuts":     {"sfx": "swish", "gain": 0.2, "minGap": 2.0, "flash": false},
    "hook":     {"dur": 2.2, "uppercase": false, "sfx": "riser", "element": {..."{text}"...}},
    "endcard":  {"dur": 2.0, "cta": "Follow for more", "element": {..."{cta}"...}}
  },
  "sfx": [],
  "music": null,
  "finish": {"grade": "punchy", "grain": 0, "vignette": false, "letterbox": 0, "sharpen": true}
}
```

Grades: `none warm cool teal-orange punchy film bw vintage faded neon vhs pastel noir` (or `lut` with a .cube file).
SFX kinds (generated, no files needed): `pop click type ding boom riser whoosh swish camera`.

> **v2:** `finish.grade` accepts every look in `color.md` (52 names: the 13 legacy grades plus 39 LUT looks; graded on the
> footage, not the graphics) and theme `sfx` kinds accept all 49 sounds in `audio.md`. A theme may also set `"color"`
> (correction, look, intensity, halation) and `"audio"` blocks; see `color.md` and `audio.md`. Genre presets
> (`--genre`) fill pacing/caption/loudness defaults the theme leaves out; the theme always wins.
