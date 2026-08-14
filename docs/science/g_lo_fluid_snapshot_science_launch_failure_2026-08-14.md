# G-LO fluid snapshot science launch failure

PBS `785483.kunanyi-ohpc` / `g_lo_fluid` ended after `00:00:13` with
`Exit_status=1`, zero CPU time, and no HDF5 analysis.

The staged hashes, six retained snapshot identities, grid/timestep contract,
and Stewart atmosphere table all passed. The first failing line was a Bash
portability defect: an empty optional-argument array was expanded under
`set -u`, which Kunanyi treated as an unbound variable.

The wrapper now uses positional arguments for the optional `--resume` flag and
has a regression test excluding the failed pattern. Original stdout, stderr,
and final scheduler evidence are preserved under the matching asset directory.
This failed record contains no scientific result.
