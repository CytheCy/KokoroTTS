from PySide6.QtWidgets import QApplication

from kokoro_reader.engine import KokoroEngine
from kokoro_reader.main_window import MainWindow


def test_remove_headings_button_edits_document_and_can_be_undone(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(KokoroEngine, "preload", lambda _engine, _voice: None)
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert not window.remove_headings_button.isEnabled()
    original = "# 03 Time to Kill\n\nOpening paragraph.\n## Next\nMore text."
    window.editor.setPlainText(original)
    assert window.remove_headings_button.isEnabled()

    window.remove_headings_button.click()
    assert window.editor.toPlainText() == "\nOpening paragraph.\nMore text."
    assert not window.remove_headings_button.isEnabled()

    window.editor.undo()
    assert window.editor.toPlainText() == original
    assert window.remove_headings_button.isEnabled()

    window.close()
    app.processEvents()
