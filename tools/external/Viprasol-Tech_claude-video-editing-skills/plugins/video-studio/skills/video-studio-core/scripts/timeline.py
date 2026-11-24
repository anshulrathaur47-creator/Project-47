#!/usr/bin/env python3
"""Multi-clip timeline: assemble several clips into one video the rest of the pipeline can use.

  timeline.py build SPEC.json --work W [--no-transcribe] [--model small]
  timeline.py auto FOLDER_OR_FILES... --work W --mode montage|story|highlights [--duration 30]
                   [--music track.wav] [--format 9:16] [--transition cut] [--beats-per-shot 0] [--dry-run]

Writes into W: assembled.mp4 (also copied to cut.mp4 and source.mp4), audio16k.wav, cutlist.json,
words.json + transcript.json (re-timed per-clip words, or a fresh transcription of the result),
timeline.json (the resolved spec with every computed time). make_plan.py / render.py / finish.py
then run unchanged. Full spec reference: references/timeline.md.

Spec (times in seconds; `in`/`out`/`at` are source-clip seconds):
{"format": "16:9", "fps": 30,
 "clips": [{"src": "a.mp4", "in": 0, "out": 5, "speed": 1, "audio": "keep|mute|duck", "volume": 1,
            "transition": {"type": "cut|dip-black|dip-white|whip|zoom|<any xfade name>", "dur": 0.4},  # INTO this clip
            "jcut": 0.5, "lcut": 0.3,            # audio leads its picture / trails into the next clip
            "speedRamp": [{"at": 2.0, "rate": 0.4, "ramp": 0.5}], "smooth": false,
            "freeze": [{"at": 3.0, "dur": 1.0}], "freezeEnd": 0, "reverse": false,
            "fit": "cover|contain", "reframe": "face|none", "kenburns": true, "color": {"contrast": 1.05},
            "words": "transcript.json"}],
 "music": {"src": "music.wav", "volume": 0.25, "duck": true, "fadeOut": 1.5, "start": 0}}
"""
import argparse, glob, os, shutil, subprocess, sys, tempfile
import numpy as np
from vs_common import probe, run, log, die, save_json, load_json, parse_format, need

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from track import piecewise_expr  # noqa: E402

XFADE = ("fade wipeleft wiperight wipeup wipedown slideleft slideright slideup slidedown circlecrop rectcrop "
         "distance fadeblack fadewhite radial smoothleft smoothright smoothup smoothdown circleopen circleclose "
         "vertopen vertclose horzopen horzclose dissolve pixelize diagtl diagtr diagbl diagbr hlslice hrslice "
         "vuslice vdslice hblur fadegrays wipetl wipetr wipebl wipebr squeezeh squeezev zoomin fadefast fadeslow "
         "hlwind hrwind vuwind vdwind coverleft coverright coverup coverdown revealleft revealright revealup "
         "revealdown").split()
