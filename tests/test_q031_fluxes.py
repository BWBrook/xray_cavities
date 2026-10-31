from __future__ import annotations

import csv
import hashlib
import importlib.util
import math
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCIENCE = ROOT / "scripts" / "science"
if str(SCIENCE) not in sys.path:
    sys.path.insert(0, str(SCIENCE))
SPEC = importlib.util.spec_from_file_location("measure_q031_fluxes", SCIENCE / "measure_q031_fluxes.py")
assert SPEC and SPEC.loader
flux = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = flux
SPEC.loader.exec_module(flux)


class ZeroPotential:
    def potential_at_radius(self, radius: np.ndarray) -> np.ndarray:
        return np.zeros_like(radius, dtype=float)


class QuadraticPotential:
    def potential_at_radius(self, radius: np.ndarray) -> np.ndarray:
        radius_kpc = np.asarray(radius, dtype=float) / flux.UNIT_LENGTH_CM
        return 0.01 * radius_kpc**2 * flux.UNIT_VELOCITY_CMS**2


def grid(n: int = 7) -> flux.Grid:
    centres = np.arange(n, dtype=float) - n // 2
    widths = np.ones(n)
    edges = np.arange(n + 1, dtype=float) - n // 2 - 0.5
    return flux.Grid(centres, centres.copy(), centres.copy(), widths, widths.copy(), widths.copy(), edges, edges.copy(), edges.copy())


def write_h5(path: Path, *, timestep: str, time_code: float, rho: float, velocity=(0.0, 0.0, 0.0)) -> None:
    shape = (7, 7, 7)
    coords = np.arange(7, dtype=float) - 3.0
    with h5py.File(path, "w") as h5:
        coordinate_group = h5.create_group("cell_coords")
        coordinate_group.create_dataset("X", data=np.broadcast_to(coords[None, None, :], shape))
        coordinate_group.create_dataset("Y", data=np.broadcast_to(coords[None, :, None], shape))
        coordinate_group.create_dataset("Z", data=np.broadcast_to(coords[:, None, None], shape))
        node_group = h5.create_group("node_coords")
        nodes = np.arange(8, dtype=float) - 3.5
        node_shape = (8, 8, 8)
        node_group.create_dataset("X", data=np.broadcast_to(nodes[None, None, :], node_shape))
        node_group.create_dataset("Y", data=np.broadcast_to(nodes[None, :, None], node_shape))
        node_group.create_dataset("Z", data=np.broadcast_to(nodes[:, None, None], node_shape))
        group = h5.create_group(timestep)
        group.attrs["Time"] = time_code
        variables = group.create_group("vars")
        variables.create_dataset("rho", data=np.full(shape, rho))
        variables.create_dataset("prs", data=np.full(shape, 2.0))
        variables.create_dataset("tr1", data=np.zeros(shape))
        for name, value in zip(("vx1", "vx2", "vx3"), velocity, strict=True):
            variables.create_dataset(name, data=np.full(shape, value))


def test_uniform_flow_has_zero_net_flux_on_both_closed_surfaces(tmp_path: Path) -> None:
    path = tmp_path / "uniform.h5"
    write_h5(path, timestep="Timestep_0", time_code=0.0, rho=2.0, velocity=(0.7, -0.4, 0.2))
    mesh = grid()
    box = flux.derive_control_box(mesh, injection_height_kpc=0.1, centre_kpc=(0.0, 0.0, 0.0))
    with h5py.File(path, "r") as h5:
        variables = h5["/Timestep_0/vars"]
        for method in flux.OUTER_RECONSTRUCTIONS:
            total = flux.measure_domain_surface(variables, mesh, ZeroPotential(), method)[-1]
            assert total["mass_flux_outward_g_s"] == pytest.approx(0.0, abs=1.0e18)
            assert total["total_energy_flux_outward_erg_s"] == pytest.approx(0.0, abs=1.0e38)
        for method in flux.CONTROL_RECONSTRUCTIONS:
            total = flux.measure_control_surface(variables, mesh, ZeroPotential(), box, method)[-1]
            assert total["mass_flux_outward_g_s"] == pytest.approx(0.0, abs=1.0e18)
            assert total["total_energy_flux_outward_erg_s"] == pytest.approx(0.0, abs=1.0e38)


