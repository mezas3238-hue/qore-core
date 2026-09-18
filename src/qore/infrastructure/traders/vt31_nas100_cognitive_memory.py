"""Composite memory facade for VT31_NAS100_SPECIALIST_R1.

The specialist's mind is split into three explicit stores:

1. Long-Term Semantic Memory
   Stable NAS100 market knowledge distilled from consumed CIBO evidence.
2. Episodic/Research Memory
   What VT31 development learned, rejected, and still considers unresolved.
3. Working Memory
   Ephemeral causal state of the current market, provided per decision.

Only the first two are embedded persistent knowledge. Working memory is never
persisted in this module and never contains historical outcomes.
"""
from __future__ import annotations

import hashlib
import json

from qore.infrastructure.traders.vt31_nas100_episodic_memory import (
    episodic_memory_fingerprint,
    episodic_memory_payload,
    validate_episodic_memory,
)
from qore.infrastructure.traders.vt31_nas100_long_term_memory import (
    long_term_memory_fingerprint,
    long_term_memory_payload,
    validate_long_term_memory,
)

SCHEMA = "qore.vt31.nas100.cognitive_memory_bundle.v2"
MARKET = "NAS100"


def memory_payload() -> dict[str, object]:
    """Return the persistent two-store brain plus working-memory contract."""
    return {
        "schema": SCHEMA,
        "market": MARKET,
        "mind_model": "THREE_MEMORY_ARCHITECTURE",
        "long_term_memory": long_term_memory_payload(),
        "episodic_research_memory": episodic_memory_payload(),
        "working_memory_contract": {
            "schema": "qore.vt31.nas100.working_memory.v1",
            "memory_class": "WORKING_CAUSAL_RUNTIME",
            "persistent": False,
            "rebuilt_each_decision": True,
            "historical_outcome_labels_allowed": False,
        },
        "fingerprints": {
            "long_term": long_term_memory_fingerprint(),
            "episodic_research": episodic_memory_fingerprint(),
        },
        "runtime_guards": {
            "external_cibo_runtime_dependency": False,
            "date_level_lookup_allowed": False,
            "future_bar_lookup_allowed": False,
            "post_outcome_lookup_allowed": False,
            "persistent_memory_mutable_at_runtime": False,
        },
    }


def memory_fingerprint() -> str:
    encoded = json.dumps(
        memory_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_memory() -> None:
    validate_long_term_memory()
    validate_episodic_memory()
    payload = memory_payload()
    guards = payload["runtime_guards"]
    assert isinstance(guards, dict)
    assert guards["external_cibo_runtime_dependency"] is False
    assert guards["date_level_lookup_allowed"] is False
    assert guards["future_bar_lookup_allowed"] is False
    assert guards["post_outcome_lookup_allowed"] is False
    assert guards["persistent_memory_mutable_at_runtime"] is False
    contract = payload["working_memory_contract"]
    assert isinstance(contract, dict)
    assert contract["persistent"] is False
    assert contract["rebuilt_each_decision"] is True
    assert contract["historical_outcome_labels_allowed"] is False
    assert len(memory_fingerprint()) == 64
