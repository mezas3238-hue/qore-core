"""Frozen M15→M1 route-stage reconstruction without inventing tradable entries."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_direction_random_baseline_v1 import (
    _runs,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_m1_stage_chain_forensic_v1 import (
    STAGES,
    M1StageChainRow,
    StageObservation,
    reconstruct_source_chain,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)

START = datetime(2026, 1, 2, 12, tzinfo=UTC)


def _bar(i: int, o: str, h: str, low: str, c: str) -> CapitalizerM1Bar:
    t = START + timedelta(minutes=i)
    return CapitalizerM1Bar(
        symbol="EURUSD", opened_at=t, closed_at=t + timedelta(minutes=1),
        open=Decimal(o), high=Decimal(h), low=Decimal(low),
        close=Decimal(c), volume=10, digits=5,
    )


SWEEP = (
    _bar(0, "1.1000", "1.1010", "1.0995", "1.1005"),
    _bar(1, "1.1005", "1.1008", "1.0990", "1.0995"),
    _bar(2, "1.0995", "1.1002", "1.0993", "1.1000"),
    _bar(3, "1.1000", "1.1001", "1.0985", "1.0990"),
    _bar(4, "1.0990", "1.0994", "1.0988", "1.0991"),
    _bar(5, "1.0991", "1.1006", "1.0990", "1.1004"),
)


FVG = (
    _bar(0, "10.00", "10.10", "9.90", "10.05"),
    _bar(1, "10.05", "10.30", "10.00", "10.25"),
    _bar(2, "10.25", "10.50", "10.20", "10.45"),
    _bar(3, "10.45", "10.48", "10.05", "10.15"),
    _bar(4, "10.15", "10.25", "10.00", "10.08"),
    _bar(5, "10.08", "10.20", "9.95", "10.02"),
    _bar(6, "10.02", "10.20", "10.00", "10.12"),
    _bar(7, "10.12", "10.60", "10.10", "10.55"),
)


def _source(family: str, bars: tuple[CapitalizerM1Bar, ...]) -> V49Opportunity:
    side = "BULLISH"
    return V49Opportunity(
        symbol="EURUSD", session="LONDON", operating_date="2026-01-02",
        h1_state_direction=side,
        h1_state_from=(START-timedelta(hours=1)).isoformat(),
        h1_state_until=(START+timedelta(days=1)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:SWING_LOW",
        m15_setup_confirmed_at=START.isoformat(),
        m15_protected_swing_price="1.0950" if family=="LIQUIDITY_SWEEP_CISD" else "9.80",
        m1_trigger_confirmed_at=bars[-1].closed_at.isoformat(),
        m1_trigger_family=family,
        decision_reference_price=str(bars[-1].close),
        structural_target_witness_price="1.1100" if family=="LIQUIDITY_SWEEP_CISD" else "11.0",
    )


def _trade(source: V49Opportunity) -> V49EconomicTrade:
    t = source.m1_trigger_confirmed_at
    return V49EconomicTrade(
        symbol=source.symbol, session=source.session,
        operating_date=source.operating_date,
        ordinal_candidate_at=t, direction="LONG",
        entry_at=t, exit_at=(START+timedelta(hours=1)).isoformat(),
        entry_price=source.decision_reference_price,
        stop_price=source.m15_protected_swing_price,
        target_price=source.structural_target_witness_price,
        planned_reward_r="1", realized_gross_r="-1",
        exit_reason="STOP", m1_bars_held=2,
        trigger_family=source.m1_trigger_family,
        h1_state_basis=source.h1_state_basis,
        same_bar_stop_target_ambiguity=False,
    )


def _probe(
    source: V49Opportunity, bars: tuple[CapitalizerM1Bar, ...]
) -> M1StageChainRow:
    return reconstruct_source_chain(
        source, _trade(source), bars,
        tuple(b.opened_at for b in bars), _runs(bars),
    )


def test_sweep_stages_include_actual_sweep_and_zero_cisd_entry_delay() -> None:
    source = _source("LIQUIDITY_SWEEP_CISD", SWEEP)
    row = _probe(source, SWEEP)
    stages = {s.kind:s for s in row.stages}
    assert len(stages) == len(STAGES)
    assert stages["M1_SWEEP_CONFIRMED_BAR"].confirmed_at == SWEEP[3].closed_at.isoformat()
    assert stages["M1_CAUSAL_OPPOSING_SERIES_END"].confirmed_at is not None
    assert stages["M1_CISD_CONFIRMED"].confirmed_at == row.original_entry_at
    assert stages["ORIGINAL_ENTRY_EXECUTED"].confirmed_at == row.original_entry_at
    assert stages["M1_PROTECTED_SWING_BECOMES_VALID"].confirmed_at is None
    assert row.cisd_to_entry_minutes == "0"
    assert not any(s.hypothetically_tradeable for s in row.stages)


def test_fvg_stages_use_confirmed_fvg_retrace_and_real_m1_pivot() -> None:
    source = _source("FVG_RETRACE_CISD", FVG)
    row = _probe(source, FVG)
    stages = {s.kind:s for s in row.stages}
    assert stages["M1_FVG_FORMATION_CONFIRMED"].confirmed_at == FVG[2].closed_at.isoformat()
    assert stages["M1_FVG_RETRACE_CONFIRMED_BAR"].confirmed_at == FVG[3].closed_at.isoformat()
    assert stages["M1_FVG_PIVOT_BAR_CLOSE_UNPROTECTED"].confirmed_at is not None
    assert stages["M1_PROTECTED_SWING_BECOMES_VALID"].confirmed_at == row.original_entry_at
    assert row.fvg_or_sweep_to_cisd_minutes == "5.0"
    assert row.cisd_to_entry_minutes == "0"


def test_source_mutation_or_shifted_entry_fails_before_labelling() -> None:
    source = _source("LIQUIDITY_SWEEP_CISD", SWEEP)
    wrong_entry = replace(_trade(source), entry_price="1.0")
    with pytest.raises(ValueError, match="contract"):
        reconstruct_source_chain(
            source, wrong_entry, SWEEP,
            tuple(b.opened_at for b in SWEEP), _runs(SWEEP),
        )
    with pytest.raises(ValueError, match="original V49"):
        _probe(replace(source,m1_trigger_confirmed_at=SWEEP[-2].closed_at.isoformat()), SWEEP)


def test_outcome_cannot_authorize_stage_and_protected_m1_is_not_early() -> None:
    with pytest.raises(ValueError, match="diagnostic"):
        StageObservation("M1_CISD_CONFIRMED",None,None,None,None,None,
                         hypothetically_tradeable=True)
    source = _source("LIQUIDITY_SWEEP_CISD", SWEEP)
    row = _probe(source, SWEEP)
    with pytest.raises(ValueError, match="protected swing"):
        replace(row, m1_protected_swing_before_cisd=True)


def test_stage_future_labels_never_use_intrabar_live_price() -> None:
    source = _source("LIQUIDITY_SWEEP_CISD", SWEEP)
    row = _probe(source, SWEEP)
    stages = {s.kind:s for s in row.stages}
    assert stages["M1_SWEEP_CONFIRMED_BAR"].price_close_asof == str(SWEEP[3].close)
    assert stages["M1_CISD_CONFIRMED"].price_close_asof == str(SWEEP[5].close)
    assert stages["M1_SWEEP_CONFIRMED_BAR"].label_uses_future_return
