"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main() -> int:
    QCoreApplication.setOrganizationName("KokoroReader")
    QCoreApplication.setApplicationName("KokoroReader")
    app = QApplication(sys.argv)
    app.setDesktopFileName("io.github.kokororeader.KokoroReader")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

