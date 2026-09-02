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
from qore.infrastructure.research_mean_reversion_producer import MeanReversionProducer
from qore.infrastructure.research_schedule import W1_NO_WARMUP_V1
from qore.infrastructure.research_trader_signal import (
    TraderSignalSide,
    extract_trader_signal_side,
)

_REVISION = "qore.trader.meanreversion.v1"


def _producer() -> MeanReversionProducer:
    return MeanReversionProducer(lookback=1, deviation_threshold=Decimal("0.01"))


def _sides(bars: tuple[tuple[float, float, float], ...]) -> list[TraderSignalSide]:
    _, decisions = evaluate_producer(_producer(), software_revision=_REVISION, bars=bars)
    return [cast(TraderSignalSide, extract_trader_signal_side(d)) for d in decisions]


def test_identity_and_config_fingerprint() -> None:
    producer = _producer()
    assert producer.identity.family.value == "qore.trader.meanreversion"
    assert producer.identity.schema_version.value == "v1"
    assert len(producer.config_fingerprint) == 64


def test_invalid_config_fails_closed() -> None:
    with pytest.raises(ResearchLineageValidationError):
        MeanReversionProducer(lookback=0, deviation_threshold=Decimal("0.01"))
    with pytest.raises(ResearchLineageValidationError):
        MeanReversionProducer(lookback=cast(int, True), deviation_threshold=Decimal("0.01"))
    with pytest.raises(ResearchLineageValidationError):
        MeanReversionProducer(lookback=2, deviation_threshold=Decimal("-0.1"))
    with pytest.raises(ResearchLineageValidationError):
        MeanReversionProducer(lookback=2, deviation_threshold=Decimal("Infinity"))


def test_insufficient_and_exact_lookback_boundary() -> None:
    producer = MeanReversionProducer(lookback=2, deviation_threshold=Decimal("0.01"))
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
    # equilibrium (prior close) = 1.00; deviation_threshold = 0.01.
    # Each bar is (close, high, low); high/low must contain close for valid OHLC.
    assert _sides(((1.00, 1.0, 1.0), (0.90, 0.90, 0.90))) == [TraderSignalSide.BUY]
    assert _sides(((1.00, 1.0, 1.0), (1.05, 1.05, 1.05))) == [TraderSignalSide.SELL]
    assert _sides(((1.00, 1.0, 1.0), (1.00, 1.0, 1.0))) == [TraderSignalSide.ABSTAIN]


def test_flat_market_abstains() -> None:
    # lookback=1 -> first signal at the 2nd bar; all visible windows flat.
    bars = tuple((1.5, 1.5, 1.5) for _ in range(3))
    assert _sides(bars) == [TraderSignalSide.ABSTAIN, TraderSignalSide.ABSTAIN]


def test_boundary_equality_abstains() -> None:
    # Lane 2 falsification 2.2: prior [1.00], current 0.99 -> 0.99 < 0.99 false -> ABSTAIN.
    assert _sides(((1.00, 1.0, 1.0), (0.99, 0.99, 0.99))) == [TraderSignalSide.ABSTAIN]


def test_deterministic_repetition() -> None:
    bars = ((1.0, 1.0, 1.0), (1.02, 1.02, 1.02), (1.01, 1.01, 1.01))
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
        software_revision="qore.trader.meanreversion.other",
        bars=((1.0, 1.0, 1.0),),
    )
    producer = _producer()
    with pytest.raises(ResearchEvaluatorIdentityMismatchError):
        producer.create_initial_state(
            strategy_binding=fixture.binding,
            start_policy=W1_NO_WARMUP_V1,
        )
