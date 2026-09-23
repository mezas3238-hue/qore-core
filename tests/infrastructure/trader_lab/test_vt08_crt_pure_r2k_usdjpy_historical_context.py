from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab.vt08_crt_pure_r2k_usdjpy_historical_context import (
    BASE_POLICY,
    END,
    FOLD,
    MARKET,
    START,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2k_window_and_market_are_frozen() -> None:
    assert MARKET is CrtPureMarket.USDJPY
    assert START == datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
    assert FOLD == datetime(2023, 9, 21, 0, 0, tzinfo=UTC)
    assert END == datetime(2024, 9, 21, 0, 0, tzinfo=UTC)


def test_r2k_reuses_r2g_newest_competition() -> None:
    assert BASE_POLICY is CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
