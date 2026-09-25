"""VT08 Index R129 — R128 strict-context overlap and risk saturation.

R128 isolated six CLOSE_BREAKOUT | NO_FAILED_ATTEMPT subcontexts that are
secondary-stress negative across 5Y, recent2Y and R66 and also negative in R66
B2. R129 changes NOTHING. It asks two questions before any new ablation:

1. Are those six labels independent drivers or mostly overlapping views of the
   same trades?
2. Is there any effective risk above the existing 0.005R floor, or would a
   further risk demotion be economically inert?

The six labels are frozen directly from the successful R128 artifact. They are
classified as:
- reactive portfolio state: LOSS_DEFENSE, LOW concurrent pressure, L2_3 loss cluster;
- structural market state: recent daily range compressed, previous source-day
  body opposed;
- market diagnostic: SP500.

Calendar periods are attached only after the pre-entry classifications. No
filter, risk change, entry/stop/target change, market removal, candidate or LIVE
authority is created.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r105_standard_context_transport_atlas as r105,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r128_close_breakout_no_attempt_context_transport as r128,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r129_r128_context_overlap_saturation.v1"
IDENTITY = "VT08_INDEX_R129_R128_CONTEXT_OVERLAP_RISK_SATURATION_001"

SOURCE_R128_RUN_ID = 36075966463
SOURCE_R128_ARTIFACT_ID = 10839358300
SOURCE_R128_ARTIFACT_DIGEST = (
    "sha256:d69448f6dc7fe3b4d49c9be54b18c315"
    "8238d38e0e0f1e953ef5a43705f103a9"
)

FLOOR = r55.MIN_EFFECTIVE_WEIGHT
MIN_REPORT_SAMPLE = r128.MIN_REPORT_SAMPLE


@dataclass(frozen=True, slots=True)
class ContextSpec:
    context_id: str
    dimension: str
    label: str
    family: str


CONTEXTS = (
    ContextSpec("LOSS_DEFENSE", "governor_state", "LOSS_DEFENSE", "REACTIVE"),
    ContextSpec("LOW_CONCURRENT", "concurrent_pressure", "LOW", "REACTIVE"),
    ContextSpec("LOSS_CLUSTER_L2_3", "loss_cluster", "L2_3", "REACTIVE"),
    ContextSpec(
        "DAILY_COMPRESSED",
        "recent_daily_range_state",
        "compressed",
        "STRUCTURAL",
    ),
    ContextSpec(
        "PREV_BODY_OPPOSED",
        "previous_source_day_body_alignment",
        "opposed",
        "STRUCTURAL",
    ),
    ContextSpec("SP500", "symbol", "SP500", "MARKET_DIAGNOSTIC"),
)

CONTEXT_BY_ID = {context.context_id: context for context in CONTEXTS}
REACTIVE_IDS = frozenset(
    context.context_id
    for context in CONTEXTS
    if context.family == "REACTIVE"
)
STRUCTURAL_IDS = frozenset(
    context.context_id
    for context in CONTEXTS
    if context.family == "STRUCTURAL"
)


def _matches(row: dict[str, Any], context: ContextSpec) -> bool:
    return str(row[context.dimension]) == context.label


def _memberships(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        context.context_id
        for context in CONTEXTS
        if _matches(row, context)
    )


def _economic(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "primary": r105._metrics_rows(
            rows,
            stress=r102.PRIMARY_STRESS,
        ),
        "secondary": r105._metrics_rows(
            rows,
            stress=r102.SECONDARY_STRESS,
        ),
    }


def _risk_bundle(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    weights = tuple(
        Decimal(str(row["effective_weight"]))
        for row in rows
    )
    floor_count = sum(weight == FLOOR for weight in weights)
    above_floor = sum(weight > FLOOR for weight in weights)
    return {
        "sample": len(rows),
        "floor_count": floor_count,
        "above_floor_count": above_floor,
        "floor_fraction": (
            str(Decimal(floor_count) / Decimal(len(rows)))
            if rows
            else "0"
        ),
        "mean_effective_weight_r": (
            str(sum(weights, Decimal()) / Decimal(len(weights)))
            if weights
            else "0"
        ),
        "economics": _economic(rows),
    }


def _profile(
    rows: Sequence[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    selected = [row for row in rows if predicate(row)]
    return _risk_bundle(selected)


def _context_predicate(
    context: ContextSpec,
) -> Callable[[dict[str, Any]], bool]:
    def predicate(row: dict[str, Any]) -> bool:
        return _matches(row, context)

    return predicate


def _pair_predicate(
    left: ContextSpec,
    right: ContextSpec,
) -> Callable[[dict[str, Any]], bool]:
    def predicate(row: dict[str, Any]) -> bool:
        return _matches(row, left) and _matches(row, right)

    return predicate


def _context_profiles(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for context in CONTEXTS:
        result[context.context_id] = {
            "dimension": context.dimension,
            "label": context.label,
            "family": context.family,
            **_profile(rows, _context_predicate(context)),
        }
    return result


def _pairwise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for index, left in enumerate(CONTEXTS):
        for right in CONTEXTS[index + 1 :]:
            key = f"{left.context_id}&{right.context_id}"
            result[key] = _profile(
                rows,
                _pair_predicate(left, right),
            )
    return result


def _signature_profiles(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        memberships = _memberships(row)
        key = "|".join(memberships) if memberships else "NONE"
        grouped[key].append(row)
    return {
        key: _risk_bundle(items)
        for key, items in sorted(grouped.items())
        if len(items) >= MIN_REPORT_SAMPLE
    }


def _family_profiles(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    def has_any(row: dict[str, Any], ids: frozenset[str]) -> bool:
        return any(context_id in ids for context_id in _memberships(row))

    return {
        "ANY_REACTIVE": _profile(
            rows,
            lambda row: has_any(row, REACTIVE_IDS),
        ),
        "NO_REACTIVE": _profile(
            rows,
            lambda row: not has_any(row, REACTIVE_IDS),
        ),
        "ANY_STRUCTURAL": _profile(
            rows,
            lambda row: has_any(row, STRUCTURAL_IDS),
        ),
        "STRUCTURAL_WITHOUT_REACTIVE": _profile(
            rows,
            lambda row: (
                has_any(row, STRUCTURAL_IDS)
                and not has_any(row, REACTIVE_IDS)
            ),
        ),
        "DAILY_COMPRESSED_WITHOUT_REACTIVE": _profile(
            rows,
            lambda row: (
                _matches(row, CONTEXT_BY_ID["DAILY_COMPRESSED"])
                and not has_any(row, REACTIVE_IDS)
            ),
        ),
        "LOW_CONCURRENT_WITHOUT_STRUCTURAL": _profile(
            rows,
            lambda row: (
                _matches(row, CONTEXT_BY_ID["LOW_CONCURRENT"])
                and not has_any(row, STRUCTURAL_IDS)
            ),
        ),
    }


def _period_profiles(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    periods: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        periods[str(row["period_id"])].append(row)
    return {
        period: {
            "sample": len(items),
            "contexts": _context_profiles(items),
            "families": _family_profiles(items),
        }
        for period, items in sorted(periods.items())
        if period != "OUTSIDE"
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    stream, bars_by_symbol_raw, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        symbol: tuple(bars)
        for symbol, bars in bars_by_symbol_raw.items()
    }
    rows, canonical_count, standard_count = r128._cohort_rows(
        stream=stream,
        bars_by_symbol=bars_by_symbol,
        window_id=window_id,
    )

    if canonical_count != r128.EXPECTED_CANONICAL[window_id]:
        raise ValueError(f"R129 {window_id} canonical drift")
    if standard_count != r128.EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R129 {window_id} STANDARD drift")
    if len(rows) != r128.EXPECTED_COHORT[window_id]:
        raise ValueError(f"R129 {window_id} cohort drift")

    membership_count = sum(bool(_memberships(row)) for row in rows)
    return {
        "window_id": window_id,
        "canonical_sample": canonical_count,
        "standard_sample": standard_count,
        "cohort_sample": len(rows),
        "cohort_state": r128.COHORT_STATE,
        "any_strict_context_count": membership_count,
        "no_strict_context_count": len(rows) - membership_count,
        "cohort": _risk_bundle(rows),
        "contexts": _context_profiles(rows),
        "families": _family_profiles(rows),
        "pairwise_overlap": _pairwise(rows),
        "signature_profiles_min20": _signature_profiles(rows),
        "period_profiles": _period_profiles(rows),
        "provenance": provenance,
    }


def _transport_summary(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for context in CONTEXTS:
        values = [
            five["contexts"][context.context_id],
            two["contexts"][context.context_id],
            failed["contexts"][context.context_id],
        ]
        b2 = failed["period_profiles"]["B2"]["contexts"][
            context.context_id
        ]
        result.append(
            {
                "context_id": context.context_id,
                "family": context.family,
                "dimension": context.dimension,
                "label": context.label,
                "samples": {
                    "five_year": values[0]["sample"],
                    "recent_two_year": values[1]["sample"],
                    "r66": values[2]["sample"],
                    "r66_b2": b2["sample"],
                },
                "floor_fraction": {
                    "five_year": values[0]["floor_fraction"],
                    "recent_two_year": values[1]["floor_fraction"],
                    "r66": values[2]["floor_fraction"],
                    "r66_b2": b2["floor_fraction"],
                },
                "above_floor_count": {
                    "five_year": values[0]["above_floor_count"],
                    "recent_two_year": values[1]["above_floor_count"],
                    "r66": values[2]["above_floor_count"],
                    "r66_b2": b2["above_floor_count"],
                },
                "secondary_total_r": {
                    "five_year": values[0]["economics"]["secondary"]["total_r"],
                    "recent_two_year": values[1]["economics"]["secondary"]["total_r"],
                    "r66": values[2]["economics"]["secondary"]["total_r"],
                    "r66_b2": b2["economics"]["secondary"]["total_r"],
                },
                "risk_demotion_actionable": any(
                    int(value["above_floor_count"]) > 0
                    for value in [*values, b2]
                ),
            }
        )
    return result


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r128.IDENTITY != (
        "VT08_INDEX_R128_CLOSE_BREAKOUT_NO_FAILED_ATTEMPT_"
        "CONTEXT_TRANSPORT_ATLAS_001"
    ):
        raise ValueError("R129 R128 identity drift")

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
        "source_r128": {
            "run_id": SOURCE_R128_RUN_ID,
            "artifact_id": SOURCE_R128_ARTIFACT_ID,
            "artifact_digest": SOURCE_R128_ARTIFACT_DIGEST,
            "decision": (
                "R128_CLOSE_BREAKOUT_NO_FAILED_ATTEMPT_CONTEXT_"
                "TRANSPORT_COMPLETE_NO_RULE_CHANGE"
            ),
        },
        "frozen_contexts": [
            {
                "context_id": context.context_id,
                "dimension": context.dimension,
                "label": context.label,
                "family": context.family,
            }
            for context in CONTEXTS
        ],
        "risk_contract": {
            "floor_r": str(FLOOR),
            "risk_changed": False,
            "released_risk_reallocated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport_summary": _transport_summary(five, two, failed),
        "decision": (
            "R129_R128_CONTEXT_OVERLAP_RISK_SATURATION_"
            "COMPLETE_NO_RULE_CHANGE"
        ),
        "governance": {
            "research_only": True,
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "calendar_or_year_runtime_feature": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "risk_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "market_removed": False,
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
                "transport_summary": report["transport_summary"],
                "r66_b2_families": report["r66_failed_holdout"][
                    "period_profiles"
                ]["B2"]["families"],
                "r66_b2_signatures": report["r66_failed_holdout"][
                    "period_profiles"
                ]["B2"]["sample"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
