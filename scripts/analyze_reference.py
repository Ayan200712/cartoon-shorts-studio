"""Measure reference shorts so their style can be copied with numbers, not vibes.

  uv run --no-project --python 3.12 --with numpy --with opencv-python-headless \
      python scripts/analyze_reference.py <videos_dir> <out_dir>

<videos_dir> holds <id>.mp4 files, optionally <id>.info.json and <id>.en-orig.vtt
(yt-dlp --write-info-json --write-auto-subs). Per video it writes
<out_dir>/<id>/report.json and contact sheets <out_dir>/<id>/sheet_NN.jpg (a frame
every 0.5 s, timestamped) for visual review, plus <out_dir>/all_reports.json.
See references/analyzing-references.md for how to read the numbers.
"""
import json, os, subprocess, sys, glob, re
import numpy as np
import cv2

import shutil
FFMPEG = shutil.which("ffmpeg") or os.path.expanduser("~/.local/bin/ffmpeg")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _audio_deep import words as vtt_words, narration_stats


def vtt_text(path):
    if not path or not os.path.exists(path):
        return ""
    lines, seen = [], set()
    for ln in open(path, encoding="utf-8", errors="ignore"):
        ln = ln.strip()
        if not ln or "-->" in ln or ln.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        ln = re.sub(r"<[^>]+>", "", ln)
        if ln not in seen:
            seen.add(ln); lines.append(ln)
    return " ".join(lines)


