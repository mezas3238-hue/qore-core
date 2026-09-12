from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_b01_h01_diagnostics_r3_8 import (
    _FEATURES,
    _cliffs_delta,
    _comparison,
    _median,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import AUTHORIZED_FOREX_MARKETS


def _diagnostic_record(*, symbol: str, value: str, winner: bool) -> dict[str, object]:
    pre_entry: dict[str, object] = {feature: value for feature in _FEATURES}
    return {
        "symbol": symbol,
        "signal_at": f"2026-01-{1 if winner else 2:02d}T09:00:00+00:00",
        "pre_entry": pre_entry,
        "outcome": {
            "exit_reason": "target" if winner else "stop",
            "return_rate": "0.01" if winner else "-0.01",
            "winner": winner,
            "stopped": not winner,
        },
    }


def test_h01_summary_primitives_are_deterministic() -> None:
    assert _median((Decimal("1"), Decimal("3"), Decimal("2"))) == Decimal("2")
    assert _median((Decimal("1"), Decimal("3"))) == Decimal("2")
    assert _cliffs_delta(
        (Decimal("1"), Decimal("2")),
        (Decimal("0"), Decimal("1")),
    ) == Decimal("0.75")


def test_h01_comparison_never_selects_threshold_or_authorizes_causal_rule() -> None:
    records: list[dict[str, object]] = []
    for symbol in AUTHORIZED_FOREX_MARKETS:
        records.append(_diagnostic_record(symbol=symbol, value="2", winner=True))
        records.append(_diagnostic_record(symbol=symbol, value="1", winner=False))

    comparison = _comparison(tuple(records))

    assert set(comparison) == set(_FEATURES)
    for payload in comparison.values():
        assert type(payload) is dict
        assert payload["winner_count"] == len(AUTHORIZED_FOREX_MARKETS)
        assert payload["stopped_count"] == len(AUTHORIZED_FOREX_MARKETS)
        assert payload["cliffs_delta_winner_vs_stopped"] == "1"
        assert payload["threshold_selected"] is False
        assert payload["causal_rule_authorized"] is False
        assert payload["per_market_cliffs_delta_winner_vs_stopped"] == {
            symbol: "1" for symbol in AUTHORIZED_FOREX_MARKETS
        }
