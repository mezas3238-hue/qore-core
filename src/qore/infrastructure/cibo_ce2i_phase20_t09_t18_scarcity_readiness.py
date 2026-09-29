"""Fresh scarcity-population readiness for CE2I T09 and T18.

The historical Phase19L result found zero exact competition epochs. This module
therefore inspects only fresh FORWARD_OBSERVED Phase20D decisions and determines
whether a later fixed OOS scarcity-utility analysis is legally possible.

T09 requires at least the already-frozen 30 exact scarce competition epochs.
T18 applies the same threshold to scarcity where at least two distinct Trader
lineages compete in the same decision epoch. Candidate-outcome coverage and
selected-outcome coverage reuse the frozen Phase20D coverage thresholds, and
coverage is checked again across four contiguous folds.

No PnL magnitude is read. Population readiness does not identify a competition
policy, demonstrate utility, or grant allocation authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19l_competition import (
    MINIMUM_ROBUST_COMPETITION_EPOCHS,
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


@dataclass(frozen=True, slots=True)
class Phase20T09T18ScarcityFold:
    fold_index: int
    decision_epochs: int
    candidate_instances: int
    candidate_outcomes: int
    selected_instances: int
    selected_outcomes: int
    candidate_outcome_coverage: Decimal
    selected_outcome_coverage: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.fold_index, int)
            or isinstance(self.fold_index, bool)
            or self.fold_index < 0
        ):
            raise CiboCapitalManagementError(
                "Phase20 scarcity fold index must be non-negative int"
            )
        for name in (
            "decision_epochs",
            "candidate_instances",
            "candidate_outcomes",
            "selected_instances",
            "selected_outcomes",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 scarcity fold {name} must be non-negative int"
                )
        for name in (
            "candidate_outcome_coverage",
            "selected_outcome_coverage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 scarcity fold {name} must be Decimal in [0,1]"
                )


@dataclass(frozen=True, slots=True)
class Phase20T09T18ScarcityReadiness:
    usable_forward_epochs: int
    exact_competition_epochs: int
    scarce_competition_epochs: int
    cross_trader_scarce_epochs: int
    scarcity_candidate_instances: int
    scarcity_candidate_outcomes: int
    scarcity_selected_instances: int
    scarcity_selected_outcomes: int
    scarcity_candidate_outcome_coverage: Decimal
    scarcity_selected_outcome_coverage: Decimal
    represented_lineages: tuple[str, ...]
    missing_policy_scarcity_epochs: int
    t09_folds: tuple[Phase20T09T18ScarcityFold, ...]
    t18_folds: tuple[Phase20T09T18ScarcityFold, ...]
    t09_ready_for_utility_analysis: bool
    t18_ready_for_utility_analysis: bool
    fresh_oos_utility_demonstrated: bool
    t09_blockers: tuple[str, ...]
    t18_blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "usable_forward_epochs",
            "exact_competition_epochs",
            "scarce_competition_epochs",
            "cross_trader_scarce_epochs",
            "scarcity_candidate_instances",
            "scarcity_candidate_outcomes",
            "scarcity_selected_instances",
            "scarcity_selected_outcomes",
            "missing_policy_scarcity_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 scarcity {name} must be non-negative int"
                )
        if self.cross_trader_scarce_epochs > self.scarce_competition_epochs:
            raise CiboCapitalManagementError(
                "Phase20 cross-Trader scarcity cannot exceed scarcity"
            )
        for name in (
            "scarcity_candidate_outcome_coverage",
            "scarcity_selected_outcome_coverage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 scarcity {name} must be Decimal in [0,1]"
                )
        if len(self.represented_lineages) != len(set(self.represented_lineages)):
            raise CiboCapitalManagementError(
                "Phase20 scarcity represented lineages must be unique"
            )
        if self.fresh_oos_utility_demonstrated:
            raise CiboCapitalManagementError(
                "Phase20 scarcity readiness cannot demonstrate utility"
            )
        if self.t09_ready_for_utility_analysis != (not self.t09_blockers):
            raise CiboCapitalManagementError(
                "Phase20 T09 scarcity readiness/blocker drift"
            )
        if self.t18_ready_for_utility_analysis != (not self.t18_blockers):
            raise CiboCapitalManagementError(
                "Phase20 T18 scarcity readiness/blocker drift"
            )


@dataclass(frozen=True, slots=True)
class _Epoch:
    decision: Phase20ForwardDecisionSeal
    candidate_signals: tuple[str, ...]
    candidate_traders: tuple[str, ...]
    selected_signals: tuple[str, ...]
    candidate_outcomes: int
    selected_outcomes: int


def assess_phase20_t09_t18_scarcity_readiness(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    policy_book: VersionedPhase20ForwardPolicyBook,
) -> Phase20T09T18ScarcityReadiness:
    """Assess fresh scarcity population maturity without reading PnL."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 scarcity readiness requires canonical evidence book"
        )
    if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
        raise CiboCapitalManagementError(
            "Phase20 scarcity readiness requires canonical policy book"
        )

    outcomes = {
        (item.decision_evidence_sha256, item.signal_fingerprint)
        for item in evidence_book.outcomes
    }
    policies = {
        item.evidence_sha256: item for item in policy_book.decisions
    }
    usable = tuple(
        item
        for item in sorted(
            evidence_book.decisions,
            key=lambda row: (row.decision_at, row.evidence_sha256),
        )
        if _usable(item)
    )

    exact_count = 0
    scarce_rows: list[_Epoch] = []
    cross_rows: list[_Epoch] = []
    missing_policy = 0
    lineages: set[str] = set()

    for decision in usable:
        payload = _payload(decision)
        candidates = _candidates(payload)
        if len(candidates) < 2:
            continue
        exact_count += 1
        if not _scarce(payload, candidates):
            continue

        policy = policies.get(decision.evidence_sha256)
        if policy is None:
            missing_policy += 1
            continue
        candidate_signals = tuple(
            str(item["signal_fingerprint"]) for item in candidates
        )
        candidate_traders = tuple(
            str(item["trader_id"]) for item in candidates
        )
        if len(candidate_signals) != len(set(candidate_signals)):
            raise CiboCapitalManagementError(
                "Phase20 scarcity candidate signals must be unique"
            )
        selected = policy.selected_signal_fingerprints
        if not set(selected).issubset(set(candidate_signals)):
            raise CiboCapitalManagementError(
                "Phase20 scarcity policy selected outside candidate set"
            )
        row = _Epoch(
            decision=decision,
            candidate_signals=candidate_signals,
            candidate_traders=candidate_traders,
            selected_signals=selected,
            candidate_outcomes=sum(
                1
                for signal in candidate_signals
                if (decision.evidence_sha256, signal) in outcomes
            ),
            selected_outcomes=sum(
                1
                for signal in selected
                if (decision.evidence_sha256, signal) in outcomes
            ),
        )
        scarce_rows.append(row)
        lineages.update(candidate_traders)
        if len(set(candidate_traders)) >= 2:
            cross_rows.append(row)

    candidate_instances = sum(
        len(item.candidate_signals) for item in scarce_rows
    )
    candidate_outcomes = sum(item.candidate_outcomes for item in scarce_rows)
    selected_instances = sum(
        len(item.selected_signals) for item in scarce_rows
    )
    selected_outcomes = sum(item.selected_outcomes for item in scarce_rows)
    candidate_coverage = _coverage(
        candidate_outcomes,
        candidate_instances,
    )
    selected_coverage = _coverage(
        selected_outcomes,
        selected_instances,
    )

    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    t09_folds = _folds(scarce_rows, plan.fold_count)
    t18_folds = _folds(cross_rows, plan.fold_count)

    t09_blockers: list[str] = []
    if len(scarce_rows) < MINIMUM_ROBUST_COMPETITION_EPOCHS:
        t09_blockers.append(
            "T09_FRESH_SCARCE_COMPETITION_EPOCHS_"
            f"{len(scarce_rows)}_OF_{MINIMUM_ROBUST_COMPETITION_EPOCHS}"
        )
    if missing_policy:
        t09_blockers.append("T09_SCARCITY_POLICY_COVERAGE_INCOMPLETE")
    if candidate_coverage < plan.minimum_candidate_outcome_coverage:
        t09_blockers.append("T09_SCARCITY_CANDIDATE_OUTCOME_COVERAGE_NOT_MET")
    if selected_instances == 0:
        t09_blockers.append("T09_SCARCITY_NO_SELECTED_OPPORTUNITIES")
    elif selected_coverage < plan.required_selected_outcome_coverage:
        t09_blockers.append("T09_SCARCITY_SELECTED_OUTCOME_COVERAGE_NOT_MET")
    if len(t09_folds) != plan.fold_count or any(
        item.decision_epochs == 0 for item in t09_folds
    ):
        t09_blockers.append("T09_SCARCITY_CONTIGUOUS_FOLDS_INCOMPLETE")
    elif any(
        item.candidate_outcome_coverage
        < plan.minimum_candidate_outcome_coverage
        or item.selected_outcome_coverage
        < plan.required_selected_outcome_coverage
        for item in t09_folds
    ):
        t09_blockers.append("T09_SCARCITY_FOLD_COVERAGE_NOT_MET")

    t18_blockers: list[str] = []
    if len(cross_rows) < MINIMUM_ROBUST_COMPETITION_EPOCHS:
        t18_blockers.append(
            "T18_FRESH_CROSS_TRADER_SCARCE_EPOCHS_"
            f"{len(cross_rows)}_OF_{MINIMUM_ROBUST_COMPETITION_EPOCHS}"
        )
    if missing_policy:
        t18_blockers.append("T18_SCARCITY_POLICY_COVERAGE_INCOMPLETE")
    cross_candidate_instances = sum(
        len(item.candidate_signals) for item in cross_rows
    )
    cross_candidate_outcomes = sum(
        item.candidate_outcomes for item in cross_rows
    )
    cross_selected_instances = sum(
        len(item.selected_signals) for item in cross_rows
    )
    cross_selected_outcomes = sum(
        item.selected_outcomes for item in cross_rows
    )
    if _coverage(
        cross_candidate_outcomes,
        cross_candidate_instances,
    ) < plan.minimum_candidate_outcome_coverage:
        t18_blockers.append(
            "T18_CROSS_TRADER_CANDIDATE_OUTCOME_COVERAGE_NOT_MET"
        )
    if cross_selected_instances == 0:
        t18_blockers.append("T18_CROSS_TRADER_NO_SELECTED_OPPORTUNITIES")
    elif _coverage(
        cross_selected_outcomes,
        cross_selected_instances,
    ) < plan.required_selected_outcome_coverage:
        t18_blockers.append(
            "T18_CROSS_TRADER_SELECTED_OUTCOME_COVERAGE_NOT_MET"
        )
    if len(t18_folds) != plan.fold_count or any(
        item.decision_epochs == 0 for item in t18_folds
    ):
        t18_blockers.append("T18_CROSS_TRADER_CONTIGUOUS_FOLDS_INCOMPLETE")
    elif any(
        item.candidate_outcome_coverage
        < plan.minimum_candidate_outcome_coverage
        or item.selected_outcome_coverage
        < plan.required_selected_outcome_coverage
        for item in t18_folds
    ):
        t18_blockers.append("T18_CROSS_TRADER_FOLD_COVERAGE_NOT_MET")

    return Phase20T09T18ScarcityReadiness(
        usable_forward_epochs=len(usable),
        exact_competition_epochs=exact_count,
        scarce_competition_epochs=len(scarce_rows),
        cross_trader_scarce_epochs=len(cross_rows),
        scarcity_candidate_instances=candidate_instances,
        scarcity_candidate_outcomes=candidate_outcomes,
        scarcity_selected_instances=selected_instances,
        scarcity_selected_outcomes=selected_outcomes,
        scarcity_candidate_outcome_coverage=candidate_coverage,
        scarcity_selected_outcome_coverage=selected_coverage,
        represented_lineages=tuple(sorted(lineages)),
        missing_policy_scarcity_epochs=missing_policy,
        t09_folds=t09_folds,
        t18_folds=t18_folds,
        t09_ready_for_utility_analysis=not t09_blockers,
        t18_ready_for_utility_analysis=not t18_blockers,
        fresh_oos_utility_demonstrated=False,
        t09_blockers=tuple(t09_blockers),
        t18_blockers=tuple(t18_blockers),
    )


