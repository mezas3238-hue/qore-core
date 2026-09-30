from __future__ import annotations

from datetime import datetime

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_third_slot_journey_atlas_2r_v1 as atlas,
)


def test_known_state_respects_true_exit_timestamp() -> None:
    row = {
        "exit_at": "2026-01-05T09:20:00+00:00",
        "realized_gross_r": "2",
    }
    assert atlas._known_state(
        row,
        decision_at=datetime.fromisoformat("2026-01-05T09:10:00+00:00"),
    ) == "OPEN"
    assert atlas._known_state(
        row,
        decision_at=datetime.fromisoformat("2026-01-05T09:20:00+00:00"),
    ) == "WIN"


def test_sign_is_causal_label_only() -> None:
    from decimal import Decimal

    assert atlas._sign(Decimal("2")) == "POSITIVE"
    assert atlas._sign(Decimal("-1")) == "NEGATIVE"
    assert atlas._sign(Decimal("0")) == "ZERO"
