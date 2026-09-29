"""Fresh OOS population readiness for CE2I T13 shadow treatment.

This audit inspects only identities, coverage and temporal population maturity.
It never reads realized PnL magnitudes and therefore cannot demonstrate T13
utility. Its purpose is to decide whether a later fixed utility analysis may be
run without selection bias or missing counterfactual-like outcomes.

Every usable FORWARD_OBSERVED decision at or after the T13 policy freeze must
have both an official baseline policy seal and a T13 treatment seal. Candidate,
baseline-selected and treatment-selected coverage reuse the already-frozen
Phase20D qualification thresholds.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_FROZEN_AT,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment_store import (
    T13ShadowTreatmentSeal,
)


@dataclass(frozen=True, slots=True)
class Phase20T13OosReadiness:
    ready_for_utility_analysis: bool
    blockers: tuple[str, ...]
    post_freeze_decision_epochs: int
    pre_t13_freeze_decisions_excluded: int
    treatment_sealed_epochs: int
    missing_treatment_decisions: int
    missing_baseline_policy_decisions: int
    selection_changed_epochs: int
    candidate_instances: int
    candidate_outcomes: int
    candidate_outcome_coverage: Decimal
    baseline_selected_instances: int
    baseline_selected_outcomes: int
    baseline_selected_outcome_coverage: Decimal
    treatment_selected_instances: int
    treatment_selected_outcomes: int
    treatment_selected_outcome_coverage: Decimal
    baseline_only_instances: int
    baseline_only_outcomes: int
    treatment_only_instances: int
    treatment_only_outcomes: int
    calendar_span_days: int
    distinct_trading_days: int
    represented_lineages: int
    minimum_outcomes_any_lineage: int
    minimum_fold_candidate_outcomes: int
    minimum_fold_lineages: int
    minimum_decision_epochs: int
    minimum_candidate_outcomes: int
    minimum_selected_outcomes: int
    required_candidate_coverage: Decimal
    required_selected_coverage: Decimal
    fold_count: int
    fresh_oos_utility_demonstrated: bool

    def __post_init__(self) -> None:
        for name in (
            "post_freeze_decision_epochs",
            "pre_t13_freeze_decisions_excluded",
            "treatment_sealed_epochs",
            "missing_treatment_decisions",
            "missing_baseline_policy_decisions",
            "selection_changed_epochs",
            "candidate_instances",
            "candidate_outcomes",
            "baseline_selected_instances",
            "baseline_selected_outcomes",
            "treatment_selected_instances",
            "treatment_selected_outcomes",
            "baseline_only_instances",
            "baseline_only_outcomes",
            "treatment_only_instances",
            "treatment_only_outcomes",
            "calendar_span_days",
            "distinct_trading_days",
            "represented_lineages",
            "minimum_outcomes_any_lineage",
            "minimum_fold_candidate_outcomes",
            "minimum_fold_lineages",
            "minimum_decision_epochs",
            "minimum_candidate_outcomes",
            "minimum_selected_outcomes",
            "fold_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 OOS {name} must be non-negative int"
                )
        for name in (
            "candidate_outcome_coverage",
            "baseline_selected_outcome_coverage",
            "treatment_selected_outcome_coverage",
            "required_candidate_coverage",
            "required_selected_coverage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 OOS {name} must be Decimal in [0,1]"
                )
        if type(self.ready_for_utility_analysis) is not bool:
            raise CiboCapitalManagementError(
                "Phase20 T13 OOS readiness flag must be bool"
            )
        if type(self.fresh_oos_utility_demonstrated) is not bool:
            raise CiboCapitalManagementError(
                "Phase20 T13 OOS utility flag must be bool"
            )
        if self.fresh_oos_utility_demonstrated:
            raise CiboCapitalManagementError(
                "Phase20 T13 readiness cannot demonstrate utility"
            )
        if self.ready_for_utility_analysis != (not self.blockers):
            raise CiboCapitalManagementError(
                "Phase20 T13 OOS readiness/blocker drift"
            )


@dataclass(frozen=True, slots=True)
class _OutcomeRow:
    decision_at_date: date
    decision_at_iso: str
    evidence_sha256: str
    trader_id: str


def assess_phase20_t13_oos_readiness(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    baseline_policy_book: VersionedPhase20ForwardPolicyBook,
    treatment_decisions: tuple[T13ShadowTreatmentSeal, ...],
) -> Phase20T13OosReadiness:
    """Assess whether T13 has a legally comparable fresh OOS population."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T13 OOS requires canonical evidence book"
        )
    if not isinstance(
        baseline_policy_book,
        VersionedPhase20ForwardPolicyBook,
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 OOS requires canonical baseline policy book"
        )
    if not isinstance(treatment_decisions, tuple) or any(
        not isinstance(item, T13ShadowTreatmentSeal)
        for item in treatment_decisions
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 OOS treatment decisions must be canonical tuple"
        )

    treatment_by_sha = {
        item.decision_evidence_sha256: item
        for item in treatment_decisions
    }
    if len(treatment_by_sha) != len(treatment_decisions):
        raise CiboCapitalManagementError(
            "Phase20 T13 OOS duplicate treatment evidence"
        )
    baseline_by_sha = {
        item.evidence_sha256: item
        for item in baseline_policy_book.decisions
    }
    outcomes = {
        (item.decision_evidence_sha256, item.signal_fingerprint): item
        for item in evidence_book.outcomes
    }

    all_usable = tuple(
        item
        for item in sorted(
            evidence_book.decisions,
            key=lambda row: (row.decision_at, row.evidence_sha256),
        )
        if _usable(item)
    )
    decisions = tuple(
        item
        for item in all_usable
        if item.decision_at >= T13_SHADOW_POLICY_FROZEN_AT
    )
    pre_freeze_excluded = len(all_usable) - len(decisions)

    candidate_instances = 0
    candidate_outcomes = 0
    baseline_instances = 0
    baseline_outcomes = 0
    treatment_instances = 0
    treatment_outcomes = 0
    baseline_only_instances = 0
    baseline_only_outcomes = 0
    treatment_only_instances = 0
    treatment_only_outcomes = 0
    missing_treatment = 0
    missing_baseline = 0
    changed_epochs = 0
    outcome_rows: list[_OutcomeRow] = []

    for decision in decisions:
        candidate_map = _candidate_lineage_map(decision)
        if set(candidate_map) != set(decision.signal_fingerprints):
            raise CiboCapitalManagementError(
                "Phase20 T13 OOS candidate payload/fingerprint mismatch"
            )
        candidate_instances += len(candidate_map)
        treatment = treatment_by_sha.get(decision.evidence_sha256)
        baseline = baseline_by_sha.get(decision.evidence_sha256)
        if treatment is None:
            missing_treatment += 1
            treatment_selected: tuple[str, ...] = ()
        else:
            if (
                treatment.decision_epoch_id != decision.decision_epoch_id
                or treatment.decision_at != decision.decision_at
            ):
                raise CiboCapitalManagementError(
                    "Phase20 T13 OOS treatment decision binding drift"
                )
            treatment_selected = (
                treatment.treatment_selected_signal_fingerprints
            )
            if treatment.selection_changed:
                changed_epochs += 1
        if baseline is None:
            missing_baseline += 1
            baseline_selected: tuple[str, ...] = ()
        else:
            baseline_selected = baseline.selected_signal_fingerprints

        if treatment is not None and baseline is not None:
            if (
                treatment.baseline_policy_record_sha256
                != baseline.policy_record_sha256
                or treatment.baseline_selected_signal_fingerprints
                != baseline_selected
            ):
                raise CiboCapitalManagementError(
                    "Phase20 T13 OOS baseline/treatment binding drift"
                )
        if not set(baseline_selected).issubset(candidate_map):
            raise CiboCapitalManagementError(
                "Phase20 T13 OOS baseline selected outside candidates"
            )
        if not set(treatment_selected).issubset(candidate_map):
            raise CiboCapitalManagementError(
                "Phase20 T13 OOS treatment selected outside candidates"
            )

        baseline_set = set(baseline_selected)
        treatment_set = set(treatment_selected)
        baseline_instances += len(baseline_selected)
        treatment_instances += len(treatment_selected)
        baseline_only = baseline_set - treatment_set
        treatment_only = treatment_set - baseline_set
        baseline_only_instances += len(baseline_only)
        treatment_only_instances += len(treatment_only)

        for fingerprint, trader_id in candidate_map.items():
            key = (decision.evidence_sha256, fingerprint)
            observed = key in outcomes
            if observed:
                candidate_outcomes += 1
                outcome_rows.append(
                    _OutcomeRow(
                        decision_at_date=decision.decision_at.date(),
                        decision_at_iso=decision.decision_at.isoformat(),
                        evidence_sha256=decision.evidence_sha256,
                        trader_id=trader_id,
                    )
                )
            if fingerprint in baseline_set and observed:
                baseline_outcomes += 1
            if fingerprint in treatment_set and observed:
                treatment_outcomes += 1
            if fingerprint in baseline_only and observed:
                baseline_only_outcomes += 1
            if fingerprint in treatment_only and observed:
                treatment_only_outcomes += 1

    candidate_coverage = _coverage(candidate_outcomes, candidate_instances)
    baseline_coverage = _coverage(baseline_outcomes, baseline_instances)
    treatment_coverage = _coverage(treatment_outcomes, treatment_instances)

    dates = tuple(item.decision_at.date() for item in decisions)
    calendar_span_days = (
        (max(dates) - min(dates)).days + 1 if dates else 0
    )
    distinct_days = len(set(dates))
    lineage_counts = Counter(item.trader_id for item in outcome_rows)
    represented_lineages = len(lineage_counts)
    minimum_outcomes_any_lineage = (
        min(lineage_counts.values()) if lineage_counts else 0
    )

    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    fold_sizes, fold_lineages = _fold_population(
        tuple(outcome_rows),
        fold_count=plan.fold_count,
    )
    minimum_fold_outcomes = min(fold_sizes) if fold_sizes else 0
    minimum_fold_lineages = min(fold_lineages) if fold_lineages else 0

    blockers: list[str] = []
    _gate(
        blockers,
        len(decisions) >= plan.minimum_decision_epochs,
        "T13_MINIMUM_DECISION_EPOCHS_NOT_MET",
    )
    _gate(
        blockers,
        candidate_outcomes >= plan.minimum_candidate_outcomes,
        "T13_MINIMUM_CANDIDATE_OUTCOMES_NOT_MET",
    )
    _gate(
        blockers,
        baseline_outcomes >= plan.minimum_selected_outcomes,
        "T13_MINIMUM_BASELINE_SELECTED_OUTCOMES_NOT_MET",
    )
    _gate(
        blockers,
        treatment_outcomes >= plan.minimum_selected_outcomes,
        "T13_MINIMUM_TREATMENT_SELECTED_OUTCOMES_NOT_MET",
    )
    _gate(
        blockers,
        calendar_span_days >= plan.minimum_calendar_span_days,
        "T13_MINIMUM_CALENDAR_SPAN_NOT_MET",
    )
    _gate(
        blockers,
        distinct_days >= plan.minimum_distinct_trading_days,
        "T13_MINIMUM_TRADING_DAYS_NOT_MET",
    )
    _gate(
        blockers,
        represented_lineages >= plan.minimum_global_lineages,
        "T13_MINIMUM_GLOBAL_LINEAGES_NOT_MET",
    )
    _gate(
        blockers,
        minimum_outcomes_any_lineage >= plan.minimum_outcomes_per_lineage,
        "T13_MINIMUM_OUTCOMES_PER_LINEAGE_NOT_MET",
    )
    _gate(
        blockers,
        minimum_fold_outcomes >= plan.minimum_fold_candidate_outcomes,
        "T13_MINIMUM_FOLD_CANDIDATE_OUTCOMES_NOT_MET",
    )
    _gate(
        blockers,
        minimum_fold_lineages >= plan.minimum_fold_lineages,
        "T13_MINIMUM_FOLD_LINEAGES_NOT_MET",
    )
    _gate(
        blockers,
        candidate_coverage >= plan.minimum_candidate_outcome_coverage,
        "T13_CANDIDATE_OUTCOME_COVERAGE_NOT_MET",
    )
    _gate(
        blockers,
        baseline_coverage >= plan.required_baseline_selected_outcome_coverage,
        "T13_BASELINE_SELECTED_OUTCOME_COVERAGE_NOT_MET",
    )
    _gate(
        blockers,
        treatment_coverage >= plan.required_selected_outcome_coverage,
        "T13_TREATMENT_SELECTED_OUTCOME_COVERAGE_NOT_MET",
    )
    _gate(
        blockers,
        missing_baseline == 0,
        "T13_MISSING_BASELINE_POLICY_DECISIONS",
    )
    _gate(
        blockers,
        missing_treatment == 0,
        "T13_MISSING_SHADOW_TREATMENT_DECISIONS",
    )
    _gate(
        blockers,
        changed_epochs > 0,
        "T13_NO_SELECTION_CHANGE_EPOCHS",
    )

    return Phase20T13OosReadiness(
        ready_for_utility_analysis=not blockers,
        blockers=tuple(blockers),
        post_freeze_decision_epochs=len(decisions),
        pre_t13_freeze_decisions_excluded=pre_freeze_excluded,
        treatment_sealed_epochs=len(treatment_decisions),
        missing_treatment_decisions=missing_treatment,
        missing_baseline_policy_decisions=missing_baseline,
        selection_changed_epochs=changed_epochs,
        candidate_instances=candidate_instances,
        candidate_outcomes=candidate_outcomes,
        candidate_outcome_coverage=candidate_coverage,
        baseline_selected_instances=baseline_instances,
        baseline_selected_outcomes=baseline_outcomes,
        baseline_selected_outcome_coverage=baseline_coverage,
        treatment_selected_instances=treatment_instances,
        treatment_selected_outcomes=treatment_outcomes,
        treatment_selected_outcome_coverage=treatment_coverage,
        baseline_only_instances=baseline_only_instances,
        baseline_only_outcomes=baseline_only_outcomes,
        treatment_only_instances=treatment_only_instances,
        treatment_only_outcomes=treatment_only_outcomes,
        calendar_span_days=calendar_span_days,
        distinct_trading_days=distinct_days,
        represented_lineages=represented_lineages,
        minimum_outcomes_any_lineage=minimum_outcomes_any_lineage,
        minimum_fold_candidate_outcomes=minimum_fold_outcomes,
        minimum_fold_lineages=minimum_fold_lineages,
        minimum_decision_epochs=plan.minimum_decision_epochs,
        minimum_candidate_outcomes=plan.minimum_candidate_outcomes,
        minimum_selected_outcomes=plan.minimum_selected_outcomes,
        required_candidate_coverage=(
            plan.minimum_candidate_outcome_coverage
        ),
        required_selected_coverage=plan.required_selected_outcome_coverage,
        fold_count=plan.fold_count,
        fresh_oos_utility_demonstrated=False,
    )


