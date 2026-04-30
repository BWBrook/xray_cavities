#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 '<remote bash command>'" >&2
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

REMOTE_CMD="$*"
REMOTE_CMD_B64="$(printf '%s' "$REMOTE_CMD" | base64 | tr -d '\n')"
export TPAC_USER TPAC_PASSWORD REMOTE_CMD_B64

/usr/bin/expect <<'EXPECT'
set timeout 120
set user $env(TPAC_USER)
set password $env(TPAC_PASSWORD)
set payload $env(REMOTE_CMD_B64)
set status 255

spawn ssh -tt -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 tpac-jumpbox
expect {
  -re "(?i)password:" { send "$password\r"; exp_continue }
  -re "$user@jumpbox-\[0-9\]+:.*\[\$#%\] ?$" { }
  -re "MFA check failed" { puts "MFA check failed. Open the TPAC jumpbox SSH window and retry."; exit 124 }
  timeout { puts "TIMEOUT waiting for jumpbox shell"; exit 125 }
}

send "ssh -tt kunanyi\r"
expect {
  -re "(?i)password:" { send "$password\r"; exp_continue }
  -re "$user@kunanyi-\[0-9\]+:.*\[\$#%\] ?$" { }
  timeout { puts "TIMEOUT waiting for kunanyi shell"; exit 126 }
}

send "printf %s $payload | base64 -d | bash; rc=\\$?; echo __CODEX_STATUS__=\\$rc\r"
expect {
  -re "__CODEX_STATUS__=(\[0-9\]+)" {
    set status $expect_out(1,string)
  }
  timeout { puts "TIMEOUT during remote command"; exit 127 }
}

send "exit\r"
expect {
  -re "$user@jumpbox-\[0-9\]+:.*\[\$#%\] ?$" { }
  eof { exit $status }
  timeout { exit $status }
}

send "exit\r"
expect eof
exit $status
EXPECT
