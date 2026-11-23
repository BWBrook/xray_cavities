#!/bin/bash
# Run in a newly transferred bundle. All dependent jobs stay behind the held preparation job until checked.
set -euo pipefail
: "${1:?supply path to the private PBS mail-recipient file}"
: "${2:?supply the user quota directory for the output allocation}"
: "${3:?supply the confirmed quota ceiling in bytes for that filesystem}"
python=${ANALYSIS_PYTHON:-/share/apps/software/Anaconda3/2024.02-1/bin/python}
pbs=${PBS_BIN:-/opt/pbs/bin}
mail=$(<"$1")
[[ $mail == *@* && $mail != *[[:space:]]* ]]
sha256sum -c --quiet SHA256SUMS
test ! -e jobs.tsv
mapfile -t cases < <("$python" -c 'import json; print(*sorted(json.load(open("contract.json"))["cases"], reverse=True),sep="\n")')
case "${cases[*]}" in
    G-HI|"G-HI C-HI") prepare=ent_prepare; simulate=ent_cases ;;
    "G-LO C-LO") prepare=ent_lo_prepare; simulate=ent_lo ;;
    *) echo "Unexpected cases in paired restart contract" >&2; exit 2 ;;
esac
layout=$("$python" - "$2" "$3" <<'PY'
import json, pathlib, shutil, subprocess, sys
cfg = json.load(open("contract.json"))
layouts = {(case["mpi_nodes"], case["mpi_ranks_per_node"]) for case in cfg["cases"].values()}
if len(layouts) != 1 or any(
        c["mpi_ranks"] != c["mpi_nodes"] * c["mpi_ranks_per_node"] or c["mpi_decomposition"] != "automatic"
        for c in cfg["cases"].values()):
    raise SystemExit("one sequential PBS allocation must reproduce each historical MPI layout")
nodes, ranks_per_node = layouts.pop()
root = pathlib.Path(sys.argv[1]).resolve(strict=True)
work = pathlib.Path(cfg["work_root"]).resolve()
if work.exists() or not work.is_relative_to(root) or root == work:
    raise SystemExit("output root must be a new directory in the measured allocation")
used = int(subprocess.check_output(["du", "-sx", "--block-size=1", str(root)], text=True).split()[0])
limit = int(sys.argv[2])
filesystem_free = shutil.disk_usage(root).free
seed = 67318639276 + 44890581676 + 8 * 1024**2
arm = 21 * 44890581676 + 67318639276 + 5 * 1024**3
required = len(cfg["cases"]) * (seed + 2 * arm) + 10 * 1024**3
receipt = dict(quota_limit_bytes=limit, directory_allocated_bytes=used, filesystem_free_bytes=filesystem_free,
               forecast_bytes=required, cases=list(cfg["cases"]))
pathlib.Path("capacity.json").write_text(json.dumps(receipt, indent=2) + "\n")
if min(limit - used, filesystem_free) < required:
    raise SystemExit("insufficient accounted space for the selected complete native histories")
print(f"select={nodes}:ncpus={ranks_per_node}:mpiprocs={ranks_per_node}")
PY
)
mkdir -p logs
(set -o noclobber; : > jobs.tsv)
submit() {
    local role=$1 case_id=$2 setting=$3 name=$4 resources=$5
    shift 5
    local job script=entropy_restart.pbs
    if [[ $role == simulate ]]; then script=entropy_restart_cases.pbs; fi
    job=$("$pbs/qsub" -N "$name" -m ae -M "$mail" -l "$resources" \
        -v "ROLE=$role,CASE_ID=$case_id,SETTING=$setting" \
        -o "$PWD/logs/$name.out" -e "$PWD/logs/$name.err" "$@" "$script")
    [[ $job =~ ^[0-9]+([.][a-zA-Z0-9._-]+)?$ ]]
    printf '%s\t%s\t%s\t%s\n' "$job" "$role" "$case_id" "$setting" >> jobs.tsv
    "$pbs/qstat" -f "$job" > "logs/$name.submitted"
    grep -Eq '^ *Mail_Points = (ae|ea)$' "logs/$name.submitted"
    grep -Fq "Mail_Users = $mail" "logs/$name.submitted"
    "$python" - "logs/$name.submitted" "${!#}" <<'PY'
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text()
text = re.sub(r"\n\t", "", text)
expected = sys.argv[2]
if expected == "-h":
    match = re.search(r"^\s*Hold_Types = (\S+)", text, re.M)
    if not match or "u" not in match[1]:
        raise SystemExit("preparation job lacks the requested user hold")
else:
    match = re.search(r"^\s*depend = afterok:([^\s]+)", text, re.M)
    actual = set() if not match else {j.split("@")[0] for j in match[1].split(":")}
    if actual != set(expected.removeprefix("depend=afterok:").split(":")):
        raise SystemExit("PBS dependency differs from the requested successful-control chain")
PY
    job_id=$job
}
submit prepare all both "$prepare" 'select=1:ncpus=12:mem=30gb,walltime=08:00:00' -h
prep=$job_id
hours=$((10 * ${#cases[@]}))
hydro="$layout,walltime=$hours:00:00"
submit simulate all ON "${simulate}_on" "$hydro" -W "depend=afterok:$prep"
on=$job_id
gates=()
for c in "${cases[@]}"; do
    short=${c//-/}
    submit gate "$c" ON "ent_${short}_gate" 'select=1:ncpus=2:mem=12gb,walltime=05:00:00' -W "depend=afterok:$on"
    gates+=("$job_id")
done
joint=$(IFS=:; echo "${gates[*]}")
submit simulate all OFF "${simulate}_off" "$hydro" -W "depend=afterok:$joint"
"$pbs/qrls" "$prep"
cat jobs.tsv
