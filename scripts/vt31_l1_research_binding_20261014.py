#!/usr/bin/env python3
"""Build a REAL canonical Trader Lab DRAFT research binding from frozen NAS100 M1.

Source-only metadata, NOT a methodology qualification, observed provider receipt,
author TTrades fidelity, execution replay, DEMO approval or profitable Trader.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
    build_historical_ohlc_replay_dataset,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.replay_availability import (
    ReplayAvailabilityBasis,
    ReplayAvailabilityEvidenceReference,
    ReplayMarketDataObservation,
    ReplayObservationId,
)
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateId,
    TraderLabCandidateVersion,
    build_trader_lab_candidate_binding,
)
from qore.infrastructure.trader_lab.lifecycle import (
    TraderLabState,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.promotion import evaluate_demo_eligibility
from qore.kernel.result import Success
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    MARKET_SHA,
    collect_hours,
    complete_hour,
    hash_file,
    market_rows,
)

VERSION = "vt31-nyam-source-research-v1"
SCHEMA = "vt31-ttrades-nyam-qore-research-v1"
SOURCE_PORT = "market-data.vt31-original-nas100-research"
PREREG = "f5db95eac6cd275add0ed8dafc814932f742b4b5"
CODES = {
    "cognitive_code_sha256":
        "scripts/vt31_ttrades_am_native_cog_v1_20261014.py",
    "fvg_source_code_sha256":
        "scripts/vt31_m4_m5_ttrades_fvg_path_20261014.py",
    "temporal_parity_code_sha256":
        "scripts/vt31_l3_m1_source_parity_20261014.py",
}


def stable_id(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "qore-vt31-research|" + "|".join(parts))


def _unwrap(value: object) -> object:
    if not isinstance(value, Success):
        raise ValueError("QORE_CANONICAL_BINDING_CONTRACT_REJECTED")
    return value.value


def source_file_hashes(root: Path) -> dict[str, str]:
    return {
        name: sha256((root / path).read_bytes()).hexdigest()
        for name, path in sorted(CODES.items())
    }


def build_research_draft(
    groups: dict[str, dict[int, tuple]],
    *, software_revision: str,
    administrative_at: datetime,
    file_hashes: dict[str, str],
    candidate_version: str = VERSION,
) -> dict:
    """Create canonical SOURCE-ONLY candidate binding, NEVER grant stage evidence."""
    if administrative_at.tzinfo is None or administrative_at.utcoffset() is None:
        raise ValueError("ADMIN_TIME_NOT_AWARE")
    if sorted(file_hashes) != sorted(CODES) or any(
        type(h) is not str or len(h) != 64
        or any(c not in "0123456789abcdef" for c in h)
        for h in file_hashes.values()
    ):
        raise ValueError("SOURCE_CODE_HASH_EVIDENCE_INVALID")
    if not software_revision or any(
        c not in "0123456789abcdef" for c in software_revision
    ):
        raise ValueError("SOFTWARE_REVISION_NOT_GIT_HEX")
    eligible = [
        (day, blocks[9] + blocks[10])
        for day, blocks in sorted(groups.items())
        if complete_hour(day, 9, blocks.get(9, ()))
        and complete_hour(day, 10, blocks.get(10, ()))
    ]
    if not eligible:
        raise ValueError("NO_COMPLETE_HISTORICAL_120_M1_FOR_BINDING")
    chosen_day, bars = eligible[0]
    if len(bars) != 120:
        raise ValueError("SOURCE_SLICE_M1_COUNT_NOT_120")
    if any(
        a.closed_at != b.opened_at for a, b in zip(bars, bars[1:], strict=False)
    ):
        raise ValueError("SOURCE_120_M1_GAP_OR_REORDER")

    instrument = Instrument("NAS100")
    timeframe = Timeframe(60)
    identity = (MARKET_SHA, chosen_day, candidate_version)
    source = ExternalSourceDescriptor(
        adapter_id=AdapterId(stable_id("historical-adapter", MARKET_SHA)),
        source_id=SourceId(stable_id("original-m1-source", MARKET_SHA)),
        port_name=PortName(SOURCE_PORT),
    )
    window = HistoricalOhlcWindow(
        instrument, timeframe, bars[0].opened_at, bars[-1].closed_at,
    )
    observations = tuple(
        ReplayMarketDataObservation(
            observation_id=ReplayObservationId(
                stable_id("observation", MARKET_SHA, bar.opened_at.isoformat())
            ),
            payload=OhlcSnapshot(
                snapshot_id=MarketDataSnapshotId(
                    stable_id("snapshot", MARKET_SHA, bar.opened_at.isoformat())
                ),
                instrument=instrument, source=source, timeframe=timeframe,
                opened_at=bar.opened_at, closed_at=bar.closed_at,
                open=float(bar.open), high=float(bar.high),
                low=float(bar.low), close=float(bar.close),
            ),
            availability_evidence_at=bar.closed_at,
            available_at=bar.closed_at,
            availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
            availability_evidence_ref=ReplayAvailabilityEvidenceReference(
                stable_id("available-m1-close", MARKET_SHA, bar.opened_at.isoformat())
            ),
        )
        for bar in bars
    )
    dataset = _unwrap(build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(stable_id("120-m1-dataset", *identity)),
        revision_id=HistoricalDatasetRevisionId(
            stable_id("source-revision", MARKET_SHA, chosen_day)
        ),
        parent_revision_id=None, revision_reason=None,
        scope=HistoricalOhlcDatasetScope(source=source, window=window),
        assembled_at=administrative_at,
        schema_version=HistoricalDatasetSchemaVersion("vt31-original-m1-research-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion(
            "source-decimal-to-canonical-float-v1"
        ),
        observations=observations,
    ))
    config_id = ResearchStrategyConfigurationId(
        stable_id("config", *identity)
    )
    parameters = (
        ResearchStrategyParameter("available_at_semantics", "M1_CLOSED_BOUNDARY_ONLY"),
        ResearchStrategyParameter("broker_contract_status", "UNHOMOLOGATED"),
        ResearchStrategyParameter("data_partition", "CONSUMED_3Y_DEVELOPMENT_NO_OOS"),
        ResearchStrategyParameter("economic_execution_enabled", False),
        ResearchStrategyParameter("fvg_model", "FIRST_3_M1_QORE_PROXY"),
        ResearchStrategyParameter("m1_slice_count", 120),
        ResearchStrategyParameter("market", "NAS100"),
        ResearchStrategyParameter("mss_9h_first_return", "QORE_PROXY"),
        ResearchStrategyParameter("mss_dol_min_points", 10),
        ResearchStrategyParameter("profile", "TTRADES_NY_AM_2025_QORE_PROXY"),
        ResearchStrategyParameter("raw_source_sha256", MARKET_SHA),
        ResearchStrategyParameter("sizing_produced", False),
        ResearchStrategyParameter("stop_reference", "C2_FULL_WICK_NOT_BROKER_ORDER"),
        ResearchStrategyParameter("ttrades_author_fidelity", "UNVERIFIED"),
        *(
            ResearchStrategyParameter(name, value)
            for name, value in sorted(file_hashes.items())
        ),
    )
    manifest = _unwrap(build_research_strategy_configuration_manifest(
        configuration_id=config_id,
        schema_version=ResearchStrategySchemaVersion(SCHEMA),
        parameters=parameters,
        frozen_at=administrative_at,
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            stable_id("freeze", *identity)
        ),
    ))
    run = _unwrap(build_research_run_evidence(
        run_id=ResearchRunId(stable_id("run", *identity, software_revision)),
        created_at=administrative_at,
        datasets=(dataset.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion(
            "m1-closed-source-only-v1"
        ),
        simulated_start=bars[0].opened_at,
        simulated_end=bars[-1].closed_at,
        strategy_configuration_id=config_id,
        software_revision=ResearchSoftwareRevision(software_revision),
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    ))
    research_binding = _unwrap(build_research_run_strategy_binding(
        run=run, manifest=manifest,
    ))
    candidate = _unwrap(build_trader_lab_candidate_binding(
        candidate_id=TraderLabCandidateId(stable_id("candidate", "VT31-NAS100")),
        version=TraderLabCandidateVersion(candidate_version),
        strategy_binding=research_binding,
    ))
    lifecycle = start_trader_lab_lifecycle(candidate)
    promotion = evaluate_demo_eligibility(lifecycle)
    assert lifecycle.state is TraderLabState.DRAFT
    assert not lifecycle.completed_stages
    assert promotion.status.value == "not_eligible_incomplete"
    assert dataset.manifest.observation_count == 120
    assert not dataset.manifest.gaps
    assert all(
        obs.availability_basis is ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY
        and obs.available_at == obs.payload.closed_at
        for obs in dataset.observations
    )
    assert run.execution_model_id is None
    assert run.transaction_cost_model_id is None
    return {
        "kind": "VT31_REAL_M1_CANONICAL_TRADER_LAB_RESEARCH_DRAFT",
        "sample_selection_rule": "EARLIEST_NY_DAY_WITH_FULL_09_10_M1",
        "selected_ny_day": chosen_day,
        "m1_sample_observations": dataset.manifest.observation_count,
        "market": "NAS100", "timeframe_seconds": 60,
        "source_raw_sha256": MARKET_SHA,
        "research_dataset_digest": dataset.manifest.evidence_digest.value,
        "research_run_input_fingerprint": run.input_fingerprint.value,
        "strategy_config_digest": manifest.content_digest.value,
        "research_strategy_binding_fingerprint":
            research_binding.binding_fingerprint.value,
        "trader_lab_candidate_fingerprint": candidate.fingerprint.value,
        "trader_lab_candidate_uuid": str(candidate.candidate_id.value),
        "trader_lab_candidate_version": candidate.version.value,
        "source_code_sha256": dict(sorted(file_hashes.items())),
        "software_revision": software_revision,
        "administrative_freeze_at": administrative_at.astimezone(UTC).isoformat(),
        "availability_basis": "STRUCTURAL_BOUNDARY_NOT_PROVIDER_RECEIPT",
        "original_source_history_consumed_before_this_round": True,
        "temporal_prereg_does_not_prove_fresh_blind_validation": True,
        "broker_contract_homologated": False,
        "broker_tick_ack_or_fills": 0,
        "sizing_calculated": False,
        "trader_lab_state": lifecycle.state.value,
        "trader_lab_completed_stages": list(lifecycle.completed_stages),
        "trader_lab_L1_method_author_certified": False,
        "trader_lab_L2_replay_qualified": False,
        "trader_lab_L3_fast_forward_qualified": False,
        "demo_eligibility": promotion.status.value,
        "evaluation_economic": None,
        "fresh_holdout": False,
        "trader_certified": False,
        "live_authorized": False,
        "prereg_commit": PREREG,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--administrative-at", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("FROZEN_REAL_M1_SOURCE_HASH_MISMATCH")
    groups, count = collect_hours(market_rows(args.market))
    report = build_research_draft(
        groups,
        software_revision=args.revision,
        administrative_at=datetime.fromisoformat(
            args.administrative_at.replace("Z", "+00:00")
        ),
        file_hashes=source_file_hashes(Path(__file__).resolve().parent.parent),
    )
    if count != 1_059_784:
        raise ValueError("ORIGINAL_NAS100_M1_COUNT_MISMATCH")
    report["original_m1_count"] = count
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        k: report[k] for k in (
            "selected_ny_day", "m1_sample_observations",
            "research_dataset_digest", "trader_lab_candidate_fingerprint",
            "trader_lab_state", "demo_eligibility",
        )
    }, sort_keys=True))


if __name__ == "__main__":
    main()
