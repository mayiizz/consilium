"""Capture system loopback + microphone via sounddevice."""

from __future__ import annotations

import platform
import queue
import threading
import time
from typing import Callable, Optional, Tuple

import numpy as np
import sounddevice as sd

from desktop.mixer import mix_to_mono, resample_simple

TARGET_RATE = 16000
CHUNK_SECONDS = 2
SAMPLES_NEEDED = TARGET_RATE * CHUNK_SECONDS

_LOOPBACK_HINTS = (
    "blackhole",
    "soundflower",
    "loopback",
    "vb-audio",
    "cable",
    "monitor",
    "multi-output",
    "aggregate",
)


def _device_name(idx: Optional[int]) -> str:
    if idx is None:
        return "none"
    try:
        return str(sd.query_devices()[idx]["name"])
    except Exception:
        return f"#{idx}"


def _pick_devices() -> Tuple[Optional[int], Optional[int]]:
    """Pick mic (default input) + system loopback (BlackHole / Multi-Output / etc.)."""
    devices = sd.query_devices()
    system_idx: Optional[int] = None
    mic_idx: Optional[int] = None

    try:
        default_in = sd.default.device[0]
        if isinstance(default_in, int) and default_in >= 0:
            info = devices[default_in]
            if int(info.get("max_input_channels", 0)) >= 1:
                mic_idx = default_in
    except Exception:
        pass

    loopback_candidates: list[tuple[int, int]] = []
    for i, d in enumerate(devices):
        name = str(d.get("name", "")).lower()
        max_in = int(d.get("max_input_channels", 0))
        if max_in < 1:
            continue
        if mic_idx is None and ("mic" in name or "input" in name or "built-in" in name):
            mic_idx = i

        score = 0
        if "blackhole" in name:
            score = 100
        elif any(h in name for h in _LOOPBACK_HINTS):
            score = 80
        if score and i != mic_idx:
            loopback_candidates.append((score, i))

    if loopback_candidates:
        loopback_candidates.sort(reverse=True)
        system_idx = loopback_candidates[0][1]

    if mic_idx is None:
        for i, d in enumerate(devices):
            if int(d.get("max_input_channels", 0)) >= 1 and i != system_idx:
                mic_idx = i
                break

    if system_idx is not None and system_idx == mic_idx:
        system_idx = next((i for _, i in loopback_candidates if i != mic_idx), None)

    return system_idx, mic_idx


