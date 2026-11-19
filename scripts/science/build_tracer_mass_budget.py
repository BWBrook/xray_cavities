"""Compare the retained mass of jet tracer with bipolar mass supply on the audited histories."""
from __future__ import annotations

import argparse
import csv
import json
import math
import tempfile
from itertools import product
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pluto_h5_level3_ambient_extract import derive_widths, UNIT_VELOCITY_CMS
from snapshot_energy import SECONDS_PER_MYR, sha256_file

ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets"
CENSUS = ASSETS / "four_case_fluid_snapshot_census_2026-08-25"
CALIBRATION = ASSETS / "nozzle_flux_calibration_2026-11-19"
FINAL = ASSETS / "three_case_final_interval_2026-11-19"
FIXED = {
    "C-HI": "turn18_high_review_2026-11-18/stage/results",
    "C-LO": "turn18_clo_review_2026-11-16/capture/stage/results",
    "G-HI": "turn18_high_review_2026-11-18/stage/results",
    "G-LO": "turn18_glo_fixed_2026-11-18/stage/results",
}


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def material(row):
    return row["side"] == "bipolar_total" and row["partition_method"] == "fractional"


def indexed(records):
    result = {}
    for row in records:
        index = int(row["snapshot_index"])
        if index in result:
            raise ValueError(f"Repeated snapshot {index}")
        result[index] = row
    return result


def check_hash(path, expected):
    if sha256_file(path) != expected:
        raise ValueError(f"Input hash differs for {path.name}")


def volume_bounds(axes_file):
    with np.load(axes_file, allow_pickle=False) as native:
        ratios = [np.diff(native[axis + "_edges"]) / derive_widths(native[axis]) for axis in "xyz"]
    return math.prod(float(r.min()) for r in ratios), math.prod(float(r.max()) for r in ratios)


def finite_volume_difference(mass, earlier_mass, lower, upper):
    """Each nonnegative inventory can have its own spatial distribution."""
    return lower * mass - upper * earlier_mass, upper * mass - lower * earlier_mass


def run_path(path):
    parts = Path(path).parts
    return parts[parts.index("xray_cavities_runs") + 1:]


