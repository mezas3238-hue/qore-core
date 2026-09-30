"""V48 route detector-readiness ledger.

This ledger separates reusable causal primitives from route-specific rebinding work and
missing detectors. It is intentionally pre-economic. A source fact being conceptually
resolved does not imply that the repository already has a source-faithful detector for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)

IDENTITY = "QORE_CAPITALIZER_V48_ROUTE_DETECTOR_READINESS"


class V48DetectorReadiness(StrEnum):
    REUSABLE_CAUSAL_PRIMITIVE = "REUSABLE_CAUSAL_PRIMITIVE"
    NEEDS_ROUTE_SCOPED_REBIND = "NEEDS_ROUTE_SCOPED_REBIND"
    DETECTOR_MISSING = "DETECTOR_MISSING"
    SOURCE_BINDING_BLOCKED = "SOURCE_BINDING_BLOCKED"


@dataclass(frozen=True, slots=True)
class V48RouteDetectorFact:
    route_id: V48RouteId
    fact_id: str
    readiness: V48DetectorReadiness
    implementation_reference: str
    note: str

    def __post_init__(self) -> None:
        if not self.fact_id or self.fact_id != self.fact_id.upper():
            raise ValueError("detector fact id must be non-empty uppercase")
        if not self.implementation_reference or not self.note:
            raise ValueError("detector fact requires implementation provenance")


FACTS: tuple[V48RouteDetectorFact, ...] = (
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        "HTF_FRACTAL_BIAS_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_daily_bias_v2.py",
        (
            "Existing bias detector freezes one C2/C3-at-POI route; Asia needs "
            "route-native HTF framing."
        ),
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        "LTF_PROTECTED_SWING_CONFIRMED_BY_CISD",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ttrades_structural_cisd_v48.py::observe_first_structural_cisd",
        "V48 source-native CISD now confirms the protected swing without old V2 coupling.",

    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        "POSITIONAL_OPEN_AVAILABLE",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_POSITIONAL_ROUTE_BINDING_REQUIRED",
        "Need causal binding of completed framework to the next HTF candle open.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "H4_PROFILE_TIME_BINDING",
        V48DetectorReadiness.SOURCE_BINDING_BLOCKED,
        "capitalizer_h4_profile_binding_v48.py",
        "Exact TTrades H4 profile-to-provider candle boundary binding remains unresolved.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "H4_C2_CONFIRMATION",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_observation_detectors_v2.py::detect_candle2_reversal_closure",
        "Candle-2 mechanics are reusable after the H4 profile clock is source-bound.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ttrades_structural_cisd_v48.py::observe_first_structural_cisd",
        "Use one causal CISD-to-protected-swing fact, not two independent gates.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "M15_CONTINUATION_AVAILABLE",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ttrades_continuation_v48.py::assess_source_native_continuation",
        "Continuation semantics exist; Asia still needs causal POI binding on 15M.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "DAILY_BIAS_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_daily_bias_v2.py",
        "London source permits broader daily-bias methods than one globally frozen C2/C3 path.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "H4_PROFILE_TIME_BINDING",
        V48DetectorReadiness.SOURCE_BINDING_BLOCKED,
        "capitalizer_h4_profile_binding_v48.py",
        "Exact TTrades H4 profile-to-provider candle boundary binding remains unresolved.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "H4_WICK_SWING_STRUCTURE_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_observation_detectors_v2.py",
        "Closure/swing primitives exist but London 4H wick semantics need route binding.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ttrades_structural_cisd_v48.py::observe_first_structural_cisd",
        "CISD confirms the protected swing; keep it as one causal route fact.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "M15_CONTINUATION_AVAILABLE",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ttrades_continuation_v48.py::assess_source_native_continuation",
        "Continuation semantics exist; London still needs causal POI binding on 15M.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "LONDON_CONTEXT_RESOLVED",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_LONDON_CONTEXT_RESOLVER_REQUIRED",
        "Need a causal London consolidation/range-context resolver for this NY profile.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "NY_CISD_CONFIRMED",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_ny_manipulation_observer_v48.py::observe_new_york_manipulation",
        "NY observer binds post-sweep opposing-series closure directly to the profile.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "NY_LIQUIDITY_SWEEP_CONFIRMED",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_ny_manipulation_observer_v48.py::observe_new_york_manipulation",
        "NY observer detects the London-range sweep causally before CISD.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        "H1_SCALP_BIAS_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_observation_detectors_v2.py",
        "C2/C3 mechanics exist; H1 scalp-bias orchestration still needs V48 route binding.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ttrades_structural_cisd_v48.py::observe_first_structural_cisd",
        "Bind H1 closure to the M15 CISD that confirms the hourly wick swing.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        "M1_CONTINUATION_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ttrades_continuation_v48.py::assess_source_native_continuation",
        "Continuation semantics exist; M1 still needs causal FVG/sweep POI binding.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        "CONTINUATION_STRUCTURE_CONFIRMED",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_source_native_ftm_observer_v48.py::observe_source_native_ftm",
        "V48 FTM primitive now encodes the source-native failure-then-continuation identity.",
    ),
    V48RouteDetectorFact(
        V48RouteId.ICT_2022_EXECUTION,
        "ICT_EXACT_PRIMARY_SOURCE_BINDING",
        V48DetectorReadiness.SOURCE_BINDING_BLOCKED,
        "ICT_2022_VIDEO_TIMESTAMP_PACK_REQUIRED",
        "Exact timestamp-level primary-source binding is not yet closed.",
    ),
)


@dataclass(frozen=True, slots=True)
class V48RouteDetectorReadinessLedger:
    identity: str = IDENTITY
    facts: tuple[V48RouteDetectorFact, ...] = FACTS
    missing_detector_blocks_route_census: bool = True
    outcome_used: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("detector readiness identity is frozen")
        keys = tuple((item.route_id, item.fact_id) for item in self.facts)
        if len(keys) != len(set(keys)):
            raise ValueError("detector readiness facts must be unique")
        if not self.missing_detector_blocks_route_census:
            raise ValueError("missing source detector must fail closed")
        if self.outcome_used or self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("detector readiness ledger is pre-economic")


V48_ROUTE_DETECTOR_READINESS = V48RouteDetectorReadinessLedger()
