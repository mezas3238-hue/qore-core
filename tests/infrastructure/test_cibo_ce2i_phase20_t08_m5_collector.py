from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_ce2i_phase20_t08_factor_returns import (
    FROZEN_T08_MARKET_SYMBOLS,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_store import (
    DurableT08FactorEvidenceError,
    build_delayed_t08_factor_snapshot,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_m5_collector import (
    collect_finalized_t08_m5_boundary_opens,
)

BOUNDARY = datetime(2026, 9, 29, 1, tzinfo=UTC)
LEGACY_SERVER_TZ = ZoneInfo("Europe/Helsinki")
PROVIDER_SYMBOLS = {
    "AUDJPY": "AUDJPY",
    "EURUSD": "EURUSD",
    "GBPJPY": "GBPJPY",
    "GBPUSD": "GBPUSD",
    "NAS100": "NDX100",
    "XAUUSD": "XAUUSD",
}


class _FakeApi:
    TIMEFRAME_M5 = object()

    def __init__(self, *, missing: str | None = None) -> None:
        self.missing = missing
        self.calls: list[str] = []

    def copy_rates_from_pos(
        self,
        symbol: str,
        timeframe: object,
        start: int,
        count: int,
    ) -> list[dict[str, object]]:
        assert timeframe is self.TIMEFRAME_M5
        assert start == 0
        assert count == 16
        self.calls.append(symbol)
        if symbol == self.missing:
            return [
                _row(
                    opened_at=BOUNDARY - timedelta(minutes=5),
                    open_price=100,
                )
            ]
        return [
            _row(
                opened_at=BOUNDARY - timedelta(minutes=5),
                open_price=99,
            ),
            _row(
                opened_at=BOUNDARY,
                open_price=(20000 if symbol == "NDX100" else 100),
            ),
        ]


def _row(
    *,
    opened_at: datetime,
    open_price: int,
) -> dict[str, object]:
    provider_wall_clock = opened_at.astimezone(
        LEGACY_SERVER_TZ
    ).replace(tzinfo=UTC)
    return {
        "time": int(provider_wall_clock.timestamp()),
        "open": open_price,
        "high": open_price + 1,
        "low": open_price - 1,
        "close": open_price,
    }


def test_collector_reads_all_six_finalized_boundary_opens_after_sla() -> None:
    api = _FakeApi()
    observed_at = BOUNDARY + timedelta(minutes=5, seconds=1)

    opens = collect_finalized_t08_m5_boundary_opens(
        api,
        provider_symbols=PROVIDER_SYMBOLS,
        boundary_at=BOUNDARY,
        observed_at=observed_at,
    )
    snapshot = build_delayed_t08_factor_snapshot(
        provider_key="ctrader-demo-observational",
        boundary_opens=opens,
    )

    assert tuple(item.qore_symbol for item in opens) == (
        FROZEN_T08_MARKET_SYMBOLS
    )
    assert set(api.calls) == set(PROVIDER_SYMBOLS.values())
    assert snapshot.market_at == BOUNDARY
    assert snapshot.observed_at == observed_at
    assert snapshot.complete_frozen_universe is True


def test_collector_refuses_to_read_before_m5_bar_finalizes() -> None:
    with pytest.raises(
        DurableT08FactorEvidenceError,
        match="must wait",
    ):
        collect_finalized_t08_m5_boundary_opens(
            _FakeApi(),
            provider_symbols=PROVIDER_SYMBOLS,
            boundary_at=BOUNDARY,
            observed_at=BOUNDARY + timedelta(seconds=3),
        )


def test_collector_fails_closed_when_nas100_boundary_bar_missing() -> None:
    with pytest.raises(
        DurableT08FactorEvidenceError,
        match="missing:NAS100",
    ):
        collect_finalized_t08_m5_boundary_opens(
            _FakeApi(missing="NDX100"),
            provider_symbols=PROVIDER_SYMBOLS,
            boundary_at=BOUNDARY,
            observed_at=BOUNDARY + timedelta(minutes=5, seconds=1),
        )


def test_collector_requires_exact_six_market_provider_map() -> None:
    incomplete = dict(PROVIDER_SYMBOLS)
    incomplete.pop("NAS100")

    with pytest.raises(
        DurableT08FactorEvidenceError,
        match="exact frozen universe",
    ):
        collect_finalized_t08_m5_boundary_opens(
            _FakeApi(),
            provider_symbols=incomplete,
            boundary_at=BOUNDARY,
            observed_at=BOUNDARY + timedelta(minutes=5, seconds=1),
        )
