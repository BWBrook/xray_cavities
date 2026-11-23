"""Extract the exposed G-HI/20 PRAiSE2 particle slice from the production cache."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import h5py
import numpy as np


def extract(cache_path, emissivity_path, output):
    with emissivity_path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != "aa0dd8f53e41e3e4e480194a95ac8ad3978ad8955e9ecd7217f7f1cde52b3631":
            raise ValueError("The production emissivity store changed")
    with h5py.File(cache_path) as cache, h5py.File(emissivity_path) as store:
        identity = json.loads(store.attrs["identity"])
        if (store.attrs["status"] != "complete_corrected_praise2_emissivity"
                or identity["cache_sha256"] != "069755aa70d02df4f8988a27d89dc0d93d26cd4d0a98a6004b74e640b3494c8d"
                or identity["praise2_commit"] != "73210e15d4c60e77ffb317b3ee2b9209c049edd4"):
            raise ValueError("Expected the completed G-HI production cache and source")
        ids = cache["endpoint_ids"][:]
        if hashlib.sha256(ids.astype(np.int64).tobytes()).hexdigest() != identity["endpoint_ids_sha256"]:
            raise ValueError("G-HI cache ID digest changed")
        [i] = np.flatnonzero(store["target_columns"][:] == 2000)
        active = store["active"][i]
        if (int(active.sum()) != 78918 or not np.all(store["source_column"][i][active] == 2000)
                or cache["output_indices"][2000] != 2000):
            raise ValueError("G-HI/20 particle support or emission column changed")
        np.savez_compressed(
            output, ids=ids[active], times=cache["times"][2000],
            tracer=cache["tracer"][:, 2000][active], tinj=cache["tinj"][:][active],
            last_shock_time=cache["last_shock_time"][:, 2000][active],
            pressure=cache["pressure"][:, 2000][active], density=cache["density"][:, 2000][active],
            lossless=store["lossless"][i][active], full_loss=store["full"][i][active],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("history_cache", type=Path)
    parser.add_argument("emissivity_store", type=Path)
    args = parser.parse_args()
    extract(args.history_cache, args.emissivity_store, sys.stdout.buffer)
