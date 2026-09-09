from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from qore.infrastructure.cibo.market_only_lab import run_market_only_lab


def _bar(opened: datetime, minutes: int, price: float) -> dict[str, str]:
    value = f"{price:.5f}"
    return {
        "period": "M15" if minutes == 15 else "H4",
        "opened_at": opened.isoformat(),
        "closed_at": (opened + timedelta(minutes=minutes)).isoformat(),
        "open": value,
        "high": f"{price + 0.0010:.5f}",
        "low": f"{price - 0.0010:.5f}",
        "close": f"{price + 0.0002:.5f}",
    }


def _evidence(path: Path, *, future_bump: float = 0.0) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    m15 = []
    for index in range(220):
        price = 1.1000 + index * 0.00005
        if index == 200:
            price += future_bump
        m15.append(_bar(start + timedelta(minutes=15 * index), 15, price))
    h4 = [
        _bar(start + timedelta(hours=4 * index), 240, 1.1000 + index * 0.0008)
        for index in range(30)
    ]
    payload = {
        "schema": "qore.ctrader_demo.lab_long_horizon_evidence.v1",
        "environment": "demo",
        "read_only": True,
        "account_fingerprint": "a" * 64,
        "symbol": {"symbol_name": "GBPUSD"},
        "checked_at": (start + timedelta(days=10)).isoformat(),
        "software_sha": "b" * 40,
        "periods": {"M15": m15, "H4": h4},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _first_record(result: dict[str, object]) -> dict[str, object]:
    results = cast(tuple[dict[str, object], ...], result["results"])
    records = cast(list[dict[str, object]], results[0]["records"])
    return records[0]


def _frozen_state(result: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], _first_record(result)["frozen_market_state"])


def test_market_only_lab_is_trader_blind_and_read_only(tmp_path: Path) -> None:
    path = tmp_path / "market.json"
    _evidence(path)
    result = run_market_only_lab((path,))
    assert result["research_only"] is True
    assert result["execution_authority"] is False
    assert result["trader_outputs_consumed"] is False
    assert result["trader_history_consumed"] is False
    assert result["oracle_visible_at_decision_time"] is False
    assert result["unknown_is_neutral"] is False
    first = _first_record(result)
    state = _frozen_state(result)
    assert len(cast(str, state["market_state_fingerprint"])) == 64
    evaluation = cast(dict[str, object], first["post_freeze_evaluation"])
    assert evaluation["oracle_visible_to_state"] is False


def test_future_change_cannot_change_already_frozen_first_state(tmp_path: Path) -> None:
    original = tmp_path / "original.json"
    changed = tmp_path / "changed.json"
    _evidence(original)
    _evidence(changed, future_bump=0.05)
    original_state = _frozen_state(run_market_only_lab((original,)))
    changed_state = _frozen_state(run_market_only_lab((changed,)))
    # Evidence-file digest is provenance, so compare causal state fields rather
    # than the whole-file provenance fingerprint.
    assert original_state["direction"] == changed_state["direction"]
    assert original_state["regime_hypothesis"] == changed_state["regime_hypothesis"]
    assert original_state["volatility"] == changed_state["volatility"]
    assert original_state["momentum_fraction"] == changed_state["momentum_fraction"]
    assert original_state["information_cutoff"] == changed_state["information_cutoff"]
