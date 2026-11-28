#!/usr/bin/env python3
"""Review app: watch an edit, fix caption words and timing, pick a style, then re-plan / stills / render.

  python app/server.py --root <folder with work folders> [--port 8765] [--no-open]
  python app/server.py --self-test

Binds 127.0.0.1 only and prints (and opens) http://127.0.0.1:PORT/?t=<token>. Every /api call needs that
per-run token (?t=... or an X-Token header). Files are read and written only inside --root; jobs run the
engine scripts one at a time, as argument lists (no shell).
"""
import argparse, itertools, json, os, queue, re, secrets, shutil, subprocess, sys, threading, time, webbrowser
from pathlib import Path

try:
    from fastapi import Body, FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse, JSONResponse
    import uvicorn
except ImportError as e:
    sys.exit(f"review app needs FastAPI + uvicorn ({e}). Install: python -m pip install fastapi uvicorn")

APP = Path(__file__).resolve().parent
CORE = APP.parent
SCRIPTS = CORE / "scripts"
SKILLS = CORE.parent                 # skin folders (theme.json) sit next to video-studio-core
TOKEN = secrets.token_urlsafe(18)
ROOT = None                          # set from --root in main()
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
END_SLACK = 0.25                     # s: ASR word ends may run a little past a trimmed duration
MAX_STILLS = 12
STILL_RE = re.compile(r"still_(\d+(?:\.\d+)?)\.png$")


# ---------- path + data checks (the trust boundary) ----------
def inside(base, rel):
    """base/rel resolved; refuses '..', absolute paths, other drives and symlinks that leave base."""
    p = (base / rel).resolve()
    if not p.is_relative_to(base):
        raise HTTPException(400, f"path leaves {base.name}: {rel}")
    return p


def work_dir(name):
    d = inside(ROOT, name)
    if d.parent != ROOT or not (d / "plan.json").is_file():
        raise HTTPException(404, f"no work folder '{name}' with plan.json")
    return d


def skin_dir(name):
    if not isinstance(name, str) or not name:
        raise HTTPException(400, "style is missing")
    d = inside(SKILLS, name)
    if d.parent != SKILLS or not (d / "theme.json").is_file():
        raise HTTPException(400, f"unknown style '{name}'")
    return d


def token_ok(t):
    return secrets.compare_digest((t or "").encode(), TOKEN.encode())


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def duration(plan):
    d = plan.get("output", {}).get("duration")
    if not is_num(d) or d <= 0:
        raise HTTPException(400, "plan.json has no output.duration")
    return d


