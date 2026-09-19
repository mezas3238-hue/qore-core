from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_c2_positional_r1_backtest import (
    SOURCE_SOFTWARE_SHA,
    build_report,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    OWNER_ENTRY_ANCHORS_NY,
    Vt08IndexC2R1AbstainReason,
    Vt08IndexC2R1Bar,
    evaluate_at_entry_indexed,
    methodology_fingerprint,
    protected_swings_in_candle2,
    resolve_daily_bias,
)

_NY = ZoneInfo("America/New_York")


def _bar(
    opened_at: datetime,
    *,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    opened_utc = opened_at.astimezone(UTC)
    return Vt08IndexC2R1Bar(
        opened_at=opened_utc,
        closed_at=opened_utc + timedelta(minutes=15),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _flat_session(
    start_local: datetime,
    *,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> list[Vt08IndexC2R1Bar]:
    return [
        _bar(
            start_local + timedelta(minutes=15 * index),
            open_price=open_price,
            high=high,
            low=low,
            close=close,
        )
        for index in range(92)
    ]


def _candidate_bars() -> tuple[dict[datetime, Vt08IndexC2R1Bar], datetime]:
    rows: list[Vt08IndexC2R1Bar] = []
    rows.extend(
        _flat_session(
            datetime(2026, 1, 3, 18, tzinfo=_NY),
            open_price="95",
            high="100",
            low="90",
            close="95",
        )
    )
    rows.extend(
        _flat_session(
            datetime(2026, 1, 4, 18, tzinfo=_NY),
            open_price="95",
            high="110",
            low="94",
            close="105",
        )
    )

    reference_start = datetime(2026, 1, 5, 22, tzinfo=_NY)
    for index in range(16):
        rows.append(
            _bar(
                reference_start + timedelta(minutes=15 * index),
                open_price="100",
                high="105",
                low="95",
                close="100",
            )
        )

    candle2_start = datetime(2026, 1, 6, 2, tzinfo=_NY)
    candle2_values = [
        ("100", "101", "98", "99"),
        ("99", "100", "93", "94"),
        ("94", "102", "94", "101"),
    ]
    for index in range(16):
        values = (
            candle2_values[index]
            if index < len(candle2_values)
            else ("100", "102", "99", "100")
        )
        rows.append(
            _bar(
                candle2_start + timedelta(minutes=15 * index),
                open_price=values[0],
                high=values[1],
                low=values[2],
                close=values[3],
            )
        )

    decision = datetime(2026, 1, 6, 6, tzinfo=_NY).astimezone(UTC)
    rows.append(
        _bar(
            decision,
            open_price="101",
            high="118",
            low="92",
            close="110",
        )
    )
    for index in range(1, 16):
        rows.append(
            _bar(
                decision + timedelta(minutes=15 * index),
                open_price="110",
                high="111",
                low="109",
                close="110",
            )
        )

    bars_by_open = {item.opened_at.astimezone(UTC): item for item in rows}
    return bars_by_open, decision


def test_bias_four_case_and_fingerprint() -> None:
    previous = Vt08IndexC2R1Bar(
        opened_at=datetime(2026, 1, 1, tzinfo=UTC),
        closed_at=datetime(2026, 1, 2, tzinfo=UTC),
        open=Decimal("95"),
        high=Decimal("100"),
        low=Decimal("90"),
        close=Decimal("95"),
    )
    bullish = Vt08IndexC2R1Bar(
        opened_at=datetime(2026, 1, 2, tzinfo=UTC),
        closed_at=datetime(2026, 1, 3, tzinfo=UTC),
        open=Decimal("95"),
        high=Decimal("105"),
        low=Decimal("94"),
        close=Decimal("101"),
    )
    reversal = Vt08IndexC2R1Bar(
        opened_at=datetime(2026, 1, 2, tzinfo=UTC),
        closed_at=datetime(2026, 1, 3, tzinfo=UTC),
        open=Decimal("95"),
        high=Decimal("99"),
        low=Decimal("89"),
        close=Decimal("92"),
    )
    unresolved = Vt08IndexC2R1Bar(
        opened_at=datetime(2026, 1, 2, tzinfo=UTC),
        closed_at=datetime(2026, 1, 3, tzinfo=UTC),
        open=Decimal("95"),
        high=Decimal("99"),
        low=Decimal("91"),
        close=Decimal("96"),
    )

    assert resolve_daily_bias(previous_day=previous, current_day=bullish) is (
        DemoTradingSetupSide.LONG
    )
    assert resolve_daily_bias(previous_day=previous, current_day=reversal) is (
        DemoTradingSetupSide.LONG
    )
    assert resolve_daily_bias(previous_day=previous, current_day=unresolved) is None
    assert len(methodology_fingerprint()) == 64
    assert OWNER_ENTRY_ANCHORS_NY == (2, 6, 10)


def test_completed_c2_produces_one_positional_candidate() -> None:
    bars_by_open, decision = _candidate_bars()
    result = evaluate_at_entry_indexed(
        symbol="NAS100",
        bars_by_open=bars_by_open,
        decision_at=decision,
    )

    assert result.candidate is not None
    assert result.abstain_reason is None
    candidate = result.candidate
    assert candidate.side is DemoTradingSetupSide.LONG
    assert candidate.entry_anchor_hour == 6
    assert candidate.setup.entry_price == Decimal("101")
    assert candidate.setup.invalidation_price == Decimal("93")
    assert candidate.setup.take_profit_price == Decimal("117")


def test_multiple_protected_swings_fail_closed() -> None:
    start = datetime(2026, 1, 6, 2, tzinfo=_NY)
    bars = (
        _bar(start, open_price="100", high="101", low="93", close="94"),
        _bar(
            start + timedelta(minutes=15),
            open_price="94",
            high="102",
            low="94",
            close="101",
        ),
        _bar(
            start + timedelta(minutes=30),
            open_price="101",
            high="102",
            low="92",
            close="93",
        ),
        _bar(
            start + timedelta(minutes=45),
            open_price="93",
            high="103",
            low="93",
            close="102",
        ),
    )
    swings = protected_swings_in_candle2(
        bars,
        side=DemoTradingSetupSide.LONG,
        important_level=Decimal("95"),
    )
    assert len(swings) == 2


def _market_payload(symbol: str, provider: str) -> dict[str, object]:
    bars_by_open, _ = _candidate_bars()
    rows = list(bars_by_open.values())
    rows.extend(
        [
            _bar(
                datetime(2024, 1, 1, tzinfo=UTC),
                open_price="100",
                high="101",
                low="99",
                close="100",
            ),
            _bar(
                datetime(2026, 2, 1, tzinfo=UTC),
                open_price="100",
                high="101",
                low="99",
                close="100",
            ),
        ]
    )
    rows.sort(key=lambda item: item.opened_at)
    return {
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "canonical_symbol": symbol,
        "provider_symbol_name": provider,
        "software_sha": SOURCE_SOFTWARE_SHA,
        "account_fingerprint": "a" * 64,
        "checked_at": "2026-09-13T00:00:00+00:00",
        "primary_source_sha256": "b" * 64,
        "periods": {
            "M15": [
                {
                    "period": "M15",
                    "opened_at": item.opened_at.isoformat(),
                    "closed_at": item.closed_at.isoformat(),
                    "open": format(item.open, "f"),
                    "high": format(item.high, "f"),
                    "low": format(item.low, "f"),
                    "close": format(item.close, "f"),
                }
                for item in rows
            ]
        },
    }


def _write_market(root: Path, symbol: str, provider: str) -> Path:
    root.mkdir(parents=True)
    path = root / "market-evidence.json"
    path.write_text(
        json.dumps(_market_payload(symbol, provider)),
        encoding="utf-8",
    )
    return path


def test_backtest_builds_real_modeled_trade_and_stop_first(tmp_path: Path) -> None:
    nas = _write_market(tmp_path / "NAS100", "NAS100", "USTEC")
    spx = _write_market(tmp_path / "SP500", "SP500", "US500")
    dow = _write_market(tmp_path / "US30", "US30", "US30")

    report = build_report(nas100=nas, sp500=spx, us30=dow)
    aggregate = report["aggregate_equal_risk_trade_economics"]
    assert isinstance(aggregate, dict)
    assert aggregate["sample_size"] == 3
    assert aggregate["winning_trades"] == 0
    assert aggregate["losing_trades"] == 3
    assert aggregate["total_r"] == "-3"
    assert aggregate["stop_count"] == 3
    assert report["governance"] == {
        "pre_economic_freeze_commit": "31bee8643cb09659a66e9ed793c1cb2bf9ba6353",
        "rules_selected_from_retained_economic_outcomes": False,
        "retained_window_is_independent_validation": False,
        "fresh_unseen_validation_required": True,
        "demo_eligible": False,
        "live_authorized": False,
        "production_authorized": False,
    }


def test_outside_anchor_fails_closed() -> None:
    bars_by_open, _ = _candidate_bars()
    decision = datetime(2026, 1, 6, 7, tzinfo=_NY)
    result = evaluate_at_entry_indexed(
        symbol="NAS100",
        bars_by_open=bars_by_open,
        decision_at=decision,
    )
    assert result.candidate is None
    assert result.abstain_reason is Vt08IndexC2R1AbstainReason.OUTSIDE_OWNER_ANCHOR
