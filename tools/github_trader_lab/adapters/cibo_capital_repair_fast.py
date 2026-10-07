#!/usr/bin/env python3
"""Fast CIBO capital-path replay for the independent GitHub Trader Lab.

Consumes a prepared causal opportunity ledger and replays only the capital
actuator path. It is non-certifying and uses burned research history.
Settlement outcomes are applied only after their exit time.
"""

from __future__ import annotations

import argparse
import heapq
import itertools
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal, localcontext
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_maximum_capability_frontier import (
    cognitive_multiplier_cap,
)

ZERO = Decimal(0)
ONE = Decimal(1)
HUNDRED = Decimal(100)
INITIAL = Decimal("60")


def d(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non-finite Decimal")
    return result


def d_or_zero(value: object) -> Decimal:
    """Parse optional research telemetry without blocking an executed base trade."""

    if value is None:
        return ZERO
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "nan"}:
        return ZERO
    try:
        result = Decimal(text)
    except Exception:
        return ZERO
    return result if result.is_finite() else ZERO


def ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return ZERO if numerator <= 0 else ONE
    with localcontext() as ctx:
        ctx.prec = 80
        return max(ZERO, min(ONE, numerator / denominator))


def floor_step(value: Decimal, step: Decimal) -> Decimal:
    if value <= 0:
        return ZERO
    with localcontext() as ctx:
        ctx.prec = 80
        return (
            (value / step).to_integral_value(rounding=ROUND_FLOOR)
            * step
        )


@dataclass(frozen=True)
class Variant:
    name: str
    risk_fraction: Decimal
    graded_intensity: bool
    uncertainty_priced: bool
    robust_portfolio: bool
    genc12_binding: bool
    fixed_multiplier: int | None = None
    recency_guard: bool = False
    profit_funded_leverage: bool = False
    max_frontier: bool = False


VARIANTS = (
    Variant(
        "TRADER_BASE_1X_CONTROL",
        Decimal("1"),
        False,
        False,
        False,
        False,
        fixed_multiplier=1,
    ),
    Variant("MATURE_4X_CONTROL", Decimal("1"), False, False, False, False),
    Variant("GRADED_INTENSITY", Decimal("1"), True, False, False, False),
    Variant("GRADED_PLUS_SURVIVAL", Decimal("0.70"), True, False, False, True),
    Variant("FULL_CAUSAL_REPAIR", Decimal("0.70"), True, True, True, True),
    Variant(
        "FULL_REPAIR_FIXED_1X_ATTRIBUTION",
        Decimal("0.70"),
        True,
        True,
        True,
        True,
        fixed_multiplier=1,
    ),
    Variant(
        "RECENCY_GUARD_FIXED_1X_ATTRIBUTION",
        Decimal("0.70"),
        True,
        True,
        True,
        True,
        fixed_multiplier=1,
        recency_guard=True,
    ),
    Variant(
        "FULL_CAUSAL_REPAIR_RECENCY_GUARD",
        Decimal("0.70"),
        True,
        True,
        True,
        True,
        recency_guard=True,
    ),
    Variant(
        "PROFIT_FUNDED_ADAPTIVE_LEVERAGE",
        Decimal("0.70"),
        True,
        True,
        True,
        True,
        profit_funded_leverage=True,
    ),
    Variant(
        "MAX_FRONTIER_WIRING_REPAIR",
        Decimal("0.70"),
        True,
        True,
        True,
        True,
        profit_funded_leverage=True,
        max_frontier=True,
    ),
)


@dataclass(frozen=True)
class EconomicAssessment:
    disposition: str
    sizing_mode: str
    expected_net_usd: Decimal
    multiplier_cap: int
    reason_codes: tuple[str, ...]
    legacy_prefilter_would_drop: bool

    def __post_init__(self) -> None:
        if self.disposition not in {
            "ELIGIBLE_FOR_INTERNAL_CAPITAL_MARKET",
            "REDUCE_INCREMENT",
            "RESERVE_DOMINATED",
            "INSUFFICIENT",
        }:
            raise ValueError("unknown economic disposition")
        if self.multiplier_cap not in {1, 2, 3, 4}:
            raise ValueError(
                "economic total multiplier cap must preserve Trader base 1x"
            )
        if not self.reason_codes:
            raise ValueError("economic assessment requires reason codes")


@dataclass
class Deployment:
    signal: str
    trader_id: str
    exit_at: str
    risk: Decimal
    margin: Decimal
    provider_cost: Decimal
    gross_r: Decimal
    multiplier: int
    volume: Decimal
    observation_count: int
    positive_blocks: int
    nonpositive_blocks: int
    mad_r: Decimal
    dispersion_r: Decimal
    expected_net_min_usd: Decimal
    global_expected_r: Decimal
    recent_block_r: Decimal


