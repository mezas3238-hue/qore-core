"""Population-readiness gate for pre-registered Phase20D V2 qualification.

This module determines whether the fresh-forward evidence population is mature
enough to run the fixed economic WFO. It intentionally does not read realized
outcome magnitudes; only causal completeness, coverage, temporal span and
lineage representation are assessed.
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
)
from qore.infrastructure.cibo_ce2i_qualification_evidence_protocol import (
    Phase20QualificationEvidenceBook,
    require_qualification_evidence_book,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)


@dataclass(frozen=True, slots=True)
class Phase20QualificationReadiness:
    ready: bool
    reasons: tuple[str, ...]
    decision_epochs: int
    candidate_instances: int
    candidate_outcomes: int
    selected_instances: int
    selected_outcomes: int
    candidate_outcome_coverage: Decimal
    selected_outcome_coverage: Decimal
    calendar_span_days: int
    distinct_trading_days: int
    represented_lineages: int
    minimum_outcomes_any_lineage: int
    minimum_fold_candidate_outcomes: int
    minimum_fold_lineages: int
    missing_policy_decisions: int
    pre_freeze_decisions: int


@dataclass(frozen=True, slots=True)
class _OutcomeRow:
    decision_at_date: date
    decision_at_iso: str
    evidence_sha256: str
    signal_fingerprint: str
    trader_id: str


def assess_phase20d_qualification_readiness(
    *,
    evidence_book: Phase20QualificationEvidenceBook,
    policy_book: VersionedPhase20ForwardPolicyBook,
) -> Phase20QualificationReadiness:
    """Assess readiness without inspecting realized outcome values."""

    evidence_book = require_qualification_evidence_book(
        evidence_book,
        context="Phase20D readiness",
    )
    if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
        raise CiboCapitalManagementError(
            "Phase20D readiness requires canonical policy book"
        )

    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    policy_by_sha = {
        item.evidence_sha256: item
        for item in policy_book.decisions
    }
    outcomes = {
        (item.decision_evidence_sha256, item.signal_fingerprint): item
        for item in evidence_book.outcomes
    }

    candidate_instances = 0
    candidate_outcomes = 0
    selected_instances = 0
    selected_outcomes = 0
    missing_policy_decisions = 0
    pre_freeze_decisions = 0
    outcome_rows: list[_OutcomeRow] = []

    for decision in sorted(
        evidence_book.decisions,
        key=lambda item: (item.decision_at, item.evidence_sha256),
    ):
        if decision.decision_at < plan.frozen_at:
            pre_freeze_decisions += 1
        candidate_map = _candidate_lineage_map(decision)
        if set(candidate_map) != set(decision.signal_fingerprints):
            raise CiboCapitalManagementError(
                "Phase20D stored candidate payload/fingerprint mismatch"
            )
        candidate_instances += len(decision.signal_fingerprints)
        policy = policy_by_sha.get(decision.evidence_sha256)
        selected = (
            policy.selected_signal_fingerprints
            if policy is not None
            else ()
        )
        if policy is None:
            missing_policy_decisions += 1
        elif not set(selected).issubset(candidate_map):
            raise CiboCapitalManagementError(
                "Phase20D policy selected signal outside sealed candidates"
            )
        selected_instances += len(selected)

        for fingerprint, trader_id in candidate_map.items():
            key = (decision.evidence_sha256, fingerprint)
            if key not in outcomes:
                continue
            candidate_outcomes += 1
            if fingerprint in selected:
                selected_outcomes += 1
            outcome_rows.append(
                _OutcomeRow(
                    decision_at_date=decision.decision_at.date(),
                    decision_at_iso=decision.decision_at.isoformat(),
                    evidence_sha256=decision.evidence_sha256,
                    signal_fingerprint=fingerprint,
                    trader_id=trader_id,
                )
            )

    candidate_coverage = _coverage(
        candidate_outcomes,
        candidate_instances,
    )
    selected_coverage = _coverage(
        selected_outcomes,
        selected_instances,
    )
    decision_dates = tuple(
        item.decision_at.date() for item in evidence_book.decisions
    )
    if decision_dates:
        calendar_span_days = (
            max(decision_dates) - min(decision_dates)
        ).days + 1
        distinct_days = len(set(decision_dates))
    else:
        calendar_span_days = 0
        distinct_days = 0

    lineage_counts = Counter(item.trader_id for item in outcome_rows)
    represented_lineages = len(lineage_counts)
    minimum_outcomes_any_lineage = (
        min(lineage_counts.values()) if lineage_counts else 0
    )
    fold_sizes, fold_lineages = _fold_population(
        tuple(outcome_rows),
        fold_count=plan.fold_count,
    )
    minimum_fold_outcomes = min(fold_sizes) if fold_sizes else 0
    minimum_fold_lineages = min(fold_lineages) if fold_lineages else 0

    reasons: list[str] = []
    _gate(
        reasons,
        pre_freeze_decisions == 0,
        "DECISION_PREDATES_QUALIFICATION_FREEZE",
    )
    _gate(
        reasons,
        len(evidence_book.decisions) >= plan.minimum_decision_epochs,
        "MINIMUM_DECISION_EPOCHS_NOT_MET",
    )
    _gate(
        reasons,
        candidate_outcomes >= plan.minimum_candidate_outcomes,
        "MINIMUM_CANDIDATE_OUTCOMES_NOT_MET",
    )
    _gate(
        reasons,
        selected_outcomes >= plan.minimum_selected_outcomes,
        "MINIMUM_SELECTED_OUTCOMES_NOT_MET",
    )
    _gate(
        reasons,
        calendar_span_days >= plan.minimum_calendar_span_days,
        "MINIMUM_CALENDAR_SPAN_NOT_MET",
    )
    _gate(
        reasons,
        distinct_days >= plan.minimum_distinct_trading_days,
        "MINIMUM_DISTINCT_TRADING_DAYS_NOT_MET",
    )
    _gate(
        reasons,
        represented_lineages >= plan.minimum_global_lineages,
        "MINIMUM_GLOBAL_LINEAGES_NOT_MET",
    )
    _gate(
        reasons,
        minimum_outcomes_any_lineage >= plan.minimum_outcomes_per_lineage,
        "MINIMUM_OUTCOMES_PER_LINEAGE_NOT_MET",
    )
    _gate(
        reasons,
        minimum_fold_outcomes >= plan.minimum_fold_candidate_outcomes,
        "MINIMUM_FOLD_CANDIDATE_OUTCOMES_NOT_MET",
    )
    _gate(
        reasons,
        minimum_fold_lineages >= plan.minimum_fold_lineages,
        "MINIMUM_FOLD_LINEAGES_NOT_MET",
    )
    _gate(
        reasons,
        candidate_coverage >= plan.minimum_candidate_outcome_coverage,
        "CANDIDATE_OUTCOME_COVERAGE_NOT_MET",
    )
    _gate(
        reasons,
        selected_coverage >= plan.required_selected_outcome_coverage,
        "SELECTED_OUTCOME_COVERAGE_NOT_MET",
    )
    _gate(
        reasons,
        missing_policy_decisions == 0,
        "MISSING_POLICY_DECISIONS",
    )

    return Phase20QualificationReadiness(
        ready=not reasons,
        reasons=tuple(reasons),
        decision_epochs=len(evidence_book.decisions),
        candidate_instances=candidate_instances,
        candidate_outcomes=candidate_outcomes,
        selected_instances=selected_instances,
        selected_outcomes=selected_outcomes,
        candidate_outcome_coverage=candidate_coverage,
        selected_outcome_coverage=selected_coverage,
        calendar_span_days=calendar_span_days,
        distinct_trading_days=distinct_days,
        represented_lineages=represented_lineages,
        minimum_outcomes_any_lineage=minimum_outcomes_any_lineage,
        minimum_fold_candidate_outcomes=minimum_fold_outcomes,
        minimum_fold_lineages=minimum_fold_lineages,
        missing_policy_decisions=missing_policy_decisions,
        pre_freeze_decisions=pre_freeze_decisions,
    )


def _candidate_lineage_map(
    decision: Phase20ForwardDecisionSeal,
) -> dict[str, str]:
    try:
        payload = json.loads(decision.canonical_payload_json)
        candidates = payload["candidates"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise CiboCapitalManagementError(
            "Phase20D canonical decision payload cannot be parsed"
        ) from error
    if not isinstance(candidates, list):
        raise CiboCapitalManagementError(
            "Phase20D canonical candidate population must be list"
        )
    result: dict[str, str] = {}
    for row in candidates:
        try:
            candidate = row["candidate"]
            fingerprint = str(candidate["signal_fingerprint"])
            trader_id = str(candidate["trader_id"])
        except (KeyError, TypeError) as error:
            raise CiboCapitalManagementError(
                "Phase20D canonical candidate row is invalid"
            ) from error
        if fingerprint in result:
            raise CiboCapitalManagementError(
                "Phase20D duplicate candidate fingerprint in payload"
            )
        result[fingerprint] = trader_id
    return result


def _fold_population(
    rows: tuple[_OutcomeRow, ...],
    *,
    fold_count: int,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Partition contiguous decision epochs; never split one epoch across folds."""

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


def _gate(reasons: list[str], condition: bool, reason: str) -> None:
    if not condition:
        reasons.append(reason)
