"""First cTrader DEMO execution intent composition.

This module is deliberately narrow: a Trader may define setup geometry, but it
never chooses an account, provider, instrument mapping, quantity, or execution
authority.  The bridge consumes one already-selected first-cohort Trader and the
actual cTrader DEMO symbol mapping, then builds the minimum broker-valid protected
LIMIT intent.  Risk remains a mandatory downstream authority.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentError,
    OrderIntentId,
    OrderPrice,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.trader_lab.cohort import FirstCohortDemoSelection
from qore.infrastructure.traders.contracts import (
    DemoTradingDecision,
    DemoTradingOutput,
    DemoTradingSetupSide,
)
from qore.kernel.result import Failure, Result, Success


class DemoFirstExecutionIntentError(OrderIntentError):
    """Fail-closed first-execution intent composition error."""

    __slots__ = ()


def minimum_broker_valid_quantity(mapping: CTraderSymbolMapping) -> OrderQuantity:
    """Return the exact minimum provider-valid QORE quantity for one symbol mapping."""

    if not isinstance(mapping, CTraderSymbolMapping):
        raise DemoFirstExecutionIntentError("symbol mapping must be CTraderSymbolMapping")
    if mapping.min_volume_units % mapping.step_volume_units != 0:
        raise DemoFirstExecutionIntentError(
            "cTrader minimum volume is not aligned to provider stepVolume"
        )
    quantity = mapping.volume_step * Decimal(mapping.min_volume_units)
    try:
        return OrderQuantity(quantity)
    except OrderIntentError as error:
        raise DemoFirstExecutionIntentError(str(error)) from error


def _price_is_provider_exact(price: Decimal, digits: int) -> bool:
    try:
        quantum = Decimal(1).scaleb(-digits)
        return price.quantize(quantum) == price
    except (InvalidOperation, ValueError):
        return False


def _validate_selected_output(
    selection: FirstCohortDemoSelection,
    output: DemoTradingOutput,
) -> Result[None, DemoFirstExecutionIntentError]:
    if not isinstance(selection, FirstCohortDemoSelection):
        return Failure(DemoFirstExecutionIntentError("selection must be FirstCohortDemoSelection"))
    selection.__post_init__()
    selected = selection.selected
    if selected is None:
        return Failure(
            DemoFirstExecutionIntentError(
                "first DEMO execution requires one selected DEMO-eligible Trader"
            )
        )
    selected.__post_init__()
    if not isinstance(output, DemoTradingOutput):
        return Failure(DemoFirstExecutionIntentError("output must be DemoTradingOutput"))
    try:
        output.__post_init__()
    except Exception as error:
        return Failure(DemoFirstExecutionIntentError(str(error)))
    if (
        output.trader_code != selected.trader_code
        or output.version != selected.trader_version
        or output.config_fingerprint != selected.config_fingerprint
        or output.methodology_id != selected.methodology_id
        or output.methodology_version != selected.methodology_version
        or output.methodology_fingerprint != selected.methodology_fingerprint
    ):
        return Failure(
            DemoFirstExecutionIntentError(
                "Trader output identity does not match the selected DEMO-eligible candidate"
            )
        )
    if output.decision is not DemoTradingDecision.SETUP or output.setup is None:
        return Failure(
            DemoFirstExecutionIntentError(
                "selected Trader must currently produce an exact SETUP before execution"
            )
        )
    return Success(None)


def build_first_demo_execution_intent(
    selection: FirstCohortDemoSelection,
    output: DemoTradingOutput,
    *,
    configuration: CTraderDemoRuntimeConfiguration,
    instrument: ExecutionInstrument,
    intent_id: OrderIntentId,
    idempotency_key: ExecutionIdempotencyKey,
    created_at: datetime,
    metadata: ExternalRequestMetadata,
) -> Result[OrderIntent, DemoFirstExecutionIntentError]:
    """Build one protected minimum-size LIMIT intent from an eligible Trader setup.

    This function creates no Risk or broker authority.  It fails closed unless
    the retained Trader output belongs to the exact selected candidate and the
    requested instrument exists in the explicit cTrader DEMO configuration.
    """

    validated = _validate_selected_output(selection, output)
    if isinstance(validated, Failure):
        return validated
    if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
        return Failure(
            DemoFirstExecutionIntentError(
                "configuration must be CTraderDemoRuntimeConfiguration"
            )
        )
    if configuration.environment is not MarketRuntimeEnvironment.DEMO:
        return Failure(
            DemoFirstExecutionIntentError("first execution configuration must be DEMO")
        )
    if not isinstance(instrument, ExecutionInstrument):
        return Failure(
            DemoFirstExecutionIntentError("instrument must be ExecutionInstrument")
        )
    mapping = configuration.symbol_mapping(instrument)
    if mapping is None:
        return Failure(
            DemoFirstExecutionIntentError(
                "first execution instrument is not mapped by cTrader DEMO configuration"
            )
        )
    setup = output.setup
    if setup is None:
        return Failure(DemoFirstExecutionIntentError("Trader SETUP is missing setup geometry"))
    for field_name, price in (
        ("entry", setup.entry_price),
        ("stop_loss", setup.invalidation_price),
        ("take_profit", setup.take_profit_price),
    ):
        if not _price_is_provider_exact(price, mapping.digits):
            message = (
                f"Trader {field_name} price is not exactly representable at "
                "cTrader symbol digits"
            )
            return Failure(DemoFirstExecutionIntentError(message))
    side = (
        OrderSide.BUY
        if setup.side is DemoTradingSetupSide.LONG
        else OrderSide.SELL
    )
    try:
        quantity = minimum_broker_valid_quantity(mapping)
        intent = OrderIntent(
            intent_id=intent_id,
            idempotency_key=idempotency_key,
            instrument=instrument,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            created_at=created_at,
            metadata=metadata,
            limit_price=OrderPrice(setup.entry_price),
            stop_loss=OrderPrice(setup.invalidation_price),
            take_profit=OrderPrice(setup.take_profit_price),
        )
    except (OrderIntentError, DemoFirstExecutionIntentError) as error:
        return Failure(DemoFirstExecutionIntentError(str(error)))
    return Success(intent)
