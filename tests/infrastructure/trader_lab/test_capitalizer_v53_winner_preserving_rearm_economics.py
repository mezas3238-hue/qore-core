from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_v53_winner_preserving_rearm_economics import (
    V53TradeRecord,
    _portfolio,
    _preservation,
)


def _row(
    *,
    parent: str,
    minute: int,
    realized: str,
    attempt: int = 1,
    policy: str = "V49_BASELINE",
) -> V53TradeRecord:
    entry = f"2026-01-05T10:{minute:02d}:00+00:00"
    return V53TradeRecord(
        source_policy=policy,
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_from="2026-01-05T09:00:00+00:00",
        m15_setup_confirmed_at=f"2026-01-05T09:{parent}:00+00:00",
        attempt_index=attempt,
        direction="LONG",
        entry_at=entry,
        exit_at=entry,
        entry_price="100",
        stop_price="99",
        target_price="102",
        planned_reward_r="2",
        realized_gross_r=realized,
        exit_reason="TARGET" if Decimal(realized) > 0 else "STOP",
        m1_bars_held=1,
        trigger_family="FVG_RETRACE_CISD",
        h1_state_basis="TEST",
    )


def test_parent_thesis_winner_is_preserved_only_if_transformed_trade_wins() -> None:
    baseline = (
        _row(parent="00", minute=1, realized="2"),
        _row(parent="01", minute=2, realized="-1"),
    )
    candidate = (
        _row(
            parent="00",
            minute=8,
            realized="3",
            attempt=2,
            policy="V50_R_TRANSFORMED",
        ),
        _row(
            parent="01",
            minute=9,
            realized="1",
            attempt=2,
            policy="V50_R_TRANSFORMED",
        ),
    )
    result = _preservation(baseline, candidate, raw_candidate=candidate)
    assert Decimal(result["winner_count_preservation"]) == Decimal("1")
    assert Decimal(result["winner_r_preservation"]) == Decimal("1.5")
    assert Decimal(result["loss_recall"]) == Decimal("1")


def test_parent_thesis_identity_without_positive_transformed_r_is_not_preserved() -> None:
    baseline = (_row(parent="00", minute=1, realized="2"),)
    candidate = (
        _row(
            parent="00",
            minute=8,
            realized="-1",
            attempt=2,
            policy="V50_R_TRANSFORMED",
        ),
    )
    result = _preservation(baseline, candidate, raw_candidate=candidate)
    assert Decimal(result["winner_count_preservation"]) == Decimal("0")
    assert Decimal(result["winner_r_preservation"]) == Decimal("0")
    assert result["baseline_winners_transformed_to_nonwinner"] == 1


def test_portfolio_uses_one_execution_per_parent_and_max3() -> None:
    rows = (
        _row(parent="00", minute=1, realized="1", policy="V50_R_TRANSFORMED"),
        _row(
            parent="00",
            minute=2,
            realized="2",
            attempt=2,
            policy="V50_R_TRANSFORMED",
        ),
        _row(parent="01", minute=3, realized="1", policy="V50_R_TRANSFORMED"),
        _row(parent="02", minute=4, realized="1", policy="V50_R_TRANSFORMED"),
        _row(parent="03", minute=5, realized="1", policy="V50_R_TRANSFORMED"),
    )
    selected = _portfolio(rows)
    assert len(selected) == 3
    assert tuple(item.m15_setup_confirmed_at for item in selected) == (
        "2026-01-05T09:00:00+00:00",
        "2026-01-05T09:01:00+00:00",
        "2026-01-05T09:02:00+00:00",
    )