def inventory(archive, case, reference, ramp, checksums):
    folder = CENSUS / "review_products" / case
    for name in ("energy_partition_timeseries.csv", "snapshot_manifest.csv"):
        target = folder / name
        check_hash(target, checksums[str(target.relative_to(ASSETS.parents[2]))])
    tagged = indexed(r for r in rows(folder / "energy_partition_timeseries.csv") if material(r))
    manifest = indexed(rows(folder / "snapshot_manifest.csv"))
    fixed = archive / FIXED[case] / f"fixed_{case}_full"
    completion = json.loads((fixed / "completion.json").read_bytes())
    hashes = {Path(f["path"]).name: f["sha256"] for f in completion["products"]}
    accepted = completion["indices"]
    if accepted != list(range(48 if case == "G-HI" else 51)):
        raise ValueError(f"Incomplete {case} fixed-volume history")
    selected = indexed(r for r in rows(ASSETS / "q029_binary_native_refresh_2026-09-06" /
                       "remote_analysis" / case / "native_energy_selected_age.csv") if material(r))
    bundle = archive / "turn19_nozzle_calibration/inputs"
    axes = bundle / case / "axes.npz"
    axis_receipt = json.loads((bundle / "axes_manifest.json").read_bytes())["cases"][case]
    check_hash(axes, axis_receipt["raw_sha256"])
    lower, upper = volume_bounds(axes)
    mass_rate = 2 * float(reference["bipolar_Q_erg_s"]) / (0.1 * UNIT_VELOCITY_CMS)**2
    prescribed_rate = float(reference["bipolar_mass_g_s"])
    base = float(tagged[0]["lobe_mass_g"])
    history = []
    for index in accepted:
        row, identity = tagged[index], manifest[index]
        file = fixed / f"snapshot_{index:04d}.json"
        check_hash(file, hashes[file.name])
        record = json.loads(file.read_bytes())
        bound = record["provenance"]["input_receipt_claims"]
        target = bound["inputs"]["current_h5"]
        time = float(row["actual_time_myr"])
        if (row["case"] != case or record["case"] != case or record["snapshot_index"] != index
                or time != record["actual_time_myr"] or time != float(identity["actual_time_myr"])
                or float(identity["actual_time_code"]) != bound["current"]["time_code"]
                or identity["timestep"] != bound["current"]["timestep"]
                or int(identity["file_size_bytes"]) != target["size_bytes"]
                or run_path(identity["input_h5"]) not in (run_path(target["path"]), run_path(target["resolved_path"]))
                or identity["shape_nz_ny_nx"] != "x".join(map(str, record["shape_nz_ny_nx"]))):
            raise ValueError(f"Native identity or time differs for {case}/{index}")
        tracer = record["tracer_diagnostics"]
        if (tracer["outside_unit_interval_cell_count"], tracer["minimum"], tracer["maximum"]) != (0, 0., 1.):
            raise ValueError(f"Clipping could change the fractional inventory for {case}/{index}")
        mass = float(row["lobe_mass_g"])
        if index in selected and not math.isclose(mass, float(selected[index]["lobe_mass_g"]), rel_tol=3e-12):
            raise ValueError(f"The selected-age reread disagrees for {case}/{index}")
        age = min(time, 50.0)
        label = mass_rate * age * SECONDS_PER_MYR
        if not math.isclose(label, 2*float(row["injected_energy_erg"])/(0.1*UNIT_VELOCITY_CMS)**2, rel_tol=1e-13):
            raise ValueError(f"Source label or clock differs for {case}/{index}")
        # All saved times fall outside the short pre-wrap ramp.
        loss_myr = 0.
        if ramp is not None:
            start, end = float(ramp["ramp_start_myr"]), float(ramp["ramp_end_myr"])
            if start < age < end:
                raise ValueError("A saved time intersects the ramp and needs a partial integral")
            if age >= end:
                loss_myr = (end - start) * 2 / math.pi
        prescribed = prescribed_rate * (age - loss_myr) * SECONDS_PER_MYR
        mass_low, mass_high = finite_volume_difference(mass, base, lower, upper)
        margin = record["operational_coverage"]["current_cocoon"]["extent"]["minimum_domain_face_margin_kpc"]
        history.append(dict(case=case, index=index, age_myr=time, retained_tagged_mass_g=mass,
                            initial_tagged_mass_g=base, delta_tagged_mass_g=mass-base, labelled_mass_g=label,
                            prescribed_mass_g=prescribed, delta_over_label=(mass-base)/label if label else None,
                            delta_over_prescription=(mass-base)/prescribed if prescribed else None,
                            exact_volume_lower_over_label=mass_low/label if label else None,
                            exact_volume_upper_over_label=mass_high/label if label else None,
                            thresholded_lobe_face_margin_kpc=margin))
    intervals = []
    for left, right in [(i-1, i) for i in accepted[1:]] + [(10, 30), (20, 30)]:
        a, b = history[left], history[right]
        label = b["labelled_mass_g"] - a["labelled_mass_g"]
        prescribed = b["prescribed_mass_g"] - a["prescribed_mass_g"]
        difference = b["retained_tagged_mass_g"] - a["retained_tagged_mass_g"]
        lo, hi = finite_volume_difference(b["retained_tagged_mass_g"], a["retained_tagged_mass_g"], lower, upper)
        intervals.append(dict(case=case, start_index=left, end_index=right, delta_tagged_mass_g=difference,
                              labelled_mass_g=label, prescribed_mass_g=prescribed, delta_over_label=difference/label,
                              delta_over_prescription=difference/prescribed, exact_volume_lower_over_label=lo/label,
                              exact_volume_upper_over_label=hi/label))
    return history, intervals


