"""VT08 Index R61 — independent reproduction, stability and leakage audit.

R61 independently reconstructs the frozen R58 candidate from the R59
specification. The canonical R58/R55 rule application is used only for final
ledger comparison.

The audit also checks:
- material-risk cohort stability by market, side, anchor, POI and rearm state;
- chronological-half stability;
- realized daily PnL dependence across NAS100/SP500/US30;
- portfolio concurrency / committed-risk invariants;
- causal timestamp ordering and source-level leakage guards.

All evidence windows are consumed development evidence. R61 cannot create
fresh-holdout, DEMO, LIVE, production or real-capital authority.
"""

from __future__ import annotations

import argparse
import heapq
import inspect
import json
import math
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r17_formation_quality_forensics as r17,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r22_concurrent_stable_formation as r22,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r34_hybrid_formation_poi_health as r34,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r43_sp500_long_stability_prior as r43,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r50_independent_reproduction as r50,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r53_cisd_reaction_quality_forensics as r53,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as canonical_overlay,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r61_independent_stability_audit.v1"
IDENTITY = "VT08_INDEX_R61_R58_INDEPENDENT_STABILITY_AUDIT_001"
CANDIDATE_ID = freeze.CANDIDATE_ID
CANDIDATE_RULE_FINGERPRINT = freeze.CANDIDATE_RULE_FINGERPRINT

SECONDARY_STRESS = Decimal("0.10")
MAX_REQUESTED_WEIGHT = Decimal("0.25")
REARM_MIN_WEIGHT = Decimal("0.10")
SUPPORTED_FVG_MIN_WEIGHT = Decimal("0.25")
LATE_REVALIDATION_MIN_WEIGHT = Decimal("0.25")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")
PORTFOLIO_BUDGET_R = Decimal("0.75")

MATERIAL_COHORT_MIN_SAMPLE = 30
MATERIAL_COHORT_MIN_MEAN_WEIGHT = Decimal("0.05")
MATERIAL_COHORT_MIN_PF = Decimal("1.00")

SOURCE_R60_RUN_ID = 35460660236
SOURCE_R60_ARTIFACT_ID = 10589738798
SOURCE_R60_ARTIFACT_DIGEST = (
    "sha256:14339ddd43fb3ca374a20294d7ed3ed2a310a2c52d33da0627c2217fc6226911"
)
_NY = ZoneInfo("America/New_York")


def dependency_contract_matches() -> bool:
    rules = freeze.r58.RULES
    return (
        freeze.dependency_contract_matches()
        and str(rules["max_requested_weight_r"]) == str(MAX_REQUESTED_WEIGHT)
        and str(rules["non_demoted_rearm_min_weight_r"]) == str(REARM_MIN_WEIGHT)
        and str(
            rules["fvg_cross_index_unanimous_with_side_min_weight_r"]
        )
        == str(SUPPORTED_FVG_MIN_WEIGHT)
        and str(rules["fvg_h4_121_180_and_cisd_4_7_min_weight_r"])
        == str(SUPPORTED_FVG_MIN_WEIGHT)
        and str(rules["late_cisd_revalidation_min_weight_r"])
        == str(LATE_REVALIDATION_MIN_WEIGHT)
        and str(rules["portfolio_budget_r"]) == str(PORTFOLIO_BUDGET_R)
        and str(rules["minimum_effective_weight_r"]) == str(MIN_EFFECTIVE_WEIGHT)
        and rules["signals_suppressed"] is False
        and rules["calendar_or_year_runtime_feature"] is False
    )


