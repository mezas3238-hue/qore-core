"""Preregistered GEN-C7 profit-preservation / giveback shadow policy.

Policy identity:
CIBO_GENC7_PROFIT_PRESERVATION_GIVEBACK_SHADOW_V1

GEN-C7 V1 is research-only. It evaluates an already evidenced capital-state
snapshot and an already evidenced proposal. It never invents proposal amounts,
never mutates the compound ledger or protected floor, and carries no sizing,
Risk, Execution, DEMO-governed, LIVE or real-capital authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

GENC7_POLICY_ID = (
    "CIBO_GENC7_PROFIT_PRESERVATION_GIVEBACK_SHADOW_V1"
)
GENC7_POLICY_FROZEN_AT = datetime(2026, 9, 29, 23, 30, tzinfo=UTC)


class Genc7Action(StrEnum):
    HOLD_CURRENT_CAPITAL_STATE = "HOLD_CURRENT_CAPITAL_STATE"
    PROTECT = "PROTECT"
    HARVEST_TO_STRATEGIC_RESERVE = "HARVEST_TO_STRATEGIC_RESERVE"
    RESERVE_OPPORTUNITY_CAPACITY = "RESERVE_OPPORTUNITY_CAPACITY"
    COMPOUND = "COMPOUND"


class Genc7SourceBucket(StrEnum):
    REALIZED_UNPROTECTED_PROFIT = "REALIZED_UNPROTECTED_PROFIT"
    COMPOUNDABLE_OR_RELEASED_CAPACITY = (
        "COMPOUNDABLE_OR_RELEASED_CAPACITY"
    )


_ACTION_SOURCE = {
    Genc7Action.PROTECT: Genc7SourceBucket.REALIZED_UNPROTECTED_PROFIT,
    Genc7Action.HARVEST_TO_STRATEGIC_RESERVE: (
        Genc7SourceBucket.REALIZED_UNPROTECTED_PROFIT
    ),
    Genc7Action.RESERVE_OPPORTUNITY_CAPACITY: (
        Genc7SourceBucket.COMPOUNDABLE_OR_RELEASED_CAPACITY
    ),
    Genc7Action.COMPOUND: (
        Genc7SourceBucket.COMPOUNDABLE_OR_RELEASED_CAPACITY
    ),
}


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C7 {name} must be timezone-aware"
        )


def _nonnegative(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C7 {name} must be finite non-negative Decimal"
        )


def _positive(value: Decimal, name: str) -> None:
    _nonnegative(value, name)
    if value <= 0:
        raise CiboCompoundCapitalError(
            f"GEN-C7 {name} must be positive"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C7 {name} must be canonical SHA-256"
        )


def _identity_payload(
    identity: CiboAccountCapitalIdentity,
) -> dict[str, object]:
    return {
        "provider_key": identity.provider_key,
        "account_ref": identity.account_ref,
        "environment": identity.environment.value,
        "provider_program": identity.provider_program,
    }


@dataclass(frozen=True, slots=True)
class Genc7CapitalStateEvidence:
    """Pre-decision realized-capital state; floating PnL is forbidden."""

    evidence_id: str
    decision_at: datetime
    account_identity: CiboAccountCapitalIdentity
    current_realized_capital_usd: Decimal
    current_realized_profit_usd: Decimal
    peak_realized_profit_usd: Decimal
    current_base_capital_usd: Decimal
    peak_base_capital_usd: Decimal
    current_compound_capital_usd: Decimal
    peak_compound_capital_usd: Decimal
    protected_profit_usd: Decimal
    protected_floor_usd: Decimal
    previous_protected_floor_usd: Decimal
    strategic_reserve_usd: Decimal
    opportunity_reserve_usd: Decimal
    compoundable_usd: Decimal
    released_compound_capital_usd: Decimal
    source_evidence_sha256: str
    realized_only: bool = True
    floating_pnl_included: bool = False
    future_outcome_present: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise CiboCompoundCapitalError(
                "GEN-C7 state evidence_id is required"
            )
        _aware(self.decision_at, "state decision_at")
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 state account identity is invalid"
            )
        for name in (
            "current_realized_capital_usd",
            "current_realized_profit_usd",
            "peak_realized_profit_usd",
            "current_base_capital_usd",
            "peak_base_capital_usd",
            "current_compound_capital_usd",
            "peak_compound_capital_usd",
            "protected_profit_usd",
            "protected_floor_usd",
            "previous_protected_floor_usd",
            "strategic_reserve_usd",
            "opportunity_reserve_usd",
            "compoundable_usd",
            "released_compound_capital_usd",
        ):
            _nonnegative(getattr(self, name), name)
        if self.current_realized_capital_usd <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C7 realized capital must be positive"
            )
        if self.peak_realized_profit_usd < self.current_realized_profit_usd:
            raise CiboCompoundCapitalError(
                "GEN-C7 realized-profit peak cannot be below current"
            )
        if self.peak_base_capital_usd < self.current_base_capital_usd:
            raise CiboCompoundCapitalError(
                "GEN-C7 base-capital peak cannot be below current"
            )
        if self.peak_compound_capital_usd < self.current_compound_capital_usd:
            raise CiboCompoundCapitalError(
                "GEN-C7 compound-capital peak cannot be below current"
            )
        if self.protected_profit_usd > self.current_realized_profit_usd:
            raise CiboCompoundCapitalError(
                "GEN-C7 protected profit cannot exceed realized profit"
            )
        if self.protected_floor_usd < self.previous_protected_floor_usd:
            raise CiboCompoundCapitalError(
                "GEN-C7 protected floor cannot ratchet downward"
            )
        _sha(self.source_evidence_sha256, "state source_evidence_sha256")
        for name in (
            "realized_only",
            "floating_pnl_included",
            "future_outcome_present",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C7 state {name} must be bool"
                )
        if (
            not self.realized_only
            or self.floating_pnl_included
            or self.future_outcome_present
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 state must be realized-only pre-outcome research evidence"
            )

    @property
    def realized_unprotected_profit_usd(self) -> Decimal:
        return self.current_realized_profit_usd - self.protected_profit_usd

    @property
    def compound_candidate_capacity_usd(self) -> Decimal:
        return self.compoundable_usd + self.released_compound_capital_usd

    @property
    def giveback_amount_usd(self) -> Decimal:
        return self.peak_realized_profit_usd - self.current_realized_profit_usd

    @property
    def profit_retention_ratio(self) -> Decimal:
        if self.peak_realized_profit_usd == 0:
            return Decimal("1")
        return self.current_realized_profit_usd / self.peak_realized_profit_usd

    @property
    def base_drawdown_usd(self) -> Decimal:
        return self.peak_base_capital_usd - self.current_base_capital_usd

    @property
    def compound_drawdown_usd(self) -> Decimal:
        return self.peak_compound_capital_usd - self.current_compound_capital_usd

    @property
    def floor_growth_rate(self) -> Decimal | None:
        if self.previous_protected_floor_usd == 0:
            return None
        return (
            self.protected_floor_usd - self.previous_protected_floor_usd
        ) / self.previous_protected_floor_usd

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["decision_at"] = self.decision_at.isoformat()
        payload["account_identity"] = _identity_payload(self.account_identity)
        for key, value in tuple(payload.items()):
            if isinstance(value, Decimal):
                payload[key] = str(value)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Genc7PreservationProposalEvidence:
    """One preregistered proposal whose amount was fixed before outcome."""

    proposal_id: str
    decision_at: datetime
    account_identity: CiboAccountCapitalIdentity
    action: Genc7Action
    source_bucket: Genc7SourceBucket
    amount_usd: Decimal
    evidence_sha256: str
    rationale_code: str
    evaluation_horizon_minutes: int
    calibrated: bool
    capital_eligible: bool
    future_outcome_present: bool = False
    house_money_bias: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.proposal_id or not self.rationale_code:
            raise CiboCompoundCapitalError(
                "GEN-C7 proposal identity/rationale is required"
            )
        _aware(self.decision_at, "proposal decision_at")
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 proposal account identity is invalid"
            )
        if self.action is Genc7Action.HOLD_CURRENT_CAPITAL_STATE:
            raise CiboCompoundCapitalError(
                "GEN-C7 proposal cannot masquerade control HOLD as treatment"
            )
        expected_source = _ACTION_SOURCE.get(self.action)
        if expected_source is not self.source_bucket:
            raise CiboCompoundCapitalError(
                "GEN-C7 proposal action/source bucket mismatch"
            )
        _positive(self.amount_usd, "proposal amount_usd")
        if (
            not isinstance(self.evaluation_horizon_minutes, int)
            or isinstance(self.evaluation_horizon_minutes, bool)
            or self.evaluation_horizon_minutes <= 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 proposal evaluation horizon must be positive int"
            )
        _sha(self.evidence_sha256, "proposal evidence_sha256")
        for name in (
            "calibrated",
            "capital_eligible",
            "future_outcome_present",
            "house_money_bias",
            "sizing_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C7 proposal {name} must be bool"
                )
        if (
            self.future_outcome_present
            or self.house_money_bias
            or self.sizing_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 proposal contains forbidden outcome/bias/authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["decision_at"] = self.decision_at.isoformat()
        payload["account_identity"] = _identity_payload(self.account_identity)
        payload["action"] = self.action.value
        payload["source_bucket"] = self.source_bucket.value
        payload["amount_usd"] = str(self.amount_usd)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Genc7ProfitPreservationShadowDecision:
    policy_id: str
    policy_sha256: str
    policy_frozen_at: datetime
    decision_id: str
    decision_at: datetime
    account_provider_key: str
    account_ref: str
    state_evidence_sha256: str
    proposal_evidence_sha256: str
    proposal_action: Genc7Action
    proposal_source_bucket: Genc7SourceBucket
    proposal_amount_usd: Decimal
    evaluation_horizon_minutes: int
    initial_realized_capital_usd: Decimal
    initial_realized_profit_usd: Decimal
    initial_protected_floor_usd: Decimal
    initial_base_capital_usd: Decimal
    initial_compound_capital_usd: Decimal
    control_action: Genc7Action
    control_amount_usd: Decimal
    treatment_action: Genc7Action
    treatment_amount_usd: Decimal
    blocker_codes: tuple[str, ...]
    giveback_amount_usd: Decimal
    profit_retention_ratio: Decimal
    floor_growth_rate: Decimal | None
    base_drawdown_usd: Decimal
    compound_drawdown_usd: Decimal
    treatment_differs_from_control: bool
    outcome_present_at_seal: bool = False
    runtime_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    live_authority: bool = False
    real_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.policy_id != GENC7_POLICY_ID:
            raise CiboCompoundCapitalError(
                "GEN-C7 policy identity drift"
            )
        if self.policy_sha256 != genc7_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C7 policy digest drift"
            )
        if self.policy_frozen_at != GENC7_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C7 policy freeze drift"
            )
        if (
            not self.decision_id
            or not self.account_provider_key
            or not self.account_ref
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 decision/account identity is required"
            )
        _aware(self.decision_at, "decision_at")
        # The policy freeze is a specification lock, not a lower bound on
        # causal market timestamps. Historical replay is valid when the state
        # remains realized-only and pre-outcome.
        _sha(self.state_evidence_sha256, "state_evidence_sha256")
        _sha(self.proposal_evidence_sha256, "proposal_evidence_sha256")
        if (
            not isinstance(self.evaluation_horizon_minutes, int)
            or isinstance(self.evaluation_horizon_minutes, bool)
            or self.evaluation_horizon_minutes <= 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 decision evaluation horizon must be positive int"
            )
        if self.proposal_action is Genc7Action.HOLD_CURRENT_CAPITAL_STATE:
            raise CiboCompoundCapitalError(
                "GEN-C7 decision proposal action cannot be control HOLD"
            )
        expected_source = _ACTION_SOURCE.get(self.proposal_action)
        if expected_source is not self.proposal_source_bucket:
            raise CiboCompoundCapitalError(
                "GEN-C7 decision proposal action/source drift"
            )
        _positive(self.proposal_amount_usd, "proposal_amount_usd")
        for name in (
            "initial_realized_capital_usd",
            "initial_realized_profit_usd",
            "initial_protected_floor_usd",
            "initial_base_capital_usd",
            "initial_compound_capital_usd",
            "control_amount_usd",
            "treatment_amount_usd",
            "giveback_amount_usd",
            "profit_retention_ratio",
            "base_drawdown_usd",
            "compound_drawdown_usd",
        ):
            _nonnegative(getattr(self, name), name)
        if self.floor_growth_rate is not None:
            if (
                not isinstance(self.floor_growth_rate, Decimal)
                or not self.floor_growth_rate.is_finite()
                or self.floor_growth_rate < 0
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C7 floor growth rate must be finite non-negative"
                )
        if (
            self.control_action is not Genc7Action.HOLD_CURRENT_CAPITAL_STATE
            or self.control_amount_usd != 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 V1 control must HOLD with zero amount"
            )
        if len(self.blocker_codes) != len(set(self.blocker_codes)):
            raise CiboCompoundCapitalError(
                "GEN-C7 blocker codes must be unique"
            )
        treatment_active = (
            self.treatment_action is not Genc7Action.HOLD_CURRENT_CAPITAL_STATE
        )
        if treatment_active:
            if self.treatment_amount_usd <= 0 or self.blocker_codes:
                raise CiboCompoundCapitalError(
                    "GEN-C7 active treatment must be positive and unblocked"
                )
            if (
                self.treatment_action is not self.proposal_action
                or self.treatment_amount_usd != self.proposal_amount_usd
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C7 active treatment must equal exact proposal"
                )
        elif self.treatment_amount_usd != 0:
            raise CiboCompoundCapitalError(
                "GEN-C7 held treatment must have zero amount"
            )
        if self.treatment_differs_from_control != treatment_active:
            raise CiboCompoundCapitalError(
                "GEN-C7 treatment/control divergence flag drift"
            )
        for name in (
            "outcome_present_at_seal",
            "runtime_authority",
            "sizing_authority",
            "risk_authority",
            "execution_authority",
            "live_authority",
            "real_capital_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C7 {name} must be bool"
                )
            if getattr(self, name):
                raise CiboCompoundCapitalError(
                    "GEN-C7 shadow decision cannot contain outcome/authority"
                )


def genc7_policy_sha256() -> str:
    payload = {
        "policy_id": GENC7_POLICY_ID,
        "frozen_at": GENC7_POLICY_FROZEN_AT.isoformat(),
        "control": {
            "action": Genc7Action.HOLD_CURRENT_CAPITAL_STATE.value,
            "amount_usd": "0",
        },
        "treatment_actions": tuple(
            item.value
            for item in Genc7Action
            if item is not Genc7Action.HOLD_CURRENT_CAPITAL_STATE
        ),
        "source_law": {
            Genc7Action.PROTECT.value: (
                Genc7SourceBucket.REALIZED_UNPROTECTED_PROFIT.value
            ),
            Genc7Action.HARVEST_TO_STRATEGIC_RESERVE.value: (
                Genc7SourceBucket.REALIZED_UNPROTECTED_PROFIT.value
            ),
            Genc7Action.RESERVE_OPPORTUNITY_CAPACITY.value: (
                Genc7SourceBucket.COMPOUNDABLE_OR_RELEASED_CAPACITY.value
            ),
            Genc7Action.COMPOUND.value: (
                Genc7SourceBucket.COMPOUNDABLE_OR_RELEASED_CAPACITY.value
            ),
        },
        "amount_rule": "exact preregistered proposal amount; never resized",
        "outcome_window_rule": (
            "proposal carries positive pre-outcome evaluation_horizon_minutes"
        ),
        "floating_pnl_capital": False,
        "house_money_bias": False,
        "protected_floor_can_decrease": False,
        "runtime_authority": False,
        "sizing_authority": False,
        "risk_authority": False,
        "execution_authority": False,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def evaluate_genc7_profit_preservation_shadow(
    *,
    state: Genc7CapitalStateEvidence,
    proposal: Genc7PreservationProposalEvidence,
    decision_id: str,
) -> Genc7ProfitPreservationShadowDecision:
    """Evaluate frozen GEN-C7 V1 treatment/control without mutating capital."""

    if not isinstance(state, Genc7CapitalStateEvidence):
        raise CiboCompoundCapitalError(
            "GEN-C7 requires canonical capital-state evidence"
        )
    if not isinstance(proposal, Genc7PreservationProposalEvidence):
        raise CiboCompoundCapitalError(
            "GEN-C7 requires canonical preservation proposal"
        )
    if not decision_id:
        raise CiboCompoundCapitalError(
            "GEN-C7 decision_id is required"
        )
    # Apply the frozen policy to any causal historical state. The engine
    # still forbids future outcomes, authority drift and cross-account mixing.
    if proposal.decision_at != state.decision_at:
        raise CiboCompoundCapitalError(
            "GEN-C7 proposal/state decision-time binding drift"
        )
    if proposal.account_identity != state.account_identity:
        raise CiboCompoundCapitalError(
            "GEN-C7 proposal/state account binding drift"
        )

    blockers: list[str] = []
    if not proposal.calibrated:
        blockers.append("PROPOSAL_NOT_CALIBRATED")
    if not proposal.capital_eligible:
        blockers.append("PROPOSAL_NOT_CAPITAL_ELIGIBLE")

    if (
        proposal.source_bucket
        is Genc7SourceBucket.REALIZED_UNPROTECTED_PROFIT
    ):
        available = state.realized_unprotected_profit_usd
    else:
        available = state.compound_candidate_capacity_usd

    if proposal.amount_usd > available:
        blockers.append("SOURCE_BUCKET_CAPACITY_INSUFFICIENT")

    if blockers:
        treatment_action = Genc7Action.HOLD_CURRENT_CAPITAL_STATE
        treatment_amount = Decimal("0")
    else:
        treatment_action = proposal.action
        treatment_amount = proposal.amount_usd

    return Genc7ProfitPreservationShadowDecision(
        policy_id=GENC7_POLICY_ID,
        policy_sha256=genc7_policy_sha256(),
        policy_frozen_at=GENC7_POLICY_FROZEN_AT,
        decision_id=decision_id,
        decision_at=state.decision_at,
        account_provider_key=state.account_identity.provider_key,
        account_ref=state.account_identity.account_ref,
        state_evidence_sha256=state.fingerprint(),
        proposal_evidence_sha256=proposal.fingerprint(),
        proposal_action=proposal.action,
        proposal_source_bucket=proposal.source_bucket,
        proposal_amount_usd=proposal.amount_usd,
        evaluation_horizon_minutes=proposal.evaluation_horizon_minutes,
        initial_realized_capital_usd=state.current_realized_capital_usd,
        initial_realized_profit_usd=state.current_realized_profit_usd,
        initial_protected_floor_usd=state.protected_floor_usd,
        initial_base_capital_usd=state.current_base_capital_usd,
        initial_compound_capital_usd=state.current_compound_capital_usd,
        control_action=Genc7Action.HOLD_CURRENT_CAPITAL_STATE,
        control_amount_usd=Decimal("0"),
        treatment_action=treatment_action,
        treatment_amount_usd=treatment_amount,
        blocker_codes=tuple(blockers),
        giveback_amount_usd=state.giveback_amount_usd,
        profit_retention_ratio=state.profit_retention_ratio,
        floor_growth_rate=state.floor_growth_rate,
        base_drawdown_usd=state.base_drawdown_usd,
        compound_drawdown_usd=state.compound_drawdown_usd,
        treatment_differs_from_control=not blockers,
        outcome_present_at_seal=False,
        runtime_authority=False,
        sizing_authority=False,
        risk_authority=False,
        execution_authority=False,
        live_authority=False,
        real_capital_authority=False,
    )
