"""VT08 Index R77 — one-cycle strict POI carry falsification.

R76 found that almost every exact no-POI slot has older source structures that
remain untouched in observed M15 data. The source freeze, however, does not
authorize indefinite POI persistence. Relevant-swing context is explicitly
three-H4 based.

R77 therefore tests one bounded source-parity hypothesis only:

- preserve every canonical source-complete signal unchanged;
- only when an executable anchor has frozen V7 daily bias but the exact current
  source snapshot has no POI;
- allow a POI formed exactly two H4 cycles before the current anchor;
- require that no observed provider M15 bar has retouched it before the anchor;
- select by frozen source hierarchy FVG -> relevant swing -> CISD;
- then require the exact same current-H4 POI touch, M15 CISD, Protected Swing,
  continuation and structural rearm logic;
- manage any added signal with the existing 2.5R R31 policy.

This is a consumed-evidence falsification, not a candidate. The experiment does
not claim that TTrades universally persists POIs; it tests the minimum one-cycle
carry suggested by the source three-H4 structural window.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
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
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r76_strict_untouched_poi_memory as r76,
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

SCHEMA = "qore.trader_lab.vt08_index_r77_one_cycle_poi_carry.v1"
IDENTITY = "VT08_INDEX_R77_ONE_CYCLE_STRICT_POI_CARRY_FALSIFICATION_001"

SOURCE_R76_RUN_ID = 35513608607
SOURCE_R76_ARTIFACT_ID = 10605463569
SOURCE_R76_ARTIFACT_DIGEST = (
    "sha256:6270e8dbe5c4c90efd4f2038af7021b161f7e98882d2c56dea9907dbf068637b"
)

TARGET_R = r31.TARGET_R
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
POI_PRIORITY = {
    v6.PoiKind.FVG.value: 0,
    v6.PoiKind.RELEVANT_SWING.value: 1,
    v6.PoiKind.CISD.value: 2,
}


def _select_one_cycle_poi(
    records: Sequence[r76.PoiRecord],
    *,
    side: DemoTradingSetupSide,
    opened: Any,
    current_h4_index: int,
    h4_index: dict[Any, int],
) -> r76.PoiRecord | None:
    eligible = [
        row
        for row in records
        if row.side is side
        and row.poi.observed_at.astimezone(UTC) <= opened.astimezone(UTC)
        and current_h4_index - h4_index[row.formed_h4_open] == 2
        and (
            row.first_retouched_at is None
            or row.first_retouched_at >= opened.astimezone(UTC)
        )
    ]
    if not eligible:
        return None
    eligible.sort(
        key=lambda row: (
            POI_PRIORITY[row.poi.kind.value],
            -row.poi.observed_at.astimezone(UTC).timestamp(),
            row.poi.low,
            row.poi.high,
        )
    )
    return eligible[0]


def _opportunities_for_poi(
    *,
    symbol: str,
    indexed: dict[Any, Vt08IndexC2R1Bar],
    h4: dict[Any, Vt08IndexC2R1Bar],
    h4_keys: tuple[Any, ...],
    h4_opened_at: Any,
    side: DemoTradingSetupSide,
    poi: v6.SourcePoi,
) -> tuple[r4.ExpandedOpportunity, ...]:
    h4_bar = h4.get(h4_opened_at.astimezone(UTC))
    if h4_bar is None:
        return ()
    bars = r6._bars_between_fast(
        indexed,
        start=h4_opened_at,
        end=h4_bar.closed_at,
    )
    if not bars:
        return ()
    model_kind = r6._completed_h4_model_fast(
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
        touches = r4._touch_indices(
            bars,
            poi,
            start_index=cursor,
        )
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

    deduped: dict[tuple[object, ...], r4.ExpandedOpportunity] = {}
    for item in sorted(
        result,
        key=lambda value: (
            value.signal.signal_at,
            value.rearm_index,
        ),
    ):
        deduped.setdefault(item.identity(), item)
    return tuple(deduped.values())


def _fallback_surface(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: Any,
    end_date: Any,
) -> tuple[tuple[r4.ExpandedOpportunity, ...], dict[str, Any]]:
    records, h4_index, h4, h4_keys = r76._records(bars=bars)
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in bars
    }
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}
    opportunities: list[r4.ExpandedOpportunity] = []
    selected_family: Counter[str] = Counter()
    fallback_slots = 0
    touched_fallback_slots = 0

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

        exact = r6._source_pois_fast(
            indexed,
            h4,
            h4_keys,
            h4_opened_at=opened,
            side=side,
        )
        if exact:
            continue

        selected = _select_one_cycle_poi(
            records,
            side=side,
            opened=opened,
            current_h4_index=h4_index[opened],
            h4_index=h4_index,
        )
        if selected is None:
            continue
        fallback_slots += 1
        selected_family[selected.poi.kind.value] += 1

        rows = _opportunities_for_poi(
            symbol=symbol,
            indexed=indexed,
            h4=h4,
            h4_keys=h4_keys,
            h4_opened_at=opened,
            side=side,
            poi=selected.poi,
        )
        if rows:
            touched_fallback_slots += 1
        opportunities.extend(rows)

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
        raise ValueError(f"R77 duplicate fallback identity for {symbol}")

    return tuple(opportunities), {
        "one_cycle_fallback_slots": fallback_slots,
        "fallback_slots_producing_signal": touched_fallback_slots,
        "selected_family_slots": dict(sorted(selected_family.items())),
        "added_signal_count": len(opportunities),
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    canonical, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, canonical_sample = r74._window_contract(window_id)
    canonical_ids = {item[0].identity() for item in canonical}
    if len(canonical_ids) != canonical_sample:
        raise ValueError(f"R77 {window_id} canonical identity drift")

    added: list[tuple[r4.ExpandedOpportunity, Any]] = []
    diagnostics: dict[str, Any] = {}
    for symbol in contract.MARKETS:
        surface, diag = _fallback_surface(
            symbol=symbol,
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        diagnostics[symbol] = diag
        added.extend(
            r74._managed(
                surface,
                bars=bars_by_symbol[symbol],
            )
        )

    added.sort(
        key=lambda item: (
            item[0].signal.signal_at,
            item[0].signal.symbol,
            item[0].signal.entry,
            item[0].signal.stop,
        )
    )
    added_ids = [item[0].identity() for item in added]
    if len(set(added_ids)) != len(added_ids):
        raise ValueError(f"R77 {window_id} cross-market identity collision")
    if canonical_ids.intersection(added_ids):
        raise ValueError(f"R77 {window_id} fallback/canonical overlap")

    combined_sample = canonical_sample + len(added)
    low_5y, high_5y = contract.FIVE_YEAR_TRADE_RANGE
    if window_id == "5Y":
        density_gate = low_5y <= combined_sample <= high_5y
    elif window_id == "2Y":
        density_gate = combined_sample >= contract.TWO_YEAR_MIN_TRADES
    else:
        density_gate = combined_sample >= r66.MIN_TRADES

    primary = r74._metrics(added, stress=PRIMARY_STRESS)
    secondary = r74._metrics(added, stress=SECONDARY_STRESS)
    secondary_blocks = r74._period_blocks(
        added,
        start_date=start_date,
        end_date=end_date,
        stress=SECONDARY_STRESS,
    )
    return {
        "window_id": window_id,
        "canonical_sample": canonical_sample,
        "added_one_cycle_signals": len(added),
        "hypothetical_combined_sample": combined_sample,
        "density_gate": density_gate,
        "added_market_counts": r74._market_counts(added),
        "primary": primary,
        "secondary": secondary,
        "secondary_blocks": secondary_blocks,
        "all_secondary_blocks_positive": bool(secondary_blocks) and all(
            Decimal(str(row["total_r"])) > 0
            for row in secondary_blocks.values()
        ),
        "diagnostics": diagnostics,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R77 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R77 source failure decision drift")
    if r76.IDENTITY != "VT08_INDEX_R76_STRICT_UNTOUCHED_POI_MEMORY_FORENSICS_001":
        raise ValueError("R77 R76 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    economic_transport = all(
        Decimal(str(window["secondary"]["total_r"])) > 0
        and Decimal(str(window["secondary"]["profit_factor"] or "0"))
        > Decimal("1")
        and bool(window["all_secondary_blocks_positive"])
        for window in (five, two, failed)
    )
    density_transport = all(
        bool(window["density_gate"])
        for window in (five, two, failed)
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r76": {
            "identity": r76.IDENTITY,
            "run_id": SOURCE_R76_RUN_ID,
            "artifact_id": SOURCE_R76_ARTIFACT_ID,
            "artifact_digest": SOURCE_R76_ARTIFACT_DIGEST,
        },
        "carry_contract": {
            "only_when_exact_source_poi_absent": True,
            "formed_exactly_h4_cycles_before": 2,
            "strictly_untouched_before_anchor": True,
            "family_hierarchy": [
                v6.PoiKind.FVG.value,
                v6.PoiKind.RELEVANT_SWING.value,
                v6.PoiKind.CISD.value,
            ],
            "same_current_h4_touch_cisd_ps_continuation_required": True,
            "same_structural_rearm": True,
            "management_target_r": str(TARGET_R),
            "indefinite_poi_persistence_claimed": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport": {
            "secondary_positive_pf_gt_1_all_blocks_all_windows": (
                economic_transport
            ),
            "density_contract_all_windows": density_transport,
            "research_mechanism_survives_both": (
                economic_transport and density_transport
            ),
        },
        "decision": "R77_ONE_CYCLE_POI_CARRY_FALSIFICATION_COMPLETE_NO_CANDIDATE",
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "single_bounded_architecture": True,
            "future_information_used": False,
            "calendar_or_year_runtime_feature": False,
            "canonical_signals_suppressed": False,
            "older_than_one_cycle_poi_admitted": False,
            "risk_allocator_applied_to_added_signals": False,
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
                        "added_one_cycle_signals",
                        "hypothetical_combined_sample",
                        "density_gate",
                        "secondary",
                        "all_secondary_blocks_positive",
                        "added_market_counts",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "added_one_cycle_signals",
                        "hypothetical_combined_sample",
                        "density_gate",
                        "secondary",
                        "all_secondary_blocks_positive",
                        "added_market_counts",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "added_one_cycle_signals",
                        "hypothetical_combined_sample",
                        "density_gate",
                        "secondary",
                        "all_secondary_blocks_positive",
                        "added_market_counts",
                    )
                },
                "transport": report["transport"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
