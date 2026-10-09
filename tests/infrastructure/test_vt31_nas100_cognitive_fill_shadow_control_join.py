"""Pure data-join tests; never turn hindsight into VT31 fill policy."""
from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.vt31_nas100_cognitive_fill_shadow_control_join_v1 import (
    BASE_ID,
    FROZEN_SOURCE_SHA,
    _observed_metrics,
    audit,
)


def fixture():
    trades = [
        {"signal_at": "2026-01-05T15:10:00+00:00", "r_multiple": "2",
         "entry_family": "fair-value-gap", "side": "long"},
        {"signal_at": "2026-01-06T15:10:00+00:00", "r_multiple": "-1",
         "entry_family": "breaker", "side": "short"},
    ]
    baseline = {
        "base_id": BASE_ID,
        "current_stack": {
            "lab_control_alias": "COMP006_CONTROL",
            "variants": {"COMP006_CONTROL": {
                "trade_count": 2,
                "candidate_rows": trades,
                "stress_0_05r": {"sample": 2},
            }},
        },
    }
    shadow = {
        "schema": "qore.vt31.nas100.3y_causal_fill_time_shadow.v1",
        "base_id": BASE_ID,
        "source_sha256": FROZEN_SOURCE_SHA,
        "governance": {
            "runtime_action_altered": False,
            "fill_cancel_authority": False,
            "fresh_holdout_opened": False,
        },
        "realized_fill_opportunities": 2,
        "per_fill_ledger": [
            {
                "signal_at": trades[0]["signal_at"],
                "structural_status": "terminal",
                "structural_r_multiple": "2.5",
                "candidate_fill_accepted": True,
                "comp008_shadow_fill_accepted": True,
                "revalidated_reasoning_action": "EXECUTE",
                "entry_mandatory_blockers": [],
                "has_zero_preterminal_post_entry_m1": False,
            },
            {
                "signal_at": trades[1]["signal_at"],
                "structural_status": "terminal",
                "structural_r_multiple": "-1",
                "candidate_fill_accepted": False,
                "comp008_shadow_fill_accepted": False,
                "revalidated_reasoning_action": "ABSTAIN",
                "entry_mandatory_blockers": [],
                "has_zero_preterminal_post_entry_m1": True,
            },
        ],
    }
    return baseline, shadow


def test_shadow_maps_the_original_admission_identity_without_future_authority():
    baseline, shadow = fixture()
    joined = audit(baseline, shadow)
    assert joined["control_admitted_trade_count"] == 2
    assert joined["shadow_rejected_admitted_trades"] == 1
    assert joined["rejected_admitted_raw_nonwinners"] == 1
    assert joined["rejected_admitted_raw_winners"] == 0
    assert joined["zero_postfill_admitted_trades"] == 1
    assert joined["zero_postfill_rejected_in_shadow"] == 1
    assert joined["naive_delete_rejected_trades_diagnostic"]["trade_count"] == 1
    assert joined["retrospective_control_metrics_recomputed"]["trade_count"] == 2
    assert joined["governance"]["source_execution_altered"] is False
    assert joined["governance"]["naive_removal_not_real_counterfactual"] is True


def test_recomputed_stressed_r_includes_cost_and_chronological_drawdown():
    data = [
        {"signal_at": "2026-01-05T15:00:00+00:00", "r_multiple": "2"},
        {"signal_at": "2026-01-06T15:00:00+00:00", "r_multiple": "-1"},
    ]
    m = _observed_metrics(data)
    assert m["raw_total_r_minus_0_05r_cost_each"] == "0.90"
    assert m["observed_max_drawdown_r"] == "1.05"
    assert m["stressed_mean_r"] == "0.45"
    assert m["longest_consecutive_negative_stressed_trades"] == 1


def test_fails_closed_on_missing_or_repeated_control_identity():
    base, shadow = fixture()
    bad = deepcopy(shadow)
    bad["per_fill_ledger"][1]["signal_at"] = "2026-01-07T15:10:00+00:00"
    with pytest.raises(ValueError, match="missing fill-time reasoning"):
        audit(base, bad)

    repeated = deepcopy(shadow)
    repeated["per_fill_ledger"][1]["signal_at"] = (
        repeated["per_fill_ledger"][0]["signal_at"]
    )
    with pytest.raises(ValueError, match="duplicate fill candidate"):
        audit(base, repeated)


def test_refuses_noncanonical_or_trade_altering_shadow():
    base, shadow = fixture()
    bad = deepcopy(shadow)
    bad["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        audit(base, bad)
    bad = deepcopy(shadow)
    bad["governance"]["runtime_action_altered"] = True
    with pytest.raises(ValueError, match="shadow did not preserve"):
        audit(base, bad)
