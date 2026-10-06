"""Universal GEN-C1..GEN-C14 accountability registry for CIBO.

This module intentionally has no Trader, symbol, asset or timeframe selector.
Capital Science eligibility is derived only from account-local economic state,
causal capital provenance, portfolio scope and governance flags.

The registry does not fabricate productive authority. Engines that exist but
are not legally consumed by the current replay are reported as
JUSTIFIED_NOT_APPLICABLE instead of disappearing as NOT_INTEGRATED.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


class CapitalScienceDisposition(StrEnum):
    APPLIED = "APPLIED"
    ELIGIBLE_NO_CHANGE = "ELIGIBLE_NO_CHANGE"
    JUSTIFIED_NOT_APPLICABLE = "JUSTIFIED_NOT_APPLICABLE"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class CapitalScienceSpec:
    code: str
    name: str
    implementation_module: str
    role: str


GENC_REGISTRY: tuple[CapitalScienceSpec, ...] = (
    CapitalScienceSpec(
        "GEN-C1",
        "Compound Capital",
        "qore.infrastructure.cibo_compound_capital",
        "realized-profit compound capital",
    ),
    CapitalScienceSpec(
        "GEN-C2",
        "Protected Capital Floor",
        "qore.infrastructure.cibo_a1_genc2_phase22_profit_graduation",
        "profit graduation / protected-floor intelligence",
    ),
    CapitalScienceSpec(
        "GEN-C3",
        "Core Compound Portfolio",
        "qore.infrastructure.cibo_core_compound_portfolio",
        "account-local cross-Trader compound portfolio",
    ),
    CapitalScienceSpec(
        "GEN-C4",
        "Marginal Capital Utility",
        "qore.infrastructure.cibo_marginal_leverage_utility",
        "marginal capital utility and opportunity-cost gate",
    ),
    CapitalScienceSpec(
        "GEN-C5",
        "Sequential Compounding",
        "qore.infrastructure.cibo_sequential_compounding_shadow_policy",
        "causal realized-profit sequential redeployment",
    ),
    CapitalScienceSpec(
        "GEN-C6",
        "Internal Capital Market",
        "qore.infrastructure.cibo_internal_capital_market",
        "scarce-capital competition and cross-Trader allocation",
    ),
    CapitalScienceSpec(
        "GEN-C7",
        "Profit Preservation",
        "qore.infrastructure.cibo_profit_preservation_economic_gate",
        "profit giveback / preservation intelligence",
    ),
    CapitalScienceSpec(
        "GEN-C8",
        "Adaptive Compound Speed",
        "qore.infrastructure.cibo_adaptive_compound_speed_economic_gate",
        "adaptive compound-speed intelligence",
    ),
    CapitalScienceSpec(
        "GEN-C9",
        "Robust Growth / Ruin",
        "qore.infrastructure.cibo_robust_growth_ruin_capacity",
        "risk-of-ruin constrained growth",
    ),
    CapitalScienceSpec(
        "GEN-C10",
        "Capital Digital Twin",
        "qore.infrastructure.cibo_capital_digital_twin",
        "account-level capital digital twin",
    ),
    CapitalScienceSpec(
        "GEN-C11",
        "Multi-Period Capital Intelligence",
        "qore.infrastructure.cibo_multi_period_capital_mpc",
        "multi-period capital planning and utility",
    ),
    CapitalScienceSpec(
        "GEN-C12",
        "Crisis Capital Intelligence",
        "qore.infrastructure.cibo_crisis_capital_intelligence",
        "crisis / tail-regime capital intelligence",
    ),
    CapitalScienceSpec(
        "GEN-C13",
        "Meta-Capital Memory",
        "qore.infrastructure.cibo_meta_capital_memory",
        "capital memory, counterfactual and skeptic layer",
    ),
    CapitalScienceSpec(
        "GEN-C14",
        "Governed Capital Science",
        "qore.infrastructure.cibo_governed_capital_science",
        "governed capital-science hypothesis lifecycle",
    ),
)


@dataclass(frozen=True, slots=True)
class UniversalCapitalScienceContext:
    """Asset-agnostic economic state observed by the GEN-C registry."""

    epoch_count: int
    selected_count: int
    realized_profit_settlement_count: int
    compound_settlement_count: int
    compound_rejected_count: int
    cross_trader_deployment_count: int
    core_ending_capital_usd: Decimal
    compound_incremental_pnl_usd: Decimal
    total_compound_risk_usd: Decimal
    total_compound_margin_usd: Decimal
    total_provider_cost_usd: Decimal
    protected_loss_reserve_usd: Decimal
    account_pool_enabled: bool
    rational_redeploy_gate_enabled: bool
    qore_risk_sovereign: bool
    fixed_leverage_experiment: bool
    burned_adaptive_research: bool

    def __post_init__(self) -> None:
        for name in (
            "epoch_count",
            "selected_count",
            "realized_profit_settlement_count",
            "compound_settlement_count",
            "compound_rejected_count",
            "cross_trader_deployment_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCapitalManagementError(
                    f"universal GEN-C context {name} must be non-negative int"
                )
        for name in (
            "core_ending_capital_usd",
            "compound_incremental_pnl_usd",
            "total_compound_risk_usd",
            "total_compound_margin_usd",
            "total_provider_cost_usd",
            "protected_loss_reserve_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"universal GEN-C context {name} must be finite Decimal"
                )
        for name in (
            "account_pool_enabled",
            "rational_redeploy_gate_enabled",
            "qore_risk_sovereign",
            "fixed_leverage_experiment",
            "burned_adaptive_research",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"universal GEN-C context {name} must be bool"
                )
        if not self.qore_risk_sovereign:
            raise CiboCapitalManagementError(
                "universal GEN-C registry requires sovereign QORE Risk"
            )


def _row(
    spec: CapitalScienceSpec,
    *,
    disposition: CapitalScienceDisposition,
    eligible_epochs: int,
    invoked_count: int,
    applied_count: int,
    fail_closed_count: int,
    not_applicable_count: int,
    decision_changed_count: int,
    risk_delta_usd: Decimal = Decimal(0),
    margin_delta_usd: Decimal = Decimal(0),
    capital_source_usage: tuple[str, ...] = (),
    incremental_pnl_attribution_usd: Decimal = Decimal(0),
    reason: str,
) -> dict[str, Any]:
    if invoked_count < applied_count:
        raise CiboCapitalManagementError(
            f"{spec.code} applied_count cannot exceed invoked_count"
        )
    return {
        "function_code": spec.code,
        "function_name": spec.name,
        "function_type": spec.role,
        "implementation_module": spec.implementation_module,
        "universal_contract": True,
        "identity_predicate_used": False,
        "status": disposition.value,
        "eligible_epochs": eligible_epochs,
        "invoked_count": invoked_count,
        "applied_count": applied_count,
        "executed_count": applied_count,
        "fail_closed_count": fail_closed_count,
        "not_applicable_count": not_applicable_count,
        "blocked_count": fail_closed_count,
        "decision_changed_count": decision_changed_count,
        "risk_delta_usd": format(risk_delta_usd, "f"),
        "margin_delta_usd": format(margin_delta_usd, "f"),
        "capital_source_usage": list(capital_source_usage),
        "incremental_pnl_attribution_usd": format(
            incremental_pnl_attribution_usd,
            "f",
        ),
        "reason_distribution": {reason: 1},
        "reason": reason,
    }


def evaluate_universal_capital_science(
    context: UniversalCapitalScienceContext,
) -> tuple[dict[str, Any], ...]:
    """Evaluate the complete GEN-C surface without Trader/symbol predicates."""

    if not isinstance(context, UniversalCapitalScienceContext):
        raise CiboCapitalManagementError(
            "universal GEN-C evaluation requires canonical context"
        )
    specs = {item.code: item for item in GENC_REGISTRY}
    rows: list[dict[str, Any]] = []

    admitted = context.realized_profit_settlement_count
    rows.append(
        _row(
            specs["GEN-C1"],
            disposition=(
                CapitalScienceDisposition.APPLIED
                if admitted
                else CapitalScienceDisposition.FAIL_CLOSED
            ),
            eligible_epochs=context.epoch_count,
            invoked_count=context.epoch_count,
            applied_count=admitted,
            fail_closed_count=0 if admitted else context.epoch_count,
            not_applicable_count=0,
            decision_changed_count=admitted,
            capital_source_usage=("REALIZED_PROFIT",) if admitted else (),
            reason=(
                "causally realized positive settlements formed compound capital"
                if admitted
                else "no causally realized positive settlement was available"
            ),
        )
    )

    rows.append(
        _row(
            specs["GEN-C2"],
            disposition=CapitalScienceDisposition.ELIGIBLE_NO_CHANGE,
            eligible_epochs=admitted,
            invoked_count=admitted,
            applied_count=0,
            fail_closed_count=0,
            not_applicable_count=0,
            decision_changed_count=0,
            capital_source_usage=("REALIZED_PROFIT",) if admitted else (),
            reason=(
                "protected-floor graduation engine is universally addressable; "
                "this compound replay observes eligibility but does not mutate "
                "the protected floor without its dedicated causal graduation gate"
            ),
        )
    )

    portfolio_applied = (
        context.compound_settlement_count if context.account_pool_enabled else 0
    )
    rows.append(
        _row(
            specs["GEN-C3"],
            disposition=(
                CapitalScienceDisposition.APPLIED
                if portfolio_applied
                else (
                    CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
                    if not context.account_pool_enabled
                    else CapitalScienceDisposition.FAIL_CLOSED
                )
            ),
            eligible_epochs=(
                context.selected_count if context.account_pool_enabled else 0
            ),
            invoked_count=(
                context.selected_count if context.account_pool_enabled else 0
            ),
            applied_count=portfolio_applied,
            fail_closed_count=(
                context.compound_rejected_count
                if context.account_pool_enabled
                else 0
            ),
            not_applicable_count=(
                context.selected_count if not context.account_pool_enabled else 0
            ),
            decision_changed_count=context.cross_trader_deployment_count,
            capital_source_usage=(
                ("REALIZED_PROFIT", "TRUE_PORTFOLIO_NETTING")
                if portfolio_applied
                else ()
            ),
            incremental_pnl_attribution_usd=(
                context.compound_incremental_pnl_usd
                if context.account_pool_enabled
                else Decimal(0)
            ),
            reason=(
                "account-local pool executed universal cross-Trader compound allocation"
                if portfolio_applied
                else (
                    "Trader-local counterfactual intentionally disables account pooling"
                    if not context.account_pool_enabled
                    else "portfolio compound had no legally executable deployment"
                )
            ),
        )
    )

    rows.append(
        _row(
            specs["GEN-C4"],
            disposition=(
                CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
                if context.rational_redeploy_gate_enabled
                else CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
            ),
            eligible_epochs=context.selected_count,
            invoked_count=(
                context.selected_count
                if context.rational_redeploy_gate_enabled
                else 0
            ),
            applied_count=0,
            fail_closed_count=0,
            not_applicable_count=(
                0
                if context.rational_redeploy_gate_enabled
                else context.selected_count
            ),
            decision_changed_count=0,
            reason=(
                "marginal-capital utility contract is universally consulted "
                "through the rational redeploy boundary; no identity filter exists"
                if context.rational_redeploy_gate_enabled
                else "this lane did not request marginal-utility admission"
            ),
        )
    )

    rows.append(
        _row(
            specs["GEN-C5"],
            disposition=(
                CapitalScienceDisposition.APPLIED
                if context.compound_settlement_count
                else CapitalScienceDisposition.FAIL_CLOSED
            ),
            eligible_epochs=context.selected_count,
            invoked_count=context.selected_count,
            applied_count=context.compound_settlement_count,
            fail_closed_count=context.compound_rejected_count,
            not_applicable_count=0,
            decision_changed_count=context.compound_settlement_count,
            risk_delta_usd=context.total_compound_risk_usd,
            margin_delta_usd=context.total_compound_margin_usd,
            capital_source_usage=(
                ("REALIZED_PROFIT",)
                if context.compound_settlement_count
                else ()
            ),
            incremental_pnl_attribution_usd=context.compound_incremental_pnl_usd,
            reason=(
                "causally prior realized profit funded later universal seeds"
                if context.compound_settlement_count
                else "no later opportunity survived the compound gates"
            ),
        )
    )

    rows.append(
        _row(
            specs["GEN-C6"],
            disposition=CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE,
            eligible_epochs=0,
            invoked_count=0,
            applied_count=0,
            fail_closed_count=0,
            not_applicable_count=context.selected_count,
            decision_changed_count=0,
            reason=(
                "fixed Core-selection ablation does not replace selection with "
                "an internal scarcity auction; engine remains universally addressable"
            ),
        )
    )

    preservation_invoked = context.compound_settlement_count
    rows.append(
        _row(
            specs["GEN-C7"],
            disposition=(
                CapitalScienceDisposition.APPLIED
                if preservation_invoked
                else CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
            ),
            eligible_epochs=context.selected_count,
            invoked_count=preservation_invoked,
            applied_count=preservation_invoked,
            fail_closed_count=0,
            not_applicable_count=0,
            decision_changed_count=preservation_invoked,
            capital_source_usage=("PROTECTED_ECONOMIC_FLOOR",)
            if preservation_invoked
            else (),
            reason=(
                "protected loss reserve constrained every executed compound seed"
                if preservation_invoked
                else "no compound seed reached the preservation stage"
            ),
        )
    )

    # GEN-C8..C14 exist as universal engines, but the fixed-leverage burned
    # research lane must not pretend that shadow/governance engines mutated the
    # economic decision when their dedicated causal inputs are absent.
    advanced_reasons = {
        "GEN-C8": (
            "fixed leverage sweep intentionally disables adaptive-speed mutation; "
            "universal adaptive-speed engine remains available for a dedicated run"
        ),
        "GEN-C9": (
            "QORE Risk remains the hard bound; robust-growth/ruin engine requires "
            "its dedicated calibrated growth state before it may alter capital"
        ),
        "GEN-C10": (
            "digital-twin engine requires a declared scenario/twin state; this "
            "historical replay does not fabricate one"
        ),
        "GEN-C11": (
            "multi-period MPC requires a declared horizon/state forecast; this "
            "single-decision replay does not synthesize future capital arrivals"
        ),
        "GEN-C12": (
            "crisis engine requires a causal crisis/tail state; no identity-based "
            "asset exception is substituted when that state is absent"
        ),
        "GEN-C13": (
            "meta-capital memory is research/governance state and cannot consume "
            "the current outcome to alter the same decision"
        ),
        "GEN-C14": (
            "governed capital science may generate/falsify future hypotheses but "
            "cannot self-promote or mutate the current control during this replay"
        ),
    }
    for code in ("GEN-C8", "GEN-C9", "GEN-C10", "GEN-C11", "GEN-C12", "GEN-C13", "GEN-C14"):
        rows.append(
            _row(
                specs[code],
                disposition=CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE,
                eligible_epochs=context.epoch_count,
                invoked_count=0,
                applied_count=0,
                fail_closed_count=0,
                not_applicable_count=context.epoch_count,
                decision_changed_count=0,
                reason=advanced_reasons[code],
            )
        )

    if tuple(row["function_code"] for row in rows) != tuple(
        item.code for item in GENC_REGISTRY
    ):
        raise CiboCapitalManagementError(
            "universal GEN-C registry lost canonical ordering"
        )
    if any(row["status"] == "NOT_INTEGRATED" for row in rows):
        raise CiboCapitalManagementError(
            "universal GEN-C registry may never emit NOT_INTEGRATED"
        )
    if any(row["identity_predicate_used"] for row in rows):
        raise CiboCapitalManagementError(
            "universal GEN-C registry forbids identity predicates"
        )
    return tuple(rows)
