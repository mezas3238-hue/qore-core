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
    reconstruct_t08_factor_returns,
)

START_AT = datetime(2026, 9, 28, 12, tzinfo=UTC)
END_AT = START_AT + timedelta(minutes=5)


def _mark(
    *,
    symbol: str,
    mid: Decimal,
    observed_at: datetime,
    suffix: str,
) -> T08MarketMark:
    return T08MarketMark(
        qore_symbol=symbol,
        bid=mid,
        ask=mid,
        observed_at=observed_at,
        evidence_ref=f"provider:{suffix}:{symbol}",
    )


def _snapshot(
    *,
    snapshot_id: str,
    observed_at: datetime,
    prices: dict[str, Decimal],
    basis: T08MarketCollectionBasis = (
        T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE
    ),
) -> T08FactorMarketSnapshot:
    return T08FactorMarketSnapshot(
        snapshot_id=snapshot_id,
        provider_key="ctrader-demo",
        observed_at=observed_at,
        collection_basis=basis,
        marks=tuple(
            _mark(
                symbol=symbol,
                mid=prices[symbol],
                observed_at=observed_at,
                suffix=snapshot_id,
            )
            for symbol in sorted(prices)
        ),
    )


def test_reconstructs_cross_fx_factors_exactly_with_usd_numeraire() -> None:
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
            observed_at=START_AT,
            prices=start_prices,
        ),
        end=_snapshot(
            snapshot_id="s1",
            observed_at=END_AT,
            prices=end_prices,
        ),
    )

    for factor_id, gross in factor_gross.items():
        assert observation.return_for(factor_id) == gross - Decimal(1)
    assert observation.return_for("USD") == Decimal(0)
    assert len(observation.source_evidence_refs) == 12


def test_candidate_only_market_evidence_is_rejected_for_t08_returns() -> None:
    prices = {
        "GBPUSD": Decimal("1.25"),
    }
    start = _snapshot(
        snapshot_id="candidate-s0",
        observed_at=START_AT,
        prices=prices,
        basis=T08MarketCollectionBasis.CANDIDATE_ONLY,
    )
    end = _snapshot(
        snapshot_id="candidate-s1",
        observed_at=END_AT,
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
            observed_at=START_AT,
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
        observed_at=START_AT,
        prices=prices,
    )
    end = T08FactorMarketSnapshot(
        snapshot_id="s1",
        provider_key="other-provider",
        observed_at=END_AT,
        collection_basis=T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE,
        marks=tuple(
            _mark(
                symbol=symbol,
                mid=value,
                observed_at=END_AT,
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
