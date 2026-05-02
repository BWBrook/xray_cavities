#!/usr/bin/env python3
"""Inspect a jet-setup tabulated environment file.

The expected format is six whitespace-separated cgs columns:
radius, density, pressure, temperature, gravitational acceleration, and
gravitational acceleration again.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


COLUMNS = [
    "radius_cm",
    "density_g_cm3",
    "pressure_dyn_cm2",
    "temperature_k",
    "gravity_1_cm_s2",
    "gravity_2_cm_s2",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect a six-column jet-setup tabulated environment file."
    )
    parser.add_argument("path", type=Path, help="Tabulated environment file to inspect.")
    parser.add_argument("--label", default="", help="Optional label for the report.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    parser.add_argument("--output", type=Path, help="Optional output file.")
    return parser.parse_args()


def inspect(path: Path, label: str = "") -> dict[str, object]:
    rows: list[list[float]] = []
    bad_lines: list[str] = []

    with path.open() as handle:
        for lineno, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != len(COLUMNS):
                bad_lines.append(f"line {lineno}: expected 6 columns, found {len(parts)}")
                continue
            try:
                values = [float(part) for part in parts]
            except ValueError as exc:
                bad_lines.append(f"line {lineno}: {exc}")
                continue
            if not all(math.isfinite(value) for value in values):
                bad_lines.append(f"line {lineno}: non-finite value")
                continue
            rows.append(values)

    if not rows:
        raise SystemExit(f"{path}: no valid data rows found")

    columns = list(zip(*rows))
    stats = {
        name: {
            "min": min(values),
            "max": max(values),
            "first": values[0],
            "last": values[-1],
        }
        for name, values in zip(COLUMNS, columns)
    }
    radii = columns[0]
    strictly_increasing = all(a < b for a, b in zip(radii, radii[1:]))

    return {
        "label": label,
        "path": str(path),
        "rows": len(rows),
        "columns": COLUMNS,
        "units": "cgs",
        "strictly_increasing_radius": strictly_increasing,
        "bad_line_count": len(bad_lines),
        "bad_lines": bad_lines[:20],
        "stats": stats,
    }


def render_markdown(report: dict[str, object]) -> str:
    stats = report["stats"]
    assert isinstance(stats, dict)
    label = report["label"] or Path(str(report["path"])).name
    lines = [
        f"# Tabulated Environment Inspection: {label}",
        "",
        f"- path: `{report['path']}`",
        f"- rows: `{report['rows']}`",
        f"- units: `{report['units']}`",
        f"- strictly increasing radius: `{report['strictly_increasing_radius']}`",
        f"- bad line count: `{report['bad_line_count']}`",
        "",
        "| Column | First | Last | Min | Max |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in COLUMNS:
        values = stats[name]
        assert isinstance(values, dict)
        lines.append(
            "| {name} | {first:.6e} | {last:.6e} | {min:.6e} | {max:.6e} |".format(
                name=name,
                first=values["first"],
                last=values["last"],
                min=values["min"],
                max=values["max"],
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    report = inspect(args.path.expanduser(), args.label)
    if args.json:
        text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    else:
        text = render_markdown(report)

    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
