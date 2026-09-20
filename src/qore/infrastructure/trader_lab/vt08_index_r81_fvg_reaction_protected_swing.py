"""VT08 Index R81 — FVG-reaction Protected-Swing recovery falsification.

Source-bound hypothesis:
TTrades recognizes two Protected-Swing families. For the FVG family, price must
trade into a fair value gap and then confirm the reaction with a directional
close through the relevant opposing candle series. R79 established that this
gap is materially present in consumed evidence; R78 showed that generic
persistent CISD without FVG conditioning is economically invalid.

R81 tests one bounded implementation only:
- preserve the entire canonical source-complete surface unchanged;
- consider only exact source-POI touches where canonical V6 CISD never confirms;
- require a direction-consistent M15 FVG to form after that touch;
- require a later observed provider M15 retest of that FVG;
- the protected-swing series may start only on an opposing candle that overlaps
  that FVG after it has formed;
- failed non-opposing candles do not reset that FVG-reaction series, matching
  the source requirement of a close through the relevant series rather than an
  undocumented one-bar reset;
- confirmation is the first directional close through the original series open;
- the Protected Swing is the structural extreme accumulated by that series;
- then require the exact existing continuation and SAME_C2 body rule.

No target search is performed. R80 falsified changing the canonical research
surface from 2.5R to source 2R as a standalone transport repair, so R81 keeps
2.5R solely to isolate the Protected-Swing architecture.

Consumed-evidence research only. No candidate is created.
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
    vt08_index_r78_persistent_cisd_series as r78,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r79_fvg_reaction_ps_gap as r79,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r80_source_2r_target_transport as r80,
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

SCHEMA = "qore.trader_lab.vt08_index_r81_fvg_reaction_protected_swing.v1"
IDENTITY = "VT08_INDEX_R81_FVG_REACTION_PROTECTED_SWING_RECOVERY_001"

SOURCE_R79_RUN_ID = 35516202970
SOURCE_R79_ARTIFACT_ID = 10606254504
SOURCE_R79_ARTIFACT_DIGEST = (
    "sha256:3389ebb2abf0faae3a494601bfb54b23bc30546094181d954dac4fe3ccc7632c"
)
SOURCE_R80_RUN_ID = 35516661428
SOURCE_R80_ARTIFACT_ID = 10607051824
SOURCE_R80_ARTIFACT_DIGEST = (
    "sha256:9d38e7d5edccd0ecb341ce4560e58286bbddc782fd95a4171f6fbc15e6b89207"
)

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
TARGET_R = r31.TARGET_R


def _opposing(
    bar: Vt08IndexC2R1Bar,
    *,
    side: DemoTradingSetupSide,
) -> bool:
    return (
        bar.close < bar.open
        if side is DemoTradingSetupSide.LONG
        else bar.close > bar.open
    )


def _fvg_reaction_cisd(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    fvg: r79.DirectionalFvg,
) -> tuple[int, Decimal, Decimal, int] | None:
    """Confirm only a persistent opposing series born while touching the FVG."""
    sequence_open: Decimal | None = None
    extreme: Decimal | None = None
    reaction_touch_index: int | None = None

    for index in range(fvg.formed_index + 1, len(bars)):
        bar = bars[index]
        is_opposing = _opposing(bar, side=side)

        if sequence_open is None:
            if not fvg.touched_by(bar) or not is_opposing:
                continue
            sequence_open = bar.open
            extreme = (
                bar.low
                if side is DemoTradingSetupSide.LONG
                else bar.high
            )
            reaction_touch_index = index
            continue

        assert extreme is not None
        assert reaction_touch_index is not None

        if is_opposing:
            extreme = (
                min(extreme, bar.low)
                if side is DemoTradingSetupSide.LONG
                else max(extreme, bar.high)
            )
            continue

        confirmed = (
            bar.close > sequence_open
            if side is DemoTradingSetupSide.LONG
            else bar.close < sequence_open
        )
        if confirmed:
            return index, sequence_open, extreme, reaction_touch_index

        # Source-bound persistence: the relevant series remains active until
        # its open is actually closed through. Unlike R78, the series can only
        # be born from an opposing candle physically reacting inside the FVG.

    return None


def _recovered_signal(
    *,
    symbol: str,
    h4_bar: Vt08IndexC2R1Bar,
    h4_opened_at: Any,
    bars: Sequence[Vt08IndexC2R1Bar],
    original_poi: v6.SourcePoi,
    side: DemoTradingSetupSide,
    model_kind: v6.H4ModelKind,
    original_touch_index: int,
) -> r4.ExpandedOpportunity | None:
    if v6._first_cisd(
        bars,
        side=side,
        start_index=original_touch_index,
    ) is not None:
        return None

    for fvg in r79._directional_fvgs(
        bars,
        side=side,
        start_index=original_touch_index,
    ):
        confirmed = _fvg_reaction_cisd(
            bars,
            side=side,
            fvg=fvg,
        )
        if confirmed is None:
            continue
        cisd_index, cisd_level, protected_swing, reaction_touch_index = (
            confirmed
        )

        continuation_index = v6._first_continuation(
            bars,
            side=side,
            start_index=cisd_index + 1,
            protected_swing=protected_swing,
        )
        if continuation_index is None:
            continue

        continuation = bars[continuation_index]
        entry = continuation.close
        if model_kind is v6.H4ModelKind.SAME_C2:
            in_body = (
                entry > h4_bar.open
                if side is DemoTradingSetupSide.LONG
                else entry < h4_bar.open
            )
            if not in_body:
                continue

        risk = (
            entry - protected_swing
            if side is DemoTradingSetupSide.LONG
            else protected_swing - entry
        )
        if risk <= 0:
            continue
        target = (
            entry + TARGET_R * risk
            if side is DemoTradingSetupSide.LONG
            else entry - TARGET_R * risk
        )
        if target <= 0:
            continue

        reaction_poi = v6.SourcePoi(
            kind=v6.PoiKind.FVG,
            low=fvg.low,
            high=fvg.high,
            observed_at=bars[fvg.formed_index].closed_at,
        )
        signal = v6.CandidateSignal(
            symbol=symbol,
            side=side,
            model_kind=model_kind,
            h4_opened_at=h4_opened_at,
            signal_at=continuation.closed_at,
            entry=entry,
            stop=protected_swing,
            target=target,
            poi=reaction_poi,
            cisd_level=cisd_level,
            cisd_confirmed_at=bars[cisd_index].closed_at,
            protected_swing_extreme=protected_swing,
        )
        return r4.ExpandedOpportunity(
            signal=signal,
            source_poi_kind="fvg-reaction-ps",
            poi_touch_at=bars[reaction_touch_index].opened_at.astimezone(UTC),
            rearm_index=0,
        )

    return None


def _recovery_surface(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: Any,
    end_date: Any,
) -> tuple[tuple[r4.ExpandedOpportunity, ...], dict[str, Any]]:
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in bars
    }
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}
    recovered: list[r4.ExpandedOpportunity] = []
    diagnostics: Counter[str] = Counter()

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

        h4_bar = h4[opened]
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
            end=h4_bar.closed_at,
        )
        if not h4_bars:
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

        for poi in pois:
            touches = r4._touch_indices(
                h4_bars,
                poi,
                start_index=0,
            )
            if not touches:
                continue
            touch_index = touches[0]
            diagnostics["exact_poi_first_touches"] += 1

            if v6._first_cisd(
                h4_bars,
                side=side,
                start_index=touch_index,
            ) is not None:
                diagnostics["canonical_cisd_present"] += 1
                continue
            diagnostics["canonical_cisd_absent"] += 1

            fvgs = r79._directional_fvgs(
                h4_bars,
                side=side,
                start_index=touch_index,
            )
            if not fvgs:
                diagnostics["no_directional_fvg"] += 1
                continue
            diagnostics["directional_fvg_present"] += 1

            fvg_with_reaction = sum(
                _fvg_reaction_cisd(
                    h4_bars,
                    side=side,
                    fvg=fvg,
                )
                is not None
                for fvg in fvgs
            )
            if not fvg_with_reaction:
                diagnostics["no_fvg_reaction_confirmation"] += 1
                continue
            diagnostics["fvg_reaction_confirmations"] += fvg_with_reaction

            row = _recovered_signal(
                symbol=symbol,
                h4_bar=h4_bar,
                h4_opened_at=opened,
                bars=h4_bars,
                original_poi=poi,
                side=side,
                model_kind=model_kind,
                original_touch_index=touch_index,
            )
            if row is None:
                diagnostics["reaction_confirmed_no_valid_continuation"] += 1
                continue
            recovered.append(row)
            diagnostics["recovered_signals"] += 1

    recovered.sort(
        key=lambda item: (
            item.signal.signal_at,
            item.signal.symbol,
            item.signal.entry,
            item.signal.stop,
        )
    )
    deduped: dict[tuple[object, ...], r4.ExpandedOpportunity] = {}
    for row in recovered:
        deduped.setdefault(row.identity(), row)
    diagnostics["pre_dedup_recovered_signals"] = len(recovered)
    diagnostics["deduplicated_recovered_signals"] = len(deduped)
    return tuple(deduped.values()), dict(diagnostics)


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
        raise ValueError(f"R81 {window_id} canonical identity drift")

    added: list[tuple[r4.ExpandedOpportunity, Any]] = []
    diagnostics: dict[str, Any] = {}
    for symbol in contract.MARKETS:
        surface, diag = _recovery_surface(
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
    unique: dict[tuple[object, ...], tuple[r4.ExpandedOpportunity, Any]] = {}
    for row in added:
        unique.setdefault(row[0].identity(), row)
    novel = [
        row
        for identity, row in unique.items()
        if identity not in canonical_ids
    ]

    combined_sample = canonical_sample + len(novel)
    low_5y, high_5y = contract.FIVE_YEAR_TRADE_RANGE
    if window_id == "5Y":
        density_gate = low_5y <= combined_sample <= high_5y
    elif window_id == "2Y":
        density_gate = combined_sample >= contract.TWO_YEAR_MIN_TRADES
    else:
        density_gate = combined_sample >= r66.MIN_TRADES

    primary = r74._metrics(novel, stress=PRIMARY_STRESS)
    secondary = r74._metrics(novel, stress=SECONDARY_STRESS)
    secondary_blocks = r74._period_blocks(
        novel,
        start_date=start_date,
        end_date=end_date,
        stress=SECONDARY_STRESS,
    )
    return {
        "window_id": window_id,
        "canonical_sample": canonical_sample,
        "added_fvg_reaction_ps_signals": len(novel),
        "hypothetical_combined_sample": combined_sample,
        "density_gate": density_gate,
        "added_market_counts": r74._market_counts(novel),
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
        raise ValueError("R81 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R81 source failure decision drift")
    if r79.IDENTITY != (
        "VT08_INDEX_R79_FVG_REACTION_PROTECTED_SWING_GAP_FORENSICS_001"
    ):
        raise ValueError("R81 R79 identity drift")
    if r80.IDENTITY != (
        "VT08_INDEX_R80_SOURCE_AUTHORIZED_2R_TARGET_TRANSPORT_001"
    ):
        raise ValueError("R81 R80 identity drift")
    if r78.IDENTITY != (
        "VT08_INDEX_R78_PERSISTENT_CISD_SERIES_RECOVERY_FALSIFICATION_001"
    ):
        raise ValueError("R81 R78 identity drift")

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
        "source_evidence": {
            "r79": {
                "run_id": SOURCE_R79_RUN_ID,
                "artifact_id": SOURCE_R79_ARTIFACT_ID,
                "artifact_digest": SOURCE_R79_ARTIFACT_DIGEST,
            },
            "r80": {
                "run_id": SOURCE_R80_RUN_ID,
                "artifact_id": SOURCE_R80_ARTIFACT_ID,
                "artifact_digest": SOURCE_R80_ARTIFACT_DIGEST,
                "source_2r_standalone_transport_survived": False,
            },
            "r78_generic_persistent_cisd_survived": False,
        },
        "protected_swing_contract": {
            "family": "FVG_REACTION",
            "requires_post_touch_directional_fvg": True,
            "series_must_be_born_on_opposing_fvg_touch": True,
            "requires_close_through_original_series_open": True,
            "protected_swing_is_series_extreme": True,
            "same_existing_continuation_rule": True,
            "same_same_c2_body_rule": True,
            "canonical_target_r_kept_for_isolation": str(TARGET_R),
            "target_grid_searched": False,
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
        "decision": "R81_FVG_REACTION_PS_FALSIFICATION_COMPLETE_NO_CANDIDATE",
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "single_source_bound_ps_family": True,
            "future_information_used": False,
            "generic_persistent_cisd_reused": False,
            "fvg_reaction_required": True,
            "canonical_signals_suppressed": False,
            "daily_bias_changed": False,
            "anchors_changed": False,
            "original_poi_families_removed": False,
            "target_changed": False,
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
                        "added_fvg_reaction_ps_signals",
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
                        "added_fvg_reaction_ps_signals",
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
                        "added_fvg_reaction_ps_signals",
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
