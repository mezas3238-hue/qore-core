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

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
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
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    manifest_row_to_shadow_outcome_observation,
)

INITIAL_CAPITAL_USD = Decimal("60")
MEDIUM_SOVEREIGN_SHARE = Decimal("0.50")
MEDIUM_CUSHION_SHARE = Decimal("0.50")
ATTACK_MINIMUM_MULTIPLIER = 2
MARGIN_CAPACITY_MULTIPLE = Decimal("100")
SOVEREIGN_DEFENSIVE_DRAWDOWN = Decimal("0.50")


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
    native_cognition_recommended: bool
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


@dataclass(slots=True)
class _State:
    sovereign_bank_usd: Decimal = INITIAL_CAPITAL_USD
    portfolio_cushion_usd: Decimal = Decimal(0)
    sovereign_reserved_usd: Decimal = Decimal(0)
    medium_seed_authorized_usd: Decimal = Decimal(0)
    medium_seed_reserved_usd: Decimal = Decimal(0)
    bank_seed_authorization_count: int = 0
    bank_seed_authorized_total_usd: Decimal = Decimal(0)
    cushion_reserved_usd: Decimal = Decimal(0)
    portfolio_attack_credit_usd: Decimal = Decimal(0)
    open_stop_risk_usd: Decimal = Decimal(0)
    open_margin_usd: Decimal = Decimal(0)
    peak_total_capital_usd: Decimal = INITIAL_CAPITAL_USD
    peak_sovereign_bank_usd: Decimal = INITIAL_CAPITAL_USD
    max_drawdown_usd: Decimal = Decimal(0)
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
    attack_net_pnl_usd: Decimal = Decimal(0)

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
    def medium_seed_available_usd(self) -> Decimal:
        return max(
            Decimal(0),
            min(
                self.medium_seed_authorized_usd
                - self.medium_seed_reserved_usd,
                self.sovereign_available_usd,
            ),
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
    native_cognition_recommended: bool,
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
    with localcontext() as context:
        context.prec = 100
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
            and native_cognition_recommended
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
    if drawdown_utilization >= SOVEREIGN_DEFENSIVE_DRAWDOWN:
        bank_reasons.append("SOVEREIGN_DRAWDOWN_GE_50PCT")
    if risk_utilization >= cibo_new_capital_risk_utilization_ceiling():
        bank_reasons.append("RISK_UTILIZATION_DEFENSIVE")
    if margin_utilization >= Decimal("0.80"):
        bank_reasons.append("MARGIN_UTILIZATION_DEFENSIVE")
    if bank_reasons:
        return CiboTraderLabMode.BANK, tuple(bank_reasons)

    if best_candidate is None:
        return CiboTraderLabMode.MEDIUM, ("NO_ATTACK_GRADE_CANDIDATE",)

    attack_context_reasons: list[str] = []
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
) -> CiboTraderLabMode:
    """Compatibility wrapper returning only the selected mode."""

    mode, _reasons = explain_three_mode(
        regime=regime,
        risk_utilization=risk_utilization,
        margin_utilization=margin_utilization,
        drawdown_utilization=drawdown_utilization,
        cushion_available_usd=cushion_available_usd,
        best_candidate=best_candidate,
    )
    return mode

