#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <run_id>" >&2
  exit 1
fi

RUN_ID="$1"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PULL_SCRIPT="$SCRIPT_DIR/pull_run_from_deep_server.sh"
PUSH_SCRIPT="$SCRIPT_DIR/push_run_to_nectar.sh"
LOCAL_DEEP_ROOT=/home/bwbrook/work/remote-mirrors/deep-server
LOCAL_NECTAR_ROOT=/home/bwbrook/work/remote-mirrors/nectar-vm

"$PULL_SCRIPT" "$RUN_ID" >/dev/null
REMOTE_PATH=$("$PUSH_SCRIPT" "$RUN_ID")

LOCAL_NECTAR_MATCH=$(find "$LOCAL_NECTAR_ROOT" -mindepth 2 -maxdepth 2 -type d -name "$RUN_ID" | sort)
MATCH_COUNT=$(printf '%s\n' "$LOCAL_NECTAR_MATCH" | sed '/^$/d' | wc -l)
if [ "$MATCH_COUNT" -ne 1 ]; then
  echo "Expected exactly one mirrored Nectar run for '$RUN_ID', found $MATCH_COUNT" >&2
  exit 1
fi

LOCAL_MANIFEST="$LOCAL_NECTAR_MATCH/run_manifest.yaml"
REMOTE_MANIFEST="$REMOTE_PATH/run_manifest.yaml"
NOW=$(date --iso-8601=seconds)
export NOW

if [ -f "$LOCAL_MANIFEST" ]; then
  yq -i \
    '.authoritative_host = "nectar-vm" |
     .status = "mirrored" |
     .last_sync_from = "deep-server" |
     .last_sync_time = strenv(NOW)' \
    "$LOCAL_MANIFEST"
  rsync -av "$LOCAL_MANIFEST" nectar-vm:"$REMOTE_MANIFEST"
fi

echo "Synced $RUN_ID from deep-server to nectar-vm"
