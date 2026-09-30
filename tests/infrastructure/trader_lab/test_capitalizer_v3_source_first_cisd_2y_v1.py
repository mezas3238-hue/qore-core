from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_2y_v1 import (
    BASELINE_DD_R,
    BASELINE_MAX3_TRADES,
    BASELINE_MEAN_R,
    BASELINE_PF,
    BASELINE_TOTAL_R,
    IDENTITY,
    MATRIX_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    BOUNDARY_SEMANTICS,
)


def test_source_first_2y_ab_contract_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_SOURCE_FIRST_CISD_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_CISD_2Y_V1"
    )
    assert BOUNDARY_SEMANTICS == "FIRST_OPPOSING_OPEN_AFTER_SWEEP_PERSISTS"
    assert BASELINE_MAX3_TRADES == 474
    assert BASELINE_PF == Decimal("1.283270342004661566350801358")
    assert BASELINE_TOTAL_R == Decimal("50.34686423146549474995387094")
    assert BASELINE_MEAN_R == Decimal("0.1062170131465516766876663944")
    assert BASELINE_DD_R == Decimal("13.43559872546085473546771142")