def _genc12_allows_new_capital(row: dict[str, Any], has_capacity: bool) -> bool:
    if not has_capacity:
        return False
    regime = row["regime"]
    if bool(regime.get("evidence_stale")):
        return False
    if str(regime.get("provider_condition")) != "HEALTHY":
        return False
    if str(regime.get("liquidity")) == "STRESSED":
        return False
    return True


def _confidence_cap(
    *,
    row: dict[str, Any],
    risk_utilization: Decimal,
    margin_utilization: Decimal,
    drawdown_utilization: Decimal,
) -> int:
    maturity = d(row.get("walk_forward_maturity_fraction", "0"))
    utilization = max(
        risk_utilization,
        margin_utilization,
        drawdown_utilization,
    )
    consensus_pct = int(row.get("walk_forward_positive_block_count", 0)) * 20
    regime = row["regime"]
    attention_pressure = 0
    provider = str(regime.get("provider_condition"))
    correlation = str(regime.get("correlation"))
    volatility = str(regime.get("volatility"))
    if provider == "UNAVAILABLE":
        attention_pressure = max(attention_pressure, 100)
    elif provider == "DEGRADED":
        attention_pressure = max(attention_pressure, 70)
    if correlation == "BREAK":
        attention_pressure = max(attention_pressure, 90)
    elif correlation != "NORMAL":
        attention_pressure = max(attention_pressure, 65)
    if volatility == "DISLOCATED":
        attention_pressure = max(attention_pressure, 95)
    if bool(regime.get("position_path_adverse")):
        attention_pressure = max(attention_pressure, 85)

    confidence_band = max(
        0,
        min(
            100,
            100 - int(utilization * HUNDRED),
            int(maturity * HUNDRED),
            consensus_pct,
            100 - attention_pressure,
        ),
    )
    if confidence_band >= 67:
        return 3
    if confidence_band >= 34:
        return 2
    return 1


def _maximum_frontier_cap(
    *,
    row: dict[str, Any],
    opportunity_count: int,
    risk_utilization: Decimal,
    margin_utilization: Decimal,
    drawdown_utilization: Decimal,
) -> int:
    """Call the subject's real MAX Frontier policy with causal live state."""

    regime = row["regime"]
    utilization = {
        "risk_utilization": format(risk_utilization, "f"),
        "margin_utilization": format(margin_utilization, "f"),
        "drawdown_utilization": format(drawdown_utilization, "f"),
    }
    receipts: list[dict[str, object]] = []
    for index in range(1, 20):
        code = f"CF{index:02d}"
        input_payload: dict[str, object] = {}
        if code == "CF02":
            input_payload = {"regime": dict(regime)}
        elif code == "CF06":
            input_payload = {
                "utilization": utilization,
                "opportunity_count": opportunity_count,
                "correlation": str(regime.get("correlation")),
            }
        elif code == "CF07":
            input_payload = {
                "provider_condition": str(regime.get("provider_condition")),
            }
        elif code == "CF10":
            input_payload = {"utilization": utilization}
        elif code == "CF12":
            input_payload = {"utilization": utilization}
        receipts.append(
            {
                "function_code": code,
                "input_payload": input_payload,
                "output_payload": {
                    "native_engine_status": (
                        "JUSTIFIED_NOT_APPLICABLE"
                        if code in {"CF08", "CF18", "CF19"}
                        else "SUCCESS"
                    )
                },
            }
        )
    cap, _codes, _reason = cognitive_multiplier_cap(
        {"faculty_receipts": receipts}
    )
    return cap


