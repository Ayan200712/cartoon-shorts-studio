"""Tiny procedural toon kit: supersampled PIL drawing of round-head stick characters, props and sets."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SS = 2  # supersampling
OL = (24, 20, 26)
F_BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
F_ROUND = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
F_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


class C:
    """Canvas drawn at SS x resolution; coordinates given in final pixels."""

    def __init__(self, w, h, bg=(0, 0, 0, 0), mode="RGBA"):
        self.w, self.h = w, h
        self.im = Image.new(mode, (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.im)

    def s(self, v):
        if isinstance(v, (list, tuple)):
            return [x * SS for x in v]
        return v * SS

    def rect(self, box, fill=None, ol=OL, w=6, r=0):
        if r:
            self.d.rounded_rectangle(self.s(box), r * SS, fill=fill, outline=ol if w else None, width=w * SS)
        else:
            self.d.rectangle(self.s(box), fill=fill, outline=ol if w else None, width=w * SS)

    def ell(self, box, fill=None, ol=OL, w=6):
        self.d.ellipse(self.s(box), fill=fill, outline=ol if w else None, width=w * SS)

    def poly(self, pts, fill=None, ol=OL, w=6):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)
        if w and ol:
            self.d.line([(x * SS, y * SS) for x, y in pts + [pts[0]]], fill=ol, width=w * SS, joint="curve")

    def line(self, pts, fill=OL, w=6):
        self.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=w * SS, joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = w / 2
            self.d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=fill)

    def arc(self, box, a0, a1, fill=OL, w=6):
        self.d.arc(self.s(box), a0, a1, fill=fill, width=w * SS)

    def chord(self, box, a0, a1, fill=None, ol=OL, w=6):
        self.d.chord(self.s(box), a0, a1, fill=fill, outline=ol, width=w * SS)

    def pie(self, box, a0, a1, fill=None, ol=OL, w=6):
        self.d.pieslice(self.s(box), a0, a1, fill=fill, outline=ol, width=w * SS)

    def text(self, xy, txt, size, fill=(255, 255, 255), font=F_BLACK, anchor="mm", stroke=0, sfill=OL, rot=0):
        f = ImageFont.truetype(font, int(size * SS))
        if rot:
            tw = int(f.getlength(txt)) + 40 * SS
            th = int(size * 1.6 * SS)
            t = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            ImageDraw.Draw(t).text((tw / 2, th / 2), txt, font=f, fill=fill, anchor="mm", stroke_width=stroke * SS, stroke_fill=sfill)
            t = t.rotate(rot, expand=True, resample=Image.BICUBIC)
            self.im.alpha_composite(t, (int(xy[0] * SS - t.width / 2), int(xy[1] * SS - t.height / 2))) if self.im.mode == "RGBA" else \
                self.im.paste(t, (int(xy[0] * SS - t.width / 2), int(xy[1] * SS - t.height / 2)), t)
            return
        self.d.text(self.s(xy), txt, font=f, fill=fill, anchor=anchor, stroke_width=stroke * SS, stroke_fill=sfill)

    def paste(self, img, xy, scale=1.0):
        """img is a final-resolution RGBA image; xy top-left in final px."""
        im = img.resize((int(img.width * scale * SS), int(img.height * scale * SS)), Image.LANCZOS)
        if self.im.mode == "RGBA":
            self.im.alpha_composite(im, (int(xy[0] * SS), int(xy[1] * SS)))
        else:
            self.im.paste(im, (int(xy[0] * SS), int(xy[1] * SS)), im)

    def vgrad(self, box, c1, c2):
        x0, y0, x1, y1 = [int(v * SS) for v in box]
        h = max(1, y1 - y0)
        for i in range(h):
            k = i / h
            col = tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))
            self.d.line([(x0, y0 + i), (x1, y0 + i)], fill=col)

    def out(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def shade(img, strength=0.18, light=(0.3, 0.2)):
    """Soft 3D-ish lighting pass: radial light + vignette, keeps toon look but adds depth."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx / W - light[0]) * 1.2) ** 2 + ((yy / H - light[1])) ** 2)
    m = 1 + strength * (0.6 - r)
    a = np.clip(a * m[..., None], 0, 255)
    out = Image.fromarray(a.astype(np.uint8))
    if img.mode == "RGBA":
        out.putalpha(img.split()[3])
    return out


