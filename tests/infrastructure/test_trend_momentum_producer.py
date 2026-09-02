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

from qore.infrastructure.research_lineage_errors import (
    ResearchEvaluatorIdentityMismatchError,
    ResearchLineageValidationError,
)
from qore.infrastructure.research_schedule import W1_NO_WARMUP_V1
from qore.infrastructure.research_trader_signal import (
    TraderSignalSide,
    extract_trader_signal_side,
)
from qore.infrastructure.research_trend_momentum_producer import TrendMomentumProducer

_REVISION = "qore.trader.trend.v1"


def _sides(bars: tuple[tuple[float, float, float], ...]) -> list[TraderSignalSide]:
    producer = TrendMomentumProducer(
        short_lookback=1,
        long_lookback=2,
        min_strength=Decimal("0.01"),
    )
    _, decisions = evaluate_producer(producer, software_revision=_REVISION, bars=bars)
    return [cast(TraderSignalSide, extract_trader_signal_side(d)) for d in decisions]


def test_identity_and_config_fingerprint() -> None:
    producer = TrendMomentumProducer(
        short_lookback=1,
        long_lookback=2,
        min_strength=Decimal("0.01"),
    )
    assert producer.identity.family.value == "qore.trader.trend"
    assert producer.identity.schema_version.value == "v1"
    assert len(producer.config_fingerprint) == 64


def test_invalid_config_fails_closed() -> None:
    with pytest.raises(ResearchLineageValidationError):
        TrendMomentumProducer(short_lookback=0, long_lookback=2, min_strength=Decimal("0.01"))
    with pytest.raises(ResearchLineageValidationError):
        TrendMomentumProducer(
            short_lookback=cast(int, True),
            long_lookback=2,
            min_strength=Decimal("0.01"),
        )
    with pytest.raises(ResearchLineageValidationError):
        TrendMomentumProducer(short_lookback=2, long_lookback=2, min_strength=Decimal("0.01"))
    with pytest.raises(ResearchLineageValidationError):
        TrendMomentumProducer(short_lookback=1, long_lookback=3, min_strength=Decimal("NaN"))
    with pytest.raises(ResearchLineageValidationError):
        TrendMomentumProducer(short_lookback=1, long_lookback=3, min_strength=Decimal("0"))


def test_insufficient_and_exact_lookback_boundary() -> None:
    producer = TrendMomentumProducer(
        short_lookback=1,
        long_lookback=3,
        min_strength=Decimal("0.01"),
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
        bars=((1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (2.0, 2.0, 2.0)),
    )
    assert len(decisions) == 1


def test_buy_sell_and_abstain() -> None:
    assert _sides(((3.0, 3.0, 3.0), (4.0, 4.0, 4.0))) == [TraderSignalSide.BUY]
    assert _sides(((4.0, 4.0, 4.0), (3.0, 3.0, 3.0))) == [TraderSignalSide.SELL]
    assert _sides(((2.0, 2.0, 2.0), (2.0, 2.0, 2.0))) == [TraderSignalSide.ABSTAIN]


def test_flat_market_abstains() -> None:
    # short=1, long=2 -> first signal at the 2nd bar; all visible windows flat.
    bars = tuple((1.5, 1.5, 1.5) for _ in range(4))
    assert _sides(bars) == [
        TraderSignalSide.ABSTAIN,
        TraderSignalSide.ABSTAIN,
        TraderSignalSide.ABSTAIN,
    ]


def test_boundary_equality_abstains() -> None:
    # Lane 2 falsification 2.1: closes [1.00, 1.01] -> momentum inside band -> ABSTAIN.
    assert _sides(((1.00, 1.0, 1.0), (1.01, 1.01, 1.01))) == [TraderSignalSide.ABSTAIN]


def test_deterministic_repetition() -> None:
    bars = ((1.0, 1.0, 1.0), (1.1, 1.1, 1.1), (1.3, 1.3, 1.3))
    first_states, first_decisions = evaluate_producer(
        TrendMomentumProducer(short_lookback=1, long_lookback=2, min_strength=Decimal("0.01")),
        software_revision=_REVISION,
        bars=bars,
    )
    second_states, second_decisions = evaluate_producer(
        TrendMomentumProducer(short_lookback=1, long_lookback=2, min_strength=Decimal("0.01")),
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
    producer = TrendMomentumProducer(
        short_lookback=1,
        long_lookback=2,
        min_strength=Decimal("0.01"),
    )
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
        software_revision="qore.trader.trend.other-revision",
        bars=((1.0, 1.0, 1.0),),
    )
    producer = TrendMomentumProducer(
        short_lookback=1,
        long_lookback=2,
        min_strength=Decimal("0.01"),
    )
    with pytest.raises(ResearchEvaluatorIdentityMismatchError):
        producer.create_initial_state(
            strategy_binding=fixture.binding,
            start_policy=W1_NO_WARMUP_V1,
        )
