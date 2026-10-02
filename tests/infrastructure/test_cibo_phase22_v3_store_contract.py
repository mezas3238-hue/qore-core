from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_v3_store_contract import (
    PHASE22_V3_STORE_IDENTITIES,
    PHASE22_V3_STORE_ROOT_NAME,
    assert_phase22_v3_store_pristine,
    phase22_v3_store_paths,
)


def test_v3_store_surface_is_physically_disjoint_from_v2(tmp_path: Path) -> None:
    root = tmp_path / PHASE22_V3_STORE_ROOT_NAME
    assert_phase22_v3_store_pristine(root)

    paths = phase22_v3_store_paths(root)
    assert len(paths) == 5
    assert len(paths) == len(set(paths))
    assert tuple(item.name for item in PHASE22_V3_STORE_IDENTITIES) == (
        "HOLDOUT_FORWARD_EVIDENCE",
        "HOLDOUT_POLICY",
        "EXECUTED_RISK",
        "CMA_SETTLEMENT",
        "T20_RELEASE",
    )
    assert all(
        item.relative_path.startswith("phase22-v3-stores/")
        for item in PHASE22_V3_STORE_IDENTITIES
    )
    assert all("phase22-v2-stores" not in item.relative_path for item in PHASE22_V3_STORE_IDENTITIES)


def test_v3_store_contract_rejects_v2_root(tmp_path: Path) -> None:
    with pytest.raises(CiboCapitalManagementError, match="V3 store root"):
        assert_phase22_v3_store_pristine(tmp_path / "phase22-v2-stores")


def test_v3_store_contract_rejects_nonpristine_file(tmp_path: Path) -> None:
    root = tmp_path / PHASE22_V3_STORE_ROOT_NAME
    root.mkdir()
    first = phase22_v3_store_paths(root)[0]
    first.write_text("{}\n", encoding="utf-8")
    with pytest.raises(CiboCapitalManagementError, match="not pristine"):
        assert_phase22_v3_store_pristine(root)
