"""Apply the production nozzle estimator to conservative cell averages of the manufactured jet."""
from __future__ import annotations

import argparse
import csv
import math
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

import h5py
import numpy as np

import calibrate_nozzle_flux as primary

flux = primary.flux


@lru_cache(maxsize=None)
def gauss_unit(order):
    nodes, weights = np.polynomial.legendre.leggauss(order)
    return (nodes + 1) / 2, weights / 2


def split_slice(x_bounds, y_bounds, radius, nodes, weights):
    """Quadrature on the rectangular cross section, split along the circular jet edge."""
    xl, xh = x_bounds
    yl, yh = y_bounds
    breaks = {xl, xh}
    for y_edge in (yl, yh):
        knot = math.sqrt(max(0.0, radius**2 - y_edge**2))
        if xl < knot < xh:
            breaks.add(knot)
    for low_x, high_x in pairwise(sorted(breaks)):
        # This map removes the square-root endpoint at the tangent x = radius.
        x = high_x - (high_x - low_x) * nodes**2
        wx = 2 * (high_x - low_x) * nodes * weights
        cut = np.clip(np.sqrt(np.maximum(0.0, radius**2 - x**2)), yl, yh)
        for low_y, high_y in ((np.full_like(cut, yl), cut), (cut, np.full_like(cut, yh))):
            inside = high_y > low_y
            if not np.any(inside):
                continue
            height = high_y[inside] - low_y[inside]
            y = low_y[inside, None] + height[:, None] * nodes[None, :]
            d_area = wx[inside, None] * height[:, None] * weights[None, :]
            yield np.broadcast_to(x[inside, None], y.shape).ravel(), y.ravel(), d_area.ravel()


def cell_points(bounds, tangent, order):
    """Return positive-octant quadrature points and weights normalized by cell volume."""
    (xl, xh), (yl, yh), (zl, zh) = bounds
    nodes, weights = gauss_unit(order)
    near, far = math.hypot(xl, yl), math.hypot(xh, yh)
    if near >= tangent * zh or far <= tangent * zl:
        coords = [lo + (hi - lo) * nodes for lo, hi in bounds]
        x, y, z = np.meshgrid(*coords, indexing="ij")
        w = weights[:, None, None] * weights[None, :, None] * weights[None, None, :]
        return x.ravel(), y.ravel(), z.ravel(), w.ravel()

    breaks = {zl, zh}
    for x in (xl, xh):
        for y in (yl, yh):
            height = math.hypot(x, y) / tangent
            if zl < height < zh:
                breaks.add(height)
    chunks = []
    for low_z, high_z in pairwise(sorted(breaks)):
        z_nodes = low_z + (high_z - low_z) * nodes
        z_weights = (high_z - low_z) * weights
        for z, wz in zip(z_nodes, z_weights, strict=True):
            for x, y, d_area in split_slice(bounds[0], bounds[1], z * tangent, nodes, weights):
                chunks.append((x, y, np.full(y.size, z), wz * d_area))
    x, y, z, w = [np.concatenate(parts) for parts in zip(*chunks, strict=True)]
    volume = (xh - xl) * (yh - yl) * (zh - zl)
    return x, y, z, w / volume


def average_primitives(jet, bounds, order):
    x, y, z, weights = cell_points(bounds, math.tan(jet.angle), order)
    if not math.isclose(float(weights.sum()), 1.0, abs_tol=2e-12, rel_tol=0.0):
        raise ValueError("quadrature does not integrate the full cell volume")

    state = jet.state(x, y, z)
    rho = state["rho"]
    velocities = [state[f"vx{i}"] for i in (1, 2, 3)]
    density = np.dot(weights, rho)
    velocity = [np.dot(weights, rho * u) / density for u in velocities]
    thermal = state["prs"] / (flux.GAMMA_GAS - 1)
    kinetic = 0.5 * rho * sum(u * u for u in velocities)
    energy = np.dot(weights, thermal + kinetic)
    pressure = (flux.GAMMA_GAS - 1) * (energy - 0.5 * density * sum(u * u for u in velocity))
    if not math.isfinite(pressure) or pressure <= 0:
        raise ValueError("invalid pressure recovered from averaged conservative state")
    return density, pressure, *velocity


