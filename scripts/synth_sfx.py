#!/usr/bin/env python3
"""Generate a free, royalty-free starter SFX kit procedurally (no downloads).

  uv run --no-project --python 3.12 --with numpy python scripts/synth_sfx.py <out_dir>

Writes 48 kHz mono WAVs: whoosh, whoosh_short, swoosh_up, pop, bubble_pop, boom,
thud, riser, ding, cash, tick, click, glitch, record_scratch, slide_whistle_down,
heartbeat, impact_hit, camera_shutter, typewriter, sparkle.
These are serviceable placeholders; swap in a real library (Freesound CC0,
Pixabay, Epidemic, Artlist) when you want polish.
"""
import os, sys, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(1)


def t(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.005, r=0.2, shape=2.0):
    x = np.ones(n)
    na, nr = int(SR * a), int(SR * r)
    if na:
        x[:na] = np.linspace(0, 1, na)
    if nr and nr < n:
        x[-nr:] *= np.linspace(1, 0, nr) ** shape
    return x


def bandnoise(n, lo, hi):
    X = np.fft.rfft(rng.normal(0, 1, n))
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, n)
    return y / (np.abs(y).max() + 1e-9)


def sweep_noise(d, f0, f1, q=0.25):
    """Noise through a moving band-pass: the core of every whoosh."""
    n = int(SR * d)
    noise = rng.normal(0, 1, n)
    out = np.zeros(n)
    hop = 512
    win = np.hanning(hop * 2)
    for i in range(0, n - hop * 2, hop):
        p = i / n
        fc = f0 * (f1 / f0) ** p
        seg = noise[i:i + hop * 2] * win
        X = np.fft.rfft(seg)
        fr = np.fft.rfftfreq(len(seg), 1 / SR)
        X *= np.exp(-((fr - fc) / (fc * q + 50)) ** 2)
        out[i:i + hop * 2] += np.fft.irfft(X, len(seg))
    return out / (np.abs(out).max() + 1e-9)


def tone(freq, d, kind="sine"):
    x = t(d)
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(freq, x.shape)) / SR if np.ndim(freq) else 2 * np.pi * freq * x
    if kind == "sine":
        return np.sin(ph)
    if kind == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if kind == "square":
        return np.sign(np.sin(ph))


def norm(y, peak=0.89):
    return y / (np.abs(y).max() + 1e-9) * peak


def save(path, y):
    y = np.clip(norm(y), -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((y * 32767).astype(np.int16).tobytes())


def kit():
    k = {}
    d = 0.6; n = int(SR * d)
    bell = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    k["whoosh"] = sweep_noise(d, 300, 3500) * bell
    d = 0.28; n = int(SR * d)
    k["whoosh_short"] = sweep_noise(d, 600, 5000) * np.sin(np.linspace(0, np.pi, n)) ** 1.2
    d = 0.5; n = int(SR * d)
    k["swoosh_up"] = sweep_noise(d, 400, 8000, 0.15) * np.linspace(0.2, 1, n) * env(n, 0.01, 0.08)
    x = t(0.09)
    k["pop"] = np.sin(2 * np.pi * (900 - 6000 * x) * x) * np.exp(-x * 60)
    x = t(0.12)
    k["bubble_pop"] = np.sin(2 * np.pi * np.cumsum(400 + 2500 * x / 0.12) / SR) * np.exp(-x * 35)
    x = t(1.6)
    sub = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-x * 3) + 30) / SR) * np.exp(-x * 2.2)
    k["boom"] = sub + bandnoise(len(x), 40, 900) * np.exp(-x * 7) * 0.7
    x = t(0.35)
    k["thud"] = np.sin(2 * np.pi * np.cumsum(140 * np.exp(-x * 12) + 45) / SR) * np.exp(-x * 14) + bandnoise(len(x), 60, 600) * np.exp(-x * 40) * 0.4
    x = t(2.0)
    k["riser"] = (sweep_noise(2.0, 200, 9000, 0.4) * 0.6 + tone(200 * (1 + 3 * x / 2.0), 2.0, "tri") * 0.25) * (x / 2.0) ** 2
    x = t(1.2)
    k["ding"] = sum(np.sin(2 * np.pi * f * x) * a * np.exp(-x * dcy) for f, a, dcy in [(1568, 1, 3), (3136, .4, 5), (4704, .2, 7), (2093, .3, 4)])
    x = t(0.9)
    ka = sum(np.sin(2 * np.pi * f * x) * np.exp(-x * 5) for f in (2637, 3136, 3951))
    k["cash"] = ka + np.concatenate([bandnoise(int(SR * .08), 2000, 9000) * np.exp(-t(.08) * 40), np.zeros(len(x) - int(SR * .08))]) * 0.8
    x = t(0.03)
    k["tick"] = bandnoise(len(x), 2500, 9000) * np.exp(-x * 300)
    x = t(0.02)
    k["click"] = bandnoise(len(x), 1000, 6000) * np.exp(-x * 400)
    g = []
    for _ in range(9):
        seg = int(SR * rng.uniform(0.01, 0.04))
        g.append(tone(rng.uniform(200, 2000), seg / SR, "square") * 0.6 + bandnoise(seg, 500, 8000) * 0.4)
    k["glitch"] = np.concatenate(g)
    x = t(0.45)
    k["record_scratch"] = bandnoise(len(x), 300, 4000) * (0.5 + 0.5 * np.sin(2 * np.pi * (6 + 20 * x) * x)) * env(len(x), .005, .15)
    x = t(0.8)
    k["slide_whistle_down"] = tone(1400 * (1 - 0.7 * x / 0.8), 0.8, "sine") * env(len(x), .02, .2)
    beat = lambda: np.sin(2 * np.pi * 55 * t(0.12)) * np.exp(-t(0.12) * 30)
    hb = np.zeros(int(SR * 1.0)); b = beat()
    hb[:len(b)] += b; hb[int(SR * .22):int(SR * .22) + len(b)] += b * 0.7
    k["heartbeat"] = hb
    x = t(0.7)
    k["impact_hit"] = k["thud"][:int(SR * .35)].tolist() + [0] * (len(x) - int(SR * .35))
    k["impact_hit"] = np.array(k["impact_hit"]) + bandnoise(len(x), 1500, 12000) * np.exp(-x * 25) * 0.5 + np.sin(2 * np.pi * 60 * x) * np.exp(-x * 6) * 0.6
    x = t(0.18)
    sh = bandnoise(len(x), 1500, 10000) * np.exp(-x * 60)
    sh[int(SR * .08):] += bandnoise(len(x) - int(SR * .08), 1500, 10000) * np.exp(-t(.1) * 70) * 0.8
    k["camera_shutter"] = sh
    tw = np.zeros(int(SR * 1.2))
    for i in range(10):
        s = int(SR * (i * 0.11 + rng.uniform(0, .02)))
        c = bandnoise(int(SR * .03), 800, 7000) * np.exp(-t(.03) * 150)
        tw[s:s + len(c)] += c
    k["typewriter"] = tw
    x = t(1.0)
    sp = np.zeros(len(x))
    for i in range(14):
        s = int(SR * i * 0.06)
        f = rng.uniform(2500, 6000)
        c = np.sin(2 * np.pi * f * t(0.15)) * np.exp(-t(0.15) * 30)
        sp[s:s + len(c)] += c[:len(sp) - s] * (1 - i / 16)
    k["sparkle"] = sp
    return k


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sfx"
    os.makedirs(out, exist_ok=True)
    for name, y in kit().items():
        save(os.path.join(out, name + ".wav"), np.asarray(y, float))
        print("wrote", os.path.join(out, name + ".wav"))
