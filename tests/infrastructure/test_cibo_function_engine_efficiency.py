from decimal import Decimal

from qore.infrastructure.cibo_engine_efficiency_sensor import (
    CiboEngineEfficiencyClass,
)
from qore.infrastructure.cibo_function_engine_efficiency import (
    build_function_engine_efficiency_reports,
)


def test_unattributed_advisory_function_is_unidentified_not_useless() -> None:
    payload = {
        "functions": [
            {
                "function_code": "CF01",
                "expected_or_enabled_count": 100,
                "invocation_count": 100,
                "consumer_observed": True,
                "decision_change_observed": False,
                "economic_effect_observed": False,
                "direct_trace_evidence_count": 0,
            }
        ]
    }

    report = build_function_engine_efficiency_reports(payload)[0]

    assert report.engine_id == "CF01"
    assert report.classification is CiboEngineEfficiencyClass.UNIDENTIFIED


def test_destructive_ablation_marks_engine_destructive() -> None:
    payload = {
        "functions": [
            {
                "function_code": "T14",
                "expected_or_enabled_count": 100,
                "invocation_count": 100,
                "consumer_observed": True,
                "decision_change_observed": True,
                "economic_effect_observed": True,
                "direct_trace_evidence_count": 80,
            }
        ]
    }

    report = build_function_engine_efficiency_reports(
        payload,
        marginal_value_usd={"T14": Decimal("0")},
        available_value_usd={"T14": Decimal("10")},
        destructive_value_usd={"T14": Decimal("3")},
    )[0]

    assert report.classification is CiboEngineEfficiencyClass.DESTRUCTIVE
    assert report.causal_loss_usd == Decimal("13")
