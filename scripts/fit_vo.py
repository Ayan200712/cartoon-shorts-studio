#!/usr/bin/env python3
"""Build a narration track whose lines start and end exactly where you want them (e.g. on a
reference video's shot timings), and write caption word timings for it.

  uv run --no-project --python 3.12 --with numpy python scripts/fit_vo.py lines.json vo.wav words.json [--voice "Reed (English (US))"] [--rate 235]

lines.json: [{"text": "Kyle scanned a stranger's scratch", "start": 0.0, "end": 1.44}, …]
  optional per line: "audio": "lines/01.mp3" (use a pre-generated TTS/recorded clip instead of macOS `say`)

Each clip is silence-trimmed, time-stretched (pitch preserved, 0.62×–1.35×) to fill start→end, and placed
at start. Lines that would need more squeezing than 0.62× are reported: shorten their text.
"""
import argparse, json, os, re, shutil, subprocess, tempfile, wave
import numpy as np

FF = shutil.which("ffmpeg") or os.path.expanduser("~/.local/bin/ffmpeg")
SR = 48000


def load(p):
    raw = subprocess.run([FF, "-v", "quiet", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def trim(y):
    idx = np.where(20 * np.log10(np.abs(y) + 1e-9) > -40)[0]
    return y[max(0, idx[0] - 200): idx[-1] + 800] if len(idx) else y


def stretch(y, factor, tmp):
    a, b = os.path.join(tmp, "i.f32"), os.path.join(tmp, "o.f32")
    y.astype(np.float32).tofile(a)
    tempo, chain = 1 / factor, []
    while tempo > 2.0:
        chain.append("atempo=2.0"); tempo /= 2
    while tempo < 0.5:
        chain.append("atempo=0.5"); tempo /= 0.5
    chain.append(f"atempo={tempo:.5f}")
    subprocess.run([FF, "-v", "quiet", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", a, "-af", ",".join(chain), "-f", "f32le", b], check=True)
    return np.fromfile(b, np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lines"); ap.add_argument("vo"); ap.add_argument("words")
    ap.add_argument("--voice", default=None); ap.add_argument("--rate", default="215")
    a = ap.parse_args()
    lines = json.load(open(a.lines))
    base = os.path.dirname(os.path.abspath(a.lines))
    total = int((max(l["end"] for l in lines) + 1.5) * SR)
    out = np.zeros(total, np.float32)
    words, tmp = [], tempfile.mkdtemp()
    for i, l in enumerate(lines):
        if l.get("audio"):
            p = l["audio"] if os.path.isabs(l["audio"]) else os.path.join(base, l["audio"])
        else:
            p = os.path.join(tmp, f"{i}.aiff")
            cmd = ["say", "-r", str(a.rate), "-o", p, l["text"]]
            if a.voice:
                cmd[1:1] = ["-v", a.voice]
            subprocess.run(cmd, check=True)
        y = trim(load(p))
        target = l["end"] - l["start"]
        factor = target / (len(y) / SR)
        if factor < 0.62:
            print(f"!! line {i} needs x{factor:.2f}: shorten '{l['text'][:40]}…'")
        factor = min(1.35, max(0.62, factor))
        if abs(factor - 1) > 0.02:
            y = stretch(y, factor, tmp)
        s = int(l["start"] * SR)
        seg = y[: max(0, min(len(y), total - s))]
        out[s:s + len(seg)] += seg
        toks = re.findall(r"\S+", l["text"])
        wts = np.array([len(re.sub(r"\W", "", w)) + 1.2 for w in toks], float)
        cum = np.concatenate([[0], np.cumsum(wts)]) / wts.sum() * (len(seg) / SR)
        words += [{"w": w, "t": round(l["start"] + x0, 3), "end": round(l["start"] + x1, 3)} for w, x0, x1 in zip(toks, cum[:-1], cum[1:])]
    out /= max(1e-6, np.abs(out).max()) / 0.9
    with wave.open(a.vo, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())
    json.dump(words, open(a.words, "w"), indent=0)
    print(f"{len(lines)} lines, {len(words)} words -> {a.vo}, {a.words}")


if __name__ == "__main__":
    main()
