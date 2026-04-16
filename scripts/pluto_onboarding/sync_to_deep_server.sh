#!/usr/bin/env bash
set -euo pipefail

LOCAL_BASE=/home/bwbrook/papers/xray_cavities/scripts/pluto_onboarding
REMOTE_BASE=/home/bwbrook/work/pluto-onboarding

rsync -av "$LOCAL_BASE/rt_instability/" deep-server:"$REMOTE_BASE/rt_instability/scripts/"
rsync -av "$LOCAL_BASE/kh_instability/" deep-server:"$REMOTE_BASE/kh_instability/scripts/"

echo "Synced PLUTO onboarding workflow scripts to deep-server"
