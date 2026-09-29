"""Native source-faithful fact operationalization gate for Capitalizer V46.

Phase A only: audit whether every canonical source fact has a deterministic
operationalization and whether one chronological replay adapter binds those
facts into the canonical dual-source gate / source trader engine.

No strategy economics are read. Phase B provider/time coverage is forbidden
until Phase A is READY.

Frozen in PR #623 comment 5883088393.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_historical_replay_adapter_v46 as historical_adapter,
)
from qore.infrastructure.trader_lab import (
    capitalizer_dual_source_entry_acceptance_v1 as dual,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as remediation,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_cisd_ftm_v2 as cisd,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_daily_bias_v2 as daily_bias,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_fractal_alignment_v2 as fractal,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_observation_detectors_v2 as observations,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_poi_v2 as poi,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_session_context_v2 as session_context,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_trade_plan_v2 as trade_plan,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_trader_engine_v2 as source_engine,
)

IDENTITY = "QORE_CAPITALIZER_NATIVE_SOURCE_FAITHFUL_FACT_COVERAGE_V46"
PREDECLARATION_COMMENT_ID = 5883088393
MANDATORY_FACT_COUNT = 26


class OperationalizationStatus(StrEnum):
    DETECTOR_READY = "DETECTOR_READY"
    COMPOSER_READY_REQUIRES_BOUND_INPUT = "COMPOSER_READY_REQUIRES_BOUND_INPUT"
    SELECTION_RULE_MISSING = "SELECTION_RULE_MISSING"
    DETECTOR_MISSING = "DETECTOR_MISSING"
    EXTERNAL_REFERENCE_REQUIRED = "EXTERNAL_REFERENCE_REQUIRED"
    REPLAY_ADAPTER_MISSING = "REPLAY_ADAPTER_MISSING"


BLOCKING_STATUSES = {
    OperationalizationStatus.SELECTION_RULE_MISSING,
    OperationalizationStatus.DETECTOR_MISSING,
    OperationalizationStatus.EXTERNAL_REFERENCE_REQUIRED,
    OperationalizationStatus.REPLAY_ADAPTER_MISSING,
}


@dataclass(frozen=True, slots=True)
class FactOperationalization:
    fact_index: int
    fact: str
    status: OperationalizationStatus
    evidence: str
    deterministic: bool
    causal_by_contract: bool
    economics_required: bool = False


def _module_source(module: Any) -> str:
    return inspect.getsource(module)


def _has_callable(module: Any, name: str) -> bool:
    return callable(getattr(module, name, None))


def _facts() -> tuple[FactOperationalization, ...]:
    session_source = _module_source(session_context)
    dual_source = _module_source(dual)
    engine_source = _module_source(source_engine)
    plan_source = _module_source(trade_plan)
    direct_source = _module_source(direct)
    v3_source = _module_source(v3)

    source_session_ready = _has_callable(
        session_context,
        "assess_source_session_context",
    )
    asian_reference_unbound = (
        "ICT_ASIAN_OPEN_REFERENCE_REQUIRED" in session_source
        and "asian_open_reference_at" in session_source
    )

    poi_primitives_ready = (
        _has_callable(poi, "detect_fair_value_gap")
        and _has_callable(poi, "detect_external_liquidity_swing")
        and _has_callable(poi, "bar_interacts_with_poi")
    )
    closure_ready = (
        _has_callable(observations, "detect_candle2_reversal_closure")
        and _has_callable(observations, "detect_candle3_confirmation")
    )
    bias_ready = _has_callable(daily_bias, "derive_daily_bias")
    target_primitive_ready = _has_callable(
        observations,
        "assess_structural_target",
    )

    ict_liquidity_ready = (
        "_liquidity_levels" in v3_source
        and "_find_sweep_closeback" in v3_source
    )
    ict_mss_ready = "find_source_first_m3_mss" in direct_source
    displacement_ready = (
        "BODY_RATIO_MIN" in v3_source
        and "ATR_MULTIPLIER" in v3_source
    )
    m1_zone_ready = "_m1_causal_zone" in direct_source
    retrace_ready = "_find_m1_fill" in direct_source

    ltf_cisd_ready = _has_callable(cisd, "detect_cisd")
    protected_swing_ready = _has_callable(
        observations,
        "confirm_protected_swing",
    )
    continuation_ready = (
        _has_callable(cisd, "assess_failure_to_manipulate")
        and _has_callable(fractal, "assess_fractal_alignment")
    )

    m1_fvg_ready = _has_callable(poi, "detect_fair_value_gap")
    trade_plan_ready = _has_callable(
        trade_plan,
        "build_source_trade_plan",
    )
    dual_composer_ready = _has_callable(dual, "assess_dual_source_entry")
    engine_composer_ready = _has_callable(
        source_engine,
        "assess_source_trader_engine",
    )
    htf_poi_context_ready = _has_callable(
        remediation,
        "resolve_htf_poi_context",
    )
    target_selector_ready = _has_callable(
        remediation,
        "resolve_structural_target",
    )
    no_chase_ready = _has_callable(
        remediation,
        "assess_no_chase_entry",
    )
    wick_ready = _has_callable(
        remediation,
        "assess_wick_formation",
    )
    m1_mss_ready = _has_callable(
        remediation,
        "detect_m1_mss",
    )
    m1_order_block_ready = _has_callable(
        remediation,
        "assess_m1_order_block",
    )
    route_resolver_ready = _has_callable(
        remediation,
        "resolve_source_entry_route",
    )

    # The historical Asian Open reference remains deliberately external.
    # V46-R1 closes the seven internal deterministic/selection gaps.
    return (
        FactOperationalization(
            1,
            "SOURCE_SESSION_CONTEXT",
            (
                OperationalizationStatus.DETECTOR_READY
                if source_session_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "assess_source_session_context exists and is DST-aware.",
            source_session_ready,
            True,
        ),
        FactOperationalization(
            2,
            "HISTORICAL_ASIAN_OPEN_REFERENCE",
            (
                OperationalizationStatus.EXTERNAL_REFERENCE_REQUIRED
                if asian_reference_unbound
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            (
                "ASIA fail-closes without asian_open_reference_at; no bound "
                "historical Asian Open source exists in the canonical stack."
            ),
            False,
            True,
        ),
        FactOperationalization(
            3,
            "HTF_SOURCE_POI",
            (
                OperationalizationStatus.DETECTOR_READY
                if poi_primitives_ready and htf_poi_context_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            (
                "V46-R1 retains all causally interacting source POIs and resolves "
                "the boolean HTF POI context without ranking them."
            ),
            poi_primitives_ready and htf_poi_context_ready,
            True,
        ),
        FactOperationalization(
            4,
            "HTF_CANDLE2_CANDLE3_CLOSURE_AT_POI",
            (
                OperationalizationStatus.DETECTOR_READY
                if closure_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "Candle2 reversal and Candle3 confirmation detectors exist.",
            closure_ready,
            True,
        ),
        FactOperationalization(
            5,
            "HIGHER_TIMEFRAME_DAILY_BIAS",
            (
                OperationalizationStatus.COMPOSER_READY_REQUIRES_BOUND_INPUT
                if bias_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "derive_daily_bias composes a confirmed HTF closure.",
            bias_ready,
            True,
        ),
        FactOperationalization(
            6,
            "STRUCTURAL_HTF_TARGET_SELECTION",
            (
                OperationalizationStatus.DETECTOR_READY
                if target_primitive_ready and target_selector_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            (
                "V46-R1 resolves only one unambiguous causal HTF target and "
                "fails closed when multiple distinct objectives survive."
            ),
            target_primitive_ready and target_selector_ready,
            True,
        ),
        FactOperationalization(
            7,
            "STRUCTURAL_TARGET_UNTOUCHED_INTACT",
            (
                OperationalizationStatus.COMPOSER_READY_REQUIRES_BOUND_INPUT
                if target_primitive_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "Target assessment can adjudicate untouched/higher_timeframe once bound.",
            target_primitive_ready,
            True,
        ),
        FactOperationalization(
            8,
            "ICT_LIQUIDITY_REFERENCE",
            (
                OperationalizationStatus.DETECTOR_READY
                if ict_liquidity_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "Existing native-M1 replay deterministically constructs causal liquidity levels.",
            ict_liquidity_ready,
            True,
        ),
        FactOperationalization(
            9,
            "ICT_LIQUIDITY_RAID",
            (
                OperationalizationStatus.DETECTOR_READY
                if ict_liquidity_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "Existing native-M1 replay detects sweep/closeback causally.",
            ict_liquidity_ready,
            True,
        ),
        FactOperationalization(
            10,
            "ICT_MSS",
            (
                OperationalizationStatus.DETECTOR_READY
                if ict_mss_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "find_source_first_m3_mss is bound in current causal source replay.",
            ict_mss_ready,
            True,
        ),
        FactOperationalization(
            11,
            "ICT_SIGNIFICANT_DISPLACEMENT",
            (
                OperationalizationStatus.DETECTOR_READY
                if displacement_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "MSS operationalization retains frozen body-ratio and ATR displacement law.",
            displacement_ready,
            True,
        ),
        FactOperationalization(
            12,
            "ICT_DISPLACEMENT_FVG",
            (
                OperationalizationStatus.DETECTOR_READY
                if m1_zone_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "Current native-M1 causal zone requires displacement-linked FVG.",
            m1_zone_ready,
            True,
        ),
        FactOperationalization(
            13,
            "ICT_VALID_PD_ARRAY_RETRACE",
            (
                OperationalizationStatus.DETECTOR_READY
                if retrace_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "Current _find_m1_fill provides causal retest/fill.",
            retrace_ready,
            True,
        ),
        FactOperationalization(
            14,
            "ICT_EXPLICIT_NO_CHASE",
            (
                OperationalizationStatus.DETECTOR_READY
                if no_chase_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            (
                "V46-R1 requires entry to remain inside the already-confirmed "
                "PD array at the entry timestamp, with no tolerance."
            ),
            no_chase_ready,
            True,
        ),
        FactOperationalization(
            15,
            "TTRADES_LTF_CISD",
            (
                OperationalizationStatus.DETECTOR_READY
                if ltf_cisd_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "detect_cisd implements causal-series close-through semantics.",
            ltf_cisd_ready,
            True,
        ),
        FactOperationalization(
            16,
            "TTRADES_PROTECTED_SWING",
            (
                OperationalizationStatus.DETECTOR_READY
                if protected_swing_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "confirm_protected_swing exists for a bound causal series.",
            protected_swing_ready,
            True,
        ),
        FactOperationalization(
            17,
            "TTRADES_CONTINUATION",
            (
                OperationalizationStatus.COMPOSER_READY_REQUIRES_BOUND_INPUT
                if continuation_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "Fractal alignment and Failure-to-Manipulate composers exist.",
            continuation_ready,
            True,
        ),
        FactOperationalization(
            18,
            "TTRADES_WICK_BEFORE_EXPANSION_BODY",
            (
                OperationalizationStatus.COMPOSER_READY_REQUIRES_BOUND_INPUT
                if wick_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            (
                "V46-R1 composes important-level reach, same-direction "
                "intracandle CISD and protected swing; no wick-size threshold."
            ),
            wick_ready,
            True,
        ),
        FactOperationalization(
            19,
            "M1_MSS",
            (
                OperationalizationStatus.DETECTOR_READY
                if m1_mss_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            (
                "V46-R1 confirms the first completed M1 close through the "
                "latest opposite structural swing."
            ),
            m1_mss_ready,
            True,
        ),
        FactOperationalization(
            20,
            "M1_FVG",
            (
                OperationalizationStatus.DETECTOR_READY
                if m1_fvg_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "Source-equivalent three-candle FVG detector is timeframe-agnostic.",
            m1_fvg_ready,
            True,
        ),
        FactOperationalization(
            21,
            "M1_ORDER_BLOCK",
            (
                OperationalizationStatus.COMPOSER_READY_REQUIRES_BOUND_INPUT
                if m1_order_block_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            (
                "V46-R1 validates the opposing M1 causal series only after "
                "source-POI reach and same-direction CISD confirmation."
            ),
            m1_order_block_ready,
            True,
        ),
        FactOperationalization(
            22,
            "DETERMINISTIC_SOURCE_ROUTE_RESOLUTION",
            (
                OperationalizationStatus.DETECTOR_READY
                if route_resolver_ready
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            (
                "V46-R1 resolves exactly-one-confirmed FRACTAL or FTM and "
                "fails closed on neither/both."
            ),
            route_resolver_ready,
            True,
        ),
        FactOperationalization(
            23,
            "CANONICAL_PROTECTED_SWING_STOP",
            (
                OperationalizationStatus.COMPOSER_READY_REQUIRES_BOUND_INPUT
                if trade_plan_ready
                and "initial_stop_price=facts.protected_swing_price" in plan_source
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "Canonical trade plan anchors stop to the bound protected swing.",
            trade_plan_ready,
            True,
        ),
        FactOperationalization(
            24,
            "CANONICAL_STRUCTURAL_HTF_TARGET",
            (
                OperationalizationStatus.COMPOSER_READY_REQUIRES_BOUND_INPUT
                if trade_plan_ready
                and "target_price=facts.structural_target_price" in plan_source
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            (
                "Canonical trade plan consumes a selected structural target; "
                "selector remains upstream."
            ),
            trade_plan_ready,
            True,
        ),
        FactOperationalization(
            25,
            "COMPOSED_DUAL_SOURCE_ENTRY_ACCEPTANCE",
            (
                OperationalizationStatus.COMPOSER_READY_REQUIRES_BOUND_INPUT
                if dual_composer_ready
                and "ttrades_wick_formation_confirmed" in dual_source
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "assess_dual_source_entry exists and fail-closes missing facts.",
            dual_composer_ready,
            True,
        ),
        FactOperationalization(
            26,
            "COMPOSED_SOURCE_TRADER_ENGINE_ASSESSMENT",
            (
                OperationalizationStatus.COMPOSER_READY_REQUIRES_BOUND_INPUT
                if engine_composer_ready
                and "DUAL_SOURCE_ENTRY_ACCEPTANCE_REQUIRED" in engine_source
                else OperationalizationStatus.DETECTOR_MISSING
            ),
            "assess_source_trader_engine exists and requires the dual-source gate.",
            engine_composer_ready,
            True,
        ),
    )


def build_report() -> dict[str, Any]:
    historical_adapter_ready = _has_callable(
        historical_adapter,
        "assess_canonical_historical_bundle",
    )
    facts = _facts()
    if len(facts) != MANDATORY_FACT_COUNT:
        raise ValueError("V46 mandatory fact inventory drift")
    if tuple(row.fact_index for row in facts) != tuple(
        range(1, MANDATORY_FACT_COUNT + 1)
    ):
        raise ValueError("V46 mandatory fact index drift")

    blocking = tuple(
        row
        for row in facts
        if row.status in BLOCKING_STATUSES
    )

    replay_adapter_status = (
        OperationalizationStatus.DETECTOR_READY
        if historical_adapter_ready
        else OperationalizationStatus.REPLAY_ADAPTER_MISSING
    )
    phase_a_ready = not blocking and historical_adapter_ready

    status_counts: dict[str, int] = {}
    for row in facts:
        status_counts[row.status.value] = (
            status_counts.get(row.status.value, 0) + 1
        )

    return {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "r1_predeclaration_comment_id": remediation.PREDECLARATION_COMMENT_ID,
        "r2_predeclaration_comment_id": (
            historical_adapter.PREDECLARATION_COMMENT_ID
        ),
        "evaluation": "PHASE_A_STATIC_CANONICAL_FACT_OPERATIONALIZATION",
        "mandatory_fact_count": MANDATORY_FACT_COUNT,
        "facts": [asdict(row) for row in facts],
        "status_counts": dict(sorted(status_counts.items())),
        "blocking_fact_count": len(blocking),
        "blocking_facts": [row.fact for row in blocking],
        "canonical_historical_replay_adapter_status": replay_adapter_status.value,
        "phase_a_ready": phase_a_ready,
        "phase_b_authorized": phase_a_ready,
        "phase_b_executed": False,
        "provider_native_m1_economics_opened": False,
        "strategy_economics_calculated": False,
        "fixed_2r_used_as_canonical_target": False,
        "synthetic_asian_open_used": False,
        "synthetic_structural_target_used": False,
        "outcomes_used": False,
        "admission_changed": False,
        "sizing_changed": False,
        "protection_changed": False,
        "fresh_holdout_opened": False,
        "runtime_policy_candidate": False,
        "candidate_count": 0,
        "trader_certified": False,
        "next_phase": (
            "CANONICAL_FACT_COVERAGE_READY_FOR_SOURCE_FAITHFUL_ECONOMIC_REPLAY"
            if phase_a_ready
            else "CANONICAL_FACT_OPERATIONALIZATION_GAPS_REQUIRE_IMPLEMENTATION"
        ),
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-native-source-faithful-fact-coverage-v46.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    report = build_report()
    write_report(report, Path("audit-output"))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
