#!/usr/bin/env bash
# Workshop entry point: runs ws.py inside the repo's ESP-IDF shell (nix develop .#esp).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v idf.py >/dev/null 2>&1; then
  exec python3 "$here/ws.py" "$@"
fi
exec nix develop "$here" -c python3 "$here/ws.py" "$@"
