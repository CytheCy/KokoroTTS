"""The deliberately small notepad-style main window."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
import re
import threading

from PySide6.QtCore import QIODevice, QSettings, QThread, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtMultimedia import (
    QAudio,
    QAudioFormat,
    QAudioOutput,
    QAudioSink,
    QMediaPlayer,
)
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .settings_dialog import SETTINGS_APP, SETTINGS_ORG, SettingsDialog, output_directory
from .engine import KokoroEngine, SAMPLE_RATE
from .output_naming import available_path
from .text_cleaning import remove_heading_lines
from .voices import VOICES
from .worker import SpeechWorker


class MainWindow(QMainWindow):
    preload_finished = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kokoro Reader")
        self.resize(820, 650)
        self._thread: QThread | None = None
        self._worker: SpeechWorker | None = None
        # Pipelines are expensive to load, so retain them between generation jobs.
        self._engine = KokoroEngine()
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._playback_state_changed)
        self.player.mediaStatusChanged.connect(self._media_status_changed)
        self.player.positionChanged.connect(self._playback_position_changed)
        self.player.durationChanged.connect(self._playback_duration_changed)
        self.player.errorOccurred.connect(self._playback_error)
        self._stream_sink: QAudioSink | None = None
        self._stream_device: QIODevice | None = None
        self._stream_queue: deque[bytes] = deque()
        self._stream_offset = 0
        self._stream_total_bytes = 0
        self._stream_paused = False
        self._stream_disabled = False
        self._generation_complete = False
        self._completed_filename: str | None = None
        self._stream_timer = QTimer(self)
        self._stream_timer.setInterval(10)
        self._stream_timer.timeout.connect(self._pump_stream)
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setPlaceholderText("Paste the document you want Kokoro to read here…")
        self.editor.setAccessibleName("Document text")
        self.remove_headings_button = QPushButton("Remove Headings")
        self.remove_headings_button.setEnabled(False)
        self.remove_headings_button.clicked.connect(self._remove_headings)
        self.editor.textChanged.connect(self._update_remove_headings_button)

        self.voice = QComboBox()
        for description, voice_id in VOICES:
            self.voice.addItem(description, voice_id)
        saved_voice = str(
            QSettings(SETTINGS_ORG, SETTINGS_APP).value("voice", "")
        )
        saved_index = self.voice.findData(saved_voice)
        self.voice.setCurrentIndex(saved_index if saved_index >= 0 else 0)
        self.voice.currentIndexChanged.connect(self._save_voice)
        self.voice.setAccessibleName("Voice")

        self.filename = QLineEdit(self._suggested_filename())
        self.filename.setPlaceholderText("narration.wav")
        self.filename.setAccessibleName("Output filename")

        self.folder_label = QLabel()
        self.folder_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        settings_button = QPushButton("Settings…")
        settings_button.clicked.connect(self._settings)

        self.generate_button = QPushButton("Create audio")
        self.generate_button.setDefault(True)
        self.generate_button.clicked.connect(self._generate)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        self.play_button = QPushButton("Play audio")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self._toggle_playback)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.playback_progress = QProgressBar()
        self.playback_progress.setRange(0, 100)
        self.playback_progress.setValue(0)
        self.playback_progress.setFormat("Playback: %p%")
        self.playback_progress.setAccessibleName("Audio playback progress")
        self.status = QLabel("Ready — speech is generated locally on this computer.")
        self.status.setWordWrap(True)
        self.preload_finished.connect(self._preload_finished)

        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("Voice:"))
        voice_row.addWidget(self.voice, 1)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("File name:"))
        file_row.addWidget(self.filename, 1)
        file_row.addWidget(settings_button)

        button_row = QHBoxLayout()
        button_row.addWidget(self.play_button)
        button_row.addStretch()
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.generate_button)

        editor_row = QHBoxLayout()
        editor_row.addStretch()
        editor_row.addWidget(self.remove_headings_button)

        layout = QVBoxLayout()
        layout.addWidget(self.editor, 1)
        layout.addLayout(editor_row)
        layout.addLayout(voice_row)
        layout.addLayout(file_row)
        layout.addWidget(self.folder_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.playback_progress)
        layout.addWidget(self.status)
        layout.addLayout(button_row)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self._refresh_folder()
        self.status.setText("Preparing the selected voice in the background…")
        self._preload_thread = threading.Thread(
            target=self._preload_selected_voice,
            args=(str(self.voice.currentData()),),
            name="kokoro-preload",
            daemon=True,
        )
        self._preload_thread.start()

    @staticmethod
    def _suggested_filename() -> str:
        return f"narration-{datetime.now():%Y-%m-%d-%H%M}.wav"

    def _refresh_folder(self) -> None:
        self.folder_label.setText(f"Save folder: {output_directory()}")

    def _settings(self) -> None:
        if SettingsDialog(self).exec():
            self._refresh_folder()

    def _save_voice(self, _index: int) -> None:
        voice_id = self.voice.currentData()
        if voice_id is not None:
            QSettings(SETTINGS_ORG, SETTINGS_APP).setValue("voice", str(voice_id))

    def _update_remove_headings_button(self) -> None:
        has_headings = any(
            line.startswith("#") for line in self.editor.toPlainText().splitlines()
        )
        self.remove_headings_button.setEnabled(
            not self.editor.isReadOnly() and has_headings
        )

    def _remove_headings(self) -> None:
        text = self.editor.toPlainText()
        without_headings = remove_heading_lines(text)
        if without_headings == text:
            return
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(without_headings)
        self.editor.setTextCursor(cursor)

    def _preload_selected_voice(self, voice_id: str) -> None:
        try:
            self._engine.preload(voice_id)
        except Exception:
            self.preload_finished.emit(False)
        else:
            self.preload_finished.emit(True)

    def _preload_finished(self, succeeded: bool) -> None:
        if self._thread is not None:
            return
        if succeeded:
            self.status.setText("Ready — the selected voice is loaded.")
        else:
            self.status.setText("Ready — the selected voice will load when audio is created.")

    def _destination(self) -> Path | None:
        name = self.filename.text().strip()
        name = re.sub(r"[\\/]", "_", name)
        if not name:
            QMessageBox.warning(self, "File name needed", "Enter a name for the audio file.")
            return None
        if not name.lower().endswith(".wav"):
            name += ".wav"
        destination = available_path(output_directory() / name)
        self.filename.setText(destination.name)
        return destination

    def _generate(self) -> None:
        text = self.editor.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Nothing to read", "Paste or type a document first.")
            return
        destination = self._destination()
        if destination is None:
            return

        self._stop_stream()
        self.player.stop()
        self.player.setSource(QUrl())
        self.play_button.setText("Play audio")
        self.play_button.setEnabled(False)
        self._reset_playback_progress()

        thread = QThread(self)
        worker = SpeechWorker(
            text, str(self.voice.currentData()), destination, self._engine
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._progress)
        worker.audio_ready.connect(self._audio_ready)
        worker.status.connect(self.status.setText)
        worker.completed.connect(self._completed)
        worker.failed.connect(self._failed)
        worker.cancelled.connect(self._cancelled)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._thread_finished)
        self._thread = thread
        self._worker = worker
        self._generation_complete = False
        self._completed_filename = None
        self._stream_disabled = False
        self._set_running(True)
        self.progress.setRange(0, 0)
        thread.start()

    def _cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.cancel_button.setEnabled(False)

    def _set_running(self, running: bool) -> None:
        self.editor.setReadOnly(running)
        self._update_remove_headings_button()
        self.voice.setEnabled(not running)
        self.filename.setEnabled(not running)
        self.generate_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)

    def _progress(self, current: int, total: int) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.status.setText(f"Generating speech locally… chunk {current} of {total}")

    def _completed(self, filename: str) -> None:
        self._generation_complete = True
        self._completed_filename = filename
        self.status.setText("Finished generating — playing the remaining audio…")
        self._maybe_finish_stream()

    def _audio_ready(self, audio: bytes) -> None:
        if not audio or self._stream_disabled:
            return
        self._stream_total_bytes += len(audio)
        self._stream_queue.append(audio)
        if self._stream_sink is None:
            self._start_stream()
        self._pump_stream()

    def _start_stream(self) -> None:
        audio_format = QAudioFormat()
        audio_format.setSampleRate(SAMPLE_RATE)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        sink = QAudioSink(audio_format, self)
        sink.stateChanged.connect(self._stream_state_changed)
        self._stream_sink = sink
        self._stream_device = sink.start()
        self._stream_timer.start()
        self.play_button.setText("Pause")
        self.play_button.setEnabled(True)
        self._update_stream_progress()

    def _pump_stream(self) -> None:
        sink = self._stream_sink
        device = self._stream_device
        if sink is None or device is None or self._stream_paused:
            return

        while self._stream_queue:
            available = sink.bytesFree()
            if available < 2:
                break
            current = self._stream_queue[0]
            amount = min(available, len(current) - self._stream_offset)
            amount -= amount % 2
            if amount <= 0:
                break
            written = device.write(
                current[self._stream_offset : self._stream_offset + amount]
            )
            if written <= 0:
                break
            self._stream_offset += written
            if self._stream_offset >= len(current):
                self._stream_queue.popleft()
                self._stream_offset = 0

        self._maybe_finish_stream()
        self._update_stream_progress()

    def _update_stream_progress(self) -> None:
        sink = self._stream_sink
        if sink is None or self._stream_total_bytes <= 0:
            return
        duration_ms = max(1, self._stream_total_bytes * 1000 // (SAMPLE_RATE * 2))
        played_ms = min(duration_ms, sink.processedUSecs() // 1000)
        self.playback_progress.setRange(0, duration_ms)
        self.playback_progress.setValue(played_ms)

    def _stream_state_changed(self, state: QAudio.State) -> None:
        if state == QAudio.State.IdleState:
            self._maybe_finish_stream()
        elif state == QAudio.State.StoppedState and self._stream_sink is not None:
            if self._stream_sink.error() != QAudio.Error.NoError:
                self._stream_disabled = True
                self._stop_stream()
                self.status.setText(
                    "Live playback stopped, but the WAV file is still being generated."
                )
                self._maybe_finish_stream()

    def _maybe_finish_stream(self) -> None:
        if not self._generation_complete or self._stream_queue:
            return
        if (
            self._stream_sink is not None
            and self._stream_sink.state() not in
            (QAudio.State.IdleState, QAudio.State.StoppedState)
        ):
            return
        # A write can refill an idle sink before its queued state-change event
        # arrives. Do not stop it until the device buffer has actually drained.
        if (
            self._stream_sink is not None
            and self._stream_sink.state() == QAudio.State.IdleState
            and self._stream_sink.bytesFree() < self._stream_sink.bufferSize()
        ):
            return

        filename = self._completed_filename
        if self._stream_total_bytes > 0:
            duration_ms = max(
                1, self._stream_total_bytes * 1000 // (SAMPLE_RATE * 2)
            )
            self.playback_progress.setRange(0, duration_ms)
            self.playback_progress.setValue(duration_ms)
        self._stop_stream()
        if filename is not None:
            self.player.setSource(QUrl.fromLocalFile(filename))
            self.play_button.setText("Play audio")
            self.play_button.setEnabled(True)
            self.status.setText(f"Finished: {filename}")
            self.filename.setText(self._suggested_filename())

    def _stop_stream(self) -> None:
        self._stream_timer.stop()
        sink = self._stream_sink
        self._stream_sink = None
        self._stream_device = None
        if sink is not None:
            sink.stop()
            sink.deleteLater()
        self._stream_queue.clear()
        self._stream_offset = 0
        self._stream_total_bytes = 0
        self._stream_paused = False

    def _toggle_playback(self) -> None:
        if self._stream_sink is not None:
            if self._stream_paused:
                self._stream_paused = False
                self._stream_sink.resume()
                self.play_button.setText("Pause")
                self._pump_stream()
            else:
                self._stream_paused = True
                self._stream_sink.suspend()
                self.play_button.setText("Play audio")
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("Pause")
        else:
            self.play_button.setText("Play audio")

    def _playback_position_changed(self, position: int) -> None:
        if self.player.duration() > 0:
            self.playback_progress.setValue(position)

    def _playback_duration_changed(self, duration: int) -> None:
        if duration > 0:
            self.playback_progress.setRange(0, duration)
            self.playback_progress.setValue(min(self.player.position(), duration))
        else:
            self._reset_playback_progress()

    def _reset_playback_progress(self) -> None:
        self.playback_progress.setRange(0, 100)
        self.playback_progress.setValue(0)

    def _media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)
            self.playback_progress.setValue(0)
            self.play_button.setText("Play audio")

    def _playback_error(self, _error, message: str) -> None:
        if message:
            self.status.setText(f"Could not play audio: {message}")

    def _failed(self, message: str) -> None:
        self._stop_stream()
        self._reset_playback_progress()
        self.status.setText("Audio generation failed.")
        QMessageBox.critical(
            self,
            "Could not create audio",
            f"{message}\n\nCheck your network on the first run; Kokoro must download its model and voice.",
        )

    def _cancelled(self) -> None:
        self._stop_stream()
        self._reset_playback_progress()
        self.status.setText("Cancelled. No incomplete audio file was kept.")

    def _thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._set_running(False)
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)

    def closeEvent(self, event) -> None:
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.information(
                self, "Audio is being created", "Cancel generation before closing Kokoro Reader."
            )
            event.ignore()
            return
        self.player.stop()
        self._stop_stream()
        super().closeEvent(event)
