#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <run_id>" >&2
  exit 1
fi

RUN_ID="$1"
LOCAL_ROOT=/home/bwbrook/work/remote-mirrors/deep-server
REMOTE_ROOT=/home/ubuntu/work/utas-agn-runs
NECTAR_MIRROR_ROOT=/home/bwbrook/work/remote-mirrors/nectar-vm
mkdir -p "$NECTAR_MIRROR_ROOT"

MATCHES=$(find "$LOCAL_ROOT" -mindepth 2 -maxdepth 2 -type d -name "$RUN_ID" | sort)

if [ -z "$MATCHES" ]; then
  echo "No mirrored run named '$RUN_ID' found under $LOCAL_ROOT" >&2
  exit 1
fi

MATCH_COUNT=$(printf '%s\n' "$MATCHES" | sed '/^$/d' | wc -l)
if [ "$MATCH_COUNT" -ne 1 ]; then
  echo "Run id '$RUN_ID' is ambiguous in the local deep-server mirror:" >&2
  printf '%s\n' "$MATCHES" >&2
  exit 1
fi

LOCAL_PATH="$MATCHES"
REL_PATH=${LOCAL_PATH#${LOCAL_ROOT}/}
REMOTE_PATH="$REMOTE_ROOT/$REL_PATH"
REMOTE_PARENT=$(dirname "$REMOTE_PATH")
LOCAL_NECTAR_PATH="$NECTAR_MIRROR_ROOT/$REL_PATH"
mkdir -p "$(dirname "$LOCAL_NECTAR_PATH")"

ssh -o BatchMode=yes nectar-vm "mkdir -p \"$REMOTE_PARENT\""
rsync -av --delete "$LOCAL_PATH/" nectar-vm:"$REMOTE_PATH/" >&2
rsync -av --delete nectar-vm:"$REMOTE_PATH/" "$LOCAL_NECTAR_PATH/" >&2

echo "$REMOTE_PATH"