def nozzle_rows(archive, case, history):
    if case == "G-HI":
        folder = archive / "turn18_ghi_addendum_2026-11-19_r2/integrated"
        expected = json.loads((folder / "integration_receipt.json").read_bytes())["products_sha256"]["integrated_control_balances.csv"]
    else:
        folder = archive / "turn19_nozzle_calibration/production" / case
        receipt = json.loads((folder / "completion.json").read_bytes())
        expected, = (r["sha256"] for r in receipt["products"] if Path(r["path"]).name == "integrated_control_balances.csv")
    path = folder / "integrated_control_balances.csv"
    check_hash(path, expected)
    result = []
    for row in rows(path):
        end = float(row["interval_end_myr"])
        i = round(end)
        if not row["surface"].startswith("nozzle_control_p") or i != 30:
            continue
        a, b = history[i-1], history[i]
        if end != b["age_myr"] or float(row["interval_start_myr"]) != a["age_myr"] or row["case"] != case:
            raise ValueError(f"Unmatched nozzle time for {case}/{i}")
        measured = dict(case=case, padding_cells=int(row["surface"].removeprefix("nozzle_control_p")),
                        reconstruction=row["reconstruction"], time_rule=row["temporal_quadrature"])
        for label, prefix, ref in (("interval", "", b["labelled_mass_g"] - a["labelled_mass_g"]),
                                   ("cumulative", "cumulative_", b["labelled_mass_g"])):
            transport = float(row[prefix + "integrated_mass_flux_outward_g"])
            storage = float(row[prefix + "storage_mass_change_g"])
            source = float(row[prefix + "inferred_internal_mass_source_g"])
            if not math.isclose(source/ref, (transport+storage)/ref, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"Invalid nozzle mass balance for {case}")
            measured.update({label+"_labelled_mass_g": ref, label+"_net_outward_transport_g": transport,
                             label+"_storage_change_g": storage, label+"_inferred_source_g": source,
                             label+"_net_outward_over_label": transport/ref, label+"_source_over_label": source/ref})
        result.append(measured)
    choices = {(r["padding_cells"], r["reconstruction"], r["time_rule"]) for r in result}
    expected_choices = set(product((1, 2, 4), ("centered_primitives", "donor_cell_primitives"),
                                   ("left_rectangle", "trapezoid", "right_rectangle")))
    if len(result) != len(expected_choices) or choices != expected_choices:
        raise ValueError(f"Incomplete nozzle comparison for {case}")
    return result


def chart(history, intervals, path):
    fig, axes = plt.subplots(1, 2, figsize=(9.1, 3.8), sharex=True, sharey=True)
    for case, colour, ls in (("C-HI", "#19648a", "-"), ("C-LO", "#19648a", "--"),
                             ("G-HI", "#9c4327", "-."), ("G-LO", "#9c4327", ":")):
        series = [r for r in history if r["case"] == case and r["index"] > 0]
        annual = [r for r in intervals if r["case"] == case and r["end_index"] == r["start_index"] + 1]
        axes[0].plot([r["age_myr"] for r in series], [r["delta_over_label"] for r in series],
                     c=colour, ls=ls, lw=1.8, label=case)
        axes[1].plot([r["age_myr"] for r in series], [r["delta_over_label"] for r in annual], c=colour, ls=ls, lw=1.8)
    for ax, title in zip(axes, ("Since startup", "During each saved interval"), strict=True):
        ax.set_title(title, fontsize=11)
        ax.axhline(1, color=".4", lw=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.22)
        ax.set_xlabel("Age (Myr)")
    axes[0].set_ylabel("Gain in tagged mass / labelled mass")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=4, frameon=False)
    fig.subplots_adjust(left=.09, right=.98, top=.88, bottom=.27, wspace=.13)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run(archive, output):
    if output.exists():
        raise FileExistsError(output)
    checksums = {name: digest for digest, name in (line.split("  ", 1) for line in
                 (CENSUS / "local_asset_manifest.sha256").read_text().splitlines())}
    refs = {r["case"]: r for r in rows(CALIBRATION/"continuum_reference.csv") if r["padding_cells"] == "1"}
    clocks = {r["case"]: r for r in rows(FINAL/"source_clock.csv")}
    histories, intervals, nozzle = [], [], []
    for case in FIXED:
        history, changes = inventory(archive, case, refs[case], clocks.get(case), checksums)
        histories.extend(history)
        intervals.extend(changes)
        nozzle.extend(nozzle_rows(archive, case, history))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "results"
        stage.mkdir()
        for name, data in (("tagged_mass_history", histories), ("tagged_mass_intervals", intervals),
                           ("nozzle_mass_at_30_myr", nozzle)):
            with (stage/(name+".csv")).open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(data)
        chart(histories, intervals, stage/"tagged_mass.png")
        stage.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(args.archive_root, args.output)
