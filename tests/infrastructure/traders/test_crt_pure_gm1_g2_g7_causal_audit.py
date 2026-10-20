"""Adversarial G2/G7 invariants. These are not source approval or trading tests."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.traders.crt_pure_gm1_g2_g7_causal_audit import (
    CrtGm1CausalVerdict,
    CrtGm1Reference,
    CrtGm1SourceEvent,
    audit_g2_reference_conflicts,
    audit_g7_rearm,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

T0 = datetime(2026, 10, 10, 8, tzinfo=UTC)
SHA = "a" * 64


def ref(
    id: str = "c1",
    *,
    parent: str = "h4-1",
    direction: CrtPureCandidateDirection = CrtPureCandidateDirection.BULLISH,
    close_at: datetime = T0,
    known_at: datetime = T0 + timedelta(minutes=1),
    market: CrtPureMarket = CrtPureMarket.AUDUSD,
) -> CrtGm1Reference:
    return CrtGm1Reference(
        market, id, parent, direction, close_at, known_at, SHA
    )


def decide(references: tuple[CrtGm1Reference, ...], complete: bool = True):
    return audit_g2_reference_conflicts(
        market=CrtPureMarket.AUDUSD, parent_id="h4-1", decision_at=T0 + timedelta(minutes=5),
        references=references, inventory_complete=complete,
    )


def evt(
    parent: str,
    source: str,
    hyp: str,
    generation: int,
    *,
    observed: datetime = T0,
    decision: datetime = T0 + timedelta(minutes=5),
    market: CrtPureMarket = CrtPureMarket.AUDUSD,
    terminal: datetime | None = None,
) -> CrtGm1SourceEvent:
    return CrtGm1SourceEvent(
        market, parent, source, hyp, generation, observed, decision, terminal
    )


def test_unique_causal_reference_is_only_provisional() -> None:
    v = decide((ref(),))
    assert v.verdict is CrtGm1CausalVerdict.PROVISIONAL
    assert v.selected_reference_id == "c1"
    assert not v.grants_execution_authority
    assert not v.grants_capital_authority


def test_conflicting_bull_bear_and_duplicate_direction_refs_abstain() -> None:
    for direction in (
        CrtPureCandidateDirection.BEARISH,
        CrtPureCandidateDirection.BULLISH,
    ):
        v = decide((ref(), ref("c2", direction=direction)))
        assert v.verdict is CrtGm1CausalVerdict.ABSTAIN
        assert v.selected_reference_id is None
        assert "MULTIPLE_REFERENCE_PRIORITY_NOT_ADJUDICATED" in v.reasons


def test_incomplete_inventory_never_claims_unique_coverage() -> None:
    v = decide((ref(),), complete=False)
    assert v.verdict is CrtGm1CausalVerdict.WAIT
    assert v.selected_reference_id is None


def test_no_reference_waits_without_inventing_old_crth() -> None:
    assert decide(()).verdict is CrtGm1CausalVerdict.WAIT


@pytest.mark.parametrize("records,message", [
    ((ref(), ref()), "duplicate reference"),
    ((ref(parent="another"),), "cross-parent"),
    ((ref(close_at=T0 + timedelta(minutes=6),
          known_at=T0 + timedelta(minutes=7)),), "future reference"),
    ((ref(known_at=T0 + timedelta(minutes=6)),), "future reference"),
])
def test_g2_bad_prefix_is_rejected(records, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        decide(records)


def test_g2_reference_must_close_before_discovery() -> None:
    with pytest.raises(ValueError, match="discovered before close"):
        ref(known_at=T0 - timedelta(minutes=1))


def test_g2_missing_evidence_digest_is_not_accepted() -> None:
    with pytest.raises(ValueError, match="SHA256"):
        CrtGm1Reference(
            CrtPureMarket.AUDUSD, "a", "h4-1",
            CrtPureCandidateDirection.BULLISH, T0, T0, "NOT_SHA",
        )


def test_g2_future_mutation_does_not_retroactively_change_first_decision() -> None:
    earlier = decide((ref(),))
    with pytest.raises(ValueError, match="future reference"):
        decide((ref(), ref("added-later", known_at=T0 + timedelta(hours=1))))
    assert earlier.selected_reference_id == "c1"


def test_g7_first_source_is_not_an_executable_rearm() -> None:
    v = audit_g7_rearm(proposal=evt("p1", "e1", "h1", 1), observed_history=())
    assert v.verdict is CrtGm1CausalVerdict.PROVISIONAL
    assert not v.grants_rearm_authority
    assert not v.grants_execution_authority
    assert not v.grants_capital_authority


def test_g7_same_parent_cannot_reenter_with_fresh_ids() -> None:
    history = (evt("p1", "e1", "h1", 1),)
    next_event = evt(
        "p1", "e2", "h2", 2,
        observed=T0 + timedelta(minutes=6),
        decision=T0 + timedelta(minutes=10),
    )
    v = audit_g7_rearm(proposal=next_event, observed_history=history)
    assert v.verdict is CrtGm1CausalVerdict.ABSTAIN
    assert "H4_PARENT_ALREADY_USED" in v.reasons


@pytest.mark.parametrize("source,hyp,gen,expected", [
    ("e1", "h2", 2, "SOURCE_OR_HYPOTHESIS_REPLAY"),
    ("e2", "h1", 2, "SOURCE_OR_HYPOTHESIS_REPLAY"),
    ("e2", "h2", 1, "NONMONOTONIC_EVENT_GENERATION"),
])
def test_g7_event_replay_and_generation_fails(source, hyp, gen, expected: str) -> None:
    prior = evt("p1", "e1", "h1", 1)
    proposal = evt(
        "p2", source, hyp, gen,
        observed=T0 + timedelta(minutes=6),
        decision=T0 + timedelta(minutes=10),
    )
    v = audit_g7_rearm(proposal=proposal, observed_history=(prior,))
    assert v.verdict is CrtGm1CausalVerdict.ABSTAIN
    assert expected in v.reasons


def test_g7_new_parent_is_provisional_but_not_authorized() -> None:
    prior = evt(
        "p1", "e1", "h1", 1,
        terminal=T0 + timedelta(minutes=5, seconds=1),
    )
    later = evt(
        "p2", "e2", "h2", 2,
        observed=T0 + timedelta(minutes=6),
        decision=T0 + timedelta(minutes=10),
    )
    v = audit_g7_rearm(proposal=later, observed_history=(prior,))
    assert v.verdict is CrtGm1CausalVerdict.PROVISIONAL
    assert "NEW_PARENT_AND_SOURCE_CAUSALLY_OBSERVED" in v.reasons
    assert not v.grants_rearm_authority
    assert not v.grants_execution_authority


def test_g7_stale_observation_even_with_new_event_is_rejected() -> None:
    v = audit_g7_rearm(
        observed_history=(evt("p1", "e1", "h1", 1),),
        proposal=evt(
            "p2", "e2", "h2", 2,
            observed=T0 + timedelta(minutes=3),
            decision=T0 + timedelta(minutes=10),
        ),
    )
    assert "SOURCE_EVENT_NOT_NEW_AFTER_PRIOR_DECISION" in v.reasons


def test_g7_future_and_duplicate_history_are_not_admitted() -> None:
    prior = evt("p1", "e1", "h1", 1)
    proposal = evt(
        "p2", "e2", "h2", 2,
        observed=T0 + timedelta(minutes=6),
        decision=T0 + timedelta(minutes=10),
    )
    with pytest.raises(ValueError, match="duplicate G7 source"):
        audit_g7_rearm(proposal=proposal, observed_history=(prior, prior))
    with pytest.raises(ValueError, match="noncausal G7 history"):
        audit_g7_rearm(
            proposal=proposal,
            observed_history=(evt(
                "px", "ex", "hx", 1,
                decision=T0 + timedelta(minutes=20),
            ),),
        )


def test_g7_invalid_source_timestamp_rejected() -> None:
    with pytest.raises(ValueError, match="observed after decision"):
        evt(
            "p", "s", "h", 1,
            observed=T0 + timedelta(minutes=11),
            decision=T0 + timedelta(minutes=10),
        )



def test_g2_cross_market_contamination_denied() -> None:
    with pytest.raises(ValueError, match="cross-market reference"):
        decide((ref(market=CrtPureMarket.USDJPY),))


def test_g7_cross_market_contamination_denied() -> None:
    prior = evt("p1", "e1", "h1", 1, market=CrtPureMarket.USDJPY)
    proposed = evt(
        "p2", "e2", "h2", 2,
        observed=T0 + timedelta(minutes=6),
        decision=T0 + timedelta(minutes=10),
    )
    with pytest.raises(ValueError, match="cross-market G7"):
        audit_g7_rearm(proposal=proposed, observed_history=(prior,))


@pytest.mark.parametrize("prior2,expected", [
    (("p2", "e1", "h2"), "duplicate G7 source"),
    (("p2", "e2", "h1"), "duplicate G7 hypothesis"),
    (("p1", "e2", "h2"), "duplicate G7 parent"),
])
def test_g7_corrupt_historical_ledger_fails_closed(
    prior2: tuple[str, str, str], expected: str,
) -> None:
    prior = evt("p1", "e1", "h1", 1)
    second = evt(
        *prior2, 2,
        observed=T0 + timedelta(minutes=6),
        decision=T0 + timedelta(minutes=10),
    )
    proposal = evt(
        "p3", "e3", "h3", 3,
        observed=T0 + timedelta(minutes=11),
        decision=T0 + timedelta(minutes=15),
    )
    with pytest.raises(ValueError, match=expected):
        audit_g7_rearm(proposal=proposal, observed_history=(prior, second))



def test_g7_missing_prior_terminal_requires_wait_not_rearm() -> None:
    prior = evt("p1", "e1", "h1", 1)
    proposed = evt(
        "p2", "e2", "h2", 2,
        observed=T0 + timedelta(minutes=6),
        decision=T0 + timedelta(minutes=10),
    )
    result = audit_g7_rearm(proposal=proposed, observed_history=(prior,))
    assert result.verdict is CrtGm1CausalVerdict.WAIT
    assert "PRIOR_THESIS_NOT_TERMINAL_BEFORE_NEW_SOURCE" in result.reasons
    assert not result.grants_rearm_authority


def test_g7_terminal_after_next_source_is_not_preexisting_evidence() -> None:
    prior = evt(
        "p1", "e1", "h1", 1,
        terminal=T0 + timedelta(minutes=7),
    )
    proposed = evt(
        "p2", "e2", "h2", 2,
        observed=T0 + timedelta(minutes=6),
        decision=T0 + timedelta(minutes=10),
    )
    result = audit_g7_rearm(proposal=proposed, observed_history=(prior,))
    assert result.verdict is CrtGm1CausalVerdict.WAIT


def test_g7_future_terminal_and_predecision_terminal_are_not_accepted() -> None:
    with pytest.raises(ValueError, match="terminal observation predates decision"):
        evt("p1", "e1", "h1", 1, terminal=T0 + timedelta(minutes=4))
    prior = evt(
        "p1", "e1", "h1", 1,
        terminal=T0 + timedelta(minutes=12),
    )
    proposed = evt(
        "p2", "e2", "h2", 2,
        observed=T0 + timedelta(minutes=6),
        decision=T0 + timedelta(minutes=10),
    )
    with pytest.raises(ValueError, match="future terminal evidence"):
        audit_g7_rearm(proposal=proposed, observed_history=(prior,))
