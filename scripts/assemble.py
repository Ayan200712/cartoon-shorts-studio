#!/usr/bin/env python3
"""Assemble a vertical (9:16) animated short from a timeline JSON.

Renders every frame (camera moves, shake, flashes, transitions, cut-out puppet
layers, colour grade, grain, word-by-word captions), then mixes voice-over,
ducked music and sound effects with ffmpeg.

Run (uv fetches the deps):
  uv run --no-project --python 3.12 --with numpy --with opencv-python-headless --with pillow \
      python scripts/assemble.py timeline.json out.mp4 [--preview]

--preview renders at half resolution for a fast check.
See references/timeline-format.md for the full schema.
"""
import argparse, json, math, os, shutil, subprocess, sys, tempfile
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

FFMPEG = shutil.which("ffmpeg") or os.path.expanduser("~/.local/bin/ffmpeg")

# ----------------------------------------------------------------- easing
def _back(t, s=1.70158):
    t -= 1
    return t * t * ((s + 1) * t + s) + 1

EASES = {
    "linear": lambda t: t,
    "in": lambda t: t * t,
    "out": lambda t: 1 - (1 - t) ** 2,
    "inOut": lambda t: 2 * t * t if t < .5 else 1 - (-2 * t + 2) ** 2 / 2,
    "inOutSine": lambda t: -(math.cos(math.pi * t) - 1) / 2,
    "outCubic": lambda t: 1 - (1 - t) ** 3,
    "inCubic": lambda t: t ** 3,
    "outExpo": lambda t: 1 if t >= 1 else 1 - 2 ** (-10 * t),
    "inExpo": lambda t: 0 if t <= 0 else 2 ** (10 * t - 10),
    "outBack": _back,
    "outElastic": lambda t: 0 if t <= 0 else 1 if t >= 1 else 2 ** (-10 * t) * math.sin((t * 10 - .75) * (2 * math.pi) / 3) + 1,
}

def ease(name, t):
    t = min(1.0, max(0.0, t))
    return EASES.get(name or "inOutSine", EASES["inOutSine"])(t)

def lerp(a, b, t):
    return a + (b - a) * t

def span(v, t, e):
    """v is a number or [from, to]; t is 0..1 progress."""
    if isinstance(v, (list, tuple)):
        return lerp(v[0], v[1], ease(e, t))
    return v

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def bgr(h):
    r, g, b = hex_rgb(h)
    return (b, g, r)

# ----------------------------------------------------------------- media
class Source:
    """Image or video, returned as a BGR frame at time t (seconds into the shot)."""
    cache = {}

    def __init__(self, path, base):
        self.path = path if os.path.isabs(path) else os.path.join(base, path)
        if not os.path.exists(self.path):
            sys.exit(f"missing source: {self.path}")
        ext = os.path.splitext(self.path)[1].lower()
        self.is_video = ext in (".mp4", ".mov", ".webm", ".mkv", ".gif", ".m4v")
        if self.is_video:
            self.cap = cv2.VideoCapture(self.path)
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.idx = -1
            self.last = None
        else:
            if self.path not in Source.cache:
                im = cv2.imread(self.path, cv2.IMREAD_UNCHANGED)
                if im is None:
                    sys.exit(f"cannot read image: {self.path}")
                if im.ndim == 2:
                    im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
                if im.shape[2] == 4:
                    a = im[..., 3:4].astype(np.float32) / 255
                    im = (im[..., :3] * a).astype(np.uint8)
                Source.cache[self.path] = im
            self.img = Source.cache[self.path]

    def frame(self, t, offset=0.0, speed=1.0, loop=True):
        if not self.is_video:
            return self.img
        want = int((offset + t * speed) * self.fps)
        if self.n > 0:
            want = want % self.n if loop else min(want, self.n - 1)
        if want != self.idx:
            if want != self.idx + 1:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, want)
            ok, fr = self.cap.read()
            if ok:
                self.last = fr
            self.idx = want
        return self.last if self.last is not None else np.zeros((10, 10, 3), np.uint8)


def load_rgba(path, base):
    p = path if os.path.isabs(path) else os.path.join(base, path)
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im is None:
        sys.exit(f"cannot read layer: {p}")
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGRA)
    elif im.shape[2] == 3:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2BGRA)
    return im

