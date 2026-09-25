from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r79_fvg_reaction_ps_gap as r79,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r81_fvg_reaction_protected_swing as r81,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    opened: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r81_reaction_series_must_be_born_inside_fvg() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99", close="100.5"),
        _bar(t0 + timedelta(minutes=15), open_="101", high="102", low="100", close="101.5"),
        _bar(t0 + timedelta(minutes=30), open_="102.4", high="103", low="102.2", close="102.8"),
        _bar(t0 + timedelta(minutes=45), open_="102.4", high="102.6", low="101.2", close="101.6"),
        _bar(t0 + timedelta(minutes=60), open_="101.7", high="102.6", low="101.5", close="102.5"),
    )
    fvg = r79.DirectionalFvg(
        low=Decimal("101"),
        high=Decimal("102.2"),
        formed_index=2,
    )
    result = r81._fvg_reaction_cisd(
        bars,
        side=DemoTradingSetupSide.LONG,
        fvg=fvg,
    )
    assert result is not None
    index, level, protected, touch_index = result
    assert index == 4
    assert level == Decimal("102.4")
    assert protected == Decimal("101.2")
    assert touch_index == 3


def test_r81_non_touching_opposing_series_is_ignored() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99", close="100.5"),
        _bar(t0 + timedelta(minutes=15), open_="101", high="102", low="100", close="101.5"),
        _bar(t0 + timedelta(minutes=30), open_="102.4", high="103", low="102.2", close="102.8"),
        _bar(t0 + timedelta(minutes=45), open_="103", high="103.1", low="102.6", close="102.7"),
        _bar(t0 + timedelta(minutes=60), open_="102.8", high="103.5", low="102.7", close="103.4"),
    )
    fvg = r79.DirectionalFvg(
        low=Decimal("101"),
        high=Decimal("102.2"),
        formed_index=2,
    )
    assert r81._fvg_reaction_cisd(
        bars,
        side=DemoTradingSetupSide.LONG,
        fvg=fvg,
    ) is None


def test_r81_source_evidence_is_pinned() -> None:
    assert r81.SOURCE_R79_RUN_ID == 35516202970
    assert r81.SOURCE_R79_ARTIFACT_ID == 10606254504
    assert r81.SOURCE_R80_RUN_ID == 35516661428
    assert r81.SOURCE_R80_ARTIFACT_ID == 10607051824


def test_r81_keeps_canonical_target_to_isolate_ps_architecture() -> None:
    assert r81.TARGET_R == Decimal("2.5")
