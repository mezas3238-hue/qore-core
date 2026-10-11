"""Independently authored B contract tests; NO Architect A producer imports.

All source rules below are synthetic and D. The only A fixture uses a very
short actual source excerpt to test citation-format checks; NOT source signoff.
"""
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab import (
    vt08_5m_b_methodology_spec_boundary_v1 as v,
)

T0 = datetime(2026, 1, 5, 12, tzinfo=UTC)


def clock(delta: int = 0) -> str:
    return (T0 + timedelta(minutes=delta)).isoformat()


def proof(closed: int, available: int) -> dict[str, object]:
    return {
        "source_bar_id": f"synthetic-m15-{closed}",
        "source_bar_sha256": "a" * 64,
        "closed_at": clock(closed),
        "available_at": clock(available),
    }


def spec() -> dict[str, object]:
    rules = []
    for fam in v.FAMILIES:
        for role in v.ROLES:
            row: dict[str, object] = {
                "id": f"{fam}-{role}",
                "family": fam,
                "role": role,
                "tag": "D",
                "ambiguity": "Unresolved: no source-author valid POI/swing/priority",
                "required_closed_inputs": ["source_m15_closed_at"],
            }
            if role == "POI":
                row["poi_allowed_for_this_family"] = ["FVG", "HIGH"]
            rules.append(row)
    return {
        "schema": "qore.vt08.a_b_methodology_text_spec.proposed.v1",
        "producer_role": "ARCHITECT_A_SOURCE",
        "verifier_role": "ARCHITECT_B_INDEPENDENT",
        "jointly_approved": False,
        "cognition_authorized": False,
        "rules": rules,
    }


def event(
    family: str = "C2_COMPLETED", *,
    against: bool = False,
) -> dict[str, object]:
    # Intent: C2 opens at T0; prior swing and its POI strictly precede T0.
    out: dict[str, object] = {
        "family": family,
        "c2_opened_at": clock(),
        "c2_closed_at": clock(240),
        "decision_at": clock(240),
        "hypothetical_entry_at": clock(255),
        "side": "long",
        "reference_swing": {
            "side": "long",
            "identified_at": clock(-20),
            "source_proof": proof(-30, -25),
            "poi_proof": proof(-60, -55),
            "pre_c2_swing_regime_independently_attested": False,
        },
        "poi": {
            "type": "HIGH",
            "source_proof": proof(-60, -55),
        },
        "cisd": {
            "confirmation": "M15_CLOSED",
            "source_proof": proof(225, 240),
        },
        "protected_swing": {
            "confirmation": "M15_CLOSED",
            "source_proof": proof(225, 240),
        },
        "c2_candle": {
            "open": "102" if against else "100",
            "close": "100" if against else "102",
            "high": "104",
            "low": "98",
        },
        "eq_basis": (
            "C2_CLOSE_TO_EXTREME_AGAINST_SWING" if against
            else "C2_FULL_WICK_TO_WICK_WITH_SWING"
        ),
        "research_only": True,
        "order_authorized": False,
        "proxy_as_real_density_estimate": False,
        "c2_dual_sweep": False,
        "dual_sweep_adjudicated": False,
        "body_engulf_strong_proxy": False,
    }
    if family == "C3_CLOSURE_TO_C4":
        out.update({
            "decision_at": clock(480),
            "hypothetical_entry_at": clock(495),
            "c3_closed_at": clock(480),
            "cisd": {
                "confirmation": "M15_CLOSED",
                "source_proof": proof(465, 480),
            },
            "protected_swing": {
                "confirmation": "M15_CLOSED",
                "source_proof": proof(465, 480),
            },
            "eq_basis": "C3_FULL_WICK_TO_WICK_AFTER_CLOSURE",
            "c4_first_m15_observed": False,
        })
    elif family == "C3_CONTINUATION_FROM_C2":
        out["eq_basis"] = "C3_FULL_WICK_TO_WICK_AFTER_CLOSURE"
    return out


