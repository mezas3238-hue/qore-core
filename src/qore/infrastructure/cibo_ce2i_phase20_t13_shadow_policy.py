"""Preregistered causal shadow policy for CE2I T13 Drawdown Reserve.

The policy is structural rather than outcome-fitted. After its frozen effective
time it may recommend, in shadow only, preserving risk capacity equal to one
currently observable provider-minimum executable seed when all of the following
were known strictly before the decision:

- at least one prior settled outcome exists;
- settlement drawdown or a consecutive-loss cluster is active;
- observed candidate-arrival density is positive; and
- at least one current candidate has provider-normalized minimum-seed economics.

The recommendation never changes CIBO sizing, QORE Risk or broker execution.
It is a preregistered candidate awaiting fresh OOS ablation, not an identified
or certified reserve policy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
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
from qore.infrastructure.cibo_ce2i_phase20_t08_forward_population import (
    Phase20ForwardCandidateFacts,
    iter_phase20_forward_candidate_facts,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    normalize_provider_economics,
)

T13_SHADOW_POLICY_ID = "CIBO_T13_ONE_MINIMUM_SEED_RESERVE_SHADOW_V1"
T13_SHADOW_POLICY_FROZEN_AT = datetime(2026, 9, 29, 3, 30, tzinfo=UTC)


def t13_shadow_policy_sha256() -> str:
    payload = {
        "policy_id": T13_SHADOW_POLICY_ID,
        "frozen_at": T13_SHADOW_POLICY_FROZEN_AT.isoformat(),
        "pressure_rule": (
            "prior_settled_outcomes>0 AND "
            "(settlement_drawdown_usd>0 OR consecutive_settled_losses>0)"
        ),
        "opportunity_rule": "observed_candidate_arrivals_per_day>0",
        "reserve_unit": "minimum_provider_executable_seed_stop_risk_usd",
        "reserve_amount": "min(hard_risk_headroom_usd,reserve_unit)",
        "runtime_authority": False,
        "outcome_aware": False,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class Phase20T13ShadowRecommendation:
    policy_id: str
    policy_sha256: str
    decision_epoch_id: str
    decision_evidence_sha256: str
    decision_at: datetime
    causal_pressure_active: bool
    arrival_evidence_available: bool
    reserve_triggered: bool
    reserved_risk_usd: Decimal
    minimum_seed_risk_usd: Decimal | None
    hard_risk_headroom_usd: Decimal
    full_seed_preserved: bool
    source_decision_sha256s: tuple[str, ...]
    source_outcome_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.policy_id != T13_SHADOW_POLICY_ID:
            raise CiboCapitalManagementError(
                "Phase20 T13 recommendation policy identity drift"
            )
        if self.policy_sha256 != t13_shadow_policy_sha256():
            raise CiboCapitalManagementError(
                "Phase20 T13 recommendation policy digest drift"
            )
        if not self.decision_epoch_id:
            raise CiboCapitalManagementError(
                "Phase20 T13 recommendation epoch id is required"
            )
        if (
            not self.decision_evidence_sha256.startswith("sha256:")
            or len(self.decision_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 recommendation decision SHA is invalid"
            )
        if (
            self.decision_at.tzinfo is None
            or self.decision_at.utcoffset() is None
            or self.decision_at < T13_SHADOW_POLICY_FROZEN_AT
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 recommendation decision time is invalid"
            )
        for name in (
            "causal_pressure_active",
            "arrival_evidence_available",
            "reserve_triggered",
            "full_seed_preserved",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 T13 recommendation {name} must be bool"
                )
        for name in (
            "reserved_risk_usd",
            "hard_risk_headroom_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 recommendation {name} is invalid"
                )
        if self.minimum_seed_risk_usd is not None and (
            not isinstance(self.minimum_seed_risk_usd, Decimal)
            or not self.minimum_seed_risk_usd.is_finite()
            or self.minimum_seed_risk_usd <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 recommendation minimum seed is invalid"
            )
        if self.reserve_triggered:
            if self.minimum_seed_risk_usd is None:
                raise CiboCapitalManagementError(
                    "Phase20 T13 triggered reserve requires minimum seed"
                )
            expected = min(
                self.hard_risk_headroom_usd,
                self.minimum_seed_risk_usd,
            )
            if self.reserved_risk_usd != expected or expected <= 0:
                raise CiboCapitalManagementError(
                    "Phase20 T13 triggered reserve amount drift"
                )
            if self.full_seed_preserved != (
                self.hard_risk_headroom_usd
                >= self.minimum_seed_risk_usd
            ):
                raise CiboCapitalManagementError(
                    "Phase20 T13 full-seed flag drift"
                )
        elif self.reserved_risk_usd != 0 or self.full_seed_preserved:
            raise CiboCapitalManagementError(
                "Phase20 T13 inactive reserve must preserve zero risk"
            )
        if len(self.source_decision_sha256s) != len(
            set(self.source_decision_sha256s)
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 recommendation decision sources must be unique"
            )
        if len(self.source_outcome_evidence_ids) != len(
            set(self.source_outcome_evidence_ids)
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 recommendation outcome sources must be unique"
            )


def evaluate_phase20_t13_shadow_decision(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    decision: Phase20ForwardDecisionSeal,
) -> Phase20T13ShadowRecommendation:
    """Produce one causal preregistered T13 shadow recommendation."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T13 recommendation requires canonical evidence book"
        )
    if not isinstance(decision, Phase20ForwardDecisionSeal):
        raise CiboCapitalManagementError(
            "Phase20 T13 recommendation requires canonical decision"
        )
    if evidence_book.decision_for_sha(decision.evidence_sha256) != decision:
        raise CiboCapitalManagementError(
            "Phase20 T13 recommendation decision must belong to evidence book"
        )
    if decision.decision_at < T13_SHADOW_POLICY_FROZEN_AT:
        raise CiboCapitalManagementError(
            "Phase20 T13 recommendation cannot use pre-freeze decision"
        )
    if not _usable(decision):
        raise CiboCapitalManagementError(
            "Phase20 T13 recommendation requires usable forward decision"
        )

    facts = tuple(
        fact
        for fact in iter_phase20_forward_candidate_facts(
            evidence_book=evidence_book
        )
        if fact.decision_sha256 == decision.evidence_sha256
    )
    history = build_phase20_causal_history_state(
        evidence_book=evidence_book,
        decision=decision,
    )
    pressure = (
        history.prior_settled_outcomes > 0
        and (
            history.settlement_cash_drawdown_usd > 0
            or history.consecutive_settled_losses > 0
        )
    )
    arrival_ready = (
        history.observed_candidate_arrivals_per_day is not None
        and history.observed_candidate_arrivals_per_day > 0
    )
    minimum_seed = (
        None
        if not facts
        else min(_minimum_seed_risk(fact) for fact in facts)
    )
    hard_headroom = _hard_headroom(decision)
    triggered = (
        minimum_seed is not None
        and pressure
        and arrival_ready
        and hard_headroom > 0
    )
    reserved = (
        Decimal(0)
        if not triggered or minimum_seed is None
        else min(hard_headroom, minimum_seed)
    )
    full_seed = bool(
        triggered
        and minimum_seed is not None
        and hard_headroom >= minimum_seed
    )

    return Phase20T13ShadowRecommendation(
        policy_id=T13_SHADOW_POLICY_ID,
        policy_sha256=t13_shadow_policy_sha256(),
        decision_epoch_id=decision.decision_epoch_id,
        decision_evidence_sha256=decision.evidence_sha256,
        decision_at=decision.decision_at,
        causal_pressure_active=pressure,
        arrival_evidence_available=arrival_ready,
        reserve_triggered=triggered,
        reserved_risk_usd=reserved,
        minimum_seed_risk_usd=minimum_seed,
        hard_risk_headroom_usd=hard_headroom,
        full_seed_preserved=full_seed,
        source_decision_sha256s=history.source_decision_sha256s,
        source_outcome_evidence_ids=history.source_outcome_evidence_ids,
    )


