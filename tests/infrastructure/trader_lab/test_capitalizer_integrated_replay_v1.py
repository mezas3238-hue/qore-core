from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_integrated_replay_v1 import (
    CapitalizerIntegratedReplayFrame,
    CapitalizerIntegratedReplayState,
    CapitalizerReplayEvidenceProvenance,
    CapitalizerReplayResolutionEvidence,
    CapitalizerReplayRiskDecision,
    cibo_m5_context_evidence,
    run_integrated_replay,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2 import (
    CapitalizerSourceEntryRoute,
    CapitalizerSourceStrategyAssessment,
    CapitalizerSourceStrategyDecision,
    SOURCE_STRATEGY_GRAMMAR_ID,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
    CapitalizerSourceTradePlan,
)
from qore.infrastructure.trader_lab.capitalizer_source_trader_engine_v2 import (
    CapitalizerSourceTraderEngineAssessment,
)
from qore.infrastructure.trader_lab.capitalizer_source_trader_pipeline_v2 import (
    CapitalizerSourcePipelineAssessment,
    CapitalizerSourcePipelineState,
)


_BASE = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
_OPERATING_DATE = date(2026, 1, 5)


def _ready_pipeline(symbol: str) -> CapitalizerSourcePipelineAssessment:
    route = CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION
    strategy = CapitalizerSourceStrategyAssessment(
        grammar_id=SOURCE_STRATEGY_GRAMMAR_ID,
        symbol=symbol,
        route=route,
        decision=CapitalizerSourceStrategyDecision.ELIGIBLE_FOR_QORE_RISK,
        reasons=("SOURCE_READY",),
    )
    plan = CapitalizerSourceTradePlan(
        symbol=symbol,
        side=CapitalizerSide.LONG,
        route=route,
        entry_price=Decimal("1.1000"),
        initial_stop_price=Decimal("1.0900"),
        target_price=Decimal("1.1200"),
        target_kind=CapitalizerSourceTargetKind.RECENT_DAILY_HIGH_LOW,
    )
    engine = CapitalizerSourceTraderEngineAssessment(
        symbol=symbol,
        route=route,
        strategy_assessment=strategy,
        trade_plan=plan,
        passes_to_qore_risk=True,
        reasons=("SOURCE_READY",),
    )
    return CapitalizerSourcePipelineAssessment(
        symbol=symbol,
        route=route,
        state=CapitalizerSourcePipelineState.PRE_RISK_READY,
        source_engine=engine,
        reasons=("SOURCE_READY",),
    )


def _native_m1(record_id: str = "m1:1") -> CapitalizerReplayResolutionEvidence:
    return CapitalizerReplayResolutionEvidence(
        resolution_seconds=60,
        provenance=CapitalizerReplayEvidenceProvenance.PROVIDER_NATIVE,
        source_record_id=record_id,
    )


def _authorized_frame(
    *,
    symbol: str = "USDJPY",
    session: CapitalizerSession = CapitalizerSession.ASIA,
    observed_at: datetime = _BASE,
) -> CapitalizerIntegratedReplayFrame:
    return CapitalizerIntegratedReplayFrame(
        symbol=symbol,
        session=session,
        operating_date=_OPERATING_DATE,
        observed_at=observed_at,
        cognitive_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
        source_pipeline=_ready_pipeline(symbol),
        resolution_evidence=(_native_m1(f"m1:{symbol}:{observed_at.isoformat()}"),),
        risk_decision=CapitalizerReplayRiskDecision.AUTHORIZED,
        risk_decision_id=f"risk:{symbol}:{observed_at.isoformat()}",
        risk_reasons=("QORE_RISK_RESEARCH_AUTHORIZED",),
    )


def test_consumed_cibo_m5_cannot_be_promoted_to_m1_execution() -> None:
    with pytest.raises(ValueError, match="CIBO M5 alone"):
        CapitalizerIntegratedReplayFrame(
            symbol="USDJPY",
            session=CapitalizerSession.ASIA,
            operating_date=_OPERATING_DATE,
            observed_at=_BASE,
            cognitive_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
            source_pipeline=_ready_pipeline("USDJPY"),
            resolution_evidence=(
                cibo_m5_context_evidence(source_record_id="atlas:USDJPY:2016-2026"),
            ),
        )


def test_native_m1_can_reach_pre_risk_without_implicit_execution() -> None:
    frame = CapitalizerIntegratedReplayFrame(
        symbol="USDJPY",
        session=CapitalizerSession.ASIA,
        operating_date=_OPERATING_DATE,
        observed_at=_BASE,
        cognitive_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
        source_pipeline=_ready_pipeline("USDJPY"),
        resolution_evidence=(_native_m1(),),
    )

    report = run_integrated_replay((frame,), require_full_universe=False)

    assert report.simulated_executions == 0
    assert report.events[0].state is CapitalizerIntegratedReplayState.PRE_RISK_READY


def test_qore_risk_authorized_research_admission_honors_max3() -> None:
    frames = tuple(
        _authorized_frame(observed_at=_BASE + timedelta(minutes=index))
        for index in range(4)
    )

    report = run_integrated_replay(frames, require_full_universe=False)

    assert report.simulated_executions == 3
    assert report.max_session_executions_observed == 3
    assert [
        event.state for event in report.events
    ] == [
        CapitalizerIntegratedReplayState.SIMULATED_EXECUTION,
        CapitalizerIntegratedReplayState.SIMULATED_EXECUTION,
        CapitalizerIntegratedReplayState.SIMULATED_EXECUTION,
        CapitalizerIntegratedReplayState.SESSION_CAP_REACHED,
    ]
    assert [
        event.session_execution_ordinal for event in report.events
    ] == [1, 2, 3, None]


def test_same_timestamp_overcapacity_requires_upstream_competition_resolution() -> None:
    frames = (
        _authorized_frame(symbol="USDJPY"),
        _authorized_frame(symbol="AUDJPY"),
        _authorized_frame(symbol="AUDUSD"),
        _authorized_frame(symbol="GBPJPY"),
    )

    with pytest.raises(ValueError, match="opportunity competition unresolved"):
        run_integrated_replay(frames, require_full_universe=False)


def test_non_pass_cognition_cannot_run_source_pipeline() -> None:
    with pytest.raises(ValueError, match="source strategy cannot run"):
        CapitalizerIntegratedReplayFrame(
            symbol="USDJPY",
            session=CapitalizerSession.ASIA,
            operating_date=_OPERATING_DATE,
            observed_at=_BASE,
            cognitive_decision=CapitalizerCognitiveGateDecision.WAIT,
            source_pipeline=_ready_pipeline("USDJPY"),
            resolution_evidence=(_native_m1(),),
        )


def test_full_integrated_replay_requires_all_nine_markets() -> None:
    frame = CapitalizerIntegratedReplayFrame(
        symbol="USDJPY",
        session=CapitalizerSession.ASIA,
        operating_date=_OPERATING_DATE,
        observed_at=_BASE,
        cognitive_decision=CapitalizerCognitiveGateDecision.WAIT,
        source_pipeline=None,
        resolution_evidence=(
            cibo_m5_context_evidence(source_record_id="atlas:USDJPY:context"),
        ),
    )

    with pytest.raises(ValueError, match="universe mismatch"):
        run_integrated_replay((frame,), require_full_universe=True)
