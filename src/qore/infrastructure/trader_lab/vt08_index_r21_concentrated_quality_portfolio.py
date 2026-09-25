"""VT08 Index R21 — concentrated static formation-quality portfolio.

R21 refines R20 without changing entries, exits, or using PnL state. The only
degree of freedom is static non-zero risk assigned to the three R17 formation
quality cohorts that were positive in BOTH consumed windows.

Tier A is no longer forced to 1R; this allows the portfolio drawdown target to
be achieved by a fixed pre-entry risk contract rather than a reactive governor.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r15_dual_window_gate as r15
from qore.infrastructure.trader_lab import vt08_index_r17_formation_quality_forensics as r17

SCHEMA = "qore.trader_lab.vt08_index_r21_concentrated_quality_portfolio.v1"
IDENTITY = "VT08_INDEX_R21_CONCENTRATED_QUALITY_PORTFOLIO_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_MIN = Decimal("1.50")
DD_MAX = Decimal("6")
SECONDARY_PF_MIN = Decimal("1.30")
SECONDARY_DD_MAX = Decimal("8")
FIVE_YEAR_MIN_TRADES = 1500
FIVE_YEAR_MAX_TRADES = 1600
TWO_YEAR_MIN_TRADES = 600
TWO_YEAR_MAX_TRADES = 700
MIN_WEIGHT = Decimal("0.005")


@dataclass(frozen=True, slots=True)
class QualityScheme:
    base_weight: Decimal
    tier_a_weight: Decimal
    tier_b_weight: Decimal
    tier_c_weight: Decimal

    @property
    def scheme_id(self) -> str:
        return (
            "R21-"
            f"BASE{self.base_weight}-A{self.tier_a_weight}-"
            f"B{self.tier_b_weight}-C{self.tier_c_weight}"
        )

    def payload(self) -> dict[str, str]:
        return {
            "scheme_id": self.scheme_id,
            "base_weight": str(self.base_weight),
            "tier_a_weight": str(self.tier_a_weight),
            "tier_b_weight": str(self.tier_b_weight),
            "tier_c_weight": str(self.tier_c_weight),
            "minimum_weight": str(MIN_WEIGHT),
        }


def _schemes() -> tuple[QualityScheme, ...]:
    return tuple(
        QualityScheme(base, tier_a, tier_b, tier_c)
        for base, tier_a, tier_b, tier_c in itertools.product(
            (Decimal("0.005"), Decimal("0.01")),
            (Decimal("0.50"), Decimal("0.75"), Decimal("1.00")),
            (Decimal("0.10"), Decimal("0.25"), Decimal("0.50")),
            (
                Decimal("0.025"),
                Decimal("0.05"),
                Decimal("0.10"),
                Decimal("0.25"),
            ),
        )
    )


def _weight(
    opportunity: r4.ExpandedOpportunity,
    scheme: QualityScheme,
) -> Decimal:
    features = r17._feature_values(opportunity)
    weight = scheme.base_weight

    if (
        features["poi"] == "fvg"
        and features["risk_fraction"] == "0.15-0.30%"
    ):
        weight = max(weight, scheme.tier_c_weight)

    if features["poi"] == "fvg" and features["cisd_latency"] == "4-7":
        weight = max(weight, scheme.tier_b_weight)

    if (
        features["poi"] == "fvg"
        and features["h4_entry_latency"] == "121-180m"
    ):
        weight = max(weight, scheme.tier_a_weight)

    if weight < MIN_WEIGHT:
        raise ValueError(f"weight {weight} below minimum {MIN_WEIGHT}")
    return weight


def _window(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    scheme: QualityScheme,
) -> dict[str, Any]:
    primary_values: list[Decimal] = []
    secondary_values: list[Decimal] = []
    weights: list[Decimal] = []
    tiers = {"tier_a": 0, "tier_b": 0, "tier_c": 0, "base": 0}

    for opportunity, outcome in stream:
        features = r17._feature_values(opportunity)
        weight = _weight(opportunity, scheme)
        weights.append(weight)

        if (
            features["poi"] == "fvg"
            and features["h4_entry_latency"] == "121-180m"
        ):
            tiers["tier_a"] += 1
        elif features["poi"] == "fvg" and features["cisd_latency"] == "4-7":
            tiers["tier_b"] += 1
        elif (
            features["poi"] == "fvg"
            and features["risk_fraction"] == "0.15-0.30%"
        ):
            tiers["tier_c"] += 1
        else:
            tiers["base"] += 1

        primary_values.append((outcome.r_multiple - PRIMARY_STRESS) * weight)
        secondary_values.append((outcome.r_multiple - SECONDARY_STRESS) * weight)

    return {
        "sample": len(stream),
        "primary": fx._metrics(tuple(primary_values)),
        "secondary": fx._metrics(tuple(secondary_values)),
        "diagnostics": {
            "minimum_weight": str(min(weights)),
            "maximum_weight": str(max(weights)),
            "mean_weight": str(sum(weights, Decimal()) / len(weights)),
            "zero_weight_trades": sum(weight == 0 for weight in weights),
            **tiers,
        },
    }


def _metric_pass(
    row: dict[str, Any],
    *,
    pf_min: Decimal,
    dd_max: Decimal,
) -> bool:
    return (
        Decimal(str(row["total_r"])) > 0
        and Decimal(str(row["profit_factor"] or "0")) >= pf_min
        and Decimal(str(row["max_drawdown_r"])) <= dd_max
    )


def _candidate(
    five_stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    two_stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    scheme: QualityScheme,
) -> dict[str, Any]:
    five = _window(five_stream, scheme=scheme)
    two = _window(two_stream, scheme=scheme)

    five_density = FIVE_YEAR_MIN_TRADES <= int(five["sample"]) <= FIVE_YEAR_MAX_TRADES
    two_density = TWO_YEAR_MIN_TRADES <= int(two["sample"]) <= TWO_YEAR_MAX_TRADES

    five_pass = (
        five_density
        and _metric_pass(five["primary"], pf_min=PF_MIN, dd_max=DD_MAX)
        and _metric_pass(
            five["secondary"],
            pf_min=SECONDARY_PF_MIN,
            dd_max=SECONDARY_DD_MAX,
        )
    )
    two_pass = (
        two_density
        and _metric_pass(two["primary"], pf_min=PF_MIN, dd_max=DD_MAX)
        and _metric_pass(
            two["secondary"],
            pf_min=SECONDARY_PF_MIN,
            dd_max=SECONDARY_DD_MAX,
        )
    )
    return {
        "scheme": scheme.payload(),
        "five_year": five,
        "recent_two_year": two,
        "five_year_pass": five_pass,
        "recent_two_year_pass": two_pass,
        "dual_window_pass": five_pass and two_pass,
    }


def _rank(row: dict[str, Any]) -> tuple[int, int, Decimal, Decimal, Decimal]:
    five = row["five_year"]["primary"]
    two = row["recent_two_year"]["primary"]
    min_pf = min(
        Decimal(str(five["profit_factor"] or "0")),
        Decimal(str(two["profit_factor"] or "0")),
    )
    worst_dd = max(
        Decimal(str(five["max_drawdown_r"])),
        Decimal(str(two["max_drawdown_r"])),
    )
    return (
        int(bool(row["dual_window_pass"])),
        int(bool(row["five_year_pass"]) + bool(row["recent_two_year_pass"])),
        min_pf,
        -worst_dd,
        Decimal(str(five["total_r"])) + Decimal(str(two["total_r"])),
    )


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, _five_contexts, five_provenance = r15._five_year_stream(roots)
    two_stream, _two_contexts, two_provenance = r15._two_year_stream(roots)

    rows = [
        _candidate(five_stream, two_stream, scheme=scheme)
        for scheme in _schemes()
    ]
    rows.sort(key=_rank, reverse=True)
    goals = [row for row in rows if bool(row["dual_window_pass"])]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "contract": {
            "five_year_density": [FIVE_YEAR_MIN_TRADES, FIVE_YEAR_MAX_TRADES],
            "two_year_density": [TWO_YEAR_MIN_TRADES, TWO_YEAR_MAX_TRADES],
            "primary_pf_minimum": str(PF_MIN),
            "primary_dd_max_r": str(DD_MAX),
            "secondary_pf_minimum": str(SECONDARY_PF_MIN),
            "secondary_dd_max_r": str(SECONDARY_DD_MAX),
            "minimum_weight": str(MIN_WEIGHT),
            "same_scheme_required_both_windows": True,
        },
        "scheme_count": len(rows),
        "dual_window_candidate_count": len(goals),
        "best": rows[0],
        "top_20": rows[:20],
        "dual_window_candidates": goals[:20],
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "development_only": True,
            "r17_cross_window_features_only": True,
            "static_pre_entry_risk_only": True,
            "all_trades_preserved": True,
            "zero_risk_allowed": False,
            "same_rules_both_windows": True,
            "both_windows_consumed": True,
            "fresh_holdout_claim": False,
            "candidate_promoted": False,
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
                "scheme_count": report["scheme_count"],
                "dual_window_candidate_count": report["dual_window_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
