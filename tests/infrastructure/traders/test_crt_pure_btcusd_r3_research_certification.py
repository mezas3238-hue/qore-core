from __future__ import annotations

from qore.infrastructure.traders.crt_pure_btcusd_r3_research_certification import (
    BTCUSD_DEMO_AUTHORIZED,
    BTCUSD_LIVE_AUTHORIZED,
    BTCUSD_PRODUCTION_AUTHORIZED,
    BTCUSD_REAL_CAPITAL_AUTHORIZED,
    BTCUSD_RESEARCH_CERTIFIED,
    CANDIDATE_IDENTITY,
    EVIDENCE_REFS,
    btcusd_research_certification_readiness,
)
from qore.infrastructure.traders.crt_pure_market_certification_readiness import (
    CrtPureMarketCertificationStage,
)


def test_btcusd_r3_exact_candidate_is_research_certified() -> None:
    readiness = btcusd_research_certification_readiness()

    assert CANDIDATE_IDENTITY == "VT08_CRT_PURE_BTCUSD_R3_REF2_PLUS_001"
    assert len(EVIDENCE_REFS) == 4
    assert readiness.stage is CrtPureMarketCertificationStage.RESEARCH_CERTIFIED
    assert BTCUSD_RESEARCH_CERTIFIED is True


def test_btcusd_research_seal_grants_no_deployment_authority() -> None:
    assert BTCUSD_DEMO_AUTHORIZED is False
    assert BTCUSD_LIVE_AUTHORIZED is False
    assert BTCUSD_REAL_CAPITAL_AUTHORIZED is False
    assert BTCUSD_PRODUCTION_AUTHORIZED is False
