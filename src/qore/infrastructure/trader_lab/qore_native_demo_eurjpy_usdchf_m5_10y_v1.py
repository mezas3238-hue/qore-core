"""Read-only ten-year provider M5 acquisition for EURJPY/USDCHF on cTrader DEMO.

Reuses the corrected seven-day Atlas transport/quality writer without changing
the legacy 12-market corpus. No orders, signals, fills, or strategy outcomes.
"""
from __future__ import annotations

from qore.infrastructure.trader_lab import cibo_market_atlas_10y_m5_consumer_v1 as base
from qore.infrastructure.trader_lab import cibo_market_atlas_10y_windowed_runtime_v1 as windowed

IDENTITY = "QORE_NATIVE_CTRADER_DEMO_FOREX_M5_10Y_V1"
PARENT_IDENTITY = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"
SCHEMA = "qore.native.ctrader_demo_forex_m5_10y.v1"
SOURCE_SYMBOLS = {"EURJPY": "EURJPY", "USDCHF": "USDCHF"}
SYMBOLS = tuple(sorted(SOURCE_SYMBOLS))
EXPECTED_START = "2016-09-17T00:00:00+00:00"
EXPECTED_END_EXCLUSIVE = "2026-09-17T00:00:00+00:00"


def activate_research_only() -> None:
    """Activate isolated new identity in this process only; preserve old files."""
    if base.TARGET_START.isoformat() != EXPECTED_START:
        raise ValueError("source window start has changed")
    if base.TARGET_END_EXCLUSIVE.isoformat() != EXPECTED_END_EXCLUSIVE:
        raise ValueError("source window end has changed")
    if base.CHUNK_DAYS != 7 or base.PERIOD_M5 != 5:
        raise ValueError("source calendar cadence has changed")
    base.PROVIDER_SYMBOL_MAP = dict(SOURCE_SYMBOLS)
    base.TARGET_SYMBOLS = SYMBOLS
    base.IDENTITY = IDENTITY
    base.PARENT_IDENTITY = PARENT_IDENTITY
    base.SCHEMA = SCHEMA
    base.RAW_SCHEMA = SCHEMA + ".raw"
    base.QUALITY_SCHEMA = SCHEMA + ".quality"
    # Corrected cTrader window transport deliberately omits count.
    windowed.install_windowed_transport()


def main() -> None:
    activate_research_only()
    base.main()


if __name__ == "__main__":
    main()
