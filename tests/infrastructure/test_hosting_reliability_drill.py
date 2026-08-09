from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.hosting_reliability_drill as drill

_NOW = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"67000000-0000-0000-0000-{suffix:012d}")


def _expected_disposition(
    scenario: drill.HostingReliabilityDrillScenario,
) -> drill.HostingReliabilityDrillDisposition:
    mapping = {
        drill.HostingReliabilityDrillScenario.SERVER_SHUTDOWN: (
            drill.HostingReliabilityDrillDisposition.CONTAINED
        ),
        drill.HostingReliabilityDrillScenario.HEARTBEAT_LOSS: (
            drill.HostingReliabilityDrillDisposition.CONTAINED
        ),
        drill.HostingReliabilityDrillScenario.NETWORK_DEGRADATION: (
            drill.HostingReliabilityDrillDisposition.CONTAINED
        ),
        drill.HostingReliabilityDrillScenario.LATENCY_300MS_PLUS: (
            drill.HostingReliabilityDrillDisposition.CONTAINED
        ),
        drill.HostingReliabilityDrillScenario.HIGH_JITTER: (
            drill.HostingReliabilityDrillDisposition.CONTAINED
        ),
        drill.HostingReliabilityDrillScenario.PACKET_LOSS: (
            drill.HostingReliabilityDrillDisposition.CONTAINED
        ),
        drill.HostingReliabilityDrillScenario.INGRESS_HEALTHY_EGRESS_BAD: (
            drill.HostingReliabilityDrillDisposition.CONTAINED
        ),
        drill.HostingReliabilityDrillScenario.EGRESS_HEALTHY_INGRESS_BAD: (
            drill.HostingReliabilityDrillDisposition.CONTAINED
        ),
        drill.HostingReliabilityDrillScenario.CANDIDATE_SERVER_UNHEALTHY: (
            drill.HostingReliabilityDrillDisposition.BLOCKED
        ),
        drill.HostingReliabilityDrillScenario.STALE_LEASE: (
            drill.HostingReliabilityDrillDisposition.BLOCKED
        ),
        drill.HostingReliabilityDrillScenario.DUPLICATE_EVENT: (
            drill.HostingReliabilityDrillDisposition.QUARANTINED
        ),
        drill.HostingReliabilityDrillScenario.DELAYED_MESSAGE: (
            drill.HostingReliabilityDrillDisposition.RECONCILIATION_REQUIRED
        ),
        drill.HostingReliabilityDrillScenario.OUT_OF_ORDER_MARKET_DATA: (
            drill.HostingReliabilityDrillDisposition.QUARANTINED
        ),
        drill.HostingReliabilityDrillScenario.FEED_DISCONNECT: (
            drill.HostingReliabilityDrillDisposition.CONTAINED
        ),
        drill.HostingReliabilityDrillScenario.PROVIDER_DISAGREEMENT: (
            drill.HostingReliabilityDrillDisposition.BLOCKED
        ),
        drill.HostingReliabilityDrillScenario.AMBIGUOUS_ORDER_STATE: (
            drill.HostingReliabilityDrillDisposition.RECONCILIATION_REQUIRED
        ),
        drill.HostingReliabilityDrillScenario.PARTIAL_FILL: (
            drill.HostingReliabilityDrillDisposition.PRESERVE_AUTHORIZED_LIFECYCLE
        ),
        drill.HostingReliabilityDrillScenario.REJECT: (
            drill.HostingReliabilityDrillDisposition.OBSERVED_NO_RETRY
        ),
        drill.HostingReliabilityDrillScenario.LOST_ACK: (
            drill.HostingReliabilityDrillDisposition.RECONCILIATION_REQUIRED
        ),
    }
    return mapping[scenario]


