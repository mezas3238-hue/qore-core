from __future__ import annotations

from pathlib import Path

from qore.infrastructure.cibo_phase22_v4_chronological_execution import (
    V4_SOURCE_RECEIPT,
)
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID
from qore.infrastructure.cibo_phase22_v4_historical_policy_replay import (
    Phase22HistoricalPolicyDecisionRecord,
)
from qore.infrastructure.cibo_phase22_v4_historical_regime import (
    PHASE22_HISTORICAL_REGIME_ADAPTER_ID,
)
from qore.infrastructure.cibo_phase22_v4_source_receipt import (
    load_phase22_v4_source_receipt,
)


def test_v4_closure_surface_is_bound_to_v4_source_receipt() -> None:
    receipt = load_phase22_v4_source_receipt(
        Path("docs/research/CIBO-PHASE22-V4-SOURCE-RECEIPT.json")
    )

    assert V4_SOURCE_RECEIPT.fingerprint() == receipt.fingerprint()
    assert receipt.candidate_id == V4_CANDIDATE_ID
    assert receipt.corpus_git_sha == "98eb0d453b45a996cce142aa0b4460e8333fffec"
    assert PHASE22_HISTORICAL_REGIME_ADAPTER_ID.startswith(
        "CIBO_PHASE22_V4_"
    )
    assert Phase22HistoricalPolicyDecisionRecord.__name__ == (
        "Phase22HistoricalPolicyDecisionRecord"
    )


def test_v4_closure_code_has_no_v3_identity_dependency() -> None:
    paths = (
        Path("src/qore/infrastructure/cibo_phase22_v4_execution_inputs.py"),
        Path("src/qore/infrastructure/cibo_phase22_v4_chronological_replay_plan.py"),
        Path("src/qore/infrastructure/cibo_phase22_v4_historical_policy_replay.py"),
        Path("src/qore/infrastructure/cibo_phase22_v4_historical_replay_sealing.py"),
        Path("src/qore/infrastructure/cibo_phase22_v4_chronological_execution.py"),
        Path("src/qore/infrastructure/cibo_phase22_v4_historical_regime.py"),
        Path("src/qore/infrastructure/cibo_phase22_v4_execution_closure.py"),
        Path("scripts/cibo_phase22_v4_execution_closure.py"),
    )
    forbidden = (
        "cibo_phase22_v3",
        "Phase22V3",
        "PHASE22_V3",
        "phase22-v3",
        "NEXT_CANDIDATE_ID",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source, (path, token)