@dataclass(frozen=True, slots=True)
class Phase20T13ShadowPolicyAudit:
    policy_id: str
    policy_sha256: str
    policy_frozen_at: datetime
    post_freeze_decision_epochs: int
    candidate_epochs: int
    causal_pressure_epochs: int
    arrival_evidence_epochs: int
    reserve_trigger_epochs: int
    full_seed_reserve_epochs: int
    partial_headroom_reserve_epochs: int
    total_shadow_reserved_risk_usd: Decimal
    maximum_shadow_reserved_risk_usd: Decimal
    shadow_policy_preregistered: bool
    reserve_policy_empirically_identified: bool
    fresh_oos_utility_demonstrated: bool
    runtime_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.policy_id != T13_SHADOW_POLICY_ID:
            raise CiboCapitalManagementError(
                "Phase20 T13 shadow policy identity drift"
            )
        if self.policy_sha256 != t13_shadow_policy_sha256():
            raise CiboCapitalManagementError(
                "Phase20 T13 shadow policy digest drift"
            )
        if self.policy_frozen_at != T13_SHADOW_POLICY_FROZEN_AT:
            raise CiboCapitalManagementError(
                "Phase20 T13 shadow policy freeze drift"
            )
        for name in (
            "post_freeze_decision_epochs",
            "candidate_epochs",
            "causal_pressure_epochs",
            "arrival_evidence_epochs",
            "reserve_trigger_epochs",
            "full_seed_reserve_epochs",
            "partial_headroom_reserve_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 shadow {name} must be non-negative int"
                )
        if self.candidate_epochs > self.post_freeze_decision_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T13 shadow candidate epochs exceed decisions"
            )
        if self.reserve_trigger_epochs > self.candidate_epochs:
            raise CiboCapitalManagementError(
                "Phase20 T13 shadow trigger epochs exceed candidates"
            )
        if (
            self.full_seed_reserve_epochs
            + self.partial_headroom_reserve_epochs
            != self.reserve_trigger_epochs
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 shadow reserve accounting drift"
            )
        for name in (
            "total_shadow_reserved_risk_usd",
            "maximum_shadow_reserved_risk_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 shadow {name} must be finite non-negative"
                )
        if type(self.shadow_policy_preregistered) is not bool:
            raise CiboCapitalManagementError(
                "Phase20 T13 shadow preregistration flag must be bool"
            )
        if not self.shadow_policy_preregistered:
            raise CiboCapitalManagementError(
                "Phase20 T13 shadow policy must remain preregistered"
            )
        if (
            self.reserve_policy_empirically_identified
            or self.fresh_oos_utility_demonstrated
            or self.runtime_authority
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 shadow audit cannot promote runtime reserve policy"
            )


