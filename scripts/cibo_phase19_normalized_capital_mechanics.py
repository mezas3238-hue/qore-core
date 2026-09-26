"""Bind all seven Phase-18 lineages to the Phase-19C normalized capital ledger.

This is a deliberately simple NON-OPTIMIZED mechanics baseline:
- initial normalized capital = 100 NCU;
- every opportunity requests exactly 1 NCU of structural-stop risk capacity;
- allocation priority is fixed/deterministic and does not use outcomes;
- provider economics are not used;
- USD, margin and execution claims remain forbidden.

The purpose is to prove the 7/7 capital-numeraire plumbing, not to select an
allocator or claim an economically optimal policy.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    reconstructed_signal_fingerprint,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedCapitalAllocation,
    Phase19NormalizedReplayTrade,
    replay_phase19_normalized_capital,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)
from scripts.cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_COMMON_START,
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    SourceSpec,
)

INITIAL_CAPITAL_NCU = Decimal("100")
FIXED_RISK_BUDGET_NCU = Decimal("1")
POLICY_ID = "PHASE19D_EQUAL_ONE_NCU_MECHANICS_BASELINE_V1"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _source_evidence_id(spec: SourceSpec) -> str:
    return (
        f"github-actions:phase18:{spec.artifact_id}:"
        f"{spec.artifact_digest}"
    )


def _normalized_outcome_r(
    row: dict[str, Any],
    *,
    trader_id: TraderLineage,
) -> Decimal:
    if trader_id is TraderLineage.VT08_FOREX:
        value = row["raw_outcome_r"]
    elif trader_id is TraderLineage.VT31_NAS100:
        value = row["legacy_vt31_net_r_per_requested_r"]
    else:
        value = row["raw_net_010_r"]
    outcome = Decimal(str(value))
    if not outcome.is_finite():
        raise ValueError(f"{trader_id.value} non-finite normalized outcome")
    return outcome


def _parse_trade(
    row: dict[str, Any],
    *,
    spec: SourceSpec,
) -> Phase19NormalizedReplayTrade:
    if str(row.get("economics_status")) != "R_DENOMINATED_ONLY":
        raise ValueError(
            f"{spec.trader_id.value} unexpectedly claims provider economics"
        )

    qore_symbol = spec.qore_symbol or str(row["symbol"])
    signal_at = datetime.fromisoformat(str(row["signal_at"]))
    entry_at = datetime.fromisoformat(str(row["entry_at"]))
    exit_at = datetime.fromisoformat(str(row["exit_at"]))
    entry = Decimal(str(row["entry_price"]))
    stop = Decimal(str(row["structural_stop"]))
    target = Decimal(str(row["technical_target"]))
    side = str(row["side"]).lower()
    evidence_id = _source_evidence_id(spec)
    fingerprint = reconstructed_signal_fingerprint(
        trader_id=spec.trader_id,
        qore_symbol=qore_symbol,
        side=side,
        signal_at=signal_at,
        entry_at=entry_at,
        entry_price=entry,
        structural_stop=stop,
        technical_target=target,
        source_evidence_ids=(evidence_id,),
    )
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=spec.trader_id,
        signal_fingerprint=fingerprint,
        qore_symbol=qore_symbol,
        entry_at=entry_at,
        exit_at=exit_at,
    )
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=fingerprint,
        trader_id=spec.trader_id,
        decision_at=signal_at,
        risk_budget_ncu=FIXED_RISK_BUDGET_NCU,
        allocation_priority=0,
        policy_id=POLICY_ID,
        evidence_id=(
            f"mechanics-baseline:{POLICY_ID}:{evidence_id}"
        ),
        train_cutoff_at=None,
        outcome_aware=False,
    )
    return Phase19NormalizedReplayTrade(
        opportunity=opportunity,
        allocation=allocation,
        normalized_outcome_r=_normalized_outcome_r(
            row,
            trader_id=spec.trader_id,
        ),
        outcome_evidence_id=evidence_id,
    )


def replay(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase 19D source set drift")

    parsed: dict[TraderLineage, list[Phase19NormalizedReplayTrade]] = {}
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} source row-count drift"
            )
        parsed[spec.trader_id] = [
            _parse_trade(row, spec=spec) for row in rows
        ]

    common_start = datetime.fromisoformat(EXPECTED_COMMON_START)
    common_end = datetime.fromisoformat(EXPECTED_COMMON_END)
    selected = {
        trader_id: [
            item
            for item in trades
            if item.opportunity.entry_at >= common_start
            and item.opportunity.exit_at <= common_end
        ]
        for trader_id, trades in parsed.items()
    }
    for trader_id, trades in selected.items():
        if len(trades) != EXPECTED_COMMON_ROWS[trader_id]:
            raise ValueError(
                f"{trader_id.value} normalized common-window row drift"
            )

    combined = tuple(
        item
        for trader_id in EXPECTED_COMMON_ROWS
        for item in selected[trader_id]
    )
    if len(combined) != sum(EXPECTED_COMMON_ROWS.values()):
        raise ValueError("Phase 19D normalized population drift")

    contract = Phase19CapitalNumeraireContract(
        contract_id="CIBO_PHASE19C_STRUCTURAL_STOP_NCU_V1"
    )
    result = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=INITIAL_CAPITAL_NCU,
        trades=combined,
    )

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19.normalized_capital_mechanics.v1",
        "identity": "CIBO_PHASE19D_NORMALIZED_CAPITAL_MECHANICS_V1",
        "status": "NORMALIZED_CAPITAL_MECHANICS_BOUND_7_OF_7",
        "common_window": {
            "start": EXPECTED_COMMON_START,
            "end": EXPECTED_COMMON_END,
        },
        "policy": {
            "policy_id": POLICY_ID,
            "optimized": False,
            "training_used": False,
            "initial_capital_ncu": str(INITIAL_CAPITAL_NCU),
            "fixed_risk_budget_ncu": str(FIXED_RISK_BUDGET_NCU),
            "allocation_priority": "DETERMINISTIC_IDENTITY_TIEBREAK_ONLY",
            "purpose": "MECHANICS_AND_ACCOUNTING_BASELINE_ONLY",
        },
        "rows_by_trader": {
            trader_id.value: len(selected[trader_id])
            for trader_id in EXPECTED_COMMON_ROWS
        },
        "total_opportunities": len(combined),
        "accepted_opportunities": result.accepted_opportunities,
        "rejected_opportunities": result.rejected_opportunities,
        "ending_capital_ncu": str(result.ending_capital_ncu),
        "total_realized_delta_ncu": str(result.total_realized_delta_ncu),
        "max_drawdown_ncu": str(result.max_drawdown_ncu),
        "peak_reserved_risk_ncu": str(result.peak_reserved_risk_ncu),
        "risk_capacity_minutes_ncu": str(result.risk_capacity_minutes_ncu),
        "capacity_breach_observed": result.capacity_breach_observed,
        "numeraire": {
            "contract_id": contract.contract_id,
            "unit_name": contract.unit_name,
            "basis": contract.basis.value,
        },
        "governance": {
            "research_only": True,
            "historical_usd_replay_authorized": False,
            "historical_provider_replay_authorized": False,
            "cross_trader_raw_r_aggregation_authorized": False,
            "normalized_budget_weighted_capital_arithmetic": True,
            "same_timestamp_exit_recycling_authorized": False,
            "allocator_policy_certified": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {
        key: getattr(args, key)
        for key in SOURCE_SPECS
    }
    print(json.dumps(replay(paths=paths, output_path=args.output), sort_keys=True))


if __name__ == "__main__":
    main()