def _folds(
    rows: list[_Epoch],
    fold_count: int,
) -> tuple[Phase20T09T18ScarcityFold, ...]:
    if not rows:
        return ()
    base, remainder = divmod(len(rows), fold_count)
    result: list[Phase20T09T18ScarcityFold] = []
    start = 0
    for index in range(fold_count):
        count = base + (1 if index < remainder else 0)
        fold = rows[start : start + count]
        start += count
        candidate_instances = sum(
            len(item.candidate_signals) for item in fold
        )
        candidate_outcomes = sum(
            item.candidate_outcomes for item in fold
        )
        selected_instances = sum(
            len(item.selected_signals) for item in fold
        )
        selected_outcomes = sum(
            item.selected_outcomes for item in fold
        )
        result.append(
            Phase20T09T18ScarcityFold(
                fold_index=index,
                decision_epochs=len(fold),
                candidate_instances=candidate_instances,
                candidate_outcomes=candidate_outcomes,
                selected_instances=selected_instances,
                selected_outcomes=selected_outcomes,
                candidate_outcome_coverage=_coverage(
                    candidate_outcomes,
                    candidate_instances,
                ),
                selected_outcome_coverage=_coverage(
                    selected_outcomes,
                    selected_instances,
                ),
            )
        )
    return tuple(result)


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


