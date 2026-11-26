"""Serve native z,y,x transport tiles from bounded, contiguous HDF5 z-stripes."""
from __future__ import annotations

import numpy as np

from measure_q031_fluxes import PRIMITIVE_FIELDS


class _SlabField:
    def __init__(self, dataset, max_planes):
        self.dataset = dataset
        self.shape = dataset.shape
        self.dtype = dataset.dtype
        if len(self.shape) != 3:
            raise ValueError("Native transport fields must have z,y,x dimensions")
        self.max_planes = min(max_planes, self.shape[0])
        self.buffer = None
        self.start = self.stop = 0
        self.tile_requests = 0
        self.hdf5_reads = 0
        self.read_bytes = 0

    def __getitem__(self, key):
        self.tile_requests += 1
        if isinstance(key, tuple) and len(key) == 3 and all(
            isinstance(s, slice) and s.step in (None, 1) for s in key
        ):
            start, stop, _ = key[0].indices(self.shape[0])
            limits = [s.indices(n) for s, n in zip(key[1:], self.shape[1:], strict=True)]
            if 0 < stop - start <= self.max_planes and all(a < b for a, b, _ in limits):
                if not (self.start <= start and stop <= self.stop):
                    self._load(start, stop)
                z = slice(start - self.start, stop - self.start)
                return self.buffer[z, key[1], key[2]].copy(order="C")
        data = self.dataset[key]
        self.hdf5_reads += 1
        self.read_bytes += data.nbytes
        return data

    def _load(self, start, stop):
        if self.buffer is None:
            self.buffer = np.empty((self.max_planes, *self.shape[1:]), dtype=self.dtype)
        source_start = start
        if self.start <= start < self.stop < stop:
            # The next stripe can reuse the previous positive halo. A core may also grow a halo.
            source_start = self.stop
            if start > self.start:
                offset = start - self.start
                remaining = self.stop - start
                self.buffer[:remaining] = self.buffer[offset:offset + remaining].copy()
        self.start = self.stop = 0
        self.dataset.read_direct(
            self.buffer,
            source_sel=np.s_[source_start:stop, :, :],
            dest_sel=np.s_[source_start - start:stop - start, :, :],
        )
        self.start, self.stop = start, stop
        self.hdf5_reads += 1
        self.read_bytes += (stop - source_start) * self.shape[1] * self.shape[2] * self.dtype.itemsize


def slab_fields(variables, max_planes=9):
    """Wrap the five open primitive datasets. Pass the same mapping twice at time zero.

    Each field reads at most one full-xy stripe into its cache. Other HDF5 index
    forms pass straight through. Returned tiles have native dtype and independent storage.
    """
    if not isinstance(max_planes, (int, np.integer)) or max_planes < 1:
        raise ValueError("max_planes must be a positive integer")
    return {name: _SlabField(variables[name], max_planes) for name in PRIMITIVE_FIELDS}
