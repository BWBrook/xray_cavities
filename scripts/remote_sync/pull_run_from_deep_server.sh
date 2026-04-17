#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <run_id>" >&2
  exit 1
fi

RUN_ID="$1"
REMOTE_ROOT=/home/bwbrook/work/utas-agn-runs
LOCAL_ROOT=/home/bwbrook/work/remote-mirrors/deep-server
mkdir -p "$LOCAL_ROOT"

MATCHES=$(ssh -o BatchMode=yes deep-server "find '$REMOTE_ROOT' -mindepth 2 -maxdepth 2 -type d -name '$RUN_ID' | sort")

if [ -z "$MATCHES" ]; then
  echo "No run named '$RUN_ID' found on deep-server under $REMOTE_ROOT" >&2
  exit 1
fi

MATCH_COUNT=$(printf '%s\n' "$MATCHES" | sed '/^$/d' | wc -l)
if [ "$MATCH_COUNT" -ne 1 ]; then
  echo "Run id '$RUN_ID' is ambiguous on deep-server:" >&2
  printf '%s\n' "$MATCHES" >&2
  exit 1
fi

REMOTE_PATH="$MATCHES"
REL_PATH=${REMOTE_PATH#${REMOTE_ROOT}/}
LOCAL_PATH="$LOCAL_ROOT/$REL_PATH"
mkdir -p "$(dirname "$LOCAL_PATH")"

rsync -av --delete deep-server:"$REMOTE_PATH/" "$LOCAL_PATH/" >&2

echo "$LOCAL_PATH"
