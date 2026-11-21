#ifndef ENTROPY_RESTART_DIAGNOSTICS_H
#define ENTROPY_RESTART_DIAGNOSTICS_H

#include "pluto.h"

#if PHYSICS != HD || EOS != IDEAL || TIME_STEPPING != RK2 || GEOMETRY != CARTESIAN || DIMENSIONS != 3 || NTRACER != 1 || RADIATION || FAILSAFE || defined(HIGH_ORDER)
#error "Entropy repair accounting is defined for the production Cartesian RK2 HD configuration"
#endif
#if ENTROPY_SWITCH != SELECTIVE && ENTROPY_SWITCH != NO
#error "Select the production entropy switch or NO for the paired restart"
#endif

enum {
  ER_NEG_RHO = 1, ER_NEG_E = 2, ER_USE_S = 4,
  ER_NEG_PS = 8, ER_NEG_PE = 16, ER_WOULD_NEG_PE = 32
};

extern const Grid *EntropyRestartActive;
void EntropyRestartBegin(int stage, const Grid *grid);
void EntropyRestartCell(int i, uint16_t flag, unsigned events, double rho0,
                        double tracer_mass, double initial, double after_e_floor,
                        double final);
void EntropyRestartCommit(void);

#ifdef ENTROPY_RESTART_IMPLEMENTATION

const Grid *EntropyRestartActive = NULL;
static int er_stage;

enum {
  ER_CELLS, ER_S_CELLS, ER_RHO_FLOORS, ER_E_FLOORS, ER_PS_FLOORS, ER_PE_FLOORS,
  ER_COUNTERFACTUAL_PE, ER_NONFINITE_ENERGY,
  ER_E_POS, ER_E_NEG, ER_S_POS, ER_S_NEG, ER_PS_POS, ER_PS_NEG, ER_PE_POS, ER_PE_NEG,
  ER_CELL_POS, ER_CELL_NEG, ER_RHO_MASS, ER_METRICS
};
enum { ER_STAGES = 2, ER_RADII = 8, ER_TRACERS = 5 };
static double er_local[ER_STAGES][ER_RADII][ER_TRACERS][ER_METRICS];

static const char *const er_shells[ER_RADII] = {
  "injector_flag", "r_lt_0.75", "r_0.75_5", "r_5_10",
  "r_10_25", "r_25_50", "r_50_100", "r_ge_100"
};
static const char *const er_tracers[ER_TRACERS] = {
  "f_le_0.001", "f_0.001_0.005", "f_0.005_0.5", "f_gt_0.5", "invalid"
};

static int er_radius(int i, uint16_t flag)
{
  const Grid *g = EntropyRestartActive;
  double x = g->x[IDIR][i], y = g->x[JDIR][g_j], z = g->x[KDIR][g_k];
  double kpc = UNIT_LENGTH/(1000.0*CONST_pc);
  double r2 = (x*x + y*y + z*z)*kpc*kpc;
  if (flag & FLAG_INTERNAL_BOUNDARY) return 0;
  if (r2 < 0.75*0.75) return 1;
  if (r2 < 25.0) return 2;
  if (r2 < 100.0) return 3;
  if (r2 < 625.0) return 4;
  if (r2 < 2500.0) return 5;
  if (r2 < 10000.0) return 6;
  return 7;
}

static int er_tracer(double tracer_mass, double rho)
{
  if (!(rho > 0.0)) return 4;
  double f = tracer_mass/rho;
  if (!(f >= 0.0 && f <= 1.0)) return 4;
  if (f <= 0.001) return 0;
  if (f <= 0.005) return 1;
  if (f <= 0.5) return 2;
  return 3;
}

static void er_signed(double *row, int positive, double change)
{
  row[positive + (change < 0.0)] += change;
}

void EntropyRestartBegin(int stage, const Grid *grid)
{
  if (stage == 1) memset(er_local, 0, sizeof(er_local));
  er_stage = stage - 1;
  EntropyRestartActive = grid;
}

