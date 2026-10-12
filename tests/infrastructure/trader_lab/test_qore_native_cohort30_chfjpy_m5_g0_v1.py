"""CHFJPY 30th M5 source: frozen SHA parent 29, no price outcomes."""
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_cohort30_chfjpy_m5_g0_v1 as m


def test_fixed_parent_29_and_new_thirtieth() -> None:
    assert len(m.EXPECTED_PARENT_SYMBOLS) == 29
    assert m.NEW_SYMBOL == "CHFJPY"
    assert m.NEW_SYMBOL not in m.EXPECTED_PARENT_SYMBOLS
    assert m.PARENT_BARS == 21396360
    assert len(m.PARENT_29_JSON_SHA) == 64


def test_missing_chfjpy_source_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="original archive absent"):
        m.original_chfjpy_audit(tmp_path / "missing")


def test_missing_or_manipulated_parent_shas_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        m.parent_29_source(tmp_path)
    (tmp_path / "OUTPUT_SHA256SUMS.txt").write_text("")
    with pytest.raises(ValueError):
        m.parent_29_source(tmp_path)


def test_30_requires_valid_parent_and_new_sidecar(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        m.combine(tmp_path / "old29", tmp_path / "chfjpy")


def test_no_outcomes_or_orders_in_source_code() -> None:
    code = Path(m.__file__).read_text()
    for needle in ('row["open_relative"]', 'row["close_relative"]',
                   "profit_factor(", "backtest(", "place_order(",
                   "ctrader_open_api_client", "ProtoOANewOrderReq"):
        assert needle not in code


def test_pending_tail_explicit_not_silently_proclaimed_33() -> None:
    assert m.NEW_SYMBOL not in {"NZDJPY", "NZDCAD", "NZDCHF"}
