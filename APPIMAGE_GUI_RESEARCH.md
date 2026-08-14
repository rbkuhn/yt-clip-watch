# AppImage GUI research

**Snapshot:** 2026-08-14. “Verified” statements below come from official documentation, specifications, package indexes, or upstream source. “Analysis” sections identify implications and unresolved choices. The recommended implementation plan follows the research. Licensing notes are not legal advice.

## Verified facts

### PySide6 / Qt for Python

- PySide6 is the official Qt 6 Python binding. Qt for Python is offered under LGPLv3/GPLv3 or the Qt commercial license; current wheels are installed with `pip install pyside6`. ([Qt for Python overview](https://doc.qt.io/qtforpython-6/))
- The `pyside6` wheel is a metapackage over `PySide6-Essentials`, `PySide6-Addons`, and `shiboken6`. Essentials/Addons contain the Qt shared libraries as well as the Python extension modules, so freezing and redistributing an application also redistributes Qt binaries. ([package details](https://doc.qt.io/qtforpython-6/package_details.html))
- Current PySide6 6.11.1 metadata requires Python 3.10–3.14. Its binary Essentials wheels are tagged `manylinux_2_34_x86_64` and `manylinux_2_39_aarch64`; under the manylinux specification those tags mean glibc 2.34+ and 2.39+ respectively. These floors apply even if the application itself is built on an older system. ([PySide6 metadata](https://pypi.org/pypi/PySide6/6.11.1/json), [Essentials files](https://pypi.org/pypi/PySide6_Essentials/6.11.1/json), [manylinux specification](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/#manylinux))
- Qt’s LGPL guidance says a proprietary application can normally remain closed when it dynamically links to LGPL Qt, but distribution must preserve the user’s ability to replace/relink the library and run the modified result; it also requires corresponding library source or an offer/instructions, the LGPL text, and prominent notice. Some Qt components are GPL-only, and third-party components have their own terms. ([Qt LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations), [Qt for Python third-party licenses](https://doc.qt.io/qtforpython-6/licenses.html))
- Qt’s own deployment frontend, `pyside6-deploy`, wraps Nuitka and produces a Linux `.bin` or standalone directory, not an AppImage. Qt also lists PyInstaller as a deployment option, but its PyInstaller page retains a contradictory March 2021 Qt 6 warning; current PyInstaller documentation/source is the better authority for PyInstaller support. ([Qt deployment overview](https://doc.qt.io/qtforpython-6/deployment/index.html), [`pyside6-deploy`](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html), [dated PyInstaller page](https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html))

### Clipboard, threading, and process facilities

- An application has one `QClipboard`, obtained from `QGuiApplication.clipboard()`. `text()`/`mimeData()` read content; `dataChanged()`, `selectionChanged()`, and `changed(mode)` report changes. X11 has separate clipboard and primary-selection stores, and `supportsSelection()` must be checked. ([QClipboard](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QClipboard.html))
- Qt warns that X11 ownership changes do not normally notify every application, that clipboard operation requires a running event loop, and that retrieval should preferably happen in direct response to user input rather than a timer. Current Qt XCB source subscribes to external owner changes only when XFixes is available. Qt gives no equivalent guarantee that every background change is observed on every Wayland compositor. ([QClipboard platform notes](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QClipboard.html), [Qt 6.11 XCB implementation](https://code.qt.io/cgit/qt/qtbase.git/tree/src/plugins/platforms/xcb/qxcbclipboard.cpp?h=6.11))
- Widgets belong in the main thread. Qt documents moving a worker `QObject` to a `QThread` and returning results through queued signals; the `QThread` object itself remains in its creator’s thread. `requestInterruption()` is advisory and worker code must cooperate; forced termination is discouraged. ([Qt thread/object rules](https://doc.qt.io/qt-6/threads-qobject.html), [QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html))
- `QProcess` starts and communicates with an external program asynchronously. It exposes started/finished/error and incremental stdout/stderr signals plus `terminate()`/`kill()`. Qt warns that `waitFor…()` calls from the application thread may freeze the UI. ([QProcess](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html))

### Brief GUI comparison

| Option | Source-grounded comparison |
|---|---|
| **PySide6** | Supplies the clipboard signals, thread primitives, and asynchronous process API above in one toolkit. It carries Qt binaries and LGPL/GPL/commercial compliance obligations. ([Qt for Python](https://doc.qt.io/qtforpython-6/), [Qt APIs](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html)) |
| **Tkinter/ttk** | Python’s standard Tcl/Tk interface is available on most Unix systems but is an optional CPython module. Classic widgets are documented as dated; ttk supplies themed widgets. Its single-threaded event handlers must return quickly, with long work split by timers or moved to another thread. ([Tkinter](https://docs.python.org/3/library/tkinter.html), [threading model](https://docs.python.org/3/library/tkinter.html#threading-model)) |
| **PyQt6** | Exposes the same Qt family, but Riverbank licenses PyQt under GPLv3 or a commercial license and explicitly does not offer LGPL; its binary wheels include corresponding LGPL Qt. ([Riverbank PyQt overview](https://riverbankcomputing.com/software/pyqt)) |
| **PyGObject/GTK** | The project is LGPLv2.1+, but its official deployment guide says Linux has no single, polished deployment strategy and only points to examples for PyInstaller/AppImageKit. ([PyGObject](https://pygobject.gnome.org/), [deployment guide](https://pygobject.gnome.org/guide/deploy.html)) |

### PyInstaller on Linux

- PyInstaller bundles the active Python interpreter, imported modules, and collected libraries. Output is specific to the build OS, Python, word size, and architecture; PyInstaller is not a cross-compiler. ([operating mode](https://pyinstaller.org/en/stable/operating-mode.html), [multi-OS guidance](https://pyinstaller.org/en/stable/usage.html#supporting-multiple-operating-systems))
- `--onedir` is the default: it creates one executable plus its supporting tree. Since PyInstaller 6, supporting files normally live under `_internal`, and POSIX bundles use symlinks extensively; AppDir staging must preserve the whole relative tree and those links. ([one-folder mode](https://pyinstaller.org/en/stable/operating-mode.html#bundling-to-one-folder), [`--contents-directory`](https://pyinstaller.org/en/stable/usage.html#cmdoption-contents-directory), [symlink requirements](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#requirements-imposed-by-symbolic-links-in-frozen-application))
- PyInstaller deliberately does not bundle glibc. It says to build on the oldest GNU/Linux release to be supported; newer-built bundles may fail on older hosts. Other collected libraries can still conflict with host graphics/driver libraries. ([Linux forward compatibility](https://pyinstaller.org/en/stable/usage.html#making-gnu-linux-apps-forward-compatible))
- Current PyInstaller 6.22.0 has first-party PySide6 hooks which collect Shiboken and dependency-selected Qt libraries/plugins; upstream also tests frozen Qt Widgets and PySide6 module imports. Only one Qt binding may be collected in a bundle. ([PySide6 hook](https://github.com/pyinstaller/pyinstaller/blob/v6.22.0/PyInstaller/hooks/hook-PySide6.py), [Qt hook core](https://github.com/pyinstaller/pyinstaller/blob/v6.22.0/PyInstaller/utils/hooks/qt/__init__.py), [Qt tests](https://github.com/pyinstaller/pyinstaller/blob/v6.22.0/tests/functional/test_qt.py))
- On Linux, PyInstaller prepends the bundle directory to `LD_LIBRARY_PATH`; child processes inherit it. PyInstaller warns that host-installed programs may then load incompatible bundled libraries and says external programs may need `LD_LIBRARY_PATH` cleared or restored from `LD_LIBRARY_PATH_ORIG`. ([external-program warning](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#launching-external-programs-from-the-frozen-application))

### AppImage and AppDir

- A type-2 AppImage is an ELF runtime plus a SquashFS image. The runtime mounts the image read-only through FUSE and executes root-level `AppRun`; application data, downloads, configuration, and caches therefore must be written outside the image. ([architecture](https://docs.appimage.org/reference/architecture.html))
- The stricter official AppDir reference requires root-level `AppRun`, `.DirIcon`, exactly one `*.desktop`, and a root icon. The desktop file/icon may be relative symlinks into `usr/share/applications` and `usr/share/icons`; the icon filename must match `Icon=` while the desktop value omits the extension. The recommended payload tree uses `usr/bin`, `usr/lib`, and `usr/share`. ([AppDir reference](https://docs.appimage.org/reference/appdir.html))
- Desktop metadata enables integration but does not install or register the AppImage by itself. Integration is performed by a desktop/helper such as AppImageLauncher or `appimaged`, normally with user participation. ([desktop integration](https://docs.appimage.org/user-guide/run-appimages.html#integrating-appimages-into-the-desktop))
- `appimagetool` is the low-level converter for an already complete AppDir. It needs/infers an architecture-specific runtime and, by default, downloads the latest runtime while building; `--runtime-file` supplies a fixed local runtime. ([appimagetool README](https://github.com/AppImage/appimagetool#usage), [environment variables/changelog](https://github.com/AppImage/appimagetool#environment-variables))
- `linuxdeploy` can populate an AppDir, copy executables/libraries/desktop files/icons, and run input/output plugins; its AppImage output delegates to `appimagetool`. It cannot discover arbitrary data, hard-coded resources, or every runtime-loaded plugin, so those remain explicit packaging inputs. It also does not alter `$PATH`; bundled helper executables must be found relative to the application. ([linuxdeploy guide](https://docs.appimage.org/packaging-guide/from-source/linuxdeploy-user-guide.html), [upstream README](https://github.com/linuxdeploy/linuxdeploy), [native-packaging limitations](https://docs.appimage.org/packaging-guide/from-source/native-binaries.html#packaging-existing-binaries-or-manually-packaging-everything))
- AppImage is not a compatibility layer: official guidance still says to build on the oldest supported target and bundle non-base dependencies. glibc, the dynamic loader, and driver-facing libraries are normally host dependencies, and each CPU architecture needs a matching runtime and payload. ([AppImage concepts](https://docs.appimage.org/introduction/concepts.html), [appimagetool architectures](https://github.com/AppImage/appimagetool/blob/main/src/appimagetool.c#L62-L67))
- The current type-2 runtime statically includes its userspace FUSE dependency, but still needs usable kernel FUSE/`fusermount`; locked-down hosts and containers may need extract-and-run. AppImage documentation calls extract-and-run expensive and warns against granting broad Docker capabilities merely to enable FUSE. ([type2 runtime](https://github.com/AppImage/type2-runtime), [FUSE fallback/container guidance](https://docs.appimage.org/user-guide/troubleshooting/fuse.html#fallback-if-fuse-cant-be-made-working))

### GitHub Actions build/distribution guidance

- GitHub currently maps `ubuntu-latest` to 24.04, offers explicit 22.04/24.04 labels, updates GA images weekly, and migrates `-latest` over time. An explicit label prevents OS-generation migration but not weekly image drift. A job container is the first-party way to select a different fixed userland on an Ubuntu runner. ([runner images](https://github.com/actions/runner-images#available-images), [migration/cadence](https://github.com/actions/runner-images#latest-migration-process), [job containers](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idcontainer))
- Upstream appimagetool and linuxdeploy workflows demonstrate architecture matrices, Docker-based builds, and Actions artifact upload. They are credible build examples, not immutable supply-chain templates. ([appimagetool workflow](https://github.com/AppImage/appimagetool/blob/main/.github/workflows/build.yml), [linuxdeploy workflow](https://github.com/linuxdeploy/linuxdeploy/blob/master/.github/workflows/main.yml))
- GitHub says a full commit SHA is the only immutable reference for an action and recommends least-privilege `GITHUB_TOKEN` permissions. `contents: write` permits release creation; `gh release create` can attach release assets using the preinstalled GitHub CLI. ([secure action use](https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions), [workflow permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions), [GitHub CLI in workflows](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-github-cli), [`gh release create`](https://cli.github.com/manual/gh_release_create))
- Workflow artifacts are temporary CI outputs with configurable retention; release assets are the end-user distribution surface. GitHub also supports binary provenance attestations, while AppImage’s embedded GPG signature requires an external verifier. ([Actions artifacts](https://docs.github.com/en/actions/tutorials/store-and-share-data), [artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations#generating-build-provenance-for-binaries), [AppImage signatures](https://docs.appimage.org/packaging-guide/optional/signatures.html#validating-the-signature))

### yt-dlp runtime and embedding

- The current stable source snapshot is yt-dlp 2026.07.04 and requires Python 3.10+. Upstream supports Python embedding through `yt_dlp.YoutubeDL` with option dictionaries, `download()`, `extract_info()`, `sanitize_info()`, a custom logger, `progress_hooks`, and separate `postprocessor_hooks`. A download hook’s `finished` event precedes possible merge/conversion work. ([version/metadata](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/pyproject.toml), [embedding examples](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/README.md#embedding-yt-dlp), [hook contract](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/YoutubeDL.py#L398-L440))
- Upstream warns not to parse normal CLI stdout because it may change; a subprocess integration should request reproducible output with `--print`/`--progress-template` or equivalent. There is no documented stable API for cancelling an in-flight embedded transfer: `DownloadCancelled` is documented for `match_filter`, while aborting from a progress-hook exception is only current implementation behavior. ([embedding warning](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/README.md#embedding-yt-dlp), [documented cancellation](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/YoutubeDL.py#L461-L469), [hook implementation](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/downloader/common.py#L488-L500))
- Cookies may come from a Netscape-format cookie file or directly from supported browser/profile/keyring/container selectors. Linux extraction reads live host browser databases, including conventional and sandboxed-browser profile locations; encrypted Chromium cookies may require the user’s GNOME Keyring or KWallet, session D-Bus, and optional `secretstorage`. Exporting browser cookies to a file may export credentials for all sites. ([cookie options](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/README.md#authentication-options), [cookie implementation](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/cookies.py), [cookie FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp))
- yt-dlp warns that logged-in YouTube cookies are only needed for account-gated content and that account use may cause temporary or permanent bans. YouTube is also gradually requiring externally supplied PO Tokens; yt-dlp cannot generate them, so some formats/features may remain unavailable regardless of packaging. ([YouTube extractor guidance](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies))
- FFmpeg and FFprobe **binaries** are strongly recommended and are required for merging separate video/audio and many post-processing tasks; the Python package named `ffmpeg` is not a substitute. `ffmpeg_location` accepts a binary or containing directory, so the pair may be bundled, but FFmpeg’s effective LGPL/GPL obligations depend on the chosen build. ([yt-dlp dependencies](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/README.md#dependencies), [resolver](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/postprocessor/ffmpeg.py#L102-L128), [FFmpeg legal page](https://ffmpeg.org/legal.html))
- Full YouTube support now requires the matching `yt-dlp-ejs` scripts plus an external JavaScript runtime. Deno 2.3+ is recommended and enabled by default; Node 22+ and QuickJS/QuickJS-NG require explicit enablement; Bun support is deprecated. The EJS package must track the yt-dlp version and stale versions may be ignored. ([EJS guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS), [runtime floors](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/utils/_jsruntime.py#L89-L153))
- yt-dlp’s PyInstaller hook collects `yt-dlp-ejs` JavaScript data, and explicit paths are supported for both JS runtimes and FFmpeg. Remote EJS downloads are disabled by default unless explicitly allowed. The yt-dlp wheel is Unlicense, but bundled EJS, FFmpeg, JS runtime, Qt, and other frozen dependencies retain their own licenses. ([yt-dlp hook](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/__pyinstaller/hook-yt_dlp.py), [remote components](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/README.md#general-options), [release licensing](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/README.md#licensing))

## Bundle boundary

| Can be included in the AppImage | Must remain host/user-session state |
|---|---|
| PyInstaller `onedir` tree: CPython, application code, imported PySide6/Qt libraries/plugins, yt-dlp, and `yt-dlp-ejs` data. ([PyInstaller](https://pyinstaller.org/en/stable/operating-mode.html), [yt-dlp hook](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/__pyinstaller/hook-yt_dlp.py)) | Browser profiles, cookie databases/files, login state, and user secrets. The application may read them only at runtime with the user’s host permissions. ([yt-dlp cookie implementation](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/cookies.py)) |
| Architecture-matched FFmpeg/FFprobe and a supported JS runtime such as Deno, located by explicit packaged paths. ([FFmpeg resolver](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/postprocessor/ffmpeg.py#L102-L128), [EJS guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS)) | GNOME Keyring/KWallet services and secrets, session D-Bus, and any browser/compositor portals. Bundling client libraries does not bundle these live services. ([keyring source](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/cookies.py#L915-L990)) |
| `AppRun`, desktop file, icons, license notices, and corresponding-source instructions. ([AppDir reference](https://docs.appimage.org/reference/appdir.html), [Qt obligations](https://www.qt.io/development/open-source-lgpl-obligations)) | Writable download/config/cache/temp directories; kernel FUSE support; host glibc, graphics drivers, and other intentionally excluded base libraries. ([AppImage architecture](https://docs.appimage.org/reference/architecture.html), [AppImage concepts](https://docs.appimage.org/introduction/concepts.html)) |
| A user-supplied cookie file can be selected from the host, but credentials should not be baked into a public immutable image. The file format and all-sites export risk are documented upstream. ([cookie FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)) | PO Tokens and other service/account state that yt-dlp cannot generate. ([YouTube extractor notice](https://github.com/yt-dlp/yt-dlp/wiki/Extractors)) |

The AppImage runtime merely mounts the payload and asks the OS to execute `AppRun`; it neither packages browser state nor grants permission to read it. Therefore cookie/profile access depends on the launching user and can be denied by an external sandbox or host policy. ([AppImage architecture](https://docs.appimage.org/reference/architecture.html), [yt-dlp profile access](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/cookies.py))

## Tradeoff analysis (not a plan)

- **Embedded yt-dlp vs child process:** embedding provides structured logger/progress/postprocessor callbacks and avoids parsing CLI output, but blocking work belongs in a `QThread` worker and in-flight cancellation has no stable supported yt-dlp API. A `QProcess` child provides asynchronous I/O, exit status, and OS signals without another Qt thread, but must use yt-dlp’s machine-oriented output options; stopping `QProcess` is not documented to stop descendants such as FFmpeg. ([yt-dlp embedding](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/README.md#embedding-yt-dlp), [QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html), [QProcess](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html))
- **PyInstaller `onedir` vs nested one-file:** an intact `onedir` tree is directly suitable as an AppDir payload and avoids a second self-extraction layer inside the AppImage. Its `_internal` layout and symlinks become load-bearing. This is an architectural inference from PyInstaller’s runtime model, not an AppImage guarantee. ([one-folder/one-file behavior](https://pyinstaller.org/en/stable/operating-mode.html))
- **`appimagetool` vs `linuxdeploy`:** direct `appimagetool` is sufficient only after the AppDir is complete. `linuxdeploy` can place metadata and discover native dependencies, but cannot replace PyInstaller’s Python/Qt hooks or discover every data/plugin/helper resource. ([appimagetool](https://github.com/AppImage/appimagetool), [linuxdeploy limitations](https://docs.appimage.org/packaging-guide/from-source/native-binaries.html#packaging-existing-binaries-or-manually-packaging-everything))
- **Toolkit choice:** PySide6 has the deepest source-backed clipboard/process/thread fit. Tkinter avoids a third-party Python binding but remains an optional Tcl/Tk payload and has a shallower documented clipboard/process surface; PyQt6 changes the binding license to GPL/commercial; PyGObject’s own guide acknowledges a weaker portable-deployment story. ([QClipboard/QProcess](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QClipboard.html), [Tkinter](https://docs.python.org/3/library/tkinter.html), [PyQt license](https://riverbankcomputing.com/software/pyqt), [PyGObject deployment](https://pygobject.gnome.org/guide/deploy.html))

## Explicit unresolved risks

1. **Supported Linux matrix:** decide CPU architectures and oldest distributions first. Current PySide6 wheel floors differ (`glibc` 2.34 x86_64 vs 2.39 aarch64), and neither PyInstaller nor AppImage removes them. ([PySide6 files](https://pypi.org/pypi/PySide6_Essentials/6.11.1/json), [PyInstaller Linux guidance](https://pyinstaller.org/en/stable/usage.html#making-gnu-linux-apps-forward-compatible))
2. **Clipboard reliability:** passive global monitoring must be proven on target X11 (with/without XFixes) and Wayland compositors; Qt does not promise every external background change. ([QClipboard](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QClipboard.html), [XCB source](https://code.qt.io/cgit/qt/qtbase.git/tree/src/plugins/platforms/xcb/qxcbclipboard.cpp?h=6.11))
3. **Dynamic resources:** Qt platform/image/TLS plugins, Python data, FFmpeg, JS runtime, and other runtime-loaded resources can escape static dependency discovery. Image creation succeeding is not target-host proof. ([PyInstaller Qt hook](https://github.com/pyinstaller/pyinstaller/blob/v6.22.0/PyInstaller/utils/hooks/qt/__init__.py), [linuxdeploy limitations](https://docs.appimage.org/packaging-guide/from-source/native-binaries.html#packaging-existing-binaries-or-manually-packaging-everything))
4. **Cookie security and availability:** browser paths vary across native/Flatpak/Snap installs; encrypted Chromium cookies depend on the live keyring/session; exported files may contain all-site credentials; YouTube warns of account bans. ([cookie source](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/cookies.py), [cookie FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp), [YouTube guidance](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies))
5. **Upstream churn:** a fixed image couples yt-dlp, matching EJS, JS-runtime floors, and changing YouTube behavior/PO Tokens. A release/update policy is required, but is outside this research. ([EJS version warning](https://github.com/yt-dlp/yt-dlp/wiki/EJS), [PO Token notice](https://github.com/yt-dlp/yt-dlp/wiki/Extractors))
6. **Cancellation:** embedded in-flight cancellation is undocumented; a killed yt-dlp process may leave an FFmpeg descendant or partial files. ([yt-dlp cancellation contract](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/YoutubeDL.py#L461-L469), [QProcess](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html))
7. **Licensing:** the exact Qt modules/plugins, FFmpeg build configuration, EJS/runtime, Python packages, and third-party notices determine the final AppImage obligations. LGPL replacement/relink rights must remain practical despite the one-file outer format. ([Qt obligations](https://www.qt.io/development/open-source-lgpl-obligations), [FFmpeg legal](https://ffmpeg.org/legal.html), [yt-dlp licensing](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/README.md#licensing))
8. **Packaging/runtime drift:** current AppImage specifications/guides contain stale or conflicting details, appimagetool fetches a latest runtime by default, linuxdeploy publishes a mutable `continuous` build, and GitHub runner images update weekly. Tool/runtime/container/action identities and hashes must be controlled for reproducible releases. ([AppImage specification status](https://docs.appimage.org/reference/specification.html), [appimagetool changelog](https://github.com/AppImage/appimagetool#changelog), [linuxdeploy releases](https://github.com/linuxdeploy/linuxdeploy/releases/tag/continuous), [runner cadence](https://github.com/actions/runner-images#image-releases))
9. **Host execution:** kernel FUSE may be unavailable, desktop integration is optional, and host FFmpeg or other subprocesses may fail under PyInstaller’s inherited library path. ([FUSE guidance](https://docs.appimage.org/user-guide/troubleshooting/fuse.html), [desktop integration](https://docs.appimage.org/user-guide/run-appimages.html#integrating-appimages-into-the-desktop), [PyInstaller subprocess warning](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#launching-external-programs-from-the-frozen-application))

## Recommended direction

Build a Linux x86-64 Qt Widgets application with **PySide6**, embed yt-dlp through its Python interface, freeze it as a **PyInstaller `onedir`** bundle, and place that intact bundle in an AppDir converted with **appimagetool**.

| Decision | Reason |
|---|---|
| PySide6 Qt Widgets | One maintained toolkit supplies the window, native clipboard access, settings, file dialogs, signals, and worker-thread integration. It is a better fit than adding separate clipboard/process packages around Tkinter. |
| Embedded `yt_dlp.YoutubeDL` | Structured logger and progress hooks avoid parsing unstable console text and avoid shipping a second Python runtime inside a standalone yt-dlp executable. |
| One worker thread, one download at a time | Preserves the current queue semantics, keeps widgets on the main thread, and avoids unnecessary parallel-download controls. |
| No in-flight cancel button initially | Embedded yt-dlp has no documented stable cancellation interface. “Stop watching” will stop accepting clipboard jobs; the current job may finish. |
| PyInstaller `onedir`, not `onefile` | AppImage already supplies the one-file outer container. A nested one-file executable would add another extraction layer. |
| Explicitly bundled Deno and FFmpeg/FFprobe | Current yt-dlp requires an external JS runtime for full YouTube support and needs FFmpeg for separate video/audio streams. The current Bun default is deprecated. |
| Ubuntu 22.04 x86-64 baseline | Building in the chosen Ubuntu 22.04 container gives a provisional glibc 2.35 floor; the final artifact must be measured and tested. ARM should wait for a separately built artifact and host matrix. |
| Manual/versioned releases first | yt-dlp, EJS, Deno, and YouTube behavior change frequently. Reproducible pinned releases are necessary; an in-app updater is not. |

### Alternatives rejected

- **Tkinter:** smaller Python dependency surface, but Tcl/Tk remains a native payload and its documented clipboard/process facilities are a weaker fit for this application.
- **PyQt6:** no technical gain here and a less suitable GPL/commercial binding license.
- **PyGObject:** upstream acknowledges the Linux portable-deployment story is not polished.
- **`pyside6-deploy`:** useful for a standalone Nuitka executable but does not produce an AppImage; it adds a compiler/deployment layer without removing the AppDir work.
- **QProcess plus a bundled yt-dlp executable:** easier hard termination, but duplicates Python and requires machine-output parsing. Revisit only if reliable cancellation becomes a requirement.
- **PyInstaller `onefile` inside AppImage:** redundant extraction and slower startup for no user-visible gain.

## Proposed application behavior

The first GUI should preserve the useful behavior of `yt-clip-watch` while removing command-line-only and host-tool assumptions:

1. Launch into a single window with clipboard watching **off** so opening the app cannot unexpectedly download the current clipboard.
2. Let the user choose an output folder; default to Qt's Movies location and remember the choice with `QSettings`.
3. Provide a target-resolution selector for 360p, 480p, 720p, and 1080p.
4. Default browser cookies to **None**. Offer supported browser selection for age/account-gated content, with a warning that account cookies can expose credentials and trigger YouTube account enforcement.
5. Provide **Start Watching** / **Stop Watching**. On `QClipboard.dataChanged`, extract YouTube URLs, deduplicate them, and enqueue them.
6. Include a URL field and **Add** button as an explicit fallback when a compositor does not reliably report passive clipboard changes.
7. Show queued, downloading, post-processing, complete, and failed states plus progress and the latest error.
8. Process one URL at a time. Stopping clipboard watching does not abort the active job. Closing while work remains should offer “wait for downloads” or “quit after the current job”; it must not silently corrupt a partial download.
9. Use a persistent yt-dlp archive in the writable application-data directory by default so completed URLs are not downloaded again across launches. Allow the user to disable it.
10. Use bundled Deno and FFmpeg through explicit paths. Do not expose a JavaScript-runtime selector in the normal UI.

Remove CLI-only controls that no longer earn their interface cost: `--poll-interval`, `--once`, and the default Bun selector. Keep custom yt-dlp sort syntax only under an Advanced section if existing use proves it is needed.

## Module and file shape

Keep the implementation small; no plugin system, dependency-injection framework, or abstract base classes.

```text
yt_clip_watch/
  __init__.py
  core.py          # URL extraction, immutable download settings, yt-dlp option construction
  downloader.py    # one queued worker around YoutubeDL; progress/result signals
  gui.py           # Qt window, clipboard events, settings, queue presentation
main.py            # QApplication setup and entry point
packaging/
  AppRun
  yt-clip-watch.desktop
  yt-clip-watch.svg
  build-appimage.sh
requirements.txt
requirements-build.txt
```

The important seam is the downloader module. Its small interface should be:

- enqueue one URL with immutable settings;
- stop accepting new work / finish current work;
- emit structured progress, completion, and failure results.

Queueing, yt-dlp options, archive use, Deno/FFmpeg paths, logger adaptation, and exception normalization stay behind that interface. The GUI must not construct yt-dlp dictionaries or parse yt-dlp strings. Tests exercise URL extraction and the downloader option/result interface; they do not reach through it.

The old extensionless `yt-clip-watch` script may remain temporarily as a behavior reference, then must be removed when the GUI/AppImage path passes the same download smoke test. Do not retain two permanent implementations.

## Phased implementation plan

### Phase 1 — Extract the downloader core

1. Create the package and move `extract_urls`, resolution sorting, archive handling, and download behavior out of the CLI script.
2. Replace the `yt-dlp` subprocess with `yt_dlp.YoutubeDL`.
3. Add a custom logger and progress/postprocessor hooks that produce structured events.
4. Add explicit dependency discovery: packaged Deno and FFmpeg paths when launched from AppImage, host paths during source development.
5. Change the runtime requirement to `yt-dlp[default]` so the matching EJS package is installed.

**Acceptance:** focused tests cover URL deduplication, resolution/custom-sort precedence, output/archive paths, cookie options, packaged tool paths, completed downloads, and normalized yt-dlp failure results. A source-run smoke test downloads and post-processes one small public video without calling the old CLI executable.

### Phase 2 — Build the GUI

1. Implement the main window and settings listed under “Proposed application behavior.”
2. Connect `QClipboard.dataChanged` only while watching; ignore clipboard contents that predate Start Watching.
3. Move a `QObject` downloader worker to one `QThread`; send all widget changes back through queued signals.
4. Keep duplicate detection in the downloader module so clipboard and manual entry share one rule.
5. Make shutdown explicit and ensure the worker thread is joined before Qt exits.

**Acceptance:** source-run GUI remains responsive during a real download; manual entry and new clipboard URLs use the same queue; duplicate URLs do not create duplicate jobs; errors appear in the window; settings survive restart. Exercise the actual GUI on both X11 and Wayland, including the manual fallback.

### Phase 3 — Create a reproducible AppDir

1. Add PySide6 and pin compatible runtime/build versions for a release.
2. Generate a PyInstaller `--onedir --windowed` bundle and keep its `_internal` tree and symlinks intact.
3. Stage that bundle under `AppDir/usr/lib/yt-clip-watch`; add a relative-path `AppRun`, desktop file, root icon, and `.DirIcon`.
4. Bundle architecture-matched, version-pinned Deno plus FFmpeg/FFprobe. Prefer the yt-dlp project's published FFmpeg builds; verify checksums and runtime linkage before inclusion.
5. Pass their absolute packaged paths to yt-dlp instead of mutating global host configuration.
6. Include Qt, FFmpeg, Deno, EJS, Python-package, and application license notices plus Qt relinking/replacement instructions.
7. Run `appimagetool` with a pinned runtime file rather than allowing a “latest” runtime download.

**Acceptance:** the staged AppDir and resulting AppImage launch without system Python, yt-dlp, clipboard utilities, Deno, or FFmpeg installed. A real URL downloads and merges successfully. `desktop-file-validate` passes, and all writes land in the selected output/XDG data locations rather than the read-only mount.

### Phase 4 — Test the distribution boundary

Test the AppImage, not just the Python source, on:

- Ubuntu 22.04 x86-64, X11;
- Ubuntu 22.04 x86-64, Wayland;
- Debian 12 x86-64;
- a host without FUSE using AppImage extract-and-run;
- native Firefox and Chromium profiles, plus clear failure messages for unavailable or inaccessible profiles.

Check launch, clipboard/manual enqueue, progress, merge/post-processing, archive deduplication, spaces/non-ASCII output paths, failure recovery, close during work, and a second launch. Record the exact glibc floor and supported distribution matrix in the README.

**Acceptance:** every supported host completes the same smoke scenario. Any failed clipboard notification is recoverable through manual entry; cookie/keyring failures are actionable and do not crash the app.

### Phase 5 — Automate release builds

1. Add a GitHub Actions workflow using an explicit runner and a digest-pinned Ubuntu 22.04 job container.
2. Pin third-party actions by full commit SHA and give the token read-only permissions except in the release job.
3. Download pinned PyInstaller/AppImage/Deno/FFmpeg inputs, verify SHA-256 values, build once, and upload the AppImage as a workflow artifact.
4. On a version tag, attach the same tested artifact and checksum to a GitHub release.
5. Add a release checklist to update yt-dlp and matching EJS together, rerun the target-host matrix, and review changed third-party licenses.

**Acceptance:** a clean tagged workflow produces an x86-64 AppImage and checksum whose downloaded artifact passes the Phase 4 smoke test. Build logs identify every tool and dependency version.

### Phase 6 — Clean cutover

1. Replace the README's CLI installation and usage with AppImage download/run instructions, source-development instructions, the supported Linux matrix, cookie warning, and FUSE fallback.
2. Remove the old `yt-clip-watch` CLI entry and obsolete clipboard-command/Bun requirements.
3. Confirm no caller, document, build recipe, or requirement references the removed path.

**Acceptance:** a new user can download, mark executable, launch, choose a folder, start watching, and complete a download without a terminal or system Python.

## Deliberate first-release exclusions

- No auto-updater, tray daemon, browser extension, playlists manager, scheduler, themes, plugin interface, or parallel downloads.
- No ARM AppImage until a separate build and host matrix exist.
- No silent cookie export or credentials inside the AppImage.
- No promise of in-flight cancellation until yt-dlp exposes a stable mechanism or the downloader is deliberately changed to a child process.
- No support claim below Ubuntu 22.04/glibc 2.35 for the first build. The final documented floor must come from the built artifact and host tests, not only the PySide6 wheel tag.

## Definition of done

The project is complete when the source GUI and released AppImage exercise the same downloader module; the x86-64 AppImage is self-contained except for host browser/session state, kernel/driver/base libraries, and network access; the documented X11/Wayland host matrix passes a real download-and-merge smoke test; third-party notices and reproducible build inputs ship with the release; and the old CLI implementation is gone.
