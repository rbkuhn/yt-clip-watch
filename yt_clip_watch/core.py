"""Pure downloader configuration and URL handling."""

from __future__ import annotations

import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

YOUTUBE_URL_RE = re.compile(
    r"https?://(?:[\w-]+\.)?(?:youtube\.com|youtu\.be)/[^\s<>'\"()]+",
    re.IGNORECASE,
)
RESOLUTION_CHOICES = (360, 480, 720, 1080)
DEFAULT_SORT_TEMPLATE = "res:{resolution},ext:mp4:m4a"

@dataclass(frozen=True, slots=True)
class RuntimePaths:
    """Executable paths used by yt-dlp post-processing and EJS."""

    js_runtime: Path | None = None
    js_runtime_name: str = "deno"
    ffmpeg: Path | None = None


@dataclass(frozen=True, slots=True)
class DownloadSettings:
    """Immutable settings for one downloader queue."""

    output_dir: Path
    resolution: int = 360
    sort_value: str | None = None
    browser: str | None = None
    archive_path: Path | None = None
    runtime_paths: RuntimePaths = RuntimePaths()

    def __post_init__(self) -> None:
        output_dir = Path(self.output_dir).expanduser()
        if self.resolution not in RESOLUTION_CHOICES:
            raise ValueError(f"resolution must be one of {RESOLUTION_CHOICES}")
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        if not output_dir.is_dir():
            raise ValueError(f"output directory is not a directory: {output_dir}")
        object.__setattr__(self, "output_dir", output_dir.resolve())
        if self.archive_path is not None:
            archive_path = Path(self.archive_path).expanduser()
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            object.__setattr__(self, "archive_path", archive_path)


def extract_urls(text: str) -> list[str]:
    """Return unique YouTube URLs in first-seen order."""

    urls: list[str] = []
    for match in YOUTUBE_URL_RE.findall(text):
        cleaned = match.rstrip(".,;:!?)]}\"'")
        if cleaned not in urls:
            urls.append(cleaned)
    return urls


def build_sort_value(settings: DownloadSettings) -> str:
    return settings.sort_value or DEFAULT_SORT_TEMPLATE.format(
        resolution=settings.resolution
    )


def build_ydl_options(
    settings: DownloadSettings,
    *,
    logger: Any = None,
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
    postprocessor_hook: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Translate app settings into the public YoutubeDL option dictionary."""
    options: dict[str, Any] = {
        "format_sort": [part.strip() for part in build_sort_value(settings).split(",") if part.strip()],
        "outtmpl": str(settings.output_dir / "%(title)s.%(ext)s"),
        "paths": {"home": str(settings.output_dir)},
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "js_runtimes": {
            settings.runtime_paths.js_runtime_name: (
                {"path": str(settings.runtime_paths.js_runtime)}
                if settings.runtime_paths.js_runtime
                else {}
            )
        },
    }
    if settings.runtime_paths.ffmpeg:
        options["ffmpeg_location"] = str(settings.runtime_paths.ffmpeg)
    if settings.browser:
        options["cookiesfrombrowser"] = (settings.browser,)
    if settings.archive_path:
        options["download_archive"] = str(settings.archive_path)
    if logger is not None:
        options["logger"] = logger
    if progress_hook is not None:
        options["progress_hooks"] = [progress_hook]
    if postprocessor_hook is not None:
        options["postprocessor_hooks"] = [postprocessor_hook]
    return options


def _find_executable(name: str, *, packaged_dir: Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if packaged_dir:
        candidates.append(packaged_dir / name)
    configured = os.environ.get(f"YT_CLIP_WATCH_{name.upper()}")
    if configured:
        candidates.append(Path(configured).expanduser())
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def resolve_runtime_paths() -> RuntimePaths:
    """Find packaged tools first, then development-host tools."""

    if getattr(sys, "frozen", False):
        bundled_dir = Path(sys.executable).resolve().parent / "tools"
        js_runtime = _find_executable("deno", packaged_dir=bundled_dir)
        js_runtime_name = "deno"
        ffmpeg = _find_executable("ffmpeg", packaged_dir=bundled_dir)
    else:
        js_runtime = _find_executable("deno")
        js_runtime_name = "deno"
        if js_runtime is None:
            js_runtime = _find_executable("node")
            js_runtime_name = "node"
        ffmpeg = _find_executable("ffmpeg")

    return RuntimePaths(
        js_runtime=js_runtime,
        js_runtime_name=js_runtime_name,
        ffmpeg=ffmpeg,
    )


def validate_runtime_paths(paths: RuntimePaths) -> list[str]:
    missing = []
    if paths.js_runtime is None:
        missing.append("a JavaScript runtime (Deno recommended; Node is supported for source runs)")
    if paths.ffmpeg is None:
        missing.append("ffmpeg")
    return missing


def build_download_options(
    settings: DownloadSettings,
    *,
    logger: Any = None,
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
    postprocessor_hook: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Compatibility alias with a name that reads well at call sites."""

    return build_ydl_options(
        settings,
        logger=logger,
        progress_hook=progress_hook,
        postprocessor_hook=postprocessor_hook,
    )
