import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_m1_loss_causal_forensics_v1 import (
    IDENTITY,
    _hourly_stop_profile,
    build_market_forensics,
)


def _relative(value: float) -> int:
    return int(round(value * 100_000))


def _m1_row(opened_at: datetime, *, o: float, h: float, low: float, c: float) -> dict[str, object]:
    return {
        "canonical_symbol": "NAS100",
        "close_relative": _relative(c),
        "digits": 2,
        "high_relative": _relative(h),
        "identity": "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1",
        "low_relative": _relative(low),
        "open_relative": _relative(o),
        "opened_at": opened_at.isoformat(),
        "schema": "qore.capitalizer.cibo.raw_m1.v1",
        "utc_timestamp_in_minutes": int(opened_at.timestamp()) // 60,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )



def test_ny_after_14_profile_separates_entry_time_from_stop_exit_time() -> None:
    entry = datetime(2024, 6, 3, 18, 5, tzinfo=UTC)  # 14:05 New York
    exit_at = datetime(2024, 6, 3, 19, 10, tzinfo=UTC)  # 15:10 New York
    rows = [
        {
            "session": "NEW_YORK",
            "entry_at": entry.isoformat(),
            "exit_at": exit_at.isoformat(),
            "exit_reason": "STOP",
        }
    ]

    profile = _hourly_stop_profile(rows)
    after_14 = {
        item["label"]: item
        for item in profile["hypothesis_windows"]
    }["NEW_YORK_AFTER_14"]

    assert after_14["entries"] == 1
    assert after_14["entries_that_stopped"] == 1
    assert after_14["entry_stop_rate"] == "1"
    assert after_14["stop_exits"] == 1
    assert profile["spread_causality_proven"] is False


def test_consumed_stop_recovery_is_forensic_not_rule_promotion(tmp_path: Path) -> None:
    replay = tmp_path / "replay"
    higher = tmp_path / "higher"
    m1 = tmp_path / "m1"
    replay.mkdir()
    higher.mkdir()

    signal = datetime(2024, 6, 3, 19, 0, tzinfo=UTC)
    entry = signal + timedelta(minutes=3)
    stop_exit = signal + timedelta(minutes=5)

    summary = {
        "identity": "QORE_CAPITALIZER_NATIVE_M1_ENTRY_REPLAY_V1",
        "symbol": "NAS100",
        "session": "NEW_YORK",
        "m1_entries": 1,
        "metrics": {
            "trades": 1,
            "profit_factor": "0",
            "max_drawdown_r": "1",
            "max_losing_streak": 1,
        },
        "entry_timeframe": "M1_NATIVE",
        "methodology_changed": False,
        "m1_mss_required": True,
        "m1_fvg_required": True,
        "m1_order_block_required": True,
        "outcome_aware_selection": False,
    }
    (replay / "capitalizer-nas100-native-m1-entry-replay-v1.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )

    trade = {
        "symbol": "NAS100",
        "session": "NEW_YORK",
        "side": "LONG",
        "higher_setup_signal_at": signal.isoformat(),
        "entry_at": entry.isoformat(),
        "exit_at": stop_exit.isoformat(),
        "entry_price": "100.00",
        "stop_price": "99.00",
        "target_price": "102.00",
        "planned_reward_r": "2",
        "realized_gross_r": "-1",
        "exit_reason": "STOP",
        "m1_bars_held": 2,
        "m1_mss_level": "100.20",
        "m1_fvg_low": "99.80",
        "m1_fvg_high": "100.10",
        "m1_order_block_low": "99.40",
        "m1_order_block_high": "100.05",
        "m1_displacement_at": (signal + timedelta(minutes=2)).isoformat(),
        "m1_fvg_confirmed_at": (signal + timedelta(minutes=3)).isoformat(),
        "same_minute_stop_target_ambiguity": False,
        "outcome_used_for_selection": False,
    }
    _write_jsonl(
        replay / "capitalizer-nas100-native-m1-entry-replay-v1-trades.jsonl",
        [trade],
    )

    source = {
        "symbol": "NAS100",
        "signal_at": signal.isoformat(),
        "event_labels": ["HIGH_ACCEPTANCE"],
        "source_strategy_status": "ELIGIBLE",
        "entry_probe": "PRESENT",
        "stop_probe": "PRESENT",
        "target_probe": "PRESENT",
        "outcome_used_for_selection": False,
    }
    _write_jsonl(
        higher / "capitalizer-nas100-three-session-replay-cell-v1-trades.jsonl",
        [source],
    )

    rows = [
        _m1_row(signal, o=100.00, h=100.05, low=99.40, c=99.70),
        _m1_row(signal + timedelta(minutes=1), o=99.70, h=100.60, low=99.65, c=100.50),
        _m1_row(signal + timedelta(minutes=2), o=100.50, h=100.80, low=100.10, c=100.60),
        _m1_row(signal + timedelta(minutes=3), o=100.00, h=100.40, low=99.80, c=100.20),
        _m1_row(signal + timedelta(minutes=4), o=100.20, h=100.30, low=98.90, c=99.10),
        _m1_row(signal + timedelta(minutes=5), o=99.10, h=101.00, low=98.80, c=100.80),
        _m1_row(signal + timedelta(minutes=6), o=100.80, h=102.20, low=100.70, c=102.00),
    ]
    _write_jsonl(m1 / "RAW_M1_LEDGER" / "2024.jsonl", rows)

    report, enriched = build_market_forensics(replay, m1, higher)

    assert report["identity"] == IDENTITY
    assert report["entry_forensics_complete"] is True
    assert report["ob_reconstruction_match_count"] == 1
    assert report["loss_classification_counts"] == [("PREMATURE_STOP_EVIDENCE", 1)]
    assert report["stop_intelligence"]["target_recovered_after_stop_same_session"] == 1
    assert report["stop_intelligence"]["target_recovery_rate"] == "1"
    assert report["evidence_status"] == "CONSUMED_FORENSIC_EVIDENCE"
    assert report["holdout_fresh_after_forensics"] is False
    assert report["methodology_changed"] is False
    assert report["rule_promotion_allowed"] is False
    assert report["economic_candidate"] is False
    assert report["trader_certified"] is False
    time_profile = report["ny_time_stop_profile"]
    assert time_profile["timezone"] == "America/New_York"
    assert time_profile["historical_spread_series_present"] is False
    assert time_profile["spread_causality_proven"] is False
    after_14 = {
        item["label"]: item
        for item in time_profile["hypothesis_windows"]
    }["NEW_YORK_AFTER_14"]
    assert after_14["entries"] == 1
    assert after_14["entries_that_stopped"] == 1
    assert after_14["entry_stop_rate"] == "1"
    assert after_14["stop_exits"] == 1
    assert enriched[0]["loss_classification"] == "PREMATURE_STOP_EVIDENCE"
    assert enriched[0]["target_reached_after_stop_same_session"] is True
