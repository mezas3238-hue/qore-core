"""Non-certifying capital truth for historical CIBO ceiling discovery.

Historical structural outcomes do not contain real broker deal/position ids, so
this ledger must never masquerade as GEN-C1 certified settlement evidence. It
tracks the same account-local economic conservation needed by Native MAX:
original base, realized-profit generations, open stop-risk provenance and
provider-cost reserves. All transitions are chronological and outcome-free
until the explicit settlement function is called.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, localcontext

from qore.infrastructure.account_wide_risk import (
    RiskAuthorization,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    CiboManifestOutcomeSettlement,
)

_INITIAL_CAPITAL_USD = Decimal("60")


def _money(
    value: Decimal,
    name: str,
    *,
    positive: bool = False,
) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
        or (positive and value <= 0)
    ):
        qualifier = "positive" if positive else "non-negative"
        raise CiboCapitalManagementError(
            f"historical ceiling {name} must be finite {qualifier} Decimal"
        )


def _add(*values: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return sum(values, Decimal(0))


def _sub(value: Decimal, *values: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        result = value
        for item in values:
            result -= item
        return result


def _mul(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return left * right


@dataclass(frozen=True, slots=True)
class CiboHistoricalProfitGeneration:
    generation: int
    proven_usd: Decimal
    consumed_usd: Decimal = Decimal(0)
    reserved_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 1
        ):
            raise CiboCapitalManagementError(
                "historical ceiling profit generation must be positive int"
            )
        for name in ("proven_usd", "consumed_usd", "reserved_usd"):
            _money(getattr(self, name), name)
        if _add(self.consumed_usd, self.reserved_usd) > self.proven_usd:
            raise CiboCapitalManagementError(
                "historical ceiling profit generation is over-allocated"
            )

    @property
    def available_usd(self) -> Decimal:
        return _sub(self.proven_usd, self.consumed_usd, self.reserved_usd)

    @property
    def economic_value_usd(self) -> Decimal:
        return _sub(self.proven_usd, self.consumed_usd)


@dataclass(frozen=True, slots=True)
class CiboHistoricalCapitalSlice:
    source: CapitalSource
    generation: int
    stop_risk_reserved_usd: Decimal = Decimal(0)
    provider_cost_reserved_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if self.source not in {
            CapitalSource.ORIGINAL_BASE_CAPITAL,
            CapitalSource.REALIZED_PROFIT,
        }:
            raise CiboCapitalManagementError(
                "historical ceiling slice source must be base or realized profit"
            )
        if (
            self.source is CapitalSource.ORIGINAL_BASE_CAPITAL
            and self.generation != 0
        ):
            raise CiboCapitalManagementError(
                "historical ceiling base slice generation must be zero"
            )
        if (
            self.source is CapitalSource.REALIZED_PROFIT
            and self.generation < 1
        ):
            raise CiboCapitalManagementError(
                "historical ceiling profit slice requires positive generation"
            )
        for name in (
            "stop_risk_reserved_usd",
            "provider_cost_reserved_usd",
        ):
            _money(getattr(self, name), name)
        if self.total_reserved_usd <= 0:
            raise CiboCapitalManagementError(
                "historical ceiling slice must reserve positive capital"
            )

    @property
    def total_reserved_usd(self) -> Decimal:
        return _add(self.stop_risk_reserved_usd, self.provider_cost_reserved_usd)


@dataclass(frozen=True, slots=True)
class CiboHistoricalOpenDeployment:
    authorization_id: str
    signal_fingerprint: str
    trader_id: TraderLineage
    authorized_at: datetime
    authorized_volume: Decimal
    authorized_stop_risk_usd: Decimal
    authorized_margin_usd: Decimal
    provider_cost_usd: Decimal
    slices: tuple[CiboHistoricalCapitalSlice, ...]

    def __post_init__(self) -> None:
        if not self.authorization_id or not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "historical ceiling deployment identity is required"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "historical ceiling deployment trader must be canonical"
            )
        if (
            self.authorized_at.tzinfo is None
            or self.authorized_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "historical ceiling deployment time must be aware"
            )
        for name in (
            "authorized_volume",
            "authorized_stop_risk_usd",
            "authorized_margin_usd",
        ):
            _money(getattr(self, name), name, positive=True)
        _money(self.provider_cost_usd, "provider_cost_usd")
        if not self.slices:
            raise CiboCapitalManagementError(
                "historical ceiling deployment requires capital slices"
            )
        stop = _add(
            *(item.stop_risk_reserved_usd for item in self.slices)
        )
        cost = _add(
            *(item.provider_cost_reserved_usd for item in self.slices)
        )
        if stop != self.authorized_stop_risk_usd:
            raise CiboCapitalManagementError(
                "historical ceiling stop-risk provenance drift"
            )
        if cost != self.provider_cost_usd:
            raise CiboCapitalManagementError(
                "historical ceiling provider-cost provenance drift"
            )

    @property
    def parent_generation(self) -> int:
        return max((item.generation for item in self.slices), default=0)


@dataclass(frozen=True, slots=True)
class CiboHistoricalResearchCapitalState:
    original_base_proven_usd: Decimal = _INITIAL_CAPITAL_USD
    original_base_consumed_usd: Decimal = Decimal(0)
    original_base_reserved_usd: Decimal = Decimal(0)
    profit_generations: tuple[CiboHistoricalProfitGeneration, ...] = ()
    open_deployments: tuple[CiboHistoricalOpenDeployment, ...] = ()
    settlement_sha256s: tuple[str, ...] = ()
    peak_realized_capital_usd: Decimal = _INITIAL_CAPITAL_USD
    cumulative_provider_cost_usd: Decimal = Decimal(0)
    cumulative_gross_profit_usd: Decimal = Decimal(0)
    cumulative_gross_loss_usd: Decimal = Decimal(0)
    non_certifying_research: bool = True

    def __post_init__(self) -> None:
        for name in (
            "original_base_proven_usd",
            "original_base_consumed_usd",
            "original_base_reserved_usd",
            "peak_realized_capital_usd",
            "cumulative_provider_cost_usd",
            "cumulative_gross_profit_usd",
            "cumulative_gross_loss_usd",
        ):
            _money(getattr(self, name), name)
        if self.original_base_proven_usd != _INITIAL_CAPITAL_USD:
            raise CiboCapitalManagementError(
                "historical ceiling opening capital must remain exactly USD60"
            )
        if (
            _add(
                self.original_base_consumed_usd,
                self.original_base_reserved_usd,
            )
            > self.original_base_proven_usd
        ):
            raise CiboCapitalManagementError(
                "historical ceiling base capital is over-allocated"
            )
        generations = tuple(item.generation for item in self.profit_generations)
        if len(generations) != len(set(generations)):
            raise CiboCapitalManagementError(
                "historical ceiling profit generations must be unique"
            )
        signals = tuple(
            item.signal_fingerprint for item in self.open_deployments
        )
        if len(signals) != len(set(signals)):
            raise CiboCapitalManagementError(
                "historical ceiling open deployment signal must be unique"
            )
        if len(self.settlement_sha256s) != len(set(self.settlement_sha256s)):
            raise CiboCapitalManagementError(
                "historical ceiling settlement evidence cannot be reused"
            )
        if type(self.non_certifying_research) is not bool:
            raise CiboCapitalManagementError(
                "historical ceiling research flag must be bool"
            )
        if not self.non_certifying_research:
            raise CiboCapitalManagementError(
                "historical ceiling ledger cannot claim certifying evidence"
            )
        if self.peak_realized_capital_usd < self.realized_capital_usd:
            raise CiboCapitalManagementError(
                "historical ceiling peak is below realized capital"
            )

    @property
    def original_base_available_usd(self) -> Decimal:
        return _sub(
            self.original_base_proven_usd,
            self.original_base_consumed_usd,
            self.original_base_reserved_usd,
        )

    @property
    def original_base_economic_value_usd(self) -> Decimal:
        return _sub(
            self.original_base_proven_usd,
            self.original_base_consumed_usd,
        )

    @property
    def realized_profit_economic_value_usd(self) -> Decimal:
        return _add(
            *(item.economic_value_usd for item in self.profit_generations)
        )

    @property
    def realized_profit_available_usd(self) -> Decimal:
        return _add(
            *(item.available_usd for item in self.profit_generations)
        )

    @property
    def realized_capital_usd(self) -> Decimal:
        return _add(
            self.original_base_economic_value_usd,
            self.realized_profit_economic_value_usd,
        )

    @property
    def open_stop_risk_usd(self) -> Decimal:
        return _add(
            *(item.authorized_stop_risk_usd for item in self.open_deployments)
        )

    @property
    def open_margin_usd(self) -> Decimal:
        return _add(
            *(item.authorized_margin_usd for item in self.open_deployments)
        )

    @property
    def open_provider_cost_reserve_usd(self) -> Decimal:
        return _add(
            *(item.provider_cost_usd for item in self.open_deployments)
        )


def initialize_historical_research_capital() -> CiboHistoricalResearchCapitalState:
    return CiboHistoricalResearchCapitalState()


def reserve_historical_authorization(
    state: CiboHistoricalResearchCapitalState,
    *,
    authorization: RiskAuthorization,
    provider_cost_usd: Decimal,
) -> CiboHistoricalResearchCapitalState:
    """Reserve authorized stop risk plus provider cost with no outcome access."""

    if not isinstance(state, CiboHistoricalResearchCapitalState):
        raise CiboCapitalManagementError(
            "historical ceiling reserve requires canonical research state"
        )
    if not isinstance(authorization, RiskAuthorization):
        raise CiboCapitalManagementError(
            "historical ceiling reserve requires canonical Risk authorization"
        )
    if authorization.decision not in {
        RiskDecision.ALLOW,
        RiskDecision.REDUCE,
    }:
        raise CiboCapitalManagementError(
            "historical ceiling reserve requires Risk ALLOW/REDUCE"
        )
    _money(provider_cost_usd, "provider_cost_usd")
    if any(
        item.signal_fingerprint == authorization.signal_fingerprint
        for item in state.open_deployments
    ):
        raise CiboCapitalManagementError(
            "historical ceiling signal already has open deployment"
        )
    if not authorization.capital_provenance:
        raise CiboCapitalManagementError(
            "historical ceiling authorization lacks capital provenance"
        )

    base_reserved = state.original_base_reserved_usd
    profits = list(state.profit_generations)
    slices: list[CiboHistoricalCapitalSlice] = []

    def reserve_profit(amount: Decimal, *, stop: bool) -> None:
        nonlocal profits
        remaining = amount
        updated: list[CiboHistoricalProfitGeneration] = []
        for lot in sorted(profits, key=lambda item: item.generation):
            take = min(remaining, lot.available_usd)
            if take > 0:
                updated.append(
                    replace(lot, reserved_usd=_add(lot.reserved_usd, take))
                )
                slices.append(
                    CiboHistoricalCapitalSlice(
                        source=CapitalSource.REALIZED_PROFIT,
                        generation=lot.generation,
                        stop_risk_reserved_usd=(take if stop else Decimal(0)),
                        provider_cost_reserved_usd=(
                            Decimal(0) if stop else take
                        ),
                    )
                )
                remaining = _sub(remaining, take)
            else:
                updated.append(lot)
        if remaining > 0:
            raise CiboCapitalManagementError(
                "historical ceiling realized-profit capacity is insufficient"
            )
        profits = updated

    for provenance in authorization.capital_provenance:
        amount = provenance.amount_usd
        if provenance.source_kind == CapitalSource.ORIGINAL_BASE_CAPITAL.value:
            available = _sub(
                state.original_base_proven_usd,
                state.original_base_consumed_usd,
                base_reserved,
            )
            if amount > available:
                raise CiboCapitalManagementError(
                    "historical ceiling base provenance exceeds available capital"
                )
            base_reserved = _add(base_reserved, amount)
            slices.append(
                CiboHistoricalCapitalSlice(
                    source=CapitalSource.ORIGINAL_BASE_CAPITAL,
                    generation=0,
                    stop_risk_reserved_usd=amount,
                )
            )
        elif provenance.source_kind == CapitalSource.REALIZED_PROFIT.value:
            reserve_profit(amount, stop=True)
        else:
            raise CiboCapitalManagementError(
                "historical ceiling unsupported Risk capital source"
            )

    remaining_cost = provider_cost_usd
    available_base = _sub(
        state.original_base_proven_usd,
        state.original_base_consumed_usd,
        base_reserved,
    )
    base_cost = min(remaining_cost, available_base)
    if base_cost > 0:
        base_reserved = _add(base_reserved, base_cost)
        remaining_cost = _sub(remaining_cost, base_cost)
        slices.append(
            CiboHistoricalCapitalSlice(
                source=CapitalSource.ORIGINAL_BASE_CAPITAL,
                generation=0,
                provider_cost_reserved_usd=base_cost,
            )
        )
    if remaining_cost > 0:
        reserve_profit(remaining_cost, stop=False)

    deployment = CiboHistoricalOpenDeployment(
        authorization_id=authorization.authorization_id,
        signal_fingerprint=authorization.signal_fingerprint,
        trader_id=TraderLineage(authorization.trader_id),
        authorized_at=authorization.issued_at,
        authorized_volume=authorization.authorized_volume,
        authorized_stop_risk_usd=authorization.monetary_stop_loss,
        authorized_margin_usd=authorization.margin_reserved,
        provider_cost_usd=provider_cost_usd,
        slices=tuple(slices),
    )
    return replace(
        state,
        original_base_reserved_usd=base_reserved,
        profit_generations=tuple(
            sorted(profits, key=lambda item: item.generation)
        ),
        open_deployments=state.open_deployments + (deployment,),
    )


def settle_historical_deployment(
    state: CiboHistoricalResearchCapitalState,
    *,
    settlement: CiboManifestOutcomeSettlement,
) -> CiboHistoricalResearchCapitalState:
    """Consume costs/losses and admit causal gross profit after settlement."""

    if not isinstance(state, CiboHistoricalResearchCapitalState):
        raise CiboCapitalManagementError(
            "historical ceiling settlement requires canonical research state"
        )
    if not isinstance(settlement, CiboManifestOutcomeSettlement):
        raise CiboCapitalManagementError(
            "historical ceiling settlement requires canonical outcome"
        )
    matches = tuple(
        item
        for item in state.open_deployments
        if item.signal_fingerprint == settlement.signal_fingerprint
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "historical ceiling settlement lacks unique open deployment"
        )
    deployment = matches[0]
    if settlement.trader_id != deployment.trader_id.value:
        raise CiboCapitalManagementError(
            "historical ceiling settlement trader lineage drift"
        )
    if settlement.exit_at < deployment.authorized_at:
        raise CiboCapitalManagementError(
            "historical ceiling settlement predates authorization"
        )
    if settlement.receipt.settlement_sha256 in state.settlement_sha256s:
        raise CiboCapitalManagementError(
            "historical ceiling settlement evidence already consumed"
        )
    if settlement.provider_cost_usd != deployment.provider_cost_usd:
        raise CiboCapitalManagementError(
            "historical ceiling reserved/settled provider cost drift"
        )
    gross_r = settlement.gross_structural_outcome_r
    if (
        gross_r < Decimal("-1")
        and not settlement.exit_reason.startswith("GAP_")
    ):
        raise CiboCapitalManagementError(
            "historical ceiling outcome below -1R requires explicit gap evidence"
        )

    base_reserved = state.original_base_reserved_usd
    base_consumed = state.original_base_consumed_usd
    profits = {
        item.generation: item for item in state.profit_generations
    }

    def apply_slice(
        item: CiboHistoricalCapitalSlice,
        *,
        stop_loss_fraction: Decimal,
    ) -> None:
        nonlocal base_reserved, base_consumed, profits
        release = item.total_reserved_usd
        consumed = _add(
            item.provider_cost_reserved_usd,
            _mul(item.stop_risk_reserved_usd, stop_loss_fraction),
        )
        if item.source is CapitalSource.ORIGINAL_BASE_CAPITAL:
            base_reserved = _sub(base_reserved, release)
            base_consumed = _add(base_consumed, consumed)
            return
        lot = profits[item.generation]
        profits[item.generation] = replace(
            lot,
            reserved_usd=_sub(lot.reserved_usd, release),
            consumed_usd=_add(lot.consumed_usd, consumed),
        )

    loss_fraction = max(Decimal(0), -gross_r)
    for item in deployment.slices:
        apply_slice(item, stop_loss_fraction=loss_fraction)

    gross_profit = max(Decimal(0), settlement.gross_pnl_usd)
    if gross_profit > 0:
        generation = deployment.parent_generation + 1
        existing = profits.get(generation)
        if existing is None:
            profits[generation] = CiboHistoricalProfitGeneration(
                generation=generation,
                proven_usd=gross_profit,
            )
        else:
            profits[generation] = replace(
                existing,
                proven_usd=_add(existing.proven_usd, gross_profit),
            )

    next_state = replace(
        state,
        original_base_consumed_usd=base_consumed,
        original_base_reserved_usd=base_reserved,
        profit_generations=tuple(
            sorted(profits.values(), key=lambda item: item.generation)
        ),
        open_deployments=tuple(
            item
            for item in state.open_deployments
            if item.signal_fingerprint != settlement.signal_fingerprint
        ),
        settlement_sha256s=(
            state.settlement_sha256s
            + (settlement.receipt.settlement_sha256,)
        ),
        cumulative_provider_cost_usd=(
            _add(
                state.cumulative_provider_cost_usd,
                settlement.provider_cost_usd,
            )
        ),
        cumulative_gross_profit_usd=(
            _add(state.cumulative_gross_profit_usd, gross_profit)
        ),
        cumulative_gross_loss_usd=(
            _add(
                state.cumulative_gross_loss_usd,
                max(Decimal(0), -settlement.gross_pnl_usd),
            )
        ),
        peak_realized_capital_usd=max(
            state.peak_realized_capital_usd,
            (
                _add(
                    state.realized_capital_usd,
                    settlement.realized_net_pnl_usd,
                )
            ),
        ),
    )
    expected = _add(
        state.realized_capital_usd,
        settlement.realized_net_pnl_usd,
    )
    if next_state.realized_capital_usd != expected:
        raise CiboCapitalManagementError(
            "historical ceiling settlement capital conservation drift: "
            f"signal={settlement.signal_fingerprint} "
            f"before={state.realized_capital_usd} "
            f"gross_pnl={settlement.gross_pnl_usd} "
            f"provider_cost={settlement.provider_cost_usd} "
            f"net_pnl={settlement.realized_net_pnl_usd} "
            f"expected={expected} "
            f"actual={next_state.realized_capital_usd}"
        )
    if next_state.realized_capital_usd < 0:
        raise CiboCapitalManagementError(
            "historical ceiling realized capital cannot be negative"
        )
    return next_state
