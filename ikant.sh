#!/bin/sh
set -eu
PORT="${IKANT_PORT:-8765}"
exec python3 -m ikant.local_app --port "$PORT" "$@"
