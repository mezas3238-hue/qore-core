"""VT08 Index R122 — R121 promotion-mechanism attribution.

R121 showed that selectively restoring exact R58 requests to the transport-
stable R120 STANDARD state improves 5Y and recent 2Y but degrades R66 overall.
R122 changes no policy. It attributes the exact incremental risk request inside
that state to the already-frozen R55/R58 promotion mechanisms and temporal
blocks.

The analysis is causal at request time and preserves the R121 signal surface.
No signal, risk, entry, stop, target, market or anchor rule is changed.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

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
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r109_standard_retest_timing_decay_attribution as r109,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r121_r120_cohort_risk_ablation as r121,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r122_promotion_mechanism_attribution.v1"
IDENTITY = "VT08_INDEX_R122_R121_PROMOTION_MECHANISM_ATTRIBUTION_001"

SOURCE_R121_RUN_ID = 36053069732
SOURCE_R121_ARTIFACT_ID = 10831129600
SOURCE_R121_ARTIFACT_DIGEST = (
    "sha256:583bbb93fbdf536565edcc234fdfff41"
    "8282968686422f7291645d0bd94823e5"
)

EXPECTED_COHORT = r121.EXPECTED_COHORT
EXPECTED_INCREMENTAL = {
    "5Y": {
        "primary": Decimal("3.157"),
        "secondary": Decimal("2.89775"),
    },
    "2Y": {
        "primary": Decimal("1.252125"),
        "secondary": Decimal("1.213"),
    },
    "R66": {
        "primary": Decimal("-0.4600234741784037558685446017"),
        "secondary": Decimal("-0.5375234741784037558685446009"),
    },
}


def _delta_metrics(
    rows: Sequence[dict[str, Any]],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    values = tuple(
        (Decimal(str(row["outcome_r"])) - stress)
        * Decimal(str(row["delta_weight"]))
        for row in rows
    )
    total = sum(values, Decimal())
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    return {
        "sample": len(values),
        "positive_delta_trades": sum(value > 0 for value in values),
        "negative_delta_trades": sum(value < 0 for value in values),
        "flat_delta_trades": sum(value == 0 for value in values),
        "total_incremental_r": str(total),
        "incremental_profit_factor": str(gains / losses) if losses else None,
    }


def _bundle(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sample": len(rows),
        "total_delta_weight_r": str(
            sum(
                (Decimal(str(row["delta_weight"])) for row in rows),
                Decimal(),
            )
        ),
        "primary": _delta_metrics(rows, stress=r102.PRIMARY_STRESS),
        "secondary": _delta_metrics(rows, stress=r102.SECONDARY_STRESS),
    }


def _group(
    rows: Sequence[dict[str, Any]],
    *,
    field: str,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return {
        label: _bundle(items)
        for label, items in sorted(groups.items())
    }


def _by_individual_label(
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for label in row["promotion_labels"]:
            groups[str(label)].append(row)
    return {
        label: _bundle(items)
        for label, items in sorted(groups.items())
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
    start_date, end_date, expected = r74._window_contract(window_id)
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        symbol: tuple(bars)
        for symbol, bars in bars_by_symbol_raw.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(stream),
        bars_by_symbol=bars_by_symbol,
    )
    base = tuple(base)
    control, control_diag = r102._apply_confidence_policy(
        base,
        bars_by_symbol=bars_by_symbol,
        policy_id=r102.POLICY_EXPLICIT_FULL,
    )
    control = tuple(control)
    if len(control) != expected:
        raise ValueError(f"R122 {window_id} control density drift")
    if int(control_diag["counts"].get("BUDGET_SCALED_BATCH", 0)) != 0:
        raise ValueError("R122 control allocator scaling changed")

    cohort_ids, cohort_diag = r121._cohort_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(cohort_ids) != EXPECTED_COHORT[window_id]:
        raise ValueError(f"R122 {window_id} cohort drift")

    variant, variant_diag = r121._apply_variant(
        base,
        bars_by_symbol=bars_by_symbol,
        cohort_ids=cohort_ids,
    )
    if len(variant) != expected:
        raise ValueError(f"R122 {window_id} variant density drift")

    control_by_identity = {
        item.opportunity.identity(): item
        for item in control
    }
    variant_by_identity = {
        item.opportunity.identity(): item
        for item in variant
    }
    if set(control_by_identity) != set(variant_by_identity):
        raise ValueError("R122 control/variant identity drift")

    h4_by_symbol = {
        symbol: v6._build_h4(
            {
                bar.opened_at.astimezone(UTC): bar
                for bar in bars
            }
        )
        for symbol, bars in bars_by_symbol.items()
    }
    reaction_bars, reaction_opened = r55._reaction_bars(bars_by_symbol)

    rows: list[dict[str, Any]] = []
    for item in base:
        identity = item.opportunity.identity()

        base_request = r102._base_request(item)
        requested, labels = r55._requested_weight(
            item,
            h4_by_symbol=h4_by_symbol,
            reaction_bars=reaction_bars,
            reaction_opened=reaction_opened,
        )
        requested_delta = requested - base_request
        control_weight = control_by_identity[identity].weight
        variant_weight = variant_by_identity[identity].weight
        effective_delta = variant_weight - control_weight
        if effective_delta == 0:
            continue

        period = r109._period_label(
            exit_date=item.exited_at.astimezone(v7._NY).date(),
            window_id=window_id,
            start_date=start_date,
            end_date=end_date,
        )
        signature = (
            "+".join(labels)
            if labels
            else "NO_R55_PROMOTION_LABEL"
        )
        change_origin = (
            "R120_COHORT"
            if identity in cohort_ids
            else "NON_COHORT_PROPAGATION"
        )
        rows.append(
            {
                "trade_id": item.trade_id,
                "change_origin": change_origin,
                "symbol": item.symbol,
                "side": item.opportunity.signal.side.value,
                "anchor": str(
                    item.opportunity.signal.h4_opened_at
                    .astimezone(v7._NY).hour
                ),
                "period": period,
                "promotion_signature": signature,
                "promotion_labels": list(labels),
                "base_request": str(base_request),
                "requested": str(requested),
                "requested_delta_weight": str(requested_delta),
                "control_effective_weight": str(control_weight),
                "variant_effective_weight": str(variant_weight),
                "delta_weight": str(effective_delta),
                "outcome_r": str(item.outcome.r_multiple),
            }
        )

    primary = _delta_metrics(rows, stress=r102.PRIMARY_STRESS)
    secondary = _delta_metrics(rows, stress=r102.SECONDARY_STRESS)
    expected_delta = EXPECTED_INCREMENTAL[window_id]
    observed_primary = Decimal(str(primary["total_incremental_r"]))
    observed_secondary = Decimal(str(secondary["total_incremental_r"]))
    if observed_primary != expected_delta["primary"]:
        raise ValueError(
            f"R122 {window_id} primary R121 delta mismatch: "
            f"observed={observed_primary} "
            f"expected={expected_delta['primary']}"
        )
    if observed_secondary != expected_delta["secondary"]:
        raise ValueError(
            f"R122 {window_id} secondary R121 delta mismatch: "
            f"observed={observed_secondary} "
            f"expected={expected_delta['secondary']}"
        )

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "r120_cohort_sample": len(cohort_ids),
        "effective_changed_trade_count": len(rows),
        "cohort_requested_promotion_count": int(
            variant_diag["counts"].get(
                "R120_COHORT_PROMOTED_ABOVE_BASE",
                0,
            )
        ),
        "cohort_diagnostics": cohort_diag,
        "variant_diagnostics": variant_diag,
        "incremental": {
            "primary": primary,
            "secondary": secondary,
        },
        "by_change_origin": _group(rows, field="change_origin"),
        "by_promotion_signature": _group(
            rows,
            field="promotion_signature",
        ),
        "by_origin_x_signature": _group(
            [
                {
                    **row,
                    "origin_x_signature": (
                        f"{row['change_origin']}|"
                        f"{row['promotion_signature']}"
                    ),
                }
                for row in rows
            ],
            field="origin_x_signature",
        ),
        "by_individual_promotion_label": _by_individual_label(rows),
        "by_period": _group(rows, field="period"),
        "by_market": _group(rows, field="symbol"),
        "by_side": _group(rows, field="side"),
        "by_anchor": _group(rows, field="anchor"),
        "rows": rows,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r121.IDENTITY != "VT08_INDEX_R121_R120_COHORT_RISK_ABLATION_001":
        raise ValueError("R122 R121 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r121": {
            "run_id": SOURCE_R121_RUN_ID,
            "artifact_id": SOURCE_R121_ARTIFACT_ID,
            "artifact_digest": SOURCE_R121_ARTIFACT_DIGEST,
            "decision": (
                "R121_R120_COHORT_RISK_ABLATION_COMPLETE_"
                "NO_CANDIDATE_SELECTED"
            ),
        },
        "attribution_contract": {
            "cohort": (
                "STANDARD|CLOSE_BREAKOUT|"
                "PRIOR_DEEPER_THAN_FINAL_PS"
            ),
            "request_function": "R55._requested_weight",
            "control_policy": r102.POLICY_EXPLICIT_FULL,
            "policy_changed": False,
            "signal_surface_changed": False,
            "outcome_used_for_classification": False,
        },
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_failed_holdout": _window(roots=roots, window_id="R66"),
        "decision": (
            "R122_R121_PROMOTION_MECHANISM_ATTRIBUTION_COMPLETE_"
            "NO_RULE_CHANGE"
        ),
        "governance": {
            "research_only": True,
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "policy_changed": False,
            "signals_suppressed": False,
            "risk_changed": False,
            "entries_changed": False,
            "stops_changed": False,
            "targets_changed": False,
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
                    "changed": report["five_year"]["effective_changed_trade_count"],
                    "cohort_requested_promotions": report["five_year"][
                        "cohort_requested_promotion_count"
                    ],
                    "incremental": report["five_year"]["incremental"],
                    "by_signature": report["five_year"][
                        "by_promotion_signature"
                    ],
                    "by_period": report["five_year"]["by_period"],
                },
                "recent_two_year": {
                    "changed": report["recent_two_year"][
                        "effective_changed_trade_count"
                    ],
                    "cohort_requested_promotions": report[
                        "recent_two_year"
                    ]["cohort_requested_promotion_count"],
                    "incremental": report["recent_two_year"]["incremental"],
                    "by_signature": report["recent_two_year"][
                        "by_promotion_signature"
                    ],
                    "by_period": report["recent_two_year"]["by_period"],
                },
                "r66": {
                    "changed": report["r66_failed_holdout"][
                        "effective_changed_trade_count"
                    ],
                    "cohort_requested_promotions": report[
                        "r66_failed_holdout"
                    ]["cohort_requested_promotion_count"],
                    "incremental": report["r66_failed_holdout"][
                        "incremental"
                    ],
                    "by_signature": report["r66_failed_holdout"][
                        "by_promotion_signature"
                    ],
                    "by_period": report["r66_failed_holdout"]["by_period"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
