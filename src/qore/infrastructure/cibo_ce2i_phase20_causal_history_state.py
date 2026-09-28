"""Causal pre-decision history state reconstructed from Phase20D evidence.

The reconstruction uses only decision epochs physically sealed before the
current decision and reconciled outcomes observed before it. It therefore
provides T13 research with loss-cluster, settlement-drawdown and opportunity
arrival evidence without rewriting any historical decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)


@dataclass(frozen=True, slots=True)
class Phase20CausalHistoryState:
    decision_at: datetime
    prior_decision_epochs: int
    prior_candidate_instances: int
    prior_settled_outcomes: int
    consecutive_settled_losses: int
    cumulative_net_pnl_usd: Decimal
    peak_cumulative_net_pnl_usd: Decimal
    settlement_cash_drawdown_usd: Decimal
    max_settlement_cash_drawdown_usd: Decimal
    observed_candidate_arrivals_per_day: Decimal | None
    source_decision_sha256s: tuple[str, ...]
    source_outcome_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            self.decision_at.tzinfo is None
            or self.decision_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "Phase20 causal history decision_at must be timezone-aware"
            )
        for name in (
            "prior_decision_epochs",
            "prior_candidate_instances",
            "prior_settled_outcomes",
            "consecutive_settled_losses",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 causal history {name} must be non-negative int"
                )
        if self.consecutive_settled_losses > self.prior_settled_outcomes:
            raise CiboCapitalManagementError(
                "Phase20 loss cluster cannot exceed settled outcome count"
            )
        for name in (
            "cumulative_net_pnl_usd",
            "peak_cumulative_net_pnl_usd",
            "settlement_cash_drawdown_usd",
            "max_settlement_cash_drawdown_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Phase20 causal history {name} must be finite Decimal"
                )
        if (
            self.settlement_cash_drawdown_usd < 0
            or self.max_settlement_cash_drawdown_usd < 0
            or self.max_settlement_cash_drawdown_usd
            < self.settlement_cash_drawdown_usd
        ):
            raise CiboCapitalManagementError(
                "Phase20 settlement drawdown accounting is invalid"
            )
        rate = self.observed_candidate_arrivals_per_day
        if rate is not None and (
            not isinstance(rate, Decimal)
            or not rate.is_finite()
            or rate < 0
        ):
            raise CiboCapitalManagementError(
                "Phase20 candidate arrival rate must be finite non-negative Decimal/null"
            )
        if len(self.source_decision_sha256s) != len(
            set(self.source_decision_sha256s)
        ):
            raise CiboCapitalManagementError(
                "Phase20 causal history decision sources must be unique"
            )
        if len(self.source_outcome_evidence_ids) != len(
            set(self.source_outcome_evidence_ids)
        ):
            raise CiboCapitalManagementError(
                "Phase20 causal history outcome sources must be unique"
            )


def build_phase20_causal_history_state(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    decision: Phase20ForwardDecisionSeal,
) -> Phase20CausalHistoryState:
    """Reconstruct only information that existed strictly before decision."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 causal history requires canonical evidence book"
        )
    if not isinstance(decision, Phase20ForwardDecisionSeal):
        raise CiboCapitalManagementError(
            "Phase20 causal history requires canonical decision seal"
        )
    if evidence_book.decision_for_sha(decision.evidence_sha256) != decision:
        raise CiboCapitalManagementError(
            "Phase20 causal history decision must belong to evidence book"
        )

    prior_decisions = tuple(
        item
        for item in sorted(
            evidence_book.decisions,
            key=lambda row: (row.decision_at, row.evidence_sha256),
        )
        if (
            item.decision_at < decision.decision_at
            and item.sealed_at is not None
            and item.sealed_at <= decision.decision_at
            and (
                item.seal_deadline_at is None
                or item.sealed_within_deadline
            )
            and _evidence_kind(item) == "FORWARD_OBSERVED"
        )
    )
    prior_shas = {item.evidence_sha256 for item in prior_decisions}
    outcomes = tuple(
        item
        for item in sorted(
            evidence_book.outcomes,
            key=lambda row: (row.observed_at, row.evidence_id),
        )
        if (
            item.decision_evidence_sha256 in prior_shas
            and item.observed_at < decision.decision_at
        )
    )

    cumulative = Decimal(0)
    peak = Decimal(0)
    max_drawdown = Decimal(0)
    for outcome in outcomes:
        cumulative += outcome.realized_net_pnl_usd
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)
    drawdown = peak - cumulative

    loss_cluster = 0
    for outcome in reversed(outcomes):
        if outcome.realized_net_pnl_usd >= 0:
            break
        loss_cluster += 1

    candidate_instances = sum(
        _candidate_count(item) for item in prior_decisions
    )
    arrival_rate: Decimal | None = None
    if prior_decisions:
        elapsed_seconds = Decimal(
            str(
                (
                    decision.decision_at
                    - prior_decisions[0].decision_at
                ).total_seconds()
            )
        )
        if elapsed_seconds > 0:
            arrival_rate = (
                Decimal(candidate_instances)
                * Decimal(86400)
                / elapsed_seconds
            )

    return Phase20CausalHistoryState(
        decision_at=decision.decision_at,
        prior_decision_epochs=len(prior_decisions),
        prior_candidate_instances=candidate_instances,
        prior_settled_outcomes=len(outcomes),
        consecutive_settled_losses=loss_cluster,
        cumulative_net_pnl_usd=cumulative,
        peak_cumulative_net_pnl_usd=peak,
        settlement_cash_drawdown_usd=drawdown,
        max_settlement_cash_drawdown_usd=max_drawdown,
        observed_candidate_arrivals_per_day=arrival_rate,
        source_decision_sha256s=tuple(
            item.evidence_sha256 for item in prior_decisions
        ),
        source_outcome_evidence_ids=tuple(
            item.evidence_id for item in outcomes
        ),
    )


def _evidence_kind(decision: Phase20ForwardDecisionSeal) -> object:
    return _payload(decision).get("evidence_kind")


def _candidate_count(decision: Phase20ForwardDecisionSeal) -> int:
    candidates = _payload(decision).get("candidates")
    if not isinstance(candidates, list):
        raise CiboCapitalManagementError(
            "Phase20 causal history candidates must be list"
        )
    return len(candidates)


def _payload(decision: Phase20ForwardDecisionSeal) -> dict[str, object]:
    try:
        payload = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20 causal history decision payload is invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 causal history decision payload must be object"
        )
    return payload
