import hashlib

from qore.infrastructure.core_stack_v2.shared_lab import (
    CableRealityReceipt,
    CapabilityLabRecord,
    EfficiencyReceipt,
    EngineKind,
    NativeEngineReceipt,
    SharedLabLevel,
    TemporalDatumReceipt,
)
from qore.infrastructure.core_stack_v2.shared_lab_ledger import build_capability_ledger


def _record(capability_id: str, *, changed: int = 2) -> CapabilityLabRecord:
    fp = hashlib.sha256(capability_id.encode()).hexdigest()
    return CapabilityLabRecord(
        capability_id=capability_id,
        engineering_green=True,
        required_levels=(SharedLabLevel.L0_STRUCTURAL_REALITY,),
        passed_levels=(SharedLabLevel.L0_STRUCTURAL_REALITY,),
        native_engine=NativeEngineReceipt(
            capability_id=capability_id,
            engine_id=capability_id.lower(),
            engine_kind=EngineKind.NATIVE,
            real_input=True,
            native_engine_exists=True,
            native_engine_called=True,
            typed_output_emitted=True,
            downstream_native_consumer=f"{capability_id}-consumer",
        ),
        cables=(
            CableRealityReceipt(
                capability_id,
                f"{capability_id}-consumer",
                fp,
                fp,
                True,
                True,
                changed > 0,
            ),
        ),
        efficiency=EfficiencyReceipt(
            capability_id,
            10,
            8,
            8,
            changed,
            2,
            0,
            0,
            0.1 if changed else 0.0,
            0.0,
            0.1 if changed else 0.0,
            5,
            100,
        ),
        temporal_data=(TemporalDatumReceipt("d", 1, 2, 3, 4),),
        mutation_pass=True,
        metamorphic_pass=True,
        ablation_pass=True,
    )


def test_no_pooled_rescue_blocks_global_success():
    strong = _record("MC09", changed=2)
    weak = _record("MC18", changed=0)
    ledger = build_capability_ledger(
        (strong, weak),
        mandatory_ids=frozenset({"MC09", "MC18"}),
    )
    assert ledger.blocker_ids == ("MC18",)
    assert ledger.no_pooled_rescue_pass is False


def test_all_mandatory_capabilities_must_individually_pass():
    ledger = build_capability_ledger(
        (_record("MC09"), _record("MC18")),
        mandatory_ids=frozenset({"MC09", "MC18"}),
    )
    assert ledger.mandatory_proven_count == 2
    assert ledger.no_pooled_rescue_pass is True
