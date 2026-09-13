from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.ctrader_demo_lab_vt08_r3_15_holdout_probe import (
    ACQUISITION_OPENED_AT,
    EVALUATION_CLOSED_AT,
    EVALUATION_OPENED_AT,
    HOLDOUT_ID,
    validate_freeze,
)
from qore.infrastructure.trader_lab.vt08_final_holdout_r3_15 import (
    CLOSED_AT,
    MAX_VARIANCE,
    MIN_SAMPLE,
    OPENED_AT,
    PORTFOLIO,
)


def test_r315_holdout_is_exactly_the_pre_frozen_730_day_window() -> None:
    validate_freeze()
    assert HOLDOUT_ID == "VT08_R3_15_FINAL_INDEPENDENT_2020_2022"
    assert EVALUATION_OPENED_AT == datetime(2020, 7, 1, tzinfo=UTC)
    assert EVALUATION_CLOSED_AT == datetime(2022, 7, 1, tzinfo=UTC)
    assert OPENED_AT == EVALUATION_OPENED_AT
    assert CLOSED_AT == EVALUATION_CLOSED_AT
    assert (CLOSED_AT - OPENED_AT).days == 730
    assert ACQUISITION_OPENED_AT < OPENED_AT


def test_r315_portfolio_and_risk_gate_are_frozen_before_access() -> None:
    assert PORTFOLIO == {
        ("AUDJPY", "short"),
        ("GBPUSD", "short"),
        ("GBPJPY", "long"),
        ("GBPJPY", "short"),
    }
    assert MIN_SAMPLE == 30
    assert MAX_VARIANCE == Decimal("0.01")