def _economic_assessment(
    row: dict[str, Any],
    *,
    variant: Variant,
    has_capacity: bool,
) -> EconomicAssessment:
    """Route every Native opportunity through economics.

    Context, forecast edge and provider state are modifiers/dispositions, not
    deletion gates. A 0x reserve decision remains an explicit economic result.
    """

    basis = str(row.get("expectation_basis", ""))
    mature = bool(row.get("walk_forward_mature"))
    context_allowed = bool(row.get("context_allowed"))
    provider_viable = bool(row.get("provider_viable"))
    capital_source_eligible = bool(row.get("capital_source_eligible"))

    minimum_volume = d(row["minimum_volume"])
    provider_cost = d(row["provider_cost_per_volume_usd"]) * minimum_volume
    minimum_stop_risk = d(row["stop_loss_per_volume"]) * minimum_volume
    value = d(row["expected_net_value_usd"]) - provider_cost

    reasons: list[str] = []
    if variant.recency_guard:
        blocks_raw = row.get("walk_forward_block_means_r")
        if isinstance(blocks_raw, list) and len(blocks_raw) == 5:
            global_r = d_or_zero(
                row.get("walk_forward_expected_structural_r")
            )
            recent_r = d_or_zero(blocks_raw[-1])
            conservative_r = min(global_r, recent_r)
            value = conservative_r * minimum_stop_risk - provider_cost
            reasons.append("RECENCY_GUARD_APPLIED")
        else:
            reasons.append("RECENCY_EVIDENCE_INSUFFICIENT")

    if variant.uncertainty_priced:
        value -= d(row["uncertainty_penalty_usd"])
        reasons.append("UNCERTAINTY_PRICED")

    regime = row["regime"]
    provider_condition = str(regime.get("provider_condition", "UNAVAILABLE"))
    evidence_stale = bool(regime.get("evidence_stale"))
    liquidity = str(regime.get("liquidity", "STRESSED"))

    legacy_would_drop = (
        basis != "WALK_FORWARD_EMPIRICAL_FORECAST"
        or not mature
        or not context_allowed
        or not provider_viable
        or not capital_source_eligible
        or value <= 0
    )

    # Missing/immature causal forecast is an explicit insufficient-evidence
    # disposition, not disappearance from the opportunity surface.
    if basis != "WALK_FORWARD_EMPIRICAL_FORECAST" or not mature:
        if basis != "WALK_FORWARD_EMPIRICAL_FORECAST":
            reasons.append("FORECAST_BASIS_NOT_WALK_FORWARD")
        if not mature:
            reasons.append("FORECAST_NOT_MATURE")
        return EconomicAssessment(
            disposition="INSUFFICIENT",
            sizing_mode="BASE_1X_PROTECT_NO_ADDITIONAL_EXPOSURE",
            expected_net_usd=value,
            multiplier_cap=1,
            reason_codes=tuple(sorted(set(reasons))),
            legacy_prefilter_would_drop=legacy_would_drop,
        )

    # Economics may choose reserve because capital/provider/edge does not
    # deserve deployment. This is downstream economic adjudication.
    if not has_capacity:
        reasons.append("ACCOUNT_CAPACITY_EXHAUSTED")
    if not capital_source_eligible:
        reasons.append("CAPITAL_SOURCE_INELIGIBLE")
    if provider_condition == "UNAVAILABLE":
        reasons.append("PROVIDER_UNAVAILABLE")
    if value <= 0:
        reasons.append("NET_INCREMENTAL_RETURN_NON_POSITIVE")
    if (
        not has_capacity
        or not capital_source_eligible
        or provider_condition == "UNAVAILABLE"
        or value <= 0
    ):
        return EconomicAssessment(
            disposition="RESERVE_DOMINATED",
            sizing_mode="BASE_1X_PROTECT_NO_ADDITIONAL_EXPOSURE",
            expected_net_usd=value,
            multiplier_cap=1,
            reason_codes=tuple(sorted(set(reasons))),
            legacy_prefilter_would_drop=legacy_would_drop,
        )

    defensive = False
    if not context_allowed:
        defensive = True
        reasons.append("CONTEXT_REQUIRES_DEFENSIVE_CAPITAL")
    if not provider_viable:
        defensive = True
        reasons.append("PROVIDER_VIABILITY_REQUIRES_REDUCTION")
    if provider_condition == "DEGRADED":
        defensive = True
        reasons.append("PROVIDER_DEGRADED")
    if variant.genc12_binding and evidence_stale:
        defensive = True
        reasons.append("GENC12_EVIDENCE_STALE")
    if variant.genc12_binding and liquidity == "STRESSED":
        defensive = True
        reasons.append("GENC12_STRESSED_LIQUIDITY")

    if defensive:
        return EconomicAssessment(
            disposition="REDUCE_INCREMENT",
            sizing_mode="BASE_1X_DEFENSIVE_NO_ADDITIONAL_EXPOSURE",
            expected_net_usd=value,
            multiplier_cap=1,
            reason_codes=tuple(sorted(set(reasons))),
            legacy_prefilter_would_drop=legacy_would_drop,
        )

    reasons.append("NEXT_INCREMENT_PASSES_MARGINAL_UTILITY_HURDLES")
    return EconomicAssessment(
        disposition="ELIGIBLE_FOR_INTERNAL_CAPITAL_MARKET",
        sizing_mode="BASE_1X_PLUS_ECONOMIC_INTENSIFICATION",
        expected_net_usd=value,
        multiplier_cap=4,
        reason_codes=tuple(sorted(set(reasons))),
        legacy_prefilter_would_drop=legacy_would_drop,
    )


