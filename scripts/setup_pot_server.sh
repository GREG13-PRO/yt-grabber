#!/usr/bin/env bash
# Clones and builds the bgutil PO-token server into vendor/bgutil-server/,
# so the app can use it locally in dev mode for best-quality downloads.
# Packaged (PyInstaller) builds bundle this at CI build time instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENDOR_DIR="$PROJECT_ROOT/vendor/bgutil-server"
CLONE_DIR="$PROJECT_ROOT/vendor/.bgutil-src"
BGUTIL_VERSION="1.3.1"

if ! command -v node >/dev/null 2>&1; then
  echo "Hiba: a Node.js (>=20) szükséges ehhez a scripthez, de nem található a PATH-on." >&2
  exit 1
fi

rm -rf "$VENDOR_DIR" "$CLONE_DIR"
git clone --depth 1 --single-branch --branch "$BGUTIL_VERSION" \
  https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git "$CLONE_DIR"

cd "$CLONE_DIR/server"
npm ci
npx tsc

mkdir -p "$VENDOR_DIR"
mv "$CLONE_DIR/server/build" "$VENDOR_DIR/build"
mv "$CLONE_DIR/server/node_modules" "$VENDOR_DIR/node_modules"
rm -rf "$CLONE_DIR"

echo "Kész. A PO-token szerver build kimenete: $VENDOR_DIR/build/main.js"
