from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
    Phase22ProviderAccountLineageReceipt,
    build_numeric_execution_specs,
)


def _lineage() -> Phase22ProviderAccountLineageReceipt:
    return Phase22ProviderAccountLineageReceipt(
        provider_key="ctrader-demo",
        legacy_account_fingerprint_sha256=(
            "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
        ),
        phase22_account_fingerprint_sha256=(
            "17585ecd6f116a92d19919e46948f06c027d0cbf9f1cb8d97802f20055bad17b"
        ),
        same_account_proven=True,
    )


def _symbol(
    symbol: str,
    *,
    bid: str,
    ask: str,
    digits: int,
    lot_size_cents: int,
    min_volume_cents: int,
    provider_symbol: str | None = None,
) -> dict[str, object]:
    return {
        "qore_symbol": symbol,
        "provider_symbol": provider_symbol or symbol,
        "bid": bid,
        "ask": ask,
        "digits": digits,
        "lot_size_cents": lot_size_cents,
        "min_volume_cents": min_volume_cents,
        "max_volume_cents": lot_size_cents * 100,
        "step_volume_cents": min_volume_cents,
        "observed_at": datetime(2026, 10, 1, tzinfo=UTC).isoformat(),
        "expected_margin": [
            {
                "native_volume_cents": min_volume_cents,
                "buy_margin_usd": "1",
                "sell_margin_usd": "1",
            },
            {
                "native_volume_cents": lot_size_cents,
                "buy_margin_usd": "100",
                "sell_margin_usd": "101",
            },
        ],
    }


def _payloads() -> tuple[dict[str, object], dict[str, object]]:
    symbols = {
        "AUDJPY": _symbol(
            "AUDJPY",
            bid="109.829",
            ask="109.832",
            digits=3,
            lot_size_cents=10_000_000,
            min_volume_cents=100_000,
        ),
        "EURUSD": _symbol(
            "EURUSD",
            bid="1.13225",
            ask="1.13226",
            digits=5,
            lot_size_cents=10_000_000,
            min_volume_cents=100_000,
        ),
        "GBPJPY": _symbol(
            "GBPJPY",
            bid="209.569",
            ask="209.574",
            digits=3,
            lot_size_cents=10_000_000,
            min_volume_cents=100_000,
        ),
        "GBPUSD": _symbol(
            "GBPUSD",
            bid="1.32515",
            ask="1.32517",
            digits=5,
            lot_size_cents=10_000_000,
            min_volume_cents=100_000,
        ),
        "NAS100": _symbol(
            "NAS100",
            bid="30597.7",
            ask="30598.7",
            digits=2,
            lot_size_cents=100,
            min_volume_cents=10,
            provider_symbol="USTEC",
        ),
        "XAUUSD": _symbol(
            "XAUUSD",
            bid="4163.95",
            ask="4164.02",
            digits=2,
            lot_size_cents=10_000,
            min_volume_cents=100,
        ),
    }
    provider = {
        "provider_key": "ctrader-demo",
        "historical_exact_claimed": False,
        "holdout_outcomes_used": False,
        "symbols": symbols,
    }
    empirical = {
        "provider_key": "ctrader-demo",
        "historical_2017_exact_claimed": False,
        "holdout_outcomes_used": False,
        "execution_model_ready": True,
        "empirical_slippage_calibrated": True,
        "summaries": [
            {
                "qore_symbol": symbol,
                "mean_commission_usd": "0.03",
                "worst_adverse_slippage_bps": "0",
            }
            for symbol in (
                "AUDJPY",
                "EURUSD",
                "GBPJPY",
                "GBPUSD",
                "NAS100",
                "XAUUSD",
            )
        ],
    }
    return provider, empirical


def test_numeric_model_derives_jpy_conversion_from_same_provider_cross() -> None:
    provider, empirical = _payloads()

    specs = build_numeric_execution_specs(
        provider_terms_payload=provider,
        empirical_execution_payload=empirical,
        account_lineage=_lineage(),
    )
    by_symbol = {item.qore_symbol: item for item in specs}

    expected = (
        (Decimal("1.32515") + Decimal("1.32517")) / 2
    ) / (
        (Decimal("209.569") + Decimal("209.574")) / 2
    )
    assert by_symbol["AUDJPY"].quote_to_usd == expected
    assert by_symbol["GBPJPY"].quote_to_usd == expected
    assert by_symbol["EURUSD"].quote_to_usd == Decimal(1)
    assert by_symbol["NAS100"].provider_symbol == "USTEC"


def test_numeric_model_uses_provider_native_lot_fraction_and_margin() -> None:
    provider, empirical = _payloads()

    specs = build_numeric_execution_specs(
        provider_terms_payload=provider,
        empirical_execution_payload=empirical,
        account_lineage=_lineage(),
    )
    eurusd = next(item for item in specs if item.qore_symbol == "EURUSD")

    assert eurusd.contract_size_per_volume == Decimal("100000")
    assert eurusd.minimum_volume == Decimal("0.01")
    assert eurusd.volume_step == Decimal("0.01")
    assert eurusd.margin_per_volume_usd == Decimal("101")
    assert eurusd.commission_per_volume_usd == Decimal("3")


def test_numeric_model_rejects_unready_empirical_execution() -> None:
    provider, empirical = _payloads()
    empirical["execution_model_ready"] = False

    with pytest.raises(
        CiboCapitalManagementError,
        match="governance/readiness",
    ):
        build_numeric_execution_specs(
            provider_terms_payload=provider,
            empirical_execution_payload=empirical,
            account_lineage=_lineage(),
        )
