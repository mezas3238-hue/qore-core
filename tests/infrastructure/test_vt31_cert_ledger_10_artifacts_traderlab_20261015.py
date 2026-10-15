"""Ten real qualitative artifacts registry, no fabricated methods/COG cert."""
from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.vt31_cert_ledger_10_artifacts_traderlab_20261015 import (
    certify_extra_cognitive_parity,
)
from scripts.vt31_original_cog_trader_lab_fast_forward_20261015 import (
    run_original_vt31_traderlab_timewarp,
)
from scripts.vt31_original_cog_traderlab_32x_long_short_20261015 import (
    bidirectional_dossier,
)
from scripts.vt31_qualitative_method_cog_certificate_decision_20261015 import (
    adjudicate_qualitative_certification,
)
from tests.infrastructure.test_vt31_qualitative_method_cog_certificate_decision_20261015 import (
    fake_review_only_fixtures,
)


def _inputs():
    old=adjudicate_qualitative_certification(fake_review_only_fixtures())
    return old, run_original_vt31_traderlab_timewarp(), bidirectional_dossier()


def test_ten_cases_adds_semantic_positive_without_certifying():
    a,b,c=_inputs()
    before_method=deepcopy(a["methodology"]["missing_necessary_conditions"])
    before_cog=deepcopy(a["cognition"]["missing_necessary_conditions"])
    p=certify_extra_cognitive_parity(a,b,c)
    assert p["all_verified_artifact_count"]==10
    assert p["cognitive_acceleration_evidence"][
        "all_closed_M1_asof_and_trace_hashes_equal"
    ] is True
    assert p["cognitive_acceleration_evidence"]["real_CPU_speedup_proven"] is False
    assert p["methodology"]["missing_necessary_conditions"]==before_method
    assert p["cognition"]["missing_necessary_conditions"]==before_cog
    assert p["methodology"]["decision"]=="PENDIENTE"
    assert p["cognition"]["decision"]=="PENDIENTE"
    assert not p["overall_method_cognitive_certified"]
    assert p["economic_profit_pf_dd_sortino_sharpe"] is None
    assert p["broker_orders"]==p["trader_lot_sizing"]==0
    assert not p["live_authorized"]


def test_source_timelines_with_forged_32x_parity_are_rejected():
    a,b,c=_inputs()
    invalid=deepcopy(c)
    invalid["cases"][0]["ff_canonical_source_and_trace_identical"]=False
    with pytest.raises(ValueError,match="TRADERLAB_24_CASE_SOURCE_OR_COG_TRACE_DRIFT"):
        certify_extra_cognitive_parity(a,b,invalid)


def test_wait_without_mss_cannot_be_relabelled_as_long():
    a,b,c=_inputs()
    invalid=deepcopy(c)
    candidate=next(x for x in invalid["cases"] if x["counterfactual_change_only_last_close"])
    candidate["original_cog_trace_before_and_after"][1]["action"]="LONG"
    with pytest.raises(ValueError,match="TRADERLAB_24_CASE_INVALID_MSS_NOT_ABSTAINED"):
        certify_extra_cognitive_parity(a,b,invalid)


def test_short_original_wrong_blob_fails_closed():
    a,b,c=_inputs()
    invalid=deepcopy(b)
    invalid["cog_original_sha"]["git_blob_sha1"]="0"*40
    with pytest.raises(ValueError,match="TRADERLAB_COG_G3_ORIGINAL_BLOB_MISMATCH"):
        certify_extra_cognitive_parity(a,invalid,c)


def test_two_approved_pr_reviews_do_not_forge_cog_and_ops_independent_roles():
    example=fake_review_only_fixtures()
    example["gh_reviews"]=[
        {"state":"APPROVED","user":{"login":"approver-one"}},
        {"state":"APPROVED","user":{"login":"approver-two"}},
    ]
    original=adjudicate_qualitative_certification(example)
    b=run_original_vt31_traderlab_timewarp()
    c=bidirectional_dossier()
    p=certify_extra_cognitive_parity(original,b,c)
    assert p["g3_governance"][
        "actual_distinct_cog_ops_role_signatures_verified"
    ] is False
    assert not p["overall_method_cognitive_certified"]
