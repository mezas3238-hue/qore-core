"""Fail-closed reporting contract for the CIBO USD60 capability exam.

The reporting layer is deliberately downstream from the economic engines. It
does not select trades, size positions, alter outcomes, or grant authority. It
reconstructs the seven Trader columns from canonical batch/Risk/settlement
evidence and requires a separately produced Compound+Portfolio lane before a
final report can exist.
"""

from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

REPORT_SCHEMA = "qore.cibo.usd60-capability-final-report.v1"
COMPOUND_LANE_SCHEMA = "qore.cibo.usd60-compound-portfolio-lane.v1"
DIAGNOSTICS_SCHEMA = "qore.cibo.usd60-lane-diagnostics.v1"
CANDIDATE_ID = "CIBO_USD60_6M_HOLDOUT_2014-10-19_2015-04-19_V4"
CANONICAL_TRADERS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)
ECONOMIC_LANES = (
    "MINIMAL_SEED_ONLY",
    "FULL_CIBO_CORE",
    "FULL_CIBO_COMPOUND_PORTFOLIO",
)
COMPOUND_FUNCTIONS = (
    "GEN-C1_COMPOUND_CAPITAL",
    "GEN-C3_CORE_COMPOUND_PORTFOLIO",
    "GEN-C5_SEQUENTIAL_COMPOUNDING",
    "GEN-C6_INTERNAL_CAPITAL_MARKET",
)
TRADER_METRICS = (
    "raw_setups",
    "opportunities_emitted",
    "cibo_selected",
    "risk_allowed",
    "risk_reduced",
    "risk_rejected",
    "entries_executed_FULL_CIBO_CORE",
    "entries_executed_FULL_CIBO_COMPOUND_PORTFOLIO",
    "settlements_FULL_CIBO_CORE",
    "settlements_FULL_CIBO_COMPOUND_PORTFOLIO",
    "gross_structural_pnl_usd_FULL_CIBO_CORE",
    "provider_execution_cost_usd_FULL_CIBO_CORE",
    "net_realized_pnl_usd_MINIMAL_SEED_ONLY",
    "net_realized_pnl_usd_FULL_CIBO_CORE",
    "net_realized_pnl_usd_FULL_CIBO_COMPOUND_PORTFOLIO",
    "compound_incremental_pnl_usd",
    "trading_days_FULL_CIBO_CORE",
    "trading_days_FULL_CIBO_COMPOUND_PORTFOLIO",
    "zero_entry_reason_FULL_CIBO_CORE",
    "zero_entry_reason_FULL_CIBO_COMPOUND_PORTFOLIO",
)
ALLOWED_FUNCTION_STATUSES = {
    "APPLIED",
    "FAIL_CLOSED",
    "REGIME_BLOCKED",
    "JUSTIFIED_NOT_APPLICABLE",
    "NOT_EXECUTED",
    "NOT_INTEGRATED",
}


