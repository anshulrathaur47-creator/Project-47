"""Re-join the shots: face-swapped main-character shots + untouched shots, original audio.

Swapped shots get a light temporal smoothing (hqdn3d, temporal only) so the face doesn't shimmer frame to frame.
Usage: python3 assemble.py [vN]
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, "work")
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "raw-videos", "2026-11-25-taxi", "taxi_source.mp4")
ver = sys.argv[1] if len(sys.argv) > 1 else "v2"
segs = [l.split() for l in open(os.path.join(W, "segs.txt")).read().split("\n") if l]
inputs, chains = [], []
for k, (i, a, b, m) in enumerate(segs):
    path = os.path.join(W, f"out{int(i):02d}.mp4") if m == "1" else os.path.join(W, f"seg{int(i):02d}.mkv")
    inputs += ["-i", path]
    f = f"[{k}:v]setpts=PTS-STARTPTS,format=yuv420p"
    if m == "1":
        f += ",hqdn3d=0:0:5:5"
    chains.append(f + f"[v{k}]")
n = len(segs)
graph = ";".join(chains) + ";" + "".join(f"[v{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0[v]"
out = os.path.join(ROOT, "exports", f"2026-11-25_taxi-faceswap_{ver}.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-i", SRC, "-filter_complex", graph, "-map", "[v]", "-map", f"{n}:a",
                "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", out], check=True)
print("wrote", out)
