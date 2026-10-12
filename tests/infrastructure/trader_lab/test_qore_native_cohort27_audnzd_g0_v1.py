"""AUDNZD 27th M5 source strictly G0 only."""
from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_cohort27_audnzd_g0_v1 as a


def test_add_one_only_and_parent_sha_frozen() -> None:
    assert a.ADDED == ("AUDNZD",)
    assert "AUDNZD" not in a.base.ALL
    assert a.PARENT26_COUNT == 19160586
    assert a.PARENT26_CODE_SHA == "2391063da42abdb733783ea9fb1781314419a946"
    assert len(a.SOURCE_PARENT26_SHA) == 64


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="original archive absent"):
        a.new_source(tmp_path / "notdownloaded")


def test_parent_requires_signed_sha_and_code_commit(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        a.old26(tmp_path)


def test_no_27_if_new_or_parent_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        a.combine(tmp_path / "old26", tmp_path / "audnzd")


def test_only_source_metadata_no_market_returns_or_trading() -> None:
    source = Path(a.__file__).read_text()
    forbidden = ("profit_factor(", "sharpe_ratio(", "backtest(",
                 "place_order(", 'row["close_relative"]', "client.request(")
    assert not any(text in source for text in forbidden)
