"""CMA open-position stop-floor invariants."""
# ruff: noqa: I001

from decimal import Decimal

from qore.infrastructure.cibo_cma_position_floor import (
    OpenPositionStopEvidence,
    evaluate_remaining_stop_floor,
)


def _evidence(**overrides: object) -> OpenPositionStopEvidence:
    values: dict[str, object] = {
        "side": "long",
        "entry_price": Decimal("100"),
        "current_stop": Decimal("95"),
        "remaining_volume": Decimal("0.20"),
        "tick_size": Decimal("1"),
        "tick_value": Decimal("10"),
        "broker_position_reconciled": True,
        "broker_stop_reconciled": True,
    }
    values.update(overrides)
    return OpenPositionStopEvidence(**values)  # type: ignore[arg-type]


def test_long_adverse_stop_produces_negative_remaining_floor() -> None:
    floor = evaluate_remaining_stop_floor(_evidence())

    assert floor.evidence_sufficient is True
    assert floor.stop_distance_ticks == Decimal("-5")
    assert floor.remaining_stop_worst_case_pnl_usd == Decimal("-10.00")


def test_long_protected_stop_above_entry_produces_positive_floor() -> None:
    floor = evaluate_remaining_stop_floor(
        _evidence(current_stop=Decimal("103"))
    )

    assert floor.stop_distance_ticks == Decimal("3")
    assert floor.remaining_stop_worst_case_pnl_usd == Decimal("6.00")


def test_short_stop_below_entry_can_lock_profit() -> None:
    floor = evaluate_remaining_stop_floor(
        _evidence(
            side="short",
            current_stop=Decimal("97"),
        )
    )

    assert floor.remaining_stop_worst_case_pnl_usd == Decimal("6.00")


def test_partial_volume_reduces_remaining_stop_loss() -> None:
    full = evaluate_remaining_stop_floor(_evidence())
    partial = evaluate_remaining_stop_floor(
        _evidence(remaining_volume=Decimal("0.10"))
    )

    assert full.remaining_stop_worst_case_pnl_usd == Decimal("-10.00")
    assert partial.remaining_stop_worst_case_pnl_usd == Decimal("-5.00")


def test_unreconciled_stop_fails_closed() -> None:
    floor = evaluate_remaining_stop_floor(
        _evidence(broker_stop_reconciled=False)
    )

    assert floor.evidence_sufficient is False
    assert floor.remaining_stop_worst_case_pnl_usd is None


def test_unreconciled_position_fails_closed() -> None:
    floor = evaluate_remaining_stop_floor(
        _evidence(broker_position_reconciled=False)
    )

    assert floor.evidence_sufficient is False
