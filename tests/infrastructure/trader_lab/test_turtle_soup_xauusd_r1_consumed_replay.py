from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1_consumed_replay as replay


def test_consumed_replay_identity_and_window() -> None:
    assert replay.IDENTITY == "TURTLE_SOUP_XAUUSD_R1_CONSUMED_10Y_REPLAY_V1"
    assert replay.SOURCE_RUN_ID == 35166210458
    assert replay.SOURCE_ARTIFACT_ID == 10476557530
    assert replay.EVAL_OPEN == datetime(2016, 9, 17, tzinfo=UTC)
    assert replay.EVAL_CLOSE == datetime(2026, 9, 17, tzinfo=UTC)
    assert r1.IDENTITY == "TURTLE_SOUP_XAUUSD_R1"


def test_stat_delegates_to_frozen_r1() -> None:
    values = [Decimal("1"), Decimal("-1"), Decimal("0.5")]
    assert replay._stat(values) == r1._stat(values)


def test_frozen_candidate_has_no_retrospective_filters() -> None:
    assert r1.TIMEFRAME_PRIORITY == {"H4": 0, "H1": 1}
    assert r1.PRIMARY_FRICTION_R == Decimal("0.05")
    assert r1.STRESS_FRICTION_R == Decimal("0.10")
