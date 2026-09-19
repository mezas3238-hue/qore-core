"""VT08 Index R18 — formation-quality weighted dual-window governor.

R18 preserves every R8 2.5R execution in both consumed development windows.
Risk is allocated from pre-entry formation-quality patterns that R17 found
positive in BOTH windows. A finite rolling drawdown governor may reduce risk,
but risk is never zero and the minimum possible effective weight is 0.025.

The SAME scheme must pass 5Y and recent-2Y simultaneously.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import deque
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

SCHEMA = "qore.trader_lab.vt08_index_r18_formation_quality_dual_governor.v1"
IDENTITY = "VT08_INDEX_R18_FORMATION_QUALITY_DUAL_GOVERNOR_001"
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
MIN_EFFECTIVE_WEIGHT = Decimal("0.025")


@dataclass(frozen=True, slots=True)
class QualityScheme:
    base_weight: Decimal
    tier_b_weight: Decimal
    tier_c_weight: Decimal
    rolling_trades: int
    warn_dd_r: Decimal
    warn_multiplier: Decimal
    hard_dd_r: Decimal
    hard_multiplier: Decimal

    @property
    def scheme_id(self) -> str:
        return (
            "R18-"
            f"BASE{self.base_weight}-B{self.tier_b_weight}-C{self.tier_c_weight}-"
            f"W{self.rolling_trades}-"
            f"D{self.warn_dd_r}x{self.warn_multiplier}-"
            f"H{self.hard_dd_r}x{self.hard_multiplier}"
        )

    def payload(self) -> dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "base_weight": str(self.base_weight),
            "tier_a_weight": "1.0",
            "tier_b_weight": str(self.tier_b_weight),
            "tier_c_weight": str(self.tier_c_weight),
            "rolling_trades": self.rolling_trades,
            "warn_dd_r": str(self.warn_dd_r),
            "warn_multiplier": str(self.warn_multiplier),
            "hard_dd_r": str(self.hard_dd_r),
            "hard_multiplier": str(self.hard_multiplier),
        }


def _schemes() -> tuple[QualityScheme, ...]:
    rows: list[QualityScheme] = []
    for (
        base,
        tier_b,
        tier_c,
        rolling,
        warn_dd,
        warn_mult,
        hard_dd,
    ) in itertools.product(
        (Decimal("0.10"), Decimal("0.15"), Decimal("0.20")),
        (Decimal("0.50"), Decimal("0.75"), Decimal("1.00")),
        (Decimal("0.25"), Decimal("0.50")),
        (40, 60),
        (Decimal("1.50"), Decimal("2.00")),
        (Decimal("0.50"), Decimal("0.75")),
        (Decimal("3.00"), Decimal("4.00")),
    ):
        if hard_dd <= warn_dd:
            continue
        rows.append(
            QualityScheme(
                base_weight=base,
                tier_b_weight=tier_b,
                tier_c_weight=tier_c,
                rolling_trades=rolling,
                warn_dd_r=warn_dd,
                warn_multiplier=warn_mult,
                hard_dd_r=hard_dd,
                hard_multiplier=Decimal("0.25"),
            )
        )
    return tuple(rows)


def _quality_weight(
    opportunity: r4.ExpandedOpportunity,
    scheme: QualityScheme,
) -> Decimal:
    features = r17._feature_values(opportunity)
    weight = scheme.base_weight

    # Tier C: cross-window stable but modest edge.
    if (
        features["poi"] == "fvg"
        and features["risk_fraction"] == "0.15-0.30%"
    ):
        weight = max(weight, scheme.tier_c_weight)

    # Tier B: stronger cross-window confirmation-latency edge.
    if features["poi"] == "fvg" and features["cisd_latency"] == "4-7":
        weight = max(weight, scheme.tier_b_weight)

    # Tier A: strongest R17 cross-window cohort.
    if (
        features["poi"] == "fvg"
        and features["h4_entry_latency"] == "121-180m"
    ):
        weight = Decimal("1")

    return weight


def _weighted_values(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    scheme: QualityScheme,
    stress: Decimal,
) -> tuple[tuple[Decimal, ...], dict[str, Any]]:
    equity = Decimal()
    history: deque[Decimal] = deque(
        [Decimal()],
        maxlen=scheme.rolling_trades + 1,
    )
    values: list[Decimal] = []
    weights: list[Decimal] = []
    tier_a = 0
    tier_b = 0
    tier_c = 0
    warn_trades = 0
    hard_trades = 0

    for opportunity, outcome in stream:
        features = r17._feature_values(opportunity)
        base = _quality_weight(opportunity, scheme)
        if (
            features["poi"] == "fvg"
            and features["h4_entry_latency"] == "121-180m"
        ):
            tier_a += 1
        elif features["poi"] == "fvg" and features["cisd_latency"] == "4-7":
            tier_b += 1
        elif (
            features["poi"] == "fvg"
            and features["risk_fraction"] == "0.15-0.30%"
        ):
            tier_c += 1

        rolling_peak = max(history)
        dd_before = rolling_peak - equity
        multiplier = Decimal("1")
        if dd_before >= scheme.hard_dd_r:
            multiplier = scheme.hard_multiplier
            hard_trades += 1
        elif dd_before >= scheme.warn_dd_r:
            multiplier = scheme.warn_multiplier
            warn_trades += 1

        weight = base * multiplier
        if weight < MIN_EFFECTIVE_WEIGHT:
            raise ValueError(
                f"effective weight {weight} below guard {MIN_EFFECTIVE_WEIGHT}"
            )

        value = (outcome.r_multiple - stress) * weight
        values.append(value)
        weights.append(weight)
        equity += value
        history.append(equity)

    return tuple(values), {
        "minimum_weight": str(min(weights)),
        "maximum_weight": str(max(weights)),
        "mean_weight": str(sum(weights, Decimal()) / len(weights)),
        "zero_weight_trades": sum(weight == 0 for weight in weights),
        "tier_a_trades": tier_a,
        "tier_b_trades": tier_b,
        "tier_c_trades": tier_c,
        "warn_trades": warn_trades,
        "hard_trades": hard_trades,
    }


def _window(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    scheme: QualityScheme,
) -> dict[str, Any]:
    primary_values, primary_diag = _weighted_values(
        stream,
        scheme=scheme,
        stress=PRIMARY_STRESS,
    )
    secondary_values, secondary_diag = _weighted_values(
        stream,
        scheme=scheme,
        stress=SECONDARY_STRESS,
    )
    return {
        "sample": len(stream),
        "primary": fx._metrics(primary_values),
        "secondary": fx._metrics(secondary_values),
        "primary_diagnostics": primary_diag,
        "secondary_diagnostics": secondary_diag,
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


def _rank(
    row: dict[str, Any],
) -> tuple[int, int, Decimal, Decimal, Decimal]:
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
        int(bool(row["recent_two_year_pass"])),
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
            "minimum_effective_weight": str(MIN_EFFECTIVE_WEIGHT),
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
            "all_trades_preserved": True,
            "zero_risk_allowed": False,
            "minimum_effective_weight_guard": str(MIN_EFFECTIVE_WEIGHT),
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
