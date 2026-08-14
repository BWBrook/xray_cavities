from pathlib import Path


COEFFICIENT = Path("scripts/kunanyi/g_lo_praise2_coefficient_correction.pbs")
COMPRESSION = Path("scripts/kunanyi/reversible_hdf5_compression_pilot.pbs")
READABILITY = Path("scripts/kunanyi/reversible_hdf5_readability_finalizer.pbs")


def test_coefficient_wrapper_is_exact_sample_and_no_overwrite() -> None:
    text = COEFFICIENT.read_text()
    assert "g_lo_history.h5" in text
    assert "stable_method_value_selection.csv" in text
    assert "praise2_uncorrected.py" in text and "praise2_corrected.py" in text
    assert "refusing to overwrite" in text
    assert "PRAISE2_PUBLISHED_COEFFICIENT_VALIDATED_FOR_PRODUCTION" in text


def test_compression_wrapper_preserves_sources_and_validates_analysis_readability() -> None:
    text = COMPRESSION.read_text()
    assert "data.0050.flt.h5" in text and "data.0010.dbl.h5" in text
    assert "data.0050.flt.reversible.h5" in text
    assert "data.0010.dbl.reversible.h5" in text
    assert "hdf5plugin-5.1.0" in text
    assert "pip install --no-deps --target" in text
    assert 'export HDF5_PLUGIN_PATH=' in text
    assert 'hdf5plugin.PLUGINS_PATH' in text
    assert "rm \"$FLOAT_SOURCE\"" not in text
    assert "rm \"$DOUBLE_SOURCE\"" not in text
    assert "xraise_grid_smoke_summary.csv" in text
    assert "bitwise_values_preserved" in text


def test_readability_finalizer_reuses_existing_copy_without_recompression() -> None:
    text = READABILITY.read_text()
    assert "data.0050.flt.reversible.h5" in text
    assert 'export HDF5_PLUGIN_PATH=' in text
    assert "fresh_process_zfp_readability=passed" in text
    assert "xraise_grid_smoke_summary.csv" in text
    assert "reversible_hdf5_compression.py" not in text
    assert "data.0010.dbl.reversible.h5" not in text
