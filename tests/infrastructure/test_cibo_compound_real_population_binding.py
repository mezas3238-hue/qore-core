from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_compound_real_population_binding import (
    CompoundPopulationEvidenceKind,
    ForwardCompoundEconomicRecord,
    bind_forward_compound_population,
)

T0 = datetime(2026, 9, 29, 0, 0, tzinfo=UTC)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _record(
    fold: int,
    *,
    trader: TraderLineage = TraderLineage.VT31_NAS100,
) -> ForwardCompoundEconomicRecord:
    decision_at = T0 + timedelta(days=fold - 1)
    return ForwardCompoundEconomicRecord(
        episode_id=f"episode-{fold}",
        deployment_id=f"deployment-{fold}",
        market_event_id=f"market-{fold}",
        decision_id=f"decision-{fold}",
        candidate_id=f"candidate-{fold}",
        trader_id=trader,
        signal_fingerprint=f"signal-{fold}",
        account_identity_fingerprint="ctrader:demo:account-a",
        qualification_fold_id=f"WF{fold}",
        decision_at=decision_at,
        deployed_at=decision_at + timedelta(seconds=1),
        settled_at=decision_at + timedelta(hours=2),
        source_generation=1,
        deployed_capital_usd=Decimal("10"),
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("2"),
        realized_pnl_usd=Decimal("3"),
        protected_floor_graduation_usd=Decimal("1"),
        decision_evidence_sha256=_sha("1"),
        provider_economics_sha256=_sha("2"),
        risk_lineage_sha256=_sha("3"),
        cma_lineage_sha256=_sha("4"),
        terminal_settlement_sha256=_sha("5"),
        release_evidence_sha256=_sha("6"),
        source_manifest_sha256=_sha("7"),
        frozen_candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        frozen_candidate_code_sha=FROZEN_PHASE20_POLICY_CANDIDATE.code_sha,
        evidence_kind=CompoundPopulationEvidenceKind.FORWARD_OBSERVED,
        floor_evidence_sha256=_sha("8"),
    )


def _population() -> tuple[ForwardCompoundEconomicRecord, ...]:
    return (
        _record(1),
        _record(2, trader=TraderLineage.R34_XAUUSD),
        _record(3),
        _record(4, trader=TraderLineage.R34_XAUUSD),
    )


def test_real_population_binding_emits_canonical_mc_episodes() -> None:
    records = _population()

    episodes = bind_forward_compound_population(records)

    assert tuple(item.episode_id for item in episodes) == (
        "episode-1",
        "episode-2",
        "episode-3",
        "episode-4",
    )
    assert all(item.market_record_present for item in episodes)
    assert all(item.terminal_release_present for item in episodes)
    assert all(not item.future_leakage_used for item in episodes)
    assert episodes[0].deployed_capital_usd == Decimal("10")
    assert episodes[0].stop_risk_usd == Decimal("1")
    assert episodes[0].margin_usd == Decimal("2")
    assert episodes[0].realized_pnl_usd == Decimal("3")
    assert episodes[0].protected_floor_graduation_usd == Decimal("1")
    assert episodes[0].floor_evidence_sha256 == _sha("8")


def test_real_population_rejects_non_forward_evidence() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires FORWARD_OBSERVED evidence",
    ):
        replace(
            _record(1),
            evidence_kind=CompoundPopulationEvidenceKind.SYNTHETIC_CONTRACT,
        )


def test_real_population_rejects_pre_freeze_decision() -> None:
    before_freeze = FROZEN_PHASE20_POLICY_CANDIDATE.frozen_at - timedelta(
        seconds=1
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="pre-freeze decision",
    ):
        replace(
            _record(1),
            decision_at=before_freeze,
            deployed_at=before_freeze + timedelta(seconds=1),
            settled_at=before_freeze + timedelta(hours=1),
        )


def test_real_population_rejects_frozen_candidate_drift() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="frozen candidate lineage drift",
    ):
        replace(
            _record(1),
            frozen_candidate_code_sha="0" * 40,
        )


def test_real_population_rejects_duplicate_decision_identity() -> None:
    records = _population()
    duplicate = replace(
        records[1],
        decision_id=records[0].decision_id,
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="duplicate decision_id",
    ):
        bind_forward_compound_population(
            (records[0], duplicate, records[2], records[3])
        )


def test_real_population_requires_all_four_frozen_folds() -> None:
    records = _population()

    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires all four frozen temporal folds",
    ):
        bind_forward_compound_population(records[:3])


def test_real_population_rejects_overlapping_temporal_folds() -> None:
    records = _population()
    fold_two = replace(
        records[1],
        decision_at=T0 + timedelta(minutes=30),
        deployed_at=T0 + timedelta(minutes=30, seconds=1),
        settled_at=T0 + timedelta(hours=3),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="temporal folds overlap or interleave",
    ):
        bind_forward_compound_population(
            (records[0], fold_two, records[2], records[3])
        )


def test_real_population_rejects_missing_provider_economics_hash() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="provider_economics_sha256 must be canonical SHA-256",
    ):
        replace(
            _record(1),
            provider_economics_sha256="",
        )
