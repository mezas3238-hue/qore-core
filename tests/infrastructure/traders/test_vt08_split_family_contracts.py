from datetime import UTC, date, datetime

import pytest

from qore.infrastructure.traders.vt08_forex import (
    AUTHORIZED_MARKETS as FOREX_MARKETS,
)
from qore.infrastructure.traders.vt08_forex import (
    MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NY_DATE as FOREX_DAILY_MAX,
)
from qore.infrastructure.traders.vt08_forex import (
    OWNER_OPERATIONAL_H4_ANCHORS_NEW_YORK as FOREX_OWNER_ANCHORS,
)
from qore.infrastructure.traders.vt08_forex import (
    SOURCE_COMPLETE_H4_ANCHORS_NEW_YORK as FOREX_SOURCE_ANCHORS,
)
from qore.infrastructure.traders.vt08_forex import (
    VT08ForexTrader,
    VT08ForexValidationError,
)
from qore.infrastructure.traders.vt08_forex import (
    config_fingerprint as forex_config_fingerprint,
)
from qore.infrastructure.traders.vt08_forex import (
    methodology_fingerprint as forex_methodology_fingerprint,
)
from qore.infrastructure.traders.vt08_futures import (
    AUTHORIZED_MARKETS as FUTURES_MARKETS,
)
from qore.infrastructure.traders.vt08_futures import (
    MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NY_DATE as FUTURES_DAILY_MAX,
)
from qore.infrastructure.traders.vt08_futures import (
    OWNER_OPERATIONAL_H4_ANCHORS_NEW_YORK as FUTURES_OWNER_ANCHORS,
)
from qore.infrastructure.traders.vt08_futures import (
    SOURCE_COMPLETE_H4_ANCHORS_NEW_YORK as FUTURES_SOURCE_ANCHORS,
)
from qore.infrastructure.traders.vt08_futures import (
    VT08FuturesTrader,
    VT08FuturesValidationError,
)
from qore.infrastructure.traders.vt08_futures import (
    config_fingerprint as futures_config_fingerprint,
)
from qore.infrastructure.traders.vt08_futures import (
    methodology_fingerprint as futures_methodology_fingerprint,
)
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import (
    VT08LtfProfile,
    VT08TimingProfile,
)

_SHA = "a" * 40
_EVIDENCE = "b" * 64


def test_forex_and_futures_have_disjoint_market_authority_and_two_timing_profiles() -> None:
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
    assert FOREX_SOURCE_ANCHORS == (1, 5, 9, 13)
    assert FOREX_OWNER_ANCHORS == (1, 5, 9)
    assert FUTURES_SOURCE_ANCHORS == (2, 6, 10, 14)
    assert FUTURES_OWNER_ANCHORS == (2, 6, 10)
    assert FOREX_DAILY_MAX == FUTURES_DAILY_MAX == 1


def test_xauusd_and_cross_family_substitution_fail_closed() -> None:
    with pytest.raises(VT08ForexValidationError):
        VT08ForexTrader.new_market_day_ledger(
            symbol="XAUUSD",
            observed_at=datetime(2026, 7, 6, 12, tzinfo=UTC),
            eligible_day=True,
            data_complete=True,
            software_sha=_SHA,
            evidence_fingerprint=_EVIDENCE,
            timing_profile=VT08TimingProfile.SOURCE_COMPLETE,
            ltf_profile=VT08LtfProfile.M15,
        )
    with pytest.raises(VT08FuturesValidationError):
        VT08FuturesTrader.new_market_day_ledger(
            symbol="XAUUSD",
            observed_at=datetime(2026, 7, 6, 12, tzinfo=UTC),
            eligible_day=True,
            data_complete=True,
            software_sha=_SHA,
            evidence_fingerprint=_EVIDENCE,
            timing_profile=VT08TimingProfile.SOURCE_COMPLETE,
            ltf_profile=VT08LtfProfile.M15,
        )
    with pytest.raises(VT08ForexValidationError):
        VT08ForexTrader.new_market_day_ledger(
            symbol="NAS100",
            observed_at=datetime(2026, 7, 6, 12, tzinfo=UTC),
            eligible_day=True,
            data_complete=True,
            software_sha=_SHA,
            evidence_fingerprint=_EVIDENCE,
            timing_profile=VT08TimingProfile.SOURCE_COMPLETE,
            ltf_profile=VT08LtfProfile.M15,
        )
    with pytest.raises(VT08FuturesValidationError):
        VT08FuturesTrader.new_market_day_ledger(
            symbol="EURUSD",
            observed_at=datetime(2026, 7, 6, 12, tzinfo=UTC),
            eligible_day=True,
            data_complete=True,
            software_sha=_SHA,
            evidence_fingerprint=_EVIDENCE,
            timing_profile=VT08TimingProfile.SOURCE_COMPLETE,
            ltf_profile=VT08LtfProfile.M15,
        )


