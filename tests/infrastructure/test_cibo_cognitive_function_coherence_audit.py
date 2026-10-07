from scripts.cibo_cognitive_function_coherence_audit import audit


def _frontier_replay(*, frontier_cap: object, selected_multiplier: object, advisory: object = True) -> dict[str, object]:
    return {
        "schema": "qore.cibo.synthetic-replay.v1",
        "decision_receipts": [
            {
                "risk_decision": "NOT_REQUESTED",
                "cognitive_sensors": [],
                "function_sensors": [
                    {
                        "function_code": "MAX_FRONTIER",
                        "called": True,
                        "downstream_consumed": True,
                        "decision_gate_triggered": False,
                        "final_capital_binding": False,
                        "output_metrics": [
                            ["frontier_cap", frontier_cap],
                            ["selected_multiplier", selected_multiplier],
                            ["advisory_diagnostic", advisory],
                        ],
                    }
                ],
            }
        ],
    }


def test_uncapped_frontier_values_are_valid_and_above_recommendation_is_diagnostic() -> None:
    report = audit(
        _frontier_replay(frontier_cap=12, selected_multiplier=39)
    )

    assert report["p0_count"] == 0
    assert report["coherence_violations"].get(
        "max_frontier_malformed_output", 0
    ) == 0
    assert report["diagnostics"][
        "portfolio_above_max_frontier_recommendation"
    ] == 1


def test_negative_frontier_values_remain_malformed() -> None:
    report = audit(
        _frontier_replay(frontier_cap=-1, selected_multiplier=0)
    )

    assert report["p0_count"] == 1
    assert report["coherence_violations"][
        "max_frontier_malformed_output"
    ] == 1


def test_frontier_must_remain_explicitly_advisory() -> None:
    report = audit(
        _frontier_replay(
            frontier_cap=20,
            selected_multiplier=10,
            advisory=False,
        )
    )

    assert report["p0_count"] == 1
    assert report["coherence_violations"][
        "max_frontier_not_advisory"
    ] == 1
