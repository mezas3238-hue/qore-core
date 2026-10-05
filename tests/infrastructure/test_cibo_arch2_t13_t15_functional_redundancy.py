from qore.infrastructure.cibo_arch2_t13_t15_functional_redundancy import (
    analyze_t13_t15_redundancy,
)


def _receipt(code: str, *, t13: bool) -> dict[str, object]:
    return {
        "tool_code": code,
        "native_engine_called": True,
        "outcome_used": False,
        "broker_mutation": False,
        "downstream_consumer": "phase20h-allocator-budget",
        "status": "APPLIED",
        "decision_changed": False,
        "economic_effect_observable": False,
        "input_payload": (
            {
                "drawdown_posture": "RECOVERY",
                "hard_risk_headroom_usd": "0",
                "margin_headroom_usd": "0",
            }
            if t13
            else {
                "regime_posture": "WATCH",
                "hard_risk_headroom_usd": "60",
                "margin_headroom_usd": "60",
                "known_options": [],
            }
        ),
        "output_payload": (
            {
                "reserve_stop_risk_usd": "0",
                "reserve_margin_usd": "0",
                "deployable_stop_risk_usd": "0",
                "deployable_margin_usd": "0",
            }
            if t13
            else {
                "reserve_stop_risk_usd": "0",
                "reserve_margin_usd": "0",
                "deployable_stop_risk_usd": "60",
                "deployable_margin_usd": "60",
            }
        ),
    }


def test_current_composition_can_close_t13_t15_as_no_measurable_effect() -> None:
    trace = {
        "group_id": "GROUP_X",
        "opportunities": [
            {
                "ce2i": {
                    "runtime_receipts": [
                        _receipt("T13", t13=True),
                        _receipt("T15", t13=False),
                    ]
                }
            }
        ],
    }

    result = analyze_t13_t15_redundancy(trace)

    assert result["functional_seam_closed"] is True
    assert result["T13"]["classification"] == "NO_MEASURABLE_EFFECT"
    assert result["T15"]["classification"] == "NO_MEASURABLE_EFFECT"
    assert result["economic_promotion_claimed"] is False
    assert result["outcome_aware_tuning"] is False


def test_t15_non_identity_output_keeps_seam_unproven() -> None:
    t15 = _receipt("T15", t13=False)
    t15["output_payload"]["deployable_stop_risk_usd"] = "59"
    trace = {
        "group_id": "GROUP_X",
        "opportunities": [
            {
                "ce2i": {
                    "runtime_receipts": [
                        _receipt("T13", t13=True),
                        t15,
                    ]
                }
            }
        ],
    }

    result = analyze_t13_t15_redundancy(trace)

    assert result["functional_seam_closed"] is False
    assert result["T15"]["classification"] == "UNPROVEN"
