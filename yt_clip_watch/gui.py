"""PySide6 desktop interface for clipboard-driven downloads."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, QThread
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .core import DownloadSettings, RESOLUTION_CHOICES, extract_urls, resolve_runtime_paths
from .downloader import DownloadJob, DownloadWorker

APP_NAME = "yt-clip-watch"
ORG_NAME = "yt-clip-watch"
BROWSERS = (
    ("None", None),
    ("Firefox", "firefox"),
    ("Chrome", "chrome"),
    ("Chromium", "chromium"),
    ("Brave", "brave"),
    ("Edge", "edge"),
    ("Opera", "opera"),
    ("Vivaldi", "vivaldi"),
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("yt-clip-watch")
        self.resize(850, 620)
        self._settings_store = QSettings(ORG_NAME, APP_NAME)
        self._watching = False
        self._last_clipboard = ""
        self._rows: dict[str, int] = {}
        self._runtime_paths = resolve_runtime_paths()

        self._worker = DownloadWorker()
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.started.connect(self._on_started)
        self._worker.progress.connect(self._on_progress)
        self._worker.message.connect(self._on_message)
        self._worker.finished.connect(self._on_finished)
        self._build_ui()
        QGuiApplication.clipboard().dataChanged.connect(self._clipboard_changed)
        self._load_settings()
        self._show_runtime_status()
        self._thread.start()

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)

        form = QFormLayout()
        self.output_edit = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._choose_output_dir)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit)
        output_row.addWidget(browse)
        form.addRow("Save downloads to", output_row)

        self.resolution_combo = QComboBox()
        for resolution in RESOLUTION_CHOICES:
            self.resolution_combo.addItem(f"{resolution}p", resolution)
        form.addRow("Maximum resolution", self.resolution_combo)

        self.browser_combo = QComboBox()
        for label, value in BROWSERS:
            self.browser_combo.addItem(label, value)
        form.addRow("Browser cookies", self.browser_combo)

        self.archive_check = QCheckBox("Avoid downloading URLs already completed")
        self.archive_check.setChecked(True)
        form.addRow("Download archive", self.archive_check)
        layout.addLayout(form)

        warning = QLabel(
            "Browser cookies are optional. They can contain credentials and should "
            "only be used when content requires them."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #8a4b08")
        layout.addWidget(warning)

        manual_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Paste a YouTube URL here when clipboard watching is unavailable")
        self.url_edit.returnPressed.connect(self._add_manual_url)
        add_button = QPushButton("Add URL")
        add_button.clicked.connect(self._add_manual_url)
        manual_row.addWidget(self.url_edit)
        manual_row.addWidget(add_button)
        layout.addLayout(manual_row)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Start Watching")
        self.stop_button = QPushButton("Stop Watching")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self._start_watching)
        self.stop_button.clicked.connect(self._stop_watching)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addStretch()
        self.status_label = QLabel("Clipboard watching is off.")
        controls.addWidget(self.status_label)
        layout.addLayout(controls)

        self.queue_table = QTableWidget(0, 4)
        self.queue_table.setHorizontalHeaderLabels(("URL", "Status", "Progress", "Details"))
        self.queue_table.horizontalHeader().setStretchLastSection(True)
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.queue_table.setAlternatingRowColors(True)
        layout.addWidget(self.queue_table)

        self.log_list = QListWidget()
        self.log_list.setMaximumHeight(120)
        layout.addWidget(QLabel("Activity"))
        layout.addWidget(self.log_list)
        self.setCentralWidget(central)

    def _load_settings(self) -> None:
        default_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation)
        if not default_dir:
            default_dir = str(Path.home() / "Videos")
        self.output_edit.setText(self._settings_store.value("output_dir", default_dir, type=str))
        self.resolution_combo.setCurrentIndex(
            max(0, self.resolution_combo.findData(self._settings_store.value("resolution", 360, type=int)))
        )
        browser = self._settings_store.value("browser", None)
        index = self.browser_combo.findData(browser)
        self.browser_combo.setCurrentIndex(index if index >= 0 else 0)
        self.archive_check.setChecked(self._settings_store.value("archive", True, type=bool))

    def _save_settings(self) -> None:
        self._settings_store.setValue("output_dir", self.output_edit.text().strip())
        self._settings_store.setValue("resolution", self.resolution_combo.currentData())
        self._settings_store.setValue("browser", self.browser_combo.currentData())
        self._settings_store.setValue("archive", self.archive_check.isChecked())
        self._settings_store.sync()

    def _choose_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose download folder", self.output_edit.text())
        if selected:
            self.output_edit.setText(selected)

    def _show_runtime_status(self) -> None:
        missing = []
        if self._runtime_paths.js_runtime is None:
            missing.append("Deno or Node")
        if self._runtime_paths.ffmpeg is None:
            missing.append("FFmpeg")
        if missing:
            self.status_label.setText("Missing: " + ", ".join(missing))
            self.status_label.setToolTip(
                "Install the missing tools for source runs. The AppImage bundles them."
            )

    def _start_watching(self) -> None:
        clipboard = QGuiApplication.clipboard()
        self._last_clipboard = clipboard.text()
        self._watching = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Watching clipboard; startup contents ignored.")

    def _stop_watching(self) -> None:
        self._watching = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Clipboard watching is off.")

    def _clipboard_changed(self) -> None:
        if not self._watching:
            return
        text = QGuiApplication.clipboard().text()
        if text == self._last_clipboard:
            return
        self._last_clipboard = text
        self._enqueue_urls(extract_urls(text))

    def _add_manual_url(self) -> None:
        urls = extract_urls(self.url_edit.text())
        if not urls:
            QMessageBox.warning(self, "No YouTube URL", "Enter a valid YouTube URL.")
            return
        self._enqueue_urls(urls)
        self.url_edit.clear()

    def _make_settings(self) -> DownloadSettings:
        output_dir = Path(self.output_edit.text().strip()).expanduser()
        app_data = Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        )
        archive_path = app_data / "download-archive.txt" if self.archive_check.isChecked() else None
        return DownloadSettings(
            output_dir=output_dir,
            resolution=int(self.resolution_combo.currentData()),
            browser=self.browser_combo.currentData(),
            archive_path=archive_path,
            runtime_paths=self._runtime_paths,
        )

    def _enqueue_urls(self, urls: list[str]) -> None:
        try:
            settings = self._make_settings()
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Invalid download settings", str(exc))
            return
        for url in urls:
            status = self._worker.enqueue(DownloadJob(url, settings))
            if status == "new":
                self._add_row(url, "Queued", "0%", "Waiting")
            elif status == "queued":
                self._add_log(f"Already queued: {url}")
            elif status == "downloaded":
                self._add_log(f"Already downloaded this session: {url}")
            else:
                self._add_log("Watching has stopped; URL was not queued.")

    def _add_row(self, url: str, status: str, progress: str, details: str) -> None:
        row = self.queue_table.rowCount()
        self.queue_table.insertRow(row)
        for column, value in enumerate((url, status, progress, details)):
            self.queue_table.setItem(row, column, QTableWidgetItem(value))
        self._rows[url] = row
        self.queue_table.scrollToBottom()

    def _set_row(self, url: str, *, status: str | None = None, progress: str | None = None, details: str | None = None) -> None:
        row = self._rows.get(url)
        if row is None:
            return
        values = (status, progress, details)
        for column, value in enumerate(values, start=1):
            if value is not None:
                self.queue_table.item(row, column).setText(value)

    def _on_started(self, url: str) -> None:
        self._set_row(url, status="Downloading", details="Starting")
        self.status_label.setText(f"Downloading {url}")

    def _on_progress(self, url: str, percent: float, detail: str) -> None:
        self._set_row(url, progress=f"{percent:.1f}%", details=detail)

    def _on_message(self, url: str, detail: str) -> None:
        self._set_row(url, details=detail)
        self._add_log(f"{url}: {detail}")

    def _on_finished(self, url: str, success: bool, detail: str) -> None:
        self._set_row(
            url,
            status="Complete" if success else "Failed",
            progress="100%" if success else "—",
            details=detail,
        )
        self._add_log(f"{'Complete' if success else 'Failed'}: {url} ({detail})")
        self.status_label.setText("Ready" if success else f"Download failed: {detail}")

    def _add_log(self, message: str) -> None:
        self.log_list.addItem(message)
        self.log_list.scrollToBottom()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_settings()
        self._stop_watching()
        if self._worker.has_work():
            choice = QMessageBox.question(
                self,
                "Downloads in progress",
                "Wait for all queued downloads? Choose No to finish only the current download.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if choice == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if choice == QMessageBox.StandardButton.Yes:
                self._worker.finish_all()
            else:
                self._worker.finish_current()
        else:
            self._worker.finish_current()
        self._thread.wait()
        event.accept()
