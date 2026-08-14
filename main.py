#!/usr/bin/env python3
"""Launch the yt-clip-watch desktop application."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from yt_clip_watch.gui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("yt-clip-watch")
    app.setOrganizationName("yt-clip-watch")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
