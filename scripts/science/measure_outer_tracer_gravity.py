"""Measure saved-state tracer transport and radial gravitational work on native cells.

The nozzle-control grid and boxes are the ones used by measure_q031_fluxes.
Pass the native HDF5 variables group to measure_snapshot. Its sign convention
is outward positive at a face and work done on the gas positive in a volume.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from measure_q031_fluxes import ControlBox, Grid, UNIT_DENSITY_CGS, UNIT_LENGTH_CM, UNIT_VELOCITY_CMS


THRESHOLD = 1.e-3
SOLVER_LENGTH_CM = 3.0856775807e21
MASS_UNIT = UNIT_DENSITY_CGS * UNIT_LENGTH_CM**3
MASS_FLUX_UNIT = UNIT_DENSITY_CGS * UNIT_LENGTH_CM**2 * UNIT_VELOCITY_CMS
FACE_NAMES = tuple(f"{axis}_{side}" for axis in "xyz" for side in ("negative", "positive"))
WORK_FIELDS = ("inward_motion_erg_s", "outward_motion_erg_s", "net_erg_s")


def _gravity_table(path, grid):
    profile = np.loadtxt(path, ndmin=2)
    if (len(profile) < 2 or profile.shape[1] != 6 or not np.all(np.isfinite(profile[:, [0, 5]]))
            or profile[0, 0] != 0 or not np.all(np.diff(profile[:, 0]) > 0)):
        raise ValueError("expected a six-column atmosphere with radii increasing from zero")
    radius = profile[:, 0] / SOLVER_LENGTH_CM
    centre_extent = np.linalg.norm([np.max(np.abs(axis)) for axis in (grid.x, grid.y, grid.z)])
    if centre_extent > radius[-1]:
        raise ValueError("native cell centres exceed the tabulated gravity radius")
    return radius, profile[:, 5]


def _new_inventory():
    return dict(raw_positive_cell_volume_kpc3=0., raw_tagged_mass_g=0.,
                dilute_cell_volume_kpc3=0., dilute_tagged_mass_g=0.)


def _add_inventory(record, mass_density, volume, positive, dilute):
    record["raw_positive_cell_volume_kpc3"] += float(np.sum(volume, where=positive))
    record["raw_tagged_mass_g"] += float(np.sum(mass_density * volume)) * MASS_UNIT
    record["dilute_cell_volume_kpc3"] += float(np.sum(volume, where=dilute))
    record["dilute_tagged_mass_g"] += float(np.sum(mass_density * volume, where=dilute)) * MASS_UNIT


def _margin(mask, k, grid):
    xs, ys = np.flatnonzero(mask.any(axis=0)), np.flatnonzero(mask.any(axis=1))
    if not xs.size:
        return np.inf
    return min(grid.x_edges[xs[0]] - grid.x_edges[0], grid.x_edges[-1] - grid.x_edges[xs[-1] + 1],
               grid.y_edges[ys[0]] - grid.y_edges[0], grid.y_edges[-1] - grid.y_edges[ys[-1] + 1],
               grid.z_edges[k] - grid.z_edges[0], grid.z_edges[-1] - grid.z_edges[k + 1])


def _new_face():
    return dict(raw_min=1., raw_max=0., raw_positive_cells=0, raw_positive_area_kpc2=0.,
                raw_positive_cell_volume_kpc3=0., adjacent_tagged_mass_g=0.,
                all_gas_outward_g_s=0., all_gas_inward_g_s=0.,
                tagged_outward_g_s=0., tagged_inward_g_s=0.)


def _add_face(record, tracer, rho, velocity, sign, area, normal_width):
    if not np.all(np.isfinite(velocity)):
        raise ValueError("nonfinite outer-face velocity")
    gas_flux = rho * velocity * sign * area * MASS_FLUX_UNIT
    tag_flux = gas_flux * tracer
    positive = tracer > 0
    positive_area = float(np.sum(area, where=positive))
    record["raw_min"] = min(record["raw_min"], float(tracer.min()))
    record["raw_max"] = max(record["raw_max"], float(tracer.max()))
    record["raw_positive_cells"] += int(positive.sum())
    record["raw_positive_area_kpc2"] += positive_area
    record["raw_positive_cell_volume_kpc3"] += positive_area * normal_width
    record["adjacent_tagged_mass_g"] += float(np.sum(rho * tracer * area)) * normal_width * MASS_UNIT
    for name, flux in (("all_gas", gas_flux), ("tagged", tag_flux)):
        record[f"{name}_outward_g_s"] += float(np.sum(flux, where=flux > 0))
        record[f"{name}_inward_g_s"] += float(np.sum(flux, where=flux < 0))


def _work_components(work, radial_speed):
    return np.array([np.sum(work, where=radial_speed < 0),
                     np.sum(work, where=radial_speed > 0), np.sum(work)])


def measure_snapshot(variables, grid: Grid, boxes: dict[int, ControlBox], atmosphere_path: Path | None,
                     *, slab_depth=4, shell_kpc=20., gravity=True, labelled_power_erg_s=None):
    """Stream one snapshot. Fields use native (z, y, x) indexing and raw tracer.

    For cells crossing the 20-kpc cut, weight a piecewise-constant cell by
    its exact volume within the union of the six layers. Each corner is counted
    once. Margins use the nearest *cell edge* and an empty selection yields
    None. Face fluxes multiply the adjacent active-cell rho, normal v and tr1.
    Signed radial work uses the sixth atmosphere column in the retained solver.
    """
    if not isinstance(slab_depth, int) or slab_depth < 1 or not np.isfinite(shell_kpc) or shell_kpc <= 0:
        raise ValueError("slab_depth and shell_kpc must be positive")
    if labelled_power_erg_s is not None and (not np.isfinite(labelled_power_erg_s) or labelled_power_erg_s <= 0):
        raise ValueError("the labelled bipolar power must be positive")
    axes = (grid.x, grid.y, grid.z)
    nodes = (grid.x_edges, grid.y_edges, grid.z_edges)
    widths = (grid.dx, grid.dy, grid.dz)
    for axis, edges, width in zip(axes, nodes, widths, strict=True):
        if (edges.shape != (len(axis) + 1,) or not np.array_equal(np.diff(edges), width)
                or not np.all((edges[:-1] < axis) & (axis < edges[1:]))):
            raise ValueError("grid widths or centres disagree with native edges")
    if gravity and all(0. in axis for axis in axes):
        raise ValueError("the source's radial unit vector is undefined at a cell centred on the origin")
    nz, ny, nx = shape = tuple(len(axis) for axis in axes[::-1])
    names = ("rho", "tr1", "vx1", "vx2", "vx3")
    if any(variables[name].shape != shape for name in names):
        raise ValueError(f"native primitive shape differs from {shape}")
    for pad, box in boxes.items():
        if (pad != box.padding_cells or not (0 <= box.i0 <= box.i1 < nx and 0 <= box.j0 <= box.j1 < ny
                                             and 0 <= box.k0 <= box.k1 < nz)):
            raise ValueError(f"inconsistent control box p{pad}")
    if gravity:
        table_r, acceleration = _gravity_table(atmosphere_path, grid)
    inner_dx, inner_dy, inner_dz = [np.maximum(0., np.minimum(e[1:], e[-1] - shell_kpc)
                                                 - np.maximum(e[:-1], e[0] + shell_kpc)) for e in nodes]
    area_xy = grid.dy[:, None] * grid.dx[None, :]
    inner_xy = inner_dy[:, None] * inner_dx[None, :]
    radius_xy2 = grid.y[:, None]**2 + grid.x[None, :]**2
    inventories = {key: _new_inventory() for key in ("whole_grid", "boundary_shell")}
    faces = {key: _new_face() for key in FACE_NAMES}
    margin_raw = margin_threshold = np.inf
    whole_work = np.zeros(len(WORK_FIELDS))
    inside_work = {pad: np.zeros_like(whole_work) for pad in boxes}
    for start in range(0, nz, slab_depth):
        stop = min(start + slab_depth, nz)
        block = {key: variables[key][start:stop, :, :] for key in (names if gravity else names[:2])}
        if not gravity:
            edge_vx = [variables["vx1"][start:stop, :, i] for i in (0, nx - 1)]
            edge_vy = [variables["vx2"][start:stop, j, :] for j in (0, ny - 1)]
        for local, k in enumerate(range(start, stop)):
            rho, tracer = (np.asarray(block[name][local], dtype=np.float64) for name in names[:2])
            if not np.all(np.isfinite(rho) & (rho > 0) & np.isfinite(tracer) & (tracer >= 0) & (tracer <= 1)):
                raise ValueError(f"invalid raw density or tracer on z plane {k}")
            dz, z = grid.dz[k], grid.z[k]
            volume = area_xy * dz
            shell_volume = volume - inner_xy * inner_dz[k]
            positive, dilute = tracer > 0., (tracer > 0.) & (tracer < THRESHOLD)
            tagged_density = rho * tracer
            for name, weight in (("whole_grid", volume), ("boundary_shell", shell_volume)):
                _add_inventory(inventories[name], tagged_density, weight, positive, dilute)
            if margin_raw > 0:
                margin_raw = min(margin_raw, _margin(positive, k, grid))
            if margin_threshold > 0:
                margin_threshold = min(margin_threshold, _margin(tracer > THRESHOLD, k, grid))
            if gravity:
                vx, vy, vz = (np.asarray(block[name][local], dtype=np.float64) for name in names[2:])
                if not np.all(np.isfinite(vx) & np.isfinite(vy) & np.isfinite(vz)):
                    raise ValueError(f"nonfinite velocity on z plane {k}")
                radius = np.sqrt(radius_xy2 + z*z)
                radial_speed = (vx * grid.x[None, :] + vy * grid.y[:, None] + vz * z) / radius
                work = rho * volume * radial_speed * np.interp(radius, table_r, acceleration)
                whole_work += _work_components(work, radial_speed)
                for pad, box in boxes.items():
                    if box.k0 <= k <= box.k1:
                        cells = np.s_[box.j0:box.j1+1, box.i0:box.i1+1]
                        inside_work[pad] += _work_components(work[cells], radial_speed[cells])
            for side, index in enumerate((0, -1)):
                sign = (-1, 1)[side]
                _add_face(faces[FACE_NAMES[side]], tracer[:, index], rho[:, index],
                          vx[:, index] if gravity else edge_vx[side][local], sign, grid.dy * dz, grid.dx[index])
                _add_face(faces[FACE_NAMES[2+side]], tracer[index, :], rho[index, :],
                          vy[index, :] if gravity else edge_vy[side][local], sign, grid.dx * dz, grid.dy[index])
                if k == (0, nz-1)[side]:
                    normal = vz if gravity else np.asarray(variables["vx3"][k, :, :], dtype=np.float64)
                    _add_face(faces[FACE_NAMES[4+side]], tracer, rho, normal, sign, area_xy, dz)
    for row in faces.values():
        for name in ("all_gas", "tagged"):
            row[f"{name}_net_outward_g_s"] = row[f"{name}_inward_g_s"] + row[f"{name}_outward_g_s"]
    work_results = {}
    if gravity:
        regions = {"whole_grid": whole_work}
        for pad, inside in inside_work.items():
            regions[f"inside_p{pad}"] = inside
            regions[f"outside_p{pad}"] = whole_work - inside
        for name, parts in regions.items():
            rates = parts * (MASS_UNIT * UNIT_VELOCITY_CMS)
            work_results[name] = {key: float(value) for key, value in zip(WORK_FIELDS, rates, strict=True)}
            if labelled_power_erg_s is not None:
                work_results[name]["net_over_labelled_power"] = float(rates[-1] / labelled_power_erg_s)
    return {
        "tracer": {**inventories, "min_margin_raw_positive_kpc": float(margin_raw) if np.isfinite(margin_raw) else None,
                   "min_margin_above_threshold_kpc": float(margin_threshold) if np.isfinite(margin_threshold) else None},
        "face_tracer": faces, "gravity": work_results,
        "geometry": {"shell_depth_kpc": shell_kpc, "threshold": THRESHOLD,
                     "shell_volume_rule": "exact cut-cell volume in union of six boundary layers",
                     "flux_state": "outer active cell; signed normal velocity at the saved time",
                     "gravity_rule": "sixth column signed, linearly interpolated at Cartesian cell-centre radius"},
        "units": {"density_g_cm3": UNIT_DENSITY_CGS, "length_cm": UNIT_LENGTH_CM,
                  "velocity_cm_s": UNIT_VELOCITY_CMS, "atmosphere_radius_length_cm": SOLVER_LENGTH_CM,
                  "labelled_bipolar_power_erg_s": labelled_power_erg_s},
    }
