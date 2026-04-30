#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 short-slug" >&2
  exit 1
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
TEMPLATE="$ROOT/docs/exchange/templates/handover-note-template.md"
LOG_DIR="$ROOT/docs/exchange/logs"
STAMP=$(date +%Y-%m-%d-%H%M)
TARGET="$LOG_DIR/${STAMP}-$1.md"

mkdir -p "$LOG_DIR"
cp "$TEMPLATE" "$TARGET"

printf 'Created %s\n' "$TARGET"
