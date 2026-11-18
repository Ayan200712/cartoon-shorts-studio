---
name: cartoon-shorts-studio
description: Plan, write, animate, edit, sound-design and render original animated cartoon YouTube Shorts / TikToks / Reels (vertical 9:16 story and explainer cartoons like "Why cowboys never load six bullets", "What if…", history explainers). Covers viral script formulas (paradox hook, twist, "You see," explanation, looping ending), character design, AI image-to-video, cut-out puppet and toon-3D pipelines, shot lists synced to voice-over, camera moves, transitions, burned-in caption styles, music, SFX and −14 LUFS mixing, and includes a renderer that assembles the final MP4 from images/clips + VO. Use this whenever the user wants to make, script, storyboard, animate, edit or improve a cartoon/animated short, faceless animated channel, explainer short or story short, or wants to analyze and copy the style of animated shorts they link — even if they don't say "skill" or name a tool.
---

# Cartoon Shorts Studio

Make original animated shorts in the styles that are winning right now. Everything here is distilled from a
frame-by-frame, audio-measured study of 15 top animated shorts (7 channels, 50k–30M views). The numbers in
the references are measurements, not guesses; follow them unless the user wants something different.

## What's in the box

| File | Read it when |
|---|---|
| `references/setup.md` | **first use on a machine**: what to install, and the ElevenLabs voice setup |
| `references/scriptwriting.md` | always: formats, beat sheets, word counts, hooks, loops, titles |
| `references/top-channel-patterns.md` | planning shot lists, camera, scene mood, props and endings: measured from a top channel's 10 latest shorts |
| `references/style-archetypes.md` | choosing the look: 4 proven systems + universal constants |
| `references/editing-and-graphics.md` | shot list, camera, transitions, captions, overlays, colour, hook/loop |
| `references/animation-and-assets.md` | making the visuals: characters, AI prompts, puppets, 3D, stills |
| `references/audio.md` | VO pace, music, SFX placement, mix/master |
| `references/timeline-format.md` | writing `timeline.json` for the renderer |
| `references/analyzing-references.md` | the user gives you new shorts to learn from |
| `references/remaking-a-reference.md` | the user wants a specific short recreated shot-for-shot and compared |
| `scripts/assemble.py` | renders the final 1080×1920 MP4 (camera, puppets, transitions, captions, mix) |
| `scripts/tts_elevenlabs.py` | narration with ElevenLabs: audio + exact word timings |
| `scripts/align_words.py` | word timestamps for a voice-over that didn't come from ElevenLabs |
| `scripts/synth_sfx.py` | free procedural SFX kit (whoosh, pop, boom, riser, ding…) |
| `scripts/analyze_reference.py` | measures reference videos + contact sheets |
| `scripts/blender/toonkit3d.py` | Blender toon-3D kit: sets, round-head rigged characters, cameras (best free look) |
| `references/drawn-character-style.md` | drawing characters with a hand-drawn brush-stroke look, detailed blurred backgrounds, and parallax camera moves |
| `scripts/brushkit.py` | brush-stroke drawing kit (variable-weight strokes, calligraphic rings, painted shading) with a finished example character |
| `scripts/toonkit2d.py` | PIL toon drawing: faces/expressions, characters, tickets, signs, textures |
| `scripts/shot_map.py` | frame-level shot boundaries, camera motion and keyframes of one reference |
| `scripts/fit_vo.py` | narration lines placed and time-fitted to exact start/end times |
| `scripts/compare.py` | remake vs reference: side-by-side video, paired frames, gap report |
| `assets/example_timeline.json` | a working timeline to start from |

Scripts need Python 3.9+, `ffmpeg`, and `numpy opencv-python-headless pillow`. `uv` is the easiest runner:
`uv run --no-project --python 3.12 --with numpy --with opencv-python-headless --with pillow python scripts/X.py …`

## Workflow

Work in a project folder: `script.md`, `characters.md`, `shotlist.md`, `prompts.md`, `shots/`, `chars/`,
`audio/`, `sfx/`, `words.json`, `timeline.json`, `out/`. Show the user the script and the shot list before
spending time or credits on generation, since those are the cheapest places to change direction.

### 0. Setup check (first use)
Follow `references/setup.md`: check for ffmpeg, uv/Python, Blender and an ElevenLabs key; tell the user what's
missing and why, and ask before installing anything.

### 1. Brief (keep it short)
Get or infer: topic (or ask for a domain and propose 3 hooks), target length (default 60 s), archetype,
and what generation tools exist. Check the session for image/video/music/SFX/voice generation connectors;
their availability decides the production route. Don't interrogate. Propose defaults and go.

### 2. Script
Read `references/scriptwriting.md`. Pick one format (Twist Tale is the strongest default for "why" facts).
- Verify the core fact (search if you can). One true mechanism per video.
- Hook ≤ 12 words at 0.0 s; ~3.6 words per second of runtime; "You see," pivot at 65–85 %; last line
  loops into the first.
- Every sentence must be drawable. Write the visual next to each line as you go.
- Give 3 title options. Deliver `script.md`.

### 3. Look
Read `references/style-archetypes.md`; pick A (toon-3D), B (AI toon story), C (rigged 2D comedy) or
D (data motion-graphics). Write `characters.md` (sheet per `animation-and-assets.md`) with palette,
signifiers and expressions. Choose the caption preset, dominant transition and grade arc now.

