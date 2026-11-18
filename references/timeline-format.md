# timeline.json — input format for scripts/assemble.py

Paths are relative to the timeline file. Times are seconds. Fractions (x, y, pan) are of frame size.
See `assets/example_timeline.json` for a complete working example.

```jsonc
{
  "fps": 30, "width": 1080, "height": 1920,
  "duration": 61.2,                 // optional; default = end of last shot
  "grade": {"saturation": 1.1, "contrast": 1.05, "vignette": 0.3},   // default for all shots
  "grain": 0.0,                     // 0.02–0.04 for gritty looks
  "shake": [{"at": 12.4, "dur": 0.25, "amp": 28}],                    // global (absolute time)
  "flashes": [{"at": 30.0, "dur": 0.1, "color": "#FFFFFF", "strength": 0.85}],

  "shots": [
    {
      "src": "shots/01.png",        // image or video (mp4/mov/webm). Videos play from src_offset at src_speed
      "start": 0.0, "end": 2.1,     // or "dur"; start defaults to previous end
      "fit": "cover",               // cover | contain
      "src_offset": 0.0, "src_speed": 1.0, "loop": true,
      "camera": {                   // [from, to] or a constant
        "zoom": [1.0, 1.12], "x": [0, -0.03], "y": [0, 0], "rot": [0, 0],
        "ease": "inOutSine",        // linear in out inOut inOutSine outCubic inCubic outExpo inExpo outBack outElastic
        "drift": 0                  // 0–2: slow organic float
      },
      "shake": [{"at": 1.2, "dur": 0.3, "amp": 24, "freq": 22, "rot": 0.6, "zoom": 0.02}],  // at = shot-relative
      "flash": [{"at": 0.0, "dur": 0.12}],                                                  // shot-relative
      "transition": {"type": "dissolve", "dur": 0.25},   // INTO this shot, centred on its start:
                                                         // cut dissolve whip whip_left whip_right whip_up whip_down zoom flash dip slide
      "grade": {"saturation": 0.9, "tint": "#2244AA", "tint_amt": 0.12, "vignette": 0.35, "brightness": -0.03},
      "layer_space": "world",       // "world": layers are placed on the source image and move/zoom with the camera
                                    // (use for characters in a set). "screen" (default): fixed on screen (stickers, HUD)
                                    // "parallax": each layer follows the camera at its own strength: "depth" on the layer
                                    // (<1 far, 1 subject, >1 foreground); the plate uses shot-level "bg_depth" (default 0.5)
      "layers": [ /* layer objects, times relative to shot start; see below */ ]
    }
  ],

  "overlays": [ /* layer objects with ABSOLUTE times: badges, counters, watermark */ ],

  "captions": {
    "words": "words.json",          // [{"w":"He","t":0.05,"end":0.18}, …] from align_words.py, or inline list
    "preset": "clean",              // clean clean_pop bubbly caps_gold build_caps minimal karaoke
    "style": {"keywords": ["six"], "y": 0.70, "size": 50, "font": "fonts/Montserrat-ExtraBold.ttf"}
  },

  "audio": {
    "vo": "audio/vo.wav", "vo_db": 0, "vo_at": 0.0,
    "music": "audio/bed.mp3", "music_db": -18, "duck": true, "duck_ratio": 6,
    "music_fade_in": 0.0, "music_fade_out": 0.4,
    "sfx": [{"src": "sfx/whoosh.wav", "at": 2.05, "db": -6}],
    "lufs": -14
  }
}
```

## Layer objects

Common fields: `start`, `end` (relative to shot, or absolute in `overlays`), `x`, `y` (0–1, anchor position),
`scale`, `rot` (degrees), `opacity`, `anchor` ([0.5,1.0] = bottom-centre: use for characters standing on
ground), `keys`, `ease`, `idle`, `pop_in`, `pop_out` (seconds).

```jsonc
// image / puppet
{"src": "chars/eli_idle.png", "x": 0.35, "y": 0.86, "scale": 0.9, "anchor": [0.5, 1.0],
 "idle": {"bob": 6, "sway": 1.5, "breathe": 0.015, "rate": 1.2, "phase": 0.0},
 "pop_in": 0.25,
 "keys": [                                  // keyframes; any of x y scale rot opacity sx sy, plus "img" to swap the picture
   {"t": 0.0, "x": -0.2},
   {"t": 0.5, "x": 0.35, "ease": "outBack"},
   {"t": 1.40, "img": "chars/eli_shock.png"},           // pose swap on the stressed word
   {"t": 1.45, "sx": 1.12, "sy": 0.9}, {"t": 1.6, "sx": 1.0, "sy": 1.0, "ease": "outElastic"}
 ]}

// frame-cycled layer (mouth flaps, walk cycles, flicker)
{"src": "chars/mouth_a.png", "frames": ["chars/mouth_a.png", "chars/mouth_b.png"], "frames_fps": 10, "x": 0.5, "y": 0.4}

// text sticker / pill label / sign / stamp / badge
{"type": "text", "text": "DISQUALIFIED", "font_preset": "heavy", "size": 56, "uppercase": true,
 "color": "#FFFFFF", "box": "#E8392B", "radius": 22, "border": 4, "border_color": "#FFFFFF",
 "stroke": 0, "rot": -3, "x": 0.5, "y": 0.3, "start": 1.2, "end": 3.0, "pop_in": 0.12}

// rolling counter HUD
{"type": "counter", "label": "TIME LEFT", "from": 86400, "to": 0, "roll": [0.0, 1.2],
 "format": "{:,.0f}s", "danger_below": 3600, "font_preset": "condensed", "size": 70,
 "color": "#FFC83D", "box": "#14121F", "x": 0.5, "y": 0.12, "start": 0, "end": 60}

// look-here ring
{"type": "ring", "x": 0.62, "y": 0.44, "radius": 120, "width": 8, "color": "#FFFFFF", "start": 2.0, "end": 2.6}
```

`font_preset`: heavy (Arial Black), bold, rounded, condensed (DIN Condensed), impact — or `font` with a .ttf path.

## Rendering

```bash
uv run --no-project --python 3.12 --with numpy --with opencv-python-headless --with pillow \
  python scripts/assemble.py timeline.json out.mp4 --preview   # half-res, fast check
uv run --no-project --python 3.12 --with numpy --with opencv-python-headless --with pillow \
  python scripts/assemble.py timeline.json out.mp4             # final 1080x1920
```
Speed: roughly 4–8 s of render per second of video at full resolution on a laptop. Without `uv`, install
`numpy opencv-python-headless pillow` with pip and run with Python 3.9+. Requires `ffmpeg` on PATH.
