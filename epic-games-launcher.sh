#!/bin/sh
set -eu

# WebKit con DMA-BUF provoca un error de protocolo Wayland en NVIDIA.
# Una variable definida por el usuario conserva su valor.
if [ -e /dev/nvidiactl ]; then
  WEBKIT_DISABLE_DMABUF_RENDERER=${WEBKIT_DISABLE_DMABUF_RENDERER:-1}
  export WEBKIT_DISABLE_DMABUF_RENDERER
fi

exec /app/extra/epic-games-launcher/usr/bin/EpicGamesLauncher "$@"
