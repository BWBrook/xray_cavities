# Independent review record

Codex subagents reviewed the migration transition adapter and flux implementation
on 31 October 2026. This record summarizes checks actually reported and observed;
review agreement does not replace live hash, receipt or numerical gates.

## Migration

Reviewed runner SHA-256:
`c5623e0e5135862f842cec593d69ca5513ee17a0030d645c0f2dade8ce7d7241`.

The adapter is restricted to unit 8, its plan/manifest/unit/path identities,
all 7,129 entries, exact NFS exports and the observed device transition 46 to 45.
It leaves the manifest unchanged and requires a new source/archive hash epoch.
Old records cannot authorize promotion. Interrupted fresh hashing requires
unchanged full signatures and the same transition receipt. Frozen promotion,
compatibility-link and deletion guards remain in force for all units.

Thirty migration tests and ten tampering subtests passed. An independent
negative control changed a promoted archive file to different same-size bytes,
then restored its mtime. Cleanup rejected the changed ctime/full signature and
retained the tombstone. No safety blocker was found. Both migration suites and
file/directory fsync probes subsequently passed on the actual copy node.

## Flux science and cache

Reviewed cache runner SHA-256:
`333d8edfad3849be50b2b0a3da481b5c273a442a012b2368e6eaf9b225546953`.

Formula review covered signs, units, enthalpy pressure work, exact stretched
geometry, array ordering and source-enclosing control-volume interpretation.
The measurements remain reconstructions from saved fields, with spatial and
temporal sensitivities, rather than solver-integrated Riemann fluxes.

The cache-only diff was compared with the retained r3 bundle. Coordinate-encoded
active/inner planes, including negative indices, matched directly read arrays
for shapes (4,5,6), (7,4,9), (6,8,4), (5,6,7), and (1014,4,4).
Nonuniform-grid HDF5 flux dictionaries matched exactly for both reconstructions.
The cache calculation succeeded after HDF5 closure and rejects missing slabs.
Storage-first execution changes no equations, mutable scientific state or output
ordering. Fifteen focused tests, compilation and whitespace checks passed.

Cache allocation on (1014,960,960) is 458,956,800 bytes (437.695 MiB); an
independent process touching the cache peaked at 479.4 MiB RSS. Live performance
is established only by the remote smoke, not by this allocation calculation.
