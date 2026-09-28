import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_freeze import (
    ACTIVE_PRE_HOLDOUT_FREEZE,
    CURRENT_HOLDOUT_SEAL_STATE,
    CiboHoldoutSealState,
    pre_holdout_freeze_ready,
    require_pre_holdout_freeze_before_2017h1_access,
)


def test_2017h1_is_sealed_until_pre_holdout_freeze() -> None:
    assert ACTIVE_PRE_HOLDOUT_FREEZE is None
    assert CURRENT_HOLDOUT_SEAL_STATE is CiboHoldoutSealState.SEALED_UNTOUCHED
    assert pre_holdout_freeze_ready() is False

    with pytest.raises(
        CiboCapitalManagementError,
        match="2017H1 SEALED_UNTOUCHED",
    ):
        require_pre_holdout_freeze_before_2017h1_access()
