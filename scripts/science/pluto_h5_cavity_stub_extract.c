/*
 * First-pass projected cavity protocol for a PLUTO static-grid HDF5 output.
 *
 * The geometry is intentionally simple and explicit:
 * - one tracer-defined ellipsoid is fitted to each lobe from the 3D
 *   tracer > threshold extents;
 * - local ambient pressure/density are estimated from a just-outside
 *   ellipsoidal shell on the same side of the jet, excluding tracer-rich cells;
 * - sound, buoyancy, and refill ages are first-pass observational proxies.
 *
 * This is a protocol stub for early smoke testing, not the final cavity fitter.
 */

#include <float.h>
#include <hdf5.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define CHECK_H5(call, message)                                                   \
    do {                                                                          \
        if ((call) < 0) {                                                         \
            fprintf(stderr, "HDF5 error: %s\n", (message));                    \
            exit(2);                                                              \
        }                                                                         \
    } while (0)

#define NSIDES 2

static const double CODE_TIME_PER_MYR = 306.6013937879523;
static const double PI_VAL = 3.141592653589793238462643383279502884;
static const double KPC_CM = 3.0856775814913673e21;
static const double UNIT_DENSITY_CGS = 1.0023678e-24;
static const double UNIT_VELOCITY_CMS = 2.99792458e10;
static const double GAMMA_GAS = 5.0 / 3.0;
static const double SECONDS_PER_MYR = 3.15576e13;
static const double DRAG_COEFF = 0.75;

typedef struct {
    unsigned long long cells;
    double x_min, x_max;
    double y_min, y_max;
    double z_min, z_max;
    double tracer_volume_kpc3;
} Bounds;

typedef struct {
    unsigned long long cells;
    double volume_kpc3;
    double pressure_volume_code;
    double density_volume_code;
    double radius_volume_kpc;
} Shell;

static const char *SIDE_NAMES[NSIDES] = {"negative_z", "positive_z"};
static const int SIDE_SIGN[NSIDES] = {-1, 1};

static void usage(const char *prog) {
    fprintf(stderr,
            "Usage: %s <input.h5> <timestep-name> <output-dir> [tracer_threshold] [ambient_tracer_max] [shell_inner] [shell_mid] [shell_outer]\n",
            prog);
}

static void ensure_dir(const char *path) {
    if (mkdir(path, 0775) != 0) {
        FILE *probe = fopen(path, "r");
        if (probe == NULL) {
            perror(path);
            exit(2);
        }
        fclose(probe);
    }
}

static void join_path(char *out, size_t out_size, const char *dir, const char *name) {
    int n = snprintf(out, out_size, "%s/%s", dir, name);
    if (n < 0 || (size_t)n >= out_size) {
        fprintf(stderr, "Path too long: %s/%s\n", dir, name);
        exit(2);
    }
}

static hid_t open_dataset(hid_t file, const char *path) {
    hid_t dataset = H5Dopen2(file, path, H5P_DEFAULT);
    if (dataset < 0) {
        fprintf(stderr, "Could not open dataset: %s\n", path);
        exit(2);
    }
    return dataset;
}

static double read_time_attr(hid_t file, const char *timestep) {
    char group_path[512];
    snprintf(group_path, sizeof(group_path), "/%s", timestep);
    hid_t group = H5Gopen2(file, group_path, H5P_DEFAULT);
    if (group < 0) {
        fprintf(stderr, "Could not open timestep group: %s\n", group_path);
        exit(2);
    }
    hid_t attr = H5Aopen(group, "Time", H5P_DEFAULT);
    if (attr < 0) {
        CHECK_H5(H5Gclose(group), "close group");
        return NAN;
    }
    double value = NAN;
    CHECK_H5(H5Aread(attr, H5T_NATIVE_DOUBLE, &value), "read Time attribute");
    CHECK_H5(H5Aclose(attr), "close attr");
    CHECK_H5(H5Gclose(group), "close group");
    return value;
}

