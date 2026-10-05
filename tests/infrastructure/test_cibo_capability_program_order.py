import pytest

from qore.infrastructure.cibo_capability_program_order import (
    CIBO_CAPABILITY_PROGRAM_ORDER,
    DEFAULT_CIBO_CAPABILITY_PROGRAM_PROGRESS,
    CiboCapabilityProgramProgress,
    CiboCapabilityProgramStage,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def test_program_starts_with_ceiling_discovery() -> None:
    progress = DEFAULT_CIBO_CAPABILITY_PROGRAM_PROGRESS

    assert (
        progress.current_stage
        is CiboCapabilityProgramStage.CEILING_DISCOVERY
    )
    assert progress.closed_stages == ()
    assert progress.ceiling_discovery_active is True
    assert progress.examinations_unlocked is False


def test_owner_mandated_program_order_is_exact() -> None:
    assert CIBO_CAPABILITY_PROGRAM_ORDER == (
        CiboCapabilityProgramStage.CEILING_DISCOVERY,
        CiboCapabilityProgramStage.POST_CEILING_REFINEMENT,
        CiboCapabilityProgramStage.EXAM_1_ALL_TRADER_RESCUE,
        CiboCapabilityProgramStage.EXAM_3_NEGATIVE_TRADER_ONLY_RESCUE,
        CiboCapabilityProgramStage.EXAM_2_2000_PERCENT_10M,
    )


def test_exam_1_cannot_open_before_ceiling_and_refinement_close() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="stage order violated",
    ):
        CiboCapabilityProgramProgress(
            current_stage=CiboCapabilityProgramStage.EXAM_1_ALL_TRADER_RESCUE,
            closed_stages=(
                CiboCapabilityProgramStage.CEILING_DISCOVERY,
            ),
        )


def test_exam_3_cannot_open_before_exam_1_closes() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="stage order violated",
    ):
        CiboCapabilityProgramProgress(
            current_stage=(
                CiboCapabilityProgramStage.EXAM_3_NEGATIVE_TRADER_ONLY_RESCUE
            ),
            closed_stages=(
                CiboCapabilityProgramStage.CEILING_DISCOVERY,
                CiboCapabilityProgramStage.POST_CEILING_REFINEMENT,
            ),
        )


def test_2000_percent_exam_is_last() -> None:
    progress = CiboCapabilityProgramProgress(
        current_stage=CiboCapabilityProgramStage.EXAM_2_2000_PERCENT_10M,
        closed_stages=(
            CiboCapabilityProgramStage.CEILING_DISCOVERY,
            CiboCapabilityProgramStage.POST_CEILING_REFINEMENT,
            CiboCapabilityProgramStage.EXAM_1_ALL_TRADER_RESCUE,
            CiboCapabilityProgramStage.EXAM_3_NEGATIVE_TRADER_ONLY_RESCUE,
        ),
    )

    assert progress.examinations_unlocked is True
