"""Folder and filters for the chronological event reader."""

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from .settings_dialog import SETTINGS_APP, SETTINGS_ORG
from .timeline import Timeline, load_timeline


class EventTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timeline = Timeline([], {}, [])
        self.folder = QLineEdit()
        self.folder.setReadOnly(True)
        self.folder.setPlaceholderText("Choose a folder of timeline Markdown files…")
        self.folder.setAccessibleName("Timeline folder")
        self.choose_button = QPushButton("Choose folder…")
        self.choose_button.clicked.connect(self._choose_folder)
        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(lambda: self.load_folder(Path(self.folder.text())))
        self.reload_button.setEnabled(False)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(self.choose_button)
        folder_row.addWidget(self.reload_button)

        self.category = QComboBox()
        self.category.addItem("All categories", None)
        self.category.setAccessibleName("Category or subcategory")
        self.category.setToolTip("A parent category includes all of its subcategories.")
        self.start_year = QSpinBox()
        self.end_year = QSpinBox()
        for spin, label in ((self.start_year, "Start year"), (self.end_year, "End year")):
            spin.setRange(1, 9999)
            spin.setAccessibleName(label)
        self.end_year.setValue(9999)
        filters = QHBoxLayout()
        filters.addWidget(QLabel("Category / subcategory:"))
        filters.addWidget(self.category, 1)
        filters.addWidget(QLabel("Start year:"))
        filters.addWidget(self.start_year)
        filters.addWidget(QLabel("End year:"))
        filters.addWidget(self.end_year)
        self.read_year = QCheckBox("Read Year")
        self.read_year.setChecked(
            QSettings(SETTINGS_ORG, SETTINGS_APP).value("event_read_year", True, type=bool)
        )
        self.summary = QLabel("Choose a timeline folder to begin.")
        self.summary.setWordWrap(True)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Events in reading order")
        self.preview.setPlaceholderText("Matching events will appear here in date order.")
        self.warnings = QLabel()
        self.warnings.setWordWrap(True)
        self.details_button = QPushButton("Show file issues…")
        self.details_button.clicked.connect(self._show_issues)
        self.details_button.hide()
        layout = QVBoxLayout(self)
        layout.addLayout(folder_row)
        layout.addLayout(filters)
        layout.addWidget(self.read_year)
        layout.addWidget(self.summary)
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.warnings)
        layout.addWidget(self.details_button)
        self.read_year.toggled.connect(self._read_year_changed)
        self.start_year.valueChanged.connect(self._refresh)
        self.end_year.valueChanged.connect(self._refresh)
        self.category.currentIndexChanged.connect(self._refresh)
        saved = str(QSettings(SETTINGS_ORG, SETTINGS_APP).value("event_folder", ""))
        if saved and Path(saved).is_dir():
            self.load_folder(Path(saved))

    def _read_year_changed(self, checked: bool):
        QSettings(SETTINGS_ORG, SETTINGS_APP).setValue("event_read_year", checked)
        self._refresh()

    def _choose_folder(self):
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose a timeline folder", self.folder.text() or str(Path.home())
        )
        if chosen:
            self.load_folder(Path(chosen))

    def load_folder(self, folder: Path):
        try:
            timeline = load_timeline(folder)
        except OSError as exc:
            QMessageBox.warning(self, "Cannot read timeline folder", str(exc))
            return
        self.timeline = timeline
        self.folder.setText(str(folder))
        self.reload_button.setEnabled(True)
        QSettings(SETTINGS_ORG, SETTINGS_APP).setValue("event_folder", str(folder))
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem("All categories", None)
        for name in sorted(timeline.parents, key=lambda n: timeline.category_path(n).casefold()):
            self.category.addItem(timeline.category_path(name), name)
        self.category.blockSignals(False)
        if timeline.events:
            self.start_year.setValue(timeline.events[0].date.year)
            self.end_year.setValue(timeline.events[-1].date.year)
        self.warnings.setText(
            f"{len(timeline.warnings)} file or metadata issue(s). See details for recovered or skipped notes."
            if timeline.warnings else ""
        )
        self.details_button.setVisible(bool(timeline.warnings))
        self._refresh()

    def _show_issues(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Timeline file issues")
        dialog.setText("Some notes or category settings could not be loaded.")
        dialog.setDetailedText("\n".join(self.timeline.warnings))
        dialog.exec()

    def _refresh(self, *_args):
        if self.start_year.value() > self.end_year.value():
            self.summary.setText("Start year must be before or equal to end year.")
            self.preview.clear()
            return
        events = self.timeline.select(
            self.category.currentData(), self.start_year.value(), self.end_year.value()
        )
        self.summary.setText(f"{len(events)} matching events — earliest first. Parent categories include subcategories.")
        self.preview.setPlainText("\n\n".join(event.narration(read_year=self.read_year.isChecked()) for event in events))

    def narration(self) -> str:
        return self.preview.toPlainText().strip()

    def set_running(self, running: bool):
        self.choose_button.setEnabled(not running)
        self.reload_button.setEnabled(not running and bool(self.folder.text()))
        self.read_year.setEnabled(not running)
        self.category.setEnabled(not running)
        self.start_year.setEnabled(not running)
        self.end_year.setEnabled(not running)
