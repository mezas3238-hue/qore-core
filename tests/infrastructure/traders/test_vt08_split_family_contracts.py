from datetime import UTC, date, datetime

import pytest

from qore.infrastructure.traders.vt08_forex import (
    AUTHORIZED_H4_ANCHOR_HOURS_NEW_YORK as FOREX_ANCHORS,
    AUTHORIZED_MARKETS as FOREX_MARKETS,
    MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NY_DATE as FOREX_DAILY_MAX,
    VT08ForexTrader,
    VT08ForexValidationError,
    config_fingerprint as forex_config_fingerprint,
    methodology_fingerprint as forex_methodology_fingerprint,
)
from qore.infrastructure.traders.vt08_futures import (
    AUTHORIZED_H4_ANCHOR_HOURS_NEW_YORK as FUTURES_ANCHORS,
    AUTHORIZED_MARKETS as FUTURES_MARKETS,
    MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NY_DATE as FUTURES_DAILY_MAX,
    VT08FuturesTrader,
    VT08FuturesValidationError,
    config_fingerprint as futures_config_fingerprint,
    methodology_fingerprint as futures_methodology_fingerprint,
)

_SHA = "a" * 40
_EVIDENCE = "b" * 64


def test_forex_and_futures_have_disjoint_market_authority_and_independent_clocks() -> None:
    assert set(FOREX_MARKETS) == {
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "AUDUSD",
        "USDCAD",
        "GBPJPY",
        "AUDJPY",
    }
    assert set(FUTURES_MARKETS) == {"NAS100", "SP500", "US30"}
    assert set(FOREX_MARKETS).isdisjoint(FUTURES_MARKETS)
    assert FOREX_ANCHORS == (1, 5, 9)
    assert FUTURES_ANCHORS == (2, 6, 10)
    assert FOREX_DAILY_MAX == FUTURES_DAILY_MAX == 1


def test_xauusd_is_outside_both_rebuilt_trader_families() -> None:
    with pytest.raises(VT08ForexValidationError):
        VT08ForexTrader.new_market_day_ledger(
            symbol="XAUUSD",
            observed_at=datetime(2026, 7, 6, 12, tzinfo=UTC),
            eligible_day=True,
            data_complete=True,
            software_sha=_SHA,
            evidence_fingerprint=_EVIDENCE,
        )
    with pytest.raises(VT08FuturesValidationError):
        VT08FuturesTrader.new_market_day_ledger(
            symbol="XAUUSD",
            observed_at=datetime(2026, 7, 6, 12, tzinfo=UTC),
            eligible_day=True,
            data_complete=True,
            software_sha=_SHA,
            evidence_fingerprint=_EVIDENCE,
        )


def test_cross_family_market_substitution_fails_closed() -> None:
    with pytest.raises(VT08ForexValidationError):
        VT08ForexTrader.new_market_day_ledger(
            symbol="NAS100",
            observed_at=datetime(2026, 7, 6, 12, tzinfo=UTC),
            eligible_day=True,
            data_complete=True,
            software_sha=_SHA,
            evidence_fingerprint=_EVIDENCE,
        )
    with pytest.raises(VT08FuturesValidationError):
        VT08FuturesTrader.new_market_day_ledger(
            symbol="EURUSD",
            observed_at=datetime(2026, 7, 6, 12, tzinfo=UTC),
            eligible_day=True,
            data_complete=True,
            software_sha=_SHA,
            evidence_fingerprint=_EVIDENCE,
        )


def test_each_family_creates_its_own_market_day_identity_and_authorized_windows() -> None:
    timestamp = datetime(2026, 7, 6, 12, tzinfo=UTC)
    forex = VT08ForexTrader.new_market_day_ledger(
        symbol="EURUSD",
        observed_at=timestamp,
        eligible_day=True,
        data_complete=True,
        software_sha=_SHA,
        evidence_fingerprint=_EVIDENCE,
    )
    futures = VT08FuturesTrader.new_market_day_ledger(
        symbol="NAS100",
        observed_at=timestamp,
        eligible_day=True,
        data_complete=True,
        software_sha=_SHA,
        evidence_fingerprint=_EVIDENCE,
    )
    assert forex.market_day_id.local_date == date(2026, 7, 6)
    assert futures.market_day_id.local_date == date(2026, 7, 6)
    assert forex.market_day_id.trader_family == "vt08-forex"
    assert futures.market_day_id.trader_family == "vt08-futures"
    assert forex.authorized_windows == FOREX_ANCHORS
    assert futures.authorized_windows == FUTURES_ANCHORS


def test_family_fingerprints_are_deterministic_and_not_interchangeable() -> None:
    assert forex_methodology_fingerprint() == forex_methodology_fingerprint()
    assert futures_methodology_fingerprint() == futures_methodology_fingerprint()
    assert forex_config_fingerprint() == forex_config_fingerprint()
    assert futures_config_fingerprint() == futures_config_fingerprint()
    assert forex_methodology_fingerprint() != futures_methodology_fingerprint()
    assert forex_config_fingerprint() != futures_config_fingerprint()
