"""VT08 Index R105 — STANDARD causal-context transport atlas.

R100 established that STANDARD POI+CISD+continuation signals are source-valid.
R102/R103/R104 established that the remaining R66 weakness is concentrated in
STANDARD_WITHOUT_EXTRA_PS, while explicit-PS promotions alone cannot solve the
temporal problem.

R105 does not change risk or suppress signals. It maps the STANDARD subset
through the pre-entry causal feature vocabulary already frozen in R46:
formation/POI health, source-day relationship, previous/current source-day body
alignment, CISD/continuation/H4 latency, POI age, range states, cross-index
state, concurrent pressure, loss cluster, governor state, plus market/side/
anchor diagnostics.

A context label is only highlighted as transport-adverse when it is adverse in
R66 B2 *and* shows corroborating weakness outside R66. Calendar/year is never a
runtime feature. No cohort is automatically converted into a rule.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r35_five_year_temporal_contract as r35,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r46_cross_window_transport_forensics as r46,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r104_r58_promotion_transport_attribution as r104,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r105_standard_context_transport_atlas.v1"
IDENTITY = "VT08_INDEX_R105_STANDARD_CAUSAL_CONTEXT_TRANSPORT_ATLAS_001"

SOURCE_R104_RUN_ID = 35556281814
SOURCE_R104_ARTIFACT_ID = 10621165375
SOURCE_R104_ARTIFACT_DIGEST = (
    "sha256:1a05f768c25fdc872ccc46495c86b250258ed4c935f98f3fd2d893c9ea14e773"
)
POLICY_ID = r102.POLICY_EXPLICIT_FULL
MIN_REPORT_SAMPLE = 20

DIMENSIONS = (
    "symbol",
    "side",
    "market_side",
    "anchor",
    "poi",
    "market_poi",
    "side_poi",
    "market_side_poi",
    "model_kind",
    "rearm",
    "formation_tier",
    "formation_health_state",
    "poi_health_state",
    "source_day_relationship",
    "previous_source_day_body_alignment",
    "current_source_day_body_alignment",
    "risk_fraction_bucket",
    "cisd_latency_bucket",
    "continuation_latency_bucket",
    "h4_entry_latency_bucket",
    "poi_age_bucket",
    "closure_reference_expansion_state",
    "recent_h4_range_state",
    "recent_daily_range_state",
    "cross_index_state",
    "concurrent_pressure",
    "loss_cluster",
    "governor_state",
)


def _period_id(window_id: str, exited_date: date) -> str:
    if window_id == "5Y":
        boundaries = r35._annual_boundaries()
        for index in range(5):
            if boundaries[index] <= exited_date < boundaries[index + 1]:
                return f"Y{index + 1}"
        return "OUTSIDE"
    if window_id == "2Y":
        boundaries = (
            r45.START_DATE,
            date(2025, 9, 15),
            r45.END_DATE_EXCLUSIVE,
        )
        for index in range(2):
            if boundaries[index] <= exited_date < boundaries[index + 1]:
                return f"Y{index + 1}"
        return "OUTSIDE"
    if window_id == "R66":
        boundaries = (
            r66.START_DATE,
            r66.BLOCK_BOUNDARY,
            r66.END_DATE_EXCLUSIVE,
        )
        for index in range(2):
            if boundaries[index] <= exited_date < boundaries[index + 1]:
                return f"B{index + 1}"
        return "OUTSIDE"
    raise ValueError(f"R105 unsupported window {window_id}")


def _metrics_rows(
    rows: Sequence[dict[str, Any]],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row["exit_timestamp"]),
            str(row["symbol"]),
            str(row["timestamp"]),
        ),
    )
    values = tuple(
        (Decimal(str(row["outcome_r"])) - stress)
        * Decimal(str(row["effective_weight"]))
        for row in ordered
    )
    return fx._metrics(values)


def _breakdown(
    rows: Sequence[dict[str, Any]],
    *,
    dimension: str,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[dimension])].append(row)
    return {
        label: {
            "sample": len(items),
            "primary": _metrics_rows(
                items,
                stress=r102.PRIMARY_STRESS,
            ),
            "secondary": _metrics_rows(
                items,
                stress=r102.SECONDARY_STRESS,
            ),
        }
        for label, items in sorted(groups.items())
    }


def _period_breakdown(
    rows: Sequence[dict[str, Any]],
    *,
    dimension: str,
) -> dict[str, Any]:
    groups: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        groups[str(row[dimension])][str(row["period_id"])].append(row)
    return {
        label: {
            period: {
                "sample": len(items),
                "primary": _metrics_rows(
                    items,
                    stress=r102.PRIMARY_STRESS,
                ),
                "secondary": _metrics_rows(
                    items,
                    stress=r102.SECONDARY_STRESS,
                ),
            }
            for period, items in sorted(periods.items())
            if period != "OUTSIDE"
        }
        for label, periods in sorted(groups.items())
    }


def _standard_rows(
    *,
    stream: Sequence[tuple[Any, Any]],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    window_id: str,
) -> tuple[list[dict[str, Any]], int]:
    base, _base_diag = r58._exact_r47(
        tuple(stream),
        bars_by_symbol=bars_by_symbol,
    )
    base = tuple(base)
    final, _policy_diag = r102._apply_confidence_policy(
        base,
        bars_by_symbol=bars_by_symbol,
        policy_id=POLICY_ID,
    )
    final = tuple(final)

    stream_ids = [item[0].identity() for item in stream]
    final_ids = [item.opportunity.identity() for item in final]
    if stream_ids != final_ids:
        raise ValueError("R105 stream/final ordering drift")

    trace = r46._causal_trace(stream)
    feature_rows = r46._feature_rows(
        assigned=final,
        trace=trace,
        window_id=("2Y" if window_id == "R66" else window_id),
        bars_by_symbol=bars_by_symbol,
    )

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }
    standard: list[dict[str, Any]] = []
    for item, row in zip(final, feature_rows, strict=True):
        classification = r82._classify_opportunity(
            item.opportunity,
            h4_bars=h4_cache[item.symbol],
        )
        if str(classification["family"]) != r82.FAMILY_UNQUALIFIED:
            continue
        row = dict(row)
        exited_date = item.exited_at.astimezone(v7._NY).date()
        row["window_id"] = window_id
        row["period_id"] = _period_id(window_id, exited_date)
        standard.append(row)
    return standard, len(final)


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    stream, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    bars: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        key: tuple(value)
        for key, value in bars_by_symbol.items()
    }
    rows, canonical_sample = _standard_rows(
        stream=stream,
        bars_by_symbol=bars,
        window_id=window_id,
    )
    return {
        "window_id": window_id,
        "canonical_sample": canonical_sample,
        "standard_sample": len(rows),
        "primary": _metrics_rows(
            rows,
            stress=r102.PRIMARY_STRESS,
        ),
        "secondary": _metrics_rows(
            rows,
            stress=r102.SECONDARY_STRESS,
        ),
        "breakdowns": {
            dimension: _breakdown(
                rows,
                dimension=dimension,
            )
            for dimension in DIMENSIONS
        },
        "period_breakdowns": {
            dimension: _period_breakdown(
                rows,
                dimension=dimension,
            )
            for dimension in DIMENSIONS
        },
        "provenance": provenance,
    }


def _whole_window_metric(
    section: dict[str, Any],
    dimension: str,
    label: str,
) -> dict[str, Any] | None:
    return section["breakdowns"][dimension].get(label)


def _period_metric(
    section: dict[str, Any],
    dimension: str,
    label: str,
    period: str,
) -> dict[str, Any] | None:
    return section["period_breakdowns"][dimension].get(
        label,
        {},
    ).get(period)


def _adverse_contexts(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dimension in DIMENSIONS:
        labels = (
            set(five["breakdowns"][dimension])
            | set(two["breakdowns"][dimension])
            | set(failed["breakdowns"][dimension])
        )
        for label in sorted(labels):
            f = _whole_window_metric(five, dimension, label)
            t = _whole_window_metric(two, dimension, label)
            r = _whole_window_metric(failed, dimension, label)
            b2 = _period_metric(failed, dimension, label, "B2")
            if not all(isinstance(x, dict) for x in (f, t, r, b2)):
                continue
            assert f is not None and t is not None and r is not None and b2 is not None

            samples = (
                int(f["sample"]),
                int(t["sample"]),
                int(r["sample"]),
                int(b2["sample"]),
            )
            if min(samples) < MIN_REPORT_SAMPLE:
                continue

            f_total = Decimal(str(f["secondary"]["total_r"]))
            t_total = Decimal(str(t["secondary"]["total_r"]))
            r_total = Decimal(str(r["secondary"]["total_r"]))
            b2_total = Decimal(str(b2["secondary"]["total_r"]))
            outside_adverse_count = sum(
                value <= 0 for value in (f_total, t_total)
            )

            five_periods = five["period_breakdowns"][dimension].get(
                label,
                {},
            )
            two_periods = two["period_breakdowns"][dimension].get(
                label,
                {},
            )
            period_totals = [
                Decimal(str(block["secondary"]["total_r"]))
                for block in [
                    *five_periods.values(),
                    *two_periods.values(),
                ]
                if int(block["sample"]) >= MIN_REPORT_SAMPLE
            ]
            adverse_periods = sum(value <= 0 for value in period_totals)
            positive_periods = sum(value > 0 for value in period_totals)

            if b2_total >= 0:
                continue
            if outside_adverse_count == 0 and adverse_periods < 2:
                continue

            rows.append(
                {
                    "dimension": dimension,
                    "label": label,
                    "samples": {
                        "five_year": samples[0],
                        "recent_two_year": samples[1],
                        "r66": samples[2],
                        "r66_b2": samples[3],
                    },
                    "secondary_total_r": {
                        "five_year": str(f_total),
                        "recent_two_year": str(t_total),
                        "r66": str(r_total),
                        "r66_b2": str(b2_total),
                    },
                    "secondary_pf": {
                        "five_year": f["secondary"]["profit_factor"],
                        "recent_two_year": t["secondary"]["profit_factor"],
                        "r66": r["secondary"]["profit_factor"],
                        "r66_b2": b2["secondary"]["profit_factor"],
                    },
                    "outside_whole_window_adverse_count": outside_adverse_count,
                    "non_r66_periods_considered": len(period_totals),
                    "non_r66_adverse_periods": adverse_periods,
                    "non_r66_positive_periods": positive_periods,
                }
            )

    rows.sort(
        key=lambda row: (
            -int(row["outside_whole_window_adverse_count"]),
            -int(row["non_r66_adverse_periods"]),
            Decimal(str(row["secondary_total_r"]["r66_b2"])),
            -int(row["samples"]["r66_b2"]),
        )
    )
    return rows


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r104.IDENTITY != (
        "VT08_INDEX_R104_R58_PROMOTION_MECHANISM_TRANSPORT_ATTRIBUTION_001"
    ):
        raise ValueError("R105 R104 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    if (
        five["canonical_sample"],
        two["canonical_sample"],
        failed["canonical_sample"],
    ) != (2448, 1017, 773):
        raise ValueError("R105 canonical sample drift")
    if (
        five["standard_sample"],
        two["standard_sample"],
        failed["standard_sample"],
    ) != (1756, 746, 546):
        raise ValueError("R105 STANDARD sample drift")

    adverse = _adverse_contexts(five, two, failed)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r104": {
            "run_id": SOURCE_R104_RUN_ID,
            "artifact_id": SOURCE_R104_ARTIFACT_ID,
            "artifact_digest": SOURCE_R104_ARTIFACT_DIGEST,
        },
        "policy_under_attribution": POLICY_ID,
        "minimum_reporting_sample": MIN_REPORT_SAMPLE,
        "dimensions": list(DIMENSIONS),
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport_adverse_contexts": adverse,
        "decision": "R105_STANDARD_CONTEXT_TRANSPORT_ATLAS_COMPLETE_NO_RULE_CHANGE",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "all_predictors_known_at_or_before_entry": True,
            "calendar_or_year_used_as_runtime_feature": False,
            "cohort_to_rule_automatic": False,
            "optimization_grid_used": False,
            "signal_suppression_performed": False,
            "risk_retuning_performed": False,
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
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "samples": {
                    "five_year": report["five_year"]["standard_sample"],
                    "recent_two_year": report["recent_two_year"]["standard_sample"],
                    "r66": report["r66_failed_holdout"]["standard_sample"],
                },
                "top_transport_adverse_contexts": report[
                    "transport_adverse_contexts"
                ][:30],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
