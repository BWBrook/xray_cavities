from pathlib import Path


WRAPPER = Path("scripts/kunanyi/three_case_endpoint_truth_alignment.pbs")


def wrapper_text() -> str:
    return WRAPPER.read_text()


def test_wrapper_declares_all_three_accepted_endpoint_contracts() -> None:
    text = wrapper_text()

    assert "data.0051.flt.h5|Timestep_51|1e45" in text
    assert "data.0053.flt.h5|Timestep_53|1e43" in text
    assert "data.0050.flt.h5|Timestep_50|1e43" in text
    assert "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64" in text
    assert "2026-07-05-c-lo-endpoint-oriented-continuation" in text
    assert "2026-07-10-g-lo-hdf5-stall-guarded-continuation" in text


def test_wrapper_runs_truth_and_cavity_extractors_sequentially() -> None:
    text = wrapper_text()

    assert '"$TRUTH_EXE" "$hdf5" "$timestep" "$truth_dir" "$jet_power" 50.0' in text
    assert '"$CAVITY_EXE" "$hdf5" "$timestep" "$cavity_dir" 5e-3 1e-3 1.00 1.15 1.35' in text
    assert "level1_injected_energy.csv" in text
    assert "level2_tracer_lobe_truth.csv" in text
    assert "cavity_stub_summary.csv" in text
    assert "three_case_truth_validation=passed" in text


def test_wrapper_uses_stable_file_list_archive_and_no_science_compute() -> None:
    text = wrapper_text()

    assert "archive_file_list.txt" in text
    assert "archive_checksums.sha256" in text
    assert "--files-from" in text
    assert "ARCHIVE_PAYLOAD_TMP" in text
    assert "mv \"$ARCHIVE_PAYLOAD_TMP\" \"$ARCHIVE_PAYLOAD\"" in text
    assert "mpirun" not in text
    assert "xraise" not in text.lower()
    assert "praise" not in text.lower()


def test_wrapper_requests_single_node_serial_postprocessing_resources() -> None:
    text = wrapper_text()

    assert "#PBS -l select=1:ncpus=1:mpiprocs=1:mem=96gb" in text
    assert "#PBS -l walltime=06:00:00" in text
    assert "module purge" in text
    assert "h5pcc" in text
