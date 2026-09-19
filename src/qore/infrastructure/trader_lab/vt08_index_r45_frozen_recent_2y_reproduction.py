"""VT08 Index R45 — frozen R44 candidate recent-2Y no-retuning reproduction.

Replays the exact frozen VT08_INDEX_R43_SOURCE_COMPLETE_2448_001 identity on:
    2024-09-15 <= New York source date < 2026-09-15

This historical region has been touched by earlier VT08 research, so this is a
robustness/reproduction gate, not a fresh certification holdout.

No entry, stop, target, POI, structural rearm, causal health, structural prior,
concurrency rule, portfolio governor, or risk parameter may be changed here.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_management_round5 as r5,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_five_year_validation as r6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r8_priority_poi_rearm_reset as r8,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r14_recent_2y_replay as r2y,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r34_hybrid_formation_poi_health as r34,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r42_hierarchical_nas100_prior as r42,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r43_sp500_long_stability_prior as r43,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r44_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r45_frozen_recent_2y_reproduction.v1"
IDENTITY = "VT08_INDEX_R45_FROZEN_RECENT_2Y_REPRODUCTION_001"

START_DATE = date(2024, 9, 15)
END_DATE_EXCLUSIVE = date(2026, 9, 15)
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")
TWO_YEAR_MIN_TRADES = 1000
_NY = ZoneInfo("America/New_York")


def _build_surface_2y(
    *,
    symbol: str,
    bars: tuple[Vt08IndexC2R1Bar, ...],
) -> tuple[r4.ExpandedOpportunity, ...]:
    """Exact source-complete R43 signal architecture over the 2Y window."""

    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[date, DemoTradingSetupSide | None] = {}
    opportunities: list[r4.ExpandedOpportunity] = []

    for opened in h4_keys:
        local = opened.astimezone(_NY)
        local_date = local.date()
        if not (START_DATE <= local_date < END_DATE_EXCLUSIVE):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(indexed, before=opened)
        side = side_cache[local_date]
        if side is None:
            continue
        opportunities.extend(
            r6._opportunities_for_h4_fast(
                symbol=symbol,
                indexed=indexed,
                h4=h4,
                h4_keys=h4_keys,
                h4_opened_at=opened,
                side=side,
            )
        )

    opportunities.sort(
        key=lambda item: (
            item.signal.signal_at,
            item.signal.symbol,
            item.signal.entry,
            item.signal.stop,
            item.rearm_index,
        )
    )
    identities = [item.identity() for item in opportunities]
    if len(set(identities)) != len(identities):
        raise ValueError(f"duplicate 2Y structural opportunity identity for {symbol}")
    return tuple(opportunities)


def _build_source_complete_stream_2y(
    *,
    roots: dict[str, Path],
) -> tuple[
    tuple[tuple[r4.ExpandedOpportunity, r5.ManagedTrade], ...],
    dict[str, tuple[Vt08IndexC2R1Bar, ...]],
    dict[str, tuple[Any, ...]],
    dict[str, Any],
]:
    stream: list[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]] = []
    bars_by_symbol: dict[str, tuple[Vt08IndexC2R1Bar, ...]] = {}
    opened_by_symbol: dict[str, tuple[Any, ...]] = {}
    provenance: dict[str, Any] = {}
    policy = r8._target_policy(Decimal(freeze.TARGET_R))

    for symbol in contract.MARKETS:
        bars, source = r2y._load_cibo_m15_2y(roots[symbol], symbol=symbol)
        typed_bars = tuple(bars)
        opened = tuple(bar.opened_at.astimezone(UTC) for bar in typed_bars)
        opportunities = _build_surface_2y(symbol=symbol, bars=typed_bars)
        for opportunity in opportunities:
            stream.append(
                (
                    opportunity,
                    r5._manage_trade(
                        opportunity.signal,
                        bars=typed_bars,
                        opened=opened,
                        policy=policy,
                    ),
                )
            )
        bars_by_symbol[symbol] = typed_bars
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
        raise ValueError("2Y cross-market structural opportunity identity collision")
    return tuple(stream), bars_by_symbol, opened_by_symbol, provenance


def _two_year_blocks(
    assigned: tuple[r15.AssignedTrade, ...],
    *,
    stress: Decimal,
) -> dict[str, dict[str, Any]]:
    boundaries = (
        START_DATE,
        date(2025, 9, 15),
        END_DATE_EXCLUSIVE,
    )
    result: dict[str, dict[str, Any]] = {}
    for index in range(2):
        start = boundaries[index]
        end = boundaries[index + 1]
        items = sorted(
            (
                item
                for item in assigned
                if start <= item.exited_at.astimezone(_NY).date() < end
            ),
            key=lambda item: (item.exited_at, item.symbol, item.trade_id),
        )
        values = tuple(
            (item.outcome.r_multiple - stress) * item.weight
            for item in items
        )
        result[f"Y{index + 1}"] = {
            "start_date": start.isoformat(),
            "end_date_exclusive": end.isoformat(),
            **fx._metrics(values),
        }
    return result


def _all_blocks_positive(blocks: dict[str, dict[str, Any]]) -> bool:
    return len(blocks) == 2 and all(
        int(block["sample"]) > 0 and Decimal(str(block["total_r"])) > 0
        for block in blocks.values()
    )


def _breakdown(
    assigned: tuple[r15.AssignedTrade, ...],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    market: dict[str, list[Decimal]] = defaultdict(list)
    side: dict[str, list[Decimal]] = defaultdict(list)
    market_side: dict[str, list[Decimal]] = defaultdict(list)
    poi: dict[str, list[Decimal]] = defaultdict(list)

    for item in assigned:
        value = (item.outcome.r_multiple - stress) * item.weight
        side_value = item.opportunity.signal.side.value
        market[item.symbol].append(value)
        side[side_value].append(value)
        market_side[f"{item.symbol}|{side_value}"].append(value)
        poi[str(item.opportunity.source_poi_kind)].append(value)

    def metrics(groups: dict[str, list[Decimal]]) -> dict[str, Any]:
        return {
            key: fx._metrics(tuple(values))
            for key, values in sorted(groups.items())
        }

    return {
        "market": metrics(market),
        "side": metrics(side),
        "market_side": metrics(market_side),
        "poi": metrics(poi),
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R44 frozen dependency contract drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    stream, bars_by_symbol, opened_by_symbol, provenance = (
        _build_source_complete_stream_2y(roots=roots)
    )

    _base_row, base_assigned = r34._row(
        stream,
        overlay=r43.BASE_POI_OVERLAY,
    )
    r42_assigned, r42_diagnostics = r42._apply_prior(base_assigned)
    assigned, r43_diagnostics = r43._apply_sp500_long_prior(r42_assigned)

    primary = fx._metrics(
        r15._realized_values(assigned, stress=PRIMARY_STRESS)
    )
    secondary = fx._metrics(
        r15._realized_values(assigned, stress=SECONDARY_STRESS)
    )
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
    primary_blocks = _two_year_blocks(assigned, stress=PRIMARY_STRESS)
    secondary_blocks = _two_year_blocks(assigned, stress=SECONDARY_STRESS)
    raw_primary = r31._raw_metrics(stream, stress=PRIMARY_STRESS)
    raw_secondary = r31._raw_metrics(stream, stress=SECONDARY_STRESS)

    density_pass = contract.validates_trade_count(years=2, sample=len(assigned))
    primary_blocks_pass = _all_blocks_positive(primary_blocks)
    secondary_blocks_pass = _all_blocks_positive(secondary_blocks)
    contract_pass = (
        density_pass
        and Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
        and Decimal(str(secondary["profit_factor"] or "0")) >= PF_SECONDARY_MIN
        and Decimal(primary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
        and Decimal(secondary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
        and primary_blocks_pass
        and secondary_blocks_pass
        and int(r43_diagnostics["suppressed_trade_count"]) == 0
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.RULE_FINGERPRINT,
            "source_5y_run_id": freeze.SOURCE_RUN_ID,
            "source_5y_artifact_id": freeze.SOURCE_ARTIFACT_ID,
            "rules_changed_for_2y": False,
        },
        "window": {
            "start_date": START_DATE.isoformat(),
            "end_date_exclusive": END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_ROBUSTNESS_REPRODUCTION",
            "fresh_certification_holdout": False,
        },
        "sample": len(assigned),
        "trade_count_by_market": {
            symbol: sum(item.symbol == symbol for item in assigned)
            for symbol in contract.MARKETS
        },
        "raw_primary": raw_primary,
        "raw_secondary": raw_secondary,
        "primary": primary,
        "secondary": secondary,
        "primary_conservative_mark_to_market": primary_mtm,
        "secondary_conservative_mark_to_market": secondary_mtm,
        "two_year_blocks_primary": primary_blocks,
        "two_year_blocks_secondary": secondary_blocks,
        "all_two_year_blocks_primary_positive": primary_blocks_pass,
        "all_two_year_blocks_secondary_positive": secondary_blocks_pass,
        "breakdown_primary": _breakdown(assigned, stress=PRIMARY_STRESS),
        "breakdown_secondary": _breakdown(assigned, stress=SECONDARY_STRESS),
        "r42_diagnostics": r42_diagnostics,
        "r43_diagnostics": r43_diagnostics,
        "decision": {
            "density_pass": density_pass,
            "primary_pf_pass": (
                Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
            ),
            "secondary_pf_pass": (
                Decimal(str(secondary["profit_factor"] or "0")) >= PF_SECONDARY_MIN
            ),
            "primary_mtm_dd_pass": (
                Decimal(primary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            ),
            "secondary_mtm_dd_pass": (
                Decimal(secondary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            ),
            "two_full_blocks_primary_positive": primary_blocks_pass,
            "two_full_blocks_secondary_positive": secondary_blocks_pass,
            "no_suppression_pass": (
                int(r43_diagnostics["suppressed_trade_count"]) == 0
            ),
            "recent_2y_contract_pass": contract_pass,
        },
        "contract": {
            "two_year_min_trades": TWO_YEAR_MIN_TRADES,
            "primary_pf_minimum": str(PF_PRIMARY_MIN),
            "secondary_pf_minimum": str(PF_SECONDARY_MIN),
            "portfolio_dd_max_r": str(PORTFOLIO_DD_MAX),
            "two_full_12m_blocks_positive_both_stresses": True,
            "same_frozen_identity_required": True,
        },
        "provenance": provenance,
        "governance": {
            "reproduction_only": True,
            "candidate_frozen_before_replay": True,
            "no_retuning": True,
            "historical_window_previously_consumed": True,
            "fresh_holdout_claim": False,
            "source_complete_architecture_preserved": True,
            "same_symbol_structural_concurrency_preserved": True,
            "all_structural_signals_preserved": True,
            "signal_suppression_allowed": False,
            "zero_risk_allowed": False,
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
                "candidate": report["candidate"],
                "sample": report["sample"],
                "trade_count_by_market": report["trade_count_by_market"],
                "primary": report["primary"],
                "secondary": report["secondary"],
                "primary_mtm": report["primary_conservative_mark_to_market"],
                "secondary_mtm": report["secondary_conservative_mark_to_market"],
                "two_year_blocks_primary": report["two_year_blocks_primary"],
                "two_year_blocks_secondary": report["two_year_blocks_secondary"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
