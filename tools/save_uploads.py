#!/usr/bin/env python3
"""Save every file the user uploads into reference-library/, permanently.

Uploads land in ~/.claude/uploads/<session>/<8-hex>-<original name>, which is wiped with the container.
This copies each one to reference-library/<YYYY-MM-DD>/<original name> (the upload's date), skips files
already saved (same content), and keeps reference-library/INDEX.md up to date.

Run by the project hooks in .claude/settings.json on every message and at the end of every turn, so nothing
is missed. Safe to run any number of times. Files over GitHub's 100 MB limit are listed in INDEX.md but not copied.

Usage: python3 tools/save_uploads.py [--quiet]
"""
import datetime
import glob
import hashlib
import os
import re
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB = os.path.join(ROOT, "reference-library")
UPLOADS = os.path.expanduser("~/.claude/uploads")
INDEX = os.path.join(LIB, "INDEX.md")
LIMIT = 95 * 1024 * 1024

KIND = {
    "audio": {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".flac"},
    "video": {".mp4", ".mov", ".mkv", ".webm", ".avi", ".3gp"},
    "image": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"},
    "text": {".txt", ".srt", ".vtt", ".md", ".json", ".csv", ".pdf", ".docx"},
}


def kind_of(name):
    ext = os.path.splitext(name)[1].lower()
    for k, exts in KIND.items():
        if ext in exts:
            return k
    return "other"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def known_hashes():
    out = {}
    for p in glob.glob(os.path.join(LIB, "*", "*")):
        if os.path.isfile(p):
            out[sha(p)] = p
    return out


def main():
    quiet = "--quiet" in sys.argv
    os.makedirs(LIB, exist_ok=True)
    have = known_hashes()
    saved, skipped_big = [], []
    for src in sorted(glob.glob(os.path.join(UPLOADS, "*", "*"))):
        if not os.path.isfile(src):
            continue
        name = re.sub(r"^[0-9a-f]{8}-", "", os.path.basename(src))
        if os.path.getsize(src) > LIMIT:
            skipped_big.append(name)
            continue
        h = sha(src)
        if h in have:
            continue
        day = datetime.date.fromtimestamp(os.path.getmtime(src)).isoformat()
        dest_dir = os.path.join(LIB, day)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, name)
        base, ext = os.path.splitext(name)
        n = 2
        while os.path.exists(dest):
            dest = os.path.join(dest_dir, f"{base}_{n}{ext}")
            n += 1
        shutil.copy2(src, dest)
        have[h] = dest
        saved.append(dest)
    write_index(skipped_big)
    if saved and not quiet:
        print(f"saved {len(saved)} new upload(s) to reference-library/")
        for p in saved:
            print("  " + os.path.relpath(p, ROOT))
    elif saved:
        print(f"reference-library: saved {len(saved)} new upload(s)")


def write_index(skipped_big):
    rows = []
    for d in sorted(os.listdir(LIB), reverse=True):
        p = os.path.join(LIB, d)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            fp = os.path.join(p, f)
            mb = os.path.getsize(fp) / 1e6
            rows.append(f"| {d} | [{f}]({d}/{f.replace(' ', '%20')}) | {kind_of(f)} | {mb:.1f} MB |")
    lines = [
        "# Reference library",
        "",
        "Every file the user has sent, saved for good (by `tools/save_uploads.py`, run automatically by the project hooks).",
        "Newest first. Working copies used in a reel also live in `assets/`, `references/` or `raw-videos/`.",
        "",
        "| Date | File | Type | Size |",
        "|---|---|---|---|",
        *rows,
        "",
    ]
    if skipped_big:
        lines += ["Not copied (over GitHub's 100 MB limit): " + ", ".join(sorted(set(skipped_big))), ""]
    old = open(INDEX).read() if os.path.exists(INDEX) else ""
    new = "\n".join(lines)
    if new != old:
        with open(INDEX, "w") as f:
            f.write(new)


if __name__ == "__main__":
    main()
