#!/usr/bin/env python3
"""
Generate synthetic reference WAVs for the demo catalog.

Real deployments would ingest broadcast audio from content partners (Gracenote,
TMS, etc.) or an OTA capture rig. For a local demo we synthesize three
acoustically distinct 30-second clips so the end-to-end fingerprint match is
observable without bundling licensed audio.

The generators deliberately place energy in different parts of the spectrum
(low / mid / high) so the averaged-log-spectrum fingerprint can separate
them even without the richness of real broadcast audio.
"""

import math
import random
import struct
import wave
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "wavs"
SAMPLE_RATE = 16_000
DURATION_S = 30


def write_wav(path: Path, samples: list[int]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def clip(v: float) -> int:
    return max(-32000, min(32000, int(v * 32000)))


def generate_sportscenter() -> list[int]:
    """
    High-band dominant: 2200 Hz carrier plus fluttering overtones at 2800 and
    3400 Hz. Energy concentrated above 2 kHz so the averaged spectrum has a
    distinctive high-band tilt.
    """
    random.seed(11)
    out = []
    for n in range(SAMPLE_RATE * DURATION_S):
        t = n / SAMPLE_RATE
        primary = 0.35 * math.sin(2 * math.pi * 2200 * t)
        second = 0.22 * math.sin(2 * math.pi * 2800 * t + math.sin(2 * math.pi * 0.5 * t))
        third = 0.15 * math.sin(2 * math.pi * 3400 * t)
        noise = 0.002 * random.uniform(-1, 1)
        out.append(clip(primary + second + third + noise))
    return out


def generate_evening_news() -> list[int]:
    """
    Low-band dominant: 220 Hz fundamental with strong 2nd/3rd harmonics
    (440, 660). Mimics a broadcast voice register. Energy concentrated below
    800 Hz so the averaged spectrum is low-tilted.
    """
    random.seed(22)
    out = []
    for n in range(SAMPLE_RATE * DURATION_S):
        t = n / SAMPLE_RATE
        fundamental = 220 + 20 * math.sin(2 * math.pi * 1.2 * t)
        h1 = 0.30 * math.sin(2 * math.pi * fundamental * t)
        h2 = 0.22 * math.sin(2 * math.pi * 2 * fundamental * t)
        h3 = 0.15 * math.sin(2 * math.pi * 3 * fundamental * t)
        noise = 0.002 * random.uniform(-1, 1)
        out.append(clip(h1 + h2 + h3 + noise))
    return out


def generate_succession() -> list[int]:
    """
    Mid-band dominant: narrow band between 900 and 1400 Hz. Slow LFO sweeps
    give it a drama-like tonal evolution while keeping spectral energy in
    the middle range, distinct from both the news and sports generators.
    """
    random.seed(33)
    out = []
    for n in range(SAMPLE_RATE * DURATION_S):
        t = n / SAMPLE_RATE
        carrier1 = 900 + 80 * math.sin(2 * math.pi * 0.15 * t)
        carrier2 = 1250 + 60 * math.sin(2 * math.pi * 0.22 * t + 1.3)
        s1 = 0.28 * math.sin(2 * math.pi * carrier1 * t)
        s2 = 0.22 * math.sin(2 * math.pi * carrier2 * t)
        noise = 0.002 * random.uniform(-1, 1)
        out.append(clip(s1 + s2 + noise))
    return out


def main():
    generators = {
        "espn_sportscenter.wav": generate_sportscenter,
        "nbc_evening_news.wav": generate_evening_news,
        "succession.wav": generate_succession,
    }
    for name, gen in generators.items():
        path = OUT_DIR / name
        samples = gen()
        write_wav(path, samples)
        print(f"wrote {path}  ({len(samples) / SAMPLE_RATE:.1f}s, {len(samples) * 2} bytes)")


if __name__ == "__main__":
    main()
