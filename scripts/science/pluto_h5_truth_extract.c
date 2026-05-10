/*
 * Extract first-pass truth diagnostics from a PLUTO static-grid HDF5 file.
 *
 * This serial HDF5 helper is intended for compute-node use on full 3D outputs.
 * It computes Level 1 injected-energy accounting and Level 2 tracer-mask lobe
 * volume/energy summaries without requiring h5py on the cluster.
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

#define N_THRESHOLDS 3
#define N_SIDES 3

static const double CODE_TIME_PER_MYR = 306.6013937879523;
static const double SECONDS_PER_MYR = 3.15576e13;
static const double GAMMA_GAS = 5.0 / 3.0;
static const double UNIT_DENSITY_CGS = 1.0023678e-24;
static const double UNIT_LENGTH_CM = 3.0856775814913673e21;
static const double UNIT_VELOCITY_CMS = 2.99792458e10;

typedef struct {
    unsigned long long cells;
    double volume;
    double tracer_weighted_volume;
    double mass;
    double thermal;
    double kinetic;
    double x_min, x_max;
    double y_min, y_max;
    double z_min, z_max;
} Accumulator;

static void usage(const char *prog) {
    fprintf(stderr,
            "Usage: %s <input.h5> <timestep-name> <output-dir> [jet_power_erg_s] [active_time_myr]\n",
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

static void read_dataset_dims(hid_t file, const char *dataset_path, hsize_t dims[3]) {
    hid_t dataset = open_dataset(file, dataset_path);
    hid_t space = H5Dget_space(dataset);
    if (space < 0) {
        fprintf(stderr, "Could not get dataspace for %s\n", dataset_path);
        exit(2);
    }
    int ndims = H5Sget_simple_extent_ndims(space);
    if (ndims != 3) {
        fprintf(stderr, "Expected 3D dataset for %s, got %dD\n", dataset_path, ndims);
        exit(2);
    }
    CHECK_H5(H5Sget_simple_extent_dims(space, dims, NULL), "read dataset dims");
    CHECK_H5(H5Sclose(space), "close dataspace");
    CHECK_H5(H5Dclose(dataset), "close dataset");
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

static void read_full_dataset(hid_t file, const char *dataset_path, double *out) {
    hid_t dataset = open_dataset(file, dataset_path);
    CHECK_H5(H5Dread(dataset, H5T_NATIVE_DOUBLE, H5S_ALL, H5S_ALL, H5P_DEFAULT, out),
             "read full dataset");
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

static void init_accumulator(Accumulator *acc) {
    acc->cells = 0;
    acc->volume = 0.0;
    acc->tracer_weighted_volume = 0.0;
    acc->mass = 0.0;
    acc->thermal = 0.0;
    acc->kinetic = 0.0;
    acc->x_min = acc->y_min = acc->z_min = DBL_MAX;
    acc->x_max = acc->y_max = acc->z_max = -DBL_MAX;
}

static void add_cell(
    Accumulator *acc,
    double x,
    double y,
    double z,
    double volume,
    double tracer,
    double rho,
    double prs,
    double vx1,
    double vx2,
    double vx3
) {
    double v2 = vx1 * vx1 + vx2 * vx2 + vx3 * vx3;
    acc->cells++;
    acc->volume += volume;
    acc->tracer_weighted_volume += tracer * volume;
    acc->mass += rho * volume;
    acc->thermal += prs * volume / (GAMMA_GAS - 1.0);
    acc->kinetic += 0.5 * rho * v2 * volume;
    if (x < acc->x_min) acc->x_min = x;
    if (x > acc->x_max) acc->x_max = x;
    if (y < acc->y_min) acc->y_min = y;
    if (y > acc->y_max) acc->y_max = y;
    if (z < acc->z_min) acc->z_min = z;
    if (z > acc->z_max) acc->z_max = z;
}

static void write_level1(
    const char *path,
    double time_code,
    double jet_power_erg_s,
    double active_time_myr
) {
    double time_myr = time_code / CODE_TIME_PER_MYR;
    double active_so_far_myr = time_myr < active_time_myr ? time_myr : active_time_myr;
    double one_sided_erg = jet_power_erg_s * active_so_far_myr * SECONDS_PER_MYR;
    double bipolar_erg = 2.0 * one_sided_erg;
    double one_sided_full_erg = jet_power_erg_s * active_time_myr * SECONDS_PER_MYR;
    double bipolar_full_erg = 2.0 * one_sided_full_erg;

    FILE *f = fopen(path, "w");
    if (f == NULL) {
        perror(path);
        exit(2);
    }
    fprintf(f, "metric,value,unit\n");
    fprintf(f, "time_code,%.17g,code_time\n", time_code);
    fprintf(f, "time_myr,%.17g,Myr\n", time_myr);
    fprintf(f, "jet_power_one_sided,%.17g,erg/s\n", jet_power_erg_s);
    fprintf(f, "active_time_configured,%.17g,Myr\n", active_time_myr);
    fprintf(f, "active_time_elapsed,%.17g,Myr\n", active_so_far_myr);
    fprintf(f, "injected_energy_one_sided_elapsed,%.17e,erg\n", one_sided_erg);
    fprintf(f, "injected_energy_bipolar_elapsed,%.17e,erg\n", bipolar_erg);
    fprintf(f, "injected_energy_one_sided_full_active_time,%.17e,erg\n", one_sided_full_erg);
    fprintf(f, "injected_energy_bipolar_full_active_time,%.17e,erg\n", bipolar_full_erg);
    fclose(f);
}

static void write_level2(
    const char *path,
    Accumulator acc[N_THRESHOLDS][N_SIDES],
    const double thresholds[N_THRESHOLDS],
    double time_code
) {
    const char *side_names[N_SIDES] = {"negative_z", "positive_z", "bipolar_total"};
    double unit_volume_cm3 = pow(UNIT_LENGTH_CM, 3.0);
    double unit_pressure = UNIT_DENSITY_CGS * UNIT_VELOCITY_CMS * UNIT_VELOCITY_CMS;
    double unit_energy = unit_pressure * unit_volume_cm3;
    double unit_mass = UNIT_DENSITY_CGS * unit_volume_cm3;
    double time_myr = time_code / CODE_TIME_PER_MYR;

    FILE *f = fopen(path, "w");
    if (f == NULL) {
        perror(path);
        exit(2);
    }
    fprintf(f,
            "threshold,side,time_myr,cell_count,volume_kpc3,tracer_weighted_volume_kpc3,"
            "mass_code,mass_g,thermal_energy_code,kinetic_energy_code,total_energy_code,"
            "thermal_energy_erg,kinetic_energy_erg,total_energy_erg,"
            "x_min_kpc,x_max_kpc,y_min_kpc,y_max_kpc,z_min_kpc,z_max_kpc\n");
    for (int t = 0; t < N_THRESHOLDS; t++) {
        for (int s = 0; s < N_SIDES; s++) {
            Accumulator *a = &acc[t][s];
            double total_code = a->thermal + a->kinetic;
            if (a->cells == 0) {
                fprintf(f,
                        "%.0e,%s,%.8f,0,0,0,0,0,0,0,0,0,0,0,,,,,,\n",
                        thresholds[t], side_names[s], time_myr);
            } else {
                fprintf(f,
                        "%.0e,%s,%.8f,%llu,%.17g,%.17g,%.17g,%.17e,"
                        "%.17g,%.17g,%.17g,%.17e,%.17e,%.17e,"
                        "%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n",
                        thresholds[t],
                        side_names[s],
                        time_myr,
                        a->cells,
                        a->volume,
                        a->tracer_weighted_volume,
                        a->mass,
                        a->mass * unit_mass,
                        a->thermal,
                        a->kinetic,
                        total_code,
                        a->thermal * unit_energy,
                        a->kinetic * unit_energy,
                        total_code * unit_energy,
                        a->x_min,
                        a->x_max,
                        a->y_min,
                        a->y_max,
                        a->z_min,
                        a->z_max);
            }
        }
    }
    fclose(f);
}

int main(int argc, char **argv) {
    if (argc < 4 || argc > 6) {
        usage(argv[0]);
        return 2;
    }

    const char *input_path = argv[1];
    const char *timestep = argv[2];
    const char *output_dir = argv[3];
    double jet_power_erg_s = argc >= 5 ? strtod(argv[4], NULL) : 1.0e45;
    double active_time_myr = argc >= 6 ? strtod(argv[5], NULL) : 50.0;
    ensure_dir(output_dir);

    hid_t file = H5Fopen(input_path, H5F_ACC_RDONLY, H5P_DEFAULT);
    if (file < 0) {
        fprintf(stderr, "Could not open HDF5 file: %s\n", input_path);
        return 2;
    }

    char rho_path[512], prs_path[512], tr1_path[512], vx1_path[512], vx2_path[512], vx3_path[512];
    snprintf(rho_path, sizeof(rho_path), "/%s/vars/rho", timestep);
    snprintf(prs_path, sizeof(prs_path), "/%s/vars/prs", timestep);
    snprintf(tr1_path, sizeof(tr1_path), "/%s/vars/tr1", timestep);
    snprintf(vx1_path, sizeof(vx1_path), "/%s/vars/vx1", timestep);
    snprintf(vx2_path, sizeof(vx2_path), "/%s/vars/vx2", timestep);
    snprintf(vx3_path, sizeof(vx3_path), "/%s/vars/vx3", timestep);

    hsize_t dims[3];
    read_dataset_dims(file, rho_path, dims);
    hsize_t nz = dims[0], ny = dims[1], nx = dims[2];
    hsize_t ncell = nz * ny * nx;
    hsize_t iy0 = ny / 2;
    hsize_t ix0 = nx / 2;

    double time_code = read_time_attr(file, timestep);

    double *x = (double *)malloc((size_t)nx * sizeof(double));
    double *y = (double *)malloc((size_t)ny * sizeof(double));
    double *z = (double *)malloc((size_t)nz * sizeof(double));
    double *dx = (double *)malloc((size_t)nx * sizeof(double));
    double *dy = (double *)malloc((size_t)ny * sizeof(double));
    double *dz = (double *)malloc((size_t)nz * sizeof(double));
    if (!x || !y || !z || !dx || !dy || !dz) {
        fprintf(stderr, "Coordinate allocation failed\n");
        return 2;
    }

    hsize_t x_start[3] = {0, iy0, 0}, x_count[3] = {1, 1, nx};
    hsize_t y_start[3] = {0, 0, ix0}, y_count[3] = {1, ny, 1};
    hsize_t z_start[3] = {0, iy0, ix0}, z_count[3] = {nz, 1, 1};
    read_vector(file, "/cell_coords/X", x_start, x_count, nx, x);
    read_vector(file, "/cell_coords/Y", y_start, y_count, ny, y);
    read_vector(file, "/cell_coords/Z", z_start, z_count, nz, z);
    derive_widths(x, nx, dx);
    derive_widths(y, ny, dy);
    derive_widths(z, nz, dz);

    double *rho = (double *)malloc((size_t)ncell * sizeof(double));
    double *prs = (double *)malloc((size_t)ncell * sizeof(double));
    double *tr1 = (double *)malloc((size_t)ncell * sizeof(double));
    double *vx1 = (double *)malloc((size_t)ncell * sizeof(double));
    double *vx2 = (double *)malloc((size_t)ncell * sizeof(double));
    double *vx3 = (double *)malloc((size_t)ncell * sizeof(double));
    if (!rho || !prs || !tr1 || !vx1 || !vx2 || !vx3) {
        fprintf(stderr, "Field allocation failed for %llu cells\n", (unsigned long long)ncell);
        return 2;
    }

    read_full_dataset(file, rho_path, rho);
    read_full_dataset(file, prs_path, prs);
    read_full_dataset(file, tr1_path, tr1);
    read_full_dataset(file, vx1_path, vx1);
    read_full_dataset(file, vx2_path, vx2);
    read_full_dataset(file, vx3_path, vx3);

    const double thresholds[N_THRESHOLDS] = {1.0e-3, 5.0e-3, 1.0e-2};
    Accumulator acc[N_THRESHOLDS][N_SIDES];
    for (int t = 0; t < N_THRESHOLDS; t++) {
        for (int s = 0; s < N_SIDES; s++) {
            init_accumulator(&acc[t][s]);
        }
    }

    for (hsize_t iz = 0; iz < nz; iz++) {
        for (hsize_t iy = 0; iy < ny; iy++) {
            double yz_volume = dy[iy] * dz[iz];
            for (hsize_t ix = 0; ix < nx; ix++) {
                hsize_t idx = (iz * ny + iy) * nx + ix;
                double cell_volume = dx[ix] * yz_volume;
                int z_side = z[iz] < 0.0 ? 0 : 1;
                for (int t = 0; t < N_THRESHOLDS; t++) {
                    if (tr1[idx] > thresholds[t]) {
                        add_cell(&acc[t][z_side], x[ix], y[iy], z[iz], cell_volume, tr1[idx],
                                 rho[idx], prs[idx], vx1[idx], vx2[idx], vx3[idx]);
                        add_cell(&acc[t][2], x[ix], y[iy], z[iz], cell_volume, tr1[idx],
                                 rho[idx], prs[idx], vx1[idx], vx2[idx], vx3[idx]);
                    }
                }
            }
        }
    }

    char path[1024];
    join_path(path, sizeof(path), output_dir, "level1_injected_energy.csv");
    write_level1(path, time_code, jet_power_erg_s, active_time_myr);
    join_path(path, sizeof(path), output_dir, "level2_tracer_lobe_truth.csv");
    write_level2(path, acc, thresholds, time_code);

    join_path(path, sizeof(path), output_dir, "truth_metadata.txt");
    FILE *meta = fopen(path, "w");
    if (meta == NULL) {
        perror(path);
        return 2;
    }
    fprintf(meta, "input_h5=%s\n", input_path);
    fprintf(meta, "timestep=%s\n", timestep);
    fprintf(meta, "time_code=%.17g\n", time_code);
    fprintf(meta, "time_myr=%.17g\n", time_code / CODE_TIME_PER_MYR);
    fprintf(meta, "shape_nz_ny_nx=%llu,%llu,%llu\n",
            (unsigned long long)nz, (unsigned long long)ny, (unsigned long long)nx);
    fprintf(meta, "jet_power_erg_s=%.17g\n", jet_power_erg_s);
    fprintf(meta, "active_time_myr=%.17g\n", active_time_myr);
    fprintf(meta, "unit_density_cgs=%.17g\n", UNIT_DENSITY_CGS);
    fprintf(meta, "unit_length_cm=%.17g\n", UNIT_LENGTH_CM);
    fprintf(meta, "unit_velocity_cm_s=%.17g\n", UNIT_VELOCITY_CMS);
    fprintf(meta, "unit_pressure_barye=%.17g\n", UNIT_DENSITY_CGS * UNIT_VELOCITY_CMS * UNIT_VELOCITY_CMS);
    fprintf(meta, "unit_energy_erg=%.17g\n",
            UNIT_DENSITY_CGS * UNIT_VELOCITY_CMS * UNIT_VELOCITY_CMS * pow(UNIT_LENGTH_CM, 3.0));
    fclose(meta);

    free(x);
    free(y);
    free(z);
    free(dx);
    free(dy);
    free(dz);
    free(rho);
    free(prs);
    free(tr1);
    free(vx1);
    free(vx2);
    free(vx3);
    CHECK_H5(H5Fclose(file), "close file");
    printf("Extracted truth diagnostics to %s\n", output_dir);
    return 0;
}
