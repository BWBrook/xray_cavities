#define  PHYSICS                        HD
#define  DIMENSIONS                     3
#define  GEOMETRY                       CARTESIAN
#define  BODY_FORCE                     VECTOR
#define  COOLING                        NO
#define  RECONSTRUCTION                 LINEAR
#define  TIME_STEPPING                  RK2
#define  NTRACER                        1
#define  SELF_GRAV                      NO
#define  PARTICLES                      NO
#define  USER_DEF_PARAMETERS            25

/* -- physics dependent declarations -- */

#define  DUST_FLUID                     NO
#define  EOS                            IDEAL
#define  ENTROPY_SWITCH                 SELECTIVE
#define  INCLUDE_LES                    NO
#define  THERMAL_CONDUCTION             NO
#define  VISCOSITY                      NO
#define  RADIATION                      NO
#define  ROTATING_FRAME                 NO

/* -- user-defined parameters (labels) -- */

#define  JET_PWR                        0
#define  JET_SPD                        1
#define  JET_CHI                        2
#define  JET_OA_PRIMARY                 3
#define  JET_OA_SECONDARY               4
#define  JET_INJECTION_HEIGHT           5
#define  JET_INITIAL_RADIUS             6
#define  JET_X1O                        7
#define  JET_X2O                        8
#define  JET_X3O                        9
#define  JET_ROTATION_ANGLE             10
#define  JET_START_TIME                 11
#define  JET_END_TIME                   12
#define  JET_ACTIVE_TIME                13
#define  JET_EPISODES                   14
#define  ENV_RHO_0                      15
#define  ENV_R_SCALING                  16
#define  ENV_DELTA_NFW                  17
#define  ENV_B_EXPONENT                 18
#define  ENV_TEMP                       19
#define  ENV_X1O                        20
#define  ENV_X2O                        21
#define  ENV_X3O                        22
#define  PART_INJECT_FREQUENCY          23
#define  STELLAR_MASS                   24

/* [Beg] user-defined constants (do not change this line) */

#define  WARNING_MESSAGES               NO
#define  INTERNAL_BOUNDARY              YES
#define  SHOCK_FLATTENING               MULTID
#define  LIMITER                        MINMOD_LIM
#define  MU_NORM                        0.60364
#define  UNIT_DENSITY                   ((CONST_amu)*MU_NORM)
#define  UNIT_LENGTH                    ((CONST_pc)*1e3)
#define  UNIT_VELOCITY                  CONST_c
#define  RECONSTRUCT_4VEL               NO
#define  INITIAL_SMOOTHING              NO
#define  CHAR_LIMITING                  NO
#define  SHOW_TIME_STEPS                YES
#define  SHOW_TIMING                    YES
#define  MULTIPLE_LOG_FILES             YES
#define  PARTICLES                      NO

/* [End] user-defined constants (do not change this line) */