def build_final_reporting_payloads(
    *,
    batch: dict[str, Any],
    capability_report: dict[str, Any],
    execution_report: dict[str, Any],
    lane_diagnostics: dict[str, Any],
    compound_lane_report: dict[str, Any],
) -> dict[str, Any]:
    """Build the exact final reporting surfaces or fail closed."""

    _require_identity(batch, "candidate_id", CANDIDATE_ID)
    _require_identity(capability_report, "candidate_id", CANDIDATE_ID)
    _require_identity(lane_diagnostics, "schema", DIAGNOSTICS_SCHEMA)
    _require_identity(lane_diagnostics, "candidate_id", CANDIDATE_ID)
    _require_identity(compound_lane_report, "schema", COMPOUND_LANE_SCHEMA)
    _require_identity(compound_lane_report, "candidate_id", CANDIDATE_ID)
    _require_identity(
        compound_lane_report,
        "lane_id",
        "FULL_CIBO_COMPOUND_PORTFOLIO",
    )

    batch_traders = tuple(
        str(item["trader_id"]) for item in _list(batch, "traders")
    )
    if batch_traders != CANONICAL_TRADERS:
        raise CiboCapitalManagementError(
            "capability reporting requires exact ordered 7/7 Trader surface"
        )

    diagnostic_rows = _keyed_rows(
        _list(lane_diagnostics, "traders"),
        key="trader_id",
        expected=CANONICAL_TRADERS,
        label="lane diagnostics",
    )
    compound_rows = _keyed_rows(
        _list(compound_lane_report, "traders"),
        key="trader_id",
        expected=CANONICAL_TRADERS,
        label="compound lane",
    )

    opportunities = {
        str(item["trader_id"]): _nonnegative_int(
            item.get("opportunity_count"),
            "opportunity_count",
        )
        for item in _list(batch, "traders")
    }

    books = _dict(execution_report, "books")
    risk_rows = _list(_dict(books, "executed_risk"), "executed_risk")
    settlements = _list(_dict(books, "cma_settlement"), "settlements")

    selected = Counter(str(item["trader_id"]) for item in risk_rows)
    risk_by_decision: dict[str, Counter[str]] = {
        trader: Counter() for trader in CANONICAL_TRADERS
    }
    for row in risk_rows:
        trader = str(row["trader_id"])
        if trader not in risk_by_decision:
            raise CiboCapitalManagementError(
                "Risk evidence contains noncanonical Trader"
            )
        decision = str(row["risk_decision"])
        if decision not in {"ALLOW", "REDUCE", "REJECT"}:
            raise CiboCapitalManagementError(
                "Risk evidence contains unknown decision"
            )
        risk_by_decision[trader][decision] += 1

    settlement_rows: dict[str, list[dict[str, Any]]] = {
        trader: [] for trader in CANONICAL_TRADERS
    }
    for row in settlements:
        trader = str(row["trader_id"])
        if trader not in settlement_rows:
            raise CiboCapitalManagementError(
                "settlement evidence contains noncanonical Trader"
            )
        settlement_rows[trader].append(row)

    baseline_pnl = _money_pair_map(
        _dict(capability_report, "minimal_seed_baseline").get("trader_pnl_usd", [])
    )
    reported_full_pnl = _money_pair_map(
        _dict(capability_report, "full_cibo").get("trader_pnl_usd", [])
    )

    values: dict[str, dict[str, Any]] = {
        metric: {} for metric in TRADER_METRICS
    }
    for trader in CANONICAL_TRADERS:
        diag = diagnostic_rows[trader]
        compound = compound_rows[trader]
        rows = settlement_rows[trader]

        raw_setups = _nonnegative_int(diag.get("raw_setups"), "raw_setups")
        entries_core = len(rows)
        net_core = sum(
            (_money(item["realized_net_pnl_usd"]) for item in rows),
            Decimal(0),
        )
        gross_core = sum(
            (
                _money(item["gross_structural_outcome_r"])
                * _money(item["executed_initial_stop_risk_usd"])
                for item in rows
            ),
            Decimal(0),
        )
        provider_cost = sum(
            (_money(item["provider_execution_adjustment_usd"]) for item in rows),
            Decimal(0),
        )
        days_core = len(
            {
                datetime.fromisoformat(str(item["observed_at"])).date()
                for item in rows
            }
        )

        if net_core != reported_full_pnl.get(trader, Decimal(0)):
            raise CiboCapitalManagementError(
                f"reported FULL_CIBO_CORE PnL drift for {trader}"
            )

        entries_compound = _nonnegative_int(
            compound.get("entries_executed"),
            "compound entries_executed",
        )
        settlements_compound = _nonnegative_int(
            compound.get("settlements"),
            "compound settlements",
        )
        if entries_compound != settlements_compound:
            raise CiboCapitalManagementError(
                f"compound entry/settlement count drift for {trader}"
            )
        net_compound = _money(compound.get("net_realized_pnl_usd"))
        days_compound = _nonnegative_int(
            compound.get("trading_days"),
            "compound trading_days",
        )

        zero_core = _zero_entry_reason(
            trader=trader,
            raw_setups=raw_setups,
            opportunities=opportunities[trader],
            selected=selected[trader],
            entries=entries_core,
            all_risk_rejected=(
                selected[trader] > 0
                and risk_by_decision[trader]["REJECT"] == selected[trader]
            ),
            diagnostic_reason=str(diag.get("zero_entry_reason", "")).strip(),
        )
        zero_compound = str(compound.get("zero_entry_reason", "")).strip()
        if entries_compound == 0 and not zero_compound:
            raise CiboCapitalManagementError(
                f"compound zero-entry reason missing for {trader}"
            )
        if entries_compound > 0 and zero_compound:
            raise CiboCapitalManagementError(
                f"compound zero-entry reason present despite entries for {trader}"
            )

        row_values = {
            "raw_setups": raw_setups,
            "opportunities_emitted": opportunities[trader],
            "cibo_selected": selected[trader],
            "risk_allowed": risk_by_decision[trader]["ALLOW"],
            "risk_reduced": risk_by_decision[trader]["REDUCE"],
            "risk_rejected": risk_by_decision[trader]["REJECT"],
            "entries_executed_FULL_CIBO_CORE": entries_core,
            "entries_executed_FULL_CIBO_COMPOUND_PORTFOLIO": entries_compound,
            "settlements_FULL_CIBO_CORE": entries_core,
            "settlements_FULL_CIBO_COMPOUND_PORTFOLIO": settlements_compound,
            "gross_structural_pnl_usd_FULL_CIBO_CORE": _decimal(gross_core),
            "provider_execution_cost_usd_FULL_CIBO_CORE": _decimal(provider_cost),
            "net_realized_pnl_usd_MINIMAL_SEED_ONLY": _decimal(
                baseline_pnl.get(trader, Decimal(0))
            ),
            "net_realized_pnl_usd_FULL_CIBO_CORE": _decimal(net_core),
            "net_realized_pnl_usd_FULL_CIBO_COMPOUND_PORTFOLIO": _decimal(
                net_compound
            ),
            "compound_incremental_pnl_usd": _decimal(net_compound - net_core),
            "trading_days_FULL_CIBO_CORE": days_core,
            "trading_days_FULL_CIBO_COMPOUND_PORTFOLIO": days_compound,
            "zero_entry_reason_FULL_CIBO_CORE": zero_core,
            "zero_entry_reason_FULL_CIBO_COMPOUND_PORTFOLIO": zero_compound,
        }
        for metric in TRADER_METRICS:
            values[metric][trader] = row_values[metric]

    function_rows = _function_accountability(
        capability_report=capability_report,
        compound_lane_report=compound_lane_report,
    )
    economic_rows = _economic_lane_rows(
        capability_report=capability_report,
        compound_lane_report=compound_lane_report,
    )

    return {
        "schema": REPORT_SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "trader_columns": {
            "traders": list(CANONICAL_TRADERS),
            "metrics": list(TRADER_METRICS),
            "values": values,
        },
        "function_accountability": function_rows,
        "economic_lane_comparison": economic_rows,
        "scientific_freshness_claimed": False,
        "fresh_oos_generalization_claimed": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "merge_authorized": False,
    }