def test_cached_domain_planes_exactly_match_contiguous_hdf5_on_nonuniform_grid(tmp_path: Path) -> None:
    z_edges = np.array([-4.0, -2.1, -0.7, 0.2, 1.8, 4.5])
    y_edges = np.array([-3.0, -1.6, -0.5, 0.1, 0.9, 2.0, 3.8])
    x_edges = np.array([-5.0, -2.8, -1.2, -0.3, 0.4, 1.5, 3.1, 5.6])
    mesh = flux.Grid(
        0.5 * (x_edges[:-1] + x_edges[1:]),
        0.5 * (y_edges[:-1] + y_edges[1:]),
        0.5 * (z_edges[:-1] + z_edges[1:]),
        np.diff(x_edges), np.diff(y_edges), np.diff(z_edges),
        x_edges, y_edges, z_edges,
    )
    shape = (mesh.z.size, mesh.y.size, mesh.x.size)
    kk, jj, ii = np.indices(shape, dtype=float)
    values = {
        "rho": 1.0 + 0.03 * kk + 0.02 * jj + 0.01 * ii,
        "prs": 2.0 + 0.04 * kk + 0.03 * jj + 0.02 * ii,
        "vx1": -0.4 + 0.02 * kk - 0.01 * jj + 0.03 * ii,
        "vx2": 0.2 - 0.01 * kk + 0.04 * jj - 0.02 * ii,
        "vx3": -0.1 + 0.03 * kk + 0.01 * jj + 0.02 * ii,
    }
    path = tmp_path / "contiguous.h5"
    with h5py.File(path, "w") as h5:
        variables = h5.create_group("vars")
        for name, data in values.items():
            dataset = variables.create_dataset(name, data=data)
            assert dataset.chunks is None
        direct = {
            method: flux.measure_domain_surface(variables, mesh, QuadraticPotential(), method)
            for method in flux.OUTER_RECONSTRUCTIONS
        }
        cache = flux.DomainPlaneCache.create(shape)
        flux.measure_storage(
            variables, mesh, QuadraticPotential(), {}, (), domain_plane_cache=cache,
        )
    cached = {
        method: flux.measure_domain_surface(
            variables, mesh, QuadraticPotential(), method, plane_cache=cache,
        )
        for method in flux.OUTER_RECONSTRUCTIONS
    }
    assert cached == direct


def test_domain_plane_cache_fails_closed_when_storage_pass_is_incomplete() -> None:
    shape = (5, 6, 7)
    cache = flux.DomainPlaneCache.create(shape)
    state = {
        "rho": np.ones(shape[1:]),
        "prs": np.ones(shape[1:]),
        "vx1": np.zeros(shape[1:]),
        "vx2": np.zeros(shape[1:]),
        "vx3": np.zeros(shape[1:]),
    }
    cache.capture_z_slab(0, state)
    with pytest.raises(ValueError, match="incomplete domain plane cache"):
        cache.primitive_state((slice(None), slice(None), 0))


