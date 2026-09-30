"""Preregistered GEN-C5 sequential compounding shadow controller.

Policy identity:
CIBO_GENC5_PROTECTED_FLOOR_GATED_SEQUENTIAL_COMPOUND_SHADOW_V1

This module implements the preregistered treatment/control mechanics frozen in
docs/research/CIBO-GEN-C5-SEQUENTIAL-COMPOUNDING-SHADOW-PREREGISTRATION-V1.md.

GEN-C5 V1 does not optimize size. It accepts the exact incremental amount
already present in causal GEN-C4 evidence and decides, in shadow only, whether
that proposal is eligible to be forwarded to downstream QORE Risk review.

No sizing, Risk, execution, DEMO-governed, LIVE, real-capital or merge authority
is granted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_core_compound_portfolio import (
    AccountCoreCompoundPortfolio,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
    SharedCapitalIntelligenceFact,
    SharedToCiboCapitalIntelligenceSnapshot,
    marginal_capital_utility_evidence_sha256,
)

GENC5_SHADOW_POLICY_ID = (
    "CIBO_GENC5_PROTECTED_FLOOR_GATED_SEQUENTIAL_COMPOUND_SHADOW_V1"
)
GENC5_SHADOW_POLICY_FROZEN_AT = datetime(
    2026,
    9,
    29,
    17,
    10,
    tzinfo=UTC,
)


class SequentialCompoundPosture(StrEnum):
    COMPOUND_PAUSED = "COMPOUND_PAUSED"
    DEFENSIVE = "DEFENSIVE"
    CAUTIOUS_COMPOUND = "CAUTIOUS_COMPOUND"
    NORMAL_COMPOUND = "NORMAL_COMPOUND"
    ACCELERATED_COMPOUND = "ACCELERATED_COMPOUND"
    SURVIVAL = "SURVIVAL"


class SequentialCompoundShadowAction(StrEnum):
    HOLD_CURRENT_STATE = "HOLD_CURRENT_STATE"
    REQUEST_DOWNSTREAM_RISK_REVIEW = "REQUEST_DOWNSTREAM_RISK_REVIEW"


_CANDIDATE_SOURCE_STATES = frozenset(
    {
        CompoundCapitalState.COMPOUNDABLE,
        CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
        CompoundCapitalState.RELEASED_COMPOUND_CAPITAL,
    }
)

_FORBIDDEN_V1_POSTURES = frozenset(
    {
        SequentialCompoundPosture.NORMAL_COMPOUND,
        SequentialCompoundPosture.ACCELERATED_COMPOUND,
        SequentialCompoundPosture.SURVIVAL,
    }
)


def genc5_shadow_policy_sha256() -> str:
    payload = {
        "policy_id": GENC5_SHADOW_POLICY_ID,
        "frozen_at": GENC5_SHADOW_POLICY_FROZEN_AT.isoformat(),
        "control": {
            "posture": SequentialCompoundPosture.COMPOUND_PAUSED.value,
            "action": SequentialCompoundShadowAction.HOLD_CURRENT_STATE.value,
            "requested_downstream_risk_review_usd": "0",
        },
        "candidate_capacity_states": tuple(
            sorted(item.value for item in _CANDIDATE_SOURCE_STATES)
        ),
        "treatment_gate": (
            "same-account AND post-freeze AND source-state-candidate "
            "AND source-amount>=GEN-C4-request "
            "AND GEN-C4-capacity==portfolio-candidate-capacity "
            "AND policy-protected-floor>0 "
            "AND pre-outcome GEN-C4 evidence"
        ),
        "treatment_amount": (
            "exact GEN-C4 requested_incremental_capital_usd; never resized"
        ),
        "v1_posture_ceiling": (
            "COMPOUND_PAUSED/DEFENSIVE/CAUTIOUS_COMPOUND only"
        ),
        "outcome_aware": False,
        "runtime_authority": False,
        "risk_authority": False,
        "execution_authority": False,
        "live_authority": False,
        "real_capital_authority": False,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def marginal_capital_evidence_sha256(
    evidence: MarginalCapitalUtilityEvidence,
) -> str:
    """Compatibility alias for the canonical GEN-C4 evidence digest."""

    return marginal_capital_utility_evidence_sha256(evidence)


def account_core_compound_portfolio_sha256(
    portfolio: AccountCoreCompoundPortfolio,
) -> str:
    if not isinstance(portfolio, AccountCoreCompoundPortfolio):
        raise CiboCompoundCapitalError(
            "GEN-C5 requires canonical account Core Compound Portfolio"
        )
    payload = {
        "account_identity": _account_payload(portfolio.account_identity),
        "active_lots": [
            {
                "lot_id": lot.lot_id,
                "amount_usd": str(lot.amount_usd),
                "state": lot.state.value,
                "generation": lot.generation,
                "origin_evidence_id": lot.origin_evidence_id,
                "origin_trader": lot.origin_trader.value,
                "origin_signal_fingerprint": (
                    lot.origin_signal_fingerprint
                ),
                "origin_position_id": lot.origin_position_id,
                "origin_deal_ids": list(lot.origin_deal_ids),
                "realized_at": lot.realized_at.isoformat(),
                "created_at": lot.created_at.isoformat(),
                "parent_lot_ids": list(lot.parent_lot_ids),
            }
            for lot in portfolio.compound_ledger.active_lots
        ],
        "floor_tranches": [
            {
                "tranche_id": tranche.tranche_id,
                "source_compound_lot_id": (
                    tranche.source_compound_lot_id
                ),
                "amount_usd": str(tranche.amount_usd),
                "protection_class": tranche.protection_class.value,
                "admitted_at": tranche.admitted_at.isoformat(),
                "policy_id": tranche.policy_id,
                "policy_sha256": tranche.policy_sha256,
                "broker_guarantee_evidence_id": (
                    tranche.broker_guarantee_evidence_id
                ),
                "broker_guarantee_sha256": (
                    tranche.broker_guarantee_sha256
                ),
            }
            for tranche in portfolio.protected_floor_ledger.tranches
        ],
        "admitted_realized_profit_usd": str(
            portfolio.admitted_realized_profit_usd
        ),
        "current_partition_usd": str(portfolio.current_partition_usd),
        "current_economic_value_usd": str(
            portfolio.current_economic_value_usd
        ),
        "policy_protected_floor_usd": str(
            portfolio.protected_floor_ledger.policy_protected_floor_usd
        ),
        "runtime_authority": portfolio.runtime_authority,
        "cross_account_transfer_authority": (
            portfolio.cross_account_transfer_authority
        ),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class Genc5SequentialCompoundingShadowDecision:
    policy_id: str
    policy_sha256: str
    policy_frozen_at: datetime
    decision_id: str
    decision_at: datetime
    account_provider_key: str
    account_ref: str
    source_lot_id: str
    source_lot_state: CompoundCapitalState
    source_lot_amount_usd: Decimal
    portfolio_sha256: str
    marginal_evidence_sha256: str
    policy_protected_floor_usd: Decimal
    candidate_compound_capacity_usd: Decimal
    control_posture: SequentialCompoundPosture
    control_action: SequentialCompoundShadowAction
    control_requested_risk_review_usd: Decimal
    treatment_posture: SequentialCompoundPosture
    treatment_action: SequentialCompoundShadowAction
    treatment_requested_risk_review_usd: Decimal
    blocker_codes: tuple[str, ...]
    treatment_differs_from_control: bool
    outcome_present_at_seal: bool = False
    runtime_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    live_authority: bool = False
    real_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.policy_id != GENC5_SHADOW_POLICY_ID:
            raise CiboCompoundCapitalError(
                "GEN-C5 shadow policy identity drift"
            )
        if self.policy_sha256 != genc5_shadow_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C5 shadow policy digest drift"
            )
        if self.policy_frozen_at != GENC5_SHADOW_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C5 shadow policy freeze drift"
            )
        if not self.decision_id or not self.account_provider_key:
            raise CiboCompoundCapitalError(
                "GEN-C5 shadow decision/account identity is required"
            )
        if not self.account_ref or not self.source_lot_id:
            raise CiboCompoundCapitalError(
                "GEN-C5 shadow account/source lot identity is required"
            )
        _aware(self.decision_at, "GEN-C5 decision_at")
        if self.decision_at < GENC5_SHADOW_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C5 cannot evaluate pre-freeze decision"
            )
        if type(self.source_lot_state) is not CompoundCapitalState:
            raise CiboCompoundCapitalError(
                "GEN-C5 source lot state is invalid"
            )
        for name in (
            "source_lot_amount_usd",
            "policy_protected_floor_usd",
            "candidate_compound_capacity_usd",
            "control_requested_risk_review_usd",
            "treatment_requested_risk_review_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C5 {name} must be finite non-negative Decimal"
                )
        if self.source_lot_amount_usd <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C5 source lot amount must be positive"
            )
        for name in ("portfolio_sha256", "marginal_evidence_sha256"):
            _sha(getattr(self, name), name)
        if self.control_posture is not SequentialCompoundPosture.COMPOUND_PAUSED:
            raise CiboCompoundCapitalError(
                "GEN-C5 V1 control posture must remain COMPOUND_PAUSED"
            )
        if (
            self.control_action
            is not SequentialCompoundShadowAction.HOLD_CURRENT_STATE
            or self.control_requested_risk_review_usd != 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 V1 control must hold with zero downstream request"
            )
        if self.treatment_posture in _FORBIDDEN_V1_POSTURES:
            raise CiboCompoundCapitalError(
                "GEN-C5 V1 emitted forbidden unvalidated posture"
            )
        if len(self.blocker_codes) != len(set(self.blocker_codes)):
            raise CiboCompoundCapitalError(
                "GEN-C5 blocker codes must be unique"
            )
        if any(not item for item in self.blocker_codes):
            raise CiboCompoundCapitalError(
                "GEN-C5 blocker code cannot be blank"
            )
        forwarded = (
            self.treatment_action
            is SequentialCompoundShadowAction.REQUEST_DOWNSTREAM_RISK_REVIEW
        )
        if forwarded:
            if self.treatment_posture is not (
                SequentialCompoundPosture.CAUTIOUS_COMPOUND
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C5 V1 forwarding requires CAUTIOUS_COMPOUND"
                )
            if self.treatment_requested_risk_review_usd <= 0:
                raise CiboCompoundCapitalError(
                    "GEN-C5 forwarded amount must be positive"
                )
            if self.blocker_codes:
                raise CiboCompoundCapitalError(
                    "GEN-C5 forwarded treatment cannot retain blockers"
                )
        else:
            if (
                self.treatment_action
                is not SequentialCompoundShadowAction.HOLD_CURRENT_STATE
                or self.treatment_requested_risk_review_usd != 0
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C5 blocked treatment must hold with zero request"
                )
        expected_difference = forwarded
        if self.treatment_differs_from_control != expected_difference:
            raise CiboCompoundCapitalError(
                "GEN-C5 treatment/control difference flag drift"
            )
        for name in (
            "outcome_present_at_seal",
            "runtime_authority",
            "risk_authority",
            "execution_authority",
            "live_authority",
            "real_capital_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C5 {name} must be bool"
                )
            if getattr(self, name):
                raise CiboCompoundCapitalError(
                    "GEN-C5 shadow decision cannot contain outcome/authority"
                )


def evaluate_genc5_sequential_compounding_shadow(
    *,
    portfolio: AccountCoreCompoundPortfolio,
    evidence: MarginalCapitalUtilityEvidence,
    source_lot_id: str,
    decision_id: str,
) -> Genc5SequentialCompoundingShadowDecision:
    """Evaluate preregistered GEN-C5 treatment/control strictly pre-outcome."""

    if not isinstance(portfolio, AccountCoreCompoundPortfolio):
        raise CiboCompoundCapitalError(
            "GEN-C5 requires canonical account Core Compound Portfolio"
        )
    if not isinstance(evidence, MarginalCapitalUtilityEvidence):
        raise CiboCompoundCapitalError(
            "GEN-C5 requires canonical GEN-C4 evidence"
        )
    if evidence.decision_at < GENC5_SHADOW_POLICY_FROZEN_AT:
        raise CiboCompoundCapitalError(
            "GEN-C5 cannot evaluate pre-freeze GEN-C4 evidence"
        )
    if evidence.account_identity != portfolio.account_identity:
        raise CiboCompoundCapitalError(
            "GEN-C5 portfolio/GEN-C4 account binding mismatch"
        )
    if evidence.outcome_present or evidence.utility_score_computed:
        raise CiboCompoundCapitalError(
            "GEN-C5 cannot consume outcome-aware/utility-scored evidence"
        )
    if not source_lot_id or not decision_id:
        raise CiboCompoundCapitalError(
            "GEN-C5 source lot and decision id are required"
        )

    source = portfolio.compound_ledger.lot(source_lot_id)
    candidate_capacity = (
        portfolio.compoundable_usd
        + portfolio.active_compound_capacity_usd
        + portfolio.released_compound_capital_usd
    )
    if evidence.current_compound_capacity_usd != candidate_capacity:
        raise CiboCompoundCapitalError(
            "GEN-C5 GEN-C4/portfolio compound capacity binding drift"
        )

    blockers: list[str] = []
    if source.state not in _CANDIDATE_SOURCE_STATES:
        blockers.append("SOURCE_STATE_NOT_CANDIDATE_COMPOUND")
    if source.amount_usd < evidence.requested_incremental_capital_usd:
        blockers.append("SOURCE_LOT_BELOW_REQUEST")
    policy_floor = (
        portfolio.protected_floor_ledger.policy_protected_floor_usd
    )
    if policy_floor <= 0:
        blockers.append("POLICY_PROTECTED_FLOOR_ABSENT")

    if blockers:
        posture = (
            SequentialCompoundPosture.DEFENSIVE
            if candidate_capacity > 0 and policy_floor <= 0
            else SequentialCompoundPosture.COMPOUND_PAUSED
        )
        treatment_action = (
            SequentialCompoundShadowAction.HOLD_CURRENT_STATE
        )
        treatment_amount = Decimal(0)
    else:
        posture = SequentialCompoundPosture.CAUTIOUS_COMPOUND
        treatment_action = (
            SequentialCompoundShadowAction.REQUEST_DOWNSTREAM_RISK_REVIEW
        )
        treatment_amount = evidence.requested_incremental_capital_usd

    return Genc5SequentialCompoundingShadowDecision(
        policy_id=GENC5_SHADOW_POLICY_ID,
        policy_sha256=genc5_shadow_policy_sha256(),
        policy_frozen_at=GENC5_SHADOW_POLICY_FROZEN_AT,
        decision_id=decision_id,
        decision_at=evidence.decision_at,
        account_provider_key=portfolio.account_identity.provider_key,
        account_ref=portfolio.account_identity.account_ref,
        source_lot_id=source.lot_id,
        source_lot_state=source.state,
        source_lot_amount_usd=source.amount_usd,
        portfolio_sha256=account_core_compound_portfolio_sha256(portfolio),
        marginal_evidence_sha256=marginal_capital_evidence_sha256(evidence),
        policy_protected_floor_usd=policy_floor,
        candidate_compound_capacity_usd=candidate_capacity,
        control_posture=SequentialCompoundPosture.COMPOUND_PAUSED,
        control_action=SequentialCompoundShadowAction.HOLD_CURRENT_STATE,
        control_requested_risk_review_usd=Decimal(0),
        treatment_posture=posture,
        treatment_action=treatment_action,
        treatment_requested_risk_review_usd=treatment_amount,
        blocker_codes=tuple(blockers),
        treatment_differs_from_control=not blockers,
        outcome_present_at_seal=False,
        runtime_authority=False,
        risk_authority=False,
        execution_authority=False,
        live_authority=False,
        real_capital_authority=False,
    )


def _shared_snapshot_payload(
    snapshot: SharedToCiboCapitalIntelligenceSnapshot,
) -> dict[str, object]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "decision_at": snapshot.decision_at.isoformat(),
        "snapshot_sha256": snapshot.snapshot_sha256,
        "facts": [_shared_fact_payload(item) for item in snapshot.facts],
        "read_only": snapshot.read_only,
        "sizing_authority": snapshot.sizing_authority,
        "capital_authority": snapshot.capital_authority,
        "risk_authority": snapshot.risk_authority,
        "execution_authority": snapshot.execution_authority,
    }


def _shared_fact_payload(
    fact: SharedCapitalIntelligenceFact,
) -> dict[str, object]:
    return {
        "fact_id": fact.fact_id,
        "kind": fact.kind.value,
        "normalized_value": str(fact.normalized_value),
        "value_semantics": fact.value_semantics,
        "observed_at": fact.observed_at.isoformat(),
        "valid_until": (
            None if fact.valid_until is None else fact.valid_until.isoformat()
        ),
        "producer_identity": fact.producer_identity,
        "producer_git_sha": fact.producer_git_sha,
        "evidence_sha256": fact.evidence_sha256,
        "calibration_artifact_sha256": fact.calibration_artifact_sha256,
        "calibrated": fact.calibrated,
        "fresh_oos_validated": fact.fresh_oos_validated,
        "temporal_stability_validated": (
            fact.temporal_stability_validated
        ),
        "economic_utility_validated": fact.economic_utility_validated,
        "eligible_for_capital_use": fact.eligible_for_capital_use,
        "read_only": fact.read_only,
    }


def _account_payload(identity: object) -> dict[str, object]:
    return {
        "provider_key": identity.provider_key,
        "account_ref": identity.account_ref,
        "environment": identity.environment.value,
        "provider_program": identity.provider_program,
    }


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C5 {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C5 {name} must be timezone-aware"
        )
