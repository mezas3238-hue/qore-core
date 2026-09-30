from __future__ import annotations

import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t02_structural_oos import (
    T02_FORWARD_STRUCTURAL_FROZEN_AT,
    T02ForwardStructuralOutcome,
    assess_t02_forward_structural_oos,
)
from qore.infrastructure.cibo_ce2i_t02_calibration_binding import (
    T02_BURNED_CONTEXT_RULES,
)
from qore.infrastructure.cibo_ce2i_t02_terminal_reason_evidence import (
    T02TerminalReason,
    T02TerminalReasonEvidence,
    T02TerminalReasonSource,
)

ELIGIBLE = tuple(
    row
    for row in T02_BURNED_CONTEXT_RULES
    if row.eligible_for_structural_leverage
)


def _decision(
    *,
    index: int,
    lineage: TraderLineage,
    field: str,
    value: str,
    matches: bool,
) -> Phase20ForwardDecisionSeal:
    at = T02_FORWARD_STRUCTURAL_FROZEN_AT + timedelta(minutes=index + 1)
    signal = f"signal-{index}"
    selected = value if matches else f"not-{value}"
    context = [] if field == "side" else [[field, selected]]
    side = selected if field == "side" else "long"
    if side not in {"long", "short"}:
        side = "short" if value == "long" else "long"
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "candidates": [
            {
                "provider_evidence_id": f"provider-{index}",
                "opportunity": {
                    "signal_fingerprint": signal,
                    "trader_id": lineage.value,
                    "side": side,
                    "decision_context": context,
                },
            }
        ],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256="sha256:" + f"{index + 1:064x}",
        decision_at=at,
        candidate_id="phase20-candidate",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + ("b" * 64),
        signal_fingerprints=(signal,),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        collector_git_sha="c" * 40,
        sealed_at=at + timedelta(milliseconds=100),
        seal_deadline_at=at + timedelta(seconds=2),
    )


def _terminal_reason(
    *,
    decision: Phase20ForwardDecisionSeal,
    outcome: Phase20ForwardOutcomeSeal,
    stopped: bool,
    index: int,
) -> T02TerminalReasonEvidence:
    return T02TerminalReasonEvidence(
        evidence_id=f"terminal-reason-{index}",
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=outcome.signal_fingerprint,
        position_id=outcome.position_id,
        settlement_deal_ids=outcome.settlement_deal_ids,
        reason=(
            T02TerminalReason.STRUCTURAL_STOP
            if stopped
            else T02TerminalReason.TAKE_PROFIT
        ),
        source=T02TerminalReasonSource.PROVIDER_NATIVE_EXPLICIT,
        source_ref=f"synthetic-explicit-terminal:{index}",
        observed_at=outcome.observed_at + timedelta(seconds=1),
    )


def _population():
    decisions = []
    outcomes = []
    structural = []
    index = 0
    for rule in ELIGIBLE:
        for slot in range(40):
            matches = slot < 30
            decision = _decision(
                index=index,
                lineage=rule.lineage,
                field=rule.selected_field,
                value=rule.selected_value,
                matches=matches,
            )
            stopped = (slot % 10 == 0) if matches else (slot % 2 == 0)
            structural_r = Decimal("-1") if stopped else Decimal("1")
            outcome = Phase20ForwardOutcomeSeal(
                evidence_id=f"outcome-{index}",
                decision_evidence_sha256=decision.evidence_sha256,
                signal_fingerprint=f"signal-{index}",
                position_id=index + 1,
                execution_risk_evidence_id=f"risk-{index}",
                settlement_deal_ids=(10000 + index,),
                fill_evidence_refs=(f"fill-{index}",),
                observed_at=decision.decision_at + timedelta(minutes=30),
                realized_net_pnl_usd=structural_r * Decimal("5"),
                executed_initial_stop_risk_usd=Decimal("5"),
                realized_structural_outcome_r=structural_r,
            )
            row = T02ForwardStructuralOutcome(
                decision_evidence_sha256=decision.evidence_sha256,
                signal_fingerprint=f"signal-{index}",
                trader_id=rule.lineage,
                source_outcome_evidence_id=outcome.evidence_id,
                provider_economics_evidence_id=f"provider-{index}",
                execution_risk_evidence_id=outcome.execution_risk_evidence_id,
                terminal_reason_evidence=_terminal_reason(
                    decision=decision,
                    outcome=outcome,
                    stopped=stopped,
                    index=index,
                ),
            )
            decisions.append(decision)
            outcomes.append(outcome)
            structural.append(row)
            index += 1
    return (
        VersionedPhase20ForwardEvidenceBook(
            generation=len(decisions) + len(outcomes),
            decisions=tuple(decisions),
            outcomes=tuple(outcomes),
        ),
        tuple(structural),
    )


