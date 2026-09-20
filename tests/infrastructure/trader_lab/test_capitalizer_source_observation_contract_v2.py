from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerChainStatus,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_contract_v2 import (
    SOURCE_OBSERVATION_CONTRACT,
    CapitalizerSourceObservationKind,
)


def test_source_observation_contract_covers_every_required_detector() -> None:
    contract = SOURCE_OBSERVATION_CONTRACT

    assert contract.status is CapitalizerChainStatus.RESEARCH_OPEN
    assert {item.kind for item in contract.requirements} == set(
        CapitalizerSourceObservationKind
    )
    assert all(item.decision_time_only is True for item in contract.requirements)
    assert all(item.source_fact_ids for item in contract.requirements)


def test_source_observation_contract_keeps_replay_blocked_only_for_open_requirements() -> None:
    contract = SOURCE_OBSERVATION_CONTRACT
    by_kind = {item.kind: item for item in contract.requirements}

    asian = by_kind[CapitalizerSourceObservationKind.HISTORICAL_ASIAN_OPEN_REFERENCE]
    assert asian.detector_implemented is False
    assert asian.source_equivalence_tested is False

    implemented = tuple(
        item
        for item in contract.requirements
        if item.kind is not CapitalizerSourceObservationKind.HISTORICAL_ASIAN_OPEN_REFERENCE
    )
    assert implemented
    assert all(item.detector_implemented is True for item in implemented)
    assert all(item.source_equivalence_tested is True for item in implemented)
    assert contract.outcome_aware_detector_allowed is False
    assert contract.numeric_fit_to_backtest_allowed is False
    assert contract.replay_authorized is False
