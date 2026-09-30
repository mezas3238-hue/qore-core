from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_feature_atlas import (
    V50CognitiveFeatureRow,
)
from qore.infrastructure.trader_lab.capitalizer_v50_prequential_cognitive_memory import (
    _features,
)


def _row(**overrides: object) -> V50CognitiveFeatureRow:
    values: dict[str, object] = {
        "identity": "QORE_CAPITALIZER_V50_COGNITIVE_FEATURE_ATLAS",
        "symbol": "EURUSD",
        "session": "LONDON",
        "operating_date": "2026-01-05",
        "entry_at": "2026-01-05T10:00:00+00:00",
        "exit_at": "2026-01-05T10:15:00+00:00",
        "state_family_id": "V50:test",
        "observation_tokens": (
            "SYMBOL=EURUSD",
            "SESSION=LONDON",
            "H1_FRESHNESS=FRESH",
            "SLOT=17",
        ),
        "structural_disposition": "PASS_TO_COMPETITION",
        "h1_freshness": "FRESH",
        "execution_freshness": "IMMEDIATE",
        "session_runway": "AMPLE",
        "stop_noise_state": "BALANCED",
        "stop_to_noise_ratio": "5",
        "destination_state": "BALANCED",
        "current_destination_room_r": "1.2",
        "target_candidate_count": 3,
        "target_has_one_r": True,
        "target_has_two_r": True,
        "execution_stop_available": True,
        "execution_vs_thesis_ratio": "0.4",
        "trigger_family": "FVG_RETRACE_CISD",
        "h1_basis": "CANDLE2_REVERSAL:BULLISH_FVG",
        "candidate_ordinal_in_session_day": 17,
        "realized_gross_r": "-1",
        "exit_reason": "STOP",
    }
    values.update(overrides)
    return V50CognitiveFeatureRow(**values)  # type: ignore[arg-type]


def test_prequential_features_replace_raw_slot_with_causal_buckets() -> None:
    features = _features(_row(), execution_slot=2)
    assert "SLOT=17" not in features
    assert "EXECUTION_SLOT=2" in features
    assert "RAW_CANDIDATE_ORDINAL=7_PLUS" in features
    assert "TARGET_HAS_2R=True" in features
    assert "EXEC_STOP_AVAILABLE=True" in features
