"""Independent centred flux check for the registered, fully enclosed C-LO/30 apertures.

The native file, radii, stretched-grid coordinates, units and potential convention are
shared with the production extraction. This reader scans whole planes, traces the two
ends of each occupied row and column, and evaluates the seven fluxes in cgs directly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from tempfile import NamedTemporaryFile

import h5py
import numpy as np

from pluto_h5_level3_ambient_extract import GAMMA_GAS, UNIT_DENSITY_CGS, UNIT_LENGTH_CM, UNIT_VELOCITY_CMS
from snapshot_energy import load_environment

FIELDS = ("rho", "prs", "vx1", "vx2", "vx3")
RATES = ("mass_flux_outward_g_s", "thermal_advective_flux_outward_erg_s", "pressure_work_outward_erg_s",
         "kinetic_flux_outward_erg_s", "gravitational_flux_outward_erg_s")
CASE = "C-LO"
INDEX = 30


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def face_rates(axis, pos, low, high, lower_centre, upper_centre, area, sign, potential):
    weight = (pos[axis] - lower_centre) / (upper_centre - lower_centre)
    q = low + weight * (high - low)
    if np.any(~np.isfinite(q)) or np.any(q[:2] <= 0):
        raise ValueError("nonfinite flux state or nonpositive density or pressure")
    rho, pressure = q[0] * UNIT_DENSITY_CGS, q[1] * (UNIT_DENSITY_CGS * UNIT_VELOCITY_CMS**2)
    speed = q[2:] * UNIT_VELOCITY_CMS
    volume_rate = sign * speed[axis] * (area * UNIT_LENGTH_CM**2)
    mass = rho * volume_rate
    work = pressure * volume_rate
    kinetic = 0.5 * mass * np.sum(speed**2, axis=0)
    phi = potential(UNIT_LENGTH_CM * np.sqrt(pos[0]**2 + pos[1]**2 + pos[2]**2))
    components = np.stack((mass, work/(GAMMA_GAS - 1), work, kinetic, mass * phi))
    return np.sum(components, axis=1, dtype=np.longdouble), np.sum(np.abs(components), axis=1, dtype=np.longdouble)


class Surface:
    def __init__(self):
        self.count = 0
        self.volume = np.longdouble(0)
        self.faces = 0
        self.area = np.longdouble(0)
        self.net = np.zeros(len(RATES), dtype=np.longdouble)
        self.absolute = np.zeros(len(RATES), dtype=np.longdouble)

    def add(self, axis, pos, low, high, lower_centre, upper_centre, area, sign, potential):
        net, absolute = face_rates(axis, pos, low, high, lower_centre, upper_centre, area, sign, potential)
        self.faces += len(area)
        self.area += area.sum(dtype=np.longdouble)
        self.net += net
        self.absolute += absolute

    def result(self, radius):
        if self.count == 0:
            raise ValueError("empty registered aperture")
        flux = dict(zip(RATES, map(float, self.net), strict=True))
        flux["gas_flux_outward_erg_s"] = float(sum(self.net[1:4]))
        flux["total_energy_flux_outward_erg_s"] = float(sum(self.net[1:]))
        return {"radius_kpc": radius, "cell_count": self.count, "volume_kpc3": float(self.volume),
                "face_count": self.faces, "area_kpc2": float(self.area), "centred_flux": flux,
                "sum_absolute_face_contributions": dict(zip(RATES, map(float, self.absolute), strict=True))}


def cropped(centres, radius):
    start = np.searchsorted(centres, -radius, side="left") - 1
    stop = np.searchsorted(centres, radius, side="right") + 1
    if start < 0 or stop > len(centres):
        raise ValueError("this check requires an exterior neighbour in every direction")
    return slice(start, stop)


def scan(fields, centres, edges, radii, potential):
    x_full, y_full, z_full = (np.asarray(a, dtype=float) for a in centres)
    shape = tuple(len(a) for a in (z_full, y_full, x_full))
    if any(fields[k].shape != shape for k in FIELDS):
        raise ValueError("native shapes and coordinates differ")
    largest = max(radii.values())
    if not all(math.isfinite(r) and r > 0 for r in radii.values()):
        raise ValueError("aperture radii must be positive and finite")
    for c, e in zip((x_full, y_full, z_full), edges, strict=True):
        if (len(e) != len(c) + 1 or np.any(np.diff(c) <= 0) or np.any(np.diff(e) <= 0)
                or not np.all((e[:-1] < c) & (c < e[1:])) or min(-e[0], e[-1]) <= largest):
            raise ValueError("requires increasing coordinates and an untruncated sphere")
    xs, ys, zs = [cropped(c, largest) for c in (x_full, y_full, z_full)]
    x, y = x_full[xs], y_full[ys]
    xe, ye, ze = edges
    dx, dy, dz = np.diff(xe)[xs], np.diff(ye)[ys], np.diff(ze)
    xy_area = dy[:, None] * dx[None, :]
    xy_squared = y[:, None]**2 + x[None, :]**2
    limits = {name: np.nextafter(radius, np.inf) for name, radius in radii.items()}
    surfaces = {name: Surface() for name in radii}
    previous_masks = {name: np.zeros(xy_squared.shape, dtype=bool) for name in radii}
    prev = None

    for iz in range(zs.start, zs.stop):
        now = np.stack([np.asarray(fields[k][iz])[ys, xs] for k in FIELDS])
        z = z_full[iz]
        radius = np.sqrt(xy_squared + z**2)
        for name, limit in limits.items():
            mask = radius <= limit
            surface = surfaces[name]
            surface.count += np.count_nonzero(mask)
            surface.volume += dz[iz] * np.sum(xy_area, where=mask, dtype=np.longdouble)
            for axis in (0, 1):
                rows = mask if axis == 0 else mask.T
                occupied = np.flatnonzero(rows.any(axis=1))
                if not occupied.size:
                    continue
                first = np.argmax(rows[occupied], axis=1)
                last = rows.shape[1] - 1 - np.argmax(rows[occupied, ::-1], axis=1)
                indices = np.concatenate((first - 1, last))
                sign = np.repeat((-1.0, 1.0), occupied.size)
                other = np.tile(occupied, 2)
                if axis == 0:
                    low, high = now[:, other, indices], now[:, other, indices + 1]
                    face = xe[xs.start + indices + 1]
                    pos = (face, y[other], z)
                    c0, c1, area = x[indices], x[indices + 1], dy[other] * dz[iz]
                else:
                    low, high = now[:, indices, other], now[:, indices + 1, other]
                    face = ye[ys.start + indices + 1]
                    pos = (x[other], face, z)
                    c0, c1, area = y[indices], y[indices + 1], dx[other] * dz[iz]
                surface.add(axis, pos, low.astype(float), high.astype(float), c0, c1, area, sign, potential)

            old = previous_masks[name]
            iy, ix = np.nonzero(old ^ mask)
            if iy.size:
                if prev is None:
                    raise ValueError("missing exterior plane")
                sign = np.where(old[iy, ix], 1.0, -1.0)
                pos = (x[ix], y[iy], ze[iz])
                surface.add(2, pos, prev[:, iy, ix].astype(float), now[:, iy, ix].astype(float),
                            z_full[iz - 1], z, xy_area[iy, ix], sign, potential)
            previous_masks[name] = mask
        prev = now
    if any(mask.any() for mask in previous_masks.values()):
        raise ValueError("missing upper exterior plane")
    return {name: surface.result(radii[name]) for name, surface in surfaces.items()}


def axis_from_native(group, label, axis):
    values = group[label]
    if values.ndim == 1:
        return np.asarray(values[:], dtype=float)
    section = [0, 0, 0]
    section[2 - axis] = slice(None)
    return np.asarray(values[tuple(section)], dtype=float)


def run(stage):
    registration_path = stage / "registration.json"
    frozen = json.loads(registration_path.read_bytes())["cases"][CASE]
    directory = stage / "requests" / CASE
    request_path = directory / "request.json"
    if sha(request_path) != frozen["input_request_sha256"]:
        raise ValueError("registered native request hash differs")
    record = json.loads(request_path.read_bytes())["history"][INDEX]
    expected = frozen["snapshots"][INDEX]
    native = Path(record["native"]["resolved_path"])
    if (record["index"] != INDEX or expected["index"] != INDEX or record["fixed_receipt_sha256"] != expected["fixed_sha256"]
            or record["native"]["sha256"] != expected["native_sha256"] or sha(native) != expected["native_sha256"]):
        raise ValueError("native file, index, or stock receipt differs from registration")
    before = native.stat()
    axes_path, env_path = directory / "axes.npz", directory / "atmosphere.csv"
    for path in (axes_path, env_path):
        if sha(path) != frozen["static_sha256"][path.name]:
            raise ValueError(f"changed {path.name}")
    roles = expected["apertures"]
    if set(roles) != {"R100", "R300"} or any(not r["geometrically_complete_in_domain_box"] for r in roles.values()):
        raise ValueError("check requires both complete current apertures")
    radii = {name: r["raw_radius_kpc"] for name, r in roles.items()}
    with h5py.File(native, "r") as src, np.load(axes_path, allow_pickle=False) as axes:
        step = src[record["timestep"]]
        if float(step.attrs["Time"]) != record["time_code"]:
            raise ValueError("snapshot time differs")
        centres = [axis_from_native(src["cell_coords"], a, i) for i, a in enumerate("XYZ")]
        edges = [axis_from_native(src["node_coords"], a, i) for i, a in enumerate("XYZ")]
        for i, key in enumerate("xyz"):
            if not np.array_equal(axes[key], centres[i]) or not np.array_equal(axes[f"{key}_edges"], edges[i]):
                raise ValueError(f"native axis {key} differs")
        values = scan(step["vars"], centres, edges, radii, load_environment(env_path).potential_at_radius)
    after = native.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError("native source changed during extraction")
    for name, r in values.items():
        if r["cell_count"] != roles[name]["cell_count"] or not math.isclose(r["volume_kpc3"], roles[name]["volume_kpc3"], rel_tol=5e-11):
            raise ValueError(f"{name}: independent cell count or volume disagrees with registered stock")
    return {"case": CASE, "index": INDEX, "age_myr": expected["age_myr"], "native_sha256": expected["native_sha256"],
            "request_sha256": frozen["input_request_sha256"], "axes_sha256": frozen["static_sha256"]["axes.npz"],
            "atmosphere_sha256": frozen["static_sha256"]["atmosphere.csv"], "registration_sha256": sha(registration_path),
            "script_sha256": sha(Path(__file__)), "apertures": values}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.dumps(run(args.stage), indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=args.output.parent, mode="w", delete=False) as tmp:
        tmp.write(payload)
    Path(tmp.name).replace(args.output)
