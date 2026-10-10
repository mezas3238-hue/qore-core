"""Source-level regression for TTrades M1 alternatives in frozen V49.

The source family is a union, never a global MSS+FVG+OB superintersection.
This tests route dispatch only; it is not an economic replay or source certificate.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from qore.infrastructure.trader_lab import capitalizer_high_frequency_capacity_census_v49
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_cisd_observer_v48 import (
    V48M1CISDStatus,
)

THESIS = datetime(2026, 10, 9, 10, tzinfo=UTC)
CLOSE_1 = THESIS + timedelta(minutes=1)
CLOSE_2 = THESIS + timedelta(minutes=2)
DEADLINE = THESIS + timedelta(minutes=8)


def _bars() -> tuple[CapitalizerM1Bar, ...]:
    return tuple(
        CapitalizerM1Bar(
            symbol="EURUSD",
            opened_at=THESIS + timedelta(minutes=idx),
            closed_at=THESIS + timedelta(minutes=idx + 1),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=None,
            digits=5,
        )
        for idx in range(2)
    )


def _configure_observers(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sweep_confirmed_at: datetime | None,
    fvg_confirmed_at: datetime | None,
) -> None:
    def sweep(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            status=(
                V48M1CISDStatus.CONFIRMED
                if sweep_confirmed_at is not None
                else V48M1CISDStatus.NO_CISD_CLOSE
            ),
            confirmed_at=sweep_confirmed_at,
            confirmation_close=Decimal("100") if sweep_confirmed_at else None,
        )

    def fvg(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            confirmed=fvg_confirmed_at is not None,
            cisd_confirmed_at=fvg_confirmed_at,
        )

    monkeypatch.setattr(
        capitalizer_high_frequency_capacity_census_v49,
        "observe_first_m1_cisd",
        sweep,
    )
    monkeypatch.setattr(
        capitalizer_high_frequency_capacity_census_v49,
        "observe_first_m1_fvg_cisd_continuation",
        fvg,
    )


@pytest.mark.parametrize(
    ("sweep_at", "fvg_at", "expected"),
    [
        (CLOSE_1, None, (CLOSE_1, "LIQUIDITY_SWEEP_CISD", Decimal("100"))),
        (None, CLOSE_2, (CLOSE_2, "FVG_RETRACE_CISD", Decimal("100"))),
        (CLOSE_2, CLOSE_1, (CLOSE_1, "FVG_RETRACE_CISD", Decimal("100"))),
        (CLOSE_1, CLOSE_2, (CLOSE_1, "LIQUIDITY_SWEEP_CISD", Decimal("100"))),
        (None, None, None),
    ],
)
def test_first_confirmed_route_wins_without_cross_route_and(
    monkeypatch: pytest.MonkeyPatch,
    sweep_at: datetime | None,
    fvg_at: datetime | None,
    expected: tuple[datetime, str, Decimal] | None,
) -> None:
    _configure_observers(
        monkeypatch, sweep_confirmed_at=sweep_at, fvg_confirmed_at=fvg_at
    )
    assert capitalizer_high_frequency_capacity_census_v49._earliest_m1_trigger(
        _bars(),
        direction=CapitalizerSourceDirection.BULLISH,
        thesis_at=THESIS,
        deadline_at=DEADLINE,
    ) == expected


def test_fvg_confirmation_must_correspond_to_observed_closed_bar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_observers(
        monkeypatch, sweep_confirmed_at=None,
        fvg_confirmed_at=THESIS + timedelta(minutes=3),
    )
    with pytest.raises(ValueError, match="confirmation bar must exist"):
        capitalizer_high_frequency_capacity_census_v49._earliest_m1_trigger(
            _bars(),
            direction=CapitalizerSourceDirection.BEARISH,
            thesis_at=THESIS,
            deadline_at=DEADLINE,
        )


def test_frozen_v49_does_not_promote_legacy_dual_gate_to_universal_source() -> None:
    from qore.infrastructure.trader_lab.capitalizer_dual_source_entry_acceptance_v1 import (
        CapitalizerM1EntryStructureFacts,
    )
    from qore.infrastructure.trader_lab.capitalizer_high_frequency_decision_graph_v49 import (
        V49_HIGH_FREQUENCY_DECISION_GRAPH,
    )

    assert V49_HIGH_FREQUENCY_DECISION_GRAPH.m1_superintersection_required is False
    # Independently prove and track the inherited AND discrepancy: this fixture
    # is deliberately NOT used as an admission gate by the V49 trigger selector.
    assert not CapitalizerM1EntryStructureFacts(
        market_structure_shift_confirmed=False,
        fair_value_gap_confirmed=True,
        order_block_confirmed=True,
    ).complete
