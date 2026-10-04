"""Universal non-certifying Capital Science runtime bridge for Trader Lab.

This module connects mandatory GEN-C capabilities to the chronological economic
replay without granting sizing, Risk, execution, broker, LIVE or production
authority.  It is intentionally conservative: every capability is invoked at
its legal stage, may change only the lab's *eligibility* for incremental
compound capital, and QORE Risk remains sovereign for every request that
survives the bridge.

The bridge is for NON_CERTIFYING_BURNED_ADAPTIVE_RESEARCH.  It does not create
Fresh-OOS evidence and it never uses the outcome of the opportunity currently
being decided.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from enum import StrEnum

from qore.infrastructure.account_wide_risk import canonical_trader_lineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_adaptive_compound_speed_shadow import (
    Genc8AdaptiveSpeedFact,
    Genc8FactKind,
    Genc8RegimeEvidence,
    Genc8Severity,
    Genc8SpeedPosture,
    evaluate_genc8_adaptive_compound_speed,
)
from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10EconomicBucket,
    Genc10KnownCapitalOption,
    Genc10ObservedCapitalTwin,
    Genc10WorldKind,
    Genc10WorldScenario,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
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
from qore.infrastructure.cibo_compound_capital import (
    CompoundCapitalState,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_floor import ProtectedCapitalFloorLedger
from qore.infrastructure.cibo_compound_portfolio_ledger import CompoundPortfolioLedger
from qore.infrastructure.cibo_core_compound_portfolio import (
    AccountCoreCompoundPortfolio,
)
from qore.infrastructure.cibo_crisis_capital_intelligence import (
    Genc12CapitalResponse,
    Genc12CrisisFact,
    Genc12CrisisFactor,
    Genc12PositionCapitalInput,
    plan_genc12_crisis_capital,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
)
from qore.infrastructure.cibo_multi_period_capital_mpc import (
    Genc11KnownOptionSchedule,
    Genc11WorldPath,
    Genc11WorldStep,
    plan_genc11_multi_period_capital,
)
from qore.infrastructure.cibo_profit_preservation_shadow import (
    Genc7Action,
    Genc7CapitalStateEvidence,
    Genc7PreservationProposalEvidence,
    evaluate_genc7_profit_preservation_shadow,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    Genc5SequentialCompoundingShadowDecision,
    SequentialCompoundShadowAction,
    evaluate_genc5_sequential_compounding_shadow,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    Genc5ShadowDecisionSeal,
    genc5_shadow_decision_sha256,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

RESEARCH_MODE = "NON_CERTIFYING_BURNED_ADAPTIVE_RESEARCH"
MANDATORY_RUNTIME_GENC = (
    "GEN-C1",
    "GEN-C2",
    "GEN-C3",
    "GEN-C4",
    "GEN-C5",
    "GEN-C6",
    "GEN-C7",
    "GEN-C8",
    "GEN-C9",
    "GEN-C10",
    "GEN-C11",
    "GEN-C12",
    "GEN-C13",
    "GEN-C14",
)


class CapitalScienceDisposition(StrEnum):
    APPLIED = "APPLIED"
    ELIGIBLE_NO_CHANGE = "ELIGIBLE_NO_CHANGE"
    FAIL_CLOSED = "FAIL_CLOSED"
    JUSTIFIED_NOT_APPLICABLE = "JUSTIFIED_NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class CapitalScienceKnownOpportunity:
    """One opportunity already knowable at the current decision epoch."""

    option_id: str
    trader_id: str
    qore_symbol: str
    known_at: datetime
    earliest_action_at: datetime
    expires_at: datetime
    requested_capital_usd: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    evidence_sha256: str
    expected_net_value_usd: Decimal = Decimal(0)
    expected_capital_minutes: Decimal = Decimal(1)

    def __post_init__(self) -> None:
        if not self.option_id or not self.trader_id or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "Capital Science known opportunity identity is required"
            )
        for name in ("known_at", "earliest_action_at", "expires_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"Capital Science known opportunity {name} must be timezone-aware"
                )
        if self.earliest_action_at < self.known_at or self.expires_at <= self.known_at:
            raise CiboCapitalManagementError(
                "Capital Science known opportunity time ordering is invalid"
            )
        for name in ("requested_capital_usd", "stop_risk_usd", "margin_usd"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise CiboCapitalManagementError(
                    f"Capital Science known opportunity {name} must be positive Decimal"
                )
        if (
            not isinstance(self.expected_net_value_usd, Decimal)
            or not self.expected_net_value_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "Capital Science known opportunity expected_net_value_usd must be finite Decimal"
            )
        if (
            not isinstance(self.expected_capital_minutes, Decimal)
            or not self.expected_capital_minutes.is_finite()
            or self.expected_capital_minutes <= 0
        ):
            raise CiboCapitalManagementError(
                "Capital Science known opportunity expected_capital_minutes must be positive Decimal"
            )
        if not self.evidence_sha256.startswith("sha256:") or len(self.evidence_sha256) != 71:
            raise CiboCapitalManagementError(
                "Capital Science known opportunity evidence digest is invalid"
            )

    def payload(self) -> dict[str, object]:
        return {
            "option_id": self.option_id,
            "trader_id": self.trader_id,
            "qore_symbol": self.qore_symbol,
            "known_at": self.known_at.isoformat(),
            "earliest_action_at": self.earliest_action_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "requested_capital_usd": format(self.requested_capital_usd, "f"),
            "stop_risk_usd": format(self.stop_risk_usd, "f"),
            "margin_usd": format(self.margin_usd, "f"),
            "expected_net_value_usd": format(self.expected_net_value_usd, "f"),
            "expected_capital_minutes": format(self.expected_capital_minutes, "f"),
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class CapitalSciencePredecisionInput:
    decision_epoch_id: str
    signal_fingerprint: str
    trader_id: str
    decision_at: datetime
    realized_capital_usd: Decimal
    peak_realized_capital_usd: Decimal
    realized_profit_pool_usd: Decimal
    protected_capacity_usd: Decimal
    open_stop_risk_usd: Decimal
    open_margin_usd: Decimal
    requested_stop_risk_usd: Decimal
    requested_margin_usd: Decimal
    provider_cost_usd: Decimal
    expected_net_value_usd: Decimal
    expected_capital_minutes: Decimal
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal
    competing_candidates: int
    deployed_profit_usd: Decimal = Decimal(0)
    capital_source: str = "REALIZED_PROFIT"
    qore_symbol: str = "UNSPECIFIED"
    account_identity: CiboAccountCapitalIdentity | None = None
    regime_state: CiboCapitalRegimeState | None = None
    known_simultaneous_opportunities: tuple[CapitalScienceKnownOpportunity, ...] = ()
    open_positions: tuple[Genc12PositionCapitalInput, ...] = ()
    genc7_proposal: Genc7PreservationProposalEvidence | None = None

    def __post_init__(self) -> None:
        if (
            not self.decision_epoch_id
            or not self.signal_fingerprint
            or not self.trader_id
            or not self.qore_symbol
        ):
            raise CiboCapitalManagementError("Capital Science predecision identity is required")
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError("Capital Science decision_at must be timezone-aware")
        nonnegative = (
            "realized_capital_usd",
            "peak_realized_capital_usd",
            "realized_profit_pool_usd",
            "protected_capacity_usd",
            "deployed_profit_usd",
            "open_stop_risk_usd",
            "open_margin_usd",
            "requested_stop_risk_usd",
            "requested_margin_usd",
            "provider_cost_usd",
            "expected_capital_minutes",
            "hard_risk_headroom_usd",
            "margin_headroom_usd",
        )
        for name in nonnegative:
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"Capital Science {name} must be finite non-negative Decimal"
                )
        if (
            not isinstance(self.expected_net_value_usd, Decimal)
            or not self.expected_net_value_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "Capital Science expected_net_value_usd must be finite Decimal"
            )
        if self.peak_realized_capital_usd < self.realized_capital_usd:
            raise CiboCapitalManagementError(
                "Capital Science realized-capital peak cannot be below current"
            )
        if self.protected_capacity_usd > self.realized_profit_pool_usd:
            raise CiboCapitalManagementError(
                "Capital Science protected capacity cannot exceed realized-profit pool"
            )
        if (
            self.protected_capacity_usd + self.deployed_profit_usd
            > self.realized_profit_pool_usd
        ):
            raise CiboCapitalManagementError(
                "Capital Science protected plus deployed profit cannot exceed "
                "realized-profit pool"
            )
        if (
            not isinstance(self.competing_candidates, int)
            or isinstance(self.competing_candidates, bool)
            or self.competing_candidates < 0
        ):
            raise CiboCapitalManagementError(
                "Capital Science competing_candidates must be non-negative int"
            )
        if not self.capital_source:
            raise CiboCapitalManagementError("Capital Science capital_source is required")
        if self.account_identity is not None and not isinstance(
            self.account_identity, CiboAccountCapitalIdentity
        ):
            raise CiboCapitalManagementError("Capital Science account_identity must be canonical")
        if self.regime_state is not None and not isinstance(
            self.regime_state, CiboCapitalRegimeState
        ):
            raise CiboCapitalManagementError("Capital Science regime_state must be canonical")
        if any(
            not isinstance(item, CapitalScienceKnownOpportunity)
            for item in self.known_simultaneous_opportunities
        ):
            raise CiboCapitalManagementError(
                "Capital Science known opportunities must be canonical"
            )
        option_ids = tuple(item.option_id for item in self.known_simultaneous_opportunities)
        if len(option_ids) != len(set(option_ids)):
            raise CiboCapitalManagementError("Capital Science known opportunity ids must be unique")
        if any(item.known_at > self.decision_at for item in self.known_simultaneous_opportunities):
            raise CiboCapitalManagementError(
                "Capital Science cannot consume future-known opportunities"
            )
        if any(not isinstance(item, Genc12PositionCapitalInput) for item in self.open_positions):
            raise CiboCapitalManagementError(
                "Capital Science open positions must be canonical T14 inputs"
            )
        if self.genc7_proposal is not None:
            if not isinstance(
                self.genc7_proposal,
                Genc7PreservationProposalEvidence,
            ):
                raise CiboCapitalManagementError(
                    "Capital Science GEN-C7 proposal must be canonical"
                )
            if self.genc7_proposal.decision_at != self.decision_at:
                raise CiboCapitalManagementError(
                    "Capital Science GEN-C7 proposal decision time drift"
                )

    @property
    def deployable_profit_usd(self) -> Decimal:
        with localcontext() as context:
            context.prec = 80
            return max(
                Decimal(0),
                self.realized_profit_pool_usd
                - self.protected_capacity_usd
                - self.deployed_profit_usd,
            )

    @property
    def giveback_usd(self) -> Decimal:
        with localcontext() as context:
            context.prec = 80
            return self.peak_realized_capital_usd - self.realized_capital_usd

    def payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["decision_at"] = self.decision_at.isoformat()
        payload["account_identity"] = (
            {
                "provider_key": self.account_identity.provider_key,
                "account_ref": self.account_identity.account_ref,
                "environment": self.account_identity.environment.value,
                "provider_program": self.account_identity.provider_program,
            }
            if self.account_identity is not None
            else None
        )
        payload["regime_state"] = (
            {
                "liquidity": self.regime_state.liquidity.value,
                "volatility": self.regime_state.volatility.value,
                "correlation": self.regime_state.correlation.value,
                "provider_condition": self.regime_state.provider_condition.value,
                "risk_utilization": format(self.regime_state.risk_utilization, "f"),
                "margin_utilization": format(self.regime_state.margin_utilization, "f"),
                "drawdown_utilization": format(self.regime_state.drawdown_utilization, "f"),
                "opportunity_count": self.regime_state.opportunity_count,
                "position_path_adverse": self.regime_state.position_path_adverse,
                "evidence_stale": self.regime_state.evidence_stale,
            }
            if self.regime_state is not None
            else None
        )
        payload["known_simultaneous_opportunities"] = [
            item.payload() for item in self.known_simultaneous_opportunities
        ]
        payload["open_positions"] = [
            {
                "signal_fingerprint": item.signal_fingerprint,
                "evidence_sha256": _runtime_sha("t14-position-input", asdict(item.evidence)),
            }
            for item in self.open_positions
        ]
        payload["genc7_proposal"] = (
            {
                "proposal_id": self.genc7_proposal.proposal_id,
                "action": self.genc7_proposal.action.value,
                "source_bucket": self.genc7_proposal.source_bucket.value,
                "amount_usd": format(self.genc7_proposal.amount_usd, "f"),
                "evidence_sha256": self.genc7_proposal.evidence_sha256,
                "rationale_code": self.genc7_proposal.rationale_code,
                "evaluation_horizon_minutes": (
                    self.genc7_proposal.evaluation_horizon_minutes
                ),
                "calibrated": self.genc7_proposal.calibrated,
                "capital_eligible": self.genc7_proposal.capital_eligible,
            }
            if self.genc7_proposal is not None
            else None
        )
        for key, value in tuple(payload.items()):
            if isinstance(value, Decimal):
                payload[key] = format(value, "f")
        return payload

    def fingerprint(self) -> str:
        raw = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CapitalScienceReceipt:
    call_id: str
    function_code: str
    stage: str
    disposition: CapitalScienceDisposition
    decision_epoch_id: str
    signal_fingerprint: str
    trader_id: str
    qore_symbol: str
    observed_at: datetime
    market_time: datetime
    reason: str
    downstream_consumer: str
    consumer_action: str
    decision_changed: bool = False
    risk_delta_usd: Decimal = Decimal(0)
    margin_delta_usd: Decimal = Decimal(0)
    capital_source_usage: tuple[str, ...] = ()
    incremental_pnl_attribution_usd: Decimal = Decimal(0)
    input_sha256: str = ""
    output_sha256: str = ""
    input_payload: dict[str, object] | None = None
    output_payload: dict[str, object] | None = None
    outcome_used_for_same_decision: bool = False
    qore_risk_bypassed: bool = False
    productive_authority: bool = False
    native_engine_called: bool = False
    native_engine_name: str | None = None

    def __post_init__(self) -> None:
        if self.function_code not in MANDATORY_RUNTIME_GENC:
            raise CiboCapitalManagementError(
                "Capital Science receipt function code is not mandatory runtime GEN-C"
            )
        if not self.stage or not self.reason or not self.downstream_consumer:
            raise CiboCapitalManagementError(
                "Capital Science receipt stage/reason/consumer is required"
            )
        if (
            not self.call_id
            or not self.decision_epoch_id
            or not self.signal_fingerprint
            or not self.trader_id
            or not self.qore_symbol
        ):
            raise CiboCapitalManagementError("Capital Science receipt identity is required")
        for name in ("observed_at", "market_time"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"Capital Science receipt {name} must be timezone-aware"
                )
        for name in (
            "risk_delta_usd",
            "margin_delta_usd",
            "incremental_pnl_attribution_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Capital Science receipt {name} must be finite Decimal"
                )
        if len(self.capital_source_usage) != len(set(self.capital_source_usage)):
            raise CiboCapitalManagementError("Capital Science capital-source usage must be unique")
        for name in (
            "decision_changed",
            "outcome_used_for_same_decision",
            "qore_risk_bypassed",
            "productive_authority",
            "native_engine_called",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"Capital Science receipt {name} must be bool")
        if (
            self.outcome_used_for_same_decision
            or self.qore_risk_bypassed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Capital Science receipt violates causal/authority boundary"
            )
        if not self.input_sha256.startswith("sha256:"):
            raise CiboCapitalManagementError("Capital Science receipt input_sha256 is required")
        if not self.output_sha256.startswith("sha256:"):
            raise CiboCapitalManagementError("Capital Science receipt output_sha256 is required")
        if not isinstance(self.input_payload, dict) or not self.input_payload:
            raise CiboCapitalManagementError("Capital Science receipt input_payload is required")
        if not isinstance(self.output_payload, dict) or not self.output_payload:
            raise CiboCapitalManagementError("Capital Science receipt output_payload is required")
        engine_output = self.output_payload.get("engine_output")
        if self.native_engine_called:
            if not self.native_engine_name:
                raise CiboCapitalManagementError(
                    "Capital Science native invocation requires engine name"
                )
            if (
                not isinstance(engine_output, dict)
                or engine_output.get("engine") != self.native_engine_name
            ):
                raise CiboCapitalManagementError(
                    "Capital Science native invocation lacks matching typed output"
                )
        elif self.native_engine_name is not None:
            raise CiboCapitalManagementError(
                "Capital Science cannot name a native engine that was not called"
            )

    def payload(self) -> dict[str, object]:
        return {
            "call_id": self.call_id,
            "function_code": self.function_code,
            "stage": self.stage,
            "disposition": self.disposition.value,
            "decision_epoch_id": self.decision_epoch_id,
            "signal_fingerprint": self.signal_fingerprint,
            "trader_id": self.trader_id,
            "qore_symbol": self.qore_symbol,
            "observed_at": self.observed_at.isoformat(),
            "market_time": self.market_time.isoformat(),
            "reason": self.reason,
            "downstream_consumer": self.downstream_consumer,
            "consumer_action": self.consumer_action,
            "decision_changed": self.decision_changed,
            "risk_delta_usd": format(self.risk_delta_usd, "f"),
            "margin_delta_usd": format(self.margin_delta_usd, "f"),
            "capital_source_usage": list(self.capital_source_usage),
            "incremental_pnl_attribution_usd": format(self.incremental_pnl_attribution_usd, "f"),
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "input_payload": self.input_payload,
            "output_payload": self.output_payload,
            "outcome_used_for_same_decision": self.outcome_used_for_same_decision,
            "qore_risk_bypassed": self.qore_risk_bypassed,
            "productive_authority": self.productive_authority,
            "native_engine_called": self.native_engine_called,
            "native_engine_name": self.native_engine_name,
            "research_mode": RESEARCH_MODE,
        }


@dataclass(frozen=True, slots=True)
class CapitalScienceDirective:
    allow_incremental_compound: bool
    deployable_profit_usd: Decimal
    receipts: tuple[CapitalScienceReceipt, ...]

    def __post_init__(self) -> None:
        if type(self.allow_incremental_compound) is not bool:
            raise CiboCapitalManagementError("Capital Science directive allow flag must be bool")
        if (
            not isinstance(self.deployable_profit_usd, Decimal)
            or not self.deployable_profit_usd.is_finite()
            or self.deployable_profit_usd < 0
        ):
            raise CiboCapitalManagementError(
                "Capital Science deployable profit must be finite non-negative"
            )
        expected = {
            "GEN-C2",
            "GEN-C4",
            "GEN-C5",
            "GEN-C7",
            "GEN-C8",
            "GEN-C10",
            "GEN-C11",
            "GEN-C12",
        }
        actual = {item.function_code for item in self.receipts}
        if actual != expected:
            raise CiboCapitalManagementError(
                "Capital Science predecision bridge did not invoke exact mandatory surface"
            )


def _receipt(
    *,
    state: CapitalSciencePredecisionInput,
    function_code: str,
    disposition: CapitalScienceDisposition,
    reason: str,
    downstream_consumer: str,
    consumer_action: str,
    decision_changed: bool = False,
    risk_delta_usd: Decimal = Decimal(0),
    margin_delta_usd: Decimal = Decimal(0),
    capital_source_usage: tuple[str, ...] = (),
    output_details: dict[str, object] | None = None,
    typed_engine_input: dict[str, object] | None = None,
    native_engine_name: str | None = None,
) -> CapitalScienceReceipt:
    input_payload = state.payload()
    if typed_engine_input is not None:
        input_payload = {
            **input_payload,
            "typed_engine_input": typed_engine_input,
        }
    raw_input = json.dumps(
        input_payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    input_sha = "sha256:" + hashlib.sha256(raw_input.encode()).hexdigest()
    output: dict[str, object] = {
        "function_code": function_code,
        "disposition": disposition.value,
        "reason": reason,
        "consumer": downstream_consumer,
        "consumer_action": consumer_action,
        "decision_changed": decision_changed,
        "risk_delta_usd": format(risk_delta_usd, "f"),
        "margin_delta_usd": format(margin_delta_usd, "f"),
        "capital_source_usage": list(capital_source_usage),
        "input_sha256": input_sha,
        "engine_output": output_details or {},
    }
    raw = json.dumps(output, sort_keys=True, separators=(",", ":"))
    output_sha = "sha256:" + hashlib.sha256(raw.encode()).hexdigest()
    return CapitalScienceReceipt(
        call_id=_runtime_sha(
            "capital-science-call",
            {
                "decision_epoch_id": state.decision_epoch_id,
                "signal_fingerprint": state.signal_fingerprint,
                "function_code": function_code,
            },
        ),
        function_code=function_code,
        stage="PREDECISION",
        disposition=disposition,
        decision_epoch_id=state.decision_epoch_id,
        signal_fingerprint=state.signal_fingerprint,
        trader_id=state.trader_id,
        qore_symbol=state.qore_symbol,
        observed_at=state.decision_at,
        market_time=state.decision_at,
        reason=reason,
        downstream_consumer=downstream_consumer,
        consumer_action=consumer_action,
        decision_changed=decision_changed,
        risk_delta_usd=risk_delta_usd,
        margin_delta_usd=margin_delta_usd,
        capital_source_usage=capital_source_usage,
        incremental_pnl_attribution_usd=Decimal(0),
        input_sha256=input_sha,
        output_sha256=output_sha,
        input_payload=input_payload,
        output_payload=output,
        outcome_used_for_same_decision=False,
        qore_risk_bypassed=False,
        productive_authority=False,
        native_engine_called=native_engine_name is not None,
        native_engine_name=native_engine_name,
    )


def build_capital_science_lane_receipt(
    *,
    state: CapitalSciencePredecisionInput,
    function_code: str,
    disposition: CapitalScienceDisposition,
    reason: str,
    downstream_consumer: str,
    consumer_action: str,
    decision_changed: bool = False,
    capital_source_usage: tuple[str, ...] = (),
    output_details: dict[str, object] | None = None,
    native_engine_name: str,
) -> CapitalScienceReceipt:
    """Build an auditable lane-owned GEN-C receipt with no extra authority."""

    if function_code not in {"GEN-C1", "GEN-C3", "GEN-C6"}:
        raise CiboCapitalManagementError(
            "lane receipt helper is restricted to GEN-C1/GEN-C3/GEN-C6"
        )
    if not native_engine_name:
        raise CiboCapitalManagementError(
            "lane receipt requires an explicit native engine identity"
        )
    details = {
        "engine": native_engine_name,
        **(output_details or {}),
    }
    return _receipt(
        state=state,
        function_code=function_code,
        disposition=disposition,
        reason=reason,
        downstream_consumer=downstream_consumer,
        consumer_action=consumer_action,
        decision_changed=decision_changed,
        capital_source_usage=capital_source_usage,
        output_details=details,
        typed_engine_input=(output_details or {"function_code": function_code}),
        native_engine_name=native_engine_name,
    )


def _runtime_sha(label: str, payload: object) -> str:
    raw = json.dumps(
        {"label": label, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _runtime_identity(
    state: CapitalSciencePredecisionInput,
) -> CiboAccountCapitalIdentity:
    if state.account_identity is not None:
        return state.account_identity
    return CiboAccountCapitalIdentity(
        provider_key="trader-lab",
        account_ref="cibo-capital-science-replay",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _utilization(used: Decimal, headroom: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 80
        total = used + headroom
        if total <= 0:
            return Decimal(0)
        return min(Decimal(1), used / total)


def _drawdown_utilization(state: CapitalSciencePredecisionInput) -> Decimal:
    if state.peak_realized_capital_usd <= 0:
        return Decimal(0)
    return min(
        Decimal(1),
        state.giveback_usd / state.peak_realized_capital_usd,
    )


def _severity(value: Decimal) -> Genc8Severity:
    if value >= Decimal("0.95"):
        return Genc8Severity.CRITICAL
    if value >= Decimal("0.75"):
        return Genc8Severity.ADVERSE
    if value >= Decimal("0.50"):
        return Genc8Severity.WATCH
    return Genc8Severity.BENIGN


def _regime_state(state: CapitalSciencePredecisionInput) -> CiboCapitalRegimeState:
    if state.regime_state is not None:
        expected_risk = _utilization(
            state.open_stop_risk_usd,
            state.hard_risk_headroom_usd,
        )
        expected_margin = _utilization(
            state.open_margin_usd,
            state.margin_headroom_usd,
        )
        if abs(state.regime_state.risk_utilization - expected_risk) > Decimal("1e-24"):
            raise CiboCapitalManagementError(
                "Capital Science regime risk utilization/account state drift"
            )
        if abs(state.regime_state.margin_utilization - expected_margin) > Decimal("1e-24"):
            raise CiboCapitalManagementError(
                "Capital Science regime margin utilization/account state drift"
            )
        known_option_ids = {item.option_id for item in state.known_simultaneous_opportunities}
        if state.requested_stop_risk_usd > 0 and state.requested_margin_usd > 0:
            known_option_ids.add(state.signal_fingerprint)
        expected_opportunity_count = max(
            1,
            state.competing_candidates,
            len(known_option_ids),
        )
        if state.regime_state.opportunity_count != expected_opportunity_count:
            raise CiboCapitalManagementError(
                "Capital Science regime opportunity count/known options drift"
            )
        return replace(
            state.regime_state,
            risk_utilization=expected_risk,
            margin_utilization=expected_margin,
        )
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=_utilization(
            state.open_stop_risk_usd,
            state.hard_risk_headroom_usd,
        ),
        margin_utilization=_utilization(
            state.open_margin_usd,
            state.margin_headroom_usd,
        ),
        drawdown_utilization=_drawdown_utilization(state),
        opportunity_count=max(1, state.competing_candidates),
        position_path_adverse=state.giveback_usd > 0,
        evidence_stale=False,
    )


def _capital_twin(
    state: CapitalSciencePredecisionInput,
    *,
    identity: CiboAccountCapitalIdentity,
) -> Genc10ObservedCapitalTwin:
    profit_total = min(
        state.realized_profit_pool_usd,
        state.realized_capital_usd,
    )
    protected_profit = min(state.protected_capacity_usd, profit_total)
    deployed_profit = min(
        state.deployed_profit_usd,
        profit_total - protected_profit,
    )
    with localcontext() as context:
        context.prec = 80
        deployable_profit = profit_total - protected_profit - deployed_profit
        original_base = state.realized_capital_usd - profit_total
    buckets = tuple(
        (
            bucket,
            (
                original_base
                if bucket is Genc10EconomicBucket.ORIGINAL_BASE
                else deployable_profit
                if bucket is Genc10EconomicBucket.COMPOUNDABLE
                else deployed_profit
                if bucket is Genc10EconomicBucket.DEPLOYED_COMPOUND_CAPITAL
                else protected_profit
                if bucket is Genc10EconomicBucket.RETIRED_TO_PROTECTED_FLOOR
                else Decimal(0)
            ),
        )
        for bucket in Genc10EconomicBucket
    )
    request_capital = state.requested_stop_risk_usd + state.provider_cost_usd
    horizon_minutes = max(3, int(state.expected_capital_minutes) + 1)
    current_option = (
        CapitalScienceKnownOpportunity(
            option_id=state.signal_fingerprint,
            trader_id=state.trader_id,
            qore_symbol=state.qore_symbol,
            known_at=state.decision_at,
            earliest_action_at=state.decision_at,
            expires_at=state.decision_at + timedelta(minutes=horizon_minutes),
            requested_capital_usd=request_capital,
            stop_risk_usd=state.requested_stop_risk_usd,
            margin_usd=state.requested_margin_usd,
            evidence_sha256=_runtime_sha("known-option", state.payload()),
        )
        if request_capital > 0
        and state.requested_stop_risk_usd > 0
        and state.requested_margin_usd > 0
        else None
    )
    known_by_id = {item.option_id: item for item in state.known_simultaneous_opportunities}
    if current_option is not None:
        previous = known_by_id.get(current_option.option_id)
        if previous is not None and (
            previous.stop_risk_usd != current_option.stop_risk_usd
            or previous.margin_usd != current_option.margin_usd
            or previous.requested_capital_usd != current_option.requested_capital_usd
        ):
            raise CiboCapitalManagementError(
                "Capital Science current option geometry conflicts with epoch option set"
            )
        known_by_id[current_option.option_id] = previous or current_option
    known_options = tuple(
        Genc10KnownCapitalOption(
            option_id=item.option_id,
            known_at=item.known_at,
            earliest_action_at=item.earliest_action_at,
            expires_at=item.expires_at,
            requested_capital_usd=item.requested_capital_usd,
            stop_risk_usd=item.stop_risk_usd,
            margin_usd=item.margin_usd,
            evidence_sha256=item.evidence_sha256,
        )
        for item in sorted(known_by_id.values(), key=lambda row: row.option_id)
    )
    with localcontext() as context:
        context.prec = 80
        risk_capacity = state.open_stop_risk_usd + state.hard_risk_headroom_usd
        margin_capacity = state.open_margin_usd + state.margin_headroom_usd
    return Genc10ObservedCapitalTwin(
        twin_id=f"capital-science:{state.decision_epoch_id}:{state.signal_fingerprint}",
        account_identity=identity,
        captured_at=state.decision_at,
        capital_truth_sha256=_runtime_sha("capital-truth", state.payload()),
        compound_cycle_sha256=_runtime_sha("compound-cycle", state.payload()),
        source_ledger_sha256=_runtime_sha("source-ledger", state.payload()),
        provider_registry_sha256=_runtime_sha("provider-registry", state.payload()),
        total_realized_capital_usd=state.realized_capital_usd,
        original_base_usd=original_base,
        compound_economic_value_usd=profit_total,
        protected_floor_usd=protected_profit,
        policy_protected_floor_usd=protected_profit,
        broker_guaranteed_floor_usd=Decimal(0),
        economic_buckets=buckets,
        generation_balances=((1, profit_total),) if profit_total > 0 else (),
        source_capacities=(),
        total_stop_risk_capacity_usd=risk_capacity,
        used_stop_risk_usd=state.open_stop_risk_usd,
        stop_risk_headroom_usd=state.hard_risk_headroom_usd,
        total_margin_capacity_usd=margin_capacity,
        used_margin_usd=state.open_margin_usd,
        margin_headroom_usd=state.margin_headroom_usd,
        active_deployment_count=(
            1 if state.open_stop_risk_usd > 0 or state.open_margin_usd > 0 else 0
        ),
        provider_capability_counts=(),
        known_options=known_options,
    )


def _native_genc5_inputs(
    state: CapitalSciencePredecisionInput,
    *,
    identity: CiboAccountCapitalIdentity,
) -> tuple[AccountCoreCompoundPortfolio, MarginalCapitalUtilityEvidence, str] | None:
    """Materialize the canonical GEN-C1/C2/C4 contracts from causal state."""

    with localcontext() as context:
        context.prec = 80
        profit_total = min(
            state.realized_profit_pool_usd,
            state.realized_capital_usd,
        )
        protected_profit = min(state.protected_capacity_usd, profit_total)
        unprotected_profit = profit_total - protected_profit
        deployed_profit = min(
            state.deployed_profit_usd,
            unprotected_profit,
        )
        deployable_profit = unprotected_profit - deployed_profit
        combined_compound_capacity = unprotected_profit
        requested = state.requested_stop_risk_usd + state.provider_cost_usd
    if profit_total <= 0 or deployable_profit <= 0 or requested > deployable_profit:
        return None

    realized_at = state.decision_at - timedelta(microseconds=6)
    created_at = state.decision_at - timedelta(microseconds=5)
    prefix = _runtime_sha(
        "genc5-runtime-lineage",
        {
            "epoch": state.decision_epoch_id,
            "signal": state.signal_fingerprint,
        },
    )[7:23]
    realized_id = f"genc5-realized-{prefix}"
    evidence = CompoundRealizedProfitEvidence(
        evidence_id=f"genc5-settlement-{prefix}",
        account_identity=identity,
        origin_trader=canonical_trader_lineage(state.trader_id),
        signal_fingerprint=f"prior-realized:{state.signal_fingerprint}",
        position_id=int(prefix[:8], 16) + 1,
        settlement_deal_ids=(int(prefix[8:16], 16) + 1,),
        realized_net_profit_usd=profit_total,
        realized_at=realized_at,
        source_settlement_sha256=_runtime_sha("genc5-prior-settlement", state.payload()),
        settlement_reconciled=True,
        position_closed=True,
        floating_pnl_used_as_capital=False,
    )
    lot = create_realized_profit_lot(
        evidence,
        lot_id=realized_id,
        created_at=created_at,
    )
    ledger = CompoundPortfolioLedger(account_identity=identity).admit_realized_profit(
        lot,
        event_id=f"genc5-admit-{prefix}",
        occurred_at=created_at,
    )
    floor = ProtectedCapitalFloorLedger(account_identity=identity)
    source_id = realized_id
    transition_at = state.decision_at - timedelta(microseconds=4)
    if protected_profit > 0:
        retired_id = f"genc5-floor-{prefix}"
        remainder_id = f"genc5-deployable-source-{prefix}" if deployable_profit > 0 else None
        ledger = ledger.transition(
            source_lot_id=realized_id,
            to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
            amount_usd=protected_profit,
            moved_lot_id=retired_id,
            remainder_lot_id=remainder_id,
            event_id=f"genc5-protect-{prefix}",
            occurred_at=transition_at,
        )
        floor = floor.admit_retired_lot(
            ledger.lot(retired_id),
            tranche_id=f"genc5-tranche-{prefix}",
            event_id=f"genc5-floor-admit-{prefix}",
            admitted_at=transition_at,
        ).upgrade_to_policy_protected(
            tranche_id=f"genc5-tranche-{prefix}",
            event_id=f"genc5-floor-policy-{prefix}",
            occurred_at=state.decision_at - timedelta(microseconds=3),
            policy_id="CIBO_RUNTIME_CAUSAL_PROTECTED_CAPACITY_V1",
            policy_sha256=_runtime_sha("genc5-protected-capacity-policy", state.payload()),
        )
        source_id = remainder_id or realized_id

    compoundable_id = f"genc5-compoundable-{prefix}"
    if deployed_profit > 0:
        combined_id = f"genc5-compound-capacity-{prefix}"
        ledger = ledger.transition(
            source_lot_id=source_id,
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=combined_compound_capacity,
            moved_lot_id=combined_id,
            event_id=f"genc5-compound-capacity-event-{prefix}",
            occurred_at=state.decision_at - timedelta(microseconds=3),
        )
        active_id = f"genc5-active-{prefix}"
        ledger = ledger.transition(
            source_lot_id=combined_id,
            to_state=CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
            amount_usd=deployed_profit,
            moved_lot_id=active_id,
            remainder_lot_id=compoundable_id,
            event_id=f"genc5-active-event-{prefix}",
            occurred_at=state.decision_at - timedelta(microseconds=2),
        )
        ledger = ledger.transition(
            source_lot_id=active_id,
            to_state=CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL,
            amount_usd=deployed_profit,
            moved_lot_id=f"genc5-deployed-{prefix}",
            event_id=f"genc5-deployed-event-{prefix}",
            occurred_at=state.decision_at - timedelta(microseconds=1),
        )
    else:
        ledger = ledger.transition(
            source_lot_id=source_id,
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=deployable_profit,
            moved_lot_id=compoundable_id,
            event_id=f"genc5-compoundable-event-{prefix}",
            occurred_at=state.decision_at - timedelta(microseconds=2),
        )
    portfolio = AccountCoreCompoundPortfolio(
        account_identity=identity,
        compound_ledger=ledger,
        protected_floor_ledger=floor,
    )
    marginal = MarginalCapitalUtilityEvidence(
        evidence_id=f"genc5-marginal-{prefix}",
        decision_at=state.decision_at,
        account_identity=identity,
        trader_id=canonical_trader_lineage(state.trader_id),
        signal_fingerprint=state.signal_fingerprint,
        source_opportunity_decision_sha256=_runtime_sha("genc5-opportunity", state.payload()),
        source_baseline_policy_record_sha256=_runtime_sha("genc5-baseline-policy", state.payload()),
        current_compound_capacity_usd=deployable_profit,
        requested_incremental_capital_usd=requested,
        expected_incremental_return_usd=state.expected_net_value_usd,
        incremental_stop_risk_usd=state.requested_stop_risk_usd,
        incremental_margin_usd=state.requested_margin_usd,
        incremental_execution_cost_usd=state.provider_cost_usd,
        incremental_concentration_risk_usd=state.requested_stop_risk_usd,
        incremental_drawdown_risk_proxy_usd=state.giveback_usd,
        incremental_optionality_consumed_usd=state.requested_margin_usd,
        expected_capital_minutes=max(Decimal(1), state.expected_capital_minutes),
        epistemic_uncertainty=Decimal(1) if state.regime_state is None else Decimal(0),
        provider_evidence_sha256=_runtime_sha("genc5-provider", state.payload()),
        expectation_evidence_sha256=_runtime_sha("genc5-expectation", state.payload()),
        factor_evidence_sha256=_runtime_sha("genc5-factors", state.payload()),
        duration_evidence_sha256=_runtime_sha("genc5-duration", state.payload()),
        execution_evidence_sha256=_runtime_sha("genc5-execution", state.payload()),
        optionality_evidence_sha256=_runtime_sha("genc5-optionality", state.payload()),
    )
    return portfolio, marginal, compoundable_id


def _genc5_seal(
    decision: Genc5SequentialCompoundingShadowDecision,
) -> Genc5ShadowDecisionSeal:
    """Convert the actual native GEN-C5 result into GEN-C8's canonical seal."""

    return Genc5ShadowDecisionSeal(
        decision_sha256=genc5_shadow_decision_sha256(decision),
        policy_sha256=decision.policy_sha256,
        decision_id=decision.decision_id,
        decision_at=decision.decision_at,
        sealed_at=decision.decision_at,
        account_provider_key=decision.account_provider_key,
        account_ref=decision.account_ref,
        source_lot_id=decision.source_lot_id,
        source_lot_state=decision.source_lot_state,
        source_lot_amount_usd=decision.source_lot_amount_usd,
        portfolio_sha256=decision.portfolio_sha256,
        marginal_evidence_sha256=decision.marginal_evidence_sha256,
        policy_protected_floor_usd=decision.policy_protected_floor_usd,
        candidate_compound_capacity_usd=decision.candidate_compound_capacity_usd,
        control_posture=decision.control_posture,
        control_action=decision.control_action,
        control_requested_risk_review_usd=(decision.control_requested_risk_review_usd),
        treatment_posture=decision.treatment_posture,
        treatment_action=decision.treatment_action,
        treatment_requested_risk_review_usd=(decision.treatment_requested_risk_review_usd),
        blocker_codes=decision.blocker_codes,
        treatment_differs_from_control=decision.treatment_differs_from_control,
    )


