from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import cast

import pytest
from _trader_fixtures import (
    BASE,
    build_trader_fixture,
    evaluate_producer,
    make_ohlc_snapshot,
    make_qualified_observation,
)

from qore.infrastructure.research_breakout_volatility_producer import (
    BreakoutVolatilityProducer,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchEvaluatorIdentityMismatchError,
    ResearchLineageValidationError,
)
from qore.infrastructure.research_schedule import W1_NO_WARMUP_V1
from qore.infrastructure.research_trader_signal import (
    TraderSignalSide,
    extract_trader_signal_side,
)

_REVISION = "qore.trader.breakout.v1"


def _producer() -> BreakoutVolatilityProducer:
    return BreakoutVolatilityProducer(
        lookback=1,
        breakout_margin=Decimal("0.01"),
        require_min_range=False,
        min_range=Decimal("0.01"),
    )


def _sides(bars: tuple[tuple[float, float, float], ...]) -> list[TraderSignalSide]:
    _, decisions = evaluate_producer(_producer(), software_revision=_REVISION, bars=bars)
    return [cast(TraderSignalSide, extract_trader_signal_side(d)) for d in decisions]


def test_identity_and_config_fingerprint() -> None:
    producer = _producer()
    assert producer.identity.family.value == "qore.trader.breakout"
    assert producer.identity.schema_version.value == "v1"
    assert len(producer.config_fingerprint) == 64


def test_invalid_config_fails_closed() -> None:
    with pytest.raises(ResearchLineageValidationError):
        BreakoutVolatilityProducer(
            lookback=0,
            breakout_margin=Decimal("0.01"),
            require_min_range=False,
            min_range=Decimal("0.01"),
        )
    with pytest.raises(ResearchLineageValidationError):
        BreakoutVolatilityProducer(
            lookback=cast(int, True),
            breakout_margin=Decimal("0.01"),
            require_min_range=False,
            min_range=Decimal("0.01"),
        )
    with pytest.raises(ResearchLineageValidationError):
        BreakoutVolatilityProducer(
            lookback=1,
            breakout_margin=Decimal("0"),
            require_min_range=False,
            min_range=Decimal("0.01"),
        )
    with pytest.raises(ResearchLineageValidationError):
        BreakoutVolatilityProducer(
            lookback=1,
            breakout_margin=Decimal("0.01"),
            require_min_range=cast(bool, 1),
            min_range=Decimal("0.01"),
        )
    with pytest.raises(ResearchLineageValidationError):
        BreakoutVolatilityProducer(
            lookback=1,
            breakout_margin=Decimal("0.01"),
            require_min_range=False,
            min_range=Decimal("-0.1"),
        )


def test_insufficient_and_exact_lookback_boundary() -> None:
    producer = BreakoutVolatilityProducer(
        lookback=2,
        breakout_margin=Decimal("0.01"),
        require_min_range=False,
        min_range=Decimal("0.01"),
    )
    _, decisions = evaluate_producer(
        producer,
        software_revision=_REVISION,
        bars=((1.0, 1.0, 1.0), (1.0, 1.0, 1.0)),
    )
    assert decisions == []
    _, decisions = evaluate_producer(
        producer,
        software_revision=_REVISION,
        bars=((1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)),
    )
    assert len(decisions) == 1


def test_buy_sell_and_abstain() -> None:
    prior = (1.0, 1.00, 0.90)  # high 1.00, low 0.90
    assert _sides((prior, (1.05, 1.05, 1.05))) == [TraderSignalSide.BUY]
    assert _sides((prior, (0.85, 0.85, 0.85))) == [TraderSignalSide.SELL]
    assert _sides((prior, (1.00, 1.00, 1.00))) == [TraderSignalSide.ABSTAIN]


def test_zero_prior_range_abstains() -> None:
    # prior range zero even though current close is far above -> ABSTAIN.
    assert _sides(((1.0, 1.00, 1.00), (1.05, 1.05, 1.05))) == [TraderSignalSide.ABSTAIN]


def test_boundary_equality_abstains() -> None:
    # upper = 1.00 * 1.01 = 1.01; current close exactly 1.01 -> ABSTAIN (not BUY).
    assert _sides(((1.0, 1.00, 0.90), (1.01, 1.01, 1.01))) == [TraderSignalSide.ABSTAIN]


def test_current_bar_not_in_own_threshold() -> None:
    # The current bar's own high/low must not define its breakout threshold.
    # Prior bar high/low = 1.00/0.90; current bar high=2.0 low=0.5 close=1.9.
    # Threshold must be prior_high*1.01=1.01, so close=1.9 -> BUY despite the
    # current bar's own high of 2.0.
    assert _sides(((1.0, 1.00, 0.90), (1.9, 2.0, 0.5))) == [TraderSignalSide.BUY]


def test_require_min_range_gate_abstains() -> None:
    producer = BreakoutVolatilityProducer(
        lookback=1,
        breakout_margin=Decimal("0.01"),
        require_min_range=True,
        min_range=Decimal("0.2"),
    )
    # prior range 0.10 < min_range * prior_low = 0.2 * 0.9 = 0.18 -> ABSTAIN.
    _, decisions = evaluate_producer(
        producer,
        software_revision=_REVISION,
        bars=((1.0, 1.00, 0.90), (1.05, 1.05, 1.05)),
    )
    assert [extract_trader_signal_side(d) for d in decisions] == [TraderSignalSide.ABSTAIN]


def test_deterministic_repetition() -> None:
    bars = ((1.0, 1.00, 0.90), (1.05, 1.05, 1.05), (1.02, 1.02, 1.02))
    first_states, first_decisions = evaluate_producer(
        _producer(),
        software_revision=_REVISION,
        bars=bars,
    )
    second_states, second_decisions = evaluate_producer(
        _producer(),
        software_revision=_REVISION,
        bars=bars,
    )
    assert first_states == second_states
    assert first_decisions == second_decisions


def test_chronology_conflict_fails_closed() -> None:
    fixture = build_trader_fixture(
        software_revision=_REVISION,
        bars=((1.0, 1.0, 1.0), (2.0, 2.0, 2.0)),
    )
    producer = _producer()
    state = producer.create_initial_state(
        strategy_binding=fixture.binding,
        start_policy=W1_NO_WARMUP_V1,
    )
    state, _ = producer.evaluate(
        strategy_binding=fixture.binding,
        prior_state=state,
        newly_visible_inputs=(fixture.qualified_observations[1],),
        simulated_now=fixture.qualified_observations[1].observation.available_at,
    )
    older = make_qualified_observation(
        fixture.manifest,
        make_ohlc_snapshot(
            9.0,
            9.0,
            9.0,
            index=99,
            opened_at=BASE,
            closed_at=BASE + timedelta(seconds=60),
        ),
        index=99,
    )
    with pytest.raises(ResearchLineageValidationError):
        producer.evaluate(
            strategy_binding=fixture.binding,
            prior_state=state,
            newly_visible_inputs=(older,),
            simulated_now=older.observation.available_at,
        )


def test_binding_revision_mismatch_fails_closed() -> None:
    fixture = build_trader_fixture(
        software_revision="qore.trader.breakout.other",
        bars=((1.0, 1.0, 1.0),),
    )
    producer = _producer()
    with pytest.raises(ResearchEvaluatorIdentityMismatchError):
        producer.create_initial_state(
            strategy_binding=fixture.binding,
            start_policy=W1_NO_WARMUP_V1,
        )
