from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import CANDIDATE_ID
from qore.infrastructure.cibo_phase22_vt08_fresh_engine import (
    Phase22M5ToM15Receipt,
    Phase22Vt08SymbolResult,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import AUTHORIZED_FOREX_MARKETS
from qore.infrastructure.cibo_phase22_vt08_fresh_runner import (
    build_vt08_phase22_fresh_payload,
    parse_sources,
)


def _result(symbol: str) -> Phase22Vt08SymbolResult:
    return Phase22Vt08SymbolResult(
        symbol=symbol,
        resampling=Phase22M5ToM15Receipt(
            symbol=symbol,
            source_m5_bars=100,
            emitted_m15_bars=30,
            incomplete_m15_bins=10,
            first_m15_opened_at="2015-10-19T00:00:00+00:00",
            last_m15_opened_at="2015-10-19T07:15:00+00:00",
        ),
        candidate_count=0,
        multiple_candidate_days=0,
        incomplete_exit_windows=0,
        abstain_reasons=(),
        opportunities=(),
    )


def test_payload_requires_exact_ordered_seven_market_surface() -> None:
    results = tuple(_result(symbol) for symbol in AUTHORIZED_FOREX_MARKETS)

    payload = build_vt08_phase22_fresh_payload(results)

    assert payload["candidate_id"] == CANDIDATE_ID
    assert payload["trader_id"] == "VT08_FOREX"
    assert payload["markets"] == list(AUTHORIZED_FOREX_MARKETS)
    assert len(payload["source_artifact_sha256s"]) == 7
    assert payload["fresh_outcomes_executed"] is True
    assert payload["methodology_changed"] is False
    assert payload["legacy_trader_sizing_used_for_cibo"] is False
    assert payload["broker_mutation_performed"] is False
    assert payload["productive_authority"] is False


def test_parse_sources_returns_canonical_order() -> None:
    reversed_values = [
        f"{symbol}=/tmp/{symbol.lower()}"
        for symbol in reversed(AUTHORIZED_FOREX_MARKETS)
    ]

    parsed = parse_sources(reversed_values)

    assert tuple(symbol for symbol, _path in parsed) == AUTHORIZED_FOREX_MARKETS
    assert all(isinstance(path, Path) for _symbol, path in parsed)


def test_parse_sources_rejects_incomplete_or_duplicate_surface() -> None:
    with pytest.raises(ValueError, match="exact seven-market"):
        parse_sources(
            [
                f"{symbol}=/tmp/{symbol.lower()}"
                for symbol in AUTHORIZED_FOREX_MARKETS[:-1]
            ]
        )

    symbol = AUTHORIZED_FOREX_MARKETS[0]
    values = [
        f"{item}=/tmp/{item.lower()}"
        for item in AUTHORIZED_FOREX_MARKETS
    ]
    values.append(f"{symbol}=/tmp/duplicate")
    with pytest.raises(ValueError, match="duplicate source"):
        parse_sources(values)
