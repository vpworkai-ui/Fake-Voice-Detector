#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
  export $(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' .env | xargs)
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"

uvicorn app.main:app --host "$HOST" --port "$PORT"