def _reaction_bars(
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[
    dict[str, tuple[r53.journey.Bar, ...]],
    dict[str, tuple[datetime, ...]],
]:
    converted = {
        symbol: r53._as_reaction_bars(tuple(bars))
        for symbol, bars in bars_by_symbol.items()
    }
    opened = {
        symbol: tuple(bar.opened_at for bar in bars)
        for symbol, bars in converted.items()
    }
    return converted, opened


def _independent_late_revalidation(
    item: r15.AssignedTrade,
    *,
    bars: Sequence[r53.journey.Bar],
    opened: Sequence[datetime],
) -> tuple[bool, int]:
    opportunity = item.opportunity
    signal_at = opportunity.signal.signal_at.astimezone(UTC)
    cisd_at = opportunity.signal.cisd_confirmed_at.astimezone(UTC)
    causal_violations = int(cisd_at > signal_at)
    if str(opportunity.source_poi_kind) != "cisd":
        return False, causal_violations
    if r17._bucket_continuation_latency(opportunity) != "5+":
        return False, causal_violations

    context = r53._reaction_context(
        item,
        bars=bars,
        opened=opened,
    )
    if not bool(context["fresh_liquidity_take_15m"]):
        return False, causal_violations
    raw_reaction_at = context.get("reaction_at")
    if raw_reaction_at is None:
        return False, causal_violations
    reaction_at = datetime.fromisoformat(
        str(raw_reaction_at).replace("Z", "+00:00")
    )
    if reaction_at.tzinfo is None:
        reaction_at = reaction_at.replace(tzinfo=UTC)
    reaction_utc = reaction_at.astimezone(UTC)
    causal_violations += int(reaction_utc > signal_at)
    return (
        cisd_at < reaction_utc <= signal_at,
        causal_violations,
    )


def _independent_requested_weight(
    item: r15.AssignedTrade,
    *,
    h4_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    reaction_bars: dict[str, tuple[r53.journey.Bar, ...]],
    reaction_opened: dict[str, tuple[datetime, ...]],
) -> tuple[Decimal, tuple[str, ...], int]:
    opportunity = item.opportunity
    signal = opportunity.signal
    r47_labels = r50._independent_labels(
        item,
        h4_by_symbol=h4_by_symbol,
    )
    requested = min(item.weight, MAX_REQUESTED_WEIGHT)
    labels: list[str] = []
    causal_violations = int(
        signal.cisd_confirmed_at.astimezone(UTC)
        > signal.signal_at.astimezone(UTC)
    )

    if r47_labels:
        return (
            requested,
            tuple(f"R47:{label}" for label in r47_labels),
            causal_violations,
        )

    if int(opportunity.rearm_index) > 0:
        requested = max(requested, REARM_MIN_WEIGHT)
        labels.append("STRUCTURAL_REARM")

    if str(opportunity.source_poi_kind) == "fvg":
        cross_state = r50._independent_cross_index_state(
            h4_by_symbol=h4_by_symbol,
            decision=signal.signal_at,
            side=signal.side,
        )
        if cross_state == "unanimous_with_side":
            requested = max(requested, SUPPORTED_FVG_MIN_WEIGHT)
            labels.append("FVG_CROSS_INDEX_UNANIMOUS_WITH_SIDE")

        if (
            r17._bucket_h4_entry_latency(opportunity) == "121-180m"
            and r17._bucket_cisd_latency(opportunity) == "4-7"
        ):
            requested = max(requested, SUPPORTED_FVG_MIN_WEIGHT)
            labels.append("FVG_H4_121_180_CISD_4_7")

    late, violations = _independent_late_revalidation(
        item,
        bars=reaction_bars[item.symbol],
        opened=reaction_opened[item.symbol],
    )
    causal_violations += violations
    if late:
        requested = max(requested, LATE_REVALIDATION_MIN_WEIGHT)
        labels.append("CISD_LATE_REVALIDATION")

    return (
        max(MIN_EFFECTIVE_WEIGHT, requested),
        tuple(labels),
        causal_violations,
    )


def _independent_overlay(
    baseline: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, object]]:
    h4_by_symbol = {
        symbol: v6._build_h4(
            {
                bar.opened_at.astimezone(UTC): bar
                for bar in bars
            }
        )
        for symbol, bars in bars_by_symbol.items()
    }
    reaction_bars, reaction_opened = _reaction_bars(bars_by_symbol)
    ordered = sorted(
        baseline,
        key=lambda item: (
            item.opportunity.signal.signal_at.astimezone(UTC),
            item.symbol,
            item.trade_id,
        ),
    )

    active: dict[int, Decimal] = {}
    exit_heap: list[tuple[datetime, int]] = []
    assigned: list[r15.AssignedTrade] = []
    cursor = 0
    next_trade_id = 0

    rule_hits = {
        "STRUCTURAL_REARM": 0,
        "FVG_CROSS_INDEX_UNANIMOUS_WITH_SIDE": 0,
        "FVG_H4_121_180_CISD_4_7": 0,
        "CISD_LATE_REVALIDATION": 0,
        "R47_DEMOTION": 0,
    }
    budget_scaled_batches = 0
    floor_overage_batches = 0
    max_committed = Decimal()
    max_concurrent = 0
    causal_violations = 0

    def settle(until: datetime) -> None:
        while exit_heap and exit_heap[0][0] <= until:
            _exit_at, trade_id = heapq.heappop(exit_heap)
            active.pop(trade_id, None)

    while cursor < len(ordered):
        batch_time = ordered[cursor].opportunity.signal.signal_at.astimezone(
            UTC
        )
        settle(batch_time)
        end = cursor + 1
        while (
            end < len(ordered)
            and ordered[end].opportunity.signal.signal_at.astimezone(UTC)
            == batch_time
        ):
            end += 1
        batch = ordered[cursor:end]

        requested: list[Decimal] = []
        labels_by_item: list[tuple[str, ...]] = []
        for item in batch:
            weight, labels, violations = _independent_requested_weight(
                item,
                h4_by_symbol=h4_by_symbol,
                reaction_bars=reaction_bars,
                reaction_opened=reaction_opened,
            )
            requested.append(weight)
            labels_by_item.append(labels)
            causal_violations += violations
            for label in labels:
                if label.startswith("R47:"):
                    rule_hits["R47_DEMOTION"] += 1
                else:
                    rule_hits[label] += 1

        active_risk = sum(active.values(), Decimal())
        weights, scaled = r22._allocate_batch(
            requested,
            active_risk=active_risk,
            budget=PORTFOLIO_BUDGET_R,
        )
        budget_scaled_batches += int(scaled)
        if active_risk + sum(weights, Decimal()) > PORTFOLIO_BUDGET_R:
            floor_overage_batches += 1

        for item, weight in zip(batch, weights, strict=True):
            replaced = r15.AssignedTrade(
                trade_id=next_trade_id,
                opportunity=item.opportunity,
                outcome=item.outcome,
                context=item.context,
                weight=weight,
            )
            next_trade_id += 1
            assigned.append(replaced)
            active[replaced.trade_id] = weight
            heapq.heappush(
                exit_heap,
                (
                    replaced.exited_at.astimezone(UTC),
                    replaced.trade_id,
                ),
            )

        max_concurrent = max(max_concurrent, len(active))
        max_committed = max(max_committed, sum(active.values(), Decimal()))
        cursor = end

    settle(datetime.max.replace(tzinfo=UTC))
    if len(assigned) != len(baseline):
        raise ValueError("R61 independent overlay changed source-complete count")
    if any(item.weight < MIN_EFFECTIVE_WEIGHT for item in assigned):
        raise ValueError("R61 independent overlay fell below risk floor")
    if any(item.weight > MAX_REQUESTED_WEIGHT for item in assigned):
        raise ValueError("R61 independent overlay exceeded weight cap")

    return tuple(assigned), {
        "assigned_trade_count": len(assigned),
        "suppressed_trade_count": 0,
        "budget_scaled_batches": budget_scaled_batches,
        "floor_overage_batches": floor_overage_batches,
        "max_concurrent_open_positions": max_concurrent,
        "max_committed_structural_risk_r": str(max_committed),
        "minimum_effective_weight": str(
            min(item.weight for item in assigned)
        ),
        "maximum_effective_weight": str(
            max(item.weight for item in assigned)
        ),
        "mean_effective_weight": str(
            sum((item.weight for item in assigned), Decimal())
            / len(assigned)
        ),
        "rule_hits": rule_hits,
        "causal_timestamp_violation_count": causal_violations,
    }


