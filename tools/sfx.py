#!/usr/bin/env python3
"""Search and download free sound effects and music for edits.

Sources:
  openverse  - Openverse (WordPress/Creative Commons) audio search. Covers Freesound,
               Jamendo, ccMixter and Wikimedia audio. No key needed (optional
               OPENVERSE_CLIENT_ID / OPENVERSE_CLIENT_SECRET for higher limits).
  freesound  - Freesound.org API directly. Needs a free key in FREESOUND_API_KEY
               (https://freesound.org/apiv2/apply). Downloads the HQ MP3 preview.

Every download is logged with its creator and licence in <folder>/CREDITS.md, so
attribution for CC-BY sounds is ready to paste into a caption.

Usage:
  python3 tools/sfx.py search "whoosh"                       # sound effects (default)
  python3 tools/sfx.py search "sad piano" --music            # music
  python3 tools/sfx.py search "rain" --source freesound
  python3 tools/sfx.py get openverse <id>                    # -> assets/sfx/
  python3 tools/sfx.py get openverse <id> --music            # -> assets/music/
  python3 tools/sfx.py get freesound <id>
  python3 tools/sfx.py check                                 # test both sources
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "video-workspace-sfx/1.0"
OV = "https://api.openverse.org/v1"
FS = "https://freesound.org/apiv2"


def http_json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def download(url, path, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        while chunk := r.read(1 << 16):
            f.write(chunk)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "sound"


def explain(err, host):
    msg = str(err)
    if "403" in msg or "Tunnel connection failed" in msg:
        return (f"{host} is blocked by this environment's network policy. "
                f"Allow it under the environment's Network access settings.")
    return msg


# ---------------- Openverse ----------------
def ov_headers():
    cid, secret = os.environ.get("OPENVERSE_CLIENT_ID"), os.environ.get("OPENVERSE_CLIENT_SECRET")
    if not (cid and secret):
        return {}
    body = urllib.parse.urlencode({"client_id": cid, "client_secret": secret,
                                   "grant_type": "client_credentials"}).encode()
    tok = http_json(f"{OV}/auth_tokens/token/", data=body)["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def ov_search(q, music, n, commercial):
    params = {"q": q, "page_size": n, "category": "music" if music else "sound_effect"}
    if commercial:
        params["license_type"] = "commercial"
    data = http_json(f"{OV}/audio/?{urllib.parse.urlencode(params)}", headers=ov_headers())
    return [{"id": r["id"], "title": r.get("title") or "untitled", "creator": r.get("creator") or "unknown",
             "license": f"CC {r.get('license', '').upper()} {r.get('license_version') or ''}".strip(),
             "seconds": round((r.get("duration") or 0) / 1000, 1), "source": r.get("source"),
             "url": r.get("url"), "page": r.get("foreign_landing_url"),
             "attribution": r.get("attribution")} for r in data.get("results", [])]


def ov_get(i):
    r = http_json(f"{OV}/audio/{i}/", headers=ov_headers())
    return {"title": r.get("title") or "untitled", "creator": r.get("creator") or "unknown",
            "license": f"CC {r.get('license', '').upper()} {r.get('license_version') or ''}".strip(),
            "url": r["url"], "page": r.get("foreign_landing_url"), "ext": r.get("filetype") or "mp3",
            "attribution": r.get("attribution")}


# ---------------- Freesound ----------------
def fs_key():
    k = os.environ.get("FREESOUND_API_KEY")
    if not k:
        sys.exit("Freesound needs a free API key: get one at https://freesound.org/apiv2/apply "
                 "and save it as the FREESOUND_API_KEY environment variable.")
    return k


FS_FIELDS = "id,name,username,license,duration,previews,url"


def fs_search(q, music, n, commercial):
    params = {"query": q, "page_size": n, "fields": FS_FIELDS, "token": fs_key(),
              "filter": "duration:[0 TO 600]" if music else "duration:[0 TO 30]"}
    if commercial:
        params["filter"] += ' -license:"Attribution NonCommercial"'
    data = http_json(f"{FS}/search/text/?{urllib.parse.urlencode(params)}")
    return [{"id": r["id"], "title": r["name"], "creator": r["username"], "license": r["license"],
             "seconds": round(r["duration"], 1), "source": "freesound",
             "url": r["previews"]["preview-hq-mp3"], "page": r["url"], "attribution": None}
            for r in data.get("results", [])]


def fs_get(i):
    r = http_json(f"{FS}/sounds/{i}/?{urllib.parse.urlencode({'fields': FS_FIELDS, 'token': fs_key()})}")
    return {"title": r["name"], "creator": r["username"], "license": r["license"],
            "url": r["previews"]["preview-hq-mp3"], "page": r["url"], "ext": "mp3", "attribution": None}


# ---------------- commands ----------------
def cmd_search(a):
    fn, host = (ov_search, "api.openverse.org") if a.source == "openverse" else (fs_search, "freesound.org")
    try:
        rows = fn(a.query, a.music, a.n, a.commercial)
    except (urllib.error.URLError, OSError) as e:
        sys.exit(explain(e, host))
    if not rows:
        print("No results.")
    for r in rows:
        print(f"{r['id']}\n   {r['title']}  ({r['seconds']}s)  by {r['creator']}  [{r['license']}]  via {r['source']}")


def cmd_get(a):
    getter, host = (ov_get, "api.openverse.org") if a.source == "openverse" else (fs_get, "freesound.org")
    folder = os.path.join(ROOT, "assets", "music" if a.music else "sfx")
    os.makedirs(folder, exist_ok=True)
    try:
        info = getter(a.id)
        path = os.path.join(folder, f"{slug(info['title'])}.{info['ext']}")
        download(info["url"], path)
    except (urllib.error.URLError, OSError) as e:
        sys.exit(explain(e, urllib.parse.urlparse(getattr(e, "url", "") or "").netloc or host))
    line = (info.get("attribution") or
            f'"{info["title"]}" by {info["creator"]}, {info["license"]} ({info["page"]})')
    with open(os.path.join(folder, "CREDITS.md"), "a", encoding="utf-8") as f:
        f.write(f"- `{os.path.basename(path)}`: {line}\n")
    print(f"saved {os.path.relpath(path, ROOT)}\ncredit: {line}")


def cmd_check(_):
    ok = True
    for name, url in (("Openverse", f"{OV}/audio/?q=whoosh&page_size=1"),):
        try:
            http_json(url)
            print(f"[ok]   {name} search reachable")
        except (urllib.error.URLError, OSError) as e:
            ok = False
            print(f"[fail] {name}: {explain(e, 'api.openverse.org')}")
    if os.environ.get("FREESOUND_API_KEY"):
        try:
            fs_search("whoosh", False, 1, False)
            print("[ok]   Freesound search reachable")
        except (urllib.error.URLError, OSError) as e:
            ok = False
            print(f"[fail] Freesound: {explain(e, 'freesound.org')}")
    else:
        print("[info] Freesound: no FREESOUND_API_KEY set (optional; Openverse already includes Freesound sounds)")
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--source", choices=["openverse", "freesound"], default="openverse")
    s.add_argument("--music", action="store_true", help="search music instead of sound effects")
    s.add_argument("-n", type=int, default=10)
    s.add_argument("--commercial", action="store_true", help="only licences that allow commercial use")
    s.set_defaults(fn=cmd_search)
    g = sub.add_parser("get")
    g.add_argument("source", choices=["openverse", "freesound"])
    g.add_argument("id")
    g.add_argument("--music", action="store_true", help="save to assets/music instead of assets/sfx")
    g.set_defaults(fn=cmd_get)
    c = sub.add_parser("check")
    c.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
