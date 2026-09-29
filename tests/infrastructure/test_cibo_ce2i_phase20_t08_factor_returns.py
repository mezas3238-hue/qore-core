from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_returns import (
    FROZEN_T08_MARKET_SYMBOLS,
    T08FactorMarketSnapshot,
    T08MarketCollectionBasis,
    T08MarketMark,
    build_t08_factor_market_snapshot_from_m5_boundaries,
    reconstruct_t08_factor_returns,
)
from qore.infrastructure.m5_boundary_cache import M5BoundarySnapshot
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Evidence,
)

START_AT = datetime(2026, 9, 28, 12, tzinfo=UTC)
END_AT = START_AT + timedelta(minutes=5)


def _mark(
    *,
    symbol: str,
    mid: Decimal,
    market_at: datetime,
    observed_at: datetime,
    suffix: str,
) -> T08MarketMark:
    return T08MarketMark(
        qore_symbol=symbol,
        bid=mid,
        ask=mid,
        price_at=market_at,
        observed_at=observed_at,
        evidence_ref=f"provider:{suffix}:{symbol}",
    )


def _snapshot(
    *,
    snapshot_id: str,
    market_at: datetime,
    prices: dict[str, Decimal],
    basis: T08MarketCollectionBasis = (
        T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE
    ),
    known_delay: timedelta = timedelta(0),
) -> T08FactorMarketSnapshot:
    observed_at = market_at + known_delay
    return T08FactorMarketSnapshot(
        snapshot_id=snapshot_id,
        provider_key="ctrader-demo",
        market_at=market_at,
        observed_at=observed_at,
        collection_basis=basis,
        marks=tuple(
            _mark(
                symbol=symbol,
                mid=prices[symbol],
                market_at=market_at,
                observed_at=observed_at,
                suffix=snapshot_id,
            )
            for symbol in sorted(prices)
        ),
    )


def _boundary(
    *,
    symbol: str,
    anchor: datetime,
    observed_at: datetime,
    price: Decimal,
) -> M5BoundarySnapshot:
    return M5BoundarySnapshot(
        symbol=symbol,
        anchor=anchor,
        evidence=Evidence(symbol=symbol, digits=5, bars=()),
        current_open=price,
        broker_tick_at=anchor,
        observed_at=observed_at,
        new_bar_first_seen_at=observed_at,
        market_state_updated_at=observed_at,
        aggregate_finished_at=observed_at,
        complete_bars=(),
        h1=(),
        h4=(),
        d1=(),
    )


def test_reconstructs_cross_fx_factors_with_usd_numeraire() -> None:
    start_prices = {
        "AUDJPY": Decimal("100"),
        "EURUSD": Decimal("1.10"),
        "GBPJPY": Decimal("190"),
        "GBPUSD": Decimal("1.25"),
        "NAS100": Decimal("20000"),
        "XAUUSD": Decimal("3800"),
    }
    factor_gross = {
        "AUD": Decimal("1.01"),
        "EUR": Decimal("1.03"),
        "GBP": Decimal("1.02"),
        "JPY": Decimal("0.99"),
        "USD": Decimal("1"),
        "US_TECH_EQUITY_BETA": Decimal("1.04"),
        "XAU": Decimal("0.98"),
    }
    end_prices = {
        "AUDJPY": (
            start_prices["AUDJPY"]
            * factor_gross["AUD"]
            / factor_gross["JPY"]
        ),
        "EURUSD": start_prices["EURUSD"] * factor_gross["EUR"],
        "GBPJPY": (
            start_prices["GBPJPY"]
            * factor_gross["GBP"]
            / factor_gross["JPY"]
        ),
        "GBPUSD": start_prices["GBPUSD"] * factor_gross["GBP"],
        "NAS100": (
            start_prices["NAS100"]
            * factor_gross["US_TECH_EQUITY_BETA"]
        ),
        "XAUUSD": start_prices["XAUUSD"] * factor_gross["XAU"],
    }

    observation = reconstruct_t08_factor_returns(
        start=_snapshot(
            snapshot_id="s0",
            market_at=START_AT,
            prices=start_prices,
            known_delay=timedelta(milliseconds=400),
        ),
        end=_snapshot(
            snapshot_id="s1",
            market_at=END_AT,
            prices=end_prices,
            known_delay=timedelta(milliseconds=500),
        ),
    )

    tolerance = Decimal("1e-24")
    for factor_id, gross in factor_gross.items():
        assert abs(
            observation.return_for(factor_id)
            - (gross - Decimal(1))
        ) <= tolerance
    assert observation.return_for("USD") == Decimal(0)
    assert observation.known_at == END_AT + timedelta(milliseconds=500)
    assert len(observation.source_evidence_refs) == 12