def _portfolio(
    rows: list[dict[str, Any]],
    *,
    variant: Variant,
    capital: Decimal,
    risk_headroom: Decimal,
    margin_headroom: Decimal,
    risk_utilization: Decimal,
    margin_utilization: Decimal,
    drawdown_utilization: Decimal,
) -> tuple[
    tuple[int, ...],
    tuple[Decimal, ...],
    tuple[EconomicAssessment, ...],
]:
    """Allocate only exposure ABOVE the Trader's mandatory base 1x.

    Returned combo values are incremental multipliers 0..3. The base 1x is
    outside CIBO admission authority and cannot be removed by this optimizer.
    """

    extra_caps: list[int] = []
    nets: list[Decimal] = []
    assessments: list[EconomicAssessment] = []
    has_capacity = risk_headroom > 0 and margin_headroom > 0

    for row in rows:
        assessment = _economic_assessment(
            row,
            variant=variant,
            has_capacity=has_capacity,
        )
        assessments.append(assessment)
        nets.append(assessment.expected_net_usd)

        minimum_volume = d(row["minimum_volume"])
        maximum_volume = d(row["maximum_volume"])
        if minimum_volume <= 0 or maximum_volume < minimum_volume:
            raise ValueError("Trader base execution geometry is invalid")

        total_cap = min(
            assessment.multiplier_cap,
            4,
            int(maximum_volume / minimum_volume),
        )
        total_cap = max(1, total_cap)

        if variant.graded_intensity:
            total_cap = max(
                1,
                min(
                    total_cap,
                    _confidence_cap(
                        row=row,
                        risk_utilization=risk_utilization,
                        margin_utilization=margin_utilization,
                        drawdown_utilization=drawdown_utilization,
                    ),
                ),
            )
        if variant.max_frontier:
            total_cap = max(
                1,
                min(
                    total_cap,
                    _maximum_frontier_cap(
                        row=row,
                        opportunity_count=len(rows),
                        risk_utilization=risk_utilization,
                        margin_utilization=margin_utilization,
                        drawdown_utilization=drawdown_utilization,
                    ),
                ),
            )
        if variant.fixed_multiplier is not None:
            total_cap = max(1, min(total_cap, variant.fixed_multiplier))

        extra_caps.append(max(0, total_cap - 1))

    best_key: tuple[Any, ...] | None = None
    best_combo = tuple(0 for _ in rows)
    best_velocity = tuple(ZERO for _ in rows)

    for combo in itertools.product(*(range(cap + 1) for cap in extra_caps)):
        incremental_loss = sum(
            (
                (
                    d(row["stop_loss_per_volume"])
                    + d(row["provider_cost_per_volume_usd"])
                )
                * d(row["minimum_volume"])
                * extra
                for row, extra in zip(rows, combo, strict=True)
            ),
            ZERO,
        )
        incremental_margin = sum(
            (
                d(row["margin_per_volume"])
                * d(row["minimum_volume"])
                * extra
                for row, extra in zip(rows, combo, strict=True)
            ),
            ZERO,
        )
        if (
            incremental_loss > risk_headroom
            or incremental_margin > margin_headroom
        ):
            continue

        if variant.profit_funded_leverage:
            incremental_leverage_risk = sum(
                (
                    d(row["stop_loss_per_volume"])
                    * d(row["minimum_volume"])
                    * extra
                    for row, extra in zip(rows, combo, strict=True)
                ),
                ZERO,
            )
            realized_profit_buffer = max(ZERO, capital - INITIAL)
            if incremental_leverage_risk > realized_profit_buffer:
                continue

        robust_lines: list[Decimal] = []
        velocity_lines: list[Decimal] = []
        for row, net, extra in zip(rows, nets, combo, strict=True):
            base_risk = (
                d(row["stop_loss_per_volume"]) * d(row["minimum_volume"])
            )
            utility = net * extra
            if variant.robust_portfolio and extra and capital > 0:
                with localcontext() as ctx:
                    ctx.prec = 80
                    total_multiplier = Decimal(1 + extra)
                    base_penalty = (base_risk * base_risk) / capital
                    total_penalty = (
                        (base_risk * total_multiplier)
                        * (base_risk * total_multiplier)
                        / capital
                    )
                    utility -= total_penalty - base_penalty
            robust_lines.append(utility)
            duration = max(ONE, d(row["expected_capital_minutes"]))
            velocity_lines.append(
                utility / duration
                if row["expectation_basis"]
                == "WALK_FORWARD_EMPIRICAL_FORECAST"
                else ZERO
            )

        trusted_velocity = sum(velocity_lines, ZERO)
        expected_utility = sum(robust_lines, ZERO)
        key = (
            trusted_velocity,
            expected_utility,
            -incremental_loss,
            -incremental_margin,
            tuple(-value for value in combo),
        )
        if best_key is None or key > best_key:
            best_key = key
            best_combo = tuple(int(value) for value in combo)
            best_velocity = tuple(velocity_lines)

    return best_combo, best_velocity, tuple(assessments)


def _temporal_blocks(settlements: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[Decimal]] = defaultdict(list)
    for row in settlements:
        stamp = str(row["settled_at"])
        month = int(stamp[5:7])
        key = stamp[:4] + ("-H1" if month <= 6 else "-H2")
        groups[key].append(d(row["net_r"]))
    result: dict[str, Any] = {}
    for key, values in sorted(groups.items()):
        equity = peak = max_dd = ZERO
        for value in values:
            equity += value
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        result[key] = {
            "mean_r": format(sum(values, ZERO) / Decimal(len(values)), "f"),
            "max_drawdown_r": format(max_dd, "f"),
        }
    return result


