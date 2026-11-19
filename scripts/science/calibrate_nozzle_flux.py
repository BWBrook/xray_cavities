"""Calibrate the retained nozzle-control estimator against a steady conical flow."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np

import measure_q031_fluxes as flux
from snapshot_energy import EnvironmentProfile, sha256_file

CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
PADDINGS = (1, 2, 4)
# The solver constants generate the input states. The unchanged estimator has its own cgs conversions.
SOLVER_LENGTH = 3.0856775807e21
SOLVER_DENSITY = 1.66053886e-24 * 0.60364
SOLVER_SPEED = 2.99792458e10
SOLVER_PRESSURE = SOLVER_DENSITY * SOLVER_SPEED**2
COMPONENTS = ("kinetic", "enthalpy", "potential", "total_energy")


@dataclass(frozen=True)
class Jet:
    power: float
    speed: float
    angle: float
    source_radius: float
    length_scale: float
    jet_density: float
    jet_pressure: float
    environment: EnvironmentProfile

    @classmethod
    def from_case(cls, ini, environment):
        params = flux.parse_pluto_parameters(ini)
        text = ini.read_text()
        for name in ("JET_OA_PRIMARY", "JET_OA_SECONDARY", "JET_CHI", "ENV_X1O", "ENV_X2O", "ENV_X3O"):
            (number,) = re.findall(rf"^{name}\s+([^\s#;]+)", text, flags=re.MULTILINE)
            params[name] = float(number)
        if any(params[key] != 0.0 for key in (
            "JET_X1O", "JET_X2O", "JET_X3O", "JET_ROTATION_ANGLE", "ENV_X1O", "ENV_X2O", "ENV_X3O"
        )):
            raise ValueError("calibration requires a centred, unrotated source and atmosphere")
        if not 0 < params["JET_OA_PRIMARY"] == params["JET_OA_SECONDARY"] < 90:
            raise ValueError("expected equal bipolar opening angles")
        angle = math.radians(params["JET_OA_PRIMARY"])
        omega = 2 * math.pi * (1 - math.cos(angle))
        inlet = 0.001 * SOLVER_LENGTH
        rho_in = np.interp(inlet, environment.radius_cm, environment.density_g_cm3)
        pressure_in = np.interp(inlet, environment.radius_cm, environment.pressure_dyn_cm2)
        speed_cgs = params["JET_SPD"] * SOLVER_SPEED
        length_cm = math.sqrt(2 * params["JET_PWR"] / (rho_in * speed_cgs**3 * omega))
        rho_jet = np.interp(length_cm, environment.radius_cm, environment.density_g_cm3)
        return cls(params["JET_PWR"], params["JET_SPD"], angle, params["JET_INJECTION_HEIGHT"],
                   length_cm / SOLVER_LENGTH, rho_jet / SOLVER_DENSITY,
                   params["JET_CHI"] * pressure_in / SOLVER_PRESSURE, environment)

    def state(self, x, y, z):
        r = np.sqrt(x*x + y*y + z*z)
        if np.any(r == 0):
            raise ValueError("sample the measuring faces away from the cone apex")
        cone = np.hypot(x, y) <= np.abs(z) * math.tan(self.angle)
        jet_thermodynamics = cone | (r <= self.source_radius)
        density_factor = (self.length_scale / r)**2
        env = self.environment
        ambient_rho = np.interp(r * SOLVER_LENGTH, env.radius_cm, env.density_g_cm3) / SOLVER_DENSITY
        ambient_prs = np.interp(r * SOLVER_LENGTH, env.radius_cm, env.pressure_dyn_cm2) / SOLVER_PRESSURE
        speed_per_radius = np.where(cone, self.speed / r, 0.0)
        return {
            "rho": np.where(jet_thermodynamics, self.jet_density * density_factor, ambient_rho),
            "prs": np.where(jet_thermodynamics, self.jet_pressure * density_factor**flux.GAMMA_GAS, ambient_prs),
            "vx1": x * speed_per_radius, "vx2": y * speed_per_radius, "vx3": z * speed_per_radius,
        }


def continuum(jet, face_heights):
    """Integrate over the solid angle at the two z caps in the estimator's cgs units."""
    mu0 = math.cos(jet.angle)
    nodes, weights = np.polynomial.legendre.leggauss(48)
    mu = (1 + mu0 + (1 - mu0) * nodes) / 2
    solid_angle_weights = math.pi * (1 - mu0) * weights
    mass_per_angle = jet.jet_density * jet.length_scale**2 * jet.speed
    mass_unit = flux.UNIT_DENSITY_CGS * flux.UNIT_LENGTH_CM**2 * flux.UNIT_VELOCITY_CMS
    energy_unit = mass_unit * flux.UNIT_VELOCITY_CMS**2
    mass = 2 * 2 * math.pi * (1 - mu0) * mass_per_angle * mass_unit
    kinetic = 0.5 * mass * (jet.speed * flux.UNIT_VELOCITY_CMS)**2
    enthalpy = potential = 0.0
    gamma = flux.GAMMA_GAS
    for height in face_heights:
        radius = height / mu
        pressure = jet.jet_pressure * (jet.length_scale / radius)**(2 * gamma)
        enthalpy += energy_unit * np.dot(solid_angle_weights, gamma / (gamma - 1) * pressure * radius**2 * jet.speed)
        phi = jet.environment.potential_at_radius(radius * flux.UNIT_LENGTH_CM)
        potential += mass_unit * mass_per_angle * np.dot(solid_angle_weights, phi)
    return {"mass_flux_outward_g_s": mass, "kinetic_flux_outward_erg_s": kinetic,
            "enthalpy_flux_outward_erg_s": enthalpy, "potential_flux_outward_erg_s": potential,
            "total_energy_flux_outward_erg_s": kinetic + enthalpy + potential}


