"""CIBO BANK / MEDIUM / ATTACK ceiling experiment for GitHub Trader Lab.

This module is deliberately isolated under Trader Lab. It does not mutate the
sovereign runtime, QORE Risk, broker state, LIVE state or certifying evidence.

Owner-defined economics:
- BANK protects sovereign capital and opens no new risk.
- MEDIUM uses ordinary 1x executable sizing. Positive net profit is partitioned
  50% to the sovereign bank and 50% to the Compound Portfolio cushion.
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
from decimal import ROUND_FLOOR, Decimal, localcontext
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
    expected_net_utility_usd: Decimal
    expected_capital_minutes: Decimal
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
            return self.expected_net_utility_usd / self.expected_capital_minutes

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
    cushion_reserved_usd: Decimal = Decimal(0)
    open_stop_risk_usd: Decimal = Decimal(0)
    open_margin_usd: Decimal = Decimal(0)
    peak_total_capital_usd: Decimal = INITIAL_CAPITAL_USD
    max_drawdown_usd: Decimal = Decimal(0)
    min_sovereign_bank_usd: Decimal = INITIAL_CAPITAL_USD
    cushion_high_watermark_usd: Decimal = Decimal(0)
    attack_sovereign_breach_usd: Decimal = Decimal(0)
    medium_profit_to_sovereign_usd: Decimal = Decimal(0)
    medium_profit_to_cushion_usd: Decimal = Decimal(0)
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

    def mark(self) -> None:
        total = self.total_capital_usd
        self.peak_total_capital_usd = max(self.peak_total_capital_usd, total)
        drawdown = max(Decimal(0), self.peak_total_capital_usd - total)
        self.max_drawdown_usd = max(self.max_drawdown_usd, drawdown)
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


def _candidate(row: Mapping[str, Any]) -> CiboThreeModeCandidate:
    evidence = manifest_row_to_ceiling_opportunity_evidence(row)
    outcome = manifest_row_to_shadow_outcome_observation(row)
    opportunity = evidence.opportunity
    minimum = minimum_seed_volume(opportunity)
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
        expected_net = (
            evidence.expected_net_value_usd
            - provider_cost
            - evidence.uncertainty_penalty_usd
        )
    return CiboThreeModeCandidate(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id.value,
        decision_at=outcome.decision_at,
        exit_at=outcome.exit_at,
        gross_r=outcome.gross_structural_outcome_r,
        expected_net_utility_usd=expected_net,
        expected_capital_minutes=evidence.expected_capital_minutes,
        minimum_volume=minimum,
        maximum_multiplier=max(0, maximum_multiplier),
        stop_risk_per_multiplier_usd=stop,
        margin_per_multiplier_usd=margin,
        provider_cost_per_multiplier_usd=provider_cost,
        context_allowed=(
            evidence.context_allowed
            and evidence.provider_viable
            and evidence.capital_source_eligible
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


def select_three_mode(
    *,
    regime: CiboTraderLabRegime,
    risk_utilization: Decimal,
    margin_utilization: Decimal,
    drawdown_utilization: Decimal,
    cushion_available_usd: Decimal,
    best_candidate: CiboThreeModeCandidate | None,
) -> CiboTraderLabMode:
    """Choose exactly BANK, MEDIUM or ATTACK from causal state."""

    if (
        regime.evidence_stale
        or regime.provider_condition is not ProviderCondition.HEALTHY
        or regime.liquidity is LiquidityState.STRESSED
        or regime.volatility is VolatilityState.DISLOCATED
        or regime.correlation is CorrelationState.BREAK
        or regime.position_path_adverse
        or drawdown_utilization >= Decimal("0.50")
        or risk_utilization >= cibo_new_capital_risk_utilization_ceiling()
        or margin_utilization >= Decimal("0.80")
    ):
        return CiboTraderLabMode.BANK

    if best_candidate is None:
        return CiboTraderLabMode.MEDIUM
    attack_context = (
        regime.liquidity is LiquidityState.NORMAL
        and regime.volatility
        in {VolatilityState.COMPRESSED, VolatilityState.NORMAL}
        and regime.correlation is CorrelationState.NORMAL
        and best_candidate.expected_net_utility_usd > 0
        and best_candidate.context_allowed
        and best_candidate.maximum_multiplier >= ATTACK_MINIMUM_MULTIPLIER
    )
    minimum_attack_cushion = (
        best_candidate.source_cost_per_multiplier_usd
        * Decimal(ATTACK_MINIMUM_MULTIPLIER)
    )
    if attack_context and cushion_available_usd >= minimum_attack_cushion:
        return CiboTraderLabMode.ATTACK
    return CiboTraderLabMode.MEDIUM


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
        if net_pnl > 0:
            sovereign_gain = net_pnl * MEDIUM_SOVEREIGN_SHARE
            cushion_gain = net_pnl - sovereign_gain
            state.sovereign_bank_usd += sovereign_gain
            state.portfolio_cushion_usd += cushion_gain
            state.medium_profit_to_sovereign_usd += sovereign_gain
            state.medium_profit_to_cushion_usd += cushion_gain
        else:
            state.sovereign_bank_usd += net_pnl
    elif trade.mode is CiboTraderLabMode.ATTACK:
        state.cushion_reserved_usd -= trade.source_reserved_usd
        state.portfolio_cushion_usd += net_pnl
        state.attack_net_pnl_usd += net_pnl
        if state.portfolio_cushion_usd < 0:
            breach = -state.portfolio_cushion_usd
            state.attack_sovereign_breach_usd += breach
            state.portfolio_cushion_usd = Decimal(0)
            state.sovereign_bank_usd -= breach
    else:
        raise CiboCapitalManagementError(
            "BANK mode cannot own an open Trader Lab trade"
        )
    state.mark()
    return net_pnl


def run_three_mode_trader_lab(
    manifest: Mapping[str, Any],
    *,
    baseline_ending_capital_usd: Decimal | None = None,
) -> dict[str, object]:
    """Run the isolated chronological three-mode ceiling experiment."""

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
    attack_epochs_funded = 0
    epoch_receipts: list[dict[str, object]] = []

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
            net = apply_three_mode_settlement(state, trade)
            trader_net[trade.trader_id] += net
            trader_trades[trade.trader_id] += 1
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
        candidates = tuple(_candidate(row) for row in epoch_rows)
        eligible = tuple(
            sorted(
                (
                    item
                    for item in candidates
                    if item.context_allowed
                    and item.expected_net_utility_usd > 0
                    and item.maximum_multiplier > 0
                ),
                key=lambda item: (
                    -item.capital_time_score,
                    -item.expected_net_utility_usd,
                    item.signal_fingerprint,
                ),
            )
        )

        total = state.total_capital_usd
        risk_capacity = (
            total * cibo_new_capital_risk_utilization_ceiling()
        )
        margin_capacity = total * MARGIN_CAPACITY_MULTIPLE
        drawdown = max(Decimal(0), state.peak_total_capital_usd - total)
        risk_utilization = _ratio(state.open_stop_risk_usd, risk_capacity)
        margin_utilization = _ratio(state.open_margin_usd, margin_capacity)
        drawdown_utilization = _ratio(
            drawdown,
            state.peak_total_capital_usd,
        )
        best = eligible[0] if eligible else None
        mode = select_three_mode(
            regime=regime,
            risk_utilization=risk_utilization,
            margin_utilization=margin_utilization,
            drawdown_utilization=drawdown_utilization,
            cushion_available_usd=state.cushion_available_usd,
            best_candidate=best,
        )
        mode_counts[mode.value] += 1
        portfolio_calls += 1
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

        if mode is not CiboTraderLabMode.BANK:
            for candidate in eligible:
                sizing_calls += 1
                if mode is CiboTraderLabMode.MEDIUM:
                    multiplier = 1
                    source_left = sovereign_left
                else:
                    adaptive_leverage_calls += 1
                    source_left = cushion_left
                    caps = [
                        candidate.maximum_multiplier,
                        int(
                            (
                                source_left
                                / candidate.source_cost_per_multiplier_usd
                            ).to_integral_value(rounding=ROUND_FLOOR)
                        ),
                        int(
                            (
                                risk_left
                                / candidate.stop_risk_per_multiplier_usd
                            ).to_integral_value(rounding=ROUND_FLOOR)
                        ),
                        int(
                            (
                                margin_left
                                / candidate.margin_per_multiplier_usd
                            ).to_integral_value(rounding=ROUND_FLOOR)
                        ),
                    ]
                    multiplier = max(0, min(caps))
                    if multiplier < ATTACK_MINIMUM_MULTIPLIER:
                        continue

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
                    stop_risk > risk_left
                    or margin > margin_left
                    or source_reserved > source_left
                ):
                    continue
                selected.append((candidate, multiplier))
                risk_left -= stop_risk
                margin_left -= margin
                if mode is CiboTraderLabMode.MEDIUM:
                    sovereign_left -= source_reserved
                else:
                    cushion_left -= source_reserved

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
            state.open_stop_risk_usd += stop_risk
            state.open_margin_usd += margin
            if mode is CiboTraderLabMode.MEDIUM:
                state.sovereign_reserved_usd += source_reserved
            else:
                state.cushion_reserved_usd += source_reserved
            trade_mode_counts[mode.value] += 1
            leverage_sum += multiplier
            leverage_max = max(leverage_max, multiplier)

        epoch_receipts.append(
            {
                "epoch_index": epoch_index,
                "decision_at": decision_at.isoformat(),
                "mode": mode.value,
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
                "portfolio_cushion_usd": format(
                    state.portfolio_cushion_usd,
                    "f",
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

    return {
        "schema": "qore.trader_lab.cibo_three_mode_ceiling.v1",
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
        "attack_net_pnl_usd": format(
            state.attack_net_pnl_usd,
            "f",
        ),
        "mode_epoch_counts": dict(sorted(mode_counts.items())),
        "trade_mode_counts": dict(sorted(trade_mode_counts.items())),
        "trade_count": trade_count,
        "average_selected_multiplier": format(
            average_leverage,
            "f",
        ),
        "maximum_selected_multiplier": leverage_max,
        "attack_epoch_count_with_funded_cushion": attack_epochs_funded,
        "function_sensors": {
            "SIZING": {
                "call_count": sizing_calls,
                "final_binding_trade_count": trade_count,
            },
            "CIBO_COMPOUND": {
                "settlement_count": compound_settlements,
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
            },
            "ADAPTIVE_LEVERAGE": {
                "call_count": adaptive_leverage_calls,
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
        "epoch_receipts": epoch_receipts,
        "governance": {
            "trader_lab_only": True,
            "sovereign_runtime_mutated": False,
            "qore_risk_authority_claimed": False,
            "broker_mutation": False,
            "live_authority": False,
            "certification_claimed": False,
            "outcome_used_for_predecision": False,
            "medium_positive_profit_split": "50%_SOVEREIGN_50%_CUSHION",
            "attack_risk_source": "PORTFOLIO_CUSHION_ONLY",
            "bank_new_risk": "FORBIDDEN",
        },
    }
