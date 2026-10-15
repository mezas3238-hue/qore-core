"""A/B per-field lineage negative cases. All fixtures are synthetic by design."""
from __future__ import annotations

import hashlib
import json
from datetime import timedelta

import pytest
from test_vt08_cognitive_5m_consumed_gate_v1 import T0, _snapshot

from qore.infrastructure.trader_lab.vt08_b_situation_field_source_audit_v1 import (
    verify_all_situation_field_receipts,
)
from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import CAUSAL_FIELDS

RAW = "f" * 64


def _bundle():
    situation = _snapshot()
    clock = T0.isoformat()
    started = (T0 - timedelta(minutes=3)).isoformat()
    body: dict[str, object] = {
        "profile": "M3",
        "source_raw_sha256": RAW,
        "opened_at_utc": started,
        "closed_at_utc": clock,
        "ohlc": ("100", "101", "99", "100"),
    }
    bar_id = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    bar: dict[str, object] = {
        **body,
        "source_bar_id": bar_id,
        "available_at_utc": clock,
        "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
    }
    values = situation.payload()
    proofs: dict[str, dict[str, object]] = {
        name: {
            "value_sha256": hashlib.sha256(
                json.dumps(
                    values[name], sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest(),
            "semantic_class": "D_UNSPECIFIED",
            "source_rule_ref": "UNRESOLVED_SOURCE_AUTHOR",
            "source_bar_ids": [bar_id],
        }
        for name in CAUSAL_FIELDS
    }
    return situation, proofs, {bar_id: bar}


def _check(situation, proofs, catalog):
    return verify_all_situation_field_receipts(
        situation, proofs, catalog, pinned_raw_shas=frozenset((RAW,))
    )


def test_complete_temporal_binding_never_auto_certifies_semantics() -> None:
    situation, proofs, catalog = _bundle()
    outcome = _check(situation, proofs, catalog)
    assert outcome.verified_field_clocks == len(CAUSAL_FIELDS)
    assert outcome.raw_bars_referenced == 1
    assert outcome.causal_values_and_clocks_bound
    assert len(outcome.unspecified_semantics_fields) == len(CAUSAL_FIELDS)
    assert not outcome.source_semantics_certified
    assert not outcome.economic_certified
    assert not outcome.order_authorized


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "missing/extra"),
        ("unknown", "missing/extra"),
        ("value_drift", "fingerprint drift"),
        ("unknown_id", "source bar ID"),
        ("wrong_feed", "outside pinned raw feed"),
        ("future", "bar interval invalid"),
        ("stale_cutoff", "bar interval invalid"),
        ("duplicate", "duplicated field bars"),
        ("unclassified", "semantic classification"),
        ("no_ref", "rule reference"),
        ("missing_bars", "bar IDs absent"),
        ("bar_ohlc_tamper", "source bar digest invalid"),
        ("bar_profile_tamper", "bar interval invalid"),
    ],
)
def test_field_provenance_fails_closed_on_single_bad_attribute(
    mutation: str, message: str
) -> None:
    situation, proofs, catalog = _bundle()
    if mutation == "missing":
        proofs.pop("bias_state")
    elif mutation == "unknown":
        proofs["made_up_state"] = proofs["bias_state"]
    elif mutation == "value_drift":
        proofs["bias_state"]["value_sha256"] = "b" * 64
    elif mutation == "unknown_id":
        proofs["bias_state"]["source_bar_ids"] = ["b" * 64]
    elif mutation == "wrong_feed":
        next(iter(catalog.values()))["source_raw_sha256"] = "b" * 64
    elif mutation == "future":
        bar = next(iter(catalog.values()))
        bar["closed_at_utc"] = (T0 + timedelta(minutes=3)).isoformat()
        bar["available_at_utc"] = (T0 + timedelta(minutes=3)).isoformat()
    elif mutation == "stale_cutoff":
        bar = next(iter(catalog.values()))
        bar["closed_at_utc"] = (T0 - timedelta(minutes=3)).isoformat()
        bar["available_at_utc"] = (T0 - timedelta(minutes=3)).isoformat()
    elif mutation == "duplicate":
        bar_id = next(iter(catalog))
        proofs["bias_state"]["source_bar_ids"] = [bar_id, bar_id]
    elif mutation == "unclassified":
        proofs["bias_state"]["semantic_class"] = "CERTIFIED"
    elif mutation == "no_ref":
        proofs["bias_state"]["source_rule_ref"] = ""
    elif mutation == "missing_bars":
        proofs["bias_state"]["source_bar_ids"] = []
    elif mutation == "bar_ohlc_tamper":
        next(iter(catalog.values()))["ohlc"] = ("100", "103", "99", "100")
    elif mutation == "bar_profile_tamper":
        next(iter(catalog.values()))["profile"] = "M15"
    with pytest.raises(ValueError, match=message):
        _check(situation, proofs, catalog)
