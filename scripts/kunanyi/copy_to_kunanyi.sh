#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <local-path> <remote-path>" >&2
  exit 2
fi

ENV_FILE="${TPAC_ENV_FILE:-$HOME/.config/tpac/kunanyi.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "Missing TPAC env file: $ENV_FILE" >&2
  exit 2
fi

set -a
# shellcheck source=/dev/null
. "$ENV_FILE"
set +a

if [ -z "${TPAC_USER:-}" ] || [ -z "${TPAC_PASSWORD:-}" ]; then
  echo "TPAC_USER and TPAC_PASSWORD must be set in $ENV_FILE" >&2
  exit 2
fi

LOCAL_PATH="$1"
REMOTE_PATH="$2"
TPAC_SCP_HOST="${TPAC_SCP_HOST:-kunanyi-via-deep}"
export TPAC_PASSWORD LOCAL_PATH REMOTE_PATH TPAC_SCP_HOST

/usr/bin/expect <<'EXPECT'
set timeout 600
set password $env(TPAC_PASSWORD)
set local_path $env(LOCAL_PATH)
set remote_path $env(REMOTE_PATH)
set host $env(TPAC_SCP_HOST)

spawn scp -r -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 $local_path ${host}:${remote_path}
expect {
  -re "(?i)password:" { send "$password\r"; exp_continue }
  -re "MFA check failed" { puts "MFA check failed. Open the TPAC jumpbox SSH window and retry."; exit 124 }
  timeout { puts "TIMEOUT during scp upload"; exit 125 }
  eof {
    catch wait result
    exit [lindex $result 3]
  }
}
EXPECT
