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
        "Existing bias detector freezes one C2/C3-at-POI route; Asia needs route-native HTF framing.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        "LTF_CISD_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_cisd_ftm_v2.py::detect_cisd",
        "Raw structural CISD mechanics are reusable but V2 setup_confirmed carries old HTF coupling.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        "PROTECTED_SWING_CONFIRMED",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_source_observation_detectors_v2.py::confirm_protected_swing",
        "Protected-swing confirmation is a causal primitive independent of economics.",
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
        "H4_C2_CONFIRMATION",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_source_observation_detectors_v2.py::detect_candle2_reversal_closure",
        "Candle-2 mechanics are reusable when rebound to the 4H route.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "M15_CISD_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_cisd_ftm_v2.py::detect_cisd",
        "Use raw structural CISD, not the old setup_confirmed conjunction.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "M15_CONTINUATION_AVAILABLE",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_ASIA_15M_CONTINUATION_DETECTOR_REQUIRED",
        "The repository does not yet have the route-native continuation detector.",
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
        "DAILY_WICK_FORMATION_CONFIRMED",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_LONDON_DAILY_WICK_DETECTOR_REQUIRED",
        "Need a causal daily-wick completion detector before body participation.",
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
        "M15_CISD_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_cisd_ftm_v2.py::detect_cisd",
        "Structural CISD mechanics reusable after removing old route coupling.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "M15_CONTINUATION_AVAILABLE",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_LONDON_15M_CONTINUATION_DETECTOR_REQUIRED",
        "Source requires continuation after protected-swing confirmation.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "NY_CISD_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_cisd_ftm_v2.py::detect_cisd",
        "CISD mechanics exist but must bind to the post-NY-sweep causal series.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "NY_LIQUIDITY_SWEEP_CONFIRMED",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_NY_RANGE_SWEEP_DETECTOR_REQUIRED",
        "Need source-native London-range/New-York sweep identity.",
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
        "M15_SWING_STRUCTURE_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_observation_detectors_v2.py",
        "Need M15 swing specifically tied to forming the H1 wick.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        "M1_CONTINUATION_CONFIRMED",
        V48DetectorReadiness.DETECTOR_MISSING,
        "capitalizer_ttrades_m1_cisd_observer_v48.py",
        "Raw M1 CISD exists, but source-valid continuation semantics are broader than CISD alone.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        "CONTINUATION_STRUCTURE_CONFIRMED",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_source_native_ftm_v48.py::assess_source_native_ftm",
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