def trader_columns_csv(payload: dict[str, Any]) -> str:
    columns = _dict(payload, "trader_columns")
    traders = tuple(str(item) for item in _list(columns, "traders"))
    metrics = tuple(str(item) for item in _list(columns, "metrics"))
    values = _dict(columns, "values")
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(("metric", *traders))
    for metric in metrics:
        row = _dict(values, metric)
        writer.writerow((metric, *(row[trader] for trader in traders)))
    return out.getvalue()


def function_accountability_csv(payload: dict[str, Any]) -> str:
    rows = _list(payload, "function_accountability")
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(
        (
            "function_code",
            "function_name",
            "status",
            "eligible_epochs",
            "executed_count",
            "blocked_count",
            "reason",
        )
    )
    for row in rows:
        writer.writerow(
            (
                row["function_code"],
                row["function_name"],
                row["status"],
                row["eligible_epochs"],
                row["executed_count"],
                row["blocked_count"],
                row["reason"],
            )
        )
    return out.getvalue()


def economic_lane_comparison_csv(payload: dict[str, Any]) -> str:
    rows = _list(payload, "economic_lane_comparison")
    headers = (
        "lane_id",
        "initial_capital_usd",
        "ending_capital_usd",
        "net_realized_pnl_usd",
        "executed_count",
        "max_realized_drawdown_usd",
        "profit_factor",
        "delta_vs_cibo_solo_usd",
    )
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(tuple(row.get(item, "") for item in headers))
    return out.getvalue()