def clean_words(words, dur):
    """Validated copies of the edited words: text, 0 <= start <= end <= duration, starts in order."""
    if not isinstance(words, list) or not words:
        raise HTTPException(400, "words must be a non-empty list")
    out, prev = [], 0.0
    for i, w in enumerate(words, 1):
        text = w.get("w") if isinstance(w, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(400, f"word {i}: text is empty")
        s, e = w.get("start"), w.get("end")
        if not (is_num(s) and is_num(e) and 0 <= s <= e <= dur + END_SLACK):
            raise HTTPException(400, f"word {i} '{text}': need 0 <= start <= end <= {dur:g} s")
        if s < prev:
            raise HTTPException(400, f"word {i} '{text}' starts before the word above it")
        prev = s
        out.append(dict(w, w=text.strip(), start=round(float(s), 3), end=round(float(e), 3)))
    return out


def frame_times(frames, dur):
    if frames is None:                                       # 6 evenly spaced, never past the end
        return [round(dur * (i + 0.5) / 6, 2) for i in range(6)]
    if not (isinstance(frames, list) and 1 <= len(frames) <= MAX_STILLS
            and all(is_num(t) and 0 <= t < dur for t in frames)):
        raise HTTPException(400, f"frames: 1-{MAX_STILLS} times from 0 to under {dur:g} s")
    return frames


def load(p):
    return json.loads(Path(p).read_text("utf-8"))


def write_json(p, data):
    """Keep the old file as .bak, then replace atomically (no half-written plan if we die mid-write)."""
    if p.exists():
        shutil.copy2(p, p.with_name(p.name + ".bak"))
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    os.replace(tmp, p)


# ---------- job queue: one job at a time ----------
JOBS, QUEUE, IDS, LOCK = {}, queue.Queue(), itertools.count(1), threading.Lock()


def py(script, *args):
    return [sys.executable, str(SCRIPTS / script), *map(str, args)]


def job_steps(kind, d, plan, body):
    p = d / "plan.json"
    if kind == "replan":
        style = skin_dir(body.get("style") or plan.get("style"))
        steps = [py("make_plan.py", "--work", d, "--style", style, *(["--genre", plan["genre"]] if plan.get("genre") else []))]
        recipe = load(style / "theme.json").get("sequence")
        return steps + ([py("sequence.py", p, "--recipe", recipe)] if recipe else [])
    if kind == "stills":
        return [py("render.py", p, "--frames", ",".join(f"{t:.2f}" for t in frame_times(body.get("frames"), duration(plan))))]
    if kind == "render":
        return [py("render.py", p), py("finish.py", p, "--platform", "reels")]
    raise HTTPException(400, f"unknown job kind '{kind}' (replan, stills, render)")


def busy(name):
    states = {j["state"] for j in JOBS.values() if j["work"] == name}
    return "running" if "running" in states else "queued" if "queued" in states else None


def public(job):
    return {k: job[k] for k in ("id", "work", "kind", "state")} | {"lines": len(job["log"])}


def run_jobs():
    while True:
        job = QUEUE.get()
        job["state"] = "running"
        try:
            if job["kind"] == "replan":                      # make_plan rewrites plan.json from scratch
                p = Path(job["cwd"]) / "plan.json"
                shutil.copy2(p, p.with_name("plan.json.bak"))
                job["log"].append("backup: plan.json -> plan.json.bak")
            for argv in job["steps"]:
                job["log"].append("$ " + subprocess.list2cmdline(argv))
                proc = subprocess.Popen(argv, cwd=job["cwd"], env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                for raw in proc.stdout:
                    job["log"].extend(raw.decode("utf-8", "replace").replace("\r", "\n").splitlines())
                if proc.wait():
                    raise RuntimeError(f"{Path(argv[1]).name} exited with code {proc.returncode}")
            job["state"] = "done"
        except Exception as e:                               # shown in the log, the worker keeps going
            job["log"].append(f"ERROR: {e}")
            job["state"] = "failed"


# ---------- HTTP ----------
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def need_token(request: Request, call_next):
    if request.url.path.startswith("/api/") and not token_ok(request.query_params.get("t") or request.headers.get("x-token")):
        return JSONResponse({"detail": "missing or wrong token: open the URL the server printed"}, 403)
    return await call_next(request)


@app.get("/")
def index():
    return FileResponse(APP / "static" / "index.html")


@app.get("/api/works")
def works():
    ds = [d for d in ROOT.iterdir() if d.is_dir() and (d / "plan.json").is_file()]
    ds.sort(key=lambda d: (d / "plan.json").stat().st_mtime, reverse=True)
    return [{"name": d.name, "final": (d / "final.mp4").is_file(), "busy": busy(d.name)} for d in ds]


@app.get("/api/works/{name}")
def work(name: str):
    d = work_dir(name)
    media = lambda f: {"file": f, "v": int((d / f).stat().st_mtime)}
    stills = sorted((p.name for p in d.glob("still_*.png") if STILL_RE.match(p.name)),
                    key=lambda f: float(STILL_RE.match(f).group(1)))
    return {"name": name, "plan": load(d / "plan.json"), "busy": busy(name),
            "videos": [media(f) for f in ("final.mp4", "composite.mp4") if (d / f).is_file()],
            "sheet": media("contact_sheet.png") if (d / "contact_sheet.png").is_file() else None,
            "stills": [dict(media(f), t=float(STILL_RE.match(f).group(1))) for f in stills]}


@app.get("/api/works/{name}/file/{rel:path}")
def work_file(name: str, rel: str):
    p = inside(work_dir(name), rel)
    if not p.is_file():
        raise HTTPException(404, f"no file {rel}")
    return FileResponse(p)                                   # Starlette answers Range requests (206) for seeking


@app.put("/api/works/{name}/words")
def save_words(name: str, body: dict = Body(...)):
    d = work_dir(name)
    if busy(name) == "running":
        raise HTTPException(409, "a job is running on this edit; save when it finishes")
    plan = load(d / "plan.json")
    words = clean_words(body.get("words"), duration(plan))
    wj = d / "words.json"
    write_json(wj, dict(load(wj) if wj.is_file() else {}, words=words))   # make_plan reads words.json on re-plan
    write_json(d / "plan.json", dict(plan, words=words))                 # render reads plan.json words
    return {"saved": len(words)}


@app.get("/api/styles")
def styles():
    return [{"name": d.name, "sequence": load(d / "theme.json").get("sequence")}
            for d in sorted(SKILLS.iterdir()) if (d / "theme.json").is_file()]


@app.post("/api/works/{name}/jobs")
def start_job(name: str, body: dict = Body(...)):
    d = work_dir(name)
    kind = body.get("kind")
    steps = job_steps(kind, d, load(d / "plan.json"), body)
    with LOCK:
        if any(j["work"] == name and j["kind"] == kind and j["state"] in ("queued", "running") for j in JOBS.values()):
            raise HTTPException(409, f"{kind} is already queued for {name}")
        job = {"id": next(IDS), "work": name, "kind": kind, "state": "queued", "steps": steps, "cwd": str(d), "log": []}
        JOBS[job["id"]] = job
    QUEUE.put(job)
    return public(job)


@app.get("/api/jobs")
def jobs():
    return [public(j) for j in JOBS.values()]


@app.get("/api/jobs/{jid}")
def job_log(jid: int, since: int = 0):
    job = JOBS.get(jid)
    if not job:
        raise HTTPException(404, f"no job {jid}")
    since = max(0, since)
    lines = job["log"][since:]
    return public(job) | {"log": lines, "next": since + len(lines)}


# ---------- entry ----------
def self_test():
    import tempfile
    global ROOT

    def rejects(fn, *args):
        try:
            fn(*args)
        except HTTPException:
            return True
        return False

    with tempfile.TemporaryDirectory() as tmp:
        ROOT = Path(tmp).resolve()
        (ROOT / "w1").mkdir()
        (ROOT / "w1" / "plan.json").write_text('{"output": {"duration": 9.7}}', "utf-8")
        (ROOT / "empty").mkdir()
        assert work_dir("w1") == ROOT / "w1"
        assert all(rejects(work_dir, b) for b in ("", "..", "../x", "w1/..", "w1/../..", "empty", "nope", "C:/Windows", "/etc"))
        w1 = ROOT / "w1"
        assert inside(w1, "deliver/final.mp4") == w1 / "deliver" / "final.mp4"
        assert all(rejects(inside, w1, b) for b in ("../plan.json", "..\\..\\x", "C:/Windows/win.ini", "/etc/passwd", "D:x"))
        write_json(w1 / "plan.json", {"output": {"duration": 9.7}, "words": []})
        assert (w1 / "plan.json.bak").is_file() and load(w1 / "plan.json")["words"] == []
    good = clean_words([{"w": "हर", "start": 0, "end": 0.28, "p": 1.0}, {"w": " बात ", "start": 0.3, "end": 0.7}], 9.7)
    assert good[0]["p"] == 1.0 and good[1]["w"] == "बात" and good[1]["start"] == 0.3
    bad_words = ([], "x", [{"w": "", "start": 0, "end": 1}], [{"w": "a", "start": 2, "end": 1}],
                 [{"w": "a", "start": 0, "end": 99}], [{"w": "a", "start": "0", "end": 1}],
                 [{"w": "a", "start": float("nan"), "end": 1}], [{"w": "a", "start": True, "end": 1}],
                 [{"w": "a", "start": 1, "end": 2}, {"w": "b", "start": 0.5, "end": 3}])
    assert all(rejects(clean_words, b, 9.7) for b in bad_words)
    assert token_ok(TOKEN) and not token_ok(None) and not token_ok("") and not token_ok("ü" + TOKEN[1:])
    ft = frame_times(None, 9.7)
    assert len(ft) == 6 and 0 < ft[0] and ft[-1] < 9.7 and frame_times([1, 2.5], 9.7) == [1, 2.5]
    assert rejects(frame_times, [9.7], 9.7) and rejects(frame_times, [], 9.7) and rejects(frame_times, "1,2", 9.7)
    assert rejects(skin_dir, "../video-studio-core") and rejects(skin_dir, "video-studio-core") and rejects(skin_dir, "")
    print("self-test ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="folder whose sub-folders are work folders (each with plan.json)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true", help="print the URL, do not open a browser")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.root:
        ap.error("--root is required")
    global ROOT
    ROOT = Path(a.root).resolve()
    if not ROOT.is_dir():
        sys.exit(f"--root is not a folder: {ROOT}")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=a.port, log_level="warning"))
    url = f"http://127.0.0.1:{a.port}/?t={TOKEN}"

    def announce():                                          # only once the port is really bound
        while not server.started:
            time.sleep(0.1)
        print(f"review app: {url}", flush=True)
        if not a.no_open:
            webbrowser.open(url)

    threading.Thread(target=announce, daemon=True).start()
    threading.Thread(target=run_jobs, daemon=True).start()
    server.run()


if __name__ == "__main__":
    main()
