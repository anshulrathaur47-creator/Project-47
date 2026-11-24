# Colour: correction, looks, film texture, matching, QC

Module: `scripts/color.py` (import or CLI). LUTs come from `scripts/luts.py` and live in `luts/` as 33^3 `.cube` files. Run `python scripts/luts.py` to regenerate them; the output is deterministic.

## Pipeline order (always this order)

| # | Stage | Where | Function |
|---|-------|-------|----------|
| 1 | Input transform: log to Rec.709 (approximate generated LUT) or the official camera LUT | speaker source in `render.py`, before overlays | `input_chain(cfg)` (called by `correction_chain`) |
| 2 | Technical correction: black/white points, white balance, exposure, contrast, saturation, then optional shot match | speaker source | `correction_chain(stats, cfg, work)` |
| 3 | Creative look: LUT with intensity, skin-protected | speaker source | `look_chain(name, intensity, W, H, work, halation=0)` |
| 4 | Texture: diffusion, halation, bloom, aberration, sharpen, vignette, weave, flicker, grain, letterbox, dither | final output in `finish.py` | `texture_chain(finish_cfg, W, H)` |
| 5 | Legal limiter (EBU R103), always last | final output | included at the end of `texture_chain` |

Stages 1 to 3 colour only the camera footage. Captions, titles and graphics keep their designed colours.
Stages 4 and 5 run on the finished composite, because grain and the legal clamp must cover everything.
Do not legalise early. EBU advises clamping only once, at the very end.

## Plan fields

```json
"color": {
  "auto": true,              // analyse + auto WB/levels/contrast/sat (default true)
  "wb": true,                // true=auto | "off" | 5600 (Kelvin, colortemperature filter)
  "wb_strength": 0.85,       // 0..1, lower keeps more of the scene's own warmth/coolness
  "exposure": 0.0,           // extra stops (+/-), applied after auto levels
  "contrast": 1.0,           // 1 = none; 1.1 = gentle S-curve. Omit = auto (only flat footage gets more)
  "saturation": 1.0,         // multiplier on top of auto
  "log": "slog3",            // slog3 | vlog | clog3 | applelog | flog  (approximate transform)
  "lut": "C:/luts/official_camera_to_709.cube",   // official LUT (preferred over "log" when you have it)
  "match": "ref.png",        // shot-match to a reference still/video (Reinhard Lab). "first" = caller resolves to first clip
  "match_strength": 0.85,
  "look": "portra",          // creative look name (see table)
  "intensity": 0.8,          // 0..1 look strength
  "halation": 0.0            // 0..1, adds halation to the speaker look (CineStill style)
},
"finish": {                  // texture + legal on the final output
  "grade": "warm",           // LEGACY: still honoured; prefer color.look (it no longer tints captions)
  "grain": 8,                // or {"strength": 10, "luma_weighted": true}
  "halation": 0.4, "bloom": 0.3, "diffusion": 0.5,
  "aberration": 2,           // px of chromatic aberration
  "sharpen": 0.45, "vignette": 0.5,      // vignette true or 0..1
  "weave": 2,                // gate weave amplitude px
  "flicker": 0.02,           // brightness flicker amplitude
  "letterbox": 2.39,         // 2.39 | 2.0 | 1.85 | "2.39:1" | 0.1 (fraction of height, legacy)
  "dither": true,
  "legal": "strict"          // "strict" Y 16-235 / C 16-240 (default) | "ebu" Y 14-241 | false
}
```

## How the auto correction works

`analyze(video, samples=12, work, pre="")` reads 12 frames spread across the clip at 480 px wide and writes `<work>/color.json`. It records:

- Luma percentiles (p0.5 to p99.5).
- A grey estimate and `wb_confidence`. The estimate is an iterative grey-pixel method: grey-world first, then the least-chromatic 30% of pixels after a provisional correction, with skin excluded.
- Cast in the R-B and G axes.
- Chroma before and after WB.
- Skin percentage and skin luma (from a YCrCb mask).
- Clip percentages at both ends.
- `likely_log`: low contrast, lifted blacks and low saturation together.

What `correction_chain` does with these numbers:

- **WB**: runs after the levels curve. It uses black-referenced `colorchannelmixer` gains with luma preserved, so a neutral lift in flat footage does not dilute the cast. A 3% deadband leaves near-neutral footage alone. Gains are clamped to 0.7 to 1.4. Strength is `wb_strength × wb_confidence`. A set with no real greys, such as a navy studio, gets low confidence, so its design is not neutralised.
- **Levels**: builds one `curves` filter.
  - Normal footage only trims near-black and near-white. A scene without whites stays without whites.
  - Flat or log footage gets a full stretch.
  - Mid-tones move only when the stretched median falls outside 0.30 to 0.55, so deliberate low-key or high-key footage is left alone.
  - The black point never cuts into skin shadows.
  - The mids are never brightened far enough to clip skin.