def test_flux_sign_and_components_are_analytic() -> None:
    state = {
        "rho": np.array([[2.0]]),
        "prs": np.array([[3.0]]),
        "vx1": np.array([[4.0]]),
        "vx2": np.array([[0.0]]),
        "vx3": np.array([[0.0]]),
    }
    result = flux.flux_components(
        state,
        normal_component="vx1",
        normal_sign=-1.0,
        area_kpc2=np.array([[5.0]]),
        potential_cm2_s2=np.array([[2.0 * flux.UNIT_VELOCITY_CMS**2]]),
    )
    mass_factor = flux.UNIT_DENSITY_CGS * flux.UNIT_VELOCITY_CMS * flux.UNIT_LENGTH_CM**2
    energy_factor = flux.UNIT_DENSITY_CGS * flux.UNIT_VELOCITY_CMS**3 * flux.UNIT_LENGTH_CM**2
    mass_code = 2.0 * -4.0 * 5.0
    assert result["mass_flux_outward_g_s"] == pytest.approx(mass_code * mass_factor)
    assert result["mass_outflow_g_s"] == 0.0
    assert result["mass_inflow_g_s"] < 0.0
    specific = 2.5 * 3.0 / 2.0 + 0.5 * 4.0**2 + 2.0
    assert result["total_energy_flux_outward_erg_s"] == pytest.approx(mass_code * specific * energy_factor)
    assert result["energy_outflow_erg_s"] == 0.0


def test_source_derived_control_box_encloses_nozzle_and_padding() -> None:
    mesh = grid()
    box = flux.derive_control_box(mesh, injection_height_kpc=1.01, centre_kpc=(0.0, 0.0, 0.0), padding_cells=1)
    assert box.source_cell_count == 7
    assert (box.source_i0, box.source_i1, box.i0, box.i1) == (2, 4, 1, 5)
    with pytest.raises(ValueError, match="exterior neighbour"):
        flux.derive_control_box(mesh, injection_height_kpc=2.1, centre_kpc=(0.0, 0.0, 0.0), padding_cells=1)


def test_source_box_search_scales_with_nozzle_not_full_3d_domain() -> None:
    n = 1001
    centres = np.linspace(-500.0, 500.0, n)
    edges = np.linspace(-500.5, 500.5, n + 1)
    mesh = flux.Grid(
        centres, centres.copy(), centres.copy(), np.diff(edges), np.diff(edges), np.diff(edges),
        edges, edges.copy(), edges.copy(),
    )
    box = flux.derive_control_box(mesh, injection_height_kpc=0.1, centre_kpc=(0.0, 0.0, 0.0))
    assert box.source_cell_count == 1
    assert box.i1 - box.i0 + 1 == 3


def test_padding_sensitivity_boxes_share_exact_source_support() -> None:
    mesh = grid(15)
    boxes = {
        padding: flux.derive_control_box(
            mesh, injection_height_kpc=0.1, centre_kpc=(0.0, 0.0, 0.0), padding_cells=padding,
        )
        for padding in (1, 2, 4)
    }
    assert {box.source_cell_count for box in boxes.values()} == {1}
    assert [boxes[padding].i1 - boxes[padding].i0 + 1 for padding in (1, 2, 4)] == [3, 5, 9]


def test_nonuniform_face_interpolation_uses_exact_distances() -> None:
    active = {name: np.array([2.0]) for name in ("rho", "prs", "vx1", "vx2", "vx3")}
    inner = {name: np.array([6.0]) for name in active}
    # Active centre is 0.25 from the boundary and 1.0 from the next centre.
    extrapolated = flux._linear_outer_state(active, inner, face_fraction=0.25)
    assert extrapolated["rho"] == pytest.approx([1.0])
    inside = {name: np.array([2.0]) for name in active}
    outside = {name: np.array([8.0]) for name in active}
    centred = flux._internal_face_state(
        inside, outside, normal_component="vx1", normal_sign=1.0,
        method="centered_primitives", inside_distance=0.25, outside_distance=0.75,
    )
    assert centred["rho"] == pytest.approx([3.5])


