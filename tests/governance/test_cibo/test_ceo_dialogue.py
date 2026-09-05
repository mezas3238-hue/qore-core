from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from qore.governance.cibo.ceo_dialogue import (
    CiboCeoDialogue,
    CiboCeoDialogueResult,
    CiboCeoDialogueValidationError,
    CiboCeoMode,
)
from qore.infrastructure.cibo.contracts import CiboFunctionalAuthority
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 13, 0, tzinfo=UTC)
_DIALOGUE = CiboCeoDialogue()


@pytest.mark.parametrize(
    ("mode", "authority"),
    [
        (CiboCeoMode.EXPLAIN, CiboFunctionalAuthority.OPINION),
        (CiboCeoMode.ASK, CiboFunctionalAuthority.REQUEST),
        (CiboCeoMode.DOUBT, CiboFunctionalAuthority.OBSERVATION),
        (CiboCeoMode.COMPARE, CiboFunctionalAuthority.OPINION),
        (CiboCeoMode.OPINE, CiboFunctionalAuthority.OPINION),
        (CiboCeoMode.STATE_UNKNOWN, CiboFunctionalAuthority.OBSERVATION),
    ],
)
def test_each_mode_maps_to_correct_authority(
    mode: CiboCeoMode,
    authority: CiboFunctionalAuthority,
) -> None:
    result = _DIALOGUE.speak(
        mode,
        summary_code=f"summary.{mode.value}",
        reason_codes=("direction.review",),
        evidence_refs=(CiboEvidenceRef("evidence:direction"),),
        question_refs=(),
        spoken_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.authority is authority


def test_ask_grants_request_not_command() -> None:
    result = _DIALOGUE.speak(
        CiboCeoMode.ASK,
        summary_code="summary.clarify",
        reason_codes=("direction.ambiguous",),
        evidence_refs=(),
        question_refs=("question:direction",),
        spoken_at=_NOW,
    )
    assert isinstance(result, Success)
    dialogue = result.value
    assert dialogue.authority is CiboFunctionalAuthority.REQUEST
    for name in ("command", "execute", "dispatch", "order", "grant", "authorize"):
        assert not hasattr(dialogue, name)


def test_authority_never_above_request() -> None:
    for mode in CiboCeoMode:
        result = _DIALOGUE.speak(
            mode,
            summary_code=f"summary.{mode.value}",
            reason_codes=("direction.review",),
            evidence_refs=(),
            question_refs=(),
            spoken_at=_NOW,
        )
        assert isinstance(result, Success)
        assert result.value.authority in (
            CiboFunctionalAuthority.OBSERVATION,
            CiboFunctionalAuthority.OPINION,
            CiboFunctionalAuthority.REQUEST,
        )


def test_malformed_mode_returns_failure() -> None:
    result = _DIALOGUE.speak(
        cast(CiboCeoMode, "command"),
        summary_code="summary.x",
        reason_codes=("direction.review",),
        evidence_refs=(),
        question_refs=(),
        spoken_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboCeoDialogueValidationError)


def test_malformed_nested_evidence_ref_returns_failure() -> None:
    result = _DIALOGUE.speak(
        CiboCeoMode.EXPLAIN,
        summary_code="summary.x",
        reason_codes=("direction.review",),
        evidence_refs=cast(tuple[CiboEvidenceRef, ...], ("not-a-ref",)),
        question_refs=(),
        spoken_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboCeoDialogueValidationError)


def test_sensitive_substring_rejected() -> None:
    result = _DIALOGUE.speak(
        CiboCeoMode.EXPLAIN,
        summary_code="summary.secret",
        reason_codes=("direction.review",),
        evidence_refs=(),
        question_refs=(),
        spoken_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboCeoDialogueValidationError)


def test_mode_authority_mismatch_rejected_on_direct_construction() -> None:
    with pytest.raises(CiboCeoDialogueValidationError):
        CiboCeoDialogueResult(
            mode=CiboCeoMode.ASK,
            summary_code="summary.clarify",
            reason_codes=("direction.ambiguous",),
            evidence_refs=(),
            question_refs=(),
            spoken_at=_NOW,
            authority=CiboFunctionalAuthority.OPINION,
        )


def test_raw_text_utterances_stay_outside_core() -> None:
    result = _DIALOGUE.speak(
        CiboCeoMode.EXPLAIN,
        summary_code="summary.review",
        reason_codes=("direction.review",),
        evidence_refs=(),
        question_refs=(),
        spoken_at=_NOW,
    )
    assert isinstance(result, Success)
    dialogue = result.value
    for name in ("text", "utterance", "message", "content", "reply"):
        assert not hasattr(dialogue, name)


def test_repeated_identical_input_equal_logical_values() -> None:
    left = _DIALOGUE.speak(
        CiboCeoMode.DOUBT,
        summary_code="summary.review",
        reason_codes=("direction.review", "risk.review"),
        evidence_refs=(CiboEvidenceRef("evidence:direction"),),
        question_refs=(),
        spoken_at=_NOW,
    )
    right = _DIALOGUE.speak(
        CiboCeoMode.DOUBT,
        summary_code="summary.review",
        reason_codes=("direction.review", "risk.review"),
        evidence_refs=(CiboEvidenceRef("evidence:direction"),),
        question_refs=(),
        spoken_at=_NOW,
    )
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()
