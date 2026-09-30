"""Forward identifiability audit for CE2I T13 Drawdown Reserve.

T13 must not invent a reserve formula from burned history. This audit asks a
more basic causal question first: does the fresh forward stream contain enough
pre-decision states where realized settlement drawdown/loss-cluster coexists
with current opportunities and scarce stop-risk headroom?

The audit reconstructs history strictly from evidence already known before each
decision. It identifies population only; it never chooses a reserve amount,
tunes thresholds, grants sizing authority, or promotes T13.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_causal_history_state import (
    build_phase20_causal_history_state,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)


@dataclass(frozen=True, slots=True)
class Phase20T13ReservePopulationAudit:
    usable_decision_epochs: int
    candidate_epochs: int
    candidate_instances: int
    settled_history_epochs: int
    loss_cluster_epochs: int
    settlement_drawdown_epochs: int
    reserve_pressure_epochs: int
    scarce_risk_headroom_epochs: int
    pressure_and_scarcity_epochs: int
    maximum_loss_cluster: int
    maximum_settlement_drawdown_usd: Decimal
    minimum_decision_epochs: int
    decision_threshold_met: bool
    source_decision_sha256s: tuple[str, ...]
    reserve_policy_identified: bool
    oos_utility_demonstrated: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "usable_decision_epochs",
            "candidate_epochs",
            "candidate_instances",
            "settled_history_epochs",
            "loss_cluster_epochs",
            "settlement_drawdown_epochs",
            "reserve_pressure_epochs",
            "scarce_risk_headroom_epochs",
            "pressure_and_scarcity_epochs",
            "maximum_loss_cluster",
            "minimum_decision_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 {name} must be non-negative int"
                )
        if self.minimum_decision_epochs <= 0:
            raise CiboCapitalManagementError(
                "Phase20 T13 minimum decision epochs must be positive"
            )
        if (
            not isinstance(self.maximum_settlement_drawdown_usd, Decimal)
            or not self.maximum_settlement_drawdown_usd.is_finite()
            or self.maximum_settlement_drawdown_usd < 0
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 maximum settlement drawdown invalid"
            )
        if self.candidate_epochs > self.usable_decision_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T13 candidate epochs exceed usable decisions"
            )
        if self.settled_history_epochs > self.usable_decision_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T13 settled-history epochs exceed usable decisions"
            )
        if self.loss_cluster_epochs > self.settled_history_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T13 loss-cluster epochs exceed settled history"
            )
        if self.settlement_drawdown_epochs > self.settled_history_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T13 drawdown epochs exceed settled history"
            )
        if self.reserve_pressure_epochs > self.candidate_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T13 reserve-pressure epochs exceed candidate epochs"
            )
        if self.scarce_risk_headroom_epochs > self.candidate_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T13 scarcity epochs exceed candidate epochs"
            )
        if self.pressure_and_scarcity_epochs > self.reserve_pressure_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T13 pressure/scarcity intersection invalid"
            )
        if type(self.decision_threshold_met) is not bool:
            raise CiboCapitalManagementError(
                "Phase20 T13 decision_threshold_met must be bool"
            )
        if self.reserve_policy_identified or self.oos_utility_demonstrated:
            raise CiboCapitalManagementError(
                "Phase20 T13 population audit cannot promote reserve policy"
            )
        if len(self.source_decision_sha256s) != len(
            set(self.source_decision_sha256s)
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 decision sources must be unique"
            )


def assess_phase20_t13_reserve_population(
    evidence_book: VersionedPhase20ForwardEvidenceBook,
) -> Phase20T13ReservePopulationAudit:
    """Measure fresh causal T13 reserve-pressure identifiability."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T13 requires canonical forward evidence book"
        )

    usable = tuple(
        item
        for item in sorted(
            evidence_book.decisions,
            key=lambda row: (row.decision_at, row.evidence_sha256),
        )
        if _usable(item)
    )
    candidate_epochs = 0
    candidate_instances = 0
    settled_history_epochs = 0
    loss_cluster_epochs = 0
    drawdown_epochs = 0
    reserve_pressure_epochs = 0
    scarce_epochs = 0
    pressure_and_scarcity = 0
    maximum_loss_cluster = 0
    maximum_drawdown = Decimal(0)

    for decision in usable:
        payload = _payload(decision)
        candidates = payload.get("candidates")
        if not isinstance(candidates, list):
            raise CiboCapitalManagementError(
                "Phase20 T13 candidates must be list"
            )
        candidate_count = len(candidates)
        candidate_instances += candidate_count
        if candidate_count > 0:
            candidate_epochs += 1

        history = build_phase20_causal_history_state(
            evidence_book=evidence_book,
            decision=decision,
        )
        if history.prior_settled_outcomes > 0:
            settled_history_epochs += 1
        if history.consecutive_settled_losses > 0:
            loss_cluster_epochs += 1
        if history.settlement_cash_drawdown_usd > 0:
            drawdown_epochs += 1
        maximum_loss_cluster = max(
            maximum_loss_cluster,
            history.consecutive_settled_losses,
        )
        maximum_drawdown = max(
            maximum_drawdown,
            history.max_settlement_cash_drawdown_usd,
        )

        pressure = candidate_count > 0 and (
            history.consecutive_settled_losses > 0
            or history.settlement_cash_drawdown_usd > 0
        )
        if pressure:
            reserve_pressure_epochs += 1

        hard_headroom = _decimal_field(
            payload,
            "hard_risk_headroom_usd",
        )
        candidate_risk = sum(
            (_candidate_stop_risk(row) for row in candidates),
            Decimal(0),
        )
        scarce = candidate_count > 0 and candidate_risk > hard_headroom
        if scarce:
            scarce_epochs += 1
        if pressure and scarce:
            pressure_and_scarcity += 1

    minimum = FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_decision_epochs
    threshold_met = len(usable) >= minimum

    blockers: list[str] = []
    if not threshold_met:
        blockers.append(
            f"PHASE20_MINIMUM_DECISION_EPOCHS_NOT_MET:{len(usable)}/{minimum}"
        )
    if settled_history_epochs == 0:
        blockers.append("NO_FORWARD_SETTLED_HISTORY_FOR_T13")
    if reserve_pressure_epochs == 0:
        blockers.append("NO_FORWARD_DRAWDOWN_RESERVE_PRESSURE_EPOCHS")
    if pressure_and_scarcity == 0:
        blockers.append("NO_T13_PRESSURE_AND_SCARCE_CAPACITY_INTERSECTION")
    blockers.extend(
        (
            "T13_RESERVE_POLICY_NOT_IDENTIFIED",
            "FRESH_OOS_T13_RESERVE_UTILITY_REQUIRED",
        )
    )

    return Phase20T13ReservePopulationAudit(
        usable_decision_epochs=len(usable),
        candidate_epochs=candidate_epochs,
        candidate_instances=candidate_instances,
        settled_history_epochs=settled_history_epochs,
        loss_cluster_epochs=loss_cluster_epochs,
        settlement_drawdown_epochs=drawdown_epochs,
        reserve_pressure_epochs=reserve_pressure_epochs,
        scarce_risk_headroom_epochs=scarce_epochs,
        pressure_and_scarcity_epochs=pressure_and_scarcity,
        maximum_loss_cluster=maximum_loss_cluster,
        maximum_settlement_drawdown_usd=maximum_drawdown,
        minimum_decision_epochs=minimum,
        decision_threshold_met=threshold_met,
        source_decision_sha256s=tuple(
            item.evidence_sha256 for item in usable
        ),
        reserve_policy_identified=False,
        oos_utility_demonstrated=False,
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


def _payload(
    decision: Phase20ForwardDecisionSeal,
) -> dict[str, object]:
    try:
        payload = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20 T13 decision payload is invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 T13 decision payload must be object"
        )
    return payload


def _decimal_field(payload: dict[str, object], name: str) -> Decimal:
    value = payload.get(name)
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            f"Phase20 T13 {name} must be Decimal-compatible"
        ) from error
    if not result.is_finite() or result < 0:
        raise CiboCapitalManagementError(
            f"Phase20 T13 {name} must be finite non-negative"
        )
    return result


def _candidate_stop_risk(row: object) -> Decimal:
    if not isinstance(row, dict):
        raise CiboCapitalManagementError(
            "Phase20 T13 candidate row must be object"
        )
    candidate = row.get("candidate")
    if not isinstance(candidate, dict):
        raise CiboCapitalManagementError(
            "Phase20 T13 candidate payload missing"
        )
    try:
        result = Decimal(str(candidate["stop_risk_usd"]))
    except (KeyError, InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            "Phase20 T13 candidate stop risk invalid"
        ) from error
    if not result.is_finite() or result < 0:
        raise CiboCapitalManagementError(
            "Phase20 T13 candidate stop risk must be finite non-negative"
        )
    return result
