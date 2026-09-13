from decimal import Decimal

from qore.infrastructure.provider_contracts import (
    FTMO_2_STEP_PHASE_1,
    AutomationMode,
    TradingPlatform,
    execution_capability,
)


def test_ftmo_match_trader_low_level_capability_fails_closed() -> None:
    capability = execution_capability(
        FTMO_2_STEP_PHASE_1,
        platform=TradingPlatform.MATCH_TRADER,
        initial_balance=Decimal("100000"),
    )

    assert capability.mode is AutomationMode.FAIL_CLOSED
    assert not capability.automated_order_submission_allowed