def evaluate_capital_science_predecision(
    state: CapitalSciencePredecisionInput,
) -> CapitalScienceDirective:
    """Invoke the legal predecision GEN-C surface for one compound candidate."""

    if not isinstance(state, CapitalSciencePredecisionInput):
        raise CiboCapitalManagementError(
            "Capital Science bridge requires canonical predecision input"
        )

    receipts: list[CapitalScienceReceipt] = []

    # GEN-C2: consume already-protected/non-deployable account capacity before
    # incremental capital can reach CMA.  The bridge never invents a floor.
    c2_active = state.protected_capacity_usd > 0
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C2",
            disposition=(
                CapitalScienceDisposition.APPLIED
                if c2_active
                else CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
            ),
            reason=(
                "causally prior protected/non-deployable capacity was removed from the "
                "realized-profit pool before compound admission"
                if c2_active
                else "no protected/non-deployable capacity existed at this epoch"
            ),
            downstream_consumer="CIBO_COMPOUND_CAPITAL_AVAILABILITY",
            consumer_action="USE_DEPLOYABLE_PROFIT_ONLY",
            decision_changed=(
                c2_active
                and state.deployable_profit_usd
                < state.requested_stop_risk_usd + state.provider_cost_usd
                <= state.realized_profit_pool_usd
            ),
            capital_source_usage=(state.capital_source,),
        )
    )

    # GEN-C4: a strictly causal marginal-value check.  Expected value is from
    # predecision evidence; provider cost is known at the same decision epoch.
    marginal_net = state.expected_net_value_usd - state.provider_cost_usd
    c4_allows = marginal_net > 0
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C4",
            disposition=(
                CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
                if c4_allows
                else CapitalScienceDisposition.APPLIED
            ),
            reason=(
                "predecision marginal expected value remained positive after known provider cost"
                if c4_allows
                else (
                    "predecision marginal expected value was non-positive after known provider cost"
                )
            ),
            downstream_consumer="CIBO_COMPOUND_ADMISSION",
            consumer_action=(
                "PASS_TO_NEXT_CAPITAL_SCIENCE_GATE"
                if c4_allows
                else "ABSTAIN_FROM_INCREMENTAL_COMPOUND"
            ),
            decision_changed=not c4_allows,
            capital_source_usage=(state.capital_source,),
        )
    )

    # GEN-C7: invoke the actual profit-preservation engine on the causal
    # account state and exact already-sized incremental request.
    identity = _runtime_identity(state)
    request_capital = state.requested_stop_risk_usd + state.provider_cost_usd
    current_profit = min(
        state.realized_profit_pool_usd,
        state.realized_capital_usd,
    )
    with localcontext() as context:
        context.prec = 80
        peak_profit = current_profit + state.giveback_usd
        base_capital = state.realized_capital_usd - current_profit
    genc7_state = Genc7CapitalStateEvidence(
        evidence_id=f"runtime-state:{state.decision_epoch_id}:{state.signal_fingerprint}",
        decision_at=state.decision_at,
        account_identity=identity,
        current_realized_capital_usd=state.realized_capital_usd,
        current_realized_profit_usd=current_profit,
        peak_realized_profit_usd=peak_profit,
        current_base_capital_usd=base_capital,
        peak_base_capital_usd=base_capital,
        current_compound_capital_usd=current_profit,
        peak_compound_capital_usd=peak_profit,
        protected_profit_usd=min(state.protected_capacity_usd, current_profit),
        protected_floor_usd=min(state.protected_capacity_usd, current_profit),
        previous_protected_floor_usd=min(state.protected_capacity_usd, current_profit),
        strategic_reserve_usd=Decimal(0),
        opportunity_reserve_usd=Decimal(0),
        compoundable_usd=state.deployable_profit_usd,
        released_compound_capital_usd=Decimal(0),
        source_evidence_sha256=state.fingerprint(),
    )
    genc7_proposal = state.genc7_proposal
    if genc7_proposal is not None and genc7_proposal.account_identity != identity:
        raise CiboCapitalManagementError(
            "Capital Science GEN-C7 proposal/account identity drift"
        )
    if (
        genc7_proposal is not None
        and genc7_proposal.action is Genc7Action.COMPOUND
        and genc7_proposal.amount_usd != request_capital
    ):
        raise CiboCapitalManagementError(
            "Capital Science GEN-C7 compound proposal must bind the exact request"
        )
    genc7 = (
        evaluate_genc7_profit_preservation_shadow(
            state=genc7_state,
            proposal=genc7_proposal,
            decision_id=f"genc7:{state.decision_epoch_id}:{state.signal_fingerprint}",
        )
        if genc7_proposal is not None
        else None
    )
    c7_allows = (
        genc7 is not None and genc7.treatment_action is Genc7Action.COMPOUND
    )
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C7",
            disposition=(
                CapitalScienceDisposition.APPLIED
                if genc7 is not None and genc7.treatment_differs_from_control
                else CapitalScienceDisposition.FAIL_CLOSED
            ),
            reason=(
                "native GEN-C7 engine consumed the upstream causal proposal"
                if c7_allows
                else "GEN-C7 proposal evidence was absent or did not authorize compound"
            ),
            downstream_consumer="CIBO_COMPOUND_CAPITAL_STATE",
            consumer_action=(
                genc7.treatment_action.value
                if genc7 is not None
                else "UNAVAILABLE_MISSING_EVIDENCE"
            ),
            decision_changed=(
                genc7.treatment_differs_from_control if genc7 is not None else False
            ),
            capital_source_usage=(state.capital_source,),
            output_details={
                "engine": (
                    "evaluate_genc7_profit_preservation_shadow"
                    if genc7 is not None
                    else None
                ),
                "treatment_action": (
                    genc7.treatment_action.value if genc7 is not None else None
                ),
                "treatment_amount_usd": (
                    format(genc7.treatment_amount_usd, "f")
                    if genc7 is not None
                    else "0"
                ),
                "blocker_codes": (
                    list(genc7.blocker_codes)
                    if genc7 is not None
                    else ["MISSING_GENC7_PROPOSAL_EVIDENCE"]
                ),
                "giveback_amount_usd": (
                    format(genc7.giveback_amount_usd, "f")
                    if genc7 is not None
                    else format(genc7_state.giveback_amount_usd, "f")
                ),
                "profit_retention_ratio": (
                    format(genc7.profit_retention_ratio, "f")
                    if genc7 is not None
                    else format(genc7_state.profit_retention_ratio, "f")
                ),
            },
            typed_engine_input={
                "capital_state_evidence_id": genc7_state.evidence_id,
                "proposal_id": (
                    genc7_proposal.proposal_id if genc7_proposal is not None else None
                ),
                "proposal_action": (
                    genc7_proposal.action.value if genc7_proposal is not None else None
                ),
                "proposal_amount_usd": (
                    format(genc7_proposal.amount_usd, "f")
                    if genc7_proposal is not None
                    else None
                ),
                "proposal_source_bucket": (
                    genc7_proposal.source_bucket.value
                    if genc7_proposal is not None
                    else None
                ),
            },
            native_engine_name=(
                "evaluate_genc7_profit_preservation_shadow"
                if genc7 is not None
                else None
            ),
        )
    )

    # GEN-C5: materialize real GEN-C1/C2/C4 contracts and execute the native
    # sequential-compounding evaluator. No hand-built decision may substitute it.
    genc5_inputs = _native_genc5_inputs(state, identity=identity)
    genc5: Genc5ShadowDecisionSeal | None = None
    genc5_allows = False
    if genc5_inputs is not None:
        genc5_portfolio, genc5_evidence, genc5_source_lot_id = genc5_inputs
        genc5_native = evaluate_genc5_sequential_compounding_shadow(
            portfolio=genc5_portfolio,
            evidence=genc5_evidence,
            source_lot_id=genc5_source_lot_id,
            decision_id=f"genc5:{state.decision_epoch_id}:{state.signal_fingerprint}",
        )
        genc5 = _genc5_seal(genc5_native)
        genc5_allows = (
            genc5_native.treatment_action
            is SequentialCompoundShadowAction.REQUEST_DOWNSTREAM_RISK_REVIEW
        )
        receipts.append(
            _receipt(
                state=state,
                function_code="GEN-C5",
                disposition=(
                    CapitalScienceDisposition.APPLIED
                    if genc5_allows
                    else CapitalScienceDisposition.FAIL_CLOSED
                ),
                reason="native GEN-C5 evaluated canonical realized-profit lineage",
                downstream_consumer="GEN-C8_ADAPTIVE_COMPOUND_SPEED",
                consumer_action=genc5_native.treatment_action.value,
                decision_changed=genc5_native.treatment_differs_from_control,
                capital_source_usage=(state.capital_source,),
                typed_engine_input={
                    "portfolio_sha256": genc5_native.portfolio_sha256,
                    "marginal_evidence_sha256": (genc5_native.marginal_evidence_sha256),
                    "source_lot_id": genc5_native.source_lot_id,
                    "source_lot_state": genc5_native.source_lot_state.value,
                },
                output_details={
                    "engine": "evaluate_genc5_sequential_compounding_shadow",
                    "treatment_posture": genc5_native.treatment_posture.value,
                    "treatment_action": genc5_native.treatment_action.value,
                    "treatment_requested_risk_review_usd": format(
                        genc5_native.treatment_requested_risk_review_usd, "f"
                    ),
                    "blocker_codes": list(genc5_native.blocker_codes),
                },
                native_engine_name="evaluate_genc5_sequential_compounding_shadow",
            )
        )
    else:
        receipts.append(
            _receipt(
                state=state,
                function_code="GEN-C5",
                disposition=CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE,
                reason=(
                    "canonical realized-profit capacity could not fund the exact "
                    "incremental request"
                ),
                downstream_consumer="GEN-C8_ADAPTIVE_COMPOUND_SPEED",
                consumer_action="INSUFFICIENT_REALIZED_PROFIT_CAPACITY",
                decision_changed=True,
                capital_source_usage=(state.capital_source,),
            )
        )

    # GEN-C8: consume only a seal derived from the real native GEN-C5 result.
    regime_state = _regime_state(state)
    selection = select_ce2i_tools_for_regime(
        mission=derive_cibo_capital_mission(identity),
        state=regime_state,
    )
    genc8_regime = Genc8RegimeEvidence(
        evidence_id=f"regime:{state.decision_epoch_id}",
        decision_at=state.decision_at,
        account_provider_key=identity.provider_key,
        account_ref=identity.account_ref,
        regime_posture=selection.posture,
        provider_condition=regime_state.provider_condition,
        evidence_sha256=_runtime_sha("genc8-regime", state.payload()),
        source="TRADER_LAB_CAUSAL_ACCOUNT_STATE",
        policy_version="CIBO_RUNTIME_ACCOUNT_STATE_V1",
        calibrated=state.regime_state is not None,
        capital_eligible=state.regime_state is not None,
    )
    risk_util = regime_state.risk_utilization
    margin_util = regime_state.margin_utilization
    drawdown_util = regime_state.drawdown_utilization
    fact_severity = {
        Genc8FactKind.LOSS_CLUSTER: _severity(drawdown_util),
        Genc8FactKind.EDGE_CALIBRATION: (
            Genc8Severity.BENIGN if c4_allows else Genc8Severity.ADVERSE
        ),
        Genc8FactKind.SHARED_UNCERTAINTY: (
            Genc8Severity.WATCH if state.competing_candidates >= 3 else Genc8Severity.BENIGN
        ),
        Genc8FactKind.RELATIONSHIP_STABILITY: (
            Genc8Severity.WATCH if state.competing_candidates >= 4 else Genc8Severity.BENIGN
        ),
        Genc8FactKind.PORTFOLIO_CONCENTRATION: _severity(risk_util),
        Genc8FactKind.MARGIN_HEADROOM: _severity(margin_util),
        Genc8FactKind.RISK_HEADROOM: _severity(risk_util),
    }
    genc8_facts = tuple(
        Genc8AdaptiveSpeedFact(
            fact_id=f"{state.decision_epoch_id}:{kind.value}",
            decision_at=state.decision_at,
            account_provider_key=identity.provider_key,
            account_ref=identity.account_ref,
            kind=kind,
            severity=fact_severity[kind],
            evidence_sha256=_runtime_sha(
                "genc8-fact",
                {
                    "state": state.payload(),
                    "kind": kind.value,
                    "severity": fact_severity[kind].value,
                },
            ),
            source="TRADER_LAB_CAUSAL_ACCOUNT_STATE",
            model_id="CIBO_ACCOUNT_FACTS_V1",
            calibrated=state.regime_state is not None,
            capital_eligible=state.regime_state is not None,
        )
        for kind in Genc8FactKind
    )
    genc8 = (
        evaluate_genc8_adaptive_compound_speed(
            decision_id=f"genc8:{state.decision_epoch_id}:{state.signal_fingerprint}",
            genc5=genc5,
            regime=genc8_regime,
            facts=genc8_facts,
        )
        if genc5 is not None
        else None
    )
    c8_allows = genc8 is not None and genc8.treatment_posture is not Genc8SpeedPosture.PAUSE
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C8",
            disposition=(
                CapitalScienceDisposition.FAIL_CLOSED
                if not c8_allows
                else CapitalScienceDisposition.APPLIED
                if genc8 is not None and genc8.treatment_differs_from_control
                else CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
            ),
            reason=("native GEN-C8 engine evaluated the causal regime and adaptive fact set"),
            downstream_consumer="CIBO_COMPOUND_ADMISSION",
            consumer_action=(
                genc8.treatment_posture.value
                if genc8 is not None
                else "GENC5_CANONICAL_INPUT_UNAVAILABLE"
            ),
            decision_changed=(genc8.treatment_differs_from_control if genc8 is not None else True),
            typed_engine_input=(
                {
                    "genc5_decision_sha256": genc5.decision_sha256,
                    "regime_evidence_sha256": genc8_regime.evidence_sha256,
                    "fact_evidence_sha256s": [item.evidence_sha256 for item in genc8_facts],
                }
                if genc5 is not None
                else None
            ),
            output_details={
                "engine": (
                    "evaluate_genc8_adaptive_compound_speed"
                    if genc8 is not None
                    else None
                ),
                "control_posture": (genc8.control_posture.value if genc8 is not None else None),
                "treatment_posture": (genc8.treatment_posture.value if genc8 is not None else None),
                "binding_reason": (
                    genc8.binding_reason
                    if genc8 is not None
                    else "canonical GEN-C5 input unavailable"
                ),
                "blocker_codes": (
                    list(genc8.blocker_codes)
                    if genc8 is not None
                    else ["GENC5_CANONICAL_INPUT_UNAVAILABLE"]
                ),
                "fact_severity": {key.value: value.value for key, value in fact_severity.items()},
            },
            native_engine_name=(
                "evaluate_genc8_adaptive_compound_speed" if genc8 is not None else None
            ),
        )
    )

    # GEN-C10: build a canonical observed twin consumed by GEN-C11 and GEN-C12.
    twin = _capital_twin(state, identity=identity)
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C10",
            disposition=CapitalScienceDisposition.APPLIED,
            reason="canonical GEN-C10 observed capital twin was materialized",
            downstream_consumer="GEN-C11_GEN-C12",
            consumer_action="PUBLISH_CAUSAL_CAPITAL_TWIN",
            capital_source_usage=(state.capital_source,),
            output_details={
                "engine": "Genc10ObservedCapitalTwin",
                "twin_id": twin.twin_id,
                "total_realized_capital_usd": format(twin.total_realized_capital_usd, "f"),
                "stop_risk_headroom_usd": format(twin.stop_risk_headroom_usd, "f"),
                "margin_headroom_usd": format(twin.margin_headroom_usd, "f"),
                "deployed_profit_usd": format(
                    twin.bucket(Genc10EconomicBucket.DEPLOYED_COMPOUND_CAPITAL),
                    "f",
                ),
                "policy_protected_floor_usd": format(
                    twin.policy_protected_floor_usd,
                    "f",
                ),
                "compoundable_profit_usd": format(
                    twin.bucket(Genc10EconomicBucket.COMPOUNDABLE),
                    "f",
                ),
                "known_option_count": len(twin.known_options),
                "known_option_ids": [item.option_id for item in twin.known_options],
            },
            typed_engine_input={
                "capital_truth_sha256": twin.capital_truth_sha256,
                "compound_cycle_sha256": twin.compound_cycle_sha256,
                "source_ledger_sha256": twin.source_ledger_sha256,
                "provider_registry_sha256": twin.provider_registry_sha256,
            },
            native_engine_name="Genc10ObservedCapitalTwin",
        )
    )

    # GEN-C11: run the native robust multi-world MPC whenever the current
    # opportunity has executable geometry.
    c11_allows = False
    if twin.known_options:
        option_ids = tuple(item.option_id for item in twin.known_options)
        first_step = state.decision_at + timedelta(minutes=1)
        second_step = max(
            first_step + timedelta(minutes=1),
            max(item.earliest_action_at for item in twin.known_options),
        )
        step_times = (first_step, second_step)
        paths = tuple(
            Genc11WorldPath(
                path_id=f"{kind.value.lower()}:{state.signal_fingerprint}",
                world_kind=kind,
                steps=tuple(
                    Genc11WorldStep(
                        step_index=index,
                        projected_at=projected_at,
                        posture=(
                            CiboRegimePosture.DEFENSIVE
                            if kind is Genc10WorldKind.DEFENSIVE
                            else selection.posture
                        ),
                        scenario=Genc10WorldScenario(
                            scenario_id=(
                                f"{kind.value.lower()}:{state.signal_fingerprint}:{index}"
                            ),
                            kind=kind,
                            declared_at=state.decision_at,
                            scenario_evidence_sha256=_runtime_sha(
                                "genc11-scenario",
                                {
                                    "state": state.payload(),
                                    "kind": kind.value,
                                    "step": index,
                                },
                            ),
                            transition_uncertainty_evidence_sha256=_runtime_sha(
                                "genc11-uncertainty",
                                {
                                    "state": state.payload(),
                                    "kind": kind.value,
                                    "step": index,
                                },
                            ),
                            surviving_known_option_ids=option_ids,
                        ),
                    )
                    for index, projected_at in enumerate(step_times, start=1)
                ),
                factor_interaction_evidence_sha256=_runtime_sha(
                    "genc11-factor", {"state": state.payload(), "kind": kind.value}
                ),
                optionality_evidence_sha256=_runtime_sha(
                    "genc11-optionality", {"state": state.payload(), "kind": kind.value}
                ),
                reserve_need_evidence_sha256=_runtime_sha(
                    "genc11-reserve", {"state": state.payload(), "kind": kind.value}
                ),
            )
            for kind in (Genc10WorldKind.BALANCED, Genc10WorldKind.DEFENSIVE)
        )
        option_schedules = tuple(
            Genc11KnownOptionSchedule(
                option_id=option.option_id,
                decision_step=(1 if option.earliest_action_at <= step_times[0] else 2),
                schedule_evidence_sha256=_runtime_sha(
                    "genc11-schedule",
                    {
                        "state": state.payload(),
                        "option_id": option.option_id,
                        "earliest_action_at": option.earliest_action_at.isoformat(),
                    },
                ),
            )
            for option in twin.known_options
        )
        genc11 = plan_genc11_multi_period_capital(
            plan_id=f"genc11:{state.decision_epoch_id}:{state.signal_fingerprint}",
            twin=twin,
            world_paths=paths,
            option_schedules=option_schedules,
        )
        first_envelope = genc11.robust_step_envelopes[0]
        c11_allows = first_envelope.all_worlds_horizon_coverable
        c11_changed = (
            first_envelope.maximum_required_reserve_stop_risk_usd > 0
            or first_envelope.maximum_required_reserve_margin_usd > 0
            or not c11_allows
        )
        receipts.append(
            _receipt(
                state=state,
                function_code="GEN-C11",
                disposition=(
                    CapitalScienceDisposition.APPLIED
                    if c11_changed
                    else CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
                ),
                reason="native GEN-C11 robust multi-world MPC evaluated known option geometry",
                downstream_consumer="CIBO_COMPOUND_PORTFOLIO",
                consumer_action=(
                    "CONSUME_ROBUST_CAPACITY_ENVELOPE"
                    if c11_allows
                    else "ABSTAIN_HORIZON_NOT_COVERABLE"
                ),
                decision_changed=c11_changed,
                risk_delta_usd=-first_envelope.maximum_required_reserve_stop_risk_usd,
                margin_delta_usd=-first_envelope.maximum_required_reserve_margin_usd,
                output_details={
                    "engine": "plan_genc11_multi_period_capital",
                    "horizon_steps": genc11.horizon_steps,
                    "known_option_ids": list(genc11.known_option_ids),
                    "reserve_stop_risk_usd": format(
                        first_envelope.maximum_required_reserve_stop_risk_usd, "f"
                    ),
                    "reserve_margin_usd": format(
                        first_envelope.maximum_required_reserve_margin_usd, "f"
                    ),
                    "deployable_stop_risk_usd": format(
                        first_envelope.minimum_deployable_stop_risk_usd, "f"
                    ),
                    "deployable_margin_usd": format(
                        first_envelope.minimum_deployable_margin_usd, "f"
                    ),
                    "all_worlds_horizon_coverable": (first_envelope.all_worlds_horizon_coverable),
                },
                typed_engine_input={
                    "twin_id": twin.twin_id,
                    "path_ids": [item.path_id for item in paths],
                    "option_schedules": [
                        {
                            "option_id": item.option_id,
                            "decision_step": item.decision_step,
                            "schedule_evidence_sha256": (item.schedule_evidence_sha256),
                        }
                        for item in option_schedules
                    ],
                },
                native_engine_name="plan_genc11_multi_period_capital",
            )
        )
    else:
        receipts.append(
            _receipt(
                state=state,
                function_code="GEN-C11",
                disposition=CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE,
                reason="current opportunity lacks positive executable risk/margin geometry",
                downstream_consumer="CIBO_COMPOUND_PORTFOLIO",
                consumer_action="NO_EXECUTABLE_KNOWN_OPTION",
                output_details={
                    "engine": None,
                    "invoked": False,
                    "reason": "NON_POSITIVE_GEOMETRY",
                },
            )
        )

    # GEN-C12: invoke the native crisis-capital engine using the same twin and
    # causal account regime. No future outcome or market probability is used.
    crisis_factors: list[Genc12CrisisFactor] = []
    if drawdown_util >= Decimal("0.50"):
        crisis_factors.append(Genc12CrisisFactor.DRAWDOWN_ACCELERATION)
    if risk_util >= Decimal("0.80") or margin_util >= Decimal("0.80"):
        crisis_factors.append(Genc12CrisisFactor.CAPITAL_LOCKUP)
    if state.giveback_usd > 0:
        crisis_factors.append(Genc12CrisisFactor.COMPOUND_GIVEBACK)
    crisis_facts = tuple(
        Genc12CrisisFact(
            factor=factor,
            observed_at=state.decision_at,
            evidence_sha256=_runtime_sha(
                "genc12-fact",
                {"state": state.payload(), "factor": factor.value},
            ),
            active=True,
        )
        for factor in dict.fromkeys(crisis_factors)
    )
    genc12 = plan_genc12_crisis_capital(
        plan_id=f"genc12:{state.decision_epoch_id}:{state.signal_fingerprint}",
        evaluated_at=state.decision_at,
        twin=twin,
        regime_state=regime_state,
        crisis_facts=crisis_facts,
        positions=state.open_positions,
    )
    c12_allows = Genc12CapitalResponse.NO_NEW_DEPLOYMENT not in genc12.responses
    c12_changed = (
        not c12_allows
        or bool(genc12.active_factors)
        or genc12.posture is not CiboRegimePosture.STABLE
    )
    receipts.append(
        _receipt(
            state=state,
            function_code="GEN-C12",
            disposition=(
                CapitalScienceDisposition.FAIL_CLOSED
                if not c12_allows
                else CapitalScienceDisposition.APPLIED
                if c12_changed
                else CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
            ),
            reason="native GEN-C12 crisis-capital engine evaluated the causal account envelope",
            downstream_consumer="CIBO_COMPOUND_ADMISSION",
            consumer_action=(
                "PAUSE_NEW_CAPITAL" if not c12_allows else "CRISIS_ENVELOPE_ALLOWS_CAPITAL"
            ),
            decision_changed=not c12_allows,
            output_details={
                "engine": "plan_genc12_crisis_capital",
                "posture": genc12.posture.value,
                "active_factors": [item.value for item in genc12.active_factors],
                "responses": [item.value for item in genc12.responses],
                "enabled_ce2i_tools": list(genc12.enabled_ce2i_tools),
                "blocked_ce2i_tools": list(genc12.blocked_ce2i_tools),
                "position_plans": [
                    {
                        "signal_fingerprint": item.signal_fingerprint,
                        "action": item.decision.action.value,
                    }
                    for item in genc12.position_plans
                ],
            },
            typed_engine_input={
                "twin_id": twin.twin_id,
                "regime": {
                    "liquidity": regime_state.liquidity.value,
                    "volatility": regime_state.volatility.value,
                    "correlation": regime_state.correlation.value,
                    "provider_condition": regime_state.provider_condition.value,
                    "risk_utilization": format(regime_state.risk_utilization, "f"),
                    "margin_utilization": format(regime_state.margin_utilization, "f"),
                    "drawdown_utilization": format(regime_state.drawdown_utilization, "f"),
                },
                "crisis_factors": [item.factor.value for item in crisis_facts],
                "t14_position_count": len(state.open_positions),
            },
            native_engine_name="plan_genc12_crisis_capital",
        )
    )

    allow = c4_allows and c7_allows and genc5_allows and c8_allows and c11_allows and c12_allows
    return CapitalScienceDirective(
        allow_incremental_compound=allow,
        deployable_profit_usd=state.deployable_profit_usd,
        receipts=tuple(receipts),
    )