def _canonical_candidate(
    stream: Sequence[Any],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[r15.AssignedTrade, ...]:
    _base_row, baseline = r34._row(
        stream,
        overlay=r43.BASE_POI_OVERLAY,
    )
    r47_assigned, _r47_diagnostics = r47._apply_transport_rules(
        baseline,
        bars_by_symbol=bars_by_symbol,
    )
    candidate, _diagnostics = canonical_overlay._apply_candidate(
        r47_assigned,
        bars_by_symbol=bars_by_symbol,
    )
    return candidate


def _independent_candidate(
    stream: Sequence[Any],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, object]]:
    _base_row, baseline = r34._row(
        stream,
        overlay=r43.BASE_POI_OVERLAY,
    )
    independent_r47, _r47_diagnostics = r50._independent_apply(
        baseline,
        bars_by_symbol=bars_by_symbol,
    )
    return _independent_overlay(
        independent_r47,
        bars_by_symbol=bars_by_symbol,
    )


def _ledger_rows(
    assigned: Sequence[r15.AssignedTrade],
) -> list[dict[str, object]]:
    return [
        {
            "trade_id": item.trade_id,
            "symbol": item.symbol,
            "signal_at": item.signal_at.astimezone(UTC).isoformat(),
            "exited_at": item.exited_at.astimezone(UTC).isoformat(),
            "side": item.opportunity.signal.side.value,
            "poi": str(item.opportunity.source_poi_kind),
            "rearm_index": int(item.opportunity.rearm_index),
            "weight": str(item.weight),
            "outcome_r": str(item.outcome.r_multiple),
        }
        for item in assigned
    ]


