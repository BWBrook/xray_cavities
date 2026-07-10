#!/bin/bash

set -u

export LC_ALL=C
export LANG=C

usage() {
  cat >&2 <<'EOF'
Usage: run_with_progress_watchdog.sh \
  --timeout-seconds N \
  --poll-seconds N \
  --term-grace-seconds N \
  --progress-dir DIR \
  --command-log PATH \
  --status-log PATH \
  --trigger-file PATH \
  -- COMMAND [ARG ...]
EOF
}

die() {
  echo "[watchdog:error] $*" >&2
  exit 2
}

require_value() {
  if [ "$#" -lt 2 ]; then
    die "missing value for $1"
  fi
}

require_nonnegative_integer() {
  local name="$1"
  local value="$2"
  case "$value" in
    ''|*[!0-9]*)
      die "${name} must be a nonnegative integer: ${value}"
      ;;
  esac
}

timeout_seconds=""
poll_seconds=""
term_grace_seconds=""
progress_dir=""
command_log=""
status_log=""
trigger_file=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --timeout-seconds)
      require_value "$@"
      timeout_seconds="$2"
      shift 2
      ;;
    --poll-seconds)
      require_value "$@"
      poll_seconds="$2"
      shift 2
      ;;
    --term-grace-seconds)
      require_value "$@"
      term_grace_seconds="$2"
      shift 2
      ;;
    --progress-dir)
      require_value "$@"
      progress_dir="$2"
      shift 2
      ;;
    --command-log)
      require_value "$@"
      command_log="$2"
      shift 2
      ;;
    --status-log)
      require_value "$@"
      status_log="$2"
      shift 2
      ;;
    --trigger-file)
      require_value "$@"
      trigger_file="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      die "unknown argument: $1"
      ;;
  esac
done

require_nonnegative_integer "timeout-seconds" "$timeout_seconds"
require_nonnegative_integer "poll-seconds" "$poll_seconds"
require_nonnegative_integer "term-grace-seconds" "$term_grace_seconds"
if [ "$timeout_seconds" -eq 0 ]; then
  die "timeout-seconds must be greater than zero"
fi
if [ "$poll_seconds" -eq 0 ]; then
  die "poll-seconds must be greater than zero"
fi
if [ -z "$progress_dir" ] || [ -z "$command_log" ] || [ -z "$status_log" ] || [ -z "$trigger_file" ]; then
  die "progress-dir, command-log, status-log, and trigger-file are required"
fi
if [ "$#" -eq 0 ]; then
  die "a command is required after --"
fi
if [ ! -d "$progress_dir" ]; then
  die "progress directory does not exist: $progress_dir"
fi

mkdir -p "$(dirname "$command_log")" || die "cannot create command-log directory"
mkdir -p "$(dirname "$status_log")" || die "cannot create status-log directory"
mkdir -p "$(dirname "$trigger_file")" || die "cannot create trigger-file directory"
rm -f "$trigger_file" || die "cannot clear trigger file: $trigger_file"
printf '%s\n' \
  $'timestamp_utc\tevent\tchild_pid\tno_progress_seconds\texit_code\tsignature' \
  > "$status_log" || die "cannot initialize status log: $status_log"

utc_now() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

epoch_now() {
  date +%s
}

child_pid=""
child_pgid=""
current_signature="unavailable"
current_no_progress=0

append_status() {
  local event="$1"
  local elapsed="$2"
  local exit_code="$3"
  local signature="$4"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(utc_now)" "$event" "${child_pid:--}" "$elapsed" "$exit_code" "$signature" \
    >> "$status_log"
}

stat_metadata() {
  local path="$1"
  local metadata
  if metadata=$(stat -L -c '%Y:%s' "$path" 2>/dev/null); then
    printf '%s\n' "$metadata"
  elif metadata=$(stat -L -f '%m:%z' "$path" 2>/dev/null); then
    printf '%s\n' "$metadata"
  else
    return 1
  fi
}

