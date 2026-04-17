#!/usr/bin/env bash
set -euo pipefail

LOCAL_BASE=/home/bwbrook/papers/xray_cavities/scripts/pluto_onboarding
REMOTE_BASE=/home/ubuntu/work/pluto-onboarding

rsync -av "$LOCAL_BASE/rt_instability/" nectar-vm:"$REMOTE_BASE/rt_instability/scripts/"
rsync -av "$LOCAL_BASE/kh_instability/" nectar-vm:"$REMOTE_BASE/kh_instability/scripts/"

echo "Synced PLUTO onboarding workflow scripts to nectar-vm"
