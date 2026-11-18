"""Build every asset for the demo short (egg-head toon art, characters with 4 expressions, music bed).

  python build_demo_assets.py <project_dir>

Then in <project_dir>: synth_sfx.py sfx ; say -r 215 -o audio/vo.aiff -f script.txt ;
align_words.py audio/vo.aiff script.txt words.json ; copy ../example_timeline.json there ; assemble.py.
"""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

out = sys.argv[1]
os.makedirs(f"{out}/shots", exist_ok=True); os.makedirs(f"{out}/chars", exist_ok=True)
W, H = 1240, 2200
OL = (17, 17, 17)


def grad(c1, c2):
    a = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(c1)[None, None] * (1 - a) + np.array(c2)[None, None] * a).repeat(W, 1)
    return Image.fromarray(arr.astype(np.uint8))


def sea(img, y0, c, c2, storm=False):
    d = ImageDraw.Draw(img)
    d.rectangle([0, y0, W, H], fill=c)
    rnd = random.Random(3)
    for i in range(40):
        x = rnd.randint(-100, W); y = rnd.randint(y0 + 20, H)
        w = rnd.randint(80, 220) * (2 if storm else 1)
        d.arc([x, y, x + w, y + w // 3], 200, 340, fill=c2, width=10 if storm else 6)


def ship(img, cx, base, windows="round", scale=1.0, crack=False):
    d = ImageDraw.Draw(img)
    s = scale
    hull = [(cx - 380 * s, base - 260 * s), (cx + 380 * s, base - 260 * s), (cx + 300 * s, base), (cx - 300 * s, base)]
    d.polygon(hull, fill=(178, 44, 44), outline=OL, width=int(12 * s))
    d.rectangle([cx - 380 * s, base - 300 * s, cx + 380 * s, base - 260 * s], fill=(240, 236, 228), outline=OL, width=int(10 * s))
    d.rectangle([cx - 200 * s, base - 520 * s, cx + 160 * s, base - 300 * s], fill=(240, 236, 228), outline=OL, width=int(10 * s))
    d.rectangle([cx - 40 * s, base - 700 * s, cx + 50 * s, base - 520 * s], fill=(40, 40, 40), outline=OL, width=int(10 * s))
    for i in range(5):
        x = cx - 290 * s + i * 140 * s
        y = base - 200 * s
        r = 42 * s
        if windows == "round":
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 214, 120), outline=OL, width=int(9 * s))
        else:
            d.rectangle([x - r * 1.2, y - r, x + r * 1.2, y + r], fill=(255, 214, 120), outline=OL, width=int(9 * s))
            if crack:
                for sx, sy in [(-1.2, 1), (1.2, 1)]:
                    px, py = x + sx * r, y + sy * r
                    pts = [(px, py)]
                    for k in range(4):
                        px += sx * 18 * s + random.uniform(-8, 8); py += 26 * s
                        pts.append((px, py))
                    d.line(pts, fill=OL, width=int(7 * s))
    for i in range(3):
        x = cx - 160 * s + i * 120 * s
        d.ellipse([x - 30 * s, base - 450 * s, x + 30 * s, base - 390 * s], fill=(255, 214, 120), outline=OL, width=int(7 * s))


def scene_harbor(path, windows):
    img = grad((120, 190, 240), (250, 215, 170))
    d = ImageDraw.Draw(img)
    d.ellipse([850, 250, 1100, 500], fill=(255, 240, 180))
    for x, y in [(200, 350), (700, 200)]:
        for k in range(4):
            d.ellipse([x + k * 70, y - (k % 2) * 30, x + k * 70 + 140, y + 90 - (k % 2) * 30], fill=(255, 255, 255))
    sea(img, 1450, (60, 130, 190), (230, 240, 250))
    ship(img, W // 2, 1520, windows, 1.1)
    img.save(path)


def scene_two_ships(path, storm=False, crack=False):
    img = grad((40, 50, 80), (90, 100, 130)) if storm else grad((130, 200, 245), (250, 220, 180))
    if storm:
        d = ImageDraw.Draw(img)
        for i in range(80):
            x = random.randint(0, W); y = random.randint(0, H)
            d.line([x, y, x - 30, y + 90], fill=(170, 180, 210), width=3)
        d.line([(700, 0), (640, 300), (720, 320), (620, 650)], fill=(255, 250, 200), width=14)
    sea(img, 1350, (35, 60, 95) if storm else (60, 130, 190), (140, 160, 200) if storm else (230, 240, 250), storm)
    ship(img, 330, 1250, "round", 0.62)
    ship(img, 910, 1450, "square", 0.72, crack)
    img.save(path)


def scene_blueprint(path):
    img = Image.new("RGB", (W, H), (22, 64, 160))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 60):
        d.line([x, 0, x, H], fill=(60, 105, 200), width=2)
    for y in range(0, H, 60):
        d.line([0, y, W, y], fill=(60, 105, 200), width=2)
    # square opening with stress lines bunching at corners
    cx, cy = W // 2, 700
    d.rectangle([cx - 200, cy - 150, cx + 200, cy + 150], outline=(255, 255, 255), width=10)
    for k in range(1, 9):
        o = k * 26
        for sx in (-1, 1):
            for sy in (-1, 1):
                x0, y0 = cx + sx * 200, cy + sy * 150
                d.arc([x0 - o, y0 - o, x0 + o, y0 + o], 0, 360, fill=(255, 120, 60), width=4)
    # round opening with even lines
    cy2 = 1450
    d.ellipse([cx - 180, cy2 - 180, cx + 180, cy2 + 180], outline=(255, 255, 255), width=10)
    for k in range(1, 6):
        o = 180 + k * 40
        d.ellipse([cx - o, cy2 - o, cx + o, cy2 + o], outline=(120, 220, 255), width=3)
    img.save(path)


