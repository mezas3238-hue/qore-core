"""Fresh forward structural-outcome audit for CE2I T02.

The burned T02 context rule is frozen before this population. Forward evidence
may validate that rule, but a negative PnL is never re-labelled as a structural
stop. Stop incidence requires an explicit terminal-reason evidence reference
bound to the canonical Phase20 outcome.

Research-only. No sizing, leverage, Risk, execution or production authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from math import ceil

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_t02_calibration_binding import (
    T02_BURNED_CONTEXT_RULES,
    T02BurnedContextRule,
)

T02_FORWARD_STRUCTURAL_AUDIT_ID = "CIBO_T02_FORWARD_STRUCTURAL_OOS_V1"
T02_FORWARD_STRUCTURAL_FROZEN_AT = datetime(2026, 9, 30, 19, 0, tzinfo=UTC)
T02_MINIMUM_CANDIDATE_OUTCOMES = 30


@dataclass(frozen=True, slots=True)
class T02ForwardStructuralOutcome:
    decision_evidence_sha256: str
    signal_fingerprint: str
    trader_id: TraderLineage
    source_outcome_evidence_id: str
    provider_economics_evidence_id: str
    execution_risk_evidence_id: str
    settlement_deal_ids: tuple[int, ...]
    stopped_at_structural_stop: bool
    terminal_reason_evidence_ref: str
    observed_at: datetime

    def __post_init__(self) -> None:
        if (
            not isinstance(self.decision_evidence_sha256, str)
            or not self.decision_evidence_sha256.startswith("sha256:")
            or len(self.decision_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "T02 forward structural outcome requires canonical decision SHA"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "T02 forward structural outcome trader lineage invalid"
            )
        for name in (
            "signal_fingerprint",
            "source_outcome_evidence_id",
            "provider_economics_evidence_id",
            "execution_risk_evidence_id",
            "terminal_reason_evidence_ref",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise CiboCapitalManagementError(
                    f"T02 forward structural outcome {name} required"
                )
        if (
            not self.settlement_deal_ids
            or len(self.settlement_deal_ids)
            != len(set(self.settlement_deal_ids))
            or any(
                not isinstance(item, int)
                or isinstance(item, bool)
                or item <= 0
                for item in self.settlement_deal_ids
            )
        ):
            raise CiboCapitalManagementError(
                "T02 forward structural settlement ids invalid"
            )
        if type(self.stopped_at_structural_stop) is not bool:
            raise CiboCapitalManagementError(
                "T02 forward structural stop flag must be bool"
            )
        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "T02 forward structural observed_at must be timezone-aware"
            )
        if self.observed_at < T02_FORWARD_STRUCTURAL_FROZEN_AT:
            raise CiboCapitalManagementError(
                "T02 forward structural outcome predates frozen audit"
            )


@dataclass(frozen=True, slots=True)
class T02ForwardLineageAudit:
    lineage: TraderLineage
    selected_field: str
    selected_value: str
    baseline_outcomes: int
    candidate_outcomes: int
    baseline_stop_rate: Decimal
    candidate_stop_rate: Decimal
    baseline_p95_loss_r: Decimal
    candidate_p95_loss_r: Decimal
    provider_binding_complete: bool
    minimum_sample_met: bool
    strict_stop_rate_improvement: bool
    tail_loss_not_worse: bool
    fresh_structural_precision_demonstrated: bool


@dataclass(frozen=True, slots=True)
class T02ForwardStructuralAudit:
    audit_id: str
    frozen_at: datetime
    lineages: tuple[T02ForwardLineageAudit, ...]
    fresh_structural_precision_demonstrated: bool
    ready_for_provider_bound_leverage_ablation: bool
    runtime_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.audit_id != T02_FORWARD_STRUCTURAL_AUDIT_ID:
            raise CiboCapitalManagementError("T02 forward audit identity drift")
        if self.frozen_at != T02_FORWARD_STRUCTURAL_FROZEN_AT:
            raise CiboCapitalManagementError("T02 forward audit freeze drift")
        if type(self.runtime_authority) is not bool or self.runtime_authority:
            raise CiboCapitalManagementError(
                "T02 forward audit cannot grant runtime authority"
            )
        expected = bool(self.lineages) and all(
            item.fresh_structural_precision_demonstrated
            for item in self.lineages
        )
        if self.fresh_structural_precision_demonstrated != expected:
            raise CiboCapitalManagementError(
                "T02 forward audit structural result drift"
            )
        if self.ready_for_provider_bound_leverage_ablation != expected:
            raise CiboCapitalManagementError(
                "T02 forward audit ablation readiness drift"
            )


def assess_t02_forward_structural_oos(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    structural_outcomes: tuple[T02ForwardStructuralOutcome, ...],
) -> T02ForwardStructuralAudit:
    """Evaluate frozen burned context rules on explicit forward terminal evidence."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "T02 forward audit requires canonical Phase20 evidence book"
        )
    if not isinstance(structural_outcomes, tuple) or any(
        not isinstance(item, T02ForwardStructuralOutcome)
        for item in structural_outcomes
    ):
        raise CiboCapitalManagementError(
            "T02 forward audit requires canonical structural outcomes"
        )
    keys = tuple(
        (item.decision_evidence_sha256, item.signal_fingerprint)
        for item in structural_outcomes
    )
    if len(keys) != len(set(keys)):
        raise CiboCapitalManagementError(
            "T02 forward structural outcomes contain duplicate decision/signal"
        )

    decision_by_sha = {
        item.evidence_sha256: item for item in evidence_book.decisions
    }
    outcome_by_id = {
        item.evidence_id: item for item in evidence_book.outcomes
    }

    eligible_rules = tuple(
        item
        for item in T02_BURNED_CONTEXT_RULES
        if item.eligible_for_structural_leverage
    )
    lineage_audits: list[T02ForwardLineageAudit] = []
    global_blockers: list[str] = []

    bound_rows: dict[
        TraderLineage,
        list[
            tuple[
                T02ForwardStructuralOutcome,
                Phase20ForwardOutcomeSeal,
                bool,
            ]
        ],
    ] = {rule.lineage: [] for rule in eligible_rules}

    for item in structural_outcomes:
        if item.trader_id not in bound_rows:
            continue
        decision = decision_by_sha.get(item.decision_evidence_sha256)
        if decision is None:
            raise CiboCapitalManagementError(
                "T02 forward structural decision binding missing"
            )
        if decision.decision_at < T02_FORWARD_STRUCTURAL_FROZEN_AT:
            raise CiboCapitalManagementError(
                "T02 forward structural decision predates audit freeze"
            )
        if item.observed_at < decision.decision_at:
            raise CiboCapitalManagementError(
                "T02 forward structural terminal evidence predates decision"
            )
        payload = _payload(decision)
        if payload.get("evidence_kind") != "FORWARD_OBSERVED":
            raise CiboCapitalManagementError(
                "T02 forward structural audit accepts FORWARD_OBSERVED only"
            )

        source = outcome_by_id.get(item.source_outcome_evidence_id)
        if source is None:
            raise CiboCapitalManagementError(
                "T02 forward structural canonical outcome binding missing"
            )
        _bind_source_outcome(item=item, source=source)
        if source.observed_at > item.observed_at:
            raise CiboCapitalManagementError(
                "T02 terminal-reason observation cannot predate canonical outcome"
            )

        rule = _rule(item.trader_id)
        candidate = _decision_matches_rule(
            decision=decision,
            signal_fingerprint=item.signal_fingerprint,
            rule=rule,
            provider_economics_evidence_id=item.provider_economics_evidence_id,
        )
        bound_rows[item.trader_id].append((item, source, candidate))

    for rule in eligible_rules:
        rows = tuple(bound_rows[rule.lineage])
        candidates = tuple(row for row in rows if row[2])
        baseline_rate = _stop_rate(rows)
        candidate_rate = _stop_rate(candidates)
        baseline_p95 = _p95_loss(rows)
        candidate_p95 = _p95_loss(candidates)
        provider_complete = bool(rows) and all(
            row[0].provider_economics_evidence_id
            and row[0].execution_risk_evidence_id
            and row[0].settlement_deal_ids
            and row[0].terminal_reason_evidence_ref
            for row in rows
        )
        sample_ok = len(candidates) >= T02_MINIMUM_CANDIDATE_OUTCOMES
        strict_improvement = (
            bool(candidates) and candidate_rate < baseline_rate
        )
        tail_not_worse = bool(candidates) and candidate_p95 <= baseline_p95
        demonstrated = (
            sample_ok
            and provider_complete
            and strict_improvement
            and tail_not_worse
        )
        lineage_audits.append(
            T02ForwardLineageAudit(
                lineage=rule.lineage,
                selected_field=rule.selected_field,
                selected_value=rule.selected_value,
                baseline_outcomes=len(rows),
                candidate_outcomes=len(candidates),
                baseline_stop_rate=baseline_rate,
                candidate_stop_rate=candidate_rate,
                baseline_p95_loss_r=baseline_p95,
                candidate_p95_loss_r=candidate_p95,
                provider_binding_complete=provider_complete,
                minimum_sample_met=sample_ok,
                strict_stop_rate_improvement=strict_improvement,
                tail_loss_not_worse=tail_not_worse,
                fresh_structural_precision_demonstrated=demonstrated,
            )
        )
        prefix = f"T02_{rule.lineage.value}"
        if not rows:
            global_blockers.append(f"{prefix}_NO_FORWARD_OUTCOMES")
        if not sample_ok:
            global_blockers.append(
                f"{prefix}_MINIMUM_CANDIDATE_OUTCOMES_NOT_MET"
            )
        if not provider_complete:
            global_blockers.append(
                f"{prefix}_PROVIDER_EXECUTION_SETTLEMENT_BINDING_INCOMPLETE"
            )
        if candidates and not strict_improvement:
            global_blockers.append(
                f"{prefix}_STOP_RATE_NOT_STRICTLY_IMPROVED"
            )
        if candidates and not tail_not_worse:
            global_blockers.append(f"{prefix}_TAIL_LOSS_WORSE")

    all_demonstrated = bool(lineage_audits) and all(
        item.fresh_structural_precision_demonstrated
        for item in lineage_audits
    )
    if all_demonstrated:
        global_blockers.append(
            "T02_PROVIDER_BOUND_LEVERAGE_ECONOMIC_ABLATION_REQUIRED"
        )
    else:
        global_blockers.append(
            "T02_FRESH_STRUCTURAL_PRECISION_NOT_YET_DEMONSTRATED"
        )

    return T02ForwardStructuralAudit(
        audit_id=T02_FORWARD_STRUCTURAL_AUDIT_ID,
        frozen_at=T02_FORWARD_STRUCTURAL_FROZEN_AT,
        lineages=tuple(lineage_audits),
        fresh_structural_precision_demonstrated=all_demonstrated,
        ready_for_provider_bound_leverage_ablation=all_demonstrated,
        runtime_authority=False,
        blockers=tuple(dict.fromkeys(global_blockers)),
    )


