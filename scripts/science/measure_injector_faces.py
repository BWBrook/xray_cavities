"""Saved-time flux from the production spherical injector to freely evolved cells.

`measure` takes primitive arrays [z,y,x], coordinate centres/edges in (x,y,z)
order, and returns code-unit rates, positive out of the flagged sphere. The
surface is the union of Cartesian faces with exactly one flagged neighbour.
Cap/stationary refers to that inner cell. A flux crossing an internal
cap-to-stationary face never enters the evolved domain.

The production settings are in the retained case's definitions.h,
definitions_usr.h, pluto.ini and jet.c/init.c. The PLUTO source checked here
is commit 2674fc38b152f96605cb24e2840e92b64ebd5b81. Relevant routines are
Src/States/plm_states.c (States, primitive MINMOD), HD/hll_speed.c (Davis),
HD/hllc.c, HD/fluxes.c, adv_flux.c, flag_shock.c and Time_Stepping/rk_step.c.
INTERNAL_BOUNDARY_REFLECT and FAILSAFE default to NO. FLAG_MINMOD gives the
configured limiter already. The shock detector can select HLL at a subsonic
face. Its recorded flags and RK intermediate primitives are unavailable.
Methods named snapshot_flags evaluate that detector on the supplied state.
The linear_hllc and linear_hll sensitivities disable or force that switch.

Ideal-gas total energy here includes kinetic and internal energy and the
flux includes pressure work. The solver evolves no independent kinetic flux:
donor_kinetic uses the mass flux times half the squared upwind velocity.
Selective entropy affects the conversion to the pressure saved in a snapshot,
not the direct Riemann calculation from a supplied positive primitive state.
No pressure clipping or replacement is applied. Supplying a static potential
adds its face-centroid value times numerical mass flux. Gravity was a volume
force in the run; this additional flux is for comparison with stored potential
energy in the same gauge. All rates here are instantaneous.
"""

import numpy as np


FIELDS = ("rho", "prs", "vx1", "vx2", "vx3", "tr1")
RATES = ("mass", "tracer_mass", "gas_energy", "donor_kinetic")
METHODS = ("linear_snapshot_flags", "first_order_snapshot_flags", "linear_hllc", "linear_hll")
REGIONS = ("cap", "stationary", "net")
GAMMA = 5 / 3


def _shock_mask(state, widths):
    """Fresh CARTESIAN FlagShock criterion for setting this cell's FLAG_HLL."""
    pressure = state[..., 1]
    core = (slice(1, -1),) * 3
    pmin = pressure[core].copy()
    div = np.zeros_like(pmin)
    jump = np.zeros_like(pmin)
    for direction in range(3):
        dim = 2 - direction
        minus, plus = list(core), list(core)
        minus[dim], plus[dim] = slice(None, -2), slice(2, None)
        minus, plus = tuple(minus), tuple(plus)
        velocity = state[..., 2 + direction]
        shape = [1, 1, 1]
        shape[dim] = -1
        div += (velocity[plus] - velocity[minus]) / widths[direction][1:-1].reshape(shape)
        jump += np.abs(pressure[plus] - pressure[minus])
        pmin = np.minimum(pmin, np.minimum(pressure[plus], pressure[minus]))
    flagged = np.zeros(pressure.shape, dtype=bool)
    flagged[core] = (div < 0) & (jump > 5 * pmin)
    return flagged


def _slope(before, middle, after):
    """Primitive minmod increment on the configured Cartesian PLM branch."""
    back, forward = middle - before, after - middle
    same = ((back > 0) & (forward > 0)) | ((back < 0) & (forward < 0))
    return np.where(same, np.copysign(np.minimum(np.abs(back), np.abs(forward)), back), 0.0)


