#!/usr/bin/env python3
"""Evaluate a completed single-account CIBO run against the frozen rescue exam.

Input is a compact research summary produced by Trader Lab. This evaluator does
not infer or tune anything. It validates identities and instantiates the frozen
CiboBadTraderRescueExamResult contract; any failing invariant exits non-zero.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_bad_trader_rescue_exam import (
    CiboBadTraderRescueExamResult,
    CiboManagedTraderContribution,
    DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _contribution(row: dict[str, Any]) -> CiboManagedTraderContribution:
    return CiboManagedTraderContribution(
        trader_id=TraderLineage(str(row["trader_id"])),
        opportunity_count=int(row["opportunity_count"]),
        selected_count=int(row["selected_count"]),
        abstained_count=int(row["abstained_count"]),
        reduced_count=int(row["reduced_count"]),
        rejected_count=int(row["rejected_count"]),
        settled_count=int(row["settled_count"]),
        gross_profit_usd=_d(row["gross_profit_usd"]),
        gross_loss_usd=_d(row["gross_loss_usd"]),
        net_contribution_usd=_d(row["net_contribution_usd"]),
    )


def evaluate(payload: dict[str, Any]) -> CiboBadTraderRescueExamResult:
    if payload.get("schema") != "qore.cibo.single-account-maxcap-summary.v1":
        raise CiboCapitalManagementError(
            "rescue evaluator requires canonical single-account summary"
        )
    rows = payload.get("trader_contributions")
    if not isinstance(rows, list):
        raise CiboCapitalManagementError(
            "rescue evaluator trader contributions missing"
        )
    by_id = {
        TraderLineage(str(row["trader_id"])): _contribution(row)
        for row in rows
    }
    required = DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM.trader_ids
    if set(by_id) != set(required):
        raise CiboCapitalManagementError(
            "rescue evaluator requires exact seven-trader contribution surface"
        )
    ordered = tuple(by_id[trader] for trader in required)

    return CiboBadTraderRescueExamResult(
        contract=DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM,
        opportunity_decision_count=int(payload["opportunity_decision_count"]),
        native_max_intelligence_decision_count=int(
            payload["native_max_intelligence_decision_count"]
        ),
        full_cf_semantic_decision_count=int(
            payload["full_cf_semantic_decision_count"]
        ),
        external_ai_call_count=int(payload["external_ai_call_count"]),
        account_reset_count=int(payload["account_reset_count"]),
        economic_era_reset_count=int(payload["economic_era_reset_count"]),
        ending_capital_usd=_d(payload["ending_capital_usd"]),
        peak_capital_usd=_d(payload["peak_capital_usd"]),
        maximum_drawdown_usd=_d(payload["maximum_drawdown_usd"]),
        trader_contributions=ordered,
        outcome_used_for_predecision=bool(
            payload.get("outcome_used_for_predecision", False)
        ),
        trader_logic_modified_for_exam=bool(
            payload.get("trader_logic_modified_for_exam", False)
        ),
        broker_mutation=bool(payload.get("broker_mutation", False)),
        live=bool(payload.get("live", False)),
        production=bool(payload.get("production", False)),
        real_capital=bool(payload.get("real_capital", False)),
        certification_claimed=bool(
            payload.get("certification_claimed", False)
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.summary.read_text(encoding="utf-8"))
    try:
        result = evaluate(payload)
    except Exception as error:
        failed = {
            "schema": "qore.cibo.bad-trader-rescue-exam-result.v1",
            "passed": False,
            "error": str(error),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(failed, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(failed, sort_keys=True))
        return 3

    passed = {
        "schema": "qore.cibo.bad-trader-rescue-exam-result.v1",
        "passed": result.passed,
        "account_net_profit_usd": format(
            result.account_net_profit_usd,
            "f",
        ),
        "ending_capital_usd": format(result.ending_capital_usd, "f"),
        "maximum_drawdown_usd": format(
            result.maximum_drawdown_usd,
            "f",
        ),
        "per_trader_net_contribution_usd": [
            [
                item.trader_id.value,
                format(item.net_contribution_usd, "f"),
            ]
            for item in result.trader_contributions
        ],
        "external_ai_call_count": result.external_ai_call_count,
        "account_reset_count": result.account_reset_count,
        "economic_era_reset_count": result.economic_era_reset_count,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(passed, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(passed, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
