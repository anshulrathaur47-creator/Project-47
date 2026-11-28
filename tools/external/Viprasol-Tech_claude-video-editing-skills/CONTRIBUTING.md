# Contributing

Thanks for helping make a free, local video editor for everyone. New styles, genres, fixes and docs are all welcome.

## Ways to help

- **Report a bug** or a bad-looking edit with the bug form. Describe it or attach a still; never attach private footage.
- **Request a style or genre** with the style request form, ideally with a reference link.
- **Add a style (skin)**: a folder in `plugins/video-studio/skills/` with `SKILL.md`, `theme.json` and `theme.css`. See "Make your own style" in the README and `video-studio-core/references/theme-schema.md`.
- **Add a scene recipe**: a file `video-studio-core/scripts/recipes/<name>.py` exposing `build(plan, args) -> plan`, then set `"sequence": "<name>"` in the skin's `theme.json`. `sequence.py` (the `ribbon` recipe) is the reference.
- **Add a genre**: a preset in `video-studio-core/scripts/genres.json` plus a skill folder. See "Make your own genre" in the README.
- **Improve the engine**: the Python scripts and `runtime/engine.js` in `video-studio-core`.

## Development setup

```bash
git clone https://github.com/Viprasol-Tech/claude-video-editing-skills
cd claude-video-editing-skills
pip install -r requirements.txt
python -m playwright install chromium
python plugins/video-studio/skills/video-studio-core/scripts/check_env.py
```

FFmpeg (full build) must be on PATH.

## Before you open a pull request

```bash
python tests/validate_repo.py                                      # every skill, theme and manifest
python plugins/video-studio/skills/video-studio-core/scripts/<script>.py --self-test   # scripts you touched
```

For visual changes, render a contact sheet (`render.py plan.json --frames 1,3,6,9`) and look at it: text readable, nothing over the face, safe zones respected (10-85% of the height, clear of the right 12% in 9:16), Devanagari matras intact.

## House rules

- **Keep it local and free.** No required accounts, API keys or cloud services. Optional add-ons are fine if the core works without them.
- **Licences.** Code is MIT. Never bundle non-commercial or GPL models or assets; make them optional, user-installed, and say so in `check_env.py`.
- **Smallest correct change.** No new dependency for what a few lines can do. Files under ~800 lines; put big new code in a new module.
- **Explicit errors.** Fail with a clear message instead of silently falling back.
- **One runnable check** (`--self-test` or an assert-based `__main__`) for non-trivial logic.
- **Every language.** Text code must keep combining marks (use `vs_common.norm`) and split text by grapheme, so Hindi and other Indic scripts work.
- **Skill front matter.** `name:` equals the folder name; `description:` says what it does and when to use it (max 1024 characters).
- **Changelog.** Add user-visible changes to `CHANGELOG.md`.

By contributing you agree that your contribution is licensed under the MIT licence and you follow the [Code of Conduct](CODE_OF_CONDUCT.md).
