"""Narration / music-bed / SFX measurements using word-level caption timing.
Imported by analyze_reference.py."""
import os, re, shutil, subprocess
import numpy as np

FF = shutil.which("ffmpeg") or os.path.expanduser("~/.local/bin/ffmpeg")
SR = 16000


def words(vtt):
    """Parse YouTube auto-caption VTT (with <c> word tags) into [(t, word)]."""
    if not vtt or not os.path.exists(vtt):
        return []
    out, cue_start = [], None
    for ln in open(vtt, encoding="utf-8", errors="ignore"):
        m = re.match(r"(\d+):(\d+):([\d.]+) -->", ln)
        if m:
            cue_start = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]); continue
        if "<c>" not in ln:
            continue
        first = re.match(r"^([^<]+)<", ln)
        if first and first[1].strip():
            out.append((cue_start, first[1].strip()))
        for t, w in re.findall(r"<(\d+:\d+:[\d.]+)><c>([^<]*)</c>", ln):
            h, mi, s = t.split(":")
            out.append((int(h) * 3600 + int(mi) * 60 + float(s), w.strip()))
    return out


def _load(video):
    raw = subprocess.run([FF, "-v", "quiet", "-i", video, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def narration_stats(video, W):
    y = _load(video)
    if y.size < SR:
        return {}
    win, hop = 1024, 256
    n = 1 + (len(y) - win) // hop
    fr = np.lib.stride_tricks.as_strided(y, (n, win), (y.strides[0] * hop, y.strides[0]))
    S = np.abs(np.fft.rfft(fr * np.hanning(win), axis=1))
    fps = SR / hop
    freqs = np.fft.rfftfreq(win, 1 / SR)
    db = 10 * np.log10((S ** 2).mean(1) + 1e-12)
    dur = len(y) / SR
    r = {"duration": round(dur, 2)}
    if W:
        times = np.array([t for t, _ in W])
        mask = np.zeros(len(db), bool)
        for i, t in enumerate(times):
            end = min(times[i + 1] if i + 1 < len(times) else t + 0.5, t + 0.6)
            mask[int(t * fps):int(end * fps)] = True
        gaps = np.diff(times)
        text = " ".join(w for _, w in W)
        sents = [s for s in re.split(r"[.!?]", text) if s.strip()]
        r.update({
            "words": len(W),
            "wpm": round(len(W) / (times[-1] - times[0] + 0.5) * 60),
            "speech_starts_at_s": round(float(times[0]), 2),
            "tail_after_speech_s": round(dur - float(times[-1]), 2),
            "pauses_over_0.6s": int((gaps > 0.6).sum()),
            "longest_pause_s": round(float(gaps.max()), 2) if len(gaps) else 0,
            "speech_coverage": round(float(mask.mean()), 3),
            "avg_words_per_sentence": round(float(np.mean([len(s.split()) for s in sents])), 1) if sents else 0,
            "questions": text.count("?"),
            "you_count": len(re.findall(r"\byou(r)?\b", text, re.I)),
            "first_sentence": sents[0].strip() if sents else "",
            "last_sentence": sents[-1].strip() if sents else "",
            "full_text": text,
        })
        if (~mask).sum() > fps:
            r["speech_over_bed_db"] = round(float(np.median(db[mask]) - np.median(db[~mask])), 1)
    flux = np.maximum(0, np.diff(np.log1p(S), axis=0))
    hi, lo = flux[:, freqs > 3000].sum(1), flux[:, freqs < 200].sum(1)
    z = lambda a: (a - np.median(a)) / (np.percentile(a, 90) - np.median(a) + 1e-9)

    def peaks(a, thr=4):
        p = []
        for i in range(1, len(a) - 1):
            if a[i] > thr and a[i] >= a[i - 1] and a[i] >= a[i + 1]:
                t = i / fps
                if not p or t - p[-1] > 0.25:
                    p.append(round(t, 2))
        return p
    r["sfx_high_transients"] = peaks(z(hi))   # whooshes, pops, clicks, swishes
    r["sfx_low_transients"] = peaks(z(lo))    # booms, thuds, impacts
    r["sfx_high_per_10s"] = round(len(r["sfx_high_transients"]) / dur * 10, 1)
    r["sfx_low_per_10s"] = round(len(r["sfx_low_transients"]) / dur * 10, 1)
    last = db[-int(fps):]
    r["end_fades_out"] = bool(last[-int(fps * 0.3):].mean() < db.mean() - 15)
    return r
