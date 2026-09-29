from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
    marginal_capital_utility_evidence_sha256,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence_store import (
    DurableGenc4MarginalEvidenceStore,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 29, 17, 40, tzinfo=UTC)


def _evidence() -> MarginalCapitalUtilityEvidence:
    return MarginalCapitalUtilityEvidence(
        evidence_id="genc4-durable-1",
        decision_at=T0,
        account_identity=CiboAccountCapitalIdentity(
            provider_key="ctrader",
            account_ref="genc4-durable-demo",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="genc4-durable-signal",
        source_opportunity_decision_sha256="sha256:" + "7" * 64,
        source_baseline_policy_record_sha256="sha256:" + "8" * 64,
        current_compound_capacity_usd=Decimal("60"),
        requested_incremental_capital_usd=Decimal("5"),
        expected_incremental_return_usd=Decimal("1.2"),
        incremental_stop_risk_usd=Decimal("0.8"),
        incremental_margin_usd=Decimal("4"),
        incremental_execution_cost_usd=Decimal("0.1"),
        incremental_concentration_risk_usd=Decimal("0.5"),
        incremental_drawdown_risk_proxy_usd=Decimal("0.4"),
        incremental_optionality_consumed_usd=Decimal("1"),
        expected_capital_minutes=Decimal("45"),
        epistemic_uncertainty=Decimal("0.25"),
        provider_evidence_sha256="sha256:" + "1" * 64,
        expectation_evidence_sha256="sha256:" + "2" * 64,
        factor_evidence_sha256="sha256:" + "3" * 64,
        duration_evidence_sha256="sha256:" + "4" * 64,
        execution_evidence_sha256="sha256:" + "5" * 64,
        optionality_evidence_sha256="sha256:" + "6" * 64,
    )


def test_genc4_durable_store_seals_full_source_lineage_pre_outcome(
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    store = DurableGenc4MarginalEvidenceStore(
        tmp_path / "genc4-evidence.json"
    )
    sealed_at = T0 + timedelta(seconds=1)

    book = store.seal(
        evidence,
        sealed_at=sealed_at,
        expected_generation=0,
    )
    seal = book.seal_for_sha(
        marginal_capital_utility_evidence_sha256(evidence)
    )

    assert seal is not None
    assert seal.evidence_id == evidence.evidence_id
    assert (
        seal.source_opportunity_decision_sha256
        == evidence.source_opportunity_decision_sha256
    )
    assert (
        seal.source_baseline_policy_record_sha256
        == evidence.source_baseline_policy_record_sha256
    )
    assert seal.signal_fingerprint == evidence.signal_fingerprint
    assert seal.incremental_stop_risk_usd == Decimal("0.8")
    assert seal.outcome_present_at_seal is False
    assert seal.runtime_authority is False
    assert store.load() == book


def test_genc4_durable_store_is_idempotent_and_cas_guarded(
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    store = DurableGenc4MarginalEvidenceStore(
        tmp_path / "genc4-evidence.json"
    )
    sealed_at = T0 + timedelta(seconds=1)

    first = store.seal(
        evidence,
        sealed_at=sealed_at,
        expected_generation=0,
    )
    second = store.seal(
        evidence,
        sealed_at=sealed_at,
        expected_generation=1,
    )
    assert second == first

    with pytest.raises(
        CiboCompoundCapitalError,
        match="generation conflict",
    ):
        store.seal(
            evidence,
            sealed_at=sealed_at,
            expected_generation=0,
        )


def test_genc4_durable_store_rejects_same_id_with_changed_evidence(
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    store = DurableGenc4MarginalEvidenceStore(
        tmp_path / "genc4-evidence.json"
    )
    sealed_at = T0 + timedelta(seconds=1)
    store.seal(
        evidence,
        sealed_at=sealed_at,
        expected_generation=0,
    )

    changed = replace(
        evidence,
        requested_incremental_capital_usd=Decimal("6"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="evidence id already exists",
    ):
        store.seal(
            changed,
            sealed_at=sealed_at,
            expected_generation=1,
        )
