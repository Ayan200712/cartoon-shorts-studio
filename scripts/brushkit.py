"""Brush-stroke drawing kit: the look that read as "an actual drawing" instead of geometric shapes.

  uv run --no-project --python 3.12 --with numpy --with pillow python scripts/brushkit.py out.png

Primitives (all draw on a supersampled RGBA canvas, SS = 2):
  bez(points)                      smooth Catmull-Rom path through points
  stroke(d, path, w0, w1, ...)     brush stroke whose width swells from the ends (w0) to the middle (w1) with a wobble
  ring(d, cx, cy, rx, ry, wmin, wmax, heavy_angle)   contour whose weight changes around the shape (calligraphic:
                                   heavy on the lower right, thin on the upper left), slightly uneven radius
  shaded_ellipse(img, ...)         painted soft gradient inside an ellipse (face shading)
  poly(d, pts, fill)               filled polygon
  kyle(mouth, eyes)                a complete example character built from them: wide head with painted shading, swept
                                   fringe with strands and a glossy band, hooked tuft, soft grey half-lidded eyes,
                                   tall capsule body with collar, name tag and badge, tapered arms
Copy kyle() as a template for your own characters. Export one PNG per expression (neutral, talk, talk2, blink,
shock) and animate them as layers in assemble.py. See references/drawn-character-style.md.
"""
import sys
import math, random, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SS = 2
W, H = 1080, 1920
INK = (30, 22, 26, 255)
rnd = random.Random(3)


