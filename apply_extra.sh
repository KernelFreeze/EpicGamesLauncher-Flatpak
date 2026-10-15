#!/bin/bash
set -euo pipefail

cd /app/extra
APP_IMAGE=epic-games-launcher.appimage
DEST=epic-games-launcher

# Re-running after a complete extraction leaves the installed files intact.
if [[ ! -f "$APP_IMAGE" ]]; then
  test -x "$DEST/usr/bin/EpicGamesLauncher"
  exit 0
fi

rm -rf squashfs-root "$DEST.new"
unappimage -no-progress -no-xattrs "$APP_IMAGE"

# GNOME provides GTK, WebKit and GLib. Keep Epic's executable and resources,
# including EOS and third-party notices, in their original layout.
mkdir -p "$DEST.new/usr/bin" "$DEST.new/usr/lib"
cp -a squashfs-root/usr/bin/EpicGamesLauncher "$DEST.new/usr/bin/"
cp -a squashfs-root/usr/lib/epic-games-launcher "$DEST.new/usr/lib/"
ln -s epic-games-launcher/libEOSSDK-Linux-Shipping.so \
  "$DEST.new/usr/lib/libEOSSDK-Linux-Shipping.so"
test -x "$DEST.new/usr/bin/EpicGamesLauncher"

rm -rf "$DEST"
mv "$DEST.new" "$DEST"
rm -rf squashfs-root "$APP_IMAGE"
