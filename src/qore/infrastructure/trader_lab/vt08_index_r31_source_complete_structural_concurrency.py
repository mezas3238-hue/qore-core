"""VT08 Index R31 — source-complete structural concurrency experiment.

R30 proved that the existing VT08 source-complete structural surface already
contains 2,448 distinct 5Y opportunities, inside Owner Contract V2 (2,300-2,500),
while one-active-position-per-symbol admits only 2,055 at the frozen 2.5R
lifecycle.

R31 does NOT change entry, stop, target, POI definitions, daily bias, anchors,
or structural rearm. It tests one bounded architectural hypothesis:

    distinct structural events on the same symbol may coexist as independent
    risk requests while QORE Risk governs total portfolio exposure.

This is research only. The permanent one-active-position-per-symbol contract is
NOT changed by this experiment. Promotion requires both:
- governed PF/DD/yearly stability under the existing R28/R29 risk intelligence;
- positive raw structural expectancy, so microscopic sizing cannot hide a
  structurally negative signal population.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as r6
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r26_formation_health_governor as r26
from qore.infrastructure.trader_lab import vt08_index_r29_candidate_freeze as freeze

SCHEMA = "qore.trader_lab.vt08_index_r31_source_complete_structural_concurrency.v1"
IDENTITY = "VT08_INDEX_R31_SOURCE_COMPLETE_STRUCTURAL_CONCURRENCY_001"

TARGET_R = Decimal("2.5")
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
RAW_PRIMARY_PF_FLOOR = Decimal("1.00")
GOVERNED_PRIMARY_PF_MIN = Decimal("1.50")
GOVERNED_SECONDARY_PF_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")


def _build_source_complete_stream(
    *,
    roots: dict[str, Path],
) -> tuple[
    tuple[tuple[Any, r5.ManagedTrade], ...],
    dict[str, tuple[Any, ...]],
    dict[str, tuple[object, ...]],
    dict[str, Any],
]:
    stream: list[tuple[Any, r5.ManagedTrade]] = []
    bars_by_symbol: dict[str, tuple[Any, ...]] = {}
    opened_by_symbol: dict[str, tuple[object, ...]] = {}
    provenance: dict[str, Any] = {}
    policy = r8._target_policy(TARGET_R)

    for symbol in contract.MARKETS:
        bars, source = r6._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
        opportunities = r6._build_surface_5y(symbol=symbol, bars=bars)
        if len({item.identity() for item in opportunities}) != len(opportunities):
            raise ValueError(f"duplicate structural opportunity identity for {symbol}")
        for opportunity in opportunities:
            stream.append(
                (
                    opportunity,
                    r5._manage_trade(
                        opportunity.signal,
                        bars=bars,
                        opened=opened,
                        policy=policy,
                    ),
                )
            )
        bars_by_symbol[symbol] = bars
        opened_by_symbol[symbol] = opened
        provenance[symbol] = source

    stream.sort(
        key=lambda item: (
            item[0].signal.signal_at,
            item[0].signal.symbol,
            item[0].signal.entry,
            item[0].signal.stop,
            item[0].rearm_index,
        )
    )
    identities = [item[0].identity() for item in stream]
    if len(set(identities)) != len(identities):
        raise ValueError("cross-market structural opportunity identity collision")
    return tuple(stream), bars_by_symbol, opened_by_symbol, provenance


def _raw_metrics(
    stream: tuple[tuple[Any, r5.ManagedTrade], ...],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    ordered = sorted(
        stream,
        key=lambda item: (
            item[1].exited_at.astimezone(UTC),
            item[0].signal.symbol,
            item[0].signal.signal_at,
        ),
    )
    values = tuple(item[1].r_multiple - stress for item in ordered)
    return fx._metrics(values)


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
    stream, bars_by_symbol, opened_by_symbol, provenance = (
        _build_source_complete_stream(roots=roots)
    )

    density_pass = contract.validates_trade_count(years=5, sample=len(stream))
    if not density_pass:
        raise ValueError(f"R31 source-complete density drift: {len(stream)}")

    raw_primary = _raw_metrics(stream, stress=PRIMARY_STRESS)
    raw_secondary = _raw_metrics(stream, stress=SECONDARY_STRESS)

    profile = freeze.frozen_formation_health_profile()
    governed, assigned = r26._row(stream, profile=profile)

    primary_mtm = r15._portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=PRIMARY_STRESS,
        adverse=True,
    )
    secondary_mtm = r15._portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=SECONDARY_STRESS,
        adverse=True,
    )

    raw_edge_pass = (
        Decimal(str(raw_primary["profit_factor"] or "0")) >= RAW_PRIMARY_PF_FLOOR
        and Decimal(str(raw_primary["total_r"])) > 0
    )
    governed_gate_pass = (
        Decimal(str(governed["primary"]["profit_factor"] or "0"))
        >= GOVERNED_PRIMARY_PF_MIN
        and Decimal(str(governed["secondary"]["profit_factor"] or "0"))
        >= GOVERNED_SECONDARY_PF_MIN
        and Decimal(primary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
        and Decimal(secondary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
        and bool(governed["all_primary_years_positive"])
        and int(governed["diagnostics"]["suppressed_trade_count"]) == 0
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "sample": len(stream),
        "density_pass": density_pass,
        "target_r": str(TARGET_R),
        "owner_contract": {
            "contract_id": contract.CONTRACT_ID,
            "five_year_trade_range": list(contract.FIVE_YEAR_TRADE_RANGE),
            "two_year_min_trades": contract.TWO_YEAR_MIN_TRADES,
            "portfolio_dd_max_r": str(contract.PORTFOLIO_MAX_DRAWDOWN_R),
        },
        "experimental_architecture": {
            "same_symbol_structural_concurrency_under_test": True,
            "permanent_max_active_positions_per_symbol_changed": False,
            "distinct_structural_identity_required": True,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "rearm_changed": False,
            "poi_set": ["fvg", "relevant-swing", "cisd"],
        },
        "raw_primary": raw_primary,
        "raw_secondary": raw_secondary,
        "raw_edge_pass": raw_edge_pass,
        "governed": governed,
        "primary_conservative_mark_to_market": primary_mtm,
        "secondary_conservative_mark_to_market": secondary_mtm,
        "governed_gate_pass": governed_gate_pass,
        "promotion_gate_pass": raw_edge_pass and governed_gate_pass,
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "consumed_window": True,
            "fresh_holdout_claim": False,
            "no_trivial_scaling_as_edge_substitute": True,
            "all_structural_signals_preserved": True,
            "signal_suppression_allowed": False,
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
                "sample": report["sample"],
                "density_pass": report["density_pass"],
                "raw_primary": report["raw_primary"],
                "raw_edge_pass": report["raw_edge_pass"],
                "governed_primary": report["governed"]["primary"],
                "governed_secondary": report["governed"]["secondary"],
                "primary_mtm": report["primary_conservative_mark_to_market"],
                "secondary_mtm": report["secondary_conservative_mark_to_market"],
                "governed_gate_pass": report["governed_gate_pass"],
                "promotion_gate_pass": report["promotion_gate_pass"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
