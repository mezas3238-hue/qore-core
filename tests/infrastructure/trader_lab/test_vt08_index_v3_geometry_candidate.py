from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_qore_ambiguity_lab_v1 import Signal
from qore.infrastructure.trader_lab.vt08_index_v3_geometry_candidate import (
    CANDIDATE_ID,
    MIN_CLOSURE_REFERENCE_RANGE_RATIO,
    MIN_PROTECTED_SWING_RISK_FRACTION,
    RULE_FINGERPRINT,
    TARGET_R_MULTIPLE,
    _geometry,
    _geometry_accepts,
    _model_v3,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
    Vt08IndexC2R1ProtectedSwing,
)

_NY = ZoneInfo("America/New_York")


def _bar(
    opened_at: datetime,
    *,
    open_price: str = "100",
    high: str = "100.5",
    low: str = "99.5",
    close: str = "100",
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=15),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _fixture(
    *,
    side: DemoTradingSetupSide,
    stop: str,
    closure_high: str = "100.6",
    closure_low: str = "99.4",
) -> tuple[Signal, dict[datetime, Vt08IndexC2R1Bar]]:
    decision_local = datetime(2026, 1, 5, 10, tzinfo=_NY)
    decision = decision_local.astimezone(UTC)
    start = (decision_local - timedelta(hours=8)).astimezone(UTC)
    indexed: dict[datetime, Vt08IndexC2R1Bar] = {}
    for index in range(48):
        opened = start + timedelta(minutes=15 * index)
        if index < 16:
            bar = _bar(opened)
        elif index < 32:
            bar = _bar(opened, high=closure_high, low=closure_low)
        elif index == 32:
            if side is DemoTradingSetupSide.LONG:
                bar = _bar(opened, high="100.8", low="99.8")
            else:
                bar = _bar(opened, high="100.2", low="99.2")
        else:
            bar = _bar(opened)
        indexed[opened] = bar
    swing = Vt08IndexC2R1ProtectedSwing(
        side=side,
        price=Decimal(stop),
        cisd_level=Decimal("99.9") if side is DemoTradingSetupSide.LONG else Decimal("100.1"),
        confirmed_at=decision - timedelta(minutes=15),
        opposing_series_opened_at=decision - timedelta(minutes=45),
    )
    signal = Signal("NAS100", decision, 10, side, swing, "c2")
    return signal, indexed


def test_v3_identity_and_empirical_contract_are_frozen() -> None:
    assert CANDIDATE_ID == "VT08_INDEX_V3_QORE_GEOMETRY_001"
    assert MIN_PROTECTED_SWING_RISK_FRACTION == Decimal("0.003")
    assert MIN_CLOSURE_REFERENCE_RANGE_RATIO == Decimal("1.2")
    assert TARGET_R_MULTIPLE == Decimal("2.5")
    assert len(RULE_FINGERPRINT) == 64


def test_geometry_gate_accepts_exact_boundaries() -> None:
    assert _geometry_accepts(
        {
            "risk_fraction": Decimal("0.003"),
            "closure_reference_range_ratio": Decimal("1.2"),
        }
    )
    assert not _geometry_accepts(
        {
            "risk_fraction": Decimal("0.002999"),
            "closure_reference_range_ratio": Decimal("1.2"),
        }
    )
    assert not _geometry_accepts(
        {
            "risk_fraction": Decimal("0.003"),
            "closure_reference_range_ratio": Decimal("1.1999"),
        }
    )


def test_long_model_uses_2_5r_target_after_strong_geometry() -> None:
    signal, indexed = _fixture(side=DemoTradingSetupSide.LONG, stop="99.7")
    geometry = _geometry(signal, bars_by_open=indexed)
    assert geometry is not None
    assert geometry["risk_fraction"] == Decimal("0.003")
    assert geometry["closure_reference_range_ratio"] == Decimal("1.2")
    trade = _model_v3(signal, bars_by_open=indexed)
    assert trade is not None
    assert trade.target == Decimal("100.75")
    assert trade.r_multiple == Decimal("2.5")
    assert trade.exit_reason == "target"


def test_short_model_is_mirrored() -> None:
    signal, indexed = _fixture(side=DemoTradingSetupSide.SHORT, stop="100.3")
    trade = _model_v3(signal, bars_by_open=indexed)
    assert trade is not None
    assert trade.target == Decimal("99.25")
    assert trade.r_multiple == Decimal("2.5")
    assert trade.exit_reason == "target"


def test_weak_protected_swing_geometry_abstains() -> None:
    signal, indexed = _fixture(side=DemoTradingSetupSide.LONG, stop="99.71")
    assert _model_v3(signal, bars_by_open=indexed) is None


def test_weak_closure_expansion_abstains() -> None:
    signal, indexed = _fixture(
        side=DemoTradingSetupSide.LONG,
        stop="99.7",
        closure_high="100.595",
        closure_low="99.405",
    )
    assert _model_v3(signal, bars_by_open=indexed) is None
