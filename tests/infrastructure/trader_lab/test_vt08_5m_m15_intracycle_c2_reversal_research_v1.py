"""Adversarial tests for source-supported M15 intracycle C2 research."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab import (
    vt08_5m_m15_intracycle_c2_reversal_research_v1 as lab,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

NY = ZoneInfo("America/New_York")


def bar(
    t: datetime,
    o: str,
    h: str,
    low: str,
    c: str,
) -> Vt08B01Bar:
    return Vt08B01Bar(
        opened_at=t.astimezone(UTC),
        closed_at=(t + timedelta(minutes=15)).astimezone(UTC),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
    )


def fixture_bars() -> tuple[Vt08B01Bar, ...]:
    open_at = datetime(2026, 1, 5, 1, tzinfo=NY)
    rows = [
        bar(open_at, "100.10", "100.15", "99.70", "99.90"),
        bar(
            open_at + timedelta(minutes=15),
            "99.90",
            "100.40",
            "99.80",
            "100.30",
        ),
        bar(
            open_at + timedelta(minutes=30),
            "100.25",
            "100.40",
            "100.10",
            "100.30",
        ),
    ]
    rows.extend(
        bar(
            open_at + timedelta(minutes=15 * i),
            "100.30",
            "100.50",
            "100.20",
            "100.35",
        )
        for i in range(3, 16)
    )
    return tuple(rows)


def _mock_prior(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        lab,
        "source_h4_from_m15",
        lambda *args, **kwargs: SimpleNamespace(
            low=Decimal("100.00"), high=Decimal("102.00")
        ),
    )
    monkeypatch.setattr(
        lab,
        "_latest_complete_source_days",
        lambda *args, **kwargs: (object(), object()),
    )
    monkeypatch.setattr(
        lab,
        "resolve_bias",
        lambda *args, **kwargs: DemoTradingSetupSide.LONG,
    )


def test_intracycle_entry_after_cisd_and_source_wick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_prior(monkeypatch)
    rows = fixture_bars()
    signal, status = lab.cycle_signal(
        market="EURJPY",
        anchor=rows[0],
        bars_by_open={r.opened_at: r for r in rows},
        evidence_fingerprint="a" * 64,
    )
    assert status == "CAUSAL_NEXT_M15_OPEN_QORE_RESEARCH_FILL"
    assert signal is not None
    assert signal.side is DemoTradingSetupSide.LONG
    assert signal.confirmed_at == rows[1].closed_at
    assert signal.decision_at == rows[2].opened_at
    assert signal.entry == Decimal("100.25")
    assert signal.stop == Decimal("99.70")
    assert signal.target == Decimal("101.35")
    assert signal.decision_at < signal.expires_at
    assert signal.payload()["cognitive_replay"] is False
    assert signal.payload()["broker_costs"] == "NOT_MODELED"


def test_missing_future_bars_cannot_veto_already_confirmed_ps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_prior(monkeypatch)
    rows = fixture_bars()[:3]
    signal, status = lab.cycle_signal(
        market="EURJPY",
        anchor=rows[0],
        bars_by_open={r.opened_at: r for r in rows},
        evidence_fingerprint="b" * 64,
    )
    assert signal is not None
    assert status == "CAUSAL_NEXT_M15_OPEN_QORE_RESEARCH_FILL"
    assert lab.replay_trade(
        signal, {r.opened_at: r for r in rows}
    ) is None


def test_no_next_bar_no_retroactive_confirmed_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_prior(monkeypatch)
    rows = fixture_bars()[:2]
    signal, status = lab.cycle_signal(
        market="EURJPY",
        anchor=rows[0],
        bars_by_open={r.opened_at: r for r in rows},
        evidence_fingerprint="c" * 64,
    )
    assert signal is None
    assert status == "NO_NEXT_M15_OPEN"


def test_stop_first_with_same_bar_stop_and_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_prior(monkeypatch)
    rows = list(fixture_bars())
    signal, _ = lab.cycle_signal(
        market="EURJPY",
        anchor=rows[0],
        bars_by_open={r.opened_at: r for r in rows},
        evidence_fingerprint="d" * 64,
    )
    assert signal is not None
    rows[2] = bar(
        rows[2].opened_at, "100.25", "102.00", "99.60", "100.30"
    )
    trade = lab.replay_trade(signal, {r.opened_at: r for r in rows})
    assert trade is not None
    assert trade.exit_reason == "stop_first_ambiguous"
    assert trade.r_multiple == Decimal("-1")


def test_infinite_or_wrong_2r_geometry_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    _mock_prior(monkeypatch)
    rows = fixture_bars()
    signal, _ = lab.cycle_signal(
        market="EURJPY",
        anchor=rows[0],
        bars_by_open={r.opened_at: r for r in rows},
        evidence_fingerprint="f" * 64,
    )
    assert signal is not None
    with pytest.raises(ValueError, match="invalid risk geometry"):
        replace(signal, stop=Decimal("101"))
    with pytest.raises(ValueError, match="2R"):
        replace(signal, target=Decimal("101.00"))


def test_owner_13_ny_not_new_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_prior(monkeypatch)
    rows = fixture_bars()
    shifted = bar(
        datetime(2026, 1, 5, 13, tzinfo=NY),
        "100.10", "100.15", "99.70", "99.90",
    )
    signal, status = lab.cycle_signal(
        market="EURJPY",
        anchor=shifted,
        bars_by_open={r.opened_at: r for r in rows},
        evidence_fingerprint="e" * 64,
    )
    assert signal is None
    assert status == "OUTSIDE_OWNER_ANCHOR"


def test_source_id_depends_on_causal_origin_not_future_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_prior(monkeypatch)
    rows = fixture_bars()
    s1, _ = lab.cycle_signal(
        market="EURJPY",
        anchor=rows[0],
        bars_by_open={r.opened_at: r for r in rows},
        evidence_fingerprint="a" * 64,
    )
    s2, _ = lab.cycle_signal(
        market="EURJPY",
        anchor=rows[0],
        bars_by_open={r.opened_at: r for r in rows},
        evidence_fingerprint="b" * 64,
    )
    assert s1 is not None and s2 is not None
    assert s1.source_event_id() == s2.source_event_id()
