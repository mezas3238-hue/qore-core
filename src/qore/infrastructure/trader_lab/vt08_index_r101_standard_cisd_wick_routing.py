"""VT08 Index R101 — source-correct STANDARD CISD wick-routing density census.

R100 corrects the root semantic error: an aligned H4->M15 POI + CISD-confirmed
swing is a valid STANDARD model. Explicit liquidity/FVG Protected-Swing
mechanism evidence is additional confirmation, not a universal density gate.

R99 independently preregistered a ratio-free wick state on the untouched
canonical surface:
- SMALL_WICK_EXPANSION: directional body through signal > adverse H4 run;
- LARGE_WICK_REVERSAL: adverse H4 run > directional body through signal;
- equality fails closed.

Primary TTrades 4H Power-of-3 guidance distinguishes the same two delivery
states:
- shallow/small wick can manipulate and expand within the current H4 candle;
- a deep/large opposing run generally shifts the expansion expectation to the
  following H4 candle.

R101 tests that source routing without PnL:
- SMALL -> preserve exact canonical same-H4 continuation.
- LARGE -> do not count the late same-H4 continuation; carry the already
  CISD-confirmed swing to the immediately following complete H4 and require:
    * swing survives the remainder of the formation H4,
    * daily bias still agrees,
    * next H4 is Owner-authorized (22/02/06/10 NY),
    * exact V6 M15 break-and-close continuation before invalidation.
- EQUAL -> fail closed.
- no positional fallback, no later-H4 deferral, no target/risk/economic logic.

This is a density/causality census only. It does not create a candidate.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r99_standard_ideal_wick_state as r99,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r100_cisd_ps_semantics_correction as r100,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r101_standard_cisd_wick_routing.v1"
IDENTITY = "VT08_INDEX_R101_STANDARD_CISD_WICK_ROUTING_DENSITY_001"

SOURCE_R100_RUN_ID = 35553739444
SOURCE_R100_ARTIFACT_ID = 10619881275
SOURCE_R100_ARTIFACT_DIGEST = (
    "sha256:c58d8e8844c5b99e46ae94653ded118b0f6564d285afe8ecbcdff227d657bb4b"
)

TTRADES_PO3_URL = (
    "https://ttrades.com/"
    "trading-the-4-hour-power-of-3-open-high-low-close-strategy/"
)
TTRADES_WICK_URL = (
    "https://ttrades.com/"
    "let-the-wick-form-trade-the-body-stop-getting-stopped-out/"
)


@dataclass(frozen=True, slots=True)
class RoutedExecution:
    symbol: str
    continuation_at: datetime
    side: DemoTradingSetupSide
    entry: Decimal
    protected_swing: Decimal
    route: str
    source_signal_at: datetime
    source_h4_opened_at: datetime
    execution_h4_opened_at: datetime

    def identity(self) -> tuple[object, ...]:
        return (
            self.symbol,
            self.continuation_at.astimezone(UTC),
            self.side.value,
            self.entry,
            self.protected_swing,
        )


def _signal_identity(opportunity: Any) -> tuple[object, ...]:
    signal = opportunity.signal
    return (
        str(signal.symbol),
        signal.signal_at.astimezone(UTC),
        signal.side.value,
        signal.entry,
        signal.protected_swing_extreme,
    )


def _survives_remainder(
    inside: Sequence[Vt08IndexC2R1Bar],
    *,
    signal_at: datetime,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
) -> bool:
    cutoff = signal_at.astimezone(UTC)
    for bar in inside:
        if bar.opened_at.astimezone(UTC) < cutoff:
            continue
        invalidated = (
            bar.low <= protected_swing
            if side is DemoTradingSetupSide.LONG
            else bar.high >= protected_swing
        )
        if invalidated:
            return False
    return True


def _next_h4_continuation(
    next_inside: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
) -> tuple[int, datetime, Decimal] | None:
    continuation_index = v6._first_continuation(
        next_inside,
        side=side,
        start_index=0,
        protected_swing=protected_swing,
    )
    if continuation_index is None:
        return None
    bar = next_inside[continuation_index]
    entry = bar.close
    risk = (
        entry - protected_swing
        if side is DemoTradingSetupSide.LONG
        else protected_swing - entry
    )
    if risk <= 0:
        return None
    return (
        continuation_index,
        bar.closed_at.astimezone(UTC),
        entry,
    )


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    stream, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, expected = r74._window_contract(window_id)
    if len(stream) != expected:
        raise ValueError(f"R101 {window_id} canonical sample drift")

    h4_bars = {
        symbol: r82._h4_bar_cache(bars_by_symbol[symbol])
        for symbol in contract.MARKETS
    }
    indexed = {
        symbol: {
            bar.opened_at.astimezone(UTC): bar
            for bar in bars_by_symbol[symbol]
        }
        for symbol in contract.MARKETS
    }

    routed: dict[tuple[object, ...], RoutedExecution] = {}
    counts: Counter[str] = Counter()
    by_market: dict[str, Counter[str]] = {
        symbol: Counter()
        for symbol in contract.MARKETS
    }
    by_old_ps_state: dict[str, Counter[str]] = {}

    for opportunity, _outcome in stream:
        signal = opportunity.signal
        symbol = str(signal.symbol)
        current_open = signal.h4_opened_at.astimezone(UTC)
        inside = h4_bars[symbol].get(current_open)
        if inside is None:
            raise ValueError("R101 canonical H4 missing")

        observed = r99._observed_through_signal(
            inside,
            signal_at=signal.signal_at,
        )
        wick_state, _adverse, _directional = r99._wick_state(
            observed,
            side=signal.side,
            h4_open=inside[0].open,
            entry=signal.entry,
        )
        old_qualification = r82._classify_opportunity(
            opportunity,
            h4_bars=h4_bars[symbol],
        )
        old_ps_state = r99._ps_state(
            str(old_qualification["family"])
        )
        by_old_ps_state.setdefault(old_ps_state, Counter())

        counts[f"CANONICAL_{wick_state}"] += 1
        by_market[symbol][f"CANONICAL_{wick_state}"] += 1
        by_old_ps_state[old_ps_state][f"CANONICAL_{wick_state}"] += 1

        if wick_state == r99.EQUAL_WICK:
            counts["EQUAL_FAIL_CLOSED"] += 1
            continue

        if wick_state == r99.SMALL_WICK:
            row = RoutedExecution(
                symbol=symbol,
                continuation_at=signal.signal_at.astimezone(UTC),
                side=signal.side,
                entry=signal.entry,
                protected_swing=signal.protected_swing_extreme,
                route="SMALL_WICK_SAME_H4",
                source_signal_at=signal.signal_at.astimezone(UTC),
                source_h4_opened_at=current_open,
                execution_h4_opened_at=current_open,
            )
            routed.setdefault(row.identity(), row)
            counts["SMALL_ROUTED_SAME_H4"] += 1
            by_market[symbol]["SMALL_ROUTED_SAME_H4"] += 1
            by_old_ps_state[old_ps_state]["SMALL_ROUTED_SAME_H4"] += 1
            continue

        counts["LARGE_ROUTE_ATTEMPT"] += 1
        by_market[symbol]["LARGE_ROUTE_ATTEMPT"] += 1
        by_old_ps_state[old_ps_state]["LARGE_ROUTE_ATTEMPT"] += 1

        if not _survives_remainder(
            inside,
            signal_at=signal.signal_at,
            side=signal.side,
            protected_swing=signal.protected_swing_extreme,
        ):
            counts["LARGE_FAIL_INVALIDATED_BEFORE_H4_CLOSE"] += 1
            by_market[symbol][
                "LARGE_FAIL_INVALIDATED_BEFORE_H4_CLOSE"
            ] += 1
            continue

        next_open = inside[-1].closed_at.astimezone(UTC)
        next_inside = h4_bars[symbol].get(next_open)
        if next_inside is None:
            counts["LARGE_FAIL_NO_NEXT_COMPLETE_H4"] += 1
            continue

        next_local = next_open.astimezone(v7._NY)
        if not (start_date <= next_local.date() < end_date):
            counts["LARGE_FAIL_NEXT_H4_OUTSIDE_WINDOW"] += 1
            continue
        if next_local.hour not in r4.V7_ANCHORS:
            counts[
                f"LARGE_FAIL_NEXT_H4_NOT_AUTHORIZED:{next_local.hour}"
            ] += 1
            by_market[symbol][
                f"LARGE_FAIL_NEXT_H4_NOT_AUTHORIZED:{next_local.hour}"
            ] += 1
            continue

        next_side = v7._daily_bias(
            indexed[symbol],
            before=next_open,
        )
        if next_side is not signal.side:
            counts["LARGE_FAIL_BIAS_CHANGED_OR_AMBIGUOUS"] += 1
            by_market[symbol][
                "LARGE_FAIL_BIAS_CHANGED_OR_AMBIGUOUS"
            ] += 1
            continue

        continuation = _next_h4_continuation(
            next_inside,
            side=signal.side,
            protected_swing=signal.protected_swing_extreme,
        )
        if continuation is None:
            counts["LARGE_FAIL_NO_NEXT_H4_CONTINUATION"] += 1
            by_market[symbol][
                "LARGE_FAIL_NO_NEXT_H4_CONTINUATION"
            ] += 1
            continue

        _index, continuation_at, entry = continuation
        row = RoutedExecution(
            symbol=symbol,
            continuation_at=continuation_at,
            side=signal.side,
            entry=entry,
            protected_swing=signal.protected_swing_extreme,
            route="LARGE_WICK_NEXT_H4",
            source_signal_at=signal.signal_at.astimezone(UTC),
            source_h4_opened_at=current_open,
            execution_h4_opened_at=next_open,
        )
        routed.setdefault(row.identity(), row)
        counts["LARGE_ROUTED_NEXT_H4"] += 1
        by_market[symbol]["LARGE_ROUTED_NEXT_H4"] += 1
        by_old_ps_state[old_ps_state]["LARGE_ROUTED_NEXT_H4"] += 1

    exact_count = len(routed)
    if window_id == "5Y":
        density_min = contract.FIVE_YEAR_TRADE_RANGE[0]
        density_max: int | None = contract.FIVE_YEAR_TRADE_RANGE[1]
        density_pass = density_min <= exact_count <= density_max
    elif window_id == "2Y":
        density_min = contract.TWO_YEAR_MIN_TRADES
        density_max = None
        density_pass = exact_count >= density_min
    else:
        density_min = 1000
        density_max = None
        density_pass = exact_count >= density_min

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "counts": dict(sorted(counts.items())),
        "exact_routed_execution_count": exact_count,
        "density_minimum": density_min,
        "density_maximum": density_max,
        "density_pass": density_pass,
        "by_market": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_market.items())
        },
        "by_old_r82_ps_state": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_old_ps_state.items())
        },
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r100.IDENTITY != (
        "VT08_INDEX_R100_CISD_PROTECTED_SWING_SEMANTICS_CORRECTION_001"
    ):
        raise ValueError("R101 R100 semantics drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r100": {
            "run_id": SOURCE_R100_RUN_ID,
            "artifact_id": SOURCE_R100_ARTIFACT_ID,
            "artifact_digest": SOURCE_R100_ARTIFACT_DIGEST,
        },
        "primary_sources": {
            "four_hour_power_of_three": TTRADES_PO3_URL,
            "wick_body": TTRADES_WICK_URL,
        },
        "routing_contract": {
            "primary_model": "D1_H4_M15",
            "standard_cisd_surface_preserved": True,
            "small_wick": "SAME_H4_CANONICAL_CONTINUATION",
            "large_wick": "IMMEDIATE_NEXT_H4_CONTINUATION",
            "equal_wick": "FAIL_CLOSED",
            "large_requires_swing_survival": True,
            "large_requires_bias_persistence": True,
            "large_requires_owner_authorized_next_h4": True,
            "positional_fallback": False,
            "later_h4_deferral": False,
            "pnl_evaluated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R101_STANDARD_CISD_WICK_ROUTING_DENSITY_CENSUS_COMPLETE_NO_PNL",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "future_information_used": False,
            "pnl_evaluated": False,
            "risk_changed": False,
            "target_changed": False,
            "anchors_changed": False,
            "numeric_wick_threshold_search": False,
            "market_or_anchor_selection_by_outcome": False,
            "candidate_created": False,
            "trader_certified": False,
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
                "five_year": {
                    "exact": report["five_year"][
                        "exact_routed_execution_count"
                    ],
                    "density_pass": report["five_year"]["density_pass"],
                    "counts": report["five_year"]["counts"],
                },
                "recent_two_year": {
                    "exact": report["recent_two_year"][
                        "exact_routed_execution_count"
                    ],
                    "density_pass": report["recent_two_year"]["density_pass"],
                    "counts": report["recent_two_year"]["counts"],
                },
                "r66": {
                    "exact": report["r66_failed_holdout"][
                        "exact_routed_execution_count"
                    ],
                    "density_pass": report["r66_failed_holdout"]["density_pass"],
                    "counts": report["r66_failed_holdout"]["counts"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
