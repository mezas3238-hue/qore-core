"""VT08 Index R8 — priority-POI + structural rearm reset.

Consumes the failed 5Y period as development evidence. R8 addresses two
identified R6 failures without outcome-based filtering:
1) excessive multi-POI initial admissions -> one source-priority POI per H4;
2) overfit specialist management -> reset to simple fixed target families.

Structural rearm remains enabled after a distinct new touch/CISD/continuation
cycle because R6 5Y forensics showed that family retained positive expectancy.

This is development, not certification.
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
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r8_priority_poi_rearm_reset.v1"
IDENTITY = "VT08_INDEX_R8_PRIORITY_POI_REARM_RESET_001"
TARGETS = (
    Decimal("1.5"),
    Decimal("2.0"),
    Decimal("2.5"),
    Decimal("3.0"),
)
MIN_TRADES = 1500
MAX_TRADES = 1600
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")


def _priority_rearm_for_h4(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_keys: tuple[datetime, ...],
    h4_opened_at: datetime,
    side: DemoTradingSetupSide,
) -> tuple[r4.ExpandedOpportunity, ...]:
    h4_bar = h4.get(h4_opened_at.astimezone(UTC))
    if h4_bar is None:
        return ()
    poi = v5y._priority_source_poi_fast(
        indexed,
        h4,
        h4_keys,
        h4_opened_at=h4_opened_at,
        side=side,
    )
    if poi is None:
        return ()
    bars = v5y._bars_between_fast(
        indexed,
        start=h4_opened_at,
        end=h4_bar.closed_at,
    )
    if not bars:
        return ()
    model_kind = v5y._completed_h4_model_fast(
        indexed,
        h4,
        h4_keys,
        current_h4_open=h4_opened_at,
        side=side,
    )
    if model_kind is None:
        model_kind = v6.H4ModelKind.SAME_C2

    result: list[r4.ExpandedOpportunity] = []
    cursor = 0
    rearm_index = 0
    while cursor < len(bars):
        touches = r4._touch_indices(bars, poi, start_index=cursor)
        if not touches:
            break
        touch_index = touches[0]
        built = r4._candidate_from_sequence(
            symbol=symbol,
            h4_bar=h4_bar,
            h4_opened_at=h4_opened_at,
            bars=bars,
            poi=poi,
            side=side,
            model_kind=model_kind,
            touch_index=touch_index,
        )
        if built is None:
            cursor = touch_index + 1
            continue
        signal, continuation_index = built
        result.append(
            r4.ExpandedOpportunity(
                signal=signal,
                source_poi_kind=poi.kind.value,
                poi_touch_at=bars[touch_index].opened_at.astimezone(UTC),
                rearm_index=rearm_index,
            )
        )
        rearm_index += 1
        cursor = continuation_index + 1
    return tuple(result)


def _opportunities(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> tuple[r4.ExpandedOpportunity, ...]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[object, DemoTradingSetupSide | None] = {}
    result: list[r4.ExpandedOpportunity] = []
    for opened in h4_keys:
        local = opened.astimezone(v5y._NY)
        if not (v5y.START_DATE <= local.date() < v5y.END_DATE_EXCLUSIVE):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local.date() not in side_cache:
            side_cache[local.date()] = v7._daily_bias(indexed, before=opened)
        side = side_cache[local.date()]
        if side is None:
            continue
        result.extend(
            _priority_rearm_for_h4(
                symbol=symbol,
                indexed=indexed,
                h4=h4,
                h4_keys=h4_keys,
                h4_opened_at=opened,
                side=side,
            )
        )
    result.sort(
        key=lambda item: (
            item.signal.signal_at,
            item.signal.symbol,
            item.signal.entry,
            item.signal.stop,
            item.rearm_index,
        )
    )
    return tuple(result)


def _target_policy(target: Decimal) -> r5.Policy:
    return r5.Policy(
        target_r=target,
        soft_close_loss_r=None,
        soft_close_until_mfe_r=None,
        deadline_bars=None,
        deadline_min_mfe_r=None,
        trail_name="OFF",
        trail_steps=(),
    )


def _sequential(
    opportunities: Sequence[r4.ExpandedOpportunity],
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    target: Decimal,
) -> tuple[tuple[r4.ExpandedOpportunity, r5.ManagedTrade], ...]:
    opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
    policy = _target_policy(target)
    candidates = tuple(
        (
            opportunity,
            r5._manage_trade(
                opportunity.signal,
                bars=bars,
                opened=opened,
                policy=policy,
            ),
        )
        for opportunity in opportunities
    )
    selected: list[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]] = []
    last_exit: datetime | None = None
    for opportunity, outcome in candidates:
        signal = opportunity.signal
        if last_exit is not None and signal.signal_at < last_exit:
            continue
        selected.append((opportunity, outcome))
        last_exit = outcome.exited_at
    return tuple(selected)


def _candidate(
    *,
    target: Decimal,
    opportunities_by_symbol: dict[str, tuple[r4.ExpandedOpportunity, ...]],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> dict[str, Any]:
    selected: list[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]] = []
    for symbol in ("NAS100", "SP500", "US30"):
        selected.extend(
            _sequential(
                opportunities_by_symbol[symbol],
                bars=bars_by_symbol[symbol],
                target=target,
            )
        )
    selected.sort(
        key=lambda item: (item[0].signal.signal_at, item[0].signal.symbol)
    )
    admissions = tuple(
        fx.Admission(
            opportunity=opportunity,
            baseline_exit_at=outcome.exited_at,
        )
        for opportunity, outcome in selected
    )
    outcomes = tuple(outcome for _opportunity, outcome in selected)
    raw_primary_values = tuple(
        outcome.r_multiple - PRIMARY_STRESS for outcome in outcomes
    )
    raw_secondary_values = tuple(
        outcome.r_multiple - SECONDARY_STRESS for outcome in outcomes
    )
    gp_trace = fx._governor_trace(
        admissions,
        outcomes,
        stress=PRIMARY_STRESS,
    )
    gs_trace = fx._governor_trace(
        admissions,
        outcomes,
        stress=SECONDARY_STRESS,
    )
    gp_values = tuple(item.value for item in gp_trace)
    gs_values = tuple(item.value for item in gs_trace)
    by_market = {
        symbol: sum(item.signal.symbol == symbol for item in admissions)
        for symbol in ("NAS100", "SP500", "US30")
    }
    rearm_count = sum(
        int(item.opportunity.rearm_index) > 0 for item in admissions
    )
    raw = fx._metrics(raw_primary_values)
    gp = fx._metrics(gp_values)
    gs = fx._metrics(gs_values)
    return {
        "target_r": str(target),
        "sample": len(admissions),
        "density_pass": MIN_TRADES <= len(admissions) <= MAX_TRADES,
        "trade_count_by_market": by_market,
        "rearm_trade_count": rearm_count,
        "raw_primary": raw,
        "raw_secondary": fx._metrics(raw_secondary_values),
        "governed_primary": gp,
        "governed_secondary": gs,
        "governor_lock_in_primary": fx._governor_lock_in(admissions, gp_trace),
    }


def _rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal, Decimal]:
    raw = row["raw_primary"]
    gp = row["governed_primary"]
    return (
        int(bool(row["density_pass"])),
        Decimal(str(raw["profit_factor"] or "0")),
        Decimal(str(gp["profit_factor"] or "0")),
        -Decimal(str(gp["max_drawdown_r"])),
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
    opportunities_by_symbol: dict[str, tuple[r4.ExpandedOpportunity, ...]] = {}
    provenance: dict[str, Any] = {}
    for symbol in ("NAS100", "SP500", "US30"):
        bars, source = v5y._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        opportunities_by_symbol[symbol] = _opportunities(
            symbol=symbol,
            bars=bars,
        )
        provenance[symbol] = source

    rows = [
        _candidate(
            target=target,
            opportunities_by_symbol=opportunities_by_symbol,
            bars_by_symbol=bars_by_symbol,
        )
        for target in TARGETS
    ]
    rows.sort(key=_rank, reverse=True)
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "start_date": v5y.START_DATE.isoformat(),
            "end_date_exclusive": v5y.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_DEVELOPMENT",
            "fresh_certification_holdout": False,
        },
        "causal_changes": {
            "initial_poi": "ONE_SOURCE_PRIORITY_POI_PER_H4",
            "poi_priority": ["fvg", "relevant-swing", "cisd"],
            "structural_rearm": True,
            "specialist_management_reset": True,
            "initial_stop": "PROTECTED_SWING_UNCHANGED",
            "no_stop_widening": True,
        },
        "raw_opportunity_count_by_market": {
            symbol: len(opportunities_by_symbol[symbol])
            for symbol in ("NAS100", "SP500", "US30")
        },
        "target_candidate_count": len(rows),
        "best": rows[0],
        "candidates": rows,
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "bounded_target_screen": True,
            "post_entry_admission_features_used": False,
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
    print(json.dumps({"identity": IDENTITY, "best": report["best"]}, sort_keys=True))


if __name__ == "__main__":
    main()