def bloom(img, amt=0.35, rad=18):
    base = img.convert("RGB")
    a = np.asarray(base).astype(np.float32)
    bright = np.clip(a - 170, 0, 255) * 2
    b = Image.fromarray(bright.astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad))
    out = np.clip(a + np.asarray(b).astype(np.float32) * amt, 0, 255)
    return Image.fromarray(out.astype(np.uint8))


# ---------------------------------------------------------------- characters
SKIN = (246, 244, 240)
HAIR = (128, 74, 36)


def face(c, cx, cy, R, kind):
    """Decal face on a round head centred (cx, cy) radius R."""
    e = R * 0.13
    lx, rx, ey = cx - R * 0.33, cx + R * 0.33, cy - R * 0.02
    w = max(4, int(R * 0.05))
    if kind in ("neutral", "talk", "talk2", "frown", "frown_talk"):
        # half-lidded deadpan eyes
        for x in (lx, rx):
            c.ell([x - e, ey - e * 0.6, x + e, ey + e * 0.8], fill=OL, w=0)
            c.rect([x - e * 1.3, ey - e * 1.4, x + e * 1.3, ey - e * 0.05], fill=SKIN, w=0)
            c.line([(x - e * 1.2, ey - e * 0.05), (x + e * 1.2, ey - e * 0.05)], w=w)
    if kind == "neutral":
        c.line([(cx - R * 0.14, cy + R * 0.42), (cx + R * 0.14, cy + R * 0.42)], w=w)
    elif kind == "talk":
        c.ell([cx - R * 0.17, cy + R * 0.3, cx + R * 0.17, cy + R * 0.58], fill=(70, 30, 30), w=w)
        c.chord([cx - R * 0.12, cy + R * 0.42, cx + R * 0.12, cy + R * 0.6], 0, 180, fill=(220, 100, 100), ol=None, w=0)
    elif kind == "talk2":
        c.rect([cx - R * 0.2, cy + R * 0.34, cx + R * 0.2, cy + R * 0.5], fill=(70, 30, 30), w=w, r=int(R * 0.08))
    elif kind in ("frown", "frown_talk"):
        # moustache
        c.poly([(cx - R * 0.3, cy + R * 0.36), (cx, cy + R * 0.26), (cx + R * 0.3, cy + R * 0.36), (cx, cy + R * 0.42)], fill=(72, 44, 30), w=0)
        if kind == "frown":
            c.arc([cx - R * 0.14, cy + R * 0.46, cx + R * 0.14, cy + R * 0.66], 200, 340, w=w)
        else:
            c.ell([cx - R * 0.12, cy + R * 0.44, cx + R * 0.12, cy + R * 0.64], fill=(70, 30, 30), w=w)
    elif kind == "shock":
        for x in (lx, rx):
            c.ell([x - e * 1.7, ey - e * 1.7, x + e * 1.7, ey + e * 1.7], fill=(255, 255, 255), w=w)
            c.ell([x - e * 0.5, ey - e * 0.5, x + e * 0.5, ey + e * 0.5], fill=OL, w=0)
        c.ell([cx - R * 0.11, cy + R * 0.34, cx + R * 0.11, cy + R * 0.6], fill=(70, 30, 30), w=w)
        # sweat drop
        sx, sy = cx + R * 0.72, cy - R * 0.45
        c.poly([(sx, sy - R * 0.2), (sx + R * 0.1, sy), (sx, sy + R * 0.08), (sx - R * 0.1, sy)], fill=(120, 190, 240), ol=OL, w=max(2, w // 2))
    elif kind == "smug":
        for x in (lx, rx):
            c.ell([x - e, ey - e * 0.4, x + e, ey + e * 0.8], fill=OL, w=0)
            c.rect([x - e * 1.3, ey - e * 1.4, x + e * 1.3, ey + e * 0.15], fill=SKIN, w=0)
            c.line([(x - e * 1.3, ey + e * 0.15), (x + e * 1.2, ey - e * 0.1)], w=w)
        c.arc([cx - R * 0.2, cy + R * 0.18, cx + R * 0.26, cy + R * 0.52], 20, 120, w=w)
    elif kind == "happy":
        for x in (lx, rx):
            c.arc([x - e * 1.3, ey - e * 0.8, x + e * 1.3, ey + e * 1.4], 200, 340, w=w)
        c.arc([cx - R * 0.22, cy + R * 0.12, cx + R * 0.22, cy + R * 0.5], 20, 160, w=w)
    elif kind == "grin":
        for x in (lx, rx):
            c.arc([x - e * 1.3, ey - e * 0.8, x + e * 1.3, ey + e * 1.4], 200, 340, w=w)
        c.rect([cx - R * 0.26, cy + R * 0.28, cx + R * 0.26, cy + R * 0.54], fill=(255, 255, 255), w=w, r=int(R * 0.06))
        for k in range(1, 4):
            x = cx - R * 0.26 + k * R * 0.13
            c.line([(x, cy + R * 0.28), (x, cy + R * 0.54)], w=max(2, w // 2))
        c.line([(cx - R * 0.26, cy + R * 0.41), (cx + R * 0.26, cy + R * 0.41)], w=max(2, w // 2))
    elif kind == "worried":
        for x, sgn in ((lx, 1), (rx, -1)):
            c.ell([x - e * 0.6, ey - e * 0.6, x + e * 0.6, ey + e * 0.6], fill=OL, w=0)
            c.line([(x - e * 1.3, ey - e * 2.2 + sgn * e * 0.6), (x + e * 1.3, ey - e * 2.2 - sgn * e * 0.6)], w=w)
        c.arc([cx - R * 0.2, cy + R * 0.4, cx + R * 0.2, cy + R * 0.66], 200, 340, w=w)
    elif kind == "sleep":
        for x in (lx, rx):
            c.arc([x - e * 1.3, ey - e * 1.4, x + e * 1.3, ey + e * 0.6], 20, 160, w=w)
        c.arc([cx - R * 0.2, cy + R * 0.14, cx + R * 0.2, cy + R * 0.46], 20, 160, w=w)
    elif kind == "glasses":
        for x in (lx, rx):
            c.rect([x - e * 1.8, ey - e * 1.4, x + e * 1.8, ey + e * 1.4], fill=(235, 240, 245), w=w, r=int(e * 0.5))
            c.ell([x - e * 0.45, ey - e * 0.45, x + e * 0.45, ey + e * 0.45], fill=OL, w=0)
        c.line([(lx + e * 1.8, ey), (rx - e * 1.8, ey)], w=w)
        c.arc([cx - R * 0.22, cy + R * 0.2, cx + R * 0.22, cy + R * 0.52], 20, 160, w=w)
    elif kind == "glasses_grin":
        for x in (lx, rx):
            c.rect([x - e * 1.8, ey - e * 1.4, x + e * 1.8, ey + e * 1.4], fill=(235, 240, 245), w=w, r=int(e * 0.5))
            c.ell([x - e * 0.45, ey - e * 0.45, x + e * 0.45, ey + e * 0.45], fill=OL, w=0)
        c.line([(lx + e * 1.8, ey), (rx - e * 1.8, ey)], w=w)
        c.rect([cx - R * 0.26, cy + R * 0.3, cx + R * 0.26, cy + R * 0.56], fill=(255, 255, 255), w=w, r=int(R * 0.06))
        for k in range(1, 4):
            x = cx - R * 0.26 + k * R * 0.13
            c.line([(x, cy + R * 0.3), (x, cy + R * 0.56)], w=max(2, w // 2))


def kyle_hair(c, cx, cy, R, back=False):
    if back:
        c.ell([cx - R, cy - R, cx + R, cy + R], fill=HAIR, w=7)
        c.arc([cx - R * 0.7, cy - R * 0.9, cx + R * 0.2, cy + R * 0.4], 200, 300, fill=(98, 55, 26), w=5)
    else:
        # hair cap = top of the head circle down to ~38% height, with a scalloped fringe
        cap = Image.new("L", c.im.size, 0)
        dm = ImageDraw.Draw(cap)
        dm.ellipse([(cx - R) * SS, (cy - R) * SS, (cx + R) * SS, (cy + R) * SS], fill=255)
        fringe_y = cy - R * 0.32
        dm.rectangle([0, fringe_y * SS, c.im.size[0], c.im.size[1]], fill=0)
        for k in range(5):
            x0 = cx - R * 0.95 + k * R * 0.38
            dm.ellipse([x0 * SS, (fringe_y - R * 0.16) * SS, (x0 + R * 0.4) * SS, (fringe_y + R * 0.16) * SS], fill=255)
        cap = cap.point(lambda v: 255 if v > 128 else 0)
        col = Image.new("RGBA", c.im.size, HAIR + (255,))
        c.im.paste(col, (0, 0), cap)
        edge = cap.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(5 * SS + 1))
        c.im.paste(Image.new("RGBA", c.im.size, OL + (255,)), (0, 0), edge)
        c.ell([cx - R, cy - R, cx + R, cy + R], fill=None, w=8)
    # the curl tuft
    c.line([(cx, cy - R * 0.98), (cx + R * 0.05, cy - R * 1.35), (cx + R * 0.25, cy - R * 1.55)], fill=OL, w=int(R * 0.12))
    c.line([(cx, cy - R * 0.98), (cx + R * 0.05, cy - R * 1.35), (cx + R * 0.25, cy - R * 1.55)], fill=HAIR, w=int(R * 0.07))


def bucket_hat(c, cx, cy, R):
    c.poly([(cx - R * 0.75, cy - R * 0.55), (cx + R * 0.75, cy - R * 0.55), (cx + R * 0.62, cy - R * 1.15), (cx - R * 0.62, cy - R * 1.15)],
           fill=(122, 128, 56), w=7)
    c.ell([cx - R * 1.15, cy - R * 0.72, cx + R * 1.15, cy - R * 0.38], fill=(108, 114, 48), w=7)
    for k, col in enumerate([(230, 80, 80), (80, 170, 220), (240, 200, 60), (230, 120, 200)]):
        x = cx - R * 0.5 + k * R * 0.33
        y = cy - R * 0.85 + (k % 2) * R * 0.12
        c.ell([x - R * 0.12, y - R * 0.05, x + R * 0.12, y + R * 0.07], fill=col, w=3)


def person(kind="kyle", face_kind="neutral", pose="idle", scale=1.0, back=False):
    """Full-body round-head character. Returns RGBA at ~ 520x1000 * scale. Anchor: bottom-centre."""
    W, H = 560, 1040
    c = C(W, H)
    cx = W // 2
    R = 175
    hy = 230
    body_col = {"kyle": (214, 40, 36), "kyle_suit": (150, 92, 44), "customer": (232, 178, 40), "agent": (40, 54, 92), "cop": (36, 50, 92),
                "lady": (40, 168, 160), "friend1": (120, 70, 160), "friend2": (240, 150, 170)}[kind]
    lw = 13
    # legs
    if pose == "sit":
        c.line([(cx - 40, 760), (cx - 120, 790), (cx - 120, 960)], w=lw)
        c.line([(cx + 40, 760), (cx - 40, 800), (cx - 40, 960)], w=lw)
    elif pose in ("walk_a", "walk_b"):
        s = 1 if pose == "walk_a" else -1
        c.line([(cx - 25, 760), (cx - 25 - s * 60, 980)], w=lw)
        c.line([(cx + 25, 760), (cx + 25 + s * 60, 980)], w=lw)
    else:
        c.line([(cx - 40, 760), (cx - 50, 990)], w=lw)
        c.line([(cx + 40, 760), (cx + 50, 990)], w=lw)
    # arms (behind torso for some poses)
    hand = lambda x, y: c.ell([x - 22, y - 22, x + 22, y + 22], fill=OL, w=0)
    arms = {
        "idle": [((cx - 95, 520), (cx - 150, 640), (cx - 150, 740)), ((cx + 95, 520), (cx + 150, 640), (cx + 150, 740))],
        "hold": [((cx - 95, 520), (cx - 140, 640), (cx - 60, 640)), ((cx + 95, 520), (cx + 160, 620), (cx + 120, 560))],
        "shrug": [((cx - 95, 520), (cx - 190, 540), (cx - 230, 440)), ((cx + 95, 520), (cx + 190, 540), (cx + 230, 440))],
        "arms_up": [((cx - 95, 520), (cx - 200, 380), (cx - 190, 250)), ((cx + 95, 520), (cx + 200, 380), (cx + 190, 250))],
        "sit": [((cx - 95, 520), (cx - 140, 660), (cx - 60, 720)), ((cx + 95, 520), (cx + 140, 660), (cx + 60, 720))],
        "walk_a": [((cx - 95, 520), (cx - 60, 680), (cx - 20, 760)), ((cx + 95, 520), (cx + 160, 660), (cx + 190, 740))],
        "walk_b": [((cx - 95, 520), (cx - 160, 660), (cx - 190, 740)), ((cx + 95, 520), (cx + 60, 680), (cx + 20, 760))],
        "wave": [((cx - 95, 520), (cx - 150, 640), (cx - 150, 740)), ((cx + 95, 520), (cx + 200, 420), (cx + 230, 300))],
    }[pose if pose in ("idle", "hold", "shrug", "arms_up", "sit", "walk_a", "walk_b", "wave") else "idle"]
    for a in arms:
        c.line(list(a), w=lw)
        hand(*a[-1])
    # torso capsule
    c.rect([cx - 120, 400, cx + 120, 800], fill=body_col, w=8, r=110)
    if kind == "kyle":
        c.rect([cx - 72, 400, cx + 72, 470], fill=body_col, w=6, r=20)   # polo collar
        c.line([(cx, 405), (cx, 480)], w=5)
        c.rect([cx - 10, 520, cx + 105, 570], fill=(250, 250, 250), w=5, r=8)
        c.text((cx + 48, 545), "KYLE", 30, fill=OL, font=F_BLACK)
        c.ell([cx - 90, 520, cx - 40, 570], fill=(250, 240, 120), w=5)
        c.ell([cx - 78, 536, cx - 52, 554], fill=(40, 120, 200), w=0)
    elif kind == "kyle_suit":
        c.poly([(cx - 70, 400), (cx, 520), (cx - 110, 470)], fill=(120, 70, 30), w=5)
        c.poly([(cx + 70, 400), (cx, 520), (cx + 110, 470)], fill=(120, 70, 30), w=5)
        c.poly([(cx - 22, 410), (cx + 22, 410), (cx + 14, 600), (cx, 630), (cx - 14, 600)], fill=(240, 190, 60), w=4)
    elif kind in ("agent",):
        c.poly([(cx - 30, 400), (cx + 30, 400), (cx, 520)], fill=(250, 250, 250), w=4)
        c.line([(cx, 420), (cx, 560)], fill=(200, 40, 40), w=12)
        c.ell([cx + 40, 640, cx + 90, 690], fill=(240, 200, 60), w=5)  # badge
    elif kind == "cop":
        c.ell([cx + 30, 460, cx + 80, 510], fill=(240, 200, 60), w=5)
        c.rect([cx - 120, 690, cx + 120, 720], fill=OL, w=0)
    elif kind == "customer":
        c.line([(cx, 410), (cx, 790)], w=5)
    elif kind == "lady":
        for k in range(9):
            a = math.pi * (0.15 + 0.7 * k / 8)
            c.ell([cx - 8 + math.cos(a) * 90, 400 + math.sin(a) * 60, cx + 8 + math.cos(a) * 90, 416 + math.sin(a) * 60], fill=(240, 200, 60), w=2)
    # head
    if kind in ("kyle", "kyle_suit"):
        if back:
            kyle_hair(c, cx, hy, R, back=True)
        else:
            c.ell([cx - R, hy - R, cx + R, hy + R], fill=SKIN, w=8)
            face(c, cx, hy + 20, R, face_kind)
            kyle_hair(c, cx, hy, R)
    else:
        if back:
            c.ell([cx - R, hy - R, cx + R, hy + R], fill=(110, 70, 40), w=8)
        else:
            c.ell([cx - R, hy - R, cx + R, hy + R], fill=SKIN, w=8)
            face(c, cx, hy + 20, R, face_kind)
        if kind in ("customer", "agent"):
            bucket_hat(c, cx, hy + 40, R)
        elif kind == "cop":
            c.chord([cx - R * 0.9, hy - R * 1.2, cx + R * 0.9, hy - R * 0.2], 180, 360, fill=(36, 50, 92), w=7)
            c.rect([cx - R * 1.0, hy - R * 0.72, cx + R * 1.0, hy - R * 0.52], fill=(24, 30, 60), w=6, r=10)
            c.ell([cx - 18, hy - R * 0.98, cx + 18, hy - R * 0.72], fill=(240, 200, 60), w=3)
        elif kind == "lady":
            rnd = random.Random(4)
            for k in range(26):
                a = math.pi * (1.05 + 0.9 * k / 25)
                x = cx + math.cos(a) * R * 0.98 + rnd.uniform(-12, 12)
                y = hy + math.sin(a) * R * 0.95 + rnd.uniform(-12, 12)
                c.ell([x - 46, y - 46, x + 46, y + 46], fill=(214, 110, 40), w=5)
        elif kind in ("friend1", "friend2"):
            col = (40, 30, 30) if kind == "friend1" else (240, 190, 60)
            c.chord([cx - R, hy - R, cx + R, hy + R * 0.3], 180, 360, fill=col, w=7)
    im = c.out()
    if scale != 1.0:
        im = im.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    return im


# ---------------------------------------------------------------- props
def ticket(w=420, h=640, tilt=0):
    c = C(w, h)
    c.rect([6, 6, w - 6, h - 6], fill=(250, 214, 60), w=6, r=18)
    c.rect([22, 22, w - 22, h * 0.48], fill=(70, 150, 230), w=4, r=10)
    c.text((w / 2, h * 0.08), "STATE LOTTERY", h * 0.035, fill=(255, 255, 255))
    c.text((w / 2, h * 0.17), "REEL BIG", h * 0.08, fill=(255, 220, 60), stroke=4)
    c.text((w / 2, h * 0.27), "CASH", h * 0.1, fill=(255, 220, 60), stroke=4)
    c.poly([(w * 0.18, h * 0.38), (w * 0.55, h * 0.32), (w * 0.8, h * 0.38), (w * 0.55, h * 0.43)], fill=(40, 90, 170), w=4)
    c.poly([(w * 0.8, h * 0.38), (w * 0.92, h * 0.31), (w * 0.92, h * 0.45)], fill=(40, 90, 170), w=4)
    c.rect([22, h * 0.5, w - 22, h * 0.58], fill=(220, 50, 40), w=0)
    c.text((w / 2, h * 0.54), "WIN UP TO $1,000,000!", h * 0.032, fill=(255, 255, 255))
    for r_ in range(3):
        for k in range(3):
            x = 60 + k * (w - 120) / 2
            y = h * (0.66 + r_ * 0.09)
            c.ell([x - 26, y - 22, x + 26, y + 22], fill=(150, 200, 240), w=4)
    for k in range(18):
        x = 40 + k * (w - 80) / 18
        c.rect([x, h * 0.93, x + (w - 80) / 36, h * 0.97], fill=OL, w=0)
    im = c.out()
    return im.rotate(tilt, expand=True, resample=Image.BICUBIC) if tilt else im


def polaroid(scene_img, w=200, label="", tilt=0):
    h = int(w * 1.22)
    c = C(w, h)
    c.rect([4, 4, w - 4, h - 4], fill=(250, 248, 240), w=3, r=4)
    im = c.out()
    thumb = scene_img.convert("RGB").resize((w - 24, int((w - 24) * 1.0)), Image.LANCZOS)
    im.paste(thumb, (12, 12))
    d = ImageDraw.Draw(im)
    if label:
        f = ImageFont.truetype(F_BLACK, max(10, int(w * 0.08)))
        d.text((w / 2, h - (h - w) / 2 + 4), label, font=f, fill=(200, 40, 40), anchor="mm")
    d.ellipse([w / 2 - 8, 2, w / 2 + 8, 18], fill=(220, 40, 40), outline=OL)
    return im.rotate(tilt, expand=True, resample=Image.BICUBIC) if tilt else im


def arm(length=900, bend=0.15, thick=46):
    """A black stick arm with ball hand, pointing down-left from top-right."""
    W, H = 600, length
    c = C(W, H)
    c.line([(W - 40, 0), (W * (0.5 + bend), H * 0.5), (80, H - 80)], w=thick)
    c.ell([40, H - 120, 120, H - 40], fill=OL, w=0)
    return c.out()
