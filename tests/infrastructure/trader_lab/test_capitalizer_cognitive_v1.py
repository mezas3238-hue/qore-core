from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerDecision,
    CapitalizerSession,
    CapitalizerStrategyIdentity,
    EvidenceStrength,
    ExecutionQuality,
    MarketState,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerExposurePosition,
    CapitalizerSide,
    factor_exposures,
)
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerLossCause,
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)
from qore.infrastructure.trader_lab.capitalizer_reasoning import (
    reason_capitalizer_opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_situation_model import (
    CapitalizerExecutionState,
    CapitalizerSituationModel,
)


def _execution(quality: ExecutionQuality = ExecutionQuality.GOOD) -> CapitalizerExecutionState:
    return CapitalizerExecutionState(
        spread_points=Decimal("0.1"),
        commission_cost_r=Decimal("0.02"),
        expected_slippage_r=Decimal("0.01"),
        quote_age_ms=50,
        observed_latency_ms=20,
        quality=quality,
    )


def _situation(
    *,
    symbol: str = "USDJPY",
    session: CapitalizerSession = CapitalizerSession.ASIA,
    hypothesis_id: str = "H-1",
    source_event_id: str = "E-1",
    execution_quality: ExecutionQuality = ExecutionQuality.GOOD,
    evidence_strength: EvidenceStrength = EvidenceStrength.HIGH,
    trigger_ready: bool = True,
    displacement_confirmed: bool = True,
    destination_available: bool = True,
    late_entry: bool = False,
    correlated_exposure_blocked: bool = False,
    contradictions: tuple[str, ...] = (),
    failure_state_fingerprint: str | None = None,
) -> CapitalizerSituationModel:
    return CapitalizerSituationModel(
        symbol=symbol,
        session=session,
        observed_at=datetime(2026, 9, 19, 10, 0, tzinfo=UTC),
        hypothesis_id=hypothesis_id,
        source_event_id=source_event_id,
        event_generation=1,
        market_state=MarketState.DISPLACEMENT,
        evidence_strength=evidence_strength,
        execution=_execution(execution_quality),
        strategy_trigger_ready=trigger_ready,
        displacement_confirmed=displacement_confirmed,
        destination_available=destination_available,
        late_entry=late_entry,
        correlated_exposure_blocked=correlated_exposure_blocked,
        contradictions=contradictions,
        failure_state_fingerprint=failure_state_fingerprint,
    )


def test_strategy_identity_is_fail_closed_and_has_no_authority() -> None:
    identity = CapitalizerStrategyIdentity()
    assert identity.runtime_mutation_allowed is False
    assert identity.risk_authority is False
    assert identity.production_authority is False
    with pytest.raises(ValueError, match="session execution ceiling"):
        CapitalizerStrategyIdentity(max_executions_per_session=3)


def test_session_universe_is_frozen() -> None:
    assert allowed_markets(CapitalizerSession.ASIA) == frozenset(
        {"USDJPY", "AUDJPY", "AUDUSD", "GBPJPY"}
    )
    assert allowed_markets(CapitalizerSession.LONDON) == frozenset({"EURUSD", "GBPUSD"})
    assert allowed_markets(CapitalizerSession.NEW_YORK) == frozenset(
        {"XAUUSD", "USDCAD", "NAS100"}
    )


def test_clean_causal_state_can_reach_execute_without_granting_capital_authority() -> None:
    decision = reason_capitalizer_opportunity(
        situation=_situation(),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    assert decision.decision is CapitalizerDecision.EXECUTE
    assert "ADVERSARIAL_CHECK_PASSED" in decision.reasons


def test_low_evidence_or_degraded_execution_waits() -> None:
    low = reason_capitalizer_opportunity(
        situation=_situation(evidence_strength=EvidenceStrength.LOW),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    degraded = reason_capitalizer_opportunity(
        situation=_situation(execution_quality=ExecutionQuality.DEGRADED),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    assert low.decision is CapitalizerDecision.WAIT
    assert degraded.decision is CapitalizerDecision.WAIT


def test_bad_execution_and_late_entry_fail_closed() -> None:
    bad = reason_capitalizer_opportunity(
        situation=_situation(execution_quality=ExecutionQuality.BAD),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    late = reason_capitalizer_opportunity(
        situation=_situation(late_entry=True),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    assert bad.decision is CapitalizerDecision.ABSTAIN
    assert late.decision is CapitalizerDecision.ABSTAIN


def test_abstain_kills_hypothesis_and_source_event() -> None:
    ledger = CapitalizerSessionLedger(CapitalizerSession.ASIA)
    killed = ledger.record_decision(
        decision=CapitalizerDecision.ABSTAIN,
        hypothesis_id="H-1",
        source_event_id="E-1",
    )
    decision = reason_capitalizer_opportunity(
        situation=_situation(),
        ledger=killed,
        loss_memory=CapitalizerLossMemory(),
    )
    assert decision.decision is CapitalizerDecision.ABSTAIN
    assert "HYPOTHESIS_ALREADY_KILLED" in decision.reasons
    assert "SOURCE_EVENT_ALREADY_KILLED" in decision.reasons


def test_session_budget_is_hard_ceiling_of_two_executions() -> None:
    ledger = CapitalizerSessionLedger(CapitalizerSession.ASIA)
    ledger = ledger.record_decision(
        decision=CapitalizerDecision.EXECUTE,
        hypothesis_id="H-1",
        source_event_id="E-1",
    )
    ledger = ledger.record_decision(
        decision=CapitalizerDecision.EXECUTE,
        hypothesis_id="H-2",
        source_event_id="E-2",
    )
    decision = reason_capitalizer_opportunity(
        situation=_situation(hypothesis_id="H-3", source_event_id="E-3"),
        ledger=ledger,
        loss_memory=CapitalizerLossMemory(),
    )
    assert ledger.execution_budget_remaining == 0
    assert decision.decision is CapitalizerDecision.ABSTAIN
    assert "SESSION_EXECUTION_BUDGET_EXHAUSTED" in decision.reasons


def test_unresolved_same_failure_state_blocks_repetition() -> None:
    loss = CapitalizerLossCause(
        loss_id="L-1",
        symbol="USDJPY",
        session=CapitalizerSession.ASIA,
        hypothesis_id="OLD-H",
        failure_state_fingerprint="fp-failed-break-no-displacement",
        realized_r=Decimal("-1"),
        causes=("FAILED_BREAK", "NO_DISPLACEMENT"),
    )
    decision = reason_capitalizer_opportunity(
        situation=_situation(
            hypothesis_id="NEW-H",
            source_event_id="NEW-E",
            failure_state_fingerprint="fp-failed-break-no-displacement",
        ),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(unresolved=(loss,)),
    )
    assert decision.decision is CapitalizerDecision.ABSTAIN
    assert "UNRESOLVED_FAILURE_STATE_REPEAT" in decision.reasons


def test_correlated_exposure_is_wait_not_a_second_blind_bet() -> None:
    decision = reason_capitalizer_opportunity(
        situation=_situation(correlated_exposure_blocked=True),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    assert decision.decision is CapitalizerDecision.WAIT
    assert "CORRELATED_EXPOSURE_BLOCKED" in decision.reasons


def test_exposure_graph_reveals_repeated_jpy_factor() -> None:
    exposures = factor_exposures(
        (
            CapitalizerExposurePosition(
                symbol="USDJPY",
                side=CapitalizerSide.LONG,
                risk_r=Decimal("0.10"),
            ),
            CapitalizerExposurePosition(
                symbol="AUDJPY",
                side=CapitalizerSide.LONG,
                risk_r=Decimal("0.10"),
            ),
            CapitalizerExposurePosition(
                symbol="GBPJPY",
                side=CapitalizerSide.LONG,
                risk_r=Decimal("0.10"),
            ),
        )
    )
    by_factor = {item.factor: item for item in exposures}
    assert by_factor["JPY"].net_r == Decimal("-0.30")
    assert by_factor["JPY"].gross_r == Decimal("0.30")
