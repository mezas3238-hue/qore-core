"""Causal and source fidelity tests for fixed NAS100 native-M1 DRIVE G1."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_drive_nas100_g1_v1 as d


def make_m1(day: date, slot: int, opening: int) -> d.Open:
    local = datetime(
        day.year, day.month, day.day,
        slot // 60, slot % 60, tzinfo=d.NY,
    )
    return d.Open(at_utc=local.astimezone(UTC), opening=opening)


def full_day(day: date, *, direction: int = 1, outcome: int = 100) -> dict[int, d.Open]:
    slots = {minute: make_m1(day, minute, 100000)
             for minute in d.EXPECTED_MINUTES}
    slots[d.NY_FORMATION_END] = make_m1(day, d.NY_FORMATION_END, 100000 + 100*direction)
    slots[d.NY_ENTRY] = make_m1(day, d.NY_ENTRY, 100000)
    slots[d.NY_EXIT] = make_m1(day, d.NY_EXIT, 100000 + outcome)
    return slots


def test_fixed_source_and_single_clock() -> None:
    assert d.PREREG_SHA == "9ebcf60628196a52cbd476e584d4f554b60af035"
    assert d.SOURCE_ARTIFACT == 10618862813
    assert d.SOURCE_RUN == 35548099334
    assert d.NY_FIRST == 570
    assert d.NY_FORMATION_END == 600
    assert d.NY_ENTRY == 601
    assert d.NY_EXIT == 660
    assert len(d.EXPECTED_MINUTES) == 91
    assert d.SEED == 941211 and d.BOOTSTRAPS == 2000


def test_new_york_dst_frozen_slots() -> None:
    summer, winter = date(2023, 7, 10), date(2023, 1, 9)
    s = make_m1(summer, 570, 100000).at_utc
    w = make_m1(winter, 570, 100000).at_utc
    assert (s.hour, s.minute) == (13, 30)
    assert (w.hour, w.minute) == (14, 30)


def test_complete_day_requires_every_open() -> None:
    day = date(2023, 7, 10)
    slots = full_day(day, direction=1)
    assert d.ny_open(day, 570, slots) == 100000
    assert d.ny_open(day, 601, slots) == 100000
    del slots[611]
    with pytest.raises(ValueError, match="DST"):
        d.ny_open(day, 570, {570: make_m1(day, 571, 100000)})
    assert any(d.ny_open(day, m, slots) is None for m in d.EXPECTED_MINUTES)


def test_zero_formation_abstains_and_no_imputation(monkeypatch: pytest.MonkeyPatch) -> None:
    # Inject a tiny bounded date interval for observational unit tests.
    monkeypatch.setattr(d, "START", datetime(2023, 7, 10, tzinfo=UTC))
    monkeypatch.setattr(d, "END", datetime(2023, 7, 12, tzinfo=UTC))
    monday = date(2023, 7, 10)
    tuesday = date(2023, 7, 11)
    both = {
        monday: full_day(monday, direction=0),
        tuesday: full_day(tuesday, direction=-1),
    }
    observed, census = d.observations(both)
    assert monday not in observed and tuesday in observed
    assert census["ZERO_FORMATION_ABSTAIN"] == 1


def test_yesterday_stale_sign_always_known_before_today() -> None:
    mon = date(2024, 7, 8)
    tue = mon + timedelta(days=1)
    wed = mon + timedelta(days=2)
    observed = {
        mon: d.Day(mon, 0.001, 15.0),
        tue: d.Day(tue, -0.001, 10.0),
        wed: d.Day(wed, -0.001, -4.0),
    }
    rows, skipped = d.pair_prior_sign(observed)
    assert len(rows) == 2
    assert skipped["NO_PREVIOUS_VALID_DAY"] == 1
    assert rows[0].ny_date == tue.isoformat()
    assert rows[0].prior_date == mon.isoformat()
    assert rows[0].drive_direction == -1
    assert rows[0].stale_direction == 1
    assert rows[0].gross_drive_bps == -10
    assert rows[0].gross_stale_bps == 10
    assert rows[0].delta_bps == -20
    assert rows[1].stale_direction == -1 and rows[1].delta_bps == 0


def test_stale_sign_over_five_calendar_days_rejected() -> None:
    first = date(2023, 7, 10)
    second = first + timedelta(days=7)
    records, census = d.pair_prior_sign({
        first: d.Day(first, 0.01, 9.0),
        second: d.Day(second, -0.02, 5.0),
    })
    assert records == []
    assert census["PREVIOUS_VALID_DAY_STALE_OVER_5D"] == 1


def test_sha_manifest_cannot_be_forged_without_rehash(tmp_path: Path) -> None:
    original = {
        "identity": d.SOURCE_IDENTITY,
        "schema": "qore.capitalizer.cibo.m1_clone.v1",
        "canonical_symbol": "NAS100",
        "provider_symbol": "USTEC",
        "provider_native_m1": True,
        "synthetic_m1": False, "interpolated_m1": False,
        "read_only": True,
        "live_authorized": False, "production_authorized": False,
        "contradictory_m1": 0,
        "target_start": d.START.isoformat(),
        "target_end_exclusive": d.END.isoformat(),
        "provider_symbol_id": 102,
        "digits": 2,
        "retained_m1": 123,
        "partitions": [{"partition": str(y), "retained_m1": 0}
                       for y in range(2016, 2027)],
    }
    file = tmp_path / "m1-clone-manifest.json"
    file.write_text(json.dumps(original))
    (tmp_path / "MANIFEST_SHA256SUMS.txt").write_text(
        hashlib.sha256(file.read_bytes()).hexdigest() + "  m1-clone-manifest.json\n"
    )
    payload, witness = d.source_manifest(tmp_path)
    assert payload["canonical_symbol"] == "NAS100"
    assert witness["source_artifact_id"] == 10618862813
    original["synthetic_m1"] = True
    file.write_text(json.dumps(original))
    with pytest.raises(ValueError, match="SHA256"):
        d.source_manifest(tmp_path)
    (tmp_path / "MANIFEST_SHA256SUMS.txt").write_text(
        hashlib.sha256(file.read_bytes()).hexdigest() + "  m1-clone-manifest.json\n"
    )
    with pytest.raises(ValueError, match="source contract mismatch"):
        d.source_manifest(tmp_path)


def test_bootstrap_week_reproducible() -> None:
    start = date(2022, 7, 4)
    rows = []
    for idx in range(18):
        day = start + timedelta(days=idx)
        iso = day.isocalendar()
        rows.append(d.Paired(
            ny_date=day.isoformat(), iso_week=f"{iso.year}-W{iso.week:02d}",
            year=day.year, formation_log=0.01, drive_direction=1,
            stale_direction=-1, prior_date=(day-timedelta(days=1)).isoformat(),
            prior_age_days=1, forward_bps=float(idx+1),
            gross_drive_bps=float(idx+1), gross_stale_bps=float(-idx-1),
            delta_bps=float(2*(idx+1)),
        ))
    a = d.bootstrap_iso_weeks(rows)
    b = d.bootstrap_iso_weeks(rows)
    assert a == b
    assert a["valid_draws"] == d.BOOTSTRAPS
    assert a["weeks"] >= 2


def test_underpowered_never_promotes(monkeypatch: pytest.MonkeyPatch) -> None:
    one = date(2022, 6, 13)
    monkeypatch.setattr(d, "read_native_nas100", lambda source: (
        {one: full_day(one)}, {"source_artifact_id": 10618862813},
    ))
    report, day_rows = d.analyze(Path("."))
    assert report["verdict"] == "DEV_DRIVE_UNDERPOWERED"
    assert report["matched_days"] == 0
    assert report["no_vps_no_mt5_no_live_no_trade"]
    assert day_rows == []
