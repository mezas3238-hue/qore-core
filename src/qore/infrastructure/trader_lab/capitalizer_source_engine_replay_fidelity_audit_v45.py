"""Canonical source-engine vs economic-replay fidelity audit for Capitalizer V45.

This module audits code/contracts only. It does not open or evaluate trade
economics. The contract was frozen in PR #623 comment 5883038006.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_dual_source_entry_acceptance_v1 as dual,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_grammar_v2 as grammar,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_trade_plan_v2 as trade_plan,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_trader_engine_v2 as source_engine,
)

IDENTITY = "QORE_CAPITALIZER_SOURCE_ENGINE_REPLAY_FIDELITY_AUDIT_V45"
PREDECLARATION_COMMENT_ID = 5883038006


@dataclass(frozen=True, slots=True)
class FidelityCheck:
    key: str
    canonical_required: bool
    replay_satisfies: bool
    hard_mismatch: bool
    evidence: str


def _source(module: Any) -> str:
    return inspect.getsource(module)


def _field_names(cls: type[Any]) -> set[str]:
    return set(cls.__dataclass_fields__)


def build_report() -> dict[str, Any]:
    engine_source = _source(source_engine)
    dual_source = _source(dual)
    grammar_source = _source(grammar)
    plan_source = _source(trade_plan)
    direct_source = _source(direct)
    v3_source = _source(v3)

    canonical_dual_fields = _field_names(dual.CapitalizerDualSourceEntryFacts)
    canonical_plan_fields = _field_names(trade_plan.CapitalizerSourceTradePlanFacts)

    canonical_gate_bound = (
        "dual_source_entry_acceptance" in _field_names(
            source_engine.CapitalizerSourceTraderEngineFacts
        )
        and "DUAL_SOURCE_ENTRY_ACCEPTANCE_REQUIRED" in engine_source
        and "passes_to_qore_risk" in engine_source
    )

    canonical_structural_target = (
        "structural_target_price" in canonical_plan_fields
        and "target_price=facts.structural_target_price" in plan_source
    )
    canonical_fixed_r_forbidden = (
        trade_plan.CapitalizerSourceTradePlan.__dataclass_fields__[
            "fixed_r_target_invented"
        ].default
        is False
    )

    replay_invokes_source_engine = (
        "capitalizer_source_trader_engine_v2" in direct_source
        or "assess_source_trader_engine" in direct_source
    )
    replay_binds_dual_gate = (
        "CapitalizerDualSourceEntryAcceptance" in direct_source
        or "assess_dual_source_entry" in direct_source
    )
    replay_binds_htf_bias = (
        "CapitalizerDailyBiasObservation" in direct_source
        or "derive_daily_bias" in direct_source
    )
    replay_binds_canonical_route = (
        "CapitalizerSourceEntryRoute" in direct_source
        or "assess_fractal_alignment" in direct_source
        or "CapitalizerFailureToManipulateObservation" in direct_source
    )
    replay_binds_structural_target = (
        "CapitalizerStructuralTargetObservation" in direct_source
        or "structural_target_price" in direct_source
    )

    replay_fixed_2r = (
        direct.TARGET_R == Decimal("2.00")
        and "TARGET_R * risk" in direct_source
    )
    replay_target_identity_fixed_2r = "FIXED_2R" in v3.TARGET_IDENTITY

    replay_m1_mss = (
        "M1_MSS" in direct_source
        or "m1_mss" in direct_source.lower()
    )
    replay_m1_fvg = (
        "_m1_causal_zone" in direct_source
        and "fvg" in v3_source.lower()
    )
    replay_m1_ob = (
        "_m1_causal_zone" in direct_source
        and "ob_" in v3_source.lower()
    )

    replay_ttrades_htf_closure = (
        "ttrades_htf_closure_at_poi_confirmed" in direct_source
    )
    replay_ttrades_ltf_cisd = "ttrades_ltf_cisd_confirmed" in direct_source
    replay_ttrades_protected_swing = (
        "ttrades_protected_swing_confirmed" in direct_source
    )
    replay_ttrades_continuation = (
        "ttrades_continuation_confirmed" in direct_source
    )
    replay_ttrades_wick = (
        "ttrades_wick_formation_confirmed" in direct_source
    )

    replay_ict_liquidity = (
        "_liquidity_levels" in direct_source
        and "_find_sweep_closeback" in direct_source
    )
    replay_ict_mss = "find_source_first_m3_mss" in direct_source
    replay_ict_displacement = (
        "BODY_RATIO_MIN" in v3_source
        and "ATR_MULTIPLIER" in v3_source
    )
    replay_ict_fvg = "_m1_causal_zone" in direct_source
    replay_ict_retrace = "_find_m1_fill" in direct_source
    replay_no_chase_explicit = (
        "ict_entry_not_chasing" in direct_source
        or "ENTRY_OPEN_OUTSIDE_FVG_CHASE" in direct_source
    )

    canonical_stop_exact_protected_swing = (
        "initial_stop_price=facts.protected_swing_price" in plan_source
    )
    replay_stop_broken_swing_buffer = (
        "broken_swing_price" in direct_source
        and "_stop_buffer" in direct_source
    )

    checks = (
        FidelityCheck(
            key="CANONICAL_SOURCE_ENGINE_HANDOFF",
            canonical_required=True,
            replay_satisfies=replay_invokes_source_engine,
            hard_mismatch=not replay_invokes_source_engine,
            evidence=(
                "Canonical engine is not invoked by direct economic replay."
                if not replay_invokes_source_engine
                else "Canonical engine is invoked."
            ),
        ),
        FidelityCheck(
            key="DUAL_SOURCE_ENTRY_ACCEPTANCE",
            canonical_required=canonical_gate_bound,
            replay_satisfies=replay_binds_dual_gate,
            hard_mismatch=canonical_gate_bound and not replay_binds_dual_gate,
            evidence=(
                "Canonical engine fail-closes without dual-source acceptance; "
                "direct replay does not bind that object."
            ),
        ),
        FidelityCheck(
            key="HIGHER_TIMEFRAME_BIAS_OBJECT",
            canonical_required="higher_timeframe_bias_confirmed_aligned"
            in canonical_dual_fields,
            replay_satisfies=replay_binds_htf_bias,
            hard_mismatch=not replay_binds_htf_bias,
            evidence="Direct replay does not bind canonical HTF bias object.",
        ),
        FidelityCheck(
            key="CANONICAL_ENTRY_ROUTE",
            canonical_required=True,
            replay_satisfies=replay_binds_canonical_route,
            hard_mismatch=not replay_binds_canonical_route,
            evidence=(
                "Direct replay does not exercise canonical FRACTAL/FTM route."
            ),
        ),
        FidelityCheck(
            key="STRUCTURAL_HTF_TARGET",
            canonical_required=canonical_structural_target,
            replay_satisfies=replay_binds_structural_target,
            hard_mismatch=(
                canonical_structural_target
                and not replay_binds_structural_target
            ),
            evidence=(
                f"Canonical target is structural; replay target identity="
                f"{v3.TARGET_IDENTITY}."
            ),
        ),
        FidelityCheck(
            key="NO_INVENTED_FIXED_R_TARGET",
            canonical_required=canonical_fixed_r_forbidden,
            replay_satisfies=not replay_fixed_2r,
            hard_mismatch=canonical_fixed_r_forbidden and replay_fixed_2r,
            evidence=(
                f"Canonical fixed_r_target_invented=False; replay TARGET_R="
                f"{direct.TARGET_R}."
            ),
        ),
        FidelityCheck(
            key="TARGET_IDENTITY_PARITY",
            canonical_required=True,
            replay_satisfies=not replay_target_identity_fixed_2r,
            hard_mismatch=replay_target_identity_fixed_2r,
            evidence=f"Replay TARGET_IDENTITY={v3.TARGET_IDENTITY}.",
        ),
        FidelityCheck(
            key="ICT_LIQUIDITY_RAID",
            canonical_required="ict_liquidity_raid_observed"
            in canonical_dual_fields,
            replay_satisfies=replay_ict_liquidity,
            hard_mismatch=not replay_ict_liquidity,
            evidence="Replay reconstructs causal liquidity + closeback.",
        ),
        FidelityCheck(
            key="ICT_MSS_DISPLACEMENT",
            canonical_required=True,
            replay_satisfies=replay_ict_mss and replay_ict_displacement,
            hard_mismatch=not (replay_ict_mss and replay_ict_displacement),
            evidence="Replay uses M3 MSS with body/ATR displacement law.",
        ),
        FidelityCheck(
            key="ICT_FVG_RETRACE",
            canonical_required=True,
            replay_satisfies=replay_ict_fvg and replay_ict_retrace,
            hard_mismatch=not (replay_ict_fvg and replay_ict_retrace),
            evidence="Replay uses M1 causal zone + fill.",
        ),
        FidelityCheck(
            key="ICT_NO_CHASE_EXPLICIT",
            canonical_required="ict_entry_not_chasing" in canonical_dual_fields,
            replay_satisfies=replay_no_chase_explicit,
            hard_mismatch=not replay_no_chase_explicit,
            evidence="Direct replay does not bind canonical no-chase fact.",
        ),
        FidelityCheck(
            key="TTRADES_HTF_CLOSURE",
            canonical_required="ttrades_htf_closure_at_poi_confirmed"
            in canonical_dual_fields,
            replay_satisfies=replay_ttrades_htf_closure,
            hard_mismatch=not replay_ttrades_htf_closure,
            evidence="Canonical TTrades HTF closure not bound in replay.",
        ),
        FidelityCheck(
            key="TTRADES_LTF_CISD",
            canonical_required="ttrades_ltf_cisd_confirmed"
            in canonical_dual_fields,
            replay_satisfies=replay_ttrades_ltf_cisd,
            hard_mismatch=not replay_ttrades_ltf_cisd,
            evidence="Canonical TTrades LTF CISD not bound in replay.",
        ),
        FidelityCheck(
            key="TTRADES_PROTECTED_SWING",
            canonical_required="ttrades_protected_swing_confirmed"
            in canonical_dual_fields,
            replay_satisfies=replay_ttrades_protected_swing,
            hard_mismatch=not replay_ttrades_protected_swing,
            evidence="Canonical TTrades protected-swing fact not bound.",
        ),
        FidelityCheck(
            key="TTRADES_CONTINUATION",
            canonical_required="ttrades_continuation_confirmed"
            in canonical_dual_fields,
            replay_satisfies=replay_ttrades_continuation,
            hard_mismatch=not replay_ttrades_continuation,
            evidence="Canonical TTrades continuation fact not bound.",
        ),
        FidelityCheck(
            key="TTRADES_WICK_FORMATION",
            canonical_required="ttrades_wick_formation_confirmed"
            in canonical_dual_fields,
            replay_satisfies=replay_ttrades_wick,
            hard_mismatch=not replay_ttrades_wick,
            evidence="Canonical wick-formation fact not bound.",
        ),
        FidelityCheck(
            key="M1_MSS_FVG_OB_COMPLETE",
            canonical_required=True,
            replay_satisfies=replay_m1_mss and replay_m1_fvg and replay_m1_ob,
            hard_mismatch=not (
                replay_m1_mss and replay_m1_fvg and replay_m1_ob
            ),
            evidence=(
                "Replay has M1 OB/FVG but its explicit structure shift is M3, "
                "not canonical M1 MSS."
            ),
        ),
        FidelityCheck(
            key="PROTECTED_SWING_STOP_PARITY",
            canonical_required=canonical_stop_exact_protected_swing,
            replay_satisfies=not replay_stop_broken_swing_buffer,
            hard_mismatch=(
                canonical_stop_exact_protected_swing
                and replay_stop_broken_swing_buffer
            ),
            evidence=(
                f"Canonical plan anchors stop at protected swing; replay stop "
                f"identity={v3.STOP_IDENTITY}."
            ),
        ),
    )

    hard = tuple(row for row in checks if row.hard_mismatch)
    return {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "evaluation": "STATIC_CODE_CONTRACT_FIDELITY_ONLY",
        "canonical_grammar_identity": grammar.SOURCE_STRATEGY_GRAMMAR_ID,
        "dual_source_identity": dual.IDENTITY,
        "replay_identity": direct.IDENTITY,
        "replay_target_r": str(direct.TARGET_R),
        "replay_target_identity": v3.TARGET_IDENTITY,
        "replay_stop_identity": v3.STOP_IDENTITY,
        "canonical_dual_gate_bound": canonical_gate_bound,
        "canonical_structural_target": canonical_structural_target,
        "canonical_fixed_r_forbidden": canonical_fixed_r_forbidden,
        "check_count": len(checks),
        "hard_mismatch_count": len(hard),
        "checks": [asdict(row) for row in checks],
        "economics_opened": False,
        "admission_changed": False,
        "target_changed": False,
        "stop_changed": False,
        "sizing_changed": False,
        "protection_changed": False,
        "fresh_holdout_opened": False,
        "runtime_policy_candidate": False,
        "candidate_count": 0,
        "trader_certified": False,
        "next_phase": (
            "SOURCE_FIDELITY_GAP_CONFIRMED_BUILD_NATIVE_SOURCE_FAITHFUL_REPLAY_V46"
            if hard
            else "SOURCE_FIDELITY_PARITY_CONFIRMED_RETURN_TO_EDGE_ARCHITECTURE"
        ),
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-source-engine-replay-fidelity-audit-v45.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    report = build_report()
    output = Path("audit-output")
    write_report(report, output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
