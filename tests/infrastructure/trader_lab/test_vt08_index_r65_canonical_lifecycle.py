from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r64_canonical_economic_binding as r64,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r65_canonical_lifecycle as r65,
)
from qore.infrastructure.traders import vt08_index_specialist_contract as specialist


def test_r65_preserves_frozen_specialist_identity() -> None:
    assert specialist.CANDIDATE_ID == (
        "VT08_INDEX_R58_EXACT_R47_DISTRIBUTED_CAUSAL_RISK_001"
    )
    assert specialist.MARKETS == ("NAS100", "SP500", "US30")
    assert specialist.TIMEFRAMES == ("M15", "H4")


def test_r65_policies_predate_typed_economic_observation() -> None:
    assert r65.POLICY_REGISTERED_AT < r64.PROCESS_EVIDENCE_AT
    assert r65.PLAN_CREATED_AT < r64.PROCESS_EVIDENCE_AT


def test_r65_reuses_core_bootstrap_contract() -> None:
    assert r65.BOOTSTRAP_BLOCK_LENGTH == 5
    assert r65.BOOTSTRAP_RESAMPLES == 10_000
    assert r65.BOOTSTRAP_SEED == 20_260_919
    assert r65.MIN_CANONICAL_SAMPLE == 1_000
