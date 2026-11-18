#!/usr/bin/env python3
"""Compare a remake against its reference short.

  uv run --no-project --python 3.12 --with numpy --with opencv-python-headless \
      python scripts/compare.py reference.mp4 remake.mp4 out_dir

Writes:
  out_dir/side_by_side.mp4   reference | remake, timecoded; audio: LEFT ear = reference, RIGHT ear = remake
  out_dir/pairs_NN.jpg       paired frames every second (reference left, remake right)
  out_dir/report.md/.json    measured gaps: timing, cut alignment, colour, motion, captions band, loudness
"""
import json, os, shutil, subprocess, sys
import numpy as np
import cv2

FF = shutil.which("ffmpeg") or os.path.expanduser("~/.local/bin/ffmpeg")


def frames(path, size=(180, 320)):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(cv2.resize(f, size, interpolation=cv2.INTER_AREA))
    return np.array(out), fps


def change_curve(F):
    hs = []
    for f in F:
        h = cv2.calcHist([cv2.cvtColor(f, cv2.COLOR_BGR2HSV)], [0, 1], None, [24, 16], [0, 180, 0, 256])
        cv2.normalize(h, h); hs.append(h)
    d = np.zeros(len(F))
    for k in range(4, len(F)):
        d[k] = cv2.compareHist(hs[k - 4], hs[k], cv2.HISTCMP_BHATTACHARYYA)
    return d


def boundaries(d, fps, thr=0.3):
    b = []
    for k in range(1, len(d) - 1):
        if d[k] > thr and d[k] >= d[k - 1] and d[k] >= d[k + 1] and (not b or k - b[-1] > fps * 0.3):
            b.append(k)
    return np.array(b) / fps