def assess_phase20_t13_shadow_policy(
    evidence_book: VersionedPhase20ForwardEvidenceBook,
) -> Phase20T13ShadowPolicyAudit:
    """Evaluate the frozen causal rule only on post-freeze forward decisions."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T13 shadow requires canonical forward evidence book"
        )

    facts_by_decision: dict[
        str,
        tuple[Phase20ForwardCandidateFacts, ...],
    ] = {}
    for fact in iter_phase20_forward_candidate_facts(
        evidence_book=evidence_book
    ):
        facts_by_decision.setdefault(fact.decision_sha256, ())
        facts_by_decision[fact.decision_sha256] += (fact,)

    decisions = tuple(
        item
        for item in sorted(
            evidence_book.decisions,
            key=lambda row: (row.decision_at, row.evidence_sha256),
        )
        if (
            item.decision_at >= T13_SHADOW_POLICY_FROZEN_AT
            and _usable(item)
        )
    )

    candidate_epochs = 0
    pressure_epochs = 0
    arrival_epochs = 0
    trigger_epochs = 0
    full_seed_epochs = 0
    partial_epochs = 0
    reserves: list[Decimal] = []

    for decision in decisions:
        facts = facts_by_decision.get(decision.evidence_sha256, ())
        if not facts:
            continue
        candidate_epochs += 1
        history = build_phase20_causal_history_state(
            evidence_book=evidence_book,
            decision=decision,
        )
        pressure = (
            history.prior_settled_outcomes > 0
            and (
                history.settlement_cash_drawdown_usd > 0
                or history.consecutive_settled_losses > 0
            )
        )
        if pressure:
            pressure_epochs += 1
        arrival_ready = (
            history.observed_candidate_arrivals_per_day is not None
            and history.observed_candidate_arrivals_per_day > 0
        )
        if arrival_ready:
            arrival_epochs += 1
        if not pressure or not arrival_ready:
            continue

        minimum_seed = min(_minimum_seed_risk(fact) for fact in facts)
        hard_headroom = _hard_headroom(decision)
        reserve = min(hard_headroom, minimum_seed)
        if reserve <= 0:
            continue
        trigger_epochs += 1
        reserves.append(reserve)
        if hard_headroom >= minimum_seed:
            full_seed_epochs += 1
        else:
            partial_epochs += 1

    blockers: list[str] = []
    if not decisions:
        blockers.append("NO_POST_FREEZE_T13_SHADOW_DECISIONS")
    if candidate_epochs == 0:
        blockers.append("NO_POST_FREEZE_T13_SHADOW_CANDIDATE_EPOCHS")
    if pressure_epochs == 0:
        blockers.append("NO_POST_FREEZE_T13_CAUSAL_PRESSURE_EPOCHS")
    if arrival_epochs == 0:
        blockers.append("NO_POST_FREEZE_T13_ARRIVAL_EVIDENCE_EPOCHS")
    if trigger_epochs == 0:
        blockers.append("NO_POST_FREEZE_T13_RESERVE_TRIGGER_EPOCHS")
    blockers.extend(
        (
            "T13_SHADOW_POLICY_NOT_EMPIRICALLY_IDENTIFIED",
            "FRESH_OOS_T13_RESERVE_UTILITY_REQUIRED",
            "T13_SHADOW_POLICY_HAS_NO_RUNTIME_AUTHORITY",
        )
    )

    return Phase20T13ShadowPolicyAudit(
        policy_id=T13_SHADOW_POLICY_ID,
        policy_sha256=t13_shadow_policy_sha256(),
        policy_frozen_at=T13_SHADOW_POLICY_FROZEN_AT,
        post_freeze_decision_epochs=len(decisions),
        candidate_epochs=candidate_epochs,
        causal_pressure_epochs=pressure_epochs,
        arrival_evidence_epochs=arrival_epochs,
        reserve_trigger_epochs=trigger_epochs,
        full_seed_reserve_epochs=full_seed_epochs,
        partial_headroom_reserve_epochs=partial_epochs,
        total_shadow_reserved_risk_usd=sum(reserves, Decimal(0)),
        maximum_shadow_reserved_risk_usd=max(
            reserves,
            default=Decimal(0),
        ),
        shadow_policy_preregistered=True,
        reserve_policy_empirically_identified=False,
        fresh_oos_utility_demonstrated=False,
        runtime_authority=False,
        blockers=tuple(blockers),
    )


def _minimum_seed_risk(fact: Phase20ForwardCandidateFacts) -> Decimal:
    normalized = normalize_provider_economics(
        opportunity=fact.opportunity,
        observation=fact.provider_observation,
    )
    if normalized.minimum_stop_risk_usd <= 0:
        raise CiboCapitalManagementError(
            "Phase20 T13 shadow minimum seed risk must be positive"
        )
    return normalized.minimum_stop_risk_usd


def _hard_headroom(decision: Phase20ForwardDecisionSeal) -> Decimal:
    payload = _payload(decision)
    try:
        result = Decimal(str(payload["hard_risk_headroom_usd"]))
    except (KeyError, InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            "Phase20 T13 shadow hard risk headroom invalid"
        ) from error
    if not result.is_finite() or result < 0:
        raise CiboCapitalManagementError(
            "Phase20 T13 shadow hard risk headroom must be finite non-negative"
        )
    return result


def _usable(decision: Phase20ForwardDecisionSeal) -> bool:
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
            "Phase20 T13 shadow decision payload invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 T13 shadow decision payload must be object"
        )
    return payload