# "dissolve" = editor-speak cross-dissolve; FFmpeg's own `dissolve` is random-pixel dither, kept as dither-dissolve
ALIAS = {"dip-black": "fadeblack", "dip-white": "fadewhite", "crossfade": "fade", "dissolve": "fade",
         "dither-dissolve": "dissolve", "whip": "slideleft", "zoom": "zoomin", "push": "slideleft"}
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
VID_EXT = (".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".mts")
CUT_XF = 0.03          # audio crossfade on a plain cut (click-free edit)
RATE_MIN, RATE_MAX = 0.25, 4.0
RATE_STEP = 1.06       # audio of speed ramps: new constant-rate piece every 6 % change
MIN_PIECE = 0.08       # ...but no ramp audio piece shorter than this (output s): fewer joins
GUARD = 0.1            # extra source fed to atempo around each piece (s)
TEMPO_LEAD = 0.021     # atempo output runs about half its window (~21 ms) ahead of its input
WHIP_BLUR = 48         # px of horizontal box blur on whip transitions
DUCK_GAIN = 0.25       # clip audio "duck"


# ------------------------------------------------------------------ clip time maps
def rate_fn(clip):
    base, keys = clip.get("speed", 1.0), sorted(clip.get("speedRamp", []), key=lambda k: k["at"])

    def r(s):
        v = base
        for k in keys:
            rp = max(float(k.get("ramp", 0.3)), 1e-3)
            if s >= k["at"]:
                v = k["rate"]
            elif s > k["at"] - rp:
                x = (s - (k["at"] - rp)) / rp
                v = v + (k["rate"] - v) * x * x * (3 - 2 * x)   # smoothstep ease
                break
            else:
                break
        return min(RATE_MAX, max(RATE_MIN, v))
    return r


def time_map(clip, fps):
    """Grid of (source time rel. to `in`, output time) without freezes, plus freezes in output time."""
    L = clip["out"] - clip["in"]
    h = 1.0 / (fps * 4)
    s = np.append(np.arange(0, L, h), L)
    r = rate_fn(clip)
    rv = np.array([r(clip["in"] + x) for x in s])
    T = np.concatenate([[0], np.cumsum(np.diff(s) * 0.5 * (1 / rv[1:] + 1 / rv[:-1]))])
    fr = sorted([(f["at"] - clip["in"], f["dur"]) for f in clip.get("freeze", []) if clip["in"] <= f["at"] <= clip["out"]])
    if clip.get("freezeEnd"):
        fr.append((L, float(clip["freezeEnd"])))
    return s, T, fr


def with_freezes(s, T, fr):
    T = T.copy()
    for at, d in fr:
        T[s >= at - 1e-9] += d
    return T


def out_time(s_rel, s, T, fr, r_in, r_out):
    """Source (rel. to in, may lie outside the clip for J/L audio) -> output time rel. to clip start."""
    Tf = with_freezes(s, T, fr)
    if s_rel < 0:
        return s_rel / r_in
    if s_rel > s[-1]:
        return Tf[-1] + (s_rel - s[-1]) / r_out
    return float(np.interp(s_rel, s, Tf))


# ------------------------------------------------------------------ spec loading
def load_spec(spec, base):
    fmt = spec.get("format", "16:9")
    W, H = (spec["width"], spec["height"]) if "width" in spec else parse_format(fmt)
    fps = float(spec.get("fps", 30))
    clips = []
    for i, c in enumerate(spec["clips"]):
        c = dict(c)
        src = c["src"] if os.path.isabs(c["src"]) else os.path.join(base, c["src"])
        if not os.path.exists(src):
            die(f"clip {i}: {src} not found")
        c["src"] = os.path.abspath(src)
        c["image"] = c["src"].lower().endswith(IMG_EXT)
        if c["image"]:
            c.setdefault("in", 0.0)
            c["out"] = c["in"] + float(c.get("dur", c.get("out", 3.0)) if "dur" in c else c.get("out", 3.0))
            c["has_audio"] = False
        else:
            info = probe(c["src"])
            c["has_audio"] = info["has_audio"]
            c["src_dur"] = info["duration"]
            c["in"] = max(0.0, float(c.get("in", 0)))
            c["out"] = min(info["duration"], float(c.get("out", info["duration"])))
        if c["out"] - c["in"] < 1.0 / fps:
            die(f"clip {i}: out must be after in")
        tr = c.get("transition") or {"type": "cut"}
        if isinstance(tr, str):
            tr = {"type": tr}
        name = ALIAS.get(tr.get("type", "cut"), tr.get("type", "cut"))
        if name not in XFADE and name != "cut":
            die(f"clip {i}: unknown transition '{tr['type']}'. Use cut, dip-black, dip-white, whip, zoom or: {' '.join(XFADE)}")
        c["_tr"] = {"type": tr.get("type", "cut"), "xfade": None if name == "cut" or i == 0 else name,
                    "dur": 0.0 if name == "cut" or i == 0 else float(tr.get("dur", 0.4))}
        if c.get("reverse") and (c.get("jcut") or c.get("lcut")):
            log(f"clip {i}: J/L cuts ignored on a reversed clip"); c["jcut"] = c["lcut"] = 0
        clips.append(c)
    return W, H, fps, clips


def resolve(clips, fps):
    """Compute every clip's output duration, start, transition and audio window (frame-exact)."""
    q = lambda x: round(x * fps) / fps
    for c in clips:
        s, T, fr = time_map(c, fps)
        c["_map"] = (s, T, fr)
        c["D"] = q(with_freezes(s, T, fr)[-1])
    for i, c in enumerate(clips):
        if c["_tr"]["dur"]:
            c["_tr"]["dur"] = q(min(c["_tr"]["dur"], 0.5 * c["D"], 0.5 * clips[i - 1]["D"]))
            if c["_tr"]["dur"] < 1 / fps:
                c["_tr"].update(dur=0.0, xfade=None)
    S = 0.0
    for i, c in enumerate(clips):
        if i:
            S = q(S + clips[i - 1]["D"] - c["_tr"]["dur"])
        c["S"] = S
    total = clips[-1]["S"] + clips[-1]["D"]
    # audio edit points: mid-transition, moved earlier by this clip's J-cut, later by the previous L-cut
    E = [0.0] + [c["S"] + c["_tr"]["dur"] / 2 - float(c.get("jcut", 0)) + float(clips[i - 1].get("lcut", 0))
                 for i, c in enumerate(clips) if i] + [total]
    X = [0.0] + [max(c["_tr"]["dur"], CUT_XF) for c in clips[1:]] + [0.0]
    for i, c in enumerate(clips):
        a0 = max(0.0, E[i] - X[i] / 2) if i else 0.0
        a1 = min(total, E[i + 1] + X[i + 1] / 2) if i < len(clips) - 1 else total
        c["A"] = (a0, a1)
        c["xf"] = (X[i] if i else 0.0, X[i + 1] if i < len(clips) - 1 else 0.0)
    return total


# ------------------------------------------------------------------ per-clip renders
def video_filter(c, W, H, fps, work, nxt_tr):
    s, T, fr = c["_map"]
    L = c["out"] - c["in"]
    chain = []
    if c.get("reframe") == "face" and not c["image"]:
        import track
        info = probe(c["src"])
        tp = os.path.join(work, "tracks", os.path.splitext(os.path.basename(c["src"]))[0] + ".json")
        tr = load_json(tp) if os.path.exists(tp) else track.analyze(c["src"])
        save_json(tp, tr)
        chain.append(track.follow_crop_filter(tr, info["width"], info["height"], W, H, info["fps"], t0=c["in"]))
    chain.append(f"trim=start=0:end={L:.4f},setpts=PTS-STARTPTS")
    Tf = with_freezes(s, T, fr)
    if not (np.allclose(Tf, s) and not fr):
        chain.append(f"setpts='({piecewise_expr(s, Tf, tol=0.2 / fps, var='T')})/TB'")
    smooth = c.get("smooth") and min(rate_fn(c)(c["in"] + x) for x in s[::8]) < 1
    chain.append(f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:vsbmc=1" if smooth else f"fps={fps}:start_time=0")
    if c.get("reframe") != "face" or c["image"]:
        if c.get("fit") == "contain":
            chain.append(f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black")
        elif c["image"] and c.get("kenburns", True):
            n = max(1, int(round(c["D"] * fps)))
            chain.append(f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
                         f"zoompan=z='1+0.08*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={fps}")
        else:
            chain.append(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}")
    col = c.get("color") or {}
    if col:
        chain.append("eq=" + ":".join(f"{k}={v}" for k, v in col.items() if k in ("brightness", "contrast", "saturation", "gamma")))
    chain.append(f"setsar=1,tpad=stop_mode=clone:stop_duration={c['D'] + 1:.3f},trim=duration={c['D']:.4f}")
    if c.get("reverse"):
        chain.append("reverse")
    if c["_tr"]["type"] == "whip" and c["_tr"]["dur"]:
        chain.append(f"avgblur=sizeX={WHIP_BLUR}:sizeY=1:enable='lt(t,{c['_tr']['dur']:.3f})'")
    if nxt_tr and nxt_tr["type"] == "whip" and nxt_tr["dur"]:
        chain.append(f"avgblur=sizeX={WHIP_BLUR}:sizeY=1:enable='gte(t,{c['D'] - nxt_tr['dur']:.3f})'")
    chain.append("format=yuv420p")
    return ",".join(chain)


def atempo(r):
    parts = []
    while r < 0.5:
        parts.append("atempo=0.5"); r /= 0.5
    while r > 2.0:
        parts.append("atempo=2.0"); r /= 2.0
    if abs(r - 1) > 1e-4:
        parts.append(f"atempo={r:.5f}")
    return parts


def audio_pieces(c, ext_head, ext_tail):
    """Constant-rate source pieces covering output [-ext_head, D + ext_tail] of this clip.
    Items: (src_a, src_b, rate) absolute source seconds, or (None, dur, None) for silence."""
    s, T, fr = c["_map"]
    r = rate_fn(c)
    r_in, r_out = r(c["in"]), r(c["out"])
    pieces = []
    if ext_head > 0:
        a = c["in"] - ext_head * r_in
        if a < 0:
            pieces.append((None, -a / r_in, None)); a = 0.0
        pieces.append((a, c["in"], r_in))
    lv = np.round(np.log(np.array([r(c["in"] + x) for x in s])) / np.log(RATE_STEP))
    cuts = [0] + [k for k in range(1, len(s)) if lv[k] != lv[k - 1]] + [len(s) - 1]
    fz = list(fr)
    for k0, k1 in zip(cuts[:-1], cuts[1:]):
        bounds = [s[k0]] + [at for at, _ in fz if s[k0] < at < s[k1]] + [s[k1]]
        for a, b in zip(bounds[:-1], bounds[1:]):
            for at, d in fz:
                if abs(at - a) < 1e-9:
                    pieces.append((None, d, None))
            if b > a:
                rate = (b - a) / max(1e-9, np.interp(b, s, T) - np.interp(a, s, T))
                pieces.append((c["in"] + a, c["in"] + b, rate))
    for at, d in fz:
        if at >= s[-1] - 1e-9:
            pieces.append((None, d, None))
    if ext_tail > 0:
        pieces.append((c["out"], c["out"] + ext_tail * r_out, r_out))
    return pieces


def merge_pieces(pieces):
    """Join source-contiguous ramp steps until each lasts MIN_PIECE of output (rate = exact span ratio)."""
    out = []
    for p in pieces:
        q = out[-1] if out else None
        if (p[0] is not None and q and q[0] is not None and abs(q[1] - p[0]) < 1e-6
                and (q[1] - q[0]) / q[2] < MIN_PIECE):
            a, b = q[0], p[1]
            out[-1] = (a, b, (b - a) / ((q[1] - q[0]) / q[2] + (p[1] - p[0]) / p[2]))
        else:
            out.append(p)
    if len(out) > 1 and out[-1][0] is not None and out[-2][0] is not None and abs(out[-2][1] - out[-1][0]) < 1e-6 \
            and (out[-1][1] - out[-1][0]) / out[-1][2] < MIN_PIECE:   # short last step joins its left neighbour
        (a, m, r1), (_, b, r2) = out[-2], out.pop()
        out[-1] = (a, b, (b - a) / ((m - a) / r1 + (b - m) / r2))
    return out


def piece_filter(pa, pb, rate):
    """One constant-rate source piece at its exact output length. atempo outputs nothing for <25 ms of
    input, runs ~TEMPO_LEAD ahead and loses up to ~25 ms at its edges, so it gets GUARD extra source on
    both sides and the kept part is cut out of the middle."""
    d = (pb - pa) / rate
    fmt = "asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    st = atempo(rate)
    if not st:
        chain = f"[0:a]atrim=start={pa:.5f}:end={pb:.5f},{fmt}"
    else:
        g = min(GUARD, pa)
        lead, k = 0.0, 1.0
        for p in reversed(st):              # each stage's lead, seen through the stages after it
            r = float(p.split("=")[1]); lead += TEMPO_LEAD / k; k *= r
        skip = g / rate - lead
        chain = (f"[0:a]atrim=start={pa - g:.5f}:end={pb + GUARD:.5f},{fmt}," + ",".join(st)
                 + (f",atrim=start={skip:.5f}" if skip >= 0 else f",adelay={-skip * 1000:.2f}:all=1"))
    # exact length; N/SR pts keep concat valid even when a filter emitted no frame at all
    return chain + f",apad=whole_dur={d:.5f},asetpts=N/SR/TB,atrim=duration={d:.5f}"


def render_clip(i, c, W, H, fps, work, tmp, nxt_tr):
    vout = os.path.join(tmp, f"clip{i:03d}.mp4")
    aout = os.path.join(tmp, f"clip{i:03d}.wav")
    L = c["out"] - c["in"]
    if c["image"]:
        vin = ["-loop", "1", "-framerate", str(fps), "-t", f"{L + 0.5:.3f}", "-i", c["src"]]
    else:
        vin = ["-ss", f"{c['in']:.4f}", "-t", f"{L + 0.2:.4f}", "-i", c["src"]]
    gf = os.path.join(tmp, f"clip{i:03d}.v.txt")
    with open(gf, "w") as f:
        f.write(f"[0:v]{video_filter(c, W, H, fps, work, nxt_tr)}[v]")
    run(["ffmpeg", "-y", "-hide_banner"] + vin + ["-filter_complex_script", gf, "-map", "[v]", "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-g", str(int(fps)), vout])
    # audio window in this clip's own output time
    a0, a1 = c["A"][0] - c["S"], c["A"][1] - c["S"]
    eh, et = max(0.0, -a0), max(0.0, a1 - c["D"])
    total = eh + c["D"] + et
    mode = c.get("audio", "keep")
    if mode == "mute" or not c["has_audio"]:
        graph = f"anullsrc=r=48000:cl=stereo,atrim=duration={a1 - a0:.4f}[a]"
    else:
        parts, labels = [], []
        for k, (pa, pb, rate) in enumerate(merge_pieces(audio_pieces(c, eh, et))):
            parts.append((f"anullsrc=r=48000:cl=stereo,atrim=duration={pb:.5f}" if pa is None
                          else piece_filter(pa, pb, rate)) + f"[p{k}]")
            labels.append(f"[p{k}]")
        vol = float(c.get("volume", 1.0)) * (DUCK_GAIN if mode == "duck" else 1.0)
        tail = f"areverse," if c.get("reverse") else ""
        xin, xout = c["xf"]
        length = a1 - a0
        graph = (";".join(parts) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=0:a=1,{tail}"
                 f"apad=whole_dur={total:.4f},atrim=start={a0 + eh:.4f}:end={a1 + eh:.4f},asetpts=PTS-STARTPTS,"
                 f"volume={vol:.3f}"
                 + (f",afade=t=in:d={xin:.3f}" if xin else "")
                 + (f",afade=t=out:st={length - xout:.4f}:d={xout:.3f}" if xout else "") + "[a]")
    gf2 = os.path.join(tmp, f"clip{i:03d}.a.txt")
    with open(gf2, "w") as f:
        f.write(graph)
    ain = [] if mode == "mute" or not c["has_audio"] else ["-i", c["src"]]
    run(["ffmpeg", "-y", "-hide_banner"] + ain + ["-filter_complex_script", gf2, "-map", "[a]",
         "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", aout])
    return vout, aout


# ------------------------------------------------------------------ assembly
def assemble(clips, W, H, fps, total, music, work, tmp):
    inputs, g = [], []
    for c in clips:
        inputs += ["-i", c["_v"]]
    for i, c in enumerate(clips):
        g.append(f"[{i}:v]fps={fps},settb=AVTB,format=yuv420p,setsar=1[n{i}]")
    cur = "n0"
    for i in range(1, len(clips)):
        tr = clips[i]["_tr"]
        if tr["xfade"]:
            g.append(f"[{cur}][n{i}]xfade=transition={tr['xfade']}:duration={tr['dur']:.4f}:offset={clips[i]['S']:.4f}[x{i}]")
        else:
            g.append(f"[{cur}][n{i}]concat=n=2:v=1:a=0,settb=AVTB[x{i}]")
        cur = f"x{i}"
    g.append(f"[{cur}]trim=duration={total:.4f},format=yuv420p[vout]")
    n = len(clips)
    for i, c in enumerate(clips):
        inputs += ["-i", c["_a"]]
        ms = int(round(c["A"][0] * 1000))
        g.append(f"[{n + i}:a]adelay={ms}:all=1[d{i}]")
    g.append("".join(f"[d{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:duration=longest,"
             f"apad=whole_dur={total:.4f},atrim=duration={total:.4f}[dia]")
    amap = "[dia]"
    if music:
        inputs += ["-stream_loop", "-1", "-i", music["src"]]
        mi = 2 * n
        fo = float(music.get("fadeOut", 1.5))
        g.append(f"[{mi}:a]atrim=start={float(music.get('start', 0)):.3f},asetpts=PTS-STARTPTS,atrim=duration={total:.4f},"
                 f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume={float(music.get('volume', 0.25)):.3f},"
                 f"afade=t=out:st={max(0, total - fo):.3f}:d={fo:.3f}[mus]")
        if music.get("duck", True) and any(c.get("audio", "keep") != "mute" and c["has_audio"] for c in clips):
            g.append("[dia]asplit=2[dia1][key]")
            g.append("[mus][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[mduck]")
            g.append("[dia1][mduck]amix=inputs=2:normalize=0:duration=first[aout]")
        else:
            g.append("[dia][mus]amix=inputs=2:normalize=0:duration=first[aout]")
        amap = "[aout]"
    gf = os.path.join(tmp, "assemble.txt")
    with open(gf, "w") as f:
        f.write(";\n".join(g))
    out = os.path.join(work, "assembled.mp4")
    run(["ffmpeg", "-y", "-hide_banner"] + inputs + ["-filter_complex_script", gf, "-map", "[vout]", "-map", amap,
         "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(fps),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
    return out


def retime_words(clips, fps):
    """Per-clip `words` files (source time) -> words on the assembled timeline. None if a clip lacks them."""
    words, used = [], 0
    for c in clips:
        if c.get("audio", "keep") == "mute" or not c["has_audio"]:
            continue
        used += 1
        if not c.get("words"):
            return None
        wf = c["words"]
        ws = load_json(wf)["words"] if isinstance(wf, str) else wf
        s, T, fr = c["_map"]
        r = rate_fn(c)
        a0, a1 = c["A"]
        for w in ws:
            ts = c["S"] + out_time(w["start"] - c["in"], s, T, fr, r(c["in"]), r(c["out"]))
            te = c["S"] + out_time(w["end"] - c["in"], s, T, fr, r(c["in"]), r(c["out"]))
            if c.get("reverse"):
                continue
            if ts >= a0 - 1e-3 and te <= a1 + 1e-3:
                nw = dict(w); nw["start"], nw["end"] = round(ts, 3), round(te, 3)
                words.append(nw)
    if not used:  # no clip carries audio (e.g. photos + voice-over as music): let the caller transcribe
        return None
    return sorted(words, key=lambda w: w["start"])


def build(spec, work, transcribe=True, model="small", spec_base="."):
    need("ffmpeg")
    os.makedirs(work, exist_ok=True)
    W, H, fps, clips = load_spec(spec, spec_base)
    total = resolve(clips, fps)
    log(f"{len(clips)} clips -> {total:.3f}s at {W}x{H} {fps:g} fps")
    tmp = tempfile.mkdtemp(prefix="vs_tl_", dir=work)
    try:
        for i, c in enumerate(clips):
            nxt = clips[i + 1]["_tr"] if i + 1 < len(clips) else None
            log(f"clip {i + 1}/{len(clips)}: {os.path.basename(c['src'])} {c['in']:.2f}-{c['out']:.2f} -> {c['D']:.3f}s")
            c["_v"], c["_a"] = render_clip(i, c, W, H, fps, work, tmp, nxt)
        music = spec.get("music")
        if music:
            music = dict(music)
            if not os.path.isabs(music["src"]):
                music["src"] = os.path.abspath(os.path.join(spec_base, music["src"]))
        out = assemble(clips, W, H, fps, total, music, work, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for name in ("cut.mp4", "source.mp4"):
        shutil.copyfile(out, os.path.join(work, name))
    run(["ffmpeg", "-y", "-hide_banner", "-i", out, "-vn", "-ac", "1", "-ar", "16000", os.path.join(work, "audio16k.wav")])
    segs = [{"clip": i, "src": c["src"], "src_start": round(c["in"], 3), "src_end": round(c["out"], 3),
             "out_start": round(c["S"], 3), "out_end": round(c["S"] + c["D"], 3),
             "audio_start": round(c["A"][0], 3), "audio_end": round(c["A"][1], 3),
             "speed": c.get("speed", 1), "ramped": bool(c.get("speedRamp")),
             "transition": c["_tr"]["type"] if i else None, "transition_dur": c["_tr"]["dur"]} for i, c in enumerate(clips)]
    src_total = sum(c["out"] - c["in"] for c in clips)
    save_json(os.path.join(work, "cutlist.json"), {"segments": segs, "duration": round(total, 3),
                                                   "removed_seconds": round(max(0.0, src_total - total), 2),
                                                   "kind": "timeline"})
    resolved = dict(spec)
    resolved["clips"] = [{k: v for k, v in c.items() if not k.startswith("_")} for c in clips]
    save_json(os.path.join(work, "timeline.json"), resolved)
    words = retime_words(clips, fps)
    if words is not None:
        save_json(os.path.join(work, "transcript.json"), {"language": spec.get("language"), "words": words, "segments": []})
        log(f"re-timed {len(words)} words from per-clip transcripts")
    elif transcribe and (any(c.get("audio", "keep") != "mute" and c["has_audio"] for c in clips)
                         or (spec.get("music") or {}).get("voiceover")):  # VO laid as the spec's music track
        r = subprocess.run([sys.executable, os.path.join(HERE, "transcribe.py"), "--work", work, "--model", model])
        if r.returncode != 0:
            log("transcription failed; words.json not written")
    tp = os.path.join(work, "transcript.json")
    if os.path.exists(tp):
        tr = load_json(tp)
        save_json(os.path.join(work, "words.json"), {"language": tr.get("language"), "words": tr["words"],
                                                     "duration": round(total, 3)})
    got = probe(out)
    log(f"assembled.mp4 {got['width']}x{got['height']} {got['duration']:.3f}s (expected {total:.3f}s) -> {work}")
    return {"total": total, "clips": segs, "out": out}


# ------------------------------------------------------------------ auto assembly
def media_files(items):
    files = []
    for it in items:
        if os.path.isdir(it):
            files += [p for p in glob.glob(os.path.join(it, "*")) if p.lower().endswith(VID_EXT + IMG_EXT)]
        elif os.path.exists(it):
            files.append(it)
    files = sorted(set(os.path.abspath(f) for f in files), key=lambda p: (os.path.getmtime(p), os.path.basename(p)))
    if not files:
        die("no video or image files found")
    return files


def onset_beats(path):
    """Fallback beat tracker: spectral-flux onsets + tempo by autocorrelation + phase-aligned grid."""
    SR, HOP = 22050, 512
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         stdout=subprocess.PIPE).stdout
    x = np.frombuffer(raw, np.float32)
    n = (len(x) - 2048) // HOP
    if n < 10:
        return {"bpm": 0, "beats": [], "downbeats": []}
    frames = np.stack([x[k * HOP:k * HOP + 2048] for k in range(n)]) * np.hanning(2048)
    mag = np.log1p(np.abs(np.fft.rfft(frames, axis=1)))
    flux = np.maximum(0, np.diff(mag, axis=0)).sum(1)
    flux = np.concatenate([[0], flux - np.convolve(flux, np.ones(16) / 16, "same")]).clip(0)
    fr = SR / HOP
    lags = np.arange(int(fr * 60 / 200), int(fr * 60 / 60))
    ac = np.array([np.dot(flux[:-l], flux[l:]) for l in lags])
    ac *= np.exp(-0.5 * (np.log2(60 * fr / lags / 120)) ** 2)  # prefer ~120 bpm
    lag = lags[int(np.argmax(ac))]
    # sub-frame refinement: the period/phase whose grid collects the most onset energy
    idx = np.arange(len(flux))
    best = (-1, lag, 0)
    for P in np.linspace(lag - 1.5, lag + 1.5, 121):
        for ph in np.arange(0, P, 0.25):
            sc = np.interp(np.arange(ph, len(flux) - 1, P), idx, flux).sum()
            if sc > best[0]:
                best = (sc, P, ph)
    _, P, phase = best
    period = P / fr
    beats = np.arange(phase, len(flux) - 1, P) / fr + 1024 / SR   # frame index -> window centre
    bpm = 60.0 / period
    grid = np.arange(phase, len(flux) - 1, P)
    down = beats[int(np.argmax([np.interp(grid[k::4], idx, flux).sum() for k in range(4)]))::4]
    return {"bpm": round(bpm, 2), "beats": [round(float(b), 4) for b in beats], "downbeats": [round(float(b), 4) for b in down]}


def get_beats(music, work):
    bj = os.path.join(work, "beats.json")
    bp = os.path.join(HERE, "beats.py")
    if not os.path.exists(bj) and os.path.exists(bp):
        r = subprocess.run([sys.executable, bp, music, "--out", bj])
        if r.returncode != 0:
            log("beats.py failed; using the built-in onset tracker")
    if os.path.exists(bj):
        b = load_json(bj)
        log(f"beats from beats.json: {b.get('bpm')} bpm, {len(b['beats'])} beats")
        return b
    b = onset_beats(music)
    save_json(bj, b)
    log(f"built-in beat tracker: {b['bpm']} bpm, {len(b['beats'])} beats")
    return b


def shot_scores(path, shots, det=None):
    """Sharpness, exposure, motion and face presence per shot -> score 0..~4."""
    import cv2
    cap = cv2.VideoCapture(path)
    out = []
    for sh in shots:
        frames = []
        for f in (0.3, 0.5, 0.7):
            cap.set(cv2.CAP_PROP_POS_MSEC, (sh["start"] + f * (sh["end"] - sh["start"])) * 1000)
            ok, im = cap.read()
            if ok:
                frames.append(cv2.resize(im, (320, int(320 * im.shape[0] / im.shape[1]))))
        if not frames:
            out.append(0.0); continue
        g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
        sharp = np.mean([cv2.Laplacian(x, cv2.CV_64F).var() for x in g])
        bright = np.mean([x.mean() for x in g])
        motion = np.mean([np.abs(g[k].astype(int) - g[k - 1]).mean() for k in range(1, len(g))]) if len(g) > 1 else 0
        face = 0.0
        if det is not None:
            face = 1.0 if det(frames[len(frames) // 2][:, :, ::-1]) else 0.0
        sc = min(1.5, np.log1p(sharp) / 5) + (1 - abs(bright - 125) / 125) + min(1.0, motion / 12) + face
        out.append(round(float(sc), 3))
    cap.release()
    return out


def _face_det():
    try:
        import track
        return track._detector(0.5)
    except SystemExit:
        return None


def speech_regions(path, thresh_db=-35, min_gap=0.8, pad=0.2):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         stdout=subprocess.PIPE).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = 800  # 50 ms
    k = len(x) // hop
    if k == 0:
        return []
    db = 20 * np.log10(np.sqrt((x[:k * hop].reshape(k, hop) ** 2).mean(1)) + 1e-9)
    on = db > max(thresh_db, np.percentile(db, 95) - 30)
    regs, start = [], None
    for i, v in enumerate(np.append(on, False)):
        t = i * hop / 16000
        if v and start is None:
            start = t
        if not v and start is not None:
            if regs and start - regs[-1][1] < min_gap:
                regs[-1][1] = t
            else:
                regs.append([start, t])
            start = None
    dur = len(x) / 16000
    return [(max(0, a - pad), min(dur, b + pad)) for a, b in regs if b - a > 0.25]


def activity_curve(path, hz=4):
    """Loudness + motion per 1/hz s, both normalised 0..1."""
    import cv2
    info = probe(path)
    n = int(info["duration"] * hz)
    loud = np.zeros(n)
    if info["has_audio"]:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                             stdout=subprocess.PIPE).stdout
        x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        hop = 16000 // hz
        k = min(n, len(x) // hop)
        loud[:k] = np.sqrt((x[:k * hop].reshape(k, hop) ** 2).mean(1))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={hz},scale=64:36,format=gray", "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 36, 64).astype(np.float32)
    mot = np.zeros(n)
    m = np.abs(np.diff(fr, axis=0)).mean((1, 2))
    mot[1:min(n, len(m) + 1)] = m[:n - 1]
    nz = lambda v: v / (v.max() + 1e-9)
    return nz(loud) + nz(mot), info["duration"]


def auto_spec(files, mode, duration, music, fmt, transition, beats_per_shot, work, fps=30):
    clips = []
    tr = {"type": transition, "dur": 0.4} if transition != "cut" else None
    if mode == "montage":
        import scenes as sc
        det = _face_det()
        pool = []
        for f in files:
            if f.lower().endswith(IMG_EXT):
                pool.append({"src": f, "start": 0, "end": 99, "score": 1.5, "image": True}); continue
            shots = sc.detect(f, 0.3, 0.5)["scenes"]
            for sh, s in zip(shots, shot_scores(f, shots, det)):
                pool.append({"src": f, "start": sh["start"], "end": sh["end"], "score": s, "image": False})
        if not music:
            die("montage needs --music (cuts land on its beats)")
        b = get_beats(music, work)
        beats = [t for t in b["beats"] if t <= duration + 0.01]
        if len(beats) < 2:
            die("no beats found in the music")
        period = float(np.median(np.diff(beats)))
        k = beats_per_shot or max(1, int(round(1.8 / period)))   # ~1.8 s shots by default
        grid = [0.0] + [round(t * fps) / fps for t in beats[k::k]]  # every cut on a beat, video ends on one
        need_d = [round(y - x, 4) for x, y in zip(grid[:-1], grid[1:])]
        pool.sort(key=lambda p: -p["score"])
        picks = [pool[i % len(pool)] for i in range(len(need_d))]   # best shots first, reuse only if short of shots
        picks.sort(key=lambda p: (files.index(p["src"]), p["start"]))  # keep story order
        uses = {}
        for p, d in zip(picks, need_d):
            if p["image"]:
                clips.append({"src": p["src"], "dur": d}); continue
            n = uses.get(id(p), 0); uses[id(p)] = n + 1
            length = p["end"] - p["start"]
            if length >= d:
                st = p["start"] + (length - d) / 2 if n == 0 else p["start"] + (n * d) % max(1e-3, length - d)
                clips.append({"src": p["src"], "in": round(st, 4), "out": round(st + d, 4), "audio": "mute"})
            else:  # too short for its beat slot: slow it down to fill
                c = {"src": p["src"], "in": p["start"], "out": p["end"], "audio": "mute",
                     "speed": round(max(RATE_MIN, length / d), 5)}
                if length / d < RATE_MIN:
                    c["freezeEnd"] = round(d - length / RATE_MIN, 4)
                clips.append(c)
        if tr:
            for c in clips[1:]:
                c["transition"] = tr
        return {"format": fmt, "fps": fps, "clips": clips, "music": {"src": music, "volume": 0.9, "duck": False},
                "beatGrid": grid}
    if mode == "story":
        for f in files:
            if f.lower().endswith(IMG_EXT):
                clips.append({"src": f, "dur": 2.5}); continue
            info = probe(f)
            regs = speech_regions(f) if info["has_audio"] else []
            if not regs:
                mid = info["duration"] / 2
                clips.append({"src": f, "in": max(0, mid - 1.5), "out": min(info["duration"], mid + 1.5), "audio": "duck"})
            for a, b in regs:
                clips.append({"src": f, "in": round(a, 3), "out": round(b, 3), "audio": "keep"})
    elif mode == "highlights":
        cands = []
        for f in files:
            if f.lower().endswith(IMG_EXT):
                continue
            cur, dur = activity_curve(f)
            win = 12  # 3 s at 4 Hz
            sm = np.convolve(cur, np.ones(win) / win, "same")
            taken = np.zeros(len(sm), bool)
            for _ in range(6):
                k = int(np.argmax(np.where(taken, -1, sm)))
                if sm[k] <= 0 or taken[k]:
                    break
                a, b = max(0, (k - win // 2) / 4), min(dur, (k + win // 2) / 4)
                cands.append({"src": f, "in": round(a, 3), "out": round(b, 3), "score": float(sm[k])})
                taken[max(0, k - win):k + win] = True
        cands.sort(key=lambda c: -c["score"])
        tot = 0.0
        for c in cands:
            if duration and tot >= duration:
                break
            clips.append({"src": c["src"], "in": c["in"], "out": c["out"], "audio": "keep"}); tot += c["out"] - c["in"]
        clips.sort(key=lambda c: (files.index(c["src"]), c["in"]))
    if duration:
        tot = sum(c.get("dur", c.get("out", 0) - c.get("in", 0)) for c in clips)
        if tot > duration * 1.05:
            log(f"{mode}: {tot:.1f}s of material for a {duration:.0f}s target; trimming the end")
            keep, acc = [], 0.0
            for c in clips:
                d = c.get("dur", c.get("out", 0) - c.get("in", 0))
                if acc + d > duration:
                    if duration - acc > 1.0 and "out" in c:
                        c["out"] = round(c["in"] + duration - acc, 3); keep.append(c)
                    break
                keep.append(c); acc += d
            clips = keep
    if tr:
        for c in clips[1:]:
            c["transition"] = tr
    spec = {"format": fmt, "fps": fps, "clips": clips}
    if music:
        spec["music"] = {"src": music, "volume": 0.2, "duck": True}
    return spec


def self_test():
    """3 clips (red/blue/testsrc, each with its own tone): dissolve + speed ramp, whip + J-cut."""
    pcm = lambda f, a=(): np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", f, *a, "-f", "f32le", "-"],
                                                       stdout=subprocess.PIPE, check=True).stdout, np.float32)
    with tempfile.TemporaryDirectory(prefix="vs_tl_test_") as d:
        for name, v, hz in (("a", "color=c=red", 440), ("b", "color=c=blue", 660), ("c", "testsrc=r=30", 880)):
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"{v}:s=160x284:d=3", "-r", "30", "-f", "lavfi", "-i",
                 f"sine=f={hz}:r=48000:d=3", "-shortest", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                 os.path.join(d, name + ".mp4")])
        spec = {"width": 160, "height": 284, "fps": 30, "clips": [
            {"src": "a.mp4"},
            {"src": "b.mp4", "transition": {"type": "dissolve", "dur": 0.5},
             "speedRamp": [{"at": 1.2, "rate": 0.4, "ramp": 0.5}, {"at": 2.2, "rate": 1.0, "ramp": 0.3}]},
            {"src": "c.mp4", "in": 0.5, "transition": {"type": "whip", "dur": 0.3}, "jcut": 0.4}]}
        _, _, fps, clips = load_spec(spec, d)
        assert clips[1]["_tr"]["xfade"] == "fade" and ALIAS["dither-dissolve"] == "dissolve"
        res = build(spec, os.path.join(d, "w"), transcribe=False, spec_base=d)
        got = probe(res["out"])["duration"]
        assert abs(got - res["total"]) <= 1.5 / fps, (got, res["total"])
        mid = res["clips"][1]["out_start"] + res["clips"][1]["transition_dur"] / 2   # true blend, not dither
        px = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{mid:.3f}", "-i", res["out"], "-frames:v",
                                           "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE,
                                          check=True).stdout, np.uint8).reshape(-1, 3).astype(float)
        assert px[:, 0].std() < 12 and 60 < px[:, 0].mean() < 200 and px[:, 2].mean() > 60, (px.mean(0), px.std(0))
        x = pcm(res["out"], ("-ac", "1", "-ar", "48000"))
        rms = np.sqrt((x[:len(x) // 480 * 480].reshape(-1, 480) ** 2).mean(1))[10:-10]   # 10 ms windows
        assert rms.min() > 0.02, f"audio hole at {(10 + rms.argmin()) / 100:.2f}s"
        c3 = res["clips"][2]
        assert c3["audio_start"] < c3["out_start"] + c3["transition_dur"] / 2 - 0.35, c3   # J-cut: sound leads
    print("timeline self-test OK")


def main():
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("spec"); b.add_argument("--work", default="work")
    b.add_argument("--no-transcribe", action="store_true"); b.add_argument("--model", default="small")
    au = sub.add_parser("auto")
    au.add_argument("inputs", nargs="+"); au.add_argument("--work", default="work")
    au.add_argument("--mode", default="montage", choices=["montage", "story", "highlights"])
    au.add_argument("--duration", type=float, default=30)
    au.add_argument("--music", default=None); au.add_argument("--format", default="16:9")
    au.add_argument("--fps", type=float, default=30)
    au.add_argument("--transition", default="cut", help="cut (default) or any transition name")
    au.add_argument("--beats-per-shot", type=int, default=0, help="0 = auto (~1.8 s shots)")
    au.add_argument("--dry-run", action="store_true", help="only write timeline_spec.json")
    au.add_argument("--no-transcribe", action="store_true"); au.add_argument("--model", default="small")
    a = ap.parse_args()
    if a.cmd == "build":
        build(load_json(a.spec), a.work, not a.no_transcribe, a.model, os.path.dirname(os.path.abspath(a.spec)))
        return
    os.makedirs(a.work, exist_ok=True)
    music = os.path.abspath(a.music) if a.music else None
    spec = auto_spec(media_files(a.inputs), a.mode, a.duration, music, a.format, a.transition, a.beats_per_shot,
                     a.work, a.fps)
    sp = os.path.join(a.work, "timeline_spec.json")
    save_json(sp, spec)
    log(f"{a.mode}: {len(spec['clips'])} clips -> {sp} (edit it and run: timeline.py build {sp} --work {a.work})")
    if not a.dry_run:
        build(spec, a.work, not a.no_transcribe and a.mode != "montage", a.model, a.work)


if __name__ == "__main__":
    main()