def test_forward_structural_precision_can_be_demonstrated_without_leverage_authority() -> None:
    book, rows = _population()
    report = assess_t02_forward_structural_oos(
        evidence_book=book,
        structural_outcomes=rows,
    )

    assert len(report.lineages) == len(ELIGIBLE)
    assert report.fresh_structural_precision_demonstrated is True
    assert report.ready_for_provider_bound_leverage_ablation is True
    assert report.runtime_authority is False
    assert all(row.candidate_outcomes == 30 for row in report.lineages)
    assert all(row.strict_stop_rate_improvement for row in report.lineages)
    assert (
        "T02_PROVIDER_BOUND_LEVERAGE_ECONOMIC_ABLATION_REQUIRED"
        in report.blockers
    )


def test_negative_pnl_does_not_implicitly_become_structural_stop() -> None:
    book, rows = _population()
    first = rows[0]
    source = book.outcomes[0]
    assert source.realized_structural_outcome_r == Decimal("-1")

    explicit_not_stop = replace(
        first.terminal_reason_evidence,
        reason=T02TerminalReason.TAKE_PROFIT,
        source_ref="explicit-not-stop",
    )
    changed = replace(
        first,
        terminal_reason_evidence=explicit_not_stop,
    )
    report = assess_t02_forward_structural_oos(
        evidence_book=book,
        structural_outcomes=(changed,) + rows[1:],
    )

    lineage = next(
        item for item in report.lineages if item.lineage is first.trader_id
    )
    assert lineage.candidate_stop_rate < Decimal("0.10")


def test_structural_outcome_requires_canonical_phase20_outcome_binding() -> None:
    book, rows = _population()
    first = rows[0]
    broken = replace(first, source_outcome_evidence_id="missing-outcome")

    with pytest.raises(
        CiboCapitalManagementError,
        match="canonical outcome binding missing",
    ):
        assess_t02_forward_structural_oos(
            evidence_book=book,
            structural_outcomes=(broken,) + rows[1:],
        )


def test_terminal_reason_position_must_match_phase20_outcome() -> None:
    book, rows = _population()
    first = rows[0]
    bad_terminal = replace(
        first.terminal_reason_evidence,
        position_id=999999,
    )
    broken = replace(first, terminal_reason_evidence=bad_terminal)

    with pytest.raises(
        CiboCapitalManagementError,
        match="position binding drift",
    ):
        assess_t02_forward_structural_oos(
            evidence_book=book,
            structural_outcomes=(broken,) + rows[1:],
        )


def test_pre_freeze_structural_classification_is_rejected() -> None:
    terminal = T02TerminalReasonEvidence(
        evidence_id="terminal-pre-freeze",
        decision_evidence_sha256="sha256:" + "1" * 64,
        signal_fingerprint="signal",
        position_id=1,
        settlement_deal_ids=(1,),
        reason=T02TerminalReason.STRUCTURAL_STOP,
        source=T02TerminalReasonSource.PROVIDER_NATIVE_EXPLICIT,
        source_ref="explicit-pre-freeze",
        observed_at=(
            T02_FORWARD_STRUCTURAL_FROZEN_AT - timedelta(seconds=1)
        ),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="predates frozen audit",
    ):
        T02ForwardStructuralOutcome(
            decision_evidence_sha256="sha256:" + "1" * 64,
            signal_fingerprint="signal",
            trader_id=TraderLineage.R34_XAUUSD,
            source_outcome_evidence_id="outcome",
            provider_economics_evidence_id="provider",
            execution_risk_evidence_id="risk",
            terminal_reason_evidence=terminal,
        )
