#!/usr/bin/env python3
"""Creator profile: the defaults this creator always wants (caption language/script, platform, fonts).
Stored once at %USERPROFILE%/.video-studio/profile.json (VS_PROFILE=path overrides, e.g. for tests).
A missing file means the defaults below (Hindi in Devanagari, Reels).

usage: profile.py show
       profile.py set language=hi script=Deva platform=reels fonts.display="Mukta"
       profile.py --self-test
Note: this file shadows the stdlib `profile` module inside scripts/ (cProfile.run would break here).
"""
import copy, json, os, re, sys
from vs_common import die, log, save_json

DEFAULTS = {"language": "hi", "script": "Deva", "platform": "reels",
            "fonts": {"display": "Mukta", "body": "Noto Sans Devanagari"}}
# Whisper often mis-detects Hindi/Haryanvi speech as these (Urdu/Sindhi = Arabic script, Punjabi = Gurmukhi, Nepali)
RISKY = {"ur", "pa", "sd", "ne"}
CHECK = {"language": r"[a-z]{2,3}", "script": r"[A-Z][a-z]{3}", "platform": r"[a-z0-9-]+"}


def path() -> str:
    return os.environ.get("VS_PROFILE") or os.path.join(os.path.expanduser("~"), ".video-studio", "profile.json")


def load() -> dict:
    """Defaults overlaid with the saved profile. A broken file is an error, never silently ignored."""
    prof = copy.deepcopy(DEFAULTS)
    if not os.path.exists(path()):
        return prof
    try:
        with open(path(), encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, ValueError) as e:
        die(f"cannot read creator profile {path()}: {e}. Fix or delete it (profile.py show).")
    if not isinstance(saved, dict):
        die(f"creator profile {path()} must be a JSON object")
    prof.update({k: v for k, v in saved.items() if k != "fonts"})
    prof["fonts"].update(saved.get("fonts") or {})
    return prof


def set_values(pairs: list) -> dict:
    """Apply key=value pairs (fonts.<role>=Name for fonts), validate, save. Returns the new profile."""
    prof = load()
    for pair in pairs:
        key, sep, val = pair.partition("=")
        key, val = key.strip(), val.strip()
        if not sep or not val:
            die(f"expected key=value, got '{pair}'")
        if key.startswith("fonts.") and len(key) > 6:
            prof["fonts"][key[6:]] = val
        elif key in CHECK:
            if not re.fullmatch(CHECK[key], val):
                die(f"bad {key} '{val}' (language: Whisper code like hi/en/ur, script: ISO 15924 like Deva/Latn/Arab)")
            prof[key] = val
        else:
            die(f"unknown profile key '{key}'. Known: {', '.join(CHECK)}, fonts.<role>")
    save_json(path(), prof)
    return prof


def asr_language(detected: str, explicit: str = None) -> str:
    """Language to transcribe and caption with. An explicit --language always wins; a detection that is a common
    mis-ID for Hindi-belt speech (ur/pa/sd/ne) becomes the profile language unless the profile says that language."""
    if explicit:
        return explicit
    want = load()["language"]
    return want if detected in RISKY and want != detected else detected


def _self_test() -> None:
    import tempfile
    os.environ["VS_PROFILE"] = os.path.join(tempfile.mkdtemp(), "profile.json")
    assert load() == DEFAULTS and asr_language("ur") == "hi" and asr_language("pa") == "hi"
    assert asr_language("en") == "en" and asr_language("ur", "ur") == "ur" and asr_language("hi") == "hi"
    set_values(["language=ur", "fonts.display=Baloo 2"])
    assert load()["language"] == "ur" and load()["fonts"] == {"display": "Baloo 2", "body": "Noto Sans Devanagari"}
    assert asr_language("ur") == "ur" and asr_language("pa") == "ur"
    print("profile.py self-test ok")


def main() -> None:
    args = sys.argv[1:]
    if args == ["--self-test"]:
        return _self_test()
    if not args or args[0] not in ("show", "set") or (args[0] == "set" and len(args) < 2):
        die("usage: profile.py show | profile.py set key=value ... (keys: language script platform fonts.<role>)")
    prof = set_values(args[1:]) if args[0] == "set" else load()
    log(f"profile {path()}" + ("" if os.path.exists(path()) else " (not saved yet: defaults)"))
    print(json.dumps(prof, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
