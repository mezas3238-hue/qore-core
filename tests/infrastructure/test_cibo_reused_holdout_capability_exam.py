from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capability_exam_cognitive_coverage import (
    EXPECTED_FACULTIES,
    EXPECTED_TOOLS,
    build_cibo_capability_cognitive_coverage,
)
from qore.infrastructure.cibo_ce2i_tool_registry import CE2I_TOOL_REGISTRY
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
    Phase22FreshTraderEvidence,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
)
from qore.infrastructure.cibo_phase22_v4_source_receipt import (
    load_phase22_v4_source_receipt,
)
from qore.infrastructure.cibo_reused_holdout_capability_exam import (
    EXAM_ID,
    VALIDATION_MODE,
)
from scripts.cibo_phase22_reused_holdout_batch_assembler import (
    _canonicalize_evidence,
)


def test_v4_replay_source_lineage_is_canonical_for_lab_replay() -> None:
    receipt = load_phase22_v4_source_receipt(
        Path("docs/research/CIBO-PHASE22-V4-SOURCE-RECEIPT.json")
    )
    book = VersionedPhase22HistoricalReplayEvidenceBook(
        generation=1,
        amendment_sha256="sha256:" + "a" * 64,
        decisions=(),
        outcomes=(),
        source_receipt_sha256=receipt.fingerprint(),
        source_collector_git_shas=(receipt.corpus_git_sha,),
    )
    assert book.source_receipt_sha256 == receipt.fingerprint()


def test_capability_exam_is_reused_holdout_and_exact_t01_t20() -> None:
    assert EXAM_ID == "CIBO_REUSED_HOLDOUT_INFRASTRUCTURE_CAPABILITY_EXAM_V1"
    assert VALIDATION_MODE == "NON_CERTIFYING_REUSED_HOLDOUT"
    assert tuple(item.code for item in CE2I_TOOL_REGISTRY) == tuple(
        f"T{i:02d}" for i in range(1, 21)
    )


def test_capability_exam_sources_cannot_mutate_broker() -> None:
    paths = (
        Path("src/qore/infrastructure/cibo_reused_holdout_capability_exam.py"),
        Path("scripts/cibo_phase22_reused_holdout_batch_assembler.py"),
        Path("scripts/cibo_reused_holdout_capability_exam.py"),
    )
    forbidden = (
        "ProtoOANewOrderReq",
        "ProtoOAClosePositionReq",
        "ProtoOACancelOrderReq",
        "ProtoOAAmendOrderReq",
        "ProtoOAAmendPositionSLTPReq",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source


def _opportunity(*, signal_hour: int, fingerprint_char: str) -> Phase22FreshOpportunity:
    return Phase22FreshOpportunity(
        trader_id=TraderLineage.VT08_FOREX,
        qore_symbol="EURUSD",
        signal_fingerprint="sha256:" + fingerprint_char * 64,
        signal_at=datetime(2015, 1, 2, signal_hour, tzinfo=UTC),
        entry_at=datetime(2015, 1, 2, signal_hour, 1, tzinfo=UTC),
        exit_at=datetime(2015, 1, 2, signal_hour, 2, tzinfo=UTC),
        side="long",
        entry_price=Decimal("1.10"),
        structural_stop=Decimal("1.09"),
        technical_target=Decimal("1.12"),
        exit_reason="TARGET",
        gross_structural_outcome_r=Decimal("1"),
        methodology_sha256="sha256:" + "c" * 64,
        source_evidence_ids=("sha256:" + "d" * 64,),
    )


def test_reused_batch_canonicalizes_per_trader_opportunity_order() -> None:
    later = _opportunity(signal_hour=12, fingerprint_char="a")
    earlier = _opportunity(signal_hour=10, fingerprint_char="b")
    evidence = Phase22FreshTraderEvidence(
        trader_id="VT08_FOREX",
        source_artifact_sha256="sha256:" + "e" * 64,
        opportunities=(later, earlier),
        fresh_outcomes_executed=True,
        methodology_changed=False,
        legacy_trader_sizing_used_for_cibo=False,
    )

    canonical = _canonicalize_evidence(evidence)

    assert canonical.opportunities == (earlier, later)
    assert canonical.source_artifact_sha256 == evidence.source_artifact_sha256


def test_capability_exam_requires_cognitive_cf01_cf19_and_cibo_sizing_authority() -> None:
    receipt = build_cibo_capability_cognitive_coverage(
        source_batch_sha256="sha256:" + "a" * 64,
        observed_at=datetime(2026, 10, 2, 20, tzinfo=UTC),
    )

    assert receipt.complete is True
    assert receipt.cognitive_used is True
    assert receipt.mission_faculties == tuple(
        item.value for item in EXPECTED_FACULTIES
    )
    assert receipt.coordinated_faculties == tuple(
        item.value for item in EXPECTED_FACULTIES
    )
    assert receipt.ce2i_tool_codes == EXPECTED_TOOLS
    assert receipt.trader_sizing_authority == "NONE"
    assert receipt.cibo_sizing_authority == "CIBO_CMA"
    assert receipt.qore_risk_sovereign is True


def test_capability_exam_function_and_tool_surfaces_are_exact() -> None:
    assert len(EXPECTED_FACULTIES) == 19
    assert len(set(EXPECTED_FACULTIES)) == 19
    assert EXPECTED_TOOLS == tuple(f"T{i:02d}" for i in range(1, 21))
