import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts/kunanyi"), str(ROOT / "scripts/science")]
from stage_entropy_restart import compare_checkpoint_slab


def test_production_float_conversion():
    # Expected bit patterns were measured on Kunanyi with production MXCSR 0x8040.
    examples = [
        ("0x1p-150", 0), ("-0x1p-149", 0x80000000),
        ("0x1.fffffcp-127", 0), ("0x1.fffffep-127", 0),
        ("0x1.fffffe0000001p-127", 0), ("-0x1.fffffep-127", 0x80000000),
        ("0x1.fffffefffffffp-127", 0), ("0x1.ffffffp-127", 0x00800000),
        ("0x1.ffffff0000001p-127", 0x00800000), ("0x1.fffffffffffffp-127", 0x00800000),
        ("-0x1p-126", 0x80800000), ("0x1.000001p-126", 0x00800000),
        ("0x1p+0", 0x3f800000),
    ]
    values = np.array([float.fromhex(value) for value, _ in examples])
    stored = np.array([bits for _, bits in examples], dtype=np.uint32).view(np.float32)
    assert compare_checkpoint_slab(values, stored, "tr1", 184) == 6


@pytest.mark.parametrize("double, stored", [
    (2.0**-140, np.float32(2.0**-140)),
    (2.0**-126, 0),
    (1.0, np.nextafter(np.float32(1), np.float32(2))),
    (np.nan, np.nan),
    (np.inf, np.inf),
])
def test_checkpoint_still_rejects_other_discrepancies(double, stored):
    with pytest.raises(ValueError, match="tr1:"):
        compare_checkpoint_slab(np.array([double]), np.array([stored], dtype=np.float32), "tr1", 0)
