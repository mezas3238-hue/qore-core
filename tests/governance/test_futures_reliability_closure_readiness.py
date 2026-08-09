from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import qore.infrastructure.futures_adapter_contracts as futures
import qore.infrastructure.futures_cross_provider_certification as cross
import qore.infrastructure.futures_paper_e2e as paper
import qore.infrastructure.futures_shadow_core as shadow
import qore.infrastructure.hosting_reliability_lab as lab
import qore.infrastructure.market_data_integrity as integrity

_REQUIRED_DELIVERIES = (
    "QORE-FUTURES-RELIABILITY-PROGRAM-SCOPE-001",
    "QORE-HOSTING-RELIABILITY-LAB-CONTRACTS-001",
    "QORE-LATENCY-SAFETY-ENVELOPE-001",
    "QORE-HOSTING-IO-CERTIFICATION-001",
    "QORE-MARKET-DATA-INTEGRITY-CERTIFICATION-001",
    "QORE-RELIABILITY-INCIDENT-GENEALOGY-001",
    "QORE-EVIDENCE-GOVERNED-FAILOVER-001",
    "QORE-FUTURES-ADAPTER-CONTRACTS-001",
    "QORE-FUTURES-TRADESTATION-ADAPTER-001",
    "QORE-FUTURES-IBKR-ADAPTER-001",
    "QORE-FUTURES-TASTYTRADE-ADAPTER-001",
    "QORE-FUTURES-CROSS-PROVIDER-CERTIFICATION-001",
    "QORE-SHADOW-FUTURES-CORE-CERTIFICATION-001",
    "QORE-HOSTING-RELIABILITY-DRILL-001",
    "QORE-PAPER-FUTURES-E2E-001",
    "QORE-FUTURES-RELIABILITY-CLOSURE-001",
)

_REQUIRED_ARTIFACTS = (
    "docs/missions/FUTURES-HOSTING-RELIABILITY-CERTIFICATION-PROGRAM.md",
    "docs/architecture/QORE-FUTURES-RELIABILITY-PROGRAM-SCOPE-001.md",
    "docs/architecture/QORE-HOSTING-RELIABILITY-LAB-CONTRACTS-001.md",
    "docs/architecture/QORE-LATENCY-SAFETY-ENVELOPE-001.md",
    "docs/architecture/QORE-HOSTING-IO-CERTIFICATION-001.md",
    "docs/architecture/QORE-MARKET-DATA-INTEGRITY-CERTIFICATION-001.md",
    "docs/architecture/QORE-RELIABILITY-INCIDENT-GENEALOGY-001.md",
    "docs/architecture/QORE-EVIDENCE-GOVERNED-FAILOVER-001.md",
    "docs/architecture/QORE-FUTURES-ADAPTER-CONTRACTS-001.md",
    "docs/architecture/QORE-FUTURES-TRADESTATION-ADAPTER-001.md",
    "docs/architecture/QORE-FUTURES-IBKR-ADAPTER-001.md",
    "docs/architecture/QORE-FUTURES-TASTYTRADE-ADAPTER-001.md",
    "docs/architecture/QORE-FUTURES-CROSS-PROVIDER-CERTIFICATION-001.md",
    "docs/architecture/QORE-SHADOW-FUTURES-CORE-CERTIFICATION-001.md",
    "docs/architecture/QORE-HOSTING-RELIABILITY-DRILL-001.md",
    "docs/architecture/QORE-PAPER-FUTURES-E2E-001.md",
    "docs/architecture/QORE-FUTURES-RELIABILITY-CLOSURE-001.md",
    "docs/missions/FUTURES-HOSTING-RELIABILITY-CERTIFICATION-PROGRAM-CLOSURE.md",
)


def test_futures_reliability_closure_records_all_mandatory_deliveries() -> None:
    scope = Path(
        "docs/missions/FUTURES-HOSTING-RELIABILITY-CERTIFICATION-PROGRAM.md"
    ).read_text(encoding="utf-8")
    closure = Path(
        "docs/missions/FUTURES-HOSTING-RELIABILITY-CERTIFICATION-PROGRAM-CLOSURE.md"
    ).read_text(encoding="utf-8")

    for delivery in _REQUIRED_DELIVERIES:
        assert delivery in scope or delivery in closure
    for artifact in _REQUIRED_ARTIFACTS:
        assert Path(artifact).is_file(), artifact

    assert "QORE-FUTURES-TRADOVATE-CANDIDATE-001" in scope
    assert "Delivery 13 is explicitly optional" in closure


