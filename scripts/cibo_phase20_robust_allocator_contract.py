"""Emit Phase20H-A robust constrained allocator contract evidence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    CiboCapitalMissionPolicy,
    derive_cibo_capital_mission,
    fundednext_stellar_instant_identity,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_optionality import KnownCapitalOption
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20RobustAllocatorDecision,
    propose_phase20h_robust_allocation,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimeToolSelection,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

NOW = datetime(2026, 9, 27, 5, 30, tzinfo=UTC)


def _demo_mission() -> CiboCapitalMissionPolicy:
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="phase20h-evidence",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )


def _regime(
    mission: CiboCapitalMissionPolicy,
    *,
    drawdown: str = "0.20",
    adverse: bool = False,
    stale: bool = False,
    opportunity_count: int = 2,
) -> CiboRegimeToolSelection:
    return select_ce2i_tools_for_regime(
        mission=mission,
        state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.20"),
            margin_utilization=Decimal("0.20"),
            drawdown_utilization=Decimal(drawdown),
            opportunity_count=opportunity_count,
            position_path_adverse=adverse,
            evidence_stale=stale,
        ),
    )


def _candidate(
    fingerprint: str,
    trader: TraderLineage,
    *,
    net: str,
    minutes: str,
) -> CapitalOpportunityCandidate:
    return CapitalOpportunityCandidate(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        qore_symbol=fingerprint.upper(),
        provider_symbol=fingerprint.upper(),
        decision_as_of=NOW,
        expectation=CausalOpportunityExpectation(
            evidence_id=f"phase20h:evidence:{fingerprint}",
            as_of=NOW,
            basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
            expected_net_value_usd=Decimal(net),
            expected_capital_minutes=Decimal(minutes),
        ),
        stop_risk_usd=Decimal("5"),
        margin_usd=Decimal("10"),
        concentration_group="USD",
        concentration_risk_usd=Decimal("5"),
    )


def _options() -> tuple[KnownCapitalOption, ...]:
    return (
        KnownCapitalOption(
            opportunity_id="future-small",
            minimum_stop_risk_usd=Decimal("4"),
            minimum_margin_usd=Decimal("20"),
        ),
        KnownCapitalOption(
            opportunity_id="future-large",
            minimum_stop_risk_usd=Decimal("10"),
            minimum_margin_usd=Decimal("40"),
        ),
    )


def _decision_row(
    scenario_id: str,
    decision: Phase20RobustAllocatorDecision,
) -> dict[str, Any]:
    selected = (
        list(decision.allocation.selected_signal_fingerprints)
        if decision.allocation is not None
        else []
    )
    used_risk = (
        str(decision.allocation.used_stop_risk_usd)
        if decision.allocation is not None
        else "0"
    )
    used_margin = (
        str(decision.allocation.used_margin_usd)
        if decision.allocation is not None
        else "0"
    )
    return {
        "scenario_id": scenario_id,
        "disposition": decision.disposition.value,
        "regime_posture": decision.regime_posture.value,
        "applied_tools": list(decision.applied_tools),
        "reserve_stop_risk_usd": str(decision.reserve_stop_risk_usd),
        "reserve_margin_usd": str(decision.reserve_margin_usd),
        "deployable_stop_risk_usd": str(
            decision.deployable_stop_risk_usd
        ),
        "deployable_margin_usd": str(decision.deployable_margin_usd),
        "selected_signal_fingerprints": selected,
        "used_stop_risk_usd": used_risk,
        "used_margin_usd": used_margin,
        "reserved_for_opportunity_ids": list(
            decision.reserved_for_opportunity_ids
        ),
        "reason": decision.reason,
    }


def build_report() -> dict[str, Any]:
    demo = _demo_mission()
    fast = _candidate(
        "fast",
        TraderLineage.R43_GBPUSD,
        net="8",
        minutes="5",
    )
    slow = _candidate(
        "slow",
        TraderLineage.R38_EURUSD,
        net="10",
        minutes="20",
    )
    stable = propose_phase20h_robust_allocation(
        mission=demo,
        regime=_regime(demo),
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(slow, fast),
    )
    stable_single = propose_phase20h_robust_allocation(
        mission=demo,
        regime=_regime(demo, opportunity_count=1),
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(fast,),
    )
    defensive = propose_phase20h_robust_allocation(
        mission=demo,
        regime=_regime(demo, adverse=True),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(fast,),
        known_options=_options(),
    )
    recovery = propose_phase20h_robust_allocation(
        mission=demo,
        regime=_regime(demo, drawdown="0.80"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(fast,),
        known_options=_options(),
    )
    stale = propose_phase20h_robust_allocation(
        mission=demo,
        regime=_regime(demo, stale=True),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(),
        known_options=_options(),
    )
    funded = derive_cibo_capital_mission(
        fundednext_stellar_instant_identity(
            account_ref="phase20h-funded-evidence"
        )
    )
    external = propose_phase20h_robust_allocation(
        mission=funded,
        regime=_regime(funded),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(fast,),
        known_options=_options(),
    )

    rows = [
        _decision_row("STABLE_DEMO", stable),
        _decision_row("STABLE_SINGLE_DEMO", stable_single),
        _decision_row("DEFENSIVE_DEMO", defensive),
        _decision_row("RECOVERY_DEMO", recovery),
        _decision_row("STALE_DEMO", stale),
        _decision_row("EXTERNAL_CONTRACT_GATED", external),
    ]
    return {
        "schema": "qore.cibo.phase20h.robust_allocator_contract.v1",
        "identity": "CIBO_PHASE20H_ROBUST_CONSTRAINED_ALLOCATOR_V1",
        "status": "SYNTHETIC_CONTRACT_CANDIDATE",
        "scenarios": rows,
        "governance": {
            "outcome_aware": False,
            "validation_tuned": False,
            "phase19j_burned_validation_reused": False,
            "historical_provider_economics_claimed": False,
            "policy_certified": False,
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
