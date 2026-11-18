# Sound: voice, music, SFX, mix

Measured on all 15 references (integrated loudness, word-timed narration analysis, transient detection).

## Voice-over

| | Story formats | Comedic explainer | Data explainer |
|---|---|---|---|
| Pace | **195–230 wpm** (3.3–3.8 w/s) | 168–215 wpm | ~155 wpm |
| Pauses > 0.6 s per minute | 7–13 | 14–35 (joke beats) | ~30 (number beats) |
| Longest pause | ≤ 0.9 s | ≤ 2 s (one deliberate beat) | 2.5 s |
| Voice | calm, slightly wry storyteller; many are AI/TTS voices | characterful human persona (accent is fine) | upbeat host |

- Starts at **0.0 s**. Trim every millisecond of leading silence.
- Delivery: conversational, confident, a touch of irony on the twist; slight slow-down on the "You see," line
  and the final callback (that's where meaning lands). Character dialogue lines get a different voice or a
  pitch/tone shift, never a long pause.
- TTS is accepted by the audience in this genre (the top-performing channel uses one). Pick a natural,
  low-mid male or female narrator voice, speed 1.05–1.15×, stability medium. Generate the whole script in one
  pass for consistent prosody, then tighten gaps > 0.4 s in an editor if needed.
- Scratch VO for timing (free, offline, macOS): `say -r 215 -o vo.aiff -f script.txt`.
- Record/export at 48 kHz; high-pass ~80 Hz, gentle compression (3:1), de-ess.

## Music

- **Continuous bed under the entire video** (silence share measured: 0.0–0.6 %). Music never stops for effect;
  a beat of quiet comes from SFX/VO pauses, not from cutting the bed.
- Level: the bed sits **5–11 dB under the voice** (median measured ≈ 8 dB; one data-explainer channel ran a loud
  bed at only ~4 dB under). Duck under VO with a sidechain (assemble.py does this: `"duck":true`).
- Character by style:
  - Toon-3D / process explainers: orchestral or fantasy game-score underscore (one reference credits
    a fantasy-MMO soundtrack under a fan-content licence), steady mid-tempo.
  - AI toon stories: light, curious, pizzicato/marimba/plucked-synth "storytelling" beds that turn darker
    (low strings, drones) at the twist. One track per video, optionally a second for the twist.
  - Comedic history: playful/ironic underscore with comic stings; period-flavoured instruments help
    (fife/drum, brass) and short meme/game stings for gags.
  - Data/challenge: ticking, pulsing electronic beds that build tension toward the deadline.
- Source **only licensed music**: YouTube Audio Library, Pixabay Music, Epidemic/Artlist subscriptions, or
  AI-generated music you have rights to. Game soundtracks only under that publisher's fan-content policy, with
  credit in the description. Copyrighted pop songs get Shorts muted or demonetised.
- Switch or swell music at the twist (where the grade changes): same moment, same function.

## Sound effects

Measured transient density (whooshes/pops/clicks = high; booms/thuds = low), per 10 s:

| Style | High (whoosh/pop/click) | Low (boom/thud) |
|---|---|---|
| Twist-tale stories with sticker graphics | **3.3–3.4** | 1–2 |
| AI story, smooth dissolves | 0.7–1.7 | 0–0.9 |
| Toon-3D slow explainer | 0–0.6 | 0.3–1.1 |
| Comedic 2D | 0.1–1.0 (+ comic stings) | 0.5–1.1 |
| Data explainer | 1.6 | 1.3 |

So: **one SFX accent every 3–6 s** in calm styles, **every 1.5–3 s** in punchy ones. Never two big ones
on top of each other.

**Update (10 latest shorts of a top channel):** their sound effects were lighter than the table above,
about 0.3–1.5 accents per 10 s, with every short mastered at exactly −14.0 LUFS. When in doubt, use fewer effects
and put them on impacts and reveals only (`top-channel-patterns.md`).

Where they go (always on the frame of the visual event):
- whoosh / whoosh_short → whip pans, fast entrances, camera rushes
- pop / bubble_pop → label, sticker, caption-emphasis and character pop-ins
- thud / impact_hit / boom → stamps, landings, slams, explosions (+ shake + flash)
- riser → the 1–2 s before the twist/reveal; cut it dead on the reveal frame
- ding / cash / sparkle → realisations, money, "perfect" moments
- tick / typewriter / camera_shutter → time, documents, evidence
- record_scratch / glitch → comic interruption, "wait, what?"
- heartbeat → tension
- Foley in the scene (saw rasp, gunshot, water hiss) sells AI/3D footage more than any music.

`scripts/synth_sfx.py` generates a royalty-free starter kit of all of the above.

## Mix & master

- Integrated loudness **−14 LUFS**, true peak ≤ −1 dBTP (13 of 15 references: −14.0 ± 0.7 LUFS; loudness
  range only 1.6–3.8 LU — these are dense, compressed mixes).
- VO 0 dB reference; music −16 to −22 dB before ducking; SFX −4 to −10 dB (big impacts can touch the VO level).
- No fade-in. Music cuts with the final frame or fades over ≤ 0.6 s; a hard end loops better.
- assemble.py mixes VO + ducked music + SFX and applies `loudnorm` to −14 LUFS.
