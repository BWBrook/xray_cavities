#!/usr/bin/env python3
"""Run one Q-031 subprocess with measured exit, wall time and peak memory."""

from pathlib import Path
import resource
import subprocess
import sys
import time


def main() -> int:
    output = Path(sys.argv[1])
    command = sys.argv[2:]
    if not command:
        raise ValueError("A command is required")
    if sys.platform not in ("linux", "darwin"):
        raise RuntimeError("Peak RSS units are only defined here for Linux and macOS")
    with output.open("x") as handle:
        started = time.monotonic()
        result = subprocess.run(command, check=False)
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        peak_kib = usage.ru_maxrss / 1024 if sys.platform == "darwin" else usage.ru_maxrss
        status = result.returncode if result.returncode >= 0 else 128 - result.returncode
        handle.write("Measurement: Python resource.getrusage(RUSAGE_CHILDREN)\n")
        handle.write(f"Maximum resident set size (kbytes): {int(peak_kib)}\n")
        handle.write(f"Elapsed wall time (seconds): {time.monotonic() - started:.6f}\n")
        handle.write(f"User CPU time (seconds): {usage.ru_utime:.6f}\n")
        handle.write(f"System CPU time (seconds): {usage.ru_stime:.6f}\n")
        handle.write(f"Exit status: {status}\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
