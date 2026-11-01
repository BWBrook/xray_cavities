#include "pluto.h"
#include "pluto_usr.h"
#include "structs_usr.h"
#include "units.h"

#include <float.h>

#if PHYSICS != HD
#error "paired no-jet diagnostics require PHYSICS == HD"
#endif
#if TIME_STEPPING != RK2
#error "paired no-jet diagnostics require TIME_STEPPING == RK2"
#endif
#if GEOMETRY != CARTESIAN
#error "paired no-jet diagnostics require Cartesian geometry"
#endif
#if !(BODY_FORCE & VECTOR)
#error "paired no-jet diagnostics require vector body force"
#endif
#if PARTICLES != NO
#error "paired no-jet diagnostics require particles disabled"
#endif
#if EOS != IDEAL
#error "paired no-jet diagnostics require the ideal equation of state"
#endif
#if DIMENSIONS != 3
#error "paired no-jet diagnostics require three dimensions"
#endif
#if COOLING != NO
#error "paired no-jet diagnostics require cooling disabled"
#endif
#if RADIATION != NO
#error "paired no-jet diagnostics require radiation disabled"
#endif
#if NTRACER != 1
#error "paired no-jet diagnostics require exactly one tracer"
#endif
#if ENTROPY_SWITCH != SELECTIVE
#error "paired no-jet diagnostics require the retained selective entropy switch"
#endif
#if FAILSAFE != NO
#error "paired no-jet diagnostics require failsafe retries disabled"
#endif

extern TabulatedEnvironmentProperties ep;

enum { FACE_COUNT = 6, QUANTITY_COUNT = 3, PART_COUNT = 3 };
enum { MASS_Q = 0, HYDRO_Q = 1, POTENTIAL_Q = 2 };
enum { NET_PART = 0, POSITIVE_PART = 1, NEGATIVE_PART = 2 };

static double step_face[FACE_COUNT][QUANTITY_COUNT][PART_COUNT];
static double step_gravity_work;
static double step_conversion_energy_repair[PART_COUNT];
static double step_conversion_energy_repair_gross;
static long step_conversion_failure_flagged_cell_observations;
static long step_conversion_nonzero_return_calls;
static double conversion_energy_repair_weight;
static Grid *conversion_energy_repair_grid;
static int conversion_energy_repair_pending;
static double step_dt = -1.0;
static long step_number = -1;
static int stage_seen[3];
static double *potential_nodes;
static double ***cell_potential;

static void fail(const char *message)
{
  print("[paired-nojet] %s\n", message);
  QUIT_PLUTO(1);
}

static double stage_weight(void)
{
  if (g_intStage == 1 || g_intStage == 2) return 0.5;
  fail("unexpected integration stage; RK2 stages 1 and 2 are required");
  return 0.0;
}

static void note_step(double dt)
{
  if (step_number < 0) {
    step_number = g_stepNumber;
    step_dt = dt;
  } else if (step_number != g_stepNumber) {
    fail("analysis did not flush diagnostics after the preceding accepted step");
  } else if (fabs(step_dt - dt) > 8.0*DBL_EPSILON*fmax(fabs(step_dt), fabs(dt))) {
    fail("RK2 stages used different time increments");
  }
  stage_seen[g_intStage] = 1;
}

static void add_signed(double value, double parts[PART_COUNT])
{
  parts[NET_PART] += value;
  if (value >= 0.0) parts[POSITIVE_PART] += value;
  else parts[NEGATIVE_PART] += value;
}

static void ensure_potential(void)
{
  int n;
  if (potential_nodes != NULL) return;
  if (ep.hot_ndata < 2 || ep.hot_rad == NULL || ep.hot_diffPot == NULL) {
    fail("tabulated environment is unavailable for the fixed potential");
  }
  potential_nodes = malloc((size_t)ep.hot_ndata*sizeof(double));
  if (potential_nodes == NULL) fail("unable to allocate the fixed-potential table");
  potential_nodes[0] = 0.0;
  for (n = 1; n < ep.hot_ndata; n++) {
    double g0 = -ep.hot_diffPot[n - 1];
    double g1 = -ep.hot_diffPot[n];
    double dr = ep.hot_rad[n] - ep.hot_rad[n - 1];
    if (!(dr > 0.0) || !isfinite(g0 + g1)) {
      fail("invalid radius or gravity in the tabulated environment");
    }
    potential_nodes[n] = potential_nodes[n - 1] + 0.5*(g0 + g1)*dr;
  }
}