def test_text_only_spec_requires_all_family_roles_and_tag_D_is_not_A() -> None:
    manifest = spec()
    declared = v.validate_text_only_spec(manifest)
    assert len(declared) == 3
    assert all(set(x) == set(v.ROLES) for x in declared.values())
    verdict = v.verify_causal_event(event(), manifest)
    assert verdict.chronology_valid
    assert not verdict.source_complete and not verdict.cognitive_ready
    assert not verdict.order_authorized
    assert len([r for r in verdict.rule_status if r[1] == "D"]) == 6
    assert "B_SOURCE:C2_COMPLETED:EQ_NOT_A" in verdict.blockers
    assert "B_SOURCE:JOINT_MANIFEST_NOT_SIGNED" in verdict.blockers


def test_A_primary_source_requires_real_citation_and_verbatim_quote() -> None:
    manifest = spec()
    rule = manifest["rules"][2]
    assert rule["role"] == "EQ"
    rule.update({
        "tag": "A",
        "source_url": "https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/",
        "source_quote": "The key is knowing which range to measure.",
        "source_section": "Introduction",
        "source_published_date": "2026-10-10",
    })
    assert v.validate_text_only_spec(manifest)["C2_COMPLETED"]["EQ"]["tag"] == "A"
    for bad in ("https://fake.example/source", "http://ttrades.com/"):
        wrong = deepcopy(manifest)
        wrong["rules"][2]["source_url"] = bad
        with pytest.raises(v.BMethodologyBoundaryError, match="A must cite"):
            v.validate_text_only_spec(wrong)
    wrong = deepcopy(manifest)
    wrong["rules"][2]["source_quote"] = ""
    with pytest.raises(v.BMethodologyBoundaryError, match="A must cite"):
        v.validate_text_only_spec(wrong)


def test_missing_family_poi_or_mislabeled_C_rule_fails_closed() -> None:
    manifest = spec()
    manifest["rules"] = manifest["rules"][:-1]
    with pytest.raises(v.BMethodologyBoundaryError, match="all six"):
        v.validate_text_only_spec(manifest)
    manifest = spec()
    manifest["rules"][1]["tag"] = "C"
    with pytest.raises(v.BMethodologyBoundaryError, match="explicitly labeled"):
        v.validate_text_only_spec(manifest)


@pytest.mark.parametrize(("delta", "expected"), [
    (0, "identified ex-post"), (5, "identified ex-post"),
])
def test_expost_swing_during_or_after_C2_is_structural_lookahead(
    delta: int, expected: str,
) -> None:
    e = event(against=True)
    e["reference_swing"]["identified_at"] = clock(delta)
    with pytest.raises(v.BMethodologyBoundaryError, match=expected):
        v.verify_causal_event(e, spec())


@pytest.mark.parametrize(("edit", "expected"), [
    ("swing_source_future", "reference_swing"),
    ("swing_poi_future", "swing_poi"),
    ("cisd_after_entry", "cisd"),
    ("ps_at_entry", "protected_swing"),
    ("incorrect_c2_eq", "C2 full/wick EQ branch wrong"),
    ("unsourced_family_poi", "POI not sourced"),
    ("proxy_as_forecast", "proxy cannot estimate real density"),
])
def test_causal_failures_never_qualify_as_source_complete(
    edit: str, expected: str,
) -> None:
    e = event(against=True)
    if edit == "swing_source_future":
        e["reference_swing"]["source_proof"] = proof(0, 5)
    elif edit == "swing_poi_future":
        e["reference_swing"]["poi_proof"] = proof(-15, 0)
    elif edit == "cisd_after_entry":
        e["cisd"]["source_proof"] = proof(255, 270)
    elif edit == "ps_at_entry":
        e["protected_swing"]["source_proof"] = proof(240, 255)
    elif edit == "incorrect_c2_eq":
        e["eq_basis"] = "C2_FULL_WICK_TO_WICK_WITH_SWING"
    elif edit == "unsourced_family_poi":
        e["poi"]["type"] = "ORDER_BLOCK"
    else:
        e["proxy_as_real_density_estimate"] = True
    with pytest.raises(v.BMethodologyBoundaryError, match=expected):
        v.verify_causal_event(e, spec())