def test_temporal_quadrature_exposes_cadence_sensitivity() -> None:
    flux_rows = []
    storage_rows = []
    for time, outward, mass, energy in ((0.0, 0.0, 10.0, 100.0), (1.0, 2.0, 13.0, 107.0)):
        flux_rows.append({
            "surface": "nozzle_control_p1", "reconstruction": "centered_primitives",
            "face": "closed_surface_total", "actual_time_myr": time,
            "mass_flux_outward_g_s": outward,
            "total_energy_flux_outward_erg_s": 10.0 * outward,
        })
        storage_rows.append({
            "volume_geometry": "exact_fv_nodes", "region": "nozzle_control_p1", "actual_time_myr": time,
            "mass_g": mass, "total_energy_erg": energy,
        })
    rows = flux.integrate_flux_series(
        flux_rows, storage_rows, one_sided_power_erg_s=1.0,
        jet_start_myr=0.0, jet_active_myr=1.0,
    )
    by_method = {row["temporal_quadrature"]: row for row in rows}
    seconds = flux.SECONDS_PER_MYR
    assert by_method["left_rectangle"]["inferred_internal_mass_source_g"] == pytest.approx(3.0)
    assert by_method["trapezoid"]["inferred_internal_mass_source_g"] == pytest.approx(3.0 + seconds)
    assert by_method["right_rectangle"]["inferred_internal_mass_source_g"] == pytest.approx(3.0 + 2.0 * seconds)


