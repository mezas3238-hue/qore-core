"""VT08 Index R128 — CLOSE_BREAKOUT / NO_FAILED_ATTEMPT context transport atlas.

R127 showed that widening the transport-adverse SWEEP_REVERSAL /
PRIOR_DEEPER_THAN_FINAL_PS stop to the earlier failed-attempt extreme is
unlikely to be the main R66 B2 repair: most stopped trades breach that deeper
extreme within 24h and only a small minority recover the canonical 2.5R move
before doing so.

R123 also shows that the larger R66 B2 loss driver is:

    CLOSE_BREAKOUT | NO_FAILED_ATTEMPT

R128 changes NOTHING. It isolates that exact STANDARD cohort and reuses the
pre-entry causal feature vocabulary frozen in R105/R46. The objective is to
find whether the B2 collapse is concentrated in a feature state that is already
adverse across 5Y, recent2Y and R66 whole windows, rather than a calendar-only
artifact.

All feature labels are known at or before entry. B2 is used only after
classification for attribution. No signal suppression, risk change, entry,
stop, target, market, side, anchor or candidate rule is created.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r46_cross_window_transport_forensics as r46,
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
from qore.infrastructure.trader_lab import (
    vt08_index_r124_targeted_source_retest as r124,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r127_target_state_stop_afterlife as r127,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = (
    "qore.trader_lab."
    "vt08_index_r128_close_breakout_no_attempt_context_transport.v1"
)
IDENTITY = (
    "VT08_INDEX_R128_CLOSE_BREAKOUT_NO_FAILED_ATTEMPT_"
    "CONTEXT_TRANSPORT_ATLAS_001"
)

SOURCE_R127_RUN_ID = 36075356615
SOURCE_R127_ARTIFACT_ID = 10839628548
SOURCE_R127_ARTIFACT_DIGEST = (
    "sha256:e604bf6828ab9b38d1d88f239ff36ffd"
    "67d46cb37755f0154c0038fb4474877b"
)

COHORT_STATE = "CLOSE_BREAKOUT|NO_FAILED_ATTEMPT"
EXPECTED_CANONICAL = {"5Y": 2448, "2Y": 1017, "R66": 773}
EXPECTED_STANDARD = {"5Y": 1756, "2Y": 746, "R66": 546}
EXPECTED_COHORT = {"5Y": 578, "2Y": 230, "R66": 161}
MIN_REPORT_SAMPLE = 20


def _cohort_rows(
    *,
    stream: Sequence[tuple[Any, Any]],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    window_id: str,
) -> tuple[list[dict[str, Any]], int, int]:
    base, _base_diag = r58._exact_r47(
        tuple(stream),
        bars_by_symbol=bars_by_symbol,
    )
    final, _policy_diag = r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=r102.POLICY_EXPLICIT_FULL,
    )
    final = tuple(final)

    trace = r46._causal_trace(stream)
    feature_rows = r46._feature_rows(
        assigned=final,
        trace=trace,
        window_id=("2Y" if window_id == "R66" else window_id),
        bars_by_symbol=bars_by_symbol,
    )
    if len(feature_rows) != len(final):
        raise ValueError("R128 feature row alignment drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }
    indexed_by_symbol = {
        symbol: {
            bar.opened_at.astimezone(UTC): bar
            for bar in bars
        }
        for symbol, bars in bars_by_symbol.items()
    }

    standard_count = 0
    rows: list[dict[str, Any]] = []
    for item, feature in zip(final, feature_rows, strict=True):
        classification = r82._classify_opportunity(
            item.opportunity,
            h4_bars=h4_cache[item.symbol],
        )
        if str(classification["family"]) != r82.FAMILY_UNQUALIFIED:
            continue
        standard_count += 1

        state, _inside = r124._state_for_item(
            item,
            indexed_by_symbol=indexed_by_symbol,
            h4_cache=h4_cache,
        )
        if state != COHORT_STATE:
            continue

        row = dict(feature)
        row["window_id"] = window_id
        row["cohort_state"] = state
        row["period_id"] = r105._period_id(
            window_id,
            item.exited_at.astimezone(v7._NY).date(),
        )
        rows.append(row)

    return rows, len(final), standard_count


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
    rows, canonical_count, standard_count = _cohort_rows(
        stream=stream,
        bars_by_symbol=bars_by_symbol,
        window_id=window_id,
    )

    if canonical_count != EXPECTED_CANONICAL[window_id]:
        raise ValueError(f"R128 {window_id} canonical drift")
    if standard_count != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R128 {window_id} STANDARD drift")
    if len(rows) != EXPECTED_COHORT[window_id]:
        raise ValueError(
            f"R128 {window_id} cohort drift: "
            f"{len(rows)} != {EXPECTED_COHORT[window_id]}"
        )

    return {
        "window_id": window_id,
        "canonical_sample": canonical_count,
        "standard_sample": standard_count,
        "cohort_state": COHORT_STATE,
        "cohort_sample": len(rows),
        "primary": r105._metrics_rows(
            rows,
            stress=r102.PRIMARY_STRESS,
        ),
        "secondary": r105._metrics_rows(
            rows,
            stress=r102.SECONDARY_STRESS,
        ),
        "breakdowns": {
            dimension: r105._breakdown(
                rows,
                dimension=dimension,
            )
            for dimension in r105.DIMENSIONS
        },
        "period_breakdowns": {
            dimension: r105._period_breakdown(
                rows,
                dimension=dimension,
            )
            for dimension in r105.DIMENSIONS
        },
        "provenance": provenance,
    }


def _metric(
    section: dict[str, Any],
    *,
    dimension: str,
    label: str,
) -> dict[str, Any] | None:
    value = section["breakdowns"][dimension].get(label)
    return value if isinstance(value, dict) else None


def _period_metric(
    section: dict[str, Any],
    *,
    dimension: str,
    label: str,
    period: str,
) -> dict[str, Any] | None:
    value = section["period_breakdowns"][dimension].get(
        label,
        {},
    ).get(period)
    return value if isinstance(value, dict) else None


def _ranked_contexts(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for dimension in r105.DIMENSIONS:
        labels = (
            set(five["breakdowns"][dimension])
            | set(two["breakdowns"][dimension])
            | set(failed["breakdowns"][dimension])
        )
        for label in sorted(labels):
            f = _metric(five, dimension=dimension, label=label)
            t = _metric(two, dimension=dimension, label=label)
            r = _metric(failed, dimension=dimension, label=label)
            b2 = _period_metric(
                failed,
                dimension=dimension,
                label=label,
                period="B2",
            )
            if not all(isinstance(x, dict) for x in (f, t, r, b2)):
                continue
            assert f is not None
            assert t is not None
            assert r is not None
            assert b2 is not None

            samples = {
                "five_year": int(f["sample"]),
                "recent_two_year": int(t["sample"]),
                "r66": int(r["sample"]),
                "r66_b2": int(b2["sample"]),
            }
            if min(samples.values()) < MIN_REPORT_SAMPLE:
                continue

            totals = {
                "five_year": Decimal(
                    str(f["secondary"]["total_r"])
                ),
                "recent_two_year": Decimal(
                    str(t["secondary"]["total_r"])
                ),
                "r66": Decimal(str(r["secondary"]["total_r"])),
                "r66_b2": Decimal(str(b2["secondary"]["total_r"])),
            }
            if totals["r66_b2"] >= 0:
                continue

            five_periods = five["period_breakdowns"][dimension].get(
                label,
                {},
            )
            two_periods = two["period_breakdowns"][dimension].get(
                label,
                {},
            )
            non_r66_blocks = [
                block
                for block in (
                    list(five_periods.values())
                    + list(two_periods.values())
                )
                if int(block["sample"]) >= MIN_REPORT_SAMPLE
            ]
            adverse_non_r66_blocks = sum(
                Decimal(str(block["secondary"]["total_r"])) < 0
                for block in non_r66_blocks
            )

            negative_whole_windows = sum(
                totals[key] < 0
                for key in (
                    "five_year",
                    "recent_two_year",
                    "r66",
                )
            )
            strict_transport_adverse = (
                negative_whole_windows == 3
            )

            result.append(
                {
                    "dimension": dimension,
                    "label": label,
                    "samples": samples,
                    "secondary_total_r": {
                        key: str(value)
                        for key, value in totals.items()
                    },
                    "secondary_pf": {
                        "five_year": f["secondary"]["profit_factor"],
                        "recent_two_year": t["secondary"][
                            "profit_factor"
                        ],
                        "r66": r["secondary"]["profit_factor"],
                        "r66_b2": b2["secondary"]["profit_factor"],
                    },
                    "negative_whole_window_count": (
                        negative_whole_windows
                    ),
                    "strict_transport_adverse": (
                        strict_transport_adverse
                    ),
                    "non_r66_periods_considered": len(
                        non_r66_blocks
                    ),
                    "non_r66_adverse_periods": (
                        adverse_non_r66_blocks
                    ),
                }
            )

    result.sort(
        key=lambda row: (
            -int(bool(row["strict_transport_adverse"])),
            -int(row["negative_whole_window_count"]),
            -int(row["non_r66_adverse_periods"]),
            Decimal(str(row["secondary_total_r"]["r66_b2"])),
            -int(row["samples"]["r66_b2"]),
        )
    )
    return result


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r127.IDENTITY != (
        "VT08_INDEX_R127_TARGET_STATE_STOP_AFTERLIFE_ATTRIBUTION_001"
    ):
        raise ValueError("R128 R127 identity drift")
    if r105.IDENTITY != (
        "VT08_INDEX_R105_STANDARD_CAUSAL_CONTEXT_TRANSPORT_ATLAS_001"
    ):
        raise ValueError("R128 R105 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")
    ranked = _ranked_contexts(five, two, failed)
    strict = [
        row
        for row in ranked
        if bool(row["strict_transport_adverse"])
    ]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r127": {
            "run_id": SOURCE_R127_RUN_ID,
            "artifact_id": SOURCE_R127_ARTIFACT_ID,
            "artifact_digest": SOURCE_R127_ARTIFACT_DIGEST,
            "decision": (
                "R127_TARGET_STATE_STOP_AFTERLIFE_ATTRIBUTION_"
                "COMPLETE_NO_RULE_CHANGE"
            ),
        },
        "cohort_contract": {
            "state": COHORT_STATE,
            "classification_cutoff": "ENTRY",
            "calendar_or_year_runtime_feature": False,
            "minimum_reporting_sample": MIN_REPORT_SAMPLE,
            "dimensions": list(r105.DIMENSIONS),
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "ranked_b2_adverse_contexts": ranked,
        "strict_transport_adverse_contexts": strict,
        "decision": (
            "R128_CLOSE_BREAKOUT_NO_FAILED_ATTEMPT_CONTEXT_"
            "TRANSPORT_COMPLETE_NO_RULE_CHANGE"
        ),
        "governance": {
            "research_only": True,
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "all_predictors_known_at_or_before_entry": True,
            "calendar_or_year_used_as_runtime_feature": False,
            "optimization_grid_used": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "risk_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
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
                    "five_year": report["five_year"]["cohort_sample"],
                    "recent_two_year": report["recent_two_year"][
                        "cohort_sample"
                    ],
                    "r66": report["r66_failed_holdout"][
                        "cohort_sample"
                    ],
                },
                "strict_transport_adverse_contexts": report[
                    "strict_transport_adverse_contexts"
                ],
                "top_ranked_contexts": report[
                    "ranked_b2_adverse_contexts"
                ][:20],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
