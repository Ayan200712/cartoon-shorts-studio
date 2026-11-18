# Cartoon Shorts Studio

A skill for Claude that helps you plan, write, animate, edit and sound-design **original animated cartoon
Shorts**: the vertical story and explainer cartoons you see on YouTube Shorts, TikTok and Reels.

It was built from a measured study of 25 top animated shorts (pacing, camera, colour, captions, sound and
scripts), so Claude works from real numbers, not guesses.

## What it does
- **Writes the script** using proven story shapes: a strange first line, a twist, a plain-language
  explanation, and an ending that loops back to the start.
- **Plans every shot** to the narration, with camera moves, transitions and captions.
- **Draws characters and backgrounds** in a hand-drawn brush-stroke look, with a depth camera that moves
  like a drone shot.
- **Makes the voice** with ElevenLabs, with exact word timing for captions.
- **Assembles the video** (captions, music, sound effects, loudness) with the included renderer.
- **Studies any short you give it** and measures how it was made.

## Install
- **Claude.ai or the Claude desktop app:** download `cartoon-shorts-studio.skill` from the
  [Releases](../../releases) page (or from this page), then go to Settings → Capabilities → Skills → upload it.
- **Claude Code:** put this folder at `~/.claude/skills/cartoon-shorts-studio/`.

Then ask: *"Make me a 60-second animated short about why ship portholes are round."*

## What you need on your computer
Claude checks this the first time and tells you what is missing. Details: `references/setup.md`.

| Needed | What for |
|---|---|
| ffmpeg | making the video and mixing audio (required) |
| uv, or Python 3.10+ | running the scripts (required) |
| ElevenLabs account and API key | the narration voice. **The account and key are free to create**; the free plan includes a monthly allowance of voice credits, and paying is optional. |
| Blender (free) | 3D backgrounds and camera moves (recommended) |
| Node.js | only to study reference videos from YouTube |

## Good to know
- The skill runs Python scripts on your computer. As with any skill, skim them before installing.
- Your ElevenLabs key is used only for the command that needs it; the skill is written never to save it to a
  file or repeat it.
- Learn structure and technique from other creators, but never re-upload their footage or copy their
  characters, scripts or branding. Use licensed or generated music, art and voices.

## Licence
MIT. See `LICENSE`. Free to use, change and share.