def _metrics(
    settlements: list[dict[str, Any]],
    *,
    peak: Decimal,
    ending: Decimal,
    max_dd: Decimal,
    multiplier_counts: Counter[str],
    block_counts: Counter[str],
) -> dict[str, Any]:
    net_rs = [d(row["net_r"]) for row in settlements]
    gains = sum((value for value in net_rs if value > 0), ZERO)
    losses = -sum((value for value in net_rs if value < 0), ZERO)
    wins = sum(value > 0 for value in net_rs)
    loss_count = sum(value < 0 for value in net_rs)
    pf = None if losses == 0 else format(gains / losses, "f")
    mean_r = ZERO if not net_rs else sum(net_rs, ZERO) / Decimal(len(net_rs))

    by_trader: dict[str, dict[str, object]] = {}
    for trader in sorted({str(row["trader_id"]) for row in settlements}):
        selected = [
            row for row in settlements if str(row["trader_id"]) == trader
        ]
        pnl = sum(
            (d(row["realized_net_pnl_usd"]) for row in selected),
            ZERO,
        )
        total_risk = sum((d(row["risk_usd"]) for row in selected), ZERO)
        simple_mean_r = (
            sum((d(row["net_r"]) for row in selected), ZERO)
            / Decimal(len(selected))
        )
        risk_weighted_mean_r = (
            ZERO if total_risk <= 0 else pnl / total_risk
        )
        by_trader[trader] = {
            "trade_count": len(selected),
            "net_pnl_usd": format(pnl, "f"),
            "total_risk_usd": format(total_risk, "f"),
            "mean_net_r": format(simple_mean_r, "f"),
            "risk_weighted_mean_net_r": format(risk_weighted_mean_r, "f"),
            "risk_allocation_sign_mismatch": (
                simple_mean_r > 0 and risk_weighted_mean_r < 0
            ),
        }

    observation_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    consensus_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    recent_sign_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    recency_relation_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    multiplier_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    trader_multiplier_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in settlements:
        observations = int(row["observation_count"])
        if observations < 50:
            observation_key = "25_49"
        elif observations < 100:
            observation_key = "50_99"
        elif observations < 250:
            observation_key = "100_249"
        else:
            observation_key = "250_PLUS"
        observation_buckets[observation_key].append(row)
        consensus_buckets[
            f"{int(row['positive_blocks'])}_OF_5_POSITIVE_BLOCKS"
        ].append(row)
        recent_sign_buckets[
            "RECENT_POSITIVE"
            if d(row["recent_block_r"]) > 0
            else "RECENT_NONPOSITIVE"
        ].append(row)
        recency_relation_buckets[
            "RECENT_BELOW_GLOBAL"
            if d(row["recent_block_r"]) < d(row["global_expected_r"])
            else "RECENT_AT_OR_ABOVE_GLOBAL"
        ].append(row)
        multiplier_buckets[f"{int(row['multiplier'])}X"].append(row)
        trader_multiplier_buckets[
            f"{row['trader_id']}|{int(row['multiplier'])}X"
        ].append(row)

    def bucket_summary(
        buckets: dict[str, list[dict[str, Any]]],
    ) -> dict[str, dict[str, object]]:
        result: dict[str, dict[str, object]] = {}
        for key, selected in sorted(buckets.items()):
            pnl = sum(
                (d(row["realized_net_pnl_usd"]) for row in selected),
                ZERO,
            )
            total_risk = sum((d(row["risk_usd"]) for row in selected), ZERO)
            result[key] = {
                "trade_count": len(selected),
                "net_pnl_usd": format(pnl, "f"),
                "total_risk_usd": format(total_risk, "f"),
                "risk_weighted_mean_net_r": format(
                    ZERO if total_risk <= 0 else pnl / total_risk,
                    "f",
                ),
                "mean_net_r": format(
                    sum((d(row["net_r"]) for row in selected), ZERO)
                    / Decimal(len(selected)),
                    "f",
                ),
                "mean_expected_net_min_usd": format(
                    sum(
                        (d(row["expected_net_min_usd"]) for row in selected),
                        ZERO,
                    )
                    / Decimal(len(selected)),
                    "f",
                ),
            }
        return result

    total_provider_cost = sum(
        (d(row["provider_cost_usd"]) for row in settlements),
        ZERO,
    )
    expected_min_total = sum(
        (d(row["expected_net_min_usd"]) for row in settlements),
        ZERO,
    )
    return {
        "trade_count": len(settlements),
        "metrics": {
            "profit_factor": pf,
            "mean_r": format(mean_r, "f"),
            "max_drawdown_r": format(max_dd / INITIAL, "f"),
            "wins": wins,
            "losses": loss_count,
        },
        "capital_path": {
            "initial_capital_usd": format(INITIAL, "f"),
            "ending_capital_usd": format(ending, "f"),
            "net_pnl_usd": format(ending - INITIAL, "f"),
            "peak_capital_usd": format(peak, "f"),
            "maximum_drawdown_usd": format(max_dd, "f"),
            "maximum_drawdown_fraction_of_initial": format(max_dd / INITIAL, "f"),
            "adaptive_leverage_counts": dict(sorted(multiplier_counts.items())),
            "block_counts": dict(sorted(block_counts.items())),
            "economic_routing": {
                "presented": int(block_counts["ECONOMIC_PRESENTED"]),
                "evaluated": int(block_counts["ECONOMIC_EVALUATED"]),
                "legacy_prefilter_would_drop": int(
                    block_counts["LEGACY_PREFILTER_WOULD_DROP"]
                ),
                "recovered_to_economy": int(
                    block_counts["RECOVERED_TO_ECONOMY"]
                ),
                "eligible": int(
                    block_counts[
                        "ECONOMIC_DISPOSITION_ELIGIBLE_FOR_INTERNAL_CAPITAL_MARKET"
                    ]
                ),
                "reduce_increment": int(
                    block_counts["ECONOMIC_DISPOSITION_REDUCE_INCREMENT"]
                ),
                "reserve_dominated": int(
                    block_counts["ECONOMIC_DISPOSITION_RESERVE_DOMINATED"]
                ),
                "insufficient": int(
                    block_counts["ECONOMIC_DISPOSITION_INSUFFICIENT"]
                ),
                "trader_base_1x_presented": int(
                    block_counts["TRADER_BASE_1X_PRESENTED"]
                ),
                "trader_base_1x_managed": int(
                    block_counts["TRADER_BASE_1X_MANAGED"]
                ),
                "legacy_prefilter_recovered_base_1x": int(
                    block_counts["LEGACY_PREFILTER_RECOVERED_BASE_1X"]
                ),
                "cibo_base_rejections": 0,
            },
        },
        "net_r_values": [format(value, "f") for value in net_rs],
        "temporal_blocks": _temporal_blocks(settlements),
        "attribution": {
            "per_trader": by_trader,
            "observation_count_buckets": bucket_summary(
                observation_buckets
            ),
            "positive_block_consensus_buckets": bucket_summary(
                consensus_buckets
            ),
            "recent_block_sign_buckets": bucket_summary(
                recent_sign_buckets
            ),
            "recency_relation_buckets": bucket_summary(
                recency_relation_buckets
            ),
            "multiplier_buckets": bucket_summary(multiplier_buckets),
            "trader_multiplier_buckets": bucket_summary(
                trader_multiplier_buckets
            ),
            "provider_cost_usd": format(total_provider_cost, "f"),
            "expected_net_minimum_size_usd_sum": format(
                expected_min_total,
                "f",
            ),
        },
    }


