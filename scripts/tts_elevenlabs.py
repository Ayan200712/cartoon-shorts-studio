#!/usr/bin/env python3
"""Narration with ElevenLabs: writes the audio and word-level timings for captions.

  ELEVENLABS_API_KEY=... python scripts/tts_elevenlabs.py script.txt vo.mp3 words.json [--voice NAME_OR_ID] [--model eleven_multilingual_v2] [--speed 1.1]
  ELEVENLABS_API_KEY=... python scripts/tts_elevenlabs.py --list

The key is read from the environment only; never put it in a file. Standard library only.
"""
import base64, json, os, sys, urllib.request, urllib.error

API = "https://api.elevenlabs.io/v1"


def call(path, key, body=None):
    req = urllib.request.Request(API + path, headers={"xi-api-key": key, "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        return json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs error {e.code}: {e.read().decode(errors='replace')[:400]}")


def main():
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("Set ELEVENLABS_API_KEY (create one at elevenlabs.io > Profile > API keys).")
    args = sys.argv[1:]
    voices = call("/voices", key).get("voices", [])
    if "--list" in args:
        for v in voices:
            print(f"{v['voice_id']}  {v['name']}  {v.get('labels', {})}")
        return
    opt = lambda f, d=None: args[args.index(f) + 1] if f in args else d
    script, out_audio, out_words = args[0], args[1], args[2]
    want = opt("--voice")
    vid = next((v["voice_id"] for v in voices if want and (v["voice_id"] == want or v["name"].lower().startswith(want.lower()))), None)
    if not vid:
        if not voices:
            sys.exit("No voices on this account.")
        vid = voices[0]["voice_id"]
        print(f"voice not specified/found; using {voices[0]['name']}")
    text = " ".join(open(script, encoding="utf-8").read().split())
    body = {"text": text, "model_id": opt("--model", "eleven_multilingual_v2"),
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "speed": float(opt("--speed", "1.1"))}}
    r = call(f"/text-to-speech/{vid}/with-timestamps", key, body)
    open(out_audio, "wb").write(base64.b64decode(r["audio_base64"]))
    al = r.get("alignment") or {}
    chars, st, en = al.get("characters", []), al.get("character_start_times_seconds", []), al.get("character_end_times_seconds", [])
    words, cur, t0, t1 = [], "", None, None
    for c, a, b in zip(chars, st, en):
        if c.isspace():
            if cur:
                words.append({"w": cur, "t": round(t0, 3), "end": round(t1, 3)}); cur = ""
            continue
        if not cur:
            t0 = a
        cur += c; t1 = b
    if cur:
        words.append({"w": cur, "t": round(t0, 3), "end": round(t1, 3)})
    json.dump(words, open(out_words, "w"), indent=0)
    dur = words[-1]["end"] if words else 0
    print(f"wrote {out_audio} ({dur:.1f}s, {len(words)} words, {len(words) / max(dur, 1e-6) * 60:.0f} wpm) and {out_words}")


if __name__ == "__main__":
    main()
