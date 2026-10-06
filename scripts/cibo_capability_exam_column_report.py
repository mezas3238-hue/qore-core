"""Build mandatory 7/7 Trader, CIBO-function and economic-lane reports."""

from __future__ import annotations

import argparse
import csv
import json
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
TOOLS = tuple(f"T{i:02d}" for i in range(1, 21))
FACULTIES = tuple(f"CF{i:02d}" for i in range(1, 20))


def _load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return raw


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _pairs(value: object) -> dict[str, Decimal]:
    if not isinstance(value, list):
        return {}
    result: dict[str, Decimal] = {}
    for row in value:
        if not isinstance(row, list) or len(row) != 2:
            raise ValueError("expected canonical pair list")
        result[str(row[0])] = _decimal(row[1])
    return result


def _selection_blockers_by_trader(
    execution: dict[str, Any],
) -> dict[str, str]:
    books = execution.get("books")
    if not isinstance(books, dict):
        raise ValueError("execution books missing")
    evidence_book = books.get("holdout_evidence")
    policy_book = books.get("holdout_policy")
    if not isinstance(evidence_book, dict) or not isinstance(policy_book, dict):
        raise ValueError("execution evidence/policy books missing")

    evidence_by_sha: dict[str, dict[str, Any]] = {}
    for row in evidence_book.get("decisions", []):
        if not isinstance(row, dict):
            continue
        raw = json.loads(str(row["canonical_payload_json"]))
        if not isinstance(raw, dict):
            raise ValueError("holdout evidence payload must be object")
        evidence_by_sha[str(row["evidence_sha256"])] = raw

    reasons: dict[str, Counter[str]] = defaultdict(Counter)
    for row in policy_book.get("decisions", []):
        if not isinstance(row, dict):
            continue
        evidence = evidence_by_sha.get(str(row["evidence_sha256"]))
        if evidence is None:
            continue
        selected = {str(item) for item in row.get("selected_signal_fingerprints", [])}
        policy = json.loads(str(row["canonical_record_json"]))
        if not isinstance(policy, dict):
            raise ValueError("holdout policy payload must be object")
        allocator = policy.get("allocator_decision", {})
        if not isinstance(allocator, dict):
            allocator = {}
        allocation = allocator.get("allocation")
        allocation_rows = (
            allocation.get("rows", [])
            if isinstance(allocation, dict)
            else []
        )
        by_signal = {
            str(item.get("signal_fingerprint")): item
            for item in allocation_rows
            if isinstance(item, dict)
        }
        regime = policy.get("full_surface", {}).get("regime", {})
        if not isinstance(regime, dict):
            regime = {}

        for candidate_row in evidence.get("candidates", []):
            if not isinstance(candidate_row, dict):
                continue
            candidate = candidate_row.get("candidate")
            if not isinstance(candidate, dict):
                continue
            signal = str(candidate.get("signal_fingerprint", ""))
            trader = str(candidate.get("trader_id", ""))
            if not signal or not trader or signal in selected:
                continue
            allocation_row = by_signal.get(signal)
            if isinstance(allocation_row, dict) and allocation_row.get("reason"):
                reasons[trader][str(allocation_row["reason"])] += 1
                continue
            disposition = str(allocator.get("disposition", "NO_DISPOSITION"))
            allocator_reason = str(
                allocator.get("reason", "allocator withheld selection")
            )
            posture = str(regime.get("posture", "UNKNOWN"))
            reasons[trader][
                f"{disposition} under {posture}: {allocator_reason}"
            ] += 1

    result: dict[str, str] = {}
    for trader, counter in reasons.items():
        top = counter.most_common(3)
        if top:
            result[trader] = "; ".join(
                f"{reason} ({count})" for reason, count in top
            )
    return result