latest_metadata() {
  local pattern="$1"
  local best_path=""
  local best_mtime=-1
  local best_size=0
  local path metadata mtime size basename

  for path in "$progress_dir"/$pattern; do
    [ -f "$path" ] || continue
    metadata=$(stat_metadata "$path") || continue
    mtime=${metadata%%:*}
    size=${metadata##*:}
    basename=${path##*/}
    if [ "$mtime" -gt "$best_mtime" ] || {
      [ "$mtime" -eq "$best_mtime" ] && [[ "$basename" > "${best_path##*/}" ]]
    }; then
      best_path="$path"
      best_mtime="$mtime"
      best_size="$size"
    fi
  done

  if [ -z "$best_path" ]; then
    printf 'none'
  else
    printf '%s,size=%s,mtime=%s' "${best_path##*/}" "$best_size" "$best_mtime"
  fi
}

surface_metadata() {
  local path="$1"
  local metadata
  if [ ! -f "$path" ]; then
    printf 'none'
    return
  fi
  metadata=$(stat_metadata "$path") || {
    printf 'unavailable'
    return
  }
  printf '%s,size=%s,mtime=%s' "${path##*/}" "${metadata##*:}" "${metadata%%:*}"
}

hdf5_metadata_signature() {
  local count=0
  local total_size=0
  local newest_path=""
  local newest_mtime=-1
  local newest_size=0
  local records=""
  local path metadata mtime size basename checksum_line checksum

  for path in "$progress_dir"/*.h5; do
    [ -f "$path" ] || continue
    metadata=$(stat_metadata "$path") || continue
    mtime=${metadata%%:*}
    size=${metadata##*:}
    basename=${path##*/}
    count=$((count + 1))
    total_size=$((total_size + size))
    records+="${basename}:${size}:${mtime}"$'\n'
    if [ "$mtime" -gt "$newest_mtime" ] || {
      [ "$mtime" -eq "$newest_mtime" ] && [[ "$basename" > "${newest_path##*/}" ]]
    }; then
      newest_path="$path"
      newest_mtime="$mtime"
      newest_size="$size"
    fi
  done

  if [ "$count" -eq 0 ]; then
    printf 'none'
    return
  fi
  checksum_line=$(printf '%s' "$records" | cksum)
  checksum=${checksum_line%% *}
  printf 'count=%s,total_size=%s,newest=%s,size=%s,mtime=%s,metadata_cksum=%s' \
    "$count" "$total_size" "${newest_path##*/}" "$newest_size" "$newest_mtime" "$checksum"
}

progress_signature() {
  printf 'hdf5=%s|particle=%s|dbl_h5_out=%s|flt_h5_out=%s|restart_out=%s' \
    "$(hdf5_metadata_signature)" \
    "$(latest_metadata 'particles.*')" \
    "$(surface_metadata "$progress_dir/dbl.h5.out")" \
    "$(surface_metadata "$progress_dir/flt.h5.out")" \
    "$(surface_metadata "$progress_dir/restart.out")"
}

child_is_running() {
  [ -n "$child_pid" ] && kill -0 "$child_pid" 2>/dev/null
}

child_group_is_running() {
  [ -n "$child_pgid" ] && kill -0 -- "-${child_pgid}" 2>/dev/null
}

stop_child() {
  local signal_name="$1"
  local event="$2"
  local deadline now

  if ! child_group_is_running; then
    return
  fi
  kill -"$signal_name" -- "-${child_pgid}" 2>/dev/null || true
  append_status "$event" "$current_no_progress" "" "$current_signature"

  deadline=$(( $(epoch_now) + term_grace_seconds ))
  while child_group_is_running; do
    now=$(epoch_now)
    if [ "$now" -ge "$deadline" ]; then
      break
    fi
    sleep 1
  done
  if child_group_is_running; then
    kill -KILL -- "-${child_pgid}" 2>/dev/null || true
    append_status "kill_group_sent" "$current_no_progress" "" "$current_signature"
  fi
  wait "$child_pid" 2>/dev/null || true
}

forward_signal() {
  local signal_name="$1"
  local exit_code="$2"
  trap '' TERM INT
  stop_child "$signal_name" "signal_forwarded"
  append_status "watchdog_exit" "$current_no_progress" "$exit_code" "$current_signature"
  exit "$exit_code"
}

write_trigger() {
  local temporary_trigger="${trigger_file}.tmp.$$"
  rm -f "$temporary_trigger"
  {
    echo "reason=no_progress_watchdog_timeout"
    echo "triggered_utc=$(utc_now)"
    echo "child_pid=${child_pid}"
    echo "timeout_seconds=${timeout_seconds}"
    echo "poll_seconds=${poll_seconds}"
    echo "term_grace_seconds=${term_grace_seconds}"
    echo "no_progress_seconds=${current_no_progress}"
    echo "signature=${current_signature}"
    echo "command_log=${command_log}"
    echo "progress_dir=${progress_dir}"
  } > "$temporary_trigger" || {
    rm -f "$temporary_trigger"
    return 1
  }
  mv -f "$temporary_trigger" "$trigger_file" || {
    rm -f "$temporary_trigger"
    return 1
  }
}

set -m
(
  trap - TERM INT
  exec "$@"
) > "$command_log" 2>&1 &
child_pid=$!
child_pgid=$child_pid

trap 'forward_signal TERM 143' TERM
trap 'forward_signal INT 130' INT

last_progress_epoch=$(epoch_now)
current_signature=$(progress_signature)
append_status "started" 0 "" "$current_signature"

while child_is_running; do
  sleep "$poll_seconds"
  if ! child_is_running; then
    break
  fi

  now=$(epoch_now)
  new_signature=$(progress_signature)
  if [ "$new_signature" != "$current_signature" ]; then
    current_signature="$new_signature"
    current_no_progress=0
    last_progress_epoch="$now"
    append_status "progress" 0 "" "$current_signature"
  else
    current_no_progress=$((now - last_progress_epoch))
    append_status "poll" "$current_no_progress" "" "$current_signature"
  fi

  if [ "$current_no_progress" -ge "$timeout_seconds" ] && child_is_running; then
    append_status "timeout" "$current_no_progress" "" "$current_signature"
    if ! write_trigger; then
      append_status "trigger_write_failed" "$current_no_progress" "" "$current_signature"
      stop_child TERM "term_sent"
      append_status "watchdog_exit" "$current_no_progress" 125 "$current_signature"
      exit 125
    fi
    append_status "trigger_written" "$current_no_progress" "" "$current_signature"
    stop_child TERM "term_sent"
    append_status "watchdog_exit" "$current_no_progress" 124 "$current_signature"
    exit 124
  fi
done

wait "$child_pid"
command_exit=$?
append_status "command_exit" "$current_no_progress" "$command_exit" "$current_signature"
exit "$command_exit"
