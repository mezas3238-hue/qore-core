from decimal import Decimal

from qore.infrastructure.cibo_pre_risk_capture_sensor import (
    measure_pre_risk_opportunity_capture,
)


def _row(
    *,
    ev: str,
    context: str = "ALLOW",
    selected: bool = False,
    disposition: str = "PRESERVE_CAPACITY",
    posture: str = "RECOVERY",
) -> dict:
    return {
        "expectation": {
            "expected_net_value_usd": ev,
            "outcome_used": False,
        },
        "context_quality": {
            "disposition": context,
            "outcome_used": False,
        },
        "allocation": {
            "selected_by_cibo_policy": selected,
            "allocator_disposition": disposition,
            "allocator_regime_posture": posture,
        },
        "ce2i": {"runtime_receipts": []},
    }


def test_recovery_probe_sensor_measures_only_causal_allowed_surface() -> None:
    trace = {
        "opportunities": [
            _row(ev="4", selected=True, disposition="ALLOCATE", posture="STABLE"),
            _row(ev="3", selected=False, posture="RECOVERY"),
            _row(ev="2", selected=False, posture="DEFENSIVE"),
            _row(ev="9", context="ABSTAIN", posture="RECOVERY"),
            _row(ev="-5", selected=False, posture="RECOVERY"),
        ]
    }

    report = measure_pre_risk_opportunity_capture(trace)

    assert report.positive_context_allowed_count == 3
    assert report.positive_context_allowed_expected_value_usd == Decimal("9")
    assert report.selected_count == 1
    assert report.selected_expected_value_usd == Decimal("4")
    assert report.recovery_preserve_miss_count == 1
    assert report.recovery_preserve_miss_expected_value_usd == Decimal("3")
    assert report.baseline_count_efficiency == Decimal(1) / Decimal(3)
    assert report.recovery_probe_count_ceiling == Decimal(2) / Decimal(3)
    assert report.baseline_value_efficiency == Decimal(4) / Decimal(9)
    assert report.recovery_probe_value_ceiling == Decimal(7) / Decimal(9)
    assert report.outcome_used is False
    assert report.productive_authority is False


def test_sensor_can_recover_posture_from_ce2i_receipt_for_old_trace() -> None:
    row = _row(ev="2")
    row["allocation"].pop("allocator_regime_posture")
    row["ce2i"] = {
        "runtime_receipts": [
            {
                "engine_name": "select_ce2i_tools_for_regime",
                "output_payload": {"posture": "RECOVERY"},
            }
        ]
    }

    report = measure_pre_risk_opportunity_capture(
        {"opportunities": [row]}
    )

    assert report.recovery_preserve_miss_count == 1
    assert report.recovery_probe_count_ceiling == Decimal("1")


def test_sensor_never_upgrades_non_preserve_or_non_recovery_misses() -> None:
    trace = {
        "opportunities": [
            _row(
                ev="2",
                selected=False,
                disposition="NO_ELIGIBLE_ALLOCATION",
                posture="RECOVERY",
            ),
            _row(
                ev="3",
                selected=False,
                disposition="PRESERVE_CAPACITY",
                posture="DEFENSIVE",
            ),
        ]
    }

    report = measure_pre_risk_opportunity_capture(trace)

    assert report.positive_context_allowed_count == 2
    assert report.selected_count == 0
    assert report.recovery_preserve_miss_count == 0
    assert report.recovery_probe_count_ceiling == Decimal("0")
    assert report.recovery_probe_value_ceiling == Decimal("0")
