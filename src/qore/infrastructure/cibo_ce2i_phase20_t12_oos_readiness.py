"""Fresh OOS population readiness for the CE2I T12 shadow ablation.

This audit does not read realized PnL magnitudes. It only verifies that every
usable post-freeze FORWARD_OBSERVED decision has a durable canonical V3 policy
seal, a durable T12 treatment/control shadow seal and sufficient outcome
coverage to make a later fixed utility analysis legally comparable.

Treatment is the frozen V3 regime-driven tool eligibility. Control preserves
the same causal evidence, regime posture and MPC plan while neutralizing only
the T12 enabled_tools intervention. Population thresholds reuse the frozen
Phase20D qualification plan. A T12 effect must also be identifiable in every
contiguous temporal fold: at least one treatment/control selection divergence
per fold is required before utility analysis may run.
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
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_policy import (
    T12_SHADOW_POLICY_FROZEN_AT,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_store import (
    T12ShadowDecisionSeal,
)


@dataclass(frozen=True, slots=True)
class Phase20T12OosReadiness:
    ready_for_utility_analysis: bool
    blockers: tuple[str, ...]
    post_freeze_decision_epochs: int
    pre_t12_freeze_decisions_excluded: int
    shadow_sealed_epochs: int
    missing_shadow_decisions: int
    missing_treatment_policy_decisions: int
    selection_changed_epochs: int
    allocator_changed_epochs: int
    candidate_instances: int
    candidate_outcomes: int
    candidate_outcome_coverage: Decimal
    treatment_selected_instances: int
    treatment_selected_outcomes: int
    treatment_selected_outcome_coverage: Decimal
    control_selected_instances: int
    control_selected_outcomes: int
    control_selected_outcome_coverage: Decimal
    treatment_only_instances: int
    treatment_only_outcomes: int
    control_only_instances: int
    control_only_outcomes: int
    calendar_span_days: int
    distinct_trading_days: int
    represented_lineages: int
    minimum_outcomes_any_lineage: int
    minimum_fold_candidate_outcomes: int
    minimum_fold_lineages: int
    minimum_fold_selection_changed_epochs: int
    minimum_decision_epochs: int
    minimum_candidate_outcomes: int
    minimum_selected_outcomes: int
    required_candidate_coverage: Decimal
    required_selected_coverage: Decimal
    fold_count: int
    decision_sha256s: tuple[str, ...]
    changed_decision_sha256s: tuple[str, ...]
    fresh_oos_utility_demonstrated: bool

    def __post_init__(self) -> None:
        for name in (
            "post_freeze_decision_epochs",
            "pre_t12_freeze_decisions_excluded",
            "shadow_sealed_epochs",
            "missing_shadow_decisions",
            "missing_treatment_policy_decisions",
            "selection_changed_epochs",
            "allocator_changed_epochs",
            "candidate_instances",
            "candidate_outcomes",
            "treatment_selected_instances",
            "treatment_selected_outcomes",
            "control_selected_instances",
            "control_selected_outcomes",
            "treatment_only_instances",
            "treatment_only_outcomes",
            "control_only_instances",
            "control_only_outcomes",
            "calendar_span_days",
            "distinct_trading_days",
            "represented_lineages",
            "minimum_outcomes_any_lineage",
            "minimum_fold_candidate_outcomes",
            "minimum_fold_lineages",
            "minimum_fold_selection_changed_epochs",
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
                    f"Phase20 T12 OOS {name} must be non-negative int"
                )
        for name in (
            "candidate_outcome_coverage",
            "treatment_selected_outcome_coverage",
            "control_selected_outcome_coverage",
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
                    f"Phase20 T12 OOS {name} must be Decimal in [0,1]"
                )
        for name in (
            "ready_for_utility_analysis",
            "fresh_oos_utility_demonstrated",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 T12 OOS {name} must be bool"
                )
        if self.fresh_oos_utility_demonstrated:
            raise CiboCapitalManagementError(
                "Phase20 T12 readiness cannot demonstrate utility"
            )
        if self.ready_for_utility_analysis != (not self.blockers):
            raise CiboCapitalManagementError(
                "Phase20 T12 OOS readiness/blocker drift"
            )
        for values, label in (
            (self.decision_sha256s, "decision identities"),
            (self.changed_decision_sha256s, "changed decision identities"),
        ):
            if (
                len(values) != len(set(values))
                or any(
                    not item.startswith("sha256:") or len(item) != 71
                    for item in values
                )
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 OOS {label} invalid"
                )
        if len(self.decision_sha256s) != self.post_freeze_decision_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T12 OOS decision identity count drift"
            )
        if len(self.changed_decision_sha256s) != self.selection_changed_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T12 OOS changed decision identity count drift"
            )
        if not set(self.changed_decision_sha256s).issubset(
            set(self.decision_sha256s)
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 OOS changed decisions outside population"
            )


@dataclass(frozen=True, slots=True)
class _OutcomeRow:
    decision_at_date: date
    evidence_sha256: str
    trader_id: str


def assess_phase20_t12_oos_readiness(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    treatment_policy_book: VersionedPhase20ForwardPolicyBook,
    shadow_decisions: tuple[T12ShadowDecisionSeal, ...],
) -> Phase20T12OosReadiness:
    """Assess fresh T12 treatment/control comparability without PnL magnitudes."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T12 OOS requires canonical evidence book"
        )
    if not isinstance(
        treatment_policy_book,
        VersionedPhase20ForwardPolicyBook,
    ):
        raise CiboCapitalManagementError(
            "Phase20 T12 OOS requires canonical treatment policy book"
        )
    if not isinstance(shadow_decisions, tuple) or any(
        not isinstance(item, T12ShadowDecisionSeal)
        for item in shadow_decisions
    ):
        raise CiboCapitalManagementError(
            "Phase20 T12 OOS shadow decisions must be canonical tuple"
        )

    shadow_by_sha = {
        item.decision_evidence_sha256: item for item in shadow_decisions
    }
    if len(shadow_by_sha) != len(shadow_decisions):
        raise CiboCapitalManagementError(
            "Phase20 T12 OOS duplicate shadow evidence"
        )
    treatment_by_sha = {
        item.evidence_sha256: item
        for item in treatment_policy_book.decisions
    }
    outcomes = {
        (item.decision_evidence_sha256, item.signal_fingerprint)
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
        if item.decision_at >= T12_SHADOW_POLICY_FROZEN_AT
    )
    pre_freeze_excluded = len(all_usable) - len(decisions)

    candidate_instances = 0
    candidate_outcomes = 0
    treatment_instances = 0
    treatment_outcomes = 0
    control_instances = 0
    control_outcomes = 0
    treatment_only_instances = 0
    treatment_only_outcomes = 0
    control_only_instances = 0
    control_only_outcomes = 0
    missing_shadow = 0
    missing_treatment = 0
    selection_changed = 0
    allocator_changed = 0
    changed_sha256s: list[str] = []
    outcome_rows: list[_OutcomeRow] = []

    for decision in decisions:
        candidate_map = _candidate_lineage_map(decision)
        if set(candidate_map) != set(decision.signal_fingerprints):
            raise CiboCapitalManagementError(
                "Phase20 T12 OOS candidate payload/fingerprint mismatch"
            )
        candidate_instances += len(candidate_map)

        treatment_policy = treatment_by_sha.get(decision.evidence_sha256)
        shadow = shadow_by_sha.get(decision.evidence_sha256)

        if treatment_policy is None:
            missing_treatment += 1
            treatment_selected: tuple[str, ...] = ()
        else:
            treatment_selected = (
                treatment_policy.selected_signal_fingerprints
            )

        if shadow is None:
            missing_shadow += 1
            control_selected: tuple[str, ...] = ()
        else:
            if (
                shadow.decision_epoch_id != decision.decision_epoch_id
                or shadow.decision_at != decision.decision_at
            ):
                raise CiboCapitalManagementError(
                    "Phase20 T12 OOS shadow decision binding drift"
                )
            if treatment_policy is not None:
                if (
                    shadow.baseline_policy_record_sha256
                    != treatment_policy.policy_record_sha256
                    or shadow.treatment_selected_signal_fingerprints
                    != treatment_selected
                    or shadow.treatment_allocator_disposition
                    != treatment_policy.allocator_disposition
                ):
                    raise CiboCapitalManagementError(
                        "Phase20 T12 OOS treatment/shadow binding drift"
                    )
            control_selected = (
                shadow.control_selected_signal_fingerprints
            )
            if shadow.selection_changed:
                selection_changed += 1
                changed_sha256s.append(decision.evidence_sha256)
            if shadow.allocator_changed:
                allocator_changed += 1

        if not set(treatment_selected).issubset(candidate_map):
            raise CiboCapitalManagementError(
                "Phase20 T12 OOS treatment selected outside candidates"
            )
        if not set(control_selected).issubset(candidate_map):
            raise CiboCapitalManagementError(
                "Phase20 T12 OOS control selected outside candidates"
            )

        treatment_set = set(treatment_selected)
        control_set = set(control_selected)
        treatment_only = treatment_set - control_set
        control_only = control_set - treatment_set

        treatment_instances += len(treatment_set)
        control_instances += len(control_set)
        treatment_only_instances += len(treatment_only)
        control_only_instances += len(control_only)

        for fingerprint, trader_id in candidate_map.items():
            observed = (
                decision.evidence_sha256,
                fingerprint,
            ) in outcomes
            if observed:
                candidate_outcomes += 1
                outcome_rows.append(
                    _OutcomeRow(
                        decision_at_date=decision.decision_at.date(),
                        evidence_sha256=decision.evidence_sha256,
                        trader_id=trader_id,
                    )
                )
            if fingerprint in treatment_set and observed:
                treatment_outcomes += 1
            if fingerprint in control_set and observed:
                control_outcomes += 1
            if fingerprint in treatment_only and observed:
                treatment_only_outcomes += 1
            if fingerprint in control_only and observed:
                control_only_outcomes += 1

    candidate_coverage = _coverage(candidate_outcomes, candidate_instances)
    treatment_coverage = _coverage(treatment_outcomes, treatment_instances)
    control_coverage = _coverage(control_outcomes, control_instances)

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
    fold_outcomes, fold_lineages, fold_changes = _fold_population(
        decisions=decisions,
        outcome_rows=tuple(outcome_rows),
        changed_sha256s=frozenset(changed_sha256s),
        fold_count=plan.fold_count,
    )
    minimum_fold_outcomes = min(fold_outcomes) if fold_outcomes else 0
    minimum_fold_lineages = min(fold_lineages) if fold_lineages else 0
    minimum_fold_changes = min(fold_changes) if fold_changes else 0

    blockers: list[str] = []
    _gate(
        blockers,
        len(decisions) >= plan.minimum_decision_epochs,
        "T12_MINIMUM_DECISION_EPOCHS_NOT_MET",
    )
    _gate(
        blockers,
        candidate_outcomes >= plan.minimum_candidate_outcomes,
        "T12_MINIMUM_CANDIDATE_OUTCOMES_NOT_MET",
    )
    _gate(
        blockers,
        treatment_outcomes >= plan.minimum_selected_outcomes,
        "T12_MINIMUM_TREATMENT_SELECTED_OUTCOMES_NOT_MET",
    )
    _gate(
        blockers,
        control_outcomes >= plan.minimum_selected_outcomes,
        "T12_MINIMUM_CONTROL_SELECTED_OUTCOMES_NOT_MET",
    )
    _gate(
        blockers,
        calendar_span_days >= plan.minimum_calendar_span_days,
        "T12_MINIMUM_CALENDAR_SPAN_NOT_MET",
    )
    _gate(
        blockers,
        distinct_days >= plan.minimum_distinct_trading_days,
        "T12_MINIMUM_TRADING_DAYS_NOT_MET",
    )
    _gate(
        blockers,
        represented_lineages >= plan.minimum_global_lineages,
        "T12_MINIMUM_GLOBAL_LINEAGES_NOT_MET",
    )
    _gate(
        blockers,
        minimum_outcomes_any_lineage >= plan.minimum_outcomes_per_lineage,
        "T12_MINIMUM_OUTCOMES_PER_LINEAGE_NOT_MET",
    )
    _gate(
        blockers,
        minimum_fold_outcomes >= plan.minimum_fold_candidate_outcomes,
        "T12_MINIMUM_FOLD_CANDIDATE_OUTCOMES_NOT_MET",
    )
    _gate(
        blockers,
        minimum_fold_lineages >= plan.minimum_fold_lineages,
        "T12_MINIMUM_FOLD_LINEAGES_NOT_MET",
    )
    _gate(
        blockers,
        candidate_coverage >= plan.minimum_candidate_outcome_coverage,
        "T12_CANDIDATE_OUTCOME_COVERAGE_NOT_MET",
    )
    _gate(
        blockers,
        treatment_instances > 0,
        "T12_NO_TREATMENT_SELECTED_OPPORTUNITIES",
    )
    _gate(
        blockers,
        treatment_coverage >= plan.required_selected_outcome_coverage,
        "T12_TREATMENT_SELECTED_OUTCOME_COVERAGE_NOT_MET",
    )
    _gate(
        blockers,
        control_instances > 0,
        "T12_NO_CONTROL_SELECTED_OPPORTUNITIES",
    )
    _gate(
        blockers,
        control_coverage >= plan.required_selected_outcome_coverage,
        "T12_CONTROL_SELECTED_OUTCOME_COVERAGE_NOT_MET",
    )
    _gate(
        blockers,
        missing_treatment == 0,
        "T12_MISSING_TREATMENT_POLICY_DECISIONS",
    )
    _gate(
        blockers,
        missing_shadow == 0,
        "T12_MISSING_SHADOW_CONTROL_DECISIONS",
    )
    _gate(
        blockers,
        selection_changed > 0,
        "T12_NO_SELECTION_CHANGE_EPOCHS",
    )
    _gate(
        blockers,
        len(fold_changes) == plan.fold_count
        and minimum_fold_changes >= 1,
        "T12_SELECTION_CHANGE_NOT_IDENTIFIED_IN_EVERY_FOLD",
    )

    return Phase20T12OosReadiness(
        ready_for_utility_analysis=not blockers,
        blockers=tuple(blockers),
        post_freeze_decision_epochs=len(decisions),
        pre_t12_freeze_decisions_excluded=pre_freeze_excluded,
        shadow_sealed_epochs=sum(
            1
            for item in shadow_decisions
            if item.decision_at >= T12_SHADOW_POLICY_FROZEN_AT
        ),
        missing_shadow_decisions=missing_shadow,
        missing_treatment_policy_decisions=missing_treatment,
        selection_changed_epochs=selection_changed,
        allocator_changed_epochs=allocator_changed,
        candidate_instances=candidate_instances,
        candidate_outcomes=candidate_outcomes,
        candidate_outcome_coverage=candidate_coverage,
        treatment_selected_instances=treatment_instances,
        treatment_selected_outcomes=treatment_outcomes,
        treatment_selected_outcome_coverage=treatment_coverage,
        control_selected_instances=control_instances,
        control_selected_outcomes=control_outcomes,
        control_selected_outcome_coverage=control_coverage,
        treatment_only_instances=treatment_only_instances,
        treatment_only_outcomes=treatment_only_outcomes,
        control_only_instances=control_only_instances,
        control_only_outcomes=control_only_outcomes,
        calendar_span_days=calendar_span_days,
        distinct_trading_days=distinct_days,
        represented_lineages=represented_lineages,
        minimum_outcomes_any_lineage=minimum_outcomes_any_lineage,
        minimum_fold_candidate_outcomes=minimum_fold_outcomes,
        minimum_fold_lineages=minimum_fold_lineages,
        minimum_fold_selection_changed_epochs=minimum_fold_changes,
        minimum_decision_epochs=plan.minimum_decision_epochs,
        minimum_candidate_outcomes=plan.minimum_candidate_outcomes,
        minimum_selected_outcomes=plan.minimum_selected_outcomes,
        required_candidate_coverage=(
            plan.minimum_candidate_outcome_coverage
        ),
        required_selected_coverage=plan.required_selected_outcome_coverage,
        fold_count=plan.fold_count,
        decision_sha256s=tuple(
            item.evidence_sha256 for item in decisions
        ),
        changed_decision_sha256s=tuple(changed_sha256s),
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
            "Phase20 T12 OOS decision JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 T12 OOS decision payload must be object"
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
            "Phase20 T12 OOS candidate payload cannot be parsed"
        ) from error
    if not isinstance(candidates, list):
        raise CiboCapitalManagementError(
            "Phase20 T12 OOS candidates must be list"
        )
    result: dict[str, str] = {}
    for row in candidates:
        try:
            candidate = row["candidate"]
            fingerprint = str(candidate["signal_fingerprint"])
            trader_id = str(candidate["trader_id"])
        except (KeyError, TypeError) as error:
            raise CiboCapitalManagementError(
                "Phase20 T12 OOS candidate row invalid"
            ) from error
        if fingerprint in result:
            raise CiboCapitalManagementError(
                "Phase20 T12 OOS duplicate candidate fingerprint"
            )
        result[fingerprint] = trader_id
    return result


