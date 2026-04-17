#!/usr/bin/env bash
set -euo pipefail

LOCAL_BASE=/home/bwbrook/papers/xray_cavities/scripts/pluto_onboarding
REMOTE_BASE=/home/bwbrook/work/pluto-onboarding

rsync -av "$LOCAL_BASE/rt_instability/" deep-server:"$REMOTE_BASE/rt_instability/scripts/"
rsync -av "$LOCAL_BASE/jet_setup_basic/" deep-server:"$REMOTE_BASE/jet_setup_basic/scripts/"
rsync -av "$LOCAL_BASE/kh_instability/" deep-server:"$REMOTE_BASE/kh_instability/scripts/"
rsync -av "$LOCAL_BASE/jet_parameter_sweep/" deep-server:"$REMOTE_BASE/jet_parameter_sweep/scripts/"
rsync -av "$LOCAL_BASE/krause_jets_assignment/" deep-server:"$REMOTE_BASE/krause_jets_assignment/scripts/"

echo "Synced PLUTO onboarding workflow scripts to deep-server"
