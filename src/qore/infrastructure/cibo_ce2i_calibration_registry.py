"""Canonical empirical calibration registry for CIBO T01..T20.

Engineering/contract maturity is deliberately separate from calibration and
economic certification. Only burned evidence may move a tool through
calibration. The preregistered 2017H1 holdout is forbidden as a calibration
source.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_burned_calibration import (
    burned_t04_t10_calibration_sha256,
)
from qore.infrastructure.cibo_ce2i_burned_lifecycle_calibration import (
    burned_lifecycle_calibration_sha256,
)
from qore.infrastructure.cibo_ce2i_burned_non_promotion import (
    burned_non_promotion_sha256,
)
from qore.infrastructure.cibo_ce2i_burned_t01_calibration import (
    burned_t01_source_calibration_sha256,
)
from qore.infrastructure.cibo_ce2i_burned_t06_calibration import (
    burned_t06_source_calibration_sha256,
)
from qore.infrastructure.cibo_ce2i_burned_t07_calibration import (
    burned_t07_source_calibration_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    provider_economics_evidence_ref,
)
from qore.infrastructure.cibo_ce2i_t02_calibration_binding import (
    T02_CONTEXT_CALIBRATION_SHA256,
    t02_calibration_source_ref,
)
from qore.infrastructure.cibo_ce2i_tool_registry import (
    CE2I_TOOL_REGISTRY,
    ToolMaturity,
)


class CiboCalibrationState(StrEnum):
    CALIBRATED_CAUSAL = "CALIBRATED_CAUSAL"
    CALIBRATED_ECONOMIC = "CALIBRATED_ECONOMIC"
    PROVIDER_ECONOMICS_REQUIRED = "PROVIDER_ECONOMICS_REQUIRED"
    CALIBRATION_UNAVAILABLE = "CALIBRATION_UNAVAILABLE"
    OOS_READY = "OOS_READY"
    CERTIFICATION_READY = "CERTIFICATION_READY"
    FAIL_CLOSED = "FAIL_CLOSED"


class CiboCalibrationType(StrEnum):
    CAUSAL_NORMALIZED = "CAUSAL_NORMALIZED"
    ECONOMIC = "ECONOMIC"
    MIXED_CAUSAL_AND_ECONOMIC = "MIXED_CAUSAL_AND_ECONOMIC"
    CONTRACT_ONLY = "CONTRACT_ONLY"


@dataclass(frozen=True, slots=True)
class CiboToolCalibrationRecord:
    tool_code: str
    state: CiboCalibrationState
    calibration_type: CiboCalibrationType
    calibration_sources: tuple[str, ...]
    provider_economics_required: bool
    fail_closed: bool
    oos_ready: bool
    certification_ready: bool
    blockers: tuple[str, ...]
    calibration_artifact_sha256: str | None = None
    holdout_outcomes_used: bool = False
    target_aware: bool = False

    def __post_init__(self) -> None:
        canonical = {tool.code for tool in CE2I_TOOL_REGISTRY}
        if self.tool_code not in canonical:
            raise CiboCapitalManagementError(
                "unknown CE2I calibration tool"
            )
        if type(self.state) is not CiboCalibrationState:
            raise CiboCapitalManagementError("invalid calibration state")
        if type(self.calibration_type) is not CiboCalibrationType:
            raise CiboCapitalManagementError("invalid calibration type")
        if not self.calibration_sources:
            raise CiboCapitalManagementError(
                "calibration record requires evidence/source references"
            )
        if len(self.calibration_sources) != len(
            set(self.calibration_sources)
        ):
            raise CiboCapitalManagementError(
                "calibration source references must be unique"
            )
        for name in (
            "provider_economics_required",
            "fail_closed",
            "oos_ready",
            "certification_ready",
            "holdout_outcomes_used",
            "target_aware",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")
        if self.holdout_outcomes_used:
            raise CiboCapitalManagementError(
                "2017H1/fresh holdout outcomes are forbidden in calibration"
            )
        if self.target_aware:
            raise CiboCapitalManagementError(
                "calibration cannot contain an economic target"
            )
        calibrated = self.state in {
            CiboCalibrationState.CALIBRATED_CAUSAL,
            CiboCalibrationState.CALIBRATED_ECONOMIC,
            CiboCalibrationState.OOS_READY,
            CiboCalibrationState.CERTIFICATION_READY,
        }
        if calibrated and not self.calibration_artifact_sha256:
            raise CiboCapitalManagementError(
                "calibrated state requires a sealed calibration artifact hash"
            )
        if (
            self.certification_ready
            and self.state is not CiboCalibrationState.CERTIFICATION_READY
        ):
            raise CiboCapitalManagementError(
                "certification_ready requires CERTIFICATION_READY state"
            )
        if self.oos_ready and self.state not in {
            CiboCalibrationState.OOS_READY,
            CiboCalibrationState.CERTIFICATION_READY,
        }:
            raise CiboCapitalManagementError(
                "oos_ready requires OOS_READY/CERTIFICATION_READY state"
            )
        if (
            self.state
            in {
                CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED,
                CiboCalibrationState.CALIBRATION_UNAVAILABLE,
                CiboCalibrationState.FAIL_CLOSED,
            }
            and not self.blockers
        ):
            raise CiboCapitalManagementError(
                "blocked/unavailable calibration must name blockers"
            )

    @property
    def implemented(self) -> bool:
        tool = next(
            tool
            for tool in CE2I_TOOL_REGISTRY
            if tool.code == self.tool_code
        )
        return tool.maturity is not ToolMaturity.ARCHITECTURE_ONLY

    @property
    def calibrated(self) -> bool:
        return self.state in {
            CiboCalibrationState.CALIBRATED_CAUSAL,
            CiboCalibrationState.CALIBRATED_ECONOMIC,
            CiboCalibrationState.OOS_READY,
            CiboCalibrationState.CERTIFICATION_READY,
        }


_PHASE18 = "burned:phase18:seven-lineage-chronological-replay"
_PHASE19 = "burned:phase19:integrated-common-window"
_PHASE19_WFO = "burned:phase19j:post-freeze-walk-forward"
_PHASE19L_COMPETITION = "burned:phase19l:exact-decision-competition-audit"
_PHASE19M_REGIME = "burned:phase19m:regime-identifiability-audit"
_PHASE19N_FACTOR = "burned:phase19n:directional-factor-topology-audit"
_PROVIDER_GAP = provider_economics_evidence_ref()
_PHASE20_CONTRACT = "phase20:contract-and-failure-proof"
_PHASE19_NON_PROMOTION = (
    "burned:phase19:non-promotion:sha256:"
    + burned_non_promotion_sha256()
)


def _row(
    code: str,
    state: CiboCalibrationState,
    kind: CiboCalibrationType,
    sources: tuple[str, ...],
    blockers: tuple[str, ...],
    *,
    provider: bool = False,
    calibration_artifact_sha256: str | None = None,
) -> CiboToolCalibrationRecord:
    return CiboToolCalibrationRecord(
        tool_code=code,
        state=state,
        calibration_type=kind,
        calibration_sources=sources,
        provider_economics_required=provider,
        fail_closed=True,
        oos_ready=False,
        certification_ready=False,
        blockers=blockers,
        calibration_artifact_sha256=calibration_artifact_sha256,
    )


_BURNED_T04_T10_SHA = burned_t04_t10_calibration_sha256()

CIBO_TOOL_CALIBRATION_REGISTRY: tuple[CiboToolCalibrationRecord, ...] = (
    _row(
        "T01",
        CiboCalibrationState.CALIBRATED_CAUSAL,
        CiboCalibrationType.MIXED_CAUSAL_AND_ECONOMIC,
        (_PHASE18, _PHASE20_CONTRACT, _PROVIDER_GAP),
        (
            "HISTORICAL_2017_PROVIDER_TERMS_NOT_PROVEN",
            "SLIPPAGE_CALIBRATION_REQUIRED_FOR_EXACT_EXECUTION",
            "FRESH_OOS_MINIMAL_SEED_UTILITY_PENDING",
        ),
        provider=True,
        calibration_artifact_sha256=burned_t01_source_calibration_sha256(),
    ),
    _row(
        "T02",
        CiboCalibrationState.CALIBRATED_CAUSAL,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (_PHASE18, t02_calibration_source_ref()),
        (
            "PARTIAL_LINEAGE_CONTEXT_ELIGIBILITY_4_OF_7",
            "R38_EURUSD_RUNTIME_MINIMUM_SAMPLE_30_NOT_MET",
            "FRESH_OOS_VALIDATION_PENDING",
        ),
        calibration_artifact_sha256=T02_CONTEXT_CALIBRATION_SHA256,
    ),
    _row(
        "T03",
        CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED,
        CiboCalibrationType.ECONOMIC,
        (
            _PROVIDER_GAP,
            _PHASE20_CONTRACT,
            "phase20:t03:forward-margin-efficiency-population",
        ),
        (
            "FORWARD_PROVIDER_MARGIN_EFFICIENCY_AUDIT_IMPLEMENTED",
            "HISTORICAL_2017_MARGIN_TERMS_NOT_PROVEN",
            "EQUIVALENT_EXPRESSION_UNIVERSE_NOT_CERTIFIED",
        ),
        provider=True,
    ),
    _row(
        "T04",
        CiboCalibrationState.CALIBRATED_CAUSAL,
        CiboCalibrationType.MIXED_CAUSAL_AND_ECONOMIC,
        (_PHASE18, _PHASE19_WFO, _PROVIDER_GAP),
        (
            "USD_TRUE_STOP_RISK_REQUIRES_HISTORICAL_2017_"
            "TICK_VALUE_AND_CONVERSION",
        ),
        provider=True,
        calibration_artifact_sha256=_BURNED_T04_T10_SHA,
    ),
    _row(
        "T05",
        CiboCalibrationState.CALIBRATED_CAUSAL,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (_PHASE19, _PHASE20_CONTRACT),
        ("INCREMENTAL_RECYCLE_UTILITY_REQUIRES_FRESH_OOS",),
        calibration_artifact_sha256=burned_lifecycle_calibration_sha256(),
    ),
    _row(
        "T06",
        CiboCalibrationState.CALIBRATED_CAUSAL,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (_PHASE19, _PHASE20_CONTRACT),
        (
            "EXPANSION_MULTIPLIER_AND_INCREMENTAL_UTILITY_REQUIRE_FRESH_OOS",
        ),
        calibration_artifact_sha256=burned_t06_source_calibration_sha256(),
    ),
    _row(
        "T07",
        CiboCalibrationState.CALIBRATED_CAUSAL,
        CiboCalibrationType.MIXED_CAUSAL_AND_ECONOMIC,
        (_PHASE19, _PHASE20_CONTRACT, _PROVIDER_GAP),
        (
            "HISTORICAL_2017_PROTECTED_FLOOR_ECONOMICS_NOT_PROVEN",
            "EMPIRICAL_SLIPPAGE_RESERVE_REQUIRED_FOR_EXACT_FLOOR",
            "INCREMENTAL_PROTECTED_CAPACITY_UTILITY_REQUIRES_FRESH_OOS",
        ),
        provider=True,
        calibration_artifact_sha256=burned_t07_source_calibration_sha256(),
    ),
    _row(
        "T08",
        CiboCalibrationState.CALIBRATION_UNAVAILABLE,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (
            _PHASE19,
            "burned:phase19:overlap-dependence",
            _PHASE19N_FACTOR,
            "phase20:t08:causal-factor-magnitude",
            "phase20:t08:forward-magnitude-population",
            "phase20:t08:unbiased-factor-return-contract",
            "phase20:t08:delayed-full-universe-factor-store",
            "phase20:t08:delayed-finalized-m5-collector",
            "phase20:t08:covariance-risk-attribution-candidate",
            "phase20:t08:fresh-oos-netting-ablation-contract",
            "phase20:t08:sealed-shadow-ablation-ledger",
            _PHASE19_NON_PROMOTION,
        ),
        (
            "OVERLAP_DEPENDENCE_DESCRIPTIVE_ONLY",
            "DIRECTIONAL_FACTOR_TOPOLOGY_IDENTIFIED_7_OF_7",
            "MONETARY_FACTOR_MAGNITUDE_CONTRACT_IMPLEMENTED_FOR_FROZEN_UNIVERSE",
            "FULL_UNIVERSE_FACTOR_RETURN_RECONSTRUCTION_IMPLEMENTED",
            "DELAYED_FULL_UNIVERSE_FACTOR_EVIDENCE_STORE_IMPLEMENTED",
            "FINALIZED_M5_SIX_MARKET_COLLECTOR_IMPLEMENTED_NOT_DEPLOYED",
            "COVARIANCE_RISK_ATTRIBUTION_CANDIDATE_IMPLEMENTED_NOT_CERTIFIED",
            "FRESH_OOS_NETTING_ABLATION_CONTRACT_IMPLEMENTED_AWAITING_POPULATION",
            "SEALED_SHADOW_ABLATION_LEDGER_IMPLEMENTED_AWAITING_FORWARD_EVIDENCE",
            "SIGNED_FACTOR_RISK_MAP_NOT_CERTIFIED",
            "CAUSAL_CORRELATION_STATE_NOT_IDENTIFIED",
            "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED",
            "NETTING_CREDIT_NOT_AUTHORIZED_WITHOUT_RISK_CORRELATION_AND_OOS_UTILITY",
        ),
    ),
    _row(
        "T09",
        CiboCalibrationState.CALIBRATION_UNAVAILABLE,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (
            _PHASE19,
            _PHASE19_WFO,
            _PHASE19L_COMPETITION,
            _PHASE20_CONTRACT,
            "phase20:t09-t18:fresh-scarcity-readiness-audit",
            "phase20:t09-t18:frozen-scarcity-utility-analysis",
            _PHASE19_NON_PROMOTION,
        ),
        (
            "ZERO_WALK_FORWARD_POLICY_SURVIVORS",
            "FRESH_SCARCITY_OOS_READINESS_AUDIT_IMPLEMENTED",
            "FROZEN_PHASE20D_SCARCITY_UTILITY_ANALYSIS_IMPLEMENTED",
            "NO_ROBUST_COMPETITION_POLICY_IDENTIFIED",
            "BURNED_EXACT_DECISION_COMPETITION_EPOCHS_0_OF_30",
            "FRESH_FORWARD_EXACT_COMPETITION_EPOCHS_MIN_30_REQUIRED",
            "FRESH_OOS_SCARCITY_GENERALIZATION_REQUIRED",
        ),
    ),
    _row(
        "T10",
        CiboCalibrationState.CALIBRATED_CAUSAL,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (_PHASE19, _PHASE19_WFO),
        (
            "USD_OUTPUT_PER_CAPITAL_TIME_REQUIRES_HISTORICAL_"
            "EXECUTION_ECONOMICS",
        ),
        provider=True,
        calibration_artifact_sha256=_BURNED_T04_T10_SHA,
    ),
    _row(
        "T11",
        CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED,
        CiboCalibrationType.MIXED_CAUSAL_AND_ECONOMIC,
        (
            _PROVIDER_GAP,
            _PHASE20_CONTRACT,
            "phase20:t11:realized-fill-economics-population",
            "phase20:t11:realized-entry-commission-spread-binding",
        ),
        (
            "REALIZED_FILL_SLIPPAGE_AND_LATENCY_POPULATION_AUDIT_IMPLEMENTED",
            "REALIZED_ENTRY_COMMISSION_AND_PREDECISION_"
            "QUOTED_SPREAD_BINDING_IMPLEMENTED",
            "EMPIRICAL_SLIPPAGE_AND_LATENCY_CALIBRATION_REQUIRED",
            "REALIZED_COMMISSION_AND_SPREAD_ECONOMICS_NOT_BOUND",
            "REALIZED_SPREAD_COMPONENT_NOT_SEPARATELY_IDENTIFIED",
            "HISTORICAL_2017_EXECUTION_TERMS_NOT_PROVEN",
        ),
        provider=True,
    ),
    _row(
        "T12",
        CiboCalibrationState.CALIBRATION_UNAVAILABLE,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (
            _PHASE19,
            "burned:phase19:temporal-stability",
            _PHASE19M_REGIME,
            "phase20:t12:canonical-forward-regime-population",
            _PHASE19_NON_PROMOTION,
        ),
        (
            "TEMPORAL_STABILITY_OBSERVATIONAL_ONLY",
            "BURNED_CANONICAL_PREDECISION_REGIME_SCHEMA_COVERAGE_5_OF_7",
            "BURNED_VT31_BESPOKE_REGIME_STATE_NOT_CANONICALLY_MAPPED",
            "BURNED_VT08_SHARED_PREDECISION_REGIME_SCHEMA_NOT_AVAILABLE",
            "FORWARD_CANONICAL_REGIME_POPULATION_AUDIT_IMPLEMENTED",
            "FORWARD_COMMON_CIBO_REGIME_STATE_AVAILABLE_FOR_SEVEN_LINEAGES",
            "FORWARD_ACCOUNT_RISK_SNAPSHOT_BINDING_AUDIT_IMPLEMENTED",
            "FORWARD_PROVIDER_CONDITION_STATE_BINDING_AUDIT_IMPLEMENTED",
            "HISTORICAL_ACCOUNT_STATE_NOT_BOUND_TO_SHARED_REGIME_SCHEMA",
            "HISTORICAL_PROVIDER_CONDITION_NOT_BOUND_TO_REGIME_STATE",
            "PORTFOLIO_CAUSAL_REGIME_BOUNDARY_NOT_IDENTIFIED",
            "FRESH_OOS_T12_REGIME_GENERALIZATION_REQUIRED",
        ),
    ),
    _row(
        "T13",
        CiboCalibrationState.CALIBRATION_UNAVAILABLE,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (
            _PHASE19_WFO,
            _PHASE20_CONTRACT,
            "phase20:t13:causal-reserve-pressure-population",
            "phase20:t13:one-minimum-seed-shadow-preregistration",
            "phase20:t13:append-only-shadow-decision-ledger",
            "phase20:t13:causal-shadow-treatment-allocation",
            "phase20:t13:append-only-shadow-treatment-ledger",
            "phase20:t13:fresh-oos-readiness-audit",
            "phase20:t13:pre-outcome-runtime-shadow-composition",
            _PHASE19_NON_PROMOTION,
        ),
        (
            "ZERO_WALK_FORWARD_POLICY_SURVIVORS",
            "FORWARD_T13_RESERVE_PRESSURE_POPULATION_AUDIT_IMPLEMENTED",
            "T13_ONE_MINIMUM_SEED_SHADOW_POLICY_PREREGISTERED",
            "T13_APPEND_ONLY_SHADOW_DECISION_LEDGER_IMPLEMENTED",
            "T13_CAUSAL_SHADOW_TREATMENT_ALLOCATOR_IMPLEMENTED",
            "T13_APPEND_ONLY_SHADOW_TREATMENT_LEDGER_IMPLEMENTED",
            "T13_FRESH_OOS_READINESS_AUDIT_IMPLEMENTED",
            "T13_PRE_OUTCOME_RUNTIME_SHADOW_COMPOSITION_IMPLEMENTED",
            "PREREGISTERED_T13_SHADOW_POLICY_NOT_EMPIRICALLY_IDENTIFIED",
            "NO_ROBUST_DRAWDOWN_RESERVE_POLICY_IDENTIFIED",
            "FRESH_OOS_T13_RESERVE_UTILITY_REQUIRED",
        ),
    ),
    _row(
        "T14",
        CiboCalibrationState.CALIBRATION_UNAVAILABLE,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (
            _PHASE18,
            _PHASE19,
            _PHASE20_CONTRACT,
            "phase20:t14:forward-path-readiness",
            "phase20:t14:natural-trader-intervention-population",
            _PHASE19_NON_PROMOTION,
        ),
        (
            "NO_POST_ENTRY_DERISK_EVENT_POPULATION_IN_BURNED_EVIDENCE",
            "CAPACITY_STRESS_EXPRESSES_ENTRY_REJECTION_NOT_OPEN_POSITION_REDUCTION",
            "FORWARD_POST_ENTRY_PATH_READINESS_AUDIT_IMPLEMENTED",
            "TRADER_OWNED_NATURAL_INTERVENTION_POPULATION_AUDIT_IMPLEMENTED",
            "PASSIVE_MANAGEMENT_TELEMETRY_EXCLUDED_FROM_T14_INTERVENTIONS",
            "PHYSICAL_STOP_OR_VOLUME_TRANSITION_REQUIRED_FOR_T14_INTERVENTION",
            "FORWARD_PATH_SAMPLE_DOES_NOT_IDENTIFY_CAUSAL_DERISK_POLICY",
            "FRESH_OOS_DERISK_UTILITY_ANALYSIS_REQUIRED",
        ),
    ),
    _row(
        "T15",
        CiboCalibrationState.CALIBRATION_UNAVAILABLE,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (
            _PHASE19,
            _PHASE20_CONTRACT,
            "phase20:t15:known-option-realization",
            "phase20:t15:sealed-mpc-reservation-binding",
            _PHASE19_NON_PROMOTION,
        ),
        (
            "OPTIONALITY_VALUE_NOT_CAUSALLY_IDENTIFIED",
            "FORWARD_KNOWN_OPTION_REALIZATION_AUDIT_IMPLEMENTED",
            "SEALED_MPC_KNOWN_OPTION_RESERVATION_BINDING_AUDIT_IMPLEMENTED",
            "RESERVATION_PROVENANCE_DOES_NOT_PROVE_COUNTERFACTUAL_EFFECT",
            "COUNTERFACTUAL_RESERVATION_CAUSAL_EFFECT_NOT_IDENTIFIED",
            "FRESH_OOS_OPTIONALITY_UTILITY_ANALYSIS_REQUIRED",
            "NO_ROBUST_OPTIONALITY_POLICY_IDENTIFIED",
        ),
    ),
    _row(
        "T16",
        CiboCalibrationState.FAIL_CLOSED,
        CiboCalibrationType.ECONOMIC,
        (_PROVIDER_GAP, _PHASE20_CONTRACT),
        (
            "CERTIFIED_HEDGE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE",
            "HEDGE_COST_AND_BASIS_ECONOMICS_NOT_CERTIFIED",
        ),
        provider=True,
    ),
    _row(
        "T17",
        CiboCalibrationState.FAIL_CLOSED,
        CiboCalibrationType.ECONOMIC,
        (_PROVIDER_GAP, _PHASE20_CONTRACT),
        (
            "CERTIFIED_LIMITED_DOWNSIDE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE",
            "PRICING_SETTLEMENT_EXECUTION_NOT_CERTIFIED",
        ),
        provider=True,
    ),
    _row(
        "T18",
        CiboCalibrationState.CALIBRATION_UNAVAILABLE,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (
            _PHASE19,
            _PHASE19_WFO,
            _PHASE19L_COMPETITION,
            _PHASE20_CONTRACT,
            "phase20:t09-t18:fresh-scarcity-readiness-audit",
            _PHASE19_NON_PROMOTION,
        ),
        (
            "ZERO_WALK_FORWARD_POLICY_SURVIVORS",
            "FRESH_CROSS_TRADER_SCARCITY_OOS_READINESS_AUDIT_IMPLEMENTED",
            "FROZEN_PHASE20D_CROSS_TRADER_SCARCITY_UTILITY_ANALYSIS_IMPLEMENTED",
            "NO_ROBUST_CROSS_TRADER_ALLOCATION_POLICY_IDENTIFIED",
            "BURNED_EXACT_DECISION_COMPETITION_EPOCHS_0_OF_30",
            "FRESH_FORWARD_EXACT_COMPETITION_EPOCHS_MIN_30_REQUIRED",
            "FRESH_OOS_SCARCITY_GENERALIZATION_REQUIRED",
        ),
    ),
    _row(
        "T19",
        CiboCalibrationState.CALIBRATED_CAUSAL,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (_PHASE19, _PHASE20_CONTRACT),
        ("INCREMENTAL_RESERVATION_UTILITY_REQUIRES_FRESH_OOS",),
        calibration_artifact_sha256=burned_lifecycle_calibration_sha256(),
    ),
    _row(
        "T20",
        CiboCalibrationState.CALIBRATED_CAUSAL,
        CiboCalibrationType.CAUSAL_NORMALIZED,
        (_PHASE19, _PHASE20_CONTRACT),
        ("INCREMENTAL_RELEASE_UTILITY_REQUIRES_FRESH_OOS",),
        calibration_artifact_sha256=burned_lifecycle_calibration_sha256(),
    ),
)


def calibration_record(tool_code: str) -> CiboToolCalibrationRecord:
    matches = tuple(
        row
        for row in CIBO_TOOL_CALIBRATION_REGISTRY
        if row.tool_code == tool_code
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "calibration registry must contain exactly one tool record"
        )
    return matches[0]


def calibration_registry_complete() -> bool:
    canonical = tuple(f"T{index:02d}" for index in range(1, 21))
    return tuple(
        row.tool_code for row in CIBO_TOOL_CALIBRATION_REGISTRY
    ) == canonical


def all_tools_ready_for_fresh_oos() -> bool:
    return calibration_registry_complete() and all(
        row.oos_ready for row in CIBO_TOOL_CALIBRATION_REGISTRY
    )
