"""AGRI-3 contract-chain and roll intelligence for Shared cognition.

All thresholds are explicit policy inputs with evidence. No provider symbols,
execution actions, continuous-series construction or relational claims are
owned here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.agricultural_instrument_identity import (
    AgriculturalFuturesContractQualification,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


class AgriculturalContractChainError(ValueError):
    """AGRI-3 contract-chain/roll invariant failed closed."""


class CommodityRollState(StrEnum):
    STABLE_FRONT_CONTRACT = "STABLE_FRONT_CONTRACT"
    LIQUIDITY_MIGRATION = "LIQUIDITY_MIGRATION"
    ROLL_WINDOW = "ROLL_WINDOW"
    FRONT_CONTRACT_DECAY = "FRONT_CONTRACT_DECAY"
    CONTRACT_TRANSITION = "CONTRACT_TRANSITION"
    DELIVERY_PROXIMITY = "DELIVERY_PROXIMITY"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class AgriculturalContractChain:
    """One underlying agricultural reference with ordered dated contracts."""

    chain_id: str
    reference_identity_id: EconomicIdentityId
    contracts: tuple[AgriculturalFuturesContractQualification, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.chain_id.strip():
            raise AgriculturalContractChainError(
                "contract chain id must be non-empty"
            )
        if not isinstance(self.reference_identity_id, EconomicIdentityId):
            raise AgriculturalContractChainError(
                "contract chain reference must be UMI EconomicIdentityId"
            )
        if not self.contracts:
            raise AgriculturalContractChainError(
                "contract chain requires at least one dated contract"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise AgriculturalContractChainError(
                "contract chain provenance must be unique and canonical"
            )

        identities = tuple(
            item.economic_identity.identity_id for item in self.contracts
        )
        if len(identities) != len(set(identities)):
            raise AgriculturalContractChainError(
                "contract chain cannot contain duplicate economic identities"
            )
        months = tuple(
            (item.contract_year, item.contract_month)
            for item in self.contracts
        )
        if months != tuple(sorted(months)):
            raise AgriculturalContractChainError(
                "contract chain must be ordered by contract month"
            )
        if len(months) != len(set(months)):
            raise AgriculturalContractChainError(
                "contract chain cannot contain duplicate contract months"
            )
        for item in self.contracts:
            reference_id = (
                item.agricultural_reference.economic_identity.identity_id
            )
            if reference_id != self.reference_identity_id:
                raise AgriculturalContractChainError(
                    "contract chain cannot mix agricultural references"
                )

    def fingerprint(self) -> str:
        payload = {
            "chain_id": self.chain_id,
            "reference_identity_id": (
                self.reference_identity_id.logical_values()
            ),
            "contracts": [
                {
                    "identity_id": item.economic_identity.identity_id.logical_values(),
                    "year": item.contract_year,
                    "month": item.contract_month,
                    "last_trade_date": (
                        item.commodity_contract.futures.last_trade_date.isoformat()
                        if item.commodity_contract.futures.last_trade_date
                        is not None
                        else None
                    ),
                    "expiry_date": (
                        item.commodity_contract.futures.expiry_date.isoformat()
                    ),
                }
                for item in self.contracts
            ],
            "provenance_refs": self.provenance_refs,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ContractLiquiditySignal:
    """Contract-local causal liquidity facts; lower rank means more liquid."""

    contract_identity_id: EconomicIdentityId
    observed_at: datetime
    evidence_cutoff_at: datetime
    volume_rank: int
    open_interest_rank: int
    volume_change_bps: int | None
    open_interest_change_bps: int | None
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.contract_identity_id, EconomicIdentityId):
            raise AgriculturalContractChainError(
                "liquidity signal contract id must be UMI EconomicIdentityId"
            )
        for value in (self.observed_at, self.evidence_cutoff_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise AgriculturalContractChainError(
                    "liquidity signal timestamps must be timezone-aware"
                )
        if self.evidence_cutoff_at > self.observed_at:
            raise AgriculturalContractChainError(
                "future liquidity evidence is forbidden"
            )
        for name in ("volume_rank", "open_interest_rank"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise AgriculturalContractChainError(
                    f"{name} must be positive int"
                )
        for name in ("volume_change_bps", "open_interest_change_bps"):
            value = getattr(self, name)
            if value is not None:
                if type(value) is not int or value < -10_000:
                    raise AgriculturalContractChainError(
                        f"{name} must be int >= -10000 or None"
                    )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise AgriculturalContractChainError(
                "liquidity signal provenance must be canonical"
            )


@dataclass(frozen=True, slots=True)
class AgriculturalRollPolicy:
    """Versioned roll classification policy; no hidden global thresholds."""

    version: str
    roll_window_days: int
    delivery_proximity_days: int
    front_decay_threshold_bps: int
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise AgriculturalContractChainError(
                "roll policy version must be non-empty"
            )
        for name in (
            "roll_window_days",
            "delivery_proximity_days",
            "front_decay_threshold_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise AgriculturalContractChainError(
                    f"{name} must be non-negative int"
                )
        if self.front_decay_threshold_bps > 10_000:
            raise AgriculturalContractChainError(
                "front_decay_threshold_bps must be <= 10000"
            )
        if self.delivery_proximity_days > self.roll_window_days:
            raise AgriculturalContractChainError(
                "delivery proximity cannot exceed roll window"
            )
        if not self.provenance_refs:
            raise AgriculturalContractChainError(
                "roll policy requires evidence provenance"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise AgriculturalContractChainError(
                "roll policy provenance must be canonical"
            )

    def fingerprint(self) -> str:
        payload = {
            "version": self.version,
            "roll_window_days": self.roll_window_days,
            "delivery_proximity_days": self.delivery_proximity_days,
            "front_decay_threshold_bps": self.front_decay_threshold_bps,
            "provenance_refs": self.provenance_refs,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CommodityRollAssessment:
    as_of: datetime
    state: CommodityRollState
    chain_fingerprint: str
    policy_fingerprint: str
    front_contract_id: EconomicIdentityId | None
    next_contract_id: EconomicIdentityId | None
    most_liquid_contract_id: EconomicIdentityId | None
    days_to_front_transition: int | None
    provenance_refs: tuple[str, ...]
    relational_claims_authorized: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise AgriculturalContractChainError(
                "roll assessment as_of must be timezone-aware"
            )
        for name in ("chain_fingerprint", "policy_fingerprint"):
            value = getattr(self, name)
            if len(value) != 64:
                raise AgriculturalContractChainError(
                    f"{name} must be sha256 hex"
                )
            try:
                int(value, 16)
            except ValueError as exc:
                raise AgriculturalContractChainError(
                    f"{name} must be sha256 hex"
                ) from exc
        if (
            self.days_to_front_transition is not None
            and self.days_to_front_transition < 0
        ):
            raise AgriculturalContractChainError(
                "days_to_front_transition cannot be negative"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise AgriculturalContractChainError(
                "roll assessment provenance must be canonical"
            )
        if self.relational_claims_authorized or self.execution_authority:
            raise AgriculturalContractChainError(
                "roll cognition cannot authorize relation or execution"
            )


@dataclass(frozen=True, slots=True)
class AgriculturalActiveContractSelection:
    """Explicitly preserve three contract concepts that may differ."""

    as_of: datetime
    front_calendar_contract_id: EconomicIdentityId
    most_liquid_contract_id: EconomicIdentityId
    economic_reference_contract_id: EconomicIdentityId
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise AgriculturalContractChainError(
                "active contract selection as_of must be timezone-aware"
            )
        for name in (
            "front_calendar_contract_id",
            "most_liquid_contract_id",
            "economic_reference_contract_id",
        ):
            if not isinstance(getattr(self, name), EconomicIdentityId):
                raise AgriculturalContractChainError(
                    f"{name} must be UMI EconomicIdentityId"
                )
        if not self.provenance_refs:
            raise AgriculturalContractChainError(
                "active contract selection requires provenance"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise AgriculturalContractChainError(
                "active contract selection provenance must be canonical"
            )


def _transition_date(
    contract: AgriculturalFuturesContractQualification,
) -> date:
    futures = contract.commodity_contract.futures
    candidates = [futures.expiry_date]
    if futures.last_trade_date is not None:
        candidates.append(futures.last_trade_date)
    if futures.first_notice_date is not None:
        candidates.append(futures.first_notice_date)
    return min(candidates)


def _active_contracts(
    chain: AgriculturalContractChain,
    *,
    evaluation_date: date,
) -> tuple[AgriculturalFuturesContractQualification, ...]:
    return tuple(
        item
        for item in chain.contracts
        if _transition_date(item) >= evaluation_date
    )


def assess_agricultural_roll_state(
    *,
    chain: AgriculturalContractChain,
    signals: tuple[ContractLiquiditySignal, ...],
    evaluation_at: datetime,
    policy: AgriculturalRollPolicy,
    previous_liquidity_leader_id: EconomicIdentityId | None = None,
) -> CommodityRollAssessment:
    """Classify roll state with explicit chronology and policy evidence."""

    if evaluation_at.tzinfo is None or evaluation_at.utcoffset() is None:
        raise AgriculturalContractChainError(
            "roll evaluation_at must be timezone-aware"
        )
    known_ids = {
        item.economic_identity.identity_id for item in chain.contracts
    }
    signal_by_id: dict[EconomicIdentityId, ContractLiquiditySignal] = {}
    for signal in signals:
        if signal.contract_identity_id not in known_ids:
            raise AgriculturalContractChainError(
                "liquidity signal references contract outside chain"
            )
        if signal.observed_at > evaluation_at:
            raise AgriculturalContractChainError(
                "future liquidity observation is forbidden"
            )
        if signal.evidence_cutoff_at > evaluation_at:
            raise AgriculturalContractChainError(
                "future liquidity evidence cutoff is forbidden"
            )
        if signal.contract_identity_id in signal_by_id:
            raise AgriculturalContractChainError(
                "roll assessment requires one signal per contract"
            )
        signal_by_id[signal.contract_identity_id] = signal

    active = _active_contracts(
        chain,
        evaluation_date=evaluation_at.date(),
    )
    provenance = tuple(
        sorted(
            set(
                chain.provenance_refs
                + policy.provenance_refs
                + tuple(
                    ref
                    for signal in signals
                    for ref in signal.provenance_refs
                )
            )
        )
    )
    if not active:
        return CommodityRollAssessment(
            as_of=evaluation_at,
            state=CommodityRollState.INSUFFICIENT,
            chain_fingerprint=chain.fingerprint(),
            policy_fingerprint=policy.fingerprint(),
            front_contract_id=None,
            next_contract_id=None,
            most_liquid_contract_id=None,
            days_to_front_transition=None,
            provenance_refs=provenance,
        )

    front = active[0]
    front_id = front.economic_identity.identity_id
    next_contract = active[1] if len(active) > 1 else None
    next_id = (
        None
        if next_contract is None
        else next_contract.economic_identity.identity_id
    )
    days_to_transition = (
        _transition_date(front) - evaluation_at.date()
    ).days

    front_signal = signal_by_id.get(front_id)
    next_signal = (
        None if next_id is None else signal_by_id.get(next_id)
    )
    most_liquid: EconomicIdentityId | None = None
    if front_signal is not None and (
        front_signal.volume_rank == 1
        and front_signal.open_interest_rank == 1
    ):
        most_liquid = front_id
    if next_signal is not None and (
        next_signal.volume_rank == 1
        and next_signal.open_interest_rank == 1
    ):
        if most_liquid is not None:
            most_liquid = None
        else:
            most_liquid = next_id

    state = CommodityRollState.INSUFFICIENT
    if days_to_transition <= policy.delivery_proximity_days:
        state = CommodityRollState.DELIVERY_PROXIMITY
    elif days_to_transition <= policy.roll_window_days:
        state = CommodityRollState.ROLL_WINDOW
    elif front_signal is None:
        state = CommodityRollState.INSUFFICIENT
    elif (
        front_signal.volume_change_bps is not None
        and front_signal.open_interest_change_bps is not None
        and front_signal.volume_change_bps
        <= -policy.front_decay_threshold_bps
        and front_signal.open_interest_change_bps
        <= -policy.front_decay_threshold_bps
    ):
        state = CommodityRollState.FRONT_CONTRACT_DECAY
    elif (
        next_id is not None
        and most_liquid == next_id
        and previous_liquidity_leader_id == front_id
    ):
        state = CommodityRollState.CONTRACT_TRANSITION
    elif next_id is not None and most_liquid == next_id:
        state = CommodityRollState.LIQUIDITY_MIGRATION
    elif most_liquid == front_id:
        state = CommodityRollState.STABLE_FRONT_CONTRACT

    return CommodityRollAssessment(
        as_of=evaluation_at,
        state=state,
        chain_fingerprint=chain.fingerprint(),
        policy_fingerprint=policy.fingerprint(),
        front_contract_id=front_id,
        next_contract_id=next_id,
        most_liquid_contract_id=most_liquid,
        days_to_front_transition=days_to_transition,
        provenance_refs=provenance,
    )


def assert_roll_safe_single_series_structural_claim(
    *,
    previous_contract_id: EconomicIdentityId,
    current_contract_id: EconomicIdentityId,
    roll_state: CommodityRollState,
) -> None:
    """Prevent contract transition/roll gaps from masquerading as market shocks."""

    if previous_contract_id != current_contract_id:
        raise AgriculturalContractChainError(
            "cross-contract discontinuity cannot support structural market claim"
        )
    if roll_state is not CommodityRollState.STABLE_FRONT_CONTRACT:
        raise AgriculturalContractChainError(
            "non-stable roll state cannot support structural market claim"
        )