def build_reports(
    *,
    batch: dict[str, Any],
    capability: dict[str, Any],
    execution: dict[str, Any],
    tool_audit: list[dict[str, Any]],
    compound: dict[str, Any],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    traders = batch.get("traders")
    if not isinstance(traders, list):
        raise ValueError("batch trader surface missing")
    opportunity_by = {
        str(row["trader_id"]): int(row["opportunity_count"])
        for row in traders
        if isinstance(row, dict)
    }
    if tuple(item for item in TRADERS if item in opportunity_by) != TRADERS:
        raise ValueError("report requires exact canonical 7/7 Traders")

    books = execution.get("books")
    if not isinstance(books, dict):
        raise ValueError("execution books missing")
    risk_book = books.get("executed_risk")
    settlement_book = books.get("cma_settlement")
    if not isinstance(risk_book, dict) or not isinstance(settlement_book, dict):
        raise ValueError("execution Risk/settlement books missing")
    risk_rows = risk_book.get("executed_risk", [])
    settlements = settlement_book.get("settlements", [])
    if not isinstance(risk_rows, list) or not isinstance(settlements, list):
        raise ValueError("execution Risk/settlement rows invalid")

    risk_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in risk_rows:
        if not isinstance(row, dict):
            raise ValueError("risk row invalid")
        trader = str(row["trader_id"])
        risk_counts[trader][str(row["risk_decision"])] += 1

    core_pnl: dict[str, Decimal] = defaultdict(Decimal)
    gross_pnl: dict[str, Decimal] = defaultdict(Decimal)
    provider_cost: dict[str, Decimal] = defaultdict(Decimal)
    trading_days: dict[str, set[str]] = defaultdict(set)
    settlement_counts: Counter[str] = Counter()
    for row in settlements:
        if not isinstance(row, dict):
            raise ValueError("settlement row invalid")
        trader = str(row["trader_id"])
        stop_risk = _decimal(row["executed_initial_stop_risk_usd"])
        gross_r = _decimal(row["gross_structural_outcome_r"])
        gross_pnl[trader] += stop_risk * gross_r
        provider_cost[trader] += _decimal(row["provider_execution_adjustment_usd"])
        core_pnl[trader] += _decimal(row["realized_net_pnl_usd"])
        settlement_counts[trader] += 1
        trading_days[trader].add(str(row["observed_at"])[:10])

    baseline = capability.get("minimal_seed_baseline")
    full = capability.get("full_cibo")
    if not isinstance(baseline, dict) or not isinstance(full, dict):
        raise ValueError("capability lane metrics missing")
    baseline_pnl = _pairs(baseline.get("trader_pnl_usd"))

    compound_by = compound.get("trader_incremental_pnl_usd")
    if not isinstance(compound_by, dict):
        raise ValueError("compound report trader_incremental_pnl_usd missing")
    compound_pnl = {str(k): _decimal(v) for k, v in compound_by.items()}
    raw_compound_entries = compound.get("trader_compound_entries")
    if not isinstance(raw_compound_entries, dict):
        raise ValueError("compound trader_compound_entries missing")
    compound_entries = {
        str(k): int(v) for k, v in raw_compound_entries.items()
    }
    selection_blockers = _selection_blockers_by_trader(execution)

    rows: list[dict[str, object]] = []
    for trader in TRADERS:
        opportunities = opportunity_by.get(trader, 0)
        selected = sum(risk_counts[trader].values())
        allowed = risk_counts[trader]["ALLOW"]
        reduced = risk_counts[trader]["REDUCE"]
        rejected = risk_counts[trader]["REJECT"]
        executed = settlement_counts[trader]
        if executed:
            zero_reason = ""
        elif opportunities == 0:
            zero_reason = "NO_OPPORTUNITIES_EMITTED; lane diagnostic required"
        elif selected == 0:
            zero_reason = (
                "CIBO_SELECTED_ZERO; "
                + selection_blockers.get(
                    trader,
                    "no canonical allocator reason recovered",
                )
            )
        elif rejected == selected:
            zero_reason = "QORE_RISK_REJECTED_ALL"
        else:
            zero_reason = "NO_SETTLEMENT_DESPITE_SELECTION; reconciliation required"
        rows.append(
            {
                "trader_id": trader,
                "opportunities_emitted": opportunities,
                "cibo_selected": selected,
                "risk_allowed": allowed,
                "risk_reduced": reduced,
                "risk_rejected": rejected,
                "entries_executed_CORE": executed,
                "compound_entries_executed": compound_entries.get(trader, 0),
                "entries_executed_WITH_COMPOUND": (
                    executed + compound_entries.get(trader, 0)
                ),
                "settlements_CORE": executed,
                "gross_structural_pnl_usd": format(gross_pnl[trader], "f"),
                "provider_execution_cost_usd": format(provider_cost[trader], "f"),
                "net_realized_pnl_usd_MINIMAL_SEED_ONLY": format(
                    baseline_pnl.get(trader, Decimal(0)), "f"
                ),
                "net_realized_pnl_usd_FULL_CIBO_CORE": format(
                    core_pnl[trader], "f"
                ),
                "compound_incremental_pnl_usd": format(
                    compound_pnl.get(trader, Decimal(0)), "f"
                ),
                "net_realized_pnl_usd_FULL_CIBO_COMPOUND_PORTFOLIO": format(
                    core_pnl[trader] + compound_pnl.get(trader, Decimal(0)), "f"
                ),
                "trading_days": len(trading_days[trader]),
                "zero_entry_reason": zero_reason,
            }
        )

    audit_by = {
        str(row["tool_code"]): row
        for row in tool_audit
        if isinstance(row, dict) and "tool_code" in row
    }
    if tuple(code for code in TOOLS if code in audit_by) != TOOLS:
        raise ValueError("T01..T20 audit surface incomplete")
    function_rows: list[dict[str, object]] = []
    for code in TOOLS:
        row = audit_by[code]
        function_rows.append(
            {
                "function_code": code,
                "function_type": "CE2I_TOOL",
                "status": str(row["status"]),
                "eligible_epochs": int(row["enabled_epochs"]),
                "executed_count": int(row["applied_count"]),
                "blocked_count": (
                    int(row["regime_blocked_epochs"])
                    + int(row["abstain_count"])
                    + int(row["fail_closed_count"])
                ),
                "reason": str(row["reason"]),
            }
        )
    coverage = capability.get("cognitive_functional_coverage")
    if not isinstance(coverage, dict):
        raise ValueError("cognitive coverage missing")
    coordinated = {
        str(x) for x in coverage.get("coordinated_faculties", [])
    }
    mission_faculties = tuple(
        str(x) for x in coverage.get("mission_faculties", [])
    )
    if len(mission_faculties) != len(FACULTIES):
        raise ValueError("cognitive coverage requires exact 19 mission faculties")
    for code, faculty_name in zip(FACULTIES, mission_faculties, strict=True):
        consulted = faculty_name in coordinated
        function_rows.append(
            {
                "function_code": code,
                "function_type": "COGNITIVE_FACULTY",
                "status": "APPLIED" if consulted else "NOT_EXECUTED",
                "eligible_epochs": 1,
                "executed_count": 1 if consulted else 0,
                "blocked_count": 0 if consulted else 1,
                "reason": (
                    f"{code}={faculty_name}; Mission Director + Functional "
                    "Coordinator consultation recorded"
                    if consulted
                    else f"{code}={faculty_name}; faculty consultation receipt missing"
                ),
            }
        )
    compound_functions = compound.get("function_accountability")
    if not isinstance(compound_functions, list):
        raise ValueError("compound function accountability missing")
    for row in compound_functions:
        if not isinstance(row, dict) or not row.get("function_code"):
            raise ValueError("compound function accountability row invalid")
        if not row.get("reason"):
            raise ValueError("compound non/usage reason is mandatory")
        function_rows.append(dict(row))

    economics = [
        {
            "lane_id": "MINIMAL_SEED_ONLY",
            "ending_capital_usd": str(baseline["ending_capital_usd"]),
            "net_realized_pnl_usd": str(baseline["net_realized_pnl_usd"]),
            "executed_count": int(baseline["executed_count"]),
            "profit_factor": baseline.get("profit_factor"),
        },
        {
            "lane_id": "FULL_CIBO_CORE",
            "ending_capital_usd": str(full["ending_capital_usd"]),
            "net_realized_pnl_usd": str(full["net_realized_pnl_usd"]),
            "executed_count": int(full["executed_count"]),
            "profit_factor": full.get("profit_factor"),
        },
        {
            "lane_id": "FULL_CIBO_COMPOUND_PORTFOLIO",
            "ending_capital_usd": str(compound["ending_capital_usd"]),
            "net_realized_pnl_usd": str(compound["net_realized_pnl_usd"]),
            "executed_count": int(compound["total_executed_count"]),
            "profit_factor": compound.get("profit_factor"),
        },
    ]
    return rows, function_rows, economics


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("cannot write empty CSV")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--capability", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--tool-audit", type=Path, required=True)
    parser.add_argument("--compound", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raw_audit = json.loads(args.tool_audit.read_text(encoding="utf-8"))
    if not isinstance(raw_audit, list):
        raise ValueError("tool audit must be list")
    traders, functions, economics = build_reports(
        batch=_load(args.batch),
        capability=_load(args.capability),
        execution=_load(args.execution),
        tool_audit=raw_audit,
        compound=_load(args.compound),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (
        ("trader-column-report", traders),
        ("cibo-function-accountability", functions),
        ("economic-lane-comparison", economics),
    ):
        _write_csv(args.output_dir / f"{name}.csv", rows)
        _write_json(args.output_dir / f"{name}.json", rows)

    diagnostics = [
        {
            "trader_id": row["trader_id"],
            "opportunities_emitted": row["opportunities_emitted"],
            "cibo_selected": row["cibo_selected"],
            "entries_executed_CORE": row["entries_executed_CORE"],
            "compound_entries_executed": row["compound_entries_executed"],
            "entries_executed_WITH_COMPOUND": row[
                "entries_executed_WITH_COMPOUND"
            ],
            "zero_entry_reason": row["zero_entry_reason"],
        }
        for row in traders
    ]
    _write_json(args.output_dir / "lane-diagnostics.json", diagnostics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