def make_grid(centres, edges):
    return flux.Grid(*centres, *(np.diff(axis) for axis in edges), *edges)


def read_grid(folder, shape):
    with np.load(folder/"axes.npz", allow_pickle=False) as data:
        centres = [data[axis].astype(float) for axis in "xyz"]
        edges = [data[axis+"_edges"].astype(float) for axis in "xyz"]
    ascii_edges = flux.parse_grid_file(folder/"grid.out", tuple(shape))
    for axis, nodes, expected in zip(centres, edges, ascii_edges, strict=True):
        if (nodes.shape != expected.shape or len(axis) + 1 != len(nodes)
                or not np.allclose(nodes, expected, rtol=0, atol=5e-5)
                or not np.all((nodes[:-1] < axis) & (axis < nodes[1:]))):
            raise ValueError("archived native axes and production geometry disagree")
    return make_grid(centres, edges)


def face_patch(full_grid, box, subdivision):
    """Keep the box and one neighbouring cell on each face; preserve the original physical surfaces."""
    centres, edges = [], []
    for axis, lo, hi in zip("xyz", (box.i0, box.j0, box.k0), (box.i1, box.j1, box.k1), strict=True):
        nodes = getattr(full_grid, axis+"_edges")[lo-1:hi+3]
        if subdivision == 1:
            centre = getattr(full_grid, axis)[lo-1:hi+2]
        else:
            inner = np.linspace(nodes[1:-2], nodes[2:-1], subdivision, endpoint=False, axis=1).ravel()
            nodes = np.r_[nodes[1] - (nodes[1]-nodes[0])/subdivision, inner,
                          nodes[-2], nodes[-2] + (nodes[-1]-nodes[-2])/subdivision]
            centre = (nodes[:-1] + nodes[1:]) / 2
        centres.append(centre)
        edges.append(nodes)
    grid = make_grid(centres, edges)
    # Subdivide the original source footprint and padding along with the control volume.
    def local(index, orig_lo):
        return 1 + (index - orig_lo) * subdivision
    bounds = []
    for first, last, lo in ((box.source_i0, box.source_i1, box.i0),
                            (box.source_j0, box.source_j1, box.j0), (box.source_k0, box.source_k1, box.k0)):
        bounds.extend((local(first, lo), local(last+1, lo)-1))
    patch_box = flux.ControlBox(1, len(grid.x)-2, 1, len(grid.y)-2, 1, len(grid.z)-2,
                                *bounds, box.source_cell_count * subdivision**3, box.padding_cells * subdivision)
    return grid, patch_box