def _payload(decision: Phase20ForwardDecisionSeal) -> dict[str, object]:
    try:
        payload = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20 scarcity decision payload invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 scarcity decision payload must be object"
        )
    return payload


def _candidates(
    payload: dict[str, object],
) -> tuple[dict[str, object], ...]:
    rows = payload.get("candidates")
    if not isinstance(rows, list):
        raise CiboCapitalManagementError(
            "Phase20 scarcity candidates must be list"
        )
    result: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "Phase20 scarcity candidate evidence must be object"
            )
        candidate = row.get("candidate")
        if not isinstance(candidate, dict):
            raise CiboCapitalManagementError(
                "Phase20 scarcity candidate must be object"
            )
        for field in (
            "signal_fingerprint",
            "trader_id",
            "concentration_group",
        ):
            if not isinstance(candidate.get(field), str):
                raise CiboCapitalManagementError(
                    f"Phase20 scarcity candidate {field} is invalid"
                )
        result.append(candidate)
    return tuple(result)


def _scarce(
    payload: dict[str, object],
    candidates: tuple[dict[str, object], ...],
) -> bool:
    risk_headroom = _decimal(payload.get("hard_risk_headroom_usd"))
    margin_headroom = _decimal(payload.get("margin_headroom_usd"))
    total_risk = sum(
        (_decimal(item.get("stop_risk_usd")) for item in candidates),
        Decimal(0),
    )
    total_margin = sum(
        (_decimal(item.get("margin_usd")) for item in candidates),
        Decimal(0),
    )
    if total_risk > risk_headroom or total_margin > margin_headroom:
        return True

    limits_raw = payload.get("concentration_limit_by_group")
    if not isinstance(limits_raw, list):
        raise CiboCapitalManagementError(
            "Phase20 scarcity concentration limits must be list"
        )
    limits: dict[str, Decimal] = {}
    for item in limits_raw:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], str)
        ):
            raise CiboCapitalManagementError(
                "Phase20 scarcity concentration limit row invalid"
            )
        limits[item[0]] = _decimal(item[1])

    used: dict[str, Decimal] = {}
    for candidate in candidates:
        group = str(candidate["concentration_group"])
        used[group] = used.get(group, Decimal(0)) + _decimal(
            candidate.get("concentration_risk_usd")
        )
    return any(
        group in limits and amount > limits[group]
        for group, amount in used.items()
    )


def _coverage(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal(1)
    return Decimal(numerator) / Decimal(denominator)


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            "Phase20 scarcity monetary field invalid"
        ) from error
    if not result.is_finite() or result < 0:
        raise CiboCapitalManagementError(
            "Phase20 scarcity monetary field must be finite non-negative"
        )
    return result
