from datetime import UTC, datetime, timedelta

from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    FrozenToolCalibration,
    FrozenToolCalibrationDisposition,
    build_calibration_freeze_manifest,
)
from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_gate import (
    CiboPreHoldoutStatus,
    calibration_matrix_sha256,
    evaluate_pre_holdout_readiness,
)
from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    PROVIDER_ECONOMICS_COMPONENT_FREEZE_ID,
    CiboProviderEconomicsComponentFreeze,
)

T0 = datetime(2026, 9, 30, 21, 30, tzinfo=UTC)


def _terminal_tools() -> tuple[FrozenToolCalibration, ...]:
    provider_required = {
        row.tool_code
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
        if row.provider_economics_required
    }
    rows = []
    for index in range(1, 21):
        code = f"T{index:02d}"
        disabled = code in {"T16", "T17"}
        rows.append(
            FrozenToolCalibration(
                tool_code=code,
                disposition=(
                    FrozenToolCalibrationDisposition.STRUCTURALLY_DISABLED
                    if disabled
                    else FrozenToolCalibrationDisposition.CERTIFICATION_READY
                ),
                evidence_refs=(f"terminal:{code}",),
                oos_ready=not disabled,
                certification_ready=not disabled,
                structurally_disabled=disabled,
                provider_economics_bound=code in provider_required,
            )
        )
    return tuple(rows)


def _ready_provider_freeze(
    *,
    frozen_at: datetime = T0,
) -> CiboProviderEconomicsComponentFreeze:
    return CiboProviderEconomicsComponentFreeze(
        freeze_id=PROVIDER_ECONOMICS_COMPONENT_FREEZE_ID,
        provider_key="ctrader-demo",
        environment="demo",
        source_evidence_ref="provider-economics:test",
        source_provenance_sha256="1" * 64,
        source_observed_at=frozen_at - timedelta(minutes=1),
        frozen_at=frozen_at,
        point_in_time_terms_frozen=True,
        spread_terms_frozen=True,
        commission_terms_frozen=True,
        expected_margin_terms_frozen=True,
        volume_contract_terms_frozen=True,
        empirical_slippage_frozen=True,
        execution_model_frozen=True,
        historical_2017_exact_claimed=False,
        holdout_outcomes_used=False,
        target_aware=False,
        broker_mutation_performed=False,
        pre_holdout_provider_economics_ready=True,
        provider_deployment_ready=True,
        certification_lane="EMPIRICAL_EXECUTION",
        blockers=(),
        deployment_blockers=(),
        execution_calibration_sha256="sha256:" + "2" * 64,
        productive_authority=False,
    )


def _terminal_manifest(
    provider: CiboProviderEconomicsComponentFreeze,
    *,
    phase20_sha: str = "sha256:" + "3" * 64,
):
    return build_calibration_freeze_manifest(
        frozen_at=provider.frozen_at + timedelta(seconds=1),
        phase20d_forward_manifest_sha256=phase20_sha,
        provider_economics_freeze_sha256=provider.fingerprint(),
        tools=_terminal_tools(),
    )


def test_pre_holdout_gate_is_fail_closed_before_calibration_freeze() -> None:
    readiness = evaluate_pre_holdout_readiness()

    assert readiness.status is CiboPreHoldoutStatus.NOT_READY
    assert (
        readiness.holdout_candidate_id
        == "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
    )
    assert readiness.holdout_outcomes_inspected is False
    assert readiness.holdout_market_data_read is False
    assert "PHASE20D_CAUSAL_TOOL_GATE_NOT_PASSED" in readiness.blockers
    assert "PHASE21_POLICY_FREEZE_NOT_SEALED" in readiness.blockers
    assert "PROVIDER_ECONOMICS_NOT_FROZEN" in readiness.blockers
    assert "CALIBRATION_FREEZE_MANIFEST_NOT_SEALED" in readiness.blockers
    assert any(
        item.startswith("UNRESOLVED_CAUSAL_CALIBRATIONS:")
        for item in readiness.blockers
    )


def test_matrix_digest_is_stable_and_nonempty() -> None:
    first = calibration_matrix_sha256()
    second = calibration_matrix_sha256()

    assert first == second
    assert len(first) == 64


