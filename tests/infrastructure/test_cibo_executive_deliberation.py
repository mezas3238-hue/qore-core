from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.infrastructure.cibo_executive_deliberation import (
    CiboAdversarialCritique,
    CiboContributionKind,
    CiboCouncilOutcome,
    CiboCouncilSynthesis,
    CiboDeliberationContext,
    CiboDeliberationContribution,
    CiboDisagreement,
    CiboExecutiveDeliberation,
    CiboExecutiveDeliberationValidationError,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboDeliberationRole,
    CiboUncertainty,
    CiboUncertaintyKind,
)

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_SYNTHESIS_ID = UUID("60000000-0000-0000-0000-0000000000ff")


def _ref(value: str) -> CiboCognitiveEvidenceRef:
    return CiboCognitiveEvidenceRef(value)


def _uncertainty() -> CiboUncertainty:
    return CiboUncertainty(kind=CiboUncertaintyKind.INSUFFICIENT_EVIDENCE)


def _contribution(cid: UUID, role: str) -> CiboDeliberationContribution:
    return CiboDeliberationContribution(
        contribution_id=cid,
        role=CiboDeliberationRole(role),
        kind=CiboContributionKind.ARGUMENT,
        position_code=f"position.{role}",
        evidence_refs=(_ref(f"evidence:{role}"),),
        uncertainty=_uncertainty(),
        contributed_at=_NOW,
    )


def _context() -> CiboDeliberationContext:
    return CiboDeliberationContext(
        deliberation_id=UUID("60000000-0000-0000-0000-000000000001"),
        version_code="v1",
        subject_code="subject-demo",
        as_of=_NOW,
    )


def _synthesis(
    synthesis_id: UUID = _SYNTHESIS_ID, *, summary: str = "Executive synthesis"
) -> CiboCouncilSynthesis:
    return CiboCouncilSynthesis(
        synthesis_id=synthesis_id,
        summary=summary,
        evidence_refs=(_ref("evidence:synthesis"),),
        uncertainty=_uncertainty(),
        synthesized_at=_NOW,
    )


def _deliberation(
    *,
    participants: tuple[CiboDeliberationContribution, ...] | None = None,
    disagreements: tuple[CiboDisagreement, ...] = (),
    critiques: tuple[CiboAdversarialCritique, ...] = (),
    synthesis: CiboCouncilSynthesis | None = None,
    outcome: CiboCouncilOutcome = CiboCouncilOutcome.NO_DECISION,
) -> CiboExecutiveDeliberation:
    return CiboExecutiveDeliberation(
        context=_context(),
        participants=participants
        if participants is not None
        else (
            _contribution(UUID("60000000-0000-0000-0000-0000000000a1"), "quant"),
            _contribution(UUID("60000000-0000-0000-0000-0000000000a2"), "risk-aware-critic"),
        ),
        concluded_at=_NOW,
        disagreements=disagreements,
        critiques=critiques,
        synthesis=synthesis,
        outcome=outcome,
    )


class TestContribution:
    def test_contribution_requires_evidence(self) -> None:
        with pytest.raises(CiboExecutiveDeliberationValidationError, match="evidence"):
            CiboDeliberationContribution(
                contribution_id=UUID("60000000-0000-0000-0000-0000000000a3"),
                role=CiboDeliberationRole("quant"),
                kind=CiboContributionKind.ARGUMENT,
                position_code="position.quant",
                evidence_refs=(),
                uncertainty=_uncertainty(),
                contributed_at=_NOW,
            )

    def test_role_is_faculty_identity_not_an_order(self) -> None:
        contribution = _contribution(UUID("60000000-0000-0000-0000-0000000000a1"), "quant")
        assert isinstance(contribution.role, CiboDeliberationRole)
        for absent in ("order", "intent", "provider", "quantity", "authority"):
            assert not hasattr(contribution, absent)