class AudioCapture:
    def __init__(self, on_chunk: Callable[[np.ndarray], None]) -> None:
        self.on_chunk = on_chunk
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.system_idx, self.mic_idx = _pick_devices()

    def start(self) -> None:
        print(
            f"[agent] Audio devices — mic={self.mic_idx}:{_device_name(self.mic_idx)} "
            f"loopback={self.system_idx}:{_device_name(self.system_idx)}"
        )
        if self.system_idx is None:
            print(
                "[agent] WARNING: No system-audio loopback found (BlackHole / Multi-Output). "
                "Only the microphone will be transcribed. "
                "Install BlackHole 2ch, create a Multi-Output Device (Speakers + BlackHole) "
                "in Audio MIDI Setup, set it as system output, then restart the daemon."
            )
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _open_input(self, device: int, callback) -> tuple[Optional[sd.InputStream], int]:
        try:
            info = sd.query_devices(device)
            native = int(info.get("default_samplerate") or TARGET_RATE)
            max_in = int(info.get("max_input_channels") or 1)
            channels = 1 if max_in < 2 else 2
        except Exception:
            native = TARGET_RATE
            channels = 1

        last_err: Optional[Exception] = None
        for attempt_rate in (TARGET_RATE, native, 48000, 44100):
            try:
                stream = sd.InputStream(
                    device=device,
                    channels=channels,
                    samplerate=attempt_rate,
                    blocksize=max(int(attempt_rate // 10), 256),
                    dtype="float32",
                    callback=callback,
                )
                stream.start()
                print(f"[agent] Opened device {device} ({_device_name(device)}) @ {attempt_rate}Hz ch={channels}")
                return stream, attempt_rate
            except Exception as exc:
                last_err = exc
        print(f"[agent] Failed to open device {device}: {last_err}")
        return None, TARGET_RATE

    def _run(self) -> None:
        sys_q: queue.Queue[np.ndarray] = queue.Queue()
        mic_q: queue.Queue[np.ndarray] = queue.Queue()
        rates = {"sys": TARGET_RATE, "mic": TARGET_RATE}

        def to_mono(indata: np.ndarray) -> np.ndarray:
            if indata.ndim == 1:
                return indata.astype(np.float32).reshape(-1)
            return indata.mean(axis=1).astype(np.float32)

        def sys_cb(indata, _frames, _time, status):
            if status:
                print(f"[agent] loopback status: {status}")
            sys_q.put(to_mono(indata.copy()))

        def mic_cb(indata, _frames, _time, status):
            if status:
                print(f"[agent] mic status: {status}")
            mic_q.put(to_mono(indata.copy()))

        streams: list[sd.InputStream] = []
        try:
            if self.mic_idx is not None:
                mic_stream, mic_hz = self._open_input(self.mic_idx, mic_cb)
                if mic_stream is not None:
                    streams.append(mic_stream)
                    rates["mic"] = mic_hz
                else:
                    self.mic_idx = None

            if self.system_idx is not None:
                sys_stream, sys_hz = self._open_input(self.system_idx, sys_cb)
                if sys_stream is not None:
                    streams.append(sys_stream)
                    rates["sys"] = sys_hz
                else:
                    self.system_idx = None

            if not streams:
                print("[agent] No audio devices available. Check mic permissions for Terminal/Python.")
                return

            buffer_sys = np.zeros(0, dtype=np.float32)
            buffer_mic = np.zeros(0, dtype=np.float32)
            chunks_emitted = 0
            last_warn = 0.0
            both = self.mic_idx is not None and self.system_idx is not None

            while not self._stop.is_set():
                got = False
                while not sys_q.empty():
                    chunk = sys_q.get()
                    if rates["sys"] != TARGET_RATE:
                        chunk = resample_simple(chunk, rates["sys"], TARGET_RATE)
                    buffer_sys = np.concatenate([buffer_sys, chunk])
                    got = True
                while not mic_q.empty():
                    chunk = mic_q.get()
                    if rates["mic"] != TARGET_RATE:
                        chunk = resample_simple(chunk, rates["mic"], TARGET_RATE)
                    buffer_mic = np.concatenate([buffer_mic, chunk])
                    got = True

                if both:
                    # Emit when both sides have enough samples for a stable mixed window.
                    while (
                        len(buffer_sys) >= SAMPLES_NEEDED
                        and len(buffer_mic) >= SAMPLES_NEEDED
                        and not self._stop.is_set()
                    ):
                        sys_chunk = buffer_sys[:SAMPLES_NEEDED]
                        mic_chunk = buffer_mic[:SAMPLES_NEEDED]
                        buffer_sys = buffer_sys[SAMPLES_NEEDED:]
                        buffer_mic = buffer_mic[SAMPLES_NEEDED:]
                        mixed = mix_to_mono(sys_chunk, mic_chunk)
                        try:
                            self.on_chunk(mixed.astype(np.float32))
                            chunks_emitted += 1
                            if chunks_emitted == 1:
                                print("[agent] First mixed audio chunk (mic + system) — transcribing…")
                        except Exception as exc:
                            print(f"[agent] Audio callback error: {exc}")
                            self._stop.set()
                            break
                else:
                    source = buffer_mic if self.system_idx is None else buffer_sys
                    while len(source) >= SAMPLES_NEEDED and not self._stop.is_set():
                        chunk = source[:SAMPLES_NEEDED]
                        source = source[SAMPLES_NEEDED:]
                        try:
                            self.on_chunk(chunk.astype(np.float32))
                            chunks_emitted += 1
                            if chunks_emitted == 1:
                                which = "mic-only" if self.system_idx is None else "system-only"
                                print(f"[agent] First audio chunk ({which}) — transcribing…")
                        except Exception as exc:
                            print(f"[agent] Audio callback error: {exc}")
                            self._stop.set()
                            break
                    if self.system_idx is None:
                        buffer_mic = source
                    else:
                        buffer_sys = source

                now = time.time()
                if chunks_emitted == 0 and now - last_warn > 5:
                    last_warn = now
                    print("[agent] Waiting for first audio chunk…")

                if not got:
                    self._stop.wait(0.05)
        finally:
            for s in streams:
                try:
                    s.stop()
                    s.close()
                except Exception:
                    pass