def _fold_population(
    *,
    decisions: tuple[Phase20ForwardDecisionSeal, ...],
    outcome_rows: tuple[_OutcomeRow, ...],
    changed_sha256s: frozenset[str],
    fold_count: int,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    if not decisions:
        return (), (), ()
    ordered = tuple(
        item.evidence_sha256
        for item in sorted(
            decisions,
            key=lambda row: (row.decision_at, row.evidence_sha256),
        )
    )
    base, remainder = divmod(len(ordered), fold_count)
    outcome_sizes: list[int] = []
    lineage_sizes: list[int] = []
    changed_sizes: list[int] = []
    start = 0
    for index in range(fold_count):
        decision_count = base + (1 if index < remainder else 0)
        fold_ids = set(ordered[start : start + decision_count])
        start += decision_count
        fold_outcomes = tuple(
            item for item in outcome_rows if item.evidence_sha256 in fold_ids
        )
        outcome_sizes.append(len(fold_outcomes))
        lineage_sizes.append(
            len({item.trader_id for item in fold_outcomes})
        )
        changed_sizes.append(
            len(fold_ids & set(changed_sha256s))
        )
    return (
        tuple(outcome_sizes),
        tuple(lineage_sizes),
        tuple(changed_sizes),
    )


def _coverage(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal(0)
    return Decimal(numerator) / Decimal(denominator)


def _gate(blockers: list[str], condition: bool, blocker: str) -> None:
    if not condition:
        blockers.append(blocker)
