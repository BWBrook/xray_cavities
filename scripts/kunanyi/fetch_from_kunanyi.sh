#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <remote-path> <local-path>" >&2
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

REMOTE_PATH="$1"
LOCAL_PATH="$2"
LOCAL_PARENT="$(dirname "$LOCAL_PATH")"
mkdir -p "$LOCAL_PARENT"

TPAC_SCP_HOST="${TPAC_SCP_HOST:-kunanyi-via-deep}"
export TPAC_PASSWORD REMOTE_PATH LOCAL_PATH TPAC_SCP_HOST

/usr/bin/expect <<'EXPECT'
set timeout 600
set password $env(TPAC_PASSWORD)
set remote_path $env(REMOTE_PATH)
set local_path $env(LOCAL_PATH)
set host $env(TPAC_SCP_HOST)

spawn scp -r -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 ${host}:${remote_path} $local_path
expect {
  -re "(?i)password:" { send "$password\r"; exp_continue }
  -re "MFA check failed" { puts "MFA check failed. Open the TPAC jumpbox SSH window and retry."; exit 124 }
  timeout { puts "TIMEOUT during scp download"; exit 125 }
  eof {
    catch wait result
    exit [lindex $result 3]
  }
}
EXPECT