# ----------------------------------------------------------------- shot render
def cam_matrix(sw, sh, W, H, cam, p, t_abs, shakes, fit="cover", depth=1.0):
    """2x3 affine for the camera at shot progress p. depth scales the move (parallax): far layers < 1 < near layers."""
    base = max(W / sw, H / sh) if fit == "cover" else min(W / sw, H / sh)
    e = cam.get("ease", "inOutSine")
    z = 1 + (span(cam.get("zoom", 1.0), p, e) - 1) * depth
    x = span(cam.get("x", 0.0), p, e) * W * depth
    y = span(cam.get("y", 0.0), p, e) * H * depth
    rot = span(cam.get("rot", 0.0), p, e)
    d = cam.get("drift", 0) * depth
    if d:
        x += math.sin(t_abs * 0.7) * d * W * 0.01
        y += math.cos(t_abs * 0.53) * d * H * 0.01
    for s in shakes:
        st, dur = s.get("at", 0), s.get("dur", 0.3)
        if st <= t_abs < st + dur:
            k = 1 - (t_abs - st) / dur
            amp, f = s.get("amp", 20) * k * depth, s.get("freq", 22)
            ph = (t_abs - st) * f * 2 * math.pi
            x += amp * math.sin(ph * 1.0 + 1.3) * (W / 1080)
            y += amp * math.sin(ph * 1.37 + 0.2) * (W / 1080)
            rot += s.get("rot", 0.6) * k * math.sin(ph * 0.9)
            z *= 1 + s.get("zoom", 0.02) * k
    M = cv2.getRotationMatrix2D((sw / 2, sh / 2), rot, base * z)
    M[0, 2] += W / 2 - sw / 2 + x
    M[1, 2] += H / 2 - sh / 2 + y
    return M


