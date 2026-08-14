from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from yt_clip_watch.core import DownloadSettings
from yt_clip_watch.downloader import DownloadJob, DownloadWorker


class DownloaderQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_duplicate_urls_are_not_queued_twice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = DownloadSettings(output_dir=Path(directory))
            worker = DownloadWorker()
            job = DownloadJob("https://youtu.be/example", settings)
            self.assertEqual(worker.enqueue(job), "new")
            self.assertEqual(worker.enqueue(job), "queued")


if __name__ == "__main__":
    unittest.main()