def _result(
    scenario: drill.HostingReliabilityDrillScenario,
    *,
    suffix: int,
) -> drill.HostingReliabilityDrillResult:
    injection = drill.HostingReliabilityDrillInjection(
        scenario=scenario,
        injected_at=_NOW + timedelta(seconds=suffix),
        evidence_ref=drill.HostingReliabilityDrillEvidenceReference(_uuid(suffix)),
    )
    return drill.HostingReliabilityDrillResult(
        injection=injection,
        disposition=_expected_disposition(scenario),
        observed_at=injection.injected_at + timedelta(milliseconds=1),
        automatic_failover_triggered=False,
        order_redispatch_triggered=False,
        provider_switch_triggered=False,
        evidence_refs=(
            drill.HostingReliabilityDrillEvidenceReference(_uuid(suffix + 100)),
        ),
    )


def test_mandatory_drill_scenarios_cover_roadmap_failure_domains() -> None:
    assert {item.value for item in drill.MANDATORY_DRILL_SCENARIOS} == {
        "server_shutdown",
        "heartbeat_loss",
        "network_degradation",
        "latency_300ms_plus",
        "high_jitter",
        "packet_loss",
        "ingress_healthy_egress_bad",
        "egress_healthy_ingress_bad",
        "candidate_server_unhealthy",
        "stale_lease",
        "duplicate_event",
        "delayed_message",
        "out_of_order_market_data",
        "feed_disconnect",
        "provider_disagreement",
        "ambiguous_order_state",
        "partial_fill",
        "reject",
        "lost_ack",
    }


def test_infrastructure_failures_contain_or_block_without_automatic_failover() -> None:
    for index, scenario in enumerate(
        (
            drill.HostingReliabilityDrillScenario.SERVER_SHUTDOWN,
            drill.HostingReliabilityDrillScenario.HEARTBEAT_LOSS,
            drill.HostingReliabilityDrillScenario.NETWORK_DEGRADATION,
            drill.HostingReliabilityDrillScenario.LATENCY_300MS_PLUS,
            drill.HostingReliabilityDrillScenario.HIGH_JITTER,
            drill.HostingReliabilityDrillScenario.PACKET_LOSS,
            drill.HostingReliabilityDrillScenario.INGRESS_HEALTHY_EGRESS_BAD,
            drill.HostingReliabilityDrillScenario.EGRESS_HEALTHY_INGRESS_BAD,
            drill.HostingReliabilityDrillScenario.CANDIDATE_SERVER_UNHEALTHY,
            drill.HostingReliabilityDrillScenario.STALE_LEASE,
        )
    ):
        observed = _result(scenario, suffix=10 + index)
        assert observed.disposition in {
            drill.HostingReliabilityDrillDisposition.CONTAINED,
            drill.HostingReliabilityDrillDisposition.BLOCKED,
        }
        assert observed.automatic_failover_triggered is False


def test_market_data_failures_quarantine_contain_or_block_without_provider_switch() -> None:
    for index, scenario in enumerate(
        (
            drill.HostingReliabilityDrillScenario.DUPLICATE_EVENT,
            drill.HostingReliabilityDrillScenario.DELAYED_MESSAGE,
            drill.HostingReliabilityDrillScenario.OUT_OF_ORDER_MARKET_DATA,
            drill.HostingReliabilityDrillScenario.FEED_DISCONNECT,
            drill.HostingReliabilityDrillScenario.PROVIDER_DISAGREEMENT,
        )
    ):
        observed = _result(scenario, suffix=30 + index)
        assert observed.provider_switch_triggered is False
        assert observed.order_redispatch_triggered is False


def test_execution_ambiguity_partial_fill_reject_and_lost_ack_never_redispatch() -> None:
    ambiguous = _result(
        drill.HostingReliabilityDrillScenario.AMBIGUOUS_ORDER_STATE,
        suffix=40,
    )
    partial = _result(drill.HostingReliabilityDrillScenario.PARTIAL_FILL, suffix=41)
    rejected = _result(drill.HostingReliabilityDrillScenario.REJECT, suffix=42)
    lost_ack = _result(drill.HostingReliabilityDrillScenario.LOST_ACK, suffix=43)

    assert ambiguous.disposition is (
        drill.HostingReliabilityDrillDisposition.RECONCILIATION_REQUIRED
    )
    assert lost_ack.disposition is (
        drill.HostingReliabilityDrillDisposition.RECONCILIATION_REQUIRED
    )
    assert partial.disposition is (
        drill.HostingReliabilityDrillDisposition.PRESERVE_AUTHORIZED_LIFECYCLE
    )
    assert rejected.disposition is (
        drill.HostingReliabilityDrillDisposition.OBSERVED_NO_RETRY
    )
    assert all(
        item.order_redispatch_triggered is False
        for item in (ambiguous, partial, rejected, lost_ack)
    )


