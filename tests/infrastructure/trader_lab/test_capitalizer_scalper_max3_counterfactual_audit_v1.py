"""MAX3 counterfactual audit must not turn hindsight into admission rules."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.capitalizer_scalper_max3_counterfactual_audit_v1 import (
    IDENTITY,
    _summary,
    build_max3_counterfactual_report,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    IDENTITY as V49_REPORT_IDENTITY,
    V49EconomicTrade,
)


def _trade(symbol: str, ordinal: int, value: str) -> V49EconomicTrade:
    start = datetime(2026, 5, 4, 10, tzinfo=UTC) + timedelta(minutes=ordinal * 2)
    return V49EconomicTrade(
        symbol=symbol, session="LONDON", operating_date="2026-05-04",
        ordinal_candidate_at=start.isoformat(),
        direction="LONG",
        entry_at=start.isoformat(),
        exit_at=(start + timedelta(minutes=1)).isoformat(),
        entry_price="100", stop_price="99", target_price="102",
        planned_reward_r="2", realized_gross_r=value,
        exit_reason="TARGET" if float(value) > 0 else "STOP",
        m1_bars_held=1,
        trigger_family=(
            "LIQUIDITY_SWEEP_CISD" if ordinal % 2 else "FVG_RETRACE_CISD"
        ),
        h1_state_basis="BULLISH_FVG",
    )


def _make(root: Path) -> Path:
    result = root / "market-economics"
    for i, symbol in enumerate((
        "USDJPY", "AUDJPY", "AUDUSD", "GBPJPY", "EURUSD",
        "GBPUSD", "XAUUSD", "USDCAD", "NAS100",
    )):
        # Four candidates at an identical session/date, so global MAX3 should
        # keep the three earlier timestamps (not the ex-post profitable one).
        rows = [_trade(symbol, 4 * i + j, "-1" if j < 3 else "8")
                for j in range(4)]
        market = result / symbol
        market.mkdir(parents=True, exist_ok=True)
        prefix = f"capitalizer-{symbol.lower()}-v49-development-economics"
        (market / f"{prefix}-trades.jsonl").write_text(
            "".join(json.dumps(asdict(row)) + "\n" for row in rows),
            encoding="utf-8",
        )
        report = {
            "identity": V49_REPORT_IDENTITY, "symbol": symbol, "session": "LONDON",
            "candidate_opportunities": 4, "replayed_trades": 4,
            "rejected_no_session_m1": 0,
            "trader_certified": False, "live_authorized": False,
        }
        (market / f"{prefix}.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
    return result


def test_max3_selection_is_chronological_and_not_winner_chasing(
    tmp_path: Path,
) -> None:
    root = _make(tmp_path)
    result = build_max3_counterfactual_report(root)
    assert result["identity"] == IDENTITY
    assert result["source_simulated_economic_rows"] == 36
    assert result["max3_selected"] == 3
    assert result["max3_excluded_simulated_counterfactuals"] == 33
    assert result["selected"]["total_gross_r"] == "-3"
    assert result["excluded_counterfactual"]["gross_winning_r"] == "72"
    assert result["excluded_counterfactual"]["count"] == 33
    assert result["can_infer_ex_ante_policy_improvement"] is False
    assert result["no_outcome_aware_reranking"] is True


def test_stats_do_not_treat_zero_loss_pf_as_qualified_strategy() -> None:
    s = _summary((_trade("EURUSD", 1, "1"),))
    assert s["profit_factor"] is None
    assert s["mean_losing_r"] is None
    assert s["count"] == 1


def test_duplicate_replay_trade_is_not_silently_deduplicated(tmp_path: Path) -> None:
    root = _make(tmp_path)
    path = (
        root / "EURUSD" /
        "capitalizer-eurusd-v49-development-economics-trades.jsonl"
    )
    original = [json.loads(row) for row in path.read_text().splitlines()]
    original[1] = original[0].copy()
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in original),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate or ambiguous"):
        build_max3_counterfactual_report(root)


def test_source_report_count_mismatch_fails_closed(tmp_path: Path) -> None:
    root = _make(tmp_path)
    path = (
        root / "EURUSD" / "capitalizer-eurusd-v49-development-economics.json"
    )
    data = json.loads(path.read_text())
    data["replayed_trades"] = 90
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="census mismatch"):
        build_max3_counterfactual_report(root)


def test_missing_ninth_market_fails_closed(tmp_path: Path) -> None:
    root = _make(tmp_path)
    path = (
        root / "AUDJPY" /
        "capitalizer-audjpy-v49-development-economics-trades.jsonl"
    )
    path.unlink()
    with pytest.raises(ValueError, match="nine-market control"):
        build_max3_counterfactual_report(root)


def test_counterfactual_diagnostics_do_not_suppress_source_rows(
    tmp_path: Path,
) -> None:
    root = _make(tmp_path)
    baseline = build_max3_counterfactual_report(root)
    # Flip the outcome of an *excluded* candidate. MAX3 must be unaffected:
    # the selection depends solely on entry chronology, not on realized R.
    path = root / "NAS100" / "capitalizer-nas100-v49-development-economics-trades.jsonl"
    rows = [json.loads(row) for row in path.read_text().splitlines()]
    rows[3] = asdict(
        replace(V49EconomicTrade(**rows[3]), realized_gross_r="-8", exit_reason="STOP")
    )
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    changed = build_max3_counterfactual_report(root)
    assert changed["max3_selected"] == baseline["max3_selected"] == 3
    assert changed["selected"] == baseline["selected"]
    assert changed["excluded_counterfactual"] != baseline["excluded_counterfactual"]