- **Contrast**: auto mode adds a gentle S-curve only when p95 minus p5 is below 0.6.
- **Saturation**: auto mode lifts dull footage toward a natural chroma target, at most 1.4x. It calms garish footage, at most 0.8x. Everything in between is left as shot.
- **Re-analysis**: if `log` or `lut` is set, the source is analysed again *through* that transform, so the correction sees Rec.709-like data.

## Log footage

`log` uses LUTs that `luts.py` generates from the published curve formulas and gamut primaries:

| Log setting | Curve and gamut |
|---|---|
| `slog3` | S-Log3 / S-Gamut3.Cine |
| `vlog` | V-Log / V-Gamut |
| `clog3` | Canon Log 3 / Cinema Gamut |
| `applelog` | Apple Log / Rec.2020 |
| `flog` | F-Log / F-Gamut |

Each LUT decodes the log curve to scene linear, converts the gamut to Rec.709 with a 3x3 matrix, then applies a soft filmic shoulder and 2.4 gamma.

These are **approximate** conversions: there is no manufacturer data in them. When the user has the official camera LUT, use `"lut"` instead.

If `likely_log` is true and no camera is known, do not guess the camera. Auto mode already stretches flat footage. Ask the user, or check the clip metadata, before you set `log`.

## Looks

Set the look in `color.look` with an `intensity` from 0 to 1. Guidance:

- **0.4 to 0.6**: subtle, for corporate work and interviews.
- **0.7 to 0.85**: the normal range for social and brand work.
- **1.0**: stylised, for music videos and trailers.

LUT looks blend in the LUT itself: `intensity` interpolates the cube toward identity, and the cached cube is written to `<work>/vs_luts/`.
The 13 legacy grades blend with the ungraded image via `split` and `blend`.

The **skin** column is how much each look is pulled back toward the original inside the skin-hue range (hue about 0 to 50 degrees, moderate saturation). This is built into the LUT.

| Look | Skin | Use for |
|---|---|---|
| none | - | no look |
| warm / cool | - | legacy: simple warm or cool shift |
| teal-orange | - | legacy teal and orange (not skin-protected; prefer teal-orange-pro) |
| punchy | - | legacy contrast and saturation boost |
| film | - | legacy faded film curve |
| bw / noir | - | legacy black and white / high-contrast noir |
| vintage / faded / pastel | - | legacy retro, faded and pastel |
| neon | - | legacy saturated neon |
| vhs | - | legacy VHS (RGB shift and half-res softness) |
| portra | 0.30 | warm, soft-contrast portraits, lifestyle, interviews |
| kodak-2383 | 0.25 | cinematic print-film contrast for narrative and brand films |
| ektachrome | 0.35 | punchy, cool slide film: travel, outdoors, product |
| fuji-eterna | 0.30 | muted cinema negative: drama, documentary, moody brand |
| fuji-velvia | 0.50 | vivid landscapes, nature, travel B-roll |
| cinestill-800t | 0.30 | night city, neon, tungsten scenes (add `halation`) |
| kodachrome | 0.35 | rich retro colour, nostalgia, travel |
| bleach-bypass | 0 | gritty, high-contrast and desaturated: action, war, sport |
| cross-process | 0.20 | lo-fi fashion and music: yellow highlights, blue shadows |
| golden-hour | 0.30 | warm sunset feel on daylight footage |
| blue-hour | 0.30 | cool dusk, calm, melancholy |
| moody | 0.40 | dark, desaturated storytelling; reflective talking heads |
| high-key | 0.20 | bright and airy: beauty, wellness, lifestyle |
| low-key | 0.20 | dramatic and dark: thrillers, premium product |
| desert | 0.30 | hot, dusty western; adventure |
| nordic | 0.40 | cool, clean and minimal; Scandinavian lifestyle |
| horror-green | 0.15 | horror and unease, sickly green-cyan |
| dreamy | 0.30 | soft and romantic: memories, flashbacks (adds a glow) |
| finance-navy | 0.60 | finance, trading and B2B explainers; trustworthy navy |
| indian-wedding | 0.65 | Indian weddings: warm gold, rich reds, skin kept natural |
| wedding-pastel | 0.50 | western weddings: soft pastel, lifted blacks |
| day-for-night | 0 | fake night from daylight footage |
| infrared | 0 | Aerochrome-style false colour, surreal music videos |
| selective-red | 0 | black and white with reds kept: emphasis, art pieces |
| matrix | 0.20 | green tech, hacker, sci-fi |
| teal-orange-pro | 0.70 | blockbuster teal and orange with natural skin |
| clean-commercial | 0.30 | ads, product, corporate: clean, bright, neutral |
| documentary-natural | 0.30 | true-to-life documentary and news; minimal look |
| music-video-neon | 0.40 | music videos and nightlife: magenta and cyan neon |
| sepia | 0 | old photos, history, flashbacks |
| two-strip | 0 | 1930s two-strip Technicolor red and cyan |
| cyberpunk | 0.40 | futuristic magenta and teal night: gaming, tech |
| vintage-70s | 0.30 | faded warm olive 70s, retro |
| 90s-camcorder | 0.20 | home-video and VHS-C nostalgia (adds softness and RGB shift) |
| sunset | 0.30 | strong warm and magenta sky: romantic, travel |
| cool-corporate | 0.50 | SaaS, tech and corporate interviews: cool neutral |
| food-pop | 0.30 | food: rich warm reds, oranges and yellows |
| real-estate-bright | 0.20 | real estate and interiors: bright, open shadows, blue sky |
| gaming-vivid | 0.30 | gaming, esports, high-energy social |

