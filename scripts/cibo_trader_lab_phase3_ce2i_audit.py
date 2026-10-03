#!/usr/bin/env python3
"""Sequential Trader Lab Phase 3 audit for CE2I T01..T20.

The audit is intentionally non-compensatory. Every tool must prove an observable
runtime path before the next tool can unlock. A registry entry, an enabled-tool
flag, or a green unit test is not sufficient evidence of economic function.

Research-only reused-holdout capability audit. No fresh-OOS, certification,
broker, LIVE, Production, real-capital, sizing, Risk, or merge authority.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

TOOLS = tuple(f"T{index:02d}" for index in range(1, 21))
ADVANCED = frozenset({"T02", "T03", "T04", "T08", "T10", "T16", "T17"})
ECONOMIC_EFFECT_REQUIRED = frozenset(
    {"T02", "T03", "T04", "T08", "T10", "T16", "T17"}
)


def _rows(trace: dict[str, Any]) -> list[dict[str, Any]]:
    rows = trace.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Phase 3 requires non-empty P0 decision trace")
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("Phase 3 trace row must be object")
    return rows


def _enabled_count(rows: list[dict[str, Any]], code: str) -> int:
    return sum(
        1
        for row in rows
        if code
        in row.get("ce2i", {}).get("enabled_tools", [])
    )


def _advanced_decisions(
    rows: list[dict[str, Any]],
    code: str,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        ce2i = row.get("ce2i")
        if not isinstance(ce2i, dict):
            continue
        candidates = ce2i.get("opportunity_advanced_decisions", [])
        portfolio = ce2i.get("portfolio_advanced_decisions", [])
        for raw in (*candidates, *portfolio):
            if not isinstance(raw, dict) or raw.get("tool_code") != code:
                continue
            key = (
                str(row.get("decision_epoch_id")),
                str(row.get("signal_fingerprint")),
                str(raw.get("disposition")),
                str(raw.get("reason")),
            )
            if key in seen:
                continue
            seen.add(key)
            found.append(raw)
    return found


def _economic_effect_count(
    rows: list[dict[str, Any]],
    code: str,
) -> int:
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        ce2i = row.get("ce2i")
        if not isinstance(ce2i, dict):
            continue
        for field in (
            "candidate_economic_effects",
            "portfolio_economic_effects",
        ):
            effects = ce2i.get(field, [])
            if not isinstance(effects, list):
                continue
            for raw in effects:
                if not isinstance(raw, dict) or raw.get("tool_code") != code:
                    continue
                key = (
                    str(row.get("decision_epoch_id")),
                    str(row.get("signal_fingerprint")),
                    field,
                    json.dumps(raw, sort_keys=True),
                )
                seen.add(key)
    return len(seen)


def _t01(rows: list[dict[str, Any]]) -> dict[str, Any]:
    enabled = _enabled_count(rows, "T01")
    selected = 0
    reached_risk = 0
    executed = 0
    for row in rows:
        if "T01" not in row.get("ce2i", {}).get("enabled_tools", []):
            continue
        allocation = row.get("allocation")
        cma = row.get("cma")
        risk = row.get("qore_risk")
        if (
            isinstance(allocation, dict)
            and allocation.get("selected_by_cibo_policy") is True
        ):
            selected += 1
        if (
            isinstance(cma, dict)
            and cma.get("risk_request_emitted") is True
            and isinstance(risk, dict)
            and risk.get("status") in {"ALLOW", "REDUCE", "REJECT"}
        ):
            reached_risk += 1
        if row.get("settlement") is not None:
            executed += 1
    passed = enabled > 0 and selected > 0 and reached_risk > 0 and executed > 0
    return {
        "tool_code": "T01",
        "status": "PASS" if passed else "FAIL",
        "enabled_opportunities": enabled,
        "selected_opportunities": selected,
        "risk_evaluated_opportunities": reached_risk,
        "settled_opportunities": executed,
        "required_observation": (
            "minimal-seed-capable opportunities reach CMA + sovereign QORE Risk "
            "and produce settled research executions"
        ),
        "failure_reasons": (
            []
            if passed
            else ["T01_MINIMAL_SEED_RUNTIME_PATH_NOT_OBSERVED"]
        ),
    }


def _advanced(rows: list[dict[str, Any]], code: str) -> dict[str, Any]:
    enabled = _enabled_count(rows, code)
    decisions = _advanced_decisions(rows, code)
    dispositions = Counter(
        str(item.get("disposition", "UNKNOWN")) for item in decisions
    )
    reasons = Counter(str(item.get("reason", "UNKNOWN")) for item in decisions)
    applied = dispositions["APPLIED"]
    effects = _economic_effect_count(rows, code)
    passed = enabled > 0 and applied > 0
    failures: list[str] = []
    if enabled <= 0:
        failures.append(f"{code}_NEVER_ENABLED")
    if not decisions:
        failures.append(f"{code}_NO_RUNTIME_DECISION")
    if applied <= 0:
        failures.append(f"{code}_NO_APPLIED_DECISION")
    if code in ECONOMIC_EFFECT_REQUIRED and effects <= 0:
        failures.append(f"{code}_NO_OBSERVABLE_ECONOMIC_EFFECT")
        passed = False
    return {
        "tool_code": code,
        "status": "PASS" if passed else "FAIL",
        "enabled_opportunities": enabled,
        "runtime_decision_count": len(decisions),
        "dispositions": dict(sorted(dispositions.items())),
        "decision_reasons": dict(sorted(reasons.items())),
        "observable_economic_effect_count": effects,
        "required_observation": (
            "causal evidence -> runtime decision -> observable economic effect"
        ),
        "failure_reasons": failures,
    }


def _locked(code: str, blocker: str) -> dict[str, Any]:
    return {
        "tool_code": code,
        "status": "LOCKED_BY_PRIOR_GATE",
        "blocked_by": blocker,
        "failure_reasons": [f"{code}_LOCKED_UNTIL_{blocker}_PASSES"],
    }


def audit(trace: dict[str, Any], *, source_head: str) -> dict[str, Any]:
    rows = _rows(trace)
    reports: list[dict[str, Any]] = []
    blocker: str | None = None
    for code in TOOLS:
        if blocker is not None:
            reports.append(_locked(code, blocker))
            continue
        if code == "T01":
            report = _t01(rows)
        elif code in ADVANCED:
            report = _advanced(rows, code)
        else:
            # Deliberately not inferred from "enabled". These tools unlock only
            # after earlier gates pass and their own semantic audit is implemented.
            report = {
                "tool_code": code,
                "status": "FAIL",
                "enabled_opportunities": _enabled_count(rows, code),
                "failure_reasons": [
                    f"{code}_SEMANTIC_RUNTIME_AUDIT_NOT_YET_EXECUTED"
                ],
            }
        reports.append(report)
        if report["status"] != "PASS":
            blocker = code

    passed_count = sum(item["status"] == "PASS" for item in reports)
    phase_pass = passed_count == len(TOOLS)
    return {
        "schema": "qore.cibo.trader-lab.phase3-ce2i-audit.v1",
        "phase": "PHASE_3_CE2I_T01_T20",
        "source_head_sha": source_head,
        "source_trace_sha256": trace.get("trace_sha256"),
        "source_opportunity_count": len(rows),
        "tool_sequence": list(TOOLS),
        "pass_count": passed_count,
        "first_blocker": blocker,
        "phase_pass": phase_pass,
        "next_phase_unlocked": (
            "PHASE_4_GENC_01_14" if phase_pass else None
        ),
        "tools": reports,
        "governance": {
            "sequential_noncompensatory_gate": True,
            "registry_presence_is_not_pass": True,
            "enabled_flag_is_not_pass": True,
            "reused_holdout": True,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
            "outcome_aware_predecision_tuning": False,
            "broker_mutation": False,
            "orders": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "merge_authority": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise RuntimeError("decision trace root must be object")
    report = audit(trace, source_head=args.source_head)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "phase_pass": report["phase_pass"],
                "pass_count": report["pass_count"],
                "first_blocker": report["first_blocker"],
                "next_phase_unlocked": report["next_phase_unlocked"],
            },
            sort_keys=True,
        )
    )
    return 2 if args.enforce and not report["phase_pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
