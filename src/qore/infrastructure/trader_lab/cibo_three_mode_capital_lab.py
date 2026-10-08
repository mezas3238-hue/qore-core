"""CIBO BANK / MEDIUM / ATTACK ceiling experiment for GitHub Trader Lab.

This module is deliberately isolated under Trader Lab. It does not mutate the
sovereign runtime, QORE Risk, broker state, LIVE state or certifying evidence.

Owner-defined economics:
- BANK is treasury only: it leaves a sovereign-backed working-capital seed
  envelope for MEDIUM and never owns a trade.
- MEDIUM is the joint Sizing + CIBO Compound engine. Sizing deploys only from
  the BANK seed envelope; CIBO Compound settles that MEDIUM production. The
  BANK seed is recycled and realized positive net profit is partitioned 50%
  to sovereign capital and 50% to the Compound Portfolio cushion.
- ATTACK is available only in healthy causal conditions and only when the
  Compound Portfolio cushion can fully fund at least 2x executable stop-risk
  plus provider cost. High leverage is paid exclusively from that cushion.

The experiment consumes outcome evidence only after each trade's exit time.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from enum import StrEnum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    minimum_seed_volume,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    cibo_new_capital_risk_utilization_ceiling,
)
from qore.infrastructure.cibo_single_account_manifest_economics import (
    manifest_row_provider_cost_per_volume_usd,
    manifest_row_to_ceiling_opportunity_evidence,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    validate_single_account_manifest_sha256,
)
from qore.infrastructure.cibo_protected_reinvestment_policy import (
    MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO,
)
from qore.infrastructure.cibo_position_lifecycle import CiboLifecycleEvent
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    manifest_row_to_shadow_outcome_observation,
)

INITIAL_CAPITAL_USD = Decimal("60")
MEDIUM_SOVEREIGN_SHARE = Decimal("0.50")
MEDIUM_CUSHION_SHARE = Decimal("0.50")
ATTACK_MINIMUM_MULTIPLIER = 2
MARGIN_CAPACITY_MULTIPLE = Decimal("100")
SOVEREIGN_DEFENSIVE_DRAWDOWN = Decimal("0.50")
ATTACK_TOTAL_DRAWDOWN_GUARD = Decimal("0.20")
ATTACK_PORTFOLIO_DRAWDOWN_BUDGET = Decimal("0.20")
MEDIUM_RECOMMEND_RISK_FRACTION = Decimal("0.04")
MEDIUM_DEFENSIVE_RISK_FRACTION = Decimal("0.01")
ECONOMIC_DRAWDOWN_CEILING = Decimal("0.25")
DISTRIBUTED_ATTACK_MIN_POSITIVE_BLOCKS = 4
DEFAULT_DISTRIBUTED_ATTACK_MULTIPLIER_CAP = 8


class CiboTraderLabMode(StrEnum):
    BANK = "BANK"
    MEDIUM = "MEDIUM"
    ATTACK = "ATTACK"


@dataclass(frozen=True, slots=True)
class CiboTraderLabRegime:
    liquidity: LiquidityState
    volatility: VolatilityState
    correlation: CorrelationState
    provider_condition: ProviderCondition
    position_path_adverse: bool
    evidence_stale: bool


@dataclass(frozen=True, slots=True)
class CiboThreeModeCandidate:
    signal_fingerprint: str
    trader_id: str
    decision_at: datetime
    exit_at: datetime
    gross_r: Decimal
    expected_edge_after_cost_usd: Decimal
    expected_net_utility_usd: Decimal
    attack_expected_net_utility_usd: Decimal
    expected_capital_minutes: Decimal
    walk_forward_positive_block_count: int
    walk_forward_nonpositive_block_count: int
    walk_forward_expected_structural_r: Decimal | None
    walk_forward_block_dispersion_r: Decimal
    planned_target_r: Decimal
    market_regime_posture: str
    h1_range_state: str | None
    h4_range_state: str | None
    native_cognition_recommended: bool | None
    context_quality_disposition: str
    minimum_volume: Decimal
    maximum_multiplier: int
    stop_risk_per_multiplier_usd: Decimal
    margin_per_multiplier_usd: Decimal
    provider_cost_per_multiplier_usd: Decimal
    context_allowed: bool

    @property
    def capital_time_score(self) -> Decimal:
        if self.expected_capital_minutes <= 0:
            return Decimal("-Infinity")
        with localcontext() as context:
            context.prec = 100
            return (
                self.expected_edge_after_cost_usd
                / self.expected_capital_minutes
            )

    @property
    def source_cost_per_multiplier_usd(self) -> Decimal:
        return (
            self.stop_risk_per_multiplier_usd
            + self.provider_cost_per_multiplier_usd
        )


@dataclass(frozen=True, slots=True)
class CiboThreeModeOpenTrade:
    signal_fingerprint: str
    trader_id: str
    mode: CiboTraderLabMode
    multiplier: int
    exit_at: datetime
    gross_r: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    provider_cost_usd: Decimal
    source_reserved_usd: Decimal
    bank_seed_usd: Decimal | None = None
    lifecycle_events: tuple[CiboLifecycleEvent, ...] = ()
    lifecycle_event_index: int = 0
    lifecycle_risk_fraction_remaining: Decimal = Decimal(1)
    lifecycle_margin_fraction_remaining: Decimal = Decimal(1)


@dataclass(slots=True)
class _State:
    sovereign_bank_usd: Decimal = INITIAL_CAPITAL_USD
    portfolio_cushion_usd: Decimal = Decimal(0)
    sovereign_reserved_usd: Decimal = Decimal(0)
    bank_seed_reserved_usd: Decimal = Decimal(0)
    bank_seed_issuance_count: int = 0
    bank_seed_issued_total_usd: Decimal = Decimal(0)
    bank_seed_recycled_total_usd: Decimal = Decimal(0)
    cushion_reserved_usd: Decimal = Decimal(0)
    portfolio_attack_credit_usd: Decimal = Decimal(0)
    portfolio_attack_credit_recycled_total_usd: Decimal = Decimal(0)
    open_stop_risk_usd: Decimal = Decimal(0)
    open_margin_usd: Decimal = Decimal(0)
    peak_total_capital_usd: Decimal = INITIAL_CAPITAL_USD
    peak_sovereign_bank_usd: Decimal = INITIAL_CAPITAL_USD
    max_drawdown_usd: Decimal = Decimal(0)
    max_drawdown_fraction_observed: Decimal = Decimal(0)
    max_sovereign_drawdown_usd: Decimal = Decimal(0)
    min_sovereign_bank_usd: Decimal = INITIAL_CAPITAL_USD
    sovereign_floor_breach_usd: Decimal = Decimal(0)
    cushion_high_watermark_usd: Decimal = Decimal(0)
    attack_sovereign_breach_usd: Decimal = Decimal(0)
    medium_profit_to_sovereign_usd: Decimal = Decimal(0)
    medium_profit_to_cushion_usd: Decimal = Decimal(0)
    medium_compound_positive_net_usd: Decimal = Decimal(0)
    medium_compound_negative_net_usd: Decimal = Decimal(0)
    medium_compound_turnover_usd: Decimal = Decimal(0)
    medium_compound_recovery_deficit_usd: Decimal = Decimal(0)
    medium_compound_recovered_usd: Decimal = Decimal(0)
    attack_net_pnl_usd: Decimal = Decimal(0)
    attack_profit_to_sovereign_usd: Decimal = Decimal(0)
    attack_profit_to_cushion_usd: Decimal = Decimal(0)

    @property
    def total_capital_usd(self) -> Decimal:
        return self.sovereign_bank_usd + self.portfolio_cushion_usd

    @property
    def sovereign_available_usd(self) -> Decimal:
        return max(
            Decimal(0),
            self.sovereign_bank_usd - self.sovereign_reserved_usd,
        )

    @property
    def cushion_available_usd(self) -> Decimal:
        return max(
            Decimal(0),
            self.portfolio_cushion_usd - self.cushion_reserved_usd,
        )

    @property
    def attack_credit_available_usd(self) -> Decimal:
        return max(
            Decimal(0),
            min(
                self.portfolio_attack_credit_usd,
                self.cushion_available_usd,
            ),
        )

    @property
    def sovereign_protection_floor_usd(self) -> Decimal:
        with localcontext() as context:
            context.prec = 100
            return (
                self.peak_sovereign_bank_usd
                * (Decimal(1) - SOVEREIGN_DEFENSIVE_DRAWDOWN)
            )

    @property
    def sovereign_risk_budget_available_usd(self) -> Decimal:
        return max(
            Decimal(0),
            self.sovereign_available_usd
            - self.sovereign_protection_floor_usd,
        )

    def mark(self) -> None:
        total = self.total_capital_usd
        self.peak_total_capital_usd = max(self.peak_total_capital_usd, total)
        drawdown = max(Decimal(0), self.peak_total_capital_usd - total)
        self.max_drawdown_usd = max(self.max_drawdown_usd, drawdown)
        current_drawdown_fraction = _ratio(
            drawdown,
            self.peak_total_capital_usd,
        )
        self.max_drawdown_fraction_observed = max(
            self.max_drawdown_fraction_observed,
            current_drawdown_fraction,
        )
        floor_before_mark = self.sovereign_protection_floor_usd
        if self.sovereign_bank_usd < floor_before_mark:
            self.sovereign_floor_breach_usd = max(
                self.sovereign_floor_breach_usd,
                floor_before_mark - self.sovereign_bank_usd,
            )
        self.peak_sovereign_bank_usd = max(
            self.peak_sovereign_bank_usd,
            self.sovereign_bank_usd,
        )
        sovereign_drawdown = max(
            Decimal(0),
            self.peak_sovereign_bank_usd - self.sovereign_bank_usd,
        )
        self.max_sovereign_drawdown_usd = max(
            self.max_sovereign_drawdown_usd,
            sovereign_drawdown,
        )
        self.min_sovereign_bank_usd = min(
            self.min_sovereign_bank_usd,
            self.sovereign_bank_usd,
        )
        self.cushion_high_watermark_usd = max(
            self.cushion_high_watermark_usd,
            self.portfolio_cushion_usd,
        )


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CiboCapitalManagementError(
            f"Trader Lab three-mode {name} must be mapping"
        )
    return value


def _dt(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(
            f"Trader Lab three-mode {name} must be string"
        )
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Trader Lab three-mode {name} must be timezone-aware"
        )
    return parsed


def _boolish(value: object, name: str) -> bool:
    if type(value) is bool:
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no", ""}:
            return False
    if value is None:
        return False
    raise CiboCapitalManagementError(
        f"Trader Lab three-mode {name} must be bool-compatible"
    )


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal(0) if numerator <= 0 else Decimal(1)
    with localcontext() as context:
        context.prec = 100
        return min(Decimal(1), max(Decimal(0), numerator / denominator))


def _regime_from_row(row: Mapping[str, Any]) -> CiboTraderLabRegime:
    ce2i = _mapping(
        row.get("ce2i_predecision_evidence"),
        "ce2i_predecision_evidence",
    )
    receipts = ce2i.get("runtime_receipts")
    if not isinstance(receipts, (list, tuple)):
        raise CiboCapitalManagementError(
            "Trader Lab three-mode regime receipts missing"
        )
    matches = tuple(
        item
        for item in receipts
        if isinstance(item, Mapping)
        and item.get("engine_name") == "select_ce2i_tools_for_regime"
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "Trader Lab three-mode requires exact CE2I regime receipt"
        )
    payload = _mapping(matches[0].get("input_payload"), "regime input_payload")
    return CiboTraderLabRegime(
        liquidity=LiquidityState(str(payload["liquidity"])),
        volatility=VolatilityState(str(payload["volatility"])),
        correlation=CorrelationState(str(payload["correlation"])),
        provider_condition=ProviderCondition(str(payload["provider_condition"])),
        position_path_adverse=_boolish(
            payload.get("position_path_adverse"),
            "position_path_adverse",
        ),
        evidence_stale=_boolish(payload.get("evidence_stale"), "evidence_stale"),
    )


def _candidate(
    row: Mapping[str, Any],
    *,
    native_cognition_recommended: bool | None,
    enforce_research_context_abstain: bool,
) -> CiboThreeModeCandidate:
    evidence = manifest_row_to_ceiling_opportunity_evidence(row)
    context_quality = _mapping(row.get("context_quality"), "context_quality")
    context_disposition = str(context_quality.get("disposition", ""))
    if context_disposition not in {"ALLOW", "ABSTAIN"}:
        raise CiboCapitalManagementError(
            "Trader Lab context-quality disposition is invalid"
        )
    if context_quality.get("causal_predecision") is not True:
        raise CiboCapitalManagementError(
            "Trader Lab context-quality evidence must be causal predecision"
        )
    if context_quality.get("outcome_used") is not False:
        raise CiboCapitalManagementError(
            "Trader Lab context-quality evidence cannot use outcome"
        )
    outcome = manifest_row_to_shadow_outcome_observation(row)
    opportunity = evidence.opportunity
    minimum = minimum_seed_volume(opportunity)
    expectation_payload = _mapping(row.get("expectation"), "expectation")
    raw_block_means = expectation_payload.get("walk_forward_block_means_r", ())
    if not isinstance(raw_block_means, (list, tuple)):
        raise CiboCapitalManagementError(
            "Trader Lab three-mode walk-forward block means malformed"
        )
    block_means = tuple(Decimal(str(value)) for value in raw_block_means)
    positive_blocks = int(
        expectation_payload.get("walk_forward_positive_block_count", 0)
    )
    nonpositive_blocks = int(
        expectation_payload.get("walk_forward_nonpositive_block_count", 0)
    )
    raw_expected_structural_r = expectation_payload.get(
        "walk_forward_expected_structural_r"
    )
    walk_forward_expected_structural_r = (
        None
        if raw_expected_structural_r is None
        else Decimal(str(raw_expected_structural_r))
    )
    walk_forward_block_dispersion_r = Decimal(
        str(expectation_payload.get("walk_forward_block_dispersion_r", "0"))
    )
    if (
        walk_forward_expected_structural_r is not None
        and not walk_forward_expected_structural_r.is_finite()
    ):
        raise CiboCapitalManagementError(
            "Trader Lab walk-forward expected structural R must be finite"
        )
    if (
        not walk_forward_block_dispersion_r.is_finite()
        or walk_forward_block_dispersion_r < 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab walk-forward block dispersion must be finite and nonnegative"
        )
    trader_opportunity = _mapping(
        row.get("trader_opportunity"),
        "trader_opportunity",
    )
    market_predecision_state = _mapping(
        row.get("market_predecision_state"),
        "market_predecision_state",
    )
    market_regime = _mapping(
        market_predecision_state.get("regime"),
        "market_predecision_state.regime",
    )
    market_regime_posture = str(market_regime.get("posture", ""))
    if market_regime_posture not in {"DEFENSIVE", "RECOVERY", "STABLE", "WATCH"}:
        raise CiboCapitalManagementError(
            "Trader Lab market regime posture is invalid"
        )
    raw_decision_context = trader_opportunity.get("decision_context", ())
    if not isinstance(raw_decision_context, (list, tuple)):
        raise CiboCapitalManagementError(
            "Trader Lab decision context must be a sequence"
        )
    decision_context = {
        str(item[0]): str(item[1])
        for item in raw_decision_context
        if isinstance(item, (list, tuple)) and len(item) == 2
    }
    h1_range_state = decision_context.get("reg_h1_range_state")
    h4_range_state = decision_context.get("reg_h4_range_state")
    intended_entry = Decimal(str(trader_opportunity.get("intended_entry")))
    stop_loss = Decimal(str(trader_opportunity.get("stop_loss")))
    take_profit = Decimal(str(trader_opportunity.get("take_profit")))
    if (
        not intended_entry.is_finite()
        or not stop_loss.is_finite()
        or not take_profit.is_finite()
        or intended_entry == stop_loss
    ):
        raise CiboCapitalManagementError(
            "Trader Lab planned target-R inputs must be finite with nonzero risk"
        )
    with localcontext() as context:
        context.prec = 100
        planned_target_r = (
            abs(take_profit - intended_entry)
            / abs(intended_entry - stop_loss)
        )
        stop = minimum * opportunity.stop_loss_per_volume
        margin = minimum * opportunity.margin_per_volume
        provider_cost = (
            minimum * manifest_row_provider_cost_per_volume_usd(row)
        )
        maximum_multiplier = int(
            (opportunity.maximum_volume / minimum).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        expected_after_cost = (
            evidence.expected_net_value_usd - provider_cost
        )
        expected_net = (
            expected_after_cost - evidence.uncertainty_penalty_usd
        )
        attack_expected_net = (
            min(block_means) * stop - provider_cost
            if len(block_means) == 5
            else Decimal("-1")
        )
    return CiboThreeModeCandidate(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id.value,
        decision_at=outcome.decision_at,
        exit_at=outcome.exit_at,
        gross_r=outcome.gross_structural_outcome_r,
        expected_edge_after_cost_usd=expected_after_cost,
        expected_net_utility_usd=expected_net,
        attack_expected_net_utility_usd=attack_expected_net,
        expected_capital_minutes=evidence.expected_capital_minutes,
        walk_forward_positive_block_count=positive_blocks,
        walk_forward_nonpositive_block_count=nonpositive_blocks,
        walk_forward_expected_structural_r=(
            walk_forward_expected_structural_r
        ),
        walk_forward_block_dispersion_r=walk_forward_block_dispersion_r,
        planned_target_r=planned_target_r,
        market_regime_posture=market_regime_posture,
        h1_range_state=h1_range_state,
        h4_range_state=h4_range_state,
        native_cognition_recommended=native_cognition_recommended,
        context_quality_disposition=context_disposition,
        minimum_volume=minimum,
        maximum_multiplier=max(0, maximum_multiplier),
        stop_risk_per_multiplier_usd=stop,
        margin_per_multiplier_usd=margin,
        provider_cost_per_multiplier_usd=provider_cost,
        context_allowed=(
            evidence.context_allowed
            and evidence.provider_viable
            and evidence.capital_source_eligible
            and native_cognition_recommended is not False
            and (
                context_disposition == "ALLOW"
                or not enforce_research_context_abstain
            )
        ),
    )


def _group_epochs(
    rows: list[Mapping[str, Any]],
) -> tuple[tuple[Mapping[str, Any], ...], ...]:
    grouped: dict[tuple[datetime, str], list[Mapping[str, Any]]] = defaultdict(
        list
    )
    for row in rows:
        decision_at = _dt(row.get("market_decision_at"), "market_decision_at")
        epoch_id = row.get("decision_epoch_id")
        if not isinstance(epoch_id, str) or not epoch_id:
            raise CiboCapitalManagementError(
                "Trader Lab three-mode decision_epoch_id is required"
            )
        grouped[(decision_at, epoch_id)].append(row)
    return tuple(
        tuple(
            sorted(
                epoch_rows,
                key=lambda row: (
                    str(row.get("trader_id")),
                    str(row.get("qore_symbol")),
                    str(row.get("signal_fingerprint")),
                ),
            )
        )
        for (_key, epoch_rows) in sorted(
            grouped.items(),
            key=lambda item: item[0],
        )
    )


def dynamic_bank_seed_budget_usd(
    current_total_capital_usd: Decimal,
) -> Decimal:
    """BANK seed budget for one MEDIUM entry: 4% of current account capital."""

    if (
        not isinstance(current_total_capital_usd, Decimal)
        or not current_total_capital_usd.is_finite()
        or current_total_capital_usd <= 0
    ):
        raise CiboCapitalManagementError(
            "BANK dynamic seed requires positive current total capital"
        )
    with localcontext() as context:
        context.prec = 100
        return (
            current_total_capital_usd
            * MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO
        )


def robust_capital_utility(
    candidate: CiboThreeModeCandidate,
    *,
    multiplier: int,
    capital_base_usd: Decimal,
    expected_net_utility_usd: Decimal | None = None,
) -> Decimal:
    """Canonical concave Portfolio utility for one causal exposure intensity."""

    if (
        not isinstance(multiplier, int)
        or isinstance(multiplier, bool)
        or multiplier < 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab robust multiplier must be non-negative int"
        )
    if (
        not isinstance(capital_base_usd, Decimal)
        or not capital_base_usd.is_finite()
        or capital_base_usd <= 0
    ):
        return Decimal("-Infinity")
    with localcontext() as context:
        context.prec = 100
        intensity = Decimal(multiplier)
        risk = candidate.stop_risk_per_multiplier_usd * intensity
        expected_net = (
            candidate.expected_net_utility_usd
            if expected_net_utility_usd is None
            else expected_net_utility_usd
        )
        return expected_net * intensity - (risk * risk / capital_base_usd)


def robust_economic_multiplier_cap(
    candidate: CiboThreeModeCandidate,
    *,
    capital_base_usd: Decimal,
    expected_net_utility_usd: Decimal | None = None,
) -> int:
    """Highest multiplier before canonical marginal robust utility turns non-positive."""

    expected_net = (
        candidate.expected_net_utility_usd
        if expected_net_utility_usd is None
        else expected_net_utility_usd
    )
    if (
        capital_base_usd <= 0
        or expected_net <= 0
        or candidate.stop_risk_per_multiplier_usd <= 0
    ):
        return 0
    with localcontext() as context:
        context.prec = 100
        marginal_limit = (
            (
                expected_net
                * capital_base_usd
                / (
                    candidate.stop_risk_per_multiplier_usd
                    * candidate.stop_risk_per_multiplier_usd
                )
            )
            + Decimal(1)
        ) / Decimal(2)
        economic_cap = max(
            0,
            int(
                marginal_limit.to_integral_value(
                    rounding=ROUND_CEILING
                )
            )
            - 1,
        )
    return min(candidate.maximum_multiplier, economic_cap)


def explain_three_mode(
    *,
    regime: CiboTraderLabRegime,
    risk_utilization: Decimal,
    margin_utilization: Decimal,
    drawdown_utilization: Decimal,
    cushion_available_usd: Decimal,
    best_candidate: CiboThreeModeCandidate | None,
    total_drawdown_utilization: Decimal | None = None,
    distributed_attack_frontier: bool = False,
) -> tuple[CiboTraderLabMode, tuple[str, ...]]:
    """Choose one mode and expose only causal reasons for that choice."""

    bank_reasons: list[str] = []
    if regime.evidence_stale:
        bank_reasons.append("EVIDENCE_STALE")
    if regime.provider_condition is not ProviderCondition.HEALTHY:
        bank_reasons.append("PROVIDER_NOT_HEALTHY")
    if regime.liquidity is LiquidityState.STRESSED:
        bank_reasons.append("LIQUIDITY_STRESSED")
    if regime.volatility is VolatilityState.DISLOCATED:
        bank_reasons.append("VOLATILITY_DISLOCATED")
    if regime.correlation is CorrelationState.BREAK:
        bank_reasons.append("CORRELATION_BREAK")
    if regime.position_path_adverse:
        bank_reasons.append("POSITION_PATH_ADVERSE")
    if risk_utilization >= cibo_new_capital_risk_utilization_ceiling():
        bank_reasons.append("RISK_UTILIZATION_DEFENSIVE")
    if margin_utilization >= Decimal("0.80"):
        bank_reasons.append("MARGIN_UTILIZATION_DEFENSIVE")
    if bank_reasons:
        # Owner invariant: the Trader already owns the admission decision.
        # CIBO may reduce intensity and defend the position, but it cannot
        # convert an already-executed Trader entry into BANK/no-trade.
        return CiboTraderLabMode.MEDIUM, tuple(
            bank_reasons + ["DEFENSIVE_MEDIUM_MANAGEMENT"]
        )

    if best_candidate is None:
        return CiboTraderLabMode.MEDIUM, ("NO_ATTACK_GRADE_CANDIDATE",)

    attack_context_reasons: list[str] = []
    total_dd = (
        drawdown_utilization
        if total_drawdown_utilization is None
        else total_drawdown_utilization
    )
    if total_dd >= ATTACK_TOTAL_DRAWDOWN_GUARD:
        attack_context_reasons.append("ATTACK_TOTAL_DRAWDOWN_GUARD")
    if drawdown_utilization >= SOVEREIGN_DEFENSIVE_DRAWDOWN:
        attack_context_reasons.append(
            "ATTACK_SOVEREIGN_DRAWDOWN_DEFENSIVE"
        )
    if distributed_attack_frontier:
        # Distributed ATTACK is an escalation grade, not an admission gate.
        # The defensive regime checks above already remove truly stressed
        # liquidity/volatility/correlation/provider states. THIN, ELEVATED
        # and CONCENTRATED contexts may still earn bounded escalation when the
        # full Native predecision stack and walk-forward evidence agree.
        if best_candidate.native_cognition_recommended is not True:
            attack_context_reasons.append(
                "ATTACK_NATIVE_POSITIVE_EVIDENCE_UNAVAILABLE"
            )
        if best_candidate.context_quality_disposition != "ALLOW":
            attack_context_reasons.append(
                "ATTACK_NATIVE_CONTEXT_QUALITY_ABSTAIN"
            )
        if best_candidate.expected_net_utility_usd <= 0:
            attack_context_reasons.append(
                "ATTACK_UNCERTAINTY_ADJUSTED_UTILITY_NONPOSITIVE"
            )
        if (
            best_candidate.walk_forward_positive_block_count
            < DISTRIBUTED_ATTACK_MIN_POSITIVE_BLOCKS
        ):
            attack_context_reasons.append(
                "ATTACK_INSUFFICIENT_POSITIVE_WALK_FORWARD_BLOCKS"
            )
    else:
        if regime.liquidity is not LiquidityState.NORMAL:
            attack_context_reasons.append("ATTACK_REQUIRES_NORMAL_LIQUIDITY")
        if regime.volatility not in {
            VolatilityState.COMPRESSED,
            VolatilityState.NORMAL,
        }:
            attack_context_reasons.append("ATTACK_VOLATILITY_NOT_GRADE")
        if regime.correlation is not CorrelationState.NORMAL:
            attack_context_reasons.append("ATTACK_CORRELATION_NOT_NORMAL")
        if best_candidate.attack_expected_net_utility_usd <= 0:
            attack_context_reasons.append(
                "ATTACK_WEAKEST_CHRONOLOGICAL_BLOCK_NOT_POSITIVE"
            )
        if not best_candidate.context_allowed:
            attack_context_reasons.append("ATTACK_CONTEXT_NOT_ALLOWED")
        if best_candidate.context_quality_disposition != "ALLOW":
            attack_context_reasons.append(
                "ATTACK_NATIVE_CONTEXT_QUALITY_ABSTAIN"
            )
    if best_candidate.maximum_multiplier < ATTACK_MINIMUM_MULTIPLIER:
        attack_context_reasons.append("ATTACK_PROVIDER_CAP_LT_2X")

    minimum_attack_cushion = (
        best_candidate.source_cost_per_multiplier_usd
        * Decimal(ATTACK_MINIMUM_MULTIPLIER)
    )
    if cushion_available_usd < minimum_attack_cushion:
        attack_context_reasons.append("ATTACK_CUSHION_LT_2X")
    if not attack_context_reasons:
        return CiboTraderLabMode.ATTACK, (
            "HEALTHY_CONTEXT",
            "POSITIVE_CAUSAL_EXPECTANCY",
            "CUSHION_FUNDS_AT_LEAST_2X",
        )
    return CiboTraderLabMode.MEDIUM, tuple(attack_context_reasons)


def select_three_mode(
    *,
    regime: CiboTraderLabRegime,
    risk_utilization: Decimal,
    margin_utilization: Decimal,
    drawdown_utilization: Decimal,
    cushion_available_usd: Decimal,
    best_candidate: CiboThreeModeCandidate | None,
    total_drawdown_utilization: Decimal | None = None,
    distributed_attack_frontier: bool = False,
) -> CiboTraderLabMode:
    """Compatibility wrapper returning only the selected mode."""

    mode, _reasons = explain_three_mode(
        regime=regime,
        risk_utilization=risk_utilization,
        margin_utilization=margin_utilization,
        drawdown_utilization=drawdown_utilization,
        cushion_available_usd=cushion_available_usd,
        best_candidate=best_candidate,
        total_drawdown_utilization=total_drawdown_utilization,
        distributed_attack_frontier=distributed_attack_frontier,
    )
    return mode

def apply_three_mode_settlement(
    state: _State,
    trade: CiboThreeModeOpenTrade,
    *,
    net_compound_before_split: bool = False,
    coordinated_economic_group: bool = False,
    economic_group_bootstrap_cushion_share: Decimal = Decimal("0.75"),
    economic_group_ablation: str | None = None,
    ceiling_discovery_mode: bool = False,
    compound_profit_reinvestment_fraction: Decimal | None = None,
) -> Decimal:
    """Settle one already-due trade; no outcome is consulted before exit."""

    with localcontext() as context:
        context.prec = 100
        gross_pnl = trade.gross_r * trade.stop_risk_usd
        net_pnl = gross_pnl - trade.provider_cost_usd

    open_stop_risk_before_usd = state.open_stop_risk_usd
    open_margin_before_usd = state.open_margin_usd
    state.open_stop_risk_usd -= trade.stop_risk_usd
    state.open_margin_usd -= trade.margin_usd
    accounting_epsilon_usd = Decimal("1e-18")
    if (
        state.open_stop_risk_usd < 0
        and state.open_stop_risk_usd >= -accounting_epsilon_usd
    ):
        state.open_stop_risk_usd = Decimal(0)
    if (
        state.open_margin_usd < 0
        and state.open_margin_usd >= -accounting_epsilon_usd
    ):
        state.open_margin_usd = Decimal(0)
    if state.open_stop_risk_usd < 0 or state.open_margin_usd < 0:
        raise CiboCapitalManagementError(
            "Trader Lab open exposure accounting became materially negative during settlement: "
            f"signal={trade.signal_fingerprint} trader={trade.trader_id} "
            f"mode={trade.mode.value} multiplier={trade.multiplier} "
            f"open_stop_before={format(open_stop_risk_before_usd, 'f')} "
            f"trade_stop_risk={format(trade.stop_risk_usd, 'f')} "
            f"open_stop_after={format(state.open_stop_risk_usd, 'f')} "
            f"open_margin_before={format(open_margin_before_usd, 'f')} "
            f"trade_margin={format(trade.margin_usd, 'f')} "
            f"open_margin_after={format(state.open_margin_usd, 'f')} "
            f"epsilon={format(accounting_epsilon_usd, 'f')}"
        )
    if trade.mode is CiboTraderLabMode.MEDIUM:
        bank_seed = (
            trade.source_reserved_usd
            if trade.bank_seed_usd is None
            else trade.bank_seed_usd
        )
        state.sovereign_reserved_usd -= trade.source_reserved_usd
        state.bank_seed_reserved_usd -= bank_seed
        state.bank_seed_recycled_total_usd += bank_seed
        state.medium_compound_turnover_usd += trade.source_reserved_usd

        if net_pnl > 0:
            recovery = (
                min(net_pnl, state.medium_compound_recovery_deficit_usd)
                if net_compound_before_split
                else Decimal(0)
            )
            if recovery > 0:
                state.sovereign_bank_usd += recovery
                state.medium_compound_recovery_deficit_usd -= recovery
                state.medium_compound_recovered_usd += recovery
            distributable = net_pnl - recovery
            sovereign_share = MEDIUM_SOVEREIGN_SHARE
            if compound_profit_reinvestment_fraction is not None:
                sovereign_share = (
                    Decimal(1) - compound_profit_reinvestment_fraction
                )
            elif economic_group_ablation == "CIBO_COMPOUND":
                sovereign_share = Decimal(1)
            elif coordinated_economic_group:
                total = max(Decimal("0.00000001"), state.total_capital_usd)
                total_dd = _ratio(
                    max(
                        Decimal(0),
                        state.peak_total_capital_usd - state.total_capital_usd,
                    ),
                    state.peak_total_capital_usd,
                )
                cushion_ratio = _ratio(
                    state.portfolio_cushion_usd,
                    total,
                )
                if ceiling_discovery_mode:
                    sovereign_share = (
                        Decimal(1)
                        - economic_group_bootstrap_cushion_share
                    )
                elif total_dd >= Decimal("0.20"):
                    sovereign_share = Decimal("0.80")
                elif total_dd >= Decimal("0.10"):
                    sovereign_share = Decimal("0.65")
                elif cushion_ratio < Decimal("0.20"):
                    sovereign_share = (
                        Decimal(1)
                        - economic_group_bootstrap_cushion_share
                    )
                elif cushion_ratio > Decimal("0.60"):
                    sovereign_share = Decimal("0.65")
            sovereign_gain = distributable * sovereign_share
            cushion_gain = distributable - sovereign_gain
            state.sovereign_bank_usd += sovereign_gain
            state.portfolio_cushion_usd += cushion_gain
            state.portfolio_attack_credit_usd += cushion_gain
            state.medium_profit_to_sovereign_usd += sovereign_gain
            state.medium_profit_to_cushion_usd += cushion_gain
            state.medium_compound_positive_net_usd += net_pnl
        elif net_pnl < 0:
            state.sovereign_bank_usd += net_pnl
            if net_compound_before_split:
                state.medium_compound_recovery_deficit_usd += -net_pnl
            state.medium_compound_negative_net_usd += -net_pnl
    elif trade.mode is CiboTraderLabMode.ATTACK:
        state.cushion_reserved_usd -= trade.source_reserved_usd
        if net_pnl > 0 and compound_profit_reinvestment_fraction is not None:
            reinvested_gain = (
                net_pnl * compound_profit_reinvestment_fraction
            )
            sovereign_gain = net_pnl - reinvested_gain
            state.portfolio_cushion_usd += reinvested_gain
            state.sovereign_bank_usd += sovereign_gain
            state.attack_profit_to_cushion_usd += reinvested_gain
            state.attack_profit_to_sovereign_usd += sovereign_gain
        else:
            state.portfolio_cushion_usd += net_pnl
            if net_pnl > 0:
                state.attack_profit_to_cushion_usd += net_pnl
        state.attack_net_pnl_usd += net_pnl
        if state.portfolio_cushion_usd < 0:
            breach = -state.portfolio_cushion_usd
            state.attack_sovereign_breach_usd += breach
            state.portfolio_cushion_usd = Decimal(0)
            state.sovereign_bank_usd -= breach
        state.portfolio_attack_credit_recycled_total_usd += (
            trade.source_reserved_usd
        )
        # Portfolio Compound is revolving capital. Once ATTACK settles, its
        # reserved principal is released and the realized PnL is already
        # reflected in the cushion. The full unreserved cushion therefore
        # becomes available to fund the next cognitively enabled ATTACK.
        state.portfolio_attack_credit_usd = state.cushion_available_usd
    elif trade.mode is CiboTraderLabMode.BANK:
        raise CiboCapitalManagementError(
            "BANK cannot own trades; BANK only seeds MEDIUM"
        )
    else:
        raise CiboCapitalManagementError(
            "unknown Trader Lab operating mode"
        )
    state.mark()
    return net_pnl


def run_three_mode_trader_lab(
    manifest: Mapping[str, Any],
    *,
    baseline_ending_capital_usd: Decimal | None = None,
    cognitive_recommend_by_signal: Mapping[str, bool | None] | None = None,
    native_profile_by_signal: (
        Mapping[str, Mapping[str, object]] | None
    ) = None,
    historical_prior_by_signal: (
        Mapping[str, Mapping[str, object]] | None
    ) = None,
    lifecycle_by_signal: (
        Mapping[str, Mapping[str, object]] | None
    ) = None,
    lifecycle_bootstrap_override_by_signal: (
        Mapping[str, Mapping[str, object]] | None
    ) = None,
    lifecycle_attack_override_by_signal: (
        Mapping[str, Mapping[str, object]] | None
    ) = None,
    lifecycle_bootstrap_override_capital_ceiling: Decimal | None = None,
    lifecycle_bootstrap_override_peak_capital_ceiling: Decimal | None = None,
    lifecycle_bootstrap_override_drawdown_trigger: Decimal | None = None,
    lifecycle_bootstrap_override_trader_loss_streak_trigger: int | None = None,
    lifecycle_bootstrap_override_medium_max_multiplier: int = 2,
    lifecycle_bootstrap_override_require_expectation: bool = False,
    lifecycle_bootstrap_override_expected_r_ceiling: Decimal | None = None,
    lifecycle_attack_override_projected_open_stop_risk_fraction_trigger: Decimal | None = None,
    lifecycle_defensive_medium_1x_only: bool = False,
    lifecycle_attack_only: bool = False,
    lifecycle_defensive_medium_max_multiplier: int | None = None,
    lifecycle_defense_drawdown_trigger: Decimal | None = None,
    lifecycle_trader_loss_streak_trigger: int | None = None,
    lifecycle_bootstrap_capital_ceiling: Decimal | None = None,
    lifecycle_minimum_stop_risk_fraction_trigger: Decimal | None = None,
    lifecycle_projected_open_stop_risk_fraction_trigger: Decimal | None = None,
    enforce_research_context_abstain: bool = False,
    soft_medium_drawdown_allocator: bool = False,
    medium_pretrade_drawdown_ceiling: Decimal = ECONOMIC_DRAWDOWN_CEILING,
    distributed_attack_frontier: bool = False,
    attack_multiplier_cap: int = DEFAULT_DISTRIBUTED_ATTACK_MULTIPLIER_CAP,
    medium_multiplier_cap: int = 4,
    medium_drawdown_intensity_trigger: Decimal | None = None,
    coordinated_economic_group: bool = False,
    economic_group_bootstrap_cushion_share: Decimal = Decimal("0.75"),
    economic_group_ablation: str | None = None,
    ceiling_discovery_mode: bool = False,
    ceiling_growth_leverage_slope: Decimal | None = None,
    ceiling_attack_compound_hysteresis_fraction: Decimal | None = None,
    ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction: Decimal | None = None,
    ceiling_attack_drawdown_budget_fraction: Decimal | None = None,
    ceiling_attack_drawdown_budget_capital_floor: Decimal | None = None,
    ceiling_attack_drawdown_budget_capital_ceiling: Decimal | None = None,
    ceiling_attack_drawdown_budget2_fraction: Decimal | None = None,
    ceiling_attack_drawdown_budget2_capital_floor: Decimal | None = None,
    ceiling_attack_drawdown_budget2_capital_ceiling: Decimal | None = None,
    ceiling_attack_single_trade_risk_fraction: Decimal | None = None,
    ceiling_attack_loss_streak_trigger: int | None = None,
    ceiling_attack_loss_streak_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_drawdown_taper_trigger: Decimal | None = None,
    ceiling_attack_drawdown_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_multiplier_band_lower: int | None = None,
    ceiling_attack_multiplier_band_upper: int | None = None,
    ceiling_attack_multiplier_band_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_risk_fraction_band_lower: Decimal | None = None,
    ceiling_attack_risk_fraction_band_upper: Decimal | None = None,
    ceiling_attack_risk_fraction_band_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_drawdown_window_lower: Decimal | None = None,
    ceiling_attack_drawdown_window_upper: Decimal | None = None,
    ceiling_attack_drawdown_window_multiplier_lower: int | None = None,
    ceiling_attack_drawdown_window_multiplier_upper: int | None = None,
    ceiling_attack_drawdown_window_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_drawdown_window2_lower: Decimal | None = None,
    ceiling_attack_drawdown_window2_upper: Decimal | None = None,
    ceiling_attack_drawdown_window2_multiplier_lower: int | None = None,
    ceiling_attack_drawdown_window2_multiplier_upper: int | None = None,
    ceiling_attack_drawdown_window2_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_drawdown_window3_lower: Decimal | None = None,
    ceiling_attack_drawdown_window3_upper: Decimal | None = None,
    ceiling_attack_drawdown_window3_multiplier_lower: int | None = None,
    ceiling_attack_drawdown_window3_multiplier_upper: int | None = None,
    ceiling_attack_drawdown_window3_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_drawdown_window4_lower: Decimal | None = None,
    ceiling_attack_drawdown_window4_upper: Decimal | None = None,
    ceiling_attack_drawdown_window4_multiplier_lower: int | None = None,
    ceiling_attack_drawdown_window4_multiplier_upper: int | None = None,
    ceiling_attack_drawdown_window4_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_drawdown_window5_lower: Decimal | None = None,
    ceiling_attack_drawdown_window5_upper: Decimal | None = None,
    ceiling_attack_drawdown_window5_multiplier_lower: int | None = None,
    ceiling_attack_drawdown_window5_multiplier_upper: int | None = None,
    ceiling_attack_drawdown_window5_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_drawdown_window6_lower: Decimal | None = None,
    ceiling_attack_drawdown_window6_upper: Decimal | None = None,
    ceiling_attack_drawdown_window6_multiplier_lower: int | None = None,
    ceiling_attack_drawdown_window6_multiplier_upper: int | None = None,
    ceiling_attack_drawdown_window6_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_drawdown_window6_capital_floor: Decimal | None = None,
    ceiling_attack_drawdown_window6_capital_ceiling: Decimal | None = None,
    ceiling_attack_drawdown_window7_lower: Decimal | None = None,
    ceiling_attack_drawdown_window7_upper: Decimal | None = None,
    ceiling_attack_drawdown_window7_multiplier_lower: int | None = None,
    ceiling_attack_drawdown_window7_multiplier_upper: int | None = None,
    ceiling_attack_drawdown_window7_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_attack_drawdown_window7_capital_floor: Decimal | None = None,
    ceiling_attack_drawdown_window7_capital_ceiling: Decimal | None = None,
    ceiling_attack_stress_confidence_drawdown_trigger: Decimal | None = None,
    ceiling_attack_stress_confidence_ratio_ceiling: Decimal | None = None,
    ceiling_attack_stress_confidence_target_r_floor: Decimal | None = None,
    ceiling_attack_stress_confidence_multiplier_lower: int | None = None,
    ceiling_attack_stress_confidence_multiplier_upper: int | None = None,
    ceiling_attack_stress_confidence_projected_risk_fraction_trigger: Decimal | None = None,
    ceiling_attack_stress_confidence_capital_floor: Decimal | None = None,
    ceiling_attack_stress_confidence_capital_ceiling: Decimal | None = None,
    ceiling_attack_stress_confidence_taper_fraction: Decimal = Decimal("0.75"),
    ceiling_attack_stress_confidence_risk_budget_taper_fraction: Decimal = Decimal("1"),
    ceiling_attack_state_pressure_expected_minutes_floor: Decimal | None = None,
    ceiling_attack_state_pressure_target_r_ceiling: Decimal | None = None,
    ceiling_attack_state_pressure_confidence_ratio_ceiling: Decimal | None = None,
    ceiling_attack_state_pressure_projected_risk_fraction_trigger: Decimal | None = None,
    ceiling_attack_state_pressure_capital_floor: Decimal | None = None,
    ceiling_attack_state_pressure_capital_ceiling: Decimal | None = None,
    ceiling_attack_state_pressure_market_posture: str | None = None,
    ceiling_attack_state_pressure_h1_range_state: str | None = None,
    ceiling_attack_state_pressure_h4_range_state: str | None = None,
    ceiling_attack_state_pressure_risk_budget_taper_fraction: Decimal = Decimal("1"),
    ceiling_attack_state_pressure2_expected_minutes_floor: Decimal | None = None,
    ceiling_attack_state_pressure2_target_r_ceiling: Decimal | None = None,
    ceiling_attack_state_pressure2_confidence_ratio_ceiling: Decimal | None = None,
    ceiling_attack_state_pressure2_projected_risk_fraction_trigger: Decimal | None = None,
    ceiling_attack_state_pressure2_capital_floor: Decimal | None = None,
    ceiling_attack_state_pressure2_capital_ceiling: Decimal | None = None,
    ceiling_attack_state_pressure2_market_posture: str | None = None,
    ceiling_attack_state_pressure2_h1_range_state: str | None = None,
    ceiling_attack_state_pressure2_h4_range_state: str | None = None,
    ceiling_attack_state_pressure2_cap_taper_fraction: Decimal = Decimal("1"),
    ceiling_attack_state_pressure2_risk_budget_taper_fraction: Decimal = Decimal("1"),
    ceiling_attack_trader_loss_ratio_trigger: Decimal | None = None,
    ceiling_attack_trader_loss_ratio_min_settlements: int = 20,
    ceiling_attack_trader_loss_ratio_taper_fraction: Decimal = Decimal("0.95"),
    ceiling_attack_recent_trader_loss_window: int | None = None,
    ceiling_attack_recent_trader_loss_fraction_trigger: Decimal | None = None,
    ceiling_attack_recent_trader_loss_drawdown_trigger: Decimal = Decimal("0.10"),
    ceiling_attack_recent_trader_loss_taper_fraction: Decimal = Decimal("0.75"),
    ceiling_attack_trader_shock_trigger_fraction: Decimal | None = None,
    ceiling_attack_trader_shock_drawdown_trigger: Decimal = Decimal("0.10"),
    ceiling_attack_trader_shock_capital_ceiling: Decimal | None = None,
    ceiling_attack_trader_shock_taper_fraction: Decimal = Decimal("0.75"),
    ceiling_attack_low_multiplier_demotion_upper: int | None = None,
    ceiling_attack_low_multiplier_demotion_drawdown_trigger: Decimal = Decimal("0.10"),
    ceiling_portfolio_shock_trigger_fraction: Decimal | None = None,
    ceiling_portfolio_shock_taper_fraction: Decimal = Decimal("0.50"),
    ceiling_portfolio_shock_one_shot: bool = False,
    compound_profit_reinvestment_fraction: Decimal | None = None,
    collect_engineering_trace: bool = True,
    collect_epoch_receipts: bool = True,
    compact_trade_receipts: bool = False,
) -> dict[str, object]:
    """Run the isolated chronological three-mode ceiling experiment."""

    for flag_name, flag_value in (
        ("collect_engineering_trace", collect_engineering_trace),
        ("collect_epoch_receipts", collect_epoch_receipts),
        ("compact_trade_receipts", compact_trade_receipts),
    ):
        if type(flag_value) is not bool:
            raise CiboCapitalManagementError(
                f"Trader Lab {flag_name} must be bool"
            )

    if lifecycle_bootstrap_override_capital_ceiling is not None and (
        not isinstance(lifecycle_bootstrap_override_capital_ceiling, Decimal)
        or not lifecycle_bootstrap_override_capital_ceiling.is_finite()
        or lifecycle_bootstrap_override_capital_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab bootstrap lifecycle override capital ceiling must be positive Decimal"
        )
    if lifecycle_bootstrap_override_peak_capital_ceiling is not None and (
        not isinstance(lifecycle_bootstrap_override_peak_capital_ceiling, Decimal)
        or not lifecycle_bootstrap_override_peak_capital_ceiling.is_finite()
        or lifecycle_bootstrap_override_peak_capital_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab bootstrap lifecycle override peak-capital ceiling must be positive Decimal"
        )
    if lifecycle_bootstrap_override_drawdown_trigger is not None and (
        not isinstance(lifecycle_bootstrap_override_drawdown_trigger, Decimal)
        or not lifecycle_bootstrap_override_drawdown_trigger.is_finite()
        or lifecycle_bootstrap_override_drawdown_trigger < 0
        or lifecycle_bootstrap_override_drawdown_trigger >= Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab bootstrap lifecycle override DD trigger must be Decimal in [0, 0.50)"
        )
    if lifecycle_bootstrap_override_trader_loss_streak_trigger is not None and (
        not isinstance(lifecycle_bootstrap_override_trader_loss_streak_trigger, int)
        or isinstance(lifecycle_bootstrap_override_trader_loss_streak_trigger, bool)
        or lifecycle_bootstrap_override_trader_loss_streak_trigger < 1
        or lifecycle_bootstrap_override_trader_loss_streak_trigger > 20
    ):
        raise CiboCapitalManagementError(
            "Trader Lab bootstrap lifecycle override loss streak trigger must be int in [1, 20]"
        )
    if (
        not isinstance(lifecycle_bootstrap_override_medium_max_multiplier, int)
        or isinstance(lifecycle_bootstrap_override_medium_max_multiplier, bool)
        or lifecycle_bootstrap_override_medium_max_multiplier < 1
        or lifecycle_bootstrap_override_medium_max_multiplier > 4
    ):
        raise CiboCapitalManagementError(
            "Trader Lab bootstrap lifecycle override MEDIUM max multiplier must be int in [1, 4]"
        )
    if type(lifecycle_bootstrap_override_require_expectation) is not bool:
        raise CiboCapitalManagementError(
            "Trader Lab bootstrap lifecycle expectation gate must be bool"
        )
    if lifecycle_bootstrap_override_expected_r_ceiling is not None and (
        not isinstance(lifecycle_bootstrap_override_expected_r_ceiling, Decimal)
        or not lifecycle_bootstrap_override_expected_r_ceiling.is_finite()
    ):
        raise CiboCapitalManagementError(
            "Trader Lab bootstrap lifecycle expected-R ceiling must be finite Decimal"
        )
    if lifecycle_bootstrap_override_by_signal is not None and (
        lifecycle_bootstrap_override_capital_ceiling is None
        or lifecycle_bootstrap_override_drawdown_trigger is None
        or lifecycle_bootstrap_override_trader_loss_streak_trigger is None
    ):
        raise CiboCapitalManagementError(
            "Trader Lab bootstrap lifecycle override requires capital, DD and loss-streak triggers"
        )
    if type(lifecycle_defensive_medium_1x_only) is not bool:
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle defensive MEDIUM 1x switch must be bool"
        )
    if type(lifecycle_attack_only) is not bool:
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle ATTACK-only switch must be bool"
        )
    if lifecycle_defensive_medium_max_multiplier is not None and (
        not isinstance(lifecycle_defensive_medium_max_multiplier, int)
        or isinstance(lifecycle_defensive_medium_max_multiplier, bool)
        or lifecycle_defensive_medium_max_multiplier < 1
        or lifecycle_defensive_medium_max_multiplier > 4
    ):
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle defensive MEDIUM max multiplier must be int in [1, 4]"
        )
    if (
        lifecycle_defensive_medium_1x_only
        and lifecycle_defensive_medium_max_multiplier is not None
    ):
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle defensive MEDIUM grade selectors are mutually exclusive"
        )
    if lifecycle_attack_only and (
        lifecycle_defensive_medium_1x_only
        or lifecycle_defensive_medium_max_multiplier is not None
    ):
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle ATTACK-only scope is mutually exclusive with MEDIUM selectors"
        )
    if lifecycle_defense_drawdown_trigger is not None and (
        not isinstance(lifecycle_defense_drawdown_trigger, Decimal)
        or not lifecycle_defense_drawdown_trigger.is_finite()
        or lifecycle_defense_drawdown_trigger < 0
        or lifecycle_defense_drawdown_trigger >= Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle defense drawdown trigger must be Decimal in [0, 0.50)"
        )
    if lifecycle_trader_loss_streak_trigger is not None and (
        not isinstance(lifecycle_trader_loss_streak_trigger, int)
        or isinstance(lifecycle_trader_loss_streak_trigger, bool)
        or lifecycle_trader_loss_streak_trigger < 1
        or lifecycle_trader_loss_streak_trigger > 10
    ):
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle Trader loss streak trigger must be int in [1, 10]"
        )
    if lifecycle_bootstrap_capital_ceiling is not None and (
        not isinstance(lifecycle_bootstrap_capital_ceiling, Decimal)
        or not lifecycle_bootstrap_capital_ceiling.is_finite()
        or lifecycle_bootstrap_capital_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle bootstrap capital ceiling must be positive Decimal"
        )
    if lifecycle_minimum_stop_risk_fraction_trigger is not None and (
        not isinstance(lifecycle_minimum_stop_risk_fraction_trigger, Decimal)
        or not lifecycle_minimum_stop_risk_fraction_trigger.is_finite()
        or lifecycle_minimum_stop_risk_fraction_trigger <= 0
        or lifecycle_minimum_stop_risk_fraction_trigger > Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle minimum stop-risk fraction trigger must be "
            "Decimal in (0, 0.50]"
        )
    if lifecycle_projected_open_stop_risk_fraction_trigger is not None and (
        not isinstance(
            lifecycle_projected_open_stop_risk_fraction_trigger, Decimal
        )
        or not lifecycle_projected_open_stop_risk_fraction_trigger.is_finite()
        or lifecycle_projected_open_stop_risk_fraction_trigger <= 0
        or lifecycle_projected_open_stop_risk_fraction_trigger > Decimal("1")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle projected open stop-risk fraction trigger "
            "must be Decimal in (0, 1]"
        )
    if (
        lifecycle_attack_override_projected_open_stop_risk_fraction_trigger
        is not None
        and (
            not isinstance(
                lifecycle_attack_override_projected_open_stop_risk_fraction_trigger,
                Decimal,
            )
            or not lifecycle_attack_override_projected_open_stop_risk_fraction_trigger.is_finite()
            or lifecycle_attack_override_projected_open_stop_risk_fraction_trigger <= 0
            or lifecycle_attack_override_projected_open_stop_risk_fraction_trigger
            > Decimal("1")
        )
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK lifecycle override projected open stop-risk "
            "fraction trigger must be Decimal in (0, 1]"
        )
    if type(enforce_research_context_abstain) is not bool:
        raise CiboCapitalManagementError(
            "Trader Lab context hypothesis switch must be bool"
        )
    if type(soft_medium_drawdown_allocator) is not bool:
        raise CiboCapitalManagementError(
            "Trader Lab soft MEDIUM drawdown allocator switch must be bool"
        )
    if type(distributed_attack_frontier) is not bool:
        raise CiboCapitalManagementError(
            "Trader Lab distributed ATTACK frontier switch must be bool"
        )
    if type(coordinated_economic_group) is not bool:
        raise CiboCapitalManagementError(
            "Trader Lab coordinated economic group switch must be bool"
        )
    if type(ceiling_discovery_mode) is not bool:
        raise CiboCapitalManagementError(
            "Trader Lab ceiling discovery switch must be bool"
        )
    if ceiling_growth_leverage_slope is not None and (
        not isinstance(ceiling_growth_leverage_slope, Decimal)
        or not ceiling_growth_leverage_slope.is_finite()
        or ceiling_growth_leverage_slope <= 0
        or ceiling_growth_leverage_slope > Decimal("50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling growth leverage slope must be Decimal in (0, 50]"
        )
    if ceiling_attack_compound_hysteresis_fraction is not None and (
        not isinstance(ceiling_attack_compound_hysteresis_fraction, Decimal)
        or not ceiling_attack_compound_hysteresis_fraction.is_finite()
        or ceiling_attack_compound_hysteresis_fraction <= 0
        or ceiling_attack_compound_hysteresis_fraction > Decimal("0.10")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK compound hysteresis fraction must be Decimal in (0, 0.10]"
        )
    if (
        ceiling_attack_compound_hysteresis_fraction is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK compound hysteresis requires ceiling discovery mode"
        )
    if (
        ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction
        is not None
        and (
            not isinstance(
                ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction,
                Decimal,
            )
            or not ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction.is_finite()
            or ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction <= 0
            or ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction > Decimal("0.10")
        )
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence reinvestment hysteresis must be Decimal in (0, 0.10]"
        )
    if (
        ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction
        is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence reinvestment hysteresis requires ceiling discovery mode"
        )
    if ceiling_attack_drawdown_budget_fraction is not None and (
        not isinstance(ceiling_attack_drawdown_budget_fraction, Decimal)
        or not ceiling_attack_drawdown_budget_fraction.is_finite()
        or ceiling_attack_drawdown_budget_fraction <= 0
        or ceiling_attack_drawdown_budget_fraction > Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK drawdown budget fraction must be Decimal in (0, 0.50]"
        )
    if ceiling_attack_drawdown_budget_capital_floor is not None and (
        not isinstance(ceiling_attack_drawdown_budget_capital_floor, Decimal)
        or not ceiling_attack_drawdown_budget_capital_floor.is_finite()
        or ceiling_attack_drawdown_budget_capital_floor < 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK drawdown budget capital floor must be nonnegative Decimal"
        )
    if ceiling_attack_drawdown_budget_capital_ceiling is not None and (
        not isinstance(ceiling_attack_drawdown_budget_capital_ceiling, Decimal)
        or not ceiling_attack_drawdown_budget_capital_ceiling.is_finite()
        or ceiling_attack_drawdown_budget_capital_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK drawdown budget capital ceiling must be positive Decimal"
        )
    if ceiling_attack_drawdown_budget2_fraction is not None and (
        not isinstance(ceiling_attack_drawdown_budget2_fraction, Decimal)
        or not ceiling_attack_drawdown_budget2_fraction.is_finite()
        or ceiling_attack_drawdown_budget2_fraction <= 0
        or ceiling_attack_drawdown_budget2_fraction > Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab second ATTACK drawdown budget fraction must be Decimal in (0, 0.50]"
        )
    if ceiling_attack_drawdown_budget2_fraction is not None and (
        ceiling_attack_drawdown_budget2_capital_floor is None
        or ceiling_attack_drawdown_budget2_capital_ceiling is None
    ):
        raise CiboCapitalManagementError(
            "Trader Lab second ATTACK drawdown budget requires capital floor and ceiling"
        )
    if ceiling_attack_drawdown_budget2_capital_floor is not None and (
        not isinstance(ceiling_attack_drawdown_budget2_capital_floor, Decimal)
        or not ceiling_attack_drawdown_budget2_capital_floor.is_finite()
        or ceiling_attack_drawdown_budget2_capital_floor < 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab second ATTACK drawdown budget capital floor must be nonnegative Decimal"
        )
    if ceiling_attack_drawdown_budget2_capital_ceiling is not None and (
        not isinstance(ceiling_attack_drawdown_budget2_capital_ceiling, Decimal)
        or not ceiling_attack_drawdown_budget2_capital_ceiling.is_finite()
        or ceiling_attack_drawdown_budget2_capital_ceiling <= 0
        or (
            ceiling_attack_drawdown_budget2_capital_floor is not None
            and ceiling_attack_drawdown_budget2_capital_ceiling
            <= ceiling_attack_drawdown_budget2_capital_floor
        )
    ):
        raise CiboCapitalManagementError(
            "Trader Lab second ATTACK drawdown budget capital band is invalid"
        )
    if ceiling_attack_drawdown_budget2_fraction is not None and not ceiling_discovery_mode:
        raise CiboCapitalManagementError(
            "Trader Lab second ATTACK drawdown budget requires ceiling discovery mode"
        )
    if (
        ceiling_attack_drawdown_budget_fraction is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK drawdown budget requires ceiling discovery mode"
        )
    if ceiling_attack_single_trade_risk_fraction is not None and (
        not isinstance(ceiling_attack_single_trade_risk_fraction, Decimal)
        or not ceiling_attack_single_trade_risk_fraction.is_finite()
        or ceiling_attack_single_trade_risk_fraction <= 0
        or ceiling_attack_single_trade_risk_fraction > Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK single-trade risk fraction must be Decimal in (0, 0.50]"
        )
    if (
        ceiling_attack_single_trade_risk_fraction is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK single-trade risk cap requires ceiling discovery mode"
        )
    if ceiling_attack_loss_streak_trigger is not None and (
        not isinstance(ceiling_attack_loss_streak_trigger, int)
        or isinstance(ceiling_attack_loss_streak_trigger, bool)
        or ceiling_attack_loss_streak_trigger < 1
        or ceiling_attack_loss_streak_trigger > 10
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK loss streak trigger must be int in [1, 10]"
        )
    if (
        not isinstance(ceiling_attack_loss_streak_taper_fraction, Decimal)
        or not ceiling_attack_loss_streak_taper_fraction.is_finite()
        or ceiling_attack_loss_streak_taper_fraction <= 0
        or ceiling_attack_loss_streak_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK loss streak taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_loss_streak_trigger is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK loss streak taper requires ceiling discovery mode"
        )
    if ceiling_attack_drawdown_taper_trigger is not None and (
        not isinstance(ceiling_attack_drawdown_taper_trigger, Decimal)
        or not ceiling_attack_drawdown_taper_trigger.is_finite()
        or ceiling_attack_drawdown_taper_trigger < 0
        or ceiling_attack_drawdown_taper_trigger >= Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK drawdown taper trigger must be Decimal in [0, 0.50)"
        )
    if (
        not isinstance(ceiling_attack_drawdown_taper_fraction, Decimal)
        or not ceiling_attack_drawdown_taper_fraction.is_finite()
        or ceiling_attack_drawdown_taper_fraction <= 0
        or ceiling_attack_drawdown_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK drawdown taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_drawdown_taper_trigger is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling ATTACK drawdown taper requires ceiling discovery mode"
        )
    if (
        ceiling_attack_multiplier_band_lower is None
    ) != (
        ceiling_attack_multiplier_band_upper is None
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK multiplier-band taper requires both lower and upper bounds"
        )
    if ceiling_attack_multiplier_band_lower is not None and (
        not isinstance(ceiling_attack_multiplier_band_lower, int)
        or isinstance(ceiling_attack_multiplier_band_lower, bool)
        or ceiling_attack_multiplier_band_lower < ATTACK_MINIMUM_MULTIPLIER
        or ceiling_attack_multiplier_band_upper is None
        or not isinstance(ceiling_attack_multiplier_band_upper, int)
        or isinstance(ceiling_attack_multiplier_band_upper, bool)
        or ceiling_attack_multiplier_band_upper < ceiling_attack_multiplier_band_lower
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK multiplier-band bounds must be ordered ints >= minimum ATTACK"
        )
    if (
        not isinstance(ceiling_attack_multiplier_band_taper_fraction, Decimal)
        or not ceiling_attack_multiplier_band_taper_fraction.is_finite()
        or ceiling_attack_multiplier_band_taper_fraction <= 0
        or ceiling_attack_multiplier_band_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK multiplier-band taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_multiplier_band_lower is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK multiplier-band taper requires ceiling discovery mode"
        )
    if (
        ceiling_attack_risk_fraction_band_lower is None
    ) != (
        ceiling_attack_risk_fraction_band_upper is None
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK risk-fraction band taper requires both bounds"
        )
    if ceiling_attack_risk_fraction_band_lower is not None and (
        not isinstance(ceiling_attack_risk_fraction_band_lower, Decimal)
        or not ceiling_attack_risk_fraction_band_lower.is_finite()
        or ceiling_attack_risk_fraction_band_lower < 0
        or ceiling_attack_risk_fraction_band_upper is None
        or not isinstance(ceiling_attack_risk_fraction_band_upper, Decimal)
        or not ceiling_attack_risk_fraction_band_upper.is_finite()
        or ceiling_attack_risk_fraction_band_upper
        <= ceiling_attack_risk_fraction_band_lower
        or ceiling_attack_risk_fraction_band_upper > Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK risk-fraction band must satisfy 0 <= lower < upper <= 0.50"
        )
    if (
        not isinstance(ceiling_attack_risk_fraction_band_taper_fraction, Decimal)
        or not ceiling_attack_risk_fraction_band_taper_fraction.is_finite()
        or ceiling_attack_risk_fraction_band_taper_fraction <= 0
        or ceiling_attack_risk_fraction_band_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK risk-fraction band taper must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_risk_fraction_band_lower is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK risk-fraction band taper requires ceiling discovery mode"
        )
    window_values = (
        ceiling_attack_drawdown_window_lower,
        ceiling_attack_drawdown_window_upper,
        ceiling_attack_drawdown_window_multiplier_lower,
        ceiling_attack_drawdown_window_multiplier_upper,
    )
    if any(value is None for value in window_values) and any(
        value is not None for value in window_values
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window taper requires all four window bounds"
        )
    if ceiling_attack_drawdown_window_lower is not None and (
        not isinstance(ceiling_attack_drawdown_window_lower, Decimal)
        or not ceiling_attack_drawdown_window_lower.is_finite()
        or ceiling_attack_drawdown_window_lower < 0
        or ceiling_attack_drawdown_window_upper is None
        or not isinstance(ceiling_attack_drawdown_window_upper, Decimal)
        or not ceiling_attack_drawdown_window_upper.is_finite()
        or ceiling_attack_drawdown_window_upper
        <= ceiling_attack_drawdown_window_lower
        or ceiling_attack_drawdown_window_upper > 1
        or ceiling_attack_drawdown_window_multiplier_lower is None
        or not isinstance(ceiling_attack_drawdown_window_multiplier_lower, int)
        or isinstance(ceiling_attack_drawdown_window_multiplier_lower, bool)
        or ceiling_attack_drawdown_window_multiplier_lower
        < ATTACK_MINIMUM_MULTIPLIER
        or ceiling_attack_drawdown_window_multiplier_upper is None
        or not isinstance(ceiling_attack_drawdown_window_multiplier_upper, int)
        or isinstance(ceiling_attack_drawdown_window_multiplier_upper, bool)
        or ceiling_attack_drawdown_window_multiplier_upper
        < ceiling_attack_drawdown_window_multiplier_lower
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window bounds are invalid"
        )
    if (
        not isinstance(ceiling_attack_drawdown_window_taper_fraction, Decimal)
        or not ceiling_attack_drawdown_window_taper_fraction.is_finite()
        or ceiling_attack_drawdown_window_taper_fraction <= 0
        or ceiling_attack_drawdown_window_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_drawdown_window_lower is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window taper requires ceiling discovery mode"
        )
    window2_values = (
        ceiling_attack_drawdown_window2_lower,
        ceiling_attack_drawdown_window2_upper,
        ceiling_attack_drawdown_window2_multiplier_lower,
        ceiling_attack_drawdown_window2_multiplier_upper,
    )
    if any(value is None for value in window2_values) and any(
        value is not None for value in window2_values
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window2 taper requires all four window bounds"
        )
    if ceiling_attack_drawdown_window2_lower is not None and (
        not isinstance(ceiling_attack_drawdown_window2_lower, Decimal)
        or not ceiling_attack_drawdown_window2_lower.is_finite()
        or ceiling_attack_drawdown_window2_lower < 0
        or ceiling_attack_drawdown_window2_upper is None
        or not isinstance(ceiling_attack_drawdown_window2_upper, Decimal)
        or not ceiling_attack_drawdown_window2_upper.is_finite()
        or ceiling_attack_drawdown_window2_upper
        <= ceiling_attack_drawdown_window2_lower
        or ceiling_attack_drawdown_window2_upper > 1
        or ceiling_attack_drawdown_window2_multiplier_lower is None
        or not isinstance(ceiling_attack_drawdown_window2_multiplier_lower, int)
        or isinstance(ceiling_attack_drawdown_window2_multiplier_lower, bool)
        or ceiling_attack_drawdown_window2_multiplier_lower
        < ATTACK_MINIMUM_MULTIPLIER
        or ceiling_attack_drawdown_window2_multiplier_upper is None
        or not isinstance(ceiling_attack_drawdown_window2_multiplier_upper, int)
        or isinstance(ceiling_attack_drawdown_window2_multiplier_upper, bool)
        or ceiling_attack_drawdown_window2_multiplier_upper
        < ceiling_attack_drawdown_window2_multiplier_lower
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window2 bounds are invalid"
        )
    if (
        not isinstance(ceiling_attack_drawdown_window2_taper_fraction, Decimal)
        or not ceiling_attack_drawdown_window2_taper_fraction.is_finite()
        or ceiling_attack_drawdown_window2_taper_fraction <= 0
        or ceiling_attack_drawdown_window2_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window2 taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_drawdown_window2_lower is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window2 taper requires ceiling discovery mode"
        )
    window3_values = (
        ceiling_attack_drawdown_window3_lower,
        ceiling_attack_drawdown_window3_upper,
        ceiling_attack_drawdown_window3_multiplier_lower,
        ceiling_attack_drawdown_window3_multiplier_upper,
    )
    if any(value is None for value in window3_values) and any(
        value is not None for value in window3_values
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window3 taper requires all four window bounds"
        )
    if ceiling_attack_drawdown_window3_lower is not None and (
        not isinstance(ceiling_attack_drawdown_window3_lower, Decimal)
        or not ceiling_attack_drawdown_window3_lower.is_finite()
        or ceiling_attack_drawdown_window3_lower < 0
        or ceiling_attack_drawdown_window3_upper is None
        or not isinstance(ceiling_attack_drawdown_window3_upper, Decimal)
        or not ceiling_attack_drawdown_window3_upper.is_finite()
        or ceiling_attack_drawdown_window3_upper
        <= ceiling_attack_drawdown_window3_lower
        or ceiling_attack_drawdown_window3_upper > 1
        or ceiling_attack_drawdown_window3_multiplier_lower is None
        or not isinstance(ceiling_attack_drawdown_window3_multiplier_lower, int)
        or isinstance(ceiling_attack_drawdown_window3_multiplier_lower, bool)
        or ceiling_attack_drawdown_window3_multiplier_lower
        < ATTACK_MINIMUM_MULTIPLIER
        or ceiling_attack_drawdown_window3_multiplier_upper is None
        or not isinstance(ceiling_attack_drawdown_window3_multiplier_upper, int)
        or isinstance(ceiling_attack_drawdown_window3_multiplier_upper, bool)
        or ceiling_attack_drawdown_window3_multiplier_upper
        < ceiling_attack_drawdown_window3_multiplier_lower
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window3 bounds are invalid"
        )
    if (
        not isinstance(ceiling_attack_drawdown_window3_taper_fraction, Decimal)
        or not ceiling_attack_drawdown_window3_taper_fraction.is_finite()
        or ceiling_attack_drawdown_window3_taper_fraction <= 0
        or ceiling_attack_drawdown_window3_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window3 taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_drawdown_window3_lower is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window3 taper requires ceiling discovery mode"
        )
    window4_values = (
        ceiling_attack_drawdown_window4_lower,
        ceiling_attack_drawdown_window4_upper,
        ceiling_attack_drawdown_window4_multiplier_lower,
        ceiling_attack_drawdown_window4_multiplier_upper,
    )
    if any(value is None for value in window4_values) and any(
        value is not None for value in window4_values
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window4 taper requires all four window bounds"
        )
    if ceiling_attack_drawdown_window4_lower is not None and (
        not isinstance(ceiling_attack_drawdown_window4_lower, Decimal)
        or not ceiling_attack_drawdown_window4_lower.is_finite()
        or ceiling_attack_drawdown_window4_lower < 0
        or ceiling_attack_drawdown_window4_upper is None
        or not isinstance(ceiling_attack_drawdown_window4_upper, Decimal)
        or not ceiling_attack_drawdown_window4_upper.is_finite()
        or ceiling_attack_drawdown_window4_upper
        <= ceiling_attack_drawdown_window4_lower
        or ceiling_attack_drawdown_window4_upper > 1
        or ceiling_attack_drawdown_window4_multiplier_lower is None
        or not isinstance(ceiling_attack_drawdown_window4_multiplier_lower, int)
        or isinstance(ceiling_attack_drawdown_window4_multiplier_lower, bool)
        or ceiling_attack_drawdown_window4_multiplier_lower
        < ATTACK_MINIMUM_MULTIPLIER
        or ceiling_attack_drawdown_window4_multiplier_upper is None
        or not isinstance(ceiling_attack_drawdown_window4_multiplier_upper, int)
        or isinstance(ceiling_attack_drawdown_window4_multiplier_upper, bool)
        or ceiling_attack_drawdown_window4_multiplier_upper
        < ceiling_attack_drawdown_window4_multiplier_lower
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window4 bounds are invalid"
        )
    if (
        not isinstance(ceiling_attack_drawdown_window4_taper_fraction, Decimal)
        or not ceiling_attack_drawdown_window4_taper_fraction.is_finite()
        or ceiling_attack_drawdown_window4_taper_fraction <= 0
        or ceiling_attack_drawdown_window4_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window4 taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_drawdown_window4_lower is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window4 taper requires ceiling discovery mode"
        )
    window5_values = (
        ceiling_attack_drawdown_window5_lower,
        ceiling_attack_drawdown_window5_upper,
        ceiling_attack_drawdown_window5_multiplier_lower,
        ceiling_attack_drawdown_window5_multiplier_upper,
    )
    if any(value is None for value in window5_values) and any(
        value is not None for value in window5_values
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window5 taper requires all four window bounds"
        )
    if ceiling_attack_drawdown_window5_lower is not None and (
        not isinstance(ceiling_attack_drawdown_window5_lower, Decimal)
        or not ceiling_attack_drawdown_window5_lower.is_finite()
        or ceiling_attack_drawdown_window5_lower < 0
        or ceiling_attack_drawdown_window5_upper is None
        or not isinstance(ceiling_attack_drawdown_window5_upper, Decimal)
        or not ceiling_attack_drawdown_window5_upper.is_finite()
        or ceiling_attack_drawdown_window5_upper
        <= ceiling_attack_drawdown_window5_lower
        or ceiling_attack_drawdown_window5_upper > 1
        or ceiling_attack_drawdown_window5_multiplier_lower is None
        or not isinstance(ceiling_attack_drawdown_window5_multiplier_lower, int)
        or isinstance(ceiling_attack_drawdown_window5_multiplier_lower, bool)
        or ceiling_attack_drawdown_window5_multiplier_lower
        < ATTACK_MINIMUM_MULTIPLIER
        or ceiling_attack_drawdown_window5_multiplier_upper is None
        or not isinstance(ceiling_attack_drawdown_window5_multiplier_upper, int)
        or isinstance(ceiling_attack_drawdown_window5_multiplier_upper, bool)
        or ceiling_attack_drawdown_window5_multiplier_upper
        < ceiling_attack_drawdown_window5_multiplier_lower
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window5 bounds are invalid"
        )
    if (
        not isinstance(ceiling_attack_drawdown_window5_taper_fraction, Decimal)
        or not ceiling_attack_drawdown_window5_taper_fraction.is_finite()
        or ceiling_attack_drawdown_window5_taper_fraction <= 0
        or ceiling_attack_drawdown_window5_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window5 taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_drawdown_window5_lower is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window5 taper requires ceiling discovery mode"
        )
    window6_values = (
        ceiling_attack_drawdown_window6_lower,
        ceiling_attack_drawdown_window6_upper,
        ceiling_attack_drawdown_window6_multiplier_lower,
        ceiling_attack_drawdown_window6_multiplier_upper,
    )
    if any(value is None for value in window6_values) and any(
        value is not None for value in window6_values
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window6 taper requires all four window bounds"
        )
    if ceiling_attack_drawdown_window6_lower is not None and (
        not isinstance(ceiling_attack_drawdown_window6_lower, Decimal)
        or not ceiling_attack_drawdown_window6_lower.is_finite()
        or ceiling_attack_drawdown_window6_lower < 0
        or ceiling_attack_drawdown_window6_upper is None
        or not isinstance(ceiling_attack_drawdown_window6_upper, Decimal)
        or not ceiling_attack_drawdown_window6_upper.is_finite()
        or ceiling_attack_drawdown_window6_upper
        <= ceiling_attack_drawdown_window6_lower
        or ceiling_attack_drawdown_window6_upper > 1
        or ceiling_attack_drawdown_window6_multiplier_lower is None
        or not isinstance(ceiling_attack_drawdown_window6_multiplier_lower, int)
        or isinstance(ceiling_attack_drawdown_window6_multiplier_lower, bool)
        or ceiling_attack_drawdown_window6_multiplier_lower
        < ATTACK_MINIMUM_MULTIPLIER
        or ceiling_attack_drawdown_window6_multiplier_upper is None
        or not isinstance(ceiling_attack_drawdown_window6_multiplier_upper, int)
        or isinstance(ceiling_attack_drawdown_window6_multiplier_upper, bool)
        or ceiling_attack_drawdown_window6_multiplier_upper
        < ceiling_attack_drawdown_window6_multiplier_lower
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window6 bounds are invalid"
        )
    if (
        not isinstance(ceiling_attack_drawdown_window6_taper_fraction, Decimal)
        or not ceiling_attack_drawdown_window6_taper_fraction.is_finite()
        or ceiling_attack_drawdown_window6_taper_fraction <= 0
        or ceiling_attack_drawdown_window6_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window6 taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_drawdown_window6_lower is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window6 taper requires ceiling discovery mode"
        )
    if ceiling_attack_drawdown_window6_capital_floor is not None and (
        not isinstance(ceiling_attack_drawdown_window6_capital_floor, Decimal)
        or not ceiling_attack_drawdown_window6_capital_floor.is_finite()
        or ceiling_attack_drawdown_window6_capital_floor < 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window6 capital floor must be nonnegative Decimal"
        )
    if ceiling_attack_drawdown_window6_capital_ceiling is not None and (
        not isinstance(ceiling_attack_drawdown_window6_capital_ceiling, Decimal)
        or not ceiling_attack_drawdown_window6_capital_ceiling.is_finite()
        or ceiling_attack_drawdown_window6_capital_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window6 capital ceiling must be positive Decimal"
        )
    if (
        ceiling_attack_drawdown_window6_capital_floor is not None
        and ceiling_attack_drawdown_window6_capital_ceiling is not None
        and ceiling_attack_drawdown_window6_capital_floor
        >= ceiling_attack_drawdown_window6_capital_ceiling
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window6 capital floor must be below ceiling"
        )
    window7_values = (
        ceiling_attack_drawdown_window7_lower,
        ceiling_attack_drawdown_window7_upper,
        ceiling_attack_drawdown_window7_multiplier_lower,
        ceiling_attack_drawdown_window7_multiplier_upper,
    )
    if any(value is None for value in window7_values) and any(
        value is not None for value in window7_values
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window7 taper requires all four window bounds"
        )
    if ceiling_attack_drawdown_window7_lower is not None and (
        not isinstance(ceiling_attack_drawdown_window7_lower, Decimal)
        or not ceiling_attack_drawdown_window7_lower.is_finite()
        or ceiling_attack_drawdown_window7_lower < 0
        or ceiling_attack_drawdown_window7_upper is None
        or not isinstance(ceiling_attack_drawdown_window7_upper, Decimal)
        or not ceiling_attack_drawdown_window7_upper.is_finite()
        or ceiling_attack_drawdown_window7_upper
        <= ceiling_attack_drawdown_window7_lower
        or ceiling_attack_drawdown_window7_upper > 1
        or ceiling_attack_drawdown_window7_multiplier_lower is None
        or not isinstance(ceiling_attack_drawdown_window7_multiplier_lower, int)
        or isinstance(ceiling_attack_drawdown_window7_multiplier_lower, bool)
        or ceiling_attack_drawdown_window7_multiplier_lower
        < ATTACK_MINIMUM_MULTIPLIER
        or ceiling_attack_drawdown_window7_multiplier_upper is None
        or not isinstance(ceiling_attack_drawdown_window7_multiplier_upper, int)
        or isinstance(ceiling_attack_drawdown_window7_multiplier_upper, bool)
        or ceiling_attack_drawdown_window7_multiplier_upper
        < ceiling_attack_drawdown_window7_multiplier_lower
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window7 bounds are invalid"
        )
    if (
        not isinstance(ceiling_attack_drawdown_window7_taper_fraction, Decimal)
        or not ceiling_attack_drawdown_window7_taper_fraction.is_finite()
        or ceiling_attack_drawdown_window7_taper_fraction <= 0
        or ceiling_attack_drawdown_window7_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window7 taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_drawdown_window7_lower is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window7 taper requires ceiling discovery mode"
        )
    if ceiling_attack_drawdown_window7_capital_floor is not None and (
        not isinstance(ceiling_attack_drawdown_window7_capital_floor, Decimal)
        or not ceiling_attack_drawdown_window7_capital_floor.is_finite()
        or ceiling_attack_drawdown_window7_capital_floor < 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window7 capital floor must be nonnegative Decimal"
        )
    if ceiling_attack_drawdown_window7_capital_ceiling is not None and (
        not isinstance(ceiling_attack_drawdown_window7_capital_ceiling, Decimal)
        or not ceiling_attack_drawdown_window7_capital_ceiling.is_finite()
        or ceiling_attack_drawdown_window7_capital_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window7 capital ceiling must be positive Decimal"
        )
    if (
        ceiling_attack_drawdown_window7_capital_floor is not None
        and ceiling_attack_drawdown_window7_capital_ceiling is not None
        and ceiling_attack_drawdown_window7_capital_floor
        >= ceiling_attack_drawdown_window7_capital_ceiling
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK drawdown-window7 capital floor must be below ceiling"
        )
    if (
        ceiling_attack_stress_confidence_drawdown_trigger is None
    ) != (
        ceiling_attack_stress_confidence_ratio_ceiling is None
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence ATTACK taper requires both "
            "drawdown trigger and confidence-ratio ceiling"
        )
    if (
        ceiling_attack_stress_confidence_drawdown_trigger is not None
        and (
            not isinstance(
                ceiling_attack_stress_confidence_drawdown_trigger,
                Decimal,
            )
            or not ceiling_attack_stress_confidence_drawdown_trigger.is_finite()
            or ceiling_attack_stress_confidence_drawdown_trigger < 0
            or ceiling_attack_stress_confidence_drawdown_trigger
            >= Decimal("0.50")
        )
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence drawdown trigger must be Decimal "
            "in [0, 0.50)"
        )
    if (
        ceiling_attack_stress_confidence_ratio_ceiling is not None
        and (
            not isinstance(
                ceiling_attack_stress_confidence_ratio_ceiling,
                Decimal,
            )
            or not ceiling_attack_stress_confidence_ratio_ceiling.is_finite()
            or ceiling_attack_stress_confidence_ratio_ceiling <= 0
        )
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence ratio ceiling must be positive Decimal"
        )
    if ceiling_attack_stress_confidence_target_r_floor is not None and (
        not isinstance(ceiling_attack_stress_confidence_target_r_floor, Decimal)
        or not ceiling_attack_stress_confidence_target_r_floor.is_finite()
        or ceiling_attack_stress_confidence_target_r_floor <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence target-R floor must be positive Decimal"
        )
    if (
        ceiling_attack_stress_confidence_multiplier_lower is None
    ) != (
        ceiling_attack_stress_confidence_multiplier_upper is None
    ):
        raise CiboCapitalManagementError(
            "Trader Lab localized stress-confidence requires both multiplier bounds"
        )
    if ceiling_attack_stress_confidence_multiplier_lower is not None and (
        not isinstance(ceiling_attack_stress_confidence_multiplier_lower, int)
        or isinstance(ceiling_attack_stress_confidence_multiplier_lower, bool)
        or ceiling_attack_stress_confidence_multiplier_lower < ATTACK_MINIMUM_MULTIPLIER
        or ceiling_attack_stress_confidence_multiplier_upper is None
        or not isinstance(ceiling_attack_stress_confidence_multiplier_upper, int)
        or isinstance(ceiling_attack_stress_confidence_multiplier_upper, bool)
        or ceiling_attack_stress_confidence_multiplier_upper
        < ceiling_attack_stress_confidence_multiplier_lower
    ):
        raise CiboCapitalManagementError(
            "Trader Lab localized stress-confidence multiplier bounds are invalid"
        )
    if (
        ceiling_attack_stress_confidence_projected_risk_fraction_trigger
        is not None
        and (
            not isinstance(
                ceiling_attack_stress_confidence_projected_risk_fraction_trigger,
                Decimal,
            )
            or not ceiling_attack_stress_confidence_projected_risk_fraction_trigger.is_finite()
            or ceiling_attack_stress_confidence_projected_risk_fraction_trigger <= 0
            or ceiling_attack_stress_confidence_projected_risk_fraction_trigger > 1
        )
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence projected risk trigger must be Decimal in (0, 1]"
        )
    if ceiling_attack_stress_confidence_capital_floor is not None and (
        not isinstance(ceiling_attack_stress_confidence_capital_floor, Decimal)
        or not ceiling_attack_stress_confidence_capital_floor.is_finite()
        or ceiling_attack_stress_confidence_capital_floor < 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence capital floor must be nonnegative Decimal"
        )
    if ceiling_attack_stress_confidence_capital_ceiling is not None and (
        not isinstance(ceiling_attack_stress_confidence_capital_ceiling, Decimal)
        or not ceiling_attack_stress_confidence_capital_ceiling.is_finite()
        or ceiling_attack_stress_confidence_capital_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence capital ceiling must be positive Decimal"
        )
    if (
        ceiling_attack_stress_confidence_capital_floor is not None
        and ceiling_attack_stress_confidence_capital_ceiling is not None
        and ceiling_attack_stress_confidence_capital_floor
        >= ceiling_attack_stress_confidence_capital_ceiling
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence capital floor must be below ceiling"
        )
    if (
        not isinstance(
            ceiling_attack_stress_confidence_risk_budget_taper_fraction,
            Decimal,
        )
        or not ceiling_attack_stress_confidence_risk_budget_taper_fraction.is_finite()
        or ceiling_attack_stress_confidence_risk_budget_taper_fraction <= 0
        or ceiling_attack_stress_confidence_risk_budget_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence risk-budget taper fraction must be Decimal in (0, 1]"
        )
    if ceiling_attack_state_pressure_expected_minutes_floor is not None and (
        not isinstance(ceiling_attack_state_pressure_expected_minutes_floor, Decimal)
        or not ceiling_attack_state_pressure_expected_minutes_floor.is_finite()
        or ceiling_attack_state_pressure_expected_minutes_floor <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure expected-minutes floor must be positive Decimal"
        )
    if ceiling_attack_state_pressure_target_r_ceiling is not None and (
        not isinstance(ceiling_attack_state_pressure_target_r_ceiling, Decimal)
        or not ceiling_attack_state_pressure_target_r_ceiling.is_finite()
        or ceiling_attack_state_pressure_target_r_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure target-R ceiling must be positive Decimal"
        )
    if ceiling_attack_state_pressure_confidence_ratio_ceiling is not None and (
        not isinstance(ceiling_attack_state_pressure_confidence_ratio_ceiling, Decimal)
        or not ceiling_attack_state_pressure_confidence_ratio_ceiling.is_finite()
        or ceiling_attack_state_pressure_confidence_ratio_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure confidence-ratio ceiling must be positive Decimal"
        )
    if (
        ceiling_attack_state_pressure_projected_risk_fraction_trigger is not None
        and (
            not isinstance(
                ceiling_attack_state_pressure_projected_risk_fraction_trigger,
                Decimal,
            )
            or not ceiling_attack_state_pressure_projected_risk_fraction_trigger.is_finite()
            or ceiling_attack_state_pressure_projected_risk_fraction_trigger <= 0
            or ceiling_attack_state_pressure_projected_risk_fraction_trigger > 1
        )
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure projected-risk trigger must be Decimal in (0, 1]"
        )
    for name, value in (
        ("state-pressure capital floor", ceiling_attack_state_pressure_capital_floor),
        ("state-pressure capital ceiling", ceiling_attack_state_pressure_capital_ceiling),
    ):
        if value is not None and (
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value <= 0
        ):
            raise CiboCapitalManagementError(
                f"Trader Lab ATTACK {name} must be positive Decimal"
            )
    if (
        ceiling_attack_state_pressure_capital_floor is not None
        and ceiling_attack_state_pressure_capital_ceiling is not None
        and ceiling_attack_state_pressure_capital_floor
        >= ceiling_attack_state_pressure_capital_ceiling
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure capital floor must be below ceiling"
        )
    if (
        ceiling_attack_state_pressure_market_posture is not None
        and ceiling_attack_state_pressure_market_posture
        not in {"DEFENSIVE", "RECOVERY", "STABLE", "WATCH"}
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure market posture is invalid"
        )
    if (
        ceiling_attack_state_pressure_h1_range_state is not None
        and ceiling_attack_state_pressure_h1_range_state
        not in {"balanced", "compressed", "expanded", "extreme"}
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure H1 range state is invalid"
        )
    if (
        ceiling_attack_state_pressure_h4_range_state is not None
        and ceiling_attack_state_pressure_h4_range_state
        not in {"balanced", "compressed", "expanded", "extreme"}
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure H4 range state is invalid"
        )
    if (
        not isinstance(
            ceiling_attack_state_pressure_risk_budget_taper_fraction,
            Decimal,
        )
        or not ceiling_attack_state_pressure_risk_budget_taper_fraction.is_finite()
        or ceiling_attack_state_pressure_risk_budget_taper_fraction <= 0
        or ceiling_attack_state_pressure_risk_budget_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure risk taper must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_state_pressure_expected_minutes_floor is None
        and (
            ceiling_attack_state_pressure_target_r_ceiling is not None
            or ceiling_attack_state_pressure_confidence_ratio_ceiling is not None
            or ceiling_attack_state_pressure_projected_risk_fraction_trigger is not None
            or ceiling_attack_state_pressure_capital_floor is not None
            or ceiling_attack_state_pressure_capital_ceiling is not None
            or ceiling_attack_state_pressure_market_posture is not None
            or ceiling_attack_state_pressure_h1_range_state is not None
            or ceiling_attack_state_pressure_h4_range_state is not None
            or ceiling_attack_state_pressure_risk_budget_taper_fraction
            != Decimal("1")
        )
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure gates require expected-minutes floor"
        )
    if (
        ceiling_attack_state_pressure_expected_minutes_floor is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure taper requires ceiling discovery mode"
        )
    if ceiling_attack_state_pressure2_expected_minutes_floor is not None and (
        not isinstance(ceiling_attack_state_pressure2_expected_minutes_floor, Decimal)
        or not ceiling_attack_state_pressure2_expected_minutes_floor.is_finite()
        or ceiling_attack_state_pressure2_expected_minutes_floor <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 expected-minutes floor must be positive Decimal"
        )
    if ceiling_attack_state_pressure2_target_r_ceiling is not None and (
        not isinstance(ceiling_attack_state_pressure2_target_r_ceiling, Decimal)
        or not ceiling_attack_state_pressure2_target_r_ceiling.is_finite()
        or ceiling_attack_state_pressure2_target_r_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 target-R ceiling must be positive Decimal"
        )
    if ceiling_attack_state_pressure2_confidence_ratio_ceiling is not None and (
        not isinstance(ceiling_attack_state_pressure2_confidence_ratio_ceiling, Decimal)
        or not ceiling_attack_state_pressure2_confidence_ratio_ceiling.is_finite()
        or ceiling_attack_state_pressure2_confidence_ratio_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 confidence-ratio ceiling must be positive Decimal"
        )
    if (
        ceiling_attack_state_pressure2_projected_risk_fraction_trigger is not None
        and (
            not isinstance(
                ceiling_attack_state_pressure2_projected_risk_fraction_trigger,
                Decimal,
            )
            or not ceiling_attack_state_pressure2_projected_risk_fraction_trigger.is_finite()
            or ceiling_attack_state_pressure2_projected_risk_fraction_trigger <= 0
            or ceiling_attack_state_pressure2_projected_risk_fraction_trigger > 1
        )
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 projected-risk trigger must be Decimal in (0, 1]"
        )
    for name, value in (
        ("state-pressure2 capital floor", ceiling_attack_state_pressure2_capital_floor),
        ("state-pressure2 capital ceiling", ceiling_attack_state_pressure2_capital_ceiling),
    ):
        if value is not None and (
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value <= 0
        ):
            raise CiboCapitalManagementError(
                f"Trader Lab ATTACK {name} must be positive Decimal"
            )
    if (
        ceiling_attack_state_pressure2_capital_floor is not None
        and ceiling_attack_state_pressure2_capital_ceiling is not None
        and ceiling_attack_state_pressure2_capital_floor
        >= ceiling_attack_state_pressure2_capital_ceiling
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 capital floor must be below ceiling"
        )
    if (
        ceiling_attack_state_pressure2_market_posture is not None
        and ceiling_attack_state_pressure2_market_posture
        not in {"DEFENSIVE", "RECOVERY", "STABLE", "WATCH"}
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 market posture is invalid"
        )
    if (
        ceiling_attack_state_pressure2_h1_range_state is not None
        and ceiling_attack_state_pressure2_h1_range_state
        not in {"balanced", "compressed", "expanded", "extreme"}
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 H1 range state is invalid"
        )
    if (
        ceiling_attack_state_pressure2_h4_range_state is not None
        and ceiling_attack_state_pressure2_h4_range_state
        not in {"balanced", "compressed", "expanded", "extreme"}
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 H4 range state is invalid"
        )
    if (
        not isinstance(
            ceiling_attack_state_pressure2_cap_taper_fraction,
            Decimal,
        )
        or not ceiling_attack_state_pressure2_cap_taper_fraction.is_finite()
        or ceiling_attack_state_pressure2_cap_taper_fraction <= 0
        or ceiling_attack_state_pressure2_cap_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 cap taper must be Decimal in (0, 1]"
        )
    if (
        not isinstance(
            ceiling_attack_state_pressure2_risk_budget_taper_fraction,
            Decimal,
        )
        or not ceiling_attack_state_pressure2_risk_budget_taper_fraction.is_finite()
        or ceiling_attack_state_pressure2_risk_budget_taper_fraction <= 0
        or ceiling_attack_state_pressure2_risk_budget_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 risk taper must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_state_pressure2_expected_minutes_floor is None
        and (
            ceiling_attack_state_pressure2_target_r_ceiling is not None
            or ceiling_attack_state_pressure2_confidence_ratio_ceiling is not None
            or ceiling_attack_state_pressure2_projected_risk_fraction_trigger is not None
            or ceiling_attack_state_pressure2_capital_floor is not None
            or ceiling_attack_state_pressure2_capital_ceiling is not None
            or ceiling_attack_state_pressure2_market_posture is not None
            or ceiling_attack_state_pressure2_h1_range_state is not None
            or ceiling_attack_state_pressure2_h4_range_state is not None
            or ceiling_attack_state_pressure2_cap_taper_fraction
            != Decimal("1")
            or ceiling_attack_state_pressure2_risk_budget_taper_fraction
            != Decimal("1")
        )
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 gates require expected-minutes floor"
        )
    if (
        ceiling_attack_state_pressure2_expected_minutes_floor is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK state-pressure2 taper requires ceiling discovery mode"
        )
    if (
        not isinstance(
            ceiling_attack_stress_confidence_taper_fraction,
            Decimal,
        )
        or not ceiling_attack_stress_confidence_taper_fraction.is_finite()
        or ceiling_attack_stress_confidence_taper_fraction <= 0
        or ceiling_attack_stress_confidence_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_stress_confidence_drawdown_trigger is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab stress-confidence ATTACK taper requires ceiling discovery mode"
        )
    if ceiling_attack_trader_loss_ratio_trigger is not None and (
        not isinstance(ceiling_attack_trader_loss_ratio_trigger, Decimal)
        or not ceiling_attack_trader_loss_ratio_trigger.is_finite()
        or ceiling_attack_trader_loss_ratio_trigger <= 0
        or ceiling_attack_trader_loss_ratio_trigger > Decimal("10")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab Trader ATTACK loss/profit ratio trigger must be Decimal in (0, 10]"
        )
    if (
        not isinstance(ceiling_attack_trader_loss_ratio_min_settlements, int)
        or isinstance(ceiling_attack_trader_loss_ratio_min_settlements, bool)
        or ceiling_attack_trader_loss_ratio_min_settlements < 1
        or ceiling_attack_trader_loss_ratio_min_settlements > 1000
    ):
        raise CiboCapitalManagementError(
            "Trader Lab Trader ATTACK loss/profit ratio minimum settlements must be int in [1, 1000]"
        )
    if (
        not isinstance(ceiling_attack_trader_loss_ratio_taper_fraction, Decimal)
        or not ceiling_attack_trader_loss_ratio_taper_fraction.is_finite()
        or ceiling_attack_trader_loss_ratio_taper_fraction <= 0
        or ceiling_attack_trader_loss_ratio_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab Trader ATTACK loss/profit ratio taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_trader_loss_ratio_trigger is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab Trader ATTACK loss/profit ratio taper requires ceiling discovery mode"
        )
    if (
        ceiling_attack_recent_trader_loss_window is None
    ) != (
        ceiling_attack_recent_trader_loss_fraction_trigger is None
    ):
        raise CiboCapitalManagementError(
            "Trader Lab recent-Trader ATTACK loss pressure requires both window and loss fraction trigger"
        )
    if ceiling_attack_recent_trader_loss_window is not None and (
        not isinstance(ceiling_attack_recent_trader_loss_window, int)
        or isinstance(ceiling_attack_recent_trader_loss_window, bool)
        or ceiling_attack_recent_trader_loss_window < 2
        or ceiling_attack_recent_trader_loss_window > 50
    ):
        raise CiboCapitalManagementError(
            "Trader Lab recent-Trader ATTACK loss window must be int in [2, 50]"
        )
    if ceiling_attack_recent_trader_loss_fraction_trigger is not None and (
        not isinstance(ceiling_attack_recent_trader_loss_fraction_trigger, Decimal)
        or not ceiling_attack_recent_trader_loss_fraction_trigger.is_finite()
        or ceiling_attack_recent_trader_loss_fraction_trigger <= 0
        or ceiling_attack_recent_trader_loss_fraction_trigger > Decimal("1")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab recent-Trader ATTACK loss fraction trigger must be Decimal in (0, 1]"
        )
    if (
        not isinstance(ceiling_attack_recent_trader_loss_drawdown_trigger, Decimal)
        or not ceiling_attack_recent_trader_loss_drawdown_trigger.is_finite()
        or ceiling_attack_recent_trader_loss_drawdown_trigger < 0
        or ceiling_attack_recent_trader_loss_drawdown_trigger >= Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab recent-Trader ATTACK loss DD trigger must be Decimal in [0, 0.50)"
        )
    if (
        not isinstance(ceiling_attack_recent_trader_loss_taper_fraction, Decimal)
        or not ceiling_attack_recent_trader_loss_taper_fraction.is_finite()
        or ceiling_attack_recent_trader_loss_taper_fraction <= 0
        or ceiling_attack_recent_trader_loss_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab recent-Trader ATTACK loss taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_recent_trader_loss_window is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab recent-Trader ATTACK loss taper requires ceiling discovery mode"
        )
    if ceiling_attack_trader_shock_trigger_fraction is not None and (
        not isinstance(ceiling_attack_trader_shock_trigger_fraction, Decimal)
        or not ceiling_attack_trader_shock_trigger_fraction.is_finite()
        or ceiling_attack_trader_shock_trigger_fraction <= 0
        or ceiling_attack_trader_shock_trigger_fraction > Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab Trader one-shot shock trigger must be Decimal in (0, 0.50]"
        )
    if (
        not isinstance(ceiling_attack_trader_shock_drawdown_trigger, Decimal)
        or not ceiling_attack_trader_shock_drawdown_trigger.is_finite()
        or ceiling_attack_trader_shock_drawdown_trigger < 0
        or ceiling_attack_trader_shock_drawdown_trigger >= Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab Trader one-shot shock DD trigger must be Decimal in [0, 0.50)"
        )
    if ceiling_attack_trader_shock_capital_ceiling is not None and (
        not isinstance(ceiling_attack_trader_shock_capital_ceiling, Decimal)
        or not ceiling_attack_trader_shock_capital_ceiling.is_finite()
        or ceiling_attack_trader_shock_capital_ceiling <= 0
    ):
        raise CiboCapitalManagementError(
            "Trader Lab Trader one-shot shock capital ceiling must be positive Decimal"
        )
    if (
        not isinstance(ceiling_attack_trader_shock_taper_fraction, Decimal)
        or not ceiling_attack_trader_shock_taper_fraction.is_finite()
        or ceiling_attack_trader_shock_taper_fraction <= 0
        or ceiling_attack_trader_shock_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab Trader one-shot shock taper must be Decimal in (0, 1]"
        )
    if (
        ceiling_attack_trader_shock_trigger_fraction is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab Trader one-shot shock requires ceiling discovery mode"
        )
    if ceiling_attack_low_multiplier_demotion_upper is not None and (
        not isinstance(ceiling_attack_low_multiplier_demotion_upper, int)
        or isinstance(ceiling_attack_low_multiplier_demotion_upper, bool)
        or ceiling_attack_low_multiplier_demotion_upper < ATTACK_MINIMUM_MULTIPLIER
    ):
        raise CiboCapitalManagementError(
            "Trader Lab low-multiplier ATTACK demotion upper must be int >= ATTACK minimum"
        )
    if (
        not isinstance(ceiling_attack_low_multiplier_demotion_drawdown_trigger, Decimal)
        or not ceiling_attack_low_multiplier_demotion_drawdown_trigger.is_finite()
        or ceiling_attack_low_multiplier_demotion_drawdown_trigger < 0
        or ceiling_attack_low_multiplier_demotion_drawdown_trigger >= Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab low-multiplier ATTACK demotion DD trigger must be Decimal in [0, 0.50)"
        )
    if (
        ceiling_attack_low_multiplier_demotion_upper is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab low-multiplier ATTACK demotion requires ceiling discovery mode"
        )
    if ceiling_portfolio_shock_trigger_fraction is not None and (
        not isinstance(ceiling_portfolio_shock_trigger_fraction, Decimal)
        or not ceiling_portfolio_shock_trigger_fraction.is_finite()
        or ceiling_portfolio_shock_trigger_fraction <= 0
        or ceiling_portfolio_shock_trigger_fraction > Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling Portfolio shock trigger must be Decimal in (0, 0.50]"
        )
    if (
        not isinstance(ceiling_portfolio_shock_taper_fraction, Decimal)
        or not ceiling_portfolio_shock_taper_fraction.is_finite()
        or ceiling_portfolio_shock_taper_fraction <= 0
        or ceiling_portfolio_shock_taper_fraction > 1
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling Portfolio shock taper fraction must be Decimal in (0, 1]"
        )
    if (
        ceiling_portfolio_shock_trigger_fraction is not None
        and not ceiling_discovery_mode
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ceiling Portfolio shock taper requires ceiling discovery mode"
        )
    if type(ceiling_portfolio_shock_one_shot) is not bool:
        raise CiboCapitalManagementError(
            "Trader Lab ceiling Portfolio shock one-shot switch must be bool"
        )
    if compound_profit_reinvestment_fraction is not None and (
        not isinstance(compound_profit_reinvestment_fraction, Decimal)
        or not compound_profit_reinvestment_fraction.is_finite()
        or compound_profit_reinvestment_fraction <= 0
        or compound_profit_reinvestment_fraction > Decimal(1)
    ):
        raise CiboCapitalManagementError(
            "Trader Lab compound profit reinvestment fraction must be Decimal in (0, 1]"
        )
    if economic_group_ablation not in {
        None,
        "SIZING",
        "CIBO_COMPOUND",
        "COMPOUND_PORTFOLIO",
        "ADAPTIVE_LEVERAGE",
    }:
        raise CiboCapitalManagementError(
            "Trader Lab economic group ablation must name one canonical function"
        )
    if (
        not isinstance(economic_group_bootstrap_cushion_share, Decimal)
        or not economic_group_bootstrap_cushion_share.is_finite()
        or economic_group_bootstrap_cushion_share < Decimal("0.50")
        or economic_group_bootstrap_cushion_share > Decimal("1.00")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab economic-group bootstrap cushion share must be Decimal in [0.50, 1.00]"
        )
    if (
        not isinstance(attack_multiplier_cap, int)
        or isinstance(attack_multiplier_cap, bool)
        or attack_multiplier_cap < ATTACK_MINIMUM_MULTIPLIER
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ATTACK multiplier cap must be int >= 2; "
            "provider/risk/margin/cushion caps remain authoritative"
        )
    if (
        not isinstance(medium_multiplier_cap, int)
        or isinstance(medium_multiplier_cap, bool)
        or medium_multiplier_cap < 1
        or medium_multiplier_cap > 20
    ):
        raise CiboCapitalManagementError(
            "Trader Lab MEDIUM multiplier cap must be int in [1, 20]"
        )
    if medium_drawdown_intensity_trigger is not None and (
        not isinstance(medium_drawdown_intensity_trigger, Decimal)
        or not medium_drawdown_intensity_trigger.is_finite()
        or medium_drawdown_intensity_trigger < 0
        or medium_drawdown_intensity_trigger >= Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab MEDIUM drawdown intensity trigger must be Decimal in [0, 0.50)"
        )
    if (
        not isinstance(medium_pretrade_drawdown_ceiling, Decimal)
        or not medium_pretrade_drawdown_ceiling.is_finite()
        or medium_pretrade_drawdown_ceiling < ECONOMIC_DRAWDOWN_CEILING
        or medium_pretrade_drawdown_ceiling > Decimal("0.50")
    ):
        raise CiboCapitalManagementError(
            "Trader Lab MEDIUM pretrade drawdown ceiling must be Decimal "
            "between 0.25 and 0.50"
        )
    source_sha = validate_single_account_manifest_sha256(manifest)
    if manifest.get("initial_capital_usd") != "60":
        raise CiboCapitalManagementError(
            "Trader Lab three-mode requires the canonical USD60 manifest"
        )
    rows_raw = manifest.get("opportunities")
    if not isinstance(rows_raw, list) or not rows_raw:
        raise CiboCapitalManagementError(
            "Trader Lab three-mode manifest has no opportunities"
        )
    rows = [_mapping(row, "manifest opportunity") for row in rows_raw]
    signals = tuple(str(row.get("signal_fingerprint", "")) for row in rows)
    lifecycle_map: dict[str, dict[str, object]] = {}
    if lifecycle_by_signal is not None:
        lifecycle_map = {
            str(signal): dict(profile)
            for signal, profile in lifecycle_by_signal.items()
        }
        if set(lifecycle_map) != set(signals):
            raise CiboCapitalManagementError(
                "Trader Lab lifecycle map must cover exact manifest signals"
            )
        for signal, profile in lifecycle_map.items():
            managed = Decimal(str(profile.get("managed_gross_r")))
            original = Decimal(str(profile.get("original_gross_r")))
            adverse_loss_cut_r = Decimal(
                str(profile.get("adverse_loss_cut_r"))
            )
            if (
                not managed.is_finite()
                or not original.is_finite()
                or not adverse_loss_cut_r.is_finite()
                or type(profile.get("data_available")) is not bool
                or not isinstance(profile.get("managed_exit_at"), str)
                or not isinstance(profile.get("actions"), (list, tuple))
                or not isinstance(profile.get("enabled_features"), (list, tuple))
                or not isinstance(profile.get("events"), (list, tuple))
                or not profile.get("events")
                or any(
                    not isinstance(item, CiboLifecycleEvent)
                    for item in profile["events"]
                )
            ):
                raise CiboCapitalManagementError(
                    f"Trader Lab lifecycle profile malformed for {signal}"
                )
            _dt(profile["managed_exit_at"], "lifecycle managed_exit_at")

    lifecycle_bootstrap_override_map: dict[str, dict[str, object]] = {}
    if lifecycle_bootstrap_override_by_signal is not None:
        lifecycle_bootstrap_override_map = {
            str(signal): dict(profile)
            for signal, profile in lifecycle_bootstrap_override_by_signal.items()
        }
        if set(lifecycle_bootstrap_override_map) != set(signals):
            raise CiboCapitalManagementError(
                "Trader Lab bootstrap lifecycle override map must cover exact manifest signals"
            )
        for signal, profile in lifecycle_bootstrap_override_map.items():
            managed = Decimal(str(profile.get("managed_gross_r")))
            original = Decimal(str(profile.get("original_gross_r")))
            if (
                not managed.is_finite()
                or not original.is_finite()
                or type(profile.get("data_available")) is not bool
                or not isinstance(profile.get("managed_exit_at"), str)
                or not isinstance(profile.get("events"), (list, tuple))
                or not profile.get("events")
                or any(
                    not isinstance(item, CiboLifecycleEvent)
                    for item in profile["events"]
                )
            ):
                raise CiboCapitalManagementError(
                    f"Trader Lab bootstrap lifecycle override profile malformed for {signal}"
                )
            _dt(
                profile["managed_exit_at"],
                "bootstrap lifecycle override managed_exit_at",
            )

    lifecycle_attack_override_map: dict[str, dict[str, object]] = {}
    if lifecycle_attack_override_by_signal is not None:
        lifecycle_attack_override_map = {
            str(signal): dict(profile)
            for signal, profile in lifecycle_attack_override_by_signal.items()
        }
        if set(lifecycle_attack_override_map) != set(signals):
            raise CiboCapitalManagementError(
                "Trader Lab ATTACK lifecycle override map must cover exact manifest signals"
            )
        for signal, profile in lifecycle_attack_override_map.items():
            managed = Decimal(str(profile.get("managed_gross_r")))
            original = Decimal(str(profile.get("original_gross_r")))
            if (
                not managed.is_finite()
                or not original.is_finite()
                or type(profile.get("data_available")) is not bool
                or not isinstance(profile.get("managed_exit_at"), str)
                or not isinstance(profile.get("events"), (list, tuple))
                or not profile.get("events")
                or any(
                    not isinstance(item, CiboLifecycleEvent)
                    for item in profile["events"]
                )
            ):
                raise CiboCapitalManagementError(
                    f"Trader Lab ATTACK lifecycle override profile malformed for {signal}"
                )
            _dt(
                profile["managed_exit_at"],
                "ATTACK lifecycle override managed_exit_at",
            )

    lifecycle_action_counts: Counter[str] = Counter()
    lifecycle_feature_sets = {
        tuple(str(item) for item in profile["enabled_features"])
        for profile in lifecycle_map.values()
    }
    lifecycle_feature_codes = sorted(
        {
            str(item)
            for profile in lifecycle_map.values()
            for item in profile["enabled_features"]
        }
    )
    lifecycle_feature_surface_mixed = len(lifecycle_feature_sets) > 1
    lifecycle_loss_cut_thresholds = {
        Decimal(str(profile["adverse_loss_cut_r"]))
        for profile in lifecycle_map.values()
    }
    if len(lifecycle_loss_cut_thresholds) > 1:
        raise CiboCapitalManagementError(
            "Trader Lab lifecycle adverse loss-cut threshold must be uniform"
        )
    lifecycle_adverse_loss_cut_r = (
        next(iter(lifecycle_loss_cut_thresholds))
        if lifecycle_loss_cut_thresholds
        else None
    )
    lifecycle_data_available_count = 0
    lifecycle_changed_count = 0
    lifecycle_applied_trade_count = 0
    lifecycle_bootstrap_override_applied_count = 0
    lifecycle_attack_override_applied_count = 0
    lifecycle_attack_override_projected_risk_blocked_count = 0
    lifecycle_drawdown_trigger_blocked_count = 0
    lifecycle_trader_loss_streak_blocked_count = 0
    lifecycle_bootstrap_capital_blocked_count = 0
    lifecycle_minimum_stop_risk_fraction_blocked_count = 0
    lifecycle_projected_open_stop_risk_fraction_blocked_count = 0
    for profile in lifecycle_map.values():
        lifecycle_data_available_count += int(bool(profile["data_available"]))
        lifecycle_changed_count += int(
            Decimal(str(profile["managed_gross_r"]))
            != Decimal(str(profile["original_gross_r"]))
        )
        for action in profile["actions"]:
            lifecycle_action_counts[str(action)] += 1
    position_lifecycle_report = {
        "enabled": bool(lifecycle_map),
        "entry_count": len(signals),
        "data_available_count": lifecycle_data_available_count,
        "fallback_original_settlement_count": (
            len(signals) - lifecycle_data_available_count if lifecycle_map else 0
        ),
        "changed_outcome_count": lifecycle_changed_count,
        "action_counts": dict(sorted(lifecycle_action_counts.items())),
        "enabled_feature_codes": lifecycle_feature_codes,
        "mixed_feature_surface": lifecycle_feature_surface_mixed,
        "feature_surface_variant_count": len(lifecycle_feature_sets),
        "adverse_loss_cut_r": (
            None
            if lifecycle_adverse_loss_cut_r is None
            else format(lifecycle_adverse_loss_cut_r, "f")
        ),
        "causal_closed_bar_only": bool(lifecycle_map),
        "outcome_used_for_trigger": False,
    }

    cognitive_map: dict[str, bool | None] = {
        signal: (
            None
            if cognitive_recommend_by_signal is None
            else cognitive_recommend_by_signal.get(signal)
        )
        for signal in signals
    }
    if any(
        value is not None and type(value) is not bool
        for value in cognitive_map.values()
    ):
        raise CiboCapitalManagementError(
            "Trader Lab cognitive recommendation telemetry must be bool/null"
        )

    def _default_native_profile(
        signal: str,
    ) -> dict[str, object]:
        recommendation = cognitive_map[signal]
        return {
            "telemetry_state": (
                "AVAILABLE"
                if type(recommendation) is bool
                else "UNAVAILABLE"
            ),
            "missing_components": [],
            "executive_synthesis": (
                "recommend"
                if recommendation is True
                else "abstain"
                if recommendation is False
                else "UNAVAILABLE"
            ),
            "reasoning_routing": "UNAVAILABLE",
            "calibration": "UNAVAILABLE",
            "confidence_band": 0,
            "scenario_abstained_count": 0,
            "metacognition": "UNAVAILABLE",
            "attention_ranked_signal_count": 0,
            "native_maximum_intelligence": True,
            "full_semantics_consumed": True,
        }

    native_profile_map = {
        signal: _default_native_profile(signal)
        for signal in signals
    }
    if native_profile_by_signal is not None:
        for signal, profile in native_profile_by_signal.items():
            key = str(signal)
            if key not in native_profile_map:
                continue
            if isinstance(profile, Mapping):
                native_profile_map[key].update(dict(profile))

    native_telemetry_counts: Counter[str] = Counter()
    for signal, profile in native_profile_map.items():
        state = str(profile.get("telemetry_state", "UNAVAILABLE"))
        if state not in {"AVAILABLE", "PARTIAL", "UNAVAILABLE"}:
            state = "PARTIAL"
        native_telemetry_counts[state] += 1

        confidence = profile.get("confidence_band", 0)
        if (
            not isinstance(confidence, int)
            or isinstance(confidence, bool)
            or confidence < 0
            or confidence > 100
        ):
            profile["confidence_band"] = 0
            state = "PARTIAL"
            profile["telemetry_state"] = state

        executive = str(
            profile.get("executive_synthesis", "UNAVAILABLE")
        )
        recommendation = cognitive_map[signal]
        if recommendation is None and executive in {"recommend", "abstain"}:
            cognitive_map[signal] = executive == "recommend"
            recommendation = cognitive_map[signal]
        elif (
            recommendation is not None
            and executive in {"recommend", "abstain"}
            and recommendation != (executive == "recommend")
        ):
            # Conflicting telemetry is diagnostic only. Keep the explicit
            # recommendation map and downgrade observability.
            profile["telemetry_state"] = "PARTIAL"


    def native_confidence(candidate: CiboThreeModeCandidate) -> int:
        raw = native_profile_map[candidate.signal_fingerprint].get(
            "confidence_band",
            0,
        )
        return int(raw) if isinstance(raw, int) and not isinstance(raw, bool) else 0

    def historical_native_intensity_cap(
        candidate: CiboThreeModeCandidate,
    ) -> int:
        if candidate.native_cognition_recommended is False:
            return min(candidate.maximum_multiplier, 1)
        # Keep the proven historical MEDIUM expression at 4x. Native
        # confidence is consumed as telemetry and by Portfolio/ATTACK; it
        # must not inflate ordinary MEDIUM after the confidence-scaling
        # ablation demonstrated destructive drawdown.
        return min(candidate.maximum_multiplier, 4)

    use_historical_prior = historical_prior_by_signal is not None
    historical_prior_map: dict[str, dict[str, object]] = {}
    if historical_prior_by_signal is not None:
        historical_prior_map = {
            str(signal): dict(profile)
            for signal, profile in historical_prior_by_signal.items()
        }
        if set(historical_prior_map) != set(signals):
            raise CiboCapitalManagementError(
                "Trader Lab historical prior must cover exact manifest signals"
            )
        for signal, profile in historical_prior_map.items():
            edge = Decimal(str(profile.get("expected_edge_after_cost_usd")))
            minutes = Decimal(str(profile.get("expected_capital_minutes")))
            allowed = profile.get("context_allowed")
            control_ready = profile.get("historical_control_ready")
            control_risk_fraction_raw = profile.get(
                "historical_stop_risk_fraction"
            )
            if (
                not edge.is_finite()
                or not minutes.is_finite()
                or minutes <= 0
                or type(allowed) is not bool
            ):
                raise CiboCapitalManagementError(
                    f"Trader Lab historical prior malformed for {signal}"
                )
            if control_ready is not None:
                control_risk_fraction = Decimal(
                    str(control_risk_fraction_raw)
                )
                if (
                    type(control_ready) is not bool
                    or not control_risk_fraction.is_finite()
                    or control_risk_fraction < 0
                    or control_risk_fraction > 1
                ):
                    raise CiboCapitalManagementError(
                        "Trader Lab historical control sizing prior malformed"
                    )

    def portfolio_edge(candidate: CiboThreeModeCandidate) -> Decimal:
        if not use_historical_prior:
            return candidate.expected_edge_after_cost_usd
        return Decimal(
            str(
                historical_prior_map[candidate.signal_fingerprint][
                    "expected_edge_after_cost_usd"
                ]
            )
        )

    def portfolio_minutes(candidate: CiboThreeModeCandidate) -> Decimal:
        if not use_historical_prior:
            return candidate.expected_capital_minutes
        return Decimal(
            str(
                historical_prior_map[candidate.signal_fingerprint][
                    "expected_capital_minutes"
                ]
            )
        )

    def portfolio_context_allowed(candidate: CiboThreeModeCandidate) -> bool:
        if not use_historical_prior:
            return candidate.context_allowed
        return bool(
            historical_prior_map[candidate.signal_fingerprint][
                "context_allowed"
            ]
        )

    def portfolio_velocity(candidate: CiboThreeModeCandidate) -> Decimal:
        minutes = portfolio_minutes(candidate)
        if minutes <= 0:
            return Decimal("-Infinity")
        with localcontext() as context:
            context.prec = 100
            return portfolio_edge(candidate) / minutes

    def historical_control_ready(
        candidate: CiboThreeModeCandidate,
    ) -> bool:
        if not use_historical_prior:
            return False
        profile = historical_prior_map[candidate.signal_fingerprint]
        if "historical_control_ready" in profile:
            return bool(profile["historical_control_ready"])
        return (
            portfolio_context_allowed(candidate)
            and portfolio_edge(candidate) > 0
        )

    def historical_control_risk_fraction(
        candidate: CiboThreeModeCandidate,
    ) -> Decimal | None:
        if not use_historical_prior:
            return None
        profile = historical_prior_map[candidate.signal_fingerprint]
        raw = profile.get("historical_stop_risk_fraction")
        if raw is None:
            return None
        value = Decimal(str(raw))
        return min(value, MEDIUM_RECOMMEND_RISK_FRACTION)

    def distributed_attack_candidate(
        candidate: CiboThreeModeCandidate,
    ) -> bool:
        return (
            candidate.native_cognition_recommended is True
            and candidate.context_quality_disposition == "ALLOW"
            and candidate.expected_net_utility_usd > 0
            and candidate.walk_forward_positive_block_count
            >= DISTRIBUTED_ATTACK_MIN_POSITIVE_BLOCKS
            and candidate.maximum_multiplier >= ATTACK_MINIMUM_MULTIPLIER
        )

    epochs = _group_epochs(rows)
    if len(rows) != manifest.get("opportunity_decision_count"):
        raise CiboCapitalManagementError(
            "Trader Lab three-mode decision count drift"
        )
    if len(epochs) != manifest.get("decision_epoch_count"):
        raise CiboCapitalManagementError(
            "Trader Lab three-mode epoch count drift"
        )

    state = _State()
    pending: list[CiboThreeModeOpenTrade] = []
    mode_counts: Counter[str] = Counter()
    trade_mode_counts: Counter[str] = Counter()
    trader_net: dict[str, Decimal] = defaultdict(Decimal)
    trader_trades: Counter[str] = Counter()
    trader_loss_streak: Counter[str] = Counter()
    trader_attack_loss_streak: Counter[str] = Counter()
    trader_attack_settlement_count: Counter[str] = Counter()
    recent_window_size = ceiling_attack_recent_trader_loss_window or 2
    trader_attack_recent_net_pnl: dict[str, deque[Decimal]] = defaultdict(
        lambda: deque(maxlen=recent_window_size)
    )
    attack_winning_trade_count = 0
    attack_losing_trade_count = 0
    attack_flat_trade_count = 0
    attack_gross_profit_usd = Decimal(0)
    attack_gross_loss_usd = Decimal(0)
    total_gross_profit_usd = Decimal(0)
    total_gross_loss_usd = Decimal(0)
    attack_gross_profit_by_trader: dict[str, Decimal] = defaultdict(Decimal)
    attack_gross_loss_by_trader: dict[str, Decimal] = defaultdict(Decimal)
    attack_gross_profit_by_multiplier: dict[int, Decimal] = defaultdict(Decimal)
    attack_gross_loss_by_multiplier: dict[int, Decimal] = defaultdict(Decimal)
    trade_realized_net_by_signal: dict[str, Decimal] = defaultdict(Decimal)
    leverage_sum = 0
    leverage_max = 0
    portfolio_calls = 0
    sizing_calls = 0
    compound_settlements = 0
    adaptive_leverage_calls = 0
    robust_sizing_reject_count = 0
    robust_leverage_cap_bind_count = 0
    attack_loss_streak_taper_bind_count = 0
    attack_drawdown_taper_bind_count = 0
    attack_multiplier_band_taper_bind_count = 0
    attack_risk_fraction_band_taper_bind_count = 0
    attack_drawdown_window_taper_bind_count = 0
    attack_drawdown_window2_taper_bind_count = 0
    attack_drawdown_window3_taper_bind_count = 0
    attack_drawdown_window4_taper_bind_count = 0
    attack_drawdown_window5_taper_bind_count = 0
    attack_drawdown_window6_taper_bind_count = 0
    attack_drawdown_window7_taper_bind_count = 0
    attack_stress_confidence_taper_bind_count = 0
    attack_stress_confidence_risk_budget_bind_count = 0
    attack_state_pressure_risk_budget_bind_count = 0
    attack_state_pressure2_risk_budget_bind_count = 0
    attack_trader_loss_ratio_taper_bind_count = 0
    attack_recent_trader_loss_taper_bind_count = 0
    attack_trader_shock_taper_bind_count = 0
    trader_last_attack_loss_fraction: dict[str, Decimal] = defaultdict(Decimal)
    trader_shock_protected_signals: set[str] = set()
    attack_low_multiplier_demotion_bind_count = 0
    portfolio_attack_shock_taper_bind_count = 0
    portfolio_last_attack_loss_fraction = Decimal(0)
    attack_epochs_funded = 0
    attack_scaling_capital_anchor_usd = INITIAL_CAPITAL_USD
    attack_compound_hysteresis_hold_count = 0
    attack_compound_hysteresis_raise_count = 0
    attack_compound_hysteresis_drop_count = 0
    attack_stress_confidence_reinvestment_anchor_usd = INITIAL_CAPITAL_USD
    attack_stress_confidence_reinvestment_hysteresis_armed = False
    attack_stress_confidence_reinvestment_arm_count = 0
    attack_stress_confidence_reinvestment_hold_count = 0
    attack_stress_confidence_reinvestment_release_count = 0
    attack_stress_confidence_reinvestment_drop_count = 0
    mode_reason_counts: Counter[str] = Counter()
    sizing_intensity_cap_counts: Counter[str] = Counter()
    medium_drawdown_intensity_cap_bind_count = 0
    drawdown_peak_at: datetime | None = None
    drawdown_episode_net_by_trader: dict[str, Decimal] = defaultdict(Decimal)
    drawdown_episode_net_by_mode: dict[str, Decimal] = defaultdict(Decimal)
    drawdown_episode_net_by_multiplier: dict[int, Decimal] = defaultdict(Decimal)
    drawdown_episode_gross_loss_by_multiplier: dict[int, Decimal] = defaultdict(Decimal)
    drawdown_episode_negative_settlements: list[dict[str, object]] = []
    current_drawdown_episode: dict[str, object] = {}
    drawdown_episodes: list[dict[str, object]] = []
    max_drawdown_attribution: dict[str, object] = {}
    trade_receipts: list[dict[str, object]] = []
    trade_receipt_by_signal: dict[str, dict[str, object]] = {}
    epoch_receipts: list[dict[str, object]] = []

    economic_functions = (
        "SIZING",
        "ADAPTIVE_LEVERAGE",
        "CIBO_COMPOUND",
        "COMPOUND_PORTFOLIO",
    )
    engineering_trace: list[dict[str, object]] = []
    sensor_event_sequence = 0
    sensor_stats: dict[str, dict[str, object]] = {
        name: {
            "call_count": 0,
            "approval_count": 0,
            "rejection_count": 0,
            "restriction_count": 0,
            "requested_capital_usd": Decimal(0),
            "approved_capital_usd": Decimal(0),
            "blocked_capital_usd": Decimal(0),
            "capital_created_usd": Decimal(0),
            "capital_destroyed_usd": Decimal(0),
            "reason_counts": Counter(),
            "action_counts": Counter(),
        }
        for name in economic_functions
    }
    upstream_intake_reason_counts: Counter[str] = Counter()
    upstream_intake_filtered_count = 0
    upstream_intake_admitted_count = 0

    def record_engineering_sensor(
        function_name: str,
        *,
        epoch_index: int | None,
        signal_fingerprint: str | None,
        event: str,
        inputs: Mapping[str, object],
        action: str,
        outputs: Mapping[str, object],
        reaction: str,
        reasons: tuple[str, ...] = (),
        call: bool = False,
        approval: bool = False,
        rejection: bool = False,
        restriction: bool = False,
        requested_capital_usd: Decimal = Decimal(0),
        approved_capital_usd: Decimal = Decimal(0),
        blocked_capital_usd: Decimal = Decimal(0),
        capital_created_usd: Decimal = Decimal(0),
        capital_destroyed_usd: Decimal = Decimal(0),
    ) -> None:
        nonlocal sensor_event_sequence
        if function_name not in sensor_stats:
            raise CiboCapitalManagementError(
                f"unknown engineering sensor function {function_name}"
            )
        sensor_event_sequence += 1
        stats = sensor_stats[function_name]
        if call:
            stats["call_count"] = int(stats["call_count"]) + 1
        if approval:
            stats["approval_count"] = int(stats["approval_count"]) + 1
        if rejection:
            stats["rejection_count"] = int(stats["rejection_count"]) + 1
        if restriction:
            stats["restriction_count"] = int(stats["restriction_count"]) + 1
        stats["requested_capital_usd"] = (
            stats["requested_capital_usd"] + requested_capital_usd
        )
        stats["approved_capital_usd"] = (
            stats["approved_capital_usd"] + approved_capital_usd
        )
        stats["blocked_capital_usd"] = (
            stats["blocked_capital_usd"] + blocked_capital_usd
        )
        stats["capital_created_usd"] = (
            stats["capital_created_usd"] + capital_created_usd
        )
        stats["capital_destroyed_usd"] = (
            stats["capital_destroyed_usd"] + capital_destroyed_usd
        )
        action_counts = stats["action_counts"]
        reason_counts = stats["reason_counts"]
        if not isinstance(action_counts, Counter) or not isinstance(
            reason_counts, Counter
        ):
            raise CiboCapitalManagementError(
                "engineering sensor counter corruption"
            )
        action_counts[action] += 1
        for reason in reasons:
            reason_counts[reason] += 1
        if not collect_engineering_trace:
            return
        engineering_trace.append(
            {
                "sequence": sensor_event_sequence,
                "epoch_index": epoch_index,
                "signal_fingerprint": signal_fingerprint,
                "function": function_name,
                "event": event,
                "inputs": dict(inputs),
                "action": action,
                "outputs": dict(outputs),
                "reaction": reaction,
                "reasons": list(reasons),
                "capital_effect": {
                    "requested_capital_usd": format(
                        requested_capital_usd, "f"
                    ),
                    "approved_capital_usd": format(
                        approved_capital_usd, "f"
                    ),
                    "blocked_capital_usd": format(
                        blocked_capital_usd, "f"
                    ),
                    "capital_created_usd": format(
                        capital_created_usd, "f"
                    ),
                    "capital_destroyed_usd": format(
                        capital_destroyed_usd, "f"
                    ),
                },
            }
        )

    def _apply_lifecycle_realization(
        trade: CiboThreeModeOpenTrade,
        *,
        net_pnl: Decimal,
        released_risk_usd: Decimal,
        released_margin_usd: Decimal,
        final_event: bool,
    ) -> None:
        state.open_stop_risk_usd = max(
            Decimal(0),
            state.open_stop_risk_usd - released_risk_usd,
        )
        state.open_margin_usd = max(
            Decimal(0),
            state.open_margin_usd - released_margin_usd,
        )

        if trade.mode is CiboTraderLabMode.MEDIUM:
            state.sovereign_reserved_usd = max(
                Decimal(0),
                state.sovereign_reserved_usd - released_risk_usd,
            )
            if final_event:
                state.sovereign_reserved_usd = max(
                    Decimal(0),
                    state.sovereign_reserved_usd - trade.provider_cost_usd,
                )
                bank_seed = trade.bank_seed_usd or Decimal(0)
                state.bank_seed_reserved_usd = max(
                    Decimal(0),
                    state.bank_seed_reserved_usd - bank_seed,
                )
                state.bank_seed_recycled_total_usd += bank_seed
                state.medium_compound_turnover_usd += (
                    trade.source_reserved_usd
                )

            if net_pnl > 0:
                recovery = (
                    min(
                        net_pnl,
                        state.medium_compound_recovery_deficit_usd,
                    )
                    if use_historical_prior
                    else Decimal(0)
                )
                if recovery > 0:
                    state.sovereign_bank_usd += recovery
                    state.medium_compound_recovery_deficit_usd -= recovery
                    state.medium_compound_recovered_usd += recovery
                distributable = net_pnl - recovery
                sovereign_share = MEDIUM_SOVEREIGN_SHARE
                if compound_profit_reinvestment_fraction is not None:
                    sovereign_share = (
                        Decimal(1) - compound_profit_reinvestment_fraction
                    )
                elif economic_group_ablation == "CIBO_COMPOUND":
                    sovereign_share = Decimal(1)
                elif coordinated_economic_group:
                    total = max(
                        Decimal("0.00000001"),
                        state.total_capital_usd,
                    )
                    total_dd = _ratio(
                        max(
                            Decimal(0),
                            state.peak_total_capital_usd
                            - state.total_capital_usd,
                        ),
                        state.peak_total_capital_usd,
                    )
                    cushion_ratio = _ratio(
                        state.portfolio_cushion_usd,
                        total,
                    )
                    if ceiling_discovery_mode:
                        sovereign_share = (
                            Decimal(1)
                            - economic_group_bootstrap_cushion_share
                        )
                    elif total_dd >= Decimal("0.20"):
                        sovereign_share = Decimal("0.80")
                    elif total_dd >= Decimal("0.10"):
                        sovereign_share = Decimal("0.65")
                    elif cushion_ratio < Decimal("0.20"):
                        sovereign_share = (
                            Decimal(1)
                            - economic_group_bootstrap_cushion_share
                        )
                    elif cushion_ratio > Decimal("0.60"):
                        sovereign_share = Decimal("0.65")
                sovereign_gain = distributable * sovereign_share
                cushion_gain = distributable - sovereign_gain
                state.sovereign_bank_usd += sovereign_gain
                state.portfolio_cushion_usd += cushion_gain
                state.portfolio_attack_credit_usd += cushion_gain
                state.medium_profit_to_sovereign_usd += sovereign_gain
                state.medium_profit_to_cushion_usd += cushion_gain
                state.medium_compound_positive_net_usd += net_pnl
            elif net_pnl < 0:
                state.sovereign_bank_usd += net_pnl
                if use_historical_prior:
                    state.medium_compound_recovery_deficit_usd += -net_pnl
                state.medium_compound_negative_net_usd += -net_pnl

        elif trade.mode is CiboTraderLabMode.ATTACK:
            state.cushion_reserved_usd = max(
                Decimal(0),
                state.cushion_reserved_usd - released_risk_usd,
            )
            if final_event:
                state.cushion_reserved_usd = max(
                    Decimal(0),
                    state.cushion_reserved_usd - trade.provider_cost_usd,
                )
            if (
                net_pnl > 0
                and compound_profit_reinvestment_fraction is not None
            ):
                reinvested_gain = (
                    net_pnl * compound_profit_reinvestment_fraction
                )
                sovereign_gain = net_pnl - reinvested_gain
                state.portfolio_cushion_usd += reinvested_gain
                state.sovereign_bank_usd += sovereign_gain
                state.attack_profit_to_cushion_usd += reinvested_gain
                state.attack_profit_to_sovereign_usd += sovereign_gain
            else:
                state.portfolio_cushion_usd += net_pnl
                if net_pnl > 0:
                    state.attack_profit_to_cushion_usd += net_pnl
            state.attack_net_pnl_usd += net_pnl
            if state.portfolio_cushion_usd < 0:
                breach = -state.portfolio_cushion_usd
                state.attack_sovereign_breach_usd += breach
                state.portfolio_cushion_usd = Decimal(0)
                state.sovereign_bank_usd -= breach
            if final_event:
                state.portfolio_attack_credit_recycled_total_usd += (
                    trade.source_reserved_usd
                )
            state.portfolio_attack_credit_usd = (
                state.cushion_available_usd
            )
        else:
            raise CiboCapitalManagementError(
                "BANK cannot own lifecycle-managed trades"
            )
        state.mark()

    def settle_due(up_to: datetime | None) -> None:
        nonlocal pending, compound_settlements
        nonlocal drawdown_peak_at, max_drawdown_attribution
        nonlocal current_drawdown_episode
        nonlocal attack_winning_trade_count, attack_losing_trade_count
        nonlocal attack_flat_trade_count
        nonlocal attack_gross_profit_usd, attack_gross_loss_usd
        nonlocal total_gross_profit_usd, total_gross_loss_usd
        nonlocal portfolio_last_attack_loss_fraction

        def due_at(trade: CiboThreeModeOpenTrade) -> datetime:
            if (
                trade.lifecycle_events
                and trade.lifecycle_event_index
                < len(trade.lifecycle_events)
            ):
                return trade.lifecycle_events[
                    trade.lifecycle_event_index
                ].occurred_at
            return trade.exit_at

        while True:
            due = sorted(
                (
                    item
                    for item in pending
                    if up_to is None or due_at(item) <= up_to
                ),
                key=lambda item: (
                    due_at(item),
                    item.signal_fingerprint,
                ),
            )
            if not due:
                return

            trade = due[0]
            pending = [item for item in pending if item is not trade]
            before_sovereign = state.sovereign_bank_usd
            before_cushion = state.portfolio_cushion_usd
            before_total = state.total_capital_usd
            before_open_stop_risk = state.open_stop_risk_usd
            before_open_margin = state.open_margin_usd
            before_sovereign_reserved = state.sovereign_reserved_usd
            before_cushion_reserved = state.cushion_reserved_usd
            before_bank_seed_reserved = state.bank_seed_reserved_usd
            peak_total_before = state.peak_total_capital_usd
            settlement_function = (
                "CIBO_COMPOUND"
                if trade.mode is CiboTraderLabMode.MEDIUM
                else "COMPOUND_PORTFOLIO"
            )

            lifecycle_event = None
            final_event = True
            released_risk_usd = trade.stop_risk_usd
            released_margin_usd = trade.margin_usd
            gross_r_delta = trade.gross_r
            event_at = trade.exit_at

            if trade.lifecycle_events:
                lifecycle_event = trade.lifecycle_events[
                    trade.lifecycle_event_index
                ]
                event_at = lifecycle_event.occurred_at
                gross_r_delta = lifecycle_event.realized_r_delta
                final_event = (
                    trade.lifecycle_event_index + 1
                    == len(trade.lifecycle_events)
                )
                released_risk_fraction = max(
                    Decimal(0),
                    trade.lifecycle_risk_fraction_remaining
                    - lifecycle_event.risk_fraction_remaining,
                )
                released_margin_fraction = max(
                    Decimal(0),
                    trade.lifecycle_margin_fraction_remaining
                    - lifecycle_event.margin_fraction_remaining,
                )
                released_risk_usd = (
                    trade.stop_risk_usd * released_risk_fraction
                )
                released_margin_usd = (
                    trade.margin_usd * released_margin_fraction
                )

            record_engineering_sensor(
                settlement_function,
                epoch_index=None,
                signal_fingerprint=trade.signal_fingerprint,
                event=(
                    "LIFECYCLE_EVENT_INPUT"
                    if lifecycle_event is not None
                    else "SETTLEMENT_INPUT"
                ),
                inputs={
                    "mode": trade.mode.value,
                    "multiplier": trade.multiplier,
                    "gross_r_delta_postdecision": format(
                        gross_r_delta, "f"
                    ),
                    "stop_risk_usd": format(trade.stop_risk_usd, "f"),
                    "provider_cost_usd": format(
                        trade.provider_cost_usd, "f"
                    ),
                    "released_risk_usd": format(
                        released_risk_usd, "f"
                    ),
                    "released_margin_usd": format(
                        released_margin_usd, "f"
                    ),
                    "lifecycle_action": (
                        None
                        if lifecycle_event is None
                        else lifecycle_event.action
                    ),
                    "final_event": final_event,
                    "sovereign_bank_before_usd": format(
                        before_sovereign, "f"
                    ),
                    "portfolio_cushion_before_usd": format(
                        before_cushion, "f"
                    ),
                },
                action=(
                    "SETTLE_CAUSAL_LIFECYCLE_EVENT"
                    if lifecycle_event is not None
                    else "SETTLE_DUE_TRADE"
                ),
                outputs={"occurred_at": event_at.isoformat()},
                reaction="AWAIT_SETTLEMENT_OUTPUT",
                call=True,
            )

            if lifecycle_event is None:
                net = apply_three_mode_settlement(
                    state,
                    trade,
                    net_compound_before_split=use_historical_prior,
                    coordinated_economic_group=coordinated_economic_group,
                    economic_group_bootstrap_cushion_share=(
                        economic_group_bootstrap_cushion_share
                    ),
                    economic_group_ablation=economic_group_ablation,
                    ceiling_discovery_mode=ceiling_discovery_mode,
                    compound_profit_reinvestment_fraction=(
                        compound_profit_reinvestment_fraction
                    ),
                )
            else:
                with localcontext() as context:
                    context.prec = 100
                    net = gross_r_delta * trade.stop_risk_usd
                    if final_event:
                        net -= trade.provider_cost_usd
                _apply_lifecycle_realization(
                    trade,
                    net_pnl=net,
                    released_risk_usd=released_risk_usd,
                    released_margin_usd=released_margin_usd,
                    final_event=final_event,
                )

            created = max(Decimal(0), net)
            destroyed = max(Decimal(0), -net)
            record_engineering_sensor(
                settlement_function,
                epoch_index=None,
                signal_fingerprint=trade.signal_fingerprint,
                event=(
                    "LIFECYCLE_EVENT_OUTPUT"
                    if lifecycle_event is not None
                    else "SETTLEMENT_OUTPUT"
                ),
                inputs={
                    "total_capital_before_usd": format(before_total, "f"),
                },
                action=(
                    "COMPOUND_GAIN"
                    if net > 0
                    else "COMPOUND_LOSS"
                    if net < 0
                    else "COMPOUND_FLAT"
                ),
                outputs={
                    "net_pnl_usd": format(net, "f"),
                    "sovereign_bank_after_usd": format(
                        state.sovereign_bank_usd, "f"
                    ),
                    "portfolio_cushion_after_usd": format(
                        state.portfolio_cushion_usd, "f"
                    ),
                    "total_capital_after_usd": format(
                        state.total_capital_usd, "f"
                    ),
                    "open_stop_risk_after_usd": format(
                        state.open_stop_risk_usd, "f"
                    ),
                    "open_margin_after_usd": format(
                        state.open_margin_usd, "f"
                    ),
                    "final_event": final_event,
                },
                reaction=(
                    "INCREASE_FUTURE_CAPITAL_CAPACITY"
                    if net > 0
                    else "REDUCE_FUTURE_CAPITAL_CAPACITY"
                    if net < 0
                    else "RELEASE_OR_PRESERVE_CAPITAL_CAPACITY"
                ),
                reasons=(
                    ("POSITIVE_SETTLEMENT",)
                    if net > 0
                    else ("NEGATIVE_SETTLEMENT",)
                    if net < 0
                    else ("FLAT_SETTLEMENT",)
                ),
                approval=net >= 0,
                restriction=net < 0,
                capital_created_usd=created,
                capital_destroyed_usd=destroyed,
            )
            trader_net[trade.trader_id] += net
            trade_realized_net_by_signal[trade.signal_fingerprint] += net

            after_total = state.total_capital_usd
            if after_total >= peak_total_before:
                if current_drawdown_episode:
                    peak_at_raw = current_drawdown_episode.get("peak_at")
                    underwater_seconds = None
                    if isinstance(peak_at_raw, str):
                        underwater_seconds = max(
                            0,
                            int(
                                (
                                    event_at - datetime.fromisoformat(peak_at_raw)
                                ).total_seconds()
                            ),
                        )
                    current_drawdown_episode["recovery_at"] = event_at.isoformat()
                    current_drawdown_episode["recovery_capital_usd"] = format(
                        after_total, "f"
                    )
                    current_drawdown_episode[
                        "underwater_duration_seconds"
                    ] = underwater_seconds
                    current_drawdown_episode.pop("_last_at", None)
                    drawdown_episodes.append(current_drawdown_episode)
                    current_drawdown_episode = {}
                drawdown_peak_at = event_at
                drawdown_episode_net_by_trader.clear()
                drawdown_episode_net_by_mode.clear()
                drawdown_episode_net_by_multiplier.clear()
                drawdown_episode_gross_loss_by_multiplier.clear()
                drawdown_episode_negative_settlements.clear()
            else:
                if not current_drawdown_episode:
                    current_drawdown_episode = {
                        "peak_at": (
                            None
                            if drawdown_peak_at is None
                            else drawdown_peak_at.isoformat()
                        ),
                        "peak_capital_usd": format(peak_total_before, "f"),
                        "peak_state": {
                            "sovereign_bank_usd": format(
                                before_sovereign, "f"
                            ),
                            "portfolio_cushion_usd": format(
                                before_cushion, "f"
                            ),
                            "open_stop_risk_usd": format(
                                before_open_stop_risk, "f"
                            ),
                            "open_margin_usd": format(
                                before_open_margin, "f"
                            ),
                            "sovereign_reserved_usd": format(
                                before_sovereign_reserved, "f"
                            ),
                            "cushion_reserved_usd": format(
                                before_cushion_reserved, "f"
                            ),
                            "bank_seed_reserved_usd": format(
                                before_bank_seed_reserved, "f"
                            ),
                        },
                        "recovery_at": None,
                        "recovery_capital_usd": None,
                        "underwater_duration_seconds": None,
                    }
                current_drawdown_episode["_last_at"] = event_at.isoformat()
                drawdown_episode_net_by_trader[trade.trader_id] += net
                drawdown_episode_net_by_mode[trade.mode.value] += net
                drawdown_episode_net_by_multiplier[trade.multiplier] += net
                if net < 0:
                    drawdown_episode_gross_loss_by_multiplier[
                        trade.multiplier
                    ] += -net
                    drawdown_episode_negative_settlements.append(
                        {
                            "occurred_at": event_at.isoformat(),
                            "signal_fingerprint": trade.signal_fingerprint,
                            "trader_id": trade.trader_id,
                            "mode": trade.mode.value,
                            "multiplier": trade.multiplier,
                            "net_pnl_usd": format(net, "f"),
                        }
                    )
                current_drawdown_fraction = _ratio(
                    peak_total_before - after_total,
                    peak_total_before,
                )
                current_episode_fraction = Decimal(
                    str(
                        current_drawdown_episode.get(
                            "drawdown_fraction", "-1"
                        )
                    )
                )
                if current_drawdown_fraction >= current_episode_fraction:
                    worst = sorted(
                        drawdown_episode_negative_settlements,
                        key=lambda item: Decimal(
                            str(item["net_pnl_usd"])
                        ),
                    )[:20]
                    current_drawdown_episode.update(
                        {
                            "trough_at": event_at.isoformat(),
                            "trough_capital_usd": format(after_total, "f"),
                            "drawdown_usd": format(
                                peak_total_before - after_total, "f"
                            ),
                            "drawdown_fraction": format(
                                current_drawdown_fraction, "f"
                            ),
                            "net_by_trader_usd": {
                                key: format(value, "f")
                                for key, value in sorted(
                                    drawdown_episode_net_by_trader.items()
                                )
                            },
                            "net_by_mode_usd": {
                                key: format(value, "f")
                                for key, value in sorted(
                                    drawdown_episode_net_by_mode.items()
                                )
                            },
                            "net_by_multiplier_usd": {
                                str(key): format(value, "f")
                                for key, value in sorted(
                                    drawdown_episode_net_by_multiplier.items()
                                )
                            },
                            "gross_loss_by_multiplier_usd": {
                                str(key): format(value, "f")
                                for key, value in sorted(
                                    drawdown_episode_gross_loss_by_multiplier.items()
                                )
                            },
                            "top_negative_settlements": worst,
                            "trough_state": {
                                "sovereign_bank_usd": format(
                                    state.sovereign_bank_usd, "f"
                                ),
                                "portfolio_cushion_usd": format(
                                    state.portfolio_cushion_usd, "f"
                                ),
                                "portfolio_attack_credit_usd": format(
                                    state.portfolio_attack_credit_usd, "f"
                                ),
                                "open_stop_risk_usd": format(
                                    state.open_stop_risk_usd, "f"
                                ),
                                "open_margin_usd": format(
                                    state.open_margin_usd, "f"
                                ),
                                "sovereign_reserved_usd": format(
                                    state.sovereign_reserved_usd, "f"
                                ),
                                "cushion_reserved_usd": format(
                                    state.cushion_reserved_usd, "f"
                                ),
                                "bank_seed_reserved_usd": format(
                                    state.bank_seed_reserved_usd, "f"
                                ),
                                "portfolio_last_attack_loss_fraction": format(
                                    (
                                        (-net) / before_total
                                        if (
                                            trade.mode
                                            is CiboTraderLabMode.ATTACK
                                            and net < 0
                                            and before_total > 0
                                        )
                                        else portfolio_last_attack_loss_fraction
                                    ),
                                    "f",
                                ),
                                "portfolio_attack_shock_taper_bind_count": (
                                    portfolio_attack_shock_taper_bind_count
                                ),
                                "trader_loss_streaks_before_settlement": {
                                    key: int(value)
                                    for key, value in sorted(
                                        trader_loss_streak.items()
                                    )
                                },
                                "trader_attack_loss_streaks_before_settlement": {
                                    key: int(value)
                                    for key, value in sorted(
                                        trader_attack_loss_streak.items()
                                    )
                                },
                            },
                        }
                    )
                if (
                    not max_drawdown_attribution
                    or current_drawdown_fraction
                    >= Decimal(
                        str(
                            max_drawdown_attribution[
                                "drawdown_fraction"
                            ]
                        )
                    )
                ):
                    max_drawdown_attribution = {
                        key: value
                        for key, value in current_drawdown_episode.items()
                        if not key.startswith("_")
                    }

            if lifecycle_event is not None and not final_event:
                pending.append(
                    replace(
                        trade,
                        lifecycle_event_index=(
                            trade.lifecycle_event_index + 1
                        ),
                        lifecycle_risk_fraction_remaining=(
                            lifecycle_event.risk_fraction_remaining
                        ),
                        lifecycle_margin_fraction_remaining=(
                            lifecycle_event.margin_fraction_remaining
                        ),
                    )
                )
                continue

            settled_trade_net = trade_realized_net_by_signal.pop(
                trade.signal_fingerprint,
                Decimal(0),
            )
            receipt = trade_receipt_by_signal.get(
                trade.signal_fingerprint
            )
            if receipt is None:
                raise CiboCapitalManagementError(
                    "Trader Lab settlement missing trade receipt"
                )
            receipt["realized_net_pnl_usd"] = format(
                settled_trade_net, "f"
            )
            receipt["realized_net_r"] = format(
                (
                    settled_trade_net / trade.stop_risk_usd
                    if trade.stop_risk_usd > 0
                    else Decimal(0)
                ),
                "f",
            )
            receipt["realized_exit_at"] = event_at.isoformat()
            if settled_trade_net < 0:
                total_gross_loss_usd += -settled_trade_net
                trader_loss_streak[trade.trader_id] += 1
            elif settled_trade_net > 0:
                total_gross_profit_usd += settled_trade_net
                trader_loss_streak[trade.trader_id] = 0
            else:
                trader_loss_streak[trade.trader_id] = 0
            if trade.mode is CiboTraderLabMode.ATTACK:
                trader_attack_settlement_count[trade.trader_id] += 1
                trader_attack_recent_net_pnl[trade.trader_id].append(
                    settled_trade_net
                )
                if settled_trade_net < 0:
                    portfolio_last_attack_loss_fraction = (
                        (-settled_trade_net) / before_total
                        if before_total > 0
                        else Decimal("0.50")
                    )
                    if trade.signal_fingerprint in trader_shock_protected_signals:
                        trader_shock_protected_signals.discard(
                            trade.signal_fingerprint
                        )
                        trader_last_attack_loss_fraction[trade.trader_id] = (
                            Decimal(0)
                        )
                    else:
                        trader_last_attack_loss_fraction[trade.trader_id] = (
                            portfolio_last_attack_loss_fraction
                        )
                    trader_attack_loss_streak[trade.trader_id] += 1
                    attack_losing_trade_count += 1
                    attack_gross_loss_usd += -settled_trade_net
                    attack_gross_loss_by_trader[trade.trader_id] += (
                        -settled_trade_net
                    )
                    attack_gross_loss_by_multiplier[trade.multiplier] += (
                        -settled_trade_net
                    )
                elif settled_trade_net > 0:
                    portfolio_last_attack_loss_fraction = Decimal(0)
                    trader_shock_protected_signals.discard(
                        trade.signal_fingerprint
                    )
                    trader_last_attack_loss_fraction[trade.trader_id] = Decimal(0)
                    trader_attack_loss_streak[trade.trader_id] = 0
                    attack_winning_trade_count += 1
                    attack_gross_profit_usd += settled_trade_net
                    attack_gross_profit_by_trader[trade.trader_id] += (
                        settled_trade_net
                    )
                    attack_gross_profit_by_multiplier[trade.multiplier] += (
                        settled_trade_net
                    )
                else:
                    portfolio_last_attack_loss_fraction = Decimal(0)
                    trader_shock_protected_signals.discard(
                        trade.signal_fingerprint
                    )
                    trader_last_attack_loss_fraction[trade.trader_id] = Decimal(0)
                    trader_attack_loss_streak[trade.trader_id] = 0
                    attack_flat_trade_count += 1

            trader_trades[trade.trader_id] += 1
            if trade.mode is CiboTraderLabMode.MEDIUM:
                compound_settlements += 1

    for epoch_index, epoch_rows in enumerate(epochs, start=1):
        decision_at = _dt(
            epoch_rows[0].get("market_decision_at"),
            "market_decision_at",
        )
        settle_due(decision_at)
        if state.total_capital_usd <= 0:
            raise CiboCapitalManagementError(
                "Trader Lab three-mode account exhausted"
            )

        regimes = tuple(_regime_from_row(row) for row in epoch_rows)
        regime = regimes[0]
        if any(item != regime for item in regimes[1:]):
            raise CiboCapitalManagementError(
                "Trader Lab three-mode mixed regime inside epoch"
            )
        base_candidates = tuple(
            _candidate(
                row,
                native_cognition_recommended=cognitive_map[
                    str(row["signal_fingerprint"])
                ],
                enforce_research_context_abstain=(
                    enforce_research_context_abstain
                ),
            )
            for row in epoch_rows
        )
        candidates = tuple(
            replace(
                candidate,
                gross_r=Decimal(
                    str(lifecycle_map[candidate.signal_fingerprint]["managed_gross_r"])
                ),
                exit_at=_dt(
                    lifecycle_map[candidate.signal_fingerprint]["managed_exit_at"],
                    "lifecycle managed_exit_at",
                ),
            )
            if (
                lifecycle_map
                and not lifecycle_defensive_medium_1x_only
                and not lifecycle_attack_only
            )
            else candidate
            for candidate in base_candidates
        )
        eligible = tuple(
            sorted(
                (
                    item
                    for item in candidates
                    if item.maximum_multiplier > 0
                ),
                key=lambda item: (
                    -portfolio_velocity(item),
                    -portfolio_edge(item),
                    item.signal_fingerprint,
                ),
            )
        )
        eligible_signals = {item.signal_fingerprint for item in eligible}
        for candidate in candidates:
            if candidate.signal_fingerprint in eligible_signals:
                upstream_intake_admitted_count += 1
                continue
            upstream_intake_filtered_count += 1
            intake_reasons: list[str] = []
            if not candidate.context_allowed:
                intake_reasons.append("CONTEXT_OR_COGNITION_NOT_ALLOWED")
            if candidate.expected_edge_after_cost_usd <= 0:
                intake_reasons.append(
                    "EXPECTED_EDGE_AFTER_COST_NONPOSITIVE"
                )
            if candidate.maximum_multiplier <= 0:
                intake_reasons.append("PROVIDER_MAX_MULTIPLIER_ZERO")
            if not intake_reasons:
                intake_reasons.append("UNCLASSIFIED_INTAKE_FILTER")
            for reason in intake_reasons:
                upstream_intake_reason_counts[reason] += 1
            record_engineering_sensor(
                "COMPOUND_PORTFOLIO",
                epoch_index=epoch_index,
                signal_fingerprint=candidate.signal_fingerprint,
                event="ECONOMIC_INTAKE_REACTION",
                inputs={
                    "context_allowed": candidate.context_allowed,
                    "expected_edge_after_cost_usd": format(
                        candidate.expected_edge_after_cost_usd, "f"
                    ),
                    "uncertainty_adjusted_utility_usd": format(
                        candidate.expected_net_utility_usd, "f"
                    ),
                    "maximum_multiplier": candidate.maximum_multiplier,
                },
                action="OBSERVE_UPSTREAM_FILTER",
                outputs={"admitted_to_economic_surface": False},
                reaction="NO_SIZING_OR_LEVERAGE_CALL_POSSIBLE",
                reasons=tuple(intake_reasons),
            )

        total = state.total_capital_usd
        risk_capacity = (
            total * cibo_new_capital_risk_utilization_ceiling()
        )
        margin_capacity = total * MARGIN_CAPACITY_MULTIPLE
        sovereign_drawdown = max(
            Decimal(0),
            state.peak_sovereign_bank_usd - state.sovereign_bank_usd,
        )
        risk_utilization = _ratio(state.open_stop_risk_usd, risk_capacity)
        margin_utilization = _ratio(state.open_margin_usd, margin_capacity)
        drawdown_utilization = _ratio(
            sovereign_drawdown,
            state.peak_sovereign_bank_usd,
        )
        total_drawdown_usd = max(
            Decimal(0),
            state.peak_total_capital_usd - state.total_capital_usd,
        )
        total_drawdown_utilization = _ratio(
            total_drawdown_usd,
            state.peak_total_capital_usd,
        )
        ceiling_attack_drawdown_budget_active = (
            ceiling_discovery_mode
            and ceiling_attack_drawdown_budget_fraction is not None
            and (
                ceiling_attack_drawdown_budget_capital_floor is None
                or state.total_capital_usd
                >= ceiling_attack_drawdown_budget_capital_floor
            )
            and (
                ceiling_attack_drawdown_budget_capital_ceiling is None
                or state.total_capital_usd
                <= ceiling_attack_drawdown_budget_capital_ceiling
            )
        )
        ceiling_attack_drawdown_budget2_active = (
            ceiling_discovery_mode
            and ceiling_attack_drawdown_budget2_fraction is not None
            and ceiling_attack_drawdown_budget2_capital_floor is not None
            and ceiling_attack_drawdown_budget2_capital_ceiling is not None
            and ceiling_attack_drawdown_budget2_capital_floor
            <= state.total_capital_usd
            <= ceiling_attack_drawdown_budget2_capital_ceiling
        )
        effective_ceiling_attack_drawdown_budget_fraction = (
            ceiling_attack_drawdown_budget_fraction
            if ceiling_attack_drawdown_budget_active
            else ceiling_attack_drawdown_budget2_fraction
            if ceiling_attack_drawdown_budget2_active
            else None
        )
        ceiling_attack_drawdown_budget_any_active = (
            ceiling_attack_drawdown_budget_active
            or ceiling_attack_drawdown_budget2_active
        )
        attack_drawdown_budget_fraction = (
            effective_ceiling_attack_drawdown_budget_fraction
            if effective_ceiling_attack_drawdown_budget_fraction is not None
            else ATTACK_PORTFOLIO_DRAWDOWN_BUDGET
        )
        with localcontext() as context:
            context.prec = 100
            attack_drawdown_headroom_usd = max(
                Decimal(0),
                (
                    state.peak_total_capital_usd
                    * attack_drawdown_budget_fraction
                )
                - total_drawdown_usd
                - state.open_stop_risk_usd,
            )
        portfolio_attack_budget_usd = (
            state.attack_credit_available_usd
            if (
                ceiling_discovery_mode
                and not ceiling_attack_drawdown_budget_any_active
            )
            else min(
                state.attack_credit_available_usd,
                attack_drawdown_headroom_usd,
            )
        )
        if economic_group_ablation == "COMPOUND_PORTFOLIO":
            portfolio_attack_budget_usd = Decimal(0)
        if distributed_attack_frontier:
            attack_eligible = tuple(
                item for item in eligible if distributed_attack_candidate(item)
            )
            best = attack_eligible[0] if attack_eligible else None
        else:
            attack_eligible = ()
            best = eligible[0] if eligible else None
        mode, mode_reasons = explain_three_mode(
            regime=regime,
            risk_utilization=risk_utilization,
            margin_utilization=margin_utilization,
            drawdown_utilization=(
                Decimal(0)
                if ceiling_discovery_mode
                else drawdown_utilization
            ),
            cushion_available_usd=portfolio_attack_budget_usd,
            best_candidate=best,
            total_drawdown_utilization=(
                Decimal(0)
                if ceiling_discovery_mode
                else total_drawdown_utilization
            ),
            distributed_attack_frontier=distributed_attack_frontier,
        )
        mode_counts[mode.value] += 1
        for reason in mode_reasons:
            mode_reason_counts[reason] += 1
        portfolio_calls += 1
        minimum_attack_cushion = (
            Decimal(0)
            if best is None
            else (
                best.source_cost_per_multiplier_usd
                * Decimal(ATTACK_MINIMUM_MULTIPLIER)
            )
        )
        attack_capital_gap = max(
            Decimal(0),
            minimum_attack_cushion - state.cushion_available_usd,
        )
        record_engineering_sensor(
            "COMPOUND_PORTFOLIO",
            epoch_index=epoch_index,
            signal_fingerprint=(
                None if best is None else best.signal_fingerprint
            ),
            event="MODE_ALLOCATION",
            inputs={
                "candidate_count": len(candidates),
                "eligible_count": len(eligible),
                "sovereign_bank_usd": format(
                    state.sovereign_bank_usd, "f"
                ),
                "sovereign_available_usd": format(
                    state.sovereign_available_usd, "f"
                ),
                "sovereign_risk_budget_available_usd": format(
                    state.sovereign_risk_budget_available_usd, "f"
                ),
                "portfolio_cushion_available_usd": format(
                    state.cushion_available_usd, "f"
                ),
                "portfolio_attack_credit_available_usd": format(
                    state.attack_credit_available_usd, "f"
                ),
                "portfolio_attack_drawdown_headroom_usd": format(
                    attack_drawdown_headroom_usd, "f"
                ),
                "portfolio_attack_budget_usd": format(
                    portfolio_attack_budget_usd, "f"
                ),
                "risk_utilization": format(risk_utilization, "f"),
                "margin_utilization": format(margin_utilization, "f"),
                "drawdown_utilization": format(
                    drawdown_utilization, "f"
                ),
                "total_drawdown_utilization": format(
                    total_drawdown_utilization, "f"
                ),
                "attack_total_drawdown_guard": format(
                    ATTACK_TOTAL_DRAWDOWN_GUARD, "f"
                ),
                "attack_drawdown_budget_fraction": format(
                    attack_drawdown_budget_fraction, "f"
                ),
                "ceiling_attack_drawdown_budget_fraction": (
                    None
                    if ceiling_attack_drawdown_budget_fraction is None
                    else format(
                        ceiling_attack_drawdown_budget_fraction, "f"
                    )
                ),
                "minimum_attack_cushion_usd": format(
                    minimum_attack_cushion, "f"
                ),
            },
            action=f"SELECT_{mode.value}",
            outputs={
                "mode": mode.value,
                "attack_capital_gap_usd": format(
                    attack_capital_gap, "f"
                ),
                "mode_reasons": list(mode_reasons),
            },
            reaction=(
                "RELEASE_CONTROLLED_CUSHION_BUDGET_TO_ATTACK"
                if mode is CiboTraderLabMode.ATTACK
                else "KEEP_BUILDING_OR_PRESERVING_CAPITAL"
                if mode is CiboTraderLabMode.MEDIUM
                else "DEFEND_CAPITAL"
            ),
            reasons=tuple(mode_reasons),
            call=True,
            approval=mode is CiboTraderLabMode.ATTACK,
            restriction=mode is not CiboTraderLabMode.ATTACK,
            requested_capital_usd=minimum_attack_cushion,
            approved_capital_usd=(
                minimum_attack_cushion
                if mode is CiboTraderLabMode.ATTACK
                else Decimal(0)
            ),
            blocked_capital_usd=attack_capital_gap,
        )
        if mode is CiboTraderLabMode.ATTACK:
            attack_epochs_funded += 1

        selected: list[
            tuple[CiboThreeModeCandidate, int, CiboTraderLabMode]
        ] = []
        risk_left = max(Decimal(0), risk_capacity - state.open_stop_risk_usd)
        margin_left = max(
            Decimal(0),
            margin_capacity - state.open_margin_usd,
        )
        sovereign_left = state.sovereign_available_usd
        cushion_left = state.cushion_available_usd

        # BANK is treasury, not execution. Each MEDIUM candidate receives its
        # own dynamic percentage seed envelope immediately before Sizing.
        portfolio_attack_release_left = (
            portfolio_attack_budget_usd
            if mode is CiboTraderLabMode.ATTACK
            else Decimal(0)
        )
        attack_risk_selected_this_epoch = Decimal(0)
        if mode is not CiboTraderLabMode.BANK:
            candidate_surface = eligible
            for candidate in candidate_surface:
                candidate_mode = (
                    CiboTraderLabMode.ATTACK
                    if (
                        mode is CiboTraderLabMode.ATTACK
                        and best is not None
                        and (
                            candidate.signal_fingerprint
                            == best.signal_fingerprint
                            or (
                                distributed_attack_frontier
                                and distributed_attack_candidate(candidate)
                            )
                        )
                    )
                    else CiboTraderLabMode.MEDIUM
                )
                if candidate_mode is CiboTraderLabMode.MEDIUM:
                    sizing_calls += 1
                    active_portfolio_edge = portfolio_edge(candidate)
                    active_portfolio_context = portfolio_context_allowed(
                        candidate
                    )
                    if (
                        not use_historical_prior
                        and candidate.native_cognition_recommended is False
                    ):
                        record_engineering_sensor(
                            "SIZING",
                            epoch_index=epoch_index,
                            signal_fingerprint=candidate.signal_fingerprint,
                            event="NATIVE_ECONOMIC_TREATMENT",
                            inputs={
                                "native_cognition_recommended": False,
                                "context_quality_disposition": (
                                    candidate.context_quality_disposition
                                ),
                                "expected_edge_after_cost_usd": format(
                                    active_portfolio_edge, "f"
                                ),
                            },
                            action="CLASSIFY_DEFENSIVE_MEDIUM",
                            outputs={
                                "economic_treatment": "DEFENSIVE_MEDIUM",
                            },
                            reaction=(
                                "REDUCE_INTENSITY_WITHOUT_REJECTING_TRADER_ENTRY"
                            ),
                            reasons=("NATIVE_ABSTAIN_DEFENSIVE",),
                        )
                    historical_prior_deployable = (
                        historical_control_ready(candidate)
                        if use_historical_prior
                        else (
                            active_portfolio_context
                            and active_portfolio_edge > 0
                        )
                    )
                    if (
                        use_historical_prior
                        and not historical_prior_deployable
                        and candidate.native_cognition_recommended is False
                    ):
                        record_engineering_sensor(
                            "SIZING",
                            epoch_index=epoch_index,
                            signal_fingerprint=candidate.signal_fingerprint,
                            event="HISTORICAL_PORTFOLIO_TREATMENT",
                            inputs={
                                "native_cognition_recommended": (
                                    candidate.native_cognition_recommended
                                ),
                                "historical_context_allowed": (
                                    active_portfolio_context
                                ),
                                "historical_edge_after_cost_usd": format(
                                    active_portfolio_edge, "f"
                                ),
                            },
                            action="CLASSIFY_HISTORICAL_DEFENSIVE_MEDIUM",
                            outputs={
                                "economic_treatment": "DEFENSIVE_MEDIUM",
                            },
                            reaction=(
                                "MANAGE_ENTRY_AT_MINIMUM_INTENSITY_NOT_DEFER"
                            ),
                            reasons=("HISTORICAL_PRIOR_DEFENSIVE",),
                        )
                    per_entry_seed_budget = dynamic_bank_seed_budget_usd(
                        state.total_capital_usd
                    )
                    bank_seed = max(
                        Decimal(0),
                        min(
                            per_entry_seed_budget,
                            sovereign_left,
                        ),
                    )
                    executable_by_seed = int(
                        (
                            bank_seed
                            / candidate.source_cost_per_multiplier_usd
                        ).to_integral_value(rounding=ROUND_FLOOR)
                    )
                    historical_risk_fraction = (
                        historical_control_risk_fraction(candidate)
                        if use_historical_prior
                        and historical_prior_deployable
                        else None
                    )
                    medium_risk_fraction = (
                        historical_risk_fraction
                        if historical_risk_fraction is not None
                        else MEDIUM_DEFENSIVE_RISK_FRACTION
                        if use_historical_prior
                        else MEDIUM_RECOMMEND_RISK_FRACTION
                        if candidate.native_cognition_recommended is not False
                        else MEDIUM_DEFENSIVE_RISK_FRACTION
                    )
                    if ceiling_discovery_mode:
                        medium_drawdown_scale = Decimal(1)
                    elif total_drawdown_utilization >= ECONOMIC_DRAWDOWN_CEILING:
                        medium_drawdown_scale = Decimal("0.0625")
                    elif total_drawdown_utilization >= Decimal("0.20"):
                        medium_drawdown_scale = Decimal("0.125")
                    elif total_drawdown_utilization >= Decimal("0.15"):
                        medium_drawdown_scale = Decimal("0.25")
                    elif total_drawdown_utilization >= Decimal("0.10"):
                        medium_drawdown_scale = Decimal("0.50")
                    else:
                        medium_drawdown_scale = Decimal(1)
                    with localcontext() as context:
                        context.prec = 100
                        medium_entry_risk_budget_usd = (
                            state.total_capital_usd
                            * medium_risk_fraction
                            * medium_drawdown_scale
                        )
                        medium_hard_drawdown_headroom_usd = max(
                            Decimal(0),
                            (
                                state.peak_total_capital_usd
                                * medium_pretrade_drawdown_ceiling
                            )
                            - total_drawdown_usd
                            - state.open_stop_risk_usd,
                        )
                        # Frontier experiment: the hard pre-trade wall assumes
                        # every open stop realizes at once. Near 25% DD that
                        # deadlocks MEDIUM at broker minimum size and removes
                        # the system's ability to compound back out. The soft
                        # lane preserves the causal DD-scaled entry budget and
                        # physical risk cap, while validating the realized DD
                        # after replay before the policy can be retained.
                        minimum_medium_risk_usd = (
                            candidate.stop_risk_per_multiplier_usd
                        )
                        raw_medium_drawdown_allocator_cap_usd = (
                            risk_left
                            if (
                                soft_medium_drawdown_allocator
                                or ceiling_discovery_mode
                            )
                            else medium_hard_drawdown_headroom_usd
                        )
                        # Drawdown is an intensity control, not an admission
                        # authority. Preserve at least broker-minimum 1x
                        # management for a Trader-executed entry whenever
                        # physical account capacity can fund it.
                        medium_drawdown_allocator_cap_usd = max(
                            minimum_medium_risk_usd,
                            raw_medium_drawdown_allocator_cap_usd,
                        )
                        medium_risk_budget_usd = max(
                            minimum_medium_risk_usd,
                            min(
                                risk_left,
                                medium_drawdown_allocator_cap_usd,
                                max(
                                    medium_entry_risk_budget_usd,
                                    minimum_medium_risk_usd,
                                ),
                            ),
                        )
                    executable_by_risk = int(
                        (
                            medium_risk_budget_usd
                            / candidate.stop_risk_per_multiplier_usd
                        ).to_integral_value(rounding=ROUND_FLOOR)
                    )
                    executable_by_margin = int(
                        (
                            margin_left
                            / candidate.margin_per_multiplier_usd
                        ).to_integral_value(rounding=ROUND_FLOOR)
                    )
                    executable_by_source = int(
                        (
                            sovereign_left
                            / candidate.source_cost_per_multiplier_usd
                        ).to_integral_value(rounding=ROUND_FLOOR)
                    )
                    native_intensity_cap = (
                        (
                            min(
                                candidate.maximum_multiplier,
                                medium_multiplier_cap,
                            )
                            if (
                                candidate.native_cognition_recommended is not False
                                and historical_prior_deployable
                            )
                            else min(
                                candidate.maximum_multiplier,
                                medium_multiplier_cap,
                                3,
                            )
                            if (
                                coordinated_economic_group
                                and candidate.native_cognition_recommended is not False
                            )
                            else min(
                                candidate.maximum_multiplier,
                                medium_multiplier_cap,
                                2,
                            )
                            if (
                                coordinated_economic_group
                                and historical_prior_deployable
                            )
                            else min(candidate.maximum_multiplier, 1)
                        )
                        if use_historical_prior
                        else min(
                            candidate.maximum_multiplier,
                            medium_multiplier_cap,
                        )
                        if (
                            candidate.native_cognition_recommended is not False
                            and candidate.context_quality_disposition == "ALLOW"
                            and candidate.expected_edge_after_cost_usd > 0
                        )
                        else 1
                    )
                    if economic_group_ablation == "SIZING":
                        native_intensity_cap = 1
                    if (
                        medium_drawdown_intensity_trigger is not None
                        and total_drawdown_utilization
                        >= medium_drawdown_intensity_trigger
                        and native_intensity_cap > 1
                    ):
                        native_intensity_cap = 1
                        medium_drawdown_intensity_cap_bind_count += 1
                    multiplier = max(
                        1,
                        min(
                            candidate.maximum_multiplier,
                            native_intensity_cap,
                            executable_by_risk,
                            executable_by_margin,
                            executable_by_source,
                        ),
                    )
                    sizing_intensity_cap_counts[
                        str(native_intensity_cap)
                    ] += 1
                    record_engineering_sensor(
                        "SIZING",
                        epoch_index=epoch_index,
                        signal_fingerprint=candidate.signal_fingerprint,
                        event="BANK_SEED_INPUT",
                        inputs={
                            "current_total_capital_usd": format(
                                state.total_capital_usd, "f"
                            ),
                            "per_entry_seed_fraction": format(
                                MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO,
                                "f",
                            ),
                            "per_entry_seed_budget_usd": format(
                                per_entry_seed_budget, "f"
                            ),
                            "sovereign_available_usd": format(
                                sovereign_left, "f"
                            ),
                        },
                        action="BANK_ISSUES_4PCT_PER_ENTRY_SEED",
                        outputs={
                            "bank_seed_usd": format(bank_seed, "f"),
                            "seed_multiplier_capacity": executable_by_seed,
                        },
                        reaction="PASS_SEED_TO_SIZING",
                    )
                    record_engineering_sensor(
                        "SIZING",
                        epoch_index=epoch_index,
                        signal_fingerprint=candidate.signal_fingerprint,
                        event="SIZING_INPUT",
                        inputs={
                            "mode": candidate_mode.value,
                            "bank_seed_usd": format(bank_seed, "f"),
                            "one_x_source_cost_usd": format(
                                candidate.source_cost_per_multiplier_usd, "f"
                            ),
                            "one_x_stop_risk_usd": format(
                                candidate.stop_risk_per_multiplier_usd, "f"
                            ),
                            "one_x_margin_usd": format(
                                candidate.margin_per_multiplier_usd, "f"
                            ),
                            "risk_left_usd": format(risk_left, "f"),
                            "medium_risk_fraction": format(
                                medium_risk_fraction, "f"
                            ),
                            "historical_control_ready": (
                                historical_prior_deployable
                                if use_historical_prior
                                else None
                            ),
                            "historical_control_risk_fraction": (
                                None
                                if historical_risk_fraction is None
                                else format(
                                    historical_risk_fraction, "f"
                                )
                            ),
                            "medium_entry_risk_budget_usd": format(
                                medium_entry_risk_budget_usd, "f"
                            ),
                            "total_drawdown_utilization": format(
                                total_drawdown_utilization, "f"
                            ),
                            "medium_drawdown_scale": format(
                                medium_drawdown_scale, "f"
                            ),
                            "medium_hard_drawdown_headroom_usd": format(
                                medium_hard_drawdown_headroom_usd, "f"
                            ),
                            "medium_drawdown_allocator": (
                                "SOFT_CAUSAL_BUDGET"
                                if soft_medium_drawdown_allocator
                                else "HARD_WORST_CASE_HEADROOM"
                            ),
                            "medium_pretrade_drawdown_ceiling": format(
                                medium_pretrade_drawdown_ceiling, "f"
                            ),
                            "medium_drawdown_intensity_trigger": (
                                None
                                if medium_drawdown_intensity_trigger is None
                                else format(
                                    medium_drawdown_intensity_trigger, "f"
                                )
                            ),
                            "medium_drawdown_allocator_cap_usd": format(
                                medium_drawdown_allocator_cap_usd, "f"
                            ),
                            "minimum_medium_risk_usd": format(
                                minimum_medium_risk_usd, "f"
                            ),
                            "medium_risk_budget_usd": format(
                                medium_risk_budget_usd, "f"
                            ),
                            "margin_left_usd": format(margin_left, "f"),
                            "native_confidence_band": native_confidence(
                                candidate
                            ),
                            "native_executive_synthesis": (
                                native_profile_map[
                                    candidate.signal_fingerprint
                                ]["executive_synthesis"]
                            ),
                            "historical_prior_deployable": (
                                historical_prior_deployable
                                if use_historical_prior
                                else None
                            ),
                        },
                        action="SIZE_FROM_BANK_SEED_WITH_NATIVE_CAPABILITY",
                        outputs={
                            "selected_multiplier": multiplier,
                            "native_intensity_cap": native_intensity_cap,
                        },
                        reaction="AWAIT_HARD_CAPACITY_CHECK",
                        call=True,
                    )
                    economic_cap = native_intensity_cap
                    source_left = sovereign_left
                else:
                    adaptive_leverage_calls += 1
                    source_left = min(
                        cushion_left,
                        portfolio_attack_release_left,
                    )
                    record_engineering_sensor(
                        "ADAPTIVE_LEVERAGE",
                        epoch_index=epoch_index,
                        signal_fingerprint=candidate.signal_fingerprint,
                        event="LEVERAGE_INPUT",
                        inputs={
                            "provider_maximum_multiplier": (
                                candidate.maximum_multiplier
                            ),
                            "attack_expected_net_utility_usd": format(
                                candidate.attack_expected_net_utility_usd,
                                "f",
                            ),
                            "cushion_left_usd": format(cushion_left, "f"),
                            "risk_left_usd": format(risk_left, "f"),
                            "margin_left_usd": format(margin_left, "f"),
                        },
                        action="EVALUATE_ATTACK_MULTIPLIER",
                        outputs={},
                        reaction="AWAIT_LEVERAGE_CAPS",
                        call=True,
                    )
                    economic_cap = candidate.maximum_multiplier
                    coordinated_attack_cap = attack_multiplier_cap
                    if economic_group_ablation == "ADAPTIVE_LEVERAGE":
                        coordinated_attack_cap = ATTACK_MINIMUM_MULTIPLIER
                    elif coordinated_economic_group:
                        if (
                            candidate.walk_forward_positive_block_count >= 5
                            and candidate.attack_expected_net_utility_usd > 0
                        ):
                            coordinated_attack_cap = attack_multiplier_cap
                        elif candidate.walk_forward_positive_block_count >= 5:
                            coordinated_attack_cap = min(
                                attack_multiplier_cap, 6
                            )
                        else:
                            coordinated_attack_cap = min(
                                attack_multiplier_cap, 4
                            )
                    attack_scaling_capital_base_usd = state.total_capital_usd
                    if ceiling_attack_compound_hysteresis_fraction is not None:
                        if state.total_capital_usd < attack_scaling_capital_anchor_usd:
                            attack_scaling_capital_anchor_usd = state.total_capital_usd
                            attack_compound_hysteresis_drop_count += 1
                        elif state.total_capital_usd >= (
                            attack_scaling_capital_anchor_usd
                            * (
                                Decimal(1)
                                + ceiling_attack_compound_hysteresis_fraction
                            )
                        ):
                            attack_scaling_capital_anchor_usd = state.total_capital_usd
                            attack_compound_hysteresis_raise_count += 1
                        else:
                            attack_compound_hysteresis_hold_count += 1
                        attack_scaling_capital_base_usd = (
                            attack_scaling_capital_anchor_usd
                        )
                    if (
                        ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction
                        is not None
                        and attack_stress_confidence_reinvestment_hysteresis_armed
                    ):
                        if (
                            state.total_capital_usd
                            < attack_stress_confidence_reinvestment_anchor_usd
                        ):
                            attack_stress_confidence_reinvestment_anchor_usd = (
                                state.total_capital_usd
                            )
                            attack_stress_confidence_reinvestment_drop_count += 1
                        elif state.total_capital_usd >= (
                            attack_stress_confidence_reinvestment_anchor_usd
                            * (
                                Decimal(1)
                                + ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction
                            )
                        ):
                            attack_stress_confidence_reinvestment_hysteresis_armed = False
                            attack_stress_confidence_reinvestment_release_count += 1
                        else:
                            attack_scaling_capital_base_usd = min(
                                attack_scaling_capital_base_usd,
                                attack_stress_confidence_reinvestment_anchor_usd,
                            )
                            attack_stress_confidence_reinvestment_hold_count += 1
                    if (
                        ceiling_discovery_mode
                        and ceiling_growth_leverage_slope is not None
                    ):
                        with localcontext() as context:
                            context.prec = 100
                            growth_multiple = max(
                                Decimal(1),
                                attack_scaling_capital_base_usd / INITIAL_CAPITAL_USD,
                            )
                            growth_cap = max(
                                ATTACK_MINIMUM_MULTIPLIER,
                                int(
                                    (
                                        growth_multiple
                                        * ceiling_growth_leverage_slope
                                    ).to_integral_value(
                                        rounding=ROUND_FLOOR
                                    )
                                ),
                            )
                        coordinated_attack_cap = min(
                            coordinated_attack_cap,
                            growth_cap,
                        )
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_loss_streak_trigger is not None
                        and trader_attack_loss_streak[candidate.trader_id]
                        >= ceiling_attack_loss_streak_trigger
                    ):
                        tapered_attack_cap = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(coordinated_attack_cap)
                                    * ceiling_attack_loss_streak_taper_fraction
                                ).to_integral_value(
                                    rounding=ROUND_FLOOR
                                )
                            ),
                        )
                        if tapered_attack_cap < coordinated_attack_cap:
                            attack_loss_streak_taper_bind_count += 1
                        coordinated_attack_cap = min(
                            coordinated_attack_cap,
                            tapered_attack_cap,
                        )
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_drawdown_taper_trigger is not None
                        and total_drawdown_utilization
                        >= ceiling_attack_drawdown_taper_trigger
                    ):
                        drawdown_tapered_attack_cap = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(coordinated_attack_cap)
                                    * ceiling_attack_drawdown_taper_fraction
                                ).to_integral_value(
                                    rounding=ROUND_FLOOR
                                )
                            ),
                        )
                        if drawdown_tapered_attack_cap < coordinated_attack_cap:
                            attack_drawdown_taper_bind_count += 1
                        coordinated_attack_cap = min(
                            coordinated_attack_cap,
                            drawdown_tapered_attack_cap,
                        )
                    stress_confidence_active = False
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_stress_confidence_drawdown_trigger
                        is not None
                        and ceiling_attack_stress_confidence_ratio_ceiling
                        is not None
                        and total_drawdown_utilization
                        >= ceiling_attack_stress_confidence_drawdown_trigger
                        and candidate.walk_forward_expected_structural_r
                        is not None
                        and (
                            ceiling_attack_stress_confidence_multiplier_lower is None
                            or (
                                ceiling_attack_stress_confidence_multiplier_upper is not None
                                and ceiling_attack_stress_confidence_multiplier_lower
                                <= coordinated_attack_cap
                                <= ceiling_attack_stress_confidence_multiplier_upper
                            )
                        )
                        and candidate.walk_forward_block_dispersion_r > 0
                        and (
                            ceiling_attack_stress_confidence_target_r_floor is None
                            or candidate.planned_target_r
                            >= ceiling_attack_stress_confidence_target_r_floor
                        )
                        and (
                            ceiling_attack_stress_confidence_capital_floor is None
                            or state.total_capital_usd
                            >= ceiling_attack_stress_confidence_capital_floor
                        )
                        and (
                            ceiling_attack_stress_confidence_capital_ceiling is None
                            or state.total_capital_usd
                            <= ceiling_attack_stress_confidence_capital_ceiling
                        )
                        and (
                            ceiling_attack_stress_confidence_projected_risk_fraction_trigger
                            is None
                            or (
                                state.total_capital_usd > 0
                                and (
                                    candidate.stop_risk_per_multiplier_usd
                                    * Decimal(coordinated_attack_cap)
                                    / state.total_capital_usd
                                )
                                >= ceiling_attack_stress_confidence_projected_risk_fraction_trigger
                            )
                        )
                    ):
                        with localcontext() as context:
                            context.prec = 100
                            stress_confidence_ratio = (
                                candidate.walk_forward_expected_structural_r
                                / candidate.walk_forward_block_dispersion_r
                            )
                        if (
                            stress_confidence_ratio
                            <= ceiling_attack_stress_confidence_ratio_ceiling
                        ):
                            stress_confidence_active = True
                            if (
                                ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction
                                is not None
                                and ceiling_attack_stress_confidence_risk_budget_taper_fraction
                                < Decimal(1)
                                and not attack_stress_confidence_reinvestment_hysteresis_armed
                            ):
                                attack_stress_confidence_reinvestment_anchor_usd = (
                                    state.total_capital_usd
                                )
                                attack_stress_confidence_reinvestment_hysteresis_armed = True
                                attack_stress_confidence_reinvestment_arm_count += 1
                            stress_confidence_tapered_attack_cap = max(
                                ATTACK_MINIMUM_MULTIPLIER,
                                int(
                                    (
                                        Decimal(coordinated_attack_cap)
                                        * ceiling_attack_stress_confidence_taper_fraction
                                    ).to_integral_value(
                                        rounding=ROUND_FLOOR
                                    )
                                ),
                            )
                            if (
                                stress_confidence_tapered_attack_cap
                                < coordinated_attack_cap
                            ):
                                attack_stress_confidence_taper_bind_count += 1
                            coordinated_attack_cap = min(
                                coordinated_attack_cap,
                                stress_confidence_tapered_attack_cap,
                            )
                    state_pressure_active = (
                        ceiling_discovery_mode
                        and ceiling_attack_state_pressure_expected_minutes_floor
                        is not None
                        and candidate.expected_capital_minutes
                        >= ceiling_attack_state_pressure_expected_minutes_floor
                        and (
                            ceiling_attack_state_pressure_target_r_ceiling is None
                            or candidate.planned_target_r
                            <= ceiling_attack_state_pressure_target_r_ceiling
                        )
                        and (
                            ceiling_attack_state_pressure_confidence_ratio_ceiling is None
                            or (
                                candidate.walk_forward_expected_structural_r is not None
                                and candidate.walk_forward_block_dispersion_r > 0
                                and (
                                    candidate.walk_forward_expected_structural_r
                                    / candidate.walk_forward_block_dispersion_r
                                )
                                <= ceiling_attack_state_pressure_confidence_ratio_ceiling
                            )
                        )
                        and (
                            ceiling_attack_state_pressure_projected_risk_fraction_trigger
                            is None
                            or (
                                state.total_capital_usd > 0
                                and (
                                    candidate.stop_risk_per_multiplier_usd
                                    * Decimal(coordinated_attack_cap)
                                    / state.total_capital_usd
                                )
                                >= ceiling_attack_state_pressure_projected_risk_fraction_trigger
                            )
                        )
                        and (
                            ceiling_attack_state_pressure_capital_floor is None
                            or state.total_capital_usd
                            >= ceiling_attack_state_pressure_capital_floor
                        )
                        and (
                            ceiling_attack_state_pressure_capital_ceiling is None
                            or state.total_capital_usd
                            <= ceiling_attack_state_pressure_capital_ceiling
                        )
                        and (
                            ceiling_attack_state_pressure_market_posture is None
                            or candidate.market_regime_posture
                            == ceiling_attack_state_pressure_market_posture
                        )
                        and (
                            ceiling_attack_state_pressure_h1_range_state is None
                            or candidate.h1_range_state
                            == ceiling_attack_state_pressure_h1_range_state
                        )
                        and (
                            ceiling_attack_state_pressure_h4_range_state is None
                            or candidate.h4_range_state
                            == ceiling_attack_state_pressure_h4_range_state
                        )
                    )
                    state_pressure2_active = (
                        ceiling_discovery_mode
                        and ceiling_attack_state_pressure2_expected_minutes_floor
                        is not None
                        and candidate.expected_capital_minutes
                        >= ceiling_attack_state_pressure2_expected_minutes_floor
                        and (
                            ceiling_attack_state_pressure2_target_r_ceiling is None
                            or candidate.planned_target_r
                            <= ceiling_attack_state_pressure2_target_r_ceiling
                        )
                        and (
                            ceiling_attack_state_pressure2_confidence_ratio_ceiling is None
                            or (
                                candidate.walk_forward_expected_structural_r is not None
                                and candidate.walk_forward_block_dispersion_r > 0
                                and (
                                    candidate.walk_forward_expected_structural_r
                                    / candidate.walk_forward_block_dispersion_r
                                )
                                <= ceiling_attack_state_pressure2_confidence_ratio_ceiling
                            )
                        )
                        and (
                            ceiling_attack_state_pressure2_projected_risk_fraction_trigger
                            is None
                            or (
                                state.total_capital_usd > 0
                                and (
                                    candidate.stop_risk_per_multiplier_usd
                                    * Decimal(coordinated_attack_cap)
                                    / state.total_capital_usd
                                )
                                >= ceiling_attack_state_pressure2_projected_risk_fraction_trigger
                            )
                        )
                        and (
                            ceiling_attack_state_pressure2_capital_floor is None
                            or state.total_capital_usd
                            >= ceiling_attack_state_pressure2_capital_floor
                        )
                        and (
                            ceiling_attack_state_pressure2_capital_ceiling is None
                            or state.total_capital_usd
                            <= ceiling_attack_state_pressure2_capital_ceiling
                        )
                        and (
                            ceiling_attack_state_pressure2_market_posture is None
                            or candidate.market_regime_posture
                            == ceiling_attack_state_pressure2_market_posture
                        )
                        and (
                            ceiling_attack_state_pressure2_h1_range_state is None
                            or candidate.h1_range_state
                            == ceiling_attack_state_pressure2_h1_range_state
                        )
                        and (
                            ceiling_attack_state_pressure2_h4_range_state is None
                            or candidate.h4_range_state
                            == ceiling_attack_state_pressure2_h4_range_state
                        )
                    )
                    if (
                        state_pressure2_active
                        and ceiling_attack_state_pressure2_cap_taper_fraction
                        < Decimal(1)
                    ):
                        state_pressure2_tapered_attack_cap = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(coordinated_attack_cap)
                                    * ceiling_attack_state_pressure2_cap_taper_fraction
                                ).to_integral_value(rounding=ROUND_FLOOR)
                            ),
                        )
                        coordinated_attack_cap = min(
                            coordinated_attack_cap,
                            state_pressure2_tapered_attack_cap,
                        )
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_trader_loss_ratio_trigger is not None
                        and trader_attack_settlement_count[candidate.trader_id]
                        >= ceiling_attack_trader_loss_ratio_min_settlements
                    ):
                        realized_attack_profit = attack_gross_profit_by_trader[
                            candidate.trader_id
                        ]
                        realized_attack_loss = attack_gross_loss_by_trader[
                            candidate.trader_id
                        ]
                        trader_loss_pressure_active = (
                            realized_attack_loss > 0
                            and (
                                realized_attack_profit <= 0
                                or (
                                    realized_attack_loss
                                    / realized_attack_profit
                                )
                                >= ceiling_attack_trader_loss_ratio_trigger
                            )
                        )
                        if trader_loss_pressure_active:
                            trader_loss_ratio_tapered_attack_cap = max(
                                ATTACK_MINIMUM_MULTIPLIER,
                                int(
                                    (
                                        Decimal(coordinated_attack_cap)
                                        * ceiling_attack_trader_loss_ratio_taper_fraction
                                    ).to_integral_value(
                                        rounding=ROUND_FLOOR
                                    )
                                ),
                            )
                            if (
                                trader_loss_ratio_tapered_attack_cap
                                < coordinated_attack_cap
                            ):
                                attack_trader_loss_ratio_taper_bind_count += 1
                            coordinated_attack_cap = min(
                                coordinated_attack_cap,
                                trader_loss_ratio_tapered_attack_cap,
                            )
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_recent_trader_loss_window is not None
                        and ceiling_attack_recent_trader_loss_fraction_trigger
                        is not None
                        and total_drawdown_utilization
                        >= ceiling_attack_recent_trader_loss_drawdown_trigger
                    ):
                        recent_values = trader_attack_recent_net_pnl[
                            candidate.trader_id
                        ]
                        if len(recent_values) >= 2:
                            recent_net_pnl = sum(recent_values, Decimal(0))
                            recent_loss_fraction = (
                                (-recent_net_pnl) / state.total_capital_usd
                                if recent_net_pnl < 0
                                and state.total_capital_usd > 0
                                else Decimal(0)
                            )
                            if (
                                recent_loss_fraction
                                >= ceiling_attack_recent_trader_loss_fraction_trigger
                            ):
                                recent_loss_tapered_attack_cap = max(
                                    ATTACK_MINIMUM_MULTIPLIER,
                                    int(
                                        (
                                            Decimal(coordinated_attack_cap)
                                            * ceiling_attack_recent_trader_loss_taper_fraction
                                        ).to_integral_value(
                                            rounding=ROUND_FLOOR
                                        )
                                    ),
                                )
                                if (
                                    recent_loss_tapered_attack_cap
                                    < coordinated_attack_cap
                                ):
                                    attack_recent_trader_loss_taper_bind_count += 1
                                coordinated_attack_cap = min(
                                    coordinated_attack_cap,
                                    recent_loss_tapered_attack_cap,
                                )
                    ceiling_drawdown_risk_cap = candidate.maximum_multiplier
                    if (
                        ceiling_attack_drawdown_budget_any_active
                    ):
                        with localcontext() as context:
                            context.prec = 100
                            live_ceiling_attack_headroom_usd = max(
                                Decimal(0),
                                (
                                    state.peak_total_capital_usd
                                    * ceiling_attack_drawdown_budget_fraction
                                )
                                - total_drawdown_usd
                                - state.open_stop_risk_usd
                                - attack_risk_selected_this_epoch,
                            )
                            ceiling_drawdown_risk_cap = max(
                                0,
                                int(
                                    (
                                        live_ceiling_attack_headroom_usd
                                        / candidate.stop_risk_per_multiplier_usd
                                    ).to_integral_value(
                                        rounding=ROUND_FLOOR
                                    )
                                ),
                            )
                    ceiling_single_trade_risk_cap = candidate.maximum_multiplier
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_single_trade_risk_fraction is not None
                    ):
                        with localcontext() as context:
                            context.prec = 100
                            effective_single_trade_risk_fraction = (
                                ceiling_attack_single_trade_risk_fraction
                            )
                            if (
                                ceiling_attack_drawdown_taper_trigger is not None
                                and total_drawdown_utilization
                                >= ceiling_attack_drawdown_taper_trigger
                            ):
                                effective_single_trade_risk_fraction *= (
                                    ceiling_attack_drawdown_taper_fraction
                                )
                            if (
                                stress_confidence_active
                                and ceiling_attack_stress_confidence_risk_budget_taper_fraction
                                < Decimal(1)
                            ):
                                effective_single_trade_risk_fraction *= (
                                    ceiling_attack_stress_confidence_risk_budget_taper_fraction
                                )
                                attack_stress_confidence_risk_budget_bind_count += 1
                            if (
                                state_pressure_active
                                and ceiling_attack_state_pressure_risk_budget_taper_fraction
                                < Decimal(1)
                            ):
                                effective_single_trade_risk_fraction *= (
                                    ceiling_attack_state_pressure_risk_budget_taper_fraction
                                )
                                attack_state_pressure_risk_budget_bind_count += 1
                            if (
                                state_pressure2_active
                                and ceiling_attack_state_pressure2_risk_budget_taper_fraction
                                < Decimal(1)
                            ):
                                effective_single_trade_risk_fraction *= (
                                    ceiling_attack_state_pressure2_risk_budget_taper_fraction
                                )
                                attack_state_pressure2_risk_budget_bind_count += 1
                            if (
                                ceiling_portfolio_shock_trigger_fraction is not None
                                and portfolio_last_attack_loss_fraction
                                >= ceiling_portfolio_shock_trigger_fraction
                            ):
                                effective_single_trade_risk_fraction *= (
                                    ceiling_portfolio_shock_taper_fraction
                                )
                                portfolio_attack_shock_taper_bind_count += 1
                                if ceiling_portfolio_shock_one_shot:
                                    portfolio_last_attack_loss_fraction = (
                                        Decimal(0)
                                    )
                            if (
                                ceiling_attack_trader_shock_trigger_fraction
                                is not None
                                and total_drawdown_utilization
                                >= ceiling_attack_trader_shock_drawdown_trigger
                                and (
                                    ceiling_attack_trader_shock_capital_ceiling is None
                                    or state.total_capital_usd
                                    <= ceiling_attack_trader_shock_capital_ceiling
                                )
                                and trader_last_attack_loss_fraction[
                                    candidate.trader_id
                                ]
                                >= ceiling_attack_trader_shock_trigger_fraction
                            ):
                                effective_single_trade_risk_fraction *= (
                                    ceiling_attack_trader_shock_taper_fraction
                                )
                                attack_trader_shock_taper_bind_count += 1
                                trader_shock_protected_signals.add(
                                    candidate.signal_fingerprint
                                )
                                trader_last_attack_loss_fraction[
                                    candidate.trader_id
                                ] = Decimal(0)
                            single_trade_risk_budget_usd = max(
                                Decimal(0),
                                attack_scaling_capital_base_usd
                                * effective_single_trade_risk_fraction,
                            )
                            ceiling_single_trade_risk_cap = max(
                                0,
                                int(
                                    (
                                        single_trade_risk_budget_usd
                                        / candidate.source_cost_per_multiplier_usd
                                    ).to_integral_value(
                                        rounding=ROUND_FLOOR
                                    )
                                ),
                            )
                    leverage_caps = {
                        "PROVIDER_MAX": candidate.maximum_multiplier,
                        "CEILING_SINGLE_TRADE_RISK_CAP": (
                            ceiling_single_trade_risk_cap
                        ),
                        "CEILING_DRAWDOWN_RISK_CAP": (
                            ceiling_drawdown_risk_cap
                        ),
                        "DISTRIBUTED_ATTACK_CAP": (
                            coordinated_attack_cap
                            if distributed_attack_frontier
                            else candidate.maximum_multiplier
                        ),
                        "CUSHION_FUNDING_CAP": int(
                            (
                                source_left
                                / candidate.source_cost_per_multiplier_usd
                            ).to_integral_value(rounding=ROUND_FLOOR)
                        ),
                        "RISK_CAP": int(
                            (
                                risk_left
                                / candidate.stop_risk_per_multiplier_usd
                            ).to_integral_value(rounding=ROUND_FLOOR)
                        ),
                        "MARGIN_CAP": int(
                            (
                                margin_left
                                / candidate.margin_per_multiplier_usd
                            ).to_integral_value(rounding=ROUND_FLOOR)
                        ),
                    }
                    preliminary_multiplier = max(0, min(leverage_caps.values()))
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_low_multiplier_demotion_upper is not None
                        and total_drawdown_utilization
                        >= ceiling_attack_low_multiplier_demotion_drawdown_trigger
                        and ATTACK_MINIMUM_MULTIPLIER
                        <= preliminary_multiplier
                        <= ceiling_attack_low_multiplier_demotion_upper
                    ):
                        attack_low_multiplier_demotion_bind_count += 1
                        leverage_caps[
                            "CEILING_LOW_MULTIPLIER_DD_DEMOTION_CAP"
                        ] = 1
                    preliminary_multiplier = max(0, min(leverage_caps.values()))
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_drawdown_window_lower is not None
                        and ceiling_attack_drawdown_window_upper is not None
                        and ceiling_attack_drawdown_window_multiplier_lower
                        is not None
                        and ceiling_attack_drawdown_window_multiplier_upper
                        is not None
                        and ceiling_attack_drawdown_window_lower
                        <= total_drawdown_utilization
                        < ceiling_attack_drawdown_window_upper
                        and ceiling_attack_drawdown_window_multiplier_lower
                        <= preliminary_multiplier
                        <= ceiling_attack_drawdown_window_multiplier_upper
                    ):
                        drawdown_window_tapered_multiplier = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(preliminary_multiplier)
                                    * ceiling_attack_drawdown_window_taper_fraction
                                ).to_integral_value(rounding=ROUND_FLOOR)
                            ),
                        )
                        if drawdown_window_tapered_multiplier < preliminary_multiplier:
                            attack_drawdown_window_taper_bind_count += 1
                            leverage_caps[
                                "CEILING_DRAWDOWN_WINDOW_TAPER_CAP"
                            ] = drawdown_window_tapered_multiplier
                    preliminary_multiplier = max(0, min(leverage_caps.values()))
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_drawdown_window2_lower is not None
                        and ceiling_attack_drawdown_window2_upper is not None
                        and ceiling_attack_drawdown_window2_multiplier_lower
                        is not None
                        and ceiling_attack_drawdown_window2_multiplier_upper
                        is not None
                        and ceiling_attack_drawdown_window2_lower
                        <= total_drawdown_utilization
                        < ceiling_attack_drawdown_window2_upper
                        and ceiling_attack_drawdown_window2_multiplier_lower
                        <= preliminary_multiplier
                        <= ceiling_attack_drawdown_window2_multiplier_upper
                    ):
                        drawdown_window2_tapered_multiplier = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(preliminary_multiplier)
                                    * ceiling_attack_drawdown_window2_taper_fraction
                                ).to_integral_value(rounding=ROUND_FLOOR)
                            ),
                        )
                        if drawdown_window2_tapered_multiplier < preliminary_multiplier:
                            attack_drawdown_window2_taper_bind_count += 1
                            leverage_caps[
                                "CEILING_DRAWDOWN_WINDOW2_TAPER_CAP"
                            ] = drawdown_window2_tapered_multiplier
                    preliminary_multiplier = max(0, min(leverage_caps.values()))
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_drawdown_window3_lower is not None
                        and ceiling_attack_drawdown_window3_upper is not None
                        and ceiling_attack_drawdown_window3_multiplier_lower
                        is not None
                        and ceiling_attack_drawdown_window3_multiplier_upper
                        is not None
                        and ceiling_attack_drawdown_window3_lower
                        <= total_drawdown_utilization
                        < ceiling_attack_drawdown_window3_upper
                        and ceiling_attack_drawdown_window3_multiplier_lower
                        <= preliminary_multiplier
                        <= ceiling_attack_drawdown_window3_multiplier_upper
                    ):
                        drawdown_window3_tapered_multiplier = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(preliminary_multiplier)
                                    * ceiling_attack_drawdown_window3_taper_fraction
                                ).to_integral_value(rounding=ROUND_FLOOR)
                            ),
                        )
                        if drawdown_window3_tapered_multiplier < preliminary_multiplier:
                            attack_drawdown_window3_taper_bind_count += 1
                            leverage_caps[
                                "CEILING_DRAWDOWN_WINDOW3_TAPER_CAP"
                            ] = drawdown_window3_tapered_multiplier
                    preliminary_multiplier = max(0, min(leverage_caps.values()))
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_drawdown_window4_lower is not None
                        and ceiling_attack_drawdown_window4_upper is not None
                        and ceiling_attack_drawdown_window4_multiplier_lower
                        is not None
                        and ceiling_attack_drawdown_window4_multiplier_upper
                        is not None
                        and ceiling_attack_drawdown_window4_lower
                        <= total_drawdown_utilization
                        < ceiling_attack_drawdown_window4_upper
                        and ceiling_attack_drawdown_window4_multiplier_lower
                        <= preliminary_multiplier
                        <= ceiling_attack_drawdown_window4_multiplier_upper
                    ):
                        drawdown_window4_tapered_multiplier = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(preliminary_multiplier)
                                    * ceiling_attack_drawdown_window4_taper_fraction
                                ).to_integral_value(rounding=ROUND_FLOOR)
                            ),
                        )
                        if drawdown_window4_tapered_multiplier < preliminary_multiplier:
                            attack_drawdown_window4_taper_bind_count += 1
                            leverage_caps[
                                "CEILING_DRAWDOWN_WINDOW4_TAPER_CAP"
                            ] = drawdown_window4_tapered_multiplier
                    preliminary_multiplier = max(0, min(leverage_caps.values()))
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_drawdown_window5_lower is not None
                        and ceiling_attack_drawdown_window5_upper is not None
                        and ceiling_attack_drawdown_window5_multiplier_lower
                        is not None
                        and ceiling_attack_drawdown_window5_multiplier_upper
                        is not None
                        and ceiling_attack_drawdown_window5_lower
                        <= total_drawdown_utilization
                        < ceiling_attack_drawdown_window5_upper
                        and ceiling_attack_drawdown_window5_multiplier_lower
                        <= preliminary_multiplier
                        <= ceiling_attack_drawdown_window5_multiplier_upper
                    ):
                        drawdown_window5_tapered_multiplier = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(preliminary_multiplier)
                                    * ceiling_attack_drawdown_window5_taper_fraction
                                ).to_integral_value(rounding=ROUND_FLOOR)
                            ),
                        )
                        if drawdown_window5_tapered_multiplier < preliminary_multiplier:
                            attack_drawdown_window5_taper_bind_count += 1
                            leverage_caps[
                                "CEILING_DRAWDOWN_WINDOW5_TAPER_CAP"
                            ] = drawdown_window5_tapered_multiplier
                    preliminary_multiplier = max(0, min(leverage_caps.values()))
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_drawdown_window6_lower is not None
                        and ceiling_attack_drawdown_window6_upper is not None
                        and ceiling_attack_drawdown_window6_multiplier_lower
                        is not None
                        and ceiling_attack_drawdown_window6_multiplier_upper
                        is not None
                        and ceiling_attack_drawdown_window6_lower
                        <= total_drawdown_utilization
                        < ceiling_attack_drawdown_window6_upper
                        and ceiling_attack_drawdown_window6_multiplier_lower
                        <= preliminary_multiplier
                        <= ceiling_attack_drawdown_window6_multiplier_upper
                        and (
                            ceiling_attack_drawdown_window6_capital_floor is None
                            or state.total_capital_usd
                            >= ceiling_attack_drawdown_window6_capital_floor
                        )
                        and (
                            ceiling_attack_drawdown_window6_capital_ceiling is None
                            or state.total_capital_usd
                            <= ceiling_attack_drawdown_window6_capital_ceiling
                        )
                    ):
                        drawdown_window6_tapered_multiplier = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(preliminary_multiplier)
                                    * ceiling_attack_drawdown_window6_taper_fraction
                                ).to_integral_value(rounding=ROUND_FLOOR)
                            ),
                        )
                        if drawdown_window6_tapered_multiplier < preliminary_multiplier:
                            attack_drawdown_window6_taper_bind_count += 1
                            leverage_caps[
                                "CEILING_DRAWDOWN_WINDOW6_TAPER_CAP"
                            ] = drawdown_window6_tapered_multiplier
                    preliminary_multiplier = max(0, min(leverage_caps.values()))
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_drawdown_window7_lower is not None
                        and ceiling_attack_drawdown_window7_upper is not None
                        and ceiling_attack_drawdown_window7_multiplier_lower
                        is not None
                        and ceiling_attack_drawdown_window7_multiplier_upper
                        is not None
                        and ceiling_attack_drawdown_window7_lower
                        <= total_drawdown_utilization
                        < ceiling_attack_drawdown_window7_upper
                        and ceiling_attack_drawdown_window7_multiplier_lower
                        <= preliminary_multiplier
                        <= ceiling_attack_drawdown_window7_multiplier_upper
                        and (
                            ceiling_attack_drawdown_window7_capital_floor is None
                            or state.total_capital_usd
                            >= ceiling_attack_drawdown_window7_capital_floor
                        )
                        and (
                            ceiling_attack_drawdown_window7_capital_ceiling is None
                            or state.total_capital_usd
                            <= ceiling_attack_drawdown_window7_capital_ceiling
                        )
                    ):
                        drawdown_window7_tapered_multiplier = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(preliminary_multiplier)
                                    * ceiling_attack_drawdown_window7_taper_fraction
                                ).to_integral_value(rounding=ROUND_FLOOR)
                            ),
                        )
                        if drawdown_window7_tapered_multiplier < preliminary_multiplier:
                            attack_drawdown_window7_taper_bind_count += 1
                            leverage_caps[
                                "CEILING_DRAWDOWN_WINDOW7_TAPER_CAP"
                            ] = drawdown_window7_tapered_multiplier
                    preliminary_multiplier = max(0, min(leverage_caps.values()))
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_risk_fraction_band_lower is not None
                        and ceiling_attack_risk_fraction_band_upper is not None
                        and preliminary_multiplier >= ATTACK_MINIMUM_MULTIPLIER
                    ):
                        with localcontext() as context:
                            context.prec = 100
                            proposed_attack_risk_fraction = _ratio(
                                candidate.stop_risk_per_multiplier_usd
                                * Decimal(preliminary_multiplier),
                                state.total_capital_usd,
                            )
                        if (
                            ceiling_attack_risk_fraction_band_lower
                            <= proposed_attack_risk_fraction
                            < ceiling_attack_risk_fraction_band_upper
                        ):
                            risk_band_tapered_multiplier = max(
                                ATTACK_MINIMUM_MULTIPLIER,
                                int(
                                    (
                                        Decimal(preliminary_multiplier)
                                        * ceiling_attack_risk_fraction_band_taper_fraction
                                    ).to_integral_value(rounding=ROUND_FLOOR)
                                ),
                            )
                            if risk_band_tapered_multiplier < preliminary_multiplier:
                                attack_risk_fraction_band_taper_bind_count += 1
                                leverage_caps[
                                    "CEILING_RISK_FRACTION_BAND_TAPER_CAP"
                                ] = risk_band_tapered_multiplier
                    band_reference_multiplier = max(
                        0, min(leverage_caps.values())
                    )
                    if (
                        ceiling_discovery_mode
                        and ceiling_attack_multiplier_band_lower is not None
                        and ceiling_attack_multiplier_band_upper is not None
                        and ceiling_attack_multiplier_band_lower
                        <= band_reference_multiplier
                        <= ceiling_attack_multiplier_band_upper
                    ):
                        band_tapered_multiplier = max(
                            ATTACK_MINIMUM_MULTIPLIER,
                            int(
                                (
                                    Decimal(band_reference_multiplier)
                                    * ceiling_attack_multiplier_band_taper_fraction
                                ).to_integral_value(rounding=ROUND_FLOOR)
                            ),
                        )
                        if band_tapered_multiplier < band_reference_multiplier:
                            attack_multiplier_band_taper_bind_count += 1
                            leverage_caps[
                                "CEILING_MULTIPLIER_BAND_TAPER_CAP"
                            ] = band_tapered_multiplier
                    multiplier = max(0, min(leverage_caps.values()))
                    binding_caps = tuple(
                        name
                        for name, cap in leverage_caps.items()
                        if cap == multiplier
                    )
                    feasible_leverage_capital = (
                        candidate.source_cost_per_multiplier_usd
                        * Decimal(multiplier)
                    )
                    requested_leverage_capital = feasible_leverage_capital
                    withheld_leverage_capital = Decimal(0)
                    if multiplier < ATTACK_MINIMUM_MULTIPLIER:
                        record_engineering_sensor(
                            "ADAPTIVE_LEVERAGE",
                            epoch_index=epoch_index,
                            signal_fingerprint=candidate.signal_fingerprint,
                            event="LEVERAGE_OUTPUT",
                            inputs={
                                "caps": leverage_caps,
                                "minimum_attack_multiplier": (
                                    ATTACK_MINIMUM_MULTIPLIER
                                ),
                            },
                            action="FALLBACK_ATTACK_TO_DEFENSIVE_MEDIUM",
                            outputs={
                                "feasible_attack_multiplier": multiplier,
                                "economic_treatment": "DEFENSIVE_MEDIUM",
                            },
                            reaction=(
                                "KEEP_TRADER_ENTRY_AND_REMOVE_ONLY_ATTACK_ESCALATION"
                            ),
                            reasons=binding_caps,
                        )
                        candidate_mode = CiboTraderLabMode.MEDIUM
                        sizing_calls += 1
                        source_left = sovereign_left
                        executable_by_risk = int(
                            (
                                risk_left
                                / candidate.stop_risk_per_multiplier_usd
                            ).to_integral_value(rounding=ROUND_FLOOR)
                        )
                        executable_by_margin = int(
                            (
                                margin_left
                                / candidate.margin_per_multiplier_usd
                            ).to_integral_value(rounding=ROUND_FLOOR)
                        )
                        executable_by_source = int(
                            (
                                sovereign_left
                                / candidate.source_cost_per_multiplier_usd
                            ).to_integral_value(rounding=ROUND_FLOOR)
                        )
                        multiplier = 1
                        medium_risk_budget_usd = (
                            candidate.stop_risk_per_multiplier_usd
                            * Decimal(multiplier)
                        )
                        economic_cap = 1
                    else:
                        record_engineering_sensor(
                            "ADAPTIVE_LEVERAGE",
                            epoch_index=epoch_index,
                            signal_fingerprint=candidate.signal_fingerprint,
                            event="LEVERAGE_OUTPUT",
                            inputs={"caps": leverage_caps},
                            action="APPROVE_ATTACK_MULTIPLIER",
                            outputs={
                                "selected_multiplier": multiplier,
                                "binding_caps": list(binding_caps),
                                "theoretical_multiplier": (
                                    candidate.maximum_multiplier
                                ),
                            },
                            reaction="ATTACK_EXECUTABLE_CAPACITY_RELEASED",
                            reasons=binding_caps,
                            approval=True,
                            restriction=withheld_leverage_capital > 0,
                            requested_capital_usd=requested_leverage_capital,
                            approved_capital_usd=feasible_leverage_capital,
                            blocked_capital_usd=withheld_leverage_capital,
                        )
                    # ATTACK is not bounded by robust utility. Portfolio
                    # Compound is the authority that enabled this mode.

                if candidate_mode is CiboTraderLabMode.MEDIUM and multiplier < 1:
                    physical_margin_block = executable_by_margin < 1
                    record_engineering_sensor(
                        "SIZING",
                        epoch_index=epoch_index,
                        signal_fingerprint=candidate.signal_fingerprint,
                        event="MANAGEMENT_INVARIANT_VIOLATION",
                        inputs={
                            "medium_risk_budget_usd": format(
                                medium_risk_budget_usd, "f"
                            ),
                            "one_x_stop_risk_usd": format(
                                candidate.stop_risk_per_multiplier_usd, "f"
                            ),
                            "sovereign_available_usd": format(
                                sovereign_left, "f"
                            ),
                            "margin_left_usd": format(margin_left, "f"),
                        },
                        action="FAIL_CLOSED_NO_SILENT_ENTRY_REJECTION",
                        outputs={
                            "selected_multiplier": 0,
                            "economic_treatment": "INVARIANT_FAILURE",
                        },
                        reaction=(
                            "TRADER_ENTRY_MUST_BE_MANAGED_NOT_DROPPED"
                        ),
                        reasons=(
                            "PHYSICAL_MARGIN_BELOW_1X"
                            if physical_margin_block
                            else "MINIMUM_MANAGEMENT_CAPACITY_BELOW_1X",
                        ),
                    )
                    raise CiboCapitalManagementError(
                        "Trader-executed entry reached CIBO without physical "
                        "capacity for minimum 1x management"
                    )

                with localcontext() as context:
                    context.prec = 100
                    stop_risk = (
                        candidate.stop_risk_per_multiplier_usd
                        * Decimal(multiplier)
                    )
                    margin = (
                        candidate.margin_per_multiplier_usd
                        * Decimal(multiplier)
                    )
                    provider_cost = (
                        candidate.provider_cost_per_multiplier_usd
                        * Decimal(multiplier)
                    )
                    source_reserved = stop_risk + provider_cost
                if (
                    candidate_mode is CiboTraderLabMode.ATTACK
                    and ceiling_discovery_mode
                    and ceiling_attack_drawdown_budget_any_active
                ):
                    if effective_ceiling_attack_drawdown_budget_fraction is None:
                        raise CiboCapitalManagementError(
                            "Trader Lab active ATTACK DD budget missing effective fraction"
                        )
                    with localcontext() as context:
                        context.prec = 100
                        allowed_ceiling_attack_stop_risk_usd = max(
                            Decimal(0),
                            (
                                state.peak_total_capital_usd
                                * effective_ceiling_attack_drawdown_budget_fraction
                            )
                            - total_drawdown_usd
                            - state.open_stop_risk_usd
                            - attack_risk_selected_this_epoch,
                        )
                    if stop_risk > allowed_ceiling_attack_stop_risk_usd:
                        raise CiboCapitalManagementError(
                            "Trader Lab ceiling ATTACK risk-cap invariant failed: "
                            f"selected_stop_risk={format(stop_risk, 'f')} "
                            f"allowed_stop_risk={format(allowed_ceiling_attack_stop_risk_usd, 'f')} "
                            f"peak_total={format(state.peak_total_capital_usd, 'f')} "
                            f"live_total={format(state.total_capital_usd, 'f')} "
                            f"live_drawdown={format(total_drawdown_utilization, 'f')} "
                            f"budget_fraction={format(effective_ceiling_attack_drawdown_budget_fraction, 'f')} "
                            f"selected_multiplier={multiplier} "
                            f"risk_cap={ceiling_drawdown_risk_cap}"
                        )
                capacity_reasons: list[str] = []
                if stop_risk > risk_left:
                    capacity_reasons.append("RISK_CAPACITY_EXHAUSTED")
                if margin > margin_left:
                    capacity_reasons.append("MARGIN_CAPACITY_EXHAUSTED")
                if source_reserved > source_left:
                    capacity_reasons.append("CAPITAL_SOURCE_EXHAUSTED")
                if capacity_reasons:
                    # The position already exists because the Trader executed
                    # it. CIBO may deny only incremental scaling, never custody
                    # of the base position. Any over-budget condition therefore
                    # collapses exposure back to 1x MEDIUM instead of rejecting
                    # the entry.
                    candidate_mode = CiboTraderLabMode.MEDIUM
                    multiplier = 1
                    economic_cap = min(economic_cap, 1)
                    source_left = sovereign_left
                    with localcontext() as context:
                        context.prec = 100
                        stop_risk = candidate.stop_risk_per_multiplier_usd
                        margin = candidate.margin_per_multiplier_usd
                        provider_cost = (
                            candidate.provider_cost_per_multiplier_usd
                        )
                        source_reserved = stop_risk + provider_cost
                    record_engineering_sensor(
                        "SIZING",
                        epoch_index=epoch_index,
                        signal_fingerprint=candidate.signal_fingerprint,
                        event="BASELINE_CUSTODY_OVER_BUDGET",
                        inputs={
                            "risk_left_usd": format(risk_left, "f"),
                            "margin_left_usd": format(margin_left, "f"),
                            "source_left_usd": format(source_left, "f"),
                        },
                        action="KEEP_EXECUTED_ENTRY_AT_1X",
                        outputs={
                            "selected_multiplier": 1,
                            "economic_treatment": "DEFENSIVE_MEDIUM",
                        },
                        reaction=(
                            "DENY_ONLY_INCREMENTAL_SCALING_KEEP_BASE_POSITION"
                        ),
                        reasons=tuple(capacity_reasons),
                    )
                selected.append((candidate, multiplier, candidate_mode))
                if candidate_mode is CiboTraderLabMode.MEDIUM:
                    record_engineering_sensor(
                        "SIZING",
                        epoch_index=epoch_index,
                        signal_fingerprint=candidate.signal_fingerprint,
                        event="SIZING_OUTPUT",
                        inputs={
                            "mode": candidate_mode.value,
                            "per_entry_bank_seed_usd": format(
                                source_left, "f"
                            ),
                            "per_entry_seed_fraction": format(
                                MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO,
                                "f",
                            ),
                        },
                        action="APPROVE_MEDIUM_FROM_4PCT_ENTRY_SEED",
                        outputs={
                            "selected_multiplier": multiplier,
                            "stop_risk_usd": format(stop_risk, "f"),
                            "margin_usd": format(margin, "f"),
                            "source_reserved_usd": format(
                                source_reserved, "f"
                            ),
                        },
                        reaction="PASS_TO_CIBO_COMPOUND",
                        approval=True,
                        requested_capital_usd=(
                            candidate.source_cost_per_multiplier_usd
                        ),
                        approved_capital_usd=(
                            candidate.source_cost_per_multiplier_usd
                        ),
                    )
                risk_left -= stop_risk
                margin_left -= margin
                if candidate_mode is CiboTraderLabMode.MEDIUM:
                    sovereign_left -= source_reserved
                else:
                    cushion_left -= source_reserved
                    portfolio_attack_release_left -= source_reserved
                    attack_risk_selected_this_epoch += stop_risk

        for candidate, multiplier, candidate_mode in selected:
            with localcontext() as context:
                context.prec = 100
                stop_risk = (
                    candidate.stop_risk_per_multiplier_usd
                    * Decimal(multiplier)
                )
                margin = (
                    candidate.margin_per_multiplier_usd
                    * Decimal(multiplier)
                )
                provider_cost = (
                    candidate.provider_cost_per_multiplier_usd
                    * Decimal(multiplier)
                )
                source_reserved = stop_risk + provider_cost
            lifecycle_grade_allowed = (
                candidate_mode is CiboTraderLabMode.ATTACK
                if lifecycle_attack_only
                else (
                    (
                        candidate_mode is CiboTraderLabMode.MEDIUM
                        and multiplier
                        <= lifecycle_defensive_medium_max_multiplier
                    )
                    if lifecycle_defensive_medium_max_multiplier is not None
                    else (
                        not lifecycle_defensive_medium_1x_only
                        or (
                            candidate_mode is CiboTraderLabMode.MEDIUM
                            and multiplier == 1
                        )
                    )
                )
            )
            lifecycle_drawdown_allowed = (
                lifecycle_defense_drawdown_trigger is None
                or total_drawdown_utilization
                >= lifecycle_defense_drawdown_trigger
            )
            lifecycle_trader_streak_allowed = (
                lifecycle_trader_loss_streak_trigger is None
                or trader_loss_streak[candidate.trader_id]
                >= lifecycle_trader_loss_streak_trigger
            )
            lifecycle_bootstrap_capital_allowed = (
                lifecycle_bootstrap_capital_ceiling is None
                or state.total_capital_usd
                <= lifecycle_bootstrap_capital_ceiling
            )
            minimum_stop_risk_fraction = _ratio(
                candidate.stop_risk_per_multiplier_usd,
                max(Decimal("0.00000001"), state.total_capital_usd),
            )
            lifecycle_minimum_stop_risk_fraction_allowed = (
                lifecycle_minimum_stop_risk_fraction_trigger is None
                or minimum_stop_risk_fraction
                >= lifecycle_minimum_stop_risk_fraction_trigger
            )
            projected_open_stop_risk_fraction = _ratio(
                state.open_stop_risk_usd + stop_risk,
                max(Decimal("0.00000001"), state.total_capital_usd),
            )
            lifecycle_projected_open_stop_risk_fraction_allowed = (
                lifecycle_projected_open_stop_risk_fraction_trigger is None
                or projected_open_stop_risk_fraction
                >= lifecycle_projected_open_stop_risk_fraction_trigger
            )
            apply_lifecycle_to_trade = bool(
                lifecycle_map
                and lifecycle_grade_allowed
                and lifecycle_drawdown_allowed
                and lifecycle_trader_streak_allowed
                and lifecycle_bootstrap_capital_allowed
                and lifecycle_minimum_stop_risk_fraction_allowed
                and lifecycle_projected_open_stop_risk_fraction_allowed
            )
            if (
                lifecycle_map
                and lifecycle_grade_allowed
                and not lifecycle_drawdown_allowed
            ):
                lifecycle_drawdown_trigger_blocked_count += 1
            if (
                lifecycle_map
                and lifecycle_grade_allowed
                and lifecycle_drawdown_allowed
                and not lifecycle_trader_streak_allowed
            ):
                lifecycle_trader_loss_streak_blocked_count += 1
            if (
                lifecycle_map
                and lifecycle_grade_allowed
                and lifecycle_drawdown_allowed
                and lifecycle_trader_streak_allowed
                and not lifecycle_bootstrap_capital_allowed
            ):
                lifecycle_bootstrap_capital_blocked_count += 1
            if (
                lifecycle_map
                and lifecycle_grade_allowed
                and lifecycle_drawdown_allowed
                and lifecycle_trader_streak_allowed
                and lifecycle_bootstrap_capital_allowed
                and not lifecycle_minimum_stop_risk_fraction_allowed
            ):
                lifecycle_minimum_stop_risk_fraction_blocked_count += 1
            if (
                lifecycle_map
                and lifecycle_grade_allowed
                and lifecycle_drawdown_allowed
                and lifecycle_trader_streak_allowed
                and lifecycle_bootstrap_capital_allowed
                and lifecycle_minimum_stop_risk_fraction_allowed
                and not lifecycle_projected_open_stop_risk_fraction_allowed
            ):
                lifecycle_projected_open_stop_risk_fraction_blocked_count += 1
            bootstrap_override_allowed = bool(
                lifecycle_bootstrap_override_map
                and candidate_mode is CiboTraderLabMode.MEDIUM
                and multiplier <= lifecycle_bootstrap_override_medium_max_multiplier
                and lifecycle_bootstrap_override_capital_ceiling is not None
                and state.total_capital_usd
                <= lifecycle_bootstrap_override_capital_ceiling
                and (
                    lifecycle_bootstrap_override_peak_capital_ceiling is None
                    or state.peak_total_capital_usd
                    <= lifecycle_bootstrap_override_peak_capital_ceiling
                )
                and lifecycle_bootstrap_override_drawdown_trigger is not None
                and total_drawdown_utilization
                >= lifecycle_bootstrap_override_drawdown_trigger
                and lifecycle_bootstrap_override_trader_loss_streak_trigger
                is not None
                and trader_loss_streak[candidate.trader_id]
                >= lifecycle_bootstrap_override_trader_loss_streak_trigger
                and (
                    not lifecycle_bootstrap_override_require_expectation
                    or candidate.walk_forward_expected_structural_r is not None
                )
                and (
                    lifecycle_bootstrap_override_expected_r_ceiling is None
                    or (
                        candidate.walk_forward_expected_structural_r is not None
                        and candidate.walk_forward_expected_structural_r
                        <= lifecycle_bootstrap_override_expected_r_ceiling
                    )
                )
            )
            lifecycle_attack_override_projected_risk_allowed = (
                lifecycle_attack_override_projected_open_stop_risk_fraction_trigger
                is None
                or projected_open_stop_risk_fraction
                >= lifecycle_attack_override_projected_open_stop_risk_fraction_trigger
            )
            lifecycle_attack_override_allowed = bool(
                lifecycle_attack_override_map
                and candidate_mode is CiboTraderLabMode.ATTACK
                and lifecycle_attack_override_projected_risk_allowed
            )
            if (
                lifecycle_attack_override_map
                and candidate_mode is CiboTraderLabMode.ATTACK
                and not lifecycle_attack_override_projected_risk_allowed
            ):
                lifecycle_attack_override_projected_risk_blocked_count += 1

            if bootstrap_override_allowed:
                lifecycle_events_for_trade = tuple(
                    lifecycle_bootstrap_override_map[
                        candidate.signal_fingerprint
                    ]["events"]
                )
                lifecycle_bootstrap_override_applied_count += 1
            elif lifecycle_attack_override_allowed:
                lifecycle_events_for_trade = tuple(
                    lifecycle_attack_override_map[
                        candidate.signal_fingerprint
                    ]["events"]
                )
                lifecycle_attack_override_applied_count += 1
            else:
                lifecycle_events_for_trade = (
                    tuple(
                        lifecycle_map[candidate.signal_fingerprint][
                            "events"
                        ]
                    )
                    if apply_lifecycle_to_trade
                    else ()
                )
            if lifecycle_events_for_trade:
                lifecycle_applied_trade_count += 1

            trade = CiboThreeModeOpenTrade(
                signal_fingerprint=candidate.signal_fingerprint,
                trader_id=candidate.trader_id,
                mode=candidate_mode,
                multiplier=multiplier,
                exit_at=candidate.exit_at,
                gross_r=candidate.gross_r,
                stop_risk_usd=stop_risk,
                margin_usd=margin,
                provider_cost_usd=provider_cost,
                source_reserved_usd=source_reserved,
                bank_seed_usd=(
                    min(
                        dynamic_bank_seed_budget_usd(
                            state.total_capital_usd
                        ),
                        source_reserved,
                    )
                    if candidate_mode is CiboTraderLabMode.MEDIUM
                    else Decimal(0)
                ),
                lifecycle_events=lifecycle_events_for_trade,
            )
            pending.append(trade)
            if compact_trade_receipts:
                trade_receipts.append(
                    {
                        "signal_fingerprint": candidate.signal_fingerprint,
                        "trader_id": candidate.trader_id,
                        "decision_at": candidate.decision_at.isoformat(),
                        "exit_at": candidate.exit_at.isoformat(),
                        "mode": candidate_mode.value,
                        "multiplier": multiplier,
                        "gross_structural_outcome_r_postdecision": format(
                            candidate.gross_r,
                            "f",
                        ),
                        "stop_risk_usd": format(stop_risk, "f"),
                        "provider_cost_usd": format(provider_cost, "f"),
                    }
                )
                trade_receipt_by_signal[
                    candidate.signal_fingerprint
                ] = trade_receipts[-1]
            else:
                trade_receipts.append(
                    {
                        "signal_fingerprint": candidate.signal_fingerprint,
                        "trader_id": candidate.trader_id,
                        "decision_at": candidate.decision_at.isoformat(),
                        "exit_at": candidate.exit_at.isoformat(),
                        "mode": candidate_mode.value,
                        "multiplier": multiplier,
                        "expected_edge_after_cost_usd": format(
                            candidate.expected_edge_after_cost_usd,
                            "f",
                        ),
                        "expected_net_utility_usd": format(
                            candidate.expected_net_utility_usd,
                            "f",
                        ),
                        "attack_expected_net_utility_usd": format(
                            candidate.attack_expected_net_utility_usd,
                            "f",
                        ),
                        "walk_forward_expected_structural_r": (
                            None
                            if candidate.walk_forward_expected_structural_r is None
                            else format(candidate.walk_forward_expected_structural_r, "f")
                        ),
                        "walk_forward_block_dispersion_r": format(
                            candidate.walk_forward_block_dispersion_r, "f"
                        ),
                        "native_confidence_band": native_confidence(candidate),
                        "walk_forward_positive_block_count": (
                            candidate.walk_forward_positive_block_count
                        ),
                        "walk_forward_nonpositive_block_count": (
                            candidate.walk_forward_nonpositive_block_count
                        ),
                        "native_cognition_recommended": (
                            candidate.native_cognition_recommended
                        ),
                        "context_quality_disposition": (
                            candidate.context_quality_disposition
                        ),
                        "capital_time_score": format(
                            candidate.capital_time_score,
                            "f",
                        ),
                        "robust_economic_multiplier_cap": economic_cap,
                        "selected_robust_utility_usd": format(
                            robust_capital_utility(
                                candidate,
                                multiplier=multiplier,
                                capital_base_usd=(
                                    state.sovereign_available_usd
                                    if candidate_mode is CiboTraderLabMode.MEDIUM
                                    else state.cushion_available_usd
                                ),
                                expected_net_utility_usd=(
                                    candidate.attack_expected_net_utility_usd
                                    if candidate_mode is CiboTraderLabMode.ATTACK
                                    else candidate.expected_edge_after_cost_usd
                                ),
                            ),
                            "f",
                        ),
                        "gross_structural_outcome_r_postdecision": format(
                            candidate.gross_r,
                            "f",
                        ),
                        "stop_risk_usd": format(stop_risk, "f"),
                        "provider_cost_usd": format(provider_cost, "f"),
                        "source_reserved_usd": format(source_reserved, "f"),
                        "bank_seed_usd": format(
                            trade.bank_seed_usd or Decimal(0), "f"
                        ),
                        "mode_reasons": list(mode_reasons),
                    }
                )
                trade_receipt_by_signal[
                    candidate.signal_fingerprint
                ] = trade_receipts[-1]
            # Economic state must be identical in FULL and SUMMARY telemetry.
            # Receipt verbosity is observational only and can never change
            # risk/margin accounting.
            state.open_stop_risk_usd += stop_risk
            state.open_margin_usd += margin
            if candidate_mode is CiboTraderLabMode.MEDIUM:
                medium_seed = trade.bank_seed_usd or Decimal(0)
                state.sovereign_reserved_usd += source_reserved
                state.bank_seed_reserved_usd += medium_seed
                state.bank_seed_issuance_count += 1
                state.bank_seed_issued_total_usd += medium_seed
            else:
                state.cushion_reserved_usd += source_reserved
                state.portfolio_attack_credit_usd = max(
                    Decimal(0),
                    state.portfolio_attack_credit_usd - source_reserved,
                )
            trade_mode_counts[candidate_mode.value] += 1
            leverage_sum += multiplier
            leverage_max = max(leverage_max, multiplier)

        if collect_epoch_receipts:
            epoch_receipts.append(
                {
                    "epoch_index": epoch_index,
                    "decision_at": decision_at.isoformat(),
                    "mode": mode.value,
                    "mode_reasons": list(mode_reasons),
                    "opportunity_count": len(candidates),
                    "eligible_count": len(eligible),
                    "selected_count": len(selected),
                    "selected_multiplier_total": sum(
                        multiplier
                        for _candidate, multiplier, _mode in selected
                    ),
                    "sovereign_bank_usd": format(
                        state.sovereign_bank_usd,
                        "f",
                    ),
                    "sovereign_protection_floor_usd": format(
                        state.sovereign_protection_floor_usd,
                        "f",
                    ),
                    "sovereign_risk_budget_available_usd": format(
                        state.sovereign_risk_budget_available_usd,
                        "f",
                    ),
                    "per_entry_bank_seed_fraction": format(
                        MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO, "f"
                    ),
                    "per_entry_bank_seed_budget_usd": format(
                        dynamic_bank_seed_budget_usd(state.total_capital_usd),
                        "f",
                    ),
                    "bank_seed_reserved_usd": format(
                        state.bank_seed_reserved_usd, "f"
                    ),
                    "portfolio_cushion_usd": format(
                        state.portfolio_cushion_usd,
                        "f",
                    ),
                    "portfolio_attack_credit_usd": format(
                        state.portfolio_attack_credit_usd, "f"
                    ),
                    "open_stop_risk_usd": format(
                        state.open_stop_risk_usd,
                        "f",
                    ),
                    "risk_utilization": format(risk_utilization, "f"),
                    "drawdown_utilization": format(
                        drawdown_utilization,
                        "f",
                    ),
                }
            )
            state.mark()

    settle_due(None)
    if current_drawdown_episode:
        peak_at_raw = current_drawdown_episode.get("peak_at")
        last_at_raw = current_drawdown_episode.pop("_last_at", None)
        underwater_seconds = None
        if isinstance(peak_at_raw, str) and isinstance(last_at_raw, str):
            underwater_seconds = max(
                0,
                int(
                    (
                        datetime.fromisoformat(last_at_raw)
                        - datetime.fromisoformat(peak_at_raw)
                    ).total_seconds()
                ),
            )
        current_drawdown_episode["underwater_duration_seconds"] = (
            underwater_seconds
        )
        drawdown_episodes.append(current_drawdown_episode)
        current_drawdown_episode = {}

    drawdown_atlas_top_10 = sorted(
        drawdown_episodes,
        key=lambda item: Decimal(str(item.get("drawdown_fraction", "0"))),
        reverse=True,
    )[:10]
    for rank, episode in enumerate(drawdown_atlas_top_10, start=1):
        episode["rank"] = rank

    if any(
        "realized_net_r" not in receipt
        or "realized_net_pnl_usd" not in receipt
        for receipt in trade_receipts
    ):
        raise CiboCapitalManagementError(
            "Trader Lab ended with incomplete realized trade receipts"
        )
    position_lifecycle_report["applied_trade_count"] = (
        lifecycle_applied_trade_count
    )
    position_lifecycle_report["bootstrap_override_enabled"] = bool(
        lifecycle_bootstrap_override_map
    )
    position_lifecycle_report["bootstrap_override_applied_count"] = (
        lifecycle_bootstrap_override_applied_count
    )
    position_lifecycle_report["bootstrap_override_capital_ceiling_usd"] = (
        None
        if lifecycle_bootstrap_override_capital_ceiling is None
        else format(lifecycle_bootstrap_override_capital_ceiling, "f")
    )
    position_lifecycle_report["bootstrap_override_peak_capital_ceiling_usd"] = (
        None
        if lifecycle_bootstrap_override_peak_capital_ceiling is None
        else format(lifecycle_bootstrap_override_peak_capital_ceiling, "f")
    )
    position_lifecycle_report["bootstrap_override_drawdown_trigger"] = (
        None
        if lifecycle_bootstrap_override_drawdown_trigger is None
        else format(lifecycle_bootstrap_override_drawdown_trigger, "f")
    )
    position_lifecycle_report["bootstrap_override_trader_loss_streak_trigger"] = (
        lifecycle_bootstrap_override_trader_loss_streak_trigger
    )
    position_lifecycle_report["bootstrap_override_medium_max_multiplier"] = (
        lifecycle_bootstrap_override_medium_max_multiplier
    )
    position_lifecycle_report["bootstrap_override_require_expectation"] = (
        lifecycle_bootstrap_override_require_expectation
    )
    position_lifecycle_report["bootstrap_override_expected_r_ceiling"] = (
        None
        if lifecycle_bootstrap_override_expected_r_ceiling is None
        else format(lifecycle_bootstrap_override_expected_r_ceiling, "f")
    )
    position_lifecycle_report["attack_override_enabled"] = bool(
        lifecycle_attack_override_map
    )
    position_lifecycle_report["attack_override_applied_count"] = (
        lifecycle_attack_override_applied_count
    )
    position_lifecycle_report[
        "attack_override_projected_open_stop_risk_fraction_trigger"
    ] = (
        None
        if lifecycle_attack_override_projected_open_stop_risk_fraction_trigger
        is None
        else format(
            lifecycle_attack_override_projected_open_stop_risk_fraction_trigger,
            "f",
        )
    )
    position_lifecycle_report[
        "attack_override_projected_risk_blocked_count"
    ] = lifecycle_attack_override_projected_risk_blocked_count
    position_lifecycle_report["defensive_medium_1x_only"] = (
        lifecycle_defensive_medium_1x_only
    )
    position_lifecycle_report["attack_only"] = lifecycle_attack_only
    position_lifecycle_report["defensive_medium_max_multiplier"] = (
        lifecycle_defensive_medium_max_multiplier
    )
    position_lifecycle_report["drawdown_trigger"] = (
        None
        if lifecycle_defense_drawdown_trigger is None
        else format(lifecycle_defense_drawdown_trigger, "f")
    )
    position_lifecycle_report["drawdown_trigger_blocked_count"] = (
        lifecycle_drawdown_trigger_blocked_count
    )
    position_lifecycle_report["trader_loss_streak_trigger"] = (
        lifecycle_trader_loss_streak_trigger
    )
    position_lifecycle_report["trader_loss_streak_blocked_count"] = (
        lifecycle_trader_loss_streak_blocked_count
    )
    position_lifecycle_report["ending_trader_loss_streaks"] = {
        key: int(value)
        for key, value in sorted(trader_loss_streak.items())
    }
    position_lifecycle_report["bootstrap_capital_ceiling_usd"] = (
        None
        if lifecycle_bootstrap_capital_ceiling is None
        else format(lifecycle_bootstrap_capital_ceiling, "f")
    )
    position_lifecycle_report["bootstrap_capital_blocked_count"] = (
        lifecycle_bootstrap_capital_blocked_count
    )
    position_lifecycle_report["minimum_stop_risk_fraction_trigger"] = (
        None
        if lifecycle_minimum_stop_risk_fraction_trigger is None
        else format(lifecycle_minimum_stop_risk_fraction_trigger, "f")
    )
    position_lifecycle_report[
        "minimum_stop_risk_fraction_blocked_count"
    ] = lifecycle_minimum_stop_risk_fraction_blocked_count
    position_lifecycle_report[
        "projected_open_stop_risk_fraction_trigger"
    ] = (
        None
        if lifecycle_projected_open_stop_risk_fraction_trigger is None
        else format(
            lifecycle_projected_open_stop_risk_fraction_trigger, "f"
        )
    )
    position_lifecycle_report[
        "projected_open_stop_risk_fraction_blocked_count"
    ] = lifecycle_projected_open_stop_risk_fraction_blocked_count
    if pending:
        raise CiboCapitalManagementError(
            "Trader Lab three-mode ended with unsettled trades"
        )

    trade_count = sum(trade_mode_counts.values())
    average_leverage = (
        Decimal(leverage_sum) / Decimal(trade_count)
        if trade_count
        else Decimal(0)
    )
    max_drawdown_pct = state.max_drawdown_fraction_observed
    baseline_delta = None
    if baseline_ending_capital_usd is not None:
        baseline_delta = (
            state.total_capital_usd - baseline_ending_capital_usd
        )

    engineering_function_reports: dict[str, dict[str, object]] = {}
    for function_name in economic_functions:
        stats = sensor_stats[function_name]
        reason_counts = stats["reason_counts"]
        action_counts = stats["action_counts"]
        if not isinstance(reason_counts, Counter) or not isinstance(
            action_counts, Counter
        ):
            raise CiboCapitalManagementError(
                "engineering sensor report counter corruption"
            )
        engineering_function_reports[function_name] = {
            "call_count": stats["call_count"],
            "approval_count": stats["approval_count"],
            "rejection_count": stats["rejection_count"],
            "restriction_count": stats["restriction_count"],
            "requested_capital_usd": format(
                stats["requested_capital_usd"], "f"
            ),
            "approved_capital_usd": format(
                stats["approved_capital_usd"], "f"
            ),
            "blocked_capital_usd": format(
                stats["blocked_capital_usd"], "f"
            ),
            "capital_created_usd": format(
                stats["capital_created_usd"], "f"
            ),
            "capital_destroyed_usd": format(
                stats["capital_destroyed_usd"], "f"
            ),
            "reason_counts": dict(sorted(reason_counts.items())),
            "action_counts": dict(sorted(action_counts.items())),
        }

    bottleneck_ranking = sorted(
        (
            {
                "function": function_name,
                "capital_pressure_usd": format(
                    sensor_stats[function_name]["blocked_capital_usd"]
                    + sensor_stats[function_name]["capital_destroyed_usd"],
                    "f",
                ),
                "blocked_capital_usd": format(
                    sensor_stats[function_name]["blocked_capital_usd"],
                    "f",
                ),
                "capital_destroyed_usd": format(
                    sensor_stats[function_name]["capital_destroyed_usd"],
                    "f",
                ),
                "rejection_count": sensor_stats[function_name][
                    "rejection_count"
                ],
                "restriction_count": sensor_stats[function_name][
                    "restriction_count"
                ],
            }
            for function_name in economic_functions
        ),
        key=lambda item: (
            -Decimal(str(item["capital_pressure_usd"])),
            -int(item["rejection_count"]),
            -int(item["restriction_count"]),
            str(item["function"]),
        ),
    )

    economic_admitted_count = upstream_intake_admitted_count
    sizing_call_count = int(sensor_stats["SIZING"]["call_count"])
    sizing_rejection_count = int(sensor_stats["SIZING"]["rejection_count"])
    sizing_approval_count = int(sensor_stats["SIZING"]["approval_count"])
    sizing_deferred_count = int(sensor_stats["SIZING"]["restriction_count"])
    leverage_call_count = int(
        sensor_stats["ADAPTIVE_LEVERAGE"]["call_count"]
    )
    leverage_rejection_count = int(
        sensor_stats["ADAPTIVE_LEVERAGE"]["rejection_count"]
    )
    leverage_approval_count = int(
        sensor_stats["ADAPTIVE_LEVERAGE"]["approval_count"]
    )
    portfolio_withheld_before_execution = max(
        0,
        economic_admitted_count - sizing_call_count - leverage_call_count,
    )
    execution_funnel = {
        "opportunity_decision_count": len(rows),
        "upstream_filtered_before_economy_count": (
            upstream_intake_filtered_count
        ),
        "economic_surface_admitted_count": economic_admitted_count,
        "compound_portfolio_withheld_before_execution_engine_count": (
            portfolio_withheld_before_execution
        ),
        "sizing_medium_evaluated_count": sizing_call_count,
        "sizing_medium_rejected_count": sizing_rejection_count,
        "sizing_medium_deferred_count": sizing_deferred_count,
        "sizing_medium_approved_count": sizing_approval_count,
        "adaptive_leverage_attack_evaluated_count": leverage_call_count,
        "adaptive_leverage_attack_rejected_count": (
            leverage_rejection_count
        ),
        "adaptive_leverage_attack_approved_count": leverage_approval_count,
        "final_trade_count": trade_count,
        "causal_conservation_check": (
            upstream_intake_filtered_count
            + portfolio_withheld_before_execution
            + sizing_rejection_count
            + sizing_deferred_count
            + sizing_approval_count
            + leverage_rejection_count
            + leverage_approval_count
            == len(rows)
        ),
    }

    engineering_sensor_report = {
        "schema": "qore.trader_lab.cibo_economic_engineering_sensors.v1",
        "trace_event_count": sensor_event_sequence,
        "trace_materialized_count": len(engineering_trace),
        "opportunity_decision_count": len(rows),
        "decision_epoch_count": len(epochs),
        "execution_funnel": execution_funnel,
        "upstream_economic_intake": {
            "admitted_count": upstream_intake_admitted_count,
            "filtered_before_economic_surface_count": (
                upstream_intake_filtered_count
            ),
            "reason_counts": dict(
                sorted(upstream_intake_reason_counts.items())
            ),
        },
        "functions": engineering_function_reports,
        "bottleneck_ranking": bottleneck_ranking,
        "interpretation_rule": (
            "blocked_capital measures capital requested but not released by "
            "that function; capital_destroyed measures realized post-exit "
            "losses at CIBO_COMPOUND. Upstream intake is reported separately "
            "and is not falsely attributed to any economic function."
        ),
    }

    return {
        "schema": "qore.trader_lab.cibo_three_mode_ceiling.v1",
        "research_lane": (
            "HISTORICAL_PRIOR_NATIVE_COORDINATED_ECONOMIC_GROUP"
            if use_historical_prior and coordinated_economic_group and not lifecycle_map
            else "HISTORICAL_PRIOR_NATIVE_LIFECYCLE_DISTRIBUTED_ATTACK_FRONTIER"
            if use_historical_prior and lifecycle_map and distributed_attack_frontier
            else "HISTORICAL_PRIOR_NATIVE_LIFECYCLE_CUSTODY"
            if use_historical_prior and lifecycle_map
            else "HISTORICAL_PRIOR_NATIVE_DISTRIBUTED_ATTACK_FRONTIER"
            if use_historical_prior and distributed_attack_frontier
            else "HISTORICAL_PRIOR_NATIVE_SOFT_DRAWDOWN_ALLOCATOR"
            if use_historical_prior and soft_medium_drawdown_allocator
            else "HISTORICAL_PRIOR_NATIVE_DD_RESERVE_FRONTIER"
            if (
                use_historical_prior
                and medium_pretrade_drawdown_ceiling
                != ECONOMIC_DRAWDOWN_CEILING
            )
            else "HISTORICAL_PRIOR_NATIVE_TRANSFER"
            if use_historical_prior
            else "POST_BURN_CONTEXT_ABSTAIN_HYPOTHESIS"
            if enforce_research_context_abstain
            else "CAUSAL_BASELINE_THREE_MODE"
        ),
        "source_manifest_sha256": source_sha,
        "decision_count": len(rows),
        "decision_epoch_count": len(epochs),
        "initial_capital_usd": format(INITIAL_CAPITAL_USD, "f"),
        "ending_total_capital_usd": format(
            state.total_capital_usd,
            "f",
        ),
        "ending_sovereign_bank_usd": format(
            state.sovereign_bank_usd,
            "f",
        ),
        "ending_portfolio_cushion_usd": format(
            state.portfolio_cushion_usd,
            "f",
        ),
        "peak_total_capital_usd": format(
            state.peak_total_capital_usd,
            "f",
        ),
        "max_drawdown_usd": format(state.max_drawdown_usd, "f"),
        "max_drawdown_fraction": format(max_drawdown_pct, "f"),
        "minimum_sovereign_bank_usd": format(
            state.min_sovereign_bank_usd,
            "f",
        ),
        "peak_sovereign_bank_usd": format(
            state.peak_sovereign_bank_usd,
            "f",
        ),
        "max_sovereign_drawdown_usd": format(
            state.max_sovereign_drawdown_usd,
            "f",
        ),
        "sovereign_protection_floor_usd": format(
            state.sovereign_protection_floor_usd,
            "f",
        ),
        "sovereign_floor_breach_usd": format(
            state.sovereign_floor_breach_usd,
            "f",
        ),
        "portfolio_cushion_high_watermark_usd": format(
            state.cushion_high_watermark_usd,
            "f",
        ),
        "attack_sovereign_breach_usd": format(
            state.attack_sovereign_breach_usd,
            "f",
        ),
        "medium_profit_to_sovereign_usd": format(
            state.medium_profit_to_sovereign_usd,
            "f",
        ),
        "medium_profit_to_portfolio_cushion_usd": format(
            state.medium_profit_to_cushion_usd,
            "f",
        ),
        "per_entry_bank_seed_fraction": format(
            MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO, "f"
        ),
        "bank_seed_issuance_count": state.bank_seed_issuance_count,
        "bank_seed_issued_total_usd": format(
            state.bank_seed_issued_total_usd, "f"
        ),
        "bank_seed_recycled_total_usd": format(
            state.bank_seed_recycled_total_usd, "f"
        ),
        "bank_seed_reserved_usd": format(
            state.bank_seed_reserved_usd, "f"
        ),
        "medium_compound_positive_net_usd": format(
            state.medium_compound_positive_net_usd, "f"
        ),
        "medium_compound_negative_net_usd": format(
            state.medium_compound_negative_net_usd, "f"
        ),
        "medium_compound_turnover_usd": format(
            state.medium_compound_turnover_usd, "f"
        ),
        "medium_compound_recovery_deficit_usd": format(
            state.medium_compound_recovery_deficit_usd, "f"
        ),
        "medium_compound_recovered_usd": format(
            state.medium_compound_recovered_usd, "f"
        ),
        "portfolio_attack_credit_usd": format(
            state.portfolio_attack_credit_usd, "f"
        ),
        "portfolio_attack_credit_recycled_total_usd": format(
            state.portfolio_attack_credit_recycled_total_usd, "f"
        ),
        "attack_net_pnl_usd": format(
            state.attack_net_pnl_usd,
            "f",
        ),
        "mode_epoch_counts": dict(sorted(mode_counts.items())),
        "mode_reason_counts": dict(sorted(mode_reason_counts.items())),
        "trade_mode_counts": dict(sorted(trade_mode_counts.items())),
        "trade_count": trade_count,
        "average_selected_multiplier": format(
            average_leverage,
            "f",
        ),
        "maximum_selected_multiplier": leverage_max,
        "attack_trade_count": trade_mode_counts["ATTACK"],
        "attack_density_fraction": format(
            (
                Decimal(trade_mode_counts["ATTACK"]) / Decimal(trade_count)
                if trade_count
                else Decimal(0)
            ),
            "f",
        ),
        "attack_epoch_count_with_funded_cushion": attack_epochs_funded,
        "engineering_sensor_report": engineering_sensor_report,
        "max_drawdown_attribution": max_drawdown_attribution,
        "drawdown_forensics": {
            "episode_count": len(drawdown_episodes),
            "top_10_episodes": drawdown_atlas_top_10,
            "frozen_control_snapshot": {
                "attack_multiplier_cap": attack_multiplier_cap,
                "medium_multiplier_cap": medium_multiplier_cap,
                "ceiling_growth_leverage_slope": (
                    None
                    if ceiling_growth_leverage_slope is None
                    else format(ceiling_growth_leverage_slope, "f")
                ),
                "ceiling_attack_compound_hysteresis_fraction": (
                    None
                    if ceiling_attack_compound_hysteresis_fraction is None
                    else format(
                        ceiling_attack_compound_hysteresis_fraction, "f"
                    )
                ),
                "attack_compound_hysteresis_hold_count": (
                    attack_compound_hysteresis_hold_count
                ),
                "attack_compound_hysteresis_raise_count": (
                    attack_compound_hysteresis_raise_count
                ),
                "attack_compound_hysteresis_drop_count": (
                    attack_compound_hysteresis_drop_count
                ),
                "ceiling_attack_single_trade_risk_fraction": (
                    None
                    if ceiling_attack_single_trade_risk_fraction is None
                    else format(
                        ceiling_attack_single_trade_risk_fraction, "f"
                    )
                ),
                "ceiling_attack_loss_streak_trigger": (
                    ceiling_attack_loss_streak_trigger
                ),
                "ceiling_attack_loss_streak_taper_fraction": format(
                    ceiling_attack_loss_streak_taper_fraction, "f"
                ),
                "ceiling_portfolio_shock_trigger_fraction": (
                    None
                    if ceiling_portfolio_shock_trigger_fraction is None
                    else format(
                        ceiling_portfolio_shock_trigger_fraction, "f"
                    )
                ),
                "ceiling_portfolio_shock_taper_fraction": format(
                    ceiling_portfolio_shock_taper_fraction, "f"
                ),
                "ceiling_portfolio_shock_one_shot": (
                    ceiling_portfolio_shock_one_shot
                ),
                "medium_drawdown_intensity_trigger": (
                    None
                    if medium_drawdown_intensity_trigger is None
                    else format(medium_drawdown_intensity_trigger, "f")
                ),
                "ceiling_attack_stress_confidence_drawdown_trigger": (
                    None
                    if ceiling_attack_stress_confidence_drawdown_trigger is None
                    else format(
                        ceiling_attack_stress_confidence_drawdown_trigger, "f"
                    )
                ),
                "ceiling_attack_stress_confidence_ratio_ceiling": (
                    None
                    if ceiling_attack_stress_confidence_ratio_ceiling is None
                    else format(
                        ceiling_attack_stress_confidence_ratio_ceiling, "f"
                    )
                ),
                "ceiling_attack_stress_confidence_taper_fraction": format(
                    ceiling_attack_stress_confidence_taper_fraction, "f"
                ),
                "attack_stress_confidence_taper_bind_count": (
                    attack_stress_confidence_taper_bind_count
                ),
            },
        },
        "economic_group_report": {
            "enabled": coordinated_economic_group,
            "bootstrap_cushion_share": format(
                economic_group_bootstrap_cushion_share, "f"
            ),
            "ablation": economic_group_ablation,
            "ceiling_discovery_mode": ceiling_discovery_mode,
            "ceiling_attack_compound_hysteresis_fraction": (
                None
                if ceiling_attack_compound_hysteresis_fraction is None
                else format(ceiling_attack_compound_hysteresis_fraction, "f")
            ),
            "ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction": (
                None
                if ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction is None
                else format(
                    ceiling_attack_stress_confidence_reinvestment_hysteresis_fraction,
                    "f",
                )
            ),
            "attack_stress_confidence_reinvestment_arm_count": (
                attack_stress_confidence_reinvestment_arm_count
            ),
            "attack_stress_confidence_reinvestment_hold_count": (
                attack_stress_confidence_reinvestment_hold_count
            ),
            "attack_stress_confidence_reinvestment_release_count": (
                attack_stress_confidence_reinvestment_release_count
            ),
            "attack_stress_confidence_reinvestment_drop_count": (
                attack_stress_confidence_reinvestment_drop_count
            ),
            "attack_compound_hysteresis_hold_count": (
                attack_compound_hysteresis_hold_count
            ),
            "attack_compound_hysteresis_raise_count": (
                attack_compound_hysteresis_raise_count
            ),
            "attack_compound_hysteresis_drop_count": (
                attack_compound_hysteresis_drop_count
            ),
            "ceiling_attack_single_trade_risk_fraction": (
                None
                if ceiling_attack_single_trade_risk_fraction is None
                else format(ceiling_attack_single_trade_risk_fraction, "f")
            ),
            "ceiling_attack_loss_streak_trigger": (
                ceiling_attack_loss_streak_trigger
            ),
            "ceiling_attack_loss_streak_taper_fraction": format(
                ceiling_attack_loss_streak_taper_fraction, "f"
            ),
            "attack_loss_streak_taper_bind_count": (
                attack_loss_streak_taper_bind_count
            ),
            "ceiling_attack_drawdown_taper_trigger": (
                None
                if ceiling_attack_drawdown_taper_trigger is None
                else format(ceiling_attack_drawdown_taper_trigger, "f")
            ),
            "ceiling_attack_drawdown_taper_fraction": format(
                ceiling_attack_drawdown_taper_fraction, "f"
            ),
            "attack_drawdown_taper_bind_count": (
                attack_drawdown_taper_bind_count
            ),
            "ceiling_attack_multiplier_band_lower": (
                ceiling_attack_multiplier_band_lower
            ),
            "ceiling_attack_multiplier_band_upper": (
                ceiling_attack_multiplier_band_upper
            ),
            "ceiling_attack_multiplier_band_taper_fraction": format(
                ceiling_attack_multiplier_band_taper_fraction, "f"
            ),
            "attack_multiplier_band_taper_bind_count": (
                attack_multiplier_band_taper_bind_count
            ),
            "ceiling_attack_risk_fraction_band_lower": (
                None
                if ceiling_attack_risk_fraction_band_lower is None
                else format(ceiling_attack_risk_fraction_band_lower, "f")
            ),
            "ceiling_attack_risk_fraction_band_upper": (
                None
                if ceiling_attack_risk_fraction_band_upper is None
                else format(ceiling_attack_risk_fraction_band_upper, "f")
            ),
            "ceiling_attack_risk_fraction_band_taper_fraction": format(
                ceiling_attack_risk_fraction_band_taper_fraction, "f"
            ),
            "attack_risk_fraction_band_taper_bind_count": (
                attack_risk_fraction_band_taper_bind_count
            ),
            "ceiling_attack_drawdown_window_lower": (
                None
                if ceiling_attack_drawdown_window_lower is None
                else format(ceiling_attack_drawdown_window_lower, "f")
            ),
            "ceiling_attack_drawdown_window_upper": (
                None
                if ceiling_attack_drawdown_window_upper is None
                else format(ceiling_attack_drawdown_window_upper, "f")
            ),
            "ceiling_attack_drawdown_window_multiplier_lower": (
                ceiling_attack_drawdown_window_multiplier_lower
            ),
            "ceiling_attack_drawdown_window_multiplier_upper": (
                ceiling_attack_drawdown_window_multiplier_upper
            ),
            "ceiling_attack_drawdown_window_taper_fraction": format(
                ceiling_attack_drawdown_window_taper_fraction, "f"
            ),
            "attack_drawdown_window_taper_bind_count": (
                attack_drawdown_window_taper_bind_count
            ),
            "ceiling_attack_drawdown_window2_lower": (
                None
                if ceiling_attack_drawdown_window2_lower is None
                else format(ceiling_attack_drawdown_window2_lower, "f")
            ),
            "ceiling_attack_drawdown_window2_upper": (
                None
                if ceiling_attack_drawdown_window2_upper is None
                else format(ceiling_attack_drawdown_window2_upper, "f")
            ),
            "ceiling_attack_drawdown_window2_multiplier_lower": (
                ceiling_attack_drawdown_window2_multiplier_lower
            ),
            "ceiling_attack_drawdown_window2_multiplier_upper": (
                ceiling_attack_drawdown_window2_multiplier_upper
            ),
            "ceiling_attack_drawdown_window2_taper_fraction": format(
                ceiling_attack_drawdown_window2_taper_fraction, "f"
            ),
            "attack_drawdown_window2_taper_bind_count": (
                attack_drawdown_window2_taper_bind_count
            ),
            "ceiling_attack_drawdown_window3_lower": (
                None
                if ceiling_attack_drawdown_window3_lower is None
                else format(ceiling_attack_drawdown_window3_lower, "f")
            ),
            "ceiling_attack_drawdown_window3_upper": (
                None
                if ceiling_attack_drawdown_window3_upper is None
                else format(ceiling_attack_drawdown_window3_upper, "f")
            ),
            "ceiling_attack_drawdown_window3_multiplier_lower": (
                ceiling_attack_drawdown_window3_multiplier_lower
            ),
            "ceiling_attack_drawdown_window3_multiplier_upper": (
                ceiling_attack_drawdown_window3_multiplier_upper
            ),
            "ceiling_attack_drawdown_window3_taper_fraction": format(
                ceiling_attack_drawdown_window3_taper_fraction, "f"
            ),
            "attack_drawdown_window3_taper_bind_count": (
                attack_drawdown_window3_taper_bind_count
            ),
            "ceiling_attack_drawdown_window4_lower": (
                None
                if ceiling_attack_drawdown_window4_lower is None
                else format(ceiling_attack_drawdown_window4_lower, "f")
            ),
            "ceiling_attack_drawdown_window4_upper": (
                None
                if ceiling_attack_drawdown_window4_upper is None
                else format(ceiling_attack_drawdown_window4_upper, "f")
            ),
            "ceiling_attack_drawdown_window4_multiplier_lower": (
                ceiling_attack_drawdown_window4_multiplier_lower
            ),
            "ceiling_attack_drawdown_window4_multiplier_upper": (
                ceiling_attack_drawdown_window4_multiplier_upper
            ),
            "ceiling_attack_drawdown_window4_taper_fraction": format(
                ceiling_attack_drawdown_window4_taper_fraction, "f"
            ),
            "attack_drawdown_window4_taper_bind_count": (
                attack_drawdown_window4_taper_bind_count
            ),
            "ceiling_attack_drawdown_window5_lower": (
                None
                if ceiling_attack_drawdown_window5_lower is None
                else format(ceiling_attack_drawdown_window5_lower, "f")
            ),
            "ceiling_attack_drawdown_window5_upper": (
                None
                if ceiling_attack_drawdown_window5_upper is None
                else format(ceiling_attack_drawdown_window5_upper, "f")
            ),
            "ceiling_attack_drawdown_window5_multiplier_lower": (
                ceiling_attack_drawdown_window5_multiplier_lower
            ),
            "ceiling_attack_drawdown_window5_multiplier_upper": (
                ceiling_attack_drawdown_window5_multiplier_upper
            ),
            "ceiling_attack_drawdown_window5_taper_fraction": format(
                ceiling_attack_drawdown_window5_taper_fraction, "f"
            ),
            "attack_drawdown_window5_taper_bind_count": (
                attack_drawdown_window5_taper_bind_count
            ),
            "ceiling_attack_drawdown_window6_lower": (
                None
                if ceiling_attack_drawdown_window6_lower is None
                else format(ceiling_attack_drawdown_window6_lower, "f")
            ),
            "ceiling_attack_drawdown_window6_upper": (
                None
                if ceiling_attack_drawdown_window6_upper is None
                else format(ceiling_attack_drawdown_window6_upper, "f")
            ),
            "ceiling_attack_drawdown_window6_multiplier_lower": (
                ceiling_attack_drawdown_window6_multiplier_lower
            ),
            "ceiling_attack_drawdown_window6_multiplier_upper": (
                ceiling_attack_drawdown_window6_multiplier_upper
            ),
            "ceiling_attack_drawdown_window6_taper_fraction": format(
                ceiling_attack_drawdown_window6_taper_fraction, "f"
            ),
            "ceiling_attack_drawdown_window6_capital_floor": (
                None
                if ceiling_attack_drawdown_window6_capital_floor is None
                else format(ceiling_attack_drawdown_window6_capital_floor, "f")
            ),
            "ceiling_attack_drawdown_window6_capital_ceiling": (
                None
                if ceiling_attack_drawdown_window6_capital_ceiling is None
                else format(ceiling_attack_drawdown_window6_capital_ceiling, "f")
            ),
            "attack_drawdown_window6_taper_bind_count": (
                attack_drawdown_window6_taper_bind_count
            ),
            "ceiling_attack_drawdown_window7_lower": (
                None
                if ceiling_attack_drawdown_window7_lower is None
                else format(ceiling_attack_drawdown_window7_lower, "f")
            ),
            "ceiling_attack_drawdown_window7_upper": (
                None
                if ceiling_attack_drawdown_window7_upper is None
                else format(ceiling_attack_drawdown_window7_upper, "f")
            ),
            "ceiling_attack_drawdown_window7_multiplier_lower": (
                ceiling_attack_drawdown_window7_multiplier_lower
            ),
            "ceiling_attack_drawdown_window7_multiplier_upper": (
                ceiling_attack_drawdown_window7_multiplier_upper
            ),
            "ceiling_attack_drawdown_window7_taper_fraction": format(
                ceiling_attack_drawdown_window7_taper_fraction, "f"
            ),
            "ceiling_attack_drawdown_window7_capital_floor": (
                None
                if ceiling_attack_drawdown_window7_capital_floor is None
                else format(ceiling_attack_drawdown_window7_capital_floor, "f")
            ),
            "ceiling_attack_drawdown_window7_capital_ceiling": (
                None
                if ceiling_attack_drawdown_window7_capital_ceiling is None
                else format(ceiling_attack_drawdown_window7_capital_ceiling, "f")
            ),
            "attack_drawdown_window7_taper_bind_count": (
                attack_drawdown_window7_taper_bind_count
            ),
            "ceiling_attack_stress_confidence_drawdown_trigger": (
                None
                if ceiling_attack_stress_confidence_drawdown_trigger is None
                else format(
                    ceiling_attack_stress_confidence_drawdown_trigger, "f"
                )
            ),
            "ceiling_attack_stress_confidence_ratio_ceiling": (
                None
                if ceiling_attack_stress_confidence_ratio_ceiling is None
                else format(
                    ceiling_attack_stress_confidence_ratio_ceiling, "f"
                )
            ),
            "ceiling_attack_stress_confidence_multiplier_lower": (
                ceiling_attack_stress_confidence_multiplier_lower
            ),
            "ceiling_attack_stress_confidence_multiplier_upper": (
                ceiling_attack_stress_confidence_multiplier_upper
            ),
            "ceiling_attack_stress_confidence_projected_risk_fraction_trigger": (
                None
                if ceiling_attack_stress_confidence_projected_risk_fraction_trigger is None
                else format(
                    ceiling_attack_stress_confidence_projected_risk_fraction_trigger,
                    "f",
                )
            ),
            "ceiling_attack_stress_confidence_capital_floor": (
                None
                if ceiling_attack_stress_confidence_capital_floor is None
                else format(ceiling_attack_stress_confidence_capital_floor, "f")
            ),
            "ceiling_attack_stress_confidence_capital_ceiling": (
                None
                if ceiling_attack_stress_confidence_capital_ceiling is None
                else format(ceiling_attack_stress_confidence_capital_ceiling, "f")
            ),
            "ceiling_attack_stress_confidence_taper_fraction": format(
                ceiling_attack_stress_confidence_taper_fraction, "f"
            ),
            "ceiling_attack_stress_confidence_risk_budget_taper_fraction": format(
                ceiling_attack_stress_confidence_risk_budget_taper_fraction, "f"
            ),
            "attack_stress_confidence_taper_bind_count": (
                attack_stress_confidence_taper_bind_count
            ),
            "attack_stress_confidence_risk_budget_bind_count": (
                attack_stress_confidence_risk_budget_bind_count
            ),
            "ceiling_attack_state_pressure_expected_minutes_floor": (
                None
                if ceiling_attack_state_pressure_expected_minutes_floor is None
                else format(
                    ceiling_attack_state_pressure_expected_minutes_floor,
                    "f",
                )
            ),
            "ceiling_attack_state_pressure_target_r_ceiling": (
                None
                if ceiling_attack_state_pressure_target_r_ceiling is None
                else format(
                    ceiling_attack_state_pressure_target_r_ceiling,
                    "f",
                )
            ),
            "ceiling_attack_state_pressure_confidence_ratio_ceiling": (
                None
                if ceiling_attack_state_pressure_confidence_ratio_ceiling is None
                else format(
                    ceiling_attack_state_pressure_confidence_ratio_ceiling,
                    "f",
                )
            ),
            "ceiling_attack_state_pressure_projected_risk_fraction_trigger": (
                None
                if ceiling_attack_state_pressure_projected_risk_fraction_trigger is None
                else format(
                    ceiling_attack_state_pressure_projected_risk_fraction_trigger,
                    "f",
                )
            ),
            "ceiling_attack_state_pressure_market_posture": (
                ceiling_attack_state_pressure_market_posture
            ),
            "ceiling_attack_state_pressure_h4_range_state": (
                ceiling_attack_state_pressure_h4_range_state
            ),
            "ceiling_attack_state_pressure_risk_budget_taper_fraction": format(
                ceiling_attack_state_pressure_risk_budget_taper_fraction,
                "f",
            ),
            "attack_state_pressure_risk_budget_bind_count": (
                attack_state_pressure_risk_budget_bind_count
            ),
            "ceiling_attack_state_pressure2_expected_minutes_floor": (
                None
                if ceiling_attack_state_pressure2_expected_minutes_floor is None
                else format(ceiling_attack_state_pressure2_expected_minutes_floor, "f")
            ),
            "ceiling_attack_state_pressure2_target_r_ceiling": (
                None
                if ceiling_attack_state_pressure2_target_r_ceiling is None
                else format(ceiling_attack_state_pressure2_target_r_ceiling, "f")
            ),
            "ceiling_attack_state_pressure2_confidence_ratio_ceiling": (
                None
                if ceiling_attack_state_pressure2_confidence_ratio_ceiling is None
                else format(ceiling_attack_state_pressure2_confidence_ratio_ceiling, "f")
            ),
            "ceiling_attack_state_pressure2_projected_risk_fraction_trigger": (
                None
                if ceiling_attack_state_pressure2_projected_risk_fraction_trigger is None
                else format(ceiling_attack_state_pressure2_projected_risk_fraction_trigger, "f")
            ),
            "ceiling_attack_state_pressure2_capital_floor": (
                None
                if ceiling_attack_state_pressure2_capital_floor is None
                else format(ceiling_attack_state_pressure2_capital_floor, "f")
            ),
            "ceiling_attack_state_pressure2_capital_ceiling": (
                None
                if ceiling_attack_state_pressure2_capital_ceiling is None
                else format(ceiling_attack_state_pressure2_capital_ceiling, "f")
            ),
            "ceiling_attack_state_pressure2_market_posture": (
                ceiling_attack_state_pressure2_market_posture
            ),
            "ceiling_attack_state_pressure2_h4_range_state": (
                ceiling_attack_state_pressure2_h4_range_state
            ),
            "ceiling_attack_state_pressure2_risk_budget_taper_fraction": format(
                ceiling_attack_state_pressure2_risk_budget_taper_fraction, "f"
            ),
            "attack_state_pressure2_risk_budget_bind_count": (
                attack_state_pressure2_risk_budget_bind_count
            ),
            "ceiling_attack_trader_loss_ratio_trigger": (
                None
                if ceiling_attack_trader_loss_ratio_trigger is None
                else format(ceiling_attack_trader_loss_ratio_trigger, "f")
            ),
            "ceiling_attack_trader_loss_ratio_min_settlements": (
                ceiling_attack_trader_loss_ratio_min_settlements
            ),
            "ceiling_attack_trader_loss_ratio_taper_fraction": format(
                ceiling_attack_trader_loss_ratio_taper_fraction, "f"
            ),
            "attack_trader_loss_ratio_taper_bind_count": (
                attack_trader_loss_ratio_taper_bind_count
            ),
            "trader_attack_settlement_counts": {
                key: int(value)
                for key, value in sorted(trader_attack_settlement_count.items())
            },
            "ceiling_attack_recent_trader_loss_window": (
                ceiling_attack_recent_trader_loss_window
            ),
            "ceiling_attack_recent_trader_loss_fraction_trigger": (
                None
                if ceiling_attack_recent_trader_loss_fraction_trigger is None
                else format(
                    ceiling_attack_recent_trader_loss_fraction_trigger, "f"
                )
            ),
            "ceiling_attack_recent_trader_loss_drawdown_trigger": format(
                ceiling_attack_recent_trader_loss_drawdown_trigger, "f"
            ),
            "ceiling_attack_recent_trader_loss_taper_fraction": format(
                ceiling_attack_recent_trader_loss_taper_fraction, "f"
            ),
            "attack_recent_trader_loss_taper_bind_count": (
                attack_recent_trader_loss_taper_bind_count
            ),
            "ceiling_attack_trader_shock_trigger_fraction": (
                None
                if ceiling_attack_trader_shock_trigger_fraction is None
                else format(ceiling_attack_trader_shock_trigger_fraction, "f")
            ),
            "ceiling_attack_trader_shock_drawdown_trigger": format(
                ceiling_attack_trader_shock_drawdown_trigger, "f"
            ),
            "ceiling_attack_trader_shock_capital_ceiling": (
                None
                if ceiling_attack_trader_shock_capital_ceiling is None
                else format(ceiling_attack_trader_shock_capital_ceiling, "f")
            ),
            "ceiling_attack_trader_shock_taper_fraction": format(
                ceiling_attack_trader_shock_taper_fraction, "f"
            ),
            "attack_trader_shock_taper_bind_count": (
                attack_trader_shock_taper_bind_count
            ),
            "ending_trader_last_attack_loss_fraction": {
                key: format(value, "f")
                for key, value in sorted(trader_last_attack_loss_fraction.items())
            },
            "ending_trader_shock_protected_signal_count": len(
                trader_shock_protected_signals
            ),
            "ceiling_attack_low_multiplier_demotion_upper": (
                ceiling_attack_low_multiplier_demotion_upper
            ),
            "ceiling_attack_low_multiplier_demotion_drawdown_trigger": format(
                ceiling_attack_low_multiplier_demotion_drawdown_trigger, "f"
            ),
            "attack_low_multiplier_demotion_bind_count": (
                attack_low_multiplier_demotion_bind_count
            ),
            "ending_trader_attack_recent_net_pnl_usd": {
                key: format(sum(values, Decimal(0)), "f")
                for key, values in sorted(trader_attack_recent_net_pnl.items())
            },
            "ceiling_portfolio_shock_trigger_fraction": (
                None
                if ceiling_portfolio_shock_trigger_fraction is None
                else format(ceiling_portfolio_shock_trigger_fraction, "f")
            ),
            "ceiling_portfolio_shock_taper_fraction": format(
                ceiling_portfolio_shock_taper_fraction, "f"
            ),
            "ceiling_portfolio_shock_one_shot": (
                ceiling_portfolio_shock_one_shot
            ),
            "portfolio_last_attack_loss_fraction": format(
                portfolio_last_attack_loss_fraction, "f"
            ),
            "portfolio_attack_shock_taper_bind_count": (
                portfolio_attack_shock_taper_bind_count
            ),
            "ending_trader_attack_loss_streaks": {
                key: int(value)
                for key, value in sorted(trader_attack_loss_streak.items())
            },
            "compound_profit_reinvestment_fraction": (
                None
                if compound_profit_reinvestment_fraction is None
                else format(compound_profit_reinvestment_fraction, "f")
            ),
            "attack_profit_to_sovereign_usd": format(
                state.attack_profit_to_sovereign_usd, "f"
            ),
            "attack_profit_to_portfolio_cushion_usd": format(
                state.attack_profit_to_cushion_usd, "f"
            ),
            "ceiling_growth_leverage_slope": (
                None
                if ceiling_growth_leverage_slope is None
                else format(ceiling_growth_leverage_slope, "f")
            ),
            "ceiling_attack_drawdown_budget_fraction": (
                None
                if ceiling_attack_drawdown_budget_fraction is None
                else format(
                    ceiling_attack_drawdown_budget_fraction, "f"
                )
            ),
            "sizing_intensity_cap_counts": dict(
                sorted(sizing_intensity_cap_counts.items())
            ),
            "medium_drawdown_intensity_trigger": (
                None
                if medium_drawdown_intensity_trigger is None
                else format(medium_drawdown_intensity_trigger, "f")
            ),
            "medium_drawdown_intensity_cap_bind_count": (
                medium_drawdown_intensity_cap_bind_count
            ),
            "medium_profit_to_sovereign_usd": format(
                state.medium_profit_to_sovereign_usd, "f"
            ),
            "medium_profit_to_portfolio_cushion_usd": format(
                state.medium_profit_to_cushion_usd, "f"
            ),
            "portfolio_attack_credit_recycled_total_usd": format(
                state.portfolio_attack_credit_recycled_total_usd, "f"
            ),
            "attack_net_pnl_usd": format(state.attack_net_pnl_usd, "f"),
        "portfolio_loss_report": {
            "attack_winning_trade_count": attack_winning_trade_count,
            "attack_losing_trade_count": attack_losing_trade_count,
            "attack_flat_trade_count": attack_flat_trade_count,
            "attack_gross_profit_usd": format(attack_gross_profit_usd, "f"),
            "attack_gross_loss_usd": format(attack_gross_loss_usd, "f"),
            "total_gross_profit_usd": format(total_gross_profit_usd, "f"),
            "total_gross_loss_usd": format(total_gross_loss_usd, "f"),
            "total_profit_factor": (
                None
                if total_gross_loss_usd <= 0
                else format(
                    total_gross_profit_usd / total_gross_loss_usd,
                    "f",
                )
            ),
            "attack_net_pnl_usd": format(state.attack_net_pnl_usd, "f"),
            "attack_profit_factor": (
                None
                if attack_gross_loss_usd <= 0
                else format(
                    attack_gross_profit_usd / attack_gross_loss_usd,
                    "f",
                )
            ),
            "gross_profit_by_trader_usd": {
                key: format(value, "f")
                for key, value in sorted(
                    attack_gross_profit_by_trader.items()
                )
            },
            "gross_loss_by_trader_usd": {
                key: format(value, "f")
                for key, value in sorted(
                    attack_gross_loss_by_trader.items()
                )
            },
            "gross_profit_by_multiplier_usd": {
                str(key): format(value, "f")
                for key, value in sorted(
                    attack_gross_profit_by_multiplier.items()
                )
            },
            "gross_loss_by_multiplier_usd": {
                str(key): format(value, "f")
                for key, value in sorted(
                    attack_gross_loss_by_multiplier.items()
                )
            },
        },
            "net_account_production_usd": format(
                state.total_capital_usd - INITIAL_CAPITAL_USD, "f"
            ),
            "handoff_chain": [
                "SIZING",
                "CIBO_COMPOUND",
                "COMPOUND_PORTFOLIO",
                "ADAPTIVE_LEVERAGE",
            ],
            "all_entries_preserved": trade_count == len(rows),
        },
        "position_lifecycle_report": position_lifecycle_report,
        "native_telemetry_report": {
            "states": dict(sorted(native_telemetry_counts.items())),
            "telemetry_is_authority": False,
            "missing_telemetry_aborts_replay": False,
            "missing_telemetry_can_authorize_attack": False,
        },
        "engineering_trace": engineering_trace,
        "function_sensors": {
            "SIZING": {
                "call_count": sizing_calls,
                "robust_utility_reject_count": robust_sizing_reject_count,
                "final_binding_trade_count": trade_count,
            },
            "CIBO_COMPOUND": {
                "medium_settlement_count": compound_settlements,
                "medium_positive_net_usd": format(
                    state.medium_compound_positive_net_usd, "f"
                ),
                "medium_negative_net_usd": format(
                    state.medium_compound_negative_net_usd, "f"
                ),
                "medium_turnover_usd": format(
                    state.medium_compound_turnover_usd, "f"
                ),
                "medium_profit_to_sovereign_usd": format(
                    state.medium_profit_to_sovereign_usd,
                    "f",
                ),
                "medium_profit_to_cushion_usd": format(
                    state.medium_profit_to_cushion_usd,
                    "f",
                ),
            },
            "COMPOUND_PORTFOLIO": {
                "call_count": portfolio_calls,
                "attack_epoch_count_with_funded_cushion": (
                    attack_epochs_funded
                ),
                "ending_cushion_usd": format(
                    state.portfolio_cushion_usd,
                    "f",
                ),
                "ending_attack_credit_usd": format(
                    state.portfolio_attack_credit_usd,
                    "f",
                ),
            },
            "ADAPTIVE_LEVERAGE": {
                "call_count": adaptive_leverage_calls,
                "robust_economic_cap_binding_count": (
                    robust_leverage_cap_bind_count
                ),
                "attack_trade_count": trade_mode_counts["ATTACK"],
                "average_selected_multiplier": format(
                    average_leverage,
                    "f",
                ),
                "maximum_selected_multiplier": leverage_max,
            },
        },
        "trader_results": {
            trader: {
                "trade_count": trader_trades[trader],
                "net_pnl_usd": format(net, "f"),
            }
            for trader, net in sorted(trader_net.items())
        },
        "baseline_ending_capital_usd": (
            None
            if baseline_ending_capital_usd is None
            else format(baseline_ending_capital_usd, "f")
        ),
        "delta_vs_baseline_ending_capital_usd": (
            None if baseline_delta is None else format(baseline_delta, "f")
        ),
        "trade_receipts": trade_receipts,
        "epoch_receipts": epoch_receipts,
        "governance": {
            "trader_lab_only": True,
            "sovereign_runtime_mutated": False,
            "full_economic_engineering_telemetry": collect_engineering_trace,
            "engineering_telemetry_mode": (
                "FULL_TRACE"
                if collect_engineering_trace
                else "SUMMARY_AGGREGATES"
            ),
            "epoch_receipts_collected": collect_epoch_receipts,
            "trade_receipt_mode": (
                "COMPACT_SCIENCE"
                if compact_trade_receipts
                else "FULL"
            ),
            "economic_sensor_functions": list(economic_functions),
            "native_cognition_gate_consumed": True,
            "native_cognition_source": (
                "FROZEN_PREDECISION_WALK_FORWARD_REPLAY"
            ),
            "native_profile_consumed": True,
            "coordinated_economic_group": coordinated_economic_group,
            "ceiling_attack_drawdown_budget_fraction": (
                None
                if ceiling_attack_drawdown_budget_fraction is None
                else format(
                    ceiling_attack_drawdown_budget_fraction, "f"
                )
            ),
            "medium_drawdown_intensity_trigger": (
                None
                if medium_drawdown_intensity_trigger is None
                else format(medium_drawdown_intensity_trigger, "f")
            ),
            "medium_drawdown_intensity_cap_bind_count": (
                medium_drawdown_intensity_cap_bind_count
            ),
            "economic_group_bootstrap_cushion_share": format(
                economic_group_bootstrap_cushion_share, "f"
            ),
            "economic_group_ablation": economic_group_ablation,
            "economic_group_handoff": (
                "SIZING_TO_CIBO_COMPOUND_TO_COMPOUND_PORTFOLIO_TO_ADAPTIVE_LEVERAGE"
                if coordinated_economic_group
                else None
            ),
            "position_lifecycle_consumed": bool(lifecycle_map),
            "position_lifecycle_defensive_medium_1x_only": (
                lifecycle_defensive_medium_1x_only
            ),
            "position_lifecycle_attack_only": lifecycle_attack_only,
            "position_lifecycle_defensive_medium_max_multiplier": (
                lifecycle_defensive_medium_max_multiplier
            ),
            "position_lifecycle_drawdown_trigger": (
                None
                if lifecycle_defense_drawdown_trigger is None
                else format(lifecycle_defense_drawdown_trigger, "f")
            ),
            "position_lifecycle_trader_loss_streak_trigger": (
                lifecycle_trader_loss_streak_trigger
            ),
            "position_lifecycle_bootstrap_capital_ceiling_usd": (
                None
                if lifecycle_bootstrap_capital_ceiling is None
                else format(lifecycle_bootstrap_capital_ceiling, "f")
            ),
            "position_lifecycle_minimum_stop_risk_fraction_trigger": (
                None
                if lifecycle_minimum_stop_risk_fraction_trigger is None
                else format(lifecycle_minimum_stop_risk_fraction_trigger, "f")
            ),
            "position_lifecycle_projected_open_stop_risk_fraction_trigger": (
                None
                if lifecycle_projected_open_stop_risk_fraction_trigger is None
                else format(
                    lifecycle_projected_open_stop_risk_fraction_trigger, "f"
                )
            ),
            "position_lifecycle_source": (
                "MARKET_ATLAS_10Y_CAUSAL_CLOSED_M5_POST_ENTRY"
                if lifecycle_map else None
            ),
            "position_lifecycle_post_entry_only": bool(lifecycle_map),
            "position_lifecycle_outcome_used_for_trigger": False,
            "position_lifecycle_fallback": (
                "ORIGINAL_SETTLEMENT_WHEN_NO_CAUSAL_BAR_INTERVENTION_DATA"
                if lifecycle_map else None
            ),
            "historical_native_intensity_law": (
                "HISTORICAL_PLUS_NATIVE_CONSENSUS_UP_TO_CONFIGURED_MEDIUM_CAP; "
                "NATIVE_ONLY_OVERRIDE_1X; HISTORICAL_ONLY_DEFENSIVE_1X; "
                "BOTH_NONDEPLOYMENT_DEFENSIVE_1X; NO_ENTRY_REJECTION"
            ),
            "historical_prior_consumed": use_historical_prior,
            "historical_control_sizing_prior_consumed": (
                use_historical_prior
                and all(
                    "historical_control_ready" in profile
                    for profile in historical_prior_map.values()
                )
            ),
            "compound_distribution_basis": (
                "NET_NEW_PRODUCTION_AFTER_LOSS_RECOVERY"
                if use_historical_prior
                else "PER_POSITIVE_SETTLEMENT"
            ),
            "portfolio_prior_source": (
                "FROZEN_HISTORICAL_PRIOR"
                if use_historical_prior
                else "CURRENT_WALK_FORWARD_EXPECTATION"
            ),
            "attack_expectation_law": (
                (
                    "DISTRIBUTED_NATIVE_ALLOW_POSITIVE_UNCERTAINTY_UTILITY_"
                    "AT_LEAST_4_POSITIVE_WALK_FORWARD_BLOCKS"
                )
                if distributed_attack_frontier
                else "WEAKEST_OF_FIVE_CAUSAL_CHRONOLOGICAL_BLOCKS"
            ),
            "distributed_attack_frontier": distributed_attack_frontier,
            "distributed_attack_min_positive_blocks": (
                DISTRIBUTED_ATTACK_MIN_POSITIVE_BLOCKS
            ),
            "attack_multiplier_cap": attack_multiplier_cap,
            "medium_multiplier_cap": medium_multiplier_cap,
            "context_quality_abstain_enforced": (
                enforce_research_context_abstain
            ),
            "context_gate_status": (
                "POST_BURN_HYPOTHESIS_REQUIRES_FRESH_VALIDATION"
                if enforce_research_context_abstain
                else "ADVISORY_ONLY_AS_DECLARED_BY_SOURCE_MANIFEST"
            ),
            "qore_risk_authority_claimed": False,
            "broker_mutation": False,
            "live_authority": False,
            "certification_claimed": False,
            "outcome_used_for_predecision": False,
            "medium_positive_profit_split": "50%_SOVEREIGN_50%_CUSHION",
            "bank_role": "TREASURY_SEEDS_MEDIUM_ONLY_NO_TRADES",
            "trader_entry_admission_authority": "TRADER",
            "cibo_entry_rejection_authority": False,
            "cibo_management_invariant": (
                "EVERY_TRADER_EXECUTED_ENTRY_RECEIVES_NONZERO_MANAGEMENT; "
                "COGNITION_CHANGES_INTENSITY_NOT_ADMISSION"
            ),
            "drawdown_policy": (
                "SOFT_CAUSAL_MEDIUM_ALLOCATOR_WITH_REALIZED_DD_VALIDATION; "
                "ATTACK_STOPS_AT_20PCT"
                if soft_medium_drawdown_allocator
                else (
                    "TOTAL_DRAWDOWN_AT_20PCT_STOPS_NEW_ATTACK_TO_PRESERVE_"
                    "THE_25PCT_CEILING; MEDIUM_REMAINS_AVAILABLE"
                )
            ),
            "soft_medium_drawdown_allocator": (
                soft_medium_drawdown_allocator
            ),
            "medium_pretrade_drawdown_ceiling": format(
                medium_pretrade_drawdown_ceiling, "f"
            ),
            "bank_seed_source": (
                "4PCT_OF_CURRENT_TOTAL_ACCOUNT_CAPITAL_PER_MEDIUM_ENTRY"
            ),
            "bank_seed_fraction_per_entry": format(
                MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO, "f"
            ),
            "bank_seed_scaling": "DYNAMIC_PER_ENTRY_WITH_ACCOUNT_GROWTH",
            "bank_seed_hard_source_cap": "REMAINING_SOVEREIGN_AVAILABLE",
            "medium_engine": "SIZING_PLUS_CIBO_COMPOUND",
            "medium_capital_source": (
                "BANK_SEED_OPENS_CYCLE; SIZING_CAPABILITY_BOUNDED_BY_"
                "NATIVE_INTENSITY_RISK_MARGIN_PROVIDER"
            ),
            "sizing_role": (
                "USE_4PCT_BANK_SEED_AS_WORKING_CAPITAL_PROVENANCE_NOT_"
                "AS_HARD_EXPOSURE_CAP"
            ),
            "sizing_second_edge_veto": False,
            "cibo_compound_role": (
                "SETTLE_MEDIUM_RETURN_SEED_TO_BANK_SPLIT_POSITIVE_PNL"
            ),
            "medium_profit_distribution_basis": (
                "REALIZED_MEDIUM_POSITIVE_PNL_50PCT_SOVEREIGN_50PCT_PORTFOLIO"
            ),
            "attack_risk_source": "PORTFOLIO_CUSHION_ONLY",
            "portfolio_attack_release_policy": (
                "REVOLVING_PORTFOLIO_CUSHION; MEDIUM_50PCT_PROFIT_AND_"
                "SETTLED_ATTACK_CAPITAL_REMAIN_AVAILABLE_FOR_FUTURE_ATTACK"
            ),
            "leverage_law": (
                (
                    "DISTRIBUTED_ATTACK_BOUNDED_BY_EXPLICIT_FRONTIER_CAP_"
                    "AFTER_PORTFOLIO_ENABLE"
                )
                if distributed_attack_frontier
                else "ATTACK_UNCAPPED_BY_ECONOMIC_UTILITY_AFTER_PORTFOLIO_ENABLE"
            ),
            "attack_enable_authority": "COMPOUND_PORTFOLIO",
            "attack_internal_economic_cap": "FORBIDDEN",
            "bank_sovereign_risk": "WORKING_CAPITAL_SEED_ENVELOPE_ONLY",
            "bank_recovery_probe": "FORBIDDEN_BANK_DOES_NOT_TRADE",
            "bank_recovery_positive_pnl": "NOT_APPLICABLE",
            "medium_sovereign_floor": (
                "NOT_PREDEDUCTED; BANK_GATE_DEFENDS_AT_50PCT_DRAWDOWN"
            ),
            "medium_uncertainty_policy": (
                "UNCERTAINTY_INFORMS_ESCALATION_NOT_MINIMUM_EDGE_EXISTENCE"
            ),
        },
    }
