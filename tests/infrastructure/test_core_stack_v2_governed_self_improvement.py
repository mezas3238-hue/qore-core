import pytest

from qore.infrastructure.core_stack_v2.governed_self_improvement import (
    GovernedImprovementProposal,
    ImprovementStage,
    ImprovementStageEvidence,
    ImprovementTarget,
)


def _evidence(end: ImprovementStage):
    return tuple(
        ImprovementStageEvidence(
            stage=stage,
            evidence_ref=f"evidence:{stage.name}",
            passed=True,
            dataset_window_id=f"window:{stage.name}",
        )
        for stage in ImprovementStage
        if int(stage) <= int(end)
    )


def test_holdout_pass_is_not_promotion() -> None:
    proposal = GovernedImprovementProposal(
        proposal_id="wp04-v3b",
        version="001",
        target=ImprovementTarget.REPRESENTATION,
        rollback_ref="rollback:wp04-v3",
        provenance_refs=("artifact:10906064254",),
        reproducibility_ref="sha:8c0b4c3",
        stages=_evidence(ImprovementStage.HOLDOUT),
    )
    assert proposal.promotion_allowed is False


def test_stage_skipping_fails_closed() -> None:
    stages = (
        ImprovementStageEvidence(
            ImprovementStage.DISCOVERY, "a", True, "window:a"
        ),
        ImprovementStageEvidence(
            ImprovementStage.FALSIFICATION, "b", True, "window:b"
        ),
    )
    with pytest.raises(ValueError, match="cannot skip"):
        GovernedImprovementProposal(
            proposal_id="skip",
            version="001",
            target=ImprovementTarget.MODEL,
            rollback_ref="rollback",
            provenance_refs=("p",),
            reproducibility_ref="repro",
            stages=stages,
        )


def test_only_full_chain_can_promote() -> None:
    proposal = GovernedImprovementProposal(
        proposal_id="full",
        version="001",
        target=ImprovementTarget.CALIBRATION,
        rollback_ref="rollback",
        provenance_refs=("p",),
        reproducibility_ref="repro",
        stages=_evidence(ImprovementStage.PROMOTION),
    )
    assert proposal.promotion_allowed is True