static double fixed_potential(double x1, double x2, double x3)
{
  int lo, hi;
  double r, fraction;
  ensure_potential();
  x1 -= ep.offset[0];
  x2 -= ep.offset[1];
  x3 -= ep.offset[2];
  r = sqrt(x1*x1 + x2*x2 + x3*x3);
  if (!isfinite(r) || r < 0.0 || r > ep.hot_rad[ep.hot_ndata - 1]*(1.0 + 1.0e-10)) {
    fail("grid coordinate lies outside the fixed-potential table");
  }
  if (r <= ep.hot_rad[0]) return potential_nodes[0];
  if (r >= ep.hot_rad[ep.hot_ndata - 1]) return potential_nodes[ep.hot_ndata - 1];
  lo = 0;
  hi = ep.hot_ndata - 1;
  while (hi - lo > 1) {
    int middle = lo + (hi - lo)/2;
    if (ep.hot_rad[middle] <= r) lo = middle;
    else hi = middle;
  }
  fraction = (r - ep.hot_rad[lo])/(ep.hot_rad[hi] - ep.hot_rad[lo]);
  return potential_nodes[lo] + fraction*(potential_nodes[hi] - potential_nodes[lo]);
}

static void ensure_cell_potential(Grid *grid)
{
  int i, j, k;
  if (cell_potential != NULL) return;
  cell_potential = ARRAY_3D(NX3_TOT, NX2_TOT, NX1_TOT, double);
  if (cell_potential == NULL) fail("unable to allocate the cell-potential cache");
  DOM_LOOP(k,j,i) {
    cell_potential[k][j][i] = fixed_potential(
        grid->x[IDIR][i], grid->x[JDIR][j], grid->x[KDIR][k]);
  }
}

static void face_geometry(Grid *grid, int direction, int interface_index,
                          int i, int j, int k, double *area, double *potential)
{
  double x1 = grid->x[IDIR][i];
  double x2 = grid->x[JDIR][j];
  double x3 = grid->x[KDIR][k];
  if (direction == IDIR) {
    i = interface_index;
    x1 = grid->xr[IDIR][interface_index];
  } else if (direction == JDIR) {
    j = interface_index;
    x2 = grid->xr[JDIR][interface_index];
  } else {
    k = interface_index;
    x3 = grid->xr[KDIR][interface_index];
  }
  *area = grid->A[direction][k][j][i];
  *potential = fixed_potential(x1, x2, x3);
}

static void accumulate_interface(const Sweep *sweep, Grid *grid, int interface_index,
                                 int face, double outward_sign, double weighted_dt)
{
  int i = g_i, j = g_j, k = g_k;
  double area, potential, mass, hydro;
  face_geometry(grid, g_dir, interface_index, i, j, k, &area, &potential);
  mass = outward_sign*sweep->flux[interface_index][RHO]*area*weighted_dt;
  hydro = outward_sign*sweep->flux[interface_index][ENG]*area*weighted_dt;
  add_signed(mass, step_face[face][MASS_Q]);
  add_signed(hydro, step_face[face][HYDRO_Q]);
  add_signed(potential*mass, step_face[face][POTENTIAL_Q]);
}

void PairedNojetAccumulateBoundaryFlux(const Sweep *sweep, int beg, int end,
                                       double dt, Grid *grid)
{
  double weighted_dt;
  note_step(dt);
  weighted_dt = stage_weight()*dt;
  if (grid->lbound[g_dir] != 0) {
    accumulate_interface(sweep, grid, beg - 1, 2*g_dir, -1.0, weighted_dt);
  }
  if (grid->rbound[g_dir] != 0) {
    accumulate_interface(sweep, grid, end, 2*g_dir + 1, 1.0, weighted_dt);
  }
}

void PairedNojetAccumulateGravityWork(double energy_density_increment, double volume)
{
  note_step(g_dt);
  step_gravity_work += stage_weight()*energy_density_increment*volume;
}

