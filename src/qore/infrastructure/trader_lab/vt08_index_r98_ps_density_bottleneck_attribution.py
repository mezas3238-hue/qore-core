"""VT08 Index R98 — Protected-Swing density bottleneck attribution.

This is a no-PnL causal census designed to identify *where* the primary
D1->H4->M15 model loses density.

Source issue under test
-----------------------
R84's liquidity-sweep Protected Swing is already lower-timeframe structural:
after the H4 POI touch, an M15 opposing series may sweep a known short-term
swing and then close through its series open.

R84's FVG Protected Swing is materially narrower: it only qualifies when the
*original H4 source POI itself* is an FVG and the opposing M15 series reacts
to that same H4 FVG.

Primary TTrades Protected Swing material does not define the FVG method that
narrowly. It says price trades into a fair value gap and then closes through
the candle series that created the low/high. Ideal Formation material also
separates the meaningful POI (reason for reaction) from Protected Swing
confirmation on the execution timeframe.

R98 therefore does not create a candidate. It measures the funnel:
daily bias -> H4 source POI -> POI touch -> post-touch opposing-series close
-> R84 liquidity PS / R84 original-H4-FVG PS -> causal intra-H4 M15-FVG PS
-> exact continuation.

The M15-FVG alternative is purely causal:
- FVG must be observable before it is touched;
- its reaction must occur after the H4 POI touch;
- no future information, PnL, target, risk, market or anchor selection is used.

If causal M15-FVG qualification materially closes the R84/R85 density gap,
that is evidence that the existing FVG qualification is implementation-narrow,
not evidence to promote a strategy. Economic testing remains forbidden here.
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
    vt08_index_r84_source_exact_ps_event_census as r84,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r86_dynamic_m15_fvg_rearm as r86,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r97_persistent_ps_lifecycle as r97,
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

SCHEMA = "qore.trader_lab.vt08_index_r98_ps_density_bottleneck_attribution.v1"
IDENTITY = "VT08_INDEX_R98_PROTECTED_SWING_DENSITY_BOTTLENECK_ATTRIBUTION_001"

SOURCE_R97_RUN_ID = 35535136703
SOURCE_R97_ARTIFACT_ID = 10613125272
SOURCE_R97_ARTIFACT_DIGEST = (
    "sha256:97864b91f41ff6578d5c16ebb98a88559795e2698110cb7297d4afad949eebf7"
)

TTRADES_PROTECTED_SWING_URL = (
    "https://ttrades.com/"
    "protected-swings-understanding-trends-and-invalidations/"
)
TTRADES_IDEAL_FORMATION_URL = (
    "https://ttrades.com/"
    "ttrades-ideal-formation-high-probability-swing-points/"
)


@dataclass(frozen=True, slots=True)
class SeriesQualification:
    confirm_index: int
    protected_swing: Decimal
    liquidity: bool
    original_h4_fvg: bool
    causal_m15_fvg: bool

    def generic_identity(self) -> tuple[object, ...]:
        return (self.confirm_index, self.protected_swing)


def _causal_m15_fvg_reaction(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    series: r84.ConfirmedSeries,
    h4_touch_index: int,
) -> bool:
    """Whether any causally known M15 FVG reacts after the H4 POI touch."""
    fvgs = r86._directional_fvgs(
        bars,
        side=side,
        earliest_formed_index=2,
    )
    for fvg in fvgs:
        poi = fvg.as_source_poi(bars)
        first_possible_touch = max(
            h4_touch_index,
            fvg.formed_index + 1,
        )
        if first_possible_touch > series.end_index:
            continue
        for touch_index in range(
            first_possible_touch,
            series.end_index + 1,
        ):
            if not poi.touched_by(bars[touch_index]):
                continue
            if r84._original_fvg_reaction(
                bars,
                poi=poi,
                series=series,
                touch_index=touch_index,
            ):
                return True
    return False


def _executable_from_series(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    h4_bar: Vt08IndexC2R1Bar,
    model_kind: v6.H4ModelKind,
    side: DemoTradingSetupSide,
    series: r84.ConfirmedSeries,
) -> tuple[int, datetime, Decimal] | None:
    continuation_index = v6._first_continuation(
        bars,
        side=side,
        start_index=series.confirm_index + 1,
        protected_swing=series.extreme,
    )
    if continuation_index is None:
        return None
    continuation = bars[continuation_index]
    entry = continuation.close
    if model_kind is v6.H4ModelKind.SAME_C2:
        in_body = (
            entry > h4_bar.open
            if side is DemoTradingSetupSide.LONG
            else entry < h4_bar.open
        )
        if not in_body:
            return None
    risk = (
        entry - series.extreme
        if side is DemoTradingSetupSide.LONG
        else series.extreme - entry
    )
    if risk <= 0:
        return None
    return (
        continuation_index,
        continuation.closed_at.astimezone(UTC),
        entry,
    )


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

    counts: Counter[str] = Counter()
    by_anchor: dict[str, Counter[str]] = {}

    generic_series: set[tuple[object, ...]] = set()
    baseline_ps: set[tuple[object, ...]] = set()
    decoupled_ps: set[tuple[object, ...]] = set()
    generic_exec: set[tuple[object, ...]] = set()
    baseline_exec: set[tuple[object, ...]] = set()
    decoupled_exec: set[tuple[object, ...]] = set()
    dynamic_only_ps: set[tuple[object, ...]] = set()
    dynamic_only_exec: set[tuple[object, ...]] = set()

    for opened in h4_keys:
        local = opened.astimezone(v7._NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        counts["H4_AUTHORIZED"] += 1
        anchor = str(local.hour)
        by_anchor.setdefault(anchor, Counter())["H4_AUTHORIZED"] += 1

        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(
                indexed,
                before=opened,
            )
        side = side_cache[local_date]
        if side is None:
            counts["H4_NO_BIAS"] += 1
            by_anchor[anchor]["H4_NO_BIAS"] += 1
            continue
        counts["H4_WITH_BIAS"] += 1
        by_anchor[anchor]["H4_WITH_BIAS"] += 1

        pois = r6._source_pois_fast(
            indexed,
            h4,
            h4_keys,
            h4_opened_at=opened,
            side=side,
        )
        if not pois:
            counts["H4_NO_SOURCE_POI"] += 1
            by_anchor[anchor]["H4_NO_SOURCE_POI"] += 1
            continue
        counts["H4_WITH_SOURCE_POI"] += 1
        by_anchor[anchor]["H4_WITH_SOURCE_POI"] += 1

        inside = r6._bars_between_fast(
            indexed,
            start=opened,
            end=h4[opened].closed_at,
        )
        if not inside:
            counts["H4_NO_M15"] += 1
            continue

        model_kind = r6._completed_h4_model_fast(
            indexed,
            h4,
            h4_keys,
            current_h4_open=opened,
            side=side,
        )
        if model_kind is None:
            model_kind = v6.H4ModelKind.SAME_C2

        swings = r84._short_term_swings(inside, side=side)
        series_rows = r84._confirmed_opposing_series(
            inside,
            side=side,
        )

        h4_had_touch = False
        h4_had_post_touch_series = False
        h4_had_baseline_ps = False
        h4_had_decoupled_ps = False
        h4_had_generic_exec = False
        h4_had_baseline_exec = False
        h4_had_decoupled_exec = False

        for poi in pois:
            touches = r4._touch_indices(
                inside,
                poi,
                start_index=0,
            )
            if not touches:
                continue
            h4_had_touch = True
            for touch_index in touches:
                counts["POI_TOUCH_INSTANCES"] += 1
                for series in series_rows:
                    if series.confirm_index <= touch_index:
                        continue
                    h4_had_post_touch_series = True

                    generic_id = (
                        symbol,
                        opened.astimezone(UTC),
                        series.confirm_index,
                        series.extreme,
                    )
                    generic_series.add(generic_id)

                    liquidity = r84._swept_known_short_term_liquidity(
                        swings,
                        series=series,
                        side=side,
                        touch_index=touch_index,
                    )
                    original_h4_fvg = r84._original_fvg_reaction(
                        inside,
                        poi=poi,
                        series=series,
                        touch_index=touch_index,
                    )
                    causal_m15_fvg = _causal_m15_fvg_reaction(
                        inside,
                        side=side,
                        series=series,
                        h4_touch_index=touch_index,
                    )

                    baseline_qualified = liquidity or original_h4_fvg
                    decoupled_qualified = liquidity or causal_m15_fvg

                    ps_id = (
                        symbol,
                        opened.astimezone(UTC),
                        inside[series.confirm_index].closed_at.astimezone(UTC),
                        side.value,
                        series.extreme,
                    )
                    if baseline_qualified:
                        baseline_ps.add(ps_id)
                        h4_had_baseline_ps = True
                    if decoupled_qualified:
                        decoupled_ps.add(ps_id)
                        h4_had_decoupled_ps = True
                    if (
                        causal_m15_fvg
                        and not baseline_qualified
                    ):
                        dynamic_only_ps.add(ps_id)

                    executable = _executable_from_series(
                        inside,
                        h4_bar=h4[opened],
                        model_kind=model_kind,
                        side=side,
                        series=series,
                    )
                    if executable is None:
                        continue
                    _continuation_index, continuation_at, entry = executable
                    exec_id = (
                        symbol,
                        continuation_at,
                        side.value,
                        entry,
                        series.extreme,
                    )
                    generic_exec.add(exec_id)
                    h4_had_generic_exec = True
                    if baseline_qualified:
                        baseline_exec.add(exec_id)
                        h4_had_baseline_exec = True
                    if decoupled_qualified:
                        decoupled_exec.add(exec_id)
                        h4_had_decoupled_exec = True
                    if causal_m15_fvg and not baseline_qualified:
                        dynamic_only_exec.add(exec_id)

        if h4_had_touch:
            counts["H4_WITH_POI_TOUCH"] += 1
            by_anchor[anchor]["H4_WITH_POI_TOUCH"] += 1
        else:
            counts["H4_POI_UNTOUCHED"] += 1
            by_anchor[anchor]["H4_POI_UNTOUCHED"] += 1
        if h4_had_post_touch_series:
            counts["H4_WITH_POST_TOUCH_CISD_SERIES"] += 1
            by_anchor[anchor]["H4_WITH_POST_TOUCH_CISD_SERIES"] += 1
        if h4_had_baseline_ps:
            counts["H4_WITH_R84_PS"] += 1
            by_anchor[anchor]["H4_WITH_R84_PS"] += 1
        if h4_had_decoupled_ps:
            counts["H4_WITH_DECOUPLED_PS"] += 1
            by_anchor[anchor]["H4_WITH_DECOUPLED_PS"] += 1
        if h4_had_generic_exec:
            counts["H4_WITH_GENERIC_EXECUTABLE"] += 1
            by_anchor[anchor]["H4_WITH_GENERIC_EXECUTABLE"] += 1
        if h4_had_baseline_exec:
            counts["H4_WITH_R84_EXECUTABLE"] += 1
            by_anchor[anchor]["H4_WITH_R84_EXECUTABLE"] += 1
        if h4_had_decoupled_exec:
            counts["H4_WITH_DECOUPLED_EXECUTABLE"] += 1
            by_anchor[anchor]["H4_WITH_DECOUPLED_EXECUTABLE"] += 1

    counts["GENERIC_POST_TOUCH_SERIES_EVENTS"] = len(generic_series)
    counts["R84_BASELINE_PS_EVENTS"] = len(baseline_ps)
    counts["DECOUPLED_M15_PS_EVENTS"] = len(decoupled_ps)
    counts["M15_FVG_ONLY_INCREMENTAL_PS_EVENTS"] = len(dynamic_only_ps)
    counts["GENERIC_EXECUTABLES"] = len(generic_exec)
    counts["R84_BASELINE_EXECUTABLES"] = len(baseline_exec)
    counts["DECOUPLED_M15_EXECUTABLES"] = len(decoupled_exec)
    counts["M15_FVG_ONLY_INCREMENTAL_EXECUTABLES"] = len(dynamic_only_exec)

    return {
        "symbol": symbol,
        "counts": dict(sorted(counts.items())),
        "by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_anchor.items())
        },
    }


def _losses(totals: Counter[str]) -> dict[str, int]:
    return {
        "bias_loss": (
            int(totals["H4_AUTHORIZED"])
            - int(totals["H4_WITH_BIAS"])
        ),
        "poi_availability_loss_after_bias": (
            int(totals["H4_WITH_BIAS"])
            - int(totals["H4_WITH_SOURCE_POI"])
        ),
        "poi_touch_loss_after_poi": (
            int(totals["H4_WITH_SOURCE_POI"])
            - int(totals["H4_WITH_POI_TOUCH"])
        ),
        "post_touch_series_loss_after_touch": (
            int(totals["H4_WITH_POI_TOUCH"])
            - int(totals["H4_WITH_POST_TOUCH_CISD_SERIES"])
        ),
        "r84_ps_qualification_loss_after_series": (
            int(totals["H4_WITH_POST_TOUCH_CISD_SERIES"])
            - int(totals["H4_WITH_R84_PS"])
        ),
        "decoupled_ps_qualification_loss_after_series": (
            int(totals["H4_WITH_POST_TOUCH_CISD_SERIES"])
            - int(totals["H4_WITH_DECOUPLED_PS"])
        ),
        "r84_continuation_loss_after_ps": (
            int(totals["H4_WITH_R84_PS"])
            - int(totals["H4_WITH_R84_EXECUTABLE"])
        ),
        "decoupled_continuation_loss_after_ps": (
            int(totals["H4_WITH_DECOUPLED_PS"])
            - int(totals["H4_WITH_DECOUPLED_EXECUTABLE"])
        ),
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
    start_date, end_date, canonical_reference = r74._window_contract(window_id)
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

    baseline = int(totals["R84_BASELINE_EXECUTABLES"])
    decoupled = int(totals["DECOUPLED_M15_EXECUTABLES"])
    generic = int(totals["GENERIC_EXECUTABLES"])

    if window_id == "5Y":
        density_min = contract.FIVE_YEAR_TRADE_RANGE[0]
        density_max: int | None = contract.FIVE_YEAR_TRADE_RANGE[1]
    else:
        density_min = 1000
        density_max = None

    return {
        "window_id": window_id,
        "canonical_signal_reference": canonical_reference,
        "funnel_totals": dict(sorted(totals.items())),
        "sequential_h4_losses": _losses(totals),
        "execution_surfaces": {
            "generic_post_touch_cisd_continuation": generic,
            "r84_baseline_ps_continuation": baseline,
            "decoupled_m15_ps_continuation": decoupled,
            "incremental_from_decoupled_m15_fvg": decoupled - baseline,
        },
        "density_reference": {
            "minimum": density_min,
            "maximum": density_max,
            "generic_reaches_minimum": generic >= density_min,
            "baseline_reaches_minimum": baseline >= density_min,
            "decoupled_reaches_minimum": decoupled >= density_min,
        },
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
        raise ValueError("R98 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R98 source failure decision drift")
    if r97.IDENTITY != (
        "VT08_INDEX_R97_PERSISTENT_PROTECTED_SWING_LIFECYCLE_001"
    ):
        raise ValueError("R98 R97 identity drift")
    if 14 in r4.V7_ANCHORS or 18 in r4.V7_ANCHORS:
        raise ValueError("R98 execution anchor contract drift")

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
        "source_r97": {
            "run_id": SOURCE_R97_RUN_ID,
            "artifact_id": SOURCE_R97_ARTIFACT_ID,
            "artifact_digest": SOURCE_R97_ARTIFACT_DIGEST,
        },
        "primary_sources": {
            "protected_swings": TTRADES_PROTECTED_SWING_URL,
            "ideal_formation": TTRADES_IDEAL_FORMATION_URL,
        },
        "attribution_contract": {
            "primary_model": "D1_H4_M15",
            "r84_liquidity_rule_unchanged": True,
            "r84_original_h4_fvg_rule_measured": True,
            "causal_m15_fvg_alternative_measured": True,
            "m15_fvg_must_exist_before_reaction_touch": True,
            "m15_fvg_reaction_must_follow_h4_poi_touch": True,
            "generic_cisd_control_measured": True,
            "pnl_evaluated": False,
            "candidate_created": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R98_PS_DENSITY_BOTTLENECK_ATTRIBUTION_COMPLETE_NO_TRADES",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "future_information_used": False,
            "pnl_evaluated": False,
            "risk_changed": False,
            "target_changed": False,
            "anchors_changed": False,
            "numeric_threshold_search": False,
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
                "five_year": report["five_year"]["execution_surfaces"],
                "five_year_losses": report["five_year"]["sequential_h4_losses"],
                "recent_two_year": report["recent_two_year"]["execution_surfaces"],
                "recent_two_year_losses": report["recent_two_year"]["sequential_h4_losses"],
                "r66": report["r66_failed_holdout"]["execution_surfaces"],
                "r66_losses": report["r66_failed_holdout"]["sequential_h4_losses"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