def simulate(rows: list[dict[str, Any]], variant: Variant) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[
            (str(row["decision_at"]), str(row["decision_epoch_id"]))
        ].append(row)

    capital = INITIAL
    peak = INITIAL
    max_dd = ZERO
    open_risk = ZERO
    open_margin = ZERO
    provider_reserve = ZERO
    pending: list[tuple[str, int, Deployment]] = []
    sequence = 0
    settlements: list[dict[str, Any]] = []
    multiplier_counts: Counter[str] = Counter()
    block_counts: Counter[str] = Counter()

    def settle_until(cutoff: str | None) -> None:
        nonlocal capital, peak, max_dd
        nonlocal open_risk, open_margin, provider_reserve
        while pending and (cutoff is None or pending[0][0] <= cutoff):
            _, _, dep = heapq.heappop(pending)
            pnl = dep.gross_r * dep.risk - dep.provider_cost
            capital += pnl
            open_risk -= dep.risk
            open_margin -= dep.margin
            provider_reserve -= dep.provider_cost
            peak = max(peak, capital)
            max_dd = max(max_dd, peak - capital)
            settlements.append(
                {
                    "signal_fingerprint": dep.signal,
                    "trader_id": dep.trader_id,
                    "settled_at": dep.exit_at,
                    "realized_net_pnl_usd": format(pnl, "f"),
                    "risk_usd": format(dep.risk, "f"),
                    "net_r": format(
                        ZERO if dep.risk <= 0 else pnl / dep.risk,
                        "f",
                    ),
                    "multiplier": dep.multiplier,
                    "volume": format(dep.volume, "f"),
                    "observation_count": dep.observation_count,
                    "positive_blocks": dep.positive_blocks,
                    "nonpositive_blocks": dep.nonpositive_blocks,
                    "mad_r": format(dep.mad_r, "f"),
                    "dispersion_r": format(dep.dispersion_r, "f"),
                    "expected_net_min_usd": format(
                        dep.expected_net_min_usd,
                        "f",
                    ),
                    "provider_cost_usd": format(dep.provider_cost, "f"),
                    "global_expected_r": format(
                        dep.global_expected_r,
                        "f",
                    ),
                    "recent_block_r": format(dep.recent_block_r, "f"),
                    "recent_minus_global_r": format(
                        dep.recent_block_r - dep.global_expected_r,
                        "f",
                    ),
                }
            )

    for (decision_at, _epoch_id), epoch_rows in sorted(grouped.items()):
        settle_until(decision_at)

        rows_sorted = sorted(
            epoch_rows,
            key=lambda row: (
                str(row["trader_id"]),
                str(row["qore_symbol"]),
                str(row["signal_fingerprint"]),
            ),
        )

        base_stop_risk = sum(
            (
                d(row["stop_loss_per_volume"]) * d(row["minimum_volume"])
                for row in rows_sorted
            ),
            ZERO,
        )
        base_margin = sum(
            (
                d(row["margin_per_volume"]) * d(row["minimum_volume"])
                for row in rows_sorted
            ),
            ZERO,
        )
        base_provider_cost = sum(
            (
                d(row["provider_cost_per_volume_usd"])
                * d(row["minimum_volume"])
                for row in rows_sorted
            ),
            ZERO,
        )

        effective_capital = max(ZERO, capital)
        if capital <= 0:
            block_counts["ACCOUNT_NONPOSITIVE_BASE_STILL_MANAGED"] += len(
                rows_sorted
            )

        stop_capacity = max(
            ZERO,
            effective_capital - provider_reserve - base_provider_cost,
        )
        total_risk_capacity = min(
            stop_capacity,
            effective_capital * variant.risk_fraction,
        )
        margin_capacity = max(
            ZERO,
            effective_capital * Decimal("100")
            - provider_reserve
            - base_provider_cost,
        )
        risk_headroom = max(
            ZERO,
            total_risk_capacity - open_risk - base_stop_risk,
        )
        margin_headroom = max(
            ZERO,
            margin_capacity - open_margin - base_margin,
        )
        risk_utilization = ratio(
            open_risk + base_stop_risk,
            total_risk_capacity,
        )
        margin_utilization = ratio(
            open_margin + base_margin,
            margin_capacity,
        )
        drawdown_utilization = ratio(peak - capital, max(peak, ONE))

        extra_combo, velocities, assessments = _portfolio(
            rows_sorted,
            variant=variant,
            capital=effective_capital,
            risk_headroom=risk_headroom,
            margin_headroom=margin_headroom,
            risk_utilization=risk_utilization,
            margin_utilization=margin_utilization,
            drawdown_utilization=drawdown_utilization,
        )

        block_counts["TRADER_BASE_1X_PRESENTED"] += len(rows_sorted)
        block_counts["TRADER_BASE_1X_MANAGED"] += len(rows_sorted)
        block_counts["ECONOMIC_PRESENTED"] += len(rows_sorted)
        block_counts["ECONOMIC_EVALUATED"] += len(assessments)

        for assessment in assessments:
            block_counts[
                f"ECONOMIC_DISPOSITION_{assessment.disposition}"
            ] += 1
            block_counts[
                f"ECONOMIC_SIZING_MODE_{assessment.sizing_mode}"
            ] += 1
            if assessment.legacy_prefilter_would_drop:
                block_counts["LEGACY_PREFILTER_WOULD_DROP"] += 1
                block_counts["LEGACY_PREFILTER_RECOVERED_BASE_1X"] += 1

        order = sorted(
            range(len(rows_sorted)),
            key=lambda index: (
                -velocities[index],
                -assessments[index].expected_net_usd,
                str(rows_sorted[index]["signal_fingerprint"]),
            ),
        )

        for row_index in order:
            row = rows_sorted[row_index]
            extra = int(extra_combo[row_index])
            total_multiplier = 1 + extra
            minimum_volume = d(row["minimum_volume"])
            maximum_volume = d(row["maximum_volume"])
            volume = minimum_volume * Decimal(total_multiplier)
            if volume > maximum_volume:
                raise ValueError(
                    "economic intensification exceeds Trader executable maximum"
                )

            stop_per_volume = d(row["stop_loss_per_volume"])
            cost_per_volume = d(row["provider_cost_per_volume_usd"])
            margin_per_volume = d(row["margin_per_volume"])
            if stop_per_volume <= 0 or margin_per_volume <= 0:
                raise ValueError(
                    "executed Trader base entry has invalid economic geometry"
                )

            risk = volume * stop_per_volume
            margin = volume * margin_per_volume
            cost = volume * cost_per_volume
            outcome = row["settlement"]
            if (
                bool(outcome["used_for_decision"])
                or not bool(outcome["not_available_to_predecision"])
            ):
                raise ValueError("same-trade outcome leakage detected")

            dep = Deployment(
                signal=str(row["signal_fingerprint"]),
                trader_id=str(row["trader_id"]),
                exit_at=str(outcome["exit_at"]),
                risk=risk,
                margin=margin,
                provider_cost=cost,
                gross_r=d(outcome["gross_structural_outcome_r"]),
                multiplier=total_multiplier,
                volume=volume,
                observation_count=int(
                    row.get("walk_forward_observation_count", 0)
                ),
                positive_blocks=int(
                    row.get("walk_forward_positive_block_count", 0)
                ),
                nonpositive_blocks=int(
                    row.get("walk_forward_nonpositive_block_count", 0)
                ),
                mad_r=d(row.get("walk_forward_mad_r", "0")),
                dispersion_r=d(row.get("walk_forward_dispersion_r", "0")),
                expected_net_min_usd=assessments[
                    row_index
                ].expected_net_usd,
                global_expected_r=d_or_zero(
                    row.get("walk_forward_expected_structural_r")
                ),
                recent_block_r=d_or_zero(
                    (
                        row.get("walk_forward_block_means_r")
                        if isinstance(
                            row.get("walk_forward_block_means_r"),
                            list,
                        )
                        and row.get("walk_forward_block_means_r")
                        else [None]
                    )[-1]
                ),
            )
            sequence += 1
            heapq.heappush(pending, (dep.exit_at, sequence, dep))
            open_risk += risk
            open_margin += margin
            provider_reserve += cost
            multiplier_counts[str(total_multiplier)] += 1
            block_counts[f"ADDITIONAL_EXPOSURE_{extra}X"] += 1

    settle_until(None)

    if len(settlements) != len(rows):
        raise ValueError(
            "CIBO admission-authority violation: every Trader base entry must "
            "remain present through economic management"
        )
    if block_counts["TRADER_BASE_1X_MANAGED"] != len(rows):
        raise ValueError("CIBO base-management invariant failed")

    return _metrics(
        settlements,
        peak=peak,
        ending=capital,
        max_dd=max_dd,
        multiplier_counts=multiplier_counts,
        block_counts=block_counts,
    )


