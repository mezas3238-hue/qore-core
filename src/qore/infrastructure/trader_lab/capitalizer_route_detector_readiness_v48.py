"""V48 route detector-readiness ledger.

Every mandatory route-contract fact and every source-valid OR option must have an explicit
implementation state. Extra local binding facts (for example the unresolved H4 profile
clock) may also be recorded.

This ledger is pre-economic. It distinguishes a reusable primitive from a fact that is
already route-bound, work that still needs route rebinding, a missing detector, and a
source-binding blocker. No missing contract fact may disappear silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_route_specific_source_contract_v48 import (
    CONTRACTS,
)
from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)

IDENTITY = "QORE_CAPITALIZER_V48_ROUTE_DETECTOR_READINESS"


class V48DetectorReadiness(StrEnum):
    REUSABLE_CAUSAL_PRIMITIVE = "REUSABLE_CAUSAL_PRIMITIVE"
    ROUTE_BOUND_PRE_ECONOMIC = "ROUTE_BOUND_PRE_ECONOMIC"
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
    # ASIA POSITIONAL
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        "DAILY_PROFILE_TIME_BINDING",
        V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC,
        "capitalizer_ttrades_forex_daily_profile_v48.py",
        (
            "TTrades Forex Daily clock is source-bound at 17:00 New York "
            "from the primary timing table."
        ),
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        "HTF_FRACTAL_BIAS_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_daily_bias_v2.py",
        "Asia positional needs its own HTF framing rather than the old global bias route.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        "LTF_PROTECTED_SWING_CONFIRMED_BY_CISD",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_ttrades_structural_cisd_v48.py::observe_first_structural_cisd",
        "Source-native CISD confirms the protected swing without old V2 setup coupling.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        "POSITIONAL_OPEN_AVAILABLE",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_POSITIONAL_ROUTE_BINDING_REQUIRED",
        "Need causal completed-framework binding to the next HTF candle open.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        "STRUCTURAL_TARGET_AVAILABLE",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_structural_target_candidate_set_v48.py",
        "Untouched causal HTF target availability exists without exact target selection.",
    ),
    # ASIA 4H -> 15M
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "DAILY_PROFILE_TIME_BINDING",
        V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC,
        "capitalizer_ttrades_forex_daily_profile_v48.py",
        "Asia Daily bias/open now uses the source-bound 17:00 New York Forex profile.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "H4_PROFILE_TIME_BINDING",
        V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC,
        "capitalizer_ttrades_forex_h4_profile_v48.py",
        "TTrades Forex H4 clock is source-bound to 01/05/09/13/17/21 New York time.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "HTF_FRACTAL_BIAS_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_daily_bias_v2.py",
        "Asia 4H route still needs route-native HTF bias orchestration.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "H4_C2_CONFIRMATION",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ttrades_forex_h4_profile_v48.py + detect_candle2_reversal_closure",
        "Forex H4 clock and C2 primitive exist; Asia orchestration remains to be wired.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_ttrades_structural_cisd_v48.py::observe_first_structural_cisd",
        "One causal CISD-to-protected-swing fact replaces duplicate gates.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "STRUCTURAL_TARGET_AVAILABLE",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_structural_target_candidate_set_v48.py",
        "Untouched causal HTF target availability is reusable.",
    ),
    # LONDON
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "DAILY_PROFILE_TIME_BINDING",
        V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC,
        "capitalizer_ttrades_forex_daily_profile_v48.py",
        "London Daily bias can use the source-bound 17:00 New York Forex profile.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "H4_PROFILE_TIME_BINDING",
        V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC,
        "capitalizer_ttrades_forex_h4_profile_v48.py",
        "TTrades Forex H4 clock is source-bound to 01/05/09/13/17/21 New York time.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "DAILY_BIAS_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_source_daily_bias_v2.py",
        "London permits broader daily-bias methods than one globally frozen C2/C3 path.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "H4_WICK_SWING_STRUCTURE_CONFIRMED",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ttrades_forex_h4_profile_v48.py + source observation detectors",
        "Forex H4 profile exists; London wick/swing route orchestration remains to be wired.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_ttrades_structural_cisd_v48.py::observe_first_structural_cisd",
        "CISD confirms the 15M protected swing as one causal fact.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "M15_CONTINUATION_AVAILABLE",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ttrades_continuation_v48.py::assess_source_native_continuation",
        "Continuation semantics exist; London still needs causal 15M POI orchestration.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "STRUCTURAL_TARGET_AVAILABLE",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_structural_target_candidate_set_v48.py",
        "Untouched causal HTF target availability is reusable.",
    ),
    # NEW YORK MANIPULATION
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "LONDON_CONTEXT_RESOLVED",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_LONDON_CONTEXT_RESOLVER_REQUIRED",
        "Need causal London consolidation/range-context resolver for this NY profile.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "NY_LIQUIDITY_SWEEP_CONFIRMED",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_ny_manipulation_observer_v48.py::observe_new_york_manipulation",
        "NY observer detects the London-range sweep causally before CISD.",
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
        "STRUCTURAL_INVALIDATION_AVAILABLE",
        V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND,
        "capitalizer_ny_manipulation_observer_v48.py",
        "Sweep extreme is observed; exact source-valid execution invalidation still needs binding.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "STRUCTURAL_TARGET_AVAILABLE",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_structural_target_candidate_set_v48.py",
        "Untouched HTF target availability is reusable.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "FVG_ENTRY_AVAILABLE",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_NY_FVG_ENTRY_BINDING_REQUIRED",
        "FVG is source-valid but exact NY entry availability is not yet route-bound.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "ORDER_BLOCK_ENTRY_AVAILABLE",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_NY_ORDER_BLOCK_ENTRY_BINDING_REQUIRED",
        "Order Block is source-valid but exact NY entry availability is not yet route-bound.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "OTHER_SOURCE_VALID_ENTRY_AVAILABLE",
        V48DetectorReadiness.DETECTOR_MISSING,
        "V48_NY_OTHER_ENTRY_MODEL_BINDING_REQUIRED",
        "No catch-all entry may be treated as available without explicit source binding.",
    ),
    # GENERIC SCALPING H1 -> M15 -> M1
    V48RouteDetectorFact(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        "H1_SCALP_BIAS_CONFIRMED",
        V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC,
        "capitalizer_generic_scalp_census_v48.py::_build_h1_bias_events",
        "V48 census binds source C2/C3-at-POI H1 bias without Daily veto.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
        V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC,
        "capitalizer_ttrades_structural_cisd_v48.py::observe_first_structural_cisd",
        "H1 closure is bound to the M15 CISD that confirms the wick/protected swing.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        "M1_CONTINUATION_CONFIRMED",
        V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC,
        "capitalizer_generic_scalp_census_v48.py",
        "Census implements sweep+CISD OR FVG-retrace+CISD with chronological arbitration.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        "LOGICAL_PROTECTED_SWING_STOP_AVAILABLE",
        V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC,
        "capitalizer_generic_scalp_census_v48.py",
        "Census verifies protected-swing geometry without choosing an execution price.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        "STRUCTURAL_TARGET_AVAILABLE",
        V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC,
        "capitalizer_generic_scalp_census_v48.py::_untouched_h1_target",
        "Census requires a causal untouched H1 target witness without freezing target selection.",
    ),
    # FAILURE TO MANIPULATE
    V48RouteDetectorFact(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        "HTF_BIAS_ALIGNED",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_source_native_ftm_observer_v48.py::observe_source_native_ftm",
        "Canonical FTM observer requires HTF direction aligned with continuation.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        "LIQUIDITY_LEVEL_TAKEN",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_source_native_ftm_observer_v48.py::observe_source_native_ftm",
        "Canonical FTM observer requires the relevant level to be taken.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        "EXPECTED_REVERSAL_FAILED_TO_CONFIRM",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_source_native_ftm_observer_v48.py::observe_source_native_ftm",
        "Canonical FTM observer explicitly distinguishes failed from confirmed reversal.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        "CONTINUATION_STRUCTURE_CONFIRMED",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_source_native_ftm_observer_v48.py::observe_source_native_ftm",
        "Canonical FTM observer requires source-native continuation structure.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        "CONTINUATION_PROTECTED_SWING_CONFIRMED",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_source_native_ftm_observer_v48.py::observe_source_native_ftm",
        "Canonical FTM observer requires the continuation protected swing.",
    ),
    V48RouteDetectorFact(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        "STRUCTURAL_TARGET_AVAILABLE",
        V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE,
        "capitalizer_structural_target_candidate_set_v48.py",
        "Untouched causal HTF target availability is reusable.",
    ),
    # ICT remains independently source-binding blocked.
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

        readiness_keys = set(keys)
        contract_keys = {
            (contract.route_id, fact_id)
            for contract in CONTRACTS
            for fact_id in contract.required_fact_ids
        }
        contract_keys.update(
            (contract.route_id, option)
            for contract in CONTRACTS
            for group in contract.alternative_groups
            for option in group.option_fact_ids
        )
        missing = contract_keys - readiness_keys
        if missing:
            raise ValueError(f"route-contract facts missing detector readiness: {sorted(missing)}")

        if not self.missing_detector_blocks_route_census:
            raise ValueError("missing source detector must fail closed")
        if self.outcome_used or self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("detector readiness ledger is pre-economic")


V48_ROUTE_DETECTOR_READINESS = V48RouteDetectorReadinessLedger()
