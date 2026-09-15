from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.fundednext_runtime_pipeline import (
    R315_OPERATIONAL_ENTRY_TYPE,
    cibo_setup_from_b01,
    request_cibo_posture,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingSetupSide,
    DemoTradingSetupSpec,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    Vt08B01Candidate,
    Vt08B01ProtectedSwing,
    methodology_fingerprint,
)
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_METHOD_FINGERPRINT,
    Vt08ForexCiboPosture,
)

_NOW = datetime(2026, 9, 15, 5, 0, tzinfo=UTC)


def _bar(opened: datetime, closed: datetime) -> Vt08B01Bar:
    return Vt08B01Bar(
        opened_at=opened,
        closed_at=closed,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
    )


def _candidate() -> Vt08B01Candidate:
    reference = _bar(_NOW - timedelta(hours=8), _NOW - timedelta(hours=4))
    candle2 = _bar(_NOW - timedelta(hours=4), _NOW)
    protected = Vt08B01ProtectedSwing(
        side=DemoTradingSetupSide.SHORT,
        price=Decimal("101"),
        cisd_level=Decimal("100.5"),
        confirmed_at=_NOW - timedelta(hours=1),
        opposing_series_opened_at=_NOW - timedelta(hours=2),
    )
    setup = DemoTradingSetupSpec(
        side=DemoTradingSetupSide.SHORT,
        entry_price=Decimal("100"),
        invalidation_price=Decimal("101"),
        take_profit_price=Decimal("98"),
        entry_reason="frozen-r315-test",
    )
    return Vt08B01Candidate(
        symbol="GBPUSD",
        side=DemoTradingSetupSide.SHORT,
        decision_at=_NOW,
        entry_anchor_hour=5,
        reference_h4=reference,
        candle2=candle2,
        protected_swing=protected,
        setup=setup,
        methodology_fingerprint=methodology_fingerprint(),
    )


def test_r38_executable_is_exact_r315_methodology_fingerprint() -> None:
    assert methodology_fingerprint() == R315_METHOD_FINGERPRINT


def test_candidate_translation_preserves_geometry_and_is_deterministic() -> None:
    first = cibo_setup_from_b01(_candidate())
    second = cibo_setup_from_b01(_candidate())
    assert first == second
    assert first.entry_type == R315_OPERATIONAL_ENTRY_TYPE == "market"
    assert first.intended_entry == Decimal("100")
    assert first.stop_loss == Decimal("101")
    assert first.take_profit == Decimal("98")


def test_posture_requests_attack_only_after_earned_cushion_without_floating_loss() -> None:
    assert request_cibo_posture(
        initial_balance=Decimal("2000"),
        balance=Decimal("2010"),
        equity=Decimal("2010"),
        current_aggregate_risk=Decimal("0"),
    ) is Vt08ForexCiboPosture.ATTACK
    assert request_cibo_posture(
        initial_balance=Decimal("2000"),
        balance=Decimal("2010"),
        equity=Decimal("2000"),
        current_aggregate_risk=Decimal("0"),
    ) is Vt08ForexCiboPosture.BANK
