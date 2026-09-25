"""VT08 Index R10 — pre-entry contextual risk allocation.

Preserves the R8 2.5R execution stream and all trades. Risk allocation uses only
pre-entry structural context; it does not depend on prior PnL drawdown state.

The goal is to avoid R6's hard-mode lock-in while retaining 1500-1600 executed
trades. No trade may receive zero risk.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.trader_lab import vt08_index_v4_regime_forensics as v4
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r10_contextual_risk.v1"
IDENTITY = "VT08_INDEX_R10_CONTEXTUAL_RISK_001"
TARGET_R = Decimal("2.5")
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
MIN_TRADES = 1500
MAX_TRADES = 1600


@dataclass(frozen=True, slots=True)
class Context:
    previous_source_day_body_opposed: bool
    rearm: bool
    c2_expansion: bool
    short: bool


@dataclass(frozen=True, slots=True)
class RiskScheme:
    opposed_weight: Decimal
    aligned_weight: Decimal
    rearm_floor: Decimal
    c2_cap: Decimal
    short_cap: Decimal

    @property
    def scheme_id(self) -> str:
        return (
            "R10-"
            f"O{self.opposed_weight}-A{self.aligned_weight}-"
            f"R{self.rearm_floor}-C2{self.c2_cap}-S{self.short_cap}"
        )

    def weight(self, context: Context) -> Decimal:
        weight = (
            self.opposed_weight
            if context.previous_source_day_body_opposed
            else self.aligned_weight
        )
        if context.rearm:
            weight = max(weight, self.rearm_floor)
        if context.c2_expansion:
            weight = min(weight, self.c2_cap)
        if context.short:
            weight = min(weight, self.short_cap)
        if weight <= 0:
            raise ValueError("R10 never permits zero-risk trades")
        return weight

    def payload(self) -> dict[str, str]:
        return {
            "scheme_id": self.scheme_id,
            "opposed_weight": str(self.opposed_weight),
            "aligned_weight": str(self.aligned_weight),
            "rearm_floor": str(self.rearm_floor),
            "c2_cap": str(self.c2_cap),
            "short_cap": str(self.short_cap),
        }


def _schemes() -> tuple[RiskScheme, ...]:
    return (
        RiskScheme(Decimal("1"), Decimal("0.25"), Decimal("1"), Decimal("1"), Decimal("1")),
        RiskScheme(Decimal("1"), Decimal("0.10"), Decimal("1"), Decimal("1"), Decimal("1")),
        RiskScheme(Decimal("0.75"), Decimal("0.10"), Decimal("1"), Decimal("1"), Decimal("1")),
        RiskScheme(Decimal("1"), Decimal("0.10"), Decimal("1"), Decimal("0.25"), Decimal("1")),
        RiskScheme(Decimal("1"), Decimal("0.10"), Decimal("1"), Decimal("0.25"), Decimal("0.50")),
        RiskScheme(
            Decimal("0.75"),
            Decimal("0.10"),
            Decimal("1"),
            Decimal("0.25"),
            Decimal("0.50"),
        ),
    )


def _base_stream(
    *,
    opportunities_by_symbol: dict[str, tuple[r4.ExpandedOpportunity, ...]],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[tuple[r4.ExpandedOpportunity, r5.ManagedTrade], ...]:
    selected: list[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]] = []
    for symbol in ("NAS100", "SP500", "US30"):
        selected.extend(
            r8._sequential(
                opportunities_by_symbol[symbol],
                bars=bars_by_symbol[symbol],
                target=TARGET_R,
            )
        )
    selected.sort(
        key=lambda item: (item[0].signal.signal_at, item[0].signal.symbol)
    )
    return tuple(selected)


def _context(
    opportunity: r4.ExpandedOpportunity,
    *,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
) -> Context:
    signal = opportunity.signal
    source_days = v7._latest_complete_source_days(
        indexed,
        before_local=signal.h4_opened_at.astimezone(v5y._NY),
    )
    opposed = False
    if source_days is not None:
        previous_day, _current_day = source_days
        opposed = v4._body_aligned(previous_day, signal.side) is False
    return Context(
        previous_source_day_body_opposed=opposed,
        rearm=int(opportunity.rearm_index) > 0,
        c2_expansion=signal.model_kind.value == "c2-closure-next-h4-expansion",
        short=signal.side is DemoTradingSetupSide.SHORT,
    )


def _weighted_metrics(
    outcomes: Sequence[r5.ManagedTrade],
    contexts: Sequence[Context],
    *,
    scheme: RiskScheme,
    stress: Decimal,
) -> tuple[dict[str, Any], tuple[Decimal, ...], tuple[Decimal, ...]]:
    weights = tuple(scheme.weight(context) for context in contexts)
    values = tuple(
        (outcome.r_multiple - stress) * weight
        for outcome, weight in zip(outcomes, weights, strict=True)
    )
    return fx._metrics(values), values, weights


def _context_breakdown(
    outcomes: Sequence[r5.ManagedTrade],
    contexts: Sequence[Context],
) -> dict[str, Any]:
    def report(indices: Sequence[int]) -> dict[str, Any]:
        values = tuple(
            outcomes[index].r_multiple - PRIMARY_STRESS for index in indices
        )
        return fx._metrics(values)

    opposed = [i for i, c in enumerate(contexts) if c.previous_source_day_body_opposed]
    aligned = [i for i, c in enumerate(contexts) if not c.previous_source_day_body_opposed]
    rearm = [i for i, c in enumerate(contexts) if c.rearm]
    c2 = [i for i, c in enumerate(contexts) if c.c2_expansion]
    short = [i for i, c in enumerate(contexts) if c.short]
    return {
        "previous_body_opposed": report(opposed),
        "previous_body_aligned": report(aligned),
        "rearm": report(rearm),
        "c2_expansion": report(c2),
        "short": report(short),
    }


def _candidate(
    outcomes: Sequence[r5.ManagedTrade],
    contexts: Sequence[Context],
    *,
    scheme: RiskScheme,
) -> dict[str, Any]:
    primary, _primary_values, primary_weights = _weighted_metrics(
        outcomes,
        contexts,
        scheme=scheme,
        stress=PRIMARY_STRESS,
    )
    secondary, _secondary_values, secondary_weights = _weighted_metrics(
        outcomes,
        contexts,
        scheme=scheme,
        stress=SECONDARY_STRESS,
    )
    return {
        "scheme": scheme.payload(),
        "sample": len(outcomes),
        "minimum_weight": str(min(primary_weights)),
        "maximum_weight": str(max(primary_weights)),
        "mean_weight": str(sum(primary_weights, Decimal()) / len(primary_weights)),
        "zero_weight_trades": sum(weight == 0 for weight in primary_weights),
        "primary": primary,
        "secondary": secondary,
        "goal_pass": (
            MIN_TRADES <= len(outcomes) <= MAX_TRADES
            and Decimal(str(primary["profit_factor"] or "0")) >= Decimal("1.50")
            and Decimal(str(primary["max_drawdown_r"])) <= Decimal("6")
            and Decimal(str(secondary["profit_factor"] or "0")) >= Decimal("1.30")
            and Decimal(str(secondary["max_drawdown_r"])) <= Decimal("8")
            and sum(weight == 0 for weight in secondary_weights) == 0
        ),
    }


def _rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal, Decimal]:
    primary = row["primary"]
    return (
        int(bool(row["goal_pass"])),
        Decimal(str(primary["profit_factor"] or "0")),
        -Decimal(str(primary["max_drawdown_r"])),
        Decimal(str(primary["total_r"])),
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
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    indexed_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]] = {}
    opportunities_by_symbol: dict[str, tuple[r4.ExpandedOpportunity, ...]] = {}
    provenance: dict[str, Any] = {}
    for symbol in ("NAS100", "SP500", "US30"):
        bars, source = v5y._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        indexed_by_symbol[symbol] = {
            bar.opened_at.astimezone(UTC): bar for bar in bars
        }
        opportunities_by_symbol[symbol] = r8._opportunities(
            symbol=symbol,
            bars=bars,
        )
        provenance[symbol] = source

    stream = _base_stream(
        opportunities_by_symbol=opportunities_by_symbol,
        bars_by_symbol=bars_by_symbol,
    )
    opportunities = tuple(item[0] for item in stream)
    outcomes = tuple(item[1] for item in stream)
    contexts = tuple(
        _context(
            opportunity,
            indexed=indexed_by_symbol[opportunity.signal.symbol],
        )
        for opportunity in opportunities
    )
    rows = [
        _candidate(outcomes, contexts, scheme=scheme)
        for scheme in _schemes()
    ]
    rows.sort(key=_rank, reverse=True)
    goals = [row for row in rows if bool(row["goal_pass"])]
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "start_date": v5y.START_DATE.isoformat(),
            "end_date_exclusive": v5y.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_DEVELOPMENT",
            "fresh_certification_holdout": False,
        },
        "execution_architecture": r8.IDENTITY,
        "target_r": str(TARGET_R),
        "sample": len(outcomes),
        "context_breakdown": _context_breakdown(outcomes, contexts),
        "scheme_count": len(rows),
        "goal_candidate_count": len(goals),
        "best": rows[0],
        "candidates": rows,
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "all_trades_preserved": True,
            "zero_risk_allowed": False,
            "pnl_state_used_for_risk": False,
            "pre_entry_context_only": True,
            "five_year_window_consumed": True,
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
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
