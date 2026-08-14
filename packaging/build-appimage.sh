#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BUILD_DIR=${BUILD_DIR:-"$ROOT/build"}
APPDIR=${APPDIR:-"$BUILD_DIR/AppDir"}
TOOLS_DIR=${TOOLS_DIR:-"$BUILD_DIR/tools"}
DIST_DIR=${DIST_DIR:-"$BUILD_DIR/dist"}
OUTPUT=${OUTPUT:-"$ROOT/yt-clip-watch-x86_64.AppImage"}
DOWNLOAD_TOOLS=${DOWNLOAD_TOOLS:-0}

# shellcheck disable=SC1091
. "$ROOT/packaging/versions.env"

fetch_checked() {
    local url=$1 output=$2 expected=$3
    if [ ! -f "$output" ]; then
        curl --fail --location --retry 3 --output "$output" "$url"
    fi
    printf '%s  %s\n' "$expected" "$output" | sha256sum --check --status
}

prepare_tools() {
    mkdir -p "$TOOLS_DIR"
    if [ "$DOWNLOAD_TOOLS" = 1 ]; then
        local cache="$BUILD_DIR/downloads"
        mkdir -p "$cache"
        fetch_checked \
            "https://github.com/denoland/deno/releases/download/$DENO_VERSION/$DENO_ARCHIVE" \
            "$cache/$DENO_ARCHIVE" "$DENO_SHA256"
        rm -rf "$TOOLS_DIR/deno-unpack"
        mkdir -p "$TOOLS_DIR/deno-unpack"
        unzip -q -o "$cache/$DENO_ARCHIVE" -d "$TOOLS_DIR/deno-unpack"
        install -m 0755 "$TOOLS_DIR/deno-unpack/deno" "$TOOLS_DIR/deno"

        fetch_checked \
            "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/$FFMPEG_ARCHIVE" \
            "$cache/$FFMPEG_ARCHIVE" "$FFMPEG_SHA256"
        rm -rf "$TOOLS_DIR/ffmpeg-unpack"
        mkdir -p "$TOOLS_DIR/ffmpeg-unpack"
        tar -xJf "$cache/$FFMPEG_ARCHIVE" -C "$TOOLS_DIR/ffmpeg-unpack"
        install -m 0755 "$TOOLS_DIR"/ffmpeg-unpack/ffmpeg-*/bin/ffmpeg "$TOOLS_DIR/ffmpeg"
        install -m 0755 "$TOOLS_DIR"/ffmpeg-unpack/ffmpeg-*/bin/ffprobe "$TOOLS_DIR/ffprobe"
        rm -rf "$TOOLS_DIR/deno-unpack" "$TOOLS_DIR/ffmpeg-unpack"
    fi
    test -x "$TOOLS_DIR/deno"
    test -x "$TOOLS_DIR/ffmpeg"
    test -x "$TOOLS_DIR/ffprobe"
}

rm -rf "$APPDIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"
python3 -m PyInstaller \
    --clean \
    --noconfirm \
    --onedir \
    --windowed \
    --name yt-clip-watch \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR/pyinstaller" \
    "$ROOT/main.py"

prepare_tools
mkdir -p "$APPDIR/usr/lib"
cp -a "$DIST_DIR/yt-clip-watch" "$APPDIR/usr/lib/yt-clip-watch"
cp -a "$TOOLS_DIR" "$APPDIR/usr/lib/yt-clip-watch/tools"
cp "$ROOT/packaging/AppRun" "$APPDIR/AppRun"
cp "$ROOT/packaging/yt-clip-watch.desktop" "$APPDIR/yt-clip-watch.desktop"
cp "$ROOT/packaging/yt-clip-watch.svg" "$APPDIR/yt-clip-watch.svg"
cp "$ROOT/packaging/THIRD_PARTY_NOTICES.txt" "$APPDIR/THIRD_PARTY_NOTICES.txt"
cp "$ROOT/LICENSE" "$APPDIR/LICENSE"
ln -sfn yt-clip-watch.svg "$APPDIR/.DirIcon"
chmod +x "$APPDIR/AppRun"

: "${APPIMAGETOOL:?Set APPIMAGETOOL to a pinned appimagetool executable}"
: "${APPIMAGE_RUNTIME:?Set APPIMAGE_RUNTIME to a pinned type-2 runtime file}"
"$APPIMAGETOOL" --runtime-file "$APPIMAGE_RUNTIME" "$APPDIR" "$OUTPUT"
chmod +x "$OUTPUT"
printf 'Wrote %s\n' "$OUTPUT"
