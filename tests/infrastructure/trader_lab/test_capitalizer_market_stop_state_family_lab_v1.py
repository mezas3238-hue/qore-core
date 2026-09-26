import json
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_market_stop_state_family_lab_v1 import (
    IDENTITY,
    build_market_report,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_state_family_key_is_pretrade_only_and_buffer_remains_unfrozen(
    tmp_path: Path,
) -> None:
    report = {
        "identity": "QORE_CAPITALIZER_M1_LOSS_CAUSAL_FORENSICS_V1",
        "symbol": "NAS100",
        "session": "NEW_YORK",
        "source_trade_count": 2,
    }
    (
        tmp_path / "capitalizer-nas100-m1-loss-causal-forensics-v1.json"
    ).write_text(json.dumps(report), encoding="utf-8")

    common = {
        "symbol": "NAS100",
        "session": "NEW_YORK",
        "side": "LONG",
        "source_event_labels": ["HIGH_ACCEPTANCE"],
        "entry_at": "2024-06-03T19:03:00+00:00",
        "order_block_candle_count": 1,
        "retest_delay_minutes": 0,
        "setup_age_minutes": 12,
        "planned_reward_r": "2.0",
        "fvg_width_r": "0.1",
        "order_block_width_r": "0.2",
        "distance_ob_to_mss_r": "0.4",
        "entry_adverse_excursion_upper_bound_r": "0.05",
        "outcome_used_for_selection": False,
    }
    rows = [
        {
            **common,
            "exit_reason": "STOP",
            "realized_gross_r": "-1",
            "target_reached_after_stop_same_session": True,
            "extra_stop_r_needed_for_same_session_target_recovery": "0.75",
        },
        {
            **common,
            "exit_reason": "TARGET",
            "realized_gross_r": "2",
            "target_reached_after_stop_same_session": False,
            "extra_stop_r_needed_for_same_session_target_recovery": None,
        },
    ]
    _write_jsonl(
        tmp_path
        / "capitalizer-nas100-m1-loss-causal-forensics-v1-ledger.jsonl",
        rows,
    )

    result = build_market_report(tmp_path)
    assert result.identity == IDENTITY
    assert result.family_count == 1
    assert result.family_key_uses_outcome is False
    assert result.buffer_candidate_frozen is False
    assert result.rule_promotion_allowed is False
    family = result.families[0]
    assert family.trades == 2
    assert family.stops == 1
    assert family.target_recovered_after_stop == 1
    assert family.target_recovery_after_stop_rate == "1"
    assert family.median_extra_stop_r_recovered == "0.75"
    assert family.buffer_candidate_frozen is False