To pick a look, preview it first. Render a sheet with all looks on the actual footage:

```
python scripts/color.py looks-sheet VIDEO --t 3 --out sheet.png   # add --correct to grade the corrected image
```

Then open the sheet with the Read tool and choose.

## Skin-tone rules

1. Correct before you look. A look over a colour cast makes skin worse.
2. Use a skin-protected look whenever faces matter: weddings, interviews, commercials. That means teal-orange-pro, indian-wedding, finance-navy, wedding-pastel or cool-corporate.
3. Skin should sit at medium luma: roughly 0.45 to 0.7 for light skin, lower for deep skin. Do not "fix" deep skin tones brighter. Auto levels never brighten mids enough to clip skin.
4. On the vectorscope, skin clusters along one line between red and yellow (the "skin line"). A strong move off that line toward green or magenta is wrong unless it is an intended stylised look such as horror-green, infrared or matrix.
5. Stylised looks (bleach-bypass, sepia, day-for-night, infrared, selective-red, two-strip) deliberately do not protect skin.

## Shot matching

`match_chain(src_video, ref, pre="", work=None, strength=0.85)` matches the source to a reference:

1. Computes Lab mean and standard deviation of the source (8 frames, clipped pixels ignored) and of the reference (a still, or 6 frames of a video).
2. Applies the Reinhard transfer `(x - mu_src) * (sd_ref / sd_src) + mu_ref`, with the sd ratio clamped to 0.5 to 2.
3. Bakes the result to `<work>/vs_luts/match_*.cube`. A baked LUT is flicker-free and fast.

In the plan, `color.match` runs **after** the auto correction (and after any manual exposure, contrast and saturation). The match LUT is fitted on the already-corrected image, so it only fine-tunes it toward the reference. On the test chart this was much better than matching raw footage. To match without correcting first, set `"auto": false`. For a multicam or multi-clip edit, set `match` on every clip to one hero frame.

Reinhard uses global statistics. A large uniform background in only one shot will skew the match, so use a reference with similar framing.

## QC and scopes

- `color.py scopes VIDEO --t 3 --out s.png` renders a still sheet with the frame, the luma waveform, the RGB parade and the vectorscope. Use it to check black and white points, colour balance in the parade and skin on the vectorscope.
- `qc(video)`, or `color.py qc VIDEO`, runs `signalstats` on about 300 sampled frames and returns `ymin`, `ymax`, `brng_pct_max`, `satmax`, `issues` and `legal`. It flags luma outside the EBU R103 preferred range of 5 to 246 (8-bit), or more than 1% out-of-range (BRNG) pixels on any frame.
- When QC fails, keep `finish.legal` enabled. It is on by default (`"strict"`).
- `color.py preview VIDEO --look portra --intensity 0.8 --correct --t 3 --out x.png` previews one frame. Add `--finish '{"grain":8,"halation":0.4}'` to include texture.

## Integration (for render.py / finish.py)

```python
import color as C
stats = C.analyze(src, 12, work)                                      # once per source clip
pre = C.correction_chain(stats, plan.get("color", {}), work)          # "" when nothing to do
look = C.look_chain(cfg.get("look", "none"), cfg.get("intensity", 1.0), W, H, work, cfg.get("halation", 0))
# speaker_chain: insert ",".join(x for x in [pre, look] if x) after zoom/scale/crop, before format=yuva420p
# finish.py: vf.append(C.texture_chain(plan.get("finish", {}), W, H))   (replaces grain/vignette/letterbox/sharpen)
```

The chains may contain `split` and `blend` with unique `[labels]`. They are valid inside `-filter_complex`, a `-/filter_complex` script and `-vf`.
LUT paths are quoted with the drive colon escaped (`lut3d=file='C\:/...'`). An unescaped `lut3d='C:/x.cube'` fails on Windows.
Never use `drawtext` on this machine. Draw labels with Pillow.
