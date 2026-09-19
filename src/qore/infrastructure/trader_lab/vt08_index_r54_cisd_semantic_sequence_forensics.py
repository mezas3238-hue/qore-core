"""VT08 Index R54 — semantic CISD sequence and concentration forensics.

R54 consumes the official R46 source-complete feature matrix and R53 reaction
forensics. It does not replay prices, alter R47, choose a candidate, or change
risk. Its purpose is to explain the causal timing sequence behind the R53 clue.

The timing contract follows existing Core labs:
- CISD -> continuation latency uses the frozen R17 causal taxonomy.
- departure/continuation semantics follow CIBO Semantic V2.
- reaction timing comes from R53, itself reusing Reaction Structure Atlas.

All analyzed windows are consumed development evidence.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import vt08_index_cibo_semantic_v2 as semantic
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r17_formation_quality_forensics as r17

SCHEMA = "qore.trader_lab.vt08_index_r54_cisd_semantic_sequence_forensics.v1"
IDENTITY = "VT08_INDEX_R54_CISD_SEMANTIC_SEQUENCE_FORENSICS_001"
SECONDARY_STRESS = Decimal("0.10")
R53_IDENTITY = "VT08_INDEX_R53_SOURCE_COMPLETE_CISD_REACTION_QUALITY_FORENSICS_001"
R47_CANDIDATE_ID = "VT08_INDEX_R47_TRANSPORT_SAFE_STRUCTURAL_DEMOTION_001"
R47_RULE_FINGERPRINT = (
    "013bffb847dff546cdb2a31ac9931bdb1336596c540f6a72c5c729d1762c36c8"
)

SOURCE_R46_RUN_ID = 35438709936
SOURCE_R46_ARTIFACT_ID = 10583481521
SOURCE_R46_ARTIFACT_DIGEST = (
    "sha256:3bfe175b7f2270ed57b0a4345a0bc722f3f5dbc110c1413bc1b068aba78c8052"
)
SOURCE_R53_RUN_ID = 35454021207
SOURCE_R53_ARTIFACT_ID = 10587384217
SOURCE_R53_ARTIFACT_DIGEST = (
    "sha256:8c71d488d18f454b9087aa92c88a0df5e8ca942373c7fb3957283578b9c3d916"
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return cast(dict[str, Any], payload)


def _metrics(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row["exit_timestamp"]),
            str(row["symbol"]),
            str(row["timestamp"]),
        ),
    )
    values = tuple(
        Decimal(str(row["outcome_r"])) - SECONDARY_STRESS
        for row in ordered
    )
    return fx._metrics(values)


def _concentration(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    values = [
        Decimal(str(row["outcome_r"])) - SECONDARY_STRESS
        for row in rows
    ]
    positive = sorted((value for value in values if value > 0), reverse=True)
    total = sum(values, Decimal())
    result: dict[str, Any] = {
        "sample": len(values),
        "terminal_r": str(total),
        "winner_count": len(positive),
    }
    for count in (1, 3):
        removed = list(values)
        contribution = sum(positive[:count], Decimal())
        for value in positive[:count]:
            removed.remove(value)
        metrics = fx._metrics(tuple(removed))
        result[f"top_{count}_winner_contribution_r"] = str(contribution)
        result[f"top_{count}_winner_fraction_of_terminal"] = (
            str(contribution / total) if total > 0 else None
        )
        result[f"leave_top_{count}_out"] = metrics
    return result


def _periods(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["period_id"])].append(row)
    return {
        period: _metrics(items)
        for period, items in sorted(groups.items())
        if period != "OUTSIDE"
    }


def _breakdown(
    rows: Sequence[dict[str, Any]],
    key: str,
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {
        label: {
            "metrics": _metrics(items),
            "concentration": _concentration(items),
        }
        for label, items in sorted(groups.items())
    }


def _all_periods_positive(periods: dict[str, dict[str, Any]]) -> bool:
    return bool(periods) and all(
        Decimal(str(metrics["total_r"])) > 0
        for metrics in periods.values()
    )


def _join_window(
    *,
    r53_rows: Sequence[dict[str, Any]],
    r46_rows: Sequence[dict[str, Any]],
    window_id: str,
) -> list[dict[str, Any]]:
    cisd_rows = [
        row for row in r46_rows
        if str(row["poi"]) == "cisd"
    ]
    index = {
        (str(row["symbol"]), str(row["timestamp"])): row
        for row in cisd_rows
    }
    if len(index) != len(cisd_rows):
        raise ValueError(f"R54 duplicate CISD join key in {window_id}")
    joined: list[dict[str, Any]] = []
    for reaction_row in r53_rows:
        key = (str(reaction_row["symbol"]), str(reaction_row["timestamp"]))
        feature = index.get(key)
        if feature is None:
            raise ValueError(f"R54 missing R46 feature row for {window_id} {key}")
        if str(feature["poi"]) != "cisd":
            raise ValueError("R54 joined non-CISD R46 row")
        continuation_m15 = int(str(feature["continuation_latency_m15"]))
        cisd_to_continuation_minutes = continuation_m15 * 15
        reaction_to_signal_raw = reaction_row.get("minutes_reaction_to_signal")
        reaction_to_signal = (
            int(str(reaction_to_signal_raw))
            if reaction_to_signal_raw is not None
            else None
        )
        cisd_to_reaction: int | None = None
        sequence_state = "NO_REACTION"
        if reaction_to_signal is not None:
            cisd_to_reaction = (
                cisd_to_continuation_minutes - reaction_to_signal
            )
            if cisd_to_reaction > 0:
                sequence_state = "REACTION_AFTER_CISD"
            elif cisd_to_reaction == 0:
                sequence_state = "REACTION_AT_CISD"
            else:
                sequence_state = "REACTION_BEFORE_CISD"

        fresh_liquidity = bool(
            reaction_row["fresh_liquidity_take_15m"]
        )
        continuation_bucket = str(feature["continuation_latency_bucket"])
        fresh_post_cisd = (
            fresh_liquidity
            and sequence_state == "REACTION_AFTER_CISD"
        )
        late_revalidation = (
            fresh_post_cisd
            and continuation_bucket == "5+"
        )
        joined.append(
            {
                **reaction_row,
                "continuation_latency_bucket": continuation_bucket,
                "continuation_latency_m15": continuation_m15,
                "minutes_cisd_to_continuation": (
                    cisd_to_continuation_minutes
                ),
                "minutes_cisd_to_reaction": cisd_to_reaction,
                "semantic_sequence_state": sequence_state,
                "fresh_post_cisd_liquidity": fresh_post_cisd,
                "late_revalidation_5plus": late_revalidation,
                "cisd_latency_bucket": feature["cisd_latency_bucket"],
                "cisd_latency_m15": feature["cisd_latency_m15"],
                "h4_entry_latency_bucket": feature[
                    "h4_entry_latency_bucket"
                ],
                "source_day_relationship": feature[
                    "source_day_relationship"
                ],
                "recent_h4_range_state": feature[
                    "recent_h4_range_state"
                ],
                "recent_daily_range_state": feature[
                    "recent_daily_range_state"
                ],
                "cross_index_state": feature["cross_index_state"],
            }
        )
    if len(joined) != len(r53_rows):
        raise ValueError("R54 join changed CISD sample")
    return joined


def _window(
    *,
    r53_payload: dict[str, Any],
    r46_payload: dict[str, Any],
    r53_key: str,
    r46_key: str,
    window_id: str,
) -> dict[str, Any]:
    r53_rows = cast(
        list[dict[str, Any]],
        r53_payload[r53_key]["rows"],
    )
    r46_rows = cast(
        list[dict[str, Any]],
        r46_payload[r46_key]["feature_matrix"],
    )
    rows = _join_window(
        r53_rows=r53_rows,
        r46_rows=r46_rows,
        window_id=window_id,
    )
    fresh = [
        row for row in rows
        if bool(row["fresh_liquidity_take_15m"])
    ]
    late = [
        row for row in rows
        if bool(row["late_revalidation_5plus"])
    ]
    late_periods = _periods(late)
    late_metrics = _metrics(late)
    late_concentration = _concentration(late)
    return {
        "cisd_sample": len(rows),
        "fresh_liquidity_sample": len(fresh),
        "fresh_liquidity_by_continuation_latency": _breakdown(
            fresh,
            "continuation_latency_bucket",
        ),
        "fresh_liquidity_by_semantic_sequence": _breakdown(
            fresh,
            "semantic_sequence_state",
        ),
        "late_revalidation_5plus": {
            "definition": (
                "fresh favorable liquidity-take <=15m before continuation "
                "after a pre-existing CISD whose continuation latency is "
                "R17 bucket 5+ (>=75m)"
            ),
            "sample": len(late),
            "metrics": late_metrics,
            "periods": late_periods,
            "all_periods_positive": _all_periods_positive(late_periods),
            "concentration": late_concentration,
            "by_symbol": _breakdown(late, "symbol"),
            "by_side": _breakdown(late, "side"),
            "by_anchor": _breakdown(late, "anchor"),
            "by_cisd_latency": _breakdown(late, "cisd_latency_bucket"),
            "rows": late,
        },
    }


def _transport_summary(
    five: dict[str, Any],
    two: dict[str, Any],
) -> dict[str, Any]:
    f = cast(dict[str, Any], five["late_revalidation_5plus"])
    t = cast(dict[str, Any], two["late_revalidation_5plus"])
    fm = cast(dict[str, Any], f["metrics"])
    tm = cast(dict[str, Any], t["metrics"])
    fc = cast(dict[str, Any], f["concentration"])
    tc = cast(dict[str, Any], t["concentration"])
    economic_transport = (
        Decimal(str(fm["total_r"])) > 0
        and Decimal(str(tm["total_r"])) > 0
        and Decimal(str(fm["profit_factor"] or "0")) >= Decimal("1.30")
        and Decimal(str(tm["profit_factor"] or "0")) >= Decimal("1.30")
        and bool(f["all_periods_positive"])
        and bool(t["all_periods_positive"])
    )
    concentration_resilience = (
        Decimal(
            str(
                cast(dict[str, Any], fc["leave_top_3_out"])[
                    "total_r"
                ]
            )
        )
        > 0
        and Decimal(
            str(
                cast(dict[str, Any], tc["leave_top_3_out"])[
                    "total_r"
                ]
            )
        )
        > 0
    )
    return {
        "positive_and_pf_1_30_both_with_all_periods_positive": (
            economic_transport
        ),
        "leave_top_3_positive_both": concentration_resilience,
        "promotion_suitable": (
            economic_transport and concentration_resilience
        ),
        "interpretation": (
            "development clue only; promotion remains forbidden "
            "without concentration resilience and independent evidence"
        ),
    }


def build_report(
    *,
    r53_path: Path,
    r46_path: Path,
) -> dict[str, Any]:
    r53_payload = _load(r53_path)
    r46_payload = _load(r46_path)
    if r53_payload.get("identity") != R53_IDENTITY:
        raise ValueError("R54 unexpected R53 identity")
    candidate = cast(dict[str, Any], r53_payload["candidate"])
    if candidate.get("candidate_id") != R47_CANDIDATE_ID:
        raise ValueError("R54 R53 candidate identity drift")
    if candidate.get("rule_fingerprint") != R47_RULE_FINGERPRINT:
        raise ValueError("R54 R53 rule fingerprint drift")
    r46_candidate = cast(dict[str, Any], r46_payload["candidate"])
    if r46_candidate.get("candidate_id") != (
        "VT08_INDEX_R43_SOURCE_COMPLETE_2448_001"
    ):
        raise ValueError("R54 unexpected R46 forensic source identity")

    five = _window(
        r53_payload=r53_payload,
        r46_payload=r46_payload,
        r53_key="five_year",
        r46_key="five_year",
        window_id="5Y",
    )
    two = _window(
        r53_payload=r53_payload,
        r46_payload=r46_payload,
        r53_key="recent_two_year",
        r46_key="recent_two_year",
        window_id="2Y",
    )
    transport = _transport_summary(five, two)
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "semantic_contract": {
            "source_module": semantic.SCHEMA,
            "departure_definition": (
                "frozen-v7-first-causal-m15-continuation-closure"
            ),
            "continuation_latency_taxonomy_source": r17.SCHEMA,
            "continuation_bucket_5plus_minimum_minutes": 75,
            "post_entry_feature_used": False,
        },
        "source_candidate": {
            "candidate_id": R47_CANDIDATE_ID,
            "rule_fingerprint": R47_RULE_FINGERPRINT,
            "candidate_modified": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "transport": transport,
        "source_evidence": {
            "r46": {
                "run_id": SOURCE_R46_RUN_ID,
                "artifact_id": SOURCE_R46_ARTIFACT_ID,
                "artifact_digest": SOURCE_R46_ARTIFACT_DIGEST,
            },
            "r53": {
                "run_id": SOURCE_R53_RUN_ID,
                "artifact_id": SOURCE_R53_ARTIFACT_ID,
                "artifact_digest": SOURCE_R53_ARTIFACT_DIGEST,
            },
        },
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "existing_core_labs_reused": True,
            "grid_search_used": False,
            "post_entry_outcome_used_as_predictor": False,
            "calendar_or_year_runtime_feature": False,
            "candidate_created": False,
            "risk_retuned": False,
            "signal_suppressed": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r53", type=Path, required=True)
    parser.add_argument("--r46", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(r53_path=args.r53, r46_path=args.r46)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "five_year_late_revalidation": report["five_year"][
                    "late_revalidation_5plus"
                ],
                "recent_two_year_late_revalidation": report[
                    "recent_two_year"
                ]["late_revalidation_5plus"],
                "transport": report["transport"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