def loud(path):
    e = subprocess.run([FF, "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    get = lambda key: float(e.split(key)[-1].split()[0])
    return {"lufs": get("I:"), "lra": get("LRA:"), "peak": get("Peak:")}


def lab(f):
    return cv2.cvtColor(f, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)


def main():
    ref, rem, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    A, fa = frames(ref); B, fb = frames(rem)
    n = min(len(A), len(B))
    A, B = A[:n], B[:n]
    fps = fa
    # per-second colour difference (mean LAB distance of average colour) and layout similarity
    per_sec = []
    for s in range(int(n / fps)):
        k = int(s * fps + fps / 2)
        a, b = A[k], B[k]
        dcol = float(np.linalg.norm(lab(a).mean(0) - lab(b).mean(0)))
        ga = cv2.GaussianBlur(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (21, 21), 0).astype(np.float32)
        gb = cv2.GaussianBlur(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (21, 21), 0).astype(np.float32)
        corr = float(np.corrcoef(ga.ravel(), gb.ravel())[0, 1])
        per_sec.append({"t": s, "colour_delta": round(dcol, 1), "layout_corr": round(corr, 2)})
    da, db = change_curve(A), change_curve(B)
    ba, bb = boundaries(da, fps), boundaries(db, fps)
    matched = [float(np.min(np.abs(bb - x))) for x in ba] if len(bb) else []
    motion = lambda F: float(np.mean(np.abs(np.diff(F.astype(np.int16), axis=0))))
    sat = lambda F: float(np.mean([cv2.cvtColor(f, cv2.COLOR_BGR2HSV)[..., 1].mean() for f in F[::10]]))
    bri = lambda F: float(np.mean([cv2.cvtColor(f, cv2.COLOR_BGR2HSV)[..., 2].mean() for f in F[::10]]))
    la, lb = loud(ref), loud(rem)
    rep = {
        "duration_s": [round(len(A) / fa, 2), round(len(B) / fb, 2)],
        "scene_changes": [len(ba), len(bb)],
        "scene_change_alignment": {"median_offset_s": round(float(np.median(matched)), 3) if matched else None,
                                   "within_0.2s_pct": round(100 * np.mean(np.array(matched) <= 0.2), 1) if matched else None},
        "mean_motion": [round(motion(A), 2), round(motion(B), 2)],
        "saturation": [round(sat(A), 1), round(sat(B), 1)],
        "brightness": [round(bri(A), 1), round(bri(B), 1)],
        "colour_delta_mean": round(float(np.mean([p["colour_delta"] for p in per_sec])), 1),
        "layout_corr_mean": round(float(np.mean([p["layout_corr"] for p in per_sec])), 2),
        "loudness": {"reference": la, "remake": lb},
        "per_second": per_sec,
    }
    json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1)
    worst = sorted(per_sec, key=lambda p: p["layout_corr"])[:6]
    md = ["# Remake vs reference", "", "| metric | reference | remake |", "|---|---|---|",
          f"| duration (s) | {rep['duration_s'][0]} | {rep['duration_s'][1]} |",
          f"| scene changes detected | {rep['scene_changes'][0]} | {rep['scene_changes'][1]} |",
          f"| mean motion (pixel change/frame) | {rep['mean_motion'][0]} | {rep['mean_motion'][1]} |",
          f"| saturation | {rep['saturation'][0]} | {rep['saturation'][1]} |",
          f"| brightness | {rep['brightness'][0]} | {rep['brightness'][1]} |",
          f"| loudness LUFS / peak | {la['lufs']} / {la['peak']} | {lb['lufs']} / {lb['peak']} |", "",
          f"- Scene-change alignment: median offset {rep['scene_change_alignment']['median_offset_s']} s, "
          f"{rep['scene_change_alignment']['within_0.2s_pct']} % of reference changes have a remake change within 0.2 s",
          f"- Mean colour difference per second (LAB distance of average colour): {rep['colour_delta_mean']} (0 = identical, >20 obvious)",
          f"- Mean layout correlation per second (blurred greyscale): {rep['layout_corr_mean']} (1 = same composition)",
          "- Least similar seconds: " + ", ".join(f"{p['t']}s (corr {p['layout_corr']})" for p in worst)]
    open(os.path.join(out, "report.md"), "w").write("\n".join(md) + "\n")
    # paired frames every second
    pairs = []
    for s in range(int(n / fps)):
        k = int(s * fps + fps / 2)
        p = np.hstack([A[k], np.full((320, 4, 3), 255, np.uint8), B[k]])
        cv2.putText(p, f"{s}s", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        pairs.append(p)
    cols = 5
    for j in range(0, len(pairs), cols * 2):
        rows = []
        for r in range(2):
            chunk = pairs[j + r * cols:j + (r + 1) * cols]
            if not chunk:
                continue
            while len(chunk) < cols:
                chunk.append(np.zeros_like(pairs[0]))
            rows.append(np.hstack([np.pad(c, ((4, 4), (4, 4), (0, 0))) for c in chunk]))
        cv2.imwrite(os.path.join(out, f"pairs_{j // (cols * 2):02d}.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
    # side-by-side video with split-ear audio
    sbs = os.path.join(out, "side_by_side.mp4")
    fc = ("[0:v]scale=540:960,setsar=1,drawtext=text='REFERENCE':x=10:y=10:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5[a];"
          "[1:v]scale=540:960,setsar=1,drawtext=text='REMAKE':x=10:y=10:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5,"
          "drawtext=text='%{pts\\:hms}':x=w-tw-10:y=10:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.5[b];"
          "[a][b]hstack=inputs=2[v];"
          "[0:a]aresample=48000,pan=mono|c0=0.5*c0+0.5*c1[al];[1:a]aresample=48000,pan=mono|c0=c0[ar];"
          "[al][ar]join=inputs=2:channel_layout=stereo[aout]")
    r = subprocess.run([FF, "-y", "-v", "error", "-i", ref, "-i", rem, "-filter_complex", fc, "-map", "[v]", "-map", "[aout]",
                        "-c:v", "libx264", "-crf", "22", "-preset", "veryfast", "-c:a", "aac", "-shortest", sbs], capture_output=True, text=True)
    if r.returncode:
        # drawtext needs a font config on some systems; retry without labels
        fc2 = "[0:v]scale=540:960,setsar=1[a];[1:v]scale=540:960,setsar=1[b];[a][b]hstack=inputs=2[v];" + fc.split("[v];", 1)[1]
        subprocess.run([FF, "-y", "-v", "error", "-i", ref, "-i", rem, "-filter_complex", fc2, "-map", "[v]", "-map", "[aout]",
                        "-c:v", "libx264", "-crf", "22", "-preset", "veryfast", "-c:a", "aac", "-shortest", sbs], check=True)
    print(open(os.path.join(out, "report.md")).read())


if __name__ == "__main__":
    main()
