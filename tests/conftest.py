import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("XRAY_CAVITIES_DATA", ROOT)).expanduser()
SENTINEL = DATA_ROOT / "docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products/xraise_grid_0deg/x_kpc.tsv"
NEEDS_BULK_DATA = tuple((Path(__file__).parent / "bulk_data_tests.txt").read_text().split())


def pytest_collection_modifyitems(config, items):
    if SENTINEL.exists():
        return
    skip = pytest.mark.skip(
        reason="needs the bulk simulation outputs, which are not in git; see README.md, section Bulk data"
    )
    for item in items:
        if item.nodeid.startswith(NEEDS_BULK_DATA):
            item.add_marker(skip)