def camera_frame(src_img, W, H, cam, p, t_abs, shakes, fit="cover", depth=1.0):
    """Place a source image on a WxH canvas with zoom/pan/rotation + shake."""
    sh, sw = src_img.shape[:2]
    M = cam_matrix(sw, sh, W, H, cam, p, t_abs, shakes, fit, depth)
    return cv2.warpAffine(src_img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def interp_keys(keys, t, default_ease):
    """keys: [{t, x, y, scale, rot, opacity, ease?}] -> dict of values at t."""
    """Each property interpolates between the nearest keys that define it, so keys can be sparse
    (e.g. a key with only "img" doesn't reset x/y). "img" is a step: the latest one at or before t."""
    if not keys:
        return {}
    keys = sorted(keys, key=lambda k: k["t"])
    out = {}
    for prop in ("x", "y", "scale", "rot", "opacity", "sx", "sy"):
        ks = [k for k in keys if prop in k]
        if not ks:
            continue
        if t <= ks[0]["t"]:
            out[prop] = ks[0][prop]
        elif t >= ks[-1]["t"]:
            out[prop] = ks[-1][prop]
        else:
            for a, b in zip(ks, ks[1:]):
                if a["t"] <= t <= b["t"]:
                    p = (t - a["t"]) / max(1e-6, b["t"] - a["t"])
                    out[prop] = lerp(a[prop], b[prop], ease(b.get("ease", default_ease), p))
                    break
    imgs = [k["img"] for k in keys if "img" in k and k["t"] <= t]
    if imgs:
        out["_img"] = imgs[-1]
    return out


def composite_layer(canvas, rgba, cx, cy, scale, rot, opacity, anchor, sx=1.0, sy=1.0, post=None):
    if opacity <= 0.001 or scale <= 0.001:
        return
    h, w = rgba.shape[:2]
    ax, ay = anchor[0] * w, anchor[1] * h
    M = cv2.getRotationMatrix2D((ax, ay), rot, 1.0)
    S = np.array([[scale * sx, 0, 0], [0, scale * sy, 0], [0, 0, 1]], np.float64)
    A = np.vstack([M, [0, 0, 1]])
    T = np.array([[1, 0, cx - ax * scale * sx], [0, 1, cy - ay * scale * sy], [0, 0, 1]], np.float64)
    # translate anchor to target, scale about origin, rotate about anchor
    full = T @ S @ A
    if post is not None:
        full = np.vstack([post, [0, 0, 1]]) @ full
    H_, W_ = canvas.shape[:2]
    warped = cv2.warpAffine(rgba, full[:2], (W_, H_), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    a = warped[..., 3:4].astype(np.float32) / 255 * opacity
    if a.max() == 0:
        return
    canvas[:] = (canvas * (1 - a) + warped[..., :3] * a).astype(np.uint8)


def text_rgba(L, text, W):
    """Render a text sticker / pill label / sign to RGBA (BGRA for cv2)."""
    sc = W / 1080
    fp = find_font(L.get("font") or FONT_PRESETS.get(L.get("font_preset", "heavy")))
    size = int(L.get("size", 60) * sc)
    font = ImageFont.truetype(fp, size) if fp else ImageFont.load_default()
    if L.get("uppercase"):
        text = text.upper()
    stroke = int(L.get("stroke", 0) * sc)
    lines = text.split("\n")
    lw = [font.getlength(s) for s in lines]
    pad = [int(p * sc) for p in L.get("padding", [28, 16])] if L.get("box") else [stroke + 4, stroke + 4]
    lh = int(size * 1.18)
    w = int(max(lw) + pad[0] * 2 + stroke * 2)
    h = int(lh * len(lines) + pad[1] * 2 + stroke * 2)
    border = int(L.get("border", 0) * sc)
    img = Image.new("RGBA", (w + border * 2 + 8, h + border * 2 + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if L.get("box"):
        rad = int(L.get("radius", 22) * sc)
        if L.get("box_shadow", True):
            d.rounded_rectangle([border + 6, border + 8, border + w + 6, border + h + 8], rad, fill=(0, 0, 0, 90))
        d.rounded_rectangle([border, border, border + w, border + h], rad, fill=hex_rgb(L["box"]) + (255,),
                            outline=hex_rgb(L.get("border_color", "#FFFFFF")) + (255,) if border else None, width=border)
    col = hex_rgb(L.get("color", "#FFFFFF"))
    for i, (s, sw) in enumerate(zip(lines, lw)):
        x = border + (w - sw) / 2
        y = border + pad[1] + stroke + i * lh
        if L.get("shadow", not L.get("box")):
            d.text((x + 3 * sc, y + 5 * sc), s, font=font, fill=(0, 0, 0, 140), stroke_width=stroke, stroke_fill=(0, 0, 0, 140))
        d.text((x, y), s, font=font, fill=col + (255,), stroke_width=stroke,
               stroke_fill=hex_rgb(L.get("stroke_color", "#000000")) + (255,))
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)


def ring_rgba(L, p, W):
    """Expanding 'look here' ring: p in 0..1."""
    r = int(L.get("radius", 120) * W / 1080 * lerp(L.get("from", 0.8), L.get("to", 1.4), ease("outCubic", p)))
    th = max(2, int(L.get("width", 8) * W / 1080))
    size = r * 2 + th * 4
    img = np.zeros((size, size, 4), np.uint8)
    b, g, rr = bgr(L.get("color", "#FFFFFF"))
    cv2.circle(img, (size // 2, size // 2), r, (b, g, rr, int(255 * (1 - p))), th, cv2.LINE_AA)
    return img


def layer_image(L, lt, W, base, cache):
    kind = L.get("type", "image")
    if kind == "text":
        key = ("text", json.dumps(L, sort_keys=True))
        if key not in cache:
            cache[key] = text_rgba(L, L["text"], W)
        return cache[key]
    if kind == "counter":  # rolling number: {"from","to","roll":[t0,t1],"format":"${:,.0f}","danger_below":...}
        t0, t1 = L.get("roll", [0, 1])
        v = lerp(L["from"], L["to"], ease(L.get("roll_ease", "outCubic"), (lt - t0) / max(1e-6, t1 - t0)))
        txt = L.get("format", "{:,.0f}").format(v)
        Lc = dict(L)
        if "danger_below" in L and v < L["danger_below"]:
            Lc["color"] = L.get("danger_color", "#FF3B30")
        if L.get("label"):
            txt = L["label"] + "\n" + txt
        key = ("counter", txt, Lc.get("color"))
        if key not in cache:
            cache[key] = text_rgba(Lc, txt, W)
        return cache[key]
    if kind == "ring":
        dur = max(1e-6, L.get("end", lt + 1) - L.get("start", 0)) if L.get("end", 1e9) < 1e8 else 0.6
        return ring_rgba(L, min(1.0, lt / L.get("ring_dur", dur)), W)
    key = L["src"]
    if key not in cache:
        cache[key] = load_rgba(key, base)
    return cache[key]


def render_layers(canvas, layers, t, W, H, base, cache, post=None, out_size=None):
    for L in layers:
        start, end = L.get("start", 0), L.get("end", 1e9)
        if not (start <= t < end):
            continue
        lt = t - start
        img = layer_image(L, lt, W, base, cache)
        # frame-swap animation (mouth flaps, blinks, hand-drawn cycles): list of images + fps
        if "frames" in L:
            fl = L["frames"]
            fi = int(lt * L.get("frames_fps", 8)) % len(fl)
            if fl[fi] not in cache:
                cache[fl[fi]] = load_rgba(fl[fi], base)
            img = cache[fl[fi]]
        kv = interp_keys(L.get("keys", []), lt, L.get("ease", "outCubic"))
        if kv.get("_img"):
            if kv["_img"] not in cache:
                cache[kv["_img"]] = load_rgba(kv["_img"], base)
            img = cache[kv["_img"]]
        x = kv.get("x", L.get("x", 0.5)) * W
        y = kv.get("y", L.get("y", 0.5)) * H
        sc = kv.get("scale", L.get("scale", 1.0)) * (W / 1080 if L.get("type", "image") == "image" else 1.0)
        rot = kv.get("rot", L.get("rot", 0.0))
        op = kv.get("opacity", L.get("opacity", 1.0))
        sx, sy = kv.get("sx", 1.0), kv.get("sy", 1.0)
        idle = L.get("idle")
        if idle:  # keeps puppets alive: bob, sway, breathing squash
            r = idle.get("rate", 1.0) * 2 * math.pi
            ph = idle.get("phase", 0)
            y += math.sin(lt * r + ph) * idle.get("bob", 0) * (W / 1080)
            rot += math.sin(lt * r * 0.5 + ph) * idle.get("sway", 0)
            br = idle.get("breathe", 0)
            sy *= 1 + br * math.sin(lt * r + ph)
            sx *= 1 - br * 0.5 * math.sin(lt * r + ph)
        pin = L.get("pop_in")
        if pin and lt < pin:
            sc *= max(0.0, ease("outBack", lt / pin))
        pout = L.get("pop_out")
        if pout and end < 1e8 and t > end - pout:
            sc *= max(0.0, 1 - ease("inCubic", (t - (end - pout)) / pout))
        composite_layer(canvas, img, x, y, sc, rot, op, L.get("anchor", [0.5, 0.5]), sx, sy, post=post(L) if callable(post) else post)


def grade(img, g):
    if not g:
        return img
    out = img.astype(np.float32)
    c = g.get("contrast", 1.0)
    br = g.get("brightness", 0.0)
    if c != 1.0 or br:
        out = (out - 128) * c + 128 + br * 255
    s = g.get("saturation", 1.0)
    if s != 1.0:
        gray = out.mean(axis=2, keepdims=True)
        out = gray + (out - gray) * s
    if g.get("tint"):
        tint = np.array(bgr(g["tint"]), np.float32)
        out = out * (1 - g.get("tint_amt", 0.1)) + tint * g.get("tint_amt", 0.1)
    bl = g.get("bloom", 0)
    if bl:  # soft glow on highlights (lamps, screens, sky), like a render engine's bloom
        H_, W_ = out.shape[:2]
        small = cv2.resize(np.clip(out - g.get("bloom_threshold", 185), 0, 255), (W_ // 4, H_ // 4))
        k = int(W_ * 0.012) * 2 + 1
        glow = cv2.resize(cv2.GaussianBlur(small, (k, k), 0), (W_, H_))
        out = out + glow * bl * 2.0
    out = np.clip(out, 0, 255).astype(np.uint8)
    v = g.get("vignette", 0)
    if v:
        H, W = out.shape[:2]
        key = (W, H, v)
        if key not in grade.vcache:
            yy, xx = np.mgrid[0:H, 0:W]
            r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
            grade.vcache[key] = (1 - v * np.clip(r, 0, 1) ** 2.2)[..., None].astype(np.float32)
        out = (out * grade.vcache[key]).astype(np.uint8)
    return out
grade.vcache = {}


def motion_blur(img, k, horizontal=True):
    k = int(k)
    if k < 3:
        return img
    ker = np.zeros((k, k), np.float32)
    if horizontal:
        ker[k // 2, :] = 1.0 / k
    else:
        ker[:, k // 2] = 1.0 / k
    return cv2.filter2D(img, -1, ker)


# ----------------------------------------------------------------- captions
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/Library/Fonts/Arial Black.ttf",
    "C:/Windows/Fonts/ariblk.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

FONT_PRESETS = {
    "heavy": "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "bold": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "rounded": "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "condensed": "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
    "impact": "/System/Library/Fonts/Supplemental/Impact.ttf",
}

# Caption looks measured from the reference shorts (see references/editing-and-graphics.md)
CAPTION_PRESETS = {
    # toon-3D explainer house style: small white bold sentence-case, outline + soft shadow, no pop
    "clean": {"font_preset": "bold", "size": 50, "uppercase": False, "stroke": 5, "shadow": True,
              "highlight_active": False, "max_words": 3, "max_chars": 16, "y": 0.70, "pop": 0},
    # same but with the 85%->100% 2-frame scale pop
    "clean_pop": {"font_preset": "bold", "size": 52, "uppercase": False, "stroke": 5, "shadow": True,
                  "highlight_active": False, "max_words": 3, "max_chars": 16, "y": 0.70, "pop": 0.067, "pop_from": 0.85},
    # chunky kid-friendly game look: lowercase rounded heavy, thick black stroke, pop from 35%
    "bubbly": {"font_preset": "rounded", "size": 70, "uppercase": False, "lowercase": True, "stroke": 11, "shadow": True,
               "highlight_active": False, "max_words": 3, "max_chars": 16, "y": 0.68, "pop": 0.067, "pop_from": 0.35},
    # data/money explainer: ALL CAPS heavy, soft shadow (no stroke), gold keywords
    "caps_gold": {"font_preset": "heavy", "size": 62, "uppercase": True, "stroke": 0, "shadow": True,
                  "highlight_active": False, "keyword_color": "#FFC83D", "max_words": 3, "max_chars": 18, "y": 0.68,
                  "pop": 0.067, "pop_from": 0.85},
    # minimal cinematic: tiny sentence-case, thin shadow, lets AI imagery carry the frame
    "minimal": {"font_preset": "bold", "size": 40, "uppercase": False, "stroke": 2, "shadow": True,
                "highlight_active": False, "max_words": 3, "max_chars": 18, "y": 0.72, "pop": 0},
    # comedic history explainer: small ALL-CAPS rounded heavy, words build in one by one,
    # each new word pops 125%->100%, punch words (keywords) in red
    "build_caps": {"font_preset": "rounded", "size": 46, "uppercase": True, "stroke": 6, "shadow": True,
                   "highlight_active": False, "build": True, "word_pop": 0.08, "word_pop_from": 1.25,
                   "keyword_color": "#E8392B", "max_words": 4, "max_chars": 22, "y": 0.70, "pop": 0},
    # karaoke highlight (generic viral style, not used by the reference set but popular)
    "karaoke": {"font_preset": "heavy", "size": 80, "uppercase": True, "stroke": 10, "shadow": True,
                "highlight_active": True, "highlight": "#FFE600", "max_words": 3, "max_chars": 18, "y": 0.66,
                "pop": 0.1, "pop_from": 0.7},
}


def find_font(path):
    for p in ([path] if path else []) + FONT_CANDIDATES:
        if p and os.path.exists(p):
            return p
    return None


def chunk_words(words, max_words=3, max_chars=18):
    """Group timed words into on-screen chunks; break after punctuation."""
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        text = " ".join(x["w"] for x in cur)
        if len(cur) >= max_words or len(text) >= max_chars or w["w"].rstrip("\"'”’)")[-1:] in ".,!?;:—":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    for i, c in enumerate(chunks):
        c_start = c[0]["t"]
        c_end = chunks[i + 1][0]["t"] if i + 1 < len(chunks) else c[-1].get("end", c[-1]["t"] + 0.6)
        for w in c:
            w.setdefault("end", w["t"] + 0.3)
        chunks[i] = {"start": c_start, "end": c_end, "words": c}
    return chunks


class Captions:
    def __init__(self, cfg, W, H, base):
        self.cfg = cfg
        st = dict(CAPTION_PRESETS.get(cfg.get("preset", "clean"), CAPTION_PRESETS["clean"]))
        st.update(cfg.get("style", {}))
        self.st = st
        self.keywords = {k.lower().strip(".,!?") for k in st.get("keywords", [])}
        words = cfg.get("words", [])
        if isinstance(words, str):
            p = words if os.path.isabs(words) else os.path.join(base, words)
            words = json.load(open(p))
        words = [dict(w) for w in words if w.get("w", "").strip() and not w["w"].startswith("[")]
        self.chunks = chunk_words(words, st.get("max_words", 3), st.get("max_chars", 18))
        fp = find_font(st.get("font") or FONT_PRESETS.get(st.get("font_preset", "bold")))
        self.size = int(st.get("size", 78) * W / 1080)
        self.font = ImageFont.truetype(fp, self.size) if fp else ImageFont.load_default()
        self.W, self.H = W, H
        self.cache = {}

    def _layout(self, ci):
        """Token strings, colours and per-token boxes for a chunk (cached)."""
        if ("lay", ci) in self.cache:
            return self.cache[("lay", ci)]
        st, c = self.st, self.chunks[ci]
        upper = st.get("uppercase", True)
        raw = [w["w"] for w in c["words"]]
        toks = [(w.upper() if upper else w.lower() if st.get("lowercase") else w) for w in raw]
        is_kw = [w.lower().strip(".,!?\"'") in self.keywords for w in raw]
        stroke = int(st.get("stroke", 10) * self.W / 1080)
        space = self.font.getlength(" ")
        widths = [self.font.getlength(t) for t in toks]
        maxw = self.W * st.get("max_width", 0.86)
        lines, line, lw = [], [], 0
        for i, w in enumerate(widths):
            if line and lw + space + w > maxw:
                lines.append(line); line, lw = [], 0
            line.append(i); lw += (space if lw else 0) + w
        lines.append(line)
        lh = int(self.size * 1.15)
        pos = {}
        for li, ln in enumerate(lines):
            lw = sum(widths[i] for i in ln) + space * (len(ln) - 1)
            x = (self.W - lw) / 2
            for i in ln:
                pos[i] = (x, stroke * 2 + li * lh)
                x += widths[i] + space
        lay = dict(toks=toks, is_kw=is_kw, stroke=stroke, widths=widths, pos=pos,
                   size=(self.W, lh * len(lines) + stroke * 4), lh=lh)
        self.cache[("lay", ci)] = lay
        return lay

    def _color(self, lay, i, active):
        st = self.st
        if lay["is_kw"][i]:
            return hex_rgb(st.get("keyword_color", "#FFC83D"))
        if i == active and st.get("highlight_active", False):
            return hex_rgb(st.get("highlight", "#FFE600"))
        return hex_rgb(st.get("color", "#FFFFFF"))

    def _draw_tok(self, d, lay, i, xy, col):
        stroke = lay["stroke"]
        if self.st.get("shadow", True):
            off = max(2, stroke) 
            d.text((xy[0] + off * 0.6, xy[1] + off * 0.9), lay["toks"][i], font=self.font, fill=(0, 0, 0, 150),
                   stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
        d.text(xy, lay["toks"][i], font=self.font, fill=col + (255,), stroke_width=stroke,
               stroke_fill=hex_rgb(self.st.get("stroke_color", "#000000")) + (255,))

    def render_chunk(self, ci, active, upto=None):
        """Whole chunk (or, in build mode, tokens < upto) as one BGRA image."""
        key = (ci, active, upto)
        if key in self.cache:
            return self.cache[key]
        lay = self._layout(ci)
        img = Image.new("RGBA", lay["size"], (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i in range(len(lay["toks"])):
            if upto is not None and i >= upto:
                break
            self._draw_tok(d, lay, i, lay["pos"][i], self._color(lay, i, active))
        arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)
        self.cache[key] = arr
        return arr

    def render_word(self, ci, i):
        key = ("w", ci, i)
        if key in self.cache:
            return self.cache[key]
        lay = self._layout(ci)
        pad = lay["stroke"] * 3 + 6
        w = int(lay["widths"][i] + pad * 2)
        img = Image.new("RGBA", (w, lay["lh"] + pad * 2), (0, 0, 0, 0))
        self._draw_tok(ImageDraw.Draw(img), lay, i, (pad, pad), self._color(lay, i, i))
        arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)
        self.cache[key] = (arr, pad)
        return self.cache[key]

    def draw(self, canvas, t):
        st = self.st
        for ci, c in enumerate(self.chunks):
            if not (c["start"] <= t < c["end"]):
                continue
            active = 0
            for i, w in enumerate(c["words"]):
                if t >= w["t"]:
                    active = i
            lt = t - c["start"]
            pop = st.get("pop", 0)
            sc = 1.0
            if pop and lt < pop:
                sc = lerp(st.get("pop_from", 0.7), 1.0, ease("outBack", lt / pop))
            cy = st.get("y", 0.70) * self.H
            if not st.get("build"):
                composite_layer(canvas, self.render_chunk(ci, active), self.W / 2, cy, sc, 0, 1.0, [0.5, 0.5])
                return
            # build mode: earlier words static, newest word pops from word_pop_from -> 1
            lay = self._layout(ci)
            base_img = self.render_chunk(ci, active, upto=active)
            composite_layer(canvas, base_img, self.W / 2, cy, 1.0, 0, 1.0, [0.5, 0.5])
            wimg, pad = self.render_word(ci, active)
            wt = t - c["words"][active]["t"]
            wp = st.get("word_pop", 0.08)
            wsc = lerp(st.get("word_pop_from", 1.25), 1.0, ease("outCubic", wt / wp)) if wp and wt < wp else 1.0
            x0, y0 = lay["pos"][active]
            top = cy - lay["size"][1] / 2
            cx = x0 + lay["widths"][active] / 2
            cyw = top + y0 + lay["lh"] / 2
            composite_layer(canvas, wimg, cx, cyw, wsc, 0, 1.0, [(pad + lay["widths"][active] / 2) / wimg.shape[1],
                                                                (pad + lay["lh"] / 2) / wimg.shape[0]])
            return


# ----------------------------------------------------------------- main render
def render(tl, out_video, preview=False, base="."):
    W, H = tl.get("width", 1080), tl.get("height", 1920)
    if preview:
        W, H = W // 2, H // 2
    fps = tl.get("fps", 30)
    shots = tl["shots"]
    for i, s in enumerate(shots):
        s.setdefault("start", shots[i - 1]["end"] if i else 0.0)
        if "end" not in s:
            s["end"] = s["start"] + s.get("dur", 3.0)
        s["_src"] = Source(s["src"], base)
    total = tl.get("duration") or shots[-1]["end"]
    n = int(round(total * fps))
    caps = Captions(tl["captions"], W, H, base) if tl.get("captions") else None
    gl_layers = tl.get("overlays", [])
    layer_cache = {}
    grain_amt = tl.get("grain", 0)
    rng = np.random.default_rng(7)
    grain_tiles = [rng.normal(0, 255 * grain_amt, (H, W, 1)).astype(np.float32) for _ in range(4)] if grain_amt else []
    gflash = tl.get("flashes", [])

    proc = subprocess.Popen([FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                             "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium" if not preview else "veryfast",
                             "-crf", "18" if not preview else "26", "-pix_fmt", "yuv420p", out_video], stdin=subprocess.PIPE)

    def shot_frame(s, t):
        lt = t - s["start"]
        dur = max(1e-6, s["end"] - s["start"])
        p = min(1.0, max(0.0, lt / dur))
        src = s["_src"].frame(max(0, lt), s.get("src_offset", 0), s.get("src_speed", 1.0), s.get("loop", True))
        world = s.get("layers") and s.get("layer_space", tl.get("layer_space", "screen")) == "world"
        if world:
            # layers live in the source image's coordinates, so camera push/pan/shake moves them too
            src = src.copy()
            render_layers(src, [dict(L, start=s["start"] + L.get("start", 0), end=s["start"] + L.get("end", dur)) for L in s["layers"]],
                          t, src.shape[1], src.shape[0], base, layer_cache)
        space = s.get("layer_space", tl.get("layer_space", "screen"))
        shk = s.get("shake", []) + tl.get("shake", [])
        if space == "parallax" and s.get("layers"):
            # each layer gets its own camera strength ("depth": <1 far, 1 subject, >1 foreground), the
            # background plate uses s["bg_depth"]. Layers are authored in the plate's pixel space.
            sh_, sw_ = src.shape[:2]
            fr = camera_frame(src, W, H, s.get("camera", {}), p, t, shk, s.get("fit", "cover"), s.get("bg_depth", 0.5))
            Ls = [dict(L, start=s["start"] + L.get("start", 0), end=s["start"] + L.get("end", dur)) for L in s["layers"]]
            render_layers(fr, Ls, t, sw_, sh_, base, layer_cache,
                          post=lambda L: cam_matrix(sw_, sh_, W, H, s.get("camera", {}), p, t, shk, s.get("fit", "cover"), L.get("depth", 1.0)))
            return grade(fr, s.get("grade") or tl.get("grade"))
        fr = camera_frame(src, W, H, s.get("camera", {}), p, t, shk, s.get("fit", "cover"))
        if s.get("layers") and not world:
            render_layers(fr, [dict(L, start=s["start"] + L.get("start", 0), end=s["start"] + L.get("end", dur)) for L in s["layers"]],
                          t, W, H, base, layer_cache)
        return grade(fr, s.get("grade") or tl.get("grade"))

    for fi in range(n):
        t = fi / fps
        idx = max(i for i, s in enumerate(shots) if s["start"] <= t or i == 0)
        cur = shots[idx]
        fr = shot_frame(cur, t)
        # transition into current shot (or into next shot if we're in its pre-roll)
        for j in (idx, idx + 1):
            if j <= 0 or j >= len(shots):
                continue
            tr = shots[j].get("transition")
            if not tr or tr.get("type", "cut") == "cut":
                continue
            d = tr.get("dur", 0.25)
            a0 = shots[j]["start"] - d / 2
            if not (a0 <= t < a0 + d):
                continue
            q = (t - a0) / d
            A = shot_frame(shots[j - 1], t)
            B = shot_frame(shots[j], max(t, shots[j]["start"]))
            ty = tr["type"]
            if ty == "dissolve":
                fr = cv2.addWeighted(A, 1 - q, B, q, 0)
            elif ty in ("whip", "whip_left", "whip_right", "whip_up", "whip_down"):
                dirn = {"whip": -1, "whip_left": -1, "whip_right": 1, "whip_up": -1, "whip_down": 1}[ty]
                vert = ty in ("whip_up", "whip_down")
                e = ease("inOutSine", q)
                off = int(e * (H if vert else W)) * dirn
                M1 = np.float32([[1, 0, 0 if vert else off], [0, 1, off if vert else 0]])
                M2 = np.float32([[1, 0, 0 if vert else off - dirn * W], [0, 1, off - dirn * H if vert else 0]])
                fr = cv2.warpAffine(A, M1, (W, H)) + cv2.warpAffine(B, M2, (W, H))
                fr = motion_blur(fr, (1 - abs(2 * q - 1)) * W * 0.12, not vert)
            elif ty == "zoom":  # punch through: A zooms in hard, B arrives from slightly zoomed
                if q < 0.5:
                    z = 1 + ease("inCubic", q * 2) * 1.2
                    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
                    fr = cv2.warpAffine(A, M, (W, H), borderMode=cv2.BORDER_REFLECT)
                else:
                    z = 1.35 - ease("outCubic", (q - 0.5) * 2) * 0.35
                    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
                    fr = cv2.warpAffine(B, M, (W, H), borderMode=cv2.BORDER_REFLECT)
                k = int((1 - abs(2 * q - 1)) * 25) * 2 + 1
                fr = cv2.GaussianBlur(fr, (k, k), 0) if k > 1 else fr
            elif ty == "slide":
                # B pushes in from the right, A is pushed out to the left
                e = ease("outCubic", q)
                off = int(e * W)
                fr = np.zeros_like(A)
                if off < W:
                    fr[:, :W - off] = A[:, off:]
                if off > 0:
                    fr[:, W - off:] = B[:, :off]
            elif ty == "flash":
                col = np.array(bgr(tr.get("color", "#FFFFFF")), np.float32)
                base_f = A if q < 0.5 else B
                k = 1 - abs(2 * q - 1)
                fr = (base_f * (1 - k) + col * k).astype(np.uint8)
            elif ty == "dip":  # dip to black
                k = 1 - abs(2 * q - 1)
                fr = ((A if q < 0.5 else B) * (1 - k)).astype(np.uint8)
        # global overlays (logos, stickers, counters as PNGs, arrows...)
        if gl_layers:
            render_layers(fr, gl_layers, t, W, H, base, layer_cache)
        # flashes (impact frames)
        for f in cur.get("flash", []) + gflash:
            at = f.get("at", 0) + (cur["start"] if f in cur.get("flash", []) else 0)
            d = f.get("dur", 0.1)
            if at <= t < at + d:
                k = (1 - (t - at) / d) * f.get("strength", 0.85)
                col = np.array(bgr(f.get("color", "#FFFFFF")), np.float32)
                fr = (fr * (1 - k) + col * k).astype(np.uint8)
        if grain_tiles:
            fr = np.clip(fr.astype(np.float32) + grain_tiles[fi % len(grain_tiles)], 0, 255).astype(np.uint8)
        if caps:
            caps.draw(fr, t)
        proc.stdin.write(fr.tobytes())
        if fi % (fps * 5) == 0:
            print(f"  frame {fi}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    return total


def mix_audio(tl, total, out_audio, base):
    a = tl.get("audio", {})
    inputs, filters, labels = [], [], []
    def P(p):
        return p if os.path.isabs(p) else os.path.join(base, p)
    idx = 0
    vo_label = None
    if a.get("vo"):
        inputs += ["-i", P(a["vo"])]
        filters.append(f"[{idx}:a]aresample=48000,volume={a.get('vo_db', 0)}dB,adelay={int(a.get('vo_at', 0) * 1000)}:all=1[vo]")
        vo_label = "[vo]"; idx += 1
    if a.get("music"):
        inputs += ["-stream_loop", "-1", "-i", P(a["music"])]
        filters.append(f"[{idx}:a]aresample=48000,atrim=0:{total},volume={a.get('music_db', -18)}dB,"
                       f"afade=t=in:d={a.get('music_fade_in', 0.0)},afade=t=out:st={max(0, total - a.get('music_fade_out', 0.6))}:d={a.get('music_fade_out', 0.6)}[mus]")
        idx += 1
        if vo_label and a.get("duck", True):
            filters.append("[vo]asplit=2[vo][vosc]")
            filters.append(f"[mus][vosc]sidechaincompress=threshold=0.03:ratio={a.get('duck_ratio', 6)}:attack=20:release=300[musd]")
            labels.append("[musd]")
        else:
            labels.append("[mus]")
    if vo_label:
        labels.append(vo_label)
    for k, s in enumerate(a.get("sfx", [])):
        inputs += ["-i", P(s["src"])]
        filters.append(f"[{idx}:a]aresample=48000,volume={s.get('db', -4)}dB,adelay={int(s['at'] * 1000)}:all=1[s{k}]")
        labels.append(f"[s{k}]"); idx += 1
    if not labels:
        return None
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,"
                   f"atrim=0:{total}[out]")
    raw = out_audio + ".raw.wav"
    cmd = [FFMPEG, "-y", "-v", "error"] + inputs + ["-filter_complex", ";".join(filters), "-map", "[out]",
                                                    "-c:a", "pcm_s16le", "-ar", "48000", raw]
    subprocess.run(cmd, check=True)
    # two-pass loudnorm: single-pass undershoots on short clips
    target = a.get("lufs", -14)
    meas = subprocess.run([FFMPEG, "-hide_banner", "-i", raw, "-af",
                           f"loudnorm=I={target}:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = (f"loudnorm=I={target}:TP=-1.0:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", raw, "-af", ln + ",aresample=48000", "-c:a", "aac", "-b:a", "192k",
                    out_audio], check=True)
    os.remove(raw)
    return out_audio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline")
    ap.add_argument("out")
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    tl = json.load(open(args.timeline))
    base = os.path.dirname(os.path.abspath(args.timeline))
    tmp = tempfile.mkdtemp()
    vid = os.path.join(tmp, "v.mp4")
    print("rendering frames…")
    total = render(tl, vid, args.preview, base)
    print("mixing audio…")
    aud = mix_audio(tl, total, os.path.join(tmp, "a.m4a"), base)
    if aud:
        subprocess.run([FFMPEG, "-y", "-v", "error", "-i", vid, "-i", aud, "-c:v", "copy", "-c:a", "copy",
                        "-shortest", args.out], check=True)
    else:
        shutil.move(vid, args.out)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
