"""Turn record-demo.mjs's frames and events into an MP4 with click sounds.

    python assemble-demo.py <recording-dir> <out.mp4> <ffmpeg>

Frames are resampled to a constant 30 fps by their own timestamps. The sounds
are synthesised here, so the video carries no third-party audio: a soft click
per click, a quiet tick per key, and a low tick when a tab's data lands. No
music. Peaks stay under -6 dBFS.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import wave

import numpy as np

FPS = 30
RATE = 48_000
HOLD = 0.6  # seconds the last frame stays before the fade ends the video
FADE = 0.4


def _envelope(n: int, decay: float) -> np.ndarray:
    t = np.arange(n) / RATE
    return np.exp(-t / decay)


def click(rng: np.random.Generator) -> np.ndarray:
    """A short, dry mouse click: a noise transient and a damped body."""
    n = int(0.035 * RATE)
    t = np.arange(n) / RATE
    noise = rng.standard_normal(n) * _envelope(n, 0.0018)
    body = np.sin(2 * np.pi * 2300 * t) * _envelope(n, 0.006) * 0.6
    low = np.sin(2 * np.pi * 180 * t) * _envelope(n, 0.01) * 0.35
    return (noise * 0.5 + body + low) * 0.32


def key(rng: np.random.Generator) -> np.ndarray:
    """A quiet keyboard tick, varied a little so typing does not sound looped."""
    n = int(0.02 * RATE)
    t = np.arange(n) / RATE
    pitch = rng.uniform(1500, 2100)
    noise = rng.standard_normal(n) * _envelope(n, 0.0012)
    body = np.sin(2 * np.pi * pitch * t) * _envelope(n, 0.003)
    return (noise * 0.6 + body * 0.5) * 0.11


def tick() -> np.ndarray:
    """A barely-there soft tone when a section's data has landed."""
    n = int(0.09 * RATE)
    t = np.arange(n) / RATE
    attack = np.minimum(1.0, t / 0.004)
    return np.sin(2 * np.pi * 1320 * t) * attack * _envelope(n, 0.025) * 0.06


def main(src: str, out: str, ffmpeg: str) -> None:
    with open(os.path.join(src, "frames.json")) as fh:
        frames = json.load(fh)
    with open(os.path.join(src, "events.json")) as fh:
        events = json.load(fh)
    frames.sort(key=lambda f: f["t"])
    t0 = frames[0]["t"]
    end = max(frames[-1]["t"], max((e["t"] for e in events), default=t0)) + HOLD
    duration = end - t0
    count = int(duration * FPS)

    # Constant frame rate: each output frame shows the latest captured frame.
    seq = os.path.join(src, "seq")
    os.makedirs(seq, exist_ok=True)
    index = 0
    for i in range(count):
        at = t0 + i / FPS
        while index + 1 < len(frames) and frames[index + 1]["t"] <= at:
            index += 1
        link = os.path.join(seq, f"{i:06d}.jpg")
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(os.path.abspath(os.path.join(src, "frames", frames[index]["file"])), link)

    rng = np.random.default_rng(7)
    track = np.zeros(int(duration * RATE) + RATE, dtype=np.float64)
    for event in events:
        sound = {"click": lambda: click(rng), "key": lambda: key(rng), "tick": tick}[event["kind"]]()
        start = int((event["t"] - t0) * RATE)
        if 0 <= start < len(track):
            stop = min(len(track), start + len(sound))
            track[start:stop] += sound[: stop - start]
    peak = np.max(np.abs(track)) or 1.0
    track = track * min(1.0, 0.5 / peak)  # -6 dBFS ceiling
    audio = os.path.join(src, "audio.wav")
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes((track * 32767).astype("<i2").tobytes())

    video_end = count / FPS
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            os.path.join(seq, "%06d.jpg"),
            "-i",
            audio,
            "-vf",
            f"fade=t=in:st=0:d={FADE},fade=t=out:st={video_end - FADE:.3f}:d={FADE},format=yuv420p",
            "-af",
            f"afade=t=out:st={video_end - FADE:.3f}:d={FADE}",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-t",
            f"{video_end:.3f}",
            "-movflags",
            "+faststart",
            out,
        ],
        check=True,
    )
    print(f"{out}: {video_end:.1f} s, {count} frames, {len(events)} sounds")


if __name__ == "__main__":
    main(*sys.argv[1:4])
