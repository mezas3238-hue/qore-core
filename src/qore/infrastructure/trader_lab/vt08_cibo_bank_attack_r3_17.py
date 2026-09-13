"""CIBO BANK->ATTACK research engine for VT-08 R3.17.

VT-08 keeps signal authority. CIBO owns the operating posture and may BUILD,
BANK or ATTACK. Risk remains sovereign over capital exposure: every CIBO posture
emits only a Risk request, which is then reduced or rejected against the daily,
capital, banked-profit and heat constraints before any modeled execution.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceRef,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.cibo_trader_manager import CiboRiskMode
from qore.infrastructure.cibo_trader_operating_manager import (
    CiboCapitalSnapshot,
    CiboOperatingAuthority,
    CiboOperatingDecision,
    CiboOperatingPosture,
    CiboRiskRequestMode,
    CiboTraderOperatingManager,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.infrastructure.trader_lab.vt08_cibo_data_r3_16 import ReplayTrade

PROVIDER_DAILY_LIMIT = 0.05
INTERNAL_DAILY_LIMIT = 0.0475
INTERNAL_CAPITAL_DRAWDOWN_LIMIT = 0.0495
_EPSILON = 1e-12

_VT08_CONFIG_FINGERPRINT = (
    "0c3fe8e1353386f7384a8532c7fe71bbbe9fcfdf1da7530be4b53e01bc59de0d"
)
_CIBO_MANAGER = CiboTraderOperatingManager()
_CIBO_AUTHORITY = CiboOperatingAuthority(
    trader_identity=ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily("virtual.trader.vt08"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("r3.8-b01-author-clarified-v1"),
    ),
    config_fingerprint=CiboTraderConfigFingerprint(_VT08_CONFIG_FINGERPRINT),
    risk_mode=CiboRiskMode.CIBO_MANAGED_TRADERS_RISK,
    authority_ref=CiboEvidenceRef("evidence:r317-consumed-research-authority"),
    research_only=True,
)
_BASE_RISK_ENVELOPE = CiboEvidenceRef("evidence:r317-risk-envelope.base")
_ATTACK_RISK_ENVELOPE = CiboEvidenceRef("evidence:r317-risk-envelope.attack")
_R317_EVIDENCE = CiboEvidenceRef("evidence:r317-bank-attack-consumed-study")


class CiboBankAttackError(ValueError):
    """Raised when the R3.17 sovereignty or drawdown contract is violated."""


@dataclass(frozen=True, slots=True)
class RiskLevel:
    name: str
    a_risk: float
    gbpjpy_risk: float
    heat: float

    def __post_init__(self) -> None:
        if min(self.a_risk, self.gbpjpy_risk, self.heat) <= 0:
            raise CiboBankAttackError("Risk values must be positive")
        if self.heat < max(self.a_risk, self.gbpjpy_risk):
            raise CiboBankAttackError("Risk heat cannot be below single-trade risk")


@dataclass(frozen=True, slots=True)
class BankAttackPolicy:
    name: str
    profit_trigger: float
    bank_fraction: float
    minimum_free_cushion: float

    def __post_init__(self) -> None:
        if not 0 < self.profit_trigger < 1:
            raise CiboBankAttackError("profit trigger must be in (0,1)")
        if not 0 < self.bank_fraction <= 1:
            raise CiboBankAttackError("bank fraction must be in (0,1]")
        if not 0 <= self.minimum_free_cushion < 1:
            raise CiboBankAttackError("minimum free cushion must be in [0,1)")


@dataclass(frozen=True, slots=True)
class BankAttackMetrics:
    terminal_return: float
    maximum_capital_drawdown: float
    maximum_daily_drawdown: float
    generated_signals: int
    executed_trades: int
    risk_lockouts: int
    bank_decisions: int
    attack_trades: int
    attack_activations: int
    cibo_protected_exits: int


RISK_LEVELS = (
    RiskLevel("r075", 0.0075, 0.0060, 0.0200),
    RiskLevel("r100", 0.0100, 0.0080, 0.0250),
    RiskLevel("r125", 0.0125, 0.0100, 0.0300),
    RiskLevel("r150", 0.0150, 0.0120, 0.0350),
    RiskLevel("r200", 0.0200, 0.0150, 0.0450),
    RiskLevel("r225", 0.0225, 0.0170, 0.0500),
    RiskLevel("r250", 0.0250, 0.0190, 0.0550),
)

BANK_POLICIES = (
    BankAttackPolicy("bank25-t2", 0.02, 0.25, 0.005),
    BankAttackPolicy("bank50-t2", 0.02, 0.50, 0.005),
    BankAttackPolicy("bank75-t3", 0.03, 0.75, 0.004),
    BankAttackPolicy("bank50-t4", 0.04, 0.50, 0.005),
)


def _risk_capital_floor(peak_equity: float) -> float:
    return max(
        1.0 - INTERNAL_CAPITAL_DRAWDOWN_LIMIT,
        peak_equity * (1.0 - INTERNAL_CAPITAL_DRAWDOWN_LIMIT),
    )


def _banked_floor(
    *,
    peak_equity: float,
    current_banked_floor: float,
    policy: BankAttackPolicy,
) -> float:
    if peak_equity < 1.0 + policy.profit_trigger:
        return current_banked_floor
    candidate = 1.0 + policy.bank_fraction * (peak_equity - 1.0)
    return max(current_banked_floor, candidate)


def protected_capital_floor(*, peak_equity: float, policy: BankAttackPolicy) -> float:
    """Return effective Risk + CIBO banked capital floor."""

    if peak_equity <= 0:
        raise CiboBankAttackError("peak equity must be positive")
    return max(
        _risk_capital_floor(peak_equity),
        _banked_floor(
            peak_equity=peak_equity,
            current_banked_floor=0.0,
            policy=policy,
        ),
    )


def attack_is_available(
    *,
    equity: float,
    peak_equity: float,
    policy: BankAttackPolicy,
) -> bool:
    if peak_equity < 1.0 + policy.profit_trigger:
        return False
    floor = protected_capital_floor(peak_equity=peak_equity, policy=policy)
    free_cushion = max(0.0, equity - floor)
    return free_cushion / max(equity, _EPSILON) >= policy.minimum_free_cushion


def _daily_floor(day_start_equity: float) -> float:
    return day_start_equity * (1.0 - INTERNAL_DAILY_LIMIT)


def _worst_loss_fraction(amount: float, trade: ReplayTrade) -> float:
    modeled_cost_r = max(0.0, trade.gross_r - trade.net_r)
    return amount * (1.0 + modeled_cost_r)


def _decision_time(trading_day: date, anchor: int) -> datetime:
    return datetime.combine(trading_day, time(hour=anchor), tzinfo=UTC)


def _cibo_operating_decision(
    *,
    equity: float,
    peak: float,
    day_start: float,
    current_banked_floor: float,
    trading_day: date,
    anchor: int,
    policy: BankAttackPolicy,
) -> CiboOperatingDecision:
    risk_floor = _risk_capital_floor(peak)
    desired_banked_floor = _banked_floor(
        peak_equity=peak,
        current_banked_floor=current_banked_floor,
        policy=policy,
    )
    effective_floor = max(risk_floor, desired_banked_floor)
    free_cushion = max(0.0, equity - effective_floor)
    cushion_fraction = free_cushion / max(equity, _EPSILON)
    banked_profit = desired_banked_floor > 1.0 + _EPSILON

    if banked_profit and cushion_fraction >= policy.minimum_free_cushion:
        posture = CiboOperatingPosture.ATTACK
        envelope = _ATTACK_RISK_ENVELOPE
        reason = "banked-profit-free-cushion"
    elif desired_banked_floor > current_banked_floor + _EPSILON:
        posture = CiboOperatingPosture.BANK
        envelope = _BASE_RISK_ENVELOPE
        reason = "profit-bank-ratchet"
    elif equity > 1.0:
        posture = CiboOperatingPosture.PROTECT
        envelope = _BASE_RISK_ENVELOPE
        reason = "capital-preservation"
    else:
        posture = CiboOperatingPosture.BUILD
        envelope = _BASE_RISK_ENVELOPE
        reason = "build-cushion"

    observed_at = _decision_time(trading_day, anchor)
    capital = CiboCapitalSnapshot(
        starting_equity=Decimal("1"),
        equity=Decimal(str(equity)),
        peak_equity=Decimal(str(peak)),
        day_start_equity=Decimal(str(day_start)),
        risk_floor=Decimal(str(risk_floor)),
        current_banked_floor=Decimal(str(current_banked_floor)),
        observed_at=observed_at,
    )
    return _CIBO_MANAGER.issue(
        _CIBO_AUTHORITY,
        posture,
        capital,
        protected_capital_floor=Decimal(str(desired_banked_floor)),
        requested_risk_envelope=envelope,
        decided_at=observed_at,
        reasons=(reason,),
        evidence_refs=(_R317_EVIDENCE,),
    )


def run_bank_attack_sequence(
    days: Sequence[date],
    mapped: Mapping[date, Mapping[int, Sequence[ReplayTrade]]],
    *,
    base_risk: RiskLevel,
    attack_risk: RiskLevel,
    policy: BankAttackPolicy,
) -> BankAttackMetrics:
    """Replay one account path with CIBO posture and independent Risk enforcement."""

    if (
        attack_risk.a_risk < base_risk.a_risk
        or attack_risk.gbpjpy_risk < base_risk.gbpjpy_risk
        or attack_risk.heat < base_risk.heat
    ):
        raise CiboBankAttackError("ATTACK Risk cannot be below base Risk")

    equity = 1.0
    peak = 1.0
    current_banked_floor = 0.0
    max_capital_dd = 0.0
    max_daily_dd = 0.0
    generated = 0
    executed = 0
    lockouts = 0
    bank_decisions = 0
    attack_trades = 0
    attack_activations = 0
    protected_exits = 0
    attack_was_active = False

    for trading_day in days:
        day_start = equity
        daily_floor = _daily_floor(day_start)
        for anchor in sorted(mapped.get(trading_day, {})):
            group = tuple(mapped[trading_day][anchor])
            generated += len(group)

            decision = _cibo_operating_decision(
                equity=equity,
                peak=peak,
                day_start=day_start,
                current_banked_floor=current_banked_floor,
                trading_day=trading_day,
                anchor=anchor,
                policy=policy,
            )
            previous_bank = current_banked_floor
            current_banked_floor = float(decision.protected_capital_floor)
            bank_decisions += int(current_banked_floor > previous_bank + _EPSILON)

            attack_active = decision.risk_request.mode is CiboRiskRequestMode.ATTACK
            if attack_active and not attack_was_active:
                attack_activations += 1
            attack_was_active = attack_active

            level = attack_risk if attack_active else base_risk
            desired = tuple(
                level.gbpjpy_risk if trade.sleeve == "G" else level.a_risk
                for trade in group
            )
            desired_total = sum(desired)
            heat_scale = (
                1.0
                if desired_total <= level.heat or desired_total == 0
                else level.heat / desired_total
            )
            worst_total = sum(
                _worst_loss_fraction(amount, trade)
                for amount, trade in zip(desired, group, strict=True)
            )

            cibo_budget = float(decision.risk_request.cibo_loss_budget_ceiling)
            daily_headroom = max(0.0, equity - daily_floor)
            risk_headroom = min(cibo_budget, daily_headroom)
            headroom_fraction = risk_headroom / max(equity, _EPSILON)
            floor_scale = (
                1.0
                if worst_total <= headroom_fraction or worst_total == 0
                else headroom_fraction / worst_total
            )

            scale = min(heat_scale, floor_scale)
            if scale <= _EPSILON:
                lockouts += len(group)
                continue

            pnl = 0.0
            for amount, trade in zip(desired, group, strict=True):
                allocated = amount * scale
                if allocated <= _EPSILON:
                    lockouts += 1
                    continue
                pnl += equity * allocated * trade.net_r
                executed += 1
                attack_trades += int(attack_active)
                protected_exits += int(
                    trade.exit_reason == "cibo_protected_stop"
                )

            equity += pnl
            peak = max(peak, equity)
            capital_dd = (peak - equity) / peak
            daily_dd = (day_start - equity) / day_start
            max_capital_dd = max(max_capital_dd, capital_dd)
            max_daily_dd = max(max_daily_dd, daily_dd)

            if daily_dd >= PROVIDER_DAILY_LIMIT - _EPSILON:
                raise CiboBankAttackError(
                    "provider 5% daily drawdown was touched"
                )
            if daily_dd > INTERNAL_DAILY_LIMIT + _EPSILON:
                raise CiboBankAttackError(
                    "internal daily drawdown floor was violated"
                )
            if capital_dd >= 0.05 - _EPSILON:
                raise CiboBankAttackError("5% capital drawdown was touched")
            if capital_dd > INTERNAL_CAPITAL_DRAWDOWN_LIMIT + _EPSILON:
                raise CiboBankAttackError(
                    "internal capital drawdown floor was violated"
                )

    return BankAttackMetrics(
        terminal_return=equity - 1.0,
        maximum_capital_drawdown=max_capital_dd,
        maximum_daily_drawdown=max_daily_dd,
        generated_signals=generated,
        executed_trades=executed,
        risk_lockouts=lockouts,
        bank_decisions=bank_decisions,
        attack_trades=attack_trades,
        attack_activations=attack_activations,
        cibo_protected_exits=protected_exits,
    )


def group_by_day_and_anchor(
    records: Sequence[ReplayTrade],
) -> dict[date, dict[int, list[ReplayTrade]]]:
    result: dict[date, dict[int, list[ReplayTrade]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item in records:
        result[item.day][item.anchor].append(item)
    return result