def _usable(decision: Phase20ForwardDecisionSeal) -> bool:
    if decision.sealed_at is None:
        return False
    if (
        decision.seal_deadline_at is not None
        and not decision.sealed_within_deadline
    ):
        return False
    try:
        payload = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20 T13 OOS decision JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 T13 OOS decision payload must be object"
        )
    return payload.get("evidence_kind") == "FORWARD_OBSERVED"


def _candidate_lineage_map(
    decision: Phase20ForwardDecisionSeal,
) -> dict[str, str]:
    try:
        payload = json.loads(decision.canonical_payload_json)
        candidates = payload["candidates"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise CiboCapitalManagementError(
            "Phase20 T13 OOS candidate payload cannot be parsed"
        ) from error
    if not isinstance(candidates, list):
        raise CiboCapitalManagementError(
            "Phase20 T13 OOS candidates must be list"
        )
    result: dict[str, str] = {}
    for row in candidates:
        try:
            candidate = row["candidate"]
            fingerprint = str(candidate["signal_fingerprint"])
            trader_id = str(candidate["trader_id"])
        except (KeyError, TypeError) as error:
            raise CiboCapitalManagementError(
                "Phase20 T13 OOS candidate row invalid"
            ) from error
        if fingerprint in result:
            raise CiboCapitalManagementError(
                "Phase20 T13 OOS duplicate candidate fingerprint"
            )
        result[fingerprint] = trader_id
    return result


def _fold_population(
    rows: tuple[_OutcomeRow, ...],
    *,
    fold_count: int,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if not rows:
        return (), ()
    decision_order = tuple(
        key
        for key, _ in sorted(
            {
                item.evidence_sha256: item.decision_at_iso
                for item in rows
            }.items(),
            key=lambda pair: (pair[1], pair[0]),
        )
    )
    base, remainder = divmod(len(decision_order), fold_count)
    sizes: list[int] = []
    lineages: list[int] = []
    start = 0
    for index in range(fold_count):
        decision_count = base + (1 if index < remainder else 0)
        fold_ids = set(
            decision_order[start : start + decision_count]
        )
        start += decision_count
        fold = tuple(
            item for item in rows if item.evidence_sha256 in fold_ids
        )
        sizes.append(len(fold))
        lineages.append(len({item.trader_id for item in fold}))
    return tuple(sizes), tuple(lineages)


def _coverage(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal(0)
    return Decimal(numerator) / Decimal(denominator)


def _gate(blockers: list[str], condition: bool, blocker: str) -> None:
    if not condition:
        blockers.append(blocker)
