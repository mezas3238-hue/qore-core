from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_arch2_t02_lifecycle_intake import (
    T02LifecycleTerminalIntake,
)
from qore.infrastructure.cibo_arch2_t02_structural_binding import (
    bind_t02_structural_outcome,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardOutcomeSeal,
)
from qore.infrastructure.cibo_ce2i_t02_terminal_reason_evidence import (
    T02TerminalReason,
    T02TerminalReasonEvidence,
    T02TerminalReasonSource,
)

T0 = datetime(2026, 10, 2, 0, 0, tzinfo=UTC)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _outcome() -> Phase20ForwardOutcomeSeal:
    return Phase20ForwardOutcomeSeal(
        evidence_id="phase20-outcome-1",
        decision_evidence_sha256=_sha("1"),
        signal_fingerprint="signal-1",
        position_id=7001,
        execution_risk_evidence_id="risk-1",
        settlement_deal_ids=(8001, 8002),
        fill_evidence_refs=("fill-1",),
        observed_at=T0 + timedelta(minutes=10),
        realized_net_pnl_usd=Decimal("-1"),
        executed_initial_stop_risk_usd=Decimal("2"),
        realized_structural_outcome_r=Decimal("-0.5"),
        capital_deployed_at=T0 + timedelta(minutes=1),
        capital_released_at=T0 + timedelta(minutes=9),
        capital_minutes=Decimal("8"),
    )


def _row() -> ArchBForwardEconomicManifestRow:
    outcome = _outcome()
    return ArchBForwardEconomicManifestRow(
        decision_epoch_id="epoch-1",
        decision_evidence_sha256=outcome.decision_evidence_sha256,
        decision_at=T0,
        fold_id="WF1",
        signal_fingerprint=outcome.signal_fingerprint,
        trader_id="R38_EURUSD",
        candidate_id="candidate-1",
        code_sha="1" * 40,
        parameter_sha256=_sha("2"),
        collector_git_sha="2" * 40,
        provider_key="ctrader-demo",
        account_ref="demo-account",
        environment="demo",
        provider_evidence_id="provider-evidence-1",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        provider_economics_sha256=_sha("3"),
        provider_observed_at=T0.isoformat(),
        provider_contract_size=Decimal("100000"),
        provider_tick_size=Decimal("0.00001"),
        provider_tick_value=Decimal("1"),
        provider_minimum_volume=Decimal("0.01"),
        provider_volume_step=Decimal("0.01"),
        provider_margin_per_volume_usd=Decimal("100"),
        provider_commission_per_volume_usd=Decimal("3"),
        provider_slippage_reserve_per_volume_usd=Decimal("0"),
        provider_bid=Decimal("1.1"),
        provider_ask=Decimal("1.10001"),
        policy_record_sha256=_sha("4"),
        policy_selected=True,
        baseline_policy_id="baseline-1",
        baseline_selected=True,
        execution_risk_evidence_id=outcome.execution_risk_evidence_id,
        executed_risk_sha256=_sha("5"),
        executed_source_volume=Decimal("0.01"),
        executed_initial_stop_risk_usd=outcome.executed_initial_stop_risk_usd,
        settlement_sha256=_sha("6"),
        settlement_deal_ids=outcome.settlement_deal_ids,
        realized_net_pnl_usd=outcome.realized_net_pnl_usd,
        outcome_observed_at=outcome.observed_at,
        release_evidence_sha256=_sha("7"),
        release_chain_sha256=_sha("8"),
        released_stop_risk_capacity_usd=outcome.executed_initial_stop_risk_usd,
        released_margin_capacity_usd=Decimal("1"),
        terminal_release_at=outcome.capital_released_at,
        capital_minutes=outcome.capital_minutes,
    )


def _intake() -> T02LifecycleTerminalIntake:
    evidence = T02TerminalReasonEvidence(
        evidence_id="terminal-1",
        decision_evidence_sha256=_sha("1"),
        signal_fingerprint="signal-1",
        position_id=7001,
        settlement_deal_ids=(8001, 8002),
        reason=T02TerminalReason.STRUCTURAL_STOP,
        source=T02TerminalReasonSource.QORE_POSITION_LIFECYCLE,
        source_ref="qore-lifecycle:explicit",
        observed_at=T0 + timedelta(minutes=10),
        explicit_reason=True,
        inferred_from_pnl=False,
        inferred_from_price=False,
        productive_authority=False,
    )
    return T02LifecycleTerminalIntake(
        provider_position_id=7001,
        provider_position_binding_ref="provider-binding:7001",
        provider_position_binding_sha256=_sha("9"),
        execution_risk_evidence_id="risk-1",
        executed_risk_sha256=_sha("5"),
        settlement_sha256=_sha("6"),
        lifecycle_evidence=evidence,
        inferred_from_pnl=False,
        inferred_from_price=False,
        productive_authority=False,
    )


def test_t02_structural_binding_reconciles_all_three_planes() -> None:
    bound = bind_t02_structural_outcome(
        manifest_row=_row(),
        source_outcome=_outcome(),
        terminal_intake=_intake(),
    )

    assert bound.lineage_reconciled is True
    assert bound.structural_outcome.signal_fingerprint == "signal-1"
    assert bound.structural_outcome.source_outcome_evidence_id == "phase20-outcome-1"
    assert bound.structural_outcome.provider_economics_evidence_id == (
        "provider-evidence-1"
    )
    assert bound.structural_outcome.execution_risk_evidence_id == "risk-1"
    assert bound.provider_position_binding_sha256 == _sha("9")
    assert bound.structural_outcome.stopped_at_structural_stop is True
    assert bound.inferred_from_pnl is False
    assert bound.inferred_from_price is False
    assert bound.productive_authority is False


def test_t02_structural_binding_rejects_position_drift() -> None:
    bad = _intake()
    object.__setattr__(bad, "provider_position_id", 9999)

    with pytest.raises(
        CiboCapitalManagementError,
        match="provider/outcome position drift",
    ):
        bind_t02_structural_outcome(
            manifest_row=_row(),
            source_outcome=_outcome(),
            terminal_intake=bad,
        )


def test_t02_structural_binding_rejects_executed_risk_digest_drift() -> None:
    bad = _intake()
    object.__setattr__(bad, "executed_risk_sha256", _sha("a"))

    with pytest.raises(
        CiboCapitalManagementError,
        match="executed-risk SHA drift",
    ):
        bind_t02_structural_outcome(
            manifest_row=_row(),
            source_outcome=_outcome(),
            terminal_intake=bad,
        )


def test_t02_structural_binding_rejects_settlement_digest_drift() -> None:
    bad = _intake()
    object.__setattr__(bad, "settlement_sha256", _sha("a"))

    with pytest.raises(
        CiboCapitalManagementError,
        match="settlement SHA drift",
    ):
        bind_t02_structural_outcome(
            manifest_row=_row(),
            source_outcome=_outcome(),
            terminal_intake=bad,
        )
