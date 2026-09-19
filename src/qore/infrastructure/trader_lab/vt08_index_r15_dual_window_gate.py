"""VT08 Index R15 — simultaneous 5Y + recent-2Y dual-window robustness gate.

Every R14 refined rolling scheme is evaluated on BOTH consumed development
windows with identical rules:
- 5Y: 2018-09-15 .. 2023-09-15
- recent 2Y: 2024-09-15 .. 2026-09-15

No scheme is allowed to pass by optimizing one window and checking the other
later. The same target, opportunity architecture, contextual features and risk
governor parameters are used in both windows.

This remains development evidence, not a fresh certification holdout.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r13_rolling_drawdown_governor as r13
from qore.infrastructure.trader_lab import vt08_index_r14_recent_2y_replay as r2y
from qore.infrastructure.trader_lab import vt08_index_r14_rolling_refinement as r14
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r15_dual_window_gate.v1"
IDENTITY = "VT08_INDEX_R15_DUAL_WINDOW_GATE_001"
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


def _five_year_stream(
    roots: dict[str, Path],
) -> tuple[
    tuple[tuple[r4.ExpandedOpportunity, r5.ManagedTrade], ...],
    tuple[r10.Context, ...],
    dict[str, Any],
]:
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

    stream = r10._base_stream(
        opportunities_by_symbol=opportunities_by_symbol,
        bars_by_symbol=bars_by_symbol,
    )
    contexts = tuple(
        r10._context(
            opportunity,
            indexed=indexed_by_symbol[opportunity.signal.symbol],
        )
        for opportunity, _outcome in stream
    )
    return stream, contexts, provenance


def _two_year_stream(
    roots: dict[str, Path],
) -> tuple[
    tuple[tuple[r4.ExpandedOpportunity, r5.ManagedTrade], ...],
    tuple[r10.Context, ...],
    dict[str, Any],
]:
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    indexed_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]] = {}
    opportunities_by_symbol: dict[str, tuple[r4.ExpandedOpportunity, ...]] = {}
    provenance: dict[str, Any] = {}
    for symbol in ("NAS100", "SP500", "US30"):
        bars, source = r2y._load_cibo_m15_2y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        indexed_by_symbol[symbol] = {
            bar.opened_at.astimezone(UTC): bar for bar in bars
        }
        opportunities_by_symbol[symbol] = r2y._opportunities_2y(
            symbol=symbol,
            bars=bars,
        )
        provenance[symbol] = source

    stream = r10._base_stream(
        opportunities_by_symbol=opportunities_by_symbol,
        bars_by_symbol=bars_by_symbol,
    )
    contexts = tuple(
        r10._context(
            opportunity,
            indexed=indexed_by_symbol[opportunity.signal.symbol],
        )
        for opportunity, _outcome in stream
    )
    return stream, contexts, provenance


def _window_metrics(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    contexts: Sequence[r10.Context],
    *,
    scheme: r14.RefinedScheme,
) -> dict[str, Any]:
    outcomes = tuple(outcome for _opportunity, outcome in stream)
    rolling = scheme.as_r13()
    primary_values, primary_diag = r13._weighted_values(
        outcomes,
        contexts,
        scheme=rolling,
        stress=PRIMARY_STRESS,
    )
    secondary_values, secondary_diag = r13._weighted_values(
        outcomes,
        contexts,
        scheme=rolling,
        stress=SECONDARY_STRESS,
    )
    primary = fx._metrics(primary_values)
    secondary = fx._metrics(secondary_values)
    return {
        "sample": len(stream),
        "primary": primary,
        "secondary": secondary,
        "primary_diagnostics": primary_diag,
        "secondary_diagnostics": secondary_diag,
    }


def _positive(metrics: dict[str, Any]) -> bool:
    return Decimal(str(metrics["total_r"])) > 0


def _primary_pass(metrics: dict[str, Any]) -> bool:
    return (
        _positive(metrics)
        and Decimal(str(metrics["profit_factor"] or "0")) >= PF_MIN
        and Decimal(str(metrics["max_drawdown_r"])) <= DD_MAX
    )


def _secondary_pass(metrics: dict[str, Any]) -> bool:
    return (
        _positive(metrics)
        and Decimal(str(metrics["profit_factor"] or "0")) >= SECONDARY_PF_MIN
        and Decimal(str(metrics["max_drawdown_r"])) <= SECONDARY_DD_MAX
    )


def _candidate(
    five_stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    five_contexts: Sequence[r10.Context],
    two_stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    two_contexts: Sequence[r10.Context],
    *,
    scheme: r14.RefinedScheme,
) -> dict[str, Any]:
    five = _window_metrics(five_stream, five_contexts, scheme=scheme)
    two = _window_metrics(two_stream, two_contexts, scheme=scheme)

    five_density = FIVE_YEAR_MIN_TRADES <= int(five["sample"]) <= FIVE_YEAR_MAX_TRADES
    two_density = TWO_YEAR_MIN_TRADES <= int(two["sample"]) <= TWO_YEAR_MAX_TRADES

    five_primary = five["primary"]
    two_primary = two["primary"]
    five_secondary = five["secondary"]
    two_secondary = two["secondary"]

    five_pass = (
        five_density
        and _primary_pass(five_primary)
        and _secondary_pass(five_secondary)
    )
    two_pass = (
        two_density
        and _primary_pass(two_primary)
        and _secondary_pass(two_secondary)
    )
    return {
        "scheme": scheme.payload(),
        "five_year": five,
        "recent_two_year": two,
        "five_year_density_pass": five_density,
        "recent_two_year_density_pass": two_density,
        "five_year_pass": five_pass,
        "recent_two_year_pass": two_pass,
        "dual_window_pass": five_pass and two_pass,
    }


def _rank(
    row: dict[str, Any],
) -> tuple[int, int, Decimal, Decimal, Decimal, Decimal]:
    five = row["five_year"]["primary"]
    two = row["recent_two_year"]["primary"]
    return (
        int(bool(row["dual_window_pass"])),
        int(bool(row["recent_two_year_pass"])),
        min(
            Decimal(str(five["profit_factor"] or "0")),
            Decimal(str(two["profit_factor"] or "0")),
        ),
        -max(
            Decimal(str(five["max_drawdown_r"])),
            Decimal(str(two["max_drawdown_r"])),
        ),
        Decimal(str(two["total_r"])),
        Decimal(str(five["total_r"])),
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
    five_stream, five_contexts, five_provenance = _five_year_stream(roots)
    two_stream, two_contexts, two_provenance = _two_year_stream(roots)

    rows = [
        _candidate(
            five_stream,
            five_contexts,
            two_stream,
            two_contexts,
            scheme=scheme,
        )
        for scheme in r14._schemes()
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
            "primary_total_must_be_positive": True,
            "secondary_pf_minimum": str(SECONDARY_PF_MIN),
            "secondary_dd_max_r": str(SECONDARY_DD_MAX),
            "same_scheme_required_in_both_windows": True,
        },
        "windows": {
            "five_year": {
                "start_date": v5y.START_DATE.isoformat(),
                "end_date_exclusive": v5y.END_DATE_EXCLUSIVE.isoformat(),
                "status": "CONSUMED_DEVELOPMENT",
            },
            "recent_two_year": {
                "start_date": r2y.START_DATE.isoformat(),
                "end_date_exclusive": r2y.END_DATE_EXCLUSIVE.isoformat(),
                "status": "CONSUMED_DEVELOPMENT",
            },
        },
        "execution_architecture": r8.IDENTITY,
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
            "both_windows_consumed": True,
            "simultaneous_dual_window_gate": True,
            "same_rules_both_windows": True,
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
