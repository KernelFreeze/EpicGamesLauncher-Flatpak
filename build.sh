#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if command -v flatpak-builder >/dev/null 2>&1; then
  BUILDER=(flatpak-builder)
else
  BUILDER=(flatpak run --user org.flatpak.Builder)
fi

"${BUILDER[@]}" \
  --user --install-deps-from=flathub --assumeyes \
  --force-clean --disable-rofiles-fuse --repo=repo \
  "$@" builddir com.epicgames.EpicGamesLauncher.yml

# apply_extra necesita un sandbox propio; la instalación se ejecuta en el host.
flatpak remote-add --user --if-not-exists --no-gpg-verify \
  epic-games-launcher-local "${PWD}/repo"
flatpak install --user --assumeyes --noninteractive --reinstall \
  epic-games-launcher-local com.epicgames.EpicGamesLauncher//stable
