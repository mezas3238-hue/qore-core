from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TargetArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ar_market_suitability_walk_forward import (
    ARM,
    IDENTITY,
    MIN_RETENTION,
    TRAINING_YEARS,
    _select_rule,
)


def test_r2ar_algorithm_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AR_MARKET_SUITABILITY_WALK_FORWARD_001"
    assert ARM is TargetArm.FIXED_1_5R
    assert TRAINING_YEARS == 3
    assert str(MIN_RETENTION) == "0.70"


def test_empty_training_selects_no_unsuitable_state() -> None:
    rule, evidence = _select_rule(training=(), training_start_year=2020)

    assert rule is None
    assert evidence["reason"] == "EMPTY_TRAINING"
