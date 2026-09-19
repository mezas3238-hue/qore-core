from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_behavior_lab import (
    CapitalizerBehaviorEpisode,
    CapitalizerBehaviorOutcome,
    CapitalizerBehaviorSnapshot,
    CapitalizerFeatureValue,
    behavior_episode_fingerprint,
)
from qore.infrastructure.trader_lab.capitalizer_behavior_metrics import (
    build_behavior_report,
    compute_behavior_metrics,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    EvidenceStrength,
    ExecutionQuality,
    MarketState,
)
from qore.infrastructure.trader_lab.capitalizer_cost_stress import (
    CapitalizerCostStressSpec,
    apply_cost_stress,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_situation_model import (
    CapitalizerExecutionState,
)


_NOW = datetime(2026, 9, 19, 10, 0, tzinfo=UTC)


def _execution() -> CapitalizerExecutionState:
    return CapitalizerExecutionState(
        spread_points=Decimal("0.1"),
        commission_cost_r=Decimal("0.02"),
        expected_slippage_r=Decimal("0.01"),
        quote_age_ms=25,
        observed_latency_ms=15,
        quality=ExecutionQuality.GOOD,
    )


def _episode(
    *,
    episode_id: str,
    net_r: Decimal,
    minute: int,
    symbol: str = "USDJPY",
    session: CapitalizerSession = CapitalizerSession.ASIA,
) -> CapitalizerBehaviorEpisode:
    decision_at = _NOW + timedelta(minutes=minute)
    gross_r = net_r + Decimal("0.03")
    snapshot = CapitalizerBehaviorSnapshot(
        episode_id=episode_id,
        symbol=symbol,
        session=session,
        decision_at=decision_at,
        hypothesis_id=f"H-{episode_id}",
        source_event_id=f"E-{episode_id}",
        event_generation=1,
        side=CapitalizerSide.LONG,
        market_state=MarketState.DISPLACEMENT,
        state_family_id=f"{session.value}_{symbol}_DISPLACEMENT",
        evidence_strength=EvidenceStrength.HIGH,
        execution=_execution(),
        features=(
            CapitalizerFeatureValue(
                name="DISPLACEMENT_STATE",
                value="CONFIRMED",
                observed_at=decision_at,
            ),
            CapitalizerFeatureValue(
                name="SESSION_PHASE",
                value="ACTIVE",
                observed_at=decision_at - timedelta(seconds=1),
            ),
        ),
    )
    return CapitalizerBehaviorEpisode(
        snapshot=snapshot,
        outcome=CapitalizerBehaviorOutcome(
            episode_id=episode_id,
            closed_at=decision_at + timedelta(minutes=2),
            gross_r=gross_r,
            explicit_cost_r=Decimal("0.03"),
            net_r=net_r,
            exit_reason="STRUCTURAL_EXIT",
            loss_cause_tags=("FAILED_DELIVERY",) if net_r < 0 else (),
        ),
    )


def test_behavior_snapshot_rejects_future_feature() -> None:
    decision_at = _NOW
    with pytest.raises(ValueError, match="future feature"):
        CapitalizerBehaviorSnapshot(
            episode_id="EP-FUTURE",
            symbol="USDJPY",
            session=CapitalizerSession.ASIA,
            decision_at=decision_at,
            hypothesis_id="H-FUTURE",
            source_event_id="E-FUTURE",
            event_generation=1,
            side=CapitalizerSide.LONG,
            market_state=MarketState.DISPLACEMENT,
            state_family_id="ASIA_USDJPY_DISPLACEMENT",
            evidence_strength=EvidenceStrength.HIGH,
            execution=_execution(),
            features=(
                CapitalizerFeatureValue(
                    name="FUTURE_FEATURE",
                    value="LEAK",
                    observed_at=decision_at + timedelta(microseconds=1),
                ),
            ),
        )


def test_outcome_is_physically_separate_and_cannot_predate_decision() -> None:
    snapshot = _episode(
        episode_id="EP-1",
        net_r=Decimal("0.5"),
        minute=0,
    ).snapshot
    outcome = CapitalizerBehaviorOutcome(
        episode_id="EP-1",
        closed_at=snapshot.decision_at - timedelta(seconds=1),
        gross_r=Decimal("0.53"),
        explicit_cost_r=Decimal("0.03"),
        net_r=Decimal("0.50"),
        exit_reason="INVALID",
    )
    with pytest.raises(ValueError, match="cannot predate"):
        CapitalizerBehaviorEpisode(snapshot=snapshot, outcome=outcome)


def test_behavior_episode_fingerprint_is_deterministic() -> None:
    episode = _episode(episode_id="EP-FP", net_r=Decimal("0.4"), minute=0)
    assert behavior_episode_fingerprint(episode) == behavior_episode_fingerprint(episode)
    assert len(behavior_episode_fingerprint(episode)) == 64


def test_metrics_compute_net_pf_drawdown_and_losing_streak() -> None:
    episodes = (
        _episode(episode_id="A", net_r=Decimal("1.0"), minute=0),
        _episode(episode_id="B", net_r=Decimal("-0.5"), minute=1),
        _episode(episode_id="C", net_r=Decimal("-0.25"), minute=2),
        _episode(episode_id="D", net_r=Decimal("0.5"), minute=3),
    )
    metrics = compute_behavior_metrics(episodes)
    assert metrics.trades == 4
    assert metrics.wins == 2
    assert metrics.losses == 2
    assert metrics.flats == 0
    assert metrics.total_r == Decimal("0.75")
    assert metrics.gross_profit_r == Decimal("1.5")
    assert metrics.gross_loss_r == Decimal("0.75")
    assert metrics.profit_factor == Decimal("2")
    assert metrics.max_drawdown_r == Decimal("0.75")
    assert metrics.max_losing_streak == 2


def test_behavior_report_separates_session_and_market_cells() -> None:
    episodes = (
        _episode(episode_id="A1", net_r=Decimal("0.4"), minute=0),
        _episode(
            episode_id="L1",
            net_r=Decimal("0.3"),
            minute=10,
            symbol="EURUSD",
            session=CapitalizerSession.LONDON,
        ),
        _episode(
            episode_id="N1",
            net_r=Decimal("-0.2"),
            minute=20,
            symbol="XAUUSD",
            session=CapitalizerSession.NEW_YORK,
        ),
    )
    report = build_behavior_report(episodes)
    assert report.total.trades == 3
    session_counts = {item.session: item.metrics.trades for item in report.by_session}
    assert session_counts == {
        CapitalizerSession.ASIA: 1,
        CapitalizerSession.LONDON: 1,
        CapitalizerSession.NEW_YORK: 1,
    }
    cells = {(item.session, item.symbol): item.metrics.trades for item in report.by_session_market}
    assert cells[(CapitalizerSession.ASIA, "USDJPY")] == 1
    assert cells[(CapitalizerSession.LONDON, "EURUSD")] == 1
    assert cells[(CapitalizerSession.NEW_YORK, "XAUUSD")] == 1


def test_cost_stress_can_destroy_marginal_scalping_edge_without_changing_snapshot() -> None:
    episode = _episode(episode_id="EDGE", net_r=Decimal("0.05"), minute=0)
    stressed = apply_cost_stress(
        (episode,),
        spec=CapitalizerCostStressSpec(
            additional_spread_r=Decimal("0.02"),
            additional_commission_r=Decimal("0.02"),
            additional_slippage_r=Decimal("0.02"),
        ),
    )
    assert stressed[0].snapshot is episode.snapshot
    assert stressed[0].outcome.net_r == Decimal("-0.01")
    assert stressed[0].outcome.explicit_cost_r == Decimal("0.09")


def test_execution_portability_fails_closed_until_every_environment_qualifies() -> None:
    from qore.infrastructure.trader_lab.capitalizer_execution_portability import (
        CapitalizerEnvironmentQualification,
        CapitalizerEnvironmentStatus,
        CapitalizerExecutionEnvironment,
        evaluate_execution_portability,
    )

    qualifications = (
        CapitalizerEnvironmentQualification(
            environment=CapitalizerExecutionEnvironment.IC_MARKETS_RAW,
            profile_fingerprint="1" * 64,
            status=CapitalizerEnvironmentStatus.QUALIFIED,
            evidence_fingerprint="a" * 64,
        ),
        CapitalizerEnvironmentQualification(
            environment=CapitalizerExecutionEnvironment.FTMO,
            profile_fingerprint="2" * 64,
            status=CapitalizerEnvironmentStatus.QUALIFIED,
            evidence_fingerprint="b" * 64,
        ),
        CapitalizerEnvironmentQualification(
            environment=CapitalizerExecutionEnvironment.FUNDEDNEXT,
            profile_fingerprint="3" * 64,
            status=CapitalizerEnvironmentStatus.REJECTED,
            evidence_fingerprint="c" * 64,
        ),
    )
    decision = evaluate_execution_portability(qualifications)
    assert decision.qualified is False
    assert "NOT_QUALIFIED:FUNDEDNEXT:REJECTED" in decision.reasons
    assert "MISSING:ADVERSE_PORTABILITY_ENVELOPE" in decision.reasons


def test_execution_portability_requires_same_candidate_to_survive_all_target_domains() -> None:
    from qore.infrastructure.trader_lab.capitalizer_execution_portability import (
        CapitalizerEnvironmentQualification,
        CapitalizerEnvironmentStatus,
        CapitalizerExecutionEnvironment,
        MANDATORY_EXECUTION_ENVIRONMENTS,
        evaluate_execution_portability,
    )

    qualifications = tuple(
        CapitalizerEnvironmentQualification(
            environment=environment,
            profile_fingerprint=f"{index:x}" * 64,
            status=CapitalizerEnvironmentStatus.QUALIFIED,
            evidence_fingerprint=f"{index + 8:x}" * 64,
        )
        for index, environment in enumerate(MANDATORY_EXECUTION_ENVIRONMENTS, start=1)
    )
    decision = evaluate_execution_portability(qualifications)
    assert decision.qualified is True
    assert decision.reasons == ()
