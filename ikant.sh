#!/bin/sh
set -eu
PORT="${IKANT_PORT:-8765}"
export PYTHONUNBUFFERED=1
exec python3 -m ikant.local_app --port "$PORT" "$@"
