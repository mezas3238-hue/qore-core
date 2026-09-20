"""Deterministic source-observation contract for QORE Capitalizer V2.

This is the missing bridge between reviewed ICT/TTrades methodology and raw market data.
The contract enumerates every observation that must be produced causally from historical bars
before integrated nine-market replay is allowed.

The contract itself is not evidence that the detectors are implemented; status remains
RESEARCH_OPEN until every detector is implemented and source-equivalence tested.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerChainStatus,
)

SOURCE_OBSERVATION_CONTRACT_ID = "QORE_CAPITALIZER_SOURCE_OBSERVATION_CONTRACT_V2"


class CapitalizerSourceObservationKind(StrEnum):
    HISTORICAL_ASIAN_OPEN_REFERENCE = "HISTORICAL_ASIAN_OPEN_REFERENCE"
    SOURCE_POINT_OF_INTEREST = "SOURCE_POINT_OF_INTEREST"
    ICT_HIGHER_TIMEFRAME_DAILY_BIAS = "ICT_HIGHER_TIMEFRAME_DAILY_BIAS"
    TTRADES_H1_C2_C3_EXPANSION_BIAS = "TTRADES_H1_C2_C3_EXPANSION_BIAS"
    STRUCTURAL_LIQUIDITY_OBJECTIVE = "STRUCTURAL_LIQUIDITY_OBJECTIVE"
    TTRADES_M15_SWING_STRUCTURE = "TTRADES_M15_SWING_STRUCTURE"
    TTRADES_M1_CONTINUATION_CONFIRMATION = "TTRADES_M1_CONTINUATION_CONFIRMATION"
    TTRADES_PROTECTED_SWING = "TTRADES_PROTECTED_SWING"
    FTM_LIQUIDITY_LEVEL_TAKEN = "FTM_LIQUIDITY_LEVEL_TAKEN"
    FTM_EXPECTED_REVERSAL_FAILED = "FTM_EXPECTED_REVERSAL_FAILED"
    FTM_CANDLE_CLOSE_CONFIRMATION = "FTM_CANDLE_CLOSE_CONFIRMATION"
    FTM_CONTINUATION_STRUCTURE = "FTM_CONTINUATION_STRUCTURE"


@dataclass(frozen=True, slots=True)
class CapitalizerSourceObservationRequirement:
    kind: CapitalizerSourceObservationKind
    source_fact_ids: tuple[str, ...]
    decision_time_only: bool = True
    detector_implemented: bool = False
    source_equivalence_tested: bool = False

    def __post_init__(self) -> None:
        if not self.source_fact_ids:
            raise ValueError("source observation requirement needs provenance")
        if not self.decision_time_only:
            raise ValueError("source observation must be causal decision-time only")
        if self.source_equivalence_tested and not self.detector_implemented:
            raise ValueError("source-equivalence test requires implemented detector")


SOURCE_OBSERVATION_REQUIREMENTS: tuple[CapitalizerSourceObservationRequirement, ...] = (
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.HISTORICAL_ASIAN_OPEN_REFERENCE,
        ("ICT_ASIAN_OPEN_RELATIVE_TWO_HOUR_WINDOW",),
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.SOURCE_POINT_OF_INTEREST,
        (
            "TTRADES_FVG_THREE_CANDLE_NON_OVERLAP",
            "TTRADES_EXTERNAL_LIQUIDITY_SWING_HIGH_LOW",
        ),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.ICT_HIGHER_TIMEFRAME_DAILY_BIAS,
        (
            "ICT_DAILY_BIAS_PRECEDES_SCALP_EXECUTION",
            "TTRADES_DAILY_BIAS_CLOSURE_BEFORE_INTRADAY_EXECUTION",
        ),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.TTRADES_H1_C2_C3_EXPANSION_BIAS,
        (
            "TTRADES_H1_EXPANSION_BIAS_C2_C3",
            "TTRADES_C2_SWEEP_CLOSE_INSIDE_AT_POI",
            "TTRADES_C3_BODY_CLOSURE_AFTER_C2_FAILURE",
        ),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.STRUCTURAL_LIQUIDITY_OBJECTIVE,
        (
            "ICT_LIQUIDITY_TARGETS_RECENT_DAILY_HIGHS_LOWS",
            "TTRADES_TARGET_USES_HIGHER_TIMEFRAME_OBJECTIVE",
            "TTRADES_TARGETS_UNTOUCHED_HTF_HIGHS_LOWS",
        ),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.TTRADES_M15_SWING_STRUCTURE,
        (
            "TTRADES_M15_SWING_THEN_M1_CONTINUATION",
            "TTRADES_CISD_CLOSES_THROUGH_CAUSAL_CANDLE_SERIES",
            "TTRADES_CISD_REQUIRES_HTF_C2_OR_C3_CONTEXT",
        ),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.TTRADES_M1_CONTINUATION_CONFIRMATION,
        (
            "TTRADES_M15_SWING_THEN_M1_CONTINUATION",
            "TTRADES_CISD_CLOSES_THROUGH_CAUSAL_CANDLE_SERIES",
        ),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.TTRADES_PROTECTED_SWING,
        (
            "TTRADES_PROTECTED_SWING_STOP",
            "TTRADES_PROTECTED_SWING_REQUIRES_CONFIRMED_CLOSURE",
            "TTRADES_PROTECTED_SWING_IS_INVALIDATION_ANCHOR",
        ),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.FTM_LIQUIDITY_LEVEL_TAKEN,
        ("TTRADES_FAILURE_TO_MANIPULATE_REQUIRES_FAILED_REVERSAL",),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.FTM_EXPECTED_REVERSAL_FAILED,
        (
            "TTRADES_FAILURE_TO_MANIPULATE_REQUIRES_FAILED_REVERSAL",
            "TTRADES_FAILURE_TO_MANIPULATE_USES_HTF_BIAS",
        ),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.FTM_CANDLE_CLOSE_CONFIRMATION,
        ("TTRADES_WAIT_FOR_CANDLE_CLOSURE_CONFIRMATION",),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
    CapitalizerSourceObservationRequirement(
        CapitalizerSourceObservationKind.FTM_CONTINUATION_STRUCTURE,
        (
            "TTRADES_FAILURE_TO_MANIPULATE_REQUIRES_FAILED_REVERSAL",
            "TTRADES_FAILURE_TO_MANIPULATE_USES_HTF_BIAS",
            "TTRADES_PROTECTED_SWING_REQUIRES_CONFIRMED_CLOSURE",
        ),
        detector_implemented=True,
        source_equivalence_tested=True,
    ),
)


@dataclass(frozen=True, slots=True)
class CapitalizerSourceObservationContract:
    contract_id: str = SOURCE_OBSERVATION_CONTRACT_ID
    requirements: tuple[
        CapitalizerSourceObservationRequirement, ...
    ] = SOURCE_OBSERVATION_REQUIREMENTS
    status: CapitalizerChainStatus = CapitalizerChainStatus.RESEARCH_OPEN
    outcome_aware_detector_allowed: bool = False
    numeric_fit_to_backtest_allowed: bool = False
    replay_authorized: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != SOURCE_OBSERVATION_CONTRACT_ID:
            raise ValueError("source observation contract identity is frozen")
        kinds = tuple(item.kind for item in self.requirements)
        if set(kinds) != set(CapitalizerSourceObservationKind):
            raise ValueError("source observation contract must cover every required detector")
        if len(kinds) != len(set(kinds)):
            raise ValueError("source observation contract cannot duplicate detector kinds")
        if self.status is not CapitalizerChainStatus.RESEARCH_OPEN:
            raise ValueError("source observation layer remains RESEARCH_OPEN")
        if self.outcome_aware_detector_allowed or self.numeric_fit_to_backtest_allowed:
            raise ValueError("source observation detectors cannot be outcome-fitted")
        if self.replay_authorized:
            raise ValueError("replay remains blocked until all source detectors close")


SOURCE_OBSERVATION_CONTRACT = CapitalizerSourceObservationContract()