def _ledger_fingerprint(
    assigned: Sequence[r15.AssignedTrade],
) -> str:
    return sha256(
        json.dumps(
            _ledger_rows(assigned),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _canonical_match(
    independent: Sequence[r15.AssignedTrade],
    canonical: Sequence[r15.AssignedTrade],
) -> dict[str, object]:
    if len(independent) != len(canonical):
        return {
            "pass": False,
            "mismatch_count": abs(len(independent) - len(canonical)),
            "first_mismatch": "length",
        }
    mismatches: list[dict[str, object]] = []
    for left, right in zip(independent, canonical, strict=True):
        if (
            left.trade_id != right.trade_id
            or left.symbol != right.symbol
            or left.signal_at != right.signal_at
            or left.exited_at != right.exited_at
            or left.weight != right.weight
            or left.outcome.r_multiple != right.outcome.r_multiple
        ):
            mismatches.append(
                {
                    "trade_id_independent": left.trade_id,
                    "trade_id_canonical": right.trade_id,
                    "symbol_independent": left.symbol,
                    "symbol_canonical": right.symbol,
                    "weight_independent": str(left.weight),
                    "weight_canonical": str(right.weight),
                }
            )
    return {
        "pass": not mismatches,
        "mismatch_count": len(mismatches),
        "first_mismatch": mismatches[0] if mismatches else None,
    }


def _secondary_metrics(
    items: Sequence[r15.AssignedTrade],
) -> dict[str, Any]:
    return fx._metrics(
        r15._realized_values(tuple(items), stress=SECONDARY_STRESS)
    )


def _dimension_value(
    item: r15.AssignedTrade,
    dimension: str,
) -> str:
    if dimension == "symbol":
        return item.symbol
    if dimension == "side":
        return item.opportunity.signal.side.value
    if dimension == "anchor":
        return str(
            item.opportunity.signal.h4_opened_at.astimezone(_NY).hour
        )
    if dimension == "poi":
        return str(item.opportunity.source_poi_kind)
    if dimension == "rearm":
        return "REARM" if int(item.opportunity.rearm_index) > 0 else "INITIAL"
    raise ValueError(f"unsupported R61 stability dimension: {dimension}")


def _stability(
    assigned: Sequence[r15.AssignedTrade],
) -> dict[str, object]:
    dimensions = ("symbol", "side", "anchor", "poi", "rearm")
    output: dict[str, object] = {}
    material_failures: list[str] = []

    for dimension in dimensions:
        groups: dict[str, list[r15.AssignedTrade]] = defaultdict(list)
        for item in assigned:
            groups[_dimension_value(item, dimension)].append(item)
        rows: dict[str, object] = {}
        for label, items in sorted(groups.items()):
            metrics = _secondary_metrics(items)
            mean_weight = (
                sum((item.weight for item in items), Decimal())
                / len(items)
            )
            material = (
                len(items) >= MATERIAL_COHORT_MIN_SAMPLE
                and mean_weight >= MATERIAL_COHORT_MIN_MEAN_WEIGHT
            )
            cohort_pass = (
                not material
                or (
                    Decimal(str(metrics["total_r"])) > 0
                    and Decimal(str(metrics["profit_factor"] or "0"))
                    >= MATERIAL_COHORT_MIN_PF
                )
            )
            if not cohort_pass:
                material_failures.append(f"{dimension}:{label}")
            rows[label] = {
                "sample": len(items),
                "mean_effective_weight": str(mean_weight),
                "material_risk_cohort": material,
                "secondary": metrics,
                "pass": cohort_pass,
            }
        output[dimension] = rows

    return {
        "material_definition": {
            "minimum_sample": MATERIAL_COHORT_MIN_SAMPLE,
            "minimum_mean_effective_weight_r": str(
                MATERIAL_COHORT_MIN_MEAN_WEIGHT
            ),
            "minimum_secondary_pf": str(MATERIAL_COHORT_MIN_PF),
            "positive_terminal_required": True,
        },
        "dimensions": output,
        "material_failure_labels": material_failures,
        "material_cohort_stability_pass": not material_failures,
    }


def _chronological_halves(
    assigned: Sequence[r15.AssignedTrade],
    *,
    midpoint: date,
) -> dict[str, object]:
    first = tuple(
        item
        for item in assigned
        if item.signal_at.astimezone(_NY).date() < midpoint
    )
    second = tuple(
        item
        for item in assigned
        if item.signal_at.astimezone(_NY).date() >= midpoint
    )
    first_metrics = _secondary_metrics(first)
    second_metrics = _secondary_metrics(second)
    return {
        "midpoint": midpoint.isoformat(),
        "first": first_metrics,
        "second": second_metrics,
        "pass": (
            Decimal(str(first_metrics["total_r"])) > 0
            and Decimal(str(second_metrics["total_r"])) > 0
        ),
    }


def _pearson(
    left: Sequence[float],
    right: Sequence[float],
) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (a - left_mean) * (b - right_mean)
        for a, b in zip(left, right, strict=True)
    )
    left_var = sum((value - left_mean) ** 2 for value in left)
    right_var = sum((value - right_mean) ** 2 for value in right)
    denominator = math.sqrt(left_var * right_var)
    if denominator == 0:
        return None
    return numerator / denominator


def _daily_dependence(
    assigned: Sequence[r15.AssignedTrade],
) -> dict[str, object]:
    daily: dict[str, dict[date, Decimal]] = {
        "NAS100": defaultdict(Decimal),
        "SP500": defaultdict(Decimal),
        "US30": defaultdict(Decimal),
    }
    for item in assigned:
        day = item.exited_at.astimezone(_NY).date()
        value = (
            item.outcome.r_multiple - SECONDARY_STRESS
        ) * item.weight
        daily[item.symbol][day] += value

    days = sorted(
        set().union(*(set(values) for values in daily.values()))
    )
    pairs: dict[str, object] = {}
    max_abs = 0.0
    symbols = ("NAS100", "SP500", "US30")
    for index, left_symbol in enumerate(symbols):
        for right_symbol in symbols[index + 1 :]:
            left = [
                float(daily[left_symbol].get(day, Decimal()))
                for day in days
            ]
            right = [
                float(daily[right_symbol].get(day, Decimal()))
                for day in days
            ]
            correlation = _pearson(left, right)
            if correlation is not None:
                max_abs = max(max_abs, abs(correlation))
            pairs[f"{left_symbol}|{right_symbol}"] = {
                "calendar_days": len(days),
                "zero_filled_daily_pnl": True,
                "correlation": correlation,
            }

    return {
        "method": "pearson-on-zero-filled-realized-daily-secondary-pnl",
        "pairs": pairs,
        "max_absolute_pairwise_correlation": max_abs,
        "descriptive_only": True,
    }


def _source_leakage_audit() -> dict[str, object]:
    functions: tuple[Callable[..., object], ...] = (
        canonical_overlay._requested_weight,
        canonical_overlay._late_revalidation,
    )
    forbidden = (
        "outcome.r_multiple",
        "exited_at",
        "datetime.now",
        "date.today",
        "random",
        "calendar_feature",
    )
    findings: list[dict[str, str]] = []
    for function in functions:
        source = inspect.getsource(function)
        for token in forbidden:
            if token in source:
                findings.append(
                    {
                        "function": function.__name__,
                        "token": token,
                    }
                )
    return {
        "functions_scanned": [function.__name__ for function in functions],
        "forbidden_tokens": list(forbidden),
        "findings": findings,
        "pass": not findings,
    }


def _window(
    *,
    stream: Sequence[Any],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    expected: dict[str, object],
    midpoint: date,
) -> dict[str, object]:
    independent, diagnostics = _independent_candidate(
        stream,
        bars_by_symbol=bars_by_symbol,
    )
    canonical = _canonical_candidate(
        stream,
        bars_by_symbol=bars_by_symbol,
    )
    match = _canonical_match(independent, canonical)
    secondary = _secondary_metrics(independent)
    exact_economics = (
        len(independent) == int(str(expected["sample"]))
        and Decimal(str(secondary["profit_factor"]))
        == Decimal(str(expected["secondary_pf"]))
        and Decimal(str(secondary["total_r"]))
        == Decimal(str(expected["secondary_total_r"]))
    )
    stability = _stability(independent)
    halves = _chronological_halves(independent, midpoint=midpoint)
    dependence = _daily_dependence(independent)

    return {
        "sample": len(independent),
        "secondary": secondary,
        "independent_ledger_fingerprint": _ledger_fingerprint(independent),
        "canonical_ledger_fingerprint": _ledger_fingerprint(canonical),
        "canonical_match": match,
        "exact_frozen_economics": exact_economics,
        "independent_diagnostics": diagnostics,
        "stability": stability,
        "chronological_halves": halves,
        "dependence": dependence,
        "window_pass": (
            bool(match["pass"])
            and exact_economics
            and int(diagnostics["causal_timestamp_violation_count"]) == 0
            and bool(stability["material_cohort_stability_pass"])
            and bool(halves["pass"])
        ),
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    if not dependency_contract_matches():
        raise ValueError("R61 frozen R59/R58 dependency drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, _five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, _two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    five = _window(
        stream=five_stream,
        bars_by_symbol=five_bars,
        expected=freeze.FIVE_YEAR,
        midpoint=date(2021, 3, 15),
    )
    two = _window(
        stream=two_stream,
        bars_by_symbol=two_bars,
        expected=freeze.RECENT_TWO_YEAR,
        midpoint=date(2025, 9, 15),
    )
    leakage = _source_leakage_audit()
    independent_validation_pass = (
        bool(five["window_pass"])
        and bool(two["window_pass"])
        and bool(leakage["pass"])
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": CANDIDATE_ID,
            "rule_fingerprint": CANDIDATE_RULE_FINGERPRINT,
            "freeze_id": freeze.FREEZE_ID,
            "candidate_modified": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "source_leakage_audit": leakage,
        "independent_validation_pass": independent_validation_pass,
        "decision": (
            "PASS_R61_INDEPENDENT_STABILITY_AUDIT"
            if independent_validation_pass
            else "FAIL_R61_RETURN_TO_LAB"
        ),
        "source_evidence": {
            "r60_core_robustness": {
                "run_id": SOURCE_R60_RUN_ID,
                "artifact_id": SOURCE_R60_ARTIFACT_ID,
                "artifact_digest": SOURCE_R60_ARTIFACT_DIGEST,
            },
        },
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "independent_rule_application_implementation": True,
            "canonical_rule_application_used_for_comparison_only": True,
            "material_stability_gate_preregistered": True,
            "dependence_evidence_descriptive": True,
            "leakage_audit_required": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "candidate_retuned": False,
            "certified": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "five_year": report["five_year"],
                "recent_two_year": report["recent_two_year"],
                "source_leakage_audit": report["source_leakage_audit"],
                "independent_validation_pass": report[
                    "independent_validation_pass"
                ],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
