from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from qore.infrastructure.ctrader_demo_full_api import CTraderDemoFullApi


def _api_with_sessions() -> CTraderDemoFullApi:
    api = CTraderDemoFullApi.__new__(CTraderDemoFullApi)
    api._canonical = lambda symbol: symbol  # type: ignore[method-assign]
    api._weekly_sessions = {
        "EURUSD": (
            ZoneInfo("America/New_York"),
            (
                (61260, 147540),
                (147660, 233940),
                (234060, 320340),
                (320460, 406740),
                (406860, 493020),
            ),
        ),
        "XAUUSD": (
            ZoneInfo("America/New_York"),
            (
                (64920, 147540),
                (151320, 233940),
                (237720, 320340),
                (324120, 406740),
                (410520, 493020),
            ),
        ),
        "NAS100": (
            ZoneInfo("America/Chicago"),
            (
                (61200, 143940),
                (147600, 230340),
                (234000, 316740),
                (320400, 403140),
                (406800, 489540),
            ),
        ),
    }
    api._session_holidays = {}
    return api


def test_broker_rollover_gaps_are_not_reported_open() -> None:
    api = _api_with_sessions()
    at_rollover = datetime(2026, 9, 24, 21, 0, tzinfo=UTC)
    assert api.session_open("EURUSD", at_rollover) is False
    assert api.session_open("XAUUSD", at_rollover) is False
    assert api.session_open("NAS100", at_rollover) is False


def test_each_market_reopens_on_its_native_schedule() -> None:
    api = _api_with_sessions()
    assert api.session_open(
        "EURUSD", datetime(2026, 9, 24, 21, 26, tzinfo=UTC)
    )
    assert not api.session_open(
        "XAUUSD", datetime(2026, 9, 24, 21, 26, tzinfo=UTC)
    )
    assert not api.session_open(
        "NAS100", datetime(2026, 9, 24, 21, 26, tzinfo=UTC)
    )
    at_2300 = datetime(2026, 9, 24, 23, 0, tzinfo=UTC)
    assert api.session_open("EURUSD", at_2300)
    assert api.session_open("XAUUSD", at_2300)
    assert api.session_open("NAS100", at_2300)
