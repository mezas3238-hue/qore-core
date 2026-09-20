from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r84_source_exact_ps_event_census as r84,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r85_source_exact_ps_continuation_rearm as r85,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r97_persistent_ps_lifecycle as r97,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
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


def _candidate(
    *,
    opened: datetime,
    confirm_index: int,
    protected_swing: str,
) -> r85.SourcePsCandidate:
    event = r84.ProtectedSwingEvent(
        symbol="NAS100",
        h4_opened_at=opened,
        side=DemoTradingSetupSide.LONG,
        confirmed_at=opened + timedelta(minutes=15 * (confirm_index + 1)),
        protected_swing=Decimal(protected_swing),
        series_open=Decimal("100"),
        family=r84.FAMILY_LIQUIDITY,
        source_poi_kind=v6.PoiKind.RELEVANT_SWING.value,
        poi_touch_at=opened,
    )
    return r85.SourcePsCandidate(
        event=event,
        source_poi=v6.SourcePoi(
            v6.PoiKind.RELEVANT_SWING,
            Decimal("99"),
            Decimal("99"),
            opened,
        ),
        confirm_index=confirm_index,
    )


def test_r97_selects_unique_newest_candidate() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    older = _candidate(opened=t0, confirm_index=2, protected_swing="98")
    newer = _candidate(opened=t0, confirm_index=5, protected_swing="99")
    selected, ambiguous = r97._select_unique_newest((older, newer))
    assert ambiguous is False
    assert selected == newer


def test_r97_conflicting_newest_candidates_fail_closed() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    first = _candidate(opened=t0, confirm_index=5, protected_swing="98")
    second = _candidate(opened=t0, confirm_index=5, protected_swing="99")
    selected, ambiguous = r97._select_unique_newest((first, second))
    assert selected is None
    assert ambiguous is True


def test_r97_active_swing_invalidates_mechanically() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    state = r97.ActiveProtectedSwing(
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
        confirmed_at=t0,
        source_h4_opened_at=t0,
        source_kind="IDEAL_C2",
    )
    safe = _bar(
        t0 + timedelta(hours=4),
        open_="101",
        high="102",
        low="99.1",
        close="101.5",
    )
    broken = _bar(
        t0 + timedelta(hours=4, minutes=15),
        open_="101.5",
        high="102",
        low="98.9",
        close="100",
    )
    assert r97._invalidated(safe, state=state) is False
    assert r97._invalidated(broken, state=state) is True


def test_r97_continuation_requires_break_and_close() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="102",
            low="100",
            close="101.5",
        ),
    )
    assert r97._is_continuation(
        bars,
        index=1,
        side=DemoTradingSetupSide.LONG,
    )


def test_r97_r96_evidence_is_pinned() -> None:
    assert r97.SOURCE_R96_RUN_ID == 35532300657
    assert r97.SOURCE_R96_ARTIFACT_ID == 10612280518
    assert r97.SOURCE_R96_ARTIFACT_DIGEST == (
        "sha256:7d3a61fe6d32b94585e370b70036ac5d3eb99330bc3524250965e53bc83ea861"
    )
