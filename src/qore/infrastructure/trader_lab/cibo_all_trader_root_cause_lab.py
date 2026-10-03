"""Trader Lab root-cause audit for CIBO all-Trader profitability.

Research-only diagnostic. It attributes observed structural limitations in the
current reused-holdout P0 path without granting execution, Risk, sizing, LIVE,
Production, real-capital, certification, or merge authority.

Important: associations with realized outcomes are diagnostics, not causal
admission rules. Any policy derived from them must be selected on TRAIN and
validated on untouched data before integration.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

TRADERS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)


def _dec(value: object) -> Decimal:
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise ValueError("root-cause numeric input must be finite")
    return parsed


def _pearson(xs: list[Decimal], ys: list[Decimal]) -> Decimal | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    n = Decimal(len(xs))
    mx = sum(xs, Decimal(0)) / n
    my = sum(ys, Decimal(0)) / n
    dx = [value - mx for value in xs]
    dy = [value - my for value in ys]
    vx = sum((value * value for value in dx), Decimal(0))
    vy = sum((value * value for value in dy), Decimal(0))
    if vx <= 0 or vy <= 0:
        return None
    cov = sum((x * y for x, y in zip(dx, dy, strict=True)), Decimal(0))
    return Decimal(str(float(cov) / math.sqrt(float(vx * vy))))


def _context(row: dict[str, Any]) -> dict[str, str]:
    raw = row.get("trader_opportunity", {}).get("decision_context", [])
    if not isinstance(raw, list):
        return {}
    out: dict[str, str] = {}
    for item in raw:
        if (
            isinstance(item, list)
            and len(item) == 2
            and isinstance(item[0], str)
            and isinstance(item[1], str)
        ):
            out[item[0]] = item[1]
    return out


def _applied_t02(row: dict[str, Any]) -> bool:
    ce2i = row.get("ce2i", {})
    if not isinstance(ce2i, dict):
        return False
    decisions = ce2i.get("opportunity_advanced_decisions", [])
    if not isinstance(decisions, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("tool_code") == "T02"
        and item.get("disposition") == "APPLIED"
        for item in decisions
    )


def _selected_rows(trace: dict[str, Any]) -> list[dict[str, Any]]:
    rows = trace.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise ValueError("root-cause audit requires non-empty decision trace")
    return [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("allocation", {}).get("selected_by_cibo_policy") is True
    ]


def _trader_report(
    trader_id: str,
    rows: list[dict[str, Any]],
    lab_result: dict[str, Any],
) -> dict[str, Any]:
    selected = [row for row in rows if row.get("trader_id") == trader_id]
    settled = [row for row in selected if isinstance(row.get("settlement"), dict)]
    realized = [
        _dec(row["settlement"]["realized_net_pnl_usd"])
        for row in settled
    ]
    expected = [
        _dec(row["expectation"]["expected_net_value_usd"])
        for row in settled
    ]
    stop_risk = [
        _dec(row["cma"]["pre_ce2i_stop_risk_usd"])
        for row in settled
    ]
    normalized_expected_r = [
        (ev / risk) for ev, risk in zip(expected, stop_risk, strict=True)
        if risk > 0
    ]
    contexts = [_context(row) for row in settled]
    result_row = next(
        item for item in lab_result["traders"]
        if item["trader_id"] == trader_id
    )
    return {
        "trader_id": trader_id,
        "selected_count": len(selected),
        "settled_count": len(settled),
        "core_pnl_usd": result_row["core_pnl_usd"],
        "compound_incremental_pnl_usd": result_row[
            "compound_incremental_pnl_usd"
        ],
        "full_pnl_usd": result_row["full_pnl_usd"],
        "positive_settlements": sum(value > 0 for value in realized),
        "negative_settlements": sum(value < 0 for value in realized),
        "nonpositive_expected_value_selected": sum(
            value <= 0 for value in expected
        ),
        "unique_normalized_expected_r": sorted(
            {format(value, "f") for value in normalized_expected_r}
        ),
        "expectation_to_realized_pearson": (
            None
            if (corr := _pearson(expected, realized)) is None
            else format(corr, "f")
        ),
        "t02_applied_count": sum(_applied_t02(row) for row in settled),
        "risk_statuses": dict(
            sorted(
                Counter(
                    str(row.get("qore_risk", {}).get("status", "UNKNOWN"))
                    for row in settled
                ).items()
            )
        ),
        "side_distribution": dict(
            sorted(
                Counter(
                    str(row.get("trader_opportunity", {}).get("side", "UNKNOWN"))
                    for row in settled
                ).items()
            )
        ),
        "session_distribution": dict(
            sorted(
                Counter(context.get("ctx_session", "MISSING")
                        for context in contexts).items()
            )
        ),
    }


def build_report(
    *,
    trace: dict[str, Any],
    lab_result: dict[str, Any],
) -> dict[str, Any]:
    selected = _selected_rows(trace)
    all_rows = trace.get("opportunities", [])
    cognitive = Counter()
    post_learning = Counter()
    for row in all_rows:
        if not isinstance(row, dict):
            continue
        cog = row.get("cognitive_orchestration", {})
        if isinstance(cog, dict):
            cognitive[
                (
                    str(cog.get("coordination_disposition")),
                    str(cog.get("coordination_request_code")),
                    bool(cog.get("economic_authority", False)),
                    bool(cog.get("executive_brain_invoked", False)),
                    str(cog.get("mission_disposition")),
                )
            ] += 1
        learning = row.get("post_outcome_learning", {})
        if isinstance(learning, dict):
            post_learning[str(learning.get("status", "UNKNOWN"))] += 1

    coverage = lab_result.get("coverage", {})
    capabilities = coverage.get("capabilities", [])
    if not isinstance(capabilities, list):
        capabilities = []
    ce2i = [
        item for item in capabilities
        if isinstance(item, dict) and item.get("stage") == "CE2I"
    ]
    capital_science = [
        item for item in capabilities
        if isinstance(item, dict) and item.get("stage") == "CAPITAL_SCIENCE"
    ]
    cognition = [
        item for item in capabilities
        if isinstance(item, dict) and item.get("stage") == "COGNITIVE"
    ]

    selected_expectations = [
        _dec(row["expectation"]["expected_net_value_usd"])
        for row in selected
        if isinstance(row.get("expectation"), dict)
    ]
    selected_risk = Counter(
        str(row.get("qore_risk", {}).get("status", "UNKNOWN"))
        for row in selected
    )

    traders = [
        _trader_report(trader, selected, lab_result)
        for trader in TRADERS
    ]

    root_causes = [
        {
            "code": "RC01_COGNITION_REQUEST_ONLY",
            "status": "OBSERVED_STRUCTURAL_LIMIT",
            "evidence": (
                "CF01-CF19 are consulted on the predecision path, but the "
                "consultation receipt has no economic/sizing/Risk/execution "
                "authority and Mission Director remains CONTINUE/request-only."
            ),
        },
        {
            "code": "RC02_LINEAGE_LEVEL_EXPECTATION_PRIOR",
            "status": "OBSERVED_STRUCTURAL_LIMIT",
            "evidence": (
                "Each Trader's executed opportunities share one normalized "
                "frozen TRAIN structural-R expectation; opportunity-specific "
                "context is not used to recalibrate expected value."
            ),
        },
        {
            "code": "RC03_NONPOSITIVE_EXPECTATION_LAB_OVERRIDE",
            "status": "OBSERVED_RESEARCH_OVERRIDE",
            "evidence": (
                f"{sum(value <= 0 for value in selected_expectations)} selected "
                "opportunities had non-positive expected net value because the "
                "P0 research treatment explicitly permits this."
            ),
        },
        {
            "code": "RC04_CE2I_EVIDENCE_GAPS",
            "status": "OBSERVED_STRUCTURAL_LIMIT",
            "evidence": (
                "Multiple registered CE2I tools remain fail-closed because "
                "their causal economic evidence is missing."
            ),
        },
        {
            "code": "RC05_CAPITAL_SCIENCE_PARTIAL_INTEGRATION",
            "status": "OBSERVED_STRUCTURAL_LIMIT",
            "evidence": (
                "Only a subset of GEN-C capabilities is economically wired "
                "into the current Compound lane."
            ),
        },
        {
            "code": "RC06_QORE_RISK_IS_NOT_EDGE_SELECTOR",
            "status": "OBSERVED_ARCHITECTURAL_FACT",
            "evidence": (
                "QORE Risk remains sovereign for solvency/risk authorization, "
                "but does not repair weak expected edge; current selected rows "
                f"show risk statuses {dict(sorted(selected_risk.items()))}."
            ),
        },
        {
            "code": "RC07_POST_OUTCOME_LEARNING_NOT_INTEGRATED",
            "status": "OBSERVED_STRUCTURAL_LIMIT",
            "evidence": (
                "Post-outcome learning is not integrated into the current "
                "economic replay, so later decisions cannot adapt from prior "
                "settled evidence through that seam."
            ),
        },
    ]

    return {
        "schema": "qore.trader-lab.cibo-all-trader-root-cause.v1",
        "mode": "NON_CERTIFYING_REUSED_HOLDOUT_DIAGNOSTIC",
        "source_trace_sha256": trace.get("trace_sha256"),
        "selected_opportunity_count": len(selected),
        "selected_nonpositive_expectation_count": sum(
            value <= 0 for value in selected_expectations
        ),
        "selected_risk_statuses": dict(sorted(selected_risk.items())),
        "cognitive_runtime_patterns": [
            {
                "coordination_disposition": key[0],
                "coordination_request_code": key[1],
                "economic_authority": key[2],
                "executive_brain_invoked": key[3],
                "mission_disposition": key[4],
                "count": count,
            }
            for key, count in sorted(cognitive.items())
        ],
        "post_outcome_learning_statuses": dict(sorted(post_learning.items())),
        "cognitive_capability_count": len(cognition),
        "ce2i": {
            "registered_count": len(ce2i),
            "applied": [
                item["capability"] for item in ce2i
                if item.get("status") == "APPLIED"
            ],
            "fail_closed": [
                {
                    "capability": item["capability"],
                    "reason": item.get("reason"),
                }
                for item in ce2i
                if item.get("status") == "FAIL_CLOSED"
            ],
        },
        "capital_science": {
            "registered_count": len(capital_science),
            "applied": [
                item["capability"] for item in capital_science
                if item.get("status") == "APPLIED"
            ],
            "not_integrated": [
                item["capability"] for item in capital_science
                if item.get("status") == "NOT_INTEGRATED"
            ],
            "justified_not_applicable": [
                item["capability"] for item in capital_science
                if item.get("status") == "JUSTIFIED_NOT_APPLICABLE"
            ],
        },
        "traders": traders,
        "root_cause_findings": root_causes,
        "governance": {
            "diagnostic_only": True,
            "associations_are_not_admission_rules": True,
            "outcome_aware_policy_tuning": False,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "merge_authority": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--lab-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    lab_result = json.loads(args.lab_result.read_text(encoding="utf-8"))
    if not isinstance(trace, dict) or not isinstance(lab_result, dict):
        raise ValueError("root-cause inputs must be JSON objects")
    report = build_report(trace=trace, lab_result=lab_result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "selected_opportunity_count": report[
                    "selected_opportunity_count"
                ],
                "selected_nonpositive_expectation_count": report[
                    "selected_nonpositive_expectation_count"
                ],
                "ce2i_fail_closed_count": len(report["ce2i"]["fail_closed"]),
                "capital_science_not_integrated_count": len(
                    report["capital_science"]["not_integrated"]
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