def test_valid_preC2_swing_boolean_does_not_become_source_proof_or_signature() -> None:
    e = event(against=True)
    first = v.verify_causal_event(e, spec())
    assert "B_SOURCE:PRE_C2_SWING_REGIME_NOT_ATTESTED" in first.blockers
    e["reference_swing"]["pre_c2_swing_regime_independently_attested"] = True
    later = v.verify_causal_event(e, spec())
    assert "B_SOURCE:PRE_C2_SWING_REGIME_NOT_ATTESTED" not in later.blockers
    assert not later.cognitive_ready and not later.source_complete
    assert "B_SOURCE:INDEPENDENT_SOURCE_ADJUDICATION_PENDING" in later.blockers


def test_C3_and_C4_two_clocks_and_PS_must_not_reach_future_M15() -> None:
    e = event("C3_CLOSURE_TO_C4")
    ok = v.verify_causal_event(e, spec())
    assert ok.chronology_valid and not ok.cognitive_ready
    too_early = deepcopy(e)
    too_early["decision_at"] = clock(465)
    with pytest.raises(v.BMethodologyBoundaryError, match="C3 closure cannot"):
        v.verify_causal_event(too_early, spec())
    future = deepcopy(e)
    future["protected_swing"]["source_proof"] = proof(480, 485)
    with pytest.raises(v.BMethodologyBoundaryError, match="not available at source decision"):
        v.verify_causal_event(future, spec())
    premature_c4 = deepcopy(e)
    premature_c4.update({
        "c4_first_m15_observed": True,
        "c4_first_m15_closed_at": clock(495),
    })
    with pytest.raises(v.BMethodologyBoundaryError, match="used before close"):
        v.verify_causal_event(premature_c4, spec())


def test_double_sweep_D_is_excluded_not_silently_classified() -> None:
    e = event("C3_CLOSURE_TO_C4")
    e["c2_dual_sweep"] = True
    e["dual_sweep_adjudicated"] = False
    verdict = v.verify_causal_event(e, spec())
    assert "B_SOURCE:C2_DUAL_SWEEP_UNADJUDICATED" in verdict.blockers


def test_body_engulf_36_must_be_qore_C_never_methodology_A() -> None:
    e = event("C3_CLOSURE_TO_C4")
    e["body_engulf_strong_proxy"] = True
    e["body_engulf_source_tag"] = "A"
    with pytest.raises(v.BMethodologyBoundaryError, match="C QORE"):
        v.verify_causal_event(e, spec())
    e["body_engulf_source_tag"] = "C_QORE_FULL_BODY_ENGULF_GEOMETRY_UNVERIFIED"
    verdict = v.verify_causal_event(e, spec())
    assert verdict.chronology_valid and not verdict.source_complete


def metrics() -> dict[str, object]:
    return {
        "c3_shapes": 294,
        "c4_owner": 213,
        "outside_qore_owner": 81,
        "c2_dual_sweep_unadjudicated": 105,
        "cisd_ps_m15_formal_proxy": 129,
        "qore_strict_full_body_engulf_geometry": 36,
        "source_confirmed_cisd_ps": 0,
        "executed_trades": 0,
        "proxy_density_extrapolation": None,
        "qore_body_engulf_rule_tag": "C",
        "body_engulf_source_verified": False,
        "dual_sweep_rule_tag": "D",
    }


def test_proxy_counts_separate_and_QORE_bucket_safely_labelled() -> None:
    report = v.audit_proxy_metrics(metrics())
    assert report["m15_CISD_PS_FORMAL_PROXY_NOT_DENSITY"] == 129
    assert report["source_confirmed_CISD_PS"] == 0
    assert report["QORE_FULL_BODY_ENGULF_GEOMETRY_C_UNVERIFIED"] == 36
    assert report["C2_DUAL_SWEEP_D_UNRESOLVED"] == 105
    assert report["source_complete"] == 0 and report["cognitive_ready"] == 0
    for key, bad in (
        ("proxy_density_extrapolation", 129),
        ("source_confirmed_cisd_ps", 129),
        ("qore_body_engulf_rule_tag", "A"),
        ("body_engulf_source_verified", True),
        ("dual_sweep_rule_tag", "A"),
    ):
        changed = metrics()
        changed[key] = bad
        with pytest.raises(v.BMethodologyBoundaryError):
            v.audit_proxy_metrics(changed)