def bez(pts, n=120):
    """Catmull-Rom through points -> list of (x, y, t)."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    segs = len(P) - 3
    for s in range(segs):
        p0, p1, p2, p3 = P[s:s + 4]
        for i in range(n // segs):
            t = i / (n // segs)
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t * t + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t ** 3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t * t + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t ** 3)
            out.append((x, y))
    out.append(pts[-1])
    return out


def stroke(d, path, w0, w1=None, col=INK, taper=(0.35, 0.35), wob=0.12, seed=0):
    """Brush stroke: width swells from w0 (ends, scaled by taper) to w1 (middle) with slight wobble."""
    w1 = w1 or w0
    r = random.Random(seed)
    ph = r.uniform(0, 6.28)
    n = len(path)
    dense = []
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        steps = max(1, int(math.hypot(x1 - x0, y1 - y0) / 1.5))
        for i in range(steps):
            dense.append((x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps))
    m = len(dense)
    for i, (x, y) in enumerate(dense):
        t = i / max(1, m - 1)
        env = min(1.0, taper[0] + (1 - taper[0]) * (t / 0.25)) if t < 0.25 else min(1.0, taper[1] + (1 - taper[1]) * ((1 - t) / 0.25)) if t > 0.75 else 1.0
        w = (w0 + (w1 - w0) * math.sin(math.pi * t)) * env * (1 + wob * math.sin(t * 9 + ph))
        rr = w / 2 * SS
        d.ellipse([x * SS - rr, y * SS - rr, x * SS + rr, y * SS + rr], fill=col)


def ring(d, cx, cy, rx, ry, w_min, w_max, heavy_angle=40, col=INK, wob=0.012, seed=1, a0=0, a1=360):
    """Closed (or partial) contour with calligraphic weight: heaviest toward heavy_angle (deg, 0=right, 90=down)."""
    r = random.Random(seed); ph = r.uniform(0, 6.28)
    steps = int((a1 - a0) * 6)
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        k = 0.5 + 0.5 * math.cos(a - math.radians(heavy_angle))
        w = w_min + (w_max - w_min) * k ** 1.3
        rad = 1 + wob * math.sin(3 * a + ph) + wob * 0.6 * math.sin(5 * a + ph * 2)
        x, y = cx + rx * rad * math.cos(a), cy + ry * rad * math.sin(a)
        rr = w / 2 * SS
        d.ellipse([x * SS - rr, y * SS - rr, x * SS + rr, y * SS + rr], fill=col)


def poly(d, pts, fill):
    d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)


def shaded_ellipse(img, cx, cy, rx, ry, base, shade, light=(0.25, -0.3), power=2.0):
    """Soft painted gradient inside an ellipse."""
    yy, xx = np.mgrid[0:H * SS, 0:W * SS].astype(np.float32)
    ex = (xx / SS - cx) / rx; ey = (yy / SS - cy) / ry
    inside = ex * ex + ey * ey <= 1.0
    dist = np.sqrt((ex - light[0]) ** 2 + (ey - light[1]) ** 2) / 1.45
    k = np.clip(dist, 0, 1) ** power
    a = np.array(img)
    for c in range(3):
        a[..., c] = np.where(inside, base[c] * (1 - k) + shade[c] * k, a[..., c])
    a[..., 3] = np.where(inside, 255, a[..., 3])
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def kyle(mouth="neutral", ticket_img=None, hold=True, eyes="half"):
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy, rx, ry = 560, 650, 372, 322
    RED, RED_D, RED_L = (216, 38, 34, 255), (150, 20, 24, 255), (240, 80, 66, 255)
    # ---------------- far arm (screen right) behind body
    arm_r = bez([(735, 985), (835, 1090), (862, 1280), (850, 1462)])
    stroke(d, arm_r, 30, 40, taper=(0.8, 0.9), seed=4)
    # ---------------- body: tall capsule, slight lean
    body = [(402, 1010), (398, 1700), (742, 1700), (748, 1010)]
    top = [(402 + (748 - 402) * i / 30, 1010 - 95 * math.sin(math.pi * i / 30)) for i in range(31)]
    poly(d, top + [(748, 1700), (398, 1700)], RED)
    # painted shading: darker left band + lighter centre highlight
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    ds.polygon([(398 * SS, 960 * SS), (470 * SS, 930 * SS), (455 * SS, 1700 * SS), (398 * SS, 1700 * SS)], fill=RED_D)
    ds.ellipse([520 * SS, 1000 * SS, 690 * SS, 1500 * SS], fill=RED_L)
    sh = sh.filter(ImageFilter.GaussianBlur(26 * SS))
    mask = Image.new("L", img.size, 0); ImageDraw.Draw(mask).polygon([(x * SS, y * SS) for x, y in top + [(748, 1700), (398, 1700)]], fill=255)
    img.paste(Image.alpha_composite(img, sh), (0, 0), mask); d = ImageDraw.Draw(img)
    stroke(d, bez([(402, 1700), (396, 1300), (404, 1010), (440, 950)]), 16, 22, taper=(1, 0.5), seed=5)
    stroke(d, bez([(748, 1700), (756, 1320), (746, 1010), (712, 950)]), 24, 34, taper=(1, 0.5), seed=6)
    # collar + placket
    poly(d, [(505, 925), (575, 1000), (470, 1010)], RED); poly(d, [(645, 925), (575, 1000), (690, 1005)], RED)
    stroke(d, bez([(500, 930), (540, 975), (575, 1002)]), 9, 13, seed=7); stroke(d, bez([(650, 930), (612, 975), (575, 1002)]), 9, 13, seed=8)
    stroke(d, [(575, 1002), (577, 1085)], 7, 9, seed=9)
    for yb in (1030, 1065):
        d.ellipse([(568) * SS, (yb - 6) * SS, 582 * SS, (yb + 8) * SS], fill=(120, 16, 20, 255))
    # name tag + badge
    tag = Image.new("RGBA", (230 * SS, 84 * SS), (0, 0, 0, 0)); dt = ImageDraw.Draw(tag)
    dt.rounded_rectangle([4 * SS, 4 * SS, 226 * SS, 80 * SS], 16 * SS, fill=(250, 250, 250, 255), outline=INK, width=8 * SS)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Black.ttf", 50 * SS)
    dt.text((115 * SS, 42 * SS), "KYLE", font=f, fill=INK, anchor="mm")
    tag = tag.rotate(-3, expand=True, resample=Image.BICUBIC); img.alpha_composite(tag, (560 * SS, 1100 * SS))
    d = ImageDraw.Draw(img)
    d.ellipse([452 * SS, 1100 * SS, 536 * SS, 1184 * SS], fill=(252, 226, 90, 255), outline=INK, width=8 * SS)
    d.ellipse([468 * SS, 1128 * SS, 512 * SS, 1158 * SS], fill=(40, 120, 200, 255)); poly(d, [(508, 1143), (526, 1128), (526, 1158)], (40, 120, 200, 255))
    # ---------------- head: painted gradient + calligraphic contour
    img = shaded_ellipse(img, cx, cy, rx, ry, (252, 252, 250), (176, 178, 194), light=(0.2, -0.25), power=2.3)
    d = ImageDraw.Draw(img)
    # ---------------- hair: swept fringe with parting, drawn as a shape
    def on_head(deg, k=1.012):
        a = math.radians(deg); return (cx + rx * k * math.cos(a), cy + ry * k * math.sin(a))
    crown = [on_head(a) for a in range(180, 352, 4)]                      # left temple -> over the top -> right temple
    fringe_r = bez([on_head(350), (cx + 255, cy - 110), (cx + 170, cy - 150), (cx + 105, cy - 178)], 40)   # right piece up to the parting
    fringe_l = bez([(cx + 105, cy - 178), (cx - 30, cy - 150), (cx - 200, cy - 95), on_head(180)], 60)      # long sweep down to the left temple
    hair_poly = crown + fringe_r + fringe_l
    poly(d, hair_poly, (132, 76, 36, 255))
    hm = Image.new("L", img.size, 0); ImageDraw.Draw(hm).polygon([(x * SS, y * SS) for x, y in hair_poly], fill=255)
    strands = Image.new("RGBA", img.size, (0, 0, 0, 0)); dst = ImageDraw.Draw(strands)
    px, py = cx + 70, cy - 300                                            # parting point: strands fan out from here
    for i in range(22):                                                   # left sweep strands
        t = i / 21
        end = fringe_l[int((1 - t) * (len(fringe_l) - 1))]
        mid = ((px + end[0]) / 2 - 70 * (1 - t), (py + end[1]) / 2 - 50)
        col = rnd.choice([(186, 124, 66, 255), (166, 104, 52, 255), (104, 58, 26, 255), (200, 140, 80, 255)])
        stroke(dst, bez([(px - 6, py + 4), mid, end], 40), 5, rnd.choice([10, 14, 18]), col=col, taper=(0.2, 0.2), seed=20 + i)
    for i in range(9):                                                    # short right-side strands
        t = i / 8
        end = fringe_r[int((1 - t) * (len(fringe_r) - 1))]
        col = rnd.choice([(186, 124, 66, 255), (104, 58, 26, 255), (166, 104, 52, 255)])
        stroke(dst, bez([(px + 6, py + 2), ((px + end[0]) / 2 + 20, (py + end[1]) / 2 - 30), end], 30), 5, rnd.choice([9, 13]), col=col, taper=(0.2, 0.2), seed=60 + i)
    strands = strands.filter(ImageFilter.GaussianBlur(0.8 * SS))
    img.paste(Image.alpha_composite(img, strands), (0, 0), hm); d = ImageDraw.Draw(img)
    # glossy highlight band on the hair
    gl = Image.new("RGBA", img.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(gl)
    stroke(dg, bez([(cx - 270, cy - 170), (cx - 130, cy - 250), (cx + 40, cy - 285)], 40), 10, 34, col=(255, 226, 180, 120), taper=(0.1, 0.1), seed=90)
    gl = gl.filter(ImageFilter.GaussianBlur(7 * SS)); img.paste(Image.alpha_composite(img, gl), (0, 0), hm); d = ImageDraw.Draw(img)
    # fringe edge lines (the hair overlaps the face: line breaks give the drawn look)
    stroke(d, fringe_l, 9, 17, taper=(0.3, 0.6), seed=11)
    stroke(d, fringe_r, 8, 14, taper=(0.5, 0.3), seed=12)
    stroke(d, bez([(cx + 105, cy - 178), (cx + 92, cy - 230), (cx + 84, cy - 275)], 20), 5, 10, taper=(0.7, 0.1), seed=13)   # parting line
    # head contour: heavy lower-right, light upper-left, with a small gap where the fringe crosses
    ring(d, cx, cy, rx, ry, 14, 34, heavy_angle=55, seed=2, a0=-10, a1=180)
    ring(d, cx, cy, rx * 1.012, ry * 1.012, 16, 28, heavy_angle=300, seed=3, a0=180, a1=350)
    # ---------------- curl tuft: tapered hook
    tuft = bez([(cx + 40, cy - ry + 18), (cx + 18, cy - ry - 70), (cx + 60, cy - ry - 132), (cx + 130, cy - ry - 128), (cx + 152, cy - ry - 86)], 60)
    stroke(d, tuft, 62, 44, taper=(1.0, 0.35), wob=0.04, seed=14)
    stroke(d, tuft, 40, 24, col=(140, 82, 40, 255), taper=(1.0, 0.25), wob=0.04, seed=14)
    stroke(d, bez([(cx + 34, cy - ry - 20), (cx + 30, cy - ry - 80), (cx + 70, cy - ry - 120)], 20), 4, 9, col=(200, 140, 80, 255), taper=(0.2, 0.2), seed=15)
    # ---------------- face: soft grey half-lidded eyes, short mouth
    G = (112, 110, 120, 255)
    for ex in (cx - 118, cx + 112):
        ey = cy + 6
        if eyes == "half":
            d.ellipse([(ex - 42) * SS, (ey - 30) * SS, (ex + 42) * SS, (ey + 44) * SS], fill=G)
            poly(d, [(ex - 60, ey - 50), (ex + 60, ey - 50), (ex + 60, ey + 2), (ex - 60, ey - 4)], (250, 250, 249, 255))
            stroke(d, bez([(ex - 62, ey - 6), (ex, ey - 12), (ex + 62, ey + 2)], 20), 9, 15, col=(88, 86, 96, 255), taper=(0.4, 0.4), seed=30 + ex)
        elif eyes == "closed":
            stroke(d, bez([(ex - 60, ey + 6), (ex, ey + 20), (ex + 60, ey + 8)], 20), 10, 17, col=(88, 86, 96, 255), taper=(0.4, 0.4), seed=30 + ex)
        else:  # wide (shock)
            d.ellipse([(ex - 62) * SS, (ey - 62) * SS, (ex + 62) * SS, (ey + 62) * SS], fill=(255, 255, 255, 255))
            ring(d, ex, ey, 62, 62, 9, 16, heavy_angle=60, col=(120, 118, 128, 255), seed=int(ex))
            d.ellipse([(ex - 16) * SS, (ey - 16) * SS, (ex + 16) * SS, (ey + 16) * SS], fill=(70, 68, 78, 255))
    if eyes == "wide":
        sx_, sy_ = cx + 250, cy - 120
        poly(d, [(sx_, sy_ - 60), (sx_ + 34, sy_ + 6), (sx_, sy_ + 36), (sx_ - 34, sy_ + 6)], (120, 190, 244, 255))
        ring(d, sx_, sy_ + 2, 30, 36, 6, 10, col=(40, 80, 150, 255), seed=77)
    if mouth == "neutral":
        stroke(d, bez([(cx - 56, cy + 152), (cx, cy + 150), (cx + 54, cy + 148)], 20), 13, 21, col=(120, 116, 124, 255), taper=(0.5, 0.5), seed=40)
    elif mouth == "talk2":
        d.ellipse([(cx - 50) * SS, (cy + 128) * SS, (cx + 50) * SS, (cy + 178) * SS], fill=(98, 34, 36, 255))
        ring(d, cx, cy + 153, 50, 25, 8, 14, heavy_angle=80, seed=42)
    elif mouth == "o":
        d.ellipse([(cx - 30) * SS, (cy + 120) * SS, (cx + 30) * SS, (cy + 190) * SS], fill=(98, 34, 36, 255))
        ring(d, cx, cy + 155, 30, 35, 8, 13, heavy_angle=80, seed=43)
    else:
        d.ellipse([(cx - 62) * SS, (cy + 96) * SS, (cx + 62) * SS, (cy + 212) * SS], fill=(98, 34, 36, 255))
        d.chord([(cx - 44) * SS, (cy + 150) * SS, (cx + 44) * SS, (cy + 214) * SS], 0, 180, fill=(232, 110, 110, 255))
        ring(d, cx, cy + 154, 62, 58, 9, 16, heavy_angle=80, seed=41)
    # soft shadow the head casts on the shirt
    return img



if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "drawn_example.png"
    im = kyle("neutral")
    bg = Image.new("RGBA", im.size, (108, 150, 88, 255)); bg.alpha_composite(im)
    bg.convert("RGB").resize((W, H), Image.LANCZOS).save(out); print("wrote", out)
