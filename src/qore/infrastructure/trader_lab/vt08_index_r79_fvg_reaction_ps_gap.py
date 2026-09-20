"""VT08 Index R79 — FVG-reaction Protected-Swing gap forensics.

The frozen TTrades source-parity audit states that a Protected Swing may arise
from a liquidity sweep OR an FVG reaction. The current VT08 source-complete
scanner mechanically models the opposing-series CISD path but does not contain a
separately frozen FVG-reaction Protected-Swing constructor.

R79 does NOT invent that missing constructor. It measures a narrower observable
fact on consumed evidence only:

For each exact executable H4, frozen V7 daily bias and exact source POI, inspect
its first causal POI touch. When the canonical V6 first-CISD scanner cannot
confirm from that touch, ask whether the remaining current-H4 M15 sequence:
1) forms a direction-consistent three-candle FVG after the touch; and
2) later retests that FVG in an observed provider M15 bar.

This is a mechanical gap census only. An FVG+retest is NOT labelled a Protected
Swing, does not create a signal, and has no PnL attached. The purpose is to
decide whether the source-authorized second Protected-Swing family is materially
present before a separate rule freeze is attempted.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
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
    vt08_index_r78_persistent_cisd_series as r78,
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

SCHEMA = "qore.trader_lab.vt08_index_r79_fvg_reaction_ps_gap.v1"
IDENTITY = "VT08_INDEX_R79_FVG_REACTION_PROTECTED_SWING_GAP_FORENSICS_001"

SOURCE_R78_RUN_ID = 35515878213
SOURCE_R78_ARTIFACT_ID = 10606817895
SOURCE_R78_ARTIFACT_DIGEST = (
    "sha256:43277175cb7f6adb8464d58ed5811ba7aa8fcafbccebefc5029c72568abf5813"
)


@dataclass(frozen=True, slots=True)
class DirectionalFvg:
    low: Decimal
    high: Decimal
    formed_index: int

    def touched_by(self, bar: Vt08IndexC2R1Bar) -> bool:
        return bar.low <= self.high and bar.high >= self.low


def _directional_fvgs(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    start_index: int,
) -> tuple[DirectionalFvg, ...]:
    result: list[DirectionalFvg] = []
    begin = max(2, start_index + 2)
    for index in range(begin, len(bars)):
        first = bars[index - 2]
        third = bars[index]
        if (
            side is DemoTradingSetupSide.LONG
            and third.low > first.high
        ):
            result.append(
                DirectionalFvg(
                    low=first.high,
                    high=third.low,
                    formed_index=index,
                )
            )
        elif (
            side is DemoTradingSetupSide.SHORT
            and third.high < first.low
        ):
            result.append(
                DirectionalFvg(
                    low=third.high,
                    high=first.low,
                    formed_index=index,
                )
            )
    return tuple(result)


def _first_later_retest(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    fvg: DirectionalFvg,
) -> int | None:
    for index in range(fvg.formed_index + 1, len(bars)):
        if fvg.touched_by(bars[index]):
            return index
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

    counts: Counter[str] = Counter()
    by_poi: dict[str, Counter[str]] = {
        family.value: Counter()
        for family in v6.PoiKind
    }
    by_anchor: dict[str, Counter[str]] = {}

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
        h4_bars = r6._bars_between_fast(
            indexed,
            start=opened,
            end=h4[opened].closed_at,
        )
        if not h4_bars:
            continue

        anchor = str(local.hour)
        by_anchor.setdefault(anchor, Counter())

        for poi in pois:
            counts["exact_poi_sequences"] += 1
            by_poi[poi.kind.value]["exact_poi_sequences"] += 1
            by_anchor[anchor]["exact_poi_sequences"] += 1

            touches = r4._touch_indices(
                h4_bars,
                poi,
                start_index=0,
            )
            if not touches:
                counts["no_touch"] += 1
                by_poi[poi.kind.value]["no_touch"] += 1
                by_anchor[anchor]["no_touch"] += 1
                continue

            touch_index = touches[0]
            counts["first_touch"] += 1
            by_poi[poi.kind.value]["first_touch"] += 1
            by_anchor[anchor]["first_touch"] += 1

            canonical_cisd = v6._first_cisd(
                h4_bars,
                side=side,
                start_index=touch_index,
            )
            if canonical_cisd is not None:
                counts["canonical_cisd_present"] += 1
                by_poi[poi.kind.value]["canonical_cisd_present"] += 1
                by_anchor[anchor]["canonical_cisd_present"] += 1
                continue

            counts["touch_without_canonical_cisd"] += 1
            by_poi[poi.kind.value]["touch_without_canonical_cisd"] += 1
            by_anchor[anchor]["touch_without_canonical_cisd"] += 1

            fvgs = _directional_fvgs(
                h4_bars,
                side=side,
                start_index=touch_index,
            )
            if not fvgs:
                counts["no_cisd_no_directional_fvg"] += 1
                by_poi[poi.kind.value]["no_cisd_no_directional_fvg"] += 1
                by_anchor[anchor]["no_cisd_no_directional_fvg"] += 1
                continue

            counts["no_cisd_with_directional_fvg"] += 1
            by_poi[poi.kind.value]["no_cisd_with_directional_fvg"] += 1
            by_anchor[anchor]["no_cisd_with_directional_fvg"] += 1

            retested = [
                (fvg, retest)
                for fvg in fvgs
                if (retest := _first_later_retest(
                    h4_bars,
                    fvg=fvg,
                )) is not None
            ]
            if not retested:
                counts["directional_fvg_without_later_retest"] += 1
                by_poi[poi.kind.value][
                    "directional_fvg_without_later_retest"
                ] += 1
                by_anchor[anchor][
                    "directional_fvg_without_later_retest"
                ] += 1
                continue

            counts["no_cisd_with_fvg_and_later_retest"] += 1
            by_poi[poi.kind.value][
                "no_cisd_with_fvg_and_later_retest"
            ] += 1
            by_anchor[anchor][
                "no_cisd_with_fvg_and_later_retest"
            ] += 1

    gap = counts["touch_without_canonical_cisd"]
    fvg = counts["no_cisd_with_directional_fvg"]
    retest = counts["no_cisd_with_fvg_and_later_retest"]
    return {
        "symbol": symbol,
        "counts": dict(sorted(counts.items())),
        "by_source_poi_family": {
            family: dict(sorted(counter.items()))
            for family, counter in sorted(by_poi.items())
        },
        "by_anchor": {
            anchor: dict(sorted(counter.items()))
            for anchor, counter in sorted(by_anchor.items())
        },
        "fractions": {
            "directional_fvg_given_touch_without_cisd": (
                str(Decimal(fvg) / Decimal(gap))
                if gap
                else "0"
            ),
            "later_retest_given_touch_without_cisd": (
                str(Decimal(retest) / Decimal(gap))
                if gap
                else "0"
            ),
            "later_retest_given_directional_fvg": (
                str(Decimal(retest) / Decimal(fvg))
                if fvg
                else "0"
            ),
        },
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    _canonical, bars_by_symbol, provenance = r74._load_window(
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
    gap = totals["touch_without_canonical_cisd"]
    fvg = totals["no_cisd_with_directional_fvg"]
    retest = totals["no_cisd_with_fvg_and_later_retest"]

    return {
        "window_id": window_id,
        "canonical_sample": canonical_sample,
        "totals": dict(sorted(totals.items())),
        "fractions": {
            "directional_fvg_given_touch_without_cisd": (
                str(Decimal(fvg) / Decimal(gap))
                if gap
                else "0"
            ),
            "later_retest_given_touch_without_cisd": (
                str(Decimal(retest) / Decimal(gap))
                if gap
                else "0"
            ),
            "later_retest_given_directional_fvg": (
                str(Decimal(retest) / Decimal(fvg))
                if fvg
                else "0"
            ),
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
        raise ValueError("R79 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R79 source failure decision drift")
    if r78.IDENTITY != (
        "VT08_INDEX_R78_PERSISTENT_CISD_SERIES_RECOVERY_FALSIFICATION_001"
    ):
        raise ValueError("R79 R78 identity drift")

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
        "source_r78": {
            "identity": r78.IDENTITY,
            "run_id": SOURCE_R78_RUN_ID,
            "artifact_id": SOURCE_R78_ARTIFACT_ID,
            "artifact_digest": SOURCE_R78_ARTIFACT_DIGEST,
            "persistent_cisd_recovery_survived": False,
        },
        "diagnostic_contract": {
            "source_gap": (
                "TTrades permits Protected Swing from liquidity sweep or "
                "FVG reaction; current stack lacks separately frozen "
                "FVG-reaction Protected-Swing constructor"
            ),
            "directional_fvg_definition": (
                "standard causal three-M15 imbalance: long third.low > "
                "first.high; short third.high < first.low"
            ),
            "later_retest_definition": (
                "a strictly later observed M15 overlaps the formed FVG range"
            ),
            "fvg_retest_equated_to_protected_swing": False,
            "pnl_evaluated": False,
            "signals_created": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R79_FVG_REACTION_PS_GAP_FORENSICS_COMPLETE_NO_RULE_CREATED",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "provider_observations_only": True,
            "future_information_used": False,
            "fvg_retest_promoted_to_protected_swing": False,
            "signals_created": False,
            "signals_suppressed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "risk_changed": False,
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
                    "totals": report["five_year"]["totals"],
                    "fractions": report["five_year"]["fractions"],
                },
                "recent_two_year": {
                    "totals": report["recent_two_year"]["totals"],
                    "fractions": report["recent_two_year"]["fractions"],
                },
                "r66": {
                    "totals": report["r66_failed_holdout"]["totals"],
                    "fractions": report["r66_failed_holdout"]["fractions"],
                    "by_market": report["r66_failed_holdout"]["by_market"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