def test_drill_contract_rejects_automatic_failover_redispatch_or_provider_switch() -> None:
    injection = drill.HostingReliabilityDrillInjection(
        scenario=drill.HostingReliabilityDrillScenario.LOST_ACK,
        injected_at=_NOW,
        evidence_ref=drill.HostingReliabilityDrillEvidenceReference(_uuid(50)),
    )
    for field_name in (
        "automatic_failover_triggered",
        "order_redispatch_triggered",
        "provider_switch_triggered",
    ):
        values = {
            "automatic_failover_triggered": False,
            "order_redispatch_triggered": False,
            "provider_switch_triggered": False,
        }
        values[field_name] = True
        with pytest.raises(drill.HostingReliabilityDrillValidationError):
            drill.HostingReliabilityDrillResult(
                injection=injection,
                disposition=(
                    drill.HostingReliabilityDrillDisposition.RECONCILIATION_REQUIRED
                ),
                observed_at=_NOW + timedelta(milliseconds=1),
                evidence_refs=(
                    drill.HostingReliabilityDrillEvidenceReference(_uuid(51)),
                ),
                **values,
            )


def test_drill_contract_rejects_unsafe_disposition_for_scenario() -> None:
    injection = drill.HostingReliabilityDrillInjection(
        scenario=drill.HostingReliabilityDrillScenario.CANDIDATE_SERVER_UNHEALTHY,
        injected_at=_NOW,
        evidence_ref=drill.HostingReliabilityDrillEvidenceReference(_uuid(60)),
    )
    with pytest.raises(drill.HostingReliabilityDrillValidationError):
        drill.HostingReliabilityDrillResult(
            injection=injection,
            disposition=drill.HostingReliabilityDrillDisposition.CONTAINED,
            observed_at=_NOW + timedelta(milliseconds=1),
            automatic_failover_triggered=False,
            order_redispatch_triggered=False,
            provider_switch_triggered=False,
            evidence_refs=(
                drill.HostingReliabilityDrillEvidenceReference(_uuid(61)),
            ),
        )


def test_full_offline_drill_report_requires_every_scenario_exactly_once() -> None:
    results = tuple(
        _result(scenario, suffix=100 + index)
        for index, scenario in enumerate(
            sorted(drill.MANDATORY_DRILL_SCENARIOS, key=lambda item: item.value)
        )
    )
    report = drill.HostingReliabilityDrillReport(
        drill_id=drill.HostingReliabilityDrillId(_uuid(200)),
        results=results,
        started_at=_NOW,
        ended_at=_NOW + timedelta(seconds=200),
        reported_at=_NOW + timedelta(seconds=201),
        evidence_ref=drill.HostingReliabilityDrillEvidenceReference(_uuid(201)),
    )

    assert report.certification_status is (
        drill.HostingReliabilityDrillCertificationStatus.CERTIFIED_OFFLINE
    )
    assert report.automatic_failovers == 0
    assert report.order_redispatches == 0
    assert report.provider_switches == 0


def test_incomplete_drill_report_cannot_be_certified() -> None:
    results = tuple(
        _result(scenario, suffix=300 + index)
        for index, scenario in enumerate(
            sorted(drill.MANDATORY_DRILL_SCENARIOS, key=lambda item: item.value)[:-1]
        )
    )
    with pytest.raises(drill.HostingReliabilityDrillValidationError):
        drill.HostingReliabilityDrillReport(
            drill_id=drill.HostingReliabilityDrillId(_uuid(400)),
            results=results,
            started_at=_NOW,
            ended_at=_NOW + timedelta(seconds=300),
            reported_at=_NOW + timedelta(seconds=301),
            evidence_ref=drill.HostingReliabilityDrillEvidenceReference(_uuid(401)),
        )
