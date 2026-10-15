#!/bin/sh
set -eu

# Disabling DMA-BUF on NVIDIA can leave empty layers with WebKitGTK 2.54.
# On Wayland, disable explicit sync to avoid the protocol error instead.
# Preserve explicit user overrides.
if [ -e /dev/nvidiactl ] || [ -e /dev/nvidia0 ] || \
   [ -e /dev/nvidia-modeset ] || [ -e /dev/nvidia-uvm ]; then
  if [ -n "${WAYLAND_DISPLAY:-}" ] && [ "${GDK_BACKEND:-}" != x11 ]; then
    __NV_DISABLE_EXPLICIT_SYNC=${__NV_DISABLE_EXPLICIT_SYNC-1}
    export __NV_DISABLE_EXPLICIT_SYNC
  else
    WEBKIT_DISABLE_DMABUF_RENDERER=${WEBKIT_DISABLE_DMABUF_RENDERER-1}
    export WEBKIT_DISABLE_DMABUF_RENDERER
  fi
fi

exec /app/extra/epic-games-launcher/usr/bin/EpicGamesLauncher "$@"
