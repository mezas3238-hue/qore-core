import hashlib

from qore.infrastructure.core_stack_v2.shared_lab import (
    CableRealityReceipt,
    CapabilityLabRecord,
    EfficiencyReceipt,
    EngineKind,
    InfluenceEdge,
    LabFault,
    LabIntegrityReceipt,
    NativeEngineReceipt,
    SharedLabLevel,
    TemporalDatumReceipt,
    assess_shared_lab,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _record(*, native=True, cable=True, changed=5, future=False):
    fp = _sha("output")
    return CapabilityLabRecord(
        capability_id="MC-18",
        engineering_green=True,
        required_levels=(
            SharedLabLevel.L0_STRUCTURAL_REALITY,
            SharedLabLevel.L3_COGNITIVE_REALITY,
            SharedLabLevel.L4_COGNITIVE_INTERACTION,
            SharedLabLevel.L5_CAUSAL_CONTRIBUTION,
            SharedLabLevel.L6_SCIENTIFIC_REALITY,
            SharedLabLevel.L7_ADVERSARIAL_LAB,
            SharedLabLevel.L9_FULL_ORGANISM_END_TO_END,
        ),
        passed_levels=(
            SharedLabLevel.L0_STRUCTURAL_REALITY,
            SharedLabLevel.L3_COGNITIVE_REALITY,
            SharedLabLevel.L4_COGNITIVE_INTERACTION,
            SharedLabLevel.L5_CAUSAL_CONTRIBUTION,
            SharedLabLevel.L6_SCIENTIFIC_REALITY,
            SharedLabLevel.L7_ADVERSARIAL_LAB,
            SharedLabLevel.L9_FULL_ORGANISM_END_TO_END,
        ),
        native_engine=NativeEngineReceipt(
            capability_id="MC-18",
            engine_id="counterfactual-world-engine",
            engine_kind=EngineKind.NATIVE if native else EngineKind.ADAPTER,
            real_input=True,
            native_engine_exists=native,
            native_engine_called=native,
            typed_output_emitted=True,
            adapter_only=not native,
            downstream_native_consumer="STI-2" if native else None,
        ),
        cables=(
            CableRealityReceipt(
                producer="MC-18",
                consumer="STI-2",
                producer_output_sha256=fp,
                consumer_input_parent_sha256=fp if cable else _sha("recreated"),
                observed=True,
                consumed=True,
                decision_changed=changed > 0,
            ),
        ),
        efficiency=EfficiencyReceipt(
            capability_id="MC-18",
            invocation_count=100,
            meaningful_output_count=80,
            downstream_consumed_count=80,
            downstream_changed_count=changed,
            no_change_count=20,
            abstention_count=5,
            contradiction_count=2,
            incremental_value=0.1 if changed else 0.0,
            incremental_risk_reduction=0.05 if changed else 0.0,
            incremental_information_gain=0.2 if changed else 0.0,
            latency_p99_ms=10,
            decision_deadline_ms=100,
        ),
        temporal_data=(
            TemporalDatumReceipt(
                datum_id="d1",
                observed_at_ns=1,
                available_at_ns=5 if future else 2,
                decision_at_ns=3,
                consumed_at_ns=6 if future else 4,
            ),
        ),
        mutation_pass=True,
        metamorphic_pass=True,
        ablation_pass=True,
    )


def test_green_adapter_is_not_native_engine_proof():
    record = _record(native=False)
    assert record.engineering_green is True
    assert record.native_engine.passed is False
    assert record.phase_proven is False


def test_cable_requires_exact_parent_fingerprint():
    record = _record(cable=False)
    assert record.cables[0].consumed is True
    assert record.cables[0].lineage_exact is False
    assert record.phase_proven is False


def test_invoked_but_zero_influence_is_not_proven():
    record = _record(changed=0)
    assert record.efficiency.cognitively_live is False
    assert record.phase_proven is False


def test_future_information_fails_leakage_firewall():
    record = _record(future=True)
    assert record.leakage_free is False
    assert record.phase_proven is False


def test_l10_requires_detection_of_every_injected_fault():
    receipt = LabIntegrityReceipt(
        injected_faults=(LabFault.DEAD_NATIVE_ENGINE, LabFault.FUTURE_LEAKAGE),
        detected_faults=(LabFault.DEAD_NATIVE_ENGINE,),
    )
    assert receipt.passed is False
    assert receipt.missing_detections == (LabFault.FUTURE_LEAKAGE,)


def test_full_lab_assessment_still_grants_no_certification_authority():
    record = _record()
    edge = InfluenceEdge(
        producer="MC-18",
        consumer="STI-2",
        real=True,
        tested=True,
        observed=True,
        consumed=True,
        value_proven=True,
        fingerprint_match=True,
    )
    l10 = LabIntegrityReceipt(
        injected_faults=tuple(LabFault),
        detected_faults=tuple(LabFault),
    )
    result = assess_shared_lab((record,), (edge,), l10)
    assert record.phase_proven is True
    assert result.all_required_capabilities_proven is True
    assert result.pre_certification_authorized is False
    assert result.protected_holdout_opening_authorized is False
    assert result.productive_authority is False