def test_candidate_only_market_evidence_is_rejected_for_t08_returns() -> None:
    start = _snapshot(
        snapshot_id="candidate-s0",
        market_at=START_AT,
        prices={"GBPUSD": Decimal("1.25")},
        basis=T08MarketCollectionBasis.CANDIDATE_ONLY,
    )
    end = _snapshot(
        snapshot_id="candidate-s1",
        market_at=END_AT,
        prices={"GBPUSD": Decimal("1.26")},
        basis=T08MarketCollectionBasis.CANDIDATE_ONLY,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="candidate-conditioned/incomplete",
    ):
        reconstruct_t08_factor_returns(start=start, end=end)


def test_full_universe_snapshot_rejects_missing_symbol() -> None:
    prices = {
        symbol: Decimal("1")
        for symbol in FROZEN_T08_MARKET_SYMBOLS
        if symbol != "NAS100"
    }

    with pytest.raises(
        CiboCapitalManagementError,
        match="every frozen symbol",
    ):
        _snapshot(
            snapshot_id="incomplete",
            market_at=START_AT,
            prices=prices,
        )


def test_factor_return_reconstruction_rejects_cross_provider_mix() -> None:
    prices = {
        "AUDJPY": Decimal("100"),
        "EURUSD": Decimal("1.10"),
        "GBPJPY": Decimal("190"),
        "GBPUSD": Decimal("1.25"),
        "NAS100": Decimal("20000"),
        "XAUUSD": Decimal("3800"),
    }
    start = _snapshot(
        snapshot_id="s0",
        market_at=START_AT,
        prices=prices,
    )
    other_known_at = END_AT + timedelta(milliseconds=100)
    end = T08FactorMarketSnapshot(
        snapshot_id="s1",
        provider_key="other-provider",
        market_at=END_AT,
        observed_at=other_known_at,
        collection_basis=T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE,
        marks=tuple(
            _mark(
                symbol=symbol,
                mid=value,
                market_at=END_AT,
                observed_at=other_known_at,
                suffix="s1",
            )
            for symbol, value in sorted(prices.items())
        ),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="one provider",
    ):
        reconstruct_t08_factor_returns(start=start, end=end)


def test_m5_builder_waits_for_last_frozen_symbol_capture() -> None:
    prices = {
        "AUDJPY": Decimal("100"),
        "EURUSD": Decimal("1.10"),
        "GBPJPY": Decimal("190"),
        "GBPUSD": Decimal("1.25"),
        "NAS100": Decimal("20000"),
        "XAUUSD": Decimal("3800"),
    }
    snapshots = tuple(
        _boundary(
            symbol=symbol,
            anchor=START_AT,
            observed_at=START_AT + timedelta(milliseconds=index * 10),
            price=prices[symbol],
        )
        for index, symbol in enumerate(FROZEN_T08_MARKET_SYMBOLS, start=1)
    )

    factor_snapshot = build_t08_factor_market_snapshot_from_m5_boundaries(
        provider_key="fundednext-mt5",
        snapshots=snapshots,
    )

    assert factor_snapshot.complete_frozen_universe is True
    assert factor_snapshot.market_at == START_AT
    assert factor_snapshot.observed_at == START_AT + timedelta(milliseconds=60)
    assert factor_snapshot.snapshot_id.startswith("sha256:")
    assert len(factor_snapshot.snapshot_id) == 71
    assert all(item.price_at == START_AT for item in factor_snapshot.marks)
    assert max(item.observed_at for item in factor_snapshot.marks) == (
        factor_snapshot.observed_at
    )


def test_m5_builder_fails_closed_when_one_market_is_missing() -> None:
    snapshots = tuple(
        _boundary(
            symbol=symbol,
            anchor=START_AT,
            observed_at=START_AT + timedelta(milliseconds=10),
            price=Decimal("1"),
        )
        for symbol in FROZEN_T08_MARKET_SYMBOLS
        if symbol != "NAS100"
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="exact frozen market universe",
    ):
        build_t08_factor_market_snapshot_from_m5_boundaries(
            provider_key="fundednext-mt5",
            snapshots=snapshots,
        )