void PairedNojetBeginConversionEnergyRepair(double final_solution_weight, Grid *grid)
{
  if (conversion_energy_repair_pending) fail("nested conversion-energy measurement");
  if (final_solution_weight != 0.5 && final_solution_weight != 1.0) {
    fail("unexpected RK2 conversion-energy weight");
  }
  conversion_energy_repair_weight = final_solution_weight;
  conversion_energy_repair_grid = grid;
  conversion_energy_repair_pending = 1;
}

void PairedNojetRecordConversionEnergyRepairCell(double energy_density_increment,
                                                  int i, uint16_t flag)
{
  double weighted_change;
  if (!conversion_energy_repair_pending) return;
  weighted_change = conversion_energy_repair_weight*energy_density_increment
                  *conversion_energy_repair_grid->dV[g_k][g_j][i];
  add_signed(weighted_change, step_conversion_energy_repair);
  step_conversion_energy_repair_gross += fabs(weighted_change);
  if (flag & FLAG_CONS2PRIM_FAIL) {
    step_conversion_failure_flagged_cell_observations++;
  }
}

void PairedNojetEndConversionEnergyRepair(int conversion_status)
{
  if (!conversion_energy_repair_pending) {
    fail("conversion-energy measurement ended without a beginning");
  }
  if (conversion_status != 0) step_conversion_nonzero_return_calls++;
  conversion_energy_repair_pending = 0;
  conversion_energy_repair_grid = NULL;
}

static void reconstruct_face(const Data *d, Grid *grid, int direction, int high,
                             double values[QUANTITY_COUNT], double *minimum_vn,
                             double *maximum_vn, int *boundary_type)
{
  int i, j, k;
  int active_index;
  double sign = high ? 1.0 : -1.0;
  *minimum_vn = DBL_MAX;
  *maximum_vn = -DBL_MAX;
  *boundary_type = high ? grid->rbound[direction] : grid->lbound[direction];
  if (*boundary_type == 0) return;
  active_index = high ? (direction == IDIR ? IEND : direction == JDIR ? JEND : KEND)
                      : (direction == IDIR ? IBEG : direction == JDIR ? JBEG : KBEG);
  if (direction == IDIR) {
    i = active_index;
    for (k = KBEG; k <= KEND; k++) for (j = JBEG; j <= JEND; j++) {
      double rho = d->Vc[RHO][k][j][i], prs = d->Vc[PRS][k][j][i];
      double vx = d->Vc[VX1][k][j][i], vy = d->Vc[VX2][k][j][i], vz = d->Vc[VX3][k][j][i];
      double vn_out = sign*vx, area, phi, mass;
      face_geometry(grid, direction, high ? i : i - 1, i, j, k, &area, &phi);
      mass = rho*vn_out*area;
      values[MASS_Q] += mass;
      values[HYDRO_Q] += vn_out*(0.5*rho*(vx*vx + vy*vy + vz*vz)
                           + nonrel_gamma*prs/(nonrel_gamma - 1.0))*area;
      values[POTENTIAL_Q] += phi*mass;
      *minimum_vn = fmin(*minimum_vn, vn_out);
      *maximum_vn = fmax(*maximum_vn, vn_out);
    }
  } else if (direction == JDIR) {
    j = active_index;
    for (k = KBEG; k <= KEND; k++) for (i = IBEG; i <= IEND; i++) {
      double rho = d->Vc[RHO][k][j][i], prs = d->Vc[PRS][k][j][i];
      double vx = d->Vc[VX1][k][j][i], vy = d->Vc[VX2][k][j][i], vz = d->Vc[VX3][k][j][i];
      double vn_out = sign*vy, area, phi, mass;
      face_geometry(grid, direction, high ? j : j - 1, i, j, k, &area, &phi);
      mass = rho*vn_out*area;
      values[MASS_Q] += mass;
      values[HYDRO_Q] += vn_out*(0.5*rho*(vx*vx + vy*vy + vz*vz)
                           + nonrel_gamma*prs/(nonrel_gamma - 1.0))*area;
      values[POTENTIAL_Q] += phi*mass;
      *minimum_vn = fmin(*minimum_vn, vn_out);
      *maximum_vn = fmax(*maximum_vn, vn_out);
    }
  } else {
    k = active_index;
    for (j = JBEG; j <= JEND; j++) for (i = IBEG; i <= IEND; i++) {
      double rho = d->Vc[RHO][k][j][i], prs = d->Vc[PRS][k][j][i];
      double vx = d->Vc[VX1][k][j][i], vy = d->Vc[VX2][k][j][i], vz = d->Vc[VX3][k][j][i];
      double vn_out = sign*vz, area, phi, mass;
      face_geometry(grid, direction, high ? k : k - 1, i, j, k, &area, &phi);
      mass = rho*vn_out*area;
      values[MASS_Q] += mass;
      values[HYDRO_Q] += vn_out*(0.5*rho*(vx*vx + vy*vy + vz*vz)
                           + nonrel_gamma*prs/(nonrel_gamma - 1.0))*area;
      values[POTENTIAL_Q] += phi*mass;
      *minimum_vn = fmin(*minimum_vn, vn_out);
      *maximum_vn = fmax(*maximum_vn, vn_out);
    }
  }
}

