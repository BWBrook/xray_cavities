/*
 * Extract lightweight quick-look products from a PLUTO static-grid HDF5 file.
 *
 * This is intentionally a small serial HDF5 program so it can run on a Kunanyi
 * compute node without requiring a private Python/numpy/h5py stack.
 */

#include <float.h>
#include <hdf5.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>

#define CHECK_H5(call, message)                                                   \
    do {                                                                          \
        if ((call) < 0) {                                                         \
            fprintf(stderr, "HDF5 error: %s\n", (message));                    \
            exit(2);                                                              \
        }                                                                         \
    } while (0)

static void usage(const char *prog) {
    fprintf(stderr, "Usage: %s <input.h5> <timestep-name> <output-dir>\n", prog);
    fprintf(stderr, "Example: %s data.0001.flt.h5 Timestep_1 quicklook\n", prog);
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

static void read_xz_slice(
    hid_t file,
    const char *dataset_path,
    hsize_t nz,
    hsize_t ny,
    hsize_t nx,
    hsize_t iy,
    double *out
) {
    (void)ny;
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

static void read_axis_profile(
    hid_t file,
    const char *dataset_path,
    hsize_t nz,
    hsize_t iy,
    hsize_t ix,
    double *out
) {
    hid_t dataset = open_dataset(file, dataset_path);
    hid_t file_space = H5Dget_space(dataset);
    hsize_t start[3] = {0, iy, ix};
    hsize_t count[3] = {nz, 1, 1};
    CHECK_H5(H5Sselect_hyperslab(file_space, H5S_SELECT_SET, start, NULL, count, NULL),
             "select axis profile");
    hsize_t mem_dims[1] = {nz};
    hid_t mem_space = H5Screate_simple(1, mem_dims, NULL);
    CHECK_H5(H5Dread(dataset, H5T_NATIVE_DOUBLE, mem_space, file_space, H5P_DEFAULT, out),
             "read axis profile");
    CHECK_H5(H5Sclose(mem_space), "close memory dataspace");
    CHECK_H5(H5Sclose(file_space), "close file dataspace");
    CHECK_H5(H5Dclose(dataset), "close dataset");
}

static void write_vector_tsv(const char *path, const double *values, hsize_t n) {
    FILE *f = fopen(path, "w");
    if (f == NULL) {
        perror(path);
        exit(2);
    }
    for (hsize_t i = 0; i < n; i++) {
        fprintf(f, "%.17g\n", values[i]);
    }
    fclose(f);
}

static void write_matrix_tsv(const char *path, const double *values, hsize_t rows, hsize_t cols) {
    FILE *f = fopen(path, "w");
    if (f == NULL) {
        perror(path);
        exit(2);
    }
    for (hsize_t i = 0; i < rows; i++) {
        for (hsize_t j = 0; j < cols; j++) {
            if (j > 0) {
                fputc('\t', f);
            }
            fprintf(f, "%.9g", values[i * cols + j]);
        }
        fputc('\n', f);
    }
    fclose(f);
}

static void write_axis_profile_tsv(
    const char *path,
    const double *z,
    const double *rho,
    const double *prs,
    const double *tr1,
    const double *vx3,
    hsize_t n
) {
    FILE *f = fopen(path, "w");
    if (f == NULL) {
        perror(path);
        exit(2);
    }
    fprintf(f, "z\trho\tprs\ttr1\tvx3\n");
    for (hsize_t i = 0; i < n; i++) {
        fprintf(f, "%.17g\t%.17g\t%.17g\t%.17g\t%.17g\n", z[i], rho[i], prs[i], tr1[i], vx3[i]);
    }
    fclose(f);
}

static void summarize_full_tracer(
    hid_t file,
    const char *dataset_path,
    const double *x,
    const double *y,
    const double *z,
    hsize_t nz,
    hsize_t ny,
    hsize_t nx,
    const char *summary_path,
    double time_value
) {
    hsize_t ncell = nz * ny * nx;
    double *tr = (double *)malloc((size_t)ncell * sizeof(double));
    if (tr == NULL) {
        fprintf(stderr, "Could not allocate tracer buffer for %llu cells\n",
                (unsigned long long)ncell);
        exit(2);
    }

    hid_t dataset = open_dataset(file, dataset_path);
    CHECK_H5(H5Dread(dataset, H5T_NATIVE_DOUBLE, H5S_ALL, H5S_ALL, H5P_DEFAULT, tr),
             "read full tracer");
    CHECK_H5(H5Dclose(dataset), "close tracer dataset");

    const double thresholds[3] = {1.0e-3, 5.0e-3, 1.0e-2};
    unsigned long long counts[3] = {0, 0, 0};
    double min_x[3], max_x[3], min_y[3], max_y[3], min_z[3], max_z[3];
    for (int t = 0; t < 3; t++) {
        min_x[t] = min_y[t] = min_z[t] = DBL_MAX;
        max_x[t] = max_y[t] = max_z[t] = -DBL_MAX;
    }

    double tr_min = DBL_MAX;
    double tr_max = -DBL_MAX;
    double tr_sum = 0.0;

    for (hsize_t iz = 0; iz < nz; iz++) {
        for (hsize_t iy = 0; iy < ny; iy++) {
            for (hsize_t ix = 0; ix < nx; ix++) {
                hsize_t idx = (iz * ny + iy) * nx + ix;
                double value = tr[idx];
                if (value < tr_min) {
                    tr_min = value;
                }
                if (value > tr_max) {
                    tr_max = value;
                }
                tr_sum += value;
                for (int t = 0; t < 3; t++) {
                    if (value > thresholds[t]) {
                        counts[t]++;
                        if (x[ix] < min_x[t]) min_x[t] = x[ix];
                        if (x[ix] > max_x[t]) max_x[t] = x[ix];
                        if (y[iy] < min_y[t]) min_y[t] = y[iy];
                        if (y[iy] > max_y[t]) max_y[t] = y[iy];
                        if (z[iz] < min_z[t]) min_z[t] = z[iz];
                        if (z[iz] > max_z[t]) max_z[t] = z[iz];
                    }
                }
            }
        }
    }

    FILE *f = fopen(summary_path, "w");
    if (f == NULL) {
        perror(summary_path);
        exit(2);
    }
    fprintf(f, "metric,value\n");
    fprintf(f, "time_code,%.17g\n", time_value);
    fprintf(f, "nz,%llu\n", (unsigned long long)nz);
    fprintf(f, "ny,%llu\n", (unsigned long long)ny);
    fprintf(f, "nx,%llu\n", (unsigned long long)nx);
    fprintf(f, "tracer_min,%.17g\n", tr_min);
    fprintf(f, "tracer_max,%.17g\n", tr_max);
    fprintf(f, "tracer_mean,%.17g\n", tr_sum / (double)ncell);
    for (int t = 0; t < 3; t++) {
        fprintf(f, "tracer_cells_gt_%.0e,%llu\n", thresholds[t], counts[t]);
        if (counts[t] > 0) {
            fprintf(f, "tracer_x_min_gt_%.0e,%.17g\n", thresholds[t], min_x[t]);
            fprintf(f, "tracer_x_max_gt_%.0e,%.17g\n", thresholds[t], max_x[t]);
            fprintf(f, "tracer_y_min_gt_%.0e,%.17g\n", thresholds[t], min_y[t]);
            fprintf(f, "tracer_y_max_gt_%.0e,%.17g\n", thresholds[t], max_y[t]);
            fprintf(f, "tracer_z_min_gt_%.0e,%.17g\n", thresholds[t], min_z[t]);
            fprintf(f, "tracer_z_max_gt_%.0e,%.17g\n", thresholds[t], max_z[t]);
        }
    }
    fclose(f);
    free(tr);
}

int main(int argc, char **argv) {
    if (argc != 4) {
        usage(argv[0]);
        return 2;
    }

    const char *input_path = argv[1];
    const char *timestep = argv[2];
    const char *output_dir = argv[3];
    ensure_dir(output_dir);

    hid_t file = H5Fopen(input_path, H5F_ACC_RDONLY, H5P_DEFAULT);
    if (file < 0) {
        fprintf(stderr, "Could not open HDF5 file: %s\n", input_path);
        return 2;
    }

    char rho_path[512], prs_path[512], tr1_path[512], vx3_path[512];
    snprintf(rho_path, sizeof(rho_path), "/%s/vars/rho", timestep);
    snprintf(prs_path, sizeof(prs_path), "/%s/vars/prs", timestep);
    snprintf(tr1_path, sizeof(tr1_path), "/%s/vars/tr1", timestep);
    snprintf(vx3_path, sizeof(vx3_path), "/%s/vars/vx3", timestep);

    hsize_t dims[3];
    read_dataset_dims(file, rho_path, dims);
    hsize_t nz = dims[0], ny = dims[1], nx = dims[2];
    hsize_t iz0 = nz / 2;
    hsize_t iy0 = ny / 2;
    hsize_t ix0 = nx / 2;
    (void)iz0;

    double time_value = read_time_attr(file, timestep);

    double *x = (double *)malloc((size_t)nx * sizeof(double));
    double *y = (double *)malloc((size_t)ny * sizeof(double));
    double *z = (double *)malloc((size_t)nz * sizeof(double));
    if (x == NULL || y == NULL || z == NULL) {
        fprintf(stderr, "Coordinate allocation failed\n");
        return 2;
    }

    hsize_t x_start[3] = {0, iy0, 0}, x_count[3] = {1, 1, nx};
    hsize_t y_start[3] = {0, 0, ix0}, y_count[3] = {1, ny, 1};
    hsize_t z_start[3] = {0, iy0, ix0}, z_count[3] = {nz, 1, 1};
    read_vector(file, "/cell_coords/X", x_start, x_count, nx, x);
    read_vector(file, "/cell_coords/Y", y_start, y_count, ny, y);
    read_vector(file, "/cell_coords/Z", z_start, z_count, nz, z);

    char path[1024];
    join_path(path, sizeof(path), output_dir, "x_centres.tsv");
    write_vector_tsv(path, x, nx);
    join_path(path, sizeof(path), output_dir, "y_centres.tsv");
    write_vector_tsv(path, y, ny);
    join_path(path, sizeof(path), output_dir, "z_centres.tsv");
    write_vector_tsv(path, z, nz);

    double *slice = (double *)malloc((size_t)nz * (size_t)nx * sizeof(double));
    if (slice == NULL) {
        fprintf(stderr, "Slice allocation failed\n");
        return 2;
    }

    const char *slice_names[4] = {"rho", "prs", "tr1", "vx3"};
    const char *slice_paths[4] = {rho_path, prs_path, tr1_path, vx3_path};
    for (int i = 0; i < 4; i++) {
        read_xz_slice(file, slice_paths[i], nz, ny, nx, iy0, slice);
        char name[128];
        snprintf(name, sizeof(name), "slice_xz_%s.tsv", slice_names[i]);
        join_path(path, sizeof(path), output_dir, name);
        write_matrix_tsv(path, slice, nz, nx);
    }
    free(slice);

    double *rho_axis = (double *)malloc((size_t)nz * sizeof(double));
    double *prs_axis = (double *)malloc((size_t)nz * sizeof(double));
    double *tr1_axis = (double *)malloc((size_t)nz * sizeof(double));
    double *vx3_axis = (double *)malloc((size_t)nz * sizeof(double));
    if (rho_axis == NULL || prs_axis == NULL || tr1_axis == NULL || vx3_axis == NULL) {
        fprintf(stderr, "Axis allocation failed\n");
        return 2;
    }

    read_axis_profile(file, rho_path, nz, iy0, ix0, rho_axis);
    read_axis_profile(file, prs_path, nz, iy0, ix0, prs_axis);
    read_axis_profile(file, tr1_path, nz, iy0, ix0, tr1_axis);
    read_axis_profile(file, vx3_path, nz, iy0, ix0, vx3_axis);
    join_path(path, sizeof(path), output_dir, "axis_profile_z.tsv");
    write_axis_profile_tsv(path, z, rho_axis, prs_axis, tr1_axis, vx3_axis, nz);

    join_path(path, sizeof(path), output_dir, "summary_metrics.csv");
    summarize_full_tracer(file, tr1_path, x, y, z, nz, ny, nx, path, time_value);

    join_path(path, sizeof(path), output_dir, "metadata.txt");
    FILE *meta = fopen(path, "w");
    if (meta == NULL) {
        perror(path);
        return 2;
    }
    fprintf(meta, "input_h5=%s\n", input_path);
    fprintf(meta, "timestep=%s\n", timestep);
    fprintf(meta, "time_code=%.17g\n", time_value);
    fprintf(meta, "shape_nz_ny_nx=%llu,%llu,%llu\n",
            (unsigned long long)nz, (unsigned long long)ny, (unsigned long long)nx);
    fprintf(meta, "ix0=%llu\n", (unsigned long long)ix0);
    fprintf(meta, "iy0=%llu\n", (unsigned long long)iy0);
    fclose(meta);

    free(x);
    free(y);
    free(z);
    free(rho_axis);
    free(prs_axis);
    free(tr1_axis);
    free(vx3_axis);
    CHECK_H5(H5Fclose(file), "close file");
    printf("Extracted quick-look products to %s\n", output_dir);
    return 0;
}
