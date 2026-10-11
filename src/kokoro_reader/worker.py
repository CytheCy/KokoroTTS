"""Qt worker object for non-blocking speech generation."""

from __future__ import annotations

from pathlib import Path
import threading

from PySide6.QtCore import QObject, Signal, Slot

from .engine import CancelledError, KokoroEngine
from .output_naming import available_path
from .text_cleaning import remove_heading_lines


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


class BatchSpeechWorker(QObject):
    """Generate one WAV per Markdown file without loading files on the UI thread."""

    progress = Signal(int, int)
    status = Signal(str)
    completed = Signal(int, int, object)
    cancelled = Signal(int, int)
    finished = Signal()

    def __init__(
        self,
        files: list[Path],
        voice: str,
        output_folder: Path,
        engine: KokoroEngine,
    ) -> None:
        super().__init__()
        self.files = files
        self.voice = voice
        self.output_folder = output_folder
        self.engine = engine
        self._cancel_event = threading.Event()

    @Slot()
    def cancel(self) -> None:
        self._cancel_event.set()
        self.status.emit("Cancelling after the current audio segment…")

    @Slot()
    def run(self) -> None:
        created = 0
        errors: list[str] = []
        total = len(self.files)
        try:
            for index, source in enumerate(self.files, start=1):
                if self._cancel_event.is_set():
                    self.cancelled.emit(created, total)
                    return
                self.status.emit(f"Creating {index} of {total}: {source.name}")
                try:
                    text = remove_heading_lines(source.read_text(encoding="utf-8-sig"))
                    destination = available_path(
                        self.output_folder / f"{source.parent.name} - {source.stem}.wav"
                    )
                    self.engine.synthesize(
                        text,
                        self.voice,
                        destination,
                        lambda _current, _total: None,
                        self._cancel_event.is_set,
                    )
                except CancelledError:
                    self.cancelled.emit(created, total)
                    return
                except Exception as exc:
                    errors.append(f"{source.name}: {exc}")
                else:
                    created += 1
                self.progress.emit(index, total)
            self.completed.emit(created, total, errors)
        finally:
            self.finished.emit()