def _face_flux(inside, outside, hll, gamma=GAMMA):
    """Mass, tag and gas-energy flux for arrays in outward normal frames.

    Columns are density, pressure, outward normal velocity, two transverse
    velocities and the tracer fraction. The HLL fallback only changes faces
    whose two Davis speeds bracket zero.
    """
    rho_i, p_i, v_i = inside[:, :3].T
    rho_o, p_o, v_o = outside[:, :3].T
    c_i = np.sqrt(gamma * p_i / rho_i)
    c_o = np.sqrt(gamma * p_o / rho_o)
    left = np.minimum(v_i - c_i, v_o - c_o)
    right = np.maximum(v_i + c_i, v_o + c_o)
    fan = (left <= 0) & (right >= 0)
    use_hll = fan & hll
    use_contact = fan & ~hll
    ke_i = 0.5 * np.sum(inside[:, 2:5]**2, axis=1)
    ke_o = 0.5 * np.sum(outside[:, 2:5]**2, axis=1)
    energy_i, energy_o = rho_i * ke_i + p_i / (gamma - 1), rho_o * ke_o + p_o / (gamma - 1)
    flux_i = np.column_stack((rho_i * v_i, (energy_i + p_i) * v_i))
    flux_o = np.column_stack((rho_o * v_o, (energy_o + p_o) * v_o))
    chosen = np.where((left > 0)[:, None], flux_i, flux_o)

    if use_hll.any():
        take = use_hll
        sl, sr = left[take, None], right[take, None]
        delta = np.column_stack((rho_o[take] - rho_i[take], energy_o[take] - energy_i[take]))
        chosen[take] = (sr * flux_i[take] - sl * flux_o[take] + sl * sr * delta) / (sr - sl)

    if use_contact.any():
        take = use_contact
        wi = rho_i[take] * (left[take] - v_i[take])
        wo = rho_o[take] * (right[take] - v_o[take])
        contact = (p_o[take] - p_i[take] + wi*v_i[take] - wo*v_o[take]) / (wi - wo)
        from_inside = contact >= 0
        wave = np.where(from_inside, left[take], right[take])
        donor = np.where(from_inside[:, None], inside[take], outside[take])
        rho, pressure, normal = donor[:, :3].T
        energy = np.where(from_inside, energy_i[take], energy_o[take])
        face_flux = np.where(from_inside[:, None], flux_i[take], flux_o[take])
        rho_star = rho * (wave - normal) / (wave - contact)
        specific_star = energy / rho + (contact - normal) * (
            contact + pressure / (rho * (wave - normal))
        )
        delta = np.column_stack((rho_star - rho, rho_star * specific_star - energy))
        chosen[take] = face_flux + wave[:, None] * delta

    mass, gas_energy = chosen.T
    donor_i = mass > 0
    rates = {
        "mass": mass,
        "tracer_mass": mass * np.where(donor_i, inside[:, 5], outside[:, 5]),
        "gas_energy": gas_energy,
        "donor_kinetic": mass * np.where(donor_i, ke_i, ke_o),
    }
    outer_incoming = v_o - c_o < 0
    sets_return = outer_incoming & (v_o - c_o < v_i - c_i)
    waves = {
        "return_wave": left < 0,
        "outside_incoming": outer_incoming,
        "outside_sets_wave": sets_return,
        "hotter_outside_sets_wave": sets_return & (c_o > c_i),
    }
    return rates, waves, use_hll


def _frame(state, direction, sign):
    fields = [0, 1, 2 + direction, 2 + (direction + 1) % 3, 2 + (direction + 2) % 3, 5]
    local = state[:, fields]
    local[:, 2] *= sign
    return local


