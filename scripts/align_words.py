#!/usr/bin/env python3
"""Produce word-level timings [{"w","t","end"}] for captions and edit planning.

  # accurate (downloads a ~150 MB speech model the first time; ask the user before using it):
  uv run --no-project --python 3.12 --with faster-whisper --with numpy python scripts/align_words.py vo.wav script.txt words.json --whisper

  # offline heuristic (no model; spreads the script's words across detected speech):
  uv run --no-project --python 3.12 --with numpy python scripts/align_words.py vo.wav script.txt words.json

The heuristic is good enough for captions within ~0.15 s on clean, fast VO; use
--whisper when cuts must land on exact words.
"""
import json, re, shutil, subprocess, sys, os
import numpy as np

FF = shutil.which("ffmpeg") or os.path.expanduser("~/.local/bin/ffmpeg")
SR = 16000


def load(path):
    raw = subprocess.run([FF, "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def heuristic(audio, text):
    y = load(audio)
    hop = 160  # 10 ms
    n = len(y) // hop
    rms = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    thr = max(np.percentile(db, 20) + 6, db.max() - 38)
    voiced = db > thr
    # close tiny gaps (<60 ms) so words are not split
    k = 6
    v = voiced.copy()
    for i in range(len(v)):
        if not v[i] and voiced[max(0, i - k):i].any() and voiced[i:i + k].any():
            v[i] = True
    words = re.findall(r"\S+", text)
    # weight = characters + pause bonus after punctuation
    wts = [len(re.sub(r"\W", "", w)) + 1.5 for w in words]
    cum_voice = np.cumsum(v) / max(1, v.sum())
    times = np.arange(len(v)) * hop / SR
    out, acc, total = [], 0.0, sum(wts)
    for w, wt in zip(words, wts):
        s = acc / total
        e = (acc + wt) / total
        ts = float(times[min(len(times) - 1, np.searchsorted(cum_voice, s + 1e-6))])
        te = float(times[min(len(times) - 1, np.searchsorted(cum_voice, e - 1e-6))])
        out.append({"w": w, "t": round(ts, 3), "end": round(max(te, ts + 0.08), 3)})
        acc += wt
    return out


def whisper(audio):
    from faster_whisper import WhisperModel
    m = WhisperModel("base.en", compute_type="int8")
    segs, _ = m.transcribe(audio, word_timestamps=True, vad_filter=False)
    out = []
    for s in segs:
        for w in s.words:
            out.append({"w": w.word.strip(), "t": round(w.start, 3), "end": round(w.end, 3)})
    return out


if __name__ == "__main__":
    audio, script, dst = sys.argv[1:4]
    text = open(script).read()
    res = whisper(audio) if "--whisper" in sys.argv else heuristic(audio, text)
    json.dump(res, open(dst, "w"), indent=0)
    print(f"{len(res)} words -> {dst}; first: {res[:3]}")
