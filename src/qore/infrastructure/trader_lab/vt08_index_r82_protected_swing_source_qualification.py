"""VT08 Index R82 — Protected-Swing source qualification audit.

R81 falsified an incorrect interpretation of the source FVG-reaction family:
it required a *new* directional FVG to form after the original POI touch.

Primary TTrades material is clearer:
- CISD requires price to reach a POI, take liquidity forming a new high/low,
  then close back through the candles that made that high/low;
- a Protected Swing may form when price reaches an important level such as an
  FVG/high/low and closes through the candle series into that level.

R82 does not create, remove or rescore any signal. It classifies the exact
canonical source-complete surface into causal, pre-entry Protected-Swing
qualification families:

1. LIQUIDITY_SWEEP:
   the canonical opposing series forms a new intrabar H4 extreme relative to
   all earlier observed M15 bars in that same H4 before the series began.

2. ORIGINAL_FVG_REACTION:
   the canonical source POI itself is an FVG and the opposing series that
   creates the canonical CISD is born while physically overlapping that FVG.

3. BOTH.

4. UNQUALIFIED_GENERIC_CISD:
   neither source-observable condition is present.

The classification uses only bars available by the canonical CISD confirmation
time and reproduces the exact current V6 first-CISD reset semantics. Economic
summaries are diagnostic only; they do not select a family or create a rule.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
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
    vt08_index_r81_fvg_reaction_protected_swing as r81,
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

SCHEMA = "qore.trader_lab.vt08_index_r82_protected_swing_source_qualification.v1"
IDENTITY = "VT08_INDEX_R82_PROTECTED_SWING_SOURCE_QUALIFICATION_AUDIT_001"

SOURCE_R81_RUN_ID = 35519062875
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")

FAMILY_LIQUIDITY = "LIQUIDITY_SWEEP"
FAMILY_FVG = "ORIGINAL_FVG_REACTION"
FAMILY_BOTH = "BOTH"
FAMILY_UNQUALIFIED = "UNQUALIFIED_GENERIC_CISD"
FAMILIES = (
    FAMILY_LIQUIDITY,
    FAMILY_FVG,
    FAMILY_BOTH,
    FAMILY_UNQUALIFIED,
)


def _cisd_trace(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    start_index: int,
) -> tuple[int, int, Decimal, Decimal] | None:
    """Exact V6 CISD semantics plus causal opposing-series start index."""
    sequence_open: Decimal | None = None
    extreme: Decimal | None = None
    sequence_start: int | None = None
    in_sequence = False

    for index in range(start_index, len(bars)):
        bar = bars[index]
        opposing = (
            bar.close < bar.open
            if side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            if not in_sequence:
                sequence_open = bar.open
                extreme = (
                    bar.low
                    if side is DemoTradingSetupSide.LONG
                    else bar.high
                )
                sequence_start = index
            else:
                assert extreme is not None
                extreme = (
                    min(extreme, bar.low)
                    if side is DemoTradingSetupSide.LONG
                    else max(extreme, bar.high)
                )
            in_sequence = True
            continue

        if (
            in_sequence
            and sequence_open is not None
            and extreme is not None
            and sequence_start is not None
        ):
            confirmed = (
                bar.close > sequence_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < sequence_open
            )
            if confirmed:
                return index, sequence_start, sequence_open, extreme

        sequence_open = None
        extreme = None
        sequence_start = None
        in_sequence = False

    return None


def _liquidity_sweep_qualified(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    sequence_start: int,
    protected_swing: Decimal,
) -> bool:
    """Did the source series form a new M15 extreme inside the current H4?"""
    prior = bars[:sequence_start]
    if not prior:
        return False
    if side is DemoTradingSetupSide.LONG:
        return protected_swing < min(bar.low for bar in prior)
    return protected_swing > max(bar.high for bar in prior)


def _fvg_reaction_qualified(
    *,
    poi: v6.SourcePoi,
    series_start_bar: Vt08IndexC2R1Bar,
) -> bool:
    return (
        poi.kind is v6.PoiKind.FVG
        and poi.touched_by(series_start_bar)
    )


def _family(
    *,
    liquidity: bool,
    fvg_reaction: bool,
) -> str:
    if liquidity and fvg_reaction:
        return FAMILY_BOTH
    if liquidity:
        return FAMILY_LIQUIDITY
    if fvg_reaction:
        return FAMILY_FVG
    return FAMILY_UNQUALIFIED


def _h4_bar_cache(
    bars: Sequence[Vt08IndexC2R1Bar],
) -> dict[datetime, tuple[Vt08IndexC2R1Bar, ...]]:
    """Materialize each complete H4's M15 bars once per market."""
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in bars
    }
    h4 = v6._build_h4(indexed)
    cache: dict[datetime, tuple[Vt08IndexC2R1Bar, ...]] = {}
    for opened, h4_bar in h4.items():
        cursor = opened.astimezone(UTC)
        rows: list[Vt08IndexC2R1Bar] = []
        while cursor < h4_bar.closed_at.astimezone(UTC):
            bar = indexed.get(cursor)
            if bar is None:
                raise ValueError("R82 complete H4 lost an M15 constituent")
            rows.append(bar)
            cursor += timedelta(minutes=15)
        cache[opened.astimezone(UTC)] = tuple(rows)
    return cache