def _function_accountability(
    *,
    capability_report: dict[str, Any],
    compound_lane_report: dict[str, Any],
) -> list[dict[str, Any]]:
    coverage = _dict(capability_report, "cognitive_functional_coverage")
    mission = tuple(str(item) for item in _list(coverage, "mission_faculties"))
    coordinated = tuple(
        str(item) for item in _list(coverage, "coordinated_faculties")
    )
    if len(mission) != 19 or coordinated != mission:
        raise CiboCapitalManagementError(
            "CF01..CF19 accountability requires exact coordinated faculty surface"
        )

    result: list[dict[str, Any]] = []
    for index, name in enumerate(coordinated, start=1):
        result.append(
            {
                "function_code": f"CF{index:02d}",
                "function_name": name,
                "status": "APPLIED",
                "eligible_epochs": 1,
                "executed_count": 1,
                "blocked_count": 0,
                "reason": (
                    "Mission Director assigned and Functional Coordinator "
                    f"consulted {name}"
                ),
            }
        )

    tools = _list(capability_report, "tool_audit")
    expected_tools = tuple(f"T{index:02d}" for index in range(1, 21))
    if tuple(str(item.get("tool_code")) for item in tools) != expected_tools:
        raise CiboCapitalManagementError(
            "T01..T20 accountability surface is not exact"
        )
    for item in tools:
        status = str(item["status"])
        if status not in ALLOWED_FUNCTION_STATUSES:
            raise CiboCapitalManagementError(
                "CIBO tool accountability status invalid"
            )
        reason = str(item.get("reason", "")).strip()
        if not reason:
            raise CiboCapitalManagementError(
                "CIBO tool accountability reason missing"
            )
        result.append(
            {
                "function_code": str(item["tool_code"]),
                "function_name": str(item["tool_name"]),
                "status": status,
                "eligible_epochs": _nonnegative_int(
                    item.get("enabled_epochs"),
                    "enabled_epochs",
                ),
                "executed_count": _nonnegative_int(
                    item.get("applied_count"),
                    "applied_count",
                ),
                "blocked_count": (
                    _nonnegative_int(
                        item.get("regime_blocked_epochs"),
                        "regime_blocked_epochs",
                    )
                    + _nonnegative_int(
                        item.get("fail_closed_count"),
                        "fail_closed_count",
                    )
                    + _nonnegative_int(
                        item.get("abstain_count"),
                        "abstain_count",
                    )
                ),
                "reason": reason,
            }
        )

    compound = _keyed_rows(
        _list(compound_lane_report, "function_audit"),
        key="function_code",
        expected=COMPOUND_FUNCTIONS,
        label="compound function audit",
    )
    for code in COMPOUND_FUNCTIONS:
        item = compound[code]
        status = str(item.get("status"))
        if status not in ALLOWED_FUNCTION_STATUSES:
            raise CiboCapitalManagementError(
                f"compound function status invalid: {code}"
            )
        reason = str(item.get("reason", "")).strip()
        if not reason:
            raise CiboCapitalManagementError(
                f"compound function reason missing: {code}"
            )
        result.append(
            {
                "function_code": code,
                "function_name": str(item.get("function_name", code)),
                "status": status,
                "eligible_epochs": _nonnegative_int(
                    item.get("eligible_epochs"),
                    "compound eligible_epochs",
                ),
                "executed_count": _nonnegative_int(
                    item.get("executed_count"),
                    "compound executed_count",
                ),
                "blocked_count": _nonnegative_int(
                    item.get("blocked_count"),
                    "compound blocked_count",
                ),
                "reason": reason,
            }
        )

    if any(item["status"] == "NOT_INTEGRATED" for item in result):
        raise CiboCapitalManagementError(
            "final capability report cannot contain NOT_INTEGRATED functions"
        )
    return result


