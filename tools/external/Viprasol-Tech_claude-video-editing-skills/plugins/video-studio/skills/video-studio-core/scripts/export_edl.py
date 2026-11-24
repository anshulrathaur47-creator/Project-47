#!/usr/bin/env python3
"""Editor hand-off: the autocut edit as CMX3600 EDL, FCPXML 1.10 (Final Cut, Resolve, Premiere
via import) and OpenTimelineIO JSON, with plan elements as markers. Plus ProRes 4444 alpha export
of overlay layers.

usage: export_edl.py WORK_OR_CUTLIST [--plan W/plan.json] [--source W/source.mp4] [--out-dir W/handoff]
                     [--record-start 01:00:00:00] [--title NAME]
       export_edl.py --alpha                                   # how to export overlays as ProRes 4444
       export_edl.py --encode-alpha "W/render/front/%05d.png" --fps 30 --out front_4444.mov

Source in/out come from cutlist.json (source seconds), record in/out run back to back on the cut
timeline. Frame counts use the same rule as FFmpeg's trim (first frame at/after the in point), so
the record total matches the frames in cut.mp4. Plan times are on the cut timeline -> markers.
"""
import argparse, json, os, pathlib, re, subprocess, sys
from fractions import Fraction
from xml.sax.saxutils import escape, quoteattr
from vs_common import load_json, probe, log, run

ALPHA_HELP = """Overlay layers as ProRes 4444 with alpha (for an editor to stack over their own grade):
  1. python render.py W/plan.json --keep         # keeps W/render/<layer>/%05d.png (RGBA, front/behind/bg)
  2. python export_edl.py --encode-alpha "W/render/front/%05d.png" --fps 30 --out W/handoff/front_4444.mov
     (repeat for 'behind'; 'bg' is opaque). In Python: overlay_to_prores(pattern, fps, out).
  The .mov is prores_ks profile 4444, yuva444p10le, 16-bit alpha; it lines up with the cut timeline at frame 0."""


def overlay_to_prores(frames_dir_pattern, fps, out):
    """Encode a PNG sequence with alpha (e.g. render/front/%05d.png) to ProRes 4444 + alpha."""
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    run(["ffmpeg", "-y", "-hide_banner", "-framerate", str(fps), "-i", frames_dir_pattern, "-c:v", "prores_ks",
         "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", "-vendor", "apl0", out])
    return out


# ------------------------------------------------------------------ timing
def frame_rate(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=r_frame_rate:stream_tags=timecode:format_tags=timecode", "-of", "json", path],
                         stdout=subprocess.PIPE, text=True).stdout
    d = json.loads(out or "{}")
    st = (d.get("streams") or [{}])[0]
    num, den = (st.get("r_frame_rate") or "30/1").split("/")
    tc = (st.get("tags") or {}).get("timecode") or (d.get("format", {}).get("tags") or {}).get("timecode")
    return Fraction(int(num), int(den)), tc


