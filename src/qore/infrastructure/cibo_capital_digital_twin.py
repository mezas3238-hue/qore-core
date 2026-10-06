"""GEN-C10 causal Capital Digital Twin.

The twin is a research-only representation of current CIBO capital truth and
hypothetical future capital worlds. Observed state is built only from causal
evidence already available at capture time. Scenario transitions are explicit
assumptions, never claimed market probabilities or hidden future observations.

No sizing, Risk, execution, LIVE, broker or real-capital authority is granted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from enum import StrEnum
from fractions import Fraction

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalCapacityDimension,
    capital_source_dimension,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_compound_cycle_audit import (
    compound_cycle_state_sha256,
)
from qore.infrastructure.cibo_compound_cycle_state import CiboCompoundCycleState
from qore.infrastructure.cibo_instrument_capability_registry import (
    CapabilityStatus,
    ProviderInstrumentCapabilityRegistry,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    IntegratedCapitalTruth,
)
from qore.infrastructure.cibo_protected_base_overlay import (
    capital_source_ledger_sha256,
)

GENC10_POLICY_ID = "CIBO_GENC10_CAUSAL_CAPITAL_DIGITAL_TWIN_V1"
GENC10_FROZEN_AT = datetime(2026, 9, 30, 7, 35, tzinfo=UTC)
GENC10_POLICY_SHA256 = (
    "sha256:d9f8eac29481e502c1f45e8eb1c4f59c6aaa90bfa63ca0dcb067ee7b5620cc0b"
)


class Genc10WorldKind(StrEnum):
    AGGRESSIVE_GROWTH = "AGGRESSIVE_GROWTH"
    BALANCED = "BALANCED"
    DEFENSIVE = "DEFENSIVE"
    CRISIS = "CRISIS"
    OPPORTUNITY_SCARCITY = "OPPORTUNITY_SCARCITY"
    OPPORTUNITY_ABUNDANCE = "OPPORTUNITY_ABUNDANCE"


class Genc10EconomicBucket(StrEnum):
    ORIGINAL_BASE = "ORIGINAL_BASE"
    REALIZED_PROFIT = "REALIZED_PROFIT"
    PROTECTED_PROFIT = "PROTECTED_PROFIT"
    COMPOUNDABLE = "COMPOUNDABLE"
    STRATEGIC_RESERVE = "STRATEGIC_RESERVE"
    OPPORTUNITY_RESERVE = "OPPORTUNITY_RESERVE"
    ACTIVE_COMPOUND_CAPACITY = "ACTIVE_COMPOUND_CAPACITY"
    DEPLOYED_COMPOUND_CAPITAL = "DEPLOYED_COMPOUND_CAPITAL"
    RELEASED_COMPOUND_CAPITAL = "RELEASED_COMPOUND_CAPITAL"
    RETIRED_TO_PROTECTED_FLOOR = "RETIRED_TO_PROTECTED_FLOOR"


class Genc10FlowKind(StrEnum):
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"
    SETTLED_GAIN = "SETTLED_GAIN"
    REALIZED_LOSS = "REALIZED_LOSS"


_COMPOUND_BUCKET_MAP = {
    CompoundCapitalState.REALIZED_PROFIT:
        Genc10EconomicBucket.REALIZED_PROFIT,
    CompoundCapitalState.PROTECTED_PROFIT:
        Genc10EconomicBucket.PROTECTED_PROFIT,
    CompoundCapitalState.COMPOUNDABLE:
        Genc10EconomicBucket.COMPOUNDABLE,
    CompoundCapitalState.STRATEGIC_RESERVE:
        Genc10EconomicBucket.STRATEGIC_RESERVE,
    CompoundCapitalState.OPPORTUNITY_RESERVE:
        Genc10EconomicBucket.OPPORTUNITY_RESERVE,
    CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY:
        Genc10EconomicBucket.ACTIVE_COMPOUND_CAPACITY,
    CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL:
        Genc10EconomicBucket.DEPLOYED_COMPOUND_CAPITAL,
    CompoundCapitalState.RELEASED_COMPOUND_CAPITAL:
        Genc10EconomicBucket.RELEASED_COMPOUND_CAPITAL,
    CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR:
        Genc10EconomicBucket.RETIRED_TO_PROTECTED_FLOOR,
}


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C10 {name} must be timezone-aware"
        )


def _money(
    value: Decimal,
    name: str,
    *,
    positive: bool = False,
) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or (positive and value <= 0)
        or (not positive and value < 0)
    ):
        qualifier = "positive" if positive else "non-negative"
        raise CiboCompoundCapitalError(
            f"GEN-C10 {name} must be finite {qualifier} Decimal"
        )


def _signed(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCompoundCapitalError(
            f"GEN-C10 {name} must be finite Decimal"
        )


def _exact_sum_equals(total: Decimal, values: tuple[Decimal, ...]) -> bool:
    """Compare Decimal conservation identities without context rounding."""

    return sum((Fraction(item) for item in values), Fraction(0)) == Fraction(total)


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C10 {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class Genc10SourceCapacityState:
    dimension: CapitalCapacityDimension
    proven: Decimal
    available: Decimal
    reserved: Decimal
    deployed: Decimal
    consumed: Decimal

    def __post_init__(self) -> None:
        if type(self.dimension) is not CapitalCapacityDimension:
            raise CiboCompoundCapitalError(
                "GEN-C10 source capacity dimension is invalid"
            )
        for name in (
            "proven",
            "available",
            "reserved",
            "deployed",
            "consumed",
        ):
            _money(getattr(self, name), f"source capacity {name}")
        if (
            self.available
            + self.reserved
            + self.deployed
            + self.consumed
            != self.proven
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 source capacity does not conserve its dimension"
            )


@dataclass(frozen=True, slots=True)
class Genc10KnownCapitalOption:
    option_id: str
    known_at: datetime
    earliest_action_at: datetime
    expires_at: datetime
    requested_capital_usd: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    evidence_sha256: str
    outcome_present: bool = False
    future_arrival_claimed: bool = False

    def __post_init__(self) -> None:
        if not self.option_id:
            raise CiboCompoundCapitalError(
                "GEN-C10 known option identity is required"
            )
        _aware(self.known_at, "known option known_at")
        _aware(self.earliest_action_at, "known option earliest_action_at")
        _aware(self.expires_at, "known option expires_at")
        if self.earliest_action_at < self.known_at:
            raise CiboCompoundCapitalError(
                "GEN-C10 known option action cannot predate knowledge"
            )
        if self.expires_at <= self.earliest_action_at:
            raise CiboCompoundCapitalError(
                "GEN-C10 known option expiry must follow action time"
            )
        for name in (
            "requested_capital_usd",
            "stop_risk_usd",
            "margin_usd",
        ):
            _money(getattr(self, name), name, positive=True)
        _sha(self.evidence_sha256, "known option evidence_sha256")
        if self.outcome_present or self.future_arrival_claimed:
            raise CiboCompoundCapitalError(
                "GEN-C10 known option cannot use future/outcome knowledge"
            )


@dataclass(frozen=True, slots=True)
class Genc10ObservedCapitalTwin:
    twin_id: str
    account_identity: CiboAccountCapitalIdentity
    captured_at: datetime
    capital_truth_sha256: str
    compound_cycle_sha256: str
    source_ledger_sha256: str
    provider_registry_sha256: str
    total_realized_capital_usd: Decimal
    original_base_usd: Decimal
    compound_economic_value_usd: Decimal
    protected_floor_usd: Decimal
    policy_protected_floor_usd: Decimal
    broker_guaranteed_floor_usd: Decimal
    economic_buckets: tuple[tuple[Genc10EconomicBucket, Decimal], ...]
    generation_balances: tuple[tuple[int, Decimal], ...]
    source_capacities: tuple[Genc10SourceCapacityState, ...]
    total_stop_risk_capacity_usd: Decimal
    used_stop_risk_usd: Decimal
    stop_risk_headroom_usd: Decimal
    total_margin_capacity_usd: Decimal
    used_margin_usd: Decimal
    margin_headroom_usd: Decimal
    active_deployment_count: int
    provider_capability_counts: tuple[tuple[CapabilityStatus, int], ...]
    known_options: tuple[Genc10KnownCapitalOption, ...] = ()
    policy_id: str = GENC10_POLICY_ID
    policy_sha256: str = GENC10_POLICY_SHA256
    frozen_at: datetime = GENC10_FROZEN_AT
    future_leakage_used: bool = False
    market_probability_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.twin_id:
            raise CiboCompoundCapitalError(
                "GEN-C10 twin identity is required"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 twin account identity is invalid"
            )
        _aware(self.captured_at, "captured_at")
        _aware(self.frozen_at, "frozen_at")
        # frozen_at versions the Digital Twin contract; it does not forbid
        # representing an earlier causal account state during historical replay.
        if self.policy_id != GENC10_POLICY_ID:
            raise CiboCompoundCapitalError(
                "GEN-C10 twin policy identity drift"
            )
        if self.policy_sha256 != GENC10_POLICY_SHA256:
            raise CiboCompoundCapitalError(
                "GEN-C10 twin policy digest drift"
            )
        for name in (
            "capital_truth_sha256",
            "compound_cycle_sha256",
            "source_ledger_sha256",
            "provider_registry_sha256",
        ):
            _sha(getattr(self, name), name)
        for name in (
            "total_realized_capital_usd",
            "original_base_usd",
            "compound_economic_value_usd",
            "protected_floor_usd",
            "policy_protected_floor_usd",
            "broker_guaranteed_floor_usd",
            "total_stop_risk_capacity_usd",
            "used_stop_risk_usd",
            "stop_risk_headroom_usd",
            "total_margin_capacity_usd",
            "used_margin_usd",
            "margin_headroom_usd",
        ):
            _money(getattr(self, name), name)
        if not _exact_sum_equals(
            self.total_realized_capital_usd,
            (self.original_base_usd, self.compound_economic_value_usd),
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 realized capital identity drift"
            )
        if not _exact_sum_equals(
            self.total_stop_risk_capacity_usd,
            (self.used_stop_risk_usd, self.stop_risk_headroom_usd),
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 stop-risk capacity identity drift"
            )
        if not _exact_sum_equals(
            self.total_margin_capacity_usd,
            (self.used_margin_usd, self.margin_headroom_usd),
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 margin capacity identity drift"
            )
        bucket_keys = tuple(item[0] for item in self.economic_buckets)
        if len(bucket_keys) != len(set(bucket_keys)):
            raise CiboCompoundCapitalError(
                "GEN-C10 economic buckets must be unique"
            )
        if set(bucket_keys) != set(Genc10EconomicBucket):
            raise CiboCompoundCapitalError(
                "GEN-C10 observed twin requires every economic bucket"
            )
        if not _exact_sum_equals(
            self.total_realized_capital_usd,
            tuple(amount for _, amount in self.economic_buckets),
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 economic buckets do not conserve realized capital"
            )
        if (
            self.bucket(
                Genc10EconomicBucket.RETIRED_TO_PROTECTED_FLOOR
            )
            != self.protected_floor_usd
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 protected-floor bucket/ledger drift"
            )
        generation_ids = tuple(item[0] for item in self.generation_balances)
        if len(generation_ids) != len(set(generation_ids)):
            raise CiboCompoundCapitalError(
                "GEN-C10 generation balances must be unique"
            )
        if any(generation <= 0 for generation in generation_ids):
            raise CiboCompoundCapitalError(
                "GEN-C10 compound generations must be positive"
            )
        if not _exact_sum_equals(
            self.compound_economic_value_usd,
            tuple(amount for _, amount in self.generation_balances),
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 generation balances do not conserve compound value"
            )
        dimensions = tuple(item.dimension for item in self.source_capacities)
        if len(dimensions) != len(set(dimensions)):
            raise CiboCompoundCapitalError(
                "GEN-C10 source capacity dimensions must be unique"
            )
        statuses = tuple(item[0] for item in self.provider_capability_counts)
        if len(statuses) != len(set(statuses)):
            raise CiboCompoundCapitalError(
                "GEN-C10 provider status counts must be unique"
            )
        if self.active_deployment_count < 0:
            raise CiboCompoundCapitalError(
                "GEN-C10 active deployment count cannot be negative"
            )
        option_ids = tuple(item.option_id for item in self.known_options)
        if len(option_ids) != len(set(option_ids)):
            raise CiboCompoundCapitalError(
                "GEN-C10 known option ids must be unique"
            )
        if any(item.known_at > self.captured_at for item in self.known_options):
            raise CiboCompoundCapitalError(
                "GEN-C10 observed twin cannot include future-known options"
            )
        if (
            self.future_leakage_used
            or self.market_probability_claimed
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 observed twin governance drift"
            )

    def bucket(self, bucket: Genc10EconomicBucket) -> Decimal:
        for key, value in self.economic_buckets:
            if key is bucket:
                return value
        raise CiboCompoundCapitalError("GEN-C10 bucket is missing")


@dataclass(frozen=True, slots=True)
class Genc10CapitalFlow:
    flow_id: str
    kind: Genc10FlowKind
    amount_usd: Decimal
    evidence_sha256: str
    source_bucket: Genc10EconomicBucket | None = None
    target_bucket: Genc10EconomicBucket | None = None

    def __post_init__(self) -> None:
        if not self.flow_id:
            raise CiboCompoundCapitalError(
                "GEN-C10 capital flow identity is required"
            )
        if type(self.kind) is not Genc10FlowKind:
            raise CiboCompoundCapitalError(
                "GEN-C10 capital flow kind is invalid"
            )
        _money(self.amount_usd, "capital flow amount", positive=True)
        _sha(self.evidence_sha256, "capital flow evidence_sha256")
        if self.kind is Genc10FlowKind.INTERNAL_TRANSFER:
            if self.source_bucket is None or self.target_bucket is None:
                raise CiboCompoundCapitalError(
                    "GEN-C10 internal flow requires source and target"
                )
            if self.source_bucket is self.target_bucket:
                raise CiboCompoundCapitalError(
                    "GEN-C10 internal flow source/target must differ"
                )
            if self.source_bucket is Genc10EconomicBucket.ORIGINAL_BASE:
                raise CiboCompoundCapitalError(
                    "GEN-C10 V1 cannot reclassify original base capital"
                )
            if (
                self.source_bucket
                is Genc10EconomicBucket.RETIRED_TO_PROTECTED_FLOOR
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C10 protected floor cannot flow back to growth"
                )
        elif self.kind is Genc10FlowKind.SETTLED_GAIN:
            if (
                self.source_bucket is not None
                or self.target_bucket
                is not Genc10EconomicBucket.REALIZED_PROFIT
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C10 settled gain must enter REALIZED_PROFIT"
                )
        else:
            if (
                self.source_bucket
                not in {
                    Genc10EconomicBucket.ORIGINAL_BASE,
                    Genc10EconomicBucket.DEPLOYED_COMPOUND_CAPITAL,
                }
                or self.target_bucket is not None
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C10 realized loss must consume deployed/base capital"
                )


@dataclass(frozen=True, slots=True)
class Genc10WorldScenario:
    scenario_id: str
    kind: Genc10WorldKind
    declared_at: datetime
    scenario_evidence_sha256: str
    transition_uncertainty_evidence_sha256: str
    flows: tuple[Genc10CapitalFlow, ...] = ()
    stop_risk_capacity_delta_usd: Decimal = Decimal(0)
    stop_risk_usage_delta_usd: Decimal = Decimal(0)
    margin_capacity_delta_usd: Decimal = Decimal(0)
    margin_usage_delta_usd: Decimal = Decimal(0)
    surviving_known_option_ids: tuple[str, ...] = ()
    hypothetical_new_option_count: int = 0
    provider_constraints_changed: bool = False
    provider_change_evidence_sha256: str | None = None
    uncertainty_calibrated: bool = False
    market_probability_claimed: bool = False
    actual_future_outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise CiboCompoundCapitalError(
                "GEN-C10 scenario identity is required"
            )
        if type(self.kind) is not Genc10WorldKind:
            raise CiboCompoundCapitalError(
                "GEN-C10 world kind is invalid"
            )
        _aware(self.declared_at, "scenario declared_at")
        _sha(self.scenario_evidence_sha256, "scenario_evidence_sha256")
        _sha(
            self.transition_uncertainty_evidence_sha256,
            "transition_uncertainty_evidence_sha256",
        )
        flow_ids = tuple(item.flow_id for item in self.flows)
        if len(flow_ids) != len(set(flow_ids)):
            raise CiboCompoundCapitalError(
                "GEN-C10 scenario flow ids must be unique"
            )
        for name in (
            "stop_risk_capacity_delta_usd",
            "stop_risk_usage_delta_usd",
            "margin_capacity_delta_usd",
            "margin_usage_delta_usd",
        ):
            _signed(getattr(self, name), name)
        if (
            not isinstance(self.hypothetical_new_option_count, int)
            or isinstance(self.hypothetical_new_option_count, bool)
            or self.hypothetical_new_option_count < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 hypothetical option count must be non-negative int"
            )
        if (
            len(self.surviving_known_option_ids)
            != len(set(self.surviving_known_option_ids))
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 surviving option ids must be unique"
            )
        if self.provider_constraints_changed:
            if self.provider_change_evidence_sha256 is None:
                raise CiboCompoundCapitalError(
                    "GEN-C10 provider change requires evidence"
                )
            _sha(
                self.provider_change_evidence_sha256,
                "provider_change_evidence_sha256",
            )
        elif self.provider_change_evidence_sha256 is not None:
            raise CiboCompoundCapitalError(
                "GEN-C10 unchanged provider cannot carry change evidence"
            )
        if (
            self.uncertainty_calibrated
            or self.market_probability_claimed
            or self.actual_future_outcome_used
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 V1 scenario cannot claim calibration/outcome/authority"
            )


@dataclass(frozen=True, slots=True)
class Genc10ProjectedTwinState:
    twin_id: str
    scenario_id: str
    world_kind: Genc10WorldKind
    projected_at: datetime
    economic_buckets: tuple[tuple[Genc10EconomicBucket, Decimal], ...]
    total_realized_capital_usd: Decimal
    settled_gain_usd: Decimal
    realized_loss_usd: Decimal
    conservation_residual_usd: Decimal
    protected_floor_usd: Decimal
    total_stop_risk_capacity_usd: Decimal
    used_stop_risk_usd: Decimal
    stop_risk_headroom_usd: Decimal
    total_margin_capacity_usd: Decimal
    used_margin_usd: Decimal
    margin_headroom_usd: Decimal
    surviving_known_option_ids: tuple[str, ...]
    hypothetical_new_option_count: int
    provider_constraints_changed: bool
    transition_uncertainty_calibrated: bool = False
    market_probability_claimed: bool = False
    actual_future_outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        _aware(self.projected_at, "projected_at")
        for name in (
            "total_realized_capital_usd",
            "settled_gain_usd",
            "realized_loss_usd",
            "protected_floor_usd",
            "total_stop_risk_capacity_usd",
            "used_stop_risk_usd",
            "stop_risk_headroom_usd",
            "total_margin_capacity_usd",
            "used_margin_usd",
            "margin_headroom_usd",
        ):
            _money(getattr(self, name), name)
        if self.conservation_residual_usd != 0:
            raise CiboCompoundCapitalError(
                "GEN-C10 projected capital conservation residual must be zero"
            )
        if not _exact_sum_equals(
            self.total_stop_risk_capacity_usd,
            (self.used_stop_risk_usd, self.stop_risk_headroom_usd),
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 projected stop-risk identity drift"
            )
        if not _exact_sum_equals(
            self.total_margin_capacity_usd,
            (self.used_margin_usd, self.margin_headroom_usd),
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 projected margin identity drift"
            )
        if any(
            (
                self.transition_uncertainty_calibrated,
                self.market_probability_claimed,
                self.actual_future_outcome_used,
                self.productive_authority,
            )
        ):
            raise CiboCompoundCapitalError(
                "GEN-C10 V1 projection cannot claim calibration/authority"
            )


def build_genc10_observed_twin(
    *,
    twin_id: str,
    captured_at: datetime,
    compound_state: CiboCompoundCycleState,
    capital_truth: IntegratedCapitalTruth,
    source_ledger: CapitalSourceLedger,
    provider_registry: ProviderInstrumentCapabilityRegistry,
    known_options: tuple[Genc10KnownCapitalOption, ...] = (),
) -> Genc10ObservedCapitalTwin:
    """Build one conserved account-local twin from current causal evidence."""

    _aware(captured_at, "captured_at")
    if compound_state.account_identity != capital_truth.account_identity:
        raise CiboCompoundCapitalError(
            "GEN-C10 compound/capital-truth account drift"
        )
    if provider_registry.account_identity != compound_state.account_identity:
        raise CiboCompoundCapitalError(
            "GEN-C10 provider registry account drift"
        )
    if provider_registry.captured_at > captured_at:
        raise CiboCompoundCapitalError(
            "GEN-C10 provider registry comes from the future"
        )
    if (
        compound_state.last_event_at is not None
        and compound_state.last_event_at > captured_at
    ):
        raise CiboCompoundCapitalError(
            "GEN-C10 compound state comes from the future"
        )
    source_sha = capital_source_ledger_sha256(source_ledger)
    if source_sha != capital_truth.source_ledger_sha256:
        raise CiboCompoundCapitalError(
            "GEN-C10 source ledger differs from integrated capital truth"
        )
    cycle_sha = compound_cycle_state_sha256(compound_state)
    if cycle_sha != capital_truth.compound_cycle_state_sha256:
        raise CiboCompoundCapitalError(
            "GEN-C10 compound cycle differs from integrated capital truth"
        )

    buckets = _observed_buckets(compound_state)
    generations = _generation_balances(compound_state)
    source_capacities = _source_capacity_states(source_ledger)
    budget = compound_state.t19_ledger.remaining_budget()
    active_provider_entries = tuple(
        item
        for item in provider_registry.entries
        if item.observed_at <= captured_at
        and (item.expires_at is None or captured_at < item.expires_at)
    )
    provider_counts = tuple(
        (
            status,
            sum(1 for item in active_provider_entries if item.status is status),
        )
        for status in CapabilityStatus
    )
    truth_sha = integrated_capital_truth_sha256(capital_truth)

    return Genc10ObservedCapitalTwin(
        twin_id=twin_id,
        account_identity=compound_state.account_identity,
        captured_at=captured_at,
        capital_truth_sha256=truth_sha,
        compound_cycle_sha256=cycle_sha,
        source_ledger_sha256=source_sha,
        provider_registry_sha256=provider_registry.fingerprint(),
        total_realized_capital_usd=(
            compound_state.closing_realized_capital_usd
        ),
        original_base_usd=compound_state.current_original_base_usd,
        compound_economic_value_usd=(
            compound_state.compound_ledger.current_economic_value_usd
        ),
        protected_floor_usd=compound_state.floor_ledger.total_floor_usd,
        policy_protected_floor_usd=(
            compound_state.floor_ledger.policy_protected_floor_usd
        ),
        broker_guaranteed_floor_usd=(
            compound_state.floor_ledger.broker_guaranteed_floor_usd
        ),
        economic_buckets=buckets,
        generation_balances=generations,
        source_capacities=source_capacities,
        total_stop_risk_capacity_usd=(
            compound_state.t19_ledger.total_stop_risk_capacity_usd
        ),
        used_stop_risk_usd=compound_state.t19_ledger.used_stop_risk_usd,
        stop_risk_headroom_usd=budget.stop_risk_headroom_usd,
        total_margin_capacity_usd=(
            compound_state.t19_ledger.total_margin_capacity_usd
        ),
        used_margin_usd=compound_state.t19_ledger.used_margin_usd,
        margin_headroom_usd=budget.margin_headroom_usd,
        active_deployment_count=sum(
            1 for item in compound_state.deployments if not item.settled
        ),
        provider_capability_counts=provider_counts,
        known_options=known_options,
        future_leakage_used=False,
        market_probability_claimed=False,
        productive_authority=False,
    )


def project_genc10_world(
    *,
    twin: Genc10ObservedCapitalTwin,
    scenario: Genc10WorldScenario,
    projected_at: datetime,
) -> Genc10ProjectedTwinState:
    """Apply one explicit hypothetical world while preserving capital identity."""

    if not isinstance(twin, Genc10ObservedCapitalTwin):
        raise CiboCompoundCapitalError(
            "GEN-C10 projection requires canonical observed twin"
        )
    if not isinstance(scenario, Genc10WorldScenario):
        raise CiboCompoundCapitalError(
            "GEN-C10 projection requires canonical scenario"
        )
    _aware(projected_at, "projected_at")
    if projected_at < twin.captured_at:
        raise CiboCompoundCapitalError(
            "GEN-C10 projection cannot predate observed twin"
        )
    if scenario.declared_at > projected_at:
        raise CiboCompoundCapitalError(
            "GEN-C10 scenario cannot be declared after projection"
        )

    balances = dict(twin.economic_buckets)
    gain = Decimal(0)
    loss = Decimal(0)
    for flow in scenario.flows:
        if flow.kind is Genc10FlowKind.INTERNAL_TRANSFER:
            assert flow.source_bucket is not None
            assert flow.target_bucket is not None
            _consume_bucket(balances, flow.source_bucket, flow.amount_usd)
            balances[flow.target_bucket] += flow.amount_usd
        elif flow.kind is Genc10FlowKind.SETTLED_GAIN:
            assert flow.target_bucket is not None
            balances[flow.target_bucket] += flow.amount_usd
            gain += flow.amount_usd
        else:
            assert flow.source_bucket is not None
            _consume_bucket(balances, flow.source_bucket, flow.amount_usd)
            loss += flow.amount_usd

    with localcontext() as context:
        context.prec = 100
        ending_total = sum(balances.values(), Decimal(0))
        expected_total = twin.total_realized_capital_usd + gain - loss
        residual = ending_total - expected_total
    if residual != 0:
        raise CiboCompoundCapitalError(
            "GEN-C10 scenario violates realized-capital conservation"
        )
    protected_floor = balances[
        Genc10EconomicBucket.RETIRED_TO_PROTECTED_FLOOR
    ]
    if protected_floor < twin.protected_floor_usd:
        raise CiboCompoundCapitalError(
            "GEN-C10 scenario cannot reduce protected floor"
        )

    with localcontext() as context:
        context.prec = 100
        total_stop = (
            twin.total_stop_risk_capacity_usd
            + scenario.stop_risk_capacity_delta_usd
        )
        used_stop = twin.used_stop_risk_usd + scenario.stop_risk_usage_delta_usd
        total_margin = (
            twin.total_margin_capacity_usd
            + scenario.margin_capacity_delta_usd
        )
        used_margin = twin.used_margin_usd + scenario.margin_usage_delta_usd
        stop_headroom = total_stop - used_stop
        margin_headroom = total_margin - used_margin
    for value, name in (
        (total_stop, "projected total stop risk"),
        (used_stop, "projected used stop risk"),
        (total_margin, "projected total margin"),
        (used_margin, "projected used margin"),
    ):
        _money(value, name)
    if used_stop > total_stop:
        raise CiboCompoundCapitalError(
            "GEN-C10 scenario exceeds projected stop-risk capacity"
        )
    if used_margin > total_margin:
        raise CiboCompoundCapitalError(
            "GEN-C10 scenario exceeds projected margin capacity"
        )

    known_ids = {item.option_id for item in twin.known_options}
    if not set(scenario.surviving_known_option_ids).issubset(known_ids):
        raise CiboCompoundCapitalError(
            "GEN-C10 scenario references unknown future option"
        )

    ordered = tuple(
        (bucket, balances[bucket]) for bucket in Genc10EconomicBucket
    )
    return Genc10ProjectedTwinState(
        twin_id=twin.twin_id,
        scenario_id=scenario.scenario_id,
        world_kind=scenario.kind,
        projected_at=projected_at,
        economic_buckets=ordered,
        total_realized_capital_usd=ending_total,
        settled_gain_usd=gain,
        realized_loss_usd=loss,
        conservation_residual_usd=residual,
        protected_floor_usd=protected_floor,
        total_stop_risk_capacity_usd=total_stop,
        used_stop_risk_usd=used_stop,
        stop_risk_headroom_usd=stop_headroom,
        total_margin_capacity_usd=total_margin,
        used_margin_usd=used_margin,
        margin_headroom_usd=margin_headroom,
        surviving_known_option_ids=(
            scenario.surviving_known_option_ids
        ),
        hypothetical_new_option_count=(
            scenario.hypothetical_new_option_count
        ),
        provider_constraints_changed=(
            scenario.provider_constraints_changed
        ),
        transition_uncertainty_calibrated=False,
        market_probability_claimed=False,
        actual_future_outcome_used=False,
        productive_authority=False,
    )


def integrated_capital_truth_sha256(
    truth: IntegratedCapitalTruth,
) -> str:
    payload = {
        "account": {
            "provider_key": truth.account_identity.provider_key,
            "account_ref": truth.account_identity.account_ref,
            "environment": truth.account_identity.environment.value,
            "provider_program": truth.account_identity.provider_program,
        },
        "source_ledger_sha256": truth.source_ledger_sha256,
        "compound_cycle_state_sha256": truth.compound_cycle_state_sha256,
        "realized_profit_source_ids": list(
            truth.realized_profit_source_ids
        ),
        "admission_lot_ids": list(truth.admission_lot_ids),
        "protected_open_source_ids": list(
            truth.protected_open_source_ids
        ),
        "realized_profit_proven_usd": format(
            truth.realized_profit_proven_usd,
            "f",
        ),
        "realized_profit_nonconsumed_usd": format(
            truth.realized_profit_nonconsumed_usd,
            "f",
        ),
        "compound_current_economic_value_usd": format(
            truth.compound_current_economic_value_usd,
            "f",
        ),
        "protected_open_capacity_usd": format(
            truth.protected_open_capacity_usd,
            "f",
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _observed_buckets(
    state: CiboCompoundCycleState,
) -> tuple[tuple[Genc10EconomicBucket, Decimal], ...]:
    values = {
        bucket: Decimal(0) for bucket in Genc10EconomicBucket
    }
    values[Genc10EconomicBucket.ORIGINAL_BASE] = (
        state.current_original_base_usd
    )
    for compound_state, bucket in _COMPOUND_BUCKET_MAP.items():
        values[bucket] = state.compound_ledger.balance(compound_state)
    return tuple((bucket, values[bucket]) for bucket in Genc10EconomicBucket)


def _generation_balances(
    state: CiboCompoundCycleState,
) -> tuple[tuple[int, Decimal], ...]:
    totals: dict[int, Decimal] = {}
    for lot in state.compound_ledger.active_lots:
        if lot.state is CompoundCapitalState.CONSUMED:
            continue
        totals[lot.generation] = (
            totals.get(lot.generation, Decimal(0)) + lot.amount_usd
        )
    return tuple(sorted(totals.items()))


def _source_capacity_states(
    ledger: CapitalSourceLedger,
) -> tuple[Genc10SourceCapacityState, ...]:
    rows: list[Genc10SourceCapacityState] = []
    for dimension in CapitalCapacityDimension:
        scoped = tuple(
            item
            for item in ledger.accounts
            if capital_source_dimension(item.source) is dimension
        )
        rows.append(
            Genc10SourceCapacityState(
                dimension=dimension,
                proven=sum(
                    (item.proven_amount_usd for item in scoped),
                    Decimal(0),
                ),
                available=sum(
                    (item.available_usd for item in scoped),
                    Decimal(0),
                ),
                reserved=sum(
                    (item.reserved_usd for item in scoped),
                    Decimal(0),
                ),
                deployed=sum(
                    (item.deployed_usd for item in scoped),
                    Decimal(0),
                ),
                consumed=sum(
                    (item.consumed_usd for item in scoped),
                    Decimal(0),
                ),
            )
        )
    return tuple(rows)


def _consume_bucket(
    balances: dict[Genc10EconomicBucket, Decimal],
    bucket: Genc10EconomicBucket,
    amount: Decimal,
) -> None:
    if balances[bucket] < amount:
        raise CiboCompoundCapitalError(
            "GEN-C10 scenario flow exceeds source bucket"
        )
    balances[bucket] -= amount
