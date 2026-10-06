from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_one_shot_source_preflight import (
    FROZEN_TURTLE_REPLAY_SOURCES,
    FROZEN_VT31_SOURCE_SHA,
    expected_source_archive_rows,
    validate_frozen_replay_source_manifest,
    validate_m5_source_root,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    ACTIVE_PHASE22_TRADER_PARITY_MANIFEST,
)


def test_frozen_replay_sources_match_parity_manifest() -> None:
    validate_frozen_replay_source_manifest()
    parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
    assert parity is not None
    by_id = {item.trader_id: item for item in parity.receipts}

    assert len(FROZEN_TURTLE_REPLAY_SOURCES) == 5
    assert {
        item.trader_id for item in FROZEN_TURTLE_REPLAY_SOURCES
    } == {
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
    }
    assert by_id["VT31_NAS100"].methodology_git_sha == FROZEN_VT31_SOURCE_SHA


def test_source_archive_manifest_is_exact_nine_m5_plus_one_m1() -> None:
    rows = expected_source_archive_rows()

    assert len(rows) == 10
    assert sum(1 for row in rows if row[1] == "M5") == 9
    assert sum(1 for row in rows if row[1] == "M1") == 1
    assert len({(row[0], row[1]) for row in rows}) == 10
    assert all(row[2] > 0 for row in rows)
    assert all(row[3].startswith("sha256:") for row in rows)
    assert all(row[4] > 0 for row in rows)


def test_m5_validation_fails_closed_without_archive(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="RAW_M5_LEDGER partitions not found"):
        validate_m5_source_root(root=tmp_path, symbol="EURUSD")


def test_unknown_symbol_fails_before_source_read(tmp_path: Path) -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="binding drift",
    ):
        validate_m5_source_root(root=tmp_path, symbol="NOT_A_SYMBOL")
