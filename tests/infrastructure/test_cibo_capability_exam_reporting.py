from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.cibo_capability_exam_reporting import (
    CANONICAL_TRADERS,
    COMPOUND_FUNCTIONS,
    build_final_reporting_payloads,
    trader_columns_csv,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _lane(
    lane: str,
    *,
    ending: str,
    pnl: str,
    executed: int,
    trader_pnl: list[list[str]],
) -> dict[str, object]:
    return {
        "lane": lane,
        "initial_capital_usd": "60",
        "ending_capital_usd": ending,
        "net_realized_pnl_usd": pnl,
        "executed_count": executed,
        "max_realized_drawdown_usd": "1",
        "profit_factor": "1.5",
        "trader_pnl_usd": trader_pnl,
    }


def _fixture() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    batch = {
        "candidate_id": "CIBO_USD60_6M_HOLDOUT_2014-10-19_2015-04-19_V4",
        "traders": [
            {
                "trader_id": trader,
                "opportunity_count": 1 if trader == "VT08_FOREX" else 0,
            }
            for trader in CANONICAL_TRADERS
        ],
    }
    tool_audit = [
        {
            "tool_code": f"T{index:02d}",
            "tool_name": f"Tool {index:02d}",
            "status": "APPLIED",
            "enabled_epochs": 1,
            "regime_blocked_epochs": 0,
            "applied_count": 1,
            "abstain_count": 0,
            "fail_closed_count": 0,
            "reason": "canonical test execution",
        }
        for index in range(1, 21)
    ]
    faculties = [f"faculty-{index:02d}" for index in range(1, 20)]
    capability = {
        "candidate_id": batch["candidate_id"],
        "cognitive_functional_coverage": {
            "mission_faculties": faculties,
            "coordinated_faculties": faculties,
        },
        "minimal_seed_baseline": _lane(
            "MINIMAL_SEED_ONLY",
            ending="60.5",
            pnl="0.5",
            executed=1,
            trader_pnl=[["VT08_FOREX", "0.5"]],
        ),
        "full_cibo": _lane(
            "FULL_CIBO_CORE",
            ending="60.6",
            pnl="0.6",
            executed=1,
            trader_pnl=[["VT08_FOREX", "0.6"]],
        ),
        "tool_audit": tool_audit,
    }
    execution = {
        "books": {
            "executed_risk": {
                "executed_risk": [
                    {
                        "trader_id": "VT08_FOREX",
                        "risk_decision": "ALLOW",
                    }
                ]
            },
            "cma_settlement": {
                "settlements": [
                    {
                        "trader_id": "VT08_FOREX",
                        "observed_at": "2015-01-02T15:00:00+00:00",
                        "gross_structural_outcome_r": "1",
                        "executed_initial_stop_risk_usd": "0.7",
                        "provider_execution_adjustment_usd": "0.1",
                        "realized_net_pnl_usd": "0.6",
                    }
                ]
            },
        }
    }
    diagnostics = {
        "schema": "qore.cibo.usd60-lane-diagnostics.v1",
        "candidate_id": batch["candidate_id"],
        "traders": [
            {
                "trader_id": trader,
                "raw_setups": 1 if trader == "VT08_FOREX" else 0,
                "zero_entry_reason": (
                    "" if trader == "VT08_FOREX" else "NO_RAW_SETUP_IN_WINDOW"
                ),
            }
            for trader in CANONICAL_TRADERS
        ],
    }
    compound = {
        "schema": "qore.cibo.usd60-compound-portfolio-lane.v1",
        "candidate_id": batch["candidate_id"],
        "lane_id": "FULL_CIBO_COMPOUND_PORTFOLIO",
        "traders": [
            {
                "trader_id": trader,
                "entries_executed": 1 if trader == "VT08_FOREX" else 0,
                "settlements": 1 if trader == "VT08_FOREX" else 0,
                "net_realized_pnl_usd": (
                    "0.8" if trader == "VT08_FOREX" else "0"
                ),
                "trading_days": 1 if trader == "VT08_FOREX" else 0,
                "zero_entry_reason": (
                    "" if trader == "VT08_FOREX" else "NO_RAW_SETUP_IN_WINDOW"
                ),
            }
            for trader in CANONICAL_TRADERS
        ],
        "performance_metrics": _lane(
            "FULL_CIBO_COMPOUND_PORTFOLIO",
            ending="60.8",
            pnl="0.8",
            executed=1,
            trader_pnl=[["VT08_FOREX", "0.8"]],
        ),
        "function_audit": [
            {
                "function_code": code,
                "function_name": code,
                "status": "APPLIED",
                "eligible_epochs": 1,
                "executed_count": 1,
                "blocked_count": 0,
                "reason": "canonical compound test execution",
            }
            for code in COMPOUND_FUNCTIONS
        ],
    }
    return batch, capability, execution, diagnostics, compound


def test_builds_exact_seven_trader_columns_and_compound_increment() -> None:
    batch, capability, execution, diagnostics, compound = _fixture()
    payload = build_final_reporting_payloads(
        batch=batch,
        capability_report=capability,
        execution_report=execution,
        lane_diagnostics=diagnostics,
        compound_lane_report=compound,
    )

    columns = payload["trader_columns"]
    assert tuple(columns["traders"]) == CANONICAL_TRADERS
    assert (
        columns["values"]["entries_executed_FULL_CIBO_CORE"]["VT08_FOREX"]
        == 1
    )
    assert (
        columns["values"]["compound_incremental_pnl_usd"]["VT08_FOREX"]
        == "0.2"
    )
    assert len(payload["function_accountability"]) == 43
    csv_text = trader_columns_csv(payload)
    assert csv_text.splitlines()[0] == "metric," + ",".join(CANONICAL_TRADERS)


def test_zero_entry_without_reason_fails_closed() -> None:
    batch, capability, execution, diagnostics, compound = _fixture()
    diagnostics = deepcopy(diagnostics)
    diagnostics["traders"][1]["raw_setups"] = 3
    diagnostics["traders"][1]["zero_entry_reason"] = ""

    with pytest.raises(
        CiboCapitalManagementError,
        match="unexplained zero-entry Trader",
    ):
        build_final_reporting_payloads(
            batch=batch,
            capability_report=capability,
            execution_report=execution,
            lane_diagnostics=diagnostics,
            compound_lane_report=compound,
        )


def test_reported_cibo_pnl_must_match_settlements() -> None:
    batch, capability, execution, diagnostics, compound = _fixture()
    capability = deepcopy(capability)
    capability["full_cibo"]["trader_pnl_usd"] = [["VT08_FOREX", "0.7"]]

    with pytest.raises(
        CiboCapitalManagementError,
        match="reported FULL_CIBO_CORE PnL drift",
    ):
        build_final_reporting_payloads(
            batch=batch,
            capability_report=capability,
            execution_report=execution,
            lane_diagnostics=diagnostics,
            compound_lane_report=compound,
        )


def test_not_integrated_function_blocks_final_report() -> None:
    batch, capability, execution, diagnostics, compound = _fixture()
    compound = deepcopy(compound)
    compound["function_audit"][0]["status"] = "NOT_INTEGRATED"

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot contain NOT_INTEGRATED",
    ):
        build_final_reporting_payloads(
            batch=batch,
            capability_report=capability,
            execution_report=execution,
            lane_diagnostics=diagnostics,
            compound_lane_report=compound,
        )
