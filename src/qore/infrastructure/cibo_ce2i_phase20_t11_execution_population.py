"""Fresh realized execution-economics population audit for CE2I T11.

This audit derives signed execution-risk slippage from reconciled fill evidence:
executed stop risk versus the same filled volume at the intended entry. Positive
delta is adverse; negative delta is favorable. It also measures decision-to-
deployment latency as an operational upper bound, never as pure broker latency.

The audit uses only forward decisions sealed before deployment and frozen
Phase20 qualification thresholds. Population readiness is not execution-model
certification and does not claim historical 2017 provider economics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)


@dataclass(frozen=True, slots=True)
class Phase20T11ExecutionPopulationAudit:
    eligible_execution_instances: int
    adverse_slippage_instances: int
    favorable_slippage_instances: int
    flat_slippage_instances: int
    latency_bound_instances: int
    represented_lineages: tuple[str, ...]
    minimum_instances_per_lineage: int
    mean_signed_slippage_r: Decimal | None
    p50_signed_slippage_r: Decimal | None
    p95_signed_slippage_r: Decimal | None
    mean_decision_to_deployment_ms: Decimal | None
    p95_decision_to_deployment_ms: Decimal | None
    minimum_required_executions: int
    minimum_required_lineages: int
    minimum_required_per_lineage: int
    empirical_execution_population_ready: bool
    slippage_empirically_calibrated: bool
    execution_model_ready: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "eligible_execution_instances",
            "adverse_slippage_instances",
            "favorable_slippage_instances",
            "flat_slippage_instances",
            "latency_bound_instances",
            "minimum_instances_per_lineage",
            "minimum_required_executions",
            "minimum_required_lineages",
            "minimum_required_per_lineage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T11 {name} must be non-negative int"
                )
        if (
            self.adverse_slippage_instances
            + self.favorable_slippage_instances
            + self.flat_slippage_instances
            != self.eligible_execution_instances
        ):
            raise CiboCapitalManagementError(
                "Phase20 T11 slippage instance accounting drift"
            )
        if self.latency_bound_instances > self.eligible_execution_instances:
            raise CiboCapitalManagementError(
                "Phase20 T11 latency coverage exceeds executions"
            )
        if len(self.represented_lineages) != len(
            set(self.represented_lineages)
        ):
            raise CiboCapitalManagementError(
                "Phase20 T11 lineages must be unique"
            )
        for name in (
            "mean_signed_slippage_r",
            "p50_signed_slippage_r",
            "p95_signed_slippage_r",
            "mean_decision_to_deployment_ms",
            "p95_decision_to_deployment_ms",
        ):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, Decimal)
                or not value.is_finite()
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T11 {name} must be finite Decimal/null"
                )
        if self.slippage_empirically_calibrated or self.execution_model_ready:
            raise CiboCapitalManagementError(
                "Phase20 T11 population audit cannot certify execution economics"
            )


def assess_phase20_t11_execution_population(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    executed_risk_book: VersionedPhase20ExecutedRiskBook,
) -> Phase20T11ExecutionPopulationAudit:
    """Measure fresh realized fill/slippage/latency coverage without promotion."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T11 requires canonical forward evidence book"
        )
    if not isinstance(executed_risk_book, VersionedPhase20ExecutedRiskBook):
        raise CiboCapitalManagementError(
            "Phase20 T11 requires canonical executed-risk book"
        )

    usable = {
        item.evidence_sha256: item
        for item in evidence_book.decisions
        if _usable(item)
    }
    lineage_counts: dict[str, int] = {}
    slippage: list[Decimal] = []
    latency_ms: list[Decimal] = []
    adverse = 0
    favorable = 0
    flat = 0

    for item in executed_risk_book.evidences:
        decision = usable.get(item.decision_evidence_sha256)
        if decision is None:
            continue
        if not item.fill_reconciled or not item.mutation_outcome_known:
            continue
        lineage = _lineage_for_signal(
            decision=decision,
            signal_fingerprint=item.signal_fingerprint,
        )
        if lineage is None:
            raise CiboCapitalManagementError(
                "Phase20 T11 executed signal not bound to forward population slot"
            )
        if decision.sealed_at is None:
            raise CiboCapitalManagementError(
                "Phase20 T11 usable decision missing seal timestamp"
            )
        if (
            item.capital_deployed_at is not None
            and decision.sealed_at > item.capital_deployed_at
        ):
            raise CiboCapitalManagementError(
                "Phase20 T11 decision sealed after capital deployment"
            )

        intended_risk = (
            item.stop_risk_per_volume_at_intended_entry_usd
            * item.filled_source_volume
        )
        if intended_risk <= 0:
            raise CiboCapitalManagementError(
                "Phase20 T11 intended filled stop risk must be positive"
            )
        delta_r = (
            item.executed_initial_stop_risk_usd - intended_risk
        ) / intended_risk
        slippage.append(delta_r)
        if delta_r > 0:
            adverse += 1
        elif delta_r < 0:
            favorable += 1
        else:
            flat += 1

        lineage_counts[lineage] = lineage_counts.get(lineage, 0) + 1
        if item.capital_deployed_at is not None:
            latency = item.capital_deployed_at - decision.decision_at
            if latency.total_seconds() < 0:
                raise CiboCapitalManagementError(
                    "Phase20 T11 capital deployment predates decision"
                )
            latency_ms.append(
                Decimal(str(latency.total_seconds())) * Decimal(1000)
            )

    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    represented = tuple(sorted(lineage_counts))
    minimum_per_lineage = (
        min(lineage_counts.values()) if lineage_counts else 0
    )
    sample_ready = len(slippage) >= plan.minimum_selected_outcomes
    lineage_ready = len(represented) >= plan.minimum_global_lineages
    per_lineage_ready = (
        minimum_per_lineage >= plan.minimum_outcomes_per_lineage
    )
    latency_ready = len(latency_ms) == len(slippage) and bool(slippage)
    ready = (
        sample_ready
        and lineage_ready
        and per_lineage_ready
        and latency_ready
    )

    blockers: list[str] = []
    if not sample_ready:
        blockers.append(
            "T11_MINIMUM_EXECUTED_SAMPLE_NOT_MET:"
            f"{len(slippage)}/{plan.minimum_selected_outcomes}"
        )
    if not lineage_ready:
        blockers.append(
            "T11_EXECUTED_LINEAGE_COVERAGE_NOT_MET:"
            f"{len(represented)}/{plan.minimum_global_lineages}"
        )
    if not per_lineage_ready:
        blockers.append(
            "T11_MINIMUM_EXECUTIONS_PER_LINEAGE_NOT_MET:"
            f"{minimum_per_lineage}/{plan.minimum_outcomes_per_lineage}"
        )
    if not latency_ready:
        blockers.append("T11_DECISION_TO_DEPLOYMENT_LATENCY_COVERAGE_INCOMPLETE")
    blockers.extend(
        (
            "REALIZED_COMMISSION_AND_SPREAD_ECONOMICS_NOT_BOUND",
            "EMPIRICAL_EXECUTION_POPULATION_DOES_NOT_PROVE_2017_TERMS",
            "T11_EXECUTION_EFFICIENCY_POLICY_NOT_IDENTIFIED",
        )
    )

    return Phase20T11ExecutionPopulationAudit(
        eligible_execution_instances=len(slippage),
        adverse_slippage_instances=adverse,
        favorable_slippage_instances=favorable,
        flat_slippage_instances=flat,
        latency_bound_instances=len(latency_ms),
        represented_lineages=represented,
        minimum_instances_per_lineage=minimum_per_lineage,
        mean_signed_slippage_r=_mean(slippage),
        p50_signed_slippage_r=_percentile(slippage, Decimal("0.50")),
        p95_signed_slippage_r=_percentile(slippage, Decimal("0.95")),
        mean_decision_to_deployment_ms=_mean(latency_ms),
        p95_decision_to_deployment_ms=_percentile(
            latency_ms,
            Decimal("0.95"),
        ),
        minimum_required_executions=plan.minimum_selected_outcomes,
        minimum_required_lineages=plan.minimum_global_lineages,
        minimum_required_per_lineage=plan.minimum_outcomes_per_lineage,
        empirical_execution_population_ready=ready,
        slippage_empirically_calibrated=False,
        execution_model_ready=False,
        blockers=tuple(blockers),
    )


