from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_source_entry_execution_v2 import (
    CapitalizerSourceExecutionOpen,
    derive_next_bar_open_entry,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)


def test_next_bar_open_entry_uses_only_open_after_source_confirmation() -> None:
    entry = derive_next_bar_open_entry(
        direction=CapitalizerSourceDirection.BULLISH,
        source_framework_confirmed=True,
        execution_open=CapitalizerSourceExecutionOpen(Decimal("100.25")),
    )

    assert entry.entry_price == Decimal("100.25")
    assert entry.source_framework_confirmed_before_entry is True
    assert entry.author_sequence_supported is True
    assert entry.qore_next_bar_open_operationalization is True
    assert entry.future_execution_bar_close_used is False
    assert entry.grants_execution_authority is False
    assert entry.grants_capital_authority is False


def test_next_bar_open_entry_cannot_front_run_source_confirmation() -> None:
    with pytest.raises(ValueError, match="completed source framework"):
        derive_next_bar_open_entry(
            direction=CapitalizerSourceDirection.BULLISH,
            source_framework_confirmed=False,
            execution_open=CapitalizerSourceExecutionOpen(Decimal("100.25")),
        )
