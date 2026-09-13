from datetime import date

import pytest

from qore.infrastructure.trader_lab.vt08_cibo_bank_attack_r3_17 import (
    BANK_POLICIES,
    RISK_LEVELS,
    CiboBankAttackError,
    attack_is_available,
    protected_capital_floor,
    run_bank_attack_sequence,
)
from qore.infrastructure.trader_lab.vt08_cibo_data_r3_16 import ReplayTrade


def trade(day: date, net_r: float, sleeve: str = "A") -> ReplayTrade:
    return ReplayTrade(
        signal_key=(
            day.isoformat(),
            "AUDJPY" if sleeve == "A" else "GBPJPY",
            "short",
        ),
        day=day,
        anchor=9,
        symbol="AUDJPY" if sleeve == "A" else "GBPJPY",
        side="short",
        sleeve=sleeve,
        gross_r=net_r,
        net_r=net_r,
        exit_reason="stop" if net_r < 0 else "target",
        baseline_exit_reason="stop" if net_r < 0 else "target",
    )


def test_attack_requires_banked_profit_and_free_cushion() -> None:
    policy = BANK_POLICIES[0]
    assert not attack_is_available(
        equity=1.019,
        peak_equity=1.019,
        policy=policy,
    )
    assert attack_is_available(
        equity=1.03,
        peak_equity=1.03,
        policy=policy,
    )


def test_banked_floor_moves_above_initial_capital() -> None:
    floor = protected_capital_floor(
        peak_equity=1.04,
        policy=BANK_POLICIES[1],
    )
    assert floor >= 1.02


def test_risk_scales_before_daily_or_capital_five_percent() -> None:
    d = date(2026, 1, 5)
    mapped = {d: {9: [trade(d, -1.0), trade(d, -1.0, "G")]}}
    metrics = run_bank_attack_sequence(
        [d],
        mapped,
        base_risk=RISK_LEVELS[-1],
        attack_risk=RISK_LEVELS[-1],
        policy=BANK_POLICIES[0],
    )
    assert metrics.maximum_daily_drawdown < 0.05
    assert metrics.maximum_capital_drawdown < 0.05


def test_cibo_banks_then_decides_attack_while_risk_sizes() -> None:
    first = date(2026, 1, 5)
    second = date(2026, 1, 6)
    mapped = {
        first: {9: [trade(first, 2.0)]},
        second: {9: [trade(second, 2.0)]},
    }
    metrics = run_bank_attack_sequence(
        [first, second],
        mapped,
        base_risk=RISK_LEVELS[1],
        attack_risk=RISK_LEVELS[4],
        policy=BANK_POLICIES[0],
    )
    assert metrics.generated_signals == 2
    assert metrics.bank_decisions >= 1
    assert metrics.attack_activations >= 1
    assert metrics.attack_trades >= 1
    assert metrics.maximum_daily_drawdown < 0.05


def test_attack_cannot_be_lower_than_base_authority() -> None:
    with pytest.raises(CiboBankAttackError):
        run_bank_attack_sequence(
            [],
            {},
            base_risk=RISK_LEVELS[-1],
            attack_risk=RISK_LEVELS[0],
            policy=BANK_POLICIES[0],
        )
