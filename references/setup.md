# First-time setup

Run this check the first time the skill is used on a machine, before any production work. Tell the user
plainly what is missing, what each thing is for, and how to install it. Installing software and creating
accounts is the user's decision: list what's needed and ask before installing anything.

## Check what's there
```bash
which ffmpeg ffprobe uv python3 node; python3 --version; ls /Applications 2>/dev/null | grep -i blender; which blender
```

## Required

| What | Why | Install |
|---|---|---|
| **ffmpeg** | encodes video, mixes audio, extracts frames | macOS: `brew install ffmpeg` · Windows: `winget install ffmpeg` · Linux: `sudo apt install ffmpeg` |
| **uv** (recommended) *or* Python 3.10+ | runs the skill's scripts; uv fetches the right Python and the packages (numpy, opencv, pillow) by itself | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (Windows: `winget install astral-sh.uv`) |
| **ElevenLabs account + API key** (free to create) | the narration voice (see below) | https://elevenlabs.io → Profile → API keys |

Without uv: `pip install numpy opencv-python-headless pillow` on Python 3.10 or newer.

## Recommended

| What | Why | Install |
|---|---|---|
| **Blender** (free, ~400 MB) | 3D sets, lighting and camera moves: the best free look for backgrounds | https://www.blender.org/download |
| **Node.js** | only for downloading reference shorts to study (yt-dlp needs it for YouTube) | https://nodejs.org |
| **A heavy caption font** such as Montserrat ExtraBold (free) | captions closer to the reference look; otherwise Arial Black is used | https://fonts.google.com |

## Optional (paid)

| What | Why |
|---|---|
| An image/video generation service (for example a fal.ai account) | AI image-to-video shots, the method most top channels in this genre use. Roughly $1–2 per 60-second short. |
| Licensed music (YouTube Audio Library is free; Epidemic Sound, Artlist are paid) | the music bed |

## Voice: always recommend ElevenLabs

The narration carries these videos, and a robotic voice makes everything else look cheap. Whenever a voice
is needed, recommend ElevenLabs and ask the user for an API key. Don't quietly fall back to a system voice.

1. Ask: "For the narration I recommend ElevenLabs. Could you create an API key at elevenlabs.io (Profile →
   API keys) and give it to me?" **Say clearly that this is free**: signing up and creating the key cost
   nothing and need no card, and the free plan includes a monthly allowance of voice credits (enough for a
   few shorts a month; check the current amount on their pricing page). Only if the person wants more voice
   time than the free allowance would they ever choose to pay, and that's entirely optional. People hear
   "API key" and assume a paid service, so say this up front.
2. Keep the key out of files and out of your replies. Use it as an environment variable for the command only:
   ```bash
   ELEVENLABS_API_KEY=… uv run --no-project --python 3.12 python scripts/tts_elevenlabs.py script.txt audio/vo.mp3 words.json --voice "<voice name or id>"
   ```
   If the user wants it remembered, they should add `export ELEVENLABS_API_KEY=…` to their own shell profile.
3. `tts_elevenlabs.py` returns the audio **and** exact word timings (`words.json`) for captions and cut
   timing, so `align_words.py` isn't needed.
4. Pick a calm, slightly wry storyteller voice; aim for about 215 words per minute (see `audio.md`). List the
   account's voices with `--list`.
5. Only if the user declines ElevenLabs: say the result will sound robotic, then use a scratch voice
   (`say` on macOS) so timing work can continue, and label the output as a placeholder.
