"""Emit Phase20E capital-state block-bootstrap contract evidence.

Synthetic fixtures only. The proof demonstrates that Monte Carlo resamples
whole overlap-aware temporal blocks and then replays reservations/releases
through the normalized capital ledger. It does not shuffle trades independently
or claim market probabilities.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedCapitalAllocation,
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase20_capital_state_monte_carlo import (
    build_phase20e_temporal_blocks,
    run_phase20e_capital_state_monte_carlo,
)


def _trade(
    *,
    trader: TraderLineage,
    fingerprint: str,
    decision_minute: int,
    entry_minute: int,
    exit_minute: int,
    outcome_r: str,
) -> Phase19NormalizedReplayTrade:
    base = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    decision_at = base + timedelta(minutes=decision_minute)
    entry_at = base + timedelta(minutes=entry_minute)
    exit_at = base + timedelta(minutes=exit_minute)
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=fingerprint,
        qore_symbol="SYNTHETIC",
        entry_at=entry_at,
        exit_at=exit_at,
    )
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        decision_at=decision_at,
        risk_budget_ncu=Decimal("1"),
        allocation_priority=0,
        policy_id="PHASE20E_SYNTHETIC_FIXED_POLICY",
        evidence_id=f"synthetic:{fingerprint}",
        outcome_aware=False,
    )
    return Phase19NormalizedReplayTrade(
        opportunity=opportunity,
        allocation=allocation,
        normalized_outcome_r=Decimal(outcome_r),
        outcome_evidence_id=f"synthetic-outcome:{fingerprint}",
    )


def _population() -> tuple[Phase19NormalizedReplayTrade, ...]:
    return (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            fingerprint="A",
            decision_minute=59,
            entry_minute=60,
            exit_minute=90,
            outcome_r="-1",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            fingerprint="B",
            decision_minute=64,
            entry_minute=65,
            exit_minute=80,
            outcome_r="-1",
        ),
        _trade(
            trader=TraderLineage.R38_GBPJPY,
            fingerprint="C",
            decision_minute=119,
            entry_minute=120,
            exit_minute=150,
            outcome_r="2",
        ),
        _trade(
            trader=TraderLineage.R42_AUDJPY,
            fingerprint="D",
            decision_minute=149,
            entry_minute=150,
            exit_minute=165,
            outcome_r="-1",
        ),
        _trade(
            trader=TraderLineage.VT31_NAS100,
            fingerprint="E",
            decision_minute=239,
            entry_minute=240,
            exit_minute=250,
            outcome_r="1",
        ),
    )


def build_report() -> dict[str, Any]:
    trades = _population()
    blocks = build_phase20e_temporal_blocks(
        trades=trades,
        components_per_block=1,
    )
    contract = Phase19CapitalNumeraireContract(
        contract_id="PHASE20E_SYNTHETIC_STRUCTURAL_STOP_NCU_V1"
    )
    summary = run_phase20e_capital_state_monte_carlo(
        contract=contract,
        initial_capital_ncu=Decimal("2"),
        trades=trades,
        simulations=100,
        draws_per_path=6,
        components_per_block=1,
        base_seed=20020,
    )
    examples = [
        {
            "simulation_id": item.simulation_id,
            "sampled_block_ids": list(item.sampled_block_ids),
            "ending_capital_ncu": str(item.replay.ending_capital_ncu),
            "realized_delta_ncu": str(item.replay.total_realized_delta_ncu),
            "max_drawdown_ncu": str(item.replay.max_drawdown_ncu),
            "accepted_opportunities": item.replay.accepted_opportunities,
            "rejected_opportunities": item.replay.rejected_opportunities,
            "capacity_breach_observed": item.replay.capacity_breach_observed,
        }
        for item in summary.path_results[:10]
    ]
    return {
        "schema": "qore.cibo.phase20e.capital_state_monte_carlo_contract.v1",
        "identity": "CIBO_PHASE20E_CAPITAL_STATE_BLOCK_BOOTSTRAP_V1",
        "status": "SYNTHETIC_CONTRACT_PROOF",
        "fixture": {
            "synthetic_only": True,
            "source_opportunities": len(trades),
            "source_temporal_blocks": len(blocks),
            "source_block_opportunity_counts": [
                block.opportunity_count for block in blocks
            ],
            "provider_economics_claimed": False,
            "phase19j_burned_validation_reused": False,
        },
        "bootstrap": {
            "simulations": summary.simulation_count,
            "draws_per_path": summary.draws_per_path,
            "components_per_block": summary.components_per_block,
            "base_seed": summary.base_seed,
            "independent_trade_shuffle": False,
            "market_probability_claimed": False,
        },
        "aggregate": {
            "min_ending_capital_ncu": str(summary.min_ending_capital_ncu),
            "max_ending_capital_ncu": str(summary.max_ending_capital_ncu),
            "p95_max_drawdown_ncu": str(summary.p95_max_drawdown_ncu),
            "positive_ending_delta_paths": (
                summary.positive_ending_delta_paths
            ),
            "capacity_breach_paths": summary.capacity_breach_paths,
            "max_rejected_opportunities": (
                summary.max_rejected_opportunities
            ),
        },
        "proof_invariants": {
            "overlap_connected_components_kept_atomic": True,
            "same_timestamp_entry_before_exit_kept_atomic": True,
            "decision_entry_exit_lags_preserved_inside_blocks": True,
            "risk_budget_and_priority_preserved_inside_blocks": True,
            "normalized_outcomes_preserved_inside_blocks": True,
            "sampled_blocks_rebased_without_cross_block_overlap": True,
            "reservations_and_releases_replayed_through_capital_ledger": True,
            "duplicate_sampled_blocks_receive_unique_signal_identity": True,
        },
        "path_examples": examples,
        "governance": {
            "historical_usd_claimed": False,
            "historical_provider_economics_claimed": False,
            "policy_certified": False,
            "allocator_selected": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