def test_end_to_end_checkpoints_storage_source_and_manifest(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    write_h5(outputs / "data.0000.flt.h5", timestep="Timestep_0", time_code=0.0, rho=1.0)
    write_h5(
        outputs / "data.0001.flt.h5",
        timestep="Timestep_1",
        time_code=flux.SECONDS_PER_MYR / (flux.UNIT_LENGTH_CM / flux.UNIT_VELOCITY_CMS),
        rho=1.25,
    )
    environment = tmp_path / "environment.csv"
    np.savetxt(environment, np.array([
        [0.0, 1.0e-27, 1.0e-12, 0.0, 0.0, 0.0],
        [20.0 * flux.UNIT_LENGTH_CM, 1.0e-27, 1.0e-12, 0.0, 0.0, 0.0],
    ]))
    pluto_ini = tmp_path / "pluto.ini"
    pluto_ini.write_text("""[Grid]\nx = 1\n[Parameters]\nJET_PWR 1e43\nJET_SPD 0.1\nJET_INJECTION_HEIGHT 0.1\nJET_INITIAL_RADIUS 0.1\nJET_X1O 0\nJET_X2O 0\nJET_X3O 0\nJET_ROTATION_ANGLE 0\nJET_START_TIME 0\nJET_END_TIME 50\nJET_ACTIVE_TIME 50\nJET_EPISODES 1\n""")
    source = tmp_path / "src"
    source.mkdir()
    (source / "definitions_usr.h").write_text("""#define DENSITY_PROFILE ENV_TABULATED\n#define JET_INJECTION_ZONE SPHERICAL_INJECTION_ZONE\n#define JET_INJECTION_CAP YES\n#define JET_INJECTION_ROTATED NO\n#define JET_DENSITY_CALCULATION DENSITY_LENGTH_SCALE\n#define JET_RELATIVISTIC_DENSITY NO\n#define SUPERNOVAE_ENERGY_INPUT NO\n#define STELLAR_MASS_LOSS NO\n""")
    (source / "definitions.h").write_text("""#define PHYSICS HD\n#define DIMENSIONS 3\n#define GEOMETRY CARTESIAN\n#define EOS IDEAL\n#define BODY_FORCE VECTOR\n#define COOLING NO\n""")
    (source / "pluto_usr.h").write_text("#define MOVING_INJECTION_REGION MOVING_INJECTION_NONE\n")
    (source / "jet.c").write_text("void Jet_WithinNozzle; jtc->r <= jtc->jet_injection_properties->injection_region_radius;")
    (source / "init.c").write_text("JET_INJECTION_ZONE == SPHERICAL_INJECTION_ZONE; if (within_r); FLAG_INTERNAL_BOUNDARY; g_gamma = 5.0/3.0;")
    result = tmp_path / "result"
    provenance = flux.run_analysis(
        case="TEST", outputs_dirs=[outputs], environment_path=environment,
        pluto_ini=pluto_ini, problem_source_dir=source, output_dir=result,
        shell_layers=(1,), control_padding_cells=(1,),
    )
    assert provenance["scientific_status"].startswith("cell-centred")
    assert len(list((result / "checkpoints").glob("*.json"))) == 2
    with (result / "integrated_control_balances.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    row = next(
        item for item in rows
        if item["surface"] == "nozzle_control_p1"
        and item["reconstruction"] == "centered_primitives"
        and item["temporal_quadrature"] == "trapezoid"
    )
    expected_mass = 0.25 * 27.0 * flux.UNIT_DENSITY_CGS * flux.UNIT_LENGTH_CM**3
    assert float(row["integrated_mass_flux_outward_g"]) == pytest.approx(0.0, abs=1.0)
    assert float(row["inferred_internal_mass_source_g"]) == pytest.approx(expected_mass)
    with (result / "manifest.sha256.csv").open(newline="") as handle:
        manifest = list(csv.DictReader(handle))
    for item in manifest:
        digest = hashlib.sha256((result / item["filename"]).read_bytes()).hexdigest()
        assert digest == item["sha256"]
    # An identical rerun resumes entirely from the durable per-snapshot state.
    resumed = flux.run_analysis(
        case="TEST", outputs_dirs=[outputs], environment_path=environment,
        pluto_ini=pluto_ini, problem_source_dir=source, output_dir=result,
        shell_layers=(1,), control_padding_cells=(1,),
    )
    assert resumed["analysis_signature"] == provenance["analysis_signature"]
    # Metadata drift invalidates every old checkpoint rather than mixing runs.
    (outputs / "data.0001.flt.h5").touch()
    with pytest.raises(ValueError, match="checkpoint provenance mismatch"):
        flux.run_analysis(
            case="TEST", outputs_dirs=[outputs], environment_path=environment,
            pluto_ini=pluto_ini, problem_source_dir=source, output_dir=result,
            shell_layers=(1,), control_padding_cells=(1,),
        )


def test_definitions_fail_closed_on_different_source_geometry(tmp_path: Path) -> None:
    path = tmp_path / "definitions_usr.h"
    path.write_text("""#define DENSITY_PROFILE ENV_TABULATED\n#define JET_INJECTION_ZONE CONICAL_INJECTION_ZONE\n#define JET_INJECTION_CAP YES\n#define JET_INJECTION_ROTATED NO\n#define JET_DENSITY_CALCULATION DENSITY_LENGTH_SCALE\n#define JET_RELATIVISTIC_DENSITY NO\n#define SUPERNOVAE_ENERGY_INPUT NO\n#define STELLAR_MASS_LOSS NO\n""")
    with pytest.raises(ValueError, match="unsupported source geometry"):
        flux.parse_source_definitions(path)


def test_nonadvective_overrides_accept_absent_or_one_explicit_no(tmp_path: Path) -> None:
    path = tmp_path / "definitions.h"
    path.write_text("#define THERMAL_CONDUCTION NO\n")
    assert flux.validate_absent_nonadvective_overrides(path) == {
        "THERMAL_CONDUCTION": "explicitly_disabled",
        "VISCOSITY": "no_problem_override; PLUTO default applies",
    }


@pytest.mark.parametrize(
    "definitions",
    (
        "#define THERMAL_CONDUCTION YES\n",
        "#define THERMAL_CONDUCTION NO\n#define THERMAL_CONDUCTION NO\n",
    ),
)
def test_nonadvective_overrides_reject_active_or_duplicate_definitions(
    tmp_path: Path, definitions: str,
) -> None:
    path = tmp_path / "definitions.h"
    path.write_text(definitions)
    with pytest.raises(ValueError, match="expected absence or exactly one definition set to NO"):
        flux.validate_absent_nonadvective_overrides(path)


def test_moving_source_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "pluto_usr.h"
    path.write_text("#define MOVING_INJECTION_REGION MOVING_INJECTION_LINEAR\n")
    with pytest.raises(ValueError, match="not uniquely stationary"):
        flux.validate_stationary_source(path)
