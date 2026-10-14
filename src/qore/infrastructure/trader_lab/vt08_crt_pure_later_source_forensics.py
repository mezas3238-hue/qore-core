"""Read-only provenance audit of 88 VT08 M15 later-source situations.

Uses original SHA-verified QORE Native M5. No new entries, R, PnL, broker orders
or claim that an engineering M15 swing equals Romeo's original old CRTH/CRTL.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar, _midpoint
from qore.infrastructure.trader_lab.vt08_crt_pure_density_root_cause_audit import (
    _geometry_valid,
    density_root_cause_report,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    load_atlas_vt08_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15,
    M15Bar,
    ReferenceKind,
    _confirmation,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
    first_r2c_trade,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

SCHEMA = "qore.vt08.crt_pure.later_source_forensics.v1"


def classify_preentry_context(
    *,
    direction: CrtPureCandidateDirection,
    parent_side: int,
    target_midpoint: float,
    first_source_extreme: int,
    first_reference_ids: tuple[str, ...],
    later_reference_ids: tuple[str, ...],
    first_reference_prices: tuple[int, ...],
    later_reference_prices: tuple[int, ...],
    post_first: tuple[M15Bar, ...],
    pre_entry: tuple[M15Bar, ...],
) -> dict[str, Any]:
    """Diagnostic flags from candles closed before possible alternative entry.

    Priority of flags produces an exhaustive *observational* classification.
    None of these classes is a source-certified rearm or invalidation rule.
    """
    if not pre_entry:
        raise ValueError("pre-entry window cannot be empty")
    bullish = direction is CrtPureCandidateDirection.BULLISH
    overlap_id = bool(set(first_reference_ids) & set(later_reference_ids))
    overlap_price = bool(set(first_reference_prices) & set(later_reference_prices))
    parent_close = next((
        b.opened_at.isoformat() for b in pre_entry
        if b.close_price < parent_side if bullish
    ), None) if bullish else next((
        b.opened_at.isoformat() for b in pre_entry
        if b.close_price > parent_side
    ), None)
    midpoint = next((
        b.opened_at.isoformat() for b in pre_entry
        if (b.high_price >= target_midpoint if bullish
            else b.low_price <= target_midpoint)
    ), None)
    old_extreme = next((
        b.opened_at.isoformat() for b in post_first
        if (b.low_price <= first_source_extreme if bullish
            else b.high_price >= first_source_extreme)
    ), None)
    classification = (
        "REPEATED_REFERENCE_ID_OR_PRICE" if overlap_id or overlap_price
        else "PARENT_SIDE_BODY_ACCEPTANCE" if parent_close
        else "TARGET_ALREADY_TOUCHED" if midpoint
        else "FIRST_SOURCE_EXTREME_RETOUCHED" if old_extreme
        else "DISTINCT_REFERENCE_NO_OBSERVED_ADVERSE_CONTEXT"
    )
    return {
        "observational_class": classification,
        "same_reference_id": overlap_id,
        "same_reference_price": overlap_price,
        "parent_side_close_beyond_at": parent_close,
        "c1_midpoint_pre_touched_at": midpoint,
        "first_source_extreme_re_touched_at": old_extreme,
        "all_context_known_before_prospective_entry": True,
        "methodology_authorization": "OPEN_NOT_CERTIFIED",
    }


def audit_88_original_cases(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    if market is CrtPureMarket.BTCUSD:
        raise ValueError("BTCUSD frozen")
    previous = density_root_cause_report(market, bars)
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {b.opened_at: b for b in m15}
    breaches = build_close_unmitigated_breach_groups(m15)
    classes: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()
    cases: list[dict[str, Any]] = []
    total_alternatives = 0
    for parent in parents:
        original, original_reason = first_r2c_trade(
            parent=parent, m15_by_time=m15_by_time, breaches=breaches
        )
        if original is not None:
            continue
        expected = (
            ReferenceKind.OLD_LOW if parent.direction is CrtPureCandidateDirection.BULLISH
            else ReferenceKind.OLD_HIGH
        )
        slots = int((parent.c3_closed_at - parent.c3_opened_at) / M15)
        series = tuple(m15_by_time[parent.c3_opened_at + i * M15]
                       for i in range(slots))
        sources = [
            (i, group) for i, b in enumerate(series)
            for group in breaches.get(b.opened_at, ())
            if group.kind is expected
        ]
        if len(sources) < 2:
            continue
        first = sources[0][1]
        alternatives: list[dict[str, Any]] = []
        for index, group in sources[1:]:
            confirmation = _confirmation(
                group.source_candle, series[index + 1:], parent.direction
            )
            if confirmation is None or not _geometry_valid(
                parent, group.source_candle, confirmation[1]
            ):
                continue
            confirm_bar, next_bar = confirmation
            entry_at = next_bar.opened_at
            if not (
                parent.c3_opened_at <= first.source_candle.opened_at
                < group.source_candle.opened_at < entry_at <= parent.c3_closed_at
            ):
                raise RuntimeError("noncausal source or entry chronology")
            if any(
                level.confirmed_at > source.source_candle.opened_at
                for source in (first, group) for level in source.references
            ):
                raise RuntimeError("future old-level pivot entered source ledger")
            if any(
                right.opened_at - left.opened_at != M15
                for left, right in zip(series[:-1], series[1:], strict=True)
            ):
                raise RuntimeError("noncontiguous M15 context")
            pre_entry = tuple(b for b in series if b.closed_at <= entry_at)
            if not pre_entry or pre_entry[-1].closed_at != entry_at:
                raise RuntimeError("pre-entry chronology incomplete")
            post_first = tuple(
                b for b in pre_entry if b.opened_at >= first.source_candle.closed_at
            )
            cls = classify_preentry_context(
                direction=parent.direction,
                parent_side=(
                    parent.c1.low_price if parent.direction is CrtPureCandidateDirection.BULLISH
                    else parent.c1.high_price
                ),
                target_midpoint=float(_midpoint(parent.c1.high_price, parent.c1.low_price)),
                first_source_extreme=(
                    first.source_candle.low_price
                    if parent.direction is CrtPureCandidateDirection.BULLISH
                    else first.source_candle.high_price
                ),
                first_reference_ids=tuple(r.evidence_id for r in first.references),
                later_reference_ids=tuple(r.evidence_id for r in group.references),
                first_reference_prices=tuple(r.price for r in first.references),
                later_reference_prices=tuple(r.price for r in group.references),
                post_first=post_first,
                pre_entry=pre_entry,
            )
            classes[cls["observational_class"]] += 1
            for key in (
                "same_reference_id", "same_reference_price",
                "parent_side_close_beyond_at", "c1_midpoint_pre_touched_at",
                "first_source_extreme_re_touched_at",
            ):
                if cls[key]:
                    flag_counts[key] += 1
            total_alternatives += 1
            alternatives.append({
                "later_source_opened_at": group.source_candle.opened_at.isoformat(),
                "later_confirmation_opened_at": confirm_bar.opened_at.isoformat(),
                "possible_entry_opened_at": entry_at.isoformat(),
                "later_source_ohlc_relative": {
                    "open": group.source_candle.open_price,
                    "high": group.source_candle.high_price,
                    "low": group.source_candle.low_price,
                    "close": group.source_candle.close_price,
                },
                "later_references": [
                    {"evidence_id": r.evidence_id,
                     "pivot_opened_at": r.pivot_opened_at.isoformat(),
                     "pivot_confirmed_at": r.confirmed_at.isoformat(),
                     "price_relative": r.price}
                    for r in group.references
                ],
                "pre_entry_evidence": cls,
                "authorization": "NOT_ADMITTED",
            })
        if alternatives:
            cases.append({
                "market": market.value,
                "parent_c3_opened_at": parent.c3_opened_at.isoformat(),
                "parent_direction": parent.direction.value,
                "parent_C1_HL_relative": [parent.c1.high_price, parent.c1.low_price],
                "parent_C2_HL_relative": [parent.c2.high_price, parent.c2.low_price],
                "first_source_opened_at": first.source_candle.opened_at.isoformat(),
                "first_source_ohlc_relative": {
                    "open": first.source_candle.open_price,
                    "high": first.source_candle.high_price,
                    "low": first.source_candle.low_price,
                    "close": first.source_candle.close_price,
                },
                "first_source_references": [
                    {"evidence_id": r.evidence_id,
                     "pivot_opened_at": r.pivot_opened_at.isoformat(),
                     "pivot_confirmed_at": r.confirmed_at.isoformat(),
                     "price_relative": r.price}
                    for r in first.references
                ],
                "first_source_rejection": original_reason,
                "alternative_sources": alternatives,
                "methodological_verdict": "OPEN_ORIGINAL_SOURCE_AND_COGNITIVE_AUDIT",
                "trades_allowed": False,
            })

    expected_cases = previous["source_stage_m15"][
        "PARENTS_REJECTED_BY_FIRST_SOURCE_WITH_LATER_VALID_CANDIDATE"
    ]
    if len(cases) != expected_cases or total_alternatives != sum(classes.values()):
        raise RuntimeError("independent prior source census reconciliation failed")
    if len({x["parent_c3_opened_at"] for x in cases}) != len(cases):
        raise RuntimeError("duplicate parent ledger cases")
    return {
        "schema": SCHEMA,
        "market": market.value,
        "reconciled_original_R2C_trades": previous["observed_r2c_trades"],
        "reconciled_previous_later_source_parent_count": expected_cases,
        "forensic_parent_cases": len(cases),
        "later_technical_sources_not_trades": total_alternatives,
        "observational_class_counts": dict(sorted(classes.items())),
        "pre_entry_flag_counts_nonexclusive": dict(sorted(flag_counts.items())),
        "primary_methodology_authority": "OPEN",
        "trading_or_certification_authority": False,
        "NO_SIZING": True,
        "NO_NEW_ORDERS": True,
        "NO_PNL_RECALCULATED": True,
        "original_source_ohlc_only": True,
    }, tuple(cases)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("market", choices=("AUDUSD", "USDJPY"))
    p.add_argument("source_root", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    bars, provenance = load_atlas_vt08_m5(CrtPureMarket(a.market), a.source_root)
    report, ledger = audit_88_original_cases(CrtPureMarket(a.market), bars)
    report["source_provenance"] = provenance
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "later-source-forensics.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    with (a.output / "later-source-forensics-cases.jsonl").open(
        "w", encoding="utf-8"
    ) as fh:
        for item in ledger:
            fh.write(json.dumps(item, sort_keys=True) + "\n")
    print("VT08_LATER_SOURCE_FORENSICS=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
