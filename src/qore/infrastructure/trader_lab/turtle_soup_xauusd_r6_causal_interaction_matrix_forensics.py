"""Pre-registered causal interaction matrix for Turtle Soup XAUUSD.

Research only. This module reproduces frozen R3 over the already-consumed CIBO
10Y corpus and evaluates pre-entry interaction states. It does not search for a
return-maximizing threshold and does not promote any state into an operating
rule. All interaction inputs are known before entry; outcomes are used only to
measure temporal behavior after the state has been defined.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5

IDENTITY = "TURTLE_SOUP_XAUUSD_R6_CAUSAL_INTERACTION_MATRIX_FORENSICS_V1"
EVIDENCE_STATUS = "CONSUMED_CIBO_10Y_CAUSAL_INTERACTION_RESEARCH_NOT_FRESH_HOLDOUT"

EARLY_YEARS = r5.EARLY_YEARS
TRANSITION_YEARS = r5.TRANSITION_YEARS
RECENT_YEARS = r5.RECENT_YEARS

JOURNEY_CORE = (
    "raid_depth_range_bucket",
    "cisd_progress_bucket",
    "reclaim_latency_bucket",
    "protected_risk_range_bucket",
)

REGIME_FEATURES = (
    "d1_prior_range_vs20",
    "d1_range_5v20",
    "d1_efficiency_5",
    "d1_reversal_edge_20",
    "h4_range_3v20",
    "h4_efficiency_20",
    "h4_reversal_edge_20",
    "h4_trend_state_20",
)

INTERACTION_TEMPLATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("CORE4", JOURNEY_CORE),
    *tuple((f"CORE4_PLUS_{feature.upper()}", JOURNEY_CORE + (feature,)) for feature in REGIME_FEATURES),
    (
        "CORE4_PLUS_D1_EDGE_H4_RANGE",
        JOURNEY_CORE + ("d1_reversal_edge_20", "h4_range_3v20"),
    ),
    (
        "CORE4_PLUS_D1_EFF_H4_EFF",
        JOURNEY_CORE + ("d1_efficiency_5", "h4_efficiency_20"),
    ),
    (
        "CORE4_PLUS_D1_RANGE_H4_RANGE",
        JOURNEY_CORE + ("d1_range_5v20", "h4_range_3v20"),
    ),
    (
        "CORE4_PLUS_D1_EDGE_H4_EDGE",
        JOURNEY_CORE + ("d1_reversal_edge_20", "h4_reversal_edge_20"),
    ),
)

MIN_EARLY = 20
MIN_TRANSITION = 15
MIN_RECENT = 20
MIN_RECENT_YEAR = 8


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _stat(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    values = [_d(row["primary_net_r"]) for row in rows]
    gross_profit = sum((value for value in values if value > 0), Decimal(0))
    gross_loss = -sum((value for value in values if value < 0), Decimal(0))
    targets = sum(1 for row in rows if "TARGET" in str(row["exit_reason"]).upper())
    stops = sum(1 for row in rows if "STOP" in str(row["exit_reason"]).upper())
    total = sum(values, Decimal(0))
    return {
        "trades": len(rows),
        "total_primary_r": str(total),
        "mean_primary_r": str(total / len(rows)) if rows else None,
        "profit_factor": str(gross_profit / gross_loss) if gross_loss > 0 else None,
        "target_rate": str(Decimal(targets) / len(rows)) if rows else None,
        "stop_rate": str(Decimal(stops) / len(rows)) if rows else None,
    }


def _period(rows: Sequence[dict[str, Any]], years: frozenset[int]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["year"]) in years]


def _mean(stat: dict[str, Any]) -> Decimal | None:
    value = stat["mean_primary_r"]
    return None if value is None else _d(value)


def _signature(row: dict[str, Any], features: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(row[feature]) for feature in features)


def _support_ok(
    early: dict[str, Any],
    transition: dict[str, Any],
    recent: dict[str, Any],
    years: dict[str, dict[str, Any]],
) -> bool:
    return (
        int(early["trades"]) >= MIN_EARLY
        and int(transition["trades"]) >= MIN_TRANSITION
        and int(recent["trades"]) >= MIN_RECENT
        and all(int(years[str(year)]["trades"]) >= MIN_RECENT_YEAR for year in (2024, 2025, 2026))
    )


def _classify(
    early: dict[str, Any],
    transition: dict[str, Any],
    recent: dict[str, Any],
    years: dict[str, dict[str, Any]],
) -> str:
    if not _support_ok(early, transition, recent, years):
        return "INSUFFICIENT_SUPPORT"
    early_mean = _mean(early)
    transition_mean = _mean(transition)
    recent_mean = _mean(recent)
    year_means = [_mean(years[str(year)]) for year in (2024, 2025, 2026)]
    if early_mean is None or transition_mean is None or recent_mean is None or any(value is None for value in year_means):
        return "INSUFFICIENT_SUPPORT"
    complete_year_means = [value for value in year_means if value is not None]
    if early_mean > 0 and transition_mean > 0 and recent_mean > 0 and all(value > 0 for value in complete_year_means):
        return "ROBUST_VALID"
    if early_mean < 0 and transition_mean < 0 and recent_mean < 0 and all(value < 0 for value in complete_year_means):
        return "ROBUST_INVALID"
    if early_mean > 0 and recent_mean < 0 and all(value < 0 for value in complete_year_means):
        return "STRUCTURAL_BREAK_TO_INVALID"
    if recent_mean > 0 and all(value > 0 for value in complete_year_means):
        return "RECENT_STABLE_VALID"
    if recent_mean < 0 and all(value < 0 for value in complete_year_means):
        return "RECENT_STABLE_INVALID"
    return "MIXED"


def _cell(features: tuple[str, ...], signature: tuple[str, ...], rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    early_rows = _period(rows, EARLY_YEARS)
    transition_rows = _period(rows, TRANSITION_YEARS)
    recent_rows = _period(rows, RECENT_YEARS)
    early = _stat(early_rows)
    transition = _stat(transition_rows)
    recent = _stat(recent_rows)
    years = {
        str(year): _stat([row for row in rows if int(row["year"]) == year])
        for year in (2024, 2025, 2026)
    }
    return {
        "features": list(features),
        "signature": {feature: value for feature, value in zip(features, signature, strict=True)},
        "all": _stat(rows),
        "early_2016_2020": early,
        "transition_2021_2023": transition,
        "recent_2024_2026": recent,
        "recent_by_year": years,
        "support_ok": _support_ok(early, transition, recent, years),
        "classification": _classify(early, transition, recent, years),
    }


def _matrix(rows: Sequence[dict[str, Any]], features: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_signature(row, features)].append(row)
    return [_cell(features, signature, grouped[signature]) for signature in sorted(grouped)]


def _rank_valid(cell: dict[str, Any]) -> Decimal:
    means = [
        _mean(cell["early_2016_2020"]),
        _mean(cell["transition_2021_2023"]),
        *[_mean(cell["recent_by_year"][str(year)]) for year in (2024, 2025, 2026)],
    ]
    values = [value for value in means if value is not None]
    return min(values) if values else Decimal("-999")


def _rank_invalid(cell: dict[str, Any]) -> Decimal:
    means = [
        _mean(cell["early_2016_2020"]),
        _mean(cell["transition_2021_2023"]),
        *[_mean(cell["recent_by_year"][str(year)]) for year in (2024, 2025, 2026)],
    ]
    values = [value for value in means if value is not None]
    return max(values) if values else Decimal("999")


def _template_summary(cells: Sequence[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = defaultdict(int)
    for cell in cells:
        counts[str(cell["classification"])] += 1
    evaluable = [cell for cell in cells if bool(cell["support_ok"])]
    robust_valid = sorted(
        (cell for cell in evaluable if cell["classification"] == "ROBUST_VALID"),
        key=_rank_valid,
        reverse=True,
    )
    robust_invalid = sorted(
        (cell for cell in evaluable if cell["classification"] == "ROBUST_INVALID"),
        key=_rank_invalid,
    )
    breaks = sorted(
        (cell for cell in evaluable if cell["classification"] == "STRUCTURAL_BREAK_TO_INVALID"),
        key=lambda cell: _d(cell["recent_2024_2026"]["mean_primary_r"] or 0),
    )
    recent_valid = sorted(
        (cell for cell in evaluable if cell["classification"] == "RECENT_STABLE_VALID"),
        key=lambda cell: _d(cell["recent_2024_2026"]["mean_primary_r"] or 0),
        reverse=True,
    )
    recent_invalid = sorted(
        (cell for cell in evaluable if cell["classification"] == "RECENT_STABLE_INVALID"),
        key=lambda cell: _d(cell["recent_2024_2026"]["mean_primary_r"] or 0),
    )
    return {
        "cells": len(cells),
        "evaluable_cells": len(evaluable),
        "classification_counts": dict(sorted(counts.items())),
        "top_robust_valid": robust_valid[:15],
        "top_robust_invalid": robust_invalid[:15],
        "top_structural_break_to_invalid": breaks[:15],
        "top_recent_stable_valid": recent_valid[:15],
        "top_recent_stable_invalid": recent_invalid[:15],
    }


def _family(row: dict[str, Any]) -> str:
    if str(row["raid_depth_range_bucket"]) == r5.STABLE_RAID:
        return "STABLE_RAID_5_10"
    if (
        str(row["raid_depth_range_bucket"]) == r5.FAILING_RAID
        and str(row["cisd_progress_bucket"]) == r5.LATE_CISD
    ):
        return "DEEP_RAID_25_50_LATE_CISD"
    return "OTHER"


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    base_rows = [causal._record(setup, trade, evidence.bars, opens) for setup, trade in selected]
    if len(base_rows) != 5885:
        raise ValueError(f"R3 reproduction drift: {len(base_rows)}")
    total = sum((_d(row["primary_net_r"]) for row in base_rows), Decimal(0))
    if abs(total - Decimal("707.7490491424")) > Decimal("0.0001"):
        raise ValueError(f"R3 R-total reproduction drift: {total}")

    d1 = r5._aggregate(evidence.bars, "D1")
    h4 = r5._aggregate(evidence.bars, "H4")
    rows: list[dict[str, Any]] = []
    for raw in base_rows:
        row = dict(raw)
        row.update(r5._regime_features(row, d1, h4))
        row["journey_family"] = _family(row)
        rows.append(row)

    matrices: dict[str, Any] = {}
    all_cells: dict[str, list[dict[str, Any]]] = {}
    for name, features in INTERACTION_TEMPLATES:
        cells = _matrix(rows, features)
        all_cells[name] = cells
        matrices[name] = {
            "features": list(features),
            "summary": _template_summary(cells),
        }

    stable = [row for row in rows if row["journey_family"] == "STABLE_RAID_5_10"]
    failing = [row for row in rows if row["journey_family"] == "DEEP_RAID_25_50_LATE_CISD"]

    payload = {
        "schema": "qore.turtle_soup_xauusd_r6.causal_interaction_matrix_forensics.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": reproduction,
        "full_r3": _stat(rows),
        "pre_registered_journey_core": list(JOURNEY_CORE),
        "pre_registered_regime_features": list(REGIME_FEATURES),
        "support_contract": {
            "min_early_2016_2020": MIN_EARLY,
            "min_transition_2021_2023": MIN_TRANSITION,
            "min_recent_2024_2026": MIN_RECENT,
            "min_each_recent_year": MIN_RECENT_YEAR,
        },
        "matrices": matrices,
        "family_reference": {
            "stable_raid_5_10": {
                "all": _stat(stable),
                "early_2016_2020": _stat(_period(stable, EARLY_YEARS)),
                "transition_2021_2023": _stat(_period(stable, TRANSITION_YEARS)),
                "recent_2024_2026": _stat(_period(stable, RECENT_YEARS)),
            },
            "deep_raid_25_50_late_cisd": {
                "all": _stat(failing),
                "early_2016_2020": _stat(_period(failing, EARLY_YEARS)),
                "transition_2021_2023": _stat(_period(failing, TRANSITION_YEARS)),
                "recent_2024_2026": _stat(_period(failing, RECENT_YEARS)),
            },
        },
        "research_question": "WHICH_PRE_ENTRY_JOURNEY_X_REGIME_INTERACTION_STATES_DISTINGUISH_TEMPORALLY_STABLE_VALID_FROM_INVALID_TURTLE_SOUP_JOURNEYS",
        "governance": {
            "diagnostic_only": True,
            "interaction_templates_pre_registered": True,
            "year_or_date_allowed_as_rule": False,
            "post_entry_leakage_allowed": False,
            "automatic_threshold_search": False,
            "rules_promoted": False,
            "fresh_holdout_consumed": False,
            "automatic_candidate_promotion": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "causal-interaction-matrix-forensics.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "interaction-cells.json").write_text(
        json.dumps(all_cells, indent=2, sort_keys=True) + "\n"
    )
    (output / "enriched-interaction-trades.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