def _faces(state, widths, sphere, caps, shocks, *, nodes=None):
    """Assemble outward-facing reflected frames; keep physical face areas."""
    geometry = []
    for direction in range(3):
        dim = 2 - direction
        lo_slice, hi_slice = [slice(None)] * 3, [slice(None)] * 3
        lo_slice[dim], hi_slice[dim] = slice(None, -1), slice(1, None)
        lower = np.column_stack(np.where(sphere[tuple(lo_slice)] != sphere[tuple(hi_slice)]))
        shift = np.zeros(3, dtype=int)
        shift[dim] = 1
        upper = lower + shift
        lo, hi = tuple(lower.T), tuple(upper.T)
        low_is_inside = sphere[lo]
        orientation = np.where(low_is_inside, 1, -1)
        is_cap = np.where(low_is_inside, caps[lo], caps[hi])
        area = np.ones(len(lower))
        for tangent in range(3):
            if tangent != direction:
                area *= widths[tangent][lower[:, 2 - tangent]]
        low_value, high_value = state[lo], state[hi]
        low_plm = low_value + 0.5 * _slope(state[tuple((lower - shift).T)], low_value, high_value)
        high_plm = high_value - 0.5 * _slope(low_value, high_value, state[tuple((upper + shift).T)])
        face = {"area": area, "cap": is_cap, "shock": shocks[lo] | shocks[hi]}
        if nodes is not None:
            radius2 = nodes[direction][upper[:, dim]]**2
            for tangent in range(3):
                if tangent != direction:
                    index = lower[:, 2 - tangent]
                    mid = (nodes[tangent][index] + nodes[tangent][index + 1]) * 0.5
                    radius2 += mid**2
            face["radius"] = np.sqrt(radius2)
        for label, low, high in (("linear", low_plm, high_plm), ("first_order", low_value, high_value)):
            inside = np.where(low_is_inside[:, None], low, high)
            outside = np.where(low_is_inside[:, None], high, low)
            face[label + "_inner"] = _frame(inside, direction, orientation)
            face[label + "_outer"] = _frame(outside, direction, orientation)
        geometry.append(face)
    return {key: np.concatenate([item[key] for item in geometry]) for key in geometry[0]}


def _summarize(method, region, mask, face, rates, waves, used_hll):
    area = face["area"]
    record = {
        "method": method, "region": region, "n_faces": int(mask.sum()),
        "area": float(area[mask].sum()), "n_snapshot_flagged": int(np.sum(face["shock"] & mask)),
        "n_hll_fallback": int(np.sum(used_hll & mask)),
    }
    for field, rate in rates.items():
        weighted = rate[mask] * area[mask]
        record[field] = float(weighted.sum())
        record[field + "_out"] = float(weighted.clip(min=0).sum())
        record[field + "_in"] = float((-weighted).clip(min=0).sum())
    mass_out_faces = mask & (rates["mass"] > 0)
    record["gas_energy_on_mass_out_faces"] = float(np.sum(rates["gas_energy"][mass_out_faces] * area[mass_out_faces]))
    for label, criterion in waves.items():
        subset = mask & criterion
        subset_area = area[subset]
        record[label + "_n_faces"] = int(subset.sum())
        record[label + "_area"] = float(subset_area.sum())
        for field in ("mass", "tracer_mass", "gas_energy"):
            weighted = rates[field][subset] * subset_area
            record[label + "_" + field + "_out"] = float(weighted.clip(min=0).sum())
    return record


def _cell_checks(state, xyz, sphere, caps):
    indices = np.where(sphere)
    position = np.column_stack([axis[index] for axis, index in zip(xyz, indices[::-1], strict=True)])
    radius = np.linalg.norm(position, axis=1, keepdims=True)
    radial_unit = np.divide(position, radius, out=np.zeros_like(position), where=radius > 0)
    velocities = state[indices][:, 2:5]
    speed = np.linalg.norm(velocities, axis=1)
    radial = np.sum(velocities * radial_unit, axis=1)
    transverse = np.linalg.norm(velocities - radial[:, None] * radial_unit, axis=1)
    is_cap = caps[indices]
    tracer_error = np.abs(state[indices][:, 5] - is_cap)
    checks = {}
    for region, mask in zip(REGIONS, (is_cap, ~is_cap, np.ones_like(is_cap)), strict=True):
        checks[region] = {
            "n_cells": int(mask.sum()),
            "tracer_max_abs_error": float(tracer_error[mask].max()) if mask.any() else None,
            "speed_min": float(speed[mask].min()) if mask.any() else None,
            "speed_max": float(speed[mask].max()) if mask.any() else None,
            "radial_speed_min": float(radial[mask].min()) if mask.any() else None,
            "transverse_speed_max": float(transverse[mask].max()) if mask.any() else None,
        }
    return checks