def _classify_opportunity(
    opportunity: Any,
    *,
    h4_bars: dict[datetime, tuple[Vt08IndexC2R1Bar, ...]],
) -> dict[str, Any]:
    signal = opportunity.signal
    inside = h4_bars.get(signal.h4_opened_at.astimezone(UTC))
    if inside is None:
        raise ValueError("R82 missing canonical H4")
    touch_index = next(
        (
            index
            for index, bar in enumerate(inside)
            if bar.opened_at.astimezone(UTC)
            == opportunity.poi_touch_at.astimezone(UTC)
        ),
        None,
    )
    if touch_index is None:
        raise ValueError("R82 canonical POI touch not found")

    trace = _cisd_trace(
        inside,
        side=signal.side,
        start_index=touch_index,
    )
    if trace is None:
        raise ValueError("R82 canonical CISD trace missing")
    cisd_index, sequence_start, sequence_open, protected_swing = trace

    if inside[cisd_index].closed_at != signal.cisd_confirmed_at:
        raise ValueError("R82 CISD confirmation drift")
    if sequence_open != signal.cisd_level:
        raise ValueError("R82 CISD level drift")
    if protected_swing != signal.protected_swing_extreme:
        raise ValueError("R82 Protected-Swing extreme drift")

    liquidity = _liquidity_sweep_qualified(
        inside,
        side=signal.side,
        sequence_start=sequence_start,
        protected_swing=protected_swing,
    )
    fvg_reaction = _fvg_reaction_qualified(
        poi=signal.poi,
        series_start_bar=inside[sequence_start],
    )
    local = signal.signal_at.astimezone(v7._NY)
    return {
        "family": _family(
            liquidity=liquidity,
            fvg_reaction=fvg_reaction,
        ),
        "liquidity_sweep": liquidity,
        "original_fvg_reaction": fvg_reaction,
        "market": str(signal.symbol),
        "side": signal.side.value,
        "anchor": str(
            signal.h4_opened_at.astimezone(v7._NY).hour
        ),
        "source_poi_family": signal.poi.kind.value,
        "signal_date": local.date().isoformat(),
        "series_start_index": sequence_start,
        "cisd_index": cisd_index,
    }