static void reset_step(void)
{
  memset(step_face, 0, sizeof(step_face));
  step_gravity_work = 0.0;
  memset(step_conversion_energy_repair, 0, sizeof(step_conversion_energy_repair));
  step_conversion_energy_repair_gross = 0.0;
  step_conversion_failure_flagged_cell_observations = 0;
  step_conversion_nonzero_return_calls = 0;
  step_dt = -1.0;
  step_number = -1;
  memset(stage_seen, 0, sizeof(stage_seen));
}

void PairedNojetAnalysis(const Data *d, Grid *grid)
{
  int i, j, k, face, quantity, part;
  double local_storage[5] = {0.0, 0.0, 0.0, 0.0, 0.0};
  double global_storage[5];
  double local_reconstructed[FACE_COUNT][QUANTITY_COUNT] = {{0.0}};
  double global_reconstructed[FACE_COUNT][QUANTITY_COUNT];
  double local_min_vn[FACE_COUNT], local_max_vn[FACE_COUNT];
  double global_min_vn[FACE_COUNT], global_max_vn[FACE_COUNT];
  int local_boundary_type[FACE_COUNT], global_boundary_type[FACE_COUNT];
  double global_step_face[FACE_COUNT][QUANTITY_COUNT][PART_COUNT];
  double global_gravity_work;
  double global_conversion_energy_repair[PART_COUNT];
  double global_conversion_energy_repair_gross;
  long global_conversion_failure_flagged_cell_observations;
  long global_conversion_nonzero_return_calls;
  static int first_analysis = 1;
  static double previous_time;
  static double previous_storage[5];
  static double previous_reconstructed[FACE_COUNT][QUANTITY_COUNT];
  static double cumulative_face[FACE_COUNT][QUANTITY_COUNT][PART_COUNT];
  static double cumulative_gravity_work;
  static double cumulative_conversion_energy_repair[PART_COUNT];
  static double cumulative_conversion_energy_repair_gross;
  static long cumulative_conversion_failure_flagged_cell_observations;
  static long cumulative_conversion_nonzero_return_calls;
  static const char *face_name[FACE_COUNT] = {
    "x1_beg", "x1_end", "x2_beg", "x2_end", "x3_beg", "x3_end"
  };
  double interval_dt = first_analysis ? 0.0 : g_time - previous_time;
  double mass_unit = vn.mass;
  double energy_unit = vn.energy;
  double mass_rate_unit = vn.mass/vn.time;
  double energy_rate_unit = vn.energy/vn.time;

  ensure_potential();
  ensure_cell_potential(grid);
  if (step_number >= 0 && (!stage_seen[1] || !stage_seen[2])) {
    fail("an accepted RK2 step did not record both integration stages");
  }
  if (conversion_energy_repair_pending) {
    fail("analysis encountered an unfinished conversion-energy measurement");
  }
  DOM_LOOP(k,j,i) {
    double rho = d->Vc[RHO][k][j][i], prs = d->Vc[PRS][k][j][i];
    double vx = d->Vc[VX1][k][j][i], vy = d->Vc[VX2][k][j][i], vz = d->Vc[VX3][k][j][i];
    double volume = grid->dV[k][j][i];
    double phi = cell_potential[k][j][i];
    if (!isfinite(rho + prs + vx + vy + vz) || rho <= 0.0 || prs <= 0.0) {
      fail("non-finite or non-positive state in Analysis");
    }
    local_storage[0] += d->Uc[k][j][i][RHO]*volume;
    local_storage[1] += d->Uc[k][j][i][ENG]*volume;
    local_storage[2] += prs*volume/(nonrel_gamma - 1.0);
    local_storage[3] += 0.5*rho*(vx*vx + vy*vy + vz*vz)*volume;
    local_storage[4] += d->Uc[k][j][i][RHO]*phi*volume;
  }
  for (face = 0; face < FACE_COUNT; face++) {
    reconstruct_face(d, grid, face/2, face%2, local_reconstructed[face],
                     &local_min_vn[face], &local_max_vn[face],
                     &local_boundary_type[face]);
  }

#ifdef PARALLEL
  MPI_Reduce(local_storage, global_storage, 5, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
  MPI_Reduce(local_reconstructed, global_reconstructed, FACE_COUNT*QUANTITY_COUNT,
             MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
  MPI_Reduce(local_min_vn, global_min_vn, FACE_COUNT, MPI_DOUBLE, MPI_MIN, 0, MPI_COMM_WORLD);
  MPI_Reduce(local_max_vn, global_max_vn, FACE_COUNT, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
  MPI_Reduce(local_boundary_type, global_boundary_type, FACE_COUNT, MPI_INT, MPI_MAX, 0, MPI_COMM_WORLD);
  MPI_Reduce(step_face, global_step_face, FACE_COUNT*QUANTITY_COUNT*PART_COUNT,
             MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
  MPI_Reduce(&step_gravity_work, &global_gravity_work, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
  MPI_Reduce(step_conversion_energy_repair, global_conversion_energy_repair,
             PART_COUNT, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
  MPI_Reduce(&step_conversion_energy_repair_gross,
             &global_conversion_energy_repair_gross,
             1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
  MPI_Reduce(&step_conversion_failure_flagged_cell_observations,
             &global_conversion_failure_flagged_cell_observations,
             1, MPI_LONG, MPI_SUM, 0, MPI_COMM_WORLD);
  MPI_Reduce(&step_conversion_nonzero_return_calls,
             &global_conversion_nonzero_return_calls,
             1, MPI_LONG, MPI_MAX, 0, MPI_COMM_WORLD);
#else
  memcpy(global_storage, local_storage, sizeof(global_storage));
  memcpy(global_reconstructed, local_reconstructed, sizeof(global_reconstructed));
  memcpy(global_min_vn, local_min_vn, sizeof(global_min_vn));
  memcpy(global_max_vn, local_max_vn, sizeof(global_max_vn));
  memcpy(global_boundary_type, local_boundary_type, sizeof(global_boundary_type));
  memcpy(global_step_face, step_face, sizeof(global_step_face));
  global_gravity_work = step_gravity_work;
  memcpy(global_conversion_energy_repair, step_conversion_energy_repair,
         sizeof(global_conversion_energy_repair));
  global_conversion_energy_repair_gross = step_conversion_energy_repair_gross;
  global_conversion_failure_flagged_cell_observations =
      step_conversion_failure_flagged_cell_observations;
  global_conversion_nonzero_return_calls = step_conversion_nonzero_return_calls;
#endif

  if (prank == 0) {
    FILE *stream;
    double sum_mass = 0.0, sum_hydro = 0.0, sum_potential = 0.0;
    double delta_mass = first_analysis ? 0.0 : global_storage[0] - previous_storage[0];
    double delta_hydro = first_analysis ? 0.0 : global_storage[1] - previous_storage[1];
    double delta_potential = first_analysis ? 0.0 : global_storage[4] - previous_storage[4];
    for (face = 0; face < FACE_COUNT; face++) {
      for (quantity = 0; quantity < QUANTITY_COUNT; quantity++) {
        for (part = 0; part < PART_COUNT; part++) {
          cumulative_face[face][quantity][part] += global_step_face[face][quantity][part];
        }
      }
      sum_mass += global_step_face[face][MASS_Q][NET_PART];
      sum_hydro += global_step_face[face][HYDRO_Q][NET_PART];
      sum_potential += global_step_face[face][POTENTIAL_Q][NET_PART];
    }
    cumulative_gravity_work += global_gravity_work;
    for (part = 0; part < PART_COUNT; part++) {
      cumulative_conversion_energy_repair[part] +=
          global_conversion_energy_repair[part];
    }
    cumulative_conversion_energy_repair_gross +=
        global_conversion_energy_repair_gross;
    cumulative_conversion_failure_flagged_cell_observations +=
        global_conversion_failure_flagged_cell_observations;
    cumulative_conversion_nonzero_return_calls +=
        global_conversion_nonzero_return_calls;
    stream = fopen("paired_nojet_budget.csv", first_analysis ? "w" : "a");
    if (stream == NULL) fail("unable to open paired-nojet diagnostic CSV");
    if (first_analysis) {
      fprintf(stream, "state_step,completed_step,time_code,time_myr,interval_dt_code,face,boundary_type_code,");
      fprintf(stream, "mass_g,hydro_total_erg,thermal_erg,kinetic_erg,potential_erg,");
      fprintf(stream, "conserved_minus_primitive_hydro_erg,");
      fprintf(stream, "actual_mass_net_g,actual_mass_positive_g,actual_mass_negative_g,");
      fprintf(stream, "actual_hydro_net_erg,actual_hydro_positive_erg,actual_hydro_negative_erg,");
      fprintf(stream, "actual_potential_net_erg,actual_potential_positive_erg,actual_potential_negative_erg,");
      fprintf(stream, "cumulative_mass_net_g,cumulative_mass_positive_g,cumulative_mass_negative_g,");
      fprintf(stream, "cumulative_hydro_net_erg,cumulative_hydro_positive_erg,cumulative_hydro_negative_erg,");
      fprintf(stream, "cumulative_potential_net_erg,cumulative_potential_positive_erg,cumulative_potential_negative_erg,");
      fprintf(stream, "reconstructed_mass_rate_g_s,reconstructed_hydro_rate_erg_s,reconstructed_potential_rate_erg_s,");
      fprintf(stream, "reconstructed_mass_interval_g,reconstructed_hydro_interval_erg,reconstructed_potential_interval_erg,");
      fprintf(stream, "minimum_outward_normal_velocity_km_s,maximum_outward_normal_velocity_km_s,");
      fprintf(stream, "gravity_work_interval_erg,gravity_work_cumulative_erg,");
      fprintf(stream, "conversion_energy_repair_net_interval_erg,");
      fprintf(stream, "conversion_energy_repair_positive_interval_erg,");
      fprintf(stream, "conversion_energy_repair_negative_interval_erg,");
      fprintf(stream, "conversion_energy_repair_gross_interval_erg,");
      fprintf(stream, "conversion_energy_repair_net_cumulative_erg,");
      fprintf(stream, "conversion_energy_repair_positive_cumulative_erg,");
      fprintf(stream, "conversion_energy_repair_negative_cumulative_erg,");
      fprintf(stream, "conversion_energy_repair_gross_cumulative_erg,");
      fprintf(stream, "conversion_failure_flagged_cell_observations_interval_count,");
      fprintf(stream, "conversion_failure_flagged_cell_observations_cumulative_count,");
      fprintf(stream, "conversion_nonzero_return_call_interval_count,");
      fprintf(stream, "conversion_nonzero_return_call_cumulative_count,");
      fprintf(stream, "mass_closure_residual_g,");
      fprintf(stream, "hydro_closure_residual_erg,potential_closure_residual_erg,total_closure_residual_erg\n");
    }
    for (face = 0; face < FACE_COUNT; face++) {
      double reconstructed_interval[QUANTITY_COUNT];
      for (quantity = 0; quantity < QUANTITY_COUNT; quantity++) {
        reconstructed_interval[quantity] = first_analysis ? 0.0
          : 0.5*(previous_reconstructed[face][quantity]
               + global_reconstructed[face][quantity])*interval_dt;
      }
      fprintf(stream, "%ld,%ld,%.17g,%.17g,%.17g,%s,%d,",
              g_stepNumber, step_number, g_time, g_time*vn.time/3.15576e13,
              interval_dt, face_name[face], global_boundary_type[face]);
      fprintf(stream, "%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,",
              global_storage[0]*mass_unit, global_storage[1]*energy_unit,
              global_storage[2]*energy_unit, global_storage[3]*energy_unit,
              global_storage[4]*energy_unit,
              (global_storage[1] - global_storage[2] - global_storage[3])*energy_unit);
      for (part = 0; part < PART_COUNT; part++) fprintf(stream, "%.17g,", global_step_face[face][MASS_Q][part]*mass_unit);
      for (part = 0; part < PART_COUNT; part++) fprintf(stream, "%.17g,", global_step_face[face][HYDRO_Q][part]*energy_unit);
      for (part = 0; part < PART_COUNT; part++) fprintf(stream, "%.17g,", global_step_face[face][POTENTIAL_Q][part]*energy_unit);
      for (part = 0; part < PART_COUNT; part++) fprintf(stream, "%.17g,", cumulative_face[face][MASS_Q][part]*mass_unit);
      for (part = 0; part < PART_COUNT; part++) fprintf(stream, "%.17g,", cumulative_face[face][HYDRO_Q][part]*energy_unit);
      for (part = 0; part < PART_COUNT; part++) fprintf(stream, "%.17g,", cumulative_face[face][POTENTIAL_Q][part]*energy_unit);
      fprintf(stream, "%.17g,%.17g,%.17g,",
              global_reconstructed[face][MASS_Q]*mass_rate_unit,
              global_reconstructed[face][HYDRO_Q]*energy_rate_unit,
              global_reconstructed[face][POTENTIAL_Q]*energy_rate_unit);
      fprintf(stream, "%.17g,%.17g,%.17g,",
              reconstructed_interval[MASS_Q]*mass_unit,
              reconstructed_interval[HYDRO_Q]*energy_unit,
              reconstructed_interval[POTENTIAL_Q]*energy_unit);
      fprintf(stream, "%.17g,%.17g,",
              global_min_vn[face]*vn.velocity*1.0e-5,
              global_max_vn[face]*vn.velocity*1.0e-5);
      fprintf(stream, "%.17g,%.17g,%.17g,%.17g,",
              global_gravity_work*energy_unit, cumulative_gravity_work*energy_unit,
              global_conversion_energy_repair[NET_PART]*energy_unit,
              global_conversion_energy_repair[POSITIVE_PART]*energy_unit);
      fprintf(stream, "%.17g,%.17g,",
              global_conversion_energy_repair[NEGATIVE_PART]*energy_unit,
              global_conversion_energy_repair_gross*energy_unit);
      fprintf(stream, "%.17g,%.17g,%.17g,%.17g,",
              cumulative_conversion_energy_repair[NET_PART]*energy_unit,
              cumulative_conversion_energy_repair[POSITIVE_PART]*energy_unit,
              cumulative_conversion_energy_repair[NEGATIVE_PART]*energy_unit,
              cumulative_conversion_energy_repair_gross*energy_unit);
      fprintf(stream, "%ld,%ld,%ld,%ld,",
              global_conversion_failure_flagged_cell_observations,
              cumulative_conversion_failure_flagged_cell_observations,
              global_conversion_nonzero_return_calls,
              cumulative_conversion_nonzero_return_calls);
      fprintf(stream, "%.17g,%.17g,%.17g,%.17g\n",
              (delta_mass + sum_mass)*mass_unit,
              (delta_hydro + sum_hydro - global_gravity_work
               - global_conversion_energy_repair[NET_PART])*energy_unit,
              (delta_potential + sum_potential + global_gravity_work)*energy_unit,
              (delta_hydro + delta_potential + sum_hydro + sum_potential
               - global_conversion_energy_repair[NET_PART])*energy_unit);
    }
    if (fclose(stream) != 0) fail("unable to close paired-nojet diagnostic CSV");
    previous_time = g_time;
    memcpy(previous_storage, global_storage, sizeof(previous_storage));
    memcpy(previous_reconstructed, global_reconstructed, sizeof(previous_reconstructed));
    first_analysis = 0;
  }
  reset_step();
}
