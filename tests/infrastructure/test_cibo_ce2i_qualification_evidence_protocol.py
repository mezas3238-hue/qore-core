from __future__ import annotations

from hashlib import sha256

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationStatus,
    run_phase20d_v2_qualification,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_readiness import (
    assess_phase20d_qualification_readiness,
)
from qore.infrastructure.cibo_ce2i_qualification_evidence_protocol import (
    require_qualification_evidence_book,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def test_forward_book_still_satisfies_structural_qualification_contract() -> None:
    book = VersionedPhase20ForwardEvidenceBook(generation=0)
    accepted = require_qualification_evidence_book(
        book,
        context="test-forward",
    )
    assert accepted is book


def test_historical_replay_book_enters_same_math_without_type_impersonation() -> None:
    book = VersionedPhase22HistoricalReplayEvidenceBook(
        generation=0,
        amendment_sha256=_sha("amendment"),
        decisions=(),
        outcomes=(),
    )
    accepted = require_qualification_evidence_book(
        book,
        context="test-replay",
    )
    assert accepted is book

    policy = VersionedPhase20ForwardPolicyBook(
        generation=0,
        decisions=(),
    )
    readiness = assess_phase20d_qualification_readiness(
        evidence_book=book,
        policy_book=policy,
    )
    assert readiness.ready is False

    report = run_phase20d_v2_qualification(
        evidence_book=book,
        policy_book=policy,
    )
    assert report.status is Phase20QualificationStatus.NOT_READY
