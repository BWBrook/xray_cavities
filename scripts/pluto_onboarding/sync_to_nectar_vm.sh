#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
LOCAL_BASE="$SCRIPT_DIR"
REMOTE_BASE=/home/ubuntu/work/pluto-onboarding

ssh nectar-vm "mkdir -p '$REMOTE_BASE'"
rsync -av \
  --include='*/' \
  --include='*.py' \
  --include='*.sh' \
  --include='README.md' \
  --exclude='*' \
  "$LOCAL_BASE/" nectar-vm:"$REMOTE_BASE/_scripts_sync/"

ssh nectar-vm "set -e; for d in '$REMOTE_BASE'/_scripts_sync/*; do [ -d \"\$d\" ] || continue; name=\$(basename \"\$d\"); mkdir -p '$REMOTE_BASE'/\"\$name\"/scripts; rsync -a \"\$d\"/ '$REMOTE_BASE'/\"\$name\"/scripts/; done"

echo "Synced PLUTO onboarding workflow scripts to nectar-vm"
