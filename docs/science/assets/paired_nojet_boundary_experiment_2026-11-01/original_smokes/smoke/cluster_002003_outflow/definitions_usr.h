#ifndef definitions_usr_h
#define definitions_usr_h
/* Problem definitions are placed here so we don't clutter up definitions.h. */

/** Which density environment profile to use.
 * Options are:
 * - ENV_MAKINO
 * - ENV_KING
 * - ENV_TABULATED
 * - ENV_EXTERNAL
 */
#define  DENSITY_PROFILE                ENV_TABULATED

/** Whether to use the initial velocity from external environment.
 * YES / NO
 */
#define EXT_ENV_VELOCITY         YES

/** Factor to multiply external environment velocities by.
 */
#define EXT_ENV_VELOCITY_FACTOR  1.0

/** Whether we have unique jets, or symmetric ones.
 * YES / NO
 */
#define  UNIQUE_JETS             YES

/** Jet injection zone shape.
 * This determines the shape of the jet injection zone.\n 
 * Options are:
 * - SPHERICAL_INJECTION_ZONE
 * - CONICAL_INJECTION_ZONE
 */
#define  JET_INJECTION_ZONE      SPHERICAL_INJECTION_ZONE

/** Whether the injection region has a cap/rounded top.
 * YES / NO
 */
#define  JET_INJECTION_CAP       YES

/** Whether the jet injection region is rotated.
 * YES / NO
 */
#define  JET_INJECTION_ROTATED          NO

/** How do we calculate our initial jet density?
 * This determines how the jet density is calculated, using
 * either the length scales approach, or from the jet power equation.\n 
 * Options are:
 * - DENSITY_LENGTH_SCALE
 * - DENSITY_JET_POWER
 */
#define JET_DENSITY_CALCULATION  DENSITY_JET_POWER

/** Use the relativistic version of the jet power equation?
 * This determines whether the special relativistic jet power equation
 * (including internal energy) is used, or the classical version.\n 
 * The relativistic jet density is given by
 * \f[
*    \rho_\textrm{j} = \frac{ Q }{ c^2 v_\textrm{j} A_\textrm{j} \left[ \gamma (\gamma - 1) + \gamma^2 / \chi \right] }\,,
 * \f]
 * while the non-relativistic jet density is given by
 * \f[
 *   \rho_\textrm{j} = \frac{ 2 Q }{ v_\textrm{j}^3 A_\textrm{j} }\,.
 * \f]\n 
 * YES / NO
 */
#define  JET_RELATIVISTIC_DENSITY       NO

/** Whether HDF5 compression should enabled.
 * Note that this feature is currently unstable, and
 * can cause simulations to freeze if enabled.\n 
 * YES / NO
 */
#define COMPRESS_HDF5            NO

/** Wether particles are injected in batches.
 * Particles are injected in the injection region either in batches
 * according to the particle injection frequency, or as a continous stream (timestep allowing).
 * In stream mode, the time between injections is set so that the same total number of particles are injected
 * in both modes.\n 
 * YES / NO
 */
#define  PARTICLES_INJECT_IN_BATCHES    NO

/** Particle random deviation mode.
 * This controls how the particles are randomly distrubed when
 * PARTICLES_INJECT_IN_BATCHES is enabled.\n 
 * Options are:
 * - PARTICLES_RANDOM_NONE
 * - PARTICLES_RANDOM_UNIFORM
 * - PARTICLES_RANDOM_GAUSSIAN
 */
#define PARTICLES_RANDOM_MODE    PARTICLES_RANDOM_GAUSSIAN

/** Whether RAiSE particles are enabled.
 * With this enabled, particles will track when they were last shocked,
 * as well as the density, pressure, and tracer from the grid.
 * YES / NO
 */
#define  PARTICLES_LP_RAISE             NO

/** The number of RAiSE particle shock bins.
 * This determines the number of particle bins evenly spaced between
 * PARTICLES_LP_SHK_THRESH_MIN and PARTICLES_LP_SHK_THRESH_MAX (inclusive).
 */
#define  PARTICLES_LP_SHK_BINS          3

/** Minimum shock threshold.
 * The shock detection method is the same as used by PLUTO for other shock flagging needs.
 * Some documentation on this threshold can be found in section 2.2.4 of the user guide,
 * and by looking at the `EPS_SHOCK_ENTROPY` variable in section B.3 of the user guide.
 */
#define  PARTICLES_LP_SHK_THRESH_MIN    0.05

/** Maximum shock threshold.
 */
#define  PARTICLES_LP_SHK_THRESH_MAX    5.0

/** Inner radial boundary condition in spherical coordinates.
 * This determines the inner radial boundary condition in spherical coordinates,
 * outside of the jet inlet. Only the following boundary conditions are implemented:
 * - REFLECTIVE
 * - OUTFLOW
 */
#define SPH_RADIUS_LOWER_BOUNDARY REFLECTIVE

/** Whether supernovae energy input is enabled.
 * Currently untested.\n 
 * YES / NO
 */
#define SUPERNOVAE_ENERGY_INPUT  NO

/** Whether stellar mass loss is enabled.
 * Currently untested.\n 
 * YES / NO
 */
#define STELLAR_MASS_LOSS        NO

/** How to define the jet domain.
 * Options are:\n 
 * - JD_GRAD, set based on pressure gradient (PLUTO default)
 * - JD_PRES, set based on difference between current and initial pressure
 */
#define JD_MODE                  JD_PRES
#endif
