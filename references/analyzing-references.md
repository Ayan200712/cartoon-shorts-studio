# Learning a new style from reference shorts

Use this when the user hands you shorts to copy that don't match the four archetypes, or wants a channel's
exact look. The goal is a **numbers + observations spec** someone could replicate, not adjectives.

## 1. Get the files (ask first)

Downloading is the user's call: say which URLs, roughly how big (5–15 MB per short), and where they'll go.
With permission, yt-dlp (needs a recent Python; `uvx` handles that) downloads the video, metadata and
word-timed auto-captions:

```bash
mkdir -p refs && cd refs
uvx --python 3.12 --from "yt-dlp[default]" yt-dlp --js-runtimes node \
  -f "bv*[height<=1080]+ba/b" --merge-output-format mp4 --write-info-json \
  --write-auto-subs --sub-langs "en-orig,en" --sub-format vtt -o "%(id)s.%(ext)s" URL1 URL2 …
```
YouTube rate-limits caption requests (HTTP 429): if captions fail, retry those IDs alone with
`--skip-download` after a pause (sleep 10–20 s between calls). If no captions, burned-in subtitles in the
contact sheets give you the script; or run `align_words.py --whisper` on the audio (asks to download a model).

Alternatives when downloading isn't possible: a video-analysis connector (e.g. a "watch short-form video"
tool) if the session has one, or the user's own screen recordings.

## 2. Measure

```bash
uv run --no-project --python 3.12 --with numpy --with opencv-python-headless \
  python scripts/analyze_reference.py refs analysis
```

How to read `analysis/<id>/report.json`:

| Field | Meaning | Interpretation |
|---|---|---|
| `video.cut_count`, `cut_times` | hard cuts | misses dissolves and whip pans |
| `video.soft_transition_count` | dissolves/morphs estimate | puppet-heavy videos over-count (smoke fills); verify on contact sheets |
| `video.total_shots_est`, `shot_len_incl_soft_mean_s` | real pacing estimate | cross-check by counting setups in the sheets |
| `video.repeat_frame_share` | share of frames identical to previous | ≈0 → smooth 30 fps (rig, 3D or AI); 0.4–0.6 → animated on twos; high + long runs → stills/limited |
| `video.small_local_change_share` | frames with only small parts moving | 0.5–0.75 → puppet/rig animation on mostly static backgrounds |
| `video.big_change_share` | frames where >25 % of pixels change | 0.1–0.4 with few cuts → AI video or constant camera motion |
| `video.camera_pan_frame_fraction`, `shake_flip_events` | global motion | camera energy |
| `video.flash_frames` | brightness spikes | white flashes (or bright hard cuts — check) |
| `video.palette`, `saturation_mean`, `brightness_mean` | colour | 8-colour k-means palette with shares |
| `audio.*` | loudness, onset density, band balance | |
| `narration.wpm`, `speech_starts_at_s`, `speech_coverage`, `longest_pause_s` | VO pacing | |
| `narration.speech_over_bed_db` | voice vs music gap level | how hard music is ducked |
| `narration.sfx_high/low_per_10s` | whoosh-pop / boom-thud density | sound-design busyness |
| `narration.first_sentence`, `last_sentence`, `full_text` | script | hook / loop analysis (don't copy lines) |

Also measure loudness: `ffmpeg -nostats -i x.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:"`.

## 3. Look

Read every `sheet_NN.jpg` (frame every 0.5 s, timestamped). For motion questions, pull consecutive frames:
`ffmpeg -v quiet -ss 12.0 -i x.mp4 -frames:v 8 -vf scale=304:540,tile=8x1 strip.jpg`. Check 3–5 moments per
video: a gesture, a cut, a camera move, a text pop, the first and last 3 s.

Decide the **technique** with evidence:
- **Rig/puppet**: perfectly stable line art; rigid parts rotating about joints; pose swaps in 1–2 frames;
  high small_local_change_share.
- **Frame-by-frame**: line boil, shapes redrawn each drawing, repeats on twos.
- **AI video**: morphing details (labels fading, hands/hair changing), garbled small text with crisp large text,
  faces drifting between shots, 5–8 s generation lengths trimmed to 1.5–4 s, soft dissolves hiding joins.
- **3D render**: exact object permanence, numerically exact in-scene counters, the same pose re-rendered in
  different sets, material swaps (X-ray), rigid-body splits.
- **Stills + camera**: big_change only during moves, nothing moves within the image.

## 4. Write the spec

Produce `style-spec.md` with the same headings as an archetype in `style-archetypes.md`: characters, world,
motion, edit (numbers), graphics, captions (font class, case, size as % of height, position, stroke, pop),
colour/grade arc, audio (wpm, bed level, SFX density, LUFS), hook and ending, and a ranked top-10 technique
list. Then map it onto a `timeline.json` caption preset/transition/camera defaults so the next video uses it.

Respect the creators: learn structure, pacing and technique — never re-use their footage, characters, lines,
or channel branding.
