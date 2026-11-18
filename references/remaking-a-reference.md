# Remaking a reference short shot-for-shot (and measuring the gap)

Use when the user wants a specific short recreated as a study ("remake this frame for frame so we can
compare"). The goal is a remake whose **timing, structure, framing, colour, captions and sound** match,
plus an honest, measured report of what still differs and why.

Ground rules:
- It's a private study. Don't publish it, and say so.
- Don't reproduce the creator's narration word for word. Write your own line for each shot with the same
  beat, word budget and timing. (Facts aren't owned. Wording is.) Captions then match in cadence, size
  and position, not in exact text.
- Don't reuse their frames, audio or music as material. Recreate them.
- Pixel-identical is impossible without the creator's source assets and models. Aim for "same shot, same
  moment, same look", and measure.

## 1. Measure the reference
```bash
uv run --no-project --python 3.12 --with numpy --with opencv-python-headless python scripts/analyze_reference.py refdir analysis
uv run --no-project --python 3.12 --with numpy --with opencv-python-headless python scripts/shot_map.py ref.mp4 map
ffmpeg -i ref.mp4 -vf "fps=3,scale=160:284,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=14:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=7x5" dense_%02d.jpg
```
`shot_map.py` gives candidate boundaries, motion per shot and keyframes. AI-video shorts hide joins with
6–9-frame dissolves and constant camera motion, so automatic detection undercounts. **Build the final shot
list by eye from the 3 fps dense sheets**, then snap each boundary to the nearest peak of the change curve.
Expect ~25–30 shots per minute in the AI toon-story style.

For each shot write: start–end, framing (wide/medium/close/insert/top-down), subject and pose changes
with times, camera move (push/pull/pan/tilt and roughly how much), the transition in, grade, and any in-shot
event (prop flip, light change, character entering).

Get the narration timing from word-level captions (`yt-dlp --write-auto-subs`, format VTT with `<c>` tags). Count
words per shot. That's your word budget per line.

## 2. Narration on the reference clock
Write one line per shot (same beats, same word budget, your own words). Build it with
`scripts/fit_vo.py`: each line is synthesized (or a supplied TTS clip), trimmed, time-stretched to the
reference's speech window for that shot, and placed at the same start. It reports lines that are too long;
shorten them, or merge two tiny windows into one line.

## 3. Art
Pick the production route (see `animation-and-assets.md`). With image/video generation, write one keyframe
prompt per shot from the reference keyframes (framing, characters, props, signage, grade) plus one motion
prompt (the measured camera move + one action). Without generation, draw sets and characters in code
(supersampled PIL) and animate them as puppet layers. That gets timing, framing and palette but not the
rendered 3D look or organic AI motion.

Details that are easy to miss and do matter:
- Costume changes across the story (dressed-up for the payoff scene).
- Recurring props and in-world callbacks (a photo of an earlier scene pinned on the evidence board).
- Who the undercover character is dressed as in the reveal.
- The last shot mirrors the first for the loop.

## 4. Assemble on the same clock
Use the measured boundaries as shot start/end in `timeline.json`, set `"layer_space": "world"` so characters
move with camera pushes, match transitions per shot, match caption preset/size/position, put SFX at the
reference's measured transient times, set the music bed level from `speech_over_bed_db`, master to the
reference's LUFS.

## 5. Compare
```bash
uv run --no-project --python 3.12 --with numpy --with opencv-python-headless python scripts/compare.py ref.mp4 remake.mp4 cmp
```
It writes a side-by-side video (left ear is the reference, right ear is the remake), paired frames every
second, and a report:

| Metric | What "close" looks like |
|---|---|
| scene-change alignment | ≥ 85 % of reference changes within 0.2 s, median offset ≤ 2 frames |
| mean motion | within ±25 % (AI video moves more than puppets: add drift/idle) |
| saturation / brightness | within ±8 |
| colour delta (LAB, per-second average colour) | < 12 good, 12–20 noticeable, > 20 different look |
| layout correlation (blurred greyscale) | > 0.6 same composition; < 0.3 means different framing/art |
| LUFS / peak | within ±1 LU |

Read the pairs sheets. Fix framing and scale problems first (characters too big or too small are the most
common), then colour/grade, then motion. Report the remaining gaps by cause: **timing/structure** (skill),
**framing/colour** (skill and effort), **render quality and organic motion** (tooling: needs image/video
generation or a 3D pipeline).
