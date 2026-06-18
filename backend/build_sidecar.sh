#!/usr/bin/env bash
# Build the Python sidecar into a single binary and place it where Tauri's
# externalBin expects it (named with the Rust host target triple).
#
# Usage: ./build_sidecar.sh    (run from backend/, with the venv created)
set -euo pipefail

cd "$(dirname "$0")"
VENV=.venv

# Rust host triple, e.g. aarch64-apple-darwin (fall back to uname if rustc absent)
TRIPLE="$( (rustc -vV 2>/dev/null || true) | sed -n 's/^host: //p')"
if [ -z "$TRIPLE" ]; then
  case "$(uname -m)" in
    arm64|aarch64) TRIPLE=aarch64-apple-darwin ;;
    x86_64) TRIPLE=x86_64-apple-darwin ;;
    *) echo "Unknown arch $(uname -m)"; exit 1 ;;
  esac
fi
OUT_DIR=../desktop/src-tauri/binaries
mkdir -p "$OUT_DIR"

echo "Building sidecar for triple: $TRIPLE"
"$VENV/bin/pyinstaller" --noconfirm --clean --onefile \
  --name tidal-backend \
  --collect-all uvicorn \
  --collect-all anthropic \
  --collect-submodules tidalapi \
  --collect-all keyring \
  --copy-metadata keyring \
  --collect-submodules sqlmodel \
  --collect-submodules sqlalchemy \
  sidecar.py

cp "dist/tidal-backend" "$OUT_DIR/tidal-backend-$TRIPLE"
chmod +x "$OUT_DIR/tidal-backend-$TRIPLE"
echo "Placed: $OUT_DIR/tidal-backend-$TRIPLE"
