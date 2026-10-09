"""Research-only compound-capital identity for CIBO GEN-C1.

This module creates no broker, sizing, Risk, DEMO-governed, LIVE or real-capital
authority. It defines the accounting identity of realized Core profit before
later compounding policies are allowed to exist.

A compound-capital lot can be created only from reconciled terminal settlement
profit. Floating PnL is intentionally absent from the evidence contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import (
    TraderIdentity,
    canonical_trader_lineage,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_four_motor_policy import (
    ZERO,
    FourMotorObservation,
    FourMotorPolicyError,
    FourMotorProposal,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class CiboCompoundCapitalError(ValueError):
    """Compound-capital evidence or identity violates GEN-C1 law."""


class CompoundCapitalState(StrEnum):
    REALIZED_PROFIT = "REALIZED_PROFIT"
    PROTECTED_PROFIT = "PROTECTED_PROFIT"
    COMPOUNDABLE = "COMPOUNDABLE"
    STRATEGIC_RESERVE = "STRATEGIC_RESERVE"
    OPPORTUNITY_RESERVE = "OPPORTUNITY_RESERVE"
    ACTIVE_COMPOUND_CAPACITY = "ACTIVE_COMPOUND_CAPACITY"
    DEPLOYED_COMPOUND_CAPITAL = "DEPLOYED_COMPOUND_CAPITAL"
    RELEASED_COMPOUND_CAPITAL = "RELEASED_COMPOUND_CAPITAL"
    RETIRED_TO_PROTECTED_FLOOR = "RETIRED_TO_PROTECTED_FLOOR"
    CONSUMED = "CONSUMED"


class CompoundProtectionClass(StrEnum):
    ACCOUNTING_PROTECTED = "ACCOUNTING_PROTECTED"
    POLICY_PROTECTED = "POLICY_PROTECTED"
    BROKER_GUARANTEED = "BROKER_GUARANTEED"


@dataclass(frozen=True, slots=True)
class CompoundRealizedProfitEvidence:
    evidence_id: str
    account_identity: CiboAccountCapitalIdentity
    origin_trader: TraderIdentity
    signal_fingerprint: str
    position_id: int
    settlement_deal_ids: tuple[int, ...]
    realized_net_profit_usd: Decimal
    realized_at: datetime
    source_settlement_sha256: str
    settlement_reconciled: bool
    position_closed: bool
    floating_pnl_used_as_capital: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.signal_fingerprint:
            raise CiboCompoundCapitalError(
                "compound realized-profit evidence identity is required"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "compound evidence account identity is invalid"
            )
        object.__setattr__(
            self,
            "origin_trader",
            canonical_trader_lineage(
                self.origin_trader,
                field_name="origin_trader",
            ),
        )
        if (
            not isinstance(self.position_id, int)
            or isinstance(self.position_id, bool)
            or self.position_id <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound evidence position_id must be positive int"
            )
        if (
            not self.settlement_deal_ids
            or len(self.settlement_deal_ids)
            != len(set(self.settlement_deal_ids))
            or any(
                not isinstance(item, int)
                or isinstance(item, bool)
                or item <= 0
                for item in self.settlement_deal_ids
            )
        ):
            raise CiboCompoundCapitalError(
                "compound evidence deal ids must be unique positive ints"
            )
        if (
            not isinstance(self.realized_net_profit_usd, Decimal)
            or not self.realized_net_profit_usd.is_finite()
            or self.realized_net_profit_usd <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound evidence requires positive realized net profit"
            )
        _aware(self.realized_at, "realized_at")
        if _SHA256_RE.fullmatch(self.source_settlement_sha256) is None:
            raise CiboCompoundCapitalError(
                "compound evidence settlement digest is invalid"
            )
        for name in (
            "settlement_reconciled",
            "position_closed",
            "floating_pnl_used_as_capital",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"compound evidence {name} must be bool"
                )


@dataclass(frozen=True, slots=True)
class CompoundCapitalLot:
    lot_id: str
    account_identity: CiboAccountCapitalIdentity
    amount_usd: Decimal
    state: CompoundCapitalState
    generation: int
    origin_evidence_id: str
    origin_trader: TraderIdentity
    origin_signal_fingerprint: str
    origin_position_id: int
    origin_deal_ids: tuple[int, ...]
    realized_at: datetime
    created_at: datetime
    parent_lot_ids: tuple[str, ...] = ()
    core_owned: bool = True
    runtime_authority: bool = False

    def __post_init__(self) -> None:
        if not self.lot_id or not self.origin_evidence_id:
            raise CiboCompoundCapitalError(
                "compound lot identity/provenance is required"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "compound lot account identity is invalid"
            )
        if (
            not isinstance(self.amount_usd, Decimal)
            or not self.amount_usd.is_finite()
            or self.amount_usd <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound lot amount must be finite positive Decimal"
            )
        if type(self.state) is not CompoundCapitalState:
            raise CiboCompoundCapitalError(
                "compound lot state is invalid"
            )
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 1
        ):
            raise CiboCompoundCapitalError(
                "compound lot generation must be positive int"
            )
        object.__setattr__(
            self,
            "origin_trader",
            canonical_trader_lineage(
                self.origin_trader,
                field_name="origin_trader",
            ),
        )
        if not self.origin_signal_fingerprint:
            raise CiboCompoundCapitalError(
                "compound lot origin signal is required"
            )
        if (
            not isinstance(self.origin_position_id, int)
            or isinstance(self.origin_position_id, bool)
            or self.origin_position_id <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound lot origin position must be positive int"
            )
        if (
            not self.origin_deal_ids
            or len(self.origin_deal_ids) != len(set(self.origin_deal_ids))
        ):
            raise CiboCompoundCapitalError(
                "compound lot origin deal ids must be unique/non-empty"
            )
        _aware(self.realized_at, "realized_at")
        _aware(self.created_at, "created_at")
        if self.created_at < self.realized_at:
            raise CiboCompoundCapitalError(
                "compound lot cannot predate realized settlement"
            )
        if len(self.parent_lot_ids) != len(set(self.parent_lot_ids)):
            raise CiboCompoundCapitalError(
                "compound lot parent ids must be unique"
            )
        if self.lot_id in self.parent_lot_ids:
            raise CiboCompoundCapitalError(
                "compound lot cannot parent itself"
            )
        if type(self.core_owned) is not bool:
            raise CiboCompoundCapitalError(
                "compound lot core_owned must be bool"
            )
        if type(self.runtime_authority) is not bool:
            raise CiboCompoundCapitalError(
                "compound lot runtime_authority must be bool"
            )
        if not self.core_owned or self.runtime_authority:
            raise CiboCompoundCapitalError(
                "GEN-C1 lots are Core-owned research evidence only"
            )


def create_realized_profit_lot(
    evidence: CompoundRealizedProfitEvidence,
    *,
    lot_id: str,
    created_at: datetime,
    parent_lots: tuple[CompoundCapitalLot, ...] = (),
) -> CompoundCapitalLot:
    """Create GEN-1+ compound capital only from terminal realized settlement."""

    if not isinstance(evidence, CompoundRealizedProfitEvidence):
        raise CiboCompoundCapitalError(
            "canonical realized-profit evidence is required"
        )
    _aware(created_at, "created_at")
    if not evidence.settlement_reconciled:
        raise CiboCompoundCapitalError(
            "unreconciled settlement cannot create compound capital"
        )
    if not evidence.position_closed:
        raise CiboCompoundCapitalError(
            "non-terminal settlement cannot create compound capital"
        )
    if evidence.floating_pnl_used_as_capital:
        raise CiboCompoundCapitalError(
            "floating PnL cannot create compound capital"
        )
    if created_at < evidence.realized_at:
        raise CiboCompoundCapitalError(
            "compound lot cannot be created before realization"
        )
    if not isinstance(parent_lots, tuple) or any(
        not isinstance(item, CompoundCapitalLot)
        for item in parent_lots
    ):
        raise CiboCompoundCapitalError(
            "compound parent lots must be canonical tuple"
        )
    parent_ids = tuple(item.lot_id for item in parent_lots)
    if len(parent_ids) != len(set(parent_ids)):
        raise CiboCompoundCapitalError(
            "compound parent lots must be unique"
        )
    if any(
        item.account_identity != evidence.account_identity
        for item in parent_lots
    ):
        raise CiboCompoundCapitalError(
            "compound parents cannot cross account domains"
        )
    generation = (
        1
        if not parent_lots
        else max(item.generation for item in parent_lots) + 1
    )
    return CompoundCapitalLot(
        lot_id=lot_id,
        account_identity=evidence.account_identity,
        amount_usd=evidence.realized_net_profit_usd,
        state=CompoundCapitalState.REALIZED_PROFIT,
        generation=generation,
        origin_evidence_id=evidence.evidence_id,
        origin_trader=evidence.origin_trader,
        origin_signal_fingerprint=evidence.signal_fingerprint,
        origin_position_id=evidence.position_id,
        origin_deal_ids=evidence.settlement_deal_ids,
        realized_at=evidence.realized_at,
        created_at=created_at,
        parent_lot_ids=parent_ids,
        core_owned=True,
        runtime_authority=False,
    )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"compound {name} must be timezone-aware"
        )



def propose_p0_compound_vote(observation: FourMotorObservation) -> FourMotorProposal:
    """Use actual reconciled NAV, not legacy loss-streak penalties.

    Settled losses must reduce QORE NAV exactly once through the verified
    cashflow ledger. Risk reservations and floating liabilities remain hard
    economic constraints; an arbitrary THREE_SETTLED_LOSSES_HAIR_CUT is not.
    """
    if not isinstance(observation, FourMotorObservation):
        raise FourMotorPolicyError("canonical observation required")
    cap = min(observation.risk_cash_remaining_usd,
              observation.base_entry_budget_usd)
    reasons = ("RECONCILED_ONLY_NET_QORE_NAV",
               "PROTECTED_AND_FLOAT_LOSS_AND_RESERVATION_DEDUCTED",
               "NO_LEGACY_LOSS_STREAK_PENALTY",
               "QDLE_IS_SOLE_PHYSICAL_LOT_AUTHORITY")
    return FourMotorProposal("CIBO_COMPOUND", observation,
                             {"approved_risk_usd": str(cap)}, reasons)
