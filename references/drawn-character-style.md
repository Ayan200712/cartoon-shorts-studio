# Drawing characters well (the brush-stroke look) and moving the camera

Hard-won from a shot-for-shot remake study: a character built from perfect spheres and even-width tubes reads
as "computed" and "circular", even with lighting and outlines. The reference channels' characters read as
**drawings**: uneven line weight, tapered limbs, painted shading, hair with direction. Draw that look first.
Then give every shot a moving, depth-aware camera. Both matter equally; a good drawing on a static camera,
or a moving camera on a stiff character, both read as amateur.

## 1. Draw like a person, not like a primitive

Use `scripts/brushkit.py` (`kyle()` is a worked example; copy it for your own characters).

**Line**
- Every contour is a brush stroke: width swells from thin ends to a thicker middle, with a slight wobble
  (`stroke`). Closed shapes use `ring()` whose weight changes around the shape: heavy toward the lower right,
  thin toward the upper left, radius slightly uneven. Never use one even-width circle.
- Leave small breaks and overlaps where strokes meet (the hair line crossing the head line). Perfect closed
  loops look mechanical.
- Limbs are tapered curves, thicker near the body, ending in a fist or hand shape. Not uniform tubes.

**Shape**
- Heads are wide, slightly squashed ovals (≈ 1.15 : 1), not circles. Tall capsule torsos with straight sides.
  Head overlaps the torso; the neck is hidden.
- Hair is a shape with direction: a fringe swept to one side, a parting, strands fanning from the parting in
  4–5 browns, a soft glossy highlight band, and a hooked tuft drawn as a tapered stroke.
- Identity comes from one costume signifier (hat, tie, collar, tag).

**Shading**
- Face: painted gradient toward the lower-left edge (light grey-blue), never flat white and never noisy grain.
- Body: soft darker band on the shadow side and a lighter centre band, blurred, not hard streaks.
- Features are soft grey, not pure black: half-lidded eyes with a heavier lid stroke, a short grey mouth.

**Acting set (export each as a separate PNG, same head position):** neutral, talk, talk2, blink, shock
(wide eyes, small mouth, sweat drop), plus smug, worried, grin as the story needs. Swap them on the stressed
word, blink every 2–4 s, and give a squash-and-stretch pop (scale 0.9/1.12 → 1.0, `outElastic`) on reactions.

**Mistakes to avoid**
- An arm or hand crossing the face or vanishing into the body. Keep hands in front of the torso or clearly
  beside it, and check every pose.
- A held prop seen edge-on. Props face the camera.
- Two copies of the same prop (one on the counter and one in the hand).
- Hard black features and a noisy face texture.

## 2. Backgrounds with detail, then depth of field

- Draw the set with real detail: signs, posters, shelves, a corkboard of small items, a lamp, wood grain,
  speckled counters. A bare coloured wall reads as unfinished. Crop signs at the frame edge as the references do.
- Blur the background (≈ 6 px at 1080 wide) so the character pops, and fall the frame edges out of focus a
  little more. Keep the character and the surface it stands behind sharp.
- Light the scene: a warm pool of light behind the character and darker corners, a soft glow on bright areas
  (`grade.bloom`), a vignette (0.4–0.5).
- Colour: one dominant colour idea set by the topic (see `top-channel-patterns.md`), warmer and more saturated
  than feels natural (saturation ×1.15–1.25, contrast ×1.1).

## 3. A camera that moves, with depth

A static or flat-zooming camera is the first thing that makes a remake feel dead. Use parallax: separate layers
move by different amounts, like a drone shot.

Layers (draw each as its own PNG at the plate's size): background plate (moves least), character (normal),
counter or ground in front of the character (normal), foreground props out of focus (moves most).

```jsonc
{"src": "bg.png", "layer_space": "parallax", "bg_depth": 0.45,
 "camera": {"zoom": [1.1, 1.3], "x": [0.05, -0.045], "y": [0.0, 0.01], "rot": [1.6, -1.0], "ease": "inOutSine", "drift": 1},
 "layers": [
   {"src": "kyle_neutral.png", "depth": 1.0, "keys": [{"t": 0.5, "img": "kyle_talk.png"}]},
   {"src": "counter.png",      "depth": 1.0},
   {"src": "scanner_blurred.png", "depth": 1.75}]}
```
`depth` < 1 is far, 1 is the subject, > 1 is foreground; `bg_depth` sets the plate. Layers that must stay
attached (a character and the counter hiding their lower body, arms and body) share the same depth, or they
slide apart.

Move per shot (vary them): fly-in (zoom 1.05 → 1.45 with a slight rotation that levels out, ease out),
fast push on an object, sideways arc around the character (x ±0.05 with a slow push), slow drift with a tilt.
Every shot has a move; `drift` keeps even a "held" shot alive. Insert shots (object close-ups, first-person)
break up character shots (`top-channel-patterns.md`).

## 4. Workflow

1. Draw the character and one background; export the acting PNGs and layers.
2. Build the shot's timeline (parallax camera, expression swaps timed to `words.json`, props, captions).
3. Assemble, then compare frames against the reference moment, side by side.
4. Fix what looks computed (line weight, shape) before adding more shots.
