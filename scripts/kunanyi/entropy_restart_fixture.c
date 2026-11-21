/* Manufactured transport for the native RK driver and conservative/primitive mappers. */
#include "pluto.h"
#include "globals.h"

static Runtime runtime;
static double initial[13][NVAR], discrete_input, initial_energy;
static const double x_coord[] = {-1, 0, .6, .75, 5, 10, 25, 50, 100, 4.9, 9.9, 110, 111};
static const double fractions[] = {0, 1, 0, .001, .003, .005, 0, .02, .5, .9, 1.02, 0, 0};

Runtime *RuntimeGet(void) { return &runtime; }
void PlutoError(int failed, char *msg) { if (failed) { fputs(msg, stderr); abort(); } }
void printLog(const char *fmt, ...) { (void)fmt; }
void Boundary(const Data *d, int side, Grid *grid) {}
void FlagShock(const Data *d, Grid *grid) {}
void Particles_LP_Predictor(Data *d, timeStep *dt, double step, Grid *grid) {}
void Particles_LP_Corrector(Data *d, timeStep *dt, double step, Grid *grid) {}
void Particles_Inject(Data *d, Grid *grid) {}

void UpdateStage(Data *d, Data_Arr u, Data_Arr vs, double **unused, double dt, timeStep *ts, Grid *grid)
{
  double u_extra[NVAR] = {0}, v_extra[NVAR] = {0}, *up = u_extra, *vp = v_extra;
  uint16_t extra_flag = 0;
  u_extra[RHO] = 1.0;
  u_extra[ENG] = -1.0;
  ConsToPrim(&up, &vp, 0, 0, &extra_flag);
  if (!(extra_flag & FLAG_CONS2PRIM_FAIL)) abort();

  for (int i = IBEG; i <= IEND; i++) {
    double *cell = u[1][1][i];
    double old_energy = cell[ENG], input[NVAR];
    if (g_intStage == 1) {
      memcpy(initial[i], cell, sizeof(initial[i]));
      initial_energy += old_energy*grid->dV[1][1][i];
      cell[ENG] = (double[]){0, 6, 1, -2, 2, 10, 1, 3, 0, 1, -1, .01}[i];
      cell[MX1] = (double[]){0, 0, 3, 1, .5, 0, 0, 1, 0, 3, 0, 0}[i];
      if (i == 6) cell[RHO] = -.3;
      cell[TRC] = fractions[i]*cell[RHO];
      #if ENTROPY_SWITCH
      cell[ENTR] = (double[]){0, 1, 1, .02, -.4, .6, 1, 1, 1, .5, -.5, 1}[i];
      #endif
      memcpy(input, cell, sizeof(input));
    } else {
      if (i == 2 || i == 3 || i == 9) cell[MX1] += 6.0;
      if (i == 10) cell[ENG] -= 4.0;
      #if ENTROPY_SWITCH
      if (i == 4) cell[ENTR] -= 4.0;
      #endif
      for (int nv = 0; nv < NVAR; nv++) input[nv] = .5*initial[i][nv] + .5*cell[nv];
    }
    discrete_input += .5*(cell[ENG] - old_energy)*grid->dV[1][1][i];
    double entropy = 0.0;
    #if ENTROPY_SWITCH
    entropy = input[ENTR];
    #endif
    printf("input,%d,%d,%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n",
           g_intStage, i, !!(d->flag[1][1][i] & FLAG_INTERNAL_BOUNDARY),
           !!(d->flag[1][1][i] & FLAG_ENTROPY), x_coord[i], grid->dV[1][1][i],
           input[RHO], input[TRC], input[MX1], input[ENG], entropy, g_gamma);
  }
}

int main(int argc, char **argv)
{
  Data data = {0};
  Grid grid = {0};
  timeStep step = {0};
  if (argc != 2) return 2;
  snprintf(runtime.output_dir, sizeof(runtime.output_dir), "%s", argv[1]);
  IBEG = JBEG = KBEG = JEND = KEND = 1;
  IEND = 11; NX1_TOT = NMAX_POINT = 13; NX2_TOT = NX3_TOT = 3;
  g_gamma = 5.0/3.0; g_smallDensity = .4; g_smallPressure = .25;
  g_time = 20; g_dt = .03125; g_stepNumber = 1234;
  double yz[3] = {-1.0, 0.0, 1.0};
  grid.x[0] = (double *)x_coord; grid.x[1] = grid.x[2] = yz;
  grid.dV = ARRAY_3D(3, 3, 13, double);
  data.flag = ARRAY_3D(3, 3, 13, uint16_t);
  data.Vc = ARRAY_4D(NVAR, 3, 3, 13, double);
  data.Uc = ARRAY_4D(3, 3, 13, NVAR, double);
  memset(data.Vc[0][0][0], 0, NVAR*3*3*13*sizeof(double));
  for (int i = IBEG; i <= IEND; i++) {
    grid.dV[1][1][i] = i*.1 + 1.0;
    data.Vc[RHO][1][1][i] = data.Vc[PRS][1][1][i] = 1.0;
    data.Vc[TRC][1][1][i] = fractions[i];
    #if ENTROPY_SWITCH
    data.Vc[ENTR][1][1][i] = 1.0;
    #endif
    uint16_t flag = (i == 1 ? FLAG_INTERNAL_BOUNDARY : 0);
    if (i == 3 || i == 4 || i == 5 || i == 9 || i == 10) flag |= FLAG_ENTROPY;
    if (i == 7) flag |= FLAG_CONS2PRIM_FAIL;
    data.flag[1][1][i] = flag;
  }
  if (AdvanceStep(&data, &step, &grid)) return 3;
  double final_energy = 0;
  for (int i = IBEG; i <= IEND; i++) {
    printf("state,%d,%u", i, (unsigned)data.flag[1][1][i]);
    for (int nv = 0; nv < NVAR; nv++)
      printf(",%a,%a", data.Uc[1][1][i][nv], data.Vc[nv][1][1][i]);
    putchar('\n');
    final_energy += data.Uc[1][1][i][ENG]*grid.dV[1][1][i];
  }
  printf("closure,%.17g\n", final_energy - initial_energy - discrete_input);
  return 0;
}