def frames_at(t, fps):
    """Index of the first frame at or after t (FFmpeg trim keeps frames with pts >= start)."""
    x = Fraction(t).limit_denominator(100000) * fps
    return int(-(-x // 1)) if x - int(x) > Fraction(1, 10000) else int(x)


def tc_to_frames(tc, fps):
    nom = round(float(fps))
    h, m, s, f = [int(x) for x in re.split(r"[:;.]", tc)]
    total = (h * 3600 + m * 60 + s) * nom + f
    if ";" in tc or (nom in (30, 60) and fps.denominator == 1001):      # drop-frame
        drop = 2 * nom // 30
        mins = h * 60 + m
        total -= drop * (mins - mins // 10)
    return total


def frames_to_tc(n, fps):
    nom = round(float(fps))
    df = fps.denominator == 1001 and nom in (30, 60)
    if df:
        drop, per10 = 2 * nom // 30, nom * 600 - 9 * (2 * nom // 30)
        d, mrem = divmod(n, per10)
        n += 9 * drop * d + (drop * ((mrem - drop) // (nom * 60 - drop)) if mrem > drop else 0)
    f = n % nom; s = n // nom
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}{';' if df else ':'}{f:02d}"


# ------------------------------------------------------------------ model
def build_events(cutlist, fps, src_tc0=0):
    """[{n, src_in, src_out, rec_in, rec_out}] in frames; record is relative (0 = first frame of the cut)."""
    ev, rec = [], 0
    for i, s in enumerate(cutlist["segments"]):
        a, b = frames_at(s["src_start"], fps), frames_at(s["src_end"], fps)
        if b <= a:
            continue
        ev.append({"n": i + 1, "src_in": a + src_tc0, "src_out": b + src_tc0, "rec_in": rec, "rec_out": rec + b - a})
        rec += b - a
    return ev


def plan_markers(plan, fps):
    out = []
    for e in (plan or {}).get("elements", []):
        if "start" not in e:
            continue
        label = e.get("text") or e.get("title") or e.get("name") or e.get("kicker") or e.get("kind") or ""
        out.append({"frame": frames_at(float(e["start"]), fps), "dur": max(1, frames_at(float(e.get("end", e["start"])), fps) - frames_at(float(e["start"]), fps)),
                    "name": f"{e['type']}: {label}"[:80].strip(": "), "color": "YELLOW" if e.get("layer") == "behind" else "BLUE"})
    for z in (plan or {}).get("speaker", {}).get("zooms", []):
        out.append({"frame": frames_at(z["start"], fps), "dur": max(1, frames_at(z["end"], fps) - frames_at(z["start"], fps)),
                    "name": f"zoom {float(z.get('scale', 1)):.3g}x", "color": "GREEN"})
    return sorted(out, key=lambda m: m["frame"])


# ------------------------------------------------------------------ writers
def reel_name(path):
    return (re.sub(r"[^A-Za-z0-9]", "", os.path.splitext(os.path.basename(path))[0]).upper() or "AX")[:8]


def write_edl(events, markers, fps, path, title, src_path, rec0):
    nom = round(float(fps))
    df = fps.denominator == 1001 and nom in (30, 60)
    reel, clip = reel_name(src_path), os.path.basename(src_path)
    L = [f"TITLE: {title}", f"FCM: {'DROP FRAME' if df else 'NON-DROP FRAME'}", ""]
    for e in events:
        T = lambda n: frames_to_tc(n, fps)
        L.append(f"{e['n']:03d}  {reel:<8} AA/V  C        {T(e['src_in'])} {T(e['src_out'])} {T(rec0 + e['rec_in'])} {T(rec0 + e['rec_out'])}")
        L += [f"* FROM CLIP NAME: {clip}", f"* SOURCE FILE: {os.path.abspath(src_path)}"]
        for m in markers:
            if e["rec_in"] <= m["frame"] < e["rec_out"]:
                L.append(f"* LOC: {T(rec0 + m['frame'])} {m['color']:<7} {m['name']}")
        L.append("")
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(L))


def _t(frames, fps):
    v = Fraction(frames) / fps
    return f"{v.numerator}s" if v.denominator == 1 else f"{v.numerator}/{v.denominator}s"


def write_fcpxml(events, markers, fps, path, title, src_path, info, rec0, src0=0):
    w, h = info["width"], info["height"]
    src_frames = frames_at(info["duration"], fps)
    total = events[-1]["rec_out"] if events else 0
    clips = []
    for e in events:
        ms = "".join(f'\n            <marker start="{_t(e["src_in"] + m["frame"] - e["rec_in"], fps)}" duration="{_t(1, fps)}" value={quoteattr(m["name"])}/>'
                     for m in markers if e["rec_in"] <= m["frame"] < e["rec_out"])
        clips.append(f'          <asset-clip ref="r2" name={quoteattr(os.path.basename(src_path))} offset="{_t(rec0 + e["rec_in"], fps)}" '
                     f'start="{_t(e["src_in"], fps)}" duration="{_t(e["rec_out"] - e["rec_in"], fps)}" tcFormat="NDF">{ms}\n          </asset-clip>')
    audio = (f' hasAudio="1" audioSources="1" audioChannels="2" audioRate="48000"' if info.get("has_audio") else "")
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.10">
  <resources>
    <format id="r1" frameDuration="{_t(1, fps)}" width="{w}" height="{h}" colorSpace="1-1-1 (Rec. 709)"/>
    <asset id="r2" name={quoteattr(os.path.basename(src_path))} start="{_t(src0, fps)}" duration="{_t(src_frames, fps)}" hasVideo="1" format="r1"{audio}>
      <media-rep kind="original-media" src={quoteattr(pathlib.Path(os.path.abspath(src_path)).as_uri())}/>
    </asset>
  </resources>
  <library>
    <event name="Video Studio">
      <project name={quoteattr(title)}>
        <sequence format="r1" duration="{_t(total, fps)}" tcStart="{_t(rec0, fps)}" tcFormat="{'DF' if fps.denominator == 1001 else 'NDF'}" audioLayout="stereo" audioRate="48k">
          <spine>
{chr(10).join(clips)}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
'''
    open(path, "w", encoding="utf-8").write(xml)


def _rt(v, fps):
    return {"OTIO_SCHEMA": "RationalTime.1", "rate": float(fps), "value": float(v)}


def _tr(a, d, fps):
    return {"OTIO_SCHEMA": "TimeRange.1", "start_time": _rt(a, fps), "duration": _rt(d, fps)}


def otio_dict(events, markers, fps, title, src_path, info, rec0):
    ref = {"OTIO_SCHEMA": "ExternalReference.1", "name": os.path.basename(src_path), "metadata": {},
           "available_range": _tr(0, frames_at(info["duration"], fps), fps), "available_image_bounds": None,
           "target_url": pathlib.Path(os.path.abspath(src_path)).as_uri()}

    def clip(e, kind):
        return {"OTIO_SCHEMA": "Clip.2", "name": f"{os.path.basename(src_path)} #{e['n']}", "metadata": {},
                "source_range": _tr(e["src_in"], e["src_out"] - e["src_in"], fps), "effects": [], "markers": [], "enabled": True,
                "media_references": {"DEFAULT_MEDIA": ref}, "active_media_reference_key": "DEFAULT_MEDIA"}

    def track(kind):
        return {"OTIO_SCHEMA": "Track.1", "name": kind[0] + "1", "metadata": {}, "source_range": None, "effects": [],
                "markers": [], "enabled": True, "kind": kind, "children": [clip(e, kind) for e in events]}

    mk = [{"OTIO_SCHEMA": "Marker.2", "name": m["name"], "metadata": {}, "color": m["color"], "comment": "",
           "marked_range": _tr(m["frame"], m["dur"], fps)} for m in markers]
    return {"OTIO_SCHEMA": "Timeline.1", "name": title, "metadata": {"generator": "video-studio export_edl.py"},
            "global_start_time": _rt(rec0, fps),
            "tracks": {"OTIO_SCHEMA": "Stack.1", "name": "tracks", "metadata": {}, "source_range": None, "effects": [],
                       "markers": mk, "enabled": True, "children": [track("Video")] + ([track("Audio")] if info.get("has_audio") else [])}}


def write_otio(d, path):
    try:
        import opentimelineio as otio
        otio.adapters.write_to_file(otio.adapters.read_from_string(json.dumps(d), "otio_json"), path)
        return "opentimelineio"
    except ImportError:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        return "hand-written"


# ------------------------------------------------------------------ main
def export(work_or_cutlist, plan_path=None, source=None, out_dir=None, record_start="01:00:00:00", title=None):
    cl_path = work_or_cutlist if work_or_cutlist.endswith(".json") else os.path.join(work_or_cutlist, "cutlist.json")
    work = os.path.dirname(os.path.abspath(cl_path))
    cutlist = load_json(cl_path)
    source = source or os.path.join(work, "source.mp4")
    plan_path = plan_path or (os.path.join(work, "plan.json") if os.path.exists(os.path.join(work, "plan.json")) else None)
    plan = load_json(plan_path) if plan_path else None
    fps, src_tc = frame_rate(source)
    info = probe(source)
    src0 = tc_to_frames(src_tc, fps) if src_tc else 0
    rec0 = tc_to_frames(record_start, fps)
    events = build_events(cutlist, fps, src0)
    markers = plan_markers(plan, fps)
    out_dir = out_dir or os.path.join(work, "handoff")
    os.makedirs(out_dir, exist_ok=True)
    title = title or os.path.basename(work)
    paths = {k: os.path.join(out_dir, f"{title}.{k}") for k in ("edl", "fcpxml", "otio")}
    write_edl(events, markers, fps, paths["edl"], title, source, rec0)
    write_fcpxml(events, markers, fps, paths["fcpxml"], title, source, info, rec0, src0)
    how = write_otio(otio_dict(events, markers, fps, title, source, info, rec0), paths["otio"])
    total = events[-1]["rec_out"] if events else 0
    log(f"{len(events)} events, {total} frames ({total / float(fps):.3f}s) @ {float(fps):g} fps, {len(markers)} markers; OTIO {how}")
    return {"events": events, "markers": markers, "fps": fps, "files": paths, "record_frames": total, "otio": how}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work", nargs="?")
    ap.add_argument("--plan"); ap.add_argument("--source"); ap.add_argument("--out-dir")
    ap.add_argument("--record-start", default="01:00:00:00"); ap.add_argument("--title")
    ap.add_argument("--alpha", action="store_true", help="print how to export overlay layers as ProRes 4444")
    ap.add_argument("--encode-alpha", metavar="PATTERN"); ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.alpha:
        print(ALPHA_HELP); return
    if a.encode_alpha:
        log(f"ProRes 4444 -> {overlay_to_prores(a.encode_alpha, a.fps, a.out or 'overlay_4444.mov')}"); return
    if not a.work:
        ap.error("WORK_OR_CUTLIST is required")
    r = export(a.work, a.plan, a.source, a.out_dir, a.record_start, a.title)
    for k, p in r["files"].items():
        log(f"{k} -> {p}")


if __name__ == "__main__":
    main()