def test_t16_t17_fail_closed_does_not_by_itself_contaminate_holdout() -> None:
    readiness = evaluate_pre_holdout_readiness(
        provider_economics_frozen=True,
        calibration_freeze_manifest_sealed=True,
    )

    assert readiness.holdout_outcomes_inspected is False
    assert readiness.holdout_market_data_read is False
    assert not any(
        item.startswith("UNRESOLVED_FAIL_CLOSED_TOOLS:T16")
        for item in readiness.blockers
    )
    assert not any(
        item.startswith("UNRESOLVED_FAIL_CLOSED_TOOLS:T17")
        for item in readiness.blockers
    )


def test_pre_holdout_gate_requires_phase20d_and_phase21_even_after_freezes() -> None:
    readiness = evaluate_pre_holdout_readiness(
        provider_economics_frozen=True,
        calibration_freeze_manifest_sealed=True,
        phase20d_causal_gate_passed=False,
        phase21_policy_freeze_sealed=False,
    )

    assert readiness.status is CiboPreHoldoutStatus.NOT_READY
    assert "PHASE20D_CAUSAL_TOOL_GATE_NOT_PASSED" in readiness.blockers
    assert "PHASE21_POLICY_FREEZE_NOT_SEALED" in readiness.blockers
    assert readiness.holdout_outcomes_inspected is False
    assert readiness.holdout_market_data_read is False


def test_dynamic_terminal_manifest_supersedes_historical_matrix_blockers() -> None:
    provider = _ready_provider_freeze()
    phase20_sha = "sha256:" + "3" * 64
    manifest = _terminal_manifest(provider, phase20_sha=phase20_sha)

    readiness = evaluate_pre_holdout_readiness(
        phase20d_causal_gate_passed=True,
        phase21_policy_freeze_sealed=True,
        provider_economics_component_freeze=provider,
        calibration_freeze_manifest=manifest,
        phase20d_forward_manifest_sha256=phase20_sha,
    )

    assert readiness.status is CiboPreHoldoutStatus.READY_TO_UNSEAL_ACTIVE_HOLDOUT
    assert readiness.blockers == ()
    assert readiness.holdout_outcomes_inspected is False
    assert readiness.holdout_market_data_read is False
    assert not any(
        item.startswith("UNRESOLVED_CAUSAL_CALIBRATIONS:")
        for item in readiness.blockers
    )
    assert not any(
        item.startswith("PROVIDER_ECONOMICS_REQUIRED:")
        for item in readiness.blockers
    )


def test_dynamic_manifest_requires_exact_provider_freeze_hash() -> None:
    provider = _ready_provider_freeze()
    phase20_sha = "sha256:" + "3" * 64
    manifest = build_calibration_freeze_manifest(
        frozen_at=provider.frozen_at + timedelta(seconds=1),
        phase20d_forward_manifest_sha256=phase20_sha,
        provider_economics_freeze_sha256="sha256:" + "9" * 64,
        tools=_terminal_tools(),
    )

    readiness = evaluate_pre_holdout_readiness(
        phase20d_causal_gate_passed=True,
        phase21_policy_freeze_sealed=True,
        provider_economics_component_freeze=provider,
        calibration_freeze_manifest=manifest,
        phase20d_forward_manifest_sha256=phase20_sha,
    )

    assert readiness.status is CiboPreHoldoutStatus.NOT_READY
    assert "PROVIDER_ECONOMICS_FREEZE_SHA_MISMATCH" in readiness.blockers


def test_dynamic_manifest_requires_bound_forward_manifest_sha() -> None:
    provider = _ready_provider_freeze()
    manifest = _terminal_manifest(provider)

    readiness = evaluate_pre_holdout_readiness(
        phase20d_causal_gate_passed=True,
        phase21_policy_freeze_sealed=True,
        provider_economics_component_freeze=provider,
        calibration_freeze_manifest=manifest,
    )

    assert readiness.status is CiboPreHoldoutStatus.NOT_READY
    assert "PHASE20D_FORWARD_MANIFEST_SHA_NOT_BOUND" in readiness.blockers