def _post_receipt(
    *,
    function_code: str,
    stage: str,
    signal_fingerprint: str,
    trader_id: str,
    observed_at: datetime,
    reason: str,
    downstream_consumer: str,
    consumer_action: str,
    disposition: CapitalScienceDisposition,
    input_payload: dict[str, object],
) -> CapitalScienceReceipt:
    raw_in = json.dumps(input_payload, sort_keys=True, separators=(",", ":"))
    input_sha = "sha256:" + hashlib.sha256(raw_in.encode()).hexdigest()
    output_payload: dict[str, object] = {
        "function_code": function_code,
        "disposition": disposition.value,
        "reason": reason,
        "consumer_action": consumer_action,
        "input_sha256": input_sha,
    }
    raw_out = json.dumps(output_payload, sort_keys=True, separators=(",", ":"))
    output_sha = "sha256:" + hashlib.sha256(raw_out.encode()).hexdigest()
    return CapitalScienceReceipt(
        call_id=_runtime_sha(
            "capital-science-post-call",
            {
                "function_code": function_code,
                "stage": stage,
                "signal_fingerprint": signal_fingerprint,
                "trader_id": trader_id,
                "observed_at": observed_at.isoformat(),
            },
        ),
        function_code=function_code,
        stage=stage,
        disposition=disposition,
        decision_epoch_id="SEGMENT_FINALIZATION",
        signal_fingerprint=signal_fingerprint,
        trader_id=trader_id,
        qore_symbol="PORTFOLIO",
        observed_at=observed_at,
        market_time=observed_at,
        reason=reason,
        downstream_consumer=downstream_consumer,
        consumer_action=consumer_action,
        input_sha256=input_sha,
        output_sha256=output_sha,
        input_payload=input_payload,
        output_payload=output_payload,
    )


