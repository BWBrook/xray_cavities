# Independent target-build audit

No material build/configuration mismatch was found before the full-run gate.
The independent reviewer verified all 29 payload hashes and all 740 final
frozen-stage checksum results. Pinned source revisions, eight guarded preimages,
ten patched/new after-hashes and the build manifest binding agree.

Compiled definitions are 3-D Cartesian HD, RK2, vector gravity, ideal EOS,
selective entropy, one tracer, with cooling, radiation and particles off.
All eight staged input variants share the definitions hashes. The exact
compiled unit constants match the new native validator.

The build used mpicc with MPI, asynchronous I/O and HDF5. GCC 12.3,
OpenMPI 4.1.5 and HDF5 1.14 gompi modules agree with linked-library evidence.
The target XML contains 77 tests, zero failures/errors/skips; the reviewer
found no compiler error or warning in the captured log.

The executable itself is retained remotely, not in this downloaded bundle.
Its recorded hash therefore cannot be recomputed locally from this package.
The frozen wrapper verifies it before launch; full-run acceptance additionally
requires each successful smoke receipt to bind the same binary hash and pass
native, pair-identity and budget validation.

Verdict: conditionally supported; no frozen-build correction indicated.
