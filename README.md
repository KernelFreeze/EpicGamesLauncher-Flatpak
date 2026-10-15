# Epic Games Launcher Flatpak

Community Flatpak for the native [Epic Games Launcher Preview for Linux](https://launcher.epicgames.com/), packaged as `com.epicgames.EpicGamesLauncher`.

The official x86_64 AppImage is not redistributed. Flatpak downloads it from Epic at install time as [`extra-data`](https://docs.flatpak.org/en/latest/module-sources.html#extra-data) and verifies its size and SHA-256. The app runs on `org.gnome.Platform//51` and bundles libayatana-appindicator for the system tray.

![Launcher sign-in screen](screenshots/login.png)

## Install

Download the `.flatpak` bundle from the [releases page](https://github.com/KernelFreeze/EpicGamesLauncher-Flatpak/releases) and install it:

```bash
flatpak install --user ./epic-games-launcher-*-x86_64.flatpak
```

Installation needs an internet connection to fetch the AppImage from Epic.

## Build from source

```bash
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.flatpak.Builder
./build.sh
```

`build.sh` builds into `builddir/`, exports the result to `repo/` and installs it from a local remote. To create a bundle afterwards:

```bash
flatpak build-bundle --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo \
  repo epic-games-launcher-x86_64.flatpak com.epicgames.EpicGamesLauncher stable
```

## Usage

```bash
flatpak run com.epicgames.EpicGamesLauncher
```

The desktop entry handles `com.epicgames.launcher://` links, so browser login callbacks reach the launcher.

Game libraries can live in `~/Games` or on drives under `/run/media`, `/media` or `/mnt`. To allow another directory:

```bash
flatpak override --user --filesystem=/path/to/library com.epicgames.EpicGamesLauncher
```

Windows games may need a compatibility layer; see [Epic's Linux FAQ](https://launcher.epicgames.com/#faq-linux).

### NVIDIA on Wayland

The wrapper sets `__NV_DISABLE_EXPLICIT_SYNC=1` on NVIDIA under Wayland to avoid a startup protocol error, and keeps WebKit's DMA-BUF renderer enabled for GPU acceleration. On X11 it sets `WEBKIT_DISABLE_DMABUF_RENDERER=1`. Variables you set yourself, for example with `flatpak run --env=...`, take precedence. Close any running instance first, since it may handle new launches without the new settings.

## Updating the launcher

`scripts/update_launcher.py` checks Epic's installer for a new AppImage and pins its URL, size and checksum in the manifest:

```bash
python3 scripts/update_launcher.py --dry-run   # check only
python3 scripts/update_launcher.py             # update the manifest
./build.sh
```

If Epic changes the AppImage layout, check `apply_extra.sh`, which extracts the launcher into `/app/extra/epic-games-launcher/`.

## Licenses

Packaging files are MIT and the AppStream metadata is CC0-1.0. The launcher, EOS SDK and icon belong to Epic Games and their respective authors; bundled third-party notices are preserved. The libayatana-appindicator modules come from [flathub/shared-modules](https://github.com/flathub/shared-modules/tree/master/libayatana-appindicator).
