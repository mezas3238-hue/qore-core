from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_causal_ablation import (
    PROTOCOL_FROZEN_AT,
    ROOT_CONTROL_ID,
    SEALED_HOLDOUT_ID,
    CausalAblationEvidenceKind,
    CompoundCausalAblationPair,
    CompoundCausalMechanism,
    gate_compound_causal_ablation_pairs,
)

_SHA_A = "sha256:" + "a" * 64
_SHA_B = "sha256:" + "b" * 64
_SHA_C = "sha256:" + "c" * 64
_SHA_D = "sha256:" + "d" * 64
T0 = PROTOCOL_FROZEN_AT + timedelta(minutes=1)


def _pair(**changes) -> CompoundCausalAblationPair:
    values = dict(
        ablation_id="ablation-genc2-001",
        workstream_id="GEN-C2",
        root_control_id=ROOT_CONTROL_ID,
        local_control_policy_id="AS_IS_PROFIT_HANDLING",
        treatment_policy_id="GENC2_PROFIT_GRADUATION_V1",
        changed_mechanism=CompoundCausalMechanism.PROFIT_GRADUATION,
        population_id="phase20d-forward-population",
        control_population_sha256=_SHA_A,
        treatment_population_sha256=_SHA_A,
        control_provider_economics_sha256=_SHA_B,
        treatment_provider_economics_sha256=_SHA_B,
        causal_horizon_sha256=_SHA_C,
        provider_constraints_sha256=_SHA_D,
        qualification_fold_id="WF1",
        preregistered_at=T0,
        first_decision_at=T0 + timedelta(minutes=1),
        evidence_kind=CausalAblationEvidenceKind.FORWARD_OBSERVED,
    )
    values.update(changes)
    return CompoundCausalAblationPair(**values)


def test_compound_causal_ablation_accepts_strict_same_population_pair() -> None:
    pair = _pair()

    report = gate_compound_causal_ablation_pairs((pair,))

    assert report.ablation_ids == ("ablation-genc2-001",)
    assert report.treatment_policy_ids == ("GENC2_PROFIT_GRADUATION_V1",)
    assert report.fold_ids == ("WF1",)
    assert report.pair_count == 1
    assert report.one_mechanism_per_pair is True
    assert report.same_population_per_pair is True
    assert report.same_provider_economics_per_pair is True
    assert report.forward_observed_only is True
    assert report.economic_outcomes_evaluated is False
    assert report.winner_selected is False
    assert report.certification_ready is False


def test_compound_causal_ablation_rejects_mechanism_workstream_mismatch() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="mechanism/workstream mismatch",
    ):
        _pair(
            changed_mechanism=(
                CompoundCausalMechanism.MARGINAL_CAPITAL_UTILITY
            )
        )


def test_compound_causal_ablation_rejects_population_drift() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="population must be identical",
    ):
        _pair(treatment_population_sha256=_SHA_C)


def test_compound_causal_ablation_rejects_provider_economics_drift() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="provider economics must be identical",
    ):
        _pair(treatment_provider_economics_sha256=_SHA_C)


def test_compound_causal_ablation_rejects_pre_freeze_registration() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot predate protocol freeze",
    ):
        _pair(
            preregistered_at=PROTOCOL_FROZEN_AT - timedelta(seconds=1),
        )


def test_compound_causal_ablation_rejects_pre_registration_decision() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="pre-registration decision",
    ):
        _pair(first_decision_at=T0 - timedelta(seconds=1))


def test_compound_causal_ablation_rejects_holdout_or_outcome_selection() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="sealed 2017H1 holdout",
    ):
        _pair(population_id=SEALED_HOLDOUT_ID)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="governance drift",
    ):
        _pair(outcomes_used_to_select_treatment=True)


def test_compound_causal_ablation_batch_rejects_duplicate_treatment() -> None:
    first = _pair()
    second = _pair(
        ablation_id="ablation-genc4-001",
        workstream_id="GEN-C4",
        changed_mechanism=CompoundCausalMechanism.MARGINAL_CAPITAL_UTILITY,
        local_control_policy_id="CURRENT_CAPITAL_EVIDENCE_PATH",
        qualification_fold_id="WF2",
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="treatment identities must be unique",
    ):
        gate_compound_causal_ablation_pairs((first, second))


def test_compound_causal_ablation_batch_accepts_distinct_mechanisms() -> None:
    first = _pair()
    second = _pair(
        ablation_id="ablation-genc4-001",
        workstream_id="GEN-C4",
        changed_mechanism=CompoundCausalMechanism.MARGINAL_CAPITAL_UTILITY,
        local_control_policy_id="CURRENT_CAPITAL_EVIDENCE_PATH",
        treatment_policy_id="GENC4_MARGINAL_ELIGIBILITY_V1",
        qualification_fold_id="WF2",
    )

    report = gate_compound_causal_ablation_pairs((first, second))

    assert report.pair_count == 2
    assert report.fold_ids == ("WF1", "WF2")

def test_compound_causal_ablation_report_rejects_manual_governance_drift() -> None:
    report = gate_compound_causal_ablation_pairs((_pair(),))

    with pytest.raises(
        CiboCompoundCapitalError,
        match="report governance drift",
    ):
        replace(report, economic_outcomes_evaluated=True)

