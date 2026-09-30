from qore.infrastructure.trader_lab.capitalizer_source_closure_adjudication_v48 import (
    V48_SOURCE_CLOSURE_ADJUDICATION,
    V48HistoricalClosureStatus,
)


def test_historical_v2_closure_is_preserved_but_superseded_for_source_fidelity() -> None:
    state = V48_SOURCE_CLOSURE_ADJUDICATION
    assert state.historical_status is V48HistoricalClosureStatus.PRESERVED_HISTORICAL_EVIDENCE
    assert state.current_source_fidelity_status is (
        V48HistoricalClosureStatus.SUPERSEDED_FOR_SOURCE_FIDELITY
    )
    assert state.historical_files_must_be_deleted is False
    assert state.v47_results_invalidated_as_history is False


def test_supersession_does_not_authorize_fresh_or_economics() -> None:
    assert V48_SOURCE_CLOSURE_ADJUDICATION.fresh_holdout_authorized is False
    assert V48_SOURCE_CLOSURE_ADJUDICATION.economics_authorized is False
