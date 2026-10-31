"""Mix microphone and loopback audio into mono 16 kHz PCM."""

from __future__ import annotations

import numpy as np


def mix_to_mono(system: np.ndarray, mic: np.ndarray) -> np.ndarray:
    """Mix two float32 streams, padding the shorter one so neither is truncated."""
    if len(system) == 0 and len(mic) == 0:
        return np.zeros(0, dtype=np.float32)
    if len(system) == 0:
        return mic.astype(np.float32)
    if len(mic) == 0:
        return system.astype(np.float32)

    length = max(len(system), len(mic))
    s = np.zeros(length, dtype=np.float32)
    m = np.zeros(length, dtype=np.float32)
    s[: len(system)] = system.astype(np.float32)
    m[: len(mic)] = mic.astype(np.float32)

    # Slightly favor system/meeting audio so remote speakers aren't drowned out by mic noise.
    mixed = (s * 1.15) + (m * 0.95)
    peak = float(np.max(np.abs(mixed)) or 1.0)
    if peak > 1.0:
        mixed = mixed / peak
    return mixed


def resample_simple(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or len(audio) == 0:
        return audio.astype(np.float32)
    ratio = dst_rate / src_rate
    new_len = int(len(audio) * ratio)
    if new_len <= 0:
        return np.zeros(0, dtype=np.float32)
    x_old = np.linspace(0, 1, len(audio), endpoint=False)
    x_new = np.linspace(0, 1, new_len, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)