def _economic_lane_rows(
    *,
    capability_report: dict[str, Any],
    compound_lane_report: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline = _dict(capability_report, "minimal_seed_baseline")
    core = _dict(capability_report, "full_cibo")
    compound = _dict(compound_lane_report, "performance_metrics")

    if str(baseline.get("lane")) != "MINIMAL_SEED_ONLY":
        raise CiboCapitalManagementError("baseline lane identity drift")
    if str(core.get("lane")) != "FULL_CIBO_CORE":
        raise CiboCapitalManagementError("CIBO solo lane identity drift")
    if str(compound.get("lane")) != "FULL_CIBO_COMPOUND_PORTFOLIO":
        raise CiboCapitalManagementError("compound lane identity drift")

    core_pnl = _money(core["net_realized_pnl_usd"])
    rows = []
    for lane_id, raw in (
        ("MINIMAL_SEED_ONLY", baseline),
        ("FULL_CIBO_CORE", core),
        ("FULL_CIBO_COMPOUND_PORTFOLIO", compound),
    ):
        pnl = _money(raw["net_realized_pnl_usd"])
        rows.append(
            {
                "lane_id": lane_id,
                "initial_capital_usd": _decimal(_money(raw["initial_capital_usd"])),
                "ending_capital_usd": _decimal(_money(raw["ending_capital_usd"])),
                "net_realized_pnl_usd": _decimal(pnl),
                "executed_count": _nonnegative_int(
                    raw.get("executed_count"),
                    "economic lane executed_count",
                ),
                "max_realized_drawdown_usd": _decimal(
                    _money(raw["max_realized_drawdown_usd"])
                ),
                "profit_factor": (
                    ""
                    if raw.get("profit_factor") is None
                    else _decimal(_money(raw["profit_factor"]))
                ),
                "delta_vs_cibo_solo_usd": _decimal(pnl - core_pnl),
            }
        )
    return rows


def _zero_entry_reason(
    *,
    trader: str,
    raw_setups: int,
    opportunities: int,
    selected: int,
    entries: int,
    all_risk_rejected: bool,
    diagnostic_reason: str,
) -> str:
    if entries > 0:
        if diagnostic_reason:
            raise CiboCapitalManagementError(
                f"zero-entry reason present despite entries for {trader}"
            )
        return ""
    if raw_setups == 0:
        reason = diagnostic_reason or "NO_RAW_SETUP_IN_WINDOW"
    elif opportunities == 0:
        reason = diagnostic_reason
    elif selected == 0:
        reason = "CIBO_POLICY_SELECTED_ZERO"
    elif all_risk_rejected:
        reason = "QORE_RISK_REJECTED_ALL"
    else:
        reason = diagnostic_reason
    if not reason:
        raise CiboCapitalManagementError(
            f"unexplained zero-entry Trader: {trader}"
        )
    return reason


def _money_pair_map(value: object) -> dict[str, Decimal]:
    if not isinstance(value, list):
        raise CiboCapitalManagementError("Trader PnL map must be list")
    result: dict[str, Decimal] = {}
    for row in value:
        if not isinstance(row, list) or len(row) != 2:
            raise CiboCapitalManagementError("Trader PnL row invalid")
        trader = str(row[0])
        if trader not in CANONICAL_TRADERS or trader in result:
            raise CiboCapitalManagementError("Trader PnL identity drift")
        result[trader] = _money(row[1])
    return result


def _keyed_rows(
    rows: list[Any],
    *,
    key: str,
    expected: tuple[str, ...],
    label: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            raise CiboCapitalManagementError(f"{label} row must be object")
        identity = str(raw.get(key))
        if identity in result:
            raise CiboCapitalManagementError(f"{label} duplicate identity")
        result[identity] = raw
    if tuple(result) != expected:
        raise CiboCapitalManagementError(
            f"{label} requires exact ordered surface"
        )
    return result


def _list(raw: dict[str, Any], key: str) -> list[Any]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise CiboCapitalManagementError(f"{key} must be list")
    return value


def _dict(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise CiboCapitalManagementError(f"{key} must be object")
    return value


def _require_identity(raw: dict[str, Any], key: str, expected: str) -> None:
    if str(raw.get(key)) != expected:
        raise CiboCapitalManagementError(f"{key} identity drift")


def _nonnegative_int(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise CiboCapitalManagementError(f"{name} must be nonnegative int")
    return value


def _money(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise CiboCapitalManagementError("reporting money value must be finite")
    return result


def _decimal(value: Decimal) -> str:
    return format(value, "f")
