"""Application settings dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

SETTINGS_ORG = "KokoroReader"
SETTINGS_APP = "KokoroReader"


def default_output_directory() -> Path:
    music = Path.home() / "Music"
    return (music if music.is_dir() else Path.home()) / "Kokoro Reader"


def output_directory() -> Path:
    settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
    return Path(str(settings.value("outputDirectory", str(default_output_directory()))))


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(560)

        label = QLabel("Save audio files in:")
        self.directory = QLineEdit(str(output_directory()))
        browse = QPushButton("Choose…")
        browse.clicked.connect(self._browse)

        row = QHBoxLayout()
        row.addWidget(self.directory, 1)
        row.addWidget(browse)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addLayout(row)
        layout.addStretch()
        layout.addWidget(buttons)

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose audio output folder", self.directory.text()
        )
        if chosen:
            self.directory.setText(chosen)

    def _save(self) -> None:
        path = Path(self.directory.text()).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Cannot use folder", str(exc))
            return
        QSettings(SETTINGS_ORG, SETTINGS_APP).setValue("outputDirectory", str(path.resolve()))
        self.accept()

