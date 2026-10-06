from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardPopulationDisposition,
)
from qore.infrastructure.cibo_ce2i_phase20_m5_shadow_batch import (
    Phase20M5ShadowTerminal,
    build_ctrader_demo_m5_observed_opportunity,
    build_ctrader_demo_m5_phase20_batch,
)
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoSymbolSpecification,
)
from qore.infrastructure.r34_xauusd_live import R34LiveSignal

OPENED = datetime(2026, 9, 27, 18, 30, tzinfo=UTC)
DEADLINE = OPENED + timedelta(seconds=2)


def _spec() -> CTraderDemoSymbolSpecification:
    return CTraderDemoSymbolSpecification(
        provider_symbol="XAUUSD",
        bid=Decimal("100.0"),
        ask=Decimal("100.1"),
        spread_points=Decimal("1"),
        digits=1,
        point=Decimal("0.1"),
        contract_size=Decimal("100"),
        tick_size=Decimal("0.1"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
        volume_step=Decimal("1"),
        minimum_stop_distance_points=Decimal("1"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("10"),
        trade_enabled=True,
        session_open=True,
        observed_at=OPENED + timedelta(milliseconds=50),
        open_commission_per_lot_usd=Decimal("0"),
    )


def _r34_signal() -> R34LiveSignal:
    return R34LiveSignal(
        signal_fingerprint="a" * 64,
        entry_at=OPENED,
        timeframe="H1",
        side="long",
        certified_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        target_rank=1,
        target_route="TEST",
        decision_source="TEST",
        family=None,
        risk_scale=Decimal("1"),
    )


def _non_candidate(
    identity: str,
    symbol: str,
    offset_ms: int,
) -> Phase20M5ShadowTerminal:
    return Phase20M5ShadowTerminal(
        identity=identity,
        symbol=symbol,
        observed_at=OPENED + timedelta(milliseconds=offset_ms),
        disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
        reason="CAUSAL_ABSTAIN",
    )


def test_m5_shadow_batch_preserves_complete_five_slot_population() -> None:
    observed = build_ctrader_demo_m5_observed_opportunity(
        identity="R34_XAUUSD",
        signal=_r34_signal(),
        provider_spec=_spec(),
        observed_at=OPENED + timedelta(milliseconds=300),
    )
    batch = build_ctrader_demo_m5_phase20_batch(
        epoch_scope="ctrader-demo:m5",
        opened_at=OPENED,
        deadline_at=DEADLINE,
        terminals=(
            _non_candidate("R43_GBPUSD", "GBPUSD", 180),
            Phase20M5ShadowTerminal(
                identity="R34_XAUUSD",
                symbol="XAUUSD",
                observed_at=OPENED + timedelta(milliseconds=300),
                disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
                reason="VALID_TRADER_OPPORTUNITY",
                opportunity=observed,
            ),
            _non_candidate("R38_GBPJPY", "GBPJPY", 220),
            _non_candidate("R38_EURUSD", "EURUSD", 240),
            _non_candidate("R42_AUDJPY", "AUDJPY", 260),
        ),
    )

    assert len(batch.population_slots) == 5
    assert len(batch.opportunities) == 1
    assert batch.opportunities[0].opportunity.signal_fingerprint == "a" * 64
    assert batch.opportunities[0].concentration_group == "SYMBOL:XAUUSD"
    assert batch.decision_at == OPENED + timedelta(milliseconds=300)
    dispositions = {
        item.slot_id: item.disposition
        for item in batch.population_slots
    }
    assert (
        dispositions["R34_XAUUSD|XAUUSD"]
        is Phase20ForwardPopulationDisposition.CANDIDATE
    )


def test_m5_shadow_batch_turns_late_actor_into_deadline_miss() -> None:
    late = build_ctrader_demo_m5_observed_opportunity(
        identity="R34_XAUUSD",
        signal=_r34_signal(),
        provider_spec=_spec(),
        observed_at=OPENED + timedelta(milliseconds=300),
    )
    batch = build_ctrader_demo_m5_phase20_batch(
        epoch_scope="ctrader-demo:m5",
        opened_at=OPENED,
        deadline_at=DEADLINE,
        terminals=(
            _non_candidate("R43_GBPUSD", "GBPUSD", 180),
            Phase20M5ShadowTerminal(
                identity="R34_XAUUSD",
                symbol="XAUUSD",
                observed_at=DEADLINE + timedelta(milliseconds=1),
                disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
                reason="LATE_VALID_TRADER_OPPORTUNITY",
                opportunity=late,
            ),
            _non_candidate("R38_GBPJPY", "GBPJPY", 220),
            _non_candidate("R38_EURUSD", "EURUSD", 240),
            _non_candidate("R42_AUDJPY", "AUDJPY", 260),
        ),
    )

    assert batch.decision_at == DEADLINE
    assert batch.opportunities == ()
    xau = next(
        item
        for item in batch.population_slots
        if item.slot_id == "R34_XAUUSD|XAUUSD"
    )
    assert xau.disposition is Phase20ForwardPopulationDisposition.DEADLINE_MISSED
    assert xau.reason == "DECISION_EPOCH_DEADLINE_MISSED"
