"""Conservative QORE-internal capital policy for the real Stellar Instant account.

Provider constraints and QORE operating limits are deliberately separate:

* FundedNext provider wall: exact 6% trailing MLL plus the separate cumulative open-risk cap.
* QORE does not replace the 6% Maximum Loss with a 3% drawdown rule; internal
  containment uses a safety buffer and shared account heat caps above the provider wall.
* CIBO may request NORMAL/BANK/ATTACK; this policy either ALLOWs the request,
  REDUCEs ATTACK to NORMAL when earned cushion is insufficient, or REJECTs new
  risk. No posture changes VT-08's certified per-trade bps.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from qore.infrastructure.account_wide_risk import AccountWideRiskError
from qore.infrastructure.fundednext_stellar_instant import (
    MAXIMUM_LOSS_FRACTION,
    StellarInstantRiskBudget,
)
from qore.infrastructure.vt08_forex_cibo_operational import Vt08ForexCiboPosture

QORE_INTERNAL_SAFETY_BUFFER_FRACTION = Decimal("0.005")
QORE_INTERNAL_BANK_HEAT_FRACTION = Decimal("0.03")
QORE_INTERNAL_NORMAL_HEAT_FRACTION = Decimal("0.03")
QORE_INTERNAL_ATTACK_HEAT_FRACTION = Decimal("0.03")
QORE_INTERNAL_ATTACK_MIN_EARNED_CUSHION_FRACTION = Decimal("0.01")
QORE_OPERATIONAL_RISK_POLICY_VERSION = "qore-stellar-instant-operational-risk-v3"


class CapitalBudgetDecision(StrEnum):
    ALLOW = "ALLOW"
    REDUCE = "REDUCE"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class QoreOperationalCapitalBudget:
    requested_posture: Vt08ForexCiboPosture
    authorized_posture: Vt08ForexCiboPosture
    decision: CapitalBudgetDecision
    provider_maximum_loss_fraction: Decimal
    provider_active_mll: Decimal
    provider_headroom: Decimal
    qore_internal_floor: Decimal
    qore_internal_safety_buffer: Decimal
    aggregate_heat_cap: Decimal
    qore_authorizable_headroom: Decimal
    current_aggregate_stop_risk: Decimal
    available_risk_budget: Decimal
    earned_closed_balance_cushion: Decimal
    attack_authorized: bool
    reason: str
    policy_version: str
    policy_fingerprint: str

    def __post_init__(self) -> None:
        if type(self.requested_posture) is not Vt08ForexCiboPosture:
            raise AccountWideRiskError("requested posture must be canonical")
        if type(self.authorized_posture) is not Vt08ForexCiboPosture:
            raise AccountWideRiskError("authorized posture must be canonical")
        if type(self.decision) is not CapitalBudgetDecision:
            raise AccountWideRiskError("capital budget decision must be canonical")
        for name, value in (
            ("provider_maximum_loss_fraction", self.provider_maximum_loss_fraction),
            ("provider_active_mll", self.provider_active_mll),
            ("provider_headroom", self.provider_headroom),
            ("qore_internal_floor", self.qore_internal_floor),
            ("qore_internal_safety_buffer", self.qore_internal_safety_buffer),
            ("aggregate_heat_cap", self.aggregate_heat_cap),
            ("qore_authorizable_headroom", self.qore_authorizable_headroom),
            ("current_aggregate_stop_risk", self.current_aggregate_stop_risk),
            ("available_risk_budget", self.available_risk_budget),
            ("earned_closed_balance_cushion", self.earned_closed_balance_cushion),
        ):
            _nonnegative(value, name)
        if self.provider_maximum_loss_fraction != MAXIMUM_LOSS_FRACTION:
            raise AccountWideRiskError("provider MLL fraction must remain exact 6%")
        if self.qore_authorizable_headroom > self.provider_headroom:
            raise AccountWideRiskError("QORE capital budget cannot exceed provider headroom")
        if self.available_risk_budget > self.qore_authorizable_headroom:
            raise AccountWideRiskError("available budget cannot exceed QORE headroom")
        if not self.reason:
            raise AccountWideRiskError("capital budget reason required")
        if self.policy_version != QORE_OPERATIONAL_RISK_POLICY_VERSION:
            raise AccountWideRiskError("capital budget policy version mismatch")
        if self.policy_fingerprint != operational_risk_policy_fingerprint():
            raise AccountWideRiskError("capital budget policy fingerprint mismatch")
        if self.attack_authorized and self.authorized_posture is not Vt08ForexCiboPosture.ATTACK:
            raise AccountWideRiskError("attack authorization requires ATTACK posture")


def operational_risk_policy_fingerprint() -> str:
    material = {
        "version": QORE_OPERATIONAL_RISK_POLICY_VERSION,
        "provider_maximum_loss_fraction": str(MAXIMUM_LOSS_FRACTION),
        "provider_cumulative_open_risk_rule": True,
        "provider_cumulative_open_risk_fraction": "0.03",
        "internal_safety_buffer_fraction": str(QORE_INTERNAL_SAFETY_BUFFER_FRACTION),
        "bank_heat_fraction": str(QORE_INTERNAL_BANK_HEAT_FRACTION),
        "normal_heat_fraction": str(QORE_INTERNAL_NORMAL_HEAT_FRACTION),
        "attack_heat_fraction": str(QORE_INTERNAL_ATTACK_HEAT_FRACTION),
        "attack_min_earned_cushion_fraction": str(
            QORE_INTERNAL_ATTACK_MIN_EARNED_CUSHION_FRACTION
        ),
        "per_trade_vt08_risk_unchanged_by_posture": True,
        "minimum_broker_volume_uplift_requires_shared_headroom": True,
        "aggregate_heat_shared_by_all_traders": True,
        "risk_final_capital_authority": True,
    }
    return sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def evaluate_qore_operational_capital_budget(
    *,
    provider_budget: StellarInstantRiskBudget,
    initial_balance: Decimal,
    balance: Decimal,
    equity: Decimal,
    highest_closed_balance: Decimal,
    current_aggregate_stop_risk: Decimal,
    requested_posture: Vt08ForexCiboPosture,
    certified_open_risk_fraction: Decimal | None = None,
) -> QoreOperationalCapitalBudget:
    """Resolve CIBO posture against provider distance and conservative QORE limits."""

    if not isinstance(provider_budget, StellarInstantRiskBudget):
        raise AccountWideRiskError("provider budget must be StellarInstantRiskBudget")
    for name, value in (
        ("initial_balance", initial_balance),
        ("balance", balance),
        ("equity", equity),
        ("highest_closed_balance", highest_closed_balance),
    ):
        _positive(value, name)
    _nonnegative(current_aggregate_stop_risk, "current_aggregate_stop_risk")
    if highest_closed_balance < initial_balance:
        raise AccountWideRiskError("highest closed balance cannot be below initial balance")
    if type(requested_posture) is not Vt08ForexCiboPosture:
        raise AccountWideRiskError("requested posture must be canonical")
    if provider_budget.initial_balance != initial_balance:
        raise AccountWideRiskError("provider/QORE initial balance mismatch")
    if certified_open_risk_fraction is not None:
        _positive(certified_open_risk_fraction, "certified_open_risk_fraction")
        if certified_open_risk_fraction > Decimal("0.03"):
            raise AccountWideRiskError(
                "certified open-risk fraction cannot exceed provider default 3%"
            )

    # The trailing Maximum Loss is exactly the provider's 6% MLL.
    # QORE adds a safety buffer and heat caps; it does not invent a separate
    # 3% drawdown/Maximum Loss floor.
    internal_floor = provider_budget.active_mll
    safety_buffer = initial_balance * QORE_INTERNAL_SAFETY_BUFFER_FRACTION
    earned_cushion = max(Decimal(0), highest_closed_balance - initial_balance)
    attack_threshold = (
        initial_balance * QORE_INTERNAL_ATTACK_MIN_EARNED_CUSHION_FRACTION
    )

    authorized_posture = requested_posture
    posture_decision = CapitalBudgetDecision.ALLOW
    posture_reason = "requested-posture-fits-qore-policy"
    if requested_posture is Vt08ForexCiboPosture.ATTACK and earned_cushion < attack_threshold:
        authorized_posture = Vt08ForexCiboPosture.NORMAL
        posture_decision = CapitalBudgetDecision.REDUCE
        posture_reason = "attack-reduced-earned-cushion-insufficient"

    heat_fraction = {
        Vt08ForexCiboPosture.BANK: QORE_INTERNAL_BANK_HEAT_FRACTION,
        Vt08ForexCiboPosture.NORMAL: QORE_INTERNAL_NORMAL_HEAT_FRACTION,
        Vt08ForexCiboPosture.ATTACK: QORE_INTERNAL_ATTACK_HEAT_FRACTION,
    }[authorized_posture]
    heat_cap = initial_balance * heat_fraction
    if certified_open_risk_fraction is not None:
        heat_cap = min(
            heat_cap,
            initial_balance * certified_open_risk_fraction,
        )
    dd_capacity = max(Decimal(0), equity - internal_floor - safety_buffer)
    total_headroom = min(
        provider_budget.provider_headroom,
        provider_budget.max_risk_at_any_time,
        dd_capacity,
        heat_cap,
    )
    available = max(Decimal(0), total_headroom - current_aggregate_stop_risk)

    decision = posture_decision
    reason = posture_reason
    if provider_budget.hard_breach:
        decision = CapitalBudgetDecision.REJECT
        reason = "provider-6pct-trailing-mll-breached"
        total_headroom = Decimal(0)
        available = Decimal(0)
    elif equity <= internal_floor + safety_buffer:
        decision = CapitalBudgetDecision.REJECT
        reason = "qore-internal-dd-buffer-exhausted"
        total_headroom = Decimal(0)
        available = Decimal(0)
    elif available <= 0:
        decision = CapitalBudgetDecision.REJECT
        reason = "qore-account-wide-heat-or-dd-budget-exhausted"

    attack_authorized = (
        decision is CapitalBudgetDecision.ALLOW
        and authorized_posture is Vt08ForexCiboPosture.ATTACK
    )
    return QoreOperationalCapitalBudget(
        requested_posture=requested_posture,
        authorized_posture=authorized_posture,
        decision=decision,
        provider_maximum_loss_fraction=MAXIMUM_LOSS_FRACTION,
        provider_active_mll=provider_budget.active_mll,
        provider_headroom=provider_budget.provider_headroom,
        qore_internal_floor=internal_floor,
        qore_internal_safety_buffer=safety_buffer,
        aggregate_heat_cap=heat_cap,
        qore_authorizable_headroom=total_headroom,
        current_aggregate_stop_risk=current_aggregate_stop_risk,
        available_risk_budget=available,
        earned_closed_balance_cushion=earned_cushion,
        attack_authorized=attack_authorized,
        reason=reason,
        policy_version=QORE_OPERATIONAL_RISK_POLICY_VERSION,
        policy_fingerprint=operational_risk_policy_fingerprint(),
    )


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise AccountWideRiskError(f"{name} must be positive finite Decimal")


def _nonnegative(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise AccountWideRiskError(f"{name} must be non-negative finite Decimal")
