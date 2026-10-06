"""Full causal economic Digital Twin composition for CIBO.

GEN-C10 remains the canonical capital truth.  This module composes additional
observed economic state around that existing twin so Maximum Capability,
GEN-C11, lifecycle, portfolio competition, leverage and redeployment can reason
from one immutable causal snapshot instead of parallel private state.

The observed twin has no allocation, sizing, Risk, execution, LIVE or broker
authority.  Counterfactual worlds are a distinct type and cannot mutate or be
mistaken for observed truth.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from enum import StrEnum

from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10ObservedCapitalTwin,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


class CiboIdleCapitalClass(StrEnum):
    SAFE_RESERVE = "SAFE_RESERVE"
    OPTIONALITY_RESERVE = "OPTIONALITY_RESERVE"
    NO_VALID_OPPORTUNITY = "NO_VALID_OPPORTUNITY"
    RISK_LIMITED = "RISK_LIMITED"
    PROVIDER_LIMITED = "PROVIDER_LIMITED"
    CONCENTRATION_LIMITED = "CONCENTRATION_LIMITED"
    WAITING_FOR_BETTER_OPPORTUNITY = "WAITING_FOR_BETTER_OPPORTUNITY"
    UNNECESSARY_IDLE = "UNNECESSARY_IDLE"


class CiboLifecycleAction(StrEnum):
    KEEP = "KEEP"
    LET_RUN = "LET_RUN"
    MOVE_TO_BREAKEVEN = "MOVE_TO_BREAKEVEN"
    TIGHTEN_STOP = "TIGHTEN_STOP"
    TRAIL_STOP = "TRAIL_STOP"
    PROTECT_PROFIT = "PROTECT_PROFIT"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"
    PARTIAL_REALIZATION = "PARTIAL_REALIZATION"
    EXTEND_TARGET = "EXTEND_TARGET"
    RELEASE_ALL = "RELEASE_ALL"
    EXIT = "EXIT"


def _exact_sum(values) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return sum(values, Decimal(0))


def _exact_sub(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return left - right


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"Full Economic Twin {name} must be timezone-aware"
        )


def _finite(value: Decimal, name: str, *, nonnegative: bool = True) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(
            f"Full Economic Twin {name} must be finite Decimal"
        )
    if nonnegative and value < 0:
        raise CiboCapitalManagementError(
            f"Full Economic Twin {name} must be non-negative"
        )


@dataclass(frozen=True, slots=True)
class CiboObservedPositionState:
    signal_fingerprint: str
    qore_symbol: str
    side: str
    entry_at: datetime
    observed_at: datetime
    current_volume: Decimal
    current_stop_risk_usd: Decimal
    current_margin_usd: Decimal
    released_stop_risk_usd: Decimal
    released_margin_usd: Decimal
    remaining_reward_r: Decimal
    provider_cost_usd: Decimal
    entry_price: Decimal | None = None
    structural_stop: Decimal | None = None
    technical_target: Decimal | None = None
    current_mark_price: Decimal | None = None
    market_state_observed_at: datetime | None = None
    mark_to_market_identified: bool = False
    entry_expected_net_value_usd: Decimal = Decimal(0)
    entry_expected_capital_minutes: Decimal = Decimal(1)
    expectation_evidence_sha256: str = "sha256:" + "0" * 64
    remaining_reward_identified: bool = False
    expected_continuation_net_value_usd: Decimal = Decimal(0)
    expected_remaining_capital_minutes: Decimal = Decimal(1)
    release_cost_usd: Decimal = Decimal(0)
    uncertainty_penalty: Decimal = Decimal(0)
    releasable: bool = True
    continuation_value_identified: bool = False
    lifecycle_actions: tuple[CiboLifecycleAction, ...] = ()
    future_outcome_used: bool = False
    structural_stop_widened: bool = False

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "Full Economic Twin position identity is required"
            )
        if self.side not in {"long", "short"}:
            raise CiboCapitalManagementError(
                "Full Economic Twin position side must be long/short"
            )
        _aware(self.entry_at, "position entry_at")
        _aware(self.observed_at, "position observed_at")
        if self.observed_at < self.entry_at:
            raise CiboCapitalManagementError(
                "Full Economic Twin position cannot be observed before entry"
            )
        for name in (
            "current_volume",
            "current_stop_risk_usd",
            "current_margin_usd",
            "released_stop_risk_usd",
            "released_margin_usd",
            "provider_cost_usd",
            "entry_expected_capital_minutes",
            "expected_remaining_capital_minutes",
            "release_cost_usd",
            "uncertainty_penalty",
        ):
            _finite(getattr(self, name), name)
        _finite(
            self.entry_expected_net_value_usd,
            "entry_expected_net_value_usd",
            nonnegative=False,
        )
        _finite(
            self.expected_continuation_net_value_usd,
            "expected_continuation_net_value_usd",
            nonnegative=False,
        )
        if self.expected_remaining_capital_minutes <= 0:
            raise CiboCapitalManagementError(
                "Full Economic Twin position remaining capital minutes must be positive"
            )
        if (
            not isinstance(self.expectation_evidence_sha256, str)
            or not self.expectation_evidence_sha256.startswith("sha256:")
            or len(self.expectation_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Full Economic Twin position expectation evidence invalid"
            )
        for name in (
            "entry_price",
            "structural_stop",
            "technical_target",
            "current_mark_price",
        ):
            value = getattr(self, name)
            if value is not None:
                _finite(value, name, nonnegative=False)
        if type(self.mark_to_market_identified) is not bool:
            raise CiboCapitalManagementError(
                "Full Economic Twin mark-to-market identity must be bool"
            )
        if self.mark_to_market_identified:
            if (
                self.entry_price is None
                or self.structural_stop is None
                or self.technical_target is None
                or self.current_mark_price is None
                or self.market_state_observed_at is None
            ):
                raise CiboCapitalManagementError(
                    "Full Economic Twin identified mark requires complete price geometry"
                )
            _aware(
                self.market_state_observed_at,
                "position market_state_observed_at",
            )
            if self.market_state_observed_at > self.observed_at:
                raise CiboCapitalManagementError(
                    "Full Economic Twin market state cannot be future-known"
                )
        elif self.current_mark_price is not None:
            raise CiboCapitalManagementError(
                "Full Economic Twin unidentified mark cannot carry current_mark_price"
            )
        if type(self.remaining_reward_identified) is not bool:
            raise CiboCapitalManagementError(
                "Full Economic Twin remaining reward identity must be bool"
            )
        if type(self.releasable) is not bool:
            raise CiboCapitalManagementError(
                "Full Economic Twin position releasable must be bool"
            )
        if type(self.continuation_value_identified) is not bool:
            raise CiboCapitalManagementError(
                "Full Economic Twin position continuation identity must be bool"
            )
        _finite(self.remaining_reward_r, "remaining_reward_r", nonnegative=False)
        if (
            self.future_outcome_used
            or self.structural_stop_widened
        ):
            raise CiboCapitalManagementError(
                "Full Economic Twin position governance drift"
            )
        if len(self.lifecycle_actions) != len(tuple(self.lifecycle_actions)):
            raise CiboCapitalManagementError(
                "Full Economic Twin lifecycle actions invalid"
            )


@dataclass(frozen=True, slots=True)
class CiboObservedOpportunityState:
    option_id: str
    trader_id: str
    qore_symbol: str
    known_at: datetime
    earliest_action_at: datetime
    expires_at: datetime
    requested_capital_usd: Decimal
    expected_net_value_usd: Decimal
    expected_capital_minutes: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    provider_cost_usd: Decimal
    uncertainty_penalty: Decimal
    context_allowed: bool
    provider_viable: bool
    capital_source_eligible: bool
    evidence_sha256: str
    expectation_basis: CausalExpectationBasis = (
        CausalExpectationBasis.CURRENT_STATE_FORECAST
    )
    maximum_multiplier: int = 4
    future_outcome_used: bool = False

    def __post_init__(self) -> None:
        if not self.option_id or not self.trader_id or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "Full Economic Twin opportunity identity is required"
            )
        for name in ("known_at", "earliest_action_at", "expires_at"):
            _aware(getattr(self, name), f"opportunity {name}")
        if (
            self.earliest_action_at < self.known_at
            or self.expires_at <= self.known_at
        ):
            raise CiboCapitalManagementError(
                "Full Economic Twin opportunity chronology invalid"
            )
        _finite(self.requested_capital_usd, "requested_capital_usd")
        if self.requested_capital_usd <= 0:
            raise CiboCapitalManagementError(
                "Full Economic Twin requested capital must be positive"
            )
        _finite(
            self.expected_net_value_usd,
            "expected_net_value_usd",
            nonnegative=False,
        )
        for name in (
            "expected_capital_minutes",
            "stop_risk_usd",
            "margin_usd",
            "provider_cost_usd",
            "uncertainty_penalty",
        ):
            _finite(getattr(self, name), name)
        if self.expected_capital_minutes <= 0:
            raise CiboCapitalManagementError(
                "Full Economic Twin expected capital minutes must be positive"
            )
        if self.stop_risk_usd <= 0 or self.margin_usd <= 0:
            raise CiboCapitalManagementError(
                "Full Economic Twin opportunity geometry must be positive"
            )
        if (
            not isinstance(self.evidence_sha256, str)
            or not self.evidence_sha256.startswith("sha256:")
            or len(self.evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Full Economic Twin opportunity evidence_sha256 invalid"
            )
        if type(self.expectation_basis) is not CausalExpectationBasis:
            raise CiboCapitalManagementError(
                "Full Economic Twin expectation basis must be canonical"
            )
        if (
            not isinstance(self.maximum_multiplier, int)
            or isinstance(self.maximum_multiplier, bool)
            or self.maximum_multiplier not in {0, 1, 2, 3, 4}
        ):
            raise CiboCapitalManagementError(
                "Full Economic Twin maximum_multiplier must be 0..4"
            )
        if self.future_outcome_used:
            raise CiboCapitalManagementError(
                "Full Economic Twin opportunity cannot contain future outcome"
            )


@dataclass(frozen=True, slots=True)
class CiboCapitalVelocityState:
    observed_at: datetime
    released_stop_risk_usd: Decimal
    released_margin_usd: Decimal
    waiting_stop_risk_usd: Decimal
    waiting_margin_usd: Decimal
    oldest_release_age_minutes: Decimal
    idle_classification: CiboIdleCapitalClass

    def __post_init__(self) -> None:
        _aware(self.observed_at, "velocity observed_at")
        for name in (
            "released_stop_risk_usd",
            "released_margin_usd",
            "waiting_stop_risk_usd",
            "waiting_margin_usd",
            "oldest_release_age_minutes",
        ):
            _finite(getattr(self, name), name)
        if self.waiting_stop_risk_usd > self.released_stop_risk_usd:
            raise CiboCapitalManagementError(
                "Full Economic Twin waiting risk exceeds released risk"
            )
        if self.waiting_margin_usd > self.released_margin_usd:
            raise CiboCapitalManagementError(
                "Full Economic Twin waiting margin exceeds released margin"
            )
        if type(self.idle_classification) is not CiboIdleCapitalClass:
            raise CiboCapitalManagementError(
                "Full Economic Twin idle classification invalid"
            )


@dataclass(frozen=True, slots=True)
class CiboObservedPortfolioState:
    observed_at: datetime
    active_position_ids: tuple[str, ...]
    opportunity_ids: tuple[str, ...]
    concentration_utilization: Decimal
    correlation_utilization: Decimal
    reserved_stop_risk_usd: Decimal
    reserved_margin_usd: Decimal

    def __post_init__(self) -> None:
        _aware(self.observed_at, "portfolio observed_at")
        if len(self.active_position_ids) != len(set(self.active_position_ids)):
            raise CiboCapitalManagementError(
                "Full Economic Twin duplicate active position"
            )
        if len(self.opportunity_ids) != len(set(self.opportunity_ids)):
            raise CiboCapitalManagementError(
                "Full Economic Twin duplicate opportunity"
            )
        for name in (
            "concentration_utilization",
            "correlation_utilization",
        ):
            value = getattr(self, name)
            _finite(value, name)
            if value > 1:
                raise CiboCapitalManagementError(
                    f"Full Economic Twin {name} outside [0,1]"
                )
        for name in ("reserved_stop_risk_usd", "reserved_margin_usd"):
            _finite(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class CiboObservedEconomicTwin:
    twin_id: str
    captured_at: datetime
    capital_twin: Genc10ObservedCapitalTwin
    positions: tuple[CiboObservedPositionState, ...]
    opportunities: tuple[CiboObservedOpportunityState, ...]
    portfolio: CiboObservedPortfolioState
    velocity: CiboCapitalVelocityState
    cognitive_constraints: tuple[tuple[str, str], ...] = ()
    provider_state: tuple[tuple[str, str], ...] = ()
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    future_outcome_used: bool = False

    def __post_init__(self) -> None:
        if not self.twin_id:
            raise CiboCapitalManagementError(
                "Full Economic Twin identity is required"
            )
        _aware(self.captured_at, "captured_at")
        if not isinstance(self.capital_twin, Genc10ObservedCapitalTwin):
            raise CiboCapitalManagementError(
                "Full Economic Twin requires canonical GEN-C10 capital twin"
            )
        if self.capital_twin.captured_at != self.captured_at:
            raise CiboCapitalManagementError(
                "Full Economic Twin capture time must equal GEN-C10 capture time"
            )
        if any(item.observed_at > self.captured_at for item in self.positions):
            raise CiboCapitalManagementError(
                "Full Economic Twin contains future position state"
            )
        if any(item.known_at > self.captured_at for item in self.opportunities):
            raise CiboCapitalManagementError(
                "Full Economic Twin contains future-known opportunity"
            )
        if self.portfolio.observed_at > self.captured_at:
            raise CiboCapitalManagementError(
                "Full Economic Twin contains future portfolio state"
            )
        if self.velocity.observed_at > self.captured_at:
            raise CiboCapitalManagementError(
                "Full Economic Twin contains future velocity state"
            )
        position_ids = tuple(item.signal_fingerprint for item in self.positions)
        option_ids = tuple(item.option_id for item in self.opportunities)
        if len(position_ids) != len(set(position_ids)):
            raise CiboCapitalManagementError(
                "Full Economic Twin position ids must be unique"
            )
        if len(option_ids) != len(set(option_ids)):
            raise CiboCapitalManagementError(
                "Full Economic Twin opportunity ids must be unique"
            )
        if set(self.portfolio.active_position_ids) != set(position_ids):
            raise CiboCapitalManagementError(
                "Full Economic Twin portfolio position surface drift"
            )
        if set(self.portfolio.opportunity_ids) != set(option_ids):
            raise CiboCapitalManagementError(
                "Full Economic Twin portfolio opportunity surface drift"
            )
        open_risk = _exact_sum(
            item.current_stop_risk_usd for item in self.positions
        )
        open_margin = _exact_sum(
            item.current_margin_usd for item in self.positions
        )
        if open_risk > self.capital_twin.used_stop_risk_usd:
            raise CiboCapitalManagementError(
                "Full Economic Twin position risk exceeds GEN-C10 used risk"
            )
        if open_margin > self.capital_twin.used_margin_usd:
            raise CiboCapitalManagementError(
                "Full Economic Twin position margin exceeds GEN-C10 used margin"
            )
        if (
            self.portfolio.reserved_stop_risk_usd
            > self.capital_twin.stop_risk_headroom_usd
            or self.portfolio.reserved_margin_usd
            > self.capital_twin.margin_headroom_usd
        ):
            raise CiboCapitalManagementError(
                "Full Economic Twin reserves exceed GEN-C10 headroom"
            )
        keys = tuple(item[0] for item in self.cognitive_constraints)
        if len(keys) != len(set(keys)):
            raise CiboCapitalManagementError(
                "Full Economic Twin cognitive constraint keys must be unique"
            )
        provider_keys = tuple(item[0] for item in self.provider_state)
        if len(provider_keys) != len(set(provider_keys)):
            raise CiboCapitalManagementError(
                "Full Economic Twin provider-state keys must be unique"
            )
        if (
            self.allocation_authority
            or self.risk_authority
            or self.execution_authority
            or self.future_outcome_used
        ):
            raise CiboCapitalManagementError(
                "Full Economic Twin cannot acquire productive authority or future knowledge"
            )

    @property
    def snapshot_sha256(self) -> str:
        payload = {
            "twin_id": self.twin_id,
            "captured_at": self.captured_at.isoformat(),
            "capital_twin_id": self.capital_twin.twin_id,
            "capital_truth_sha256": self.capital_twin.capital_truth_sha256,
            "positions": [
                {
                    **asdict(item),
                    "entry_at": item.entry_at.isoformat(),
                    "observed_at": item.observed_at.isoformat(),
                    "lifecycle_actions": [
                        action.value for action in item.lifecycle_actions
                    ],
                }
                for item in self.positions
            ],
            "opportunities": [
                {
                    **asdict(item),
                    "known_at": item.known_at.isoformat(),
                    "earliest_action_at": item.earliest_action_at.isoformat(),
                    "expires_at": item.expires_at.isoformat(),
                }
                for item in self.opportunities
            ],
            "portfolio": {
                **asdict(self.portfolio),
                "observed_at": self.portfolio.observed_at.isoformat(),
            },
            "velocity": {
                **asdict(self.velocity),
                "observed_at": self.velocity.observed_at.isoformat(),
                "idle_classification": self.velocity.idle_classification.value,
            },
            "cognitive_constraints": self.cognitive_constraints,
            "provider_state": self.provider_state,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class CiboCounterfactualEconomicWorld:
    world_id: str
    observed_twin_id: str
    declared_at: datetime
    assumptions: tuple[tuple[str, str], ...]
    hypothetical_actions: tuple[str, ...]
    projected_stop_risk_delta_usd: Decimal = Decimal(0)
    projected_margin_delta_usd: Decimal = Decimal(0)
    actual_future_outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.world_id or not self.observed_twin_id:
            raise CiboCapitalManagementError(
                "Counterfactual Economic World identity is required"
            )
        _aware(self.declared_at, "counterfactual declared_at")
        _finite(
            self.projected_stop_risk_delta_usd,
            "projected_stop_risk_delta_usd",
            nonnegative=False,
        )
        _finite(
            self.projected_margin_delta_usd,
            "projected_margin_delta_usd",
            nonnegative=False,
        )
        if self.actual_future_outcome_used or self.productive_authority:
            raise CiboCapitalManagementError(
                "Counterfactual Economic World cannot use oracle outcomes or authority"
            )
        keys = tuple(item[0] for item in self.assumptions)
        if len(keys) != len(set(keys)):
            raise CiboCapitalManagementError(
                "Counterfactual Economic World assumptions must be unique"
            )


def observed_twin_constraints(
    twin: CiboObservedEconomicTwin,
) -> Mapping[str, Decimal]:
    """Expose canonical capacity constraints without granting authority."""

    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboCapitalManagementError(
            "observed_twin_constraints requires canonical Full Economic Twin"
        )
    return {
        "stop_risk_headroom_usd": (
            _exact_sub(
                twin.capital_twin.stop_risk_headroom_usd,
                twin.portfolio.reserved_stop_risk_usd,
            )
        ),
        "margin_headroom_usd": (
            _exact_sub(
                twin.capital_twin.margin_headroom_usd,
                twin.portfolio.reserved_margin_usd,
            )
        ),
        "waiting_stop_risk_usd": twin.velocity.waiting_stop_risk_usd,
        "waiting_margin_usd": twin.velocity.waiting_margin_usd,
    }
