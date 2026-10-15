# Epic Games Launcher Flatpak

Community Flatpak packaging for the native [Epic Games Launcher Preview for Linux](https://launcher.epicgames.com/). It repackages the official x86_64 AppImage as `com.epicgames.EpicGamesLauncher`.

Following the LMStudio-Flatpak and MusicPresence-Flatpak repositories, the manifest downloads the AppImage as [Flatpak `extra-data`](https://docs.flatpak.org/en/latest/module-sources.html#extra-data) during installation and verifies its size and SHA-256. Epic hosts the launcher binary; this repository contains the packaging scripts, metadata and icon.

The package uses `org.gnome.Platform//51` and `org.gnome.Sdk//51` for GTK 3 and WebKitGTK 4.1. It builds libayatana-appindicator 0.6.1 and libdbusmenu for the system tray. Sources are pinned in `modules/libayatana-appindicator.json`.

## Build and install

Install Flatpak, add Flathub for your user, then run:

```bash
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.flatpak.Builder
./build.sh
```

`build.sh` uses a native `flatpak-builder` when available, or the version in `org.flatpak.Builder`. It installs missing dependencies, builds the package, exports an OSTree repository to `repo/`, and installs the app from the local `epic-games-launcher-local` remote. Installation runs on the host so that `extra-data` can create its extraction sandbox. Build files are stored in `builddir/`.

Prebuilt bundles are available on the [releases page](https://github.com/KernelFreeze/EpicGamesLauncher-Flatpak/releases).

## Run

```bash
flatpak run com.epicgames.EpicGamesLauncher
```

The desktop entry registers the `com.epicgames.launcher://` protocol. The wrapper forwards command-line arguments, including login callback URLs. Close the launcher before testing different environment settings: an existing instance may handle subsequent launches without applying them.

### NVIDIA on Wayland

On NVIDIA, the wrapper sets `__NV_DISABLE_EXPLICIT_SYNC=1` for Wayland and keeps WebKit's DMA-BUF renderer enabled. This avoids the startup protocol error while preserving GPU acceleration. Disabling DMA-BUF instead can leave black or empty layers with WebKitGTK 2.54.1, as described in the [WebKit bug report](https://bugs.webkit.org/show_bug.cgi?id=280210#c14).

For X11, the wrapper retains `WEBKIT_DISABLE_DMABUF_RENDERER=1`. Explicit user settings take precedence over the wrapper defaults.

If an older override still disables DMA-BUF, close the launcher and test:

```bash
flatpak run --env=WEBKIT_DISABLE_DMABUF_RENDERER=0 com.epicgames.EpicGamesLauncher
```

To test upstream's explicit-sync behavior, use `--env=__NV_DISABLE_EXPLICIT_SYNC=0` for a fresh instance.

## Storage and permissions

Application data is stored in `~/.var/app/com.epicgames.EpicGamesLauncher/`. The manifest grants network, graphics, audio and system-tray access, plus access to the desktop Secret Service through `org.freedesktop.secrets`.

Game libraries can use `~/Games` and drives mounted under `/run/media`, `/media` or `/mnt`. To allow another library directory:

```bash
flatpak override --user --filesystem=/path/to/your/library com.epicgames.EpicGamesLauncher
```

This package contains the native launcher. Windows games may need a compatibility layer, as explained in [Epic's Linux FAQ](https://launcher.epicgames.com/#faq-linux).

## Create an installable bundle

After building:

```bash
flatpak build-bundle --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo \
  repo epic-games-launcher-x86_64.flatpak com.epicgames.EpicGamesLauncher stable
flatpak install --user ./epic-games-launcher-x86_64.flatpak
```

The bundle retains the `extra-data` reference. Installation needs an internet connection to download the AppImage from Epic.

## Upstream updates

The **Update launcher** workflow runs daily at 09:23 UTC and can also be started manually from GitHub Actions. It follows the official installer redirect, downloads the AppImage, calculates its SHA-256 and size, and pins the versioned URL in the manifest. New versions also receive an AppStream release entry. Updates use one automation branch and open or refresh a pull request against `main`.

The workflow uses `GITHUB_TOKEN` with `contents: write` and `pull-requests: write`. Enable **Allow GitHub Actions to create and approve pull requests** in the repository's Actions settings. As in the Caelestia workflow, an optional `SPEC_UPDATE_TOKEN` secret can supply a token with those permissions, including when follow-up workflows must run on the bot's PR.

To check locally without changing files:

```bash
python3 scripts/update_launcher.py --dry-run
```

To apply an upstream update locally:

```bash
python3 scripts/update_launcher.py
./build.sh
```

Review the icon and AppImage layout when upstream changes its packaging. `apply_extra.sh` extracts the Zstandard-compressed SquashFS and retains the executable, EOS SDK and `ThirdPartyNotices.txt` under `/app/extra/epic-games-launcher/`. GTK, GLib and WebKit come from the GNOME runtime.

The updater changes the packaging sources. Building, testing and publishing a new bundle remain separate steps.

## Local validation

Version 0.95.2+gfa9ad49 was built and installed on x86_64 with GNOME 51 on October 14, 2026. Checks covered shell syntax, AppStream metadata, the desktop entry, linked libraries, third-party notices, `extra-data` extraction and system-tray registration. The desktop Secret Service answered `org.freedesktop.DBus.Peer.Ping` from inside the sandbox.

With WebKitGTK 2.54.1 and NVIDIA driver 615.78.08 on an RTX 3080, the explicit-sync workaround rendered the signed-in library correctly inside Cage at 1280 × 720 and after resizing to 1024 × 1024. Epic and its WebKit processes loaded NVIDIA libraries. A separate WebKit probe rendered transformed layers, transparency, filters and WebGL. The launcher restored the existing signed-in session after restarting.

To run a nested Wayland test, close the launcher first:

```bash
WLR_BACKENDS=wayland cage -d -- flatpak run --user com.epicgames.EpicGamesLauncher
```

The initial signed-out screen was also checked inside Cage:

![Launcher sign-in screen inside Cage](screenshots/login.png)

Fresh browser-based login, DPoP, game downloads and game execution remain untested, as do systems without NVIDIA and the X11 fallback. An earlier Preview startup logged `NoDefaultStore` and disabled DPoP. Secret Service access is verified, but its effect on that upstream credential-store behavior has not been established.

## Licenses

Packaging scripts and configuration use MIT; AppStream metadata uses CC0-1.0. The launcher, EOS SDK and icon retain Epic's and their respective authors' licenses. Extraction preserves the bundled third-party notices. The intltool and libdbusmenu recipes and patches come from [flathub/shared-modules](https://github.com/flathub/shared-modules/tree/master/libayatana-appindicator) and retain their attribution. Built dependencies retain their own licenses.