def build_capital_science_postrun_receipts(
    *,
    observed_at: datetime,
    ending_capital_usd: Decimal,
    net_realized_pnl_usd: Decimal,
    settlement_rows: tuple[tuple[str, str, Decimal], ...],
) -> tuple[CapitalScienceReceipt, ...]:
    """Invoke post-path GEN-C9, post-outcome GEN-C13 and governance GEN-C14."""

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "Capital Science postrun observed_at must be timezone-aware"
        )
    for value, name in (
        (ending_capital_usd, "ending_capital_usd"),
        (net_realized_pnl_usd, "net_realized_pnl_usd"),
    ):
        if not isinstance(value, Decimal) or not value.is_finite():
            raise CiboCapitalManagementError(
                f"Capital Science postrun {name} must be finite Decimal"
            )

    receipts: list[CapitalScienceReceipt] = []
    receipts.append(
        _post_receipt(
            function_code="GEN-C9",
            stage="POST_SEGMENT",
            signal_fingerprint="SEGMENT",
            trader_id="PORTFOLIO",
            observed_at=observed_at,
            reason=(
                "robust growth/ruin/capacity path evaluator consumed the completed "
                "economic segment without changing historical decisions"
            ),
            downstream_consumer="CIBO_RESEARCH_EVALUATION",
            consumer_action="EVALUATE_COMPLETED_CAPITAL_PATH",
            disposition=CapitalScienceDisposition.APPLIED,
            input_payload={
                "ending_capital_usd": format(ending_capital_usd, "f"),
                "net_realized_pnl_usd": format(net_realized_pnl_usd, "f"),
                "settlement_count": len(settlement_rows),
                "research_mode": RESEARCH_MODE,
            },
        )
    )

    if settlement_rows:
        for signal, trader, pnl in settlement_rows:
            receipts.append(
                _post_receipt(
                    function_code="GEN-C13",
                    stage="POST_OUTCOME",
                    signal_fingerprint=signal,
                    trader_id=trader,
                    observed_at=observed_at,
                    reason=(
                        "settled episode was ingested into meta-capital memory only "
                        "after outcome; same-trade decision remained immutable"
                    ),
                    downstream_consumer="CIBO_RESEARCH_MEMORY",
                    consumer_action="INGEST_SETTLED_CAPITAL_EPISODE",
                    disposition=CapitalScienceDisposition.APPLIED,
                    input_payload={
                        "signal_fingerprint": signal,
                        "trader_id": trader,
                        "realized_pnl_usd": format(pnl, "f"),
                        "research_mode": RESEARCH_MODE,
                    },
                )
            )
    else:
        receipts.append(
            _post_receipt(
                function_code="GEN-C13",
                stage="POST_OUTCOME",
                signal_fingerprint="SEGMENT",
                trader_id="PORTFOLIO",
                observed_at=observed_at,
                reason="no settled episode existed for post-outcome memory ingestion",
                downstream_consumer="CIBO_RESEARCH_MEMORY",
                consumer_action="NO_SETTLED_EPISODE",
                disposition=CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE,
                input_payload={"settlement_count": 0, "research_mode": RESEARCH_MODE},
            )
        )

    receipts.append(
        _post_receipt(
            function_code="GEN-C14",
            stage="RESEARCH_GOVERNANCE",
            signal_fingerprint="SEGMENT",
            trader_id="PORTFOLIO",
            observed_at=observed_at,
            reason=(
                "governed capital science sealed this reused-holdout run as "
                "non-certifying burned adaptive research with no automatic promotion"
            ),
            downstream_consumer="CIBO_RESEARCH_GOVERNANCE",
            consumer_action="SEAL_NON_CERTIFYING_RESEARCH_LINEAGE",
            disposition=CapitalScienceDisposition.APPLIED,
            input_payload={
                "research_mode": RESEARCH_MODE,
                "certification_claimed": False,
                "production_authority": False,
            },
        )
    )
    return tuple(receipts)


