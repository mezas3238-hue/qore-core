"""QORE Native exact 23+3 research-source G0: strict no-return and SHA tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_cohort26_source_addendum_v1 as a


def test_fixed_extension_three_no_overlap() -> None:
    assert a.MORE == ("GBPNZD", "AUDCAD", "AUDCHF")
    assert len(set(a.MORE) | set(a.first.ALL)) == 26
    assert len(a.first.ALL) == 23
    assert a.EXACT_PARENT_SHA == "cb9a21f77131b07db2da964ba123bd8c282ded23"
    assert a.EXPECTED_PARENT_COUNT == 16924567
    assert len(a.EXPECTED_PARENT_MANIFEST_SHA256) == 64


def test_new_source_not_in_three_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside 3"):
        a.audit_additional("EURJPY", tmp_path)


def test_empty_expected_raw_source_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="original archive absent"):
        a.audit_additional("AUDCAD", tmp_path / "unknown")


def test_parent_missing_sha_or_malformed_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="required original hash"):
        a.read_verified_parent(tmp_path)
    (tmp_path / "OUTPUT_SHA256SUMS.txt").write_text("")
    with pytest.raises(ValueError, match="wrong scope"):
        a.read_verified_parent(tmp_path)


def test_extra_cohort_union_requires_three_independent_witnesses(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        a.combine(tmp_path / "parent", tmp_path / "extra")


def test_no_new_economic_processing_or_live_connector_imports() -> None:
    source = Path(a.__file__).read_text()
    for banned in (
        'row["close_relative"]', 'row["open_relative"]', 'row["volume"]',
        "backtest(", "profit_factor(", "sharpe_ratio(", "place_order(",
        "ctrader_open_api_client", "trading_authorized=True",
    ):
        assert banned not in source