def sample_surfaces(jet, grid, box):
    shape = (grid.z.size, grid.y.size, grid.x.size)
    rows = []
    # Only the inner/outer stencil layers are needed. Unfilled HDF5 cells are NaN.
    with h5py.File("synthetic.h5", "w", driver="core", backing_store=False) as h5:
        variables = h5.create_group("vars")
        for field in flux.PRIMITIVE_FIELDS:
            variables.create_dataset(field, shape=shape, dtype="<f4", chunks=(4, 4, 4), fillvalue=np.nan)
        for normal_dim in range(3):
            for edge in (slice(0, 2), slice(-2, None)):
                where = [slice(1, -1)] * 3
                where[normal_dim] = edge
                z = grid.z[where[0]][:, None, None]
                y = grid.y[where[1]][None, :, None]
                x = grid.x[where[2]][None, None, :]
                for field, values in jet.state(x, y, z).items():
                    variables[field][tuple(where)] = values
        for method in flux.CONTROL_RECONSTRUCTIONS:
            for row in flux.measure_control_surface(variables, grid, jet.environment, box, method):
                rows.append({"method": method, **row})
    return rows


def midpoint_caps(jet, grid):
    """Sample the analytic state at face centres to isolate Cartesian area sampling."""
    x, y = grid.x[None, 1:-1], grid.y[1:-1, None]
    area = grid.dy[1:-1, None] * grid.dx[None, 1:-1]
    rows = []
    for z, sign in ((grid.z_edges[1], -1), (grid.z_edges[-2], 1)):
        radius = np.sqrt(x*x + y*y + z*z)
        phi = jet.environment.potential_at_radius(radius * flux.UNIT_LENGTH_CM)
        rows.append(flux.flux_components(jet.state(x, y, z), normal_component="vx3",
                    normal_sign=sign, area_kpc2=area, potential_cm2_s2=phi))
    return {field: sum(row[field] for row in rows) for field in flux.FLUX_FIELDS}


