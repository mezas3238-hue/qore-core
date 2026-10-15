"""A G-M5 PASS cannot be manufactured by source-open flags or PnL."""

import pytest

from qore.infrastructure.traders.crt_pure_methodological_certification import (
    CrtPureMethodGateEvidence,
    CrtPureMethodGateState,
    evaluate_methodological_gm5,
    present_vt08_gm5_status,
)


def test_current_gate_status_remains_uncertified() -> None:
    status = present_vt08_gm5_status()
    assert status.certificate_issued is False
    assert status.source_closed is False
    assert len(status.gate_states) == 4
    assert all(state is CrtPureMethodGateState.PARTIAL for _, state in status.gate_states)
    assert "THREE_SOURCE_RULE_OPEN:multiple_reference_priority" in status.blockers
    assert status.volume_authorized is False
    assert status.demo_authorized is False
    assert status.live_authorized is False


def test_forged_four_pass_attestations_still_cannot_certify_source_open() -> None:
    gates = tuple(
        CrtPureMethodGateEvidence(
            gate_id=gate_id,
            state=CrtPureMethodGateState.PASS,
            audited_source_refs=("https://example.org/evidence",),
            independent_adjudicator="independent-reviewer",
            no_future_leak_attested=True,
        )
        for gate_id in ("G-M1", "G-M2", "G-M3", "G-M4")
    )
    result = evaluate_methodological_gm5(gates)
    assert result.certificate_issued is False
    assert "THREE_SOURCE_RULE_OPEN:multiple_reference_priority" in result.blockers
    assert all(
        f"{gate}_PASS_ATTESTATION_UNVERIFIED" in result.blockers
        for gate in ("G-M1", "G-M2", "G-M3", "G-M4")
    )
    assert all(not b.startswith("SOURCE_NOT_ADJUDICATED:") for b in result.blockers)


def test_pass_requires_provenance_and_independent_review() -> None:
    with pytest.raises(ValueError, match="PASS requires"):
        CrtPureMethodGateEvidence("G-M1", CrtPureMethodGateState.PASS)


def test_sizing_is_forbidden_in_any_gate() -> None:
    with pytest.raises(ValueError, match="categorically forbidden"):
        CrtPureMethodGateEvidence(
            "G-M2", CrtPureMethodGateState.PARTIAL, sizing_used=True
        )


def test_no_gate_may_be_omitted_or_duplicated() -> None:
    with pytest.raises(ValueError, match="ordered and unique"):
        evaluate_methodological_gm5((
            CrtPureMethodGateEvidence("G-M1", CrtPureMethodGateState.PARTIAL),
            CrtPureMethodGateEvidence("G-M1", CrtPureMethodGateState.PARTIAL),
            CrtPureMethodGateEvidence("G-M3", CrtPureMethodGateState.PARTIAL),
            CrtPureMethodGateEvidence("G-M4", CrtPureMethodGateState.PARTIAL),
        ))


def test_fake_approval_links_and_no_leak_boolean_cannot_issue_gm5() -> None:
    fake = tuple(
        CrtPureMethodGateEvidence(
            gate_id=name,
            state=CrtPureMethodGateState.PASS,
            audited_source_refs=("https://github.com/example/fake-review",),
            independent_adjudicator="FORGED_GITHUB_ACCOUNT",
            no_future_leak_attested=True,
        )
        for name in ("G-M1", "G-M2", "G-M3", "G-M4")
    )
    certificate = evaluate_methodological_gm5(fake)
    assert certificate.certificate_issued is False
    assert len([b for b in certificate.blockers if b.endswith("_PASS_ATTESTATION_UNVERIFIED")]) == 4
    assert not certificate.broker_order_authorized
    assert not certificate.demo_authorized
    assert not certificate.live_authorized
    assert not certificate.volume_authorized
