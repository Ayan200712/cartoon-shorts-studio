# Editing, camera, transitions, captions, graphics, colour

Contents: [Shot planning](#shot-planning) · [Camera](#camera) · [Transitions](#transitions) ·
[Captions](#captions) · [Graphics layer](#graphics-layer) · [Effects](#effects) · [Colour](#colour-grade-as-story) ·
[Hook & loop](#hook-and-loop)

## Shot planning

**The rule that explains every reference: one visual idea per narration clause, cut on the clause.**
Write the shot list *from* the word timings, not from a clock.

Measured rhythm (real shots, including dissolves the cut detector misses):

| Style | Median shot | Range | Notes |
|---|---|---|---|
| AI toon story (fast) | ~1 s | 0.13–7 s | hard cuts + whip smears |
| AI toon story (smooth) | ~2 s | 1–8 s | 0.2–0.3 s dissolves hide almost every join |
| Rigged 2D comedy | 3–5 s | 0.3–12 s | bursts of 0.3–1.5 s around jokes |
| Data motion-graphics | ~3 s | 0.1–16 s | long shots carry in-shot changes |
| Toon-3D slow explainer | 6–10 s | 4–24 s | something new happens in-shot every 2–3 s |

Whatever the shot length, **something must change every 1.5–3 s**: a cut, a pose swap, a prop/label pop,
a camera move reversal, a counter tick. Long shots are fine only if they're busy.

Shot list format (one row per clause):
```
#  | start–end (s) | VO words            | Visual (literal)                        | Camera            | In-shot events @ word      | Join in  | SFX
1  | 0.00–2.10     | "He sawed gaps…"    | engineer sawing a rail, canyon behind   | slow push 1.0→1.1 | sparks @ "gaps"            | —        | saw rasp
2  | 2.10–3.60     | "two companies…"    | two crews racing, banners               | truck right       | banner pops @ "first"      | dissolve | whoosh
```

Sync points that matter most (use word timestamps from `scripts/align_words.py`):
- Cuts land **on the first word of a clause** (or 2–3 frames before it).
- Pose/expression swaps, label pops, stamps and flashes land **on the stressed word** (the noun or verb
  carrying the meaning, e.g. "*purple*", "*nothing*", "*six*").
- Impacts (shake + boom) land on the hard consonant of the impact word.

## Camera

No shot is static. Default move per shot: a slow push-in from 1.00 to 1.06–1.15 scale over the shot,
eased in-out, or a gentle truck/pan of 2–5 % of frame width. Alternate push-in / pull-out / lateral so
consecutive shots don't feel identical.

| Move | assemble.py | Use for |
|---|---|---|
| Slow push-in | `"camera":{"zoom":[1.0,1.12]}` | default, building tension |
| Pull-out reveal | `"zoom":[1.25,1.0]` | reveal scale / the twist |
| Truck / pan | `"x":[0.04,-0.04]` | crowds, landscapes, following action |
| Tilt | `"y":[0.05,-0.05]` | tall subjects, "so deep you can't see the bottom" |
| Crash zoom | `"zoom":[1.0,1.6],"ease":"inExpo"` over 0.3–0.5 s | shock, emphasis (fast AI-story channels) |
| Drift | `"drift":1` | keeps any still image alive |
| Impact shake | `"shake":[{"at":t,"dur":0.15–0.3,"amp":15–35}]` | gunshots, slams, explosions (3–8 frames) |
| Handheld | long low shake `amp 4–8, dur = shot` | tense beats only |
| Dutch tilt | `"rot":[0,-4]` | something's wrong |

Framing: characters fill 60–90 % of frame width in mediums; keep faces in the upper-middle third (above the
caption band at ~70 %). Use extreme close-ups cropped by the frame edge for reactions; POV and over-the-shoulder
inserts for "you" scenes.

## Transitions

Frame counts at 30 fps. `assemble.py` supports the starred ones via `"transition":{"type":…,"dur":…}`.

| Transition | Duration | When |
|---|---|---|
| Hard cut ★`cut` | 0 | default in fast edits; every punchline |
| Cross-dissolve ★`dissolve` | 6–9 frames (0.2–0.3 s) | smooth AI-story style: between almost all clips |
| Whip pan ★`whip`, `whip_left/right/up/down` | 4–9 frames (0.15–0.3 s) | dialogue back-and-forth; location change; energy |
| Zoom punch-through ★`zoom` | 8–12 frames | concept jump ("inside the atom") |
| White flash cut ★`flash` | 2–4 frames | montage beats, impacts, time skips |
| Dip to black ★`dip` | 8–15 frames | act break: "It doesn't." / "You see," |
| Push slide ★`slide` | 8–10 frames | list items, comparisons |
| Pass-through (in-camera) | — | push through a door / into a screen / over an edge; generate in the clip itself |
| Iris in/out, push-through-pupil | 10–15 frames | concept transitions (make as a layer/mask in your editor) |
| FX fill (smoke/explosion fills screen) | 10–20 frames | showpiece transition every 10–15 s (2D comedy) |
| Match cut | 0 | same pose in a new environment (montage: "12 duels in 12 towns") |

Pick **one dominant join** per video (dissolve *or* hard cut) and use the others as accents.

## Captions

Every reference burns in captions. Measured spec (at 1080×1920):

- Position: horizontally centred, vertical centre **68–72 %** of height. Max width ≈ 86 %.
- Chunk: **1–3 words**, broken at punctuation/breath; card changes every 0.3–0.7 s. (Build-up style: words
  accumulate up to 4–9 words, then clear per phrase.)
- Colour: white `#FFFFFF`; outline black 2–6 px and/or soft drop shadow. **No boxes.**
- Case/font by style:

| Preset | Look | Matches |
|---|---|---|
| `clean` | bold sans, sentence case, thin outline + shadow, hard swaps | AI toon story, Toon-3D |
| `clean_pop` | same + 85 → 100 % scale pop over 2 frames | Cowboy toon-3D |
| `bubbly` | lowercase rounded heavy, thick black stroke, pop from 35 % | kid-friendly game look |
| `caps_gold` | ALL CAPS heavy, shadow only, gold keywords, 2-frame pop | data explainer |
| `build_caps` | small ALL-CAPS rounded, builds word-by-word, each word pops 125 → 100 %, red punch words | rigged 2D comedy |
| `minimal` | small sentence case, thin shadow | cinematic AI story |
| `karaoke` | big caps, active word yellow | generic viral style (not used by references) |

Set keywords (gold/red words) with `"style":{"keywords":["trillion","red"]}`. Use them sparingly:
one or two per sentence at most, on the payload word.

Real fonts used by references: Montserrat ExtraBold/Black, Poppins Bold, Inter Bold, Nunito Black,
Fredoka/Baloo (rounded). They're free on Google Fonts. Pass a `.ttf` path via `"style":{"font":…}`;
the presets fall back to Arial Black / Arial Bold / Arial Rounded Bold.

## Graphics layer

Graphics carry information so the voice doesn't have to. Built into assemble.py as layer `type`s:

- **Pill label / sticker** (`type:"text"`, `box`, `border`, `rot` ±3°, `pop_in` 0.1 s): pinned next to the
  object. Colour code: red = rule/penalty/danger, gold = info/number, green = good outcome, white = time/place.
- **Sign / title card** (`type:"text"`, `box:"#7A4E2D"`, wood colours, `keys` dropping in from above with
  `outBack`): diegetic-looking labels ("10 TONS / IRON SAND").
- **Counter HUD** (`type:"counter"`): dark rounded box, small tracked label, big gold digits rolling over
  0.5–1.5 s on the spoken number, red under a danger threshold.
- **Look-here ring** (`type:"ring"`): 80 → 140 % scale, fading, 0.5 s, on the object as it's named.
- **Level badge** (`type:"text"`, navy `#1C2A4A` box, 2 px gold border, "LEVEL 3\nOBSIDIAN"): persistent in
  the top 15–25 % band, swapped at each escalation rung.
- **Stamps** (SOLD / CANCELED / ✓ / ✕): text layer, `rot` −12°, `keys` scale 1.6 → 1.0 in 4 frames +
  `thud` SFX + tiny shake.
- **Onomatopoeia** ("glug", "click!", "BANG"): text layer next to the source, pop + slight rotation.
- **Arrows, X-ray labels, blueprint**: draw as PNGs (or generate) and add as image layers.

In AI-image styles, prefer **baking big signs into the generated keyframe** (room signs, banners, headlines);
use overlays only for numbers and labels that must be exact (AI garbles small text).

## Effects

- **Flash frames**: 2–4 frames of white at 60–90 % on impacts and montage cuts (`"flash"`).
- **Impact frame**: flash + shake + boom on the same frame.
- **Grain**: none in clean styles; `grain 0.02–0.04` for gritty/historical moods.
- **Vignette**: 0.25–0.4 to centre attention; edge blur for data explainers.
- **Bloom/glow, god-rays, DOF**: come from the render/AI model — ask for them in prompts.
- **Smoke puffs, sparkles, muzzle stars, steam**: outlined cartoon FX (2D) or particle bursts (3D); also
  available as stock overlays.

## Colour: grade as story

- Pick a 4–6 colour palette per video with **one saturated accent** reserved for the key object/hero.
- Setup is bright and saturated; **shift to cold blue / night / rain exactly at the twist or "You see,"**;
  resolve warm (amber/gold) if the ending is kind, stay cold if it's dark.
- "One warm window in a cold frame" = the secret/anomaly.
- Explanation mode: switch to a blueprint/hologram grade (monochrome electric blue, one accent colour
  for the key quantity).
- assemble.py per-shot `"grade":{"saturation":1.1,"contrast":1.05,"tint":"#2244AA","tint_amt":0.12,"vignette":0.3}`.

## Hook and loop

- Frame 1 is already the most striking image of the video (often the payoff/transformation), with the hook
  line starting at 0.0 s. No title card, no logo. A flash or whip into the first frame is fine.
- First 3 s: show the contradiction visually (a FIRE button that does nothing, a blade going in straight and
  coming out curved, a guy parking an F1 car on the grass).
- Loop: final shot returns to the opening location/framing **and/or** the final line grammatically runs into
  the first line. End within 0.5–1.5 s of the last word; music doesn't fade to silence (a hard end loops
  better), unless the last gag needs a beat.