def measure(patch, centres, edges, *, radius=0.75, half_angle_deg=15.0, potential=None):
    """Return rates by method and region for the active, centered bipolar source.

    Each primitive array has shape (len(z), len(y), len(x)). Coordinates are
    in code length units. At least two intact exterior cells per direction
    around the sphere enclose the limiter and shock stencils. The four
    production cases use radius 0.75, half angle 15 degrees and gamma 5/3.

    Rates without suffix are net signed. _out and _in are positive gross
    magnitudes. For each wave mask, its field_out divided by the region's
    field_out gives the share of gross outward transport on those faces.
    return_wave is S_left < 0, outside_incoming is u_out - c_out < 0,
    outside_sets_wave also requires that the outside supplies the strictly
    lower Davis bound, and hotter_outside_sets_wave adds c_out > c_in.
    These are characteristic speeds; wave energy is not separately evolved.
    With potential(r), in code velocity squared, potential_energy and
    gas_plus_potential add the mass transport of Phi at each face centroid.
    Cell checks compare the saved tag with 1 (cap) or 0 (stationary), and
    report velocity and its departure from radial motion in code units.
    """
    if not (0 < radius and 0 < half_angle_deg < 90):
        raise ValueError("expected a positive radius and bipolar conical half angle in (0,90)")
    if len(centres) != 3 or len(edges) != 3:
        raise ValueError("expected three Cartesian centre and edge vectors")
    xyz = [np.asarray(axis, dtype=float) for axis in centres]
    nodes = [np.asarray(axis, dtype=float) for axis in edges]
    widths = [np.diff(axis) for axis in nodes]
    for centres_1d, edges_1d, dx in zip(xyz, nodes, widths, strict=True):
        if (centres_1d.ndim != 1 or len(centres_1d) < 5 or edges_1d.shape != (len(centres_1d) + 1,)
                or not np.all(dx > 0) or not np.all((edges_1d[:-1] < centres_1d) & (centres_1d < edges_1d[1:]))
                or not (edges_1d[0] < -radius and edges_1d[-1] > radius)):
            raise ValueError("invalid axes or injector sphere cropped by patch")
    shape = tuple(len(axis) for axis in reversed(xyz))
    if any(np.shape(patch[field]) != shape for field in FIELDS):
        raise ValueError("primitive array shape disagrees with [z,y,x] patch coordinates")
    state = np.stack([np.asarray(patch[field], dtype=float) for field in FIELDS], axis=-1)
    if not np.all(np.isfinite(state)) or np.any(state[..., :2] <= 0):
        raise ValueError("nonfinite primitive or nonpositive density/pressure in supplied patch")
    x, y, z = xyz[0][None, None, :], xyz[1][None, :, None], xyz[2][:, None, None]
    radial2 = x*x + y*y
    sphere = radial2 + z*z <= radius*radius
    if not sphere.any():
        raise ValueError("injector contains no cell centres")
    for dim, indices in enumerate(np.where(sphere)):
        if np.min(indices) < 2 or np.max(indices) >= shape[dim] - 2:
            raise ValueError("at least two exterior cells required for face and shock stencils")
    caps = (z != 0) & (radial2 <= (np.abs(z) * np.tan(np.deg2rad(half_angle_deg)))**2)
    checks = _cell_checks(state, xyz, sphere, caps)
    faces = _faces(state, widths, sphere, caps, _shock_mask(state, widths),
                   nodes=nodes if potential is not None else None)
    if potential is not None:
        phi = np.broadcast_to(np.asarray(potential(faces["radius"]), dtype=float), faces["area"].shape)
        if not np.all(np.isfinite(phi)):
            raise ValueError("nonfinite potential at injector face")
    all_faces = np.ones_like(faces["cap"])
    rows = []
    for method in METHODS:
        order = "first_order" if method.startswith("first_order") else "linear"
        shock = faces["shock"]
        if method == "linear_hllc":
            shock = np.zeros_like(shock)
        elif method == "linear_hll":
            shock = all_faces
        rates, waves, used_hll = _face_flux(faces[order + "_inner"], faces[order + "_outer"], shock)
        if potential is not None:
            rates["potential_energy"] = phi * rates["mass"]
            rates["gas_plus_potential"] = rates["gas_energy"] + rates["potential_energy"]
        for region, mask in zip(REGIONS, (faces["cap"], ~faces["cap"], all_faces), strict=True):
            row = _summarize(method, region, mask, faces, rates, waves, used_hll)
            rows.append({**row, **checks[region]})
    return rows
