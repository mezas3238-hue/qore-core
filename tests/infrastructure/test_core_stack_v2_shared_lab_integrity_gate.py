from qore.infrastructure.core_stack_v2.shared_lab import LabFault, LabIntegrityReceipt
from qore.infrastructure.core_stack_v2.shared_lab_integrity_gate import assess_global_l10


def test_global_l10_refuses_partial_lane_coverage():
    core_faults = (
        LabFault.DEAD_NATIVE_ENGINE,
        LabFault.ADAPTER_SUBSTITUTED_FOR_ENGINE,
        LabFault.FAKE_CONSUMER,
        LabFault.FUTURE_LEAKAGE,
        LabFault.DUPLICATED_OUTPUT,
        LabFault.IGNORED_COGNITION,
        LabFault.FAKE_PASS,
    )
    core = LabIntegrityReceipt(core_faults, core_faults)
    result = assess_global_l10((core,))
    assert result.missing_injections
    assert result.l10_global_pass is False


def test_global_l10_passes_only_when_all_faults_detected_across_lanes():
    core_faults = (
        LabFault.DEAD_NATIVE_ENGINE,
        LabFault.ADAPTER_SUBSTITUTED_FOR_ENGINE,
        LabFault.FAKE_CONSUMER,
        LabFault.DUPLICATED_OUTPUT,
        LabFault.IGNORED_COGNITION,
        LabFault.FAKE_PASS,
    )
    data_faults = tuple(fault for fault in LabFault if fault not in core_faults)
    core = LabIntegrityReceipt(core_faults, core_faults)
    data = LabIntegrityReceipt(data_faults, data_faults)
    result = assess_global_l10((core, data))
    assert result.missing_injections == ()
    assert result.missing_detections == ()
    assert result.l10_global_pass is True
