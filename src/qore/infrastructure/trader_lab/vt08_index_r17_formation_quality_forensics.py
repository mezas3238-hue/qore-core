"""VT08 Index R17 — cross-window pre-entry formation-quality forensics.

Extends R16 beyond coarse market/side/anchor cohorts. Every feature is fully
known at the entry close:
- POI touch -> CISD confirmation latency
- CISD -> continuation/entry latency
- entry timing inside the H4
- POI age at H4 start
- structural stop distance as fraction of entry
- POI family, model family and structural rearm state

The same fixed buckets are applied to consumed 5Y and recent-2Y development
windows. No outcome-derived feature, parameter search or candidate promotion.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r15_dual_window_gate as r15

SCHEMA = "qore.trader_lab.vt08_index_r17_formation_quality_forensics.v1"
IDENTITY = "VT08_INDEX_R17_FORMATION_QUALITY_FORENSICS_001"
STRESS = Decimal("0.05")


def _minutes(delta_seconds: float) -> int:
    return max(0, int(round(delta_seconds / 60)))


def _bucket_cisd_latency(opportunity: r4.ExpandedOpportunity) -> str:
    minutes = _minutes(
        (
            opportunity.signal.cisd_confirmed_at.astimezone(UTC)
            - opportunity.poi_touch_at.astimezone(UTC)
        ).total_seconds()
    )
    bars = minutes // 15
    if bars <= 1:
        return "0-1"
    if bars <= 3:
        return "2-3"
    if bars <= 7:
        return "4-7"
    return "8+"


def _bucket_continuation_latency(opportunity: r4.ExpandedOpportunity) -> str:
    minutes = _minutes(
        (
            opportunity.signal.signal_at.astimezone(UTC)
            - opportunity.signal.cisd_confirmed_at.astimezone(UTC)
        ).total_seconds()
    )
    bars = minutes // 15
    if bars <= 1:
        return "0-1"
    if bars == 2:
        return "2"
    if bars <= 4:
        return "3-4"
    return "5+"


def _bucket_h4_entry_latency(opportunity: r4.ExpandedOpportunity) -> str:
    minutes = _minutes(
        (
            opportunity.signal.signal_at.astimezone(UTC)
            - opportunity.signal.h4_opened_at.astimezone(UTC)
        ).total_seconds()
    )
    if minutes <= 60:
        return "<=60m"
    if minutes <= 120:
        return "61-120m"
    if minutes <= 180:
        return "121-180m"
    return "181m+"


def _bucket_poi_age(opportunity: r4.ExpandedOpportunity) -> str:
    minutes = _minutes(
        (
            opportunity.signal.h4_opened_at.astimezone(UTC)
            - opportunity.signal.poi.observed_at.astimezone(UTC)
        ).total_seconds()
    )
    hours = Decimal(minutes) / Decimal(60)
    if hours <= Decimal("4"):
        return "<=4h"
    if hours <= Decimal("8"):
        return "4-8h"
    if hours <= Decimal("16"):
        return "8-16h"
    return "16h+"


def _bucket_risk_fraction(opportunity: r4.ExpandedOpportunity) -> str:
    signal = opportunity.signal
    fraction = abs(signal.entry - signal.stop) / signal.entry
    if fraction < Decimal("0.0015"):
        return "<0.15%"
    if fraction < Decimal("0.0030"):
        return "0.15-0.30%"
    if fraction < Decimal("0.0050"):
        return "0.30-0.50%"
    return ">=0.50%"


def _feature_values(opportunity: r4.ExpandedOpportunity) -> dict[str, str]:
    return {
        "cisd_latency": _bucket_cisd_latency(opportunity),
        "continuation_latency": _bucket_continuation_latency(opportunity),
        "h4_entry_latency": _bucket_h4_entry_latency(opportunity),
        "poi_age": _bucket_poi_age(opportunity),
        "risk_fraction": _bucket_risk_fraction(opportunity),
        "poi": str(opportunity.source_poi_kind),
        "model_kind": opportunity.signal.model_kind.value,
        "rearm": "rearm" if int(opportunity.rearm_index) > 0 else "initial",
    }


def _breakdown(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    feature: str,
) -> dict[str, Any]:
    labels = sorted({_feature_values(o)[feature] for o, _outcome in stream})
    result: dict[str, Any] = {}
    for label in labels:
        values = tuple(
            outcome.r_multiple - STRESS
            for opportunity, outcome in stream
            if _feature_values(opportunity)[feature] == label
        )
        result[label] = fx._metrics(values)
    return result


def _crosses(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    feature_a: str,
    feature_b: str,
) -> dict[str, Any]:
    def label(opportunity: r4.ExpandedOpportunity) -> str:
        values = _feature_values(opportunity)
        return f"{values[feature_a]}|{values[feature_b]}"

    labels = sorted({label(o) for o, _outcome in stream})
    result: dict[str, Any] = {}
    for name in labels:
        values = tuple(
            outcome.r_multiple - STRESS
            for opportunity, outcome in stream
            if label(opportunity) == name
        )
        result[name] = fx._metrics(values)
    return result


def _stable(
    five: dict[str, Any],
    two: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label in sorted(set(five) & set(two)):
        f = five[label]
        t = two[label]
        fp = Decimal(str(f["profit_factor"] or "0"))
        tp = Decimal(str(t["profit_factor"] or "0"))
        ft = Decimal(str(f["total_r"]))
        tt = Decimal(str(t["total_r"]))
        rows.append(
            {
                "label": label,
                "five_year": f,
                "recent_two_year": t,
                "positive_both": ft > 0 and tt > 0,
                "min_profit_factor": str(min(fp, tp)),
                "pf_above_1_2_both": fp >= Decimal("1.20")
                and tp >= Decimal("1.20"),
                "pf_above_1_3_both": fp >= Decimal("1.30")
                and tp >= Decimal("1.30"),
            }
        )
    rows.sort(
        key=lambda row: (
            Decimal(str(row["min_profit_factor"])),
            min(
                int(row["five_year"]["sample"]),
                int(row["recent_two_year"]["sample"]),
            ),
        ),
        reverse=True,
    )
    return rows


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
    five_stream, _five_contexts, five_provenance = r15._five_year_stream(roots)
    two_stream, _two_contexts, two_provenance = r15._two_year_stream(roots)

    features = (
        "cisd_latency",
        "continuation_latency",
        "h4_entry_latency",
        "poi_age",
        "risk_fraction",
        "poi",
        "model_kind",
        "rearm",
    )
    cross_pairs = (
        ("poi", "cisd_latency"),
        ("poi", "h4_entry_latency"),
        ("poi", "risk_fraction"),
        ("h4_entry_latency", "cisd_latency"),
        ("risk_fraction", "cisd_latency"),
        ("model_kind", "cisd_latency"),
    )

    feature_reports: dict[str, Any] = {}
    stable_rows: list[dict[str, Any]] = []
    for feature in features:
        five = _breakdown(five_stream, feature=feature)
        two = _breakdown(two_stream, feature=feature)
        stable = _stable(five, two)
        feature_reports[feature] = {
            "five_year": five,
            "recent_two_year": two,
            "stable": stable,
        }
        for row in stable:
            if bool(row["pf_above_1_2_both"]):
                stable_rows.append(
                    {"feature": feature, **row}
                )

    cross_reports: dict[str, Any] = {}
    for feature_a, feature_b in cross_pairs:
        name = f"{feature_a}__{feature_b}"
        five = _crosses(
            five_stream,
            feature_a=feature_a,
            feature_b=feature_b,
        )
        two = _crosses(
            two_stream,
            feature_a=feature_a,
            feature_b=feature_b,
        )
        stable = _stable(five, two)
        cross_reports[name] = {
            "five_year": five,
            "recent_two_year": two,
            "stable": stable,
        }
        for row in stable:
            if bool(row["pf_above_1_2_both"]):
                stable_rows.append(
                    {"feature": name, **row}
                )

    stable_rows.sort(
        key=lambda row: (
            Decimal(str(row["min_profit_factor"])),
            min(
                int(row["five_year"]["sample"]),
                int(row["recent_two_year"]["sample"]),
            ),
        ),
        reverse=True,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "stress_r_per_trade": str(STRESS),
        "samples": {
            "five_year": len(five_stream),
            "recent_two_year": len(two_stream),
        },
        "features": feature_reports,
        "cross_features": cross_reports,
        "stable_pf_1_2_rows": stable_rows,
        "stable_pf_1_2_count": len(stable_rows),
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "forensics_only": True,
            "pre_entry_features_only": True,
            "fixed_buckets": True,
            "parameter_search": False,
            "candidate_promotion": False,
            "both_windows_consumed": True,
            "fresh_holdout_claim": False,
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
                "samples": report["samples"],
                "stable_pf_1_2_count": report["stable_pf_1_2_count"],
                "top_stable": report["stable_pf_1_2_rows"][:15],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
