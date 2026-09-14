from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt31_r4_ny_reversal_candidate import (
    CANDIDATE_ID,
    Bar,
    Setup,
    _new_protected_stop,
    _simulate,
    contract_fingerprint,
    contract_payload,
    select_simultaneous,
)


def _bar(
    minute: int,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Bar:
    opened = datetime(2026, 1, 2, 14, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return Bar(
        opened,
        opened + timedelta(minutes=1),
        Decimal(open_),
        Decimal(high),
        Decimal(low),
        Decimal(close),
    )


def _setup(market: str, quality: str) -> Setup:
    return Setup(
        market=market,
        local_date=date(2026, 1, 2),
        side="long",
        signal_at=datetime(2026, 1, 2, 15, 0, tzinfo=UTC),
        entry=Decimal("100"),
        initial_stop=Decimal("99"),
        target=Decimal("103"),
        directional_body_fraction=Decimal(quality),
    )


def test_frozen_contract_is_deterministic_and_safe() -> None:
    contract = contract_payload()

    assert contract["candidate_id"] == CANDIDATE_ID
    assert contract["identical_configuration_across_markets"] is True
    assert contract["fresh_acquisition"] == "one-shot-after-freeze"
    assert contract["retuning_after_fresh"] is False
    assert contract["live_authorized"] is False
    assert contract["real_capital_authorized"] is False
    assert contract["production_authorized"] is False
    assert contract_fingerprint() == contract_fingerprint()
    assert len(contract_fingerprint()) == 64


def test_simultaneous_selection_uses_body_fraction_and_abstains_ties() -> None:
    stamp_group = (
        _setup("NAS100", "0.60"),
        _setup("SP500", "0.80"),
        _setup("US30", "0.70"),
    )

    selected = select_simultaneous(stamp_group)

    assert [item.market for item in selected] == ["SP500"]
    assert select_simultaneous((_setup("NAS100", "0.8"), _setup("SP500", "0.8"))) == ()


def test_m1_protected_swing_trails_only_after_sweep_and_cisd_close() -> None:
    confirmed = (
        _bar(0, "10", "12", "9", "11"),
        _bar(1, "12", "13", "10", "13"),
        _bar(2, "13", "13", "8", "11"),
        _bar(3, "11", "15", "10", "14"),
    )
    no_cross = confirmed[:-1] + (_bar(3, "11", "12.5", "10", "12"),)

    assert _new_protected_stop(confirmed, 3, "long", Decimal("7")) == Decimal("8")
    assert _new_protected_stop(no_cross, 3, "long", Decimal("7")) == Decimal("7")


def test_bar_rejects_impossible_ohlc() -> None:
    try:
        _bar(0, "10", "9", "8", "11")
    except ValueError as error:
        assert "OHLC" in str(error)
    else:
        raise AssertionError("invalid OHLC accepted")


def test_gap_immediately_after_entry_is_censored() -> None:
    setup = _setup("NAS100", "0.8")
    first_visible_bar = _bar(61, "100", "100.5", "99.5", "100.25")

    assert _simulate(setup, (first_visible_bar,)) is None
