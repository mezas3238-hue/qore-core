from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as mod
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r6_governed_candidate_freeze as freeze


def test_forensics_identity_and_authority_boundaries() -> None:
    assert mod.IDENTITY == "VT08_INDEX_R6_5Y_FAILURE_FORENSICS_001"
    assert mod.PRIMARY_STRESS == Decimal("0.05")
    assert mod.SECONDARY_STRESS == Decimal("0.10")


def test_basic_metrics_delegate_is_stable() -> None:
    row = mod._metrics(
        (Decimal("2"), Decimal("-1"), Decimal("-1"), Decimal("2"))
    )
    assert row["sample"] == 4
    assert row["profit_factor"] == "2"
    assert row["max_drawdown_r"] == "2"


def test_failed_5y_contract_remains_consumed_and_frozen() -> None:
    assert v5y.MIN_TRADES == 1500
    assert v5y.MAX_TRADES == 1600
    assert freeze.CANDIDATE_ID == "VT08_INDEX_R6_GOVERNED_657_001"
    assert freeze.RISK_GOVERNOR["zero_weight_allowed"] is False
