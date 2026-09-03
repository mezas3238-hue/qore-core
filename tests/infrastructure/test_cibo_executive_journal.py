from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.infrastructure.cibo_executive_journal import (
    CiboEconomicJournalLink,
    CiboEvidenceSufficiency,
    CiboExecutiveJournalValidationError,
    CiboJournalEntry,
    CiboJournalEntryKind,
    CiboJournalStore,
    CiboLossDiagnosis,
    CiboLossDiagnosisState,
    CiboLossHypothesis,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_ENTRY_ID = UUID("50000000-0000-0000-0000-000000000001")


def _ref(value: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(value)


def _entry(
    entry_id: UUID = _ENTRY_ID,
    *,
    kind: CiboJournalEntryKind = CiboJournalEntryKind.DECISION,
    loss_diagnosis: CiboLossDiagnosis | None = None,
    economic_link: CiboEconomicJournalLink | None = None,
    supersedes: tuple[UUID, ...] = (),
) -> CiboJournalEntry:
    return CiboJournalEntry(
        entry_id=entry_id,
        episode_id=UUID("50000000-0000-0000-0000-0000000000aa"),
        kind=kind,
        subject_code="subject-demo",
        recorded_at=_NOW,
        evidence_refs=(_ref("evidence:demo"),),
        loss_diagnosis=loss_diagnosis,
        economic_link=economic_link,
        supersedes=supersedes,
    )


class TestLossDiagnosis:
    def test_insufficient_evidence_is_first_class(self) -> None:
        diagnosis = CiboLossDiagnosis(state=CiboLossDiagnosisState.INSUFFICIENT_EVIDENCE)
        assert diagnosis.hypotheses == ()

    def test_insufficient_evidence_must_not_assert_hypotheses(self) -> None:
        with pytest.raises(CiboExecutiveJournalValidationError, match="insufficient"):
            CiboLossDiagnosis(
                state=CiboLossDiagnosisState.INSUFFICIENT_EVIDENCE,
                hypotheses=(CiboLossHypothesis.MARKET_NOISE,),
            )

    def test_hypothesized_requires_hypotheses(self) -> None:
        with pytest.raises(CiboExecutiveJournalValidationError, match="hypothesis"):
            CiboLossDiagnosis(state=CiboLossDiagnosisState.HYPOTHESIZED)

    def test_hypotheses_are_non_causal_advisory_codes(self) -> None:
        diagnosis = CiboLossDiagnosis(
            state=CiboLossDiagnosisState.HYPOTHESIZED,
            hypotheses=(CiboLossHypothesis.REGIME_CHANGE,),
            evidence_refs=(_ref("evidence:loss"),),
        )
        assert diagnosis.state is CiboLossDiagnosisState.HYPOTHESIZED
        # A hypothesis is a research input, not a silent parameter change.
        assert diagnosis.hypotheses == (CiboLossHypothesis.REGIME_CHANGE,)

    def test_loss_hypothesis_covers_required_set(self) -> None:
        assert {h.value for h in CiboLossHypothesis} == {
            "risk-containment",
            "entry-quality",
            "market-noise",
            "regime-change",
            "volatility-expansion",
            "late-signal",
            "lifecycle-mismatch",
            "instrument-mismatch",
            "stop-methodology",
            "concentration-correlation",
            "execution-cost-degradation",
        }


class TestEconomicJournalLink:
    def test_empty_link_invents_no_pnl_or_cause(self) -> None:
        link = CiboEconomicJournalLink()
        for field in (
            "pnl_ref",
            "cost_ref",
            "slippage_ref",
            "carry_ref",
            "stop_ref",
            "mfe_ref",
            "mae_ref",
        ):
            assert getattr(link, field) is None

    def test_link_binds_exact_evidence_refs(self) -> None:
        link = CiboEconomicJournalLink(
            trader_ref=_ref("evidence:trader-config"),
            receipt_ref=_ref("evidence:demo-receipt"),
            evidence_sufficiency=CiboEvidenceSufficiency.SUFFICIENT,
        )
        assert link.trader_ref == _ref("evidence:trader-config")
        assert link.evidence_sufficiency is CiboEvidenceSufficiency.SUFFICIENT

    def test_link_rejects_non_ref_type(self) -> None:
        with pytest.raises(CiboExecutiveJournalValidationError):
            CiboEconomicJournalLink(trader_ref="not-a-ref")  # type: ignore[arg-type]


class TestJournalEntryAndStore:
    def test_entry_requires_evidence(self) -> None:
        with pytest.raises(CiboExecutiveJournalValidationError, match="evidence"):
            CiboJournalEntry(
                entry_id=UUID("50000000-0000-0000-0000-000000000002"),
                episode_id=UUID("50000000-0000-0000-0000-0000000000aa"),
                kind=CiboJournalEntryKind.DECISION,
                subject_code="subject-demo",
                recorded_at=_NOW,
                evidence_refs=(),
            )

    def test_entry_rejects_naive_datetime(self) -> None:
        with pytest.raises(CiboExecutiveJournalValidationError, match="timezone"):
            CiboJournalEntry(
                entry_id=UUID("50000000-0000-0000-0000-000000000002"),
                episode_id=UUID("50000000-0000-0000-0000-0000000000aa"),
                kind=CiboJournalEntryKind.DECISION,
                subject_code="subject-demo",
                recorded_at=datetime(2026, 8, 9, 0, 0),
                evidence_refs=(_ref("evidence:demo"),),
            )

    def test_entry_has_no_authority_fields(self) -> None:
        entry = _entry()
        for absent in ("order", "intent", "provider", "quantity", "authorization"):
            assert not hasattr(entry, absent)

    def test_record_is_append_only_no_hindsight_rewrite(self) -> None:
        decision_id = UUID("50000000-0000-0000-0000-000000000003")
        lesson_id = UUID("50000000-0000-0000-0000-000000000004")
        store = CiboJournalStore()
        recorded = store.record(_entry(entry_id=decision_id))
        assert isinstance(recorded, Success)
        # A later lesson links to the decision without rewriting its belief.
        lesson = _entry(
            entry_id=lesson_id,
            kind=CiboJournalEntryKind.LESSON,
            supersedes=(decision_id,),
        )
        updated = recorded.value.record(lesson)
        assert isinstance(updated, Success)
        by_id = {e.entry_id: e for e in updated.value.entries}
        assert by_id[decision_id].kind is CiboJournalEntryKind.DECISION
        assert by_id[decision_id].superseded_by == (lesson_id,)
        assert by_id[lesson_id].supersedes == (decision_id,)

    def test_record_rejects_duplicate_id(self) -> None:
        store = CiboJournalStore()
        first = store.record(_entry())
        assert isinstance(first, Success)
        result = first.value.record(_entry())
        assert isinstance(result, Failure)

    def test_record_rejects_supersedes_unknown(self) -> None:
        store = CiboJournalStore()
        result = store.record(
            _entry(supersedes=(UUID("50000000-0000-0000-0000-000000000099"),))
        )
        assert isinstance(result, Failure)

    def test_revalidate_detects_tampered_evidence_ref(self) -> None:
        entry = _entry()
        object.__setattr__(entry.evidence_refs[0], "value", "secret=injected")
        with pytest.raises(CiboExecutiveJournalValidationError):
            entry.revalidate()
