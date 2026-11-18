#!/usr/bin/env python3
"""Frame-accurate shot map of a reference short, as the basis for a remake.

  uv run --no-project --python 3.12 --with numpy --with opencv-python-headless \
      python scripts/shot_map.py ref.mp4 out_dir [--words words.json]

Writes out_dir/shotmap.json with, per frame-range shot: start/end (s and frame), how it begins
(hard cut / dissolve), measured camera motion (zoom % and pan as fraction of frame over the shot),
mean colour, plus caption-card change times (burned-in captions). Also writes
out_dir/shots/shot_NN_{first,mid,last}.jpg keyframes for each shot, which are the reference
images to recreate, and out_dir/boundaries.jpg, a strip of frames around every boundary for checking.
"""
import argparse, json, os
import numpy as np
import cv2


def hist(fr):
    hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
    h = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256])
    cv2.normalize(h, h)
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--min-shot", type=float, default=0.35)
    ap.add_argument("--soft", type=float, default=0.24, help="8-frame histogram distance for dissolves")
    ap.add_argument("--cap-y", type=float, nargs=2, default=[0.62, 0.76], help="caption band (fraction of height)")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "shots"), exist_ok=True)
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frames, hs, grays, capmasks, means = [], [], [], [], []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        small = cv2.resize(fr, (180, 320), interpolation=cv2.INTER_AREA)
        frames.append(small)
        H = small.shape[0]
        y0, y1 = int(a.cap_y[0] * H), int(a.cap_y[1] * H)
        # mask the caption band out of the scene measurements (captions change constantly)
        scene = small.copy(); scene[y0:y1] = 0
        hs.append(hist(scene))
        g = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY).astype(np.float32)
        grays.append(g)
        band = small[y0:y1]
        white = (band.min(axis=2) > 225).astype(np.uint8)
        capmasks.append(white)
        means.append(small.reshape(-1, 3).mean(0)[::-1])
    n = len(frames)
    d1 = np.zeros(n); d8 = np.zeros(n); dx = np.zeros(n); dy = np.zeros(n); dz = np.zeros(n); resp = np.zeros(n)
    win = cv2.createHanningWindow((180, 320), cv2.CV_32F)
    for k in range(1, n):
        d1[k] = cv2.compareHist(hs[k - 1], hs[k], cv2.HISTCMP_BHATTACHARYYA)
        if k >= 8:
            d8[k] = cv2.compareHist(hs[k - 8], hs[k], cv2.HISTCMP_BHATTACHARYYA)
        (sx, sy), r = cv2.phaseCorrelate(grays[k - 1], grays[k], win)
        dx[k], dy[k], resp[k] = sx, sy, r
        c = (90, 120)
        lp1 = cv2.warpPolar(grays[k - 1], (128, 128), c, 140, cv2.WARP_POLAR_LOG)
        lp2 = cv2.warpPolar(grays[k], (128, 128), c, 140, cv2.WARP_POLAR_LOG)
        (zx, _), zr = cv2.phaseCorrelate(lp1, lp2)
        dz[k] = np.exp(zx * np.log(140) / 128) - 1 if zr > 0.15 else 0.0
    # boundaries
    bounds = []
    minf = int(a.min_shot * fps)
    for k in range(1, n):
        hard = d1[k] > 0.35 and d1[k] > 3 * np.median(d1[max(1, k - 6):k + 6]) + 0.08
        if hard and (not bounds or k - bounds[-1][0] >= minf):
            bounds.append((k, "cut"))
    for k in range(9, n - 1):
        if d8[k] > a.soft and d8[k] >= d8[k - 1] and d8[k] >= d8[k + 1] and d1[k - 7:k + 1].max() < 0.3:
            c = k - 4
            if all(abs(c - b) >= minf for b, _ in bounds):
                bounds.append((c, "dissolve"))
    bounds.sort()
    edges = [0] + [b for b, _ in bounds] + [n]
    kinds = ["start"] + [t for _, t in bounds]
    shots = []
    for i in range(len(edges) - 1):
        s, e = edges[i], edges[i + 1]
        ks = range(s + 1, e)
        good = [k for k in ks if resp[k] > 0.2]
        pan_x = float(sum(dx[k] for k in good)) / 180
        pan_y = float(sum(dy[k] for k in good)) / 320
        zoom = float(np.prod([1 + dz[k] for k in ks])) - 1 if e - s > 1 else 0
        mid = (s + e) // 2
        for tag, f in (("first", s), ("mid", mid), ("last", max(s, e - 1))):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, big = cap.read()
            if ok:
                cv2.imwrite(os.path.join(a.out, "shots", f"shot_{i + 1:02d}_{tag}.jpg"), big, [cv2.IMWRITE_JPEG_QUALITY, 88])
        shots.append({
            "shot": i + 1, "start": round(s / fps, 3), "end": round(e / fps, 3), "dur": round((e - s) / fps, 3),
            "start_frame": s, "end_frame": e, "begins_with": kinds[i],
            "camera": {"zoom_pct": round(zoom * 100, 1), "pan_x_frac": round(-pan_x, 3), "pan_y_frac": round(-pan_y, 3),
                       "motion_energy": round(float(np.mean([abs(dx[k]) + abs(dy[k]) for k in ks]) if len(ks) else 0), 2)},
            "mean_rgb": [int(v) for v in np.mean(means[s:e], axis=0)],
        })
    # caption card changes
    capt = []
    for k in range(1, n):
        a_, b_ = capmasks[k - 1], capmasks[k]
        diff = np.logical_xor(a_, b_).mean()
        if diff > 0.004 and (not capt or k - capt[-1] > 3):
            capt.append(k)
    out = {"fps": fps, "frames": n, "duration": round(n / fps, 3), "shot_count": len(shots), "shots": shots,
           "caption_changes_s": [round(k / fps, 3) for k in capt]}
    json.dump(out, open(os.path.join(a.out, "shotmap.json"), "w"), indent=1)
    # boundary strips: 6 frames around each boundary
    rows = []
    for b, kind in bounds:
        idx = [max(0, min(n - 1, b + o)) for o in (-6, -3, -1, 0, 1, 3, 6)]
        row = np.hstack([cv2.resize(frames[i], (90, 160)) for i in idx])
        cv2.putText(row, f"{b / fps:.2f}s {kind}", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        rows.append(row)
    for j in range(0, len(rows), 12):
        cv2.imwrite(os.path.join(a.out, f"boundaries_{j // 12:02d}.jpg"), np.vstack(rows[j:j + 12]))
    print(f"{len(shots)} shots, {len(capt)} caption changes")
    for s in shots:
        print(f"{s['shot']:2d} {s['start']:6.2f}-{s['end']:6.2f} ({s['dur']:4.2f}s) {s['begins_with']:8s} zoom {s['camera']['zoom_pct']:+5.1f}% "
              f"pan x {s['camera']['pan_x_frac']:+.3f} y {s['camera']['pan_y_frac']:+.3f}")


if __name__ == "__main__":
    main()
