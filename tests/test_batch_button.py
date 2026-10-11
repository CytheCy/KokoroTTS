import time

from PySide6.QtWidgets import QApplication, QFileDialog

from kokoro_reader.engine import KokoroEngine
from kokoro_reader.main_window import MainWindow
import kokoro_reader.main_window as main_window


def test_batch_button_selects_folder_and_generates_files(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(KokoroEngine, "preload", lambda _engine, _voice: None)
    source = tmp_path / "MTTRC"
    source.mkdir()
    (source / "02-second.md").write_text("# Heading\nSecond chapter.")
    (source / "01-first.md").write_text("# Heading\nFirst chapter.")
    (source / "skip.txt").write_text("Ignored")
    output = tmp_path / "audio"
    output.mkdir()
    monkeypatch.setattr(main_window, "output_directory", lambda: output)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *_args: str(source)
    )
    calls = []

    def fake_synthesize(_engine, text, voice, destination, on_progress, is_cancelled):
        calls.append((text, destination.name))
        destination.write_bytes(b"fake wav")

    monkeypatch.setattr(KokoroEngine, "synthesize", fake_synthesize)
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert not calls
    window.batch_button.click()
    deadline = time.monotonic() + 5
    while window._thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)

    assert window._thread is None
    assert calls == [
        ("First chapter.", "MTTRC - 01-first.wav"),
        ("Second chapter.", "MTTRC - 02-second.wav"),
    ]
    assert window.progress.value() == 2
    assert window.batch_button.isEnabled()
    assert (source / "01-first.md").read_text().startswith("# Heading")
    window.close()
    app.processEvents()