def test_futures_reliability_closure_keeps_exact_three_mandatory_providers() -> None:
    providers = {
        paper.TRADESTATION_PROVIDER.value,
        paper.IBKR_PROVIDER.value,
        paper.TASTYTRADE_PROVIDER.value,
    }
    assert providers == {"tradestation", "ibkr", "tastytrade"}

    environments = {item.value for item in futures.FuturesExecutionEnvironment}
    assert environments == {"paper", "simulation"}
    assert "production" not in environments
    assert "live" not in environments


def test_futures_execution_requires_core_decision_and_writer_authority() -> None:
    request_fields = {field.name for field in fields(futures.FuturesExecutionRequest)}

    assert "decision_id" in request_fields
    assert "authority" in request_fields
    assert "account_id" in request_fields
    assert "runtime_ref" in request_fields
    assert "idempotency_key" in request_fields

    replay_states = {item.value for item in futures.FuturesReplayDisposition}
    assert replay_states == {
        "new_request_unseen",
        "duplicate_already_known",
        "idempotency_conflict",
    }
    assert replay_states.isdisjoint({"retry", "redispatch", "resend"})


def test_futures_adapter_secret_boundary_remains_reference_only() -> None:
    profile_fields = {field.name for field in fields(futures.FuturesAdapterProfile)}

    assert "secret_refs" in profile_fields
    assert profile_fields.isdisjoint(
        {
            "access_token",
            "authorization_header",
            "bearer_token",
            "password",
            "refresh_token",
            "secret_value",
            "token",
        }
    )


def test_reliability_lab_has_no_direct_failover_or_trading_authority() -> None:
    actions = {item.value for item in lab.HostingReliabilityInfrastructureAction}
    assert actions == {
        "no_action",
        "contain_new_work",
        "run_stabilization",
        "initiate_failover_evaluation",
    }
    assert actions.isdisjoint(
        {
            "buy",
            "sell",
            "failover",
            "switch_server",
            "switch_provider",
            "acquire_lease",
        }
    )


def test_market_data_integrity_states_remain_explicit_and_non_synthetic() -> None:
    states = {item.value for item in integrity.MarketDataIntegrityState}
    assert states == {
        "valid",
        "delayed",
        "gap_detected",
        "duplicate",
        "out_of_order",
        "corrupted",
        "quarantined",
    }

    prohibited = {"repair_candle", "replace_candle", "synthesize_candle"}
    assert prohibited.isdisjoint(set(dir(integrity.MarketDataIntegrityAssessment)))


def test_cross_provider_shadow_and_paper_certificates_do_not_mutate_authority() -> None:
    prohibited = {
        "activate_provider",
        "buy",
        "redispatch_order",
        "retry_order",
        "sell",
        "submit_order",
        "switch_provider",
        "switch_server",
    }
    for surface in (
        cross.FuturesCrossProviderAssessment,
        shadow.FuturesShadowDecisionRecord,
        paper.FuturesPaperE2ECaseResult,
        paper.FuturesPaperE2EReport,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))

    sinks = {item.value for item in shadow.FuturesShadowSink}
    assert sinks == {"null_shadow_sink"}
    statuses = {item.value for item in paper.FuturesPaperE2ECertificationStatus}
    assert statuses == {"certified_offline"}


def test_futures_reliability_closure_preserves_external_blocker_and_production() -> None:
    closure = Path(
        "docs/missions/FUTURES-HOSTING-RELIABILITY-CERTIFICATION-PROGRAM-CLOSURE.md"
    ).read_text(encoding="utf-8")
    architecture = Path(
        "docs/architecture/QORE-FUTURES-RELIABILITY-CLOSURE-001.md"
    ).read_text(encoding="utf-8")

    assert "#146" in closure
    assert "OPEN/BLOCKED" in closure
    assert "Production = CLOSED" in closure
    assert "Futures Production = CLOSED" in closure
    assert "Native Broker Production = CLOSED" in closure
    assert "Real capital = CLOSED" in closure
    assert "NO CORE DECISION -> NO NEW TRADING ACTION" in architecture
    assert "NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION" in architecture
    assert "AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE" in architecture
