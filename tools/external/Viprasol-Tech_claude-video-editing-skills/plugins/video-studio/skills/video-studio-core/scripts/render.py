#!/usr/bin/env python3
"""Render a plan.json into a finished composite video.

  1. extracts any clips the plan uses into image sequences
  2. renders the HTML overlay layers (bg / behind / front) frame by frame with headless Chromium
  3. composites with FFmpeg:  bg -> speaker video -> behind -> person cut-out -> cutaways -> front

usage: render.py PLAN.json [--out work/composite.mp4] [--preview 3.5]   (preview = render one PNG at t)
       render.py PLAN.json --frames 0,2.5,6   (contact sheet of stills for checking the look)
"""
import argparse, base64, io, json, math, os, shutil, subprocess, sys, tempfile
from vs_common import RUNTIME, load_json, run, probe, log, die, need

ap = argparse.ArgumentParser()
ap.add_argument("plan")
ap.add_argument("--out", default=None)
ap.add_argument("--preview", type=float, default=None, help="render a single composited still at this time")
ap.add_argument("--frames", default=None, help="comma list of times -> contact sheet PNG")
# each worker is one Chromium; software raster scales ~linearly to 4 and saturates a 6-core laptop at 6
ap.add_argument("--workers", type=int, default=max(1, min(4, (os.cpu_count() or 2) // 2)),
                help="parallel browsers (default: 4, or half the CPU threads if fewer)")
ap.add_argument("--keep", action="store_true", help="keep rendered PNG frames")
ap.add_argument("--self-test", action="store_true", help="check that frames reused as unchanged match a fresh capture")
a = ap.parse_args()
need("ffmpeg")

plan_path = os.path.abspath(a.plan)
pdir = os.path.dirname(plan_path)
plan = load_json(plan_path)
O = plan["output"]
W, H, FPS = int(O["width"]), int(O["height"]), int(O.get("fps", 30))
DUR = float(O["duration"])
NF = int(math.ceil(DUR * FPS))
work = os.path.abspath(os.path.join(pdir, plan.get("workDir", ".")))
rdir = os.path.join(work, "render")
os.makedirs(rdir, exist_ok=True)


def P(p):
    if p is None:
        return None
    if p.startswith(("http://", "https://", "data:", "file://")):
        return p
    return os.path.abspath(os.path.join(pdir, p))


def uri(p):
    p = P(p)
    return p if p.startswith(("http", "data:", "file:")) else "file://" + p

# ---------- 1. clips -> image sequences ----------
for c in plan.get("clips", []):
    src = P(c["src"])
    d = os.path.join(rdir, "clips", c["id"])
    marker = os.path.join(d, ".src")
    sig = json.dumps([src, c.get("start"), c.get("end"), c.get("maxWidth", 1080), FPS])
    if not (os.path.exists(marker) and open(marker, encoding="utf-8").read() == sig):
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        cmd = ["ffmpeg", "-y", "-hide_banner"]
        if c.get("start") is not None: cmd += ["-ss", str(c["start"])]
        if c.get("end") is not None: cmd += ["-to", str(c["end"])]
        mw = c.get("maxWidth", 1080)
        cmd += ["-i", src, "-vf", f"fps={FPS},scale='min({mw},iw)':-2", "-q:v", "3", os.path.join(d, "%05d.jpg")]
        log(f"extracting clip '{c['id']}' frames")
        run(cmd)
        open(marker, "w").write(sig)
    c["frames"] = len([f for f in os.listdir(d) if f.endswith(".jpg")])
    c["dir"] = "file://" + d

# resolve element asset paths
for el in plan.get("elements", []):
    for k in ("image", "before", "after"):
        if el.get(k):
            el[k] = uri(el[k])

# ---------- 2. HTML ----------
theme = plan.get("theme", {})
css = open(os.path.join(RUNTIME, "base.css"), encoding="utf-8").read()
for cf in theme.get("cssFiles", []):
    css += "\n" + open(P(cf), encoding="utf-8").read()
css += "\n" + theme.get("css", "")
fonts = theme.get("fontsUrl")
engine = open(os.path.join(RUNTIME, "engine.js"), encoding="utf-8").read()
html = f"""<!doctype html><html><head><meta charset="utf-8">
{f'<link rel="stylesheet" href="{fonts}">' if fonts else ''}
<style>{css}</style></head><body><div id="stage"></div>
<script>window.__PLAN={json.dumps(plan, ensure_ascii=False)};</script>
<script>{engine}</script></body></html>"""
html_path = os.path.join(rdir, "index.html")
open(html_path, "w", encoding="utf-8").write(html)

# ---------- render frames ----------
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    die("playwright not installed. Run: pip install playwright && python -m playwright install chromium")


def open_page(pw):
    br = pw.chromium.launch(args=["--allow-file-access-from-files", "--disable-web-security", "--font-render-hinting=none"])
    pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    pg.on("console", lambda m: m.type == "error" and log(f"page error: {m.text}"))
    pg.on("pageerror", lambda e: log(f"page exception: {e}"))
    pg.goto("file://" + html_path)
    try:
        pg.wait_for_function("window.__ready !== undefined", timeout=15000)
        pg.evaluate("Promise.race([window.__ready, new Promise(r=>setTimeout(r,8000))])")
    except Exception as e:
        die(f"overlay page failed to load: {e}")
    return br, pg, pg.context.new_cdp_session(pg)


TRANSPARENT = {"color": {"r": 0, "g": 0, "b": 0, "a": 0}}
# __render plus the layer's state signature. Every element is a pure function of t drawn through inline DOM, so an
# identical layer DOM means identical pixels. A <canvas> (grain) draws outside the DOM: such a layer never matches.
STATE_JS = """async ([t, l]) => {
  if (!(await window.__render(t, l))) return null;
  const root = document.querySelector('#stage > .layer-' + l);
  return root.querySelector('canvas') ? 'canvas@' + t : document.documentElement.style.cssText + root.outerHTML;
}"""


def set_layer(cdp, layer):
    """bg keeps the browser's opaque default background (as page.screenshot did); other layers keep alpha.
    Never mix with page.screenshot(omit_background=...) on the same page: it resets this override."""
    cdp.send("Emulation.setDefaultBackgroundColorOverride", {} if layer == "bg" else TRANSPARENT)


def capture(cdp, layer, path):
    # CDP capture with optimizeForSpeed (lighter zlib, same pixels): ~4x faster than page.screenshot()
    png = base64.b64decode(cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True})["data"])
    if layer != "bg" and png[25] != 6:   # IHDR colour type, 6 = RGBA
        # A fully opaque frame (e.g. a full-screen title card) is saved as RGB, not RGBA. A pixel-format change
        # mid-sequence breaks FFmpeg's overlay and the rest of the video renders black. Always store RGBA.
        Image.open(io.BytesIO(png)).convert("RGBA").save(path)
    else:
        with open(path, "wb") as f:
            f.write(png)


