#!/bin/bash
# Run from the verified readout bundle once the native restart jobs are registered.
set -euo pipefail
umask 077
: "${1:?path to private PBS recipient file}"
: "${2:?path to the simulation jobs.tsv}"
: "${3:?native output root for the paired restarts}"
pbs=${PBS_BIN:-/opt/pbs/bin}
python=${ANALYSIS_PYTHON:-/share/apps/software/Anaconda3/2024.02-1/bin/python}
recipient_file=$1
native_root=$3
mail=$(<"$recipient_file")
[[ $mail == *@* && $mail != *[[:space:]]* ]]
sha256sum --check --quiet inputs.sha256
off=$("$python" - "$2" <<'PY'
import csv, sys
with open(sys.argv[1]) as f:
    jobs = {tuple(row[1:]): row[0] for row in csv.reader(f, delimiter="\t")}
assert set(jobs) == {("prepare","all","both"), ("simulate","all","ON"),
                     ("gate","C-LO","ON"), ("gate","G-LO","ON"), ("simulate","all","OFF")}
print(jobs["simulate","all","OFF"])
PY
)
mkdir registration.lock
trap 'rmdir registration.lock' EXIT
register() {
    local receipt=$1 script=$2 depends=$3 id
    if [[ -s $receipt.id ]]; then
        id=$(<"$receipt.id")
    else
        id=$("$pbs/qsub" -m ae -M "$mail" -W "depend=afterok:$depends" \
            -v "ENTROPY_WORK_ROOT=$native_root" "$script")
        [[ $id =~ ^[0-9]+(\[\])?\.[[:alnum:]_.-]+$ ]]
        (set -o noclobber; printf '%s\n' "$id" > "$receipt.id")
    fi
    "$pbs/qstat" -xf -F json "$id" > "$receipt.pbs.private.json"
    "$python" - "$receipt" "$id" "$depends" "$recipient_file" <<'PY'
import json, pathlib, sys
name, job, predecessor, recipient = sys.argv[1:]
record = json.loads(pathlib.Path(name + ".pbs.private.json").read_text())["Jobs"][job]
mail = pathlib.Path(recipient).read_text().strip()
dep = record.get("depend", "").split(",")
ok = [item.split("@")[0] for group in dep if group.startswith("afterok:")
      for item in group.split(":")[1:]]
if ok != [predecessor] or set(record["Mail_Points"]) != set("ae") or record["Mail_Users"] != mail:
    raise SystemExit(f"{job}: PBS dependency or mail configuration differs from the registered chain")
if (name == "readout") != ("[]" in job):
    raise SystemExit(f"{job}: PBS job type differs from the requested array or scalar")
if name == "readout" and record.get("array_indices_submitted") != "0-15":
    raise SystemExit(f"{job}: missing readout workers")
public = dict(id=job, name=record["Job_Name"], state=record["job_state"],
              afterok=predecessor, mail_points=record["Mail_Points"], recipient_verified=True)
if name == "readout":
    public["array_indices"] = record["array_indices_submitted"]
pathlib.Path(name + ".submission.json").write_text(json.dumps(public, indent=2) + "\n")
print(job, name, "afterok", predecessor)
PY
}
register readout entropy_restart_readout.pbs "$off"
register score entropy_low_power_score.pbs "$(<readout.id)"
