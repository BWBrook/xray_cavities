#!/usr/bin/env bash
set -euo pipefail

# Open the TPAC Open OnDemand "Enable Jumpbox SSH" endpoint in Safari.
#
# A plain curl request is not enough because the portal is protected by UTAS
# SAML/AAF browser authentication. This helper relies on an already-authenticated
# Safari session, which is the same state Computer Use can operate through.

URL="${1:-https://<tpac-host>/pun/sys/enable_ssh/}"

open -a Safari "$URL"
echo "Opened $URL in Safari. If the Safari session is logged in, this starts a new 5-minute jumpbox SSH window."
