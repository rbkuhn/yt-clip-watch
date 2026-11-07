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
    is_batch_url,
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

    def test_extract_urls_finds_instagram_reels_and_posts(self) -> None:
        text = (
            "https://www.instagram.com/reel/DAbc-12_x/?igsh=MTk2bXZ "
            "and https://youtu.be/abc123 and "
            "https://instagram.com/some.user/reels/XyZ987/ and "
            "https://www.instagram.com/reel/DAbc-12_x/?igsh=OTHER "
            "and https://www.instagram.com/p/Post_42/?img_index=1 "
            "but not https://www.instagram.com/some.user/"
        )
        self.assertEqual(
            extract_urls(text),
            [
                "https://www.instagram.com/reel/DAbc-12_x",
                "https://youtu.be/abc123",
                "https://instagram.com/some.user/reels/XyZ987",
                "https://www.instagram.com/p/Post_42",
            ],
        )

    def test_instagram_filenames_include_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = DownloadSettings(output_dir=Path(directory))
            reel = build_download_options(
                settings, url="https://www.instagram.com/reel/DAbc"
            )
            video = build_download_options(settings, url="https://youtu.be/abc123")
            self.assertTrue(reel["outtmpl"].endswith("%(title)s [%(id)s].%(ext)s"))
            self.assertTrue(video["outtmpl"].endswith("%(title)s.%(ext)s"))

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

    def test_single_videos_are_not_batches(self) -> None:
        for url in (
            "https://youtu.be/abc123",
            "https://youtu.be/abc123?list=PL123",
            "https://www.youtube.com/watch?v=abc123",
            "https://www.youtube.com/watch?v=abc123&list=PL123&index=2",
            "https://m.youtube.com/watch?v=abc123",
            "https://www.youtube.com/shorts/abc123",
            "https://www.youtube.com/live/abc123",
            "https://www.instagram.com/reel/DAbc",
        ):
            with self.subTest(url=url):
                self.assertFalse(is_batch_url(url))

    def test_playlists_and_channels_are_batches(self) -> None:
        for url in (
            "https://www.youtube.com/playlist?list=PL123",
            "https://www.youtube.com/@somechannel",
            "https://www.youtube.com/@somechannel/videos",
            "https://www.youtube.com/channel/UC123",
            "https://www.youtube.com/c/SomeName",
            "https://www.youtube.com/user/someone",
            "https://www.youtube.com/watch?list=PL123",
        ):
            with self.subTest(url=url):
                self.assertTrue(is_batch_url(url))

    def test_playlist_params_on_video_links_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = DownloadSettings(output_dir=Path(directory))
            self.assertTrue(build_download_options(settings)["noplaylist"])

    def test_restrict_filenames_option(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = DownloadSettings(
                output_dir=Path(directory),
                restrict_filenames=True,
            )
            self.assertTrue(build_download_options(settings)["restrictfilenames"])

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
