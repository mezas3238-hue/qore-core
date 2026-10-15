"""Adversarial A/B source catalog tests; no TTrades semantics or execution."""
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_a_b_market_custody_catalog_v1 import (
    STAGE,
    build_catalog,
)
from qore.infrastructure.trader_lab.vt08_a_m30m3_raw_bar_custody_v1 import _bar_receipt
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

C2 = datetime(2026, 10, 15, 12, tzinfo=UTC)
M3_SHA = "a" * 64
M15_SHA = "b" * 64


def _bars(start: datetime, count: int, duration: int, sha: str, profile: str):
    out = []
    for index in range(count):
        opened = start + timedelta(minutes=index * duration)
        source_bar = Vt08B01Bar(
            opened_at=opened,
            closed_at=opened + timedelta(minutes=duration),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
        )
        out.append(_bar_receipt(source_bar, sha, profile))
    return out


def _fixture():
    case = {
        "market": "EURJPY",
        "stage": STAGE,
        "c1_opened_at_utc": (C2 - timedelta(minutes=30)).isoformat(),
        "c2_opened_at_utc": C2.isoformat(),
        "decision_at_utc": (C2 + timedelta(minutes=30)).isoformat(),
        "source_m3_file_sha256": M3_SHA,
        "source_m15_file_sha256": M15_SHA,
        "c1_m3_raw_bar_receipts": _bars(
            C2 - timedelta(minutes=30), 10, 3, M3_SHA, "M3",
        ),
        "c2_m3_raw_bar_receipts": _bars(C2, 10, 3, M3_SHA, "M3"),
        "c2_m15_raw_bar_receipts": _bars(C2, 2, 15, M15_SHA, "M15"),
        "pre_c2_h1_m15_raw_bar_receipts": _bars(
            C2 - timedelta(hours=3), 12, 15, M15_SHA, "M15",
        ),
        "pre_c2_h1_context_available": True,
        "A_rule_complete": False,
        "cognitive_ready": False,
        "broker_fill": False,
        "pnl_read": False,
    }
    report = {
        "market": "EURJPY",
        "source_m3_sha256": M3_SHA,
        "source_m15_sha256": M15_SHA,
        "c2_windows_total": 1,
        "stage_counts": {STAGE: 1},
        "pnl_evaluated": False,
        "examples_by_stage": {STAGE: [case]},
    }
    frozen = {
        "market_rows": {
            "EURJPY": {
                "m3_raw_sha256": M3_SHA,
                "m15_raw_sha256": M15_SHA,
                "c2_windows_total": 1,
                "stage_counts": {STAGE: 1},
            },
        },
    }
    return report, frozen


def _run(report, frozen):
    return build_catalog(
        market="EURJPY", source_report=report, frozen_manifest=frozen,
    )


def test_market_catalog_pins_raw_shas_with_real_bar_ids_and_denies_trading():
    report, frozen = _fixture()
    payload = _run(report, frozen)
    assert payload["source_only_event_count"] == 1
    assert payload["catalog_unique_bars"] == 34
    assert payload["pinned_raw_shas"] == [M3_SHA, M15_SHA]
    assert payload["source_raw_market_map"] == {
        M3_SHA: "EURJPY", M15_SHA: "EURJPY",
    }
    assert all(
        bar["market"] == "EURJPY" and bar["profile"] in ("M3", "M15")
        for bar in payload["bar_catalog"].values()
    )
    assert len(payload["source_only_events"][0]["source_bar_groups"][
        "pre_c2_h1_m15_raw_bar_receipts"
    ]) == 12
    assert not payload["author_fidelity_certified"]
    assert not payload["cognitive_certified"]
    assert not payload["independent_B_verified"]
    assert payload["signed_A_B_manifest_sha256"] is None
    assert payload["fills"] == payload["orders"] == 0


def test_foreign_market_or_feed_digest_rejected():
    report, frozen = _fixture()
    report["market"] = "USDCHF"
    with pytest.raises(ValueError, match="market identity"):
        _run(report, frozen)
    report, frozen = _fixture()
    report["examples_by_stage"][STAGE][0]["source_m3_file_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="cross-feed"):
        _run(report, frozen)


def test_wrong_bar_id_or_modified_ohlc_rejected():
    report, frozen = _fixture()
    bar = report["examples_by_stage"][STAGE][0]["c2_m3_raw_bar_receipts"][0]
    bar["ohlc"] = ("100", "102", "99", "100")
    with pytest.raises(ValueError, match="bar SHA"):
        _run(report, frozen)
    report, frozen = _fixture()
    bar = report["examples_by_stage"][STAGE][0]["c2_m3_raw_bar_receipts"][0]
    bar["source_bar_id"] = "1" * 64
    with pytest.raises(ValueError, match="bar SHA"):
        _run(report, frozen)


def test_future_bar_and_clock_backdating_rejected():
    report, frozen = _fixture()
    bar = report["examples_by_stage"][STAGE][0]["c1_m3_raw_bar_receipts"][-1]
    bar["available_at_utc"] = (C2 + timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError, match="availability mismatch"):
        _run(report, frozen)
    report, frozen = _fixture()
    bar = report["examples_by_stage"][STAGE][0]["c2_m15_raw_bar_receipts"][-1]
    bar["closed_at_utc"] = (C2 + timedelta(minutes=45)).isoformat()
    with pytest.raises(ValueError, match="interval"):
        _run(report, frozen)


def test_legacy_h1_profile_cannot_masquerade_as_original_m15():
    report, frozen = _fixture()
    bar = report["examples_by_stage"][STAGE][0][
        "pre_c2_h1_m15_raw_bar_receipts"
    ][0]
    bar["profile"] = "M15_PRE_C2_H1"
    with pytest.raises(ValueError, match="no legacy"):
        _run(report, frozen)


def test_one_missing_h1_context_remains_source_only_and_not_admitted():
    report, frozen = _fixture()
    case = report["examples_by_stage"][STAGE][0]
    case["pre_c2_h1_context_available"] = False
    case["pre_c2_h1_m15_raw_bar_receipts"] = []
    result = _run(report, frozen)
    assert not result["source_only_events"][0]["source_bar_groups"][
        "pre_c2_h1_m15_raw_bar_receipts"
    ]
    assert not result["source_only_events"][0]["source_complete"]


def test_no_positive_sampling_and_frozen_counts_are_mandatory():
    report, frozen = _fixture()
    report["stage_counts"][STAGE] = 2
    frozen["market_rows"]["EURJPY"]["stage_counts"][STAGE] = 2
    with pytest.raises(ValueError, match="missing a structural precursor"):
        _run(report, frozen)


def test_caller_author_claim_or_pnl_claim_cannot_be_promoted():
    report, frozen = _fixture()
    report["examples_by_stage"][STAGE][0]["A_rule_complete"] = True
    with pytest.raises(ValueError, match="synthetic shape"):
        _run(report, frozen)
    report, frozen = _fixture()
    report["pnl_evaluated"] = True
    with pytest.raises(ValueError, match="PnL"):
        _run(report, frozen)
