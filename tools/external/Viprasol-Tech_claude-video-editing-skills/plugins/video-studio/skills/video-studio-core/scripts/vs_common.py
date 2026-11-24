"""Shared helpers for Video Studio scripts."""
import re, json, os, shutil, subprocess, sys

# Windows consoles/pipes default to cp1252: printing Devanagari would crash. Force UTF-8 output.
for _st in (sys.stdout, sys.stderr):
    if hasattr(_st, "reconfigure"):
        _st.reconfigure(encoding="utf-8", errors="replace")

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(CORE, "runtime")


def die(msg, code=1):
    print(f"[video-studio] ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def log(msg):
    print(f"[video-studio] {msg}", flush=True)


def need(binary):
    if not shutil.which(binary):
        die(f"'{binary}' not found. Install FFmpeg (https://ffmpeg.org/download.html) and make sure it is on PATH.")


_FF_MAJOR = None


def ffmpeg_major():
    """Major version of the ffmpeg on PATH (0 if unknown, e.g. git builds)."""
    global _FF_MAJOR
    if _FF_MAJOR is None:
        try:
            out = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, text=True).stdout
            num = out.split("version", 1)[1].split()[0].lstrip("n")
            _FF_MAJOR = int(num.split(".")[0]) if num[:1].isdigit() else 0
        except Exception:
            _FF_MAJOR = 0
    return _FF_MAJOR


def _compat(cmd):
    """FFmpeg 7+ reads option values from files with '-/opt file'; FFmpeg 9 removed the old
    '-filter_complex_script'. Translate so every script works on old and new builds."""
    if cmd and os.path.basename(cmd[0]).startswith("ffmpeg") and "-filter_complex_script" in cmd:
        if ffmpeg_major() == 0 or ffmpeg_major() >= 7:
            cmd = ["-/filter_complex" if c == "-filter_complex_script" else c for c in cmd]
    return cmd


def run(cmd, quiet=True):
    """Run a command list; raise with stderr tail on failure."""
    need(cmd[0])
    cmd = _compat(cmd)
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0 and os.environ.get("VS_DEBUG"): print(" ".join(cmd), p.stderr)
    if p.returncode != 0:
        tail = "\n".join(p.stderr.strip().splitlines()[-25:])
        die(f"command failed: {' '.join(cmd[:6])} ...\n{tail}")
    if not quiet:
        print(p.stdout)
    return p.stdout


def probe(path):
    need("ffprobe")
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if out.returncode != 0:
        die(f"cannot read {path}: {out.stderr.strip()}")
    info = json.loads(out.stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"].get("duration", 0) or 0)
    res = {"duration": dur, "has_audio": a is not None, "has_video": v is not None}
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(float(sd["rotation"]))
        if "tags" in v and "rotate" in v["tags"]:
            rot = int(v["tags"]["rotate"])
        if abs(rot) in (90, 270):
            w, h = h, w
        num, den = (v.get("avg_frame_rate") or "30/1").split("/")
        fps = float(num) / float(den) if float(den) else 30.0
        res.update({"width": w, "height": h, "fps": fps})
    return res


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(p, data):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


FORMATS = {
    "9:16": (1080, 1920), "reel": (1080, 1920), "short": (1080, 1920),
    "1:1": (1080, 1080), "square": (1080, 1080),
    "4:5": (1080, 1350),
    "16:9": (1920, 1080), "youtube": (1920, 1080),
}


def parse_format(s):
    if s in FORMATS:
        return FORMATS[s]
    if "x" in s:
        w, h = s.lower().split("x")
        return int(w), int(h)
    die(f"unknown format '{s}'. Use 9:16, 1:1, 4:5, 16:9 or WIDTHxHEIGHT")


# ---- text helpers shared by every script (Indic-safe) ----
import unicodedata as _ud
SENT_END = re.compile(r"[.!?।॥]$")   # sentence end incl. Devanagari danda / double danda


def norm(s: str) -> str:
    """Lower-case NFC word key that KEEPS combining marks (Devanagari vowel signs are Unicode category M)."""
    s = _ud.normalize("NFC", s or "").lower()
    return "".join(ch for ch in s if ch.isalnum() or ch in "'_" or _ud.category(ch).startswith("M"))


assert norm("बरगी,") == "बरगी" and norm("Hello!") == "hello" and SENT_END.search("है।")