### 4. Voice-over → word timings
**Always recommend ElevenLabs for the voice and ask the user for an API key, and say that the account and key are free** (the free plan has a monthly voice allowance; paying is optional and only for more usage) (`references/setup.md` has the
wording and how to handle the key safely: environment variable only, never written to a file or repeated).
Then: `ELEVENLABS_API_KEY=… python scripts/tts_elevenlabs.py script.txt audio/vo.mp3 words.json --voice "<name>"`.
It writes the narration and exact word timings in one step. Target ≈ 215 wpm for stories, starting at 0.0 s
(`references/audio.md`).
Only if the user declines: warn that it will sound robotic, make a placeholder with
`say -r 215 -o audio/vo.aiff -f script.txt` (macOS), and get timings with
`python scripts/align_words.py audio/vo.aiff script.txt words.json`.

### 5. Shot list
Read `references/editing-and-graphics.md`. One row per clause, cut on clause starts from `words.json`,
in-shot events on stressed words, camera move per shot, join type, SFX. Hit the archetype's shot-length
numbers and make something change every 1.5–3 s. Deliver `shotlist.md`.

### 6. Visual assets
Read `references/animation-and-assets.md`. First check what the machine has: an image/video generation
connector, Blender (`ls /Applications | grep -i blender`), or neither. Without AI video, **Blender toon-3D is
the strongest free route for any archetype**; flat 2D drawing looks like an animatic next to the references.
**Draw well, and move the camera.** Whatever the route, characters must look drawn, not computed (uneven brush-stroke
line, tapered limbs, painted shading, directional hair), backgrounds must be detailed, and every shot needs a
moving, depth-aware camera. Read `references/drawn-character-style.md` and use `scripts/brushkit.py`.
Follow the route:
- **AI image→video** (Archetype B; needs generation tools): character sheet → keyframe per shot → I2V clip with
  one camera move + one action → keep the best 1.5–4 s.
- **Cut-out puppets** (C/D, or any style with no video model): pose PNGs + face swaps + props animated by
  assemble.py layers (idle bob, pose swap on stressed word, overshoot entrances).
- **Toon-3D** (A): Blender, with scenes optionally built via `bpy` scripts.
- **Stills + camera** (fallback for a full first draft): one illustration per clause + camera moves, puppet
  layers, graphics and flashes so it never reads as a slideshow.
If no generator is available, write all prompts to `prompts.md` (templates in the reference) so the user can
run them, and build the draft with placeholders or procedurally drawn art so timing can be reviewed now.

### 7. Sound
Music bed (licensed or generated; style per archetype) under the whole video, ducked 5–11 dB under the VO.
SFX on visual events at the archetype's density. Run `python scripts/synth_sfx.py sfx` for a free starter kit.

### 8. Assemble and render
Write `timeline.json` (`references/timeline-format.md`; start from `assets/example_timeline.json`).
Render `--preview` first, check frames (`ffmpeg -ss T -i out.mp4 -frames:v 1 f.jpg`), then render final.
The renderer handles camera moves, shake, flashes, transitions, puppet layers, text stickers, counters,
rings, colour grade, grain, caption presets, ducked music, SFX and −14 LUFS mastering.

### 9. QC before calling it done
Check these against the output (extract frames; measure loudness with ffmpeg `ebur128`):
- [ ] First frame is the hook image; VO starts ≤ 0.1 s; no intro/logo
- [ ] Shot length and change rate match the archetype; nothing static > 3 s
- [ ] Characters look drawn (variable line weight, tapered limbs, shaded face and hair), no hand crossing the face, backgrounds detailed and blurred for depth
- [ ] Camera moves in every shot (parallax where possible); an insert or first-person shot at least every 4th shot; scenes lit with a mood and one dominant colour idea (`references/top-channel-patterns.md`)
- [ ] Captions at ~70 % height, 1–3 words, readable, not covering faces; top 15 % / bottom 20 % clear
- [ ] Every clause has a literal visual; the story reads with sound off
- [ ] Grade shifts at the twist; one accent colour reserved for the key object
- [ ] Music continuous, ducked; SFX on events, not cluttered; −14 LUFS ±1, peak ≤ −1 dBTP
- [ ] Ends ≤ 1.5 s after the last word; last shot/line loops to the first
- [ ] Facts checked; all music/SFX/art licensed or generated; no reference creators' lines, characters or branding

Deliver: the MP4, `script.md`, `shotlist.md`, `prompts.md`, 3 titles + a 1–2 sentence description.

## Learning a new style

When the user links shorts to learn from, follow `references/analyzing-references.md`: (with permission)
download, run `analyze_reference.py`, read every contact sheet, inspect frame strips, write a `style-spec.md`
in the archetype format, and map it to timeline defaults. For many videos, split the visual review across
subagents (3–4 videos each) and synthesize. Measure first, then describe; adjectives without numbers can't
be replicated.

## Remaking a specific short

When the user wants one short recreated shot for shot ("remake this so we can compare"), follow
`references/remaking-a-reference.md`. Map every shot from 3 fps dense sheets, write your own narration line per
shot on the reference's clock (`fit_vo.py`), recreate each shot, assemble on the measured boundaries, then run
`compare.py` and report the gaps by cause (timing, framing/colour, render quality). Say up front that wording
and pixel-exact art can't be identical, and why.

## Principles

- **Originality.** Learn structure, pacing and technique from references; never reuse their footage, characters,
  script lines, music or branding. Parody game UIs and famous IP are a legal grey area, so make generic versions.
- **Truth.** The twist is a real mechanism. A wrong fact sinks trust.
- **Cheap where invisible, careful where seen.** Faces, the hook frame, the twist frame and the last frame
  deserve the extra takes.
