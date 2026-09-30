"""Path-dependent CIBO compound-cycle state and accounting mechanics.

This module joins terminal settlement evidence to GEN-C1/2/3 accounting without
creating a new capital policy.  It is research-only and grants no sizing, Risk,
execution, LIVE, real-capital or merge authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementState
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_floor import (
    ProtectedCapitalFloorLedger,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioLedger,
)
from qore.infrastructure.cibo_core_compound_portfolio import (
    AccountCoreCompoundPortfolio,
)


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"compound cycle {name} must be timezone-aware"
        )


def _money(value: Decimal, name: str, *, positive: bool = False) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
        or (positive and value <= 0)
    ):
        qualifier = "positive" if positive else "non-negative"
        raise CiboCompoundCapitalError(
            f"compound cycle {name} must be finite {qualifier} Decimal"
        )


def settlement_sha256(state: CmaSettlementState) -> str:
    """Canonical digest of one reconciled settlement lifecycle."""

    if not isinstance(state, CmaSettlementState):
        raise CiboCompoundCapitalError(
            "compound cycle settlement must be canonical"
        )
    payload = {
        "signal_fingerprint": state.signal_fingerprint,
        "position_id": state.position_id,
        "position_closed": state.position_closed,
        "records": [
            {
                "event": item.event,
                "deal_id": item.deal_id,
                "signal_fingerprint": item.signal_fingerprint,
                "position_id": item.position_id,
                "net_profit_usd": format(item.net_profit_usd, "f"),
                "position_open_after": item.position_open_after,
            }
            for item in state.records
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def require_terminal_settlement(state: CmaSettlementState) -> None:
    if not isinstance(state, CmaSettlementState):
        raise CiboCompoundCapitalError(
            "compound cycle requires canonical settlement state"
        )
    if not state.position_closed or not state.records:
        raise CiboCompoundCapitalError(
            "compound cycle requires terminal non-empty settlement"
        )


@dataclass(frozen=True, slots=True)
class CompoundCycleSettlementRecord:
    event_id: str
    occurred_at: datetime
    source_kind: str
    trader_id: TraderLineage
    signal_fingerprint: str
    position_id: int
    settlement_sha256: str
    realized_net_pnl_usd: Decimal
    deployment_id: str | None = None

    def __post_init__(self) -> None:
        if self.source_kind not in {"BASE_CAPITAL", "COMPOUND_CAPITAL"}:
            raise CiboCompoundCapitalError(
                "compound cycle settlement source kind is invalid"
            )
        if not self.event_id or not self.signal_fingerprint:
            raise CiboCompoundCapitalError(
                "compound cycle settlement identity is required"
            )
        _aware(self.occurred_at, "settlement occurred_at")
        if type(self.trader_id) is not TraderLineage:
            raise CiboCompoundCapitalError(
                "compound cycle settlement Trader is invalid"
            )
        if (
            not isinstance(self.position_id, int)
            or isinstance(self.position_id, bool)
            or self.position_id <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound cycle settlement position must be positive int"
            )
        if (
            not self.settlement_sha256.startswith("sha256:")
            or len(self.settlement_sha256) != 71
        ):
            raise CiboCompoundCapitalError(
                "compound cycle settlement digest is invalid"
            )
        if (
            not isinstance(self.realized_net_pnl_usd, Decimal)
            or not self.realized_net_pnl_usd.is_finite()
        ):
            raise CiboCompoundCapitalError(
                "compound cycle realized PnL must be finite Decimal"
            )
        if self.source_kind == "COMPOUND_CAPITAL":
            if not self.deployment_id:
                raise CiboCompoundCapitalError(
                    "compound settlement requires deployment id"
                )
        elif self.deployment_id is not None:
            raise CiboCompoundCapitalError(
                "base settlement cannot carry deployment id"
            )


@dataclass(frozen=True, slots=True)
class CompoundCycleMarketRecord:
    event_id: str
    occurred_at: datetime
    decision_id: str
    action: str
    candidate_id: str | None
    amount_usd: Decimal
    scarcity_event_id: str
    portfolio_state_sha256: str
    t19_ledger_sha256: str

    def __post_init__(self) -> None:
        if (
            not self.event_id
            or not self.decision_id
            or not self.action
            or not self.scarcity_event_id
        ):
            raise CiboCompoundCapitalError(
                "compound cycle market record identity is required"
            )
        _aware(self.occurred_at, "market occurred_at")
        _money(self.amount_usd, "market amount")
        for name in (
            "portfolio_state_sha256",
            "t19_ledger_sha256",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboCompoundCapitalError(
                    f"compound cycle market {name} is invalid"
                )


@dataclass(frozen=True, slots=True)
class CompoundCycleDeployment:
    deployment_id: str
    market_event_id: str
    decision_id: str
    candidate_id: str
    deployed_at: datetime
    trader_id: TraderLineage
    signal_fingerprint: str
    source_lot_id: str
    deployed_lot_id: str
    amount_usd: Decimal
    source_generation: int
    stop_risk_usd: Decimal
    margin_usd: Decimal
    settled: bool = False
    settlement_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "deployment_id",
            "market_event_id",
            "decision_id",
            "candidate_id",
            "signal_fingerprint",
            "source_lot_id",
            "deployed_lot_id",
        ):
            if not getattr(self, name):
                raise CiboCompoundCapitalError(
                    f"compound cycle deployment {name} is required"
                )
        _aware(self.deployed_at, "deployment deployed_at")
        if type(self.trader_id) is not TraderLineage:
            raise CiboCompoundCapitalError(
                "compound cycle deployment Trader is invalid"
            )
        for name in ("amount_usd", "stop_risk_usd", "margin_usd"):
            _money(getattr(self, name), name, positive=True)
        if (
            not isinstance(self.source_generation, int)
            or isinstance(self.source_generation, bool)
            or self.source_generation < 1
        ):
            raise CiboCompoundCapitalError(
                "compound cycle source generation must be positive int"
            )
        if type(self.settled) is not bool:
            raise CiboCompoundCapitalError(
                "compound cycle settled flag must be bool"
            )
        if self.settled != (self.settlement_sha256 is not None):
            raise CiboCompoundCapitalError(
                "compound cycle settlement flag/digest drift"
            )


@dataclass(frozen=True, slots=True)
class CiboCompoundCycleState:
    account_identity: CiboAccountCapitalIdentity
    opening_original_base_usd: Decimal
    current_original_base_usd: Decimal
    compound_ledger: CompoundPortfolioLedger
    floor_ledger: ProtectedCapitalFloorLedger
    t19_ledger: PortfolioAllocationLedger
    settlements: tuple[CompoundCycleSettlementRecord, ...] = ()
    market_records: tuple[CompoundCycleMarketRecord, ...] = ()
    deployments: tuple[CompoundCycleDeployment, ...] = ()
    event_ids: tuple[str, ...] = ()
    cumulative_realized_gains_usd: Decimal = Decimal(0)
    cumulative_realized_losses_usd: Decimal = Decimal(0)
    last_event_at: datetime | None = None
    runtime_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "compound cycle account identity is invalid"
            )
        for name in (
            "opening_original_base_usd",
            "current_original_base_usd",
            "cumulative_realized_gains_usd",
            "cumulative_realized_losses_usd",
        ):
            _money(getattr(self, name), name)
        if self.opening_original_base_usd <= 0:
            raise CiboCompoundCapitalError(
                "compound cycle opening original base must be positive"
            )
        if self.compound_ledger.account_identity != self.account_identity:
            raise CiboCompoundCapitalError(
                "compound cycle compound-ledger account drift"
            )
        if self.floor_ledger.account_identity != self.account_identity:
            raise CiboCompoundCapitalError(
                "compound cycle floor-ledger account drift"
            )
        if not isinstance(self.t19_ledger, PortfolioAllocationLedger):
            raise CiboCompoundCapitalError(
                "compound cycle T19 ledger is invalid"
            )
        if len(self.event_ids) != len(set(self.event_ids)):
            raise CiboCompoundCapitalError(
                "compound cycle event ids must be unique"
            )
        settlement_ids = tuple(
            item.settlement_sha256 for item in self.settlements
        )
        if len(settlement_ids) != len(set(settlement_ids)):
            raise CiboCompoundCapitalError(
                "compound cycle settlement evidence cannot be reused"
            )
        market_event_ids = tuple(item.event_id for item in self.market_records)
        if len(market_event_ids) != len(set(market_event_ids)):
            raise CiboCompoundCapitalError(
                "compound cycle market event ids must be unique"
            )
        market_decision_ids = tuple(
            item.decision_id for item in self.market_records
        )
        if len(market_decision_ids) != len(set(market_decision_ids)):
            raise CiboCompoundCapitalError(
                "compound cycle market decision ids must be unique"
            )
        deployment_ids = tuple(item.deployment_id for item in self.deployments)
        if len(deployment_ids) != len(set(deployment_ids)):
            raise CiboCompoundCapitalError(
                "compound cycle deployment ids must be unique"
            )
        if self.last_event_at is not None:
            _aware(self.last_event_at, "last_event_at")
        for name in (
            "runtime_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool or getattr(self, name):
                raise CiboCompoundCapitalError(
                    "compound cycle cannot carry productive authority"
                )
        _ = self.core_portfolio
        if self.closing_realized_capital_usd != self.accounting_identity_usd:
            raise CiboCompoundCapitalError(
                "compound cycle accounting identity drift"
            )

    @property
    def core_portfolio(self) -> AccountCoreCompoundPortfolio:
        return AccountCoreCompoundPortfolio(
            account_identity=self.account_identity,
            compound_ledger=self.compound_ledger,
            protected_floor_ledger=self.floor_ledger,
        )

    @property
    def closing_realized_capital_usd(self) -> Decimal:
        return (
            self.current_original_base_usd
            + self.compound_ledger.current_economic_value_usd
        )

    @property
    def accounting_identity_usd(self) -> Decimal:
        return (
            self.opening_original_base_usd
            + self.cumulative_realized_gains_usd
            - self.cumulative_realized_losses_usd
        )

    @property
    def original_capital_dependence_ratio(self) -> Decimal:
        closing = self.closing_realized_capital_usd
        if closing == 0:
            return Decimal(0)
        return self.current_original_base_usd / closing

    @property
    def highest_generation(self) -> int:
        generations = tuple(
            item.generation
            for item in self.compound_ledger.active_lots
            if item.state is not CompoundCapitalState.CONSUMED
        )
        return max(generations) if generations else 0


def initialize_compound_cycle(
    *,
    account_identity: CiboAccountCapitalIdentity,
    opening_original_base_usd: Decimal,
    t19_ledger: PortfolioAllocationLedger,
) -> CiboCompoundCycleState:
    _money(opening_original_base_usd, "opening base", positive=True)
    return CiboCompoundCycleState(
        account_identity=account_identity,
        opening_original_base_usd=opening_original_base_usd,
        current_original_base_usd=opening_original_base_usd,
        compound_ledger=CompoundPortfolioLedger(
            account_identity=account_identity
        ),
        floor_ledger=ProtectedCapitalFloorLedger(
            account_identity=account_identity
        ),
        t19_ledger=t19_ledger,
    )


def ingest_base_settlement(
    state: CiboCompoundCycleState,
    *,
    event_id: str,
    occurred_at: datetime,
    trader_id: TraderLineage,
    settlement: CmaSettlementState,
) -> CiboCompoundCycleState:
    require_event_order(state, event_id, occurred_at)
    require_terminal_settlement(settlement)
    digest = settlement_sha256(settlement)
    require_new_settlement(state, digest)
    pnl = settlement.realized_net_pnl_usd
    ledger = state.compound_ledger
    base = state.current_original_base_usd
    gains = state.cumulative_realized_gains_usd
    losses = state.cumulative_realized_losses_usd

    if pnl > 0:
        evidence = profit_evidence_from_settlement(
            state=state,
            evidence_id=f"{event_id}:profit",
            occurred_at=occurred_at,
            trader_id=trader_id,
            settlement=settlement,
            settlement_digest=digest,
        )
        lot = create_realized_profit_lot(
            evidence,
            lot_id=f"{event_id}:gen1",
            created_at=occurred_at,
        )
        ledger = ledger.admit_realized_profit(
            lot,
            event_id=f"{event_id}:admit",
            occurred_at=occurred_at,
        )
        gains += pnl
    elif pnl < 0:
        loss = -pnl
        if loss > base:
            raise CiboCompoundCapitalError(
                "base settlement loss exceeds remaining original base"
            )
        base -= loss
        losses += loss

    record = CompoundCycleSettlementRecord(
        event_id=event_id,
        occurred_at=occurred_at,
        source_kind="BASE_CAPITAL",
        trader_id=trader_id,
        signal_fingerprint=settlement.signal_fingerprint,
        position_id=settlement.position_id,
        settlement_sha256=digest,
        realized_net_pnl_usd=pnl,
    )
    return replace(
        state,
        current_original_base_usd=base,
        compound_ledger=ledger,
        settlements=state.settlements + (record,),
        event_ids=state.event_ids + (event_id,),
        cumulative_realized_gains_usd=gains,
        cumulative_realized_losses_usd=losses,
        last_event_at=occurred_at,
    )


def classify_compound_capital(
    state: CiboCompoundCycleState,
    *,
    event_id: str,
    occurred_at: datetime,
    source_lot_id: str,
    to_state: CompoundCapitalState,
    amount_usd: Decimal,
) -> CiboCompoundCycleState:
    require_event_order(state, event_id, occurred_at)
    if to_state in {
        CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL,
    }:
        raise CiboCompoundCapitalError(
            "floor/deployment requires dedicated compound-cycle operation"
        )
    source = state.compound_ledger.lot(source_lot_id)
    remainder = source.amount_usd - amount_usd
    ledger = state.compound_ledger.transition(
        source_lot_id=source_lot_id,
        to_state=to_state,
        amount_usd=amount_usd,
        moved_lot_id=f"{event_id}:moved",
        remainder_lot_id=(
            f"{event_id}:remainder" if remainder > 0 else None
        ),
        event_id=f"{event_id}:transition",
        occurred_at=occurred_at,
    )
    return replace(
        state,
        compound_ledger=ledger,
        event_ids=state.event_ids + (event_id,),
        last_event_at=occurred_at,
    )


def protect_compound_capital(
    state: CiboCompoundCycleState,
    *,
    event_id: str,
    occurred_at: datetime,
    source_lot_id: str,
    amount_usd: Decimal,
) -> CiboCompoundCycleState:
    require_event_order(state, event_id, occurred_at)
    source = state.compound_ledger.lot(source_lot_id)
    remainder = source.amount_usd - amount_usd
    retired_id = f"{event_id}:retired"
    ledger = state.compound_ledger.transition(
        source_lot_id=source_lot_id,
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=amount_usd,
        moved_lot_id=retired_id,
        remainder_lot_id=(
            f"{event_id}:remainder" if remainder > 0 else None
        ),
        event_id=f"{event_id}:retire",
        occurred_at=occurred_at,
    )
    floor = state.floor_ledger.admit_retired_lot(
        ledger.lot(retired_id),
        tranche_id=f"{event_id}:tranche",
        event_id=f"{event_id}:floor-admit",
        admitted_at=occurred_at,
    )
    return replace(
        state,
        compound_ledger=ledger,
        floor_ledger=floor,
        event_ids=state.event_ids + (event_id,),
        last_event_at=occurred_at,
    )


def policy_protect_floor(
    state: CiboCompoundCycleState,
    *,
    event_id: str,
    occurred_at: datetime,
    tranche_id: str,
    policy_id: str,
    policy_sha256: str,
) -> CiboCompoundCycleState:
    require_event_order(state, event_id, occurred_at)
    floor = state.floor_ledger.upgrade_to_policy_protected(
        tranche_id=tranche_id,
        event_id=f"{event_id}:policy",
        occurred_at=occurred_at,
        policy_id=policy_id,
        policy_sha256=policy_sha256,
    )
    return replace(
        state,
        floor_ledger=floor,
        event_ids=state.event_ids + (event_id,),
        last_event_at=occurred_at,
    )


def profit_evidence_from_settlement(
    *,
    state: CiboCompoundCycleState,
    evidence_id: str,
    occurred_at: datetime,
    trader_id: TraderLineage,
    settlement: CmaSettlementState,
    settlement_digest: str,
) -> CompoundRealizedProfitEvidence:
    pnl = settlement.realized_net_pnl_usd
    if pnl <= 0:
        raise CiboCompoundCapitalError(
            "compound profit evidence requires positive realized PnL"
        )
    return CompoundRealizedProfitEvidence(
        evidence_id=evidence_id,
        account_identity=state.account_identity,
        origin_trader=trader_id,
        signal_fingerprint=settlement.signal_fingerprint,
        position_id=settlement.position_id,
        settlement_deal_ids=tuple(
            item.deal_id for item in settlement.records
        ),
        realized_net_profit_usd=pnl,
        realized_at=occurred_at,
        source_settlement_sha256=settlement_digest,
        settlement_reconciled=True,
        position_closed=True,
        floating_pnl_used_as_capital=False,
    )


def require_event_order(
    state: CiboCompoundCycleState,
    event_id: str,
    occurred_at: datetime,
) -> None:
    if not event_id or event_id in state.event_ids:
        raise CiboCompoundCapitalError(
            "compound cycle event id is missing or duplicated"
        )
    _aware(occurred_at, "event occurred_at")
    if state.last_event_at is not None and occurred_at < state.last_event_at:
        raise CiboCompoundCapitalError(
            "compound cycle event chronology is reversed"
        )


def require_new_settlement(
    state: CiboCompoundCycleState,
    digest: str,
) -> None:
    if digest in {item.settlement_sha256 for item in state.settlements}:
        raise CiboCompoundCapitalError(
            "compound cycle settlement evidence already consumed"
        )
