from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from yt_clip_watch.core import (
    DownloadSettings,
    RuntimePaths,
    build_download_options,
    build_sort_value,
    extract_urls,
)


class CoreTests(unittest.TestCase):
    def test_extract_urls_deduplicates_and_strips_punctuation(self) -> None:
        text = (
            "See https://youtu.be/abc123, then https://www.youtube.com/watch?v=xyz! "
            "Again: https://youtu.be/abc123."
        )
        self.assertEqual(
            extract_urls(text),
            ["https://youtu.be/abc123", "https://www.youtube.com/watch?v=xyz"],
        )

    def test_settings_control_sort_and_runtime_options(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = DownloadSettings(
                output_dir=Path(directory),
                resolution=720,
                browser="firefox",
                archive_path=Path(directory) / "state" / "archive.txt",
                runtime_paths=RuntimePaths(
                    js_runtime=Path("/opt/deno"),
                    js_runtime_name="deno",
                    ffmpeg=Path("/opt/ffmpeg"),
                ),
            )
            options = build_download_options(settings)
            self.assertEqual(build_sort_value(settings), "res:720,ext:mp4:m4a")
            self.assertEqual(options["format_sort"], ["res:720", "ext:mp4:m4a"])
            self.assertEqual(options["js_runtimes"], {"deno": {"path": "/opt/deno"}})
            self.assertEqual(options["ffmpeg_location"], "/opt/ffmpeg")
            self.assertTrue(Path(directory, "state", "archive.txt").parent.is_dir())

    def test_custom_sort_overrides_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = DownloadSettings(
                output_dir=Path(directory),
                resolution=360,
                sort_value="codec:h264,res:1080",
            )
            self.assertEqual(build_sort_value(settings), "codec:h264,res:1080")


if __name__ == "__main__":
    unittest.main()
