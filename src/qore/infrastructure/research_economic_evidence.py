from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from qore.functional.decisions import (
    DecisionOutcome,
    DecisionStatus,
    FunctionalDecision,
)
from qore.infrastructure.order_intent import (
    ExecutionInstrument,
    OrderIntent,
    OrderPrice,
    OrderQuantity,
    OrderSide,
)
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.infrastructure.proprietary_accounts import MoneyAmount
from qore.infrastructure.research_run import (
    ResearchRunEvidence,
    ResearchTransactionCostModelId,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchEconomicEvidenceError(InfrastructureError):
    """Base error for immutable research execution and economic evidence."""

    __slots__ = ()


class ResearchEconomicEvidenceValidationError(ResearchEconomicEvidenceError):
    """Violation of a research economic-evidence invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ResearchEconomicEvidenceValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchEconomicEvidenceValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchEconomicEvidenceValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ResearchExecutionIntentEvidenceId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research execution intent evidence id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchFillId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research fill id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchEconomicResultId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research economic result id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchReturnObservationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research return observation id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchEconomicEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research economic evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchExecutionIntentEvidence:
    """Research-only causal binding from approved Core decision to one order intent.

    This record does not authorize live execution. It proves which resolved Core
    trading decision and research run caused a replay execution intent.
    """

    evidence_id: ResearchExecutionIntentEvidenceId
    run: ResearchRunEvidence
    decision: FunctionalDecision
    intent: OrderIntent
    evidenced_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, ResearchExecutionIntentEvidenceId):
            raise ResearchEconomicEvidenceValidationError(
                "evidence_id must be ResearchExecutionIntentEvidenceId"
            )
        if not isinstance(self.run, ResearchRunEvidence):
            raise ResearchEconomicEvidenceValidationError(
                "research execution intent requires ResearchRunEvidence"
            )
        if not isinstance(self.decision, FunctionalDecision):
            raise ResearchEconomicEvidenceValidationError(
                "research execution intent requires FunctionalDecision"
            )
        if self.decision.decision_type.value != "core.trade":
            raise ResearchEconomicEvidenceValidationError(
                "research execution intent requires core.trade decision"
            )
        if (
            self.decision.status is not DecisionStatus.RESOLVED
            or self.decision.outcome is not DecisionOutcome.APPROVED
        ):
            raise ResearchEconomicEvidenceValidationError(
                "research execution intent requires resolved approved Core decision"
            )
        if not isinstance(self.intent, OrderIntent):
            raise ResearchEconomicEvidenceValidationError(
                "research execution intent requires OrderIntent"
            )
        _validate_timestamp(self.evidenced_at, field_name="research intent evidenced_at")
        if not self.run.simulated_start <= self.decision.timestamp <= self.run.simulated_end:
            raise ResearchEconomicEvidenceValidationError(
                "Core decision timestamp must be inside research simulated window"
            )
        if self.intent.created_at < self.decision.timestamp:
            raise ResearchEconomicEvidenceValidationError(
                "research order intent must not predate Core decision"
            )
        if not self.run.simulated_start <= self.intent.created_at <= self.run.simulated_end:
            raise ResearchEconomicEvidenceValidationError(
                "research order intent must be inside research simulated window"
            )
        if self.evidenced_at < self.intent.created_at:
            raise ResearchEconomicEvidenceValidationError(
                "research intent evidence must not predate order intent"
            )
        if self.evidenced_at > self.run.simulated_end:
            raise ResearchEconomicEvidenceValidationError(
                "research intent evidence must not postdate simulated run"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_id.logical_values(),
            self.run.logical_values(),
            self.decision.logical_values(),
            self.intent.logical_values(),
            self.evidenced_at.isoformat(),
        )


def build_research_execution_intent_evidence(
    *,
    evidence_id: ResearchExecutionIntentEvidenceId,
    run: ResearchRunEvidence,
    decision: FunctionalDecision,
    intent: OrderIntent,
    evidenced_at: datetime,
) -> Result[ResearchExecutionIntentEvidence, ResearchEconomicEvidenceError]:
    try:
        return Success(
            ResearchExecutionIntentEvidence(
                evidence_id=evidence_id,
                run=run,
                decision=decision,
                intent=intent,
                evidenced_at=evidenced_at,
            )
        )
    except ResearchEconomicEvidenceError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class ResearchFillEvidence:
    """One immutable replay fill with actual price and quantity evidence."""

    fill_id: ResearchFillId
    intent_evidence: ResearchExecutionIntentEvidence
    source: ExternalSourceDescriptor
    price: OrderPrice
    quantity: OrderQuantity
    filled_at: datetime
    evidence_ref: ResearchEconomicEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.fill_id, ResearchFillId):
            raise ResearchEconomicEvidenceValidationError(
                "fill_id must be ResearchFillId"
            )
        if not isinstance(self.intent_evidence, ResearchExecutionIntentEvidence):
            raise ResearchEconomicEvidenceValidationError(
                "fill requires ResearchExecutionIntentEvidence"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise ResearchEconomicEvidenceValidationError(
                "fill source must be ExternalSourceDescriptor"
            )
        if not isinstance(self.price, OrderPrice):
            raise ResearchEconomicEvidenceValidationError("fill price must be OrderPrice")
        if not isinstance(self.quantity, OrderQuantity):
            raise ResearchEconomicEvidenceValidationError(
                "fill quantity must be OrderQuantity"
            )
        if self.quantity.value > self.intent_evidence.intent.quantity.value:
            raise ResearchEconomicEvidenceValidationError(
                "single fill quantity cannot exceed originating intent quantity"
            )
        _validate_timestamp(self.filled_at, field_name="research fill filled_at")
        if self.filled_at < self.intent_evidence.evidenced_at:
            raise ResearchEconomicEvidenceValidationError(
                "research fill must not predate intent evidence"
            )
        if self.filled_at > self.intent_evidence.run.simulated_end:
            raise ResearchEconomicEvidenceValidationError(
                "research fill must not postdate simulated run"
            )
        if not isinstance(self.evidence_ref, ResearchEconomicEvidenceReference):
            raise ResearchEconomicEvidenceValidationError(
                "fill evidence_ref must be ResearchEconomicEvidenceReference"
            )

    @property
    def instrument(self) -> ExecutionInstrument:
        return self.intent_evidence.intent.instrument

    @property
    def side(self) -> OrderSide:
        return self.intent_evidence.intent.side

    @property
    def run(self) -> ResearchRunEvidence:
        return self.intent_evidence.run

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.fill_id.logical_values(),
            self.intent_evidence.logical_values(),
            self.source.logical_values(),
            self.price.logical_values(),
            self.quantity.logical_values(),
            self.filled_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def build_research_fill_evidence(
    *,
    fill_id: ResearchFillId,
    intent_evidence: ResearchExecutionIntentEvidence,
    source: ExternalSourceDescriptor,
    price: OrderPrice,
    quantity: OrderQuantity,
    filled_at: datetime,
    evidence_ref: ResearchEconomicEvidenceReference,
) -> Result[ResearchFillEvidence, ResearchEconomicEvidenceError]:
    try:
        return Success(
            ResearchFillEvidence(
                fill_id=fill_id,
                intent_evidence=intent_evidence,
                source=source,
                price=price,
                quantity=quantity,
                filled_at=filled_at,
                evidence_ref=evidence_ref,
            )
        )
    except ResearchEconomicEvidenceError as error:
        return Failure(error)


def _canonical_fills(
    fills: tuple[ResearchFillEvidence, ...],
    *,
    field_name: str,
) -> tuple[ResearchFillEvidence, ...]:
    if not isinstance(fills, tuple) or not fills or any(
        not isinstance(fill, ResearchFillEvidence) for fill in fills
    ):
        raise ResearchEconomicEvidenceValidationError(
            f"{field_name} must be a non-empty immutable fill tuple"
        )
    return tuple(sorted(fills, key=lambda fill: (fill.filled_at, str(fill.fill_id.value))))


def _validate_closed_fill_chain(
    run: ResearchRunEvidence,
    entry_fills: tuple[ResearchFillEvidence, ...],
    exit_fills: tuple[ResearchFillEvidence, ...],
) -> tuple[tuple[ResearchFillEvidence, ...], tuple[ResearchFillEvidence, ...]]:
    ordered_entries = _canonical_fills(entry_fills, field_name="entry_fills")
    ordered_exits = _canonical_fills(exit_fills, field_name="exit_fills")
    all_fills = (*ordered_entries, *ordered_exits)
    if any(fill.run != run for fill in all_fills):
        raise ResearchEconomicEvidenceValidationError(
            "all economic-result fills must belong to the same research run"
        )
    fill_ids = tuple(fill.fill_id for fill in all_fills)
    if len(set(fill_ids)) != len(fill_ids):
        raise ResearchEconomicEvidenceValidationError(
            "economic-result fill ids must be globally unique"
        )
    instruments = {fill.instrument for fill in all_fills}
    if len(instruments) != 1:
        raise ResearchEconomicEvidenceValidationError(
            "closed economic result must use one execution instrument"
        )
    entry_sides = {fill.side for fill in ordered_entries}
    exit_sides = {fill.side for fill in ordered_exits}
    if len(entry_sides) != 1 or len(exit_sides) != 1:
        raise ResearchEconomicEvidenceValidationError(
            "entry and exit fills must each use one consistent side"
        )
    entry_side = next(iter(entry_sides))
    exit_side = next(iter(exit_sides))
    if entry_side is exit_side:
        raise ResearchEconomicEvidenceValidationError(
            "closed economic result requires opposite entry and exit sides"
        )
    entry_quantity = sum((fill.quantity.value for fill in ordered_entries), Decimal(0))
    exit_quantity = sum((fill.quantity.value for fill in ordered_exits), Decimal(0))
    if entry_quantity != exit_quantity:
        raise ResearchEconomicEvidenceValidationError(
            "closed economic result requires exactly balanced fill quantities"
        )
    events = [
        (fill.filled_at, 0, str(fill.fill_id.value), fill.quantity.value)
        for fill in ordered_entries
    ]
    events.extend(
        (fill.filled_at, 1, str(fill.fill_id.value), -fill.quantity.value)
        for fill in ordered_exits
    )
    open_quantity = Decimal(0)
    for _filled_at, _kind_order, _fill_id, quantity_delta in sorted(events):
        open_quantity += quantity_delta
        if open_quantity < 0:
            raise ResearchEconomicEvidenceValidationError(
                "exit fills cannot exceed accumulated entry quantity at any replay instant"
            )
    if open_quantity != 0:
        raise ResearchEconomicEvidenceValidationError(
            "closed economic result must finish with zero open quantity"
        )
    return ordered_entries, ordered_exits


@dataclass(frozen=True, slots=True)
class ResearchGrossEconomicResult:
    """Evidence-backed gross cash P&L before separately assessed cash charges.

    Gross P&L is deliberately supplied as evidence rather than recomputed from
    price × quantity. Instrument multipliers, pip values and currency conversion
    are outside this provider-neutral contract. Actual fill prices already carry
    price effects such as spread/slippage/market impact; those effects must not be
    subtracted again as independent cash charges.
    """

    result_id: ResearchEconomicResultId
    run: ResearchRunEvidence
    entry_fills: tuple[ResearchFillEvidence, ...]
    exit_fills: tuple[ResearchFillEvidence, ...]
    gross_pnl: MoneyAmount
    valued_at: datetime
    evidence_ref: ResearchEconomicEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.result_id, ResearchEconomicResultId):
            raise ResearchEconomicEvidenceValidationError(
                "gross result_id must be ResearchEconomicResultId"
            )
        if not isinstance(self.run, ResearchRunEvidence):
            raise ResearchEconomicEvidenceValidationError(
                "gross economic result requires ResearchRunEvidence"
            )
        if not self.run.binds_execution_model:
            raise ResearchEconomicEvidenceValidationError(
                "gross economic result requires research run execution model identity"
            )
        ordered_entries, ordered_exits = _validate_closed_fill_chain(
            self.run,
            self.entry_fills,
            self.exit_fills,
        )
        if self.entry_fills != ordered_entries or self.exit_fills != ordered_exits:
            raise ResearchEconomicEvidenceValidationError(
                "gross economic result fills must use canonical chronological order"
            )
        if not isinstance(self.gross_pnl, MoneyAmount):
            raise ResearchEconomicEvidenceValidationError(
                "gross_pnl must be MoneyAmount"
            )
        _validate_timestamp(self.valued_at, field_name="gross result valued_at")
        if self.valued_at < max(fill.filled_at for fill in (*self.entry_fills, *self.exit_fills)):
            raise ResearchEconomicEvidenceValidationError(
                "gross economic result cannot predate its fill evidence"
            )
        if not isinstance(self.evidence_ref, ResearchEconomicEvidenceReference):
            raise ResearchEconomicEvidenceValidationError(
                "gross result evidence_ref must be ResearchEconomicEvidenceReference"
            )

    @property
    def instrument(self) -> ExecutionInstrument:
        return self.entry_fills[0].instrument

    @property
    def quantity(self) -> Decimal:
        return sum((fill.quantity.value for fill in self.entry_fills), Decimal(0))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.result_id.logical_values(),
            self.run.logical_values(),
            tuple(fill.logical_values() for fill in self.entry_fills),
            tuple(fill.logical_values() for fill in self.exit_fills),
            self.gross_pnl.logical_values(),
            self.valued_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def build_research_gross_economic_result(
    *,
    result_id: ResearchEconomicResultId,
    run: ResearchRunEvidence,
    entry_fills: tuple[ResearchFillEvidence, ...],
    exit_fills: tuple[ResearchFillEvidence, ...],
    gross_pnl: MoneyAmount,
    valued_at: datetime,
    evidence_ref: ResearchEconomicEvidenceReference,
) -> Result[ResearchGrossEconomicResult, ResearchEconomicEvidenceError]:
    try:
        ordered_entries, ordered_exits = _validate_closed_fill_chain(
            run,
            entry_fills,
            exit_fills,
        )
        return Success(
            ResearchGrossEconomicResult(
                result_id=result_id,
                run=run,
                entry_fills=ordered_entries,
                exit_fills=ordered_exits,
                gross_pnl=gross_pnl,
                valued_at=valued_at,
                evidence_ref=evidence_ref,
            )
        )
    except ResearchEconomicEvidenceError as error:
        return Failure(error)


class ResearchCashCostCategory(StrEnum):
    """Cash adjustments only; fill-price effects are intentionally excluded."""

    COMMISSION = "commission"
    FEE = "fee"
    FINANCING = "financing"
    TAX = "tax"
    BORROW = "borrow"
    OTHER = "other"


class ResearchCashCostStatus(StrEnum):
    INCLUDED = "included"
    EXPLICIT_ZERO = "explicit_zero"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ResearchCashCostEvidence:
    """One model-declared cash cost assessment.

    INCLUDED amounts are signed: positive values are charges and negative values
    are rebates/credits. EXPLICIT_ZERO is evidence-backed zero. UNKNOWN is never
    silently converted to zero.
    """

    category: ResearchCashCostCategory
    status: ResearchCashCostStatus
    amount: MoneyAmount | None
    observed_at: datetime
    evidence_ref: ResearchEconomicEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.category, ResearchCashCostCategory):
            raise ResearchEconomicEvidenceValidationError(
                "cash cost category must be ResearchCashCostCategory"
            )
        if not isinstance(self.status, ResearchCashCostStatus):
            raise ResearchEconomicEvidenceValidationError(
                "cash cost status must be ResearchCashCostStatus"
            )
        if self.status is ResearchCashCostStatus.INCLUDED:
            if not isinstance(self.amount, MoneyAmount) or self.amount.amount == 0:
                raise ResearchEconomicEvidenceValidationError(
                    "included cash cost requires non-zero MoneyAmount"
                )
        elif self.status is ResearchCashCostStatus.EXPLICIT_ZERO:
            if not isinstance(self.amount, MoneyAmount) or self.amount.amount != 0:
                raise ResearchEconomicEvidenceValidationError(
                    "explicit-zero cash cost requires zero MoneyAmount"
                )
        elif self.amount is not None:
            raise ResearchEconomicEvidenceValidationError(
                "unknown cash cost must not carry a monetary amount"
            )
        _validate_timestamp(self.observed_at, field_name="cash cost observed_at")
        if not isinstance(self.evidence_ref, ResearchEconomicEvidenceReference):
            raise ResearchEconomicEvidenceValidationError(
                "cash cost evidence_ref must be ResearchEconomicEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.category.value,
            self.status.value,
            self.amount.logical_values() if self.amount is not None else None,
            self.observed_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ResearchCashCostCoverage:
    """Exact model-declared cash categories required for one research run."""

    run: ResearchRunEvidence
    model_id: ResearchTransactionCostModelId
    required_categories: tuple[ResearchCashCostCategory, ...]
    costs: tuple[ResearchCashCostEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.run, ResearchRunEvidence):
            raise ResearchEconomicEvidenceValidationError(
                "cash cost coverage requires ResearchRunEvidence"
            )
        if not self.run.binds_transaction_cost_model:
            raise ResearchEconomicEvidenceValidationError(
                "cash cost coverage requires run transaction cost model identity"
            )
        if not isinstance(self.model_id, ResearchTransactionCostModelId):
            raise ResearchEconomicEvidenceValidationError(
                "cash cost model_id must be ResearchTransactionCostModelId"
            )
        if self.run.transaction_cost_model_id != self.model_id:
            raise ResearchEconomicEvidenceValidationError(
                "cash cost model identity must match research run"
            )
        if not isinstance(self.required_categories, tuple) or any(
            not isinstance(category, ResearchCashCostCategory)
            for category in self.required_categories
        ):
            raise ResearchEconomicEvidenceValidationError(
                "required cash cost categories must be an immutable category tuple"
            )
        if len(set(self.required_categories)) != len(self.required_categories):
            raise ResearchEconomicEvidenceValidationError(
                "required cash cost categories must be unique"
            )
        canonical_required = tuple(sorted(self.required_categories, key=lambda item: item.value))
        if self.required_categories != canonical_required:
            raise ResearchEconomicEvidenceValidationError(
                "required cash cost categories must use canonical order"
            )
        if not isinstance(self.costs, tuple) or any(
            not isinstance(cost, ResearchCashCostEvidence) for cost in self.costs
        ):
            raise ResearchEconomicEvidenceValidationError(
                "cash costs must be an immutable ResearchCashCostEvidence tuple"
            )
        canonical_costs = tuple(sorted(self.costs, key=lambda item: item.category.value))
        if self.costs != canonical_costs:
            raise ResearchEconomicEvidenceValidationError(
                "cash cost evidence must use canonical category order"
            )
        observed_categories = tuple(cost.category for cost in self.costs)
        if observed_categories != self.required_categories:
            raise ResearchEconomicEvidenceValidationError(
                "every required cash cost category must have exactly one evidence record"
            )

    @property
    def complete(self) -> bool:
        return all(cost.status is not ResearchCashCostStatus.UNKNOWN for cost in self.costs)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.run.logical_values(),
            self.model_id.logical_values(),
            tuple(category.value for category in self.required_categories),
            tuple(cost.logical_values() for cost in self.costs),
        )


def build_research_cash_cost_coverage(
    *,
    run: ResearchRunEvidence,
    model_id: ResearchTransactionCostModelId,
    required_categories: tuple[ResearchCashCostCategory, ...],
    costs: tuple[ResearchCashCostEvidence, ...],
) -> Result[ResearchCashCostCoverage, ResearchEconomicEvidenceError]:
    try:
        ordered_required = tuple(sorted(required_categories, key=lambda item: item.value))
        ordered_costs = tuple(sorted(costs, key=lambda item: item.category.value))
        return Success(
            ResearchCashCostCoverage(
                run=run,
                model_id=model_id,
                required_categories=ordered_required,
                costs=ordered_costs,
            )
        )
    except (AttributeError, TypeError):
        return Failure(
            ResearchEconomicEvidenceValidationError(
                "cash cost coverage inputs must use canonical typed values"
            )
        )
    except ResearchEconomicEvidenceError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class ResearchNetEconomicResult:
    """Deterministic net cash P&L = gross cash P&L - explicit cash adjustments."""

    result_id: ResearchEconomicResultId
    gross_result: ResearchGrossEconomicResult
    cost_coverage: ResearchCashCostCoverage
    net_pnl: MoneyAmount
    valued_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.result_id, ResearchEconomicResultId):
            raise ResearchEconomicEvidenceValidationError(
                "net result_id must be ResearchEconomicResultId"
            )
        if not isinstance(self.gross_result, ResearchGrossEconomicResult):
            raise ResearchEconomicEvidenceValidationError(
                "net result requires ResearchGrossEconomicResult"
            )
        if not isinstance(self.cost_coverage, ResearchCashCostCoverage):
            raise ResearchEconomicEvidenceValidationError(
                "net result requires ResearchCashCostCoverage"
            )
        if self.cost_coverage.run != self.gross_result.run:
            raise ResearchEconomicEvidenceValidationError(
                "net result gross and cost evidence must reference the same research run"
            )
        if not self.cost_coverage.complete:
            raise ResearchEconomicEvidenceValidationError(
                "unknown required cash cost blocks net-performance evidence"
            )
        if not isinstance(self.net_pnl, MoneyAmount):
            raise ResearchEconomicEvidenceValidationError("net_pnl must be MoneyAmount")
        currency = self.gross_result.gross_pnl.currency
        if self.net_pnl.currency != currency:
            raise ResearchEconomicEvidenceValidationError(
                "net P&L currency must match gross P&L"
            )
        adjustments = Decimal(0)
        for cost in self.cost_coverage.costs:
            if cost.amount is None:
                raise ResearchEconomicEvidenceValidationError(
                    "complete cash cost evidence cannot contain missing amount"
                )
            if cost.amount.currency != currency:
                raise ResearchEconomicEvidenceValidationError(
                    "cash cost currency must match gross P&L currency"
                )
            adjustments += cost.amount.amount
        expected = MoneyAmount(
            currency=currency,
            amount=self.gross_result.gross_pnl.amount - adjustments,
        )
        if self.net_pnl != expected:
            raise ResearchEconomicEvidenceValidationError(
                "net P&L must equal gross P&L minus explicit cash adjustments"
            )
        _validate_timestamp(self.valued_at, field_name="net result valued_at")
        latest_cost = max(
            (cost.observed_at for cost in self.cost_coverage.costs),
            default=self.gross_result.valued_at,
        )
        if self.valued_at < max(self.gross_result.valued_at, latest_cost):
            raise ResearchEconomicEvidenceValidationError(
                "net result cannot predate gross or cash cost evidence"
            )

    @property
    def run(self) -> ResearchRunEvidence:
        return self.gross_result.run

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.result_id.logical_values(),
            self.gross_result.logical_values(),
            self.cost_coverage.logical_values(),
            self.net_pnl.logical_values(),
            self.valued_at.isoformat(),
        )


def build_research_net_economic_result(
    *,
    result_id: ResearchEconomicResultId,
    gross_result: ResearchGrossEconomicResult,
    cost_coverage: ResearchCashCostCoverage,
    valued_at: datetime,
) -> Result[ResearchNetEconomicResult, ResearchEconomicEvidenceError]:
    try:
        if not isinstance(gross_result, ResearchGrossEconomicResult):
            raise ResearchEconomicEvidenceValidationError(
                "gross_result must be ResearchGrossEconomicResult"
            )
        if not isinstance(cost_coverage, ResearchCashCostCoverage):
            raise ResearchEconomicEvidenceValidationError(
                "cost_coverage must be ResearchCashCostCoverage"
            )
        if not cost_coverage.complete:
            raise ResearchEconomicEvidenceValidationError(
                "unknown required cash cost blocks net-performance evidence"
            )
        currency = gross_result.gross_pnl.currency
        adjustments = Decimal(0)
        for cost in cost_coverage.costs:
            if cost.amount is None:
                raise ResearchEconomicEvidenceValidationError(
                    "complete cash cost evidence cannot contain missing amount"
                )
            if cost.amount.currency != currency:
                raise ResearchEconomicEvidenceValidationError(
                    "cash cost currency must match gross P&L currency"
                )
            adjustments += cost.amount.amount
        net_pnl = MoneyAmount(
            currency=currency,
            amount=gross_result.gross_pnl.amount - adjustments,
        )
        return Success(
            ResearchNetEconomicResult(
                result_id=result_id,
                gross_result=gross_result,
                cost_coverage=cost_coverage,
                net_pnl=net_pnl,
                valued_at=valued_at,
            )
        )
    except ResearchEconomicEvidenceError as error:
        return Failure(error)


class ResearchReturnBasis(StrEnum):
    GROSS = "gross"
    NET = "net"


ResearchEconomicResult = ResearchGrossEconomicResult | ResearchNetEconomicResult


@dataclass(frozen=True, slots=True)
class ResearchReturnObservation:
    """Return evidence requiring an explicit positive monetary capital basis."""

    observation_id: ResearchReturnObservationId
    source_result: ResearchEconomicResult
    capital_basis: MoneyAmount
    observed_at: datetime
    return_rate: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, ResearchReturnObservationId):
            raise ResearchEconomicEvidenceValidationError(
                "return observation_id must be ResearchReturnObservationId"
            )
        if not isinstance(
            self.source_result,
            (ResearchGrossEconomicResult, ResearchNetEconomicResult),
        ):
            raise ResearchEconomicEvidenceValidationError(
                "return source_result must be a research economic result"
            )
        if not isinstance(self.capital_basis, MoneyAmount):
            raise ResearchEconomicEvidenceValidationError(
                "return capital_basis must be MoneyAmount"
            )
        if self.capital_basis.amount <= 0:
            raise ResearchEconomicEvidenceValidationError(
                "return capital_basis must be positive"
            )
        pnl = self._pnl
        if self.capital_basis.currency != pnl.currency:
            raise ResearchEconomicEvidenceValidationError(
                "return capital basis currency must match P&L currency"
            )
        _validate_timestamp(self.observed_at, field_name="return observed_at")
        if self.observed_at < self.source_result.valued_at:
            raise ResearchEconomicEvidenceValidationError(
                "return observation cannot predate economic result"
            )
        if not isinstance(self.return_rate, Decimal) or not self.return_rate.is_finite():
            raise ResearchEconomicEvidenceValidationError(
                "return_rate must be a finite Decimal"
            )
        expected = pnl.amount / self.capital_basis.amount
        if self.return_rate != expected:
            raise ResearchEconomicEvidenceValidationError(
                "return_rate must equal P&L divided by explicit capital basis"
            )

    @property
    def _pnl(self) -> MoneyAmount:
        if isinstance(self.source_result, ResearchNetEconomicResult):
            return self.source_result.net_pnl
        return self.source_result.gross_pnl

    @property
    def basis(self) -> ResearchReturnBasis:
        if isinstance(self.source_result, ResearchNetEconomicResult):
            return ResearchReturnBasis.NET
        return ResearchReturnBasis.GROSS

    @property
    def run(self) -> ResearchRunEvidence:
        return self.source_result.run

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id.logical_values(),
            self.source_result.logical_values(),
            self.capital_basis.logical_values(),
            self.observed_at.isoformat(),
            format(self.return_rate, "f"),
            self.basis.value,
        )


def build_research_return_observation(
    *,
    observation_id: ResearchReturnObservationId,
    source_result: ResearchEconomicResult,
    capital_basis: MoneyAmount,
    observed_at: datetime,
) -> Result[ResearchReturnObservation, ResearchEconomicEvidenceError]:
    try:
        if not isinstance(
            source_result,
            (ResearchGrossEconomicResult, ResearchNetEconomicResult),
        ):
            raise ResearchEconomicEvidenceValidationError(
                "source_result must be a research economic result"
            )
        if not isinstance(capital_basis, MoneyAmount) or capital_basis.amount <= 0:
            raise ResearchEconomicEvidenceValidationError(
                "capital_basis must be positive MoneyAmount"
            )
        pnl = (
            source_result.net_pnl
            if isinstance(source_result, ResearchNetEconomicResult)
            else source_result.gross_pnl
        )
        if capital_basis.currency != pnl.currency:
            raise ResearchEconomicEvidenceValidationError(
                "capital basis currency must match P&L currency"
            )
        return Success(
            ResearchReturnObservation(
                observation_id=observation_id,
                source_result=source_result,
                capital_basis=capital_basis,
                observed_at=observed_at,
                return_rate=pnl.amount / capital_basis.amount,
            )
        )
    except ResearchEconomicEvidenceError as error:
        return Failure(error)
