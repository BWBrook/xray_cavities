/*
 * Extract a compact 5 Myr, 0 degree observable smoke product from a PLUTO
 * static-grid HDF5 output plus the nearest PLUTO particle output.
 *
 * This is a bridge diagnostic for Kunanyi, where the full Python GRAiLE/XRAiSE
 * stack is not yet available. The X-ray grid calculation ports the supplied
 * XRAiSE thermal bremsstrahlung expression before the APEC/Gaunt correction
 * stage. The radio map ports the pressure/tracer scaling used by plutokore's
 * 3D surface-brightness helper. Treat these as smoke products, not final
 * science observables.
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

#define MAX_FIELDS 64
#define MAX_TOKENS 128

static const double CODE_TIME_PER_MYR = 306.6013937879523;
static const double KPC_M = 3.0856775814913673e19;
static const double C_LIGHT = 2.99792458e8;
static const double UNIT_DENSITY_SI = 1.0023678e-21;
static const double UNIT_PRESSURE_SI = 1.0023678e-21 * 2.99792458e8 * 2.99792458e8;
static const double XRAISE_XRAY_FREQ_HZ = 2.417990504024e17;
static const double RADIO_FREQ_HZ = 1.5e8;
static const double TRACER_THRESHOLD = 5.0e-3;
static const double MU = 0.60364;
static const double PI_VAL = 3.141592653589793238462643383279502884;

typedef struct {
    char name[64];
    int dim;
    int offset;
} FieldInfo;

typedef struct {
    long nparticles;
    double time_code;
    char endianity[32];
    int nfields;
    int total_dim;
    FieldInfo fields[MAX_FIELDS];
} ParticleHeader;

typedef struct {
    double min;
    double max;
    double sum;
    unsigned long long positive;
} MapStats;

static void usage(const char *prog) {
    fprintf(stderr,
            "Usage: %s <input.h5> <timestep-name> <particle.dbl> <output-dir> [redshift] [view_angle_deg]\n",
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
            fprintf(f, "%.9e", values[i * cols + j]);
        }
        fputc('\n', f);
    }
    fclose(f);
}

static void stats_init(MapStats *stats) {
    stats->min = DBL_MAX;
    stats->max = -DBL_MAX;
    stats->sum = 0.0;
    stats->positive = 0;
}

static void stats_add(MapStats *stats, double value) {
    if (value < stats->min) stats->min = value;
    if (value > stats->max) stats->max = value;
    stats->sum += value;
    if (value > 0.0) stats->positive++;
}

static double xraise_temperature_k(double pressure_si, double density_si) {
    const double mp = 1.6726e-27;
    const double kb = 1.380649e-23;
    if (pressure_si <= 0.0 || density_si <= 0.0) {
        return NAN;
    }
    return (pressure_si / density_si) * ((MU * mp) / kb);
}

static double xraise_grid_bremsstrahlung(double rho_code, double prs_code, double redshift) {
    const double e = 1.602176634e-19;
    const double h = 6.62607015e-34;
    const double me = 9.1093837015e-31;
    const double kb = 1.380649e-23;
    const double eps0 = 8.8541878128e-12;
    const double z_atomic = 1.04;

    double rho_si = rho_code * UNIT_DENSITY_SI;
    double prs_si = prs_code * UNIT_PRESSURE_SI;
    double temp = xraise_temperature_k(prs_si, rho_si);
    if (!(temp > 0.0) || !isfinite(temp)) {
        return 0.0;
    }

    double emitted_freq = XRAISE_XRAY_FREQ_HZ * (1.0 + redshift);
    double exp_arg = -(h * emitted_freq) / (kb * temp);
    if (exp_arg < -700.0) {
        return 0.0;
    }

    double constants =
        (z_atomic * z_atomic * pow(e, 6.0) /
         (3.0 * PI_VAL * PI_VAL * pow(eps0, 3.0) * me * me * pow(C_LIGHT, 3.0))) *
        sqrt(PI_VAL * me / 6.0) *
        pow(kb * temp, -2.5) *
        prs_si * prs_si;

    return constants * exp(exp_arg) / (4.0 * PI_VAL);
}

static double get_A_radio(double q) {
    return (tgamma(q / 4.0 + 19.0 / 12.0) *
            tgamma(q / 4.0 - 1.0 / 12.0) *
            tgamma(q / 4.0 + 5.0 / 4.0)) /
           tgamma(q / 4.0 + 7.0 / 4.0);
}

static double get_K_radio(double q, double gamma_c) {
    return get_A_radio(q) *
           pow(gamma_c - 1.0, -((q + 5.0) / 4.0)) *
           pow((2.0 * PI_VAL / 3.0), -((q - 1.0) / 2.0)) *
           (sqrt(3.0 * PI_VAL) / (16.0 * PI_VAL * PI_VAL * (q + 1.0)));
}

static double get_I_radio(double q, double gamma_min, double gamma_max) {
    const double me = 9.1093837015e-31;
    double mec2 = me * C_LIGHT * C_LIGHT;
    return pow(mec2, 2.0 - q) *
           ((pow(gamma_max, 2.0 - q) - pow(gamma_min, 2.0 - q)) / (2.0 - q));
}

static double radio_j0(double q, double gamma_c, double eta, double gamma_min, double gamma_max) {
    const double mu0 = 1.25663706212e-6;
    const double me = 9.1093837015e-31;
    const double e = 1.602176634e-19;
    const double eps0 = 8.8541878128e-12;
    const double freq0 = 1.0e9;
    const double p0 = 1.0e-11;

    double log_inverse_I = -log10(get_I_radio(q, gamma_min, gamma_max));
    double log_eta_term = ((q + 1.0) / 4.0) * log10(eta) -
                          ((q + 5.0) / 4.0) * log10(1.0 + eta);
    double log_mu0_term = ((q + 1.0) / 4.0) * log10(2.0 * mu0);
    double log_nu_term = -((q - 1.0) / 2.0) *
                         log10(freq0 * pow(me, 3.0) * pow(C_LIGHT, 4.0) / e);
    double log_const_term = log10(get_K_radio(q, gamma_c) *
                                  (pow(e, 3.0) / (eps0 * C_LIGHT * me)));
    double log_p0_term = ((q + 5.0) / 4.0) * log10(p0);

    return pow(10.0, log_const_term + log_nu_term + log_mu0_term +
                         log_inverse_I + log_eta_term + log_p0_term);
}

static int tokenize(char *line, char *tokens[MAX_TOKENS]) {
    int ntok = 0;
    char *tok = strtok(line, " \t\r\n");
    while (tok != NULL && ntok < MAX_TOKENS) {
        tokens[ntok++] = tok;
        tok = strtok(NULL, " \t\r\n");
    }
    return ntok;
}

static int field_index(const ParticleHeader *header, const char *name) {
    for (int i = 0; i < header->nfields; i++) {
        if (strcmp(header->fields[i].name, name) == 0) {
            return i;
        }
    }
    return -1;
}

static void parse_particle_header(const char *path, ParticleHeader *header, long *data_start) {
    memset(header, 0, sizeof(*header));
    strcpy(header->endianity, "little");
    header->time_code = NAN;
    *data_start = 0;

    FILE *f = fopen(path, "rb");
    if (f == NULL) {
        perror(path);
        exit(2);
    }

    char line[4096];
    while (fgets(line, sizeof(line), f) != NULL) {
        if (line[0] != '#') {
            break;
        }
        *data_start = ftell(f);
        char copy[4096];
        strncpy(copy, line, sizeof(copy) - 1);
        copy[sizeof(copy) - 1] = '\0';
        char *tokens[MAX_TOKENS];
        int ntok = tokenize(copy, tokens);
        if (ntok < 2) {
            continue;
        }
        const char *key = tokens[1];
        if (strcmp(key, "field_names") == 0) {
            header->nfields = ntok - 2;
            if (header->nfields > MAX_FIELDS) {
                fprintf(stderr, "Too many particle fields: %d\n", header->nfields);
                exit(2);
            }
            for (int i = 0; i < header->nfields; i++) {
                strncpy(header->fields[i].name, tokens[i + 2], sizeof(header->fields[i].name) - 1);
            }
        } else if (strcmp(key, "field_dim") == 0) {
            int n = ntok - 2;
            int offset = 0;
            for (int i = 0; i < n && i < header->nfields; i++) {
                header->fields[i].dim = atoi(tokens[i + 2]);
                header->fields[i].offset = offset;
                offset += header->fields[i].dim;
            }
            header->total_dim = offset;
        } else if (strcmp(key, "nparticles") == 0) {
            header->nparticles = atol(tokens[ntok - 1]);
        } else if (strcmp(key, "time") == 0) {
            header->time_code = strtod(tokens[ntok - 1], NULL);
        } else if (strcmp(key, "endianity") == 0) {
            strncpy(header->endianity, tokens[ntok - 1], sizeof(header->endianity) - 1);
        }
    }
    fclose(f);

    if (header->nparticles < 0 || header->nfields <= 0 || header->total_dim <= 0) {
        fprintf(stderr, "Could not parse particle header for %s\n", path);
        exit(2);
    }
    if (strcmp(header->endianity, "little") != 0) {
        fprintf(stderr, "Unsupported particle endianity: %s\n", header->endianity);
        exit(2);
    }
}

static void write_particle_positions(
    const char *particle_path,
    const char *output_path,
    const char *summary_path
) {
    ParticleHeader header;
    long data_start = 0;
    parse_particle_header(particle_path, &header, &data_start);

    int id_idx = field_index(&header, "id");
    int x1_idx = field_index(&header, "x1");
    int x2_idx = field_index(&header, "x2");
    int x3_idx = field_index(&header, "x3");
    int tinj_idx = field_index(&header, "tinj");

    if (x1_idx < 0 || x2_idx < 0 || x3_idx < 0) {
        fprintf(stderr, "Particle file missing x1/x2/x3 fields\n");
        exit(2);
    }

    FILE *in = fopen(particle_path, "rb");
    if (in == NULL) {
        perror(particle_path);
        exit(2);
    }
    FILE *out = fopen(output_path, "w");
    if (out == NULL) {
        perror(output_path);
        exit(2);
    }

    if (fseek(in, 0, SEEK_END) != 0) {
        perror("fseek end particle");
        exit(2);
    }
    long file_size = ftell(in);
    long payload_bytes = header.nparticles * header.total_dim * (long)sizeof(double);
    long payload_start = file_size - payload_bytes;
    if (payload_start < data_start) {
        payload_start = data_start;
    }
    if (fseek(in, payload_start, SEEK_SET) != 0) {
        perror("fseek particle payload");
        exit(2);
    }

    double *row = (double *)malloc((size_t)header.total_dim * sizeof(double));
    if (row == NULL) {
        fprintf(stderr, "Could not allocate particle row\n");
        exit(2);
    }

    double x_min = DBL_MAX, x_max = -DBL_MAX;
    double y_min = DBL_MAX, y_max = -DBL_MAX;
    double z_min = DBL_MAX, z_max = -DBL_MAX;
    double tinj_min = DBL_MAX, tinj_max = -DBL_MAX;

    fprintf(out, "id\tx_kpc\ty_kpc\tz_kpc\ttinj_code\ttinj_myr\n");
    for (long p = 0; p < header.nparticles; p++) {
        size_t got = fread(row, sizeof(double), (size_t)header.total_dim, in);
        if (got != (size_t)header.total_dim) {
            fprintf(stderr, "Short read in particle payload at particle %ld\n", p);
            exit(2);
        }
        double id = id_idx >= 0 ? row[header.fields[id_idx].offset] : (double)(p + 1);
        double x = row[header.fields[x1_idx].offset];
        double y = row[header.fields[x2_idx].offset];
        double z = row[header.fields[x3_idx].offset];
        double tinj = tinj_idx >= 0 ? row[header.fields[tinj_idx].offset] : NAN;
        fprintf(out, "%.0f\t%.17g\t%.17g\t%.17g\t%.17g\t%.17g\n",
                id, x, y, z, tinj, tinj / CODE_TIME_PER_MYR);
        if (x < x_min) x_min = x;
        if (x > x_max) x_max = x;
        if (y < y_min) y_min = y;
        if (y > y_max) y_max = y;
        if (z < z_min) z_min = z;
        if (z > z_max) z_max = z;
        if (isfinite(tinj)) {
            if (tinj < tinj_min) tinj_min = tinj;
            if (tinj > tinj_max) tinj_max = tinj;
        }
    }

    free(row);
    fclose(out);
    fclose(in);

    FILE *summary = fopen(summary_path, "w");
    if (summary == NULL) {
        perror(summary_path);
        exit(2);
    }
    fprintf(summary, "metric,value,unit\n");
    fprintf(summary, "particle_file,%s,path\n", particle_path);
    fprintf(summary, "particle_time_code,%.17g,code_time\n", header.time_code);
    fprintf(summary, "particle_time_myr,%.17g,Myr\n", header.time_code / CODE_TIME_PER_MYR);
    fprintf(summary, "nparticles,%ld,count\n", header.nparticles);
    fprintf(summary, "x_min,%.17g,kpc\n", x_min);
    fprintf(summary, "x_max,%.17g,kpc\n", x_max);
    fprintf(summary, "y_min,%.17g,kpc\n", y_min);
    fprintf(summary, "y_max,%.17g,kpc\n", y_max);
    fprintf(summary, "z_min,%.17g,kpc\n", z_min);
    fprintf(summary, "z_max,%.17g,kpc\n", z_max);
    fprintf(summary, "tinj_min_code,%.17g,code_time\n", tinj_min);
    fprintf(summary, "tinj_max_code,%.17g,code_time\n", tinj_max);
    fprintf(summary, "tinj_min_myr,%.17g,Myr\n", tinj_min / CODE_TIME_PER_MYR);
    fprintf(summary, "tinj_max_myr,%.17g,Myr\n", tinj_max / CODE_TIME_PER_MYR);
    fclose(summary);
}

int main(int argc, char **argv) {
    if (argc < 5 || argc > 7) {
        usage(argv[0]);
        return 2;
    }

    const char *input_h5 = argv[1];
    const char *timestep = argv[2];
    const char *particle_file = argv[3];
    const char *output_dir = argv[4];
    double redshift = argc >= 6 ? strtod(argv[5], NULL) : 0.05;
    double view_angle_deg = argc >= 7 ? strtod(argv[6], NULL) : 0.0;

    if (fabs(view_angle_deg) > 1.0e-9) {
        fprintf(stderr, "This smoke extractor currently supports only the 0 degree y-axis projection.\n");
        return 2;
    }

    ensure_dir(output_dir);

    hid_t file = H5Fopen(input_h5, H5F_ACC_RDONLY, H5P_DEFAULT);
    if (file < 0) {
        fprintf(stderr, "Could not open HDF5 file: %s\n", input_h5);
        return 2;
    }

    char rho_path[512], prs_path[512], tr1_path[512];
    snprintf(rho_path, sizeof(rho_path), "/%s/vars/rho", timestep);
    snprintf(prs_path, sizeof(prs_path), "/%s/vars/prs", timestep);
    snprintf(tr1_path, sizeof(tr1_path), "/%s/vars/tr1", timestep);

    hsize_t dims[3];
    read_dataset_dims(file, rho_path, dims);
    hsize_t nz = dims[0], ny = dims[1], nx = dims[2];
    hsize_t map_cells = nz * nx;

    double *x = (double *)malloc((size_t)nx * sizeof(double));
    double *y = (double *)malloc((size_t)ny * sizeof(double));
    double *z = (double *)malloc((size_t)nz * sizeof(double));
    double *dx = (double *)malloc((size_t)nx * sizeof(double));
    double *dy = (double *)malloc((size_t)ny * sizeof(double));
    double *dz = (double *)malloc((size_t)nz * sizeof(double));
    double *rho_slice = (double *)malloc((size_t)map_cells * sizeof(double));
    double *prs_slice = (double *)malloc((size_t)map_cells * sizeof(double));
    double *tr1_slice = (double *)malloc((size_t)map_cells * sizeof(double));
    double *xray_map = (double *)calloc((size_t)map_cells, sizeof(double));
    double *radio_map = (double *)calloc((size_t)map_cells, sizeof(double));
    double *tracer_max = (double *)calloc((size_t)map_cells, sizeof(double));
    if (!x || !y || !z || !dx || !dy || !dz || !rho_slice || !prs_slice ||
        !tr1_slice || !xray_map || !radio_map || !tracer_max) {
        fprintf(stderr, "Could not allocate observable smoke buffers\n");
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

    const double q = 2.2;
    const double gamma_c = 4.0 / 3.0;
    const double eta = 0.03;
    const double gamma_min = 500.0;
    const double gamma_max = 1.0e5;
    const double pressure_exp = (q + 5.0) / 4.0;
    const double freq_exp = -((q - 1.0) / 2.0);
    const double p0 = 1.0e-11;
    double j0 = radio_j0(q, gamma_c, eta, gamma_min, gamma_max);
    double radio_freq_factor = pow(RADIO_FREQ_HZ / 1.0e9, freq_exp);
    double total_radio_luminosity = 0.0;
    unsigned long long lobe_cells = 0;

    for (hsize_t iy = 0; iy < ny; iy++) {
        read_xz_slice(file, rho_path, nz, nx, iy, rho_slice);
        read_xz_slice(file, prs_path, nz, nx, iy, prs_slice);
        read_xz_slice(file, tr1_path, nz, nx, iy, tr1_slice);

        double dy_m = dy[iy] * KPC_M;
        for (hsize_t iz = 0; iz < nz; iz++) {
            double dz_m = dz[iz] * KPC_M;
            for (hsize_t ix = 0; ix < nx; ix++) {
                hsize_t midx = iz * nx + ix;
                double rho = rho_slice[midx];
                double prs = prs_slice[midx];
                double tr = tr1_slice[midx];

                double xray_emis = xraise_grid_bremsstrahlung(rho, prs, redshift);
                xray_map[midx] += (xray_emis * dy_m) / 1.0e-29;

                if (tr > tracer_max[midx]) {
                    tracer_max[midx] = tr;
                }

                if (tr >= TRACER_THRESHOLD && prs > 0.0) {
                    double prs_si = prs * UNIT_PRESSURE_SI;
                    double tracer_weight = tr;
                    double j_radio = j0 * radio_freq_factor *
                                     pow(prs_si / p0, pressure_exp) * tracer_weight;
                    radio_map[midx] += (j_radio / (4.0 * PI_VAL)) * dy_m / 1.0e-29;
                    total_radio_luminosity += j_radio * dx[ix] * KPC_M * dy_m * dz_m;
                    lobe_cells++;
                }
            }
        }
    }

    double time_code = read_time_attr(file, timestep);
    CHECK_H5(H5Fclose(file), "close input file");

    char path[1024];
    join_path(path, sizeof(path), output_dir, "x_kpc.tsv");
    write_vector_tsv(path, x, nx);
    join_path(path, sizeof(path), output_dir, "z_kpc.tsv");
    write_vector_tsv(path, z, nz);
    join_path(path, sizeof(path), output_dir, "xray_1kev_raw_mjy_sr.tsv");
    write_matrix_tsv(path, xray_map, nz, nx);
    join_path(path, sizeof(path), output_dir, "radio_150mhz_proxy_mjy_sr.tsv");
    write_matrix_tsv(path, radio_map, nz, nx);
    join_path(path, sizeof(path), output_dir, "tracer_max_los.tsv");
    write_matrix_tsv(path, tracer_max, nz, nx);

    char particle_positions_path[1024], particle_summary_path[1024];
    join_path(particle_positions_path, sizeof(particle_positions_path), output_dir, "particle_positions_0deg.tsv");
    join_path(particle_summary_path, sizeof(particle_summary_path), output_dir, "particle_summary.csv");
    write_particle_positions(particle_file, particle_positions_path, particle_summary_path);

    MapStats xstats, rstats, tstats;
    stats_init(&xstats);
    stats_init(&rstats);
    stats_init(&tstats);
    for (hsize_t i = 0; i < map_cells; i++) {
        stats_add(&xstats, xray_map[i]);
        stats_add(&rstats, radio_map[i]);
        stats_add(&tstats, tracer_max[i]);
    }

    join_path(path, sizeof(path), output_dir, "observable_summary.csv");
    FILE *summary = fopen(path, "w");
    if (summary == NULL) {
        perror(path);
        return 2;
    }
    fprintf(summary, "metric,value,unit\n");
    fprintf(summary, "input_h5,%s,path\n", input_h5);
    fprintf(summary, "timestep,%s,label\n", timestep);
    fprintf(summary, "time_code,%.17g,code_time\n", time_code);
    fprintf(summary, "time_myr,%.17g,Myr\n", time_code / CODE_TIME_PER_MYR);
    fprintf(summary, "view_angle_deg,%.17g,deg\n", view_angle_deg);
    fprintf(summary, "redshift,%.17g,dimensionless\n", redshift);
    fprintf(summary, "nx,%llu,cells\n", (unsigned long long)nx);
    fprintf(summary, "ny,%llu,cells\n", (unsigned long long)ny);
    fprintf(summary, "nz,%llu,cells\n", (unsigned long long)nz);
    fprintf(summary, "xray_frequency,%.17g,Hz\n", XRAISE_XRAY_FREQ_HZ);
    fprintf(summary, "radio_frequency,%.17g,Hz\n", RADIO_FREQ_HZ);
    fprintf(summary, "tracer_threshold,%.17g,dimensionless\n", TRACER_THRESHOLD);
    fprintf(summary, "xray_raw_mjy_sr_min,%.17e,mJy/sr\n", xstats.min);
    fprintf(summary, "xray_raw_mjy_sr_max,%.17e,mJy/sr\n", xstats.max);
    fprintf(summary, "xray_raw_mjy_sr_sum,%.17e,mJy/sr_pixel_sum\n", xstats.sum);
    fprintf(summary, "xray_positive_pixels,%llu,count\n", xstats.positive);
    fprintf(summary, "radio_proxy_mjy_sr_min,%.17e,mJy/sr\n", rstats.min);
    fprintf(summary, "radio_proxy_mjy_sr_max,%.17e,mJy/sr\n", rstats.max);
    fprintf(summary, "radio_proxy_mjy_sr_sum,%.17e,mJy/sr_pixel_sum\n", rstats.sum);
    fprintf(summary, "radio_positive_pixels,%llu,count\n", rstats.positive);
    fprintf(summary, "radio_luminosity_proxy,%.17e,W/Hz\n", total_radio_luminosity);
    fprintf(summary, "radio_lobe_cells_counted,%llu,cells\n", lobe_cells);
    fprintf(summary, "tracer_los_max,%.17e,dimensionless\n", tstats.max);
    fprintf(summary, "xray_formula,XRAiSE grid_bremsstrahlung before APEC/Gaunt correction,text\n");
    fprintf(summary, "radio_formula,plutokore pressure/tracer lossless surface-brightness scaling,text\n");
    fclose(summary);

    free(x);
    free(y);
    free(z);
    free(dx);
    free(dy);
    free(dz);
    free(rho_slice);
    free(prs_slice);
    free(tr1_slice);
    free(xray_map);
    free(radio_map);
    free(tracer_max);

    return 0;
}