static void read_dataset_dims(hid_t file, const char *dataset_path, hsize_t dims[3]) {
    hid_t dataset = open_dataset(file, dataset_path);
    hid_t space = H5Dget_space(dataset);
    int ndims = H5Sget_simple_extent_ndims(space);
    if (ndims != 3) {
        fprintf(stderr, "Expected 3D dataset for %s, got %dD\n", dataset_path, ndims);
        exit(2);
    }
    CHECK_H5(H5Sget_simple_extent_dims(space, dims, NULL), "read dataset dims");
    CHECK_H5(H5Sclose(space), "close dataspace");
    CHECK_H5(H5Dclose(dataset), "close dataset");
}

static void read_vector(
    hid_t file,
    const char *dataset_path,
    const hsize_t start[3],
    const hsize_t count[3],
    hsize_t length,
    double *out
) {
    hid_t dataset = open_dataset(file, dataset_path);
    hid_t file_space = H5Dget_space(dataset);
    CHECK_H5(H5Sselect_hyperslab(file_space, H5S_SELECT_SET, start, NULL, count, NULL),
             "select vector hyperslab");
    hsize_t mem_dims[1] = {length};
    hid_t mem_space = H5Screate_simple(1, mem_dims, NULL);
    CHECK_H5(H5Dread(dataset, H5T_NATIVE_DOUBLE, mem_space, file_space, H5P_DEFAULT, out),
             "read vector");
    CHECK_H5(H5Sclose(mem_space), "close memory dataspace");
    CHECK_H5(H5Sclose(file_space), "close file dataspace");
    CHECK_H5(H5Dclose(dataset), "close dataset");
}

static void read_xz_slice(
    hid_t file,
    const char *dataset_path,
    hsize_t nz,
    hsize_t nx,
    hsize_t iy,
    double *out
) {
    hid_t dataset = open_dataset(file, dataset_path);
    hid_t file_space = H5Dget_space(dataset);
    hsize_t start[3] = {0, iy, 0};
    hsize_t count[3] = {nz, 1, nx};
    CHECK_H5(H5Sselect_hyperslab(file_space, H5S_SELECT_SET, start, NULL, count, NULL),
             "select XZ slice");
    hsize_t mem_dims[2] = {nz, nx};
    hid_t mem_space = H5Screate_simple(2, mem_dims, NULL);
    CHECK_H5(H5Dread(dataset, H5T_NATIVE_DOUBLE, mem_space, file_space, H5P_DEFAULT, out),
             "read XZ slice");
    CHECK_H5(H5Sclose(mem_space), "close memory dataspace");
    CHECK_H5(H5Sclose(file_space), "close file dataspace");
    CHECK_H5(H5Dclose(dataset), "close dataset");
}

static void derive_widths(const double *centres, hsize_t n, double *widths) {
    if (n == 1) {
        widths[0] = 1.0;
        return;
    }
    widths[0] = fabs(centres[1] - centres[0]);
    for (hsize_t i = 1; i + 1 < n; i++) {
        widths[i] = fabs(0.5 * (centres[i + 1] - centres[i - 1]));
    }
    widths[n - 1] = fabs(centres[n - 1] - centres[n - 2]);
}

static void init_bounds(Bounds *bounds) {
    bounds->cells = 0;
    bounds->x_min = bounds->y_min = bounds->z_min = DBL_MAX;
    bounds->x_max = bounds->y_max = bounds->z_max = -DBL_MAX;
    bounds->tracer_volume_kpc3 = 0.0;
}

static void add_bound_cell(Bounds *bounds, double x, double y, double z, double volume) {
    bounds->cells++;
    bounds->tracer_volume_kpc3 += volume;
    if (x < bounds->x_min) bounds->x_min = x;
    if (x > bounds->x_max) bounds->x_max = x;
    if (y < bounds->y_min) bounds->y_min = y;
    if (y > bounds->y_max) bounds->y_max = y;
    if (z < bounds->z_min) bounds->z_min = z;
    if (z > bounds->z_max) bounds->z_max = z;
}

