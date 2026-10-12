"""No-economics safeguards for QORE Native 30→33 source SHA closure."""
from __future__ import annotations

from pathlib import Path
import pytest

from qore.infrastructure.trader_lab import qore_native_final33_three_m5_g0_v1 as m


def test_30_plus_3_no_roster_collision_and_original_parent_fixed() -> None:
    m.roster_contract()
    assert len(m.EXPECTED_PARENT_30) == 30
    assert m.SOURCE_TAIL == ("NZDJPY", "NZDCAD", "NZDCHF")
    assert len(m.FROZEN_UNIVERSE_33) == 33
    assert m.PARENT_30_M5_BARS == 22141699
    assert m.PARENT_30_CODE_SHA == "7c41bc4d0b135efb0885c17bafe9869342a5c377"
    assert len(m.PARENT_30_JSON_SHA) == 64


def test_no_self_asserted_or_missing_archive_can_pass_SHA(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside frozen"):
        m.audit_tail("EURUSD", tmp_path)
    with pytest.raises(ValueError, match="original archive absent"):
        m.audit_tail("NZDJPY", tmp_path / "not downloaded")


def test_parent_30_hash_and_code_head_required(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        m.verified_parent30(tmp_path)
    (tmp_path / "OUTPUT_SHA256SUMS.txt").write_text("")
    with pytest.raises(ValueError):
        m.verified_parent30(tmp_path)


def test_no_declaring_33_without_three_sha_and_parent(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        m.build33(tmp_path, tmp_path / "tail-witness-missing")


def test_33_module_no_prices_returns_or_orders() -> None:
    code = Path(m.__file__).read_text(encoding="utf-8")
    for banned in (
        'row["open_relative"]', 'row["close_relative"]', 'row["volume"]',
        "profit_factor(", "sharpe_ratio(", "backtest(", "place_order(",
        "ProtoOANewOrderReq", "ctrader_open_api_client",
    ):
        assert banned not in code