def _bind_source_outcome(
    *,
    item: T02ForwardStructuralOutcome,
    source: Phase20ForwardOutcomeSeal,
) -> None:
    if source.decision_evidence_sha256 != item.decision_evidence_sha256:
        raise CiboCapitalManagementError(
            "T02 structural/canonical decision binding drift"
        )
    if source.signal_fingerprint != item.signal_fingerprint:
        raise CiboCapitalManagementError(
            "T02 structural/canonical signal binding drift"
        )
    if source.execution_risk_evidence_id != item.execution_risk_evidence_id:
        raise CiboCapitalManagementError(
            "T02 structural/canonical execution-risk binding drift"
        )
    if source.settlement_deal_ids != item.settlement_deal_ids:
        raise CiboCapitalManagementError(
            "T02 structural/canonical settlement binding drift"
        )


def _rule(lineage: TraderLineage) -> T02BurnedContextRule:
    rows = tuple(
        item
        for item in T02_BURNED_CONTEXT_RULES
        if item.lineage is lineage
    )
    if len(rows) != 1:
        raise CiboCapitalManagementError(
            "T02 burned rule registry lineage drift"
        )
    return rows[0]


def _payload(decision: Phase20ForwardDecisionSeal) -> dict[str, object]:
    try:
        value = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "T02 forward decision payload invalid"
        ) from error
    if not isinstance(value, dict):
        raise CiboCapitalManagementError(
            "T02 forward decision payload must be object"
        )
    return value