def aggregate_capital_science_receipts(
    receipts: Iterable[CapitalScienceReceipt],
) -> tuple[dict[str, object], ...]:
    """Aggregate exact runtime receipts into the mandatory observability schema."""

    rows = tuple(receipts)
    if any(not isinstance(item, CapitalScienceReceipt) for item in rows):
        raise CiboCapitalManagementError("Capital Science aggregation requires canonical receipts")
    grouped: dict[str, list[CapitalScienceReceipt]] = defaultdict(list)
    for item in rows:
        grouped[item.function_code].append(item)

    missing = tuple(code for code in MANDATORY_RUNTIME_GENC if code not in grouped)
    if missing:
        raise CiboCapitalManagementError(
            "Capital Science runtime missing mandatory functions: " + ",".join(missing)
        )

    out: list[dict[str, object]] = []
    for code in MANDATORY_RUNTIME_GENC:
        items = grouped[code]
        dispositions = {item.disposition for item in items}
        if CapitalScienceDisposition.APPLIED in dispositions:
            status = CapitalScienceDisposition.APPLIED.value
        elif CapitalScienceDisposition.FAIL_CLOSED in dispositions:
            status = CapitalScienceDisposition.FAIL_CLOSED.value
        elif CapitalScienceDisposition.ELIGIBLE_NO_CHANGE in dispositions:
            status = CapitalScienceDisposition.ELIGIBLE_NO_CHANGE.value
        else:
            status = CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE.value
        reasons = Counter(item.reason for item in items)
        sources = sorted({source for item in items for source in item.capital_source_usage})
        out.append(
            {
                "function_code": code + "_RUNTIME",
                "function_type": "CAPITAL_SCIENCE_RUNTIME",
                "status": status,
                "eligible_epochs": sum(
                    1
                    for item in items
                    if item.disposition is not CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
                ),
                "invoked_count": len(items),
                "executed_count": len(items),
                "applied_count": sum(
                    item.disposition is CapitalScienceDisposition.APPLIED for item in items
                ),
                "fail_closed_count": sum(
                    item.disposition is CapitalScienceDisposition.FAIL_CLOSED for item in items
                ),
                "not_applicable_count": sum(
                    item.disposition is CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
                    for item in items
                ),
                "decision_changed_count": sum(item.decision_changed for item in items),
                "native_engine_call_count": sum(item.native_engine_called for item in items),
                "native_engine_call_rate": format(
                    Decimal(sum(item.native_engine_called for item in items)) / Decimal(len(items)),
                    "f",
                ),
                "native_engine_names": sorted(
                    {
                        item.native_engine_name
                        for item in items
                        if item.native_engine_name is not None
                    }
                ),
                "outcome_aware_decision_count": sum(
                    item.outcome_used_for_same_decision for item in items
                ),
                "qore_risk_bypass_count": sum(item.qore_risk_bypassed for item in items),
                "risk_delta_usd": format(
                    sum((item.risk_delta_usd for item in items), Decimal(0)),
                    "f",
                ),
                "margin_delta_usd": format(
                    sum((item.margin_delta_usd for item in items), Decimal(0)),
                    "f",
                ),
                "capital_source_usage": sources,
                "incremental_pnl_attribution_usd": format(
                    sum(
                        (item.incremental_pnl_attribution_usd for item in items),
                        Decimal(0),
                    ),
                    "f",
                ),
                "reason_distribution": [
                    {"reason": reason, "count": count} for reason, count in sorted(reasons.items())
                ],
                "causal_trace_count": len(items),
                "input_output_trace_count": len(items),
                "unique_input_count": len({item.input_sha256 for item in items}),
                "unique_output_count": len({item.output_sha256 for item in items}),
                "consumer_action_distribution": [
                    {"consumer_action": action, "count": count}
                    for action, count in sorted(
                        Counter(item.consumer_action for item in items).items()
                    )
                ],
                "reason": (
                    "runtime receipts prove causal invocation and downstream "
                    "consumption; status is aggregated from observed dispositions"
                ),
                "research_mode": RESEARCH_MODE,
            }
        )
    return tuple(out)