def _usable(decision: Phase20ForwardDecisionSeal) -> bool:
    if decision.decision_at < FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at:
        return False
    if decision.sealed_at is None:
        return False
    if (
        decision.seal_deadline_at is not None
        and not decision.sealed_within_deadline
    ):
        return False
    return _payload(decision).get("evidence_kind") == "FORWARD_OBSERVED"


def _lineage_for_signal(
    *,
    decision: Phase20ForwardDecisionSeal,
    signal_fingerprint: str,
) -> str | None:
    slots = _payload(decision).get("population_slots")
    if not isinstance(slots, list):
        raise CiboCapitalManagementError(
            "Phase20 T11 population_slots must be list"
        )
    matches: list[str] = []
    for row in slots:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "Phase20 T11 population slot must be object"
            )
        if row.get("signal_fingerprint") != signal_fingerprint:
            continue
        trader = row.get("trader_id")
        if not isinstance(trader, str) or not trader:
            raise CiboCapitalManagementError(
                "Phase20 T11 population slot trader_id missing"
            )
        matches.append(trader)
    if len(matches) > 1:
        raise CiboCapitalManagementError(
            "Phase20 T11 signal maps to multiple lineages"
        )
    return matches[0] if matches else None


def _payload(
    decision: Phase20ForwardDecisionSeal,
) -> dict[str, object]:
    try:
        payload = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20 T11 decision payload invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 T11 decision payload must be object"
        )
    return payload


def _mean(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal(0)) / Decimal(len(values))


def _percentile(
    values: list[Decimal],
    probability: Decimal,
) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    raw_rank = probability * Decimal(len(ordered))
    rank = int(raw_rank.to_integral_value(rounding="ROUND_CEILING"))
    index = max(0, min(len(ordered) - 1, rank - 1))
    return ordered[index]