def _decision_matches_rule(
    *,
    decision: Phase20ForwardDecisionSeal,
    signal_fingerprint: str,
    rule: T02BurnedContextRule,
    provider_economics_evidence_id: str,
) -> bool:
    payload = _payload(decision)
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise CiboCapitalManagementError(
            "T02 forward decision candidates missing"
        )
    matches: list[dict[str, object]] = []
    for raw in candidates:
        if not isinstance(raw, dict):
            continue
        opportunity = raw.get("opportunity")
        if not isinstance(opportunity, dict):
            continue
        if opportunity.get("signal_fingerprint") == signal_fingerprint:
            matches.append(raw)
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "T02 forward decision signal candidate binding is not unique"
        )
    candidate = matches[0]
    if candidate.get("provider_evidence_id") != provider_economics_evidence_id:
        raise CiboCapitalManagementError(
            "T02 provider economics evidence binding drift"
        )
    opportunity = candidate.get("opportunity")
    assert isinstance(opportunity, dict)
    if opportunity.get("trader_id") != rule.lineage.value:
        raise CiboCapitalManagementError(
            "T02 forward decision trader lineage drift"
        )
    if rule.selected_field == "side":
        return opportunity.get("side") == rule.selected_value
    context = opportunity.get("decision_context")
    if not isinstance(context, list):
        return False
    for item in context:
        if (
            isinstance(item, list)
            and len(item) == 2
            and item[0] == rule.selected_field
            and item[1] == rule.selected_value
        ):
            return True
    return False


def _stop_rate(
    rows: tuple[
        tuple[T02ForwardStructuralOutcome, Phase20ForwardOutcomeSeal, bool],
        ...,
    ],
) -> Decimal:
    if not rows:
        return Decimal(1)
    stopped = sum(1 for item, _source, _candidate in rows if item.stopped_at_structural_stop)
    return Decimal(stopped) / Decimal(len(rows))


def _p95_loss(
    rows: tuple[
        tuple[T02ForwardStructuralOutcome, Phase20ForwardOutcomeSeal, bool],
        ...,
    ],
) -> Decimal:
    if not rows:
        return Decimal("Infinity")
    losses = sorted(
        max(Decimal(0), -source.realized_structural_outcome_r)
        for _item, source, _candidate in rows
    )
    index = max(0, ceil(Decimal("0.95") * Decimal(len(losses))) - 1)
    return losses[index]