static void init_shell(Shell *shell) {
    shell->cells = 0;
    shell->volume_kpc3 = 0.0;
    shell->pressure_volume_code = 0.0;
    shell->density_volume_code = 0.0;
    shell->radius_volume_kpc = 0.0;
}

static void add_shell_cell(Shell *shell, double volume, double pressure, double density, double radius) {
    shell->cells++;
    shell->volume_kpc3 += volume;
    shell->pressure_volume_code += pressure * volume;
    shell->density_volume_code += density * volume;
    shell->radius_volume_kpc += radius * volume;
}

static double shell_avg_pressure(const Shell *shell) {
    return shell->volume_kpc3 > 0.0 ? shell->pressure_volume_code / shell->volume_kpc3 : NAN;
}

static double shell_avg_density(const Shell *shell) {
    return shell->volume_kpc3 > 0.0 ? shell->density_volume_code / shell->volume_kpc3 : NAN;
}

static double shell_avg_radius(const Shell *shell) {
    return shell->volume_kpc3 > 0.0 ? shell->radius_volume_kpc / shell->volume_kpc3 : NAN;
}

static void write_ellipse_boundary(
    const char *path,
    const double cx[NSIDES],
    const double cz[NSIDES],
    const double ax[NSIDES],
    const double az[NSIDES]
) {
    FILE *f = fopen(path, "w");
    if (f == NULL) {
        perror(path);
        exit(2);
    }
    fprintf(f, "side\tx_kpc\tz_kpc\n");
    for (int s = 0; s < NSIDES; s++) {
        for (int i = 0; i <= 360; i++) {
            double theta = 2.0 * PI_VAL * (double)i / 360.0;
            fprintf(f, "%s\t%.17g\t%.17g\n",
                    SIDE_NAMES[s],
                    cx[s] + ax[s] * cos(theta),
                    cz[s] + az[s] * sin(theta));
        }
    }
    fclose(f);
}