class TestDeliberation:
    def test_deliberation_requires_participants(self) -> None:
        with pytest.raises(CiboExecutiveDeliberationValidationError, match="non-empty"):
            CiboExecutiveDeliberation(
                context=_context(),
                participants=(),
                concluded_at=_NOW,
            )

    def test_deliberation_rejects_duplicate_roles(self) -> None:
        with pytest.raises(CiboExecutiveDeliberationValidationError, match="unique roles"):
            CiboExecutiveDeliberation(
                context=_context(),
                participants=(
                    _contribution(UUID("60000000-0000-0000-0000-0000000000a1"), "quant"),
                    _contribution(UUID("60000000-0000-0000-0000-0000000000a2"), "quant"),
                ),
                concluded_at=_NOW,
            )

    def test_deliberation_rejects_duplicate_contribution_ids(self) -> None:
        cid = UUID("60000000-0000-0000-0000-0000000000a1")
        with pytest.raises(CiboExecutiveDeliberationValidationError, match="unique ids"):
            CiboExecutiveDeliberation(
                context=_context(),
                participants=(
                    _contribution(cid, "quant"),
                    _contribution(cid, "risk-aware-critic"),
                ),
                concluded_at=_NOW,
            )

    def test_disagreement_is_never_collapsed_to_consensus(self) -> None:
        disagreement = CiboDisagreement(
            a_ref=UUID("60000000-0000-0000-0000-0000000000a1"),
            b_ref=UUID("60000000-0000-0000-0000-0000000000a2"),
            reason_code="contradiction",
        )
        with pytest.raises(CiboExecutiveDeliberationValidationError, match="collapsed"):
            _deliberation(
                disagreements=(disagreement,),
                outcome=CiboCouncilOutcome.DECISION,
            )

    def test_disagreement_forbids_synthesis(self) -> None:
        disagreement = CiboDisagreement(
            a_ref=UUID("60000000-0000-0000-0000-0000000000a1"),
            b_ref=UUID("60000000-0000-0000-0000-0000000000a2"),
            reason_code="contradiction",
        )
        with pytest.raises(CiboExecutiveDeliberationValidationError, match="synthesis"):
            _deliberation(
                disagreements=(disagreement,),
                outcome=CiboCouncilOutcome.DISAGREEMENT,
                synthesis=_synthesis(),
            )

    def test_disagreement_outcome_is_retained(self) -> None:
        disagreement = CiboDisagreement(
            a_ref=UUID("60000000-0000-0000-0000-0000000000a1"),
            b_ref=UUID("60000000-0000-0000-0000-0000000000a2"),
            reason_code="contradiction",
        )
        deliberation = _deliberation(
            disagreements=(disagreement,),
            outcome=CiboCouncilOutcome.DISAGREEMENT,
        )
        assert deliberation.outcome is CiboCouncilOutcome.DISAGREEMENT
        assert deliberation.disagreements == (disagreement,)
        assert deliberation.synthesis is None

    def test_synthesis_requires_decision_outcome(self) -> None:
        with pytest.raises(CiboExecutiveDeliberationValidationError, match="decision"):
            _deliberation(
                outcome=CiboCouncilOutcome.NO_DECISION,
                synthesis=_synthesis(),
            )

    def test_disagreement_must_reference_existing_contribution(self) -> None:
        disagreement = CiboDisagreement(
            a_ref=UUID("60000000-0000-0000-0000-0000000000a1"),
            b_ref=UUID("60000000-0000-0000-0000-000000000099"),
            reason_code="contradiction",
        )
        with pytest.raises(CiboExecutiveDeliberationValidationError, match="existing"):
            _deliberation(disagreements=(disagreement,))

    def test_critique_must_reference_existing_contribution(self) -> None:
        critique = CiboAdversarialCritique(
            target_ref=UUID("60000000-0000-0000-0000-000000000099"),
            critique_reason_codes=("unsupported",),
        )
        with pytest.raises(CiboExecutiveDeliberationValidationError, match="existing"):
            _deliberation(critiques=(critique,))

    def test_participant_order_is_canonical(self) -> None:
        first = _contribution(UUID("60000000-0000-0000-0000-0000000000a1"), "quant")
        second = _contribution(UUID("60000000-0000-0000-0000-0000000000a2"), "risk-aware-critic")
        left = _deliberation(participants=(first, second))
        right = _deliberation(participants=(second, first))
        assert left.participants == right.participants
        assert left.logical_values() == right.logical_values()

    def test_revalidate_detects_tampered_participant(self) -> None:
        deliberation = _deliberation()
        object.__setattr__(deliberation.participants[0], "position_code", "Position Changed")
        with pytest.raises(CiboExecutiveDeliberationValidationError):
            deliberation.revalidate()


class TestReflectiveCorruptionFailsAtConstruction:
    def test_deliberation_rejects_corrupted_participant_role(self) -> None:
        participant = _contribution(UUID("60000000-0000-0000-0000-0000000000a1"), "quant")
        object.__setattr__(participant.role, "value", "NOT A ROLE!")
        with pytest.raises(CiboExecutiveDeliberationValidationError):
            CiboExecutiveDeliberation(
                context=_context(), participants=(participant,), concluded_at=_NOW
            )

    def test_deliberation_rejects_corrupted_participant_uncertainty(self) -> None:
        participant = _contribution(UUID("60000000-0000-0000-0000-0000000000a1"), "quant")
        object.__setattr__(participant.uncertainty, "kind", CiboUncertaintyKind.BOUNDED_CONFIDENCE)
        with pytest.raises(CiboExecutiveDeliberationValidationError):
            CiboExecutiveDeliberation(
                context=_context(), participants=(participant,), concluded_at=_NOW
            )


class TestCouncilSynthesisSecretRejection:
    _WITNESSES = (
        "sk-proj-abcdefghijklmnopqrstuvwxyz123456",
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_abcdefghijklmnopqrstuvwxyz1234",
        "gho_abcdefghijklmnopqrstuvwxyz1234",
        "ghu_abcdefghijklmnopqrstuvwxyz1234",
        "ghs_abcdefghijklmnopqrstuvwxyz1234",
        "ghr_abcdefghijklmnopqrstuvwxyz1234",
        "xoxb-123456789012-abcdefghijklmnopqrstuvwxyz",
        "xoxp-123456789012-abcdefghijklmnopqrstuvwxyz",
        "xoxa-123456789012-abcdefghijklmnopqrstuvwxyz",
        "xoxr-123456789012-abcdefghijklmnopqrstuvwxyz",
        "xoxs-123456789012-abcdefghijklmnopqrstuvwxyz",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature",
        "https://alice:correcthorsebatterystaple@example.com/x",
        "token=abc123",
        "client_secret=abcdefghijklmnopqrstuvwxyz123456",
        "Authorization: Bearer abcdef1234567890",
        "-----BEGIN PRIVATE KEY-----",
    )

    @pytest.mark.parametrize("witness", _WITNESSES)
    def test_summary_rejects_structural_secrets(self, witness: str) -> None:
        with pytest.raises(CiboExecutiveDeliberationValidationError, match="sensitive"):
            _synthesis(summary=witness)

    def test_revalidate_rejects_injected_structural_secret(self) -> None:
        synthesis = _synthesis()
        object.__setattr__(
            synthesis, "summary", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature"
        )
        with pytest.raises(CiboExecutiveDeliberationValidationError):
            synthesis.revalidate()

    def test_benign_summary_still_accepted(self) -> None:
        assert _synthesis(summary="the authentication failed and was retried").summary
        assert _synthesis(summary="the client_secret field must be configured").summary
