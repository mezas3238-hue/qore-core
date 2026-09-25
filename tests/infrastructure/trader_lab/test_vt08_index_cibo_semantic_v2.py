from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

from qore.infrastructure.trader_lab.vt08_index_cibo_semantic_v2 import (
    _departure_row,
    _event_order,
    _find_h4_open,
    _taxonomy,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar


def _h4(opened: datetime) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(hours=4),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
    )


def _trade(*, stopped: bool = True, later2: bool = True) -> dict[str, object]:
    signal = datetime(2024, 1, 2, 15, 0, tzinfo=UTC)
    return {
        "symbol": "NAS100",
        "side": "long",
        "signal_at": signal.isoformat(),
        "weekday_new_york": "Tuesday",
        "anchor_hour_new_york": 6,
        "model_kind": "same-c2-intracandle",
        "poi_kind": "fvg",
        "exit_reason": "stop" if stopped else "target",
        "raw_r": "-1" if stopped else "2",
        "primary_r": "-1.05" if stopped else "1.95",
        "peer_alignment_count": 0,
        "relative_strength_rank": 3,
        "time_to_favorable_levels": {
            "0.5": {
                "hit": later2,
                "minutes": 180 if later2 else None,
                "at": (
                    (signal + timedelta(minutes=180)).isoformat()
                    if later2
                    else None
                ),
            },
            "1": {
                "hit": later2,
                "minutes": 240 if later2 else None,
                "at": (
                    (signal + timedelta(minutes=240)).isoformat()
                    if later2
                    else None
                ),
            },
            "2": {
                "hit": later2,
                "minutes": 300 if later2 else None,
                "at": (
                    (signal + timedelta(minutes=300)).isoformat()
                    if later2
                    else None
                ),
            },
            "3": {"hit": False, "minutes": None, "at": None},
        },
        "horizon_excursions": {
            "1440": {
                "max_favorable_r": "2.1" if later2 else "0.2",
                "max_adverse_r": "1.4",
            }
        },
        "post_stop_afterlife": (
            {
                "levels": {
                    "2": {
                        "hit": later2,
                        "minutes_after_stop": 120 if later2 else None,
                        "at": (
                            (signal + timedelta(minutes=300)).isoformat()
                            if later2
                            else None
                        ),
                    }
                }
            }
            if stopped
            else None
        ),
    }


def test_find_h4_open_uses_containing_anchor_bar() -> None:
    opened = datetime(2024, 1, 2, 11, 0, tzinfo=UTC)
    signal = opened + timedelta(hours=2)
    assert (
        _find_h4_open(
            signal_at=signal,
            anchor_hour_new_york=6,
            h4={opened: _h4(opened)},
        )
        == opened
    )


def test_departure_is_frozen_continuation_not_half_r_proxy() -> None:
    trade = _trade()
    reaction: dict[str, object] = {
        "reaction_at": "2024-01-02T14:00:00+00:00",
    }
    mechanics: dict[str, object] = {
        "source_poi": {
            "first_touch_at": "2024-01-02T14:15:00+00:00",
        },
        "cisd_confirmed_at": "2024-01-02T14:30:00+00:00",
        "protected_swing_confirmed_at": "2024-01-02T14:30:00+00:00",
        "continuation_at": trade["signal_at"],
    }
    row = _departure_row(trade, reaction, mechanics)
    assert row["departure_at"] == trade["signal_at"]
    assert row["departure_definition"] == (
        "frozen-v7-first-causal-m15-continuation-closure"
    )
    proxy = row["legacy_0_5r_proxy"]
    assert isinstance(proxy, dict)
    assert proxy["is_departure_definition"] is False
    assert proxy["at"] != row["departure_at"]


def test_taxonomy_is_explicitly_non_causal_and_multi_label() -> None:
    taxonomy = _taxonomy(
        _trade(),
        {
            "reaction_structure_combo": "order-block+liquidity-sweep",
        },
    )
    assert taxonomy["non_causal_multi_label"] is True
    timing = taxonomy["B_TIMING_ERROR"]
    stop = taxonomy["C_STOP_LOCATION_ERROR"]
    cross = taxonomy["H_CROSS_INDEX_CONTEXT_ERROR"]
    assert isinstance(timing, dict) and timing["status"] == "candidate"
    assert isinstance(stop, dict) and stop["status"] == "candidate"
    assert isinstance(cross, dict) and cross["status"] == "candidate"
    confirmation = taxonomy["E_CONFIRMATION_ERROR"]
    regime = taxonomy["G_REGIME_ERROR"]
    assert isinstance(confirmation, dict) and confirmation["status"] == "unresolved"
    assert isinstance(regime, dict) and regime["status"] == "unresolved"


def test_correct_loss_requires_no_favorable_recovery() -> None:
    taxonomy = _taxonomy(
        _trade(later2=False),
        {"reaction_structure_combo": "none-detected"},
    )
    correct = taxonomy["I_CORRECT_LOSS"]
    assert isinstance(correct, dict)
    assert correct["status"] == "candidate"


def test_cross_index_event_order_tracks_arrival_cisd_and_continuation() -> None:
    base = datetime(2024, 1, 2, 14, 0, tzinfo=UTC)
    cohort: list[dict[str, object]] = []
    mechanics: dict[tuple[str, str], dict[str, object]] = {}
    for offset, symbol in enumerate(("NAS100", "SP500", "US30")):
        signal = base + timedelta(minutes=60 + offset * 15)
        trade: dict[str, object] = {
            "symbol": symbol,
            "signal_at": signal.isoformat(),
        }
        cohort.append(trade)
        mechanics[(symbol, signal.isoformat())] = {
            "source_poi": {
                "first_touch_at": (
                    base + timedelta(minutes=offset * 15)
                ).isoformat()
            },
            "cisd_confirmed_at": (
                base + timedelta(minutes=30 + offset * 15)
            ).isoformat(),
            "continuation_at": signal.isoformat(),
        }
    result = _event_order(cohort, mechanics)
    arrival = cast(dict[str, object], result["source_poi_arrival"])
    cisd = cast(dict[str, object], result["cisd_confirmation"])
    departure = cast(dict[str, object], result["continuation_departure"])
    lags = cast(dict[str, int], departure["lag_minutes"])
    assert arrival["leader"] == "NAS100"
    assert cisd["order"] == ["NAS100", "SP500", "US30"]
    assert lags["US30"] == 30
