"""Structural evidence-book contract shared by forward and historical replay.

The economic qualification math depends on sealed decisions plus a small,
explicit outcome surface. Provider-specific settlement provenance belongs to the
evidence producer, not to the qualification math itself.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol, cast, runtime_checkable

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
)


@runtime_checkable
class Phase20QualificationOutcome(Protocol):
    evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    observed_at: datetime
    realized_net_pnl_usd: Decimal
    executed_initial_stop_risk_usd: Decimal
    realized_structural_outcome_r: Decimal
    capital_minutes: Decimal | None


@runtime_checkable
class Phase20QualificationEvidenceBook(Protocol):
    generation: int
    decisions: tuple[Phase20ForwardDecisionSeal, ...]
    outcomes: tuple[Phase20QualificationOutcome, ...]


def require_qualification_evidence_book(
    value: object,
    *,
    context: str,
) -> Phase20QualificationEvidenceBook:
    """Validate the exact structural surface consumed by qualification."""

    if not isinstance(value, Phase20QualificationEvidenceBook):
        raise CiboCapitalManagementError(
            f"{context} requires canonical qualification evidence surface"
        )
    if (
        not isinstance(value.generation, int)
        or isinstance(value.generation, bool)
        or value.generation < 0
    ):
        raise CiboCapitalManagementError(
            f"{context} evidence generation invalid"
        )
    if any(
        not isinstance(item, Phase20ForwardDecisionSeal)
        for item in value.decisions
    ):
        raise CiboCapitalManagementError(
            f"{context} decisions must be canonical sealed decisions"
        )
    if any(
        not isinstance(item, Phase20QualificationOutcome)
        for item in value.outcomes
    ):
        raise CiboCapitalManagementError(
            f"{context} outcomes do not satisfy qualification contract"
        )

    decision_shas = tuple(item.evidence_sha256 for item in value.decisions)
    outcome_ids = tuple(item.evidence_id for item in value.outcomes)
    outcome_keys = tuple(
        (item.decision_evidence_sha256, item.signal_fingerprint)
        for item in value.outcomes
    )
    if len(decision_shas) != len(set(decision_shas)):
        raise CiboCapitalManagementError(
            f"{context} duplicate decision SHA"
        )
    if len(outcome_ids) != len(set(outcome_ids)):
        raise CiboCapitalManagementError(
            f"{context} duplicate outcome id"
        )
    if len(outcome_keys) != len(set(outcome_keys)):
        raise CiboCapitalManagementError(
            f"{context} duplicate decision/signal outcome"
        )
    decision_by_sha = {
        item.evidence_sha256: item for item in value.decisions
    }
    for outcome in value.outcomes:
        decision = decision_by_sha.get(outcome.decision_evidence_sha256)
        if decision is None:
            raise CiboCapitalManagementError(
                f"{context} outcome has no sealed decision"
            )
        if outcome.signal_fingerprint not in decision.signal_fingerprints:
            raise CiboCapitalManagementError(
                f"{context} outcome signal was not sealed pre-decision"
            )
        if outcome.observed_at <= decision.decision_at:
            raise CiboCapitalManagementError(
                f"{context} outcome must follow decision"
            )
    return cast(Phase20QualificationEvidenceBook, value)