int main(int argc, char **argv) {
    if (argc < 4 || argc > 9) {
        usage(argv[0]);
        return 2;
    }

    const char *input_path = argv[1];
    const char *timestep = argv[2];
    const char *output_dir = argv[3];
    double tracer_threshold = argc >= 5 ? strtod(argv[4], NULL) : 5.0e-3;
    double ambient_tracer_max = argc >= 6 ? strtod(argv[5], NULL) : 1.0e-3;
    double shell_inner = argc >= 7 ? strtod(argv[6], NULL) : 1.00;
    double shell_mid = argc >= 8 ? strtod(argv[7], NULL) : 1.15;
    double shell_outer = argc >= 9 ? strtod(argv[8], NULL) : 1.35;

    ensure_dir(output_dir);

    hid_t file = H5Fopen(input_path, H5F_ACC_RDONLY, H5P_DEFAULT);
    if (file < 0) {
        fprintf(stderr, "Could not open HDF5 file: %s\n", input_path);
        return 2;
    }

    char rho_path[512], prs_path[512], tr1_path[512];
    snprintf(rho_path, sizeof(rho_path), "/%s/vars/rho", timestep);
    snprintf(prs_path, sizeof(prs_path), "/%s/vars/prs", timestep);
    snprintf(tr1_path, sizeof(tr1_path), "/%s/vars/tr1", timestep);

    hsize_t dims[3];
    read_dataset_dims(file, tr1_path, dims);
    hsize_t nz = dims[0], ny = dims[1], nx = dims[2];
    hsize_t map_cells = nz * nx;

    double *x = (double *)malloc((size_t)nx * sizeof(double));
    double *y = (double *)malloc((size_t)ny * sizeof(double));
    double *z = (double *)malloc((size_t)nz * sizeof(double));
    double *dx = (double *)malloc((size_t)nx * sizeof(double));
    double *dy = (double *)malloc((size_t)ny * sizeof(double));
    double *dz = (double *)malloc((size_t)nz * sizeof(double));
    double *tr = (double *)malloc((size_t)map_cells * sizeof(double));
    double *rho = (double *)malloc((size_t)map_cells * sizeof(double));
    double *prs = (double *)malloc((size_t)map_cells * sizeof(double));
    if (!x || !y || !z || !dx || !dy || !dz || !tr || !rho || !prs) {
        fprintf(stderr, "Could not allocate cavity-stub buffers\n");
        return 2;
    }

    hsize_t x_start[3] = {0, 0, 0}, x_count[3] = {1, 1, nx};
    hsize_t y_start[3] = {0, 0, 0}, y_count[3] = {1, ny, 1};
    hsize_t z_start[3] = {0, 0, 0}, z_count[3] = {nz, 1, 1};
    read_vector(file, "/cell_coords/X", x_start, x_count, nx, x);
    read_vector(file, "/cell_coords/Y", y_start, y_count, ny, y);
    read_vector(file, "/cell_coords/Z", z_start, z_count, nz, z);
    derive_widths(x, nx, dx);
    derive_widths(y, ny, dy);
    derive_widths(z, nz, dz);

    Bounds bounds[NSIDES];
    for (int s = 0; s < NSIDES; s++) {
        init_bounds(&bounds[s]);
    }

    for (hsize_t iy = 0; iy < ny; iy++) {
        read_xz_slice(file, tr1_path, nz, nx, iy, tr);
        double cell_dy = dy[iy];
        for (hsize_t iz = 0; iz < nz; iz++) {
            int side = z[iz] < 0.0 ? 0 : 1;
            if (z[iz] == 0.0) {
                continue;
            }
            double cell_dz = dz[iz];
            for (hsize_t ix = 0; ix < nx; ix++) {
                hsize_t idx = iz * nx + ix;
                if (tr[idx] < tracer_threshold) {
                    continue;
                }
                double volume = dx[ix] * cell_dy * cell_dz;
                add_bound_cell(&bounds[side], x[ix], y[iy], z[iz], volume);
            }
        }
    }

    double cx[NSIDES], cy[NSIDES], cz[NSIDES], ax[NSIDES], ay[NSIDES], az[NSIDES];
    for (int s = 0; s < NSIDES; s++) {
        if (bounds[s].cells == 0) {
            fprintf(stderr, "No tracer-defined cells found for %s\n", SIDE_NAMES[s]);
            return 2;
        }
        cx[s] = 0.5 * (bounds[s].x_min + bounds[s].x_max);
        cy[s] = 0.5 * (bounds[s].y_min + bounds[s].y_max);
        cz[s] = 0.5 * (bounds[s].z_min + bounds[s].z_max);
        ax[s] = 0.5 * (bounds[s].x_max - bounds[s].x_min);
        ay[s] = 0.5 * (bounds[s].y_max - bounds[s].y_min);
        az[s] = 0.5 * (bounds[s].z_max - bounds[s].z_min);
    }

    Shell shell_inner_acc[NSIDES], shell_outer_acc[NSIDES], shell_total_acc[NSIDES];
    for (int s = 0; s < NSIDES; s++) {
        init_shell(&shell_inner_acc[s]);
        init_shell(&shell_outer_acc[s]);
        init_shell(&shell_total_acc[s]);
    }

    for (hsize_t iy = 0; iy < ny; iy++) {
        read_xz_slice(file, tr1_path, nz, nx, iy, tr);
        read_xz_slice(file, rho_path, nz, nx, iy, rho);
        read_xz_slice(file, prs_path, nz, nx, iy, prs);
        double cell_dy = dy[iy];
        for (hsize_t iz = 0; iz < nz; iz++) {
            if (z[iz] == 0.0) {
                continue;
            }
            int side = z[iz] < 0.0 ? 0 : 1;
            if (SIDE_SIGN[side] < 0 && z[iz] > 0.0) continue;
            if (SIDE_SIGN[side] > 0 && z[iz] < 0.0) continue;
            double cell_dz = dz[iz];
            for (hsize_t ix = 0; ix < nx; ix++) {
                hsize_t idx = iz * nx + ix;
                if (tr[idx] > ambient_tracer_max) {
                    continue;
                }
                double ex = (x[ix] - cx[side]) / ax[side];
                double ey = (y[iy] - cy[side]) / ay[side];
                double ez = (z[iz] - cz[side]) / az[side];
                double ell = sqrt(ex * ex + ey * ey + ez * ez);
                if (ell < shell_inner || ell > shell_outer) {
                    continue;
                }
                double volume = dx[ix] * cell_dy * cell_dz;
                double radius = sqrt(x[ix] * x[ix] + y[iy] * y[iy] + z[iz] * z[iz]);
                add_shell_cell(&shell_total_acc[side], volume, prs[idx], rho[idx], radius);
                if (ell <= shell_mid) {
                    add_shell_cell(&shell_inner_acc[side], volume, prs[idx], rho[idx], radius);
                } else {
                    add_shell_cell(&shell_outer_acc[side], volume, prs[idx], rho[idx], radius);
                }
            }
        }
    }

    double time_code = read_time_attr(file, timestep);
    CHECK_H5(H5Fclose(file), "close input file");

    char path[1024];
    join_path(path, sizeof(path), output_dir, "cavity_ellipse_boundary_0deg.tsv");
    write_ellipse_boundary(path, cx, cz, ax, az);

    double unit_pressure_cgs = UNIT_DENSITY_CGS * UNIT_VELOCITY_CMS * UNIT_VELOCITY_CMS;
    join_path(path, sizeof(path), output_dir, "cavity_stub_summary.csv");
    FILE *summary = fopen(path, "w");
    if (summary == NULL) {
        perror(path);
        return 2;
    }
    fprintf(summary,
            "side,time_myr,tracer_threshold,ambient_tracer_max,"
            "center_x_kpc,center_y_kpc,center_z_kpc,"
            "semi_x_kpc,semi_y_kpc,semi_z_kpc,"
            "projected_area_kpc2,ellipsoid_volume_kpc3,tracer_extent_volume_kpc3,"
            "ambient_shell_cells,ambient_shell_volume_kpc3,"
            "ambient_pressure_code,ambient_pressure_dyn_cm2,"
            "ambient_density_code,ambient_density_g_cm3,"
            "pV_erg,four_pV_erg,"
            "cavity_distance_kpc,sound_speed_km_s,"
            "sound_age_myr,gravity_hse_cm_s2,buoyancy_age_myr,refill_age_myr,"
            "inner_shell_pressure_code,outer_shell_pressure_code,"
            "inner_shell_radius_kpc,outer_shell_radius_kpc\n");

    for (int s = 0; s < NSIDES; s++) {
        double projected_area = PI_VAL * ax[s] * az[s];
        double ellipsoid_volume = (4.0 / 3.0) * PI_VAL * ax[s] * ay[s] * az[s];
        double ambient_p_code = shell_avg_pressure(&shell_total_acc[s]);
        double ambient_rho_code = shell_avg_density(&shell_total_acc[s]);
        double ambient_p_cgs = ambient_p_code * unit_pressure_cgs;
        double ambient_rho_cgs = ambient_rho_code * UNIT_DENSITY_CGS;
        double pV = ambient_p_cgs * ellipsoid_volume * pow(KPC_CM, 3.0);
        double four_pV = 4.0 * pV;
        double distance_kpc = sqrt(cx[s] * cx[s] + cy[s] * cy[s] + cz[s] * cz[s]);
        double sound_speed = sqrt(GAMMA_GAS * ambient_p_cgs / ambient_rho_cgs);
        double sound_age = (distance_kpc * KPC_CM) / sound_speed / SECONDS_PER_MYR;

        double p_inner = shell_avg_pressure(&shell_inner_acc[s]);
        double p_outer = shell_avg_pressure(&shell_outer_acc[s]);
        double r_inner = shell_avg_radius(&shell_inner_acc[s]);
        double r_outer = shell_avg_radius(&shell_outer_acc[s]);
        double rho_grad = 0.5 * (shell_avg_density(&shell_inner_acc[s]) +
                                 shell_avg_density(&shell_outer_acc[s])) * UNIT_DENSITY_CGS;
        double g_hse = NAN;
        if (isfinite(p_inner) && isfinite(p_outer) && isfinite(r_inner) &&
            isfinite(r_outer) && fabs(r_outer - r_inner) > 0.0 && rho_grad > 0.0) {
            double dpdr = fabs((p_outer - p_inner) * unit_pressure_cgs /
                               ((r_outer - r_inner) * KPC_CM));
            g_hse = dpdr / rho_grad;
        }

        double buoyancy_age = NAN;
        double refill_age = NAN;
        if (isfinite(g_hse) && g_hse > 0.0) {
            double volume_cm3 = ellipsoid_volume * pow(KPC_CM, 3.0);
            double area_cm2 = PI_VAL * ax[s] * ay[s] * KPC_CM * KPC_CM;
            double terminal_velocity = sqrt(2.0 * g_hse * volume_cm3 / (DRAG_COEFF * area_cm2));
            double r_eff_cm = pow(3.0 * volume_cm3 / (4.0 * PI_VAL), 1.0 / 3.0);
            buoyancy_age = (distance_kpc * KPC_CM) / terminal_velocity / SECONDS_PER_MYR;
            refill_age = 2.0 * sqrt(r_eff_cm / g_hse) / SECONDS_PER_MYR;
        }

        fprintf(summary,
                "%s,%.10f,%.17g,%.17g,"
                "%.17g,%.17g,%.17g,"
                "%.17g,%.17g,%.17g,"
                "%.17g,%.17g,%.17g,"
                "%llu,%.17g,"
                "%.17g,%.17e,"
                "%.17g,%.17e,"
                "%.17e,%.17e,"
                "%.17g,%.17g,"
                "%.17g,%.17e,%.17g,%.17g,"
                "%.17g,%.17g,"
                "%.17g,%.17g\n",
                SIDE_NAMES[s],
                time_code / CODE_TIME_PER_MYR,
                tracer_threshold,
                ambient_tracer_max,
                cx[s], cy[s], cz[s],
                ax[s], ay[s], az[s],
                projected_area,
                ellipsoid_volume,
                bounds[s].tracer_volume_kpc3,
                shell_total_acc[s].cells,
                shell_total_acc[s].volume_kpc3,
                ambient_p_code,
                ambient_p_cgs,
                ambient_rho_code,
                ambient_rho_cgs,
                pV,
                four_pV,
                distance_kpc,
                sound_speed / 1.0e5,
                sound_age,
                g_hse,
                buoyancy_age,
                refill_age,
                p_inner,
                p_outer,
                r_inner,
                r_outer);
    }
    fclose(summary);

    join_path(path, sizeof(path), output_dir, "cavity_stub_metadata.txt");
    FILE *meta = fopen(path, "w");
    if (meta == NULL) {
        perror(path);
        return 2;
    }
    fprintf(meta, "input_h5=%s\n", input_path);
    fprintf(meta, "timestep=%s\n", timestep);
    fprintf(meta, "time_code=%.17g\n", time_code);
    fprintf(meta, "time_myr=%.17g\n", time_code / CODE_TIME_PER_MYR);
    fprintf(meta, "grid_shape_nz_ny_nx=%llu,%llu,%llu\n",
            (unsigned long long)nz, (unsigned long long)ny, (unsigned long long)nx);
    fprintf(meta, "geometry=one_ellipsoid_per_lobe_from_3d_tracer_extent\n");
    fprintf(meta, "ambient_shell=ellipsoidal_radius_%.2f_to_%.2f_same_side_tracer_le_%.4g\n",
            shell_inner, shell_outer, ambient_tracer_max);
    fprintf(meta, "age_gravity=hydrostatic_proxy_from_inner_outer_ambient_shell_pressure_gradient\n");
    fprintf(meta, "drag_coefficient=%.17g\n", DRAG_COEFF);
    fclose(meta);

    free(x);
    free(y);
    free(z);
    free(dx);
    free(dy);
    free(dz);
    free(tr);
    free(rho);
    free(prs);

    return 0;
}
