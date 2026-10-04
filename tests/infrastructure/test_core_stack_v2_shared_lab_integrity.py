import hashlib

from qore.infrastructure.core_stack_v2.shared_lab import (
    CableRealityReceipt,
    CapabilityLabRecord,
    EfficiencyReceipt,
    EngineKind,
    LabFault,
    NativeEngineReceipt,
    SharedLabLevel,
    TemporalDatumReceipt,
)
from qore.infrastructure.core_stack_v2.shared_lab_integrity import (
    FaultScenario,
    run_l10_core_integrity,
)


def _record(*, native=True, changed=5, future=False):
    fp = hashlib.sha256(b"x").hexdigest()
    return CapabilityLabRecord(
        capability_id="MC18",
        engineering_green=True,
        required_levels=(SharedLabLevel.L0_STRUCTURAL_REALITY,),
        passed_levels=(SharedLabLevel.L0_STRUCTURAL_REALITY,),
        native_engine=NativeEngineReceipt(
            capability_id="MC18",
            engine_id="mc18",
            engine_kind=EngineKind.NATIVE if native else EngineKind.ADAPTER,
            real_input=True,
            native_engine_exists=native,
            native_engine_called=native,
            typed_output_emitted=True,
            adapter_only=not native,
            downstream_native_consumer="STI2" if native else None,
        ),
        cables=(CableRealityReceipt("MC18", "STI2", fp, fp, True, True, changed > 0),),
        efficiency=EfficiencyReceipt("MC18", 10, 8, 8, changed, 2, 0, 0, 0.1 if changed else 0.0, 0.0, 0.1 if changed else 0.0, 10, 100),
        temporal_data=(TemporalDatumReceipt("d", 1, 5 if future else 2, 3, 6 if future else 4),),
        mutation_pass=True,
        metamorphic_pass=True,
        ablation_pass=True,
    )


def test_l10_detects_core_failures():
    scenarios = (
        FaultScenario(LabFault.DEAD_NATIVE_ENGINE, record=_record(native=False)),
        FaultScenario(LabFault.ADAPTER_SUBSTITUTED_FOR_ENGINE, record=_record(native=False)),
        FaultScenario(LabFault.FUTURE_LEAKAGE, record=_record(future=True)),
        FaultScenario(LabFault.IGNORED_COGNITION, record=_record(changed=0)),
        FaultScenario(LabFault.DUPLICATED_OUTPUT, duplicate_output_count=2),
        FaultScenario(LabFault.FAKE_PASS, record=_record(native=False), claimed_pass=True),
    )
    receipt = run_l10_core_integrity(scenarios)
    assert receipt.passed is True


def test_l10_fails_when_detector_misses_fault():
    receipt = run_l10_core_integrity((FaultScenario(LabFault.STALE_SENSOR),))
    assert receipt.passed is False
    assert receipt.missing_detections == (LabFault.STALE_SENSOR,)
