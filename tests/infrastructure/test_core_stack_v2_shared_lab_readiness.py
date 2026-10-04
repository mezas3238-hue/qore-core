from qore.infrastructure.core_stack_v2.shared_lab_readiness import (
    LabLaneStatus,
    SharedLabReadinessInput,
    assess_shared_lab_readiness,
)


def status(data_ready: bool):
    return SharedLabReadinessInput(
        core_lane=LabLaneStatus("core", True, True, True, "core:evidence"),
        data_sensor_lane=LabLaneStatus(
            "data",
            data_ready,
            data_ready,
            data_ready,
            "data:evidence",
        ),
        tool_registry_fingerprinted=True,
        deterministic_replay_proven=True,
        capability_ledger_proven=True,
        influence_graph_proven=True,
        mutation_metamorphic_ablation_proven=True,
        uncertainty_contradiction_proven=True,
        counterfactual_truth_proven=True,
        resource_latency_proven=True,
        information_value_proven=True,
        degraded_mode_proven=True,
        seven_trader_harness_built=True,
        organism_harness_built=True,
        global_l10_pass=data_ready,
        authority_isolation_pass=True,
    )


def test_lab_cannot_be_available_while_data_lane_is_missing():
    result = assess_shared_lab_readiness(status(False))
    assert "DATA_SENSOR_LANE" in result.blocker_ids
    assert "GLOBAL_L10" in result.blocker_ids
    assert result.laboratory_available_for_shared_validation is False


def test_complete_lab_can_be_available_without_granting_shared_authority():
    result = assess_shared_lab_readiness(status(True))
    assert result.blocker_ids == ()
    assert result.laboratory_available_for_shared_validation is True
    assert result.shared_pre_certification_authorized is False
    assert result.protected_holdout_opening_authorized is False
    assert result.productive_authority is False