def load_case(root, case):
    folder = root / case
    bound = json.loads((root / "bindings.json").read_bytes())[case]
    native_types = json.loads((root / "native_types.json").read_bytes())["snapshots"][case]
    native_axes = json.loads((root / "axes_manifest.json").read_bytes())["cases"][case]
    nozzle_log = json.loads((root / "jet_logged_properties.json").read_bytes())[case]
    for record in bound["static"].values():
        if sha256_file(folder/record["name"]) != record["sha256"]:
            raise ValueError(f"{case} static input hash differs: {record['name']}")
    for name, expected in bound["source_helpers"].items():
        if sha256_file(folder/"src"/name) != expected:
            raise ValueError(f"{case} source hash differs: {name}")
    if sha256_file(Path(flux.__file__)) != bound["flux_reader"]["sha256"]:
        raise ValueError("flux reader differs from production")
    if any(native_types["primitive_dtypes"][f] != "<f4" for f in flux.PRIMITIVE_FIELDS):
        raise ValueError("unexpected primitive storage precision")
    flux.parse_source_definitions(folder/"src/definitions_usr.h")
    flux.parse_core_definitions(folder/"src/definitions.h")
    env = flux.load_environment(folder/bound["static"]["environment"]["name"])
    jet = Jet.from_case(folder/"pluto.ini", env)
    for name, value in (("L1b", jet.length_scale), ("density", jet.jet_density),
                        ("pressure", jet.jet_pressure), ("injection_cone_offset", 0.0)):
        pair = nozzle_log[name][-2:]
        if len(pair) != 2 or any(not math.isclose(float(raw), value, rel_tol=1e-6) for raw, _ in pair):
            raise ValueError(f"{case} manufactured {name} disagrees with startup log")
    if (sha256_file(folder/"axes.npz") != native_axes["raw_sha256"]
            or bound["analysis_signature"] != native_axes["source_checkpoint_signature"]):
        raise ValueError(f"{case} coordinate capture differs from original binding")
    grid = read_grid(folder, bound["baseline_snapshot"]["shape"])
    boxes = {}
    for pad in PADDINGS:
        box = flux.derive_control_box(grid, injection_height_kpc=jet.source_radius,
                                      centre_kpc=(0., 0., 0.), padding_cells=pad)
        if vars(box) != native_axes["verified_control_boxes"][str(pad)]:
            raise ValueError(f"{case} control box {pad} differs from original binding")
        boxes[pad] = box
    return jet, grid, boxes, {"axes_sha256": native_axes["raw_sha256"], "production_flux_signature": bound["analysis_signature"],
                              "l1b_kpc": jet.length_scale, "boxes": {pad: vars(box) for pad, box in boxes.items()}}


def run(root, out):
    if out.exists():
        raise FileExistsError(out)
    results, faces, midpoint, receipts = [], [], [], {}
    for case in CASES:
        jet, grid, boxes, receipts[case] = load_case(root, case)
        for pad, box in boxes.items():
            heights = [-grid.z_edges[box.k0], grid.z_edges[box.k1+1]]
            clearance = min(-grid.x_edges[box.i0], grid.x_edges[box.i1+1],
                            -grid.y_edges[box.j0], grid.y_edges[box.j1+1])
            if min(heights) <= 0 or max(heights)*math.tan(jet.angle) >= clearance:
                raise ValueError("cone intersects a side of the box")
            truth = continuum(jet, heights)
            for subdivision in (1, 4, 8):
                patch, local_box = face_patch(grid, box, subdivision)
                label = 2 * jet.power
                key = dict(case=case, padding_cells=pad, subdivision=subdivision)
                direct = midpoint_caps(jet, patch)
                midpoint.append({**key, "total_over_label": direct["total_energy_flux_outward_erg_s"]/label,
                                 "kinetic_over_label": direct["kinetic_flux_outward_erg_s"]/label})
                for row in sample_surfaces(jet, patch, local_box):
                    if subdivision == 1:
                        faces.append({**key, **row})
                    if row["face"] != "closed_surface_total":
                        continue
                    result = {**key, "method": row["method"], "bipolar_label_erg_s": label,
                              "mass_over_reference": row["mass_flux_outward_g_s"]/truth["mass_flux_outward_g_s"]}
                    for component in COMPONENTS:
                        field = component+"_flux_outward_erg_s"
                        result[component+"_over_label"] = row[field]/label
                        result[component+"_reference_over_label"] = truth[field]/label
                    result["bias_over_label"] = result["total_energy_over_label"]-result["total_energy_reference_over_label"]
                    results.append(result)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp)/"results"
        stage.mkdir()
        for name, rows in (("calibration", results), ("native_faces", faces), ("face_midpoints", midpoint)):
            with (stage/(name+".csv")).open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
        receipt = {"cases": receipts, "bindings_sha256": sha256_file(root/"bindings.json"),
                   "native_types_sha256": sha256_file(root/"native_types.json"), "calibrator_sha256": sha256_file(Path(__file__)),
                   "flux_reader_sha256": sha256_file(Path(flux.__file__)), "products_sha256": {
                       f.name: sha256_file(f) for f in sorted(stage.glob("*.csv"))}}
        (stage/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
        stage.rename(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.inputs, args.output)
