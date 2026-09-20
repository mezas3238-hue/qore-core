"""VT08 Index R67 — R66 fresh-holdout failure forensics.

R67 starts only after the preregistered R66 holdout rejected the exact frozen
R58/R59 identity. The failed holdout is now consumed diagnostic evidence.

This module does NOT retune R58, lower R66 gates, suppress signals, create a
replacement candidate, or use calendar/year as a runtime feature. It
reconstructs the exact R58 causal pipeline on:

- 5Y consumed development: 2018-09-15 -> 2023-09-15;
- recent 2Y consumed development: 2024-09-15 -> 2026-09-15;
- failed R66 holdout: 2016-09-17 -> 2018-09-15.

The objective is attribution:
1. quantify why R66 produced materially lower structural opportunity density;
2. isolate causal pre-entry cohorts whose weighted edge transported poorly;
3. distinguish R66-specific transport breaks from persistent losing cohorts;
4. preserve the failed frozen identity unchanged while producing evidence for
   a future NEW identity only if a generalizable cause is later preregistered.

Outcome is used only as the forensic label. Every feature used for cohort
attribution is available at or before the signal timestamp.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime
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
    vt08_index_r31_source_complete_structural_concurrency as r31,
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
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as overlay,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r67_r66_failure_forensics.v1"
IDENTITY = "VT08_INDEX_R67_R66_FRESH_HOLDOUT_FAILURE_FORENSICS_001"

SOURCE_R66_RUN_ID = 35502695314
SOURCE_R66_ARTIFACT_ID = 10602364737
SOURCE_R66_ARTIFACT_DIGEST = (
    "sha256:c4f41497400a47c277753444eadd11f59f178e5b02f354fb48f97de53f9c4bfe"
)
SOURCE_R66_HEAD_SHA = "2a6668333ccd4e90e4098fd1a56ac1acdfcb04a3"
SOURCE_R66_DECISION = "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
MIN_COHORT_SAMPLE = 10
NORMALIZATION_DAYS = Decimal("364")

EXTRA_DIMENSIONS = (
    "market_anchor",
    "side_anchor",
    "poi_anchor",
    "market_side_anchor",
    "market_side_poi_anchor",
    "r47_demotion_state",
    "r58_rule_family",
    "effective_weight_bucket",
)
DIMENSIONS = tuple(dict.fromkeys((*r46.DIMENSIONS, *EXTRA_DIMENSIONS)))


def _window_days(window_id: str) -> int:
    if window_id == "5Y":
        boundaries = r35._annual_boundaries()
        return (boundaries[-1] - boundaries[0]).days
    if window_id == "2Y":
        return (r45.END_DATE_EXCLUSIVE - r45.START_DATE).days
    if window_id == "R66":
        return (r66.END_DATE_EXCLUSIVE - r66.START_DATE).days
    raise ValueError(f"unsupported R67 window {window_id}")


def _period_id(window_id: str, item: r15.AssignedTrade) -> str:
    if window_id in {"5Y", "2Y"}:
        return r46._period_id(window_id, item)
    exited = item.exited_at.astimezone(r66._NY).date()
    if r66.START_DATE <= exited < r66.BLOCK_BOUNDARY:
        return "B1"
    if r66.BLOCK_BOUNDARY <= exited < r66.END_DATE_EXCLUSIVE:
        return "B2"
    return "OUTSIDE"


def _weight_bucket(weight: Decimal) -> str:
    if weight <= overlay.MIN_EFFECTIVE_WEIGHT:
        return "FLOOR_0_005"
    if weight < Decimal("0.10"):
        return "LOW_LT_0_10"
    if weight < Decimal("0.25"):
        return "MID_0_10_TO_LT_0_25"
    return "CAP_0_25"


def _joined_rule_family(labels: Sequence[str]) -> str:
    if not labels:
        return "BASE_CAPPED"
    cleaned = sorted(
        {
            "R47_DEMOTION" if label.startswith("R47:") else label
            for label in labels
        }
    )
    return "+".join(cleaned)


def _feature_rows(
    *,
    stream: Sequence[Any],
    base_r47: Sequence[r15.AssignedTrade],
    assigned: Sequence[r15.AssignedTrade],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    window_id: str,
) -> list[dict[str, Any]]:
    trace = r46._causal_trace(stream)
    if not (len(trace) == len(base_r47) == len(assigned)):
        raise ValueError("R67 causal reconstruction changed trade count")

    indexed_by_symbol = {
        symbol: {
            bar.opened_at.astimezone(UTC): bar
            for bar in bars
        }
        for symbol, bars in bars_by_symbol.items()
    }
    h4_by_symbol = {
        symbol: v6._build_h4(indexed)
        for symbol, indexed in indexed_by_symbol.items()
    }
    reaction_bars, reaction_opened = overlay._reaction_bars(bars_by_symbol)

    rows: list[dict[str, Any]] = []
    for base_item, item, state in zip(
        base_r47,
        assigned,
        trace,
        strict=True,
    ):
        if base_item.opportunity.identity() != item.opportunity.identity():
            raise ValueError("R67 R47-to-R58 opportunity ordering drift")

        # R46's feature constructor contains only causal pre-entry predictors.
        # For R66 we overwrite the period/window labels because R46 predates R66.
        row = r46._feature_row(
            item,
            state=state,
            window_id="2Y" if window_id == "R66" else window_id,
            indexed_by_symbol=indexed_by_symbol,
            h4_by_symbol=h4_by_symbol,
        )
        row["window_id"] = window_id
        row["period_id"] = _period_id(window_id, item)

        r47_labels = r47._rule_labels(
            base_item,
            h4_by_symbol=h4_by_symbol,
        )
        _requested, overlay_labels = overlay._requested_weight(
            base_item,
            h4_by_symbol=h4_by_symbol,
            reaction_bars=reaction_bars,
            reaction_opened=reaction_opened,
        )

        signal = item.opportunity.signal
        anchor = str(signal.h4_opened_at.astimezone(r66._NY).hour)
        poi = str(item.opportunity.source_poi_kind)
        side = signal.side.value

        row.update(
            {
                "market_anchor": f"{item.symbol}|{anchor}",
                "side_anchor": f"{side}|{anchor}",
                "poi_anchor": f"{poi}|{anchor}",
                "market_side_anchor": f"{item.symbol}|{side}|{anchor}",
                "market_side_poi_anchor": (
                    f"{item.symbol}|{side}|{poi}|{anchor}"
                ),
                "r47_demotion_state": (
                    "DEMOTED" if r47_labels else "NOT_DEMOTED"
                ),
                "r47_demotion_labels": list(r47_labels),
                "r58_overlay_labels": list(overlay_labels),
                "r58_rule_family": _joined_rule_family(overlay_labels),
                "r47_effective_weight": str(base_item.weight),
                "effective_weight": str(item.weight),
                "effective_weight_bucket": _weight_bucket(item.weight),
            }
        )
        rows.append(row)
    return rows


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
    key: str,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {
        label: {
            "primary": _metrics_rows(items, stress=PRIMARY_STRESS),
            "secondary": _metrics_rows(items, stress=SECONDARY_STRESS),
            "effective_risk_sum": str(
                sum(
                    (Decimal(str(item["effective_weight"])) for item in items),
                    Decimal(),
                )
            ),
        }
        for label, items in sorted(groups.items())
    }


def _period_breakdown(
    rows: Sequence[dict[str, Any]],
    *,
    key: str,
) -> dict[str, Any]:
    groups: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        groups[str(row[key])][str(row["period_id"])].append(row)
    return {
        label: {
            period: {
                "primary": _metrics_rows(items, stress=PRIMARY_STRESS),
                "secondary": _metrics_rows(items, stress=SECONDARY_STRESS),
            }
            for period, items in sorted(periods.items())
            if period != "OUTSIDE"
        }
        for label, periods in sorted(groups.items())
    }


def _trade_count_by_market(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = defaultdict(int)
    for row in rows:
        result[str(row["symbol"])] += 1
    return dict(sorted(result.items()))


def _window(
    *,
    stream: Sequence[Any],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    window_id: str,
) -> dict[str, Any]:
    base_r47, r47_diagnostics = r58._exact_r47(
        stream,
        bars_by_symbol=bars_by_symbol,
    )
    assigned, r58_diagnostics = overlay._apply_candidate(
        base_r47,
        bars_by_symbol=bars_by_symbol,
    )
    rows = _feature_rows(
        stream=stream,
        base_r47=base_r47,
        assigned=assigned,
        bars_by_symbol=bars_by_symbol,
        window_id=window_id,
    )
    days = _window_days(window_id)
    sample = len(rows)
    normalized = Decimal(sample) * NORMALIZATION_DAYS / Decimal(days)

    return {
        "sample": sample,
        "days": days,
        "trades_per_364d": str(normalized),
        "trade_count_by_market": _trade_count_by_market(rows),
        "primary": _metrics_rows(rows, stress=PRIMARY_STRESS),
        "secondary": _metrics_rows(rows, stress=SECONDARY_STRESS),
        "r47_diagnostics": r47_diagnostics,
        "r58_diagnostics": r58_diagnostics,
        "breakdowns": {
            dimension: _breakdown(rows, key=dimension)
            for dimension in DIMENSIONS
        },
        "period_breakdowns": {
            dimension: _period_breakdown(rows, key=dimension)
            for dimension in DIMENSIONS
        },
        "feature_matrix": rows,
    }


def _economic_transport(
    *,
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for label in sorted(set(five) & set(two) & set(failed)):
        f = five[label]["secondary"]
        t = two[label]["secondary"]
        h = failed[label]["secondary"]
        fs = int(f["sample"])
        ts = int(t["sample"])
        hs = int(h["sample"])
        if min(fs, ts, hs) <= 0:
            continue
        ft = Decimal(str(f["total_r"]))
        tt = Decimal(str(t["total_r"]))
        ht = Decimal(str(h["total_r"]))
        fm = Decimal(str(f["mean_r"]))
        tm = Decimal(str(t["mean_r"]))
        hm = Decimal(str(h["mean_r"]))
        result.append(
            {
                "label": label,
                "five_year_sample": fs,
                "recent_two_year_sample": ts,
                "r66_sample": hs,
                "five_year_secondary_pf": f["profit_factor"],
                "recent_two_year_secondary_pf": t["profit_factor"],
                "r66_secondary_pf": h["profit_factor"],
                "five_year_secondary_total_r": str(ft),
                "recent_two_year_secondary_total_r": str(tt),
                "r66_secondary_total_r": str(ht),
                "five_year_secondary_mean_r": str(fm),
                "recent_two_year_secondary_mean_r": str(tm),
                "r66_secondary_mean_r": str(hm),
                "r66_vs_5y_mean_delta_r": str(hm - fm),
                "r66_vs_recent2y_mean_delta_r": str(hm - tm),
                "positive_both_development_negative_r66": (
                    ft > 0 and tt > 0 and ht < 0
                ),
                "negative_all_three_windows": ft < 0 and tt < 0 and ht < 0,
                "minimum_sample_pass": min(fs, ts, hs) >= MIN_COHORT_SAMPLE,
            }
        )
    result.sort(
        key=lambda row: (
            Decimal(str(row["r66_secondary_mean_r"])),
            -int(row["r66_sample"]),
        )
    )
    return result


def _density_transport(
    *,
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    days = {
        "five": Decimal(_window_days("5Y")),
        "two": Decimal(_window_days("2Y")),
        "r66": Decimal(_window_days("R66")),
    }
    for label in sorted(set(five) & set(two) & set(failed)):
        fs = int(five[label]["secondary"]["sample"])
        ts = int(two[label]["secondary"]["sample"])
        hs = int(failed[label]["secondary"]["sample"])
        if min(fs, ts) <= 0:
            continue
        fr = Decimal(fs) * NORMALIZATION_DAYS / days["five"]
        tr = Decimal(ts) * NORMALIZATION_DAYS / days["two"]
        hr = Decimal(hs) * NORMALIZATION_DAYS / days["r66"]
        result.append(
            {
                "label": label,
                "five_year_trades_per_364d": str(fr),
                "recent_two_year_trades_per_364d": str(tr),
                "r66_trades_per_364d": str(hr),
                "r66_vs_5y_rate_ratio": str(hr / fr) if fr else None,
                "r66_vs_recent2y_rate_ratio": str(hr / tr) if tr else None,
                "r66_sample": hs,
            }
        )
    result.sort(
        key=lambda row: (
            Decimal(str(row["r66_vs_5y_rate_ratio"] or "999")),
            Decimal(str(row["r66_vs_recent2y_rate_ratio"] or "999")),
        )
    )
    return result


def _r66_block_drags(period_breakdown: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for label, periods in period_breakdown.items():
        for period, metrics in periods.items():
            row = metrics["secondary"]
            sample = int(row["sample"])
            total = Decimal(str(row["total_r"]))
            if sample >= MIN_COHORT_SAMPLE and total < 0:
                result.append(
                    {
                        "label": label,
                        "period": period,
                        "sample": sample,
                        "secondary_pf": row["profit_factor"],
                        "secondary_total_r": str(total),
                        "secondary_mean_r": row["mean_r"],
                    }
                )
    result.sort(key=lambda row: Decimal(str(row["secondary_total_r"])))
    return result


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R67 frozen R59/R58 dependency drift")
    if freeze.CANDIDATE_ID != r58.CANDIDATE_ID:
        raise ValueError("R67 frozen candidate identity drift")
    if freeze.CANDIDATE_RULE_FINGERPRINT != r58.RULE_FINGERPRINT:
        raise ValueError("R67 frozen candidate fingerprint drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, _five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, _two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    failed_stream, failed_bars, _failed_opened, failed_provenance = (
        r66._build_stream(roots=roots)
    )

    five = _window(
        stream=five_stream,
        bars_by_symbol={
            key: tuple(value) for key, value in five_bars.items()
        },
        window_id="5Y",
    )
    two = _window(
        stream=two_stream,
        bars_by_symbol={
            key: tuple(value) for key, value in two_bars.items()
        },
        window_id="2Y",
    )
    failed = _window(
        stream=failed_stream,
        bars_by_symbol={
            key: tuple(value) for key, value in failed_bars.items()
        },
        window_id="R66",
    )

    if int(five["sample"]) != 2448:
        raise ValueError(f"R67 5Y sample drift: {five['sample']}")
    if int(two["sample"]) != 1017:
        raise ValueError(f"R67 recent2Y sample drift: {two['sample']}")
    if int(failed["sample"]) != 773:
        raise ValueError(f"R67 R66 sample drift: {failed['sample']}")

    economic_transport = {
        dimension: _economic_transport(
            five=five["breakdowns"][dimension],
            two=two["breakdowns"][dimension],
            failed=failed["breakdowns"][dimension],
        )
        for dimension in DIMENSIONS
    }
    density_transport = {
        dimension: _density_transport(
            five=five["breakdowns"][dimension],
            two=two["breakdowns"][dimension],
            failed=failed["breakdowns"][dimension],
        )
        for dimension in DIMENSIONS
    }

    breaks = [
        {"dimension": dimension, **row}
        for dimension, rows in economic_transport.items()
        for row in rows
        if bool(row["positive_both_development_negative_r66"])
        and bool(row["minimum_sample_pass"])
    ]
    breaks.sort(
        key=lambda row: (
            Decimal(str(row["r66_secondary_total_r"])),
            Decimal(str(row["r66_secondary_mean_r"])),
        )
    )

    persistent = [
        {"dimension": dimension, **row}
        for dimension, rows in economic_transport.items()
        for row in rows
        if bool(row["negative_all_three_windows"])
        and bool(row["minimum_sample_pass"])
    ]
    persistent.sort(
        key=lambda row: (
            Decimal(str(row["r66_secondary_total_r"])),
            Decimal(str(row["r66_secondary_mean_r"])),
        )
    )

    density_contractions = [
        {"dimension": dimension, **row}
        for dimension, rows in density_transport.items()
        for row in rows
        if int(row["r66_sample"]) >= MIN_COHORT_SAMPLE
    ]
    density_contractions.sort(
        key=lambda row: (
            Decimal(str(row["r66_vs_5y_rate_ratio"] or "999")),
            Decimal(str(row["r66_vs_recent2y_rate_ratio"] or "999")),
        )
    )

    r66_drags = [
        {"dimension": dimension, **row}
        for dimension in DIMENSIONS
        for row in _r66_block_drags(
            failed["period_breakdowns"][dimension]
        )
    ]
    r66_drags.sort(
        key=lambda row: Decimal(str(row["secondary_total_r"]))
    )

    five_rate = Decimal(str(five["trades_per_364d"]))
    two_rate = Decimal(str(two["trades_per_364d"]))
    failed_rate = Decimal(str(failed["trades_per_364d"]))

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_failure": {
            "run_id": SOURCE_R66_RUN_ID,
            "artifact_id": SOURCE_R66_ARTIFACT_ID,
            "artifact_digest": SOURCE_R66_ARTIFACT_DIGEST,
            "head_sha": SOURCE_R66_HEAD_SHA,
            "decision": SOURCE_R66_DECISION,
            "failed_identity_preserved": True,
        },
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.CANDIDATE_RULE_FINGERPRINT,
            "freeze_id": freeze.FREEZE_ID,
            "candidate_retuned": False,
            "replacement_candidate_created": False,
        },
        "density_failure": {
            "r66_sample": failed["sample"],
            "r66_gate_minimum": r66.MIN_TRADES,
            "shortfall_trades": r66.MIN_TRADES - int(failed["sample"]),
            "five_year_trades_per_364d": five["trades_per_364d"],
            "recent_two_year_trades_per_364d": two["trades_per_364d"],
            "r66_trades_per_364d": failed["trades_per_364d"],
            "r66_vs_5y_rate_ratio": str(failed_rate / five_rate),
            "r66_vs_recent2y_rate_ratio": str(failed_rate / two_rate),
            "largest_structural_rate_contractions": density_contractions[:80],
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "economic_transport": economic_transport,
        "strongest_positive_development_to_negative_r66_breaks": breaks[:100],
        "persistent_negative_causal_cohorts": persistent[:100],
        "r66_largest_secondary_block_drags": r66_drags[:100],
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
            "r66_failed_holdout": failed_provenance,
        },
        "decision": "R67_FORENSICS_COMPLETE_NO_NEW_CANDIDATE",
        "governance": {
            "forensics_only": True,
            "r66_is_consumed_failure_evidence": True,
            "fresh_holdout_claim": False,
            "frozen_r58_r59_modified": False,
            "candidate_retuned": False,
            "replacement_candidate_created": False,
            "all_predictors_known_at_or_before_entry": True,
            "post_entry_outcome_used_as_predictor": False,
            "calendar_or_year_used_as_runtime_feature": False,
            "optimization_grid_used": False,
            "signal_suppression_performed": False,
            "risk_retuning_performed": False,
            "r66_gates_lowered": False,
            "r66_window_changed": False,
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
                "candidate": report["candidate"],
                "density_failure": report["density_failure"],
                "five_year": {
                    "sample": report["five_year"]["sample"],
                    "primary": report["five_year"]["primary"],
                    "secondary": report["five_year"]["secondary"],
                },
                "recent_two_year": {
                    "sample": report["recent_two_year"]["sample"],
                    "primary": report["recent_two_year"]["primary"],
                    "secondary": report["recent_two_year"]["secondary"],
                },
                "r66_failed_holdout": {
                    "sample": report["r66_failed_holdout"]["sample"],
                    "primary": report["r66_failed_holdout"]["primary"],
                    "secondary": report["r66_failed_holdout"]["secondary"],
                },
                "strongest_breaks": report[
                    "strongest_positive_development_to_negative_r66_breaks"
                ][:20],
                "persistent_negative": report[
                    "persistent_negative_causal_cohorts"
                ][:20],
                "r66_block_drags": report[
                    "r66_largest_secondary_block_drags"
                ][:20],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