def dup(src, dst):
    try:
        os.link(src, dst)
    except OSError:   # NTFS caps a file at 1023 hard links (FAT has none): a copy is the same frame
        shutil.copyfile(src, dst)


blank = os.path.join(rdir, "blank.png")
from PIL import Image
Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)

with sync_playwright() as pw:
    br, pg, cdp = open_page(pw)
    layers = pg.evaluate("window.__layersUsed")

    if a.self_test:   # the reuse rule on this plan: an unchanged layer state must give unchanged pixels
        same = 0
        for l in layers:
            set_layer(cdp, l); prev = None
            for i in range(min(NF, 45)):
                st = pg.evaluate(STATE_JS, [i / FPS, l])
                if st is None:
                    prev = None; continue
                p = os.path.join(rdir, f"selftest_{i % 2}.png"); capture(cdp, l, p)
                if prev and prev[0] == st:
                    with Image.open(p) as x, Image.open(prev[1]) as y:
                        assert x.tobytes() == y.tobytes(), f"layer {l} frame {i + 1}: same state, different pixels"
                    same += 1
                prev = (st, p)
        br.close()
        log(f"self-test ok: {same} unchanged layer frames matched a fresh capture")
        sys.exit(0)

    if a.preview is not None or a.frames:
        times = [a.preview] if a.preview is not None else [float(x) for x in a.frames.split(",")]
        stills = []
        for t in times:
            lp = {}
            for l in layers:
                p = os.path.join(rdir, f"still_{l}_{t:.2f}.png")
                set_layer(cdp, l)
                if pg.evaluate("([t,l]) => window.__render(t,l)", [t, l]):
                    capture(cdp, l, p); lp[l] = p
                else:
                    lp[l] = blank
            stills.append((t, lp))
        br.close()
    else:
        # parallel pages
        import threading
        for l in layers:
            d = os.path.join(rdir, l); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        br.close()

    if a.preview is None and not a.frames:
        nw = max(1, min(a.workers, NF))
        errors, stats = [], []

        def worker(f0, f1, idx):
            # one contiguous frame range per worker: consecutive frames let an unchanged layer reuse the last PNG
            try:
                n = n_cap = n_reuse = 0
                with sync_playwright() as pw2:
                    b2, p2, c2 = open_page(pw2)
                    for l in layers:
                        set_layer(c2, l)
                        prev = None   # (state, path) of the previous frame of this layer
                        for i in range(f0, f1):
                            path = os.path.join(rdir, l, f"{i + 1:05d}.png")
                            st = p2.evaluate(STATE_JS, [i / FPS, l])
                            if st is None:
                                dup(blank, path)
                            elif prev and prev[0] == st:
                                dup(prev[1], path); n_reuse += 1
                            else:
                                capture(c2, l, path); n_cap += 1
                            prev = None if st is None else (st, path)
                            if idx == 0 and n % 90 == 0:
                                log(f"overlay frames {n * nw}/{NF * len(layers)}")
                            n += 1
                    b2.close()
                stats.append((n_cap, n_reuse))
            except BaseException as e:   # die() raises SystemExit, which a thread would swallow silently
                errors.append(e)
        ths = [threading.Thread(target=worker, args=(k * NF // nw, (k + 1) * NF // nw, k)) for k in range(nw)]
        [t.start() for t in ths]; [t.join() for t in ths]
        if errors:
            die(f"render failed: {errors[0]!r}")
        counts = {l: len(os.listdir(os.path.join(rdir, l))) for l in layers}
        if any(c != NF for c in counts.values()):   # a gap would make FFmpeg freeze the graphics silently
            die(f"render failed: layer frame counts {counts}, expected {NF} each")
        caps, reuse = sum(s[0] for s in stats), sum(s[1] for s in stats)
        log(f"overlay: {caps} captured, {reuse} unchanged reused, {NF * len(layers) - caps - reuse} blank ({nw} workers)")

# ---------- 3. composite ----------
sp = plan.get("speaker", {"mode": "none"})
mode = sp.get("mode", "full") if plan.get("source") else "none"
src = P(plan.get("source")) if plan.get("source") else None
matte = P(plan.get("matte")) if plan.get("matte") else None
PSC = float(sp.get("personScale", 1.0))   # <1 shrinks the person cut-out (needs backdrop blur/hide)
PDROP = int(float(sp.get("personDrop", 0)) * H)   # slide the cut-out down (full width, no side edges) to free the top
BACKDROP = sp.get("backdrop", "video")   # video | blur | hide: what shows behind the person cut-out
use_person = matte and os.path.exists(matte) and ("behind" in layers or sp.get("person") or BACKDROP != "video" or sp.get("glow"))
if BACKDROP != "video" and not use_person:
    log("WARNING: speaker.backdrop needs the person matte (run matte.py) - showing the plain video instead.")
    BACKDROP = "video"
if plan.get("matte") and not use_person and "behind" in layers:
    log("WARNING: matte file missing - 'behind' layer will sit on top of the speaker. Run matte.py.")


COLOR_CHAIN = ""
if mode != "none" and src:
    import color as COL
    _si = probe(src)
    COLOR_CHAIN = COL.source_chain(plan, src, work, _si["width"], _si["height"])
    if COLOR_CHAIN:
        log("colour on source: " + (plan.get("color", {}).get("look") or plan.get("finish", {}).get("grade", "correction")))


def zoom_expr():
    zs = sp.get("zooms", [])
    push = sp.get("push", 0)
    terms = ["1"]
    if push:
        terms.append(f"{push}*it/{DUR}")
    for z in zs:
        s, e, k = z["start"], z["end"], z.get("scale", 1.12) - 1
        r = z.get("ramp", 0.12)
        if z.get("snap"):
            terms.append(f"{k}*between(it,{s},{e})")
        else:
            terms.append(f"{k}*clip((it-{s})/{r},0,1)*clip(({e}-it)/{r},0,1)")
    return "+".join(terms) if len(terms) > 1 else None


def _face_at(t):
    """Primary face centre (normalised source coords) at time t from plan["track"] [{t,x,y,w,h}], if present."""
    tr = plan.get("track") or []
    if not tr:
        return None
    f = min(tr, key=lambda p: abs(p["t"] - t))
    return f["x"] + f.get("w", 0) / 2, f["y"] + f.get("h", 0) / 2


def zoom_centre_expr():
    """Punch-ins zoom toward the face (or a zoom's own cx/cy, normalised) instead of the frame centre.
    Each zoom holds its centre for its whole window; zoompan keeps the crop inside the frame."""
    xs, ys = ["0.5"], ["0.5"]
    for z in sp.get("zooms", []):
        c = (z["cx"], z["cy"]) if "cx" in z and "cy" in z else (_face_at(z["start"]) if z.get("toFace", True) else None)
        if not c:
            continue
        pad = 0 if z.get("snap") else 0.2  # snap punch-ins sit back to back: padded windows would add their offsets twice
        s, e = z["start"] - pad, z["end"] + pad
        xs.append(f"{c[0] - 0.5:.4f}*between(it,{s},{e})")
        ys.append(f"{max(0.0, c[1] - 0.06) - 0.5:.4f}*between(it,{s},{e})")  # a touch above centre: eyes, not chin
    if len(xs) == 1:
        return "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    fx, fy = "+".join(xs), "+".join(ys)
    return (f"clip(iw*({fx})-iw/zoom/2,0,iw-iw/zoom)", f"clip(ih*({fy})-ih/zoom/2,0,ih-ih/zoom)")


def speaker_chain(label_in, label_out, is_mask=False, sw=0, sh=0, rect=None):
    """zoom -> cover-crop to rect."""
    rx, ry, rw, rh = rect or sp.get("rect", [0, 0, W, H])
    fx = sp.get("focusX", 0.5); fy = sp.get("focusY", 0.5)
    f = []
    ze = zoom_expr()
    if ze:
        zx, zy = zoom_centre_expr()
        f.append(f"zoompan=z='{ze}':d=1:x='{zx}':y='{zy}':s={sw}x{sh}:fps={FPS}")
    f.append(f"scale={rw}:{rh}:force_original_aspect_ratio=increase:flags=lanczos")
    f.append(f"crop={rw}:{rh}:(iw-{rw})*{fx}:(ih-{rh})*{fy}")
    if sp.get("mirror"):
        f.append("hflip")
    f.append("format=gray" if is_mask else "format=yuva420p")
    return f"[{label_in}]" + ",".join(f) + f"[{label_out}]"


def layouts_overlay(graph, add_input, cur, si, sw, sh, single_t):
    """speaker.layouts: [{start, end, rect:[x,y,w,h] px (or rectFrac), radius, rot (deg)}] - the footage moves
    between framed cards over time (editorial explainers). Each layout is its own cropped, rounded, rotated card."""
    from PIL import ImageDraw
    los = []
    for lo in sp["layouts"]:
        if "rectFrac" in lo:
            x, y, w, h = lo["rectFrac"]; r = [int(x * W), int(y * H), int(w * W) // 2 * 2, int(h * H) // 2 * 2]
        else:
            r = [int(v) for v in lo["rect"]]; r[2] -= r[2] % 2; r[3] -= r[3] % 2
        if single_t is None or lo["start"] <= single_t < lo["end"]:
            los.append((lo, r))
    if not los:
        return cur
    graph.append(f"[srcL]split={len(los)}" + "".join(f"[sl{k}]" for k in range(len(los))) if len(los) > 1 else "[srcL]null[sl0]")
    for k, (lo, (x, y, w, h)) in enumerate(los):
        graph.append(speaker_chain(f"sl{k}", f"lc{k}", sw=sw, sh=sh, rect=[x, y, w, h]))
        rad = min(lo.get("radius", sp.get("radius", 36)), min(w, h) // 2)
        rm = os.path.join(rdir, f"rmask_{w}x{h}_{rad}.png")
        if not os.path.exists(rm):
            im = Image.new("L", (w, h), 0); ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], radius=rad, fill=255); im.save(rm)
        ri = add_input(["-loop", "1", "-i", rm])
        graph.append(f"[{ri}:v]format=gray[lm{k}]")
        graph.append(f"[lc{k}][lm{k}]alphamerge[la{k}]")
        rot = lo.get("rot", 0)
        lab, ox, oy = f"la{k}", x, y
        if rot:
            import math
            a = math.radians(rot); ow = int(abs(w * math.cos(a)) + abs(h * math.sin(a))) // 2 * 2 + 2; oh = int(abs(w * math.sin(a)) + abs(h * math.cos(a))) // 2 * 2 + 2
            graph.append(f"[la{k}]rotate=a={a:.5f}:ow={ow}:oh={oh}:c=none[lr{k}]")
            lab, ox, oy = f"lr{k}", x - (ow - w) // 2, y - (oh - h) // 2
        en = "" if single_t is not None else f":enable='between(t,{lo['start']},{lo['end']})'"
        graph.append(f"[{cur}][{lab}]overlay={ox}:{oy}:shortest=0:eof_action=pass{en}[lo{k}]"); cur = f"lo{k}"
    return cur


def composite(out_path, single_t=None, still_layers=None):
    inputs, graph = [], []

    def add_input(args):
        inputs.extend(args); return len([x for x in inputs if x == "-i"]) - 1

    seq = lambda l: (["-loop", "1", "-t", "0.04", "-i", still_layers[l]] if single_t is not None
                     else ["-framerate", str(FPS), "-i", os.path.join(rdir, l, "%05d.png")])
    dur = 0.5 if single_t is not None else DUR
    bgcol = O.get("background", "black")
    if "bg" in layers:
        i = add_input(seq("bg")); graph.append(f"[{i}:v]format=yuva420p,scale={W}:{H}[base]")
    else:
        graph.append(f"color=c={bgcol}:s={W}x{H}:r={FPS}:d={dur}[base]")
    cur = "base"
    if mode != "none":
        ss = ["-ss", str(single_t)] if single_t is not None else []
        si = add_input(ss + ["-i", src])
        info = probe(src)
        sw, sh = info["width"], info["height"]
        rx, ry, rw, rh = sp.get("rect", [0, 0, W, H])
        n_split = 2 if use_person else 1
        # colour on the camera footage, before overlays (and identical for the person cut-out)
        cc = ("," + COLOR_CHAIN) if COLOR_CHAIN else ""
        if n_split == 2:
            graph.append(f"[{si}:v]setpts=PTS-STARTPTS{cc},split=2[srcA][srcB]")
        else:
            graph.append(f"[{si}:v]setpts=PTS-STARTPTS{cc}[srcA]")
        if sp.get("layouts") and not use_person:
            graph.append(f"[srcA]null[srcL]")
        else:
            graph.append(speaker_chain("srcA", "spk", sw=sw, sh=sh))
        radius = 0 if (sp.get("layouts") and not use_person) else min(sp.get("radius", 0), min(rw, rh) // 2)
        rmask = None
        if radius:
            rm = os.path.join(rdir, f"rmask_{rw}x{rh}_{radius}.png")
            if not os.path.exists(rm):
                from PIL import ImageDraw
                im = Image.new("L", (rw, rh), 0); ImageDraw.Draw(im).rounded_rectangle([0, 0, rw - 1, rh - 1], radius=radius, fill=255); im.save(rm)
            ri = add_input(["-loop", "1", "-i", rm])
            if use_person:
                graph.append(f"[{ri}:v]format=gray,split=2[rm1][rm2]")
            else:
                graph.append(f"[{ri}:v]format=gray[rm1]")
            graph.append("[spk][rm1]alphamerge[spkr]")
            rmask = "rm2"
            spk = "spkr"
        else:
            spk = "spk"
        if sp.get("layouts") and not use_person:
            cur = layouts_overlay(graph, add_input, cur, si, sw, sh, single_t)
        elif BACKDROP == "blur":
            bd = sp.get("backdropBlur", 40); dim = sp.get("backdropDim", 0.45)
            graph.append(f"[{spk}]gblur=sigma={bd},colorchannelmixer=rr={1-dim}:gg={1-dim}:bb={1-dim}[spkb]")
            graph.append(f"[{cur}][spkb]overlay={rx}:{ry}:shortest=0:eof_action=pass[c1]"); cur = "c1"
        elif BACKDROP != "hide":
            graph.append(f"[{cur}][{spk}]overlay={rx}:{ry}:shortest=0:eof_action=pass[c1]"); cur = "c1"
        else:
            graph.append(f"[{spk}]nullsink")   # background replaced: only the cut-out is shown
        if "behind" in layers:
            bi = add_input(seq("behind")); graph.append(f"[{cur}][{bi}:v]overlay=0:0[c2]"); cur = "c2"
        if use_person:
            mi = add_input(ss + ["-i", matte])
            graph.append(f"[{mi}:v]setpts=PTS-STARTPTS[mraw]")
            graph.append(speaker_chain("mraw", "mk", is_mask=True, sw=sw, sh=sh))
            if rmask:
                graph.append(f"[mk][{rmask}]blend=all_mode=multiply[mk2]"); mk = "mk2"
            else:
                mk = "mk"
            graph.append(speaker_chain("srcB", "pv", sw=sw, sh=sh).replace("format=yuva420p", "format=yuv420p"))
            if PSC < 1 or PDROP:   # the frame's top edge would show as a hard line once the cut-out is smaller: fade it
                fm = os.path.join(rdir, f"topfade_{rw}x{rh}.png")
                if not os.path.exists(fm):
                    import numpy as _np
                    ramp = _np.clip(_np.arange(rh) / max(1, rh * 0.12), 0, 1) ** 1.5
                    Image.fromarray((_np.repeat(ramp[:, None], rw, 1) * 255).astype("uint8"), "L").save(fm)
                fi_ = add_input(["-loop", "1", "-i", fm])
                graph.append(f"[{fi_}:v]format=gray,split=2[tfm][tfm2]")
                graph.append(f"[{mk}][tfm]blend=all_mode=multiply:shortest=1[mkf]"); mk = "mkf"
            if sp.get("glow"):
                gl = sp["glow"] if isinstance(sp["glow"], dict) else {"color": sp["glow"]}
                gsz, gain = gl.get("size", 22), gl.get("strength", 1.6)
                graph.append(f"[{mk}]split=2[mkp][mkg]"); mk = "mkp"
                graph.append(f"[mkg]gblur=sigma={gsz},lut=y='min(255,val*{gain})'[gma0]")
                if PSC < 1 or PDROP:
                    graph.append("[gma0][tfm2]blend=all_mode=multiply:shortest=1,lut=y='val*val/255'[gma]")
                else:
                    graph.append("[gma0]null[gma]")
                graph.append(f"color=c={gl.get('color', '#FFC24D')}:s={rw}x{rh}:r={FPS}:d={dur},format=yuva420p[gcol]")
                graph.append("[gcol][gma]alphamerge[glow]")
                gx, gy, glab = rx, ry, "glow"
                if PSC < 1:
                    graph.append(f"[glow]scale={int(rw * PSC) // 2 * 2}:{int(rh * PSC) // 2 * 2}[glows]"); glab = "glows"
                    gx, gy = rx + (rw - int(rw * PSC) // 2 * 2) // 2, ry + rh - int(rh * PSC) // 2 * 2
                gy += PDROP
                graph.append(f"[{cur}][{glab}]overlay={gx}:{gy}:shortest=0:eof_action=pass[cg]"); cur = "cg"
            if (PSC < 1 or PDROP) and not sp.get("glow"):
                graph.append("[tfm2]nullsink")
            graph.append(f"[pv][{mk}]alphamerge[person]")
            px, py, plab = rx, ry, "person"
            if PSC < 1:   # smaller cut-out, bottom-centred, over the (blurred / replaced) background
                graph.append(f"[person]scale={int(rw * PSC) // 2 * 2}:{int(rh * PSC) // 2 * 2}[persons]"); plab = "persons"
                px, py = rx + (rw - int(rw * PSC) // 2 * 2) // 2, ry + rh - int(rh * PSC) // 2 * 2
            py += PDROP
            graph.append(f"[{cur}][{plab}]overlay={px}:{py}[c3]"); cur = "c3"
    elif "behind" in layers:
        bi = add_input(seq("behind")); graph.append(f"[{cur}][{bi}:v]overlay=0:0[c2]"); cur = "c2"
    # cutaways (full-frame b-roll videos); stills show the one on screen at single_t
    if single_t is not None:
        for k, cw in enumerate(c for c in plan.get("cutaways", []) if c["start"] <= single_t < c["end"]):
            off = max(0.0, single_t - cw["start"] + cw.get("srcStart", 0))
            img = str(cw["src"]).lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            ci = add_input((["-loop", "1"] if img else ["-ss", str(off)]) + ["-i", P(cw["src"])])
            graph.append(f"[{ci}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=yuva420p[cws{k}]")
            graph.append(f"[{cur}][cws{k}]overlay=0:0[cwso{k}]"); cur = f"cwso{k}"
    for k, cw in enumerate(plan.get("cutaways", []) if single_t is None else []):
        ci = add_input(["-i", P(cw["src"])])
        d = cw["end"] - cw["start"]
        graph.append(f"[{ci}:v]trim=start={cw.get('srcStart', 0)}:duration={d},setpts=PTS-STARTPTS+{cw['start']}/TB,"
                     f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuva420p[cw{k}]")
        graph.append(f"[{cur}][cw{k}]overlay=0:0:enable='between(t,{cw['start']},{cw['end']})':eof_action=pass[cwo{k}]"); cur = f"cwo{k}"
    # privacy / focus blurs on the picture (not the graphics): plan "blurs": [{x,y,w,h,start,end,strength}]
    # x,y,w,h in output pixels (top-left box); strength = blur radius (default 24); "pixelate": true for mosaic
    for k, b in enumerate(plan.get("blurs", [])):
        s_, e_ = b.get("start", 0), b.get("end", DUR + 1)
        if single_t is not None and not (s_ <= single_t < e_):
            continue
        bx, by = max(0, int(b["x"])), max(0, int(b["y"]))
        bw, bh = max(8, min(int(b["w"]), W - bx)) // 2 * 2, max(8, min(int(b["h"]), H - by)) // 2 * 2
        fx = (f"scale=iw/{int(b.get('block', 24))}:-2,scale={bw}:{bh}:flags=neighbor" if b.get("pixelate")
              else f"boxblur={min(int(b.get('strength', 24)), bw // 2 - 1, bh // 2 - 1)}:2")
        en = "" if single_t is not None else f":enable='between(t,{s_},{e_})'"
        graph.append(f"[{cur}]split=2[bb{k}a][bb{k}b]")
        graph.append(f"[bb{k}b]crop={bw}:{bh}:{bx}:{by},{fx}[bb{k}c]")
        graph.append(f"[bb{k}a][bb{k}c]overlay={bx}:{by}{en}[bbo{k}]"); cur = f"bbo{k}"
    if "front" in layers:
        fi = add_input(seq("front")); graph.append(f"[{cur}][{fi}:v]overlay=0:0[c4]"); cur = "c4"
    # softCuts: full-frame blur pulse that hides a scene change (plan "softCuts": [{at, dur .36, sigma 22}])
    for k, sc in enumerate(plan.get("softCuts", [])):
        at, d, sg = sc["at"], sc.get("dur", 0.36), sc.get("sigma", 22)
        steps = [(at - d / 2, at - d / 6, sg / 3), (at - d / 6, at + d / 6, sg), (at + d / 6, at + d / 2, sg / 3)]
        for j, (a0, a1, sgj) in enumerate(steps):
            if single_t is not None:
                if a0 <= single_t < a1:
                    graph.append(f"[{cur}]gblur=sigma={sgj:.1f}[sc{k}_{j}]"); cur = f"sc{k}_{j}"
                continue
            graph.append(f"[{cur}]gblur=sigma={sgj:.1f}:enable='between(t,{a0:.3f},{a1:.3f})'[sc{k}_{j}]"); cur = f"sc{k}_{j}"
    graph.append(f"[{cur}]format=yuv420p[vout]")
    gf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False); gf.write(";\n".join(graph)); gf.close()
    cmd = ["ffmpeg", "-y", "-hide_banner"] + inputs + ["-filter_complex_script", gf.name, "-map", "[vout]"]
    if single_t is not None:
        cmd += ["-frames:v", "1", out_path]
    else:
        if mode != "none":
            cmd += ["-map", "1:a?" if "bg" in layers else "0:a?"]
        cmd += ["-t", str(DUR), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_path]
    run(cmd)
    os.unlink(gf.name)


if a.preview is not None or a.frames:
    outs = []
    for t, lp in stills:
        p = os.path.join(work, f"still_{t:.2f}.png")
        composite(p, single_t=t, still_layers=lp)
        outs.append(p)
    if len(outs) > 1:
        ims = [Image.open(p).convert("RGB") for p in outs]
        sc = 540 / ims[0].width
        ims = [im.resize((int(im.width * sc), int(im.height * sc))) for im in ims]
        cols = min(4, len(ims)); rows = math.ceil(len(ims) / cols)
        sheet = Image.new("RGB", (cols * ims[0].width, rows * ims[0].height), "white")
        for k, im in enumerate(ims):
            sheet.paste(im, ((k % cols) * im.width, (k // cols) * im.height))
        sp_path = os.path.join(work, "contact_sheet.png"); sheet.save(sp_path); log(f"contact sheet -> {sp_path}")
    else:
        log(f"still -> {outs[0]}")
    sys.exit(0)

out = a.out or os.path.join(work, "composite.mp4")
log("compositing with ffmpeg")
composite(out)
if not a.keep:
    for l in layers:
        shutil.rmtree(os.path.join(rdir, l), ignore_errors=True)
log(f"composite -> {out}")
