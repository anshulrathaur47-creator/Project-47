#!/usr/bin/env python3
"""Check that everything Video Studio needs is installed, and print the fix for anything missing.

Required: Python 3.9+, FFmpeg/ffprobe, numpy, Pillow, Playwright + Chromium, faster-whisper.
Optional add-ons unlock extra features. Some optional models have NON-COMMERCIAL licences: fine for
personal use, never bundled in this MIT repo - install them yourself if you want them.
"""
import importlib, shutil, subprocess, sys
import sys as _sys
for _st in (_sys.stdout, _sys.stderr):  # UTF-8 output on Windows (Devanagari logs)
    if hasattr(_st, "reconfigure"):
        _st.reconfigure(encoding="utf-8", errors="replace")

ok = True


def report(name, good, fix=""):
    global ok
    print(f"  [{'ok' if good else 'MISSING'}] {name}" + ("" if good else f"\n          fix: {fix}"))
    ok = ok and good


def optional(name, good, fix):
    print(f"  [{'ok' if good else 'optional'}] {name}" + ("" if good else f"  -> {fix}"))


def has_mod(mod):
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


def ff_filters():
    try:
        return subprocess.run(["ffmpeg", "-hide_banner", "-filters"], stdout=subprocess.PIPE, text=True).stdout
    except Exception:
        return ""


print("Video Studio environment check\n-- required")
report("python >= 3.9", sys.version_info >= (3, 9), "install Python 3.10+ from python.org")
report("ffmpeg", bool(shutil.which("ffmpeg")), "macOS: brew install ffmpeg | Windows: winget install ffmpeg | Linux: sudo apt install ffmpeg")
report("ffprobe", bool(shutil.which("ffprobe")), "comes with ffmpeg")
for mod, fix in [("numpy", "pip install numpy"), ("PIL", "pip install pillow"),
                 ("playwright", "pip install playwright && python -m playwright install chromium"),
                 ("faster_whisper", "pip install faster-whisper")]:
    report(mod, has_mod(mod), fix)
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); b.close()
    report("chromium for playwright", True)
except Exception:
    report("chromium for playwright", False, "python -m playwright install chromium")

flt = ff_filters()
print("-- ffmpeg filters used by v2 (transitions, colour, audio)")
for f in ["xfade", "acrossfade", "lut3d", "loudnorm", "ebur128", "afftdn", "deesser", "sidechaincompress",
          "minterpolate", "scdet", "blackdetect", "signalstats", "limiter"]:
    optional(f, f" {f} " in flt, "use a full FFmpeg build (e.g. gyan.dev 'full' on Windows)")

print("-- optional add-ons (free)")
for mod, fix in [
    ("cv2", "pip install opencv-python   (face tracking, reframe, colour analysis, thumbnails)"),
    ("mediapipe", "pip install mediapipe   (text-behind-head, face tracking/reframe)"),
    ("rembg", "pip install rembg onnxruntime   (alternative person matte)"),
    ("kokoro", "pip install kokoro soundfile   (best free offline voice-over, Apache-2.0)"),
    ("librosa", "pip install librosa   (optional; beats.py has a built-in numpy tracker)"),
    ("scenedetect", "pip install scenedetect   (optional; scenes.py uses FFmpeg otherwise)"),
    ("opentimelineio", "pip install opentimelineio   (optional; export_edl.py writes OTIO by hand otherwise)"),
    ("demucs", "pip install demucs   (stem separation: vocals/music; slow on CPU)"),
    ("open_clip", "pip install open_clip_torch   (optional semantic B-roll matching)"),
]:
    optional(mod, has_mod(mod), fix)
optional("piper (CLI)", bool(shutil.which("piper")), "optional TTS; GPL-3.0 - run as a separate program only")

print("-- optional heavy models (personal use; check each licence, NOT bundled)")
for name, fix in [
    ("ProPainter (object removal)", "github.com/sczhou/ProPainter - NON-COMMERCIAL licence, needs a big GPU"),
    ("XTTS-v2 / F5-TTS (voice cloning)", "non-commercial weights - personal use only"),
    ("MusicGen (music generation)", "CC-BY-NC weights - personal use only"),
    ("Real-ESRGAN / RIFE (upscale / interpolation)", "BSD/MIT - pip or ncnn-vulkan builds"),
    ("SAM 2 (masks)", "Apache-2.0 - github.com/facebookresearch/sam2"),
]:
    print(f"  [info] {name}: {fix}")

try:
    import ctranslate2
    gpu = ctranslate2.get_cuda_device_count() > 0
except Exception:
    gpu = False
print(f"-- GPU for whisper: {'yes (CUDA)' if gpu else 'no (CPU; use --model base or small)'}")
print("\nAll required parts are installed." if ok else "\nInstall the missing parts above, then run this check again.")
sys.exit(0 if ok else 1)
