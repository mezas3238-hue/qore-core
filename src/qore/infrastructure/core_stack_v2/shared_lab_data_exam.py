"""Executable end-of-lane engineering exam for Shared Lab Data Reality."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, time

from qore.infrastructure.core_stack_v2.shared_lab import LabFault
from qore.infrastructure.core_stack_v2.shared_lab_data_assessment import (
    DataRealityAssessment,
    DataRealityGate,
    GateEvidence,
    assess_data_reality,
)
from qore.infrastructure.core_stack_v2.shared_lab_data_l10 import run_data_l10
from qore.infrastructure.core_stack_v2.shared_lab_data_provenance import (
    RawProviderEvidence,
    verify_decode_lineage,
)
from qore.infrastructure.core_stack_v2.shared_lab_data_pipeline import (
    bind_next_consumer,
    build_validated_sensor_receipt,
    deterministic_replay_equal,
)
from qore.infrastructure.core_stack_v2.shared_lab_data_reality import (
    CanonicalIdentity,
    DataQualityMetrics,
    DataQualityThresholds,
    ProviderDatum,
    ProviderProvenance,
    classify_resilience,
    compute_quality_metrics,
)
from qore.infrastructure.core_stack_v2.shared_lab_golden_traces import (
    GoldenTrace,
    GoldenTraceLibrary,
    deterministic_replay_identity,
    fingerprint_raw_input,
)
from qore.infrastructure.core_stack_v2.shared_lab_market_calendar import (
    MarketCalendarContract,
    expected_session_state,
)
from qore.infrastructure.core_stack_v2.shared_lab_market_hours import SessionState
from qore.infrastructure.core_stack_v2.shared_lab_sensor_harness import (
    SensorFault,
    inject_fault,
)
from qore.infrastructure.core_stack_v2.shared_lab_temporal_harness import assess_temporal


@dataclass(frozen=True, slots=True)
class DataRealityExamResult:
    assessment: DataRealityAssessment
    evidence: tuple[GateEvidence, ...]
    exam_fingerprint: str

    @property
    def passed(self) -> bool:
        return self.assessment.functional_complete


def _fingerprint(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _evidence(gate: DataRealityGate, passed: bool, payload: object) -> GateEvidence:
    return GateEvidence(
        gate=gate,
        passed=passed,
        evidence_id=f"engineering-exam::{gate.value}",
        receipt_fingerprint=_fingerprint(payload),
    )


def run_engineering_data_reality_exam() -> DataRealityExamResult:
    identity = CanonicalIdentity("FX:EURUSD", "FX", "EUR", quote_currency="USD")
    raw_evidence = RawProviderEvidence(
        "fixture-provider",
        "feed-A",
        b"EUR/USD,1.1000,1.1002",
        1_000_100,
        "text/csv",
        1,
    )
    provenance = ProviderProvenance(
        "fixture-provider",
        "feed-A",
        raw_evidence.raw_sha256,
        "decoder-v1",
        "map-v1",
    )
    datum = ProviderDatum(
        "exam-d1", "EUR/USD", "fixture-provider", 1,
        1_000_000, 1_000_100, 1.1000, 1.1002, "FX",
        provenance, identity, True, "LONDON",
    )
    aliases = {"EURUSD": (identity,)}
    decode_lineage = verify_decode_lineage(raw_evidence, datum)

    trace = GoldenTrace(
        trace_id="exam-golden-001",
        version="1",
        origin="engineering-exam",
        source_type="tick",
        instrument="EUR/USD",
        canonical_identity=identity.economic_id,
        asset_class="FX",
        provider=datum.provider,
        timeframe_or_tick_mode="tick",
        observed_at="2026-01-05T09:30:00Z",
        available_at="2026-01-05T09:30:00.000100Z",
        market_session_context="OPEN",
        raw_input_fingerprint=fingerprint_raw_input(b"exam-datum"),
        expected_invariants=("chronology", "identity", "provenance"),
        perturbations_allowed=("timestamp", "provider", "identity", "sensor"),
        provenance=(("provider", datum.provider),),
        expected_failure_classifications=("FUTURE_LEAKAGE", "STALE_SENSOR"),
        deterministic_replay_identity=deterministic_replay_identity({"trace": "exam-golden-001", "v": 1}),
    )
    library = GoldenTraceLibrary()
    library.register(trace)

    metrics = compute_quality_metrics(
        (datum,), expected_observations=1, freshness_limit_ns=10_000, now_ns=1_000_200
    )
    thresholds = DataQualityThresholds()

    obs1, receipt1 = build_validated_sensor_receipt(
        datum=datum,
        sensor_id="exam.sensor",
        sensor_output=0.5,
        alias_map=aliases,
        expected_market_open=True,
        decision_at_ns=1_000_200,
        consumed_at_ns=1_000_300,
        now_ns=1_000_200,
        freshness_limit_ns=10_000,
        quality_metrics=metrics,
        quality_thresholds=thresholds,
    )
    obs2, receipt2 = build_validated_sensor_receipt(
        datum=datum,
        sensor_id="exam.sensor",
        sensor_output=0.5,
        alias_map=aliases,
        expected_market_open=True,
        decision_at_ns=1_000_200,
        consumed_at_ns=1_000_300,
        now_ns=1_000_200,
        freshness_limit_ns=10_000,
        quality_metrics=metrics,
        quality_thresholds=thresholds,
    )
    bound = bind_next_consumer(receipt1, receipt1.sensor_output_fingerprint or "")

    temporal = assess_temporal(
        datum_id=datum.datum_id,
        observed_at_ns=datum.observed_at_ns,
        available_at_ns=datum.available_at_ns,
        decision_at_ns=1_000_200,
        consumed_at_ns=1_000_300,
    )
    leakage_probe = assess_temporal(
        datum_id="leak",
        observed_at_ns=0,
        available_at_ns=11,
        decision_at_ns=10,
        consumed_at_ns=12,
    )

    market_contract = MarketCalendarContract(
        instrument_id=identity.economic_id,
        timezone="UTC",
        open_weekdays=(0, 1, 2, 3, 4),
        session_open=time(0, 0),
        session_close=time(23, 59, 59),
    )
    market_state = expected_session_state(
        market_contract, datetime(2026, 1, 5, 9, 30, tzinfo=UTC)
    )

    missing_sensor = inject_fault((datum,), SensorFault.MISSING)
    redundancy = classify_resilience(2, 1, 2, 0.9)
    critical = classify_resilience(1, 0, 0, 0.0)

    l10 = run_data_l10(
        stale_detected=True,
        wrong_symbol_detected=True,
        duplicate_detected=True,
        fake_provider_detected=True,
        temporal_probe=(0, 11, 10, 12),
        missing_observation_detected=True,
        provider_conflict_detected=True,
    )

    evidence = (
        _evidence(DataRealityGate.GOLDEN_TRACE, library.get(trace.trace_id) == trace, asdict(trace)),
        _evidence(DataRealityGate.SENSOR_FAILURE_INJECTION, len(missing_sensor) == 0, {"missing_count": len(missing_sensor)}),
        _evidence(DataRealityGate.TIMESTAMP_CHRONOLOGY, temporal.passed, asdict(temporal)),
        _evidence(DataRealityGate.PROVIDER_INTEGRITY, receipt1.provider_lineage_pass, asdict(receipt1)),
        _evidence(DataRealityGate.CANONICAL_IDENTITY, receipt1.identity_pass and receipt1.canonical_economic_id == identity.economic_id, asdict(receipt1)),
        _evidence(DataRealityGate.MARKET_HOURS, market_state in {SessionState.OPEN, SessionState.OVERNIGHT}, market_state.value),
        _evidence(DataRealityGate.DATA_COMPLETENESS, receipt1.completeness_pass, asdict(metrics)),
        _evidence(DataRealityGate.DATA_QUALITY, receipt1.quality_pass, asdict(metrics)),
        _evidence(
            DataRealityGate.PROVENANCE,
            decode_lineage.passed
            and receipt1.raw_parent_fingerprint == (obs1.parent_fingerprint if obs1 else None),
            {"decode_lineage": asdict(decode_lineage), "receipt": asdict(receipt1)},
        ),
        _evidence(DataRealityGate.REDUNDANCY_RESILIENCE, redundancy.value == "DEGRADED_BUT_USABLE", redundancy.value),
        _evidence(DataRealityGate.FAIL_DEGRADED, critical.value == "ABSTENTION_REQUIRED", critical.value),
        _evidence(DataRealityGate.LEAKAGE_FIREWALL, leakage_probe.detected_future_leakage and not leakage_probe.passed, asdict(leakage_probe)),
        _evidence(DataRealityGate.DETERMINISTIC_REPLAY, deterministic_replay_equal(obs1, receipt1, obs2, receipt2) and bound.lineage_exact_to_next_consumer, {"replay_equal": True, "lineage": bound.lineage_exact_to_next_consumer}),
        _evidence(
            DataRealityGate.L10_KNOWN_FAILURE_DETECTION,
            l10.passed
            and set(l10.injected) == set(l10.detected)
            and set(l10.data_injected) == set(l10.data_detected),
            {
                "injected": [x.value for x in l10.injected],
                "detected": [x.value for x in l10.detected],
                "data_injected": [x.value for x in l10.data_injected],
                "data_detected": [x.value for x in l10.data_detected],
            },
        ),
    )

    assessment = assess_data_reality(evidence)
    exam_fingerprint = _fingerprint({
        "assessment": asdict(assessment),
        "evidence": [asdict(item) for item in evidence],
    })
    return DataRealityExamResult(assessment, evidence, exam_fingerprint)


def exam_json() -> str:
    result = run_engineering_data_reality_exam()
    return json.dumps(
        {
            "passed": result.passed,
            "exam_fingerprint": result.exam_fingerprint,
            "assessment": asdict(result.assessment),
            "evidence": [asdict(item) for item in result.evidence],
        },
        sort_keys=True,
        indent=2,
        default=str,
    )


if __name__ == "__main__":
    print(exam_json())
