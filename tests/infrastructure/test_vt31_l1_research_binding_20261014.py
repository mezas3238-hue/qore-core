"""Canonical VT31 DRAFT binding from M1; synthetic tests are not real data."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_l1_research_binding_20261014 import (
    CODES,
    MARKET_SHA,
    VERSION,
    build_research_draft,
    source_file_hashes,
)

NY = ZoneInfo("America/New_York")
TIME = datetime(2026, 10, 14, 21, 30, tzinfo=UTC)
FAKE_HASHES = dict.fromkeys(CODES, "a" * 64)


def m1(at):
    return M1Bar(
        at, at + timedelta(minutes=1),
        Decimal("20101"), Decimal("20104"),
        Decimal("20098"), Decimal("20102"),
    )


def fixtures():
    first = datetime(2024, 1, 15, 9, tzinfo=NY).astimezone(UTC)
    second = datetime(2025, 7, 15, 9, tzinfo=NY).astimezone(UTC)

    def day(start):
        return {
            9: tuple(m1(start + timedelta(minutes=i)) for i in range(60)),
            10: tuple(m1(start + timedelta(minutes=60+i)) for i in range(60)),
        }

    return {"2025-07-15": day(second), "2024-01-15": day(first)}


def build(groups=None, **kwargs):
    return build_research_draft(
        groups if groups is not None else fixtures(),
        software_revision=kwargs.pop("software_revision", "ab12345678"),
        administrative_at=kwargs.pop("administrative_at", TIME),
        file_hashes=kwargs.pop("file_hashes", FAKE_HASHES),
        **kwargs,
    )


def test_canonical_120_real_contract_types_are_built_for_earliest_ny_day():
    out = build()
    assert out["selected_ny_day"] == "2024-01-15"
    assert out["m1_sample_observations"] == 120
    assert out["market"] == "NAS100"
    assert out["timeframe_seconds"] == 60
    assert out["source_raw_sha256"] == MARKET_SHA
    assert out["availability_basis"] == (
        "STRUCTURAL_BOUNDARY_NOT_PROVIDER_RECEIPT"
    )
    assert out["trader_lab_state"] == "draft"
    assert out["trader_lab_completed_stages"] == []
    assert out["demo_eligibility"] == "not_eligible_incomplete"
    assert out["trader_lab_L1_method_author_certified"] is False
    assert out["trader_lab_L2_replay_qualified"] is False
    assert out["trader_lab_L3_fast_forward_qualified"] is False
    assert out["trader_certified"] is False
    assert out["broker_tick_ack_or_fills"] == 0
    assert out["sizing_calculated"] is False
    assert out["evaluation_economic"] is None


def test_same_source_version_code_and_timestamp_yields_same_fingerprint():
    first, second = build(), build()
    assert first == second
    assert len(first["trader_lab_candidate_fingerprint"]) == 64
    assert first["research_dataset_digest"] == second["research_dataset_digest"]


def test_version_mutation_invalidates_exact_candidate_binding():
    prior = build()
    changed = build(candidate_version="vt31-nyam-source-research-v2")
    assert prior["trader_lab_candidate_fingerprint"] != (
        changed["trader_lab_candidate_fingerprint"]
    )
    assert prior["trader_lab_candidate_uuid"] == (
        changed["trader_lab_candidate_uuid"]
    )
    assert changed["trader_lab_state"] == "draft"
    assert changed["demo_eligibility"] == "not_eligible_incomplete"


def test_real_code_sha_mutation_invalidates_config_and_candidate():
    old = build()
    modified = dict(FAKE_HASHES)
    modified["cognitive_code_sha256"] = "b" * 64
    fresh = build(file_hashes=modified)
    assert fresh["strategy_config_digest"] != old["strategy_config_digest"]
    assert fresh["trader_lab_candidate_fingerprint"] != (
        old["trader_lab_candidate_fingerprint"]
    )
    assert fresh["trader_lab_state"] == "draft"


def test_software_revision_changes_run_and_candidate_fingerprint():
    old = build()
    fresh = build(software_revision="cd23456789")
    assert old["research_run_input_fingerprint"] != (
        fresh["research_run_input_fingerprint"]
    )
    assert old["trader_lab_candidate_fingerprint"] != (
        fresh["trader_lab_candidate_fingerprint"]
    )


def test_administrative_time_not_backfilled_or_naive():
    with pytest.raises(ValueError, match="ADMIN_TIME_NOT_AWARE"):
        build(administrative_at=datetime(2026, 10, 14, 21, 30))


def test_critical_missing_minute_fail_closed_not_imputed():
    samples = fixtures()
    original = samples["2024-01-15"]
    samples["2024-01-15"] = {
        9: original[9][:30] + original[9][31:], 10: original[10],
    }
    out = build(samples)
    assert out["selected_ny_day"] == "2025-07-15"
    samples["2025-07-15"] = {9: (), 10: ()}
    with pytest.raises(ValueError, match="NO_COMPLETE_HISTORICAL"):
        build(samples)


def test_corrupt_file_hash_or_fake_software_revision_fails_closed():
    invalid = dict(FAKE_HASHES)
    invalid["cognitive_code_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="SOURCE_CODE_HASH"):
        build(file_hashes=invalid)
    with pytest.raises(ValueError, match="SOFTWARE_REVISION_NOT_GIT_HEX"):
        build(software_revision="release-v1")


def test_manifest_source_reader_collects_only_expected_sha_form():
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    actual = source_file_hashes(root)
    assert sorted(actual) == sorted(CODES)
    assert all(len(value) == 64 for value in actual.values())
    assert VERSION == "vt31-nyam-source-research-v1"


def test_dataset_changes_if_original_source_M1_changes():
    first = build()
    groups = fixtures()
    old = groups["2024-01-15"][10]
    changed = list(old)
    item = old[10]
    changed[10] = M1Bar(
        item.opened_at, item.closed_at, item.open, item.high + Decimal("1"),
        item.low, item.close,
    )
    groups["2024-01-15"][10] = tuple(changed)
    new = build(groups)
    assert first["research_dataset_digest"] != new["research_dataset_digest"]
    assert first["trader_lab_candidate_fingerprint"] != (
        new["trader_lab_candidate_fingerprint"]
    )


def test_dst_window_hour_instrument_and_no_stages_for_summer():
    sample = fixtures()
    sample.pop("2024-01-15")
    out = build(sample)
    assert out["selected_ny_day"] == "2025-07-15"
    assert out["m1_sample_observations"] == 120
    assert out["trader_lab_completed_stages"] == []
    assert out["demo_eligibility"] == "not_eligible_incomplete"
