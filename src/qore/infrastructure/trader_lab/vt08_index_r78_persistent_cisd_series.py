"""VT08 Index R78 — persistent CISD opposing-series recovery falsification.

The source-parity audit identifies one explicit QORE addition in V6:
the current first-CISD scanner discards an active opposing candle series as
soon as the first non-opposing candle fails to confirm. TTrades requires a
close through the relevant opposing series but does not establish that reset.

R78 makes one bounded correction only. Within the same current H4 and after an
exact canonical POI touch:
- start the opposing M15 series exactly as V6 does;
- a non-opposing candle that fails the close-through test does NOT reset it;
- later opposing candles may extend the same series;
- confirmation is still the first bias-direction close through the original
  series-open;
- no state carries across the H4 boundary.

To isolate this mechanism, R78 only adds a recovery when the canonical
first-CISD scanner returns None for that touch. Canonical signals are preserved
byte-for-byte. POIs, daily bias, anchors, continuation, SAME_C2 body rule,
Protected Swing stop, structural rearm and 2.5R management remain unchanged.

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
    vt08_index_r77_one_cycle_poi_carry as r77,
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

SCHEMA = "qore.trader_lab.vt08_index_r78_persistent_cisd_series.v1"
IDENTITY = "VT08_INDEX_R78_PERSISTENT_CISD_SERIES_RECOVERY_FALSIFICATION_001"

SOURCE_R77_RUN_ID = 35515490620
SOURCE_R77_ARTIFACT_ID = 10607130490
SOURCE_R77_ARTIFACT_DIGEST = (
    "sha256:c0a7790385dc1055e9a8024e7acb7f4db639aef591ee61b73adb18c726cb585f"
)

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
TARGET_R = r31.TARGET_R


def _persistent_first_cisd(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    start_index: int,
) -> tuple[int, Decimal, Decimal] | None:
    """Keep the first opposing series alive through failed non-opposing bars."""
    sequence_open: Decimal | None = None
    extreme: Decimal | None = None
    active = False

    for index in range(start_index, len(bars)):
        bar = bars[index]
        opposing = (
            bar.close < bar.open
            if side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            if not active:
                sequence_open = bar.open
                extreme = (
                    bar.low
                    if side is DemoTradingSetupSide.LONG
                    else bar.high
                )
                active = True
            else:
                assert extreme is not None
                extreme = (
                    min(extreme, bar.low)
                    if side is DemoTradingSetupSide.LONG
                    else max(extreme, bar.high)
                )
            continue

        if not active or sequence_open is None or extreme is None:
            continue

        confirmed = (
            bar.close > sequence_open
            if side is DemoTradingSetupSide.LONG
            else bar.close < sequence_open
        )
        if confirmed:
            return index, sequence_open, extreme
        # Sole R78 change: retain the active series after a failed close-through.

    return None


def _recover_from_touch(
    *,
    symbol: str,
    h4_bar: Vt08IndexC2R1Bar,
    h4_opened_at: Any,
    bars: Sequence[Vt08IndexC2R1Bar],
    poi: v6.SourcePoi,
    side: DemoTradingSetupSide,
    model_kind: v6.H4ModelKind,
    touch_index: int,
    rearm_index: int,
) -> r4.ExpandedOpportunity | None:
    if v6._first_cisd(
        bars,
        side=side,
        start_index=touch_index,
    ) is not None:
        return None

    cisd = _persistent_first_cisd(
        bars,
        side=side,
        start_index=touch_index,
    )
    if cisd is None:
        return None
    cisd_index, cisd_level, protected_swing = cisd

    continuation_index = v6._first_continuation(
        bars,
        side=side,
        start_index=cisd_index + 1,
        protected_swing=protected_swing,
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
        entry - protected_swing
        if side is DemoTradingSetupSide.LONG
        else protected_swing - entry
    )
    if risk <= 0:
        return None
    target = (
        entry + Decimal("2") * risk
        if side is DemoTradingSetupSide.LONG
        else entry - Decimal("2") * risk
    )
    if target <= 0:
        return None

    signal = v6.CandidateSignal(
        symbol=symbol,
        side=side,
        model_kind=model_kind,
        h4_opened_at=h4_opened_at,
        signal_at=continuation.closed_at,
        entry=entry,
        stop=protected_swing,
        target=target,
        poi=poi,
        cisd_level=cisd_level,
        cisd_confirmed_at=bars[cisd_index].closed_at,
        protected_swing_extreme=protected_swing,
    )
    return r4.ExpandedOpportunity(
        signal=signal,
        source_poi_kind=poi.kind.value,
        poi_touch_at=bars[touch_index].opened_at.astimezone(UTC),
        rearm_index=rearm_index,
    )


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
            cursor = 0
            rearm_index = 0
            while cursor < len(h4_bars):
                touches = r4._touch_indices(
                    h4_bars,
                    poi,
                    start_index=cursor,
                )
                if not touches:
                    break
                touch_index = touches[0]
                canonical_cisd = v6._first_cisd(
                    h4_bars,
                    side=side,
                    start_index=touch_index,
                )
                if canonical_cisd is not None:
                    diagnostics["touches_with_canonical_cisd"] += 1
                    built = r4._candidate_from_sequence(
                        symbol=symbol,
                        h4_bar=h4_bar,
                        h4_opened_at=opened,
                        bars=h4_bars,
                        poi=poi,
                        side=side,
                        model_kind=model_kind,
                        touch_index=touch_index,
                    )
                    if built is None:
                        cursor = touch_index + 1
                    else:
                        _signal, continuation_index = built
                        cursor = continuation_index + 1
                        rearm_index += 1
                    continue

                diagnostics["touches_without_canonical_cisd"] += 1
                persistent = _persistent_first_cisd(
                    h4_bars,
                    side=side,
                    start_index=touch_index,
                )
                if persistent is None:
                    diagnostics["persistent_still_unresolved"] += 1
                    cursor = touch_index + 1
                    continue
                diagnostics["persistent_cisd_recovered"] += 1

                row = _recover_from_touch(
                    symbol=symbol,
                    h4_bar=h4_bar,
                    h4_opened_at=opened,
                    bars=h4_bars,
                    poi=poi,
                    side=side,
                    model_kind=model_kind,
                    touch_index=touch_index,
                    rearm_index=rearm_index,
                )
                if row is None:
                    diagnostics["recovered_cisd_no_valid_continuation"] += 1
                    cursor = touch_index + 1
                    continue

                recovered.append(row)
                diagnostics["recovered_signals"] += 1
                continuation_index = next(
                    index
                    for index, bar in enumerate(h4_bars)
                    if bar.closed_at == row.signal.signal_at
                )
                rearm_index += 1
                cursor = continuation_index + 1

    recovered.sort(
        key=lambda item: (
            item.signal.signal_at,
            item.signal.symbol,
            item.signal.entry,
            item.signal.stop,
            item.rearm_index,
        )
    )
    deduped: dict[tuple[object, ...], r4.ExpandedOpportunity] = {}
    for row in recovered:
        deduped.setdefault(row.identity(), row)
    diagnostics["deduplicated_recovered_signals"] = len(deduped)
    diagnostics["pre_dedup_recovered_signals"] = len(recovered)
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
        raise ValueError(f"R78 {window_id} canonical identity drift")

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
    added_ids = [item[0].identity() for item in added]
    if len(set(added_ids)) != len(added_ids):
        raise ValueError(f"R78 {window_id} recovery identity collision")

    overlapping_existing = sum(
        identity in canonical_ids
        for identity in added_ids
    )
    novel_added = [
        item
        for item in added
        if item[0].identity() not in canonical_ids
    ]

    combined_sample = canonical_sample + len(novel_added)
    low_5y, high_5y = contract.FIVE_YEAR_TRADE_RANGE
    if window_id == "5Y":
        density_gate = low_5y <= combined_sample <= high_5y
    elif window_id == "2Y":
        density_gate = combined_sample >= contract.TWO_YEAR_MIN_TRADES
    else:
        density_gate = combined_sample >= r66.MIN_TRADES

    primary = r74._metrics(novel_added, stress=PRIMARY_STRESS)
    secondary = r74._metrics(novel_added, stress=SECONDARY_STRESS)
    secondary_blocks = r74._period_blocks(
        novel_added,
        start_date=start_date,
        end_date=end_date,
        stress=SECONDARY_STRESS,
    )

    return {
        "window_id": window_id,
        "canonical_sample": canonical_sample,
        "recovered_signals_before_canonical_dedup": len(added),
        "recovered_matching_existing_canonical_identity_count": (
            overlapping_existing
        ),
        "added_persistent_cisd_signals": len(novel_added),
        "hypothetical_combined_sample": combined_sample,
        "density_gate": density_gate,
        "added_market_counts": r74._market_counts(novel_added),
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
        raise ValueError("R78 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R78 source failure decision drift")
    if r77.IDENTITY != (
        "VT08_INDEX_R77_ONE_CYCLE_STRICT_POI_CARRY_FALSIFICATION_001"
    ):
        raise ValueError("R78 R77 identity drift")

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
        "source_r77": {
            "identity": r77.IDENTITY,
            "run_id": SOURCE_R77_RUN_ID,
            "artifact_id": SOURCE_R77_ARTIFACT_ID,
            "artifact_digest": SOURCE_R77_ARTIFACT_DIGEST,
            "one_cycle_poi_carry_survived": False,
        },
        "correction_contract": {
            "audit_defect": (
                "canonical CISD series resets on first non-opposing "
                "non-confirming M15 candle"
            ),
            "persistent_state_scope": "CURRENT_H4_ONLY",
            "series_open_preserved": True,
            "opposing_extreme_updates_only_on_opposing_bars": True,
            "failed_non_opposing_bar_resets_series": False,
            "recovery_only_when_canonical_first_cisd_none": True,
            "canonical_signals_preserved": True,
            "poi_changed": False,
            "daily_bias_changed": False,
            "anchors_changed": False,
            "continuation_changed": False,
            "same_c2_body_rule_changed": False,
            "stop_rule_changed": False,
            "management_target_r": str(TARGET_R),
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
        "decision": "R78_PERSISTENT_CISD_FALSIFICATION_COMPLETE_NO_CANDIDATE",
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "single_source_audit_correction": True,
            "future_information_used": False,
            "calendar_or_year_runtime_feature": False,
            "canonical_signals_suppressed": False,
            "persistent_state_crosses_h4_boundary": False,
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
                        "added_persistent_cisd_signals",
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
                        "added_persistent_cisd_signals",
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
                        "added_persistent_cisd_signals",
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
