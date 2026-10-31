from pathlib import Path
import ast
import hashlib
import json
import shutil
import subprocess
import tarfile

repo = Path('/Users/bwbrook/papers/xray_cavities')
stage = Path('/private/tmp/q031-native-session/q031_native_emission_2026-10-31_r4')
stage.mkdir()
names = [
    'scripts/science/build_q031_native_emission.py',
    'scripts/science/build_selected_age_native_shock.py',
    'scripts/science/snapshot_shock_energy.py',
    'scripts/science/snapshot_energy.py',
    'scripts/science/pluto_h5_level3_ambient_extract.py',
    'scripts/science/select_common_age_hdf5.py',
    'scripts/science/xraise_grid_smoke.py',
    'scripts/science/measure_q031_fluxes.py',
    'scripts/kunanyi/q031_native_emission.pbs',
    'scripts/kunanyi/package_q031_native_pilot.py',
    'scripts/kunanyi/run_q031_measured.py',
    'scripts/kunanyi/package_q031_flux_results.py',
    'scripts/kunanyi/validate_q031_native_dependencies.py',
    'tests/test_q031_native_emission.py',
    'tests/test_q031_native_dependencies.py',
    'tests/test_q031_native_packaging.py',
    'tests/test_xraise_grid_smoke_projection.py',
    'tests/test_selected_age_native_shock.py',
    'tests/test_snapshot_shock_energy.py',
    'docs/science/q031_native_path_length_design_2026-10-31.md',
    'docs/science/q031_emissivity_extrapolation_2026-10-31.md',
]
pending = [Path(name) for name in names if name.startswith('scripts/science/')]
seen = set()
while pending:
    relative = pending.pop()
    if relative in seen:
        continue
    seen.add(relative)
    for node in ast.walk(ast.parse((repo / relative).read_text())):
        modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                   else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
        for module in modules:
            dependency = Path('scripts/science') / (module.split('.')[0] + '.py')
            if (repo / dependency).is_file():
                pending.append(dependency)
names = sorted(set(names) | {str(path) for path in seen})
for name in names:
    target = stage/name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(repo/name, target)
ref = repo/'docs/science/assets/q029_binary_native_refresh_2026-09-06/remote_analysis'
refs = ('source_manifest.csv', 'accepted_axial_shock_dynamics.csv',
        'control_threshold_calibration.csv', 'native_energy_selected_age.csv',
        'native_shock_energy_selected_age.csv', 'tracer_threshold_precision.csv')
for case in ('C-HI','G-HI'):
    target = stage/'inputs'/case
    target.mkdir(parents=True)
    for name in refs:
        shutil.copyfile(ref/case/name, target/name)
runtime = {
    'xraise.py':'4bf17cb8e63e2d87a06615c170c7dd307788554a0cee83409762223123ec8da5',
    'apec_corrections.txt':'e0f53a9f276a956f347af0e4fe627ee152762abc8b5116fc458070ee5f0925e3',
    'gaunt_lut_2d.npz':'64df88d39896f14064bb799fd5b70c6f68d20bcbdc5a15d19e2e4fd15b22f747',
}
(stage/'runtime_checksums.sha256').write_text(''.join(
    f'{digest}  /u/bwbrook/codex_kunanyi/xraise_runtime/{name}\n'
    for name,digest in sorted(runtime.items())))
origin = {
    'repository_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
    'scope':'C-HI and G-HI, retained snapshot40, 0/45/90 degrees, retained linear and clamp sensitivity',
    'authority':'Barry: Go ahead with the C-HI and G-HI 40 Myr native pilot, including the clamp sensitivity. Keep coordinating with Claude and respect the migration and flux job dependencies.',
    'authority_date':'2026-10-31',
    'native_dependencies':['870323.kunanyi-ohpc','870374.kunanyi-ohpc','successful same-stage real-kernel synthetic smoke'],
    'planned_resources':{'smoke':'2 CPUs / 8 GB / 1 h', 'pilot':'2 CPUs / 128 GB / 24 h'},
    'resource_rationale':'Kunanyi holds the native payloads; avoid TB-scale transfers. Historical Q029 mask peak about41GB, chunked emissivity and sequential cases. Target synthetic smoke measures implementation runtime before dependent native submission; pilot records each case peak RSS.',
    'native_payloads_staged':False,
}
(stage/'stage_origin.json').write_text(json.dumps(origin,indent=2)+'\n')
paths = sorted(p for p in stage.rglob('*') if p.is_file())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(stage/'stage_checksums.sha256').write_text(''.join(f'{sha(p)}  {p.relative_to(stage)}\n' for p in paths))
archive = stage.with_suffix('.tar.gz')
with tarfile.open(archive,'x:gz') as handle:
    for path in sorted(p for p in stage.rglob('*') if p.is_file()):
        info=handle.gettarinfo(str(path),arcname=str(path.relative_to(stage)))
        info.uid=info.gid=0
        info.uname=info.gname=''
        info.mtime=0
        info.mode=0o600
        with path.open('rb') as source:
            handle.addfile(info,source)
print(json.dumps({'stage':str(stage),'archive':str(archive),'archive_sha256':sha(archive),
                  'archive_bytes':archive.stat().st_size,'files':len(paths)+1,
                  'repository_head':origin['repository_head']},indent=2))
