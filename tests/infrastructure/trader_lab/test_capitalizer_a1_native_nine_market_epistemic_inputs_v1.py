"""Nine-market actual cognition input types: honest missing quotes/clock/causality."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.capitalizer_a1_native_nine_market_bar_witness_v1 import (
    A1NativeMarketObservation,
)
from qore.infrastructure.trader_lab.capitalizer_a1_native_nine_market_epistemic_inputs_v1 import (
    A1NineMarketNativeCognitiveInputs,
    build_epistemic_inputs,
)
from qore.infrastructure.trader_lab.capitalizer_cross_market_causality import (
    CapitalizerCrossMarketRelation,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerPerceptionStatus,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeResolution,
    assess_regime,
)

T = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


def _observations(
    *, incomplete: str | None = None,
) -> tuple[A1NativeMarketObservation, ...]:
    return tuple(
        A1NativeMarketObservation(
            symbol=s,
            decision_at=T.isoformat(),
            last_native_m1_closed_at=(
                (T-timedelta(minutes=1)).isoformat()
                if s == incomplete else T.isoformat()
            ),
            last_native_m1_opened_at=(
                (T-timedelta(minutes=2)).isoformat()
                if s == incomplete
                else (T-timedelta(minutes=1)).isoformat()
            ),
            last_completed_close="1.23456",
            has_exact_predecision_m1=(s != incomplete),
        )
        for s in sorted(NINE_MARKET_UNIVERSE)
    )


def test_nine_native_m1_can_be_typed_into_real_full_frame_contracts() -> None:
    evidence = build_epistemic_inputs(observations=_observations())
    assert evidence.complete_exact_native_m1
    assert evidence.observed_at == T
    assert len(evidence.perceptions) == 9
    assert len(evidence.regimes) == 9
    assert len(evidence.cross_market_graph.edges) == 36
    assert all(
        p.assessment.status is CapitalizerPerceptionStatus.BAD
        for p in evidence.perceptions
    )
    assert all(
        set(p.assessment.reasons) >= {"SESSION_CLOCK_INVALID"}
        for p in evidence.perceptions
    )
    assert all(
        assess_regime(r).resolution is CapitalizerRegimeResolution.UNRESOLVED
        for r in evidence.regimes
    )
    assert all(
        e.relation is CapitalizerCrossMarketRelation.UNKNOWN
        for e in evidence.cross_market_graph.edges
    )
    assert not evidence.broker_quotes_proven
    assert not evidence.session_clock_proven
    assert not evidence.portfolio_ledger_proven
    assert not evidence.full_cognitive_frame_executed


def test_missing_exact_one_native_market_is_visible_not_forward_filled() -> None:
    symbol = "GBPJPY"
    evidence = build_epistemic_inputs(observations=_observations(incomplete=symbol))
    assert not evidence.complete_exact_native_m1
    perceptions = {p.symbol: p for p in evidence.perceptions}
    assert "BARS_INCOMPLETE" in perceptions[symbol].assessment.reasons
    assert "BARS_INCOMPLETE" not in perceptions["EURUSD"].assessment.reasons
    assert len(evidence.perceptions) == len(NINE_MARKET_UNIVERSE)
    assert len(evidence.cross_market_graph.edges) == 36


def test_future_data_duplicate_market_fake_quote_and_wrong_bar_time_rejected() -> None:
    original = _observations()
    with pytest.raises(ValueError, match="duplicate|unduplicated"):
        build_epistemic_inputs(observations=(*original[:-1], original[0]))
    with pytest.raises(ValueError, match="must be same|timestamps"):
        build_epistemic_inputs(observations=(
            replace(
                original[0], decision_at=(T+timedelta(minutes=1)).isoformat(),
                last_native_m1_closed_at=(T+timedelta(minutes=1)).isoformat(),
            ),
            *original[1:],
        ))
    with pytest.raises(ValueError, match="never attest broker"):
        replace(original[0], bid_ask_quote_available=True)
    with pytest.raises(ValueError, match="closure was invented"):
        replace(
            build_epistemic_inputs(observations=original),
            complete_exact_native_m1=False,
        )
    with pytest.raises(ValueError, match="missing full cognition"):
        replace(
            build_epistemic_inputs(observations=original),
            full_cognitive_frame_executed=True,
        )


def test_no_false_good_perception_or_supported_market_regime_allowed() -> None:
    inputs: A1NineMarketNativeCognitiveInputs = build_epistemic_inputs(
        observations=_observations()
    )
    assert all(r.family_id is None for r in inputs.regimes)
    assert all(not r.contradictions for r in inputs.regimes)
    assert all(p.observed_at == T for p in inputs.perceptions)