def _metrics(
    rows: Sequence[tuple[Any, Any]],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    return r74._metrics(rows, stress=stress)


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    stream, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    _start, _end, expected = r74._window_contract(window_id)
    if len(stream) != expected:
        raise ValueError(f"R82 {window_id} canonical sample drift")

    grouped: dict[str, list[tuple[Any, Any]]] = defaultdict(list)
    counts: Counter[str] = Counter()
    by_market: dict[str, Counter[str]] = {
        symbol: Counter()
        for symbol in contract.MARKETS
    }
    by_anchor: dict[str, Counter[str]] = defaultdict(Counter)
    by_poi: dict[str, Counter[str]] = defaultdict(Counter)

    h4_bars_by_symbol = {
        symbol: _h4_bar_cache(bars_by_symbol[symbol])
        for symbol in contract.MARKETS
    }

    for opportunity, outcome in stream:
        symbol = str(opportunity.signal.symbol)
        classification = _classify_opportunity(
            opportunity,
            h4_bars=h4_bars_by_symbol[symbol],
        )
        family = str(classification["family"])
        grouped[family].append((opportunity, outcome))
        counts[family] += 1
        by_market[symbol][family] += 1
        by_anchor[str(classification["anchor"])][family] += 1
        by_poi[str(classification["source_poi_family"])][family] += 1

    if sum(counts.values()) != expected:
        raise ValueError(f"R82 {window_id} classification count drift")

    qualified = (
        grouped[FAMILY_LIQUIDITY]
        + grouped[FAMILY_FVG]
        + grouped[FAMILY_BOTH]
    )
    unqualified = grouped[FAMILY_UNQUALIFIED]

    family_reports = {
        family: {
            "sample": len(grouped[family]),
            "fraction_of_canonical": str(
                Decimal(len(grouped[family])) / Decimal(expected)
            ),
            "primary": _metrics(
                grouped[family],
                stress=PRIMARY_STRESS,
            ),
            "secondary": _metrics(
                grouped[family],
                stress=SECONDARY_STRESS,
            ),
        }
        for family in FAMILIES
    }

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "family_counts": {
            family: int(counts[family])
            for family in FAMILIES
        },
        "source_qualified_count": len(qualified),
        "source_qualified_fraction": str(
            Decimal(len(qualified)) / Decimal(expected)
        ),
        "unqualified_generic_count": len(unqualified),
        "unqualified_generic_fraction": str(
            Decimal(len(unqualified)) / Decimal(expected)
        ),
        "qualified_union": {
            "primary": _metrics(
                qualified,
                stress=PRIMARY_STRESS,
            ),
            "secondary": _metrics(
                qualified,
                stress=SECONDARY_STRESS,
            ),
        },
        "unqualified_generic": {
            "primary": _metrics(
                unqualified,
                stress=PRIMARY_STRESS,
            ),
            "secondary": _metrics(
                unqualified,
                stress=SECONDARY_STRESS,
            ),
        },
        "families": family_reports,
        "by_market": {
            symbol: dict(sorted(counter.items()))
            for symbol, counter in sorted(by_market.items())
        },
        "by_anchor": {
            anchor: dict(sorted(counter.items()))
            for anchor, counter in sorted(by_anchor.items())
        },
        "by_source_poi_family": {
            poi: dict(sorted(counter.items()))
            for poi, counter in sorted(by_poi.items())
        },
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R82 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R82 source failure decision drift")
    if r81.IDENTITY != (
        "VT08_INDEX_R81_FVG_REACTION_PROTECTED_SWING_RECOVERY_001"
    ):
        raise ValueError("R82 R81 identity drift")

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
        "source_r81": {
            "identity": r81.IDENTITY,
            "run_id": SOURCE_R81_RUN_ID,
            "post_touch_new_fvg_interpretation_survived": False,
        },
        "source_contract": {
            "cisd_requires_poi": True,
            "cisd_requires_liquidity_new_high_or_low": True,
            "cisd_requires_close_through_series": True,
            "fvg_reaction_uses_original_important_level": True,
            "liquidity_sweep_definition": (
                "canonical opposing series extreme forms a new M15 high/low "
                "relative to every earlier M15 bar in the same H4"
            ),
            "original_fvg_reaction_definition": (
                "canonical source POI is FVG and canonical opposing series "
                "starts while overlapping that FVG"
            ),
            "no_numeric_thresholds": True,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R82_PROTECTED_SWING_SOURCE_QUALIFICATION_AUDIT_COMPLETE_NO_RULE",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "future_information_used": False,
            "canonical_signal_surface_changed": False,
            "signals_created": False,
            "signals_suppressed": False,
            "family_selected_by_pnl": False,
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
                    key: report["five_year"][key]
                    for key in (
                        "canonical_sample",
                        "family_counts",
                        "source_qualified_count",
                        "source_qualified_fraction",
                        "unqualified_generic_count",
                        "unqualified_generic_fraction",
                        "qualified_union",
                        "unqualified_generic",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "canonical_sample",
                        "family_counts",
                        "source_qualified_count",
                        "source_qualified_fraction",
                        "unqualified_generic_count",
                        "unqualified_generic_fraction",
                        "qualified_union",
                        "unqualified_generic",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "canonical_sample",
                        "family_counts",
                        "source_qualified_count",
                        "source_qualified_fraction",
                        "unqualified_generic_count",
                        "unqualified_generic_fraction",
                        "qualified_union",
                        "unqualified_generic",
                    )
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
