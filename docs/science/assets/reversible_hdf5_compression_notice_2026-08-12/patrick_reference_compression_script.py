#!/usr/bin/env python

"""Patrick-supplied reference only; not yet approved for production mutation.

This file preserves the example submitted with the 2026-08-12 reversible
HDF5-compression proposal.  The associated agent-comms thread records the
validation and rollout gates required before operational use.
"""

import sys, os
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import time
import shutil
import textwrap

from plutokore import PlutoSimulation, ProcessedJetSimulation
import plutokore as pk

import h5py
import hdf5plugin


class LogStatement(object):
    def __init__(self, status_string, length=100, success="DONE", failure="FAILED"):
        self.wrapped_status_string = [
            s
            for s in textwrap.wrap(
                status_string,
                width=length,
                subsequent_indent="    ",
                break_on_hyphens=False,
            )
        ]
        self.wrapped_status_string[-1] = self.wrapped_status_string[-1].ljust(
            length, "."
        )
        for i in range(len(self.wrapped_status_string) - 1):
            self.wrapped_status_string[i] += "\n"
        self.success = success
        self.failure = failure

    def __enter__(self):
        self.start = time.time()
        for st in self.wrapped_status_string:
            print(st, end="", flush=True)

    def __exit__(self, type, value, traceback):
        elapsed = time.time() - self.start
        status_string = ""

        if type is None:
            status_string += self.success
        else:
            status_string += self.failure

        status_string += f" ({timedelta(seconds=elapsed)})"
        print(status_string)


def compress_simulation_output(*, output_path, overwrite=False):
    var_compression_args = hdf5plugin.Zfp(reversible=True)
    coord_compression_args = {"shuffle": True, "compression": "gzip"}

    compressed_path = f"{output_path}.compressed"
    zfp_id = "32013"

    if os.path.exists(compressed_path):
        print("Compressed file aready exists, skipping")
        print(f"Delete {compressed_path} to recompress")
        return

    with h5py.File(output_path, mode="r") as original_file:
        data_key = [s for s in list(original_file.keys()) if "Timestep" in s][0]
        if zfp_id in original_file[f"{data_key}/vars/rho"]._filters:
            print("Output file is already compressed, skipping")
            return

    print(f"Compressing {output_path}\n")
    start = time.time()
    start_size = os.path.getsize(output_path)

    try:
        with h5py.File(output_path, mode="r") as original_file, h5py.File(
            compressed_path, mode="x"
        ) as compressed_file:

            def _visit_recursive(name, object):
                if type(object) is h5py.Group:
                    with LogStatement(f"Creating group {name}"):
                        compressed_file.create_group(name)
                if type(object) is h5py.Dataset:
                    with LogStatement(f"Creating dataset {name}"):
                        if "coords" in object.parent.name:
                            comp_args = coord_compression_args
                        else:
                            comp_args = var_compression_args
                        compressed_file.create_dataset_like(
                            name, object, chunks=True, **comp_args
                        )
                    with LogStatement(f"Copying dataset {name}"):
                        compressed_file[name][...] = object[()]
                with LogStatement(f"Copying attributes for {name}"):
                    _copy_attributes(src_group=object, dest_group=compressed_file[name])

            def _copy_attributes(*, src_group, dest_group):
                if len(src_group.attrs) > 0:
                    for k, v in src_group.attrs.items():
                        dest_group.attrs[k] = v

            # copy base attributes
            with LogStatement("Copying base attributes"):
                _copy_attributes(src_group=original_file, dest_group=compressed_file)

            print("Begin recursively copying groups and datasets")
            original_file.visititems(_visit_recursive)
            print("Finish recursive copying")

            with LogStatement("Flushing buffers"):
                compressed_file.flush()

    except Exception as e:
        print(f"\nFailed to compress {output_path}:")
        print(e)
        print("")
        if os.path.exists(compressed_path):
            with LogStatement(f"Removing {compressed_path}"):
                os.remove(compressed_path)
        return

    end_size = os.path.getsize(compressed_path)

    if overwrite:
        with LogStatement(f"Moving {compressed_path} to {output_path}"):
            shutil.move(compressed_path, output_path)

    elapsed = time.time() - start
    ss_gb = start_size / (1024 ** 3)
    es_gb = end_size / (1024 ** 3)
    print(f"Succesfully compressed {output_path}.")
    print(
        f"Original: {ss_gb:.2f}GB | Compressed: {es_gb:.2f}GB | Compression ratio: {(ss_gb / es_gb):.2f}".ljust(
            100, "."
        )
        + f"{timedelta(seconds=elapsed)}"
    )


def main():
    parser = argparse.ArgumentParser()
    pk.scripts.add_simulation_catalogue_arguments(parser=parser)
    parser.add_argument(
        "--no-log", help="Disable logging", action="store_true",
    )
    parser.add_argument(
        "--skip-overwrite",
        help="Skip overwriting the uncompressed file with the compressed file.",
        action="store_false",
    )

    args = parser.parse_args()

    print(logo)

    sims_to_process = pk.scripts.get_sims_to_process(processed_args=args)

    print(f"Compressing simulations: {','.join([s.name for s in sims_to_process])}")

    for sim in sims_to_process:
        # setup log file
        if not args.no_log:
            from IPython.utils.io import Tee

            log_fname = sim.directory / "compression.log"

            with open(log_fname, "a") as lf:
                lf.write(logo)

            t = Tee(log_fname, mode="a", channel="stdout")

        # write some log info
        print(
            f"[{datetime.now().isoformat(timespec='seconds')}] Simulation compression script"
        )
        print(
            f"[{datetime.now().isoformat(timespec='seconds')}] Compressing {sim.group}:{sim.name}"
        )

        # get double outputs
        for dt, dt_ext in zip(["float", "double"], ["flt", "dbl"]):
            try:
                files = sorted(sim.directory.glob(f'data.*.{dt_ext}.h5'))

                completed_output_count = pk.simulations.get_hdf5_output_count(sim_path = sim.directory, data_type=dt)+1
                # try to avoid compressing files that are currently being written by a simulation
                files = files[:completed_output_count]

                for f in files:
                    compress_simulation_output(
                        output_path=f, overwrite=args.skip_overwrite,
                    )
                    t.flush()
            except Exception as e:
                print(e)
                pass

    if not args.no_log:
        t.close()

    return


logo = """
 _____ _____ _____ _____ _____ _____ _____ _____
|     |     |     |  _  | __  |   __|   __|   __|
|   --|  |  | | | |   __|    -|   __|__   |__   |
|_____|_____|_|_|_|__|  |__|__|_____|_____|_____|

"""
if __name__ == "__main__":
    main()
