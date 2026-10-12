"""G0 27+2 M5 research source evidence, never PnL."""
from __future__ import annotations

from pathlib import Path
import pytest

from qore.infrastructure.trader_lab import qore_native_cohort29_cadjpy_cadchf_m5_g0_v1 as m


def test_fixed_source_27_to_29() -> None:
    assert m.NEW_TWO == ("CADJPY", "CADCHF")
    assert len(m.EXPECTED_27) == 27
    assert not (set(m.NEW_TWO) & m.EXPECTED_27)
    assert len(m.EXPECTED_27 | set(m.NEW_TWO)) == 29
    assert m.FROZEN_PARENT_BARS == 19905871
    assert len(m.FROZEN_PARENT_MANIFEST_SHA) == 64


def test_audit_unknown_symbol_fails_before_any_read(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unexpected/overlapping"):
        m.audit_new("EURUSD", tmp_path)
    with pytest.raises(ValueError, match="original archive absent"):
        m.audit_new("CADJPY", tmp_path / "source-missing")


def test_parent_requires_original_27_signed_witness(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        m.verify_parent(tmp_path)


def test_combine_not_29_without_both_new_sha_witnesses(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        m.combine(tmp_path / "parent-missing", tmp_path / "new-missing")


def test_source_script_never_reads_OHLC_or_calls_live() -> None:
    text = Path(m.__file__).read_text(encoding="utf-8")
    for forbidden in (
        'row["close_relative"]', 'row["open_relative"]', 'row["volume"]',
        "backtest(", "profit_factor(", "sharpe_ratio(", "place_order(",
        "ProtoOANewOrderReq", "ctrader_open_api_client",
    ):
        assert forbidden not in text


def test_no_historical_bidask_or_broker_H4_assertion() -> None:
    assert m.FROZEN_PARENT_IDENTITY == "QORE_NATIVE_COHORT27_WITH_AUDNZD_G0_SOURCE_V1"
    assert m.FROZEN_PARENT_CODE_SHA == "56b07172bdded93f9fafadedf614c770a2a2dc40"
    assert m.FROZEN_PARENT_RUN == 38204152494
