"""VT08 Index R106 — bounded STANDARD causal-demotion ablation.

R105 identified STANDARD pre-entry contexts that are adverse in all three
consumed windows, with corroboration outside R66. R106 tests them one at a time
as risk demotions only.

The control is R102 EXPLICIT_FULL_R58_STANDARD_BASE. Every variant preserves:
- the exact 2448 / 1017 / 773 signal surfaces;
- entries, stops, targets, markets and anchors;
- the explicit-PS R58 promotion logic from R102;
- the 0.005R existing positive-risk floor;
- no released-risk reallocation.

Only STANDARD_WITHOUT_EXTRA_PS trades matching one preregistered causal state
are demoted to the existing 0.005R floor.

No combinations are evaluated and no variant is auto-selected. R66 remains
consumed failure evidence.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r46_cross_window_transport_forensics as r46,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
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
    vt08_index_r105_standard_context_transport_atlas as r105,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r106_standard_causal_demotion_ablation.v1"
IDENTITY = "VT08_INDEX_R106_STANDARD_CAUSAL_DEMOTION_ABLATION_001"

SOURCE_R105_RUN_ID = 35556744176
SOURCE_R105_ARTIFACT_ID = 10620118359
SOURCE_R105_ARTIFACT_DIGEST = (
    "sha256:6a81182ff3e710509b755cad94cb84f1901adfdb02aa706a444c7591fe1df381"
)
BASE_POLICY_ID = r102.POLICY_EXPLICIT_FULL
FLOOR = r55.MIN_EFFECTIVE_WEIGHT


@dataclass(frozen=True, slots=True)
class DemotionPolicy:
    policy_id: str
    dimension: str | None
    label: str | None


POLICIES = (
    DemotionPolicy("CONTROL_R102_EXPLICIT_FULL", None, None),
    DemotionPolicy(
        "STANDARD_CURRENT_SOURCE_DAY_BODY_OPPOSED",
        "current_source_day_body_alignment",
        "opposed",
    ),
    DemotionPolicy(
        "STANDARD_SHORT_CISD",
        "side_poi",
        "short|cisd",
    ),
    DemotionPolicy(
        "STANDARD_RISK_FRACTION_030_050",
        "risk_fraction_bucket",
        "0.30-0.50%",
    ),
    DemotionPolicy(
        "STANDARD_C2_CLOSURE_NEXT_H4_EXPANSION",
        "model_kind",
        "c2-closure-next-h4-expansion",
    ),
    DemotionPolicy(
        "STANDARD_H4_ENTRY_LATENCY_61_120",
        "h4_entry_latency_bucket",
        "61-120m",
    ),
)


def _feature_map(
    *,
    stream: Sequence[tuple[Any, Any]],
    assigned: Sequence[r15.AssignedTrade],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    window_id: str,
) -> dict[tuple[object, ...], dict[str, Any]]:
    stream_ids = [opportunity.identity() for opportunity, _outcome in stream]
    assigned_ids = [item.opportunity.identity() for item in assigned]
    if stream_ids != assigned_ids:
        raise ValueError("R106 stream/assigned ordering drift")

    trace = r46._causal_trace(stream)
    rows = r46._feature_rows(
        assigned=assigned,
        trace=trace,
        window_id=("2Y" if window_id == "R66" else window_id),
        bars_by_symbol=bars_by_symbol,
    )
    result = {
        item.opportunity.identity(): row
        for item, row in zip(assigned, rows, strict=True)
    }
    if len(result) != len(assigned):
        raise ValueError("R106 feature identity collision")
    return result


def _standard_identity_set(
    assigned: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> set[tuple[object, ...]]:
    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }
    result: set[tuple[object, ...]] = set()
    for item in assigned:
        classification = r82._classify_opportunity(
            item.opportunity,
            h4_bars=h4_cache[item.symbol],
        )
        if str(classification["family"]) == r82.FAMILY_UNQUALIFIED:
            result.add(item.opportunity.identity())
    return result


def _apply_policy(
    control: Sequence[r15.AssignedTrade],
    *,
    feature_map: dict[tuple[object, ...], dict[str, Any]],
    standard_ids: set[tuple[object, ...]],
    policy: DemotionPolicy,
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    assigned: list[r15.AssignedTrade] = []
    demoted = 0
    released = Decimal()

    for item in control:
        identity = item.opportunity.identity()
        weight = item.weight
        matched = False
        if policy.dimension is not None and identity in standard_ids:
            row = feature_map[identity]
            matched = str(row[policy.dimension]) == str(policy.label)
        if matched:
            new_weight = min(weight, FLOOR)
            if new_weight < weight:
                demoted += 1
                released += weight - new_weight
            weight = new_weight

        assigned.append(
            r15.AssignedTrade(
                trade_id=item.trade_id,
                opportunity=item.opportunity,
                outcome=item.outcome,
                context=item.context,
                weight=weight,
            )
        )

    result = tuple(assigned)
    if len(result) != len(control):
        raise ValueError("R106 policy changed signal count")
    if any(item.weight < FLOOR for item in result):
        raise ValueError("R106 policy fell below positive-risk floor")
    if any(item.weight > control[index].weight for index, item in enumerate(result)):
        raise ValueError("R106 demotion increased risk")

    return result, {
        "policy_id": policy.policy_id,
        "dimension": policy.dimension,
        "label": policy.label,
        "demoted_trade_count": demoted,
        "released_risk_not_reallocated_r": str(released),
        "minimum_effective_weight_r": str(min(item.weight for item in result)),
        "maximum_effective_weight_r": str(max(item.weight for item in result)),
        "mean_effective_weight_r": str(
            sum((item.weight for item in result), Decimal()) / len(result)
        ),
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    stream, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    _start, _end, expected = r74._window_contract(window_id)
    bars: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        key: tuple(value)
        for key, value in bars_by_symbol.items()
    }
    opened = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(stream),
        bars_by_symbol=bars,
    )
    base = tuple(base)
    control, control_diag = r102._apply_confidence_policy(
        base,
        bars_by_symbol=bars,
        policy_id=BASE_POLICY_ID,
    )
    control = tuple(control)

    features = _feature_map(
        stream=stream,
        assigned=control,
        bars_by_symbol=bars,
        window_id=window_id,
    )
    standard_ids = _standard_identity_set(
        control,
        bars_by_symbol=bars,
    )

    variants: dict[str, Any] = {}
    for policy in POLICIES:
        assigned, diagnostics = _apply_policy(
            control,
            feature_map=features,
            standard_ids=standard_ids,
            policy=policy,
        )
        if len(assigned) != expected:
            raise ValueError(f"R106 {window_id} sample drift")

        if window_id == "5Y":
            metrics = r47._window_metrics(
                assigned,
                bars_by_symbol=bars,
                opened_by_symbol=opened,
                years=5,
            )
        elif window_id == "2Y":
            metrics = r47._window_metrics(
                assigned,
                bars_by_symbol=bars,
                opened_by_symbol=opened,
                years=2,
            )
        else:
            metrics = r102._r66_metrics(
                assigned,
                bars_by_symbol=bars,
                opened_by_symbol=opened,
            )

        variants[policy.policy_id] = {
            "metrics": metrics,
            "diagnostics": diagnostics,
            "concentration": r55._concentration(assigned),
        }

    return {
        "window_id": window_id,
        "sample": expected,
        "standard_sample": len(standard_ids),
        "control_diagnostics": control_diag,
        "variants": variants,
        "provenance": provenance,
    }


def _summary(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for policy in POLICIES:
        policy_id = policy.policy_id
        f = five["variants"][policy_id]["metrics"]
        t = two["variants"][policy_id]["metrics"]
        r = failed["variants"][policy_id]["metrics"]
        rows.append(
            {
                "policy_id": policy_id,
                "demotion": {
                    "dimension": policy.dimension,
                    "label": policy.label,
                },
                "demoted_trades": {
                    "five_year": five["variants"][policy_id]["diagnostics"][
                        "demoted_trade_count"
                    ],
                    "recent_two_year": two["variants"][policy_id]["diagnostics"][
                        "demoted_trade_count"
                    ],
                    "r66": failed["variants"][policy_id]["diagnostics"][
                        "demoted_trade_count"
                    ],
                },
                "five_year": {
                    "primary_pf": f["primary"]["profit_factor"],
                    "secondary_pf": f["secondary"]["profit_factor"],
                    "secondary_total_r": f["secondary"]["total_r"],
                    "primary_mtm_dd_r": f[
                        "primary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "secondary_mtm_dd_r": f[
                        "secondary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "temporal_pass": f["temporal_pass"],
                    "economic_pass": f["economic_pass"],
                },
                "recent_two_year": {
                    "primary_pf": t["primary"]["profit_factor"],
                    "secondary_pf": t["secondary"]["profit_factor"],
                    "secondary_total_r": t["secondary"]["total_r"],
                    "primary_mtm_dd_r": t[
                        "primary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "secondary_mtm_dd_r": t[
                        "secondary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "temporal_pass": t["temporal_pass"],
                    "economic_pass": t["economic_pass"],
                },
                "r66": {
                    "primary_pf": r["primary"]["profit_factor"],
                    "secondary_pf": r["secondary"]["profit_factor"],
                    "primary_total_r": r["primary"]["total_r"],
                    "secondary_total_r": r["secondary"]["total_r"],
                    "primary_mtm_dd_r": r[
                        "primary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "secondary_mtm_dd_r": r[
                        "secondary_conservative_mark_to_market"
                    ]["max_drawdown_r"],
                    "all_primary_blocks_positive": r[
                        "all_primary_blocks_positive"
                    ],
                    "all_secondary_blocks_positive": r[
                        "all_secondary_blocks_positive"
                    ],
                },
            }
        )
    return rows


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r105.IDENTITY != (
        "VT08_INDEX_R105_STANDARD_CAUSAL_CONTEXT_TRANSPORT_ATLAS_001"
    ):
        raise ValueError("R106 R105 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    if (five["sample"], two["sample"], failed["sample"]) != (2448, 1017, 773):
        raise ValueError("R106 canonical sample drift")
    if (
        five["standard_sample"],
        two["standard_sample"],
        failed["standard_sample"],
    ) != (1756, 746, 546):
        raise ValueError("R106 STANDARD sample drift")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r105": {
            "run_id": SOURCE_R105_RUN_ID,
            "artifact_id": SOURCE_R105_ARTIFACT_ID,
            "artifact_digest": SOURCE_R105_ARTIFACT_DIGEST,
        },
        "base_policy_id": BASE_POLICY_ID,
        "positive_risk_floor_r": str(FLOOR),
        "policies": [
            {
                "policy_id": policy.policy_id,
                "dimension": policy.dimension,
                "label": policy.label,
            }
            for policy in POLICIES
        ],
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport_summary": _summary(five, two, failed),
        "decision": "R106_STANDARD_CAUSAL_DEMOTION_ABLATION_COMPLETE_NO_CANDIDATE_SELECTED",
        "governance": {
            "forensics_only": True,
            "bounded_single_feature_ablation": True,
            "combination_search_used": False,
            "variant_auto_selected": False,
            "r66_consumed_failure_evidence": True,
            "fresh_holdout_claim": False,
            "signals_suppressed": False,
            "entries_changed": False,
            "stops_changed": False,
            "targets_changed": False,
            "released_risk_reallocated": False,
            "new_risk_constant": False,
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
                "transport_summary": report["transport_summary"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