def audio_features(video):
    sr = 22050
    raw = subprocess.run([FFMPEG, "-v", "quiet", "-i", video, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True).stdout
    y = np.frombuffer(raw, dtype=np.float32)
    if y.size == 0:
        return {"has_audio": False}
    hop, win = 512, 2048
    n = 1 + (len(y) - win) // hop
    frames = np.lib.stride_tricks.as_strided(y, (n, win), (y.strides[0] * hop, y.strides[0]))
    rms = np.sqrt((frames ** 2).mean(1) + 1e-12)
    spec = np.abs(np.fft.rfft(frames * np.hanning(win), axis=1))
    freqs = np.fft.rfftfreq(win, 1 / sr)
    centroid = (spec * freqs).sum(1) / (spec.sum(1) + 1e-9)
    flux = np.maximum(0, np.diff(np.log1p(spec), axis=0)).sum(1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    # onset peaks
    thr = 1.5
    peaks = [i for i in range(1, len(flux) - 1) if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
    # dedupe peaks within 80ms
    t = np.array(peaks) * hop / sr
    onsets = []
    for x in t:
        if not onsets or x - onsets[-1] > 0.08:
            onsets.append(float(x))
    dur = len(y) / sr
    # tempo via autocorrelation of onset envelope
    env = np.maximum(flux, 0)
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    fps = sr / hop
    lo, hi = int(fps * 60 / 200), int(fps * 60 / 60)
    lag = lo + int(np.argmax(ac[lo:hi])) if hi > lo else 0
    tempo = 60 * fps / lag if lag else 0
    beat_strength = float(ac[lag] / (ac[0] + 1e-9)) if lag else 0
    db = 20 * np.log10(rms + 1e-9)
    silence = float((db < -45).mean())
    # low / mid / high energy balance
    bands = {"sub_bass<120": (0, 120), "low_mid120-800": (120, 800), "mid800-4k": (800, 4000), "high>4k": (4000, sr / 2)}
    tot = spec.sum() + 1e-9
    band_share = {k: round(float(spec[:, (freqs >= a) & (freqs < b)].sum() / tot), 3) for k, (a, b) in bands.items()}
    # loudness timeline per second
    per_sec = [round(float(db[int(i * fps):int((i + 1) * fps)].mean()), 1) for i in range(int(dur))]
    return {
        "has_audio": True, "duration": round(dur, 2),
        "peak_dbfs": round(float(20 * np.log10(np.abs(y).max() + 1e-9)), 1),
        "mean_rms_db": round(float(db.mean()), 1),
        "dynamic_range_db_p95_p10": round(float(np.percentile(db, 95) - np.percentile(db, 10)), 1),
        "silence_fraction": round(silence, 3),
        "onsets_per_sec": round(len(onsets) / dur, 2),
        "onset_times": [round(o, 2) for o in onsets],
        "tempo_bpm_est": round(tempo, 1), "beat_regularity": round(beat_strength, 2),
        "spectral_centroid_hz_mean": round(float(centroid.mean())),
        "band_energy_share": band_share,
        "loudness_per_sec_db": per_sec,
    }


def phase_shift(a, b):
    (dx, dy), resp = cv2.phaseCorrelate(a, b)
    return dx, dy, resp


def video_features(video, outdir):
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    prev_small = prev_hist = prev_gray = None
    diffs, hdiffs, sats, vals, shifts, scales, thumbs = [], [], [], [], [], [], []
    palette_samples = []
    changed = []
    hists = []
    prev_fine = None
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        small = cv2.resize(fr, (90, 160), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256]); cv2.normalize(hist, hist)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
        sats.append(float(hsv[..., 1].mean())); vals.append(float(hsv[..., 2].mean()))
        if prev_small is not None:
            diffs.append(float(np.abs(small.astype(np.int16) - prev_small.astype(np.int16)).mean()))
            hdiffs.append(float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)))
            dx, dy, resp = phase_shift(prev_gray, gray)
            shifts.append((dx, dy, resp))
            # zoom estimate via log-polar
            lp1 = cv2.warpPolar(prev_gray, (64, 64), (45, 80), 80, cv2.WARP_POLAR_LOG)
            lp2 = cv2.warpPolar(gray, (64, 64), (45, 80), 80, cv2.WARP_POLAR_LOG)
            (sx, sy), r2 = cv2.phaseCorrelate(lp1, lp2)
            scales.append((sx, r2))
        else:
            diffs.append(0.0); hdiffs.append(0.0); shifts.append((0, 0, 0)); scales.append((0, 0))
        if i % max(1, int(fps / 2)) == 0:
            palette_samples.append(cv2.resize(fr, (36, 64)).reshape(-1, 3))
        if i % max(1, int(round(fps / 2))) == 0:
            thumbs.append((i / fps, cv2.resize(fr, (180, 320))))
        fine = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(fr, (216, 384)), cv2.COLOR_BGR2GRAY), (3, 3), 0).astype(np.int16)
        if prev_fine is not None:
            changed.append(float((np.abs(fine - prev_fine) > 14).mean()))
        prev_fine = fine
        hists.append(hist)
        prev_small, prev_hist, prev_gray = small, hist, gray
        i += 1
    n = i
    diffs, hdiffs = np.array(diffs), np.array(hdiffs)
    # cut detection: histogram jump that is a local spike
    cuts = []
    for k in range(1, n):
        h = hdiffs[k]
        local = np.median(hdiffs[max(1, k - 6):k + 6]) if n > 2 else 0
        if (h > 0.35 and h > 3 * local + 0.08) or (diffs[k] > 45 and h > 0.2):
            if not cuts or k - cuts[-1] > 3:
                cuts.append(k)
    cut_times = [round(c / fps, 2) for c in cuts]
    # soft transitions (cross-dissolves / morphs) that a hard-cut detector misses:
    # big change across an 8-frame window while no single frame jumps
    soft, lag = [], 8
    d8 = np.zeros(n)
    for k in range(lag, n):
        d8[k] = cv2.compareHist(hists[k - lag], hists[k], cv2.HISTCMP_BHATTACHARYYA)
    for k in range(lag + 1, n - 1):
        win = hdiffs[k - lag + 1:k + 1]
        if d8[k] > 0.26 and d8[k] >= d8[k - 1] and d8[k] >= d8[k + 1] and win.max() < 0.25 \
                and all(abs(k - c) > lag for c in cuts) and (not soft or k - soft[-1] > lag * 2):
            soft.append(k)
    soft_times = [round((k - lag / 2) / fps, 2) for k in soft]
    all_bounds = sorted(cuts + [int(k - lag / 2) for k in soft])
    bounds = [0] + cuts + [n]
    shot_lens = [(bounds[j + 1] - bounds[j]) / fps for j in range(len(bounds) - 1)]
    # held frames: >0.15% pixels changing = new drawing. Runs of 2/3 = animating on twos/threes.
    c = np.array(changed) if changed else np.zeros(1)
    held = c < 0.0015
    runs, r = [], 1
    for h in held:
        if h: r += 1
        else: runs.append(r); r = 1
    runs.append(r); runs = np.array(runs)
    hold_hist = {str(h): int((runs == h).sum()) for h in range(1, 7)}
    hold_hist["7+"] = int((runs >= 7).sum())
    moving = runs[runs <= 4]
    typical_hold = float(np.median(moving)) if moving.size else 1.0
    # camera motion: coherent global shift with decent response
    cam_pan_frames = sum(1 for (dx, dy, rsp) in shifts if rsp > 0.3 and (abs(dx) + abs(dy)) > 0.4)
    zoom_frames = sum(1 for (sx, r2) in scales if r2 > 0.3 and abs(sx) > 0.35)
    # shake: high-frequency sign flipping of shift
    dxs = np.array([s[0] for s in shifts]); dys = np.array([s[1] for s in shifts])
    flips = int(((np.sign(dxs[1:]) != np.sign(dxs[:-1])) & (np.abs(dxs[1:]) > 0.8) & (np.abs(dxs[:-1]) > 0.8)).sum()
                + ((np.sign(dys[1:]) != np.sign(dys[:-1])) & (np.abs(dys[1:]) > 0.8) & (np.abs(dys[:-1]) > 0.8)).sum())
    # flash frames: brightness spikes
    v = np.array(vals)
    flashes = [round(k / fps, 2) for k in range(1, n - 1) if v[k] - (v[k - 1] + v[k + 1]) / 2 > 35]
    # palette via kmeans
    px = np.concatenate(palette_samples).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, lab, cen = cv2.kmeans(px, 8, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(lab.flatten(), minlength=8)
    order = np.argsort(-counts)
    palette = [{"hex": "#%02x%02x%02x" % tuple(int(c) for c in cen[j][::-1]), "share": round(float(counts[j] / counts.sum()), 3)} for j in order]
    # contact sheets: 4 cols x 4 rows per sheet
    os.makedirs(outdir, exist_ok=True)
    cols, rows = 6, 3
    per = cols * rows
    for s in range(0, len(thumbs), per):
        chunk = thumbs[s:s + per]
        sheet = np.full((rows * 340, cols * 180, 3), 20, np.uint8)
        for j, (t, im) in enumerate(chunk):
            rr, cc = divmod(j, cols)
            sheet[rr * 340:rr * 340 + 320, cc * 180:cc * 180 + 180] = im
            cv2.putText(sheet, f"{t:.1f}s", (cc * 180 + 4, rr * 340 + 335), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.imwrite(os.path.join(outdir, f"sheet_{s // per:02d}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
    cap.release()
    return {
        "fps": round(fps, 2), "resolution": f"{W}x{H}", "frames": n,
        "cut_count": len(cuts), "cut_times": cut_times,
        "soft_transition_count": len(soft), "soft_transition_times": soft_times,
        "total_shots_est": len(all_bounds) + 1,
        "shot_len_incl_soft_mean_s": round((n / fps) / (len(all_bounds) + 1), 2),
        "cuts_per_sec": round(len(cuts) / (n / fps), 2),
        "shot_len_mean_s": round(float(np.mean(shot_lens)), 2), "shot_len_median_s": round(float(np.median(shot_lens)), 2),
        "shot_len_min_s": round(float(np.min(shot_lens)), 2), "shot_len_max_s": round(float(np.max(shot_lens)), 2),
        "hold_run_histogram": hold_hist, "typical_hold_frames": typical_hold,
        "effective_anim_fps_est": round(fps / typical_hold, 1) if typical_hold else None,
        "repeat_frame_share": round(float(held.mean()), 3),
        "small_local_change_share": round(float(((c >= 0.0015) & (c < 0.05)).mean()), 3),
        "big_change_share": round(float((c >= 0.25).mean()), 3),
        "mean_motion": round(float(diffs.mean()), 2),
        "camera_pan_frame_fraction": round(cam_pan_frames / n, 3),
        "zoom_frame_fraction": round(zoom_frames / n, 3),
        "shake_flip_events": flips,
        "flash_frames": flashes,
        "saturation_mean": round(float(np.mean(sats)), 1), "brightness_mean": round(float(np.mean(vals)), 1),
        "saturation_p90": round(float(np.percentile(sats, 90)), 1),
        "palette": palette,
    }


def main():
    vdir, odir = sys.argv[1], sys.argv[2]
    summary = []
    for v in sorted(glob.glob(os.path.join(vdir, "*.mp4"))):
        vid = os.path.basename(v)[:-4]
        out = os.path.join(odir, vid)
        ip = os.path.join(vdir, vid + ".info.json")
        info = json.load(open(ip)) if os.path.exists(ip) else {}
        sub = os.path.join(vdir, vid + ".en-orig.vtt")
        if not os.path.exists(sub):
            sub = os.path.join(vdir, vid + ".en.vtt")
        rep = {
            "id": vid, "title": info.get("title"), "channel": info.get("channel") or info.get("uploader"),
            "channel_followers": info.get("channel_follower_count"), "views": info.get("view_count"),
            "likes": info.get("like_count"), "upload_date": info.get("upload_date"),
            "duration": info.get("duration"), "description": (info.get("description") or "")[:600],
            "tags": info.get("tags", [])[:25],
            "speech_captions": vtt_text(sub)[:3000],
        }
        rep["video"] = video_features(v, out)
        rep["audio"] = audio_features(v)
        rep["narration"] = narration_stats(v, vtt_words(sub))
        json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1)
        summary.append(rep)
        print("done", vid, rep["title"], flush=True)
    json.dump(summary, open(os.path.join(odir, "all_reports.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
