#!/bin/bash
set -euo pipefail

cd /app/extra
APP_IMAGE=epic-games-launcher.appimage
DEST=epic-games-launcher

# Una segunda ejecución sobre una extracción completa no cambia el resultado.
if [[ ! -f "$APP_IMAGE" ]]; then
  test -x "$DEST/usr/bin/EpicGamesLauncher"
  exit 0
fi

rm -rf squashfs-root "$DEST.new"
unappimage -no-progress -no-xattrs "$APP_IMAGE"

# GNOME aporta GTK, WebKit y GLib. Conservamos el ejecutable y los recursos
# de Epic, incluido EOS y sus avisos de terceros, en su estructura original.
mkdir -p "$DEST.new/usr/bin" "$DEST.new/usr/lib"
cp -a squashfs-root/usr/bin/EpicGamesLauncher "$DEST.new/usr/bin/"
cp -a squashfs-root/usr/lib/epic-games-launcher "$DEST.new/usr/lib/"
ln -s epic-games-launcher/libEOSSDK-Linux-Shipping.so \
  "$DEST.new/usr/lib/libEOSSDK-Linux-Shipping.so"
test -x "$DEST.new/usr/bin/EpicGamesLauncher"

rm -rf "$DEST"
mv "$DEST.new" "$DEST"
rm -rf squashfs-root "$APP_IMAGE"
