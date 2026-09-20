"""VT08 Index R84 — source-exact Protected-Swing event census.

R82/R83 showed that the existing generic CISD scanner admits a large surface
that cannot be mechanically attributed to the Protected-Swing causes described
by TTrades, while R58 transports materially better on the source-qualified
subset.

R84 rebuilds the Protected-Swing *event layer* directly from the primary source
semantics, without creating trades or evaluating PnL.

Primary source contract frozen for this census:
- TTrades, "Protected Swings in Trading", 2025-08-06:
  bullish: run below a short-term low, then close above the down-close series
  that formed the low; bearish is the inverse. A second valid family is a
  reaction at a Fair Value Gap followed by a close through the candle series
  that created the reaction high/low.
- TTrades, "Intracandle CISD", 2026-06-13:
  price reaches a POI, takes liquidity forming a new high/low, closes back
  through the candles that made that high/low, then continuation is sought.

Mechanical interpretation, fixed before any economics:
1. The current frozen V7 daily bias and exact source POIs remain unchanged.
2. A short-term low/high is a causal three-M15 swing point: the middle bar is
   lower/higher than both neighbors and is known only after the right neighbor
   closes.
3. An opposing candle series is contiguous and uses the exact V6 close-through
   threshold: first opposing candle open, extreme across the series, first
   non-opposing bar closing through that open.
4. LIQUIDITY_SWEEP qualifies only if the series forms its protected extreme at
   or after the POI touch and crosses a previously known short-term swing level.
5. ORIGINAL_FVG_REACTION qualifies only when the exact source POI is an FVG,
   an opposing candle in the confirmed series trades into that FVG at/after
   the POI touch, and the series extreme is formed at/after that touch.
6. Events are deduplicated by market/H4/side/confirmation/extreme/family.

No continuation, entry, stop, target, risk or PnL is attached in R84. Event
counts are only an upper-bound census for a later source-faithful entry engine.
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
    vt08_index_r6_five_year_validation as r6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r83_ps_qualification_r58_transport as r83,
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

SCHEMA = "qore.trader_lab.vt08_index_r84_source_exact_ps_event_census.v1"
IDENTITY = "VT08_INDEX_R84_SOURCE_EXACT_PROTECTED_SWING_EVENT_CENSUS_001"

SOURCE_R83_RUN_ID = 35519881915

FAMILY_LIQUIDITY = "LIQUIDITY_SWEEP"
FAMILY_FVG = "ORIGINAL_FVG_REACTION"
FAMILY_BOTH = "BOTH"


@dataclass(frozen=True, slots=True)
class ConfirmedSeries:
    start_index: int
    end_index: int
    confirm_index: int
    series_open: Decimal
    extreme: Decimal
    extreme_index: int


@dataclass(frozen=True, slots=True)
class ProtectedSwingEvent:
    symbol: str
    h4_opened_at: datetime
    side: DemoTradingSetupSide
    confirmed_at: datetime
    protected_swing: Decimal
    series_open: Decimal
    family: str
    source_poi_kind: str
    poi_touch_at: datetime

    def identity(self) -> tuple[object, ...]:
        return (
            self.symbol,
            self.h4_opened_at.astimezone(UTC),
            self.side.value,
            self.confirmed_at.astimezone(UTC),
            self.protected_swing,
            self.family,
        )


def _short_term_swings(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
) -> tuple[tuple[int, Decimal, int], ...]:
    """Return (pivot_index, level, known_after_index) for causal ST liquidity."""
    result: list[tuple[int, Decimal, int]] = []
    for index in range(1, len(bars) - 1):
        left, middle, right = bars[index - 1 : index + 2]
        if (
            side is DemoTradingSetupSide.LONG
            and middle.low < left.low
            and middle.low < right.low
        ):
            result.append((index, middle.low, index + 1))
        elif (
            side is DemoTradingSetupSide.SHORT
            and middle.high > left.high
            and middle.high > right.high
        ):
            result.append((index, middle.high, index + 1))
    return tuple(result)


def _confirmed_opposing_series(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
) -> tuple[ConfirmedSeries, ...]:
    """Enumerate every exact-V6 contiguous opposing series that confirms."""
    result: list[ConfirmedSeries] = []
    start: int | None = None
    series_open: Decimal | None = None
    extreme: Decimal | None = None
    extreme_index: int | None = None

    for index, bar in enumerate(bars):
        opposing = (
            bar.close < bar.open
            if side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            if start is None:
                start = index
                series_open = bar.open
                extreme = (
                    bar.low
                    if side is DemoTradingSetupSide.LONG
                    else bar.high
                )
                extreme_index = index
            else:
                assert extreme is not None
                next_extreme = (
                    min(extreme, bar.low)
                    if side is DemoTradingSetupSide.LONG
                    else max(extreme, bar.high)
                )
                if next_extreme != extreme:
                    extreme = next_extreme
                    extreme_index = index
            continue

        if (
            start is not None
            and series_open is not None
            and extreme is not None
            and extreme_index is not None
        ):
            confirmed = (
                bar.close > series_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < series_open
            )
            if confirmed:
                result.append(
                    ConfirmedSeries(
                        start_index=start,
                        end_index=index - 1,
                        confirm_index=index,
                        series_open=series_open,
                        extreme=extreme,
                        extreme_index=extreme_index,
                    )
                )
        start = None
        series_open = None
        extreme = None
        extreme_index = None

    return tuple(result)


def _swept_known_short_term_liquidity(
    swings: Sequence[tuple[int, Decimal, int]],
    *,
    series: ConfirmedSeries,
    side: DemoTradingSetupSide,
    touch_index: int,
) -> bool:
    if series.extreme_index < touch_index:
        return False
    for _pivot_index, level, known_after_index in swings:
        if known_after_index >= series.extreme_index:
            continue
        if (
            side is DemoTradingSetupSide.LONG
            and series.extreme < level
        ):
            return True
        if (
            side is DemoTradingSetupSide.SHORT
            and series.extreme > level
        ):
            return True
    return False


def _original_fvg_reaction(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    poi: v6.SourcePoi,
    series: ConfirmedSeries,
    touch_index: int,
) -> bool:
    if poi.kind is not v6.PoiKind.FVG:
        return False
    if series.extreme_index < touch_index:
        return False
    start = max(series.start_index, touch_index)
    return any(
        poi.touched_by(bars[index])
        for index in range(start, series.end_index + 1)
    )


def _event_family(*, liquidity: bool, fvg: bool) -> str | None:
    if liquidity and fvg:
        return FAMILY_BOTH
    if liquidity:
        return FAMILY_LIQUIDITY
    if fvg:
        return FAMILY_FVG
    return None


def _market(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: Any,
    end_date: Any,
) -> dict[str, Any]:
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in bars
    }
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}

    events: dict[tuple[object, ...], ProtectedSwingEvent] = {}
    counts: Counter[str] = Counter()
    by_anchor: dict[str, Counter[str]] = {}
    by_poi: dict[str, Counter[str]] = {}

    for opened in h4_keys:
        local = opened.astimezone(v7._NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(
                indexed,
                before=opened,
            )
        side = side_cache[local_date]
        if side is None:
            continue

        pois = r6._source_pois_fast(
            indexed,
            h4,
            h4_keys,
            h4_opened_at=opened,
            side=side,
        )
        if not pois:
            continue
        inside = r6._bars_between_fast(
            indexed,
            start=opened,
            end=h4[opened].closed_at,
        )
        if not inside:
            continue

        swings = _short_term_swings(inside, side=side)
        series_rows = _confirmed_opposing_series(inside, side=side)
        anchor = str(local.hour)
        by_anchor.setdefault(anchor, Counter())

        for poi in pois:
            poi_key = poi.kind.value
            by_poi.setdefault(poi_key, Counter())
            touches = r4._touch_indices(
                inside,
                poi,
                start_index=0,
            )
            if not touches:
                continue

            for touch_index in touches:
                counts["poi_touches"] += 1
                for series in series_rows:
                    if series.confirm_index <= touch_index:
                        continue
                    liquidity = _swept_known_short_term_liquidity(
                        swings,
                        series=series,
                        side=side,
                        touch_index=touch_index,
                    )
                    fvg = _original_fvg_reaction(
                        inside,
                        poi=poi,
                        series=series,
                        touch_index=touch_index,
                    )
                    family = _event_family(
                        liquidity=liquidity,
                        fvg=fvg,
                    )
                    if family is None:
                        continue

                    event = ProtectedSwingEvent(
                        symbol=symbol,
                        h4_opened_at=opened,
                        side=side,
                        confirmed_at=inside[
                            series.confirm_index
                        ].closed_at.astimezone(UTC),
                        protected_swing=series.extreme,
                        series_open=series.series_open,
                        family=family,
                        source_poi_kind=poi_key,
                        poi_touch_at=inside[
                            touch_index
                        ].opened_at.astimezone(UTC),
                    )
                    events.setdefault(event.identity(), event)

    for event in events.values():
        counts["source_ps_events"] += 1
        counts[event.family] += 1
        anchor = str(event.h4_opened_at.astimezone(v7._NY).hour)
        by_anchor.setdefault(anchor, Counter())[event.family] += 1
        by_poi.setdefault(event.source_poi_kind, Counter())[
            event.family
        ] += 1

    return {
        "symbol": symbol,
        "counts": dict(sorted(counts.items())),
        "by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_anchor.items())
        },
        "by_source_poi_family": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_poi.items())
        },
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    _stream, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, canonical_sample = r74._window_contract(window_id)

    markets = {
        symbol: _market(
            symbol=symbol,
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        for symbol in contract.MARKETS
    }
    totals: Counter[str] = Counter()
    for row in markets.values():
        totals.update(row["counts"])

    return {
        "window_id": window_id,
        "canonical_signal_sample_reference": canonical_sample,
        "source_ps_event_count": int(totals["source_ps_events"]),
        "source_ps_events_per_canonical_signal": str(
            Decimal(totals["source_ps_events"])
            / Decimal(canonical_sample)
        ),
        "totals": dict(sorted(totals.items())),
        "by_market": markets,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R84 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R84 source failure decision drift")
    if r83.IDENTITY != (
        "VT08_INDEX_R83_PROTECTED_SWING_QUALIFICATION_R58_TRANSPORT_001"
    ):
        raise ValueError("R84 R83 identity drift")

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
        "source_r83": {
            "identity": r83.IDENTITY,
            "run_id": SOURCE_R83_RUN_ID,
        },
        "source_contract": {
            "protected_swing_primary_source_date": "2025-08-06",
            "ic_cisd_primary_source_date": "2026-06-13",
            "short_term_liquidity": (
                "causal three-M15 swing point known only after right neighbor"
            ),
            "opposing_series": (
                "contiguous exact-V6 direction-opposing candle series"
            ),
            "confirmation": (
                "first non-opposing close through first opposing-series open"
            ),
            "liquidity_sweep_requires_post_touch_extreme": True,
            "fvg_reaction_uses_exact_original_source_fvg": True,
            "numeric_separation_threshold": None,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R84_SOURCE_EXACT_PS_EVENT_CENSUS_COMPLETE_NO_TRADES_CREATED",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "provider_observations_only": True,
            "future_information_used": False,
            "pnl_evaluated": False,
            "continuation_required": False,
            "entries_created": False,
            "signals_created": False,
            "signals_suppressed": False,
            "risk_changed": False,
            "target_changed": False,
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
                    "events": report["five_year"]["source_ps_event_count"],
                    "ratio": report["five_year"][
                        "source_ps_events_per_canonical_signal"
                    ],
                    "totals": report["five_year"]["totals"],
                },
                "recent_two_year": {
                    "events": report["recent_two_year"][
                        "source_ps_event_count"
                    ],
                    "ratio": report["recent_two_year"][
                        "source_ps_events_per_canonical_signal"
                    ],
                    "totals": report["recent_two_year"]["totals"],
                },
                "r66": {
                    "events": report["r66_failed_holdout"][
                        "source_ps_event_count"
                    ],
                    "ratio": report["r66_failed_holdout"][
                        "source_ps_events_per_canonical_signal"
                    ],
                    "totals": report["r66_failed_holdout"]["totals"],
                    "by_market": report["r66_failed_holdout"]["by_market"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
