#!/usr/bin/env bash
# Build the Python sidecar into a single binary and place it where Tauri's
# externalBin expects it (named with the Rust host target triple).
#
# Cross-platform: works on macOS/Linux (bin/, no ext) and Windows git-bash
# (Scripts/, .exe). Run from backend/, with the venv already created.
set -euo pipefail

cd "$(dirname "$0")"
VENV=.venv

# venv layout + binary extension per OS.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) BINDIR=Scripts; EXT=.exe ;;
  *) BINDIR=bin; EXT= ;;
esac

# Rust host triple (rustc), with a uname fallback if rustc isn't on PATH.
TRIPLE="$( (rustc -vV 2>/dev/null || true) | sed -n 's/^host: //p')"
if [ -z "$TRIPLE" ]; then
  case "$(uname -s)-$(uname -m)" in
    Darwin-arm64) TRIPLE=aarch64-apple-darwin ;;
    Darwin-x86_64) TRIPLE=x86_64-apple-darwin ;;
    MINGW*-x86_64|MSYS*-x86_64) TRIPLE=x86_64-pc-windows-msvc ;;
    Linux-x86_64) TRIPLE=x86_64-unknown-linux-gnu ;;
    *) echo "Cannot determine target triple; install Rust or set it manually"; exit 1 ;;
  esac
fi

OUT_DIR=../desktop/src-tauri/binaries
mkdir -p "$OUT_DIR"

echo "Building sidecar for triple: $TRIPLE"
"$VENV/$BINDIR/pyinstaller$EXT" --noconfirm --clean --onefile \
  --name tidal-backend \
  --collect-all uvicorn \
  --collect-all anthropic \
  --collect-submodules tidalapi \
  --collect-all keyring \
  --copy-metadata keyring \
  --collect-submodules sqlmodel \
  --collect-submodules sqlalchemy \
  sidecar.py

cp "dist/tidal-backend$EXT" "$OUT_DIR/tidal-backend-$TRIPLE$EXT"
chmod +x "$OUT_DIR/tidal-backend-$TRIPLE$EXT" || true
echo "Placed: $OUT_DIR/tidal-backend-$TRIPLE$EXT"
