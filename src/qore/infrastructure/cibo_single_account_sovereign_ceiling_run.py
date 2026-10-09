"""Canonical receipt for one continuous CIBO sovereign ceiling-discovery run.

This module is downstream of the real Native MAX sovereign runtime and QORE
Risk. It cannot invent decisions. It converts real runtime/Risk outputs plus
post-decision settlement evidence into the exact non-certifying receipt consumed
by the CEILING_DISCOVERY assembler.

The receipt preserves one USD60 account, forbids resets/leakage/target tuning,
and requires causal ablations for Sizing, Adaptive Leverage, CIBO Compound,
Compound Portfolio and Cognition.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.account_wide_risk import (
    RiskAuthorization,
    RiskDecision,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ceiling_discovery import CiboCeilingLimitKind
from qore.infrastructure.cibo_cognitive_reach_sensors import (
    CiboCognitiveReachSensor,
    build_native_cognitive_reach_sensors,
    summarize_cognitive_reach_sensors,
)
from qore.infrastructure.cibo_function_economic_sensors import (
    CiboFunctionEconomicSensor,
    build_sovereign_function_sensors,
    summarize_function_sensors,
)
from qore.infrastructure.cibo_native_mode_authority import NativeSovereignModeInstruction
from qore.infrastructure.cibo_native_sovereign_capital_runtime import (
    CiboNativeSovereignCapitalDecision,
)
from qore.infrastructure.cibo_single_account_maximum_capability import (
    CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD,
)

_SCHEMA = "qore.cibo.single-account-sovereign-ceiling-run.v1"
_NOT_REQUESTED = "NOT_REQUESTED"
_MANDATORY_ABLATIONS = (
    "sizing",
    "adaptive_leverage",
    "cibo_compound",
    "compound_portfolio",
    "cognition",
)


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"sovereign ceiling {name} must be timezone-aware"
        )


def _money(
    value: Decimal,
    name: str,
    *,
    nonnegative: bool = True,
) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(
            f"sovereign ceiling {name} must be finite Decimal"
        )
    if nonnegative and value < 0:
        raise CiboCapitalManagementError(
            f"sovereign ceiling {name} must be non-negative"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
    ):
        raise CiboCapitalManagementError(
            f"sovereign ceiling {name} must be sha256 digest"
        )


@dataclass(frozen=True, slots=True)
class CiboSovereignCeilingDecisionReceipt:
    decision_epoch_id: str
    decision_id: str
    option_id: str
    signal_fingerprint: str
    trader_id: str
    decided_at: datetime
    capital_disposition: str
    risk_decision: str
    requested_volume: Decimal
    authorized_volume: Decimal
    requested_stop_risk_usd: Decimal
    authorized_stop_risk_usd: Decimal
    authorized_margin_usd: Decimal
    adaptive_leverage_multiplier: int
    sizing_mode: str
    semantic_digest: str
    native_mpc_derived_from_cognition: bool
    function_sensors: tuple[CiboFunctionEconomicSensor, ...] = ()
    cognitive_sensors: tuple[CiboCognitiveReachSensor, ...] = ()
    native_mode_instruction: NativeSovereignModeInstruction | None = None
    native_maximum_intelligence: bool = True
    sovereign_runtime_evaluated: bool = True
    full_semantics_consumed: bool = True
    external_ai_call_count: int = 0
    outcome_used_for_predecision: bool = False

    def __post_init__(self) -> None:
        for name in (
            "decision_epoch_id",
            "decision_id",
            "option_id",
            "signal_fingerprint",
            "trader_id",
            "capital_disposition",
            "risk_decision",
            "sizing_mode",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise CiboCapitalManagementError(
                    f"sovereign ceiling decision {name} is required"
                )
        _aware(self.decided_at, "decision decided_at")
        for name in (
            "requested_volume",
            "authorized_volume",
            "requested_stop_risk_usd",
            "authorized_stop_risk_usd",
            "authorized_margin_usd",
        ):
            _money(getattr(self, name), name)
        _sha(self.semantic_digest, "semantic_digest")
        if (
            not isinstance(self.adaptive_leverage_multiplier, int)
            or isinstance(self.adaptive_leverage_multiplier, bool)
            or self.adaptive_leverage_multiplier < 0
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling leverage multiplier must be non-negative"
            )
        if self.risk_decision not in {
            _NOT_REQUESTED,
            RiskDecision.ALLOW.value,
            RiskDecision.REDUCE.value,
            RiskDecision.REJECT.value,
        }:
            raise CiboCapitalManagementError(
                "sovereign ceiling risk decision invalid"
            )
        bool_fields = (
            "native_mpc_derived_from_cognition",
            "native_maximum_intelligence",
            "sovereign_runtime_evaluated",
            "full_semantics_consumed",
            "outcome_used_for_predecision",
        )
        if any(type(getattr(self, name)) is not bool for name in bool_fields):
            raise CiboCapitalManagementError(
                "sovereign ceiling decision boolean evidence malformed"
            )
        if (
            not self.native_maximum_intelligence
            or not self.sovereign_runtime_evaluated
            or not self.full_semantics_consumed
            or self.external_ai_call_count != 0
            or self.outcome_used_for_predecision
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling decision violates Native MAX governance"
            )
        if (
            not isinstance(self.external_ai_call_count, int)
            or isinstance(self.external_ai_call_count, bool)
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling external AI count must be int"
            )
        if any(
            not isinstance(item, CiboFunctionEconomicSensor)
            for item in self.function_sensors
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling function sensor receipt invalid"
            )
        sensor_codes = tuple(
            item.function_code for item in self.function_sensors
        )
        if len(sensor_codes) != len(set(sensor_codes)):
            raise CiboCapitalManagementError(
                "sovereign ceiling duplicate function sensor code"
            )
        if any(
            item.decision_id != self.decision_id
            or item.productive_authority
            for item in self.function_sensors
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling function sensor lineage/authority drift"
            )
        if any(
            not isinstance(item, CiboCognitiveReachSensor)
            for item in self.cognitive_sensors
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling cognitive sensor receipt invalid"
            )
        if self.native_mode_instruction is not None:
            instruction = self.native_mode_instruction
            if (not isinstance(instruction, NativeSovereignModeInstruction)
                or instruction.signal_fingerprint != self.signal_fingerprint
                or instruction.trader_id != self.trader_id
                or instruction.semantic_digest != self.semantic_digest
                or instruction.decided_at != self.decided_at
                or instruction.broker_execution_authorized):
                raise CiboCapitalManagementError(
                    "sovereign Native MAX management instruction identity/provenance drift"
                )
        cognitive_codes = tuple(
            item.component_code for item in self.cognitive_sensors
        )
        if len(cognitive_codes) != len(set(cognitive_codes)):
            raise CiboCapitalManagementError(
                "sovereign ceiling duplicate cognitive sensor code"
            )
        if any(
            item.decision_id != self.decision_id
            or item.productive_authority
            for item in self.cognitive_sensors
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling cognitive sensor lineage/authority drift"
            )

        if self.risk_decision == _NOT_REQUESTED:
            if any(
                value != 0
                for value in (
                    self.requested_volume,
                    self.authorized_volume,
                    self.requested_stop_risk_usd,
                    self.authorized_stop_risk_usd,
                    self.authorized_margin_usd,
                )
            ):
                raise CiboCapitalManagementError(
                    "non-Risk decision cannot carry requested/authorized capital"
                )
        elif self.risk_decision == RiskDecision.REJECT.value:
            if self.requested_volume <= 0 or self.requested_stop_risk_usd <= 0:
                raise CiboCapitalManagementError(
                    "Risk reject requires a positive CIBO request"
                )
            if (
                self.authorized_volume != 0
                or self.authorized_stop_risk_usd != 0
                or self.authorized_margin_usd != 0
            ):
                raise CiboCapitalManagementError(
                    "Risk reject cannot authorize capital"
                )
        else:
            if (
                self.requested_volume <= 0
                or self.authorized_volume <= 0
                or self.requested_stop_risk_usd <= 0
                or self.authorized_stop_risk_usd <= 0
                or self.authorized_margin_usd <= 0
            ):
                raise CiboCapitalManagementError(
                    "Risk allow/reduce requires positive capital"
                )
            if self.authorized_volume > self.requested_volume:
                raise CiboCapitalManagementError(
                    "Risk cannot authorize more than CIBO requested"
                )
            if (
                self.risk_decision == RiskDecision.ALLOW.value
                and self.authorized_volume != self.requested_volume
            ):
                raise CiboCapitalManagementError(
                    "Risk ALLOW must preserve requested volume"
                )
            if (
                self.risk_decision == RiskDecision.REDUCE.value
                and self.authorized_volume >= self.requested_volume
            ):
                raise CiboCapitalManagementError(
                    "Risk REDUCE must lower requested volume"
                )


@dataclass(frozen=True, slots=True)
class CiboSovereignCeilingSettlementReceipt:
    signal_fingerprint: str
    trader_id: str
    settled_at: datetime
    realized_net_pnl_usd: Decimal
    settlement_sha256: str
    outcome_available_to_predecision: bool = False

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.trader_id:
            raise CiboCapitalManagementError(
                "sovereign ceiling settlement identity is required"
            )
        _aware(self.settled_at, "settlement settled_at")
        _money(
            self.realized_net_pnl_usd,
            "realized_net_pnl_usd",
            nonnegative=False,
        )
        _sha(self.settlement_sha256, "settlement_sha256")
        if (
            type(self.outcome_available_to_predecision) is not bool
            or self.outcome_available_to_predecision
        ):
            raise CiboCapitalManagementError(
                "settlement outcome cannot be available to predecision"
            )


@dataclass(frozen=True, slots=True)
class CiboCeilingAblationReceipt:
    name: str
    ending_capital_usd: Decimal
    maximum_drawdown_usd: Decimal
    executed: bool = True
    outcome_aware_tuning: bool = False

    def __post_init__(self) -> None:
        if self.name not in _MANDATORY_ABLATIONS:
            raise CiboCapitalManagementError(
                "sovereign ceiling ablation name is invalid"
            )
        _money(self.ending_capital_usd, "ablation ending_capital_usd")
        _money(self.maximum_drawdown_usd, "ablation maximum_drawdown_usd")
        if (
            type(self.executed) is not bool
            or type(self.outcome_aware_tuning) is not bool
            or not self.executed
            or self.outcome_aware_tuning
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling ablation must execute causally"
            )


def decision_receipt_from_native_runtime(
    *,
    decision_epoch_id: str,
    decided_at: datetime,
    opportunity: TraderOpportunityEnvelope,
    native_decision: CiboNativeSovereignCapitalDecision,
    risk_authorization: RiskAuthorization | None,
) -> CiboSovereignCeilingDecisionReceipt:
    """Bind a real Native MAX sovereign decision to its QORE Risk result."""

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "ceiling receipt requires canonical Trader opportunity"
        )
    if not isinstance(
        native_decision,
        CiboNativeSovereignCapitalDecision,
    ):
        raise CiboCapitalManagementError(
            "ceiling receipt requires Native MAX sovereign decision"
        )
    _aware(decided_at, "decision decided_at")
    intelligence = native_decision.intelligence
    capital = native_decision.capital

    if capital.final_plan.trader_id != opportunity.trader_id:
        raise CiboCapitalManagementError(
            "ceiling receipt runtime/opportunity trader drift"
        )

    target_lines = tuple(
        item
        for item in capital.economic_run.portfolio_plan.lines
        if item.option_id == capital.option_id
    )
    if len(target_lines) != 1:
        raise CiboCapitalManagementError(
            "ceiling receipt target missing from portfolio allocation"
        )
    multiplier = target_lines[0].multiplier
    request = capital.risk_request

    if request is None:
        if risk_authorization is not None:
            raise CiboCapitalManagementError(
                "ceiling receipt cannot attach Risk authorization without request"
            )
        risk_decision = _NOT_REQUESTED
        requested_volume = Decimal(0)
        requested_risk = Decimal(0)
        authorized_volume = Decimal(0)
        authorized_risk = Decimal(0)
        authorized_margin = Decimal(0)
    else:
        if risk_authorization is None:
            raise CiboCapitalManagementError(
                "ceiling receipt requires QORE Risk authorization for request"
            )
        if (
            request.signal_fingerprint != opportunity.signal_fingerprint
            or request.trader_id != opportunity.trader_id
            or risk_authorization.request_id != request.request_id
            or risk_authorization.signal_fingerprint
            != request.signal_fingerprint
            or risk_authorization.trader_id != request.trader_id
        ):
            raise CiboCapitalManagementError(
                "ceiling receipt Risk request/authorization lineage drift"
            )
        risk_decision = risk_authorization.decision.value
        requested_volume = request.requested_volume
        requested_risk = request.requested_stop_risk
        authorized_volume = risk_authorization.authorized_volume
        authorized_risk = risk_authorization.monetary_stop_loss
        authorized_margin = risk_authorization.margin_reserved

    return CiboSovereignCeilingDecisionReceipt(
        decision_epoch_id=decision_epoch_id,
        decision_id=capital.decision_id,
        option_id=capital.option_id,
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id.value,
        decided_at=decided_at,
        capital_disposition=capital.disposition.value,
        risk_decision=risk_decision,
        requested_volume=requested_volume,
        authorized_volume=authorized_volume,
        requested_stop_risk_usd=requested_risk,
        authorized_stop_risk_usd=authorized_risk,
        authorized_margin_usd=authorized_margin,
        adaptive_leverage_multiplier=multiplier,
        sizing_mode=capital.sizing.mode.value,
        semantic_digest=intelligence.semantic_digest,
        native_mpc_derived_from_cognition=(
            native_decision.native_mpc_derived_from_cognition
        ),
        function_sensors=build_sovereign_function_sensors(capital),
        cognitive_sensors=build_native_cognitive_reach_sensors(
            native_decision
        ),
        native_mode_instruction=native_decision.native_qdle_mode_instruction,
        native_maximum_intelligence=True,
        sovereign_runtime_evaluated=True,
        full_semantics_consumed=(
            intelligence.applicable_faculty_count
            + intelligence.not_applicable_faculty_count
            == 19
        ),
        external_ai_call_count=intelligence.external_ai_call_count,
        outcome_used_for_predecision=False,
    )


def build_single_account_sovereign_ceiling_run(
    *,
    source_manifest_sha256: str,
    decision_count: int,
    decisions: tuple[CiboSovereignCeilingDecisionReceipt, ...],
    settlements: tuple[CiboSovereignCeilingSettlementReceipt, ...],
    ablations: tuple[CiboCeilingAblationReceipt, ...],
    population_exhausted: bool,
    growth_capacity_remaining_at_population_end: bool,
    intrinsic_ceiling_claimed: bool,
    observed_lower_bound_only: bool,
    limiting_factor: CiboCeilingLimitKind,
) -> dict[str, Any]:
    """Build the authoritative single-account ceiling-run receipt."""

    _sha(source_manifest_sha256, "source_manifest_sha256")
    if (
        not isinstance(decision_count, int)
        or isinstance(decision_count, bool)
        or decision_count <= 0
    ):
        raise CiboCapitalManagementError(
            "sovereign ceiling decision_count must be positive int"
        )
    if len(decisions) != decision_count:
        raise CiboCapitalManagementError(
            "sovereign ceiling requires one runtime receipt per decision"
        )
    if any(
        not isinstance(item, CiboSovereignCeilingDecisionReceipt)
        for item in decisions
    ):
        raise CiboCapitalManagementError(
            "sovereign ceiling decision receipts must be canonical"
        )
    if any(
        not isinstance(item, CiboSovereignCeilingSettlementReceipt)
        for item in settlements
    ):
        raise CiboCapitalManagementError(
            "sovereign ceiling settlement receipts must be canonical"
        )
    for name, value in (
        ("population_exhausted", population_exhausted),
        (
            "growth_capacity_remaining_at_population_end",
            growth_capacity_remaining_at_population_end,
        ),
        ("intrinsic_ceiling_claimed", intrinsic_ceiling_claimed),
        ("observed_lower_bound_only", observed_lower_bound_only),
    ):
        if type(value) is not bool:
            raise CiboCapitalManagementError(
                f"sovereign ceiling {name} must be bool"
            )
    if type(limiting_factor) is not CiboCeilingLimitKind:
        raise CiboCapitalManagementError(
            "sovereign ceiling limiting_factor must be canonical"
        )

    signals = tuple(item.signal_fingerprint for item in decisions)
    if len(signals) != len(set(signals)):
        raise CiboCapitalManagementError(
            "sovereign ceiling duplicate decision signal"
        )
    decided_at = {
        item.signal_fingerprint: item.decided_at for item in decisions
    }
    authorized = {
        item.signal_fingerprint
        for item in decisions
        if item.risk_decision
        in {RiskDecision.ALLOW.value, RiskDecision.REDUCE.value}
    }

    settlement_signals = tuple(item.signal_fingerprint for item in settlements)
    if len(settlement_signals) != len(set(settlement_signals)):
        raise CiboCapitalManagementError(
            "sovereign ceiling duplicate settlement"
        )
    if not set(settlement_signals).issubset(authorized):
        raise CiboCapitalManagementError(
            "sovereign ceiling settlement lacks Risk-authorized selection"
        )
    for item in settlements:
        if item.settled_at < decided_at[item.signal_fingerprint]:
            raise CiboCapitalManagementError(
                "sovereign ceiling settlement predates decision"
            )

    ablation_by_name = {item.name: item for item in ablations}
    if (
        len(ablation_by_name) != len(ablations)
        or set(ablation_by_name) != set(_MANDATORY_ABLATIONS)
    ):
        raise CiboCapitalManagementError(
            "sovereign ceiling requires exact mandatory ablation set"
        )

    capital = CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD
    peak = capital
    maximum_drawdown = Decimal(0)
    by_trader: dict[str, Decimal] = {}
    for settlement in sorted(
        settlements,
        key=lambda item: (item.settled_at, item.signal_fingerprint),
    ):
        capital += settlement.realized_net_pnl_usd
        if capital < 0:
            raise CiboCapitalManagementError(
                "sovereign ceiling capital cannot settle below zero"
            )
        peak = max(peak, capital)
        maximum_drawdown = max(maximum_drawdown, peak - capital)
        by_trader[settlement.trader_id] = (
            by_trader.get(settlement.trader_id, Decimal(0))
            + settlement.realized_net_pnl_usd
        )

    risk_counts = {
        name: sum(1 for item in decisions if item.risk_decision == name)
        for name in (
            _NOT_REQUESTED,
            RiskDecision.ALLOW.value,
            RiskDecision.REDUCE.value,
            RiskDecision.REJECT.value,
        )
    }
    leverage_counts = {
        str(multiplier): sum(
            1
            for item in decisions
            if item.adaptive_leverage_multiplier == multiplier
        )
        for multiplier in range(5)
    }
    function_sensors = tuple(
        sensor
        for decision in decisions
        for sensor in decision.function_sensors
    )
    function_sensor_summary = summarize_function_sensors(
        function_sensors,
        full_ending_capital_usd=capital,
        ablation_ending_capital_usd={
            name: item.ending_capital_usd
            for name, item in ablation_by_name.items()
        },
    )
    cognitive_sensors = tuple(
        sensor
        for decision in decisions
        for sensor in decision.cognitive_sensors
    )
    cognitive_sensor_summary = summarize_cognitive_reach_sensors(
        cognitive_sensors,
        full_ending_capital_usd=capital,
        global_cognition_ablation_ending_capital_usd=(
            ablation_by_name["cognition"].ending_capital_usd
        ),
    )

    return {
        "schema": _SCHEMA,
        "source_manifest_sha256": source_manifest_sha256,
        "decision_count": decision_count,
        "sovereign_runtime_evaluation_count": sum(
            item.sovereign_runtime_evaluated for item in decisions
        ),
        "full_semantic_decision_count": sum(
            item.full_semantics_consumed for item in decisions
        ),
        "native_max_decision_count": sum(
            item.native_maximum_intelligence for item in decisions
        ),
        "external_ai_call_count": sum(
            item.external_ai_call_count for item in decisions
        ),
        "account_reset_count": 0,
        "economic_era_reset_count": 0,
        "initial_capital_usd": format(
            CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD,
            "f",
        ),
        "ending_capital_usd": format(capital, "f"),
        "peak_capital_usd": format(peak, "f"),
        "net_pnl_usd": format(
            capital - CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD,
            "f",
        ),
        "maximum_drawdown_usd": format(maximum_drawdown, "f"),
        "native_sovereign_runtime_used": True,
        "qore_risk_sovereign": True,
        "outcome_used_for_predecision": False,
        "target_capital_used_for_tuning": False,
        "population_exhausted": population_exhausted,
        "growth_capacity_remaining_at_population_end": (
            growth_capacity_remaining_at_population_end
        ),
        "intrinsic_ceiling_claimed": intrinsic_ceiling_claimed,
        "observed_lower_bound_only": observed_lower_bound_only,
        "limiting_factor": limiting_factor.value,
        "risk_decision_counts": risk_counts,
        "adaptive_leverage_distribution": leverage_counts,
        "selected_count": len(authorized),
        "settled_count": len(settlements),
        "native_mpc_derived_decision_count": sum(
            item.native_mpc_derived_from_cognition for item in decisions
        ),
        "per_trader_realized_pnl_usd": {
            trader: format(value, "f")
            for trader, value in sorted(by_trader.items())
        },
        "function_economic_sensors": function_sensor_summary,
        "cognitive_reach_sensors": cognitive_sensor_summary,
        "ablations": {
            name: {
                "executed": True,
                "ending_capital_usd": format(
                    ablation_by_name[name].ending_capital_usd,
                    "f",
                ),
                "maximum_drawdown_usd": format(
                    ablation_by_name[name].maximum_drawdown_usd,
                    "f",
                ),
                "delta_ending_capital_vs_full_usd": format(
                    capital - ablation_by_name[name].ending_capital_usd,
                    "f",
                ),
            }
            for name in _MANDATORY_ABLATIONS
        },
        "governance": {
            "single_account": True,
            "initial_capital_usd": "60",
            "continuous_compound": True,
            "external_ai": False,
            "outcome_aware_tuning": False,
            "target_capital_tuning": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "certification_claimed": False,
        },
    }