def averaged_surfaces(jet, grid, box, order):
    axes = (grid.x_edges, grid.y_edges, grid.z_edges)
    shape = (grid.z.size, grid.y.size, grid.x.size)
    selected = np.zeros(shape, dtype=bool)
    for dim in range(3):
        for layer in (slice(0, 2), slice(-2, None)):
            take = [slice(1, -1)] * 3
            take[dim] = layer
            selected[tuple(take)] = True

    fields = {name: np.full(shape, np.nan, dtype="<f4") for name in flux.PRIMITIVE_FIELDS}
    cache = {}
    for k, j, i in np.argwhere(selected):
        # The unrotated bipolar field is reflection-symmetric and invariant under x/y exchange.
        bounds, signs = [], []
        for axis, cell in zip(axes, (i, j, k), strict=True):
            lo, hi = axis[cell:cell + 2]
            if lo < 0 < hi:
                raise ValueError("cell symmetry requires grid faces at the origin")
            bounds.append((lo, hi) if lo >= 0 else (-hi, -lo))
            signs.append(1 if lo >= 0 else -1)
        swap = bounds[0] > bounds[1]
        if swap:
            bounds[0], bounds[1] = bounds[1], bounds[0]
        key = tuple(bounds)
        if key not in cache:
            if math.sqrt(sum(lo * lo for lo, _ in bounds)) < jet.source_radius:
                raise ValueError("the measuring stencil must lie outside the injection sphere")
            cache[key] = average_primitives(jet, key, order)
        rho, prs, vx, vy, vz = cache[key]
        if swap:
            vx, vy = vy, vx
        restored = (rho, prs, vx * signs[0], vy * signs[1], vz * signs[2])
        for field, value in zip(flux.PRIMITIVE_FIELDS, restored, strict=True):
            fields[field][k, j, i] = value

    totals = {}
    with h5py.File("synthetic_average.h5", "w", driver="core", backing_store=False) as h5:
        for name, field in fields.items():
            h5.create_dataset(name, data=field)
        for method in flux.CONTROL_RECONSTRUCTIONS:
            faces = flux.measure_control_surface(h5, grid, jet.environment, box, method)
            totals[method] = next(row for row in faces if row["face"] == "closed_surface_total")
    return totals


def run(inputs, out, orders):
    if len(orders) < 2 or list(orders) != sorted(set(orders)) or min(orders) < 2:
        raise ValueError("supply at least two increasing quadrature orders")
    if out.exists():
        raise FileExistsError(out)

    rows = []
    for case in primary.CASES:
        jet, full, boxes, _ = primary.load_case(inputs, case)
        labelled_power = 2 * jet.power
        for pad, box in boxes.items():
            grid, patch_box = primary.face_patch(full, box, 1)
            truth = primary.continuum(jet, (-grid.z_edges[1], grid.z_edges[-2]))
            centre = {row["method"]: row for row in primary.sample_surfaces(jet, grid, patch_box)
                      if row["face"] == "closed_surface_total"}
            for order in orders:
                measured = averaged_surfaces(jet, grid, patch_box, order)
                for method, average in measured.items():
                    row = {"case": case, "padding_cells": pad, "reconstruction": method,
                           "quadrature_order": order}
                    for kind in primary.COMPONENTS:
                        field = f"{kind}_flux_outward_erg_s"
                        row[f"{kind}_reference_over_label"] = truth[field] / labelled_power
                        row[f"{kind}_cell_centre_over_label"] = centre[method][field] / labelled_power
                        row[f"{kind}_conservative_average_over_label"] = average[field] / labelled_power
                    mass = "mass_flux_outward_g_s"
                    row["mass_centre_over_reference"] = centre[method][mass] / truth[mass]
                    row["mass_average_over_reference"] = average[mass] / truth[mass]
                    rows.append(row)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", newline="") as fp:
        writer = csv.DictWriter(fp, list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--orders", type=int, nargs="+", default=(4, 8, 16))
    args = parser.parse_args()
    run(args.inputs, args.output, tuple(args.orders))
