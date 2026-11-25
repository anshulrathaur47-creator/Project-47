#!/usr/bin/env python3
"""Steady a face-swapped shot: kill frame-to-frame shimmer in the swapped face without smearing motion.

For each frame, the previous smoothed swap RESIDUAL (swapped minus original) is warped onto the current frame with optical flow computed on the
ORIGINAL footage (so it follows the real head motion), then blended with the current swapped frame, only inside
the area the swap changed. That is a motion-compensated temporal average: the face holds still where the head
holds still, and follows it where it moves.

Usage: python3 tools/face_stabilize.py <original_shot> <swapped_shot> <out.mp4> [--strength 0.6]
  strength: how much of the previous frame to keep (0 = off, 0.6 = strong, 0.8 = very strong)
"""
import argparse
import subprocess

import cv2
import numpy as np


def frames(path):
    cap = cv2.VideoCapture(path)
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield f
    cap.release()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("original")
    ap.add_argument("swapped")
    ap.add_argument("out")
    ap.add_argument("--strength", type=float, default=0.6)
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.swapped)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                            "-c:v", "libx264", "-crf", "0", "-preset", "veryfast", "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
    prev_o = prev_res = None
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
    for o, s in zip(frames(a.original), frames(a.swapped)):
        sf = s.astype(np.float32)
        # where did the swap change the picture? (soft mask)
        diff = cv2.cvtColor(cv2.absdiff(s, o), cv2.COLOR_BGR2GRAY).astype(np.float32)
        m = cv2.GaussianBlur((diff > 6).astype(np.float32), (0, 0), 6)
        m = cv2.dilate(m, np.ones((9, 9), np.uint8))
        m = np.clip(cv2.GaussianBlur(m, (0, 0), 8) * 1.5, 0, 1)[..., None]
        of = o.astype(np.float32)
        # smooth the swap's RESIDUAL (swapped - original), not the picture: the original's motion and grain stay exact,
        # only the frame-to-frame wobble of the new face is averaged out
        res = (sf - of) * m
        if prev_res is None:
            res_s = res
        else:
            g0, g1 = cv2.cvtColor(prev_o, cv2.COLOR_BGR2GRAY), cv2.cvtColor(o, cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(g1, g0, None, 0.5, 4, 21, 3, 5, 1.1, 0)   # current -> previous
            warped = cv2.remap(prev_res, gx + flow[..., 0], gy + flow[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            mag = np.linalg.norm(flow, axis=2)
            k = (a.strength * np.clip(1.0 - (mag - 2.0) / 10.0, 0.3, 1.0))[..., None]   # less history on fast moves
            res_s = res * (1 - k) + warped * k
        out = of + res_s
        enc.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
        prev_o, prev_res = o, res_s
    enc.stdin.close()
    enc.wait()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
