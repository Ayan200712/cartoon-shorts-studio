# Making the pictures move: four production routes

Contents: [Character design](#character-design-first) · [Route 1 AI image→video](#route-1-ai-image--video-archetype-b) ·
[Route 2 Cut-out puppets](#route-2-cut-out-puppets-archetypes-c-d-and-the-zero-budget-option) ·
[Route 3 Toon-3D](#route-3-toon-3d-archetype-a) · [Route 4 Stills + camera](#route-4-stills--camera-the-fallback) ·
[Acting rules](#acting-rules-all-routes)

## Character design first

Design one protagonist + a small cast **before** any shot. Every reference channel uses a simple, high-contrast,
outline-heavy design whose identity lives in one costume signifier. That simplicity is what makes it cheap to
pose, consistent across AI generations, and readable at phone size.

Write a character sheet (save it as `characters.md` in the project):
```
NAME: Engineer Eli (protagonist)
HEAD: large round white head, ~38% of height, no neck, no nose, thick black outline
FACE: two black dot eyes, single-stroke brows, small line mouth; extremes: grid-of-teeth grimace, ^ ^ grin
BODY: teal capsule torso (work jacket), thin black stick limbs, round ball hands
SIGNIFIER: orange hard hat
PALETTE: #F2EFEA head, #1F8A8A jacket, #F28C28 hat, #111111 outlines
EXPRESSIONS NEEDED: neutral, smug, shocked (O-mouth), grimace, determined
```
Generate (or draw) a **turnaround sheet**: front, 3/4, side, back + 6 expressions, on a flat background.
Every later image prompt references this sheet.

## Route 1: AI image → video (Archetype B)

The cheapest route to the most-viewed style. Pipeline: character sheet → one 9:16 keyframe per clause
(text-capable image model, signs baked in) → image-to-video (5–8 s gens) → keep the best 1.5–4 s →
assemble.

### Keyframe prompt template
```
Vertical 9:16 frame, stylized 3D cartoon render, cel-shaded with ink outlines, soft global illumination,
volumetric light, shallow depth of field, saturated colours.
Characters in the style of the attached sheet: big round white heads, stick limbs, thick black outlines,
dot eyes. [CHARACTER] wearing [SIGNIFIER], [POSE/ACTION], [EXPRESSION].
Setting: [LOCATION with 2–3 concrete props]. [TIME OF DAY / GRADE: warm afternoon | cold blue night].
[BIG SIGN TEXT: "PRIZE HALL" in bold letters on a sign] (only for large, short text).
Composition: subject in upper-middle third, clean lower third for captions, nothing important in the top 15%.
```
Rules: always attach the character sheet as a reference image; one action per frame; keep text to 1–4 big
words; specify the grade that matches the story beat (bright setup → cold twist).

### Image-to-video motion prompt template
```
Slow dolly-in. [CHARACTER] [ONE simple action, e.g. "slams the rail with a hammer, sparks fly"].
Camera steady, no cuts, keep the character's face and outfit unchanged, keep sign text unchanged.
```
- One camera move + one action per clip. Complex choreography morphs.
- For transitions, prompt the move into the next scene: "camera pushes through the doorway",
  "camera flies over the cliff edge revealing the canyon", "camera pushes into the phone screen".
- Generate 2–4 takes for hero shots; keep the cleanest 1.5–4 s window. Trim before faces drift.
- Cover AI tells: cut before morphs, put exact numbers/labels on overlays (AI garbles small print),
  dissolve over glitches, keep shots short.

### Tooling
Any image model with reference-image support and any image-to-video model works. If connectors in this
session provide generation tools (e.g. image/video/music/SFX generation MCPs), use them; otherwise write the
prompts into `shots/prompts.md` for the user to run, and continue with placeholders.

## Route 2: Cut-out puppets (Archetypes C, D, and the zero-budget option)

Characters are separate PNG parts (or whole-pose PNGs) composited and keyframed. This is how the 2D comedy
and data styles are made (Moho / After Effects / Toon Boom / Spine), and `scripts/assemble.py` can do a useful
subset directly.

### Making parts
Draw or generate each character as a **flat-colour illustration on a transparent or plain background**, then
cut into layers: head, face decals (eyes/mouths per expression), torso, upper/lower arms, hands, legs, props.
Keep pivot points (anchors) at joints. Prompt for parts: "flat vector cartoon, thick black outline, plain white
background, character facing 3/4 left, arms down at sides" then remove background.

Simplest workable kit (what assemble.py animates well): **whole-body pose PNGs** (idle, point, shrug, shocked,
walk_a, walk_b) + **face PNGs** + props. Swap poses on the stressed word; idle bob in between.

### Motion principles that make cheap puppets feel alive (measured in the 2D references)
- **Always 30 fps, never on twos.** Smooth eased tweens on every part.
- **Idle never stops**: bob 4–8 px at ~1–1.5 Hz, sway 1–2°, breathing squash 1–2 %
  (`"idle":{"bob":6,"sway":1.5,"breathe":0.015,"rate":1.2}`). Offset `phase` per character.
- **Pose swaps are 1–2 frame replacements**, not tweens, timed to the stressed word. Add a 2–3-frame
  anticipation (small move opposite) and overshoot (`outBack`) on big gestures.
- **Faces cut, don't morph**: swap the face decal on the emotional word.
- **Squash & stretch on landings/impacts**: `sx/sy` keys 1.15/0.85 → 1/1 over 4–6 frames.
- **Entrances**: pop-in with overshoot (`pop_in: 0.2–0.3`), slide in from off-screen with `outBack`,
  or drop in with motion + a `thud`.
- Mouth flaps: `"frames":["mouth_a.png","mouth_b.png"],"frames_fps":10` while that character speaks.
- **Emoji emotion marks**: sweat drop, "…", spiral eyes as small layers popping near the head.

### Backgrounds
Painted/illustrated scenes with the same outline language as characters (C) or flat vector with gradients (D).
Make backgrounds 15–25 % larger than the frame so camera pushes and pans have room.

## Route 3: Toon-3D (Archetype A), and the best free route for Archetype B looks

**Check first:** `ls /Applications | grep -i blender` (macOS) or `which blender`. If Blender is installed,
this route beats flat 2D drawing by a wide margin: real perspective, soft light, depth of field and
outlines get much closer to the AI/3D reference look, at about 1.5–2.5 s per 1080×1920 frame on an M-series
Mac (Eevee, 24 samples).

`scripts/blender/toonkit3d.py` (run inside Blender: `blender -b --factory-startup -P shot.py -- args`) gives you:
- `reset(frames, res)`: Eevee, Standard view transform, 30 fps
- `toon(color|tex)`: soft 3D toon material (diffuse plus a lift so shadows never go black)
- `flat(tex, alpha=True)`: unlit decals and signs
- `outline(obj)`: inverted-hull ink outline
- `box / plane / wall_plane(tile) / sphere / cyl`: primitives with materials and outlines
- `Char(name, kind, loc, R, faces=[...], back=False)`: the round-head stick character, built from a sphere
  head, a hair cap with fringe and curl tuft, a capsule body, name tag and badge decals, jointed arms and legs,
  and swappable face decals (`set_face(name, frame)`). It supports hats (bucket with lures, cop), curls,
  ties and gold badges. Poses (`pose("shrug"|"arms_up"|"hold"|"wave"|"wheel"|…, frame)`), `walk(f0, f1)`,
  `sit(frame)`, `bob(frames)`, `move(frame, loc, rot_z, scale)`
- `camera(loc, look, lens, dof_obj)` + `key_cam(...)`: tracked camera with keyframed moves and DOF
- `lamp_light(...)`, `render(dir)`, `still(path, frame)`

Workflow that worked:
1. Make flat textures with PIL (`scripts/toonkit2d.py` has `face()` expressions, tickets, signs). Face
   decals are PNGs drawn on a transparent square, one per expression.
2. Write one function per shot: build the set, place characters, keyframe acting on the word timings,
   keyframe the camera.
3. **Composition pass first:** render 3 stills per shot at 540×960 and pair them with the reference frames.
   Expect most first cameras to be too close; fix every shot before the full render.
4. Full render to PNG frames, encode each shot with light denoise (`hqdn3d=1.2:1.2:3:3`), then assemble
   with `assemble.py` (`src` = shot clip, `loop: false`), adding captions, transitions, iris or vignette
   overlays, bloom (`grade.bloom`) and audio.

Gotchas:
- Eevee in Blender 4.2+ has no bloom: use `grade.bloom` in assemble.py.
- Blended transparency is unreliable for big glass panes: use frames instead of glass, or alpha-hashed decals.
- A camera placed behind a character's head fills the frame. For over-the-shoulder shots, put the camera
  0.6+ m behind and offset sideways.
- Hide shadow-casting helpers (blinds for light stripes) from the camera with `visible_camera = False`.

General Blender notes: low-poly kit (faceted terrain, cone trees, cloud blobs), toon/cel
shader with outline (Freestyle or inverted-hull), bloom, DOF, warm haze. Egg-head character = sphere head with
an image-texture face (swap the texture for expressions — instant single-frame face changes), simple rigged
body. Keyframe the camera (slow push/truck/crane), render 1080×1920 at 30 fps, then assemble captions/audio
with assemble.py (pass the rendered MP4 shots as `src`). Claude can write Blender Python (`bpy`) to build
scenes procedurally if the user has Blender installed — that is very likely how the reference channels
template their videos.

## Route 4: Stills + camera (the fallback)

When video generation isn't available: one illustration per clause + assemble.py camera moves (push, pan,
drift), puppet layers for the characters, flashes, shakes, dissolves and graphics. Keep shots ≤ 2.5 s and add
an in-shot event in every shot so it never reads as a slideshow. This is the default path for a fully
automated first draft.

## Acting rules (all routes)

- **Literalise the narration.** "His ears turn red" → ears turn red. "Nothing" → empty box. The visual
  pun is the joke and the comprehension aid.
- **One idea per frame.** If you need a label to explain the shot, the shot is too complicated.
- **React shots** (deadpan stare, sweat drop, crowd laughing) between beats give the pacing air without
  silence.
- **Escalate** sizes, speeds and stakes rung by rung; the climax shot is the biggest/most destructive image.
- Keep the protagonist screen-direction consistent (hero faces/moves right, rival left) so 1-second cuts stay
  readable.
