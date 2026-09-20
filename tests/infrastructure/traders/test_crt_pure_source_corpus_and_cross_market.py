import pytest

from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureReasoningAction,
)
from qore.infrastructure.traders.crt_pure_cross_market_cognition import (
    CrtPureCompetitionState,
    CrtPureCrossMarketEdge,
    CrtPureCrossMarketRelation,
    CrtPureOpportunityCandidate,
    compete,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_source_corpus import (
    CRT_PURE_PRIMARY_SOURCE_CORPUS,
    CrtPureSourceArtifactStatus,
    pending_primary_locators,
    verified_primary_artifacts,
)


def test_primary_corpus_contains_verified_romeo_series_and_kod_pdf() -> None:
    verified = verified_primary_artifacts()
    ids = {item.artifact_id for item in verified}
    assert "ROMEO_CRT_SECRETS_EP01" in ids
    assert "ROMEO_CRT_SECRETS_EP02" in ids
    assert "ROMEO_KOD_PDF" in ids
    assert "ROMEO_CRT_SECRETS_EP09" in ids
    assert "ROMEO_CRTOLOGY_EP01" in ids
    assert "ROMEO_CRTOLOGY_EP02" in ids
    assert all(
        item.status is CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK
        for item in verified
    )


def test_unresolved_primary_locators_remain_explicit() -> None:
    pending = {item.artifact_id for item in pending_primary_locators()}
    assert "ROMEO_CRT_FOUNDATION_VIDEO" in pending
    assert "ROMEO_CRT_SECRETS_EP06" in pending
    assert "ROMEO_CRT_SECRETS_EP10" in pending
    assert len(CRT_PURE_PRIMARY_SOURCE_CORPUS) == len(
        {item.artifact_id for item in CRT_PURE_PRIMARY_SOURCE_CORPUS}
    )


def _candidate(
    market: CrtPureMarket,
    action: CrtPureReasoningAction,
) -> CrtPureOpportunityCandidate:
    return CrtPureOpportunityCandidate(
        market=market,
        hypothesis_id=f"hyp-{market.value}",
        source_event_id=f"event-{market.value}",
        action=action,
    )


def test_single_execute_does_not_need_competition() -> None:
    result = compete(
        (
            _candidate(CrtPureMarket.AUDUSD, CrtPureReasoningAction.EXECUTE),
            _candidate(CrtPureMarket.USDJPY, CrtPureReasoningAction.WAIT),
        )
    )
    assert result.state is CrtPureCompetitionState.SINGLE_EXECUTABLE
    assert result.selected_market is None
    assert result.grants_capital_authority is False


def test_multiple_execute_candidates_are_handed_to_qore_risk_without_ranking() -> None:
    result = compete(
        (
            _candidate(CrtPureMarket.AUDUSD, CrtPureReasoningAction.EXECUTE),
            _candidate(CrtPureMarket.USDJPY, CrtPureReasoningAction.EXECUTE),
        )
    )
    assert result.state is CrtPureCompetitionState.MULTIPLE_REQUIRE_QORE_RISK
    assert result.selected_market is None
    assert result.relation_findings == ("AUDUSD:USDJPY:UNKNOWN",)


def test_non_unknown_cross_market_relation_requires_causal_evidence() -> None:
    with pytest.raises(ValueError, match="requires causal evidence"):
        CrtPureCrossMarketEdge(
            left=CrtPureMarket.AUDUSD,
            right=CrtPureMarket.USDJPY,
            relation=CrtPureCrossMarketRelation.REDUNDANT,
        )


def test_mutually_invalidating_executable_hypotheses_create_cognitive_conflict() -> None:
    edge = CrtPureCrossMarketEdge(
        left=CrtPureMarket.AUDUSD,
        right=CrtPureMarket.USDJPY,
        relation=CrtPureCrossMarketRelation.MUTUALLY_INVALIDATING,
        evidence_id="research-proof-001",
        causally_validated=True,
    )
    result = compete(
        (
            _candidate(CrtPureMarket.AUDUSD, CrtPureReasoningAction.EXECUTE),
            _candidate(CrtPureMarket.USDJPY, CrtPureReasoningAction.EXECUTE),
        ),
        causal_edges=(edge,),
    )
    assert result.state is CrtPureCompetitionState.COGNITIVE_CONFLICT
    assert result.selected_market is None
