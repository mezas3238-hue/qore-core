"""Read-only QORE RESET G2 M1 causal boundary tests."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_reset_fix_g1_v1 as g1
from qore.infrastructure.trader_lab import qore_native_reset_fix_g2_m1_exploratory_v1 as g2


def sample_event() -> g1.Event:
    return g1.Event(
        day="2022-07-12", week="2022-W28", year=2022,
        fixing_class="HIGH", placebo_class="LOW",
        fixing_pressure_bps=3.0, placebo_pressure_bps=-4.0,
        fixing_reversal_bps=55.0, placebo_reversal_bps=-55.0,
        fixing_delay_bps=2.0, placebo_delay_bps=2.0,
        month_end=False,
    )


def open_at(day: date, minute: int, opening: float) -> g2.M1Open:
    stamp = datetime(day.year, day.month, day.day,
                     minute // 60, minute % 60, tzinfo=g1.LONDON)
    return g2.M1Open(stamp.astimezone(UTC), opening)


def test_clock_and_prereg_no_pnl_optimisation() -> None:
    assert g2.PREREG_SHA == "3d96c55b06d376b26fc9e501be9fe9d2539f59b4"
    assert g2.M1_RUN == 35548099334
    assert g2.M1_ARTIFACT == 10618547852
    assert g2.M1_WINDOWS == {"FIX": (963, 975), "PLACEBO": (843, 855)}
    assert g1.LOOKBACK == 120
    assert g1.SEED == 941102
    assert g1.N_BOOTSTRAP == 2000


def test_dst_native_m1_window_utc_conversion() -> None:
    day = date(2022, 7, 12)
    record = open_at(day, 963, 1.12)
    assert record.timestamp_utc.hour == 15
    assert record.timestamp_utc.minute == 3
    assert g2.native_open(day, 963, {963: record}) == 1.12
    winter = date(2022, 1, 11)
    assert open_at(winter, 963, 1.1).timestamp_utc.hour == 16


def test_fake_misaligned_open_fails_closed() -> None:
    day = date(2022, 7, 12)
    record = open_at(day, 964, 1.12)
    with pytest.raises(ValueError, match="DST-adjusted"):
        g2.native_open(day, 963, {963: record})


def test_m1_reversion_uses_only_original_g1_pressure_and_native_open() -> None:
    prior = sample_event()
    day = date.fromisoformat(prior.day)
    pairs = {
        963: open_at(day, 963, 1.1020),
        975: open_at(day, 975, 1.1000),
        843: open_at(day, 843, 1.1020),
        855: open_at(day, 855, 1.1000),
    }
    fixed, placebo = g2.reversals(prior, pairs) or (None, None)
    assert fixed is not None and fixed > 0
    assert placebo is not None and placebo < 0
    del pairs[855]
    assert g2.reversals(prior, pairs) is None


def test_manifest_sha_native_identity_and_no_synthetic(tmp_path: Path) -> None:
    p = tmp_path / "m1-clone-manifest.json"
    data = {
        "identity": g2.M1_IDENTITY,
        "schema": "qore.capitalizer.cibo.m1_clone.v1",
        "canonical_symbol": "EURUSD", "provider_symbol": "EURUSD",
        "target_start": g1.START_UTC.isoformat(),
        "target_end_exclusive": g1.END_UTC.isoformat(),
        "digits": 5, "provider_native_m1": True,
        "synthetic_m1": False, "interpolated_m1": False,
        "read_only": True, "live_authorized": False,
        "production_authorized": False, "contradictory_m1": 0,
        "partitions": [{"partition": str(year)}
                       for year in range(2016, 2027)],
        "retained_m1": 2,
    }
    p.write_text(json.dumps(data))
    (tmp_path / "MANIFEST_SHA256SUMS.txt").write_text(
        hashlib.sha256(p.read_bytes()).hexdigest() + "  m1-clone-manifest.json\n"
    )
    result, witness = g2.manifest_m1(tmp_path)
    assert result["retained_m1"] == 2
    assert witness["consumed_development_only"]
    data["synthetic_m1"] = True
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="sha256"):
        g2.manifest_m1(tmp_path)


def test_manifest_rejects_synthetic_even_if_rehashed(tmp_path: Path) -> None:
    data = {
        "identity": g2.M1_IDENTITY,
        "schema": "qore.capitalizer.cibo.m1_clone.v1",
        "canonical_symbol": "EURUSD", "provider_symbol": "EURUSD",
        "target_start": g1.START_UTC.isoformat(),
        "target_end_exclusive": g1.END_UTC.isoformat(),
        "digits": 5, "provider_native_m1": True,
        "synthetic_m1": True, "interpolated_m1": False,
        "read_only": True, "live_authorized": False,
        "production_authorized": False, "contradictory_m1": 0,
        "partitions": [{"partition": str(year)}
                       for year in range(2016, 2027)],
        "retained_m1": 1,
    }
    raw = tmp_path / "m1-clone-manifest.json"
    raw.write_text(json.dumps(data))
    (tmp_path / "MANIFEST_SHA256SUMS.txt").write_text(
        hashlib.sha256(raw.read_bytes()).hexdigest() + "  m1-clone-manifest.json\n"
    )
    with pytest.raises(ValueError, match="native M1 immutable"):
        g2.manifest_m1(tmp_path)


def test_joint_cohort_missing_m1_not_imputed(monkeypatch: pytest.MonkeyPatch) -> None:
    prior = sample_event()
    monkeypatch.setattr(g2.g1, "read_existing_cibo_atlas",
                        lambda root: ({}, {"source": "already_consumed_G1_M5"}))
    monkeypatch.setattr(g2.g1, "build_events",
                        lambda m5: ([prior], {"causal_cohort": True}))
    monkeypatch.setattr(g2, "read_native_m1",
                        lambda root: ({}, {"source": "native_M1"}))
    report, rows = g2.run(Path("."), Path("."))
    assert report["m1_matched_days"] == 0
    assert report["joint_rejection_reasons"]["MISSING_M1_ENTRY_OR_EXIT_JOINT_PAIR"] == 1
    assert report["verdict"] == "DEV_M1_UNDERPOWERED"
    assert rows == []


def test_joint_sample_does_not_inherit_economic_g1_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prior = sample_event()
    day = date.fromisoformat(prior.day)
    native = {
        day: {
            963: open_at(day, 963, 1.1020),
            975: open_at(day, 975, 1.1000),
            843: open_at(day, 843, 1.1020),
            855: open_at(day, 855, 1.1000),
        }
    }
    monkeypatch.setattr(g2.g1, "read_existing_cibo_atlas", lambda root: ({}, {}))
    monkeypatch.setattr(g2.g1, "build_events", lambda m5: ([prior], {}))
    monkeypatch.setattr(g2, "read_native_m1", lambda root: (native, {}))
    report, records = g2.run(Path("."), Path("."))
    assert len(records) == 1
    assert report["m1_matched_days"] == 1
    assert report["verdict"] == "DEV_M1_UNDERPOWERED"
    assert 0 < records[0]["fixing_tail_reversal_bps_m1"] < 30
    assert records[0]["fixing_tail_reversal_bps_m1"] != prior.fixing_reversal_bps
    assert report["bidask_not_required_for_gross_signal"]
    assert report["reserved_2014_2016_raw_not_opened"]
