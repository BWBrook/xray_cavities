"""Small kunanyi compatibility shim for uncompressed plutokore HDF5 writes.

The site Anaconda module used for these smoke jobs does not include the
external hdf5plugin package. Returning an empty kwargs mapping lets the
plutokore import path and optional save helpers fall back to standard HDF5
datasets for smoke-test products.
"""


def Zfp(**_kwargs):
    return {}
