"""Local Kokoro-82M synthesis and streaming WAV writing."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import threading
from typing import Callable

import numpy as np
import soundfile as sf

from .chunking import streaming_chunks
from .text_cleaning import clean_for_speech
from .voices import language_for_voice

SAMPLE_RATE = 24_000
# Short batches reduce time-to-first-audio while retaining enough surrounding
# text for natural sentence phrasing.
FIRST_CHUNK_LIMIT = 120
LATER_CHUNK_LIMIT = 300


class CancelledError(Exception):
    """Raised when the user cancels generation."""


class KokoroEngine:
    """Lazily loads and reuses Kokoro pipelines in the worker thread."""

    def __init__(self) -> None:
        self._pipelines: dict[str, object] = {}
        self._load_lock = threading.RLock()

    def _pipeline(self, language: str):
        with self._load_lock:
            pipeline = self._pipelines.get(language)
            if pipeline is None:
                from kokoro import KPipeline

                pipeline = KPipeline(lang_code=language)
                self._pipelines[language] = pipeline
            return pipeline

    def preload(self, voice: str) -> None:
        """Load the model, language pipeline, and selected voice into memory."""
        with self._load_lock:
            pipeline = self._pipeline(language_for_voice(voice))
            pipeline.load_voice(voice)

    def synthesize(
        self,
        text: str,
        voice: str,
        destination: Path,
        on_progress: Callable[[int, int], None],
        is_cancelled: Callable[[], bool],
        on_audio: Callable[[bytes], None] | None = None,
    ) -> None:
        cleaned_text = clean_for_speech(text)
        chunks = streaming_chunks(
            cleaned_text,
            first_limit=FIRST_CHUNK_LIMIT,
            later_limit=LATER_CHUNK_LIMIT,
        )
        if not chunks:
            raise ValueError("There is no text to read.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{destination.stem}-", suffix=".wav", dir=destination.parent
        )
        os.close(fd)
        temp_path = Path(temp_name)

        try:
            pipeline = self._pipeline(language_for_voice(voice))
            silence = np.zeros(int(SAMPLE_RATE * 0.16), dtype=np.float32)
            with sf.SoundFile(temp_path, "w", samplerate=SAMPLE_RATE, channels=1) as output:
                for index, chunk in enumerate(chunks, start=1):
                    if is_cancelled():
                        raise CancelledError
                    produced_audio = False
                    for _graphemes, _phonemes, audio in pipeline(chunk, voice=voice):
                        if is_cancelled():
                            raise CancelledError
                        if audio is not None:
                            if hasattr(audio, "detach"):
                                audio = audio.detach().cpu().numpy()
                            samples = np.asarray(audio, dtype=np.float32).reshape(-1)
                            output.write(samples)
                            if on_audio is not None:
                                on_audio(_pcm16(samples))
                            produced_audio = True
                    if produced_audio and index < len(chunks):
                        output.write(silence)
                        if on_audio is not None:
                            on_audio(_pcm16(silence))
                    on_progress(index, len(chunks))
            os.replace(temp_path, destination)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise


def _pcm16(samples: np.ndarray) -> bytes:
    """Convert Kokoro float samples to little-endian PCM for live playback."""
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()
