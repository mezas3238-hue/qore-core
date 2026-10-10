"""P0 freeze: A2 MFE/MAE future observations NEVER reach cognition."""
from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from test_capitalizer_a1_source_sensor_independent_attestation_v1 import (
    _source,
)

from qore.infrastructure.trader_lab.capitalizer_a1_cisd_outcome_blind_method_boundary_v1 import (
    A1CISDPredecisionMethodWitness,
    sanitize_a2_forensic,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)

T = datetime(2026, 1, 5, 1, 4, tzinfo=UTC)
CANARY = "EX_POST_PLUS_60_MIN_WINNER_R_DO_NOT_LEAK_987654321"


def _raw(
    original: V49Opportunity, *, mode: str = "MATCHED",
) -> dict[str, Any]:
    instant = (
        (T-timedelta(minutes=2)).isoformat()
        if mode == "SENSOR_EARLIER_THAN_V49"
        else T.isoformat()
    )
    family = (
        "LIQUIDITY_SWEEP_CISD" if mode != "MATCHED"
        else original.m1_trigger_family
    )
    return {
        "source_opportunity_id": source_opportunity_id(original),
        "symbol": original.symbol,
        "session": original.session,
        "operating_date": original.operating_date,
        "original_family": original.m1_trigger_family,
        "sensor_family": family,
        "original_entry_at": original.m1_trigger_confirmed_at,
        "sensor_first_cisd_at": instant,
        "direction": original.h1_state_direction,
        "h1_basis": original.h1_state_basis,
        "m15_confirmed_at": original.m15_setup_confirmed_at,
        "classification": mode,
        "sensor_minus_original_minutes": (
            "-2.0" if mode == "SENSOR_EARLIER_THAN_V49" else "0.0"
        ),
        "sensor_event_not_necessarily_valid_under_v49_window": (
            mode != "MATCHED"
        ),
        "original_excur": [{"mfe_r_original_m15_stop": CANARY}],
        "sensor_excur": [{"mae_r_original_m15_stop": CANARY}],
        "input_was_a_paper_order": False,
        "outcome_used_to_admit_trade": False,
    }


@pytest.mark.parametrize(
    "mode", ("MATCHED", "SENSOR_EARLIER_THAN_V49", "SAME_TIME_DIFFERENT_FAMILY"),
)
def test_post_decision_excursions_never_forward_into_predecision_contract(
    mode: str,
) -> None:
    original = _source()
    witness = sanitize_a2_forensic(original=original, raw=_raw(original, mode=mode))
    serialized = json.dumps(asdict(witness))
    assert CANARY not in serialized
    assert "original_excur" not in serialized
    assert "sensor_excur" not in serialized
    assert "mfe" not in serialized
    assert "mae" not in serialized
    assert witness.source_opportunity_id == source_opportunity_id(original)
    assert witness.classification == mode
    assert not witness.contains_future_excursions
    assert not witness.author_eligible_methodology_adjudicated
    assert not witness.enters_master_frame_before_author_review
    assert not witness.changes_trade_admission


def test_any_source_identity_or_future_sensor_ambiguity_fails_closed() -> None:
    original = _source()
    for key, wrong in (
        ("symbol", "EURUSD"),
        ("operating_date", "2026-01-04"),
        ("source_opportunity_id", "FORGED"),
        ("h1_basis", "FUTURE_H1_BASIS"),
        ("original_family", "LIQUIDITY_SWEEP_CISD"),
    ):
        raw = _raw(original)
        raw[key] = wrong
        with pytest.raises(ValueError, match="SAME frozen V49"):
            sanitize_a2_forensic(original=original, raw=raw)
    raw = _raw(original)
    raw["sensor_first_cisd_at"] = (T+timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError, match="future"):
        sanitize_a2_forensic(original=original, raw=raw)


def test_malformed_classification_unreviewed_a2_fields_and_trading_authority_rejected() -> None:
    original = _source()
    raw = _raw(original, mode="SENSOR_EARLIER_THAN_V49")
    raw["classification"] = "MATCHED"
    with pytest.raises(ValueError, match="classification"):
        sanitize_a2_forensic(original=original, raw=raw)
    raw = _raw(original)
    raw["EX_POST_INTRADAY_PROFIT_FACTOR"] = "9.99"
    with pytest.raises(ValueError, match="schema changed"):
        sanitize_a2_forensic(original=original, raw=raw)
    raw = _raw(original)
    raw["outcome_used_to_admit_trade"] = True
    with pytest.raises(ValueError, match="paper-order admission"):
        sanitize_a2_forensic(original=original, raw=raw)
    a = sanitize_a2_forensic(original=original, raw=_raw(original))
    with pytest.raises(ValueError, match="no trade authority"):
        replace(a, enters_master_frame_before_author_review=True)
    with pytest.raises(ValueError, match="no trade authority"):
        replace(a, author_eligible_methodology_adjudicated=True)


def test_early_before_m15_and_false_opposite_direction_inference_blocked() -> None:
    original = _source()
    raw = _raw(original, mode="SENSOR_EARLIER_THAN_V49")
    raw["sensor_first_cisd_at"] = (T-timedelta(minutes=6)).isoformat()
    raw["sensor_minus_original_minutes"] = "-6.0"
    with pytest.raises(ValueError, match="pre-thesis"):
        sanitize_a2_forensic(original=original, raw=raw)
    witness = sanitize_a2_forensic(original=original, raw=_raw(original))
    with pytest.raises(ValueError, match="no trade authority"):
        replace(witness, opposite_direction_assessed=True)
    assert isinstance(witness, A1CISDPredecisionMethodWitness)
