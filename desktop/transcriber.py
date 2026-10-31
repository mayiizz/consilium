"""Faster-whisper transcription for 2-second PCM chunks."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None  # type: ignore


class Transcriber:
    def __init__(self, model_size: str = "tiny") -> None:
        self.model_size = model_size
        self._model: Optional[WhisperModel] = None

    def _ensure_model(self) -> WhisperModel:
        if WhisperModel is None:
            raise RuntimeError("faster-whisper not installed. Run: pip install faster-whisper")
        if self._model is None:
            print(f"[agent] Loading whisper model '{self.model_size}'…")
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, pcm: np.ndarray, sample_rate: int = 16000) -> Tuple[str, float]:
        if len(pcm) == 0:
            return "", 0.0
        model = self._ensure_model()
        audio = pcm.astype(np.float32)
        segments, _ = model.transcribe(audio, language="en", vad_filter=True)
        texts = []
        confidences = []
        for seg in segments:
            texts.append(seg.text.strip())
            confidences.append(getattr(seg, "avg_logprob", -0.5))
        text = " ".join(t for t in texts if t)
        if not confidences:
            return text, 0.0
        # Map logprob roughly to 0-1 confidence
        avg = sum(confidences) / len(confidences)
        confidence = max(0.0, min(1.0, 1.0 + avg))
        return text, confidence
