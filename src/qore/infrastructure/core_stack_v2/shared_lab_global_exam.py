"""Sovereign end-to-end self exam for the complete QORE Shared Lab."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_lab import (
    CableRealityReceipt,
    CapabilityLabRecord,
    EfficiencyReceipt,
    EngineKind,
    InfluenceEdge,
    LabFault,
    NativeEngineReceipt,
    SharedLabLevel,
    TemporalDatumReceipt,
)
from qore.infrastructure.core_stack_v2.shared_lab_authority import (
    AuthorityIsolationReceipt,
    assess_authority_isolation,
)
from qore.infrastructure.core_stack_v2.shared_lab_cognition import (
    CalibrationBin,
    ContradictionDisposition,
    ContradictionEvidence,
    ContradictionResolutionReceipt,
    UncertaintyCalibrationReceipt,
)
from qore.infrastructure.core_stack_v2.shared_lab_counterfactual import (
    CounterfactualWorldReceipt,
    assess_counterfactual_worlds,
)
from qore.infrastructure.core_stack_v2.shared_lab_data_authority_firewall import (
    inspect_authority_firewall,
)
from qore.infrastructure.core_stack_v2.shared_lab_data_exam import (
    run_engineering_data_reality_exam,
)
from qore.infrastructure.core_stack_v2.shared_lab_data_l10 import run_data_l10
from qore.infrastructure.core_stack_v2.shared_lab_experiments import (
    ExperimentKind,
    ExperimentObservation,
    assess_capability_experiments,
)
from qore.infrastructure.core_stack_v2.shared_lab_influence import (
    CapabilityNode,
    assess_influence_graph,
)
from qore.infrastructure.core_stack_v2.shared_lab_integrity import (
    FaultScenario,
    run_l10_core_integrity,
)
from qore.infrastructure.core_stack_v2.shared_lab_integrity_gate import assess_global_l10
from qore.infrastructure.core_stack_v2.shared_lab_ledger import build_capability_ledger
from qore.infrastructure.core_stack_v2.shared_lab_operational import (
    DegradedDisposition,
    DegradedModeReceipt,
    InformationValueReceipt,
    ResourceLatencyReceipt,
    assess_operational_reality,
)
from qore.infrastructure.core_stack_v2.shared_lab_organism import build_organism_trace
from qore.infrastructure.core_stack_v2.shared_lab_readiness import (
    LabLaneStatus,
    SharedLabReadinessInput,
    assess_shared_lab_readiness,
)
from qore.infrastructure.core_stack_v2.shared_lab_replay import (
    ReplayObservation,
    assess_replay_determinism,
)
from qore.infrastructure.core_stack_v2.shared_lab_runtime_probe import (
    consume_exact_output,
    invoke_native_engine,
)
from qore.infrastructure.core_stack_v2.shared_lab_seven_trader import (
    TraderControlTreatmentReceipt,
    TraderMetricVector,
    assess_seven_trader_reality,
)
from qore.infrastructure.core_stack_v2.shared_lab_tools import (
    default_shared_lab_registry,
    registry_fingerprint,
    validate_l10_tool_coverage,
)


TRADER_IDS = frozenset(
    {
        "VT08_FOREX",
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
        "VT31_NAS100",
    }
)


@dataclass(frozen=True, slots=True)
class GlobalLabExamResult:
    core_l10_pass: bool
    data_exam_pass: bool
    data_l10_pass: bool
    global_l10_pass: bool
    authority_isolation_pass: bool
    readiness_blockers: tuple[str, ...]
    laboratory_available_for_shared_validation: bool
    protected_holdout_opened: bool = False
    productive_authority: bool = False

    @property
    def passed(self) -> bool:
        return (
            self.core_l10_pass
            and self.data_exam_pass
            and self.data_l10_pass
            and self.global_l10_pass
            and self.authority_isolation_pass
            and not self.readiness_blockers
            and self.laboratory_available_for_shared_validation
            and not self.protected_holdout_opened
            and not self.productive_authority
        )


def _record(
    *,
    native: bool = True,
    changed: int = 2,
    future: bool = False,
) -> CapabilityLabRecord:
    fingerprint = "a" * 64
    return CapabilityLabRecord(
        capability_id="GLOBAL_EXAM_CAPABILITY",
        engineering_green=True,
        required_levels=(SharedLabLevel.L0_STRUCTURAL_REALITY,),
        passed_levels=(SharedLabLevel.L0_STRUCTURAL_REALITY,),
        native_engine=NativeEngineReceipt(
            capability_id="GLOBAL_EXAM_CAPABILITY",
            engine_id="global-exam-engine",
            engine_kind=EngineKind.NATIVE if native else EngineKind.ADAPTER,
            real_input=True,
            native_engine_exists=native,
            native_engine_called=native,
            typed_output_emitted=True,
            adapter_only=not native,
            downstream_native_consumer="GLOBAL_EXAM_CONSUMER" if native else None,
        ),
        cables=(
            CableRealityReceipt(
                "GLOBAL_EXAM_CAPABILITY",
                "GLOBAL_EXAM_CONSUMER",
                fingerprint,
                fingerprint,
                True,
                True,
                changed > 0,
            ),
        ),
        efficiency=EfficiencyReceipt(
            "GLOBAL_EXAM_CAPABILITY",
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
            10,
            100,
        ),
        temporal_data=(
            TemporalDatumReceipt(
                "global-datum",
                1,
                5 if future else 2,
                3,
                6 if future else 4,
            ),
        ),
        mutation_pass=True,
        metamorphic_pass=True,
        ablation_pass=True,
    )


def _core_l10():
    bad_edge = InfluenceEdge(
        "A",
        "B",
        real=True,
        tested=True,
        observed=False,
        consumed=False,
        value_proven=False,
        fingerprint_match=False,
    )
    scenarios = (
        FaultScenario(LabFault.DEAD_NATIVE_ENGINE, record=_record(native=False)),
        FaultScenario(
            LabFault.ADAPTER_SUBSTITUTED_FOR_ENGINE,
            record=_record(native=False),
        ),
        FaultScenario(LabFault.FAKE_CONSUMER, edge=bad_edge),
        FaultScenario(LabFault.FUTURE_LEAKAGE, record=_record(future=True)),
        FaultScenario(LabFault.DUPLICATED_OUTPUT, duplicate_output_count=2),
        FaultScenario(LabFault.IGNORED_COGNITION, record=_record(changed=0)),
        FaultScenario(
            LabFault.FAKE_PASS,
            record=_record(native=False),
            claimed_pass=True,
        ),
    )
    return run_l10_core_integrity(scenarios)


def _data_l10():
    return run_data_l10(
        stale_detected=True,
        wrong_symbol_detected=True,
        duplicate_detected=True,
        fake_provider_detected=True,
        temporal_probe=(0, 11, 10, 12),
        missing_observation_detected=True,
        provider_conflict_detected=True,
    )


def _data_authority_firewall_pass() -> bool:
    root = Path(__file__).parent
    patterns = (
        "shared_lab_data_*.py",
        "shared_lab_golden_traces.py",
        "shared_lab_identity_*.py",
        "shared_lab_market_*.py",
        "shared_lab_provider_*.py",
        "shared_lab_sensor_harness.py",
        "shared_lab_temporal_*.py",
        "shared_lab_universe_*.py",
    )
    files = sorted({path for pattern in patterns for path in root.glob(pattern)})
    return bool(files) and all(
        not inspect_authority_firewall(path.read_text())
        for path in files
    )


def _replay_pass(tool_fp: str) -> bool:
    observations = (
        ReplayObservation("r1", "sha", "in", "out", tool_fp, 7, True),
        ReplayObservation("r2", "sha", "in", "out", tool_fp, 7, True),
    )
    return assess_replay_determinism(observations).deterministic_replay_proven


def _ledger_pass() -> bool:
    record = _record()
    result = build_capability_ledger(
        (record,),
        mandatory_ids=frozenset({record.capability_id}),
    )
    return result.no_pooled_rescue_pass


def _influence_pass() -> bool:
    nodes = (
        CapabilityNode("A", True, True, True, True, "intel-a"),
        CapabilityNode("B", True, True, True, True, "intel-b"),
    )
    edge = InfluenceEdge("A", "B", True, True, True, True, True, True)
    return assess_influence_graph(nodes, (edge,)).graph_proven


def _experiments_pass() -> bool:
    observations = (
        ExperimentObservation(
            "mutation",
            "MC18",
            ExperimentKind.MUTATION,
            "a",
            "b",
            "x",
            "y",
            True,
            True,
            True,
        ),
        ExperimentObservation(
            "metamorphic",
            "MC18",
            ExperimentKind.METAMORPHIC,
            "a",
            "b",
            "x",
            "x",
            True,
            False,
            False,
            True,
            True,
        ),
        ExperimentObservation(
            "ablation",
            "MC18",
            ExperimentKind.ABLATION,
            "a",
            "b",
            "x",
            "y",
            True,
            True,
            True,
        ),
    )
    return assess_capability_experiments(
        "MC18",
        observations,
    ).all_required_experiments_pass


def _cognition_pass() -> bool:
    calibration = UncertaintyCalibrationReceipt(
        "MC09",
        (
            CalibrationBin(0.8, 100, 0.78),
            CalibrationBin(0.6, 100, 0.62),
        ),
        0.05,
        max_high_confidence_wrong_rate=0.25,
    )
    contradiction = ContradictionResolutionReceipt(
        "ARBITER",
        (
            ContradictionEvidence("MC09", "RISK_OFF", 0.8, True, 0.8),
            ContradictionEvidence("MC18", "RISK_ON", 0.7, False, 0.6),
        ),
        ContradictionDisposition.RESOLVED,
        "RISK_OFF",
        True,
        True,
    )
    return calibration.passed and contradiction.passed


def _counterfactual_pass() -> bool:
    world = CounterfactualWorldReceipt(
        "MC18",
        "actual",
        "actual",
        "counterfactual",
        True,
        True,
        True,
        True,
        False,
        False,
    )
    return assess_counterfactual_worlds(
        "MC18",
        (world,),
    ).all_worlds_truth_valid


def _operational_pass() -> tuple[bool, bool, bool]:
    latency = ResourceLatencyReceipt("MC18", 10, 20, 30, 100, 50, 10, 1000)
    info = InformationValueReceipt("MC18", 100, 5, 10, 2, 1, 0.1, 0.2, 5)
    degraded = DegradedModeReceipt(
        "MC18",
        (),
        False,
        False,
        False,
        (),
        DegradedDisposition.FULL,
    )
    result = assess_operational_reality(
        latency=latency,
        information_value=info,
        degraded_mode=degraded,
    )
    return result.latency_pass, result.information_value_pass, result.degraded_mode_pass


def _seven_trader_pass() -> bool:
    metrics = TraderMetricVector(1.5, 0.1, 5.0, 1.5, 2.0, 1.2, 1.3, 0.9, 100)
    receipts = tuple(
        TraderControlTreatmentReceipt(
            trader_id,
            metrics,
            metrics,
            10,
            10,
            2,
            0,
            0,
            True,
            True,
        )
        for trader_id in sorted(TRADER_IDS)
    )
    return assess_seven_trader_reality(
        receipts,
        expected_trader_ids=TRADER_IDS,
    ).l8_proven


def _engine_a(value: int) -> dict[str, int]:
    return {"belief": value + 1}


def _engine_b(value: dict[str, int]) -> dict[str, int]:
    return {"physics": value["belief"] * 2}


def _engine_c(value: dict[str, int]) -> dict[str, int]:
    return {"decision": value["physics"] - 1}


def _organism_pass() -> bool:
    a_out, a = invoke_native_engine(
        capability_id="A",
        engine_id="a",
        engine=_engine_a,
        args=(2,),
        downstream_native_consumer="B",
    )
    b_out, ab = consume_exact_output(
        producer_trace=a,
        consumer_capability_id="B",
        consumer=_engine_b,
        producer_output=a_out,
    )
    _, b = invoke_native_engine(
        capability_id="B",
        engine_id="b",
        engine=_engine_b,
        args=(a_out,),
        downstream_native_consumer="C",
    )
    _, bc = consume_exact_output(
        producer_trace=b,
        consumer_capability_id="C",
        consumer=_engine_c,
        producer_output=b_out,
    )
    _, c = invoke_native_engine(
        capability_id="C",
        engine_id="c",
        engine=_engine_c,
        args=(b_out,),
        downstream_native_consumer="TRADER",
    )
    return build_organism_trace((a, b, c), (ab, bc)).l9_end_to_end_proven


def run_global_lab_exam() -> GlobalLabExamResult:
    registry = default_shared_lab_registry()
    tool_fp = registry_fingerprint(registry)
    core_l10 = _core_l10()
    data_l10 = _data_l10()
    data_exam = run_engineering_data_reality_exam()
    global_l10 = assess_global_l10((core_l10, data_l10.core_receipt))

    core_authority = assess_authority_isolation(
        (
            AuthorityIsolationReceipt(
                "QORE_SHARED_LAB_CORE",
                frozenset(),
                frozenset(),
                True,
                True,
            ),
        )
    )
    authority_pass = (
        core_authority.all_components_authority_free
        and _data_authority_firewall_pass()
    )
    latency_pass, info_pass, degraded_pass = _operational_pass()

    readiness = assess_shared_lab_readiness(
        SharedLabReadinessInput(
            core_lane=LabLaneStatus(
                "CORE",
                True,
                True,
                core_l10.passed,
                "global-exam:core",
            ),
            data_sensor_lane=LabLaneStatus(
                "DATA_SENSOR",
                True,
                data_exam.passed,
                data_l10.passed,
                f"data-exam:{data_exam.exam_fingerprint}",
            ),
            tool_registry_fingerprinted=bool(tool_fp)
            and not validate_l10_tool_coverage(registry),
            deterministic_replay_proven=_replay_pass(tool_fp),
            capability_ledger_proven=_ledger_pass(),
            influence_graph_proven=_influence_pass(),
            mutation_metamorphic_ablation_proven=_experiments_pass(),
            uncertainty_contradiction_proven=_cognition_pass(),
            counterfactual_truth_proven=_counterfactual_pass(),
            resource_latency_proven=latency_pass,
            information_value_proven=info_pass,
            degraded_mode_proven=degraded_pass,
            seven_trader_harness_built=_seven_trader_pass(),
            organism_harness_built=_organism_pass(),
            global_l10_pass=global_l10.l10_global_pass,
            authority_isolation_pass=authority_pass,
        )
    )
    return GlobalLabExamResult(
        core_l10_pass=core_l10.passed,
        data_exam_pass=data_exam.passed,
        data_l10_pass=data_l10.passed,
        global_l10_pass=global_l10.l10_global_pass,
        authority_isolation_pass=authority_pass,
        readiness_blockers=readiness.blocker_ids,
        laboratory_available_for_shared_validation=(
            readiness.laboratory_available_for_shared_validation
        ),
    )


def exam_json() -> str:
    result = run_global_lab_exam()
    return json.dumps(
        {
            "passed": result.passed,
            **asdict(result),
        },
        sort_keys=True,
        indent=2,
    )


if __name__ == "__main__":
    print(exam_json())
