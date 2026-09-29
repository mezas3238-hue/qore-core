import pytest

import qore.infrastructure.cibo_ce2i_pre_holdout_freeze as freeze_module
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_freeze import (
    ACTIVE_PRE_HOLDOUT_FREEZE,
    CURRENT_HOLDOUT_SEAL_STATE,
    CiboHoldoutSealState,
    CiboPreHoldoutFreezeManifest,
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



def _manifest(
    *,
    phase20d_ready: bool,
    phase21_frozen: bool,
) -> CiboPreHoldoutFreezeManifest:
    return CiboPreHoldoutFreezeManifest(
        head_sha="a" * 40,
        config_sha256="b" * 64,
        calibration_sha256="c" * 64,
        dataset_sha256="d" * 64,
        phase20d_qualification_sha256="e" * 64,
        phase21_policy_freeze_sha256="f" * 64,
        anti_leakage_passed=True,
        phase20d_causal_tool_gate_passed=phase20d_ready,
        phase21_policy_freeze_sealed=phase21_frozen,
        all_calibrations_frozen=True,
        provider_economics_frozen=True,
    )


def test_pre_holdout_freeze_rejects_missing_phase20d_or_phase21(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        freeze_module,
        "CURRENT_HOLDOUT_SEAL_STATE",
        CiboHoldoutSealState.PRE_HOLDOUT_FROZEN,
    )
    monkeypatch.setattr(
        freeze_module,
        "ACTIVE_PRE_HOLDOUT_FREEZE",
        _manifest(
            phase20d_ready=False,
            phase21_frozen=True,
        ),
    )
    assert pre_holdout_freeze_ready() is False

    monkeypatch.setattr(
        freeze_module,
        "ACTIVE_PRE_HOLDOUT_FREEZE",
        _manifest(
            phase20d_ready=True,
            phase21_frozen=False,
        ),
    )
    assert pre_holdout_freeze_ready() is False


def test_pre_holdout_freeze_accepts_complete_phase20d_phase21_lineage(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        freeze_module,
        "CURRENT_HOLDOUT_SEAL_STATE",
        CiboHoldoutSealState.PRE_HOLDOUT_FROZEN,
    )
    monkeypatch.setattr(
        freeze_module,
        "ACTIVE_PRE_HOLDOUT_FREEZE",
        _manifest(
            phase20d_ready=True,
            phase21_frozen=True,
        ),
    )
    assert pre_holdout_freeze_ready() is True
