"""A genuinely neutral visual first look cannot expose model/cognitive output."""

from copy import deepcopy
import hashlib

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_gm2_visual_firstlook import (
    build_visual_firstlook,
)


def _case(case_id: str = "aud-001") -> dict[str, object]:
    return {
        "schema": "qore.vt08.crt_pure.gm2_real_blinded_casebook.v1",
        "case_id": case_id,
        "market": "AUDUSD",
        "decision_clock_utc": "2025-03-03T10:30:00+00:00",
        "parent_H4_direction_context": "BEARISH",
        "parent_H4_c3_opened_at_utc": "2025-03-03T10:00:00+00:00",
        "parent_H4_C1_ohlc": {
            "opened_at_utc": "2025-03-03T02:00:00+00:00",
            "open_relative": 102, "high_relative": 108,
            "low_relative": 99, "close_relative": 104,
        },
        "parent_H4_C2_ohlc": {
            "opened_at_utc": "2025-03-03T06:00:00+00:00",
            "open_relative": 104, "high_relative": 110,
            "low_relative": 100, "close_relative": 106,
        },
        "M15_observed_prefix_through_C2": [
            {
                "opened_at_utc": "2025-03-03T10:00:00+00:00",
                "open_relative": 106, "high_relative": 112,
                "low_relative": 105, "close_relative": 109,
            },
            {
                "opened_at_utc": "2025-03-03T10:15:00+00:00",
                "open_relative": 108, "high_relative": 109,
                "low_relative": 102, "close_relative": 103,
            },
        ],
        "reference_level_selection": "UNRESOLVED_BY_PRIMARY_SOURCE",
        "author_model1_equivalence": "NOT_ADJUDICATED",
        "is_execution_authorized": False,
        "future_C3_withheld_from_blind_file": True,
        "not_new_holdout": True,
    }


def test_neutral_visual_packet_has_real_history_but_no_engineered_answers() -> None:
    output, manifest = build_visual_firstlook([_case()])
    assert "<svg" in output and output.count("<svg") == 2
    assert "H4-1" in output and "H4-2" in output and "M15-2" in output
    assert "2025-03-03T10:30:00+00:00" in output
    assert ">112<" in output and ">99<" in output
    for forbidden in (
        "BEARISH", "BULLISH", "UNRESOLVED_BY_PRIMARY_SOURCE",
        "NOT_ADJUDICATED", "mechanical_confirmations_by_C2",
        "first_body_confirmation_known_at", "gm3_real_safety",
        "C3_M5_reveal_after_independent_review", "risk_per_trade",
        "position_lots", "future_C3_ohlc",
    ):
        assert forbidden not in output
    assert manifest["firstlook_html_sha256"] == hashlib.sha256(
        output.encode("utf-8")
    ).hexdigest()
    assert manifest["G_M2_passed"] is False
    assert manifest["G_M5_certificate_issued"] is False


def test_case_identifier_is_escaped_and_no_scripts_are_allowed() -> None:
    output, _ = build_visual_firstlook([_case("<script>alert(1)</script>")])
    assert "<script>alert(1)</script>" not in output
    assert "&lt;script&gt;" in output
    assert "<script" not in output
    assert 'default-src &#39;none&#39;' in output


def test_duplicate_or_empty_cases_fail() -> None:
    with pytest.raises(ValueError, match="no real blind"):
        build_visual_firstlook([])
    with pytest.raises(ValueError, match="empty or repeated"):
        build_visual_firstlook([_case(), _case()])


def test_any_future_output_or_financial_field_rejected_before_rendering() -> None:
    for forbidden in ("future_C3_ohlc", "trade_PnL", "position_lots", "source_selector"):
        data = deepcopy(_case())
        data[forbidden] = [{"opened_at_utc": "2025-03-03T10:30:00+00:00"}]
        with pytest.raises(ValueError, match="sealed future|unexpected blind"):
            build_visual_firstlook([data])


def test_noncausal_incomplete_m15_prefix_rejected() -> None:
    data = deepcopy(_case())
    data["M15_observed_prefix_through_C2"][1]["opened_at_utc"] = "2025-03-03T10:30:00+00:00"  # type: ignore[index]
    with pytest.raises(ValueError, match="future/partial"):
        build_visual_firstlook([data])


def test_review_order_is_preserved_without_geometry_ranking() -> None:
    a = _case("case-Z")
    b = _case("case-A")
    _, m = build_visual_firstlook([a, b])
    assert m["case_ids_in_review_order"] == ["case-Z", "case-A"]
    assert m["source_reference_authenticated"] is False
    assert m["reveal_or_cognitive_output_included"] is False