def run(prepared_path: Path, lane: str) -> dict[str, Any]:
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    if prepared.get("schema") != "qore.github-trader-lab.cibo-capital-prepared.v1":
        raise ValueError("unexpected CIBO prepared ledger schema")
    rows = prepared["rows"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("prepared CIBO rows missing")

    raw = {variant.name: simulate(rows, variant) for variant in VARIANTS}
    control = raw["TRADER_BASE_1X_CONTROL"]
    control_count = int(control["trade_count"])
    control_winners = sum(d(value) > 0 for value in control["net_r_values"])
    control_winner_r = sum(
        (d(value) for value in control["net_r_values"] if d(value) > 0),
        ZERO,
    )

    variants: dict[str, Any] = {}
    for name, row in raw.items():
        count = int(row["trade_count"])
        winner_count = sum(d(value) > 0 for value in row["net_r_values"])
        winner_r = sum(
            (d(value) for value in row["net_r_values"] if d(value) > 0),
            ZERO,
        )
        row["relative_density_vs_control"] = format(
            ZERO if control_count == 0 else Decimal(count) / Decimal(control_count),
            "f",
        )
        row["winner_preservation"] = {
            "count": format(
                ONE
                if control_winners == 0
                else Decimal(winner_count) / Decimal(control_winners),
                "f",
            ),
            "r": format(
                ONE
                if control_winner_r == 0
                else winner_r / control_winner_r,
                "f",
            ),
        }
        if count != len(rows):
            raise ValueError(
                f"{name}: CIBO cannot reject Trader base entries "
                f"({count} != {len(rows)})"
            )
        variants[name] = row

    return {
        "schema": "qore.github-trader-lab.normalized-replay.v2",
        "adapter": "cibo-post-entry-economic-management-fast-v2",
        "subject": "CIBO",
        "lane": lane,
        "control": "TRADER_BASE_1X_CONTROL",
        "variants": variants,
        "governance": {
            "burned_repair_window_only": True,
            "prepared_causal_ledger_reused": True,
            "max_frontier_policy_loaded_from_current_subject": True,
            "max_frontier_constraining_only": True,
            "trader_base_1x_is_already_executed": True,
            "cibo_has_no_entry_admission_authority": True,
            "cibo_controls_incremental_exposure_only": True,
            "economic_increment_space": "0..3x_above_mandatory_base_1x",
            "native_opportunities_route_to_economy_after_base_execution": True,
            "context_edge_provider_are_increment_modifiers_not_entry_gates": True,
            "base_entry_rejection_count": 0,
            "outcome_available_to_same_decision": False,
            "trader_methodology_changed": False,
            "fresh_holdout_opened": False,
            "certification_claimed": False,
            "sovereign_workflow_modified": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = run(args.prepared, args.lane)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    headline = {
        name: row["capital_path"]
        for name, row in payload["variants"].items()
    }
    print(
        "QORE_CIBO_FAST_CAPITAL_PATH "
        + json.dumps(headline, sort_keys=True),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
