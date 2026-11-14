import time

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFileDialog

from kokoro_reader.engine import KokoroEngine
from kokoro_reader.main_window import MainWindow
import kokoro_reader.main_window as main_window


def test_event_filters_use_existing_speech_worker_and_preserve_paste(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(KokoroEngine, "preload", lambda *_: None)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    source = tmp_path / "Timeline"
    source.mkdir()
    for name, day, category in [
        ("a-late", "2050-01-01", "AI"),
        ("z-early", "2040-01-01", "AI"),
        ("other", "2045-01-01", "Food"),
    ]:
        (source / f"{name}.md").write_text(
            f"---\ntitle: {name}\ndate: {day}\ncategory: {category}\n---\nBody of {name}."
        )
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *_: str(source))
    monkeypatch.setattr(main_window, "output_directory", lambda: tmp_path)
    calls = []

    def synthesize(_engine, text, voice, destination, progress, cancelled, audio_ready, **options):
        calls.append((text, options))
        destination.write_bytes(b"fake wav")

    monkeypatch.setattr(KokoroEngine, "synthesize", synthesize)
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert [window.tabs.tabText(i) for i in range(2)] == ["Paste", "Event"]
    window.editor.setPlainText("Keep this pasted text")
    window.tabs.setCurrentIndex(1)
    event = window.event_tab
    event.choose_button.click()
    event.category.setCurrentIndex(event.category.findData("AI"))
    assert event.start_year.value() == 2040
    assert event.end_year.value() == 2050
    assert event.read_year.isChecked()
    assert event.narration().startswith("Year 2040. z-early.")
    event.read_year.setChecked(False)
    assert event.narration().startswith("z-early.")
    assert "2040" not in event.narration() and "2050" not in event.narration()
    event.read_year.setChecked(True)
    text = event.narration()
    assert text.index("z-early") < text.index("a-late")
    assert "other" not in text and "category:" not in text
    event.end_year.setValue(2049)
    assert "a-late" not in event.narration()
    event.end_year.setValue(2030)
    assert not event.narration()
    event.end_year.setValue(2050)
    event.pause_seconds.setValue(2.5)
    window.generate_button.click()
    assert not event.choose_button.isEnabled()
    assert not event.read_year.isEnabled()
    assert not event.pause_seconds.isEnabled()
    deadline = time.monotonic() + 5
    while window._thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert window._thread is None
    assert calls == [(text, {
        "event_texts": [e.narration() for e in event.timeline.select("AI", 2040, 2050)],
        "event_pause_seconds": 2.5,
    })]
    assert (tmp_path / "AI-2040-2050.wav").read_bytes() == b"fake wav"
    assert window.filename.text() == "AI-2040-2050.wav"
    assert event.choose_button.isEnabled()
    assert event.pause_seconds.isEnabled()
    from kokoro_reader.event_tab import EventTab
    restored = EventTab()
    assert restored.pause_seconds.value() == 2.5
    restored.close()
    assert window.editor.toPlainText() == "Keep this pasted text"
    window.tabs.setCurrentIndex(0)
    assert not window.batch_button.isHidden()
    window.close()
    app.processEvents()


def test_event_default_filename_tracks_filters_and_preserves_custom_names(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(KokoroEngine, "preload", lambda *_: None)
    monkeypatch.setattr(main_window, "output_directory", lambda: tmp_path)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    paste_name = window.filename.text()
    event = window.event_tab
    event.category.clear()
    event.category.addItem("All categories", None)
    event.category.addItem("Science / AI", "AI")
    event.category.addItem("Science / Robots: future?", "Robots: future?")
    event.start_year.setValue(2040)
    event.end_year.setValue(2050)
    window.tabs.setCurrentIndex(1)
    assert window.filename.text() == "All categories-2040-2050.wav"
    event.category.setCurrentIndex(1)
    event.end_year.setValue(2049)
    assert window.filename.text() == "AI-2040-2049.wav"
    event.category.setCurrentIndex(2)
    assert window.filename.text() == "Robots_ future_-2040-2049.wav"
    window.tabs.setCurrentIndex(0)
    assert window.filename.text() == paste_name
    window.tabs.setCurrentIndex(1)
    window.filename.setText("My custom narration.wav")
    event.start_year.setValue(2041)
    event.category.setCurrentIndex(1)
    window.tabs.setCurrentIndex(0)
    window.tabs.setCurrentIndex(1)
    assert window.filename.text() == "My custom narration.wav"
    assert window._destination() == tmp_path / "My custom narration.wav"
    window.filename.clear()
    event.end_year.setValue(2051)
    assert window.filename.text() == "AI-2041-2051.wav"
    (tmp_path / window.filename.text()).write_bytes(b"existing audio")
    assert window._destination() == tmp_path / "AI-2041-2051-2.wav"
    assert (tmp_path / "AI-2041-2051.wav").read_bytes() == b"existing audio"
    window.close()
    app.processEvents()
