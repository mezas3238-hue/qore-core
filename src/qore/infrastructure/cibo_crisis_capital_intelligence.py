"""GEN-C12 crisis / extreme-regime capital intelligence.

GEN-C12 composes existing CIBO regime selection and T14 dynamic de-risking.
It does not replace sovereign Risk, change Trader methodology or execute broker
mutations. It determines only a research/shadow capital-response envelope from
current causal evidence.

No LIVE, real-capital, sizing, Risk or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_account_capital_mission import (
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10ObservedCapitalTwin,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_dynamic_derisking import (
    CiboDeRiskAction,
    CiboDeRiskingDecision,
    CiboDeRiskingInput,
    plan_dynamic_derisking,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimePosture,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    select_ce2i_tools_for_regime,
)

GENC12_POLICY_ID = "CIBO_GENC12_CRISIS_CAPITAL_INTELLIGENCE_V1"
GENC12_FROZEN_AT = datetime(2026, 9, 30, 7, 45, tzinfo=UTC)
GENC12_POLICY_SHA256 = (
    "sha256:0a681561b84ffcc681674a37e93ca5629ae69b0ad8765c7f16cf05a155795d49"
)


class Genc12CrisisFactor(StrEnum):
    LIQUIDITY_STRESS = "LIQUIDITY_STRESS"
    VOLATILITY_DISLOCATION = "VOLATILITY_DISLOCATION"
    CORRELATION_CONVERGENCE = "CORRELATION_CONVERGENCE"
    PROVIDER_DEGRADATION = "PROVIDER_DEGRADATION"
    MARGIN_EXPANSION = "MARGIN_EXPANSION"
    DRAWDOWN_ACCELERATION = "DRAWDOWN_ACCELERATION"
    CAPITAL_LOCKUP = "CAPITAL_LOCKUP"
    COMPOUND_GIVEBACK = "COMPOUND_GIVEBACK"
    SIMULTANEOUS_LOSS_CLUSTER = "SIMULTANEOUS_LOSS_CLUSTER"
    EXTREME_OPPORTUNITY = "EXTREME_OPPORTUNITY"


class Genc12CapitalResponse(StrEnum):
    NO_NEW_DEPLOYMENT = "NO_NEW_DEPLOYMENT"
    MINIMAL_SEED_ELIGIBLE = "MINIMAL_SEED_ELIGIBLE"
    RESERVE_CAPACITY = "RESERVE_CAPACITY"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"
    RELEASE_CAPACITY = "RELEASE_CAPACITY"
    SELECTIVE_EXPANSION_ELIGIBLE = "SELECTIVE_EXPANSION_ELIGIBLE"


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"GEN-C12 {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"GEN-C12 {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class Genc12CrisisFact:
    factor: Genc12CrisisFactor
    observed_at: datetime
    evidence_sha256: str
    active: bool
    future_outcome_present: bool = False
    market_probability_claimed: bool = False

    def __post_init__(self) -> None:
        if type(self.factor) is not Genc12CrisisFactor:
            raise CiboCapitalManagementError(
                "GEN-C12 crisis factor is invalid"
            )
        _aware(self.observed_at, "crisis fact observed_at")
        _sha(self.evidence_sha256, "crisis fact evidence_sha256")
        if type(self.active) is not bool:
            raise CiboCapitalManagementError(
                "GEN-C12 crisis fact active must be bool"
            )
        if self.future_outcome_present or self.market_probability_claimed:
            raise CiboCapitalManagementError(
                "GEN-C12 crisis fact cannot use future/probability claims"
            )


@dataclass(frozen=True, slots=True)
class Genc12PositionCapitalInput:
    signal_fingerprint: str
    evidence: CiboDeRiskingInput

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "GEN-C12 position signal identity is required"
            )
        if not isinstance(self.evidence, CiboDeRiskingInput):
            raise CiboCapitalManagementError(
                "GEN-C12 position requires canonical T14 evidence"
            )


@dataclass(frozen=True, slots=True)
class Genc12PositionCapitalPlan:
    signal_fingerprint: str
    decision: CiboDeRiskingDecision

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "GEN-C12 position plan identity is required"
            )
        if not isinstance(self.decision, CiboDeRiskingDecision):
            raise CiboCapitalManagementError(
                "GEN-C12 position plan must use T14 decision"
            )


@dataclass(frozen=True, slots=True)
class Genc12CrisisCapitalPlan:
    plan_id: str
    evaluated_at: datetime
    twin_id: str
    posture: CiboRegimePosture
    active_factors: tuple[Genc12CrisisFactor, ...]
    enabled_ce2i_tools: tuple[str, ...]
    blocked_ce2i_tools: tuple[str, ...]
    responses: tuple[Genc12CapitalResponse, ...]
    position_plans: tuple[Genc12PositionCapitalPlan, ...]
    policy_id: str = GENC12_POLICY_ID
    policy_sha256: str = GENC12_POLICY_SHA256
    frozen_at: datetime = GENC12_FROZEN_AT
    trader_methodology_changed: bool = False
    risk_boundary_overridden: bool = False
    market_probability_claimed: bool = False
    future_outcome_used: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.plan_id or not self.twin_id:
            raise CiboCapitalManagementError(
                "GEN-C12 plan identity is required"
            )
        _aware(self.evaluated_at, "evaluated_at")
        _aware(self.frozen_at, "frozen_at")
        # frozen_at is policy-version metadata, not an availability gate on
        # historical causal evaluation timestamps.
        if self.policy_id != GENC12_POLICY_ID:
            raise CiboCapitalManagementError(
                "GEN-C12 policy identity drift"
            )
        if self.policy_sha256 != GENC12_POLICY_SHA256:
            raise CiboCapitalManagementError(
                "GEN-C12 policy digest drift"
            )
        if type(self.posture) is not CiboRegimePosture:
            raise CiboCapitalManagementError(
                "GEN-C12 posture is invalid"
            )
        if len(self.active_factors) != len(set(self.active_factors)):
            raise CiboCapitalManagementError(
                "GEN-C12 active factors must be unique"
            )
        if len(self.responses) != len(set(self.responses)):
            raise CiboCapitalManagementError(
                "GEN-C12 responses must be unique"
            )
        signals = tuple(item.signal_fingerprint for item in self.position_plans)
        if len(signals) != len(set(signals)):
            raise CiboCapitalManagementError(
                "GEN-C12 position plans must be unique"
            )
        if (
            self.trader_methodology_changed
            or self.risk_boundary_overridden
            or self.market_probability_claimed
            or self.future_outcome_used
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "GEN-C12 plan governance drift"
            )


def plan_genc12_crisis_capital(
    *,
    plan_id: str,
    evaluated_at: datetime,
    twin: Genc10ObservedCapitalTwin,
    regime_state: CiboCapitalRegimeState,
    crisis_facts: tuple[Genc12CrisisFact, ...],
    positions: tuple[Genc12PositionCapitalInput, ...] = (),
) -> Genc12CrisisCapitalPlan:
    """Compose T12/T14 into a non-authoritative crisis capital envelope."""

    if not plan_id:
        raise CiboCapitalManagementError("GEN-C12 plan_id is required")
    _aware(evaluated_at, "evaluated_at")
    if not isinstance(twin, Genc10ObservedCapitalTwin):
        raise CiboCapitalManagementError(
            "GEN-C12 requires canonical GEN-C10 twin"
        )
    if twin.captured_at > evaluated_at:
        raise CiboCapitalManagementError(
            "GEN-C12 twin comes from the future"
        )
    if not isinstance(regime_state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "GEN-C12 regime state is invalid"
        )
    if any(
        not isinstance(item, Genc12CrisisFact)
        for item in crisis_facts
    ):
        raise CiboCapitalManagementError(
            "GEN-C12 crisis facts are invalid"
        )
    if any(item.observed_at > evaluated_at for item in crisis_facts):
        raise CiboCapitalManagementError(
            "GEN-C12 crisis fact comes from the future"
        )
    factor_ids = tuple(item.factor for item in crisis_facts)
    if len(factor_ids) != len(set(factor_ids)):
        raise CiboCapitalManagementError(
            "GEN-C12 crisis factors must be unique"
        )
    if any(
        not isinstance(item, Genc12PositionCapitalInput)
        for item in positions
    ):
        raise CiboCapitalManagementError(
            "GEN-C12 position inputs are invalid"
        )
    signals = tuple(item.signal_fingerprint for item in positions)
    if len(signals) != len(set(signals)):
        raise CiboCapitalManagementError(
            "GEN-C12 position input signals must be unique"
        )

    expected_risk = _utilization(
        twin.used_stop_risk_usd,
        twin.total_stop_risk_capacity_usd,
    )
    expected_margin = _utilization(
        twin.used_margin_usd,
        twin.total_margin_capacity_usd,
    )
    if regime_state.risk_utilization != expected_risk:
        raise CiboCapitalManagementError(
            "GEN-C12 regime risk utilization differs from Digital Twin"
        )
    if regime_state.margin_utilization != expected_margin:
        raise CiboCapitalManagementError(
            "GEN-C12 regime margin utilization differs from Digital Twin"
        )
    _require_regime_fact_coverage(regime_state, crisis_facts)

    mission = derive_cibo_capital_mission(twin.account_identity)
    selection = select_ce2i_tools_for_regime(
        mission=mission,
        state=regime_state,
    )
    enabled = set(selection.enabled_tools)
    position_plans = (
        tuple(
            Genc12PositionCapitalPlan(
                signal_fingerprint=item.signal_fingerprint,
                decision=plan_dynamic_derisking(item.evidence),
            )
            for item in positions
        )
        if "T14" in enabled
        else ()
    )
    responses = _responses(
        enabled=enabled,
        position_plans=position_plans,
    )
    active_factors = tuple(
        sorted(
            (item.factor for item in crisis_facts if item.active),
            key=lambda item: item.value,
        )
    )
    return Genc12CrisisCapitalPlan(
        plan_id=plan_id,
        evaluated_at=evaluated_at,
        twin_id=twin.twin_id,
        posture=selection.posture,
        active_factors=active_factors,
        enabled_ce2i_tools=selection.enabled_tools,
        blocked_ce2i_tools=selection.blocked_tools,
        responses=responses,
        position_plans=position_plans,
        trader_methodology_changed=False,
        risk_boundary_overridden=False,
        market_probability_claimed=False,
        future_outcome_used=False,
        productive_authority=False,
        certification_ready=False,
    )


def _utilization(used: Decimal, total: Decimal) -> Decimal:
    if total == 0:
        return Decimal(0)
    return used / total


def _require_regime_fact_coverage(
    state: CiboCapitalRegimeState,
    facts: tuple[Genc12CrisisFact, ...],
) -> None:
    active = {item.factor for item in facts if item.active}
    required: set[Genc12CrisisFactor] = set()
    if state.liquidity is LiquidityState.STRESSED:
        required.add(Genc12CrisisFactor.LIQUIDITY_STRESS)
    if state.volatility is VolatilityState.DISLOCATED:
        required.add(Genc12CrisisFactor.VOLATILITY_DISLOCATION)
    if state.correlation is CorrelationState.BREAK:
        required.add(Genc12CrisisFactor.CORRELATION_CONVERGENCE)
    if state.provider_condition in {
        ProviderCondition.DEGRADED,
        ProviderCondition.UNAVAILABLE,
    }:
        required.add(Genc12CrisisFactor.PROVIDER_DEGRADATION)
    missing = required - active
    if missing:
        raise CiboCapitalManagementError(
            "GEN-C12 regime crisis state lacks matching evidence facts"
        )


def _responses(
    *,
    enabled: set[str],
    position_plans: tuple[Genc12PositionCapitalPlan, ...],
) -> tuple[Genc12CapitalResponse, ...]:
    responses: set[Genc12CapitalResponse] = set()
    if "T01" in enabled:
        responses.add(Genc12CapitalResponse.MINIMAL_SEED_ELIGIBLE)
    if "T13" in enabled:
        responses.add(Genc12CapitalResponse.RESERVE_CAPACITY)
    if "T20" in enabled:
        responses.add(Genc12CapitalResponse.RELEASE_CAPACITY)
    expansion_tools = {"T06", "T07", "T09", "T18"}
    if enabled & expansion_tools:
        responses.add(Genc12CapitalResponse.SELECTIVE_EXPANSION_ELIGIBLE)
    if any(
        item.decision.action
        in {CiboDeRiskAction.REDUCE, CiboDeRiskAction.RELEASE_ALL}
        for item in position_plans
    ):
        responses.add(Genc12CapitalResponse.REDUCE_EXPOSURE)
    if "T01" not in enabled and not (enabled & expansion_tools):
        responses.add(Genc12CapitalResponse.NO_NEW_DEPLOYMENT)
    return tuple(sorted(responses, key=lambda item: item.value))
