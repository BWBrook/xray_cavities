"""Reconstruct transport through native cell unions and their exact changes in membership."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import math

import numpy as np

from measure_q031_fluxes import (
    CONTROL_RECONSTRUCTIONS, GAMMA_GAS, PRIMITIVE_FIELDS, UNIT_DENSITY_CGS,
    UNIT_ENERGY_ERG, UNIT_LENGTH_CM, _validate_primitive_state, flux_components,
)


AXES = ("z", "y", "x")
VELOCITY = ("vx3", "vx2", "vx1")
PATCHES = ("internal", *(f"{a}_{side}" for a in AXES for side in ("negative", "positive")))
STOCK_FIELDS = ("mass_g", "thermal_erg", "kinetic_erg", "gravitational_erg")
MASS_UNIT = UNIT_DENSITY_CGS * UNIT_LENGTH_CM**3
ROLES = ("previous", "current", "next")
DIRECTIONS = (("previous", "current"), ("current", "next"))


@dataclass(frozen=True)
class _Block:
    start: int
    stop: int
    halo_stop: int
    width: float
    min2: float
    max2: float
    halo_min2: float
    halo_max2: float


def _blocks(centres, widths, step):
    squared = centres**2
    blocks = []
    for start in range(0, len(centres), step):
        stop = min(start + step, len(centres))
        halo_stop = min(stop + 1, len(centres))
        core = squared[start:stop]
        halo = squared[start:halo_stop]
        blocks.append(_Block(start, stop, halo_stop, float(widths[start:stop].sum()),
                             core.min(), core.max(), halo.min(), halo.max()))
    return blocks


def _bound(tile, key):
    return math.sqrt(getattr(tile[1], key) + getattr(tile[2], key) + getattr(tile[0], key))


def _output_rates(values):
    mass, enthalpy, kinetic, gravity = map(float, values)
    return {"mass_flux_outward_g_s": mass,
            "thermal_advective_flux_outward_erg_s": enthalpy / GAMMA_GAS,
            "pressure_work_outward_erg_s": enthalpy * ((GAMMA_GAS - 1) / GAMMA_GAS),
            "kinetic_flux_outward_erg_s": kinetic, "gravitational_flux_outward_erg_s": gravity,
            "gas_flux_outward_erg_s": math.fsum((enthalpy, kinetic)),
            "total_energy_flux_outward_erg_s": math.fsum((enthalpy, kinetic, gravity))}


class _Surface:
    def __init__(self):
        self.cells = 0
        self.volume = np.longdouble(0)
        self.faces = np.zeros(len(PATCHES), dtype=np.int64)
        self.area = np.zeros(len(PATCHES), dtype=np.longdouble)
        self.rates = np.zeros((len(CONTROL_RECONSTRUCTIONS), len(PATCHES), 4), dtype=np.longdouble)

    def finish(self, radius, inradius):
        def geometry(indices):
            return {"face_count": int(self.faces[indices].sum()), "area_kpc2": float(self.area[indices].sum())}

        parts = {"internal": slice(0, 1), "domain": slice(1, None), "total": slice(None)}
        return {
            "radius_kpc": None if radius is None else float(radius), "cell_count": int(self.cells),
            "volume_kpc3": float(self.volume),
            "domain_contact": bool(np.any(self.faces[1:])),
            "sphere_fully_inside_domain": None if radius is None else bool(radius <= inradius),
            "geometry": {key: geometry(loc) for key, loc in parts.items()},
            "box_faces": {PATCHES[i]: geometry(slice(i, i + 1)) for i in range(1, len(PATCHES))},
            "flux": {method: {part: _output_rates(self.rates[i, loc].sum(axis=0))
                              for part, loc in parts.items()}
                     for i, method in enumerate(CONTROL_RECONSTRUCTIONS)},
        }


def _faces(mask, shape, tile, dimensions):
    # The lower-index cell owns each internal face, including a tile's positive halo.
    core = [slice(0, n) for n in shape]
    for axis, block in enumerate(tile):
        length = shape[axis] - int(block.stop == dimensions[axis])
        left, right = core.copy(), core.copy()
        left[axis], right[axis] = slice(0, length), slice(1, length + 1)
        left_mask, right_mask = mask[tuple(left)], mask[tuple(right)]
        low = np.nonzero(left_mask != right_mask)
        if low[0].size:
            high = list(low)
            high[axis] = low[axis] + 1
            sign = np.where(left_mask[low], 1.0, -1.0)
            yield axis, 0, low, tuple(high), sign
        for upper in (False, True):
            if (block.stop == dimensions[axis] if upper else block.start == 0):
                edge = shape[axis] - 1 if upper else 0
                plane = core.copy()
                plane[axis] = slice(edge, edge + 1)
                idx = list(np.nonzero(mask[tuple(plane)]))
                if idx[0].size:
                    idx[axis] += edge
                    yield axis, 1 + 2 * axis + int(upper), tuple(idx), None, (1.0 if upper else -1.0)


def _accumulate_face(surface, face, now, tile, axes, widths, edges, environment):
    axis, patch, low, high, sign = face
    idx = tuple(b.start + i for b, i in zip(tile, low, strict=True))
    tangents = [i for i in range(3) if i != axis]
    area = widths[tangents[0]][idx[tangents[0]]] * widths[tangents[1]][idx[tangents[1]]]
    coord = [a[i] for a, i in zip(axes, idx, strict=True)]
    edge_index = idx[axis] + int(high is not None or patch % 2 == 0)
    point = edges[axis][edge_index]
    coord[axis] = point
    radius = np.sqrt(coord[1]**2 + coord[2]**2 + coord[0]**2)
    phi = environment.potential_at_radius(radius * UNIT_LENGTH_CM)
    if not np.isfinite(phi).all():
        raise ValueError("nonfinite potential on an aperture face")
    left = {name: now[name][low] for name in PRIMITIVE_FIELDS}
    if high is None:
        states = (left,)
    else:
        right = {name: now[name][high] for name in PRIMITIVE_FIELDS}
        lower = axes[axis][idx[axis]]
        upper = axes[axis][idx[axis] + 1]
        centred = {k: ((upper - point) * left[k] + (point - lower) * right[k]) / (upper - lower)
                   for k in PRIMITIVE_FIELDS}
        from_inside = sign * centred[VELOCITY[axis]] >= 0
        use_left = np.where(sign > 0, from_inside, ~from_inside)
        donor = {k: np.where(use_left, left[k], right[k]) for k in PRIMITIVE_FIELDS}
        states = (centred, donor)
    surface.faces[patch] += area.size
    surface.area[patch] += area.sum()
    for i, state in enumerate(states):
        rates = flux_components(state, normal_component=VELOCITY[axis], normal_sign=sign,
                                area_kpc2=area, potential_cm2_s2=phi)
        values = [rates[k] for k in ("mass_flux_outward_g_s", "enthalpy_flux_outward_erg_s",
                                     "kinetic_flux_outward_erg_s", "potential_flux_outward_erg_s")]
        if not np.isfinite(values).all():
            raise ValueError("nonfinite aperture face flux")
        if high is None:
            surface.rates[:, patch] += values
        else:
            surface.rates[i, patch] += values


def _stock_change(now, initial, idx, volume, radius, environment):
    mass = (now["rho"][idx] - initial["rho"][idx]) * volume * MASS_UNIT
    thermal = (now["prs"][idx] - initial["prs"][idx]) * volume * (UNIT_ENERGY_ERG / (GAMMA_GAS - 1))
    speed2 = sum(now[v][idx]**2 for v in VELOCITY)
    speed20 = sum(initial[v][idx]**2 for v in VELOCITY)
    kinetic = 0.5 * (now["rho"][idx] * speed2 - initial["rho"][idx] * speed20) * volume * UNIT_ENERGY_ERG
    gravitational = mass * environment.potential_at_radius(radius * UNIT_LENGTH_CM)
    moments = np.array([x.sum() for x in (mass, thermal, kinetic, gravitational)])
    if not np.isfinite(moments).all():
        raise ValueError("nonfinite change of stock in a swept aperture shell")
    return moments


def _read(variables, selection):
    return _validate_primitive_state({k: variables[k][selection] for k in PRIMITIVE_FIELDS})


def _validate_inputs(current, initial, grid, radii, tile_shape):
    axes = tuple(np.asarray(getattr(grid, a), dtype=float) for a in AXES)
    edges = tuple(np.asarray(getattr(grid, a + "_edges"), dtype=float) for a in AXES)
    widths = tuple(np.asarray(getattr(grid, "d" + a), dtype=float) for a in AXES)
    for c, e, w in zip(axes, edges, widths, strict=True):
        if (c.ndim != 1 or len(c) == 0 or len(e) != len(c) + 1 or not np.all(np.diff(c) > 0)
                or not np.isfinite(e).all() or not np.all((c > e[:-1]) & (c < e[1:]))
                or not np.array_equal(w, np.diff(e)) or not e[0] < 0 < e[-1]):
            raise ValueError("invalid native centres, widths, or edges for an origin-centred aperture")
    shape = tuple(map(len, axes))
    if any(fields[k].shape != shape for fields in (current, initial) for k in PRIMITIVE_FIELDS):
        raise ValueError("native primitive shape differs from the z,y,x grid")
    if len(tile_shape) != 3 or any(not isinstance(n, (int, np.integer)) or n <= 0 for n in tile_shape):
        raise ValueError("tile_shape must have three positive integers in z,y,x order")
    if set(radii) != {"R100", "R300"}:
        raise ValueError("both R100 and R300 are required")
    for roles in radii.values():
        if "current" not in roles or set(roles).difference(ROLES):
            raise ValueError("radius records require current and optional previous and next")
        if any(r is not None and (not np.isfinite(r) or r < 0) for r in roles.values()):
            raise ValueError("radius must be nonnegative and finite or None")
    return axes, widths, edges


def measure_snapshot(*, current, initial, grid, environment, radii, tile_shape=(8, 96, 160)):
    """Measure face fluxes and endpoint perturbation stocks between consecutive aperture masks.

    Primitive mappings contain native z,y,x arrays (or HDF5 datasets) in code units.
    Radii in kpc are keyed by R100/R300 and previous/current/next. Omit unavailable
    temporal neighbours; an explicit None is a measured empty aperture. Sweeps always
    describe the later mask minus the earlier mask at this single endpoint state.
    """
    axes, widths, edges = _validate_inputs(current, initial, grid, radii, tile_shape)
    dims = tuple(map(len, axes))
    chunks = [_blocks(a, w, step) for a, w, step in zip(axes, widths, tile_shape, strict=True)]
    unique = {r for roles in radii.values() for r in roles.values()}
    # The saved sphere stock uses the next representable radius to include a defining centre.
    limits = {r: -math.inf if r is None else float(np.nextafter(float(r), math.inf)) for r in unique}
    surface = {r: _Surface() for r in unique}
    pairs = {(roles[old], roles[new]) for roles in radii.values() for old, new in DIRECTIONS
             if old in roles and new in roles}
    swept = {pair: np.zeros(len(STOCK_FIELDS), dtype=np.longdouble) for pair in pairs}
    read_tiles = {"current": 0, "initial": 0}

    for tile in product(*chunks):
        shape = tuple(b.stop - b.start for b in tile)
        lower, upper = _bound(tile, "min2"), _bound(tile, "max2")
        halo_min, halo_max = _bound(tile, "halo_min2"), _bound(tile, "halo_max2")
        on_box = any(b.start == 0 or b.stop == n for b, n in zip(tile, dims, strict=True))
        for r, limit in limits.items():
            if upper <= limit:
                surface[r].cells += math.prod(shape)
                surface[r].volume += math.prod(b.width for b in tile)
        partial = [r for r, limit in limits.items() if lower <= limit < upper]
        surfaces = [r for r, limit in limits.items()
                    if halo_min <= limit < halo_max or (on_box and lower <= limit)]
        shells = [pair for pair in pairs if pair[0] != pair[1]
                  and upper > min(limits[pair[0]], limits[pair[1]]) and lower <= max(limits[pair[0]], limits[pair[1]])]
        if not (partial or surfaces or shells):
            continue

        core = tuple(slice(b.start, b.stop) for b in tile)
        halo = tuple(slice(b.start, b.halo_stop) for b in tile)
        interior = tuple(slice(0, n) for n in shape)
        z, y, x = [a[s] for a, s in zip(axes, halo, strict=True)]
        radius = np.sqrt((y[:, None]**2 + x[None, :]**2)[None, :, :] + z[:, None, None]**2)
        core_radius = radius[interior]
        dz, dy, dx = [w[s] for w, s in zip(widths, core, strict=True)]
        volume = dz[:, None, None] * (dy[:, None] * dx[None, :])[None, :, :]
        for r in partial:
            membership = core_radius <= limits[r]
            surface[r].cells += np.count_nonzero(membership)
            surface[r].volume += volume[membership].sum()
        face_groups = [(r, face) for r in surfaces for face in _faces(radius <= limits[r], shape, tile, dims)]
        selected = []
        for pair in shells:
            old, new = (limits[r] for r in pair)
            idx = np.nonzero((core_radius > min(old, new)) & (core_radius <= max(old, new)))
            if idx[0].size:
                selected.append((pair, 1 if new > old else -1, idx))
        if not (face_groups or selected):
            continue
        now = _read(current, halo)
        read_tiles["current"] += 1
        for r, face in face_groups:
            _accumulate_face(surface[r], face, now, tile, axes, widths, edges, environment)
        if selected:
            before = _read(initial, core)
            read_tiles["initial"] += 1
            for pair, sign, idx in selected:
                swept[pair] += sign * _stock_change(now, before, idx, volume[idx], core_radius[idx], environment)

    inradius = min(min(-e[0], e[-1]) for e in edges)
    finished = {r: s.finish(r, inradius) for r, s in surface.items()}
    result = {}
    for name, roles in radii.items():
        changes = {}
        for old, new in DIRECTIONS:
            if old in roles and new in roles:
                r0, r1 = roles[old], roles[new]
                values = {k: float(x) for k, x in zip(STOCK_FIELDS, swept[r0, r1], strict=True)}
                changes[f"{old}_to_{new}"] = {
                    "cell_count_delta": int(surface[r1].cells - surface[r0].cells),
                    "volume_delta_kpc3": float(surface[r1].volume - surface[r0].volume),
                    **values, "total_energy_erg": math.fsum(values[k] for k in STOCK_FIELDS[1:]),
                }
        result[name] = {"surfaces": {role: finished[r] for role, r in roles.items()}, "sweeps": changes}
    return {"apertures": result, "tile_shape_zyx": list(map(int, tile_shape)), "primitive_tiles_read": read_tiles,
            "internal_face_methods": list(CONTROL_RECONSTRUCTIONS), "domain_face_method": "outer_active_cell"}