def egghead(path, hat, body, face="neutral"):
    im = Image.new("RGBA", (520, 980), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # legs + arms
    d.line([(220, 760), (200, 960)], fill=OL, width=16); d.line([(300, 760), (320, 960)], fill=OL, width=16)
    d.line([(170, 560), (90, 720)], fill=OL, width=14); d.line([(350, 560), (430, 720)], fill=OL, width=14)
    d.ellipse([70, 700, 110, 740], fill=(242, 239, 234), outline=OL, width=6)
    d.ellipse([410, 700, 450, 740], fill=(242, 239, 234), outline=OL, width=6)
    d.rounded_rectangle([160, 500, 360, 790], 70, fill=body, outline=OL, width=12)
    d.ellipse([90, 120, 430, 520], fill=(242, 239, 234), outline=OL, width=14)
    # face decal
    if face == "neutral":
        d.ellipse([200, 290, 228, 322], fill=OL); d.ellipse([292, 290, 320, 322], fill=OL)
        d.line([(232, 410), (288, 410)], fill=OL, width=8)
    elif face == "smug":
        d.line([(195, 305), (232, 305)], fill=OL, width=9); d.line([(288, 305), (325, 305)], fill=OL, width=9)
        d.arc([220, 370, 300, 430], 20, 160, fill=OL, width=8)
    elif face == "shock":
        d.ellipse([190, 270, 240, 330], fill=(255, 255, 255), outline=OL, width=7); d.ellipse([280, 270, 330, 330], fill=(255, 255, 255), outline=OL, width=7)
        d.ellipse([208, 292, 222, 308], fill=OL); d.ellipse([298, 292, 312, 308], fill=OL)
        d.ellipse([235, 380, 285, 450], fill=OL)
    elif face == "grimace":
        d.line([(195, 285), (235, 300)], fill=OL, width=9); d.line([(325, 285), (285, 300)], fill=OL, width=9)
        d.rectangle([205, 380, 315, 440], fill=(255, 255, 255), outline=OL, width=6)
        for x in range(232, 315, 27):
            d.line([(x, 380), (x, 440)], fill=OL, width=4)
        d.line([(205, 410), (315, 410)], fill=OL, width=4)
    if hat == "hardhat":
        d.chord([110, 90, 410, 330], 180, 360, fill=(242, 140, 40), outline=OL, width=12)
        d.rectangle([90, 200, 430, 225], fill=(242, 140, 40), outline=OL, width=10)
    elif hat == "tophat":
        d.rectangle([180, 0, 340, 170], fill=(30, 30, 35), outline=OL, width=10)
        d.rectangle([180, 120, 340, 150], fill=(170, 30, 30))
        d.rectangle([120, 160, 400, 190], fill=(30, 30, 35), outline=OL, width=10)
    im.save(path)


random.seed(5)
scene_harbor(f"{out}/shots/harbor_round.png", "round")
scene_two_ships(f"{out}/shots/two_ships.png")
scene_two_ships(f"{out}/shots/storm.png", storm=True)
scene_two_ships(f"{out}/shots/storm_crack.png", storm=True, crack=True)
scene_blueprint(f"{out}/shots/blueprint.png")
for f in ("neutral", "smug", "shock", "grimace"):
    egghead(f"{out}/chars/hero_{f}.png", "hardhat", (31, 138, 138), f)
    egghead(f"{out}/chars/rival_{f}.png", "tophat", (120, 60, 140), f)
print("art done")

# ---- music bed: simple pizzicato arpeggio (placeholder; use licensed music for real videos)
import wave
SR = 48000; beat = 60 / 100; dur = 32
os.makedirs(f"{out}/audio", exist_ok=True)
t = np.arange(int(SR * dur)) / SR; y = np.zeros_like(t)
notes = [0, 4, 7, 12, 7, 4, 2, 5, 9, 12, 9, 5]
for i in range(int(dur / (beat / 2))):
    st = i * beat / 2; f = 261.63 * 2 ** (notes[i % len(notes)] / 12) * (0.5 if i % 8 == 0 else 1)
    s = int(st * SR); L = int(0.35 * SR); tt = np.arange(L) / SR
    if s + L > len(y): break
    y[s:s + L] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 14) * 0.5 + np.sin(4 * np.pi * f * tt) * np.exp(-tt * 20) * 0.15
    if i % 4 == 0:
        Lb = int(0.5 * SR); tb = np.arange(Lb) / SR
        if s + Lb < len(y): y[s:s + Lb] += np.sin(2 * np.pi * 65 * tb) * np.exp(-tb * 6) * 0.5
y /= np.abs(y).max() * 1.1
with wave.open(f"{out}/audio/bed.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes())
print("music bed done")