def apply_three_mode_settlement(
    state: _State,
    trade: CiboThreeModeOpenTrade,
) -> Decimal:
    """Settle one already-due trade; no outcome is consulted before exit."""

    with localcontext() as context:
        context.prec = 100
        gross_pnl = trade.gross_r * trade.stop_risk_usd
        net_pnl = gross_pnl - trade.provider_cost_usd

    state.open_stop_risk_usd -= trade.stop_risk_usd
    state.open_margin_usd -= trade.margin_usd
    if trade.mode is CiboTraderLabMode.MEDIUM:
        state.sovereign_reserved_usd -= trade.source_reserved_usd
        state.medium_seed_reserved_usd -= trade.source_reserved_usd
        state.medium_compound_turnover_usd += trade.source_reserved_usd
        if net_pnl > 0:
            sovereign_gain = net_pnl * MEDIUM_SOVEREIGN_SHARE
            cushion_gain = net_pnl - sovereign_gain
            state.sovereign_bank_usd += sovereign_gain
            state.portfolio_cushion_usd += cushion_gain
            # Only MEDIUM production creates new ATTACK release credit.
            state.portfolio_attack_credit_usd += cushion_gain
            state.medium_profit_to_sovereign_usd += sovereign_gain
            state.medium_profit_to_cushion_usd += cushion_gain
            state.medium_compound_positive_net_usd += net_pnl
        else:
            # The BANK seed is the MEDIUM working capital. A MEDIUM loss
            # consumes that seed and sovereign capital; Portfolio is not used
            # to subsidize the loss.
            state.sovereign_bank_usd += net_pnl
            state.medium_seed_authorized_usd = max(
                Decimal(0),
                state.medium_seed_authorized_usd + net_pnl,
            )
            state.medium_compound_negative_net_usd += -net_pnl
    elif trade.mode is CiboTraderLabMode.ATTACK:
        state.cushion_reserved_usd -= trade.source_reserved_usd
        state.portfolio_cushion_usd += net_pnl
        state.attack_net_pnl_usd += net_pnl
        if state.portfolio_cushion_usd < 0:
            breach = -state.portfolio_cushion_usd
            state.attack_sovereign_breach_usd += breach
            state.portfolio_cushion_usd = Decimal(0)
            state.sovereign_bank_usd -= breach
        state.portfolio_attack_credit_usd = min(
            state.portfolio_attack_credit_usd,
            state.cushion_available_usd,
        )
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
    cognitive_recommend_by_signal: Mapping[str, bool] | None = None,
    enforce_research_context_abstain: bool = False,
) -> dict[str, object]:
    """Run the isolated chronological three-mode ceiling experiment."""

    if type(enforce_research_context_abstain) is not bool:
        raise CiboCapitalManagementError(
            "Trader Lab context hypothesis switch must be bool"
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
    cognitive_map = (
        {signal: True for signal in signals}
        if cognitive_recommend_by_signal is None
        else dict(cognitive_recommend_by_signal)
    )
    if set(cognitive_map) != set(signals) or any(
        type(value) is not bool for value in cognitive_map.values()
    ):
        raise CiboCapitalManagementError(
            "Trader Lab cognitive recommendation map must cover exact manifest signals"
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
    leverage_sum = 0
    leverage_max = 0
    portfolio_calls = 0
    sizing_calls = 0
    compound_settlements = 0
    adaptive_leverage_calls = 0
    robust_sizing_reject_count = 0
    robust_leverage_cap_bind_count = 0
    attack_epochs_funded = 0
    mode_reason_counts: Counter[str] = Counter()
    trade_receipts: list[dict[str, object]] = []
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

    def settle_due(up_to: datetime | None) -> None:
        nonlocal pending, compound_settlements
        due = sorted(
            (
                item
                for item in pending
                if up_to is None or item.exit_at <= up_to
            ),
            key=lambda item: (item.exit_at, item.signal_fingerprint),
        )
        if not due:
            return
        due_ids = {id(item) for item in due}
        pending = [item for item in pending if id(item) not in due_ids]
        for trade in due:
            before_sovereign = state.sovereign_bank_usd
            before_cushion = state.portfolio_cushion_usd
            before_total = state.total_capital_usd
            settlement_function = (
                "CIBO_COMPOUND"
                if trade.mode is CiboTraderLabMode.MEDIUM
                else "COMPOUND_PORTFOLIO"
            )
            record_engineering_sensor(
                settlement_function,
                epoch_index=None,
                signal_fingerprint=trade.signal_fingerprint,
                event="SETTLEMENT_INPUT",
                inputs={
                    "mode": trade.mode.value,
                    "multiplier": trade.multiplier,
                    "gross_r_postdecision": format(trade.gross_r, "f"),
                    "stop_risk_usd": format(trade.stop_risk_usd, "f"),
                    "provider_cost_usd": format(
                        trade.provider_cost_usd, "f"
                    ),
                    "source_reserved_usd": format(
                        trade.source_reserved_usd, "f"
                    ),
                    "sovereign_bank_before_usd": format(
                        before_sovereign, "f"
                    ),
                    "portfolio_cushion_before_usd": format(
                        before_cushion, "f"
                    ),
                },
                action="SETTLE_DUE_TRADE",
                outputs={"exit_at": trade.exit_at.isoformat()},
                reaction="AWAIT_SETTLEMENT_OUTPUT",
                call=True,
            )
            net = apply_three_mode_settlement(state, trade)
            created = max(Decimal(0), net)
            destroyed = max(Decimal(0), -net)
            record_engineering_sensor(
                settlement_function,
                epoch_index=None,
                signal_fingerprint=trade.signal_fingerprint,
                event="SETTLEMENT_OUTPUT",
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
                    "sovereign_delta_usd": format(
                        state.sovereign_bank_usd - before_sovereign, "f"
                    ),
                    "cushion_delta_usd": format(
                        state.portfolio_cushion_usd - before_cushion, "f"
                    ),
                },
                reaction=(
                    "INCREASE_FUTURE_CAPITAL_CAPACITY"
                    if net > 0
                    else "REDUCE_FUTURE_CAPITAL_CAPACITY"
                    if net < 0
                    else "NO_CAPITAL_CHANGE"
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
        candidates = tuple(
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
        eligible = tuple(
            sorted(
                (
                    item
                    for item in candidates
                    if item.context_allowed
                    and item.expected_edge_after_cost_usd > 0
                    and item.maximum_multiplier > 0
                ),
                key=lambda item: (
                    -item.capital_time_score,
                    -item.expected_net_utility_usd,
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
        best = eligible[0] if eligible else None
        mode, mode_reasons = explain_three_mode(
            regime=regime,
            risk_utilization=risk_utilization,
            margin_utilization=margin_utilization,
            drawdown_utilization=drawdown_utilization,
            cushion_available_usd=state.attack_credit_available_usd,
            best_candidate=best,
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
                "risk_utilization": format(risk_utilization, "f"),
                "margin_utilization": format(margin_utilization, "f"),
                "drawdown_utilization": format(
                    drawdown_utilization, "f"
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

        selected: list[tuple[CiboThreeModeCandidate, int]] = []
        risk_left = max(Decimal(0), risk_capacity - state.open_stop_risk_usd)
        margin_left = max(
            Decimal(0),
            margin_capacity - state.open_margin_usd,
        )
        sovereign_left = state.sovereign_available_usd
        cushion_left = state.cushion_available_usd

        # BANK is treasury, not execution. Before MEDIUM works, BANK leaves a
        # working-capital seed sized to current 1x MEDIUM demand. The seed is
        # an earmarked subset of sovereign capital, so it never inflates total
        # account capital.
        if mode is CiboTraderLabMode.MEDIUM and eligible:
            medium_seed_demand = sum(
                (
                    item.source_cost_per_multiplier_usd
                    for item in eligible
                ),
                Decimal(0),
            )
            bank_seed_target = min(
                state.sovereign_available_usd
                + state.medium_seed_reserved_usd,
                medium_seed_demand,
            )
            bank_seed_topup = max(
                Decimal(0),
                bank_seed_target - state.medium_seed_authorized_usd,
            )
            if bank_seed_topup > 0:
                state.medium_seed_authorized_usd += bank_seed_topup
                state.bank_seed_authorization_count += 1
                state.bank_seed_authorized_total_usd += bank_seed_topup
            record_engineering_sensor(
                "SIZING",
                epoch_index=epoch_index,
                signal_fingerprint=None,
                event="BANK_SEED_SUPPLY",
                inputs={
                    "medium_seed_demand_usd": format(
                        medium_seed_demand, "f"
                    ),
                    "sovereign_available_usd": format(
                        state.sovereign_available_usd, "f"
                    ),
                },
                action="BANK_LEAVES_MEDIUM_SEED",
                outputs={
                    "medium_seed_authorized_usd": format(
                        state.medium_seed_authorized_usd, "f"
                    ),
                    "medium_seed_topup_usd": format(
                        bank_seed_topup, "f"
                    ),
                },
                reaction="SIZING_RECEIVES_BANK_SEED",
                approved_capital_usd=bank_seed_topup,
            )

        portfolio_attack_release_left = (
            state.attack_credit_available_usd
            if mode is CiboTraderLabMode.ATTACK
            else Decimal(0)
        )
        medium_seed_left = (
            state.medium_seed_available_usd
            if mode is CiboTraderLabMode.MEDIUM
            else Decimal(0)
        )

        if mode is not CiboTraderLabMode.BANK:
            candidate_surface = eligible
            for candidate in candidate_surface:
                if mode is CiboTraderLabMode.MEDIUM:
                    sizing_calls += 1
                    record_engineering_sensor(
                        "SIZING",
                        epoch_index=epoch_index,
                        signal_fingerprint=candidate.signal_fingerprint,
                        event="SIZING_INPUT",
                        inputs={
                            "mode": mode.value,
                            "one_x_source_cost_usd": format(
                                candidate.source_cost_per_multiplier_usd, "f"
                            ),
                            "one_x_stop_risk_usd": format(
                                candidate.stop_risk_per_multiplier_usd, "f"
                            ),
                            "one_x_margin_usd": format(
                                candidate.margin_per_multiplier_usd, "f"
                            ),
                            "expected_net_utility_usd": format(
                                candidate.expected_net_utility_usd, "f"
                            ),
                            "bank_seed_available_usd": format(
                                medium_seed_left, "f"
                            ),
                            "risk_left_usd": format(risk_left, "f"),
                            "margin_left_usd": format(margin_left, "f"),
                        },
                        action="SIZE_FROM_BANK_SEED",
                        outputs={},
                        reaction="AWAIT_SIZING_DECISION",
                        call=True,
                    )
                    economic_cap = 1
                    multiplier = 1
                    source_left = medium_seed_left
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
                    leverage_caps = {
                        "PROVIDER_MAX": candidate.maximum_multiplier,
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
                        robust_sizing_reject_count += 1
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
                            action="REJECT_ATTACK_MULTIPLIER",
                            outputs={
                                "feasible_multiplier": multiplier,
                                "selected_multiplier": 0,
                                "binding_caps": list(binding_caps),
                            },
                            reaction="ATTACK_NOT_DEPLOYED",
                            reasons=binding_caps,
                            rejection=True,
                            requested_capital_usd=requested_leverage_capital,
                            blocked_capital_usd=(
                                requested_leverage_capital
                            ),
                        )
                        continue
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
                capacity_reasons: list[str] = []
                if stop_risk > risk_left:
                    capacity_reasons.append("RISK_CAPACITY_EXHAUSTED")
                if margin > margin_left:
                    capacity_reasons.append("MARGIN_CAPACITY_EXHAUSTED")
                if source_reserved > source_left:
                    capacity_reasons.append("CAPITAL_SOURCE_EXHAUSTED")
                if capacity_reasons:
                    target_function = (
                        "ADAPTIVE_LEVERAGE"
                        if mode is CiboTraderLabMode.ATTACK
                        else "SIZING"
                    )
                    record_engineering_sensor(
                        target_function,
                        epoch_index=epoch_index,
                        signal_fingerprint=candidate.signal_fingerprint,
                        event="CAPACITY_REACTION",
                        inputs={
                            "stop_risk_usd": format(stop_risk, "f"),
                            "risk_left_usd": format(risk_left, "f"),
                            "margin_usd": format(margin, "f"),
                            "margin_left_usd": format(margin_left, "f"),
                            "source_reserved_usd": format(
                                source_reserved, "f"
                            ),
                            "source_left_usd": format(source_left, "f"),
                        },
                        action="REJECT_ON_HARD_CAPACITY",
                        outputs={"selected_multiplier": 0},
                        reaction="CAPITAL_NOT_DEPLOYED",
                        reasons=tuple(capacity_reasons),
                        rejection=True,
                        requested_capital_usd=source_reserved,
                        blocked_capital_usd=source_reserved,
                    )
                    continue
                selected.append((candidate, multiplier))
                if mode is CiboTraderLabMode.MEDIUM:
                    record_engineering_sensor(
                        "SIZING",
                        epoch_index=epoch_index,
                        signal_fingerprint=candidate.signal_fingerprint,
                        event="SIZING_OUTPUT",
                        inputs={
                            "mode": mode.value,
                            "bank_seed_authorized_usd": format(
                                state.medium_seed_authorized_usd, "f"
                            ),
                        },
                        action="APPROVE_MEDIUM_FROM_BANK_SEED",
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
                if mode is CiboTraderLabMode.MEDIUM:
                    sovereign_left -= source_reserved
                    medium_seed_left -= source_reserved
                else:
                    cushion_left -= source_reserved
                    portfolio_attack_release_left -= source_reserved

        for candidate, multiplier in selected:
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
            trade = CiboThreeModeOpenTrade(
                signal_fingerprint=candidate.signal_fingerprint,
                trader_id=candidate.trader_id,
                mode=mode,
                multiplier=multiplier,
                exit_at=candidate.exit_at,
                gross_r=candidate.gross_r,
                stop_risk_usd=stop_risk,
                margin_usd=margin,
                provider_cost_usd=provider_cost,
                source_reserved_usd=source_reserved,
            )
            pending.append(trade)
            trade_receipts.append(
                {
                    "signal_fingerprint": candidate.signal_fingerprint,
                    "trader_id": candidate.trader_id,
                    "decision_at": candidate.decision_at.isoformat(),
                    "exit_at": candidate.exit_at.isoformat(),
                    "mode": mode.value,
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
                                state.medium_seed_available_usd
                                if mode is CiboTraderLabMode.MEDIUM
                                else state.cushion_available_usd
                            ),
                            expected_net_utility_usd=(
                                candidate.attack_expected_net_utility_usd
                                if mode is CiboTraderLabMode.ATTACK
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
                    "mode_reasons": list(mode_reasons),
                }
            )
            state.open_stop_risk_usd += stop_risk
            state.open_margin_usd += margin
            if mode is CiboTraderLabMode.MEDIUM:
                state.sovereign_reserved_usd += source_reserved
                state.medium_seed_reserved_usd += source_reserved
            else:
                state.cushion_reserved_usd += source_reserved
                state.portfolio_attack_credit_usd = max(
                    Decimal(0),
                    state.portfolio_attack_credit_usd - source_reserved,
                )
            trade_mode_counts[mode.value] += 1
            leverage_sum += multiplier
            leverage_max = max(leverage_max, multiplier)

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
                    multiplier for _candidate, multiplier in selected
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
                "medium_seed_authorized_usd": format(
                    state.medium_seed_authorized_usd, "f"
                ),
                "medium_seed_available_usd": format(
                    state.medium_seed_available_usd, "f"
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
    max_drawdown_pct = _ratio(
        state.max_drawdown_usd,
        state.peak_total_capital_usd,
    )
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
            + sizing_approval_count
            + leverage_rejection_count
            + leverage_approval_count
            == len(rows)
        ),
    }

    engineering_sensor_report = {
        "schema": "qore.trader_lab.cibo_economic_engineering_sensors.v1",
        "trace_event_count": len(engineering_trace),
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
            "POST_BURN_CONTEXT_ABSTAIN_HYPOTHESIS"
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
        "bank_seed_authorization_count": (
            state.bank_seed_authorization_count
        ),
        "bank_seed_authorized_total_usd": format(
            state.bank_seed_authorized_total_usd, "f"
        ),
        "medium_seed_authorized_usd": format(
            state.medium_seed_authorized_usd, "f"
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
        "portfolio_attack_credit_usd": format(
            state.portfolio_attack_credit_usd, "f"
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
        "attack_epoch_count_with_funded_cushion": attack_epochs_funded,
        "engineering_sensor_report": engineering_sensor_report,
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
            "full_economic_engineering_telemetry": True,
            "economic_sensor_functions": list(economic_functions),
            "native_cognition_gate_consumed": True,
            "native_cognition_source": (
                "FROZEN_PREDECISION_WALK_FORWARD_REPLAY"
            ),
            "attack_expectation_law": (
                "WEAKEST_OF_FIVE_CAUSAL_CHRONOLOGICAL_BLOCKS"
            ),
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
            "bank_seed_source": "SOVEREIGN_WORKING_CAPITAL_ENVELOPE",
            "medium_engine": "SIZING_PLUS_CIBO_COMPOUND",
            "medium_capital_source": "BANK_SEED_ONLY",
            "sizing_role": (
                "ALLOCATE_BANK_SEED_AFTER_COGNITIVE_ECONOMIC_ADMISSION"
            ),
            "sizing_second_edge_veto": False,
            "cibo_compound_role": (
                "SETTLE_MEDIUM_RECYCLE_SEED_SPLIT_POSITIVE_PROFIT"
            ),
            "attack_risk_source": "PORTFOLIO_CUSHION_ONLY",
            "portfolio_attack_release_policy": (
                "ONLY_UNSPENT_CREDITS_CREATED_BY_MEDIUM_50PCT_PROFIT_SHARE"
            ),
            "leverage_law": (
                "ATTACK_UNCAPPED_BY_ECONOMIC_UTILITY_AFTER_PORTFOLIO_ENABLE"
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
