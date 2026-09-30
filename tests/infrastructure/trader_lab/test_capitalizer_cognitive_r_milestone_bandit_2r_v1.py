from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_bandit_2r_v1 as bandit,
)


def _outcome(value: str, *, mode: str = "ORIGINAL") -> bandit.TradeOutcome:
    return bandit.TradeOutcome(
        symbol="NAS100",
        session="NEW_YORK",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T10:00:00+00:00",
        exit_at="2026-01-05T10:20:00+00:00",
        realized_gross_r=value,
        exit_reason="STOP" if Decimal(value) <= 0 else "TARGET",
        mode=mode,
    )


def test_distribution_penalizes_negative_realized_not_stop_label() -> None:
    positive_stop = bandit.TradeOutcome(
        symbol="NAS100",
        session="NEW_YORK",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T10:00:00+00:00",
        exit_at="2026-01-05T10:20:00+00:00",
        realized_gross_r="0.25",
        exit_reason="STOP",
        mode="LOCK025_AFTER_075",
    )
    mean_r, negative_rate, downside = bandit._distribution(
        (positive_stop, _outcome("-1"))
    )
    assert mean_r == Decimal("-0.375")
    assert negative_rate == Decimal("0.5")
    assert downside == Decimal("1")


def test_warmup_cycles_all_arms_evenly() -> None:
    from collections import Counter

    counts: Counter[tuple[str, str]] = Counter()
    first = bandit._warmup_arm(symbol="NAS100", selection_counts=counts)
    assert first == bandit.ARMS[0]
    counts[("NAS100", bandit.ARMS[0])] = 1
    second = bandit._warmup_arm(symbol="NAS100", selection_counts=counts)
    assert second == bandit.ARMS[1]


def test_systemic_pressure_requires_cross_symbol_losses() -> None:
    rows = tuple(
        bandit.TradeOutcome(
            symbol=f"S{i}",
            session="NEW_YORK",
            operating_date="2026-01-05",
            side="LONG",
            entry_at=f"2026-01-05T1{i}:00:00+00:00",
            exit_at=f"2026-01-05T1{i}:10:00+00:00",
            realized_gross_r="-0.5",
            exit_reason="STOP",
            mode="ORIGINAL",
        )
        for i in range(6)
    )
    assert bandit._systemic_pressure(rows) is True
