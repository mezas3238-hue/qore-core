from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_partial_realization_2r_v1 as lab,
)


def _row(max_mfe: str, realized: str) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol="NAS100",
        session="NEW_YORK",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T10:00:00+00:00",
        exit_at="2026-01-05T10:30:00+00:00",
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99.5",
        target_price="102",
        realized_gross_r=realized,
        exit_reason="STOP",
        mode="STAGED_050_100_150",
        protection_updates=1,
        first_protection_at="2026-01-05T10:05:00+00:00",
        max_milestone_r_seen_before_exit=max_mfe,
        same_minute_stop_target_ambiguity=False,
    )


def test_partial_only_triggers_when_milestone_reached() -> None:
    plan = lab.PartialPlan(
        "TEST",
        milestone.ProtectionMode.STAGED_050_100_150,
        (lab.PartialStep(Decimal("0.50"), Decimal("0.20")),),
    )
    untouched = lab._apply_plan(_row("0.40", "-1"), plan=plan)
    assert Decimal(untouched.realized_gross_r) == Decimal("-1")

    triggered = lab._apply_plan(_row("0.60", "-1"), plan=plan)
    assert Decimal(triggered.realized_gross_r) == Decimal("-0.70")


def test_two_partials_use_original_position_fractions() -> None:
    plan = lab.PartialPlan(
        "TEST2",
        milestone.ProtectionMode.STAGED_050_100_150,
        (
            lab.PartialStep(Decimal("0.50"), Decimal("0.25")),
            lab.PartialStep(Decimal("1.00"), Decimal("0.25")),
        ),
    )
    row = lab._apply_plan(_row("1.20", "0"), plan=plan)
    assert Decimal(row.realized_gross_r) == Decimal("0.375")
