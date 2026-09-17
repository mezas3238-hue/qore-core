from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

from qore.infrastructure.trader_lab import cibo_xauusd_market_intelligence_v1 as dossier
from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab as behavior
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import SourceCandle


def _source(*, low: str, high: str, close: str) -> SourceCandle:
    opened = datetime(2025, 1, 2, 10, tzinfo=UTC)
    return SourceCandle(
        opened_at=opened,
        closed_at=opened + timedelta(hours=1),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        m5=(),
    )


def _event(*, side: str, reference_level: str) -> behavior.Event:
    source = datetime(2025, 1, 2, 10, tzinfo=UTC)
    raw = SimpleNamespace(
        reference_type="prior-candle",
        timeframe="H1",
        source_opened_at=source,
        side=side,
        reference_level=Decimal(reference_level),
    )
    return cast(behavior.Event, raw)


def test_exact_c2_long_requires_sweep_and_close_back_inside() -> None:
    source = _source(low="98", high="106", close="101")
    frames = {"H1": {source.opened_at: source}}
    assert dossier._exact_c2_closure(_event(side="long", reference_level="100"), frames)

    failed = _source(low="98", high="106", close="99")
    frames = {"H1": {failed.opened_at: failed}}
    assert not dossier._exact_c2_closure(
        _event(side="long", reference_level="100"), frames
    )


def test_exact_c2_short_requires_sweep_and_close_back_inside() -> None:
    source = _source(low="94", high="102", close="99")
    frames = {"H1": {source.opened_at: source}}
    assert dossier._exact_c2_closure(_event(side="short", reference_level="100"), frames)

    failed = _source(low="94", high="102", close="101")
    frames = {"H1": {failed.opened_at: failed}}
    assert not dossier._exact_c2_closure(
        _event(side="short", reference_level="100"), frames
    )


def test_non_prior_reference_fails_closed_for_c2() -> None:
    event = _event(side="long", reference_level="100")
    event = cast(
        behavior.Event,
        SimpleNamespace(
            reference_type="swing-3",
            timeframe=event.timeframe,
            source_opened_at=event.source_opened_at,
            side=event.side,
            reference_level=event.reference_level,
        ),
    )
    assert dossier._exact_c2_closure(event, {}) is None


def test_dossier_governance_is_research_only() -> None:
    assert dossier.IDENTITY == "CIBO_XAUUSD_MARKET_INTELLIGENCE_DOSSIER_V1"
    assert dossier.SYMBOL == "XAUUSD"
    assert dossier.EVIDENCE_TIER == "E1_ASSOCIATION_ONLY"
    assert dossier.SOURCE_M5_RUN_ID == 35166210458
    assert dossier.SOURCE_JOURNEY_RUN_ID == 35175979474
