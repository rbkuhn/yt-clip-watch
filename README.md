# yt-clip-watch

A Linux desktop application that watches the clipboard for YouTube URLs and downloads them with yt-dlp. The GUI queues one URL at a time, shows progress, and remembers its output folder and download archive.

## AppImage

The supported distribution target is Linux x86-64 on Ubuntu 22.04 or newer. The AppImage bundles Python, PySide6, yt-dlp, matching EJS scripts, Deno, FFmpeg, and FFprobe. It still uses host browser profiles and keyring/session services when browser cookies are enabled.

1. Download the `yt-clip-watch-x86_64.AppImage` release asset.
2. Mark it executable:

   ```bash
   chmod +x yt-clip-watch-x86_64.AppImage
   ```

3. Run it:

   ```bash
   ./yt-clip-watch-x86_64.AppImage
   ```

The application starts with clipboard watching disabled. Choose a download folder, click **Start Watching**, then copy YouTube URLs. The manual URL field is available when a Wayland compositor does not report passive clipboard changes reliably.

If FUSE is unavailable on the host, extract and run the AppImage instead:

```bash
./yt-clip-watch-x86_64.AppImage --appimage-extract
./squashfs-root/AppRun
```

The AppImage is not a sandbox and does not package browser logins. Use browser cookies only when necessary; exported or readable cookies can contain credentials and may trigger account enforcement by YouTube.

## Source development

Python 3.10 or newer is required. Install the runtime dependencies in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Source runs use Deno when it is available, otherwise Node 22 or newer. FFmpeg and FFprobe are required for merging separate video and audio streams. The AppImage build bundles these tools explicitly.

Launch the source GUI with:

```bash
python main.py
```

Run the focused core tests with:

```bash
python -m unittest discover -s tests -v
```

## Building the AppImage

Builds target Ubuntu 22.04 x86-64. Install the pinned Python build dependencies first:

```bash
python -m pip install -r requirements.txt -r requirements-build.txt
```

The build also requires `curl`, `unzip`, `xz`, a pinned `appimagetool`, and a pinned type-2 AppImage runtime. Set their paths explicitly:

```bash
APPIMAGETOOL=/path/to/appimagetool \
APPIMAGE_RUNTIME=/path/to/runtime-x86_64 \
DOWNLOAD_TOOLS=1 \
packaging/build-appimage.sh
```

`packaging/versions.env` records the pinned Deno, FFmpeg, AppImage tool, runtime URLs, and SHA-256 values. The script verifies downloaded tools before placing them in the AppDir. The generated AppImage is written to `yt-clip-watch-x86_64.AppImage`.

GitHub Actions builds the same x86-64 artifact in an Ubuntu 22.04 container. Tagged builds upload the tested AppImage and checksum as a release asset.

## Runtime data

- Downloads go to the folder selected in the GUI.
- Qt stores GUI settings through `QSettings`.
- The persistent yt-dlp archive is stored below the platform application-data directory when enabled.
- The AppImage mount is read-only; application data never belongs inside it.

## Licensing

The application source is released under the [MIT License](LICENSE).
The release includes `THIRD_PARTY_NOTICES.txt` with the Qt, yt-dlp/EJS, Deno, and FFmpeg sources and distribution obligations. Review the licenses for the exact frozen dependency versions before publishing an AppImage.
