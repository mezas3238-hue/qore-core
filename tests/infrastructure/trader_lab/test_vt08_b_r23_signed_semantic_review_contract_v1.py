"""R23 adversarial dual-signature source review tests; all ballots synthetic."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import qore.infrastructure.trader_lab.vt08_b_r23_signed_semantic_review_contract_v1 as r23

M = "EURJPY"
T = datetime(2026, 4, 6, 12, tzinfo=UTC)
ID = "c" * 64
R18 = "d" * 64
R19 = "e" * 64


def _packet():
    return {
        "case_id_sha256": ID,
        "market": M,
        "c2_opened_at_utc": (T - timedelta(minutes=30)).isoformat(),
        "c3_opened_at_utc": T.isoformat(),
        "cisd_closed_at_utc": (T-timedelta(minutes=3)).isoformat(),
        "human_rater_A_source_signoff": None,
        "human_rater_B_independent_signoff": None,
        "source_complete": False,
        "cognitive_ready": False,
        "orders_authorized": False,
    }


def _source(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(r23, "MARKET_EXPECTED", {M: (1, R18)})
    monkeypatch.setattr(r23, "PINNED_R19_REPORT_DIGESTS", {M: R19})
    monkeypatch.setattr(r23, "digest_r19", lambda _: R19)
    return {
        "schema": r23.R19_SCHEMA, "market": M, "seed": r23.SEED,
        "original_r18_sha256": R18, "original_r18_cases": 1,
        "rater_A_signed": 0, "rater_B_signed": 0,
        "source_complete_entries": 0, "cognitive_admissions": 0,
        "broker_fills": 0, "holdout_7y_accessed": False, "sizing_used": False,
        "selected_source_only_cases": 1,
        "review_packets": [_packet()],
    }


def _finding(status: str = "SUPPORTED") -> dict[str, object]:
    return {
        "disposition": status,
        "author_source_url":
            "https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/",
        "author_section": "The Ideal Candle 2 Formation",
        "source_bar_ids": ["f"*64],
        "latest_source_available_at_utc": (
            T - timedelta(minutes=3)
        ).isoformat(),
        "reason": "Original source says protected swing must be confirmed.",
    }


def _signed(role: str, private: Ed25519PrivateKey, state: str = "SUPPORTED"):
    ballot: dict[str, object] = {
        "schema": r23.BALLOT_SCHEMA, "market": M,
        "case_id_sha256": ID,
        "r19_source_report_sha256": R19,
        "reviewer_role": role,
        "reviewer_key_id": "A" if role == "A_METHOD" else "B",
        "reviewed_at_utc": (T + timedelta(hours=1)).isoformat(),
        "findings": {k: _finding(state) for k in r23.CLAIMS},
        "ed25519_signature": "",
    }
    ballot["ed25519_signature"] = private.sign(r23._ballot_digest(ballot)).hex()
    return ballot


def _two_keys(monkeypatch: pytest.MonkeyPatch):
    a = Ed25519PrivateKey.generate()
    b = Ed25519PrivateKey.generate()
    def pub(p: Ed25519PrivateKey):
        return p.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()
    monkeypatch.setattr(r23, "APPROVED_RATER_ED25519_PUBLIC_KEYS", {
        "A_METHOD": {"A": pub(a)},
        "B_INDEPENDENT": {"B": pub(b)},
    })
    return a, b


def test_without_governance_keys_every_authentic_packet_stays_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = _source(monkeypatch)
    report = r23.audit_dual_source_review(src, market=M, submitted_ballots=[])
    assert report["original_preregistered_cases"] == 1
    assert report["approved_rater_keys_A"] == 0
    assert report["approved_rater_keys_B"] == 0
    assert report["source_review_status_counts"]["WAIT_UNREVIEWED"] == 1
    assert report["author_complete_entries"] == report["real_cognitive_admissions"] == 0
    assert report["broker_fills"] == 0


def test_signature_from_nonapproved_signer_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = _source(monkeypatch)
    evil = Ed25519PrivateKey.generate()
    with pytest.raises(ValueError, match="NOT APPROVED"):
        r23.audit_dual_source_review(
            src, market=M, submitted_ballots=[_signed("A_METHOD", evil)],
        )


def test_two_independent_valid_signed_reviews_are_only_review_not_trade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = _source(monkeypatch)
    a, b = _two_keys(monkeypatch)
    report = r23.audit_dual_source_review(
        src, market=M,
        submitted_ballots=[_signed("A_METHOD", a), _signed("B_INDEPENDENT", b)],
    )
    assert report["source_review_status_counts"][
        "DUAL_SOURCE_REVIEW_CONSISTENT_ONLY"
    ] == 1
    assert not report["case_review_register"][0]["TTrades_methodology_source_complete"]
    assert not report["case_review_register"][0]["cognitive_admission_authorized"]
    assert not report["case_review_register"][0]["broker_orders_authorized"]
    assert report["author_complete_entries"] == report["broker_fills"] == 0


def test_one_signature_never_counts_as_dual_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = _source(monkeypatch)
    a, _ = _two_keys(monkeypatch)
    out = r23.audit_dual_source_review(
        src, market=M, submitted_ballots=[_signed("A_METHOD", a)],
    )
    assert out["source_review_status_counts"]["WAIT_SECOND_REVIEWER"] == 1


@pytest.mark.parametrize(
    ("status", "wanted"),
    [
        ("D_UNSPECIFIED", "WAIT_DISAGREEMENT_OR_D"),
        ("REJECTED", "SOURCE_REVIEW_REJECTED"),
    ],
)
def test_source_disagreement_or_rejection_never_grants_entry(
    monkeypatch: pytest.MonkeyPatch, status: str, wanted: str,
) -> None:
    src = _source(monkeypatch)
    a, b = _two_keys(monkeypatch)
    out = r23.audit_dual_source_review(
        src, market=M, submitted_ballots=[
            _signed("A_METHOD", a, status),
            _signed("B_INDEPENDENT", b),
        ],
    )
    assert out["source_review_status_counts"][wanted] == 1
    assert out["author_complete_entries"] == 0


@pytest.mark.parametrize("attack", [
    "altered_signature", "future_source", "foreign_rule", "missing_claim",
    "missing_source_id", "weak_rationale", "changed_source_sha",
    "changed_market", "changed_identity", "wrong_role", "duplicate",
    "unsigned_field_injection", "fake_authority", "tampered_sample",
    "naive_time", "unknown_claim_status",
])
def test_forgeries_and_temporal_changes_fail_closed(
    monkeypatch: pytest.MonkeyPatch, attack: str,
) -> None:
    src = _source(monkeypatch)
    a, b = _two_keys(monkeypatch)
    ballot = _signed("A_METHOD", a)
    if attack == "altered_signature":
        ballot["findings"]["relevant_swing_selection"]["reason"] = (
            "Changed rationale from signed primary source attribution"
        )
    elif attack == "future_source":
        ballot["findings"]["relevant_swing_selection"][
            "latest_source_available_at_utc"
        ] = (T+timedelta(minutes=3)).isoformat()
    elif attack == "foreign_rule":
        ballot["findings"]["relevant_swing_selection"][
            "author_source_url"
        ] = "https://invalid-not-ttrades.com"
    elif attack == "missing_claim":
        ballot["findings"].pop("important_poi_selected_before_cisd")
    elif attack == "missing_source_id":
        ballot["findings"]["breaker_source_sequence"]["source_bar_ids"] = []
    elif attack == "weak_rationale":
        ballot["findings"]["breaker_source_sequence"]["reason"] = "ok"
    elif attack == "changed_source_sha":
        ballot["r19_source_report_sha256"] = "9"*64
    elif attack == "changed_market":
        ballot["market"] = "USDCAD"
    elif attack == "changed_identity":
        ballot["case_id_sha256"] = "f"*64
    elif attack == "wrong_role":
        ballot["reviewer_role"] = "C_OTHER"
    elif attack == "duplicate":
        pass
    elif attack == "unsigned_field_injection":
        ballot["operational_authority"] = True
    elif attack == "fake_authority":
        src["review_packets"][0]["orders_authorized"] = True
    elif attack == "tampered_sample":
        src["seed"] = "choose-profitable"
    elif attack == "naive_time":
        ballot["reviewed_at_utc"] = "2026-04-06T12:00:00"
    elif attack == "unknown_claim_status":
        ballot["findings"]["relevant_swing_selection"]["disposition"] = "WINNER"
    second = (
        [deepcopy(ballot)] if attack == "duplicate" else []
    )
    with pytest.raises(ValueError):
        r23.audit_dual_source_review(
            src, market=M, submitted_ballots=[ballot, *second],
        )


def test_same_public_key_under_two_different_role_aliases_cannot_sign_both(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = _source(monkeypatch)
    a, _ = _two_keys(monkeypatch)
    raw_pub = r23.APPROVED_RATER_ED25519_PUBLIC_KEYS["A_METHOD"]["A"]
    monkeypatch.setitem(
        r23.APPROVED_RATER_ED25519_PUBLIC_KEYS["B_INDEPENDENT"],
        "B", raw_pub,
    )
    with pytest.raises(ValueError, match="same signer"):
        r23.audit_dual_source_review(
            src, market=M,
            submitted_ballots=[
                _signed("A_METHOD", a),
                _signed("B_INDEPENDENT", a),
            ],
        )


def test_same_rater_cannot_overwrite_first_vote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = _source(monkeypatch)
    a, _ = _two_keys(monkeypatch)
    ballot = _signed("A_METHOD", a)
    with pytest.raises(ValueError, match="duplicate review"):
        r23.audit_dual_source_review(
            src, market=M, submitted_ballots=[ballot, deepcopy(ballot)],
        )