def test_each_family_creates_independent_source_complete_market_day_ledger() -> None:
    forex = VT08ForexTrader.new_market_day_ledger(
        symbol="EURUSD",
        observed_at=datetime(2026, 7, 6, 12, tzinfo=UTC),
        eligible_day=True,
        data_complete=True,
        software_sha=_SHA,
        evidence_fingerprint=_EVIDENCE,
        timing_profile=VT08TimingProfile.SOURCE_COMPLETE,
        ltf_profile=VT08LtfProfile.M15,
    )
    futures = VT08FuturesTrader.new_market_day_ledger(
        symbol="NAS100",
        observed_at=datetime(2026, 7, 6, 12, tzinfo=UTC),
        eligible_day=True,
        data_complete=True,
        software_sha=_SHA,
        evidence_fingerprint=_EVIDENCE,
        timing_profile=VT08TimingProfile.SOURCE_COMPLETE,
        ltf_profile=VT08LtfProfile.M15,
    )
    assert forex.cardinality.market_day_id.local_date == date(2026, 7, 6)
    assert futures.cardinality.market_day_id.local_date == date(2026, 7, 6)
    assert forex.cardinality.market_day_id.trader_family == "vt08-forex"
    assert futures.cardinality.market_day_id.trader_family == "vt08-futures"
    assert forex.cardinality.authorized_windows == FOREX_SOURCE_ANCHORS
    assert futures.cardinality.authorized_windows == FUTURES_SOURCE_ANCHORS
    assert forex.timing_profile is VT08TimingProfile.SOURCE_COMPLETE
    assert futures.ltf_profile is VT08LtfProfile.M15


def test_owner_subset_is_explicitly_distinct_from_source_complete() -> None:
    timestamp = datetime(2026, 7, 6, 12, tzinfo=UTC)
    forex = VT08ForexTrader.new_market_day_ledger(
        symbol="EURUSD",
        observed_at=timestamp,
        eligible_day=True,
        data_complete=True,
        software_sha=_SHA,
        evidence_fingerprint=_EVIDENCE,
        timing_profile=VT08TimingProfile.OWNER_OPERATIONAL,
        ltf_profile=VT08LtfProfile.M5_FRACTAL,
    )
    futures = VT08FuturesTrader.new_market_day_ledger(
        symbol="NAS100",
        observed_at=timestamp,
        eligible_day=True,
        data_complete=True,
        software_sha=_SHA,
        evidence_fingerprint=_EVIDENCE,
        timing_profile=VT08TimingProfile.OWNER_OPERATIONAL,
        ltf_profile=VT08LtfProfile.M3_FRACTAL,
    )
    assert forex.cardinality.authorized_windows == FOREX_OWNER_ANCHORS
    assert futures.cardinality.authorized_windows == FUTURES_OWNER_ANCHORS
    assert forex.ltf_profile is VT08LtfProfile.M5_FRACTAL
    assert futures.ltf_profile is VT08LtfProfile.M3_FRACTAL


def test_family_fingerprints_are_deterministic_and_not_interchangeable() -> None:
    assert forex_methodology_fingerprint() == forex_methodology_fingerprint()
    assert futures_methodology_fingerprint() == futures_methodology_fingerprint()
    assert forex_config_fingerprint() == forex_config_fingerprint()
    assert futures_config_fingerprint() == futures_config_fingerprint()
    assert forex_methodology_fingerprint() != futures_methodology_fingerprint()
    assert forex_config_fingerprint() != futures_config_fingerprint()
