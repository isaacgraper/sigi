"""Turn record-demo.mjs's frames and events into a calm product video.

    python assemble-demo.py <recording-dir> <out.mp4> <ffmpeg>

Picture: frames are resampled to a constant 30 fps by their own timestamps, and
a virtual camera eases between the recorder's focus keyframes, zooming gently
into what the cursor points at and back out before every scroll or tab.

Sound: soft and rounded rather than mechanical, in the manner of modern
product films, and synthesised here so the video carries no third-party
audio. A warm pop per click, muted ticks while typing, an airy whoosh per
scroll, a two-note chime when a section's data lands, and a short room reverb
over everything. No music. Peaks stay under -6 dBFS.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image

FPS = 30
RATE = 48_000
WIDTH, HEIGHT = 1920, 1080
HOLD = 0.8  # seconds held after the last event, inside the fade
FADE = 0.5
CAMERA = 1.0  # seconds for each camera move
RNG = np.random.default_rng(7)


# ── Sound ────────────────────────────────────────────────────────────────────


def _lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    alpha = 1 - np.exp(-2 * np.pi * cutoff / RATE)
    out = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        out[i] = acc
    return out


def _attack_decay(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / RATE
    rise = np.where(t < attack, 0.5 - 0.5 * np.cos(np.pi * t / attack), 1.0)
    return rise * np.exp(-np.maximum(0, t - attack) / decay)


def pop() -> np.ndarray:
    """A warm, rounded click: a sine that drops a little in pitch, no transient."""
    n = int(0.18 * RATE)
    t = np.arange(n) / RATE
    freq = 360 + 180 * np.exp(-t / 0.02)
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    tone = np.sin(phase) + 0.18 * np.sin(2 * phase)
    return tone * _attack_decay(n, 0.004, 0.045) * 0.30


def key() -> np.ndarray:
    """A muted keystroke: a breath of filtered noise with a faint low body."""
    n = int(0.03 * RATE)
    t = np.arange(n) / RATE
    noise = _lowpass(RNG.standard_normal(n), RNG.uniform(1400, 2000))
    body = np.sin(2 * np.pi * RNG.uniform(700, 900) * t)
    return (noise * 1.6 + body * 0.25) * _attack_decay(n, 0.0015, 0.007) * 0.05


def whoosh() -> np.ndarray:
    """Air moving past: band-limited noise that swells and settles."""
    n = int(0.5 * RATE)
    t = np.arange(n) / RATE
    noise = RNG.standard_normal(n)
    band = _lowpass(noise, 1500) - _lowpass(noise, 250)
    shape = np.sin(np.pi * t / t[-1]) ** 2
    return band * shape * 0.07


def chime() -> np.ndarray:
    """Two soft bell notes a fifth apart, the second a breath after the first."""
    n = int(0.9 * RATE)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    for freq, delay, gain in ((784.0, 0.0, 0.055), (1174.7, 0.07, 0.04)):
        start = int(delay * RATE)
        tt = t[: n - start]
        tone = np.sin(2 * np.pi * freq * tt) + 0.2 * np.sin(2 * np.pi * 2 * freq * tt)
        out[start:] += tone * _attack_decay(n - start, 0.006, 0.22) * gain
    return out


SOUNDS = {"click": pop, "key": key, "whoosh": whoosh, "chime": chime}


def reverb(dry: np.ndarray) -> np.ndarray:
    """A small, dark room: convolve with decaying low-passed noise, mix 22 % wet."""
    n = int(0.7 * RATE)
    ir = _lowpass(RNG.standard_normal(n), 3000) * np.exp(-np.arange(n) / RATE / 0.18)
    ir /= np.sqrt(np.sum(ir**2))
    size = 1 << int(np.ceil(np.log2(len(dry) + n)))
    wet = np.fft.irfft(np.fft.rfft(dry, size) * np.fft.rfft(ir, size), size)[: len(dry)]
    return dry + wet * 0.22


# ── Picture ──────────────────────────────────────────────────────────────────


def _ease(p: float) -> float:
    return 4 * p**3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def camera_path(focus: list[dict], t0: float, count: int) -> list[tuple[float, float, float]]:
    """The camera (x, y, zoom) per output frame, easing between keyframes."""
    state = (WIDTH / 2, HEIGHT / 2, 1.0)
    origin, target, began = state, state, -1.0
    keyframes = sorted(focus, key=lambda e: e["t"])
    k = 0
    path = []
    for i in range(count):
        at = t0 + i / FPS
        while k < len(keyframes) and keyframes[k]["t"] <= at:
            origin, began = state, keyframes[k]["t"]
            target = (keyframes[k]["x"], keyframes[k]["y"], keyframes[k]["zoom"])
            k += 1
        p = 1.0 if began < 0 else min(1.0, (at - began) / CAMERA)
        e = _ease(p)
        state = tuple(o + (g - o) * e for o, g in zip(origin, target, strict=True))
        path.append(state)
    return path


def framed(image: Image.Image, x: float, y: float, zoom: float) -> Image.Image:
    w, h = WIDTH / zoom, HEIGHT / zoom
    cx = min(max(x, w / 2), WIDTH - w / 2)
    cy = min(max(y, h / 2), HEIGHT - h / 2)
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS, box=box)


# ── Assembly ─────────────────────────────────────────────────────────────────


def main(src: str, out: str, ffmpeg: str) -> None:
    with open(os.path.join(src, "frames.json")) as fh:
        frames = sorted(json.load(fh), key=lambda f: f["t"])
    with open(os.path.join(src, "events.json")) as fh:
        events = json.load(fh)
    t0 = frames[0]["t"]
    end = max(frames[-1]["t"], max(e["t"] for e in events)) + HOLD
    count = int((end - t0) * FPS)

    path = camera_path([e for e in events if e["kind"] == "focus"], t0, count)
    seq = os.path.join(src, "seq-camera")
    os.makedirs(seq, exist_ok=True)
    index, cached = 0, None
    for i in range(count):
        at = t0 + i / FPS
        while index + 1 < len(frames) and frames[index + 1]["t"] <= at:
            index += 1
        if cached is None or cached[0] != index:
            cached = (index, Image.open(os.path.join(src, "frames", frames[index]["file"])).convert("RGB"))
        framed(cached[1], *path[i]).save(os.path.join(seq, f"{i:06d}.jpg"), quality=93)

    duration = count / FPS
    track = np.zeros(int(duration * RATE) + RATE)
    for event in events:
        make = SOUNDS.get(event["kind"])
        if make is None:
            continue
        sound = make()
        start = int((event["t"] - t0) * RATE)
        if 0 <= start < len(track):
            stop = min(len(track), start + len(sound))
            track[start:stop] += sound[: stop - start]
    track = reverb(track)
    track *= min(1.0, 0.5 / (np.max(np.abs(track)) or 1.0))  # -6 dBFS ceiling
    audio = os.path.join(src, "audio-soft.wav")
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes((track * 32767).astype("<i2").tobytes())

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            str(FPS),
            "-i",
            os.path.join(seq, "%06d.jpg"),
            "-i",
            audio,
            "-vf",
            f"fade=t=in:st=0:d={FADE},fade=t=out:st={duration - FADE:.3f}:d={FADE},format=yuv420p",
            "-af",
            f"afade=t=out:st={duration - FADE:.3f}:d={FADE}",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "17",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{duration:.3f}",
            "-movflags",
            "+faststart",
            out,
        ],
        check=True,
    )
    print(f"{out}: {duration:.1f} s, {count} frames, {len(events)} events")


if __name__ == "__main__":
    main(*sys.argv[1:4])
