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


def test_source_observation_contract_keeps_replay_blocked_until_detectors_close() -> None:
    contract = SOURCE_OBSERVATION_CONTRACT

    assert all(item.detector_implemented is False for item in contract.requirements)
    assert all(item.source_equivalence_tested is False for item in contract.requirements)
    assert contract.outcome_aware_detector_allowed is False
    assert contract.numeric_fit_to_backtest_allowed is False
    assert contract.replay_authorized is False
