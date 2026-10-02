from pathlib import Path

from qore.infrastructure.cibo_ce2i_tool_registry import CE2I_TOOL_REGISTRY
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
