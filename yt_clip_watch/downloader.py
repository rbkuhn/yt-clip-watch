"""Qt worker that serializes yt-dlp downloads without blocking the UI."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from .core import DownloadSettings, build_download_options, validate_runtime_paths


@dataclass(frozen=True, slots=True)
class DownloadJob:
    url: str
    settings: DownloadSettings


class _YtDlpLogger:
    def __init__(self, emit_message) -> None:
        self._emit_message = emit_message

    def debug(self, message: str) -> None:
        if not message.startswith("[debug] "):
            self.info(message)

    def info(self, message: str) -> None:
        message = message.strip()
        if message:
            self._emit_message(message)

    def warning(self, message: str) -> None:
        message = message.strip()
        if message:
            self._emit_message(f"Warning: {message}")

    def error(self, message: str) -> None:
        message = message.strip()
        if message:
            self._emit_message(f"Error: {message}")


class DownloadWorker(QObject):
    """One-at-a-time queue with a small GUI-facing signal interface."""

    started = Signal(str)
    progress = Signal(str, float, str)
    message = Signal(str, str)
    finished = Signal(str, bool, str)

    def __init__(self) -> None:
        super().__init__()
        self._jobs: queue.Queue[DownloadJob | None] = queue.Queue()
        self._lock = threading.Lock()
        self._accepting = True
        self._sentinel_queued = False
        self._queued_urls: set[str] = set()
        self._downloaded_urls: set[str] = set()
        self._active_url: str | None = None

    def enqueue(self, job: DownloadJob) -> str:
        """Queue a URL, returning ``new``, ``queued``, or ``downloaded``."""

        with self._lock:
            if not self._accepting:
                return "stopped"
            if job.url in self._downloaded_urls:
                return "downloaded"
            if job.url in self._queued_urls or job.url == self._active_url:
                return "queued"
            self._queued_urls.add(job.url)
        self._jobs.put(job)
        return "new"

    def stop_accepting(self) -> None:
        with self._lock:
            self._accepting = False

    def finish_all(self) -> None:
        """Stop accepting jobs and finish everything already queued."""

        self.stop_accepting()
        self._queue_sentinel()

    def finish_current(self) -> None:
        """Stop accepting jobs, discard pending jobs, and finish the active job."""

        self.stop_accepting()
        while True:
            try:
                job = self._jobs.get_nowait()
            except queue.Empty:
                break
            if job is not None:
                with self._lock:
                    self._queued_urls.discard(job.url)
            self._jobs.task_done()
        self._queue_sentinel()

    def has_work(self) -> bool:
        with self._lock:
            return self._active_url is not None or bool(self._queued_urls)

    @Slot()
    def run(self) -> None:
        while True:
            job = self._jobs.get()
            try:
                if job is None:
                    QThread.currentThread().quit()
                    return
                with self._lock:
                    self._active_url = job.url
                    self._queued_urls.discard(job.url)
                self.started.emit(job.url)
                success, detail = self._download_one(job)
                with self._lock:
                    self._active_url = None
                    if success:
                        self._downloaded_urls.add(job.url)
                self.finished.emit(job.url, success, detail)
            except Exception as exc:  # keep the worker alive for later jobs
                if job is not None:
                    with self._lock:
                        self._active_url = None
                    self.finished.emit(job.url, False, str(exc))
            finally:
                self._jobs.task_done()

    def _queue_sentinel(self) -> None:
        with self._lock:
            if self._sentinel_queued:
                return
            self._sentinel_queued = True
        self._jobs.put(None)

    def _download_one(self, job: DownloadJob) -> tuple[bool, str]:
        missing = validate_runtime_paths(job.settings.runtime_paths)
        if missing:
            return False, "Missing runtime dependency: " + ", ".join(missing)

        import yt_dlp

        latest_message = "Starting download"

        def emit_message(message: str) -> None:
            nonlocal latest_message
            latest_message = message
            self.message.emit(job.url, message)

        def progress_hook(data: dict[str, Any]) -> None:
            status = data.get("status")
            if status == "finished":
                self.progress.emit(job.url, 100.0, "Post-processing")
                return
            if status != "downloading":
                return
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes", 0)
            percent = (downloaded / total * 100) if total else 0.0
            speed = data.get("speed")
            eta = data.get("eta")
            detail = f"{percent:.1f}%"
            if speed:
                detail += f" at {speed / 1024 / 1024:.2f} MiB/s"
            if eta is not None:
                detail += f", {eta}s remaining"
            self.progress.emit(job.url, min(percent, 100.0), detail)

        def postprocessor_hook(data: dict[str, Any]) -> None:
            emit_message(f"Post-processing: {data.get('postprocessor', 'media')}")

        logger = _YtDlpLogger(emit_message)
        options = build_download_options(
            job.settings,
            url=job.url,
            logger=logger,
            progress_hook=progress_hook,
            postprocessor_hook=postprocessor_hook,
        )
        emit_message("Downloading")
        with yt_dlp.YoutubeDL(options) as ydl:
            error_code = ydl.download([job.url])
        if error_code:
            return False, latest_message or f"yt-dlp exited with status {error_code}"
        return True, "Download complete"