void EntropyRestartCell(int i, uint16_t flag, unsigned events, double rho0,
                        double tracer_mass, double initial, double after_e_floor,
                        double final)
{
  double *row = er_local[er_stage][er_radius(i, flag)][er_tracer(tracer_mass, rho0)];
  double volume = EntropyRestartActive->dV[g_k][g_j][i];
  row[ER_CELLS]++;
  if (events & ER_NEG_RHO) {
    row[ER_RHO_FLOORS]++;
    row[ER_RHO_MASS] += (g_smallDensity - rho0)*volume;
  }
  if (events & ER_WOULD_NEG_PE) row[ER_COUNTERFACTUAL_PE]++;
  if (!isfinite(initial) || !isfinite(after_e_floor) || !isfinite(final))
    row[ER_NONFINITE_ENERGY]++;
  if (events & ER_NEG_E) {
    row[ER_E_FLOORS]++;
    er_signed(row, ER_E_POS, (after_e_floor - initial)*volume);
  }
  if (events & ER_USE_S) {
    row[ER_S_CELLS]++;
    if (events & ER_NEG_PS) {
      row[ER_PS_FLOORS]++;
      er_signed(row, ER_PS_POS, (final - after_e_floor)*volume);
    } else {
      er_signed(row, ER_S_POS, (final - after_e_floor)*volume);
    }
  } else if (events & ER_NEG_PE) {
    row[ER_PE_FLOORS]++;
    er_signed(row, ER_PE_POS, (final - after_e_floor)*volume);
  }
  er_signed(row, ER_CELL_POS, (final - initial)*volume);
}

static FILE *er_output(void)
{
  static FILE *stream;
  if (stream == NULL) {
    char filename[512];
    snprintf(filename, sizeof(filename), "%s/entropy_rk_%ld.csv", RuntimeGet()->output_dir, g_stepNumber);
    stream = fopen(filename, "wx");
    if (stream == NULL) {
      perror(filename);
      QUIT_PLUTO(1);
    }
    fputs("step,time_start_code,time_end_code,dt_code,entropy_switch,stage,rk_weight,"
          "radius_kpc,tracer_fraction,cell_visits,entropy_visits,density_floors,gas_energy_floors,"
          "p_entropy_floors,p_energy_floors,entropy_visits_with_negative_p_energy,nonfinite_energy_visits,"
          "raw_E_floor_gain,raw_E_floor_loss,raw_entropy_gain,raw_entropy_loss,"
          "raw_entropy_with_p_floor_gain,raw_entropy_with_p_floor_loss,raw_p_energy_floor_gain,raw_p_energy_floor_loss,"
          "raw_cell_gain,raw_cell_loss,raw_density_floor_mass_code,effective_net_code,effective_cell_gross_code,energy_unit_erg\n", stream);
  }
  return stream;
}

void EntropyRestartCommit(void)
{
  static double global[ER_STAGES][ER_RADII][ER_TRACERS][ER_METRICS];
  int s, r, t, metric;
  double unit_energy = UNIT_DENSITY*UNIT_VELOCITY*UNIT_VELOCITY*UNIT_LENGTH*UNIT_LENGTH*UNIT_LENGTH;
#ifdef PARALLEL
  MPI_Reduce(er_local, global, ER_STAGES*ER_RADII*ER_TRACERS*ER_METRICS,
             MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
#else
  memcpy(global, er_local, sizeof(global));
#endif
  if (prank != 0) return;
  FILE *stream = er_output();
  for (s = 0; s < ER_STAGES; s++) {
    double weight = s == 0 ? 0.5 : 1.0;
    for (r = 0; r < ER_RADII; r++) {
      for (t = 0; t < ER_TRACERS; t++) {
        double *row = global[s][r][t];
        if (row[ER_CELLS] == 0.0) continue;
        fprintf(stream, "%ld,%.17g,%.17g,%.17g,%s,%d,%.1f,%s,%s", g_stepNumber,
                g_time, g_time + g_dt, g_dt, ENTROPY_SWITCH ? "selective" : "off",
                s + 1, weight, er_shells[r], er_tracers[t]);
        for (metric = 0; metric < ER_METRICS; metric++) fprintf(stream, ",%.17g", row[metric]);
        fprintf(stream, ",%.17g,%.17g,%.17g\n", weight*(row[ER_CELL_POS] + row[ER_CELL_NEG]),
                weight*(row[ER_CELL_POS] - row[ER_CELL_NEG]), unit_energy);
      }
    }
  }
  if (fflush(stream) != 0 || ferror(stream)) {
    perror("entropy RK ledger");
    QUIT_PLUTO(1);
  }
}

#endif
#endif
