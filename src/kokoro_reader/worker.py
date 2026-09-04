"""Qt worker object for non-blocking speech generation."""

from __future__ import annotations

from pathlib import Path
import threading

from PySide6.QtCore import QObject, Signal, Slot

from .engine import CancelledError, KokoroEngine


class SpeechWorker(QObject):
    progress = Signal(int, int)
    audio_ready = Signal(bytes)
    status = Signal(str)
    completed = Signal(str)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(
        self, text: str, voice: str, destination: Path, engine: KokoroEngine
    ) -> None:
        super().__init__()
        self.text = text
        self.voice = voice
        self.destination = destination
        self.engine = engine
        self._cancel_event = threading.Event()

    @Slot()
    def cancel(self) -> None:
        self._cancel_event.set()
        self.status.emit("Cancelling after the current audio segment…")

    @Slot()
    def run(self) -> None:
        try:
            self.status.emit("Loading Kokoro-82M (the first run may download model files)…")
            self.status.emit("Removing formatting and unsupported characters…")
            self.engine.synthesize(
                self.text,
                self.voice,
                self.destination,
                self.progress.emit,
                self._cancel_event.is_set,
                self.audio_ready.emit,
            )
            self.completed.emit(str(self.destination))
        except CancelledError:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()
