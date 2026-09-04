from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from kokoro_reader.engine import KokoroEngine
from kokoro_reader.main_window import MainWindow
from kokoro_reader.settings_dialog import SETTINGS_APP, SETTINGS_ORG


def test_window_restores_and_saves_voice_choice(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(KokoroEngine, "preload", lambda _engine, _voice: None)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path),
    )
    settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
    settings.clear()
    settings.setValue("voice", "bm_george")
    settings.sync()

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.voice.currentData() == "bm_george"

    window.voice.setCurrentIndex(window.voice.findData("af_bella"))
    settings.sync()
    assert settings.value("voice") == "af_bella"

    window.close()
    app.processEvents()
